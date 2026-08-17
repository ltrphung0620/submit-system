from __future__ import annotations

import codecs
import csv
import hashlib
import io
import json
import re
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Protocol

from app.errors import ApiError
from app.models import Query, ResultCandidate

PREVIEW_COLUMNS = [
    "file_name",
    "query_type",
    "priority",
    "video_id",
    "img_id",
    "answer",
    "submitter",
]
HISTORY_COLUMNS = [
    "received_at",
    "file_name",
    "query_type",
    "arrival_seq",
    "priority",
    "video_id",
    "img_id",
    "answer",
    "submitter",
    "note",
    "status",
    "updated_at",
    "deleted_at",
]


class OfficialFormatProvider(Protocol):
    @property
    def verified(self) -> bool: ...

    def serialize(self, query_type: str, query: Query) -> tuple[str, bytes]: ...


class UnverifiedOfficialFormatProvider:
    @property
    def verified(self) -> bool:
        return False

    def require_verified(self) -> None:
        raise ApiError(
            409,
            "OFFICIAL_FORMAT_NOT_VERIFIED",
            "Chưa thể xác minh định dạng submission chính thức",
            details={
                "missing": [
                    "KIS/QA/TRAKE columns",
                    "header and encoding",
                    "filename mapping",
                    "candidate selection policy",
                    "official accepted fixture",
                ]
            },
        )

    def serialize(self, query_type: str, query: Query) -> tuple[str, bytes]:
        self.require_verified()
        raise AssertionError("require_verified always raises for the unverified provider")


class OfficialCsvExporter:
    query_type: str

    def __init__(self, provider: OfficialFormatProvider) -> None:
        self.provider = provider

    def serialize(self, query: Query) -> tuple[str, bytes]:
        if query.query_type != self.query_type:
            raise ApiError(422, "EXPORT_QUERY_TYPE_MISMATCH", "Sai adapter CSV cho query type")
        return self.provider.serialize(self.query_type, query)


class KisCsvExporter(OfficialCsvExporter):
    query_type = "kis"


class QaCsvExporter(OfficialCsvExporter):
    query_type = "qa"


class TrakeCsvExporter(OfficialCsvExporter):
    query_type = "trake"


class ExportSelectionPolicy:
    """Internal preview policy: all active valid candidates in backend priority order."""

    @staticmethod
    def select(query: Query) -> list[ResultCandidate]:
        return sorted(
            (
                result
                for result in query.results
                if result.deleted_at is None and result.structural_validation_status == "valid"
            ),
            key=lambda result: (result.priority, result.arrival_seq),
        )


class PreviewCsvExporter:
    def serialize(self, query: Query) -> bytes:
        output = io.StringIO(newline="")
        writer = csv.DictWriter(output, fieldnames=PREVIEW_COLUMNS, lineterminator="\r\n")
        writer.writeheader()
        for result in ExportSelectionPolicy.select(query):
            writer.writerow(
                {
                    "file_name": query.file_name,
                    "query_type": query.query_type,
                    "priority": result.priority,
                    "video_id": result.video_id,
                    "img_id": json.dumps(
                        result.frame_ids, ensure_ascii=False, separators=(",", ":")
                    )
                    if query.query_type == "trake"
                    else result.frame_ids[0],
                    "answer": result.answer or "",
                    "submitter": result.submitter,
                }
            )
        return output.getvalue().encode("utf-8-sig")


def utc_iso(value: datetime | None) -> str:
    if value is None:
        return ""
    aware = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    return aware.astimezone(UTC).isoformat().replace("+00:00", "Z")


class SubmissionHistoryCsvExporter:
    """Operational history export; deliberately separate from official competition output."""

    def serialize(self, results: list[ResultCandidate]) -> bytes:
        output = io.StringIO(newline="")
        writer = csv.DictWriter(output, fieldnames=HISTORY_COLUMNS, lineterminator="\r\n")
        writer.writeheader()
        for result in sorted(
            results,
            key=lambda item: (
                utc_iso(item.created_at),
                item.query.file_name_key,
                item.arrival_seq,
                item.id,
            ),
        ):
            query = result.query
            writer.writerow(
                {
                    "received_at": utc_iso(result.created_at),
                    "file_name": query.file_name,
                    "query_type": query.query_type,
                    "arrival_seq": result.arrival_seq,
                    "priority": result.priority,
                    "video_id": result.video_id,
                    "img_id": json.dumps(
                        result.frame_ids, ensure_ascii=False, separators=(",", ":")
                    )
                    if query.query_type == "trake"
                    else result.frame_ids[0],
                    "answer": result.answer or "",
                    "submitter": result.submitter,
                    "note": result.note or "",
                    "status": "deleted" if result.deleted_at is not None else "active",
                    "updated_at": utc_iso(result.updated_at),
                    "deleted_at": utc_iso(result.deleted_at),
                }
            )
        return output.getvalue().encode("utf-8-sig")


def safe_csv_name(file_name: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9._-]", "_", file_name).strip("._")
    if not sanitized:
        raise ApiError(422, "INVALID_EXPORT_FILE_NAME", "file_name không thể tạo tên CSV an toàn")
    return f"{sanitized}.csv"


@dataclass(frozen=True)
class BuiltExport:
    data: bytes
    sha256: str
    entries: list[str]


class SubmissionZipBuilder:
    def __init__(self) -> None:
        self.exporter = PreviewCsvExporter()

    def build_preview(self, queries: list[Query]) -> BuiltExport:
        stream = io.BytesIO()
        entries: list[str] = []
        seen_entries: set[str] = set()
        with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for query in sorted(queries, key=lambda item: item.display_order):
                entry = f"submission/{safe_csv_name(query.file_name)}"
                if entry.casefold() in seen_entries:
                    raise ApiError(
                        422,
                        "EXPORT_FILE_NAME_COLLISION",
                        "Nhiều file_name tạo ra cùng một tên CSV trong submission.zip",
                    )
                seen_entries.add(entry.casefold())
                info = zipfile.ZipInfo(entry, date_time=(2020, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o600 << 16
                archive.writestr(info, self.exporter.serialize(query))
                entries.append(entry)
        data = stream.getvalue()
        self.validate_preview(data, entries)
        return BuiltExport(data, hashlib.sha256(data).hexdigest(), entries)

    @staticmethod
    def validate_preview(data: bytes, expected_entries: list[str]) -> None:
        try:
            archive = zipfile.ZipFile(io.BytesIO(data))
        except zipfile.BadZipFile as exc:
            raise ApiError(
                500, "EXPORT_SELF_VALIDATION_FAILED", "ZIP vừa tạo không đọc được"
            ) from exc
        with archive:
            if archive.namelist() != expected_entries:
                raise ApiError(500, "EXPORT_ENTRY_MISMATCH", "Danh sách entry ZIP không khớp")
            for entry in archive.namelist():
                path = PurePosixPath(entry)
                if path.is_absolute() or ".." in path.parts or path.parts[0] != "submission":
                    raise ApiError(500, "EXPORT_UNSAFE_PATH", "ZIP có đường dẫn không an toàn")
                try:
                    payload = archive.read(entry)
                    if not payload.startswith(codecs.BOM_UTF8):
                        raise ApiError(
                            500,
                            "EXPORT_CSV_BOM_MISSING",
                            f"CSV thiếu UTF-8 BOM: {entry}",
                        )
                    text = payload.decode("utf-8-sig", errors="strict")
                    rows = list(csv.DictReader(io.StringIO(text)))
                except (UnicodeDecodeError, csv.Error) as exc:
                    raise ApiError(
                        500, "EXPORT_CSV_INVALID", f"CSV không đọc lại được: {entry}"
                    ) from exc
                if rows and list(rows[0].keys()) != PREVIEW_COLUMNS:
                    raise ApiError(500, "EXPORT_COLUMNS_INVALID", f"Cột preview sai: {entry}")


def save_export(root: str, export_id: str, data: bytes) -> str:
    directory = Path(root).resolve() / "exports"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{export_id}.zip"
    path.write_bytes(data)
    return str(path.relative_to(Path(root).resolve())).replace("\\", "/")
