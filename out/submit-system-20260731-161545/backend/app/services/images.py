from __future__ import annotations

import base64
import binascii
import hashlib
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from app.errors import ApiError, FieldError

DATA_URL = re.compile(r"^data:([^;,]+);base64,(.*)$", re.DOTALL)
EXTENSIONS = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}


@dataclass(frozen=True)
class DecodedImage:
    data: bytes
    supplied_mime: str | None
    detected_mime: str
    sha256: str


def detect_image_mime(data: bytes) -> str | None:
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def decode_image(value: str, supplied_mime: str | None, max_bytes: int) -> DecodedImage:
    encoded = value
    match = DATA_URL.match(value)
    if match:
        data_url_mime, encoded = match.groups()
        if supplied_mime and supplied_mime != data_url_mime:
            raise ApiError(
                422,
                "IMAGE_MIME_MISMATCH",
                "MIME trong data URL không khớp image_mime_type",
                [FieldError("image_mime_type", "MIME_MISMATCH", "MIME không khớp")],
            )
        supplied_mime = data_url_mime
    try:
        data = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ApiError(
            422,
            "INVALID_BASE64",
            "image_base64 không hợp lệ",
            [FieldError("image_base64", "INVALID_BASE64", "Base64 không hợp lệ")],
        ) from exc
    if len(data) > max_bytes:
        raise ApiError(413, "IMAGE_TOO_LARGE", "Ảnh sau giải mã vượt giới hạn")
    detected = detect_image_mime(data)
    if detected not in EXTENSIONS:
        raise ApiError(422, "UNSUPPORTED_IMAGE_TYPE", "Chỉ nhận JPEG, PNG hoặc WebP")
    if supplied_mime and supplied_mime != detected:
        raise ApiError(422, "IMAGE_MIME_MISMATCH", "MIME khai báo không khớp nội dung ảnh")
    return DecodedImage(data, supplied_mime, detected, hashlib.sha256(data).hexdigest())


class ImageStorage(Protocol):
    def save(self, image: DecodedImage) -> str: ...

    def read(self, storage_key: str) -> bytes: ...

    def delete(self, storage_key: str) -> None: ...


class LocalImageStorage:
    def __init__(self, root: str) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, storage_key: str) -> Path:
        if not re.fullmatch(r"[0-9a-f]{2}/[0-9a-f-]{36}\.(jpg|png|webp)", storage_key):
            raise ValueError("Invalid storage key")
        path = (self.root / storage_key).resolve()
        if self.root not in path.parents:
            raise ValueError("Storage path escaped root")
        return path

    def save(self, image: DecodedImage) -> str:
        identifier = str(uuid.uuid4())
        key = f"{identifier[:2]}/{identifier}{EXTENSIONS[image.detected_mime]}"
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(image.data)
        return key

    def read(self, storage_key: str) -> bytes:
        return self._path(storage_key).read_bytes()

    def delete(self, storage_key: str) -> None:
        self._path(storage_key).unlink(missing_ok=True)
