from __future__ import annotations

import io
import posixpath
import zipfile
from dataclasses import dataclass
from pathlib import PurePosixPath

from app.config import Settings
from app.errors import ApiError, FieldError
from app.services.validation import canonical_file_name, infer_query_type, natural_sort_key


@dataclass(frozen=True)
class ImportedQuery:
    file_name: str
    file_name_key: str
    query_type: str
    content: str
    source_path: str


def _safe_archive_name(name: str) -> str:
    normalized = name.replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute() or ".." in path.parts or posixpath.normpath(normalized).startswith("../"):
        raise ApiError(422, "ZIP_PATH_TRAVERSAL", f"Đường dẫn ZIP không an toàn: {name}")
    return normalized


def parse_query_zip(data: bytes, settings: Settings) -> list[ImportedQuery]:
    if len(data) > settings.max_zip_bytes:
        raise ApiError(413, "ZIP_TOO_LARGE", "ZIP vượt giới hạn upload")
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise ApiError(422, "MALFORMED_ZIP", "File upload không phải ZIP hợp lệ") from exc
    with archive:
        infos = archive.infolist()
        if len(infos) > settings.max_zip_entries:
            raise ApiError(413, "ZIP_TOO_MANY_ENTRIES", "ZIP có quá nhiều entry")
        total = 0
        imported: list[ImportedQuery] = []
        seen: set[str] = set()
        for info in infos:
            safe_name = _safe_archive_name(info.filename)
            if info.is_dir():
                continue
            total += info.file_size
            if total > settings.max_zip_extracted_bytes:
                raise ApiError(413, "ZIP_EXTRACTED_TOO_LARGE", "Dữ liệu giải nén vượt giới hạn")
            if info.compress_size and info.file_size / info.compress_size > 200:
                raise ApiError(413, "ZIP_SUSPICIOUS_RATIO", "Entry ZIP có tỷ lệ nén bất thường")
            if not safe_name.casefold().endswith(".txt"):
                continue
            base_name = PurePosixPath(safe_name).name[:-4]
            key = canonical_file_name(base_name)
            if key in seen:
                raise ApiError(
                    409,
                    "DUPLICATE_FILE_NAME",
                    f"Hai query tạo cùng file_name: {base_name}",
                    [FieldError("file_name", "DUPLICATE", base_name)],
                )
            seen.add(key)
            try:
                content = archive.read(info).decode("utf-8-sig", errors="strict")
            except UnicodeDecodeError as exc:
                raise ApiError(
                    422, "QUERY_ENCODING_INVALID", f"{safe_name} không phải UTF-8"
                ) from exc
            imported.append(
                ImportedQuery(base_name, key, infer_query_type(base_name), content, safe_name)
            )
        if not imported:
            raise ApiError(422, "NO_QUERY_FILES", "ZIP không chứa file query .txt hợp lệ")
        return sorted(imported, key=lambda query: natural_sort_key(query.file_name))
