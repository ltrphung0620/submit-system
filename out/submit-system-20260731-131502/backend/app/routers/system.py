from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import get_db
from app.errors import ApiError
from app.models import ImageAttachment
from app.services.images import LocalImageStorage

router = APIRouter(tags=["system"])


@router.get("/health/live")
def live() -> dict[str, str]:
    return {"status": "live"}


@router.get("/health/ready")
def ready(db: Session = Depends(get_db)) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        raise ApiError(503, "DATABASE_NOT_READY", "Database chưa sẵn sàng") from exc
    return {"status": "ready", "database": "ok"}


@router.get("/images/{image_id}")
def get_image(
    image_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Response:
    image = db.scalar(select(ImageAttachment).where(ImageAttachment.id == image_id))
    if image is None:
        raise ApiError(404, "IMAGE_NOT_FOUND", "Không tìm thấy ảnh")
    try:
        data = LocalImageStorage(settings.storage_root).read(image.storage_key)
    except FileNotFoundError as exc:
        raise ApiError(404, "IMAGE_FILE_NOT_FOUND", "File ảnh không còn tồn tại") from exc
    return Response(
        data,
        media_type=image.detected_mime_type,
        headers={
            "Content-Security-Policy": "default-src 'none'",
            "X-Content-Type-Options": "nosniff",
        },
    )
