from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Response
from fastapi.responses import FileResponse
from sqlalchemy import select, true
from sqlalchemy.orm import Session, joinedload

from app.config import Settings, get_settings
from app.database import get_db
from app.errors import ApiError
from app.models import ExportSnapshot, Query, QuerySet, ResultCandidate, new_id
from app.services.export import (
    ExportSelectionPolicy,
    PreviewCsvExporter,
    SubmissionHistoryCsvExporter,
    SubmissionZipBuilder,
    UnverifiedOfficialFormatProvider,
    safe_csv_name,
    save_export,
)

router = APIRouter(prefix="/exports", tags=["exports"])
official_provider = UnverifiedOfficialFormatProvider()


def active_queries(db: Session) -> tuple[QuerySet, list[Query]]:
    query_set = db.scalar(select(QuerySet).where(QuerySet.is_active == true()))
    if query_set is None:
        raise ApiError(409, "NO_ACTIVE_QUERY_SET", "Chưa có Query Set active")
    queries = (
        db.scalars(
            select(Query)
            .where(Query.query_set_id == query_set.id)
            .options(joinedload(Query.results))
            .order_by(Query.display_order)
        )
        .unique()
        .all()
    )
    return query_set, list(queries)


def validation_report(queries: list[Query]) -> dict[str, object]:
    errors: list[dict[str, object]] = []
    warnings: list[dict[str, object]] = []
    for query in queries:
        if query.query_type == "unknown":
            errors.append(
                {
                    "code": "UNKNOWN_QUERY_TYPE",
                    "query_id": query.id,
                    "file_name": query.file_name,
                    "result_id": None,
                    "message": "Không thể xác định KIS, QA hoặc TRAKE",
                    "remediation": "Đổi tên query với hậu tố được xác nhận và import lại",
                }
            )
        active = [result for result in query.results if result.deleted_at is None]
        if not active:
            warnings.append(
                {
                    "code": "QUERY_HAS_NO_RESULTS",
                    "query_id": query.id,
                    "file_name": query.file_name,
                    "result_id": None,
                    "message": "Query chưa có candidate",
                    "remediation": "Thêm candidate nếu query cần được xuất",
                }
            )
        for result in active:
            if result.structural_validation_status != "valid":
                errors.append(
                    {
                        "code": "RESULT_STRUCTURALLY_INVALID",
                        "query_id": query.id,
                        "file_name": query.file_name,
                        "result_id": result.id,
                        "message": "Candidate không hợp lệ về cấu trúc",
                        "remediation": "Sửa candidate trước khi export",
                    }
                )
    return {
        "mode": "preview",
        "format_verification_status": "unverified",
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "official_blocker": "OFFICIAL_FORMAT_NOT_VERIFIED",
    }


@router.get("/status")
def export_status() -> dict[str, object]:
    return {
        "preview_enabled": True,
        "preview_label": "UNVERIFIED",
        "official_enabled": official_provider.verified,
        "official_status": "OFFICIAL_FORMAT_NOT_VERIFIED",
        "blockers": [
            "organizer verification of preview CSV rows",
            "encoding/BOM and filenames",
            "candidate selection policy",
            "accepted official fixture",
        ],
    }


@router.get(
    "/history.csv",
    response_class=Response,
    summary="Tải toàn bộ lịch sử submission dưới dạng CSV nội bộ",
)
def download_submission_history(db: Session = Depends(get_db)) -> Response:
    results = (
        db.scalars(
            select(ResultCandidate)
            .options(joinedload(ResultCandidate.query))
            .order_by(ResultCandidate.created_at, ResultCandidate.id)
        )
        .unique()
        .all()
    )
    data = SubmissionHistoryCsvExporter().serialize(list(results))
    return Response(
        content=data,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="submission-history.csv"',
            "X-Submission-Format": "operational-history-not-official",
        },
    )


@router.get("/validate")
def validate_export(db: Session = Depends(get_db)) -> dict[str, object]:
    _, queries = active_queries(db)
    return validation_report(queries)


@router.get(
    "/queries/{query_id}.csv",
    response_class=Response,
    summary="Tải CSV UTF-8 của một nhóm file_name",
)
def download_query_csv(query_id: str, db: Session = Depends(get_db)) -> Response:
    query = (
        db.scalars(
            select(Query)
            .join(QuerySet, Query.query_set_id == QuerySet.id)
            .where(Query.id == query_id, QuerySet.is_active == true())
            .options(joinedload(Query.results))
        )
        .unique()
        .first()
    )
    if query is None:
        raise ApiError(404, "QUERY_NOT_FOUND", "Không tìm thấy nhóm submission")
    report = validation_report([query])
    if not report["valid"]:
        raise ApiError(
            422,
            "EXPORT_VALIDATION_FAILED",
            "CSV của nhóm có lỗi cấu trúc",
            details=report,
        )
    if not ExportSelectionPolicy.select(query):
        raise ApiError(409, "NO_SUBMISSIONS_TO_EXPORT", "Nhóm chưa có submission hợp lệ")
    filename = safe_csv_name(query.file_name)
    return Response(
        content=PreviewCsvExporter().serialize(query),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Submission-Format": "preview-unverified-not-official",
        },
    )


@router.post("/preview", status_code=201)
def create_preview_export(
    db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
) -> dict[str, object]:
    query_set, queries = active_queries(db)
    report = validation_report(queries)
    if not report["valid"]:
        raise ApiError(
            422, "EXPORT_VALIDATION_FAILED", "Preview export có lỗi cấu trúc", details=report
        )
    exportable_queries = [query for query in queries if ExportSelectionPolicy.select(query)]
    if not exportable_queries:
        raise ApiError(
            409,
            "NO_SUBMISSIONS_TO_EXPORT",
            "Chưa có submission hợp lệ để tạo submission.zip",
        )
    built = SubmissionZipBuilder().build_preview(exportable_queries)
    export_id = new_id()
    archive_path = save_export(settings.storage_root, export_id, built.data)
    snapshot = ExportSnapshot(
        id=export_id,
        query_set_id=query_set.id,
        status="ready",
        format_verification_status="unverified",
        archive_path=archive_path,
        validation_report=report,
        source_data_version=built.sha256,
    )
    db.add(snapshot)
    db.commit()
    return {
        "id": export_id,
        "mode": "preview",
        "label": "UNVERIFIED",
        "format_verification_status": "unverified",
        "entries": built.entries,
        "sha256": built.sha256,
        "download_url": f"/api/v1/exports/{export_id}/download",
    }


@router.post("/official")
def create_official_export() -> None:
    official_provider.require_verified()


@router.get("/{export_id}/download")
def download_export(
    export_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> FileResponse:
    snapshot = db.get(ExportSnapshot, export_id)
    if snapshot is None or snapshot.status != "ready":
        raise ApiError(404, "EXPORT_NOT_FOUND", "Không tìm thấy export")
    root = Path(settings.storage_root).resolve()
    path = (root / snapshot.archive_path).resolve()
    if root not in path.parents or not path.is_file():
        raise ApiError(404, "EXPORT_FILE_NOT_FOUND", "File export không còn tồn tại")
    return FileResponse(
        path,
        media_type="application/zip",
        filename="submission.zip",
        headers={"X-Submission-Format": "preview-unverified-not-official"},
    )
