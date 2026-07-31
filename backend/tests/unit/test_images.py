from __future__ import annotations

import base64

import pytest

from app.errors import ApiError
from app.services.images import LocalImageStorage, decode_image, detect_image_mime

PNG = b"\x89PNG\r\n\x1a\n" + b"synthetic"


def test_raw_base64_data_url_and_mime_detection() -> None:
    raw = base64.b64encode(PNG).decode()
    decoded = decode_image(raw, "image/png", 100)
    assert decoded.data == PNG
    assert decoded.detected_mime == "image/png"
    assert decode_image(f"data:image/png;base64,{raw}", None, 100).data == PNG
    assert detect_image_mime(b"\xff\xd8\xffx") == "image/jpeg"
    assert detect_image_mime(b"RIFFxxxxWEBP") == "image/webp"


@pytest.mark.parametrize("value", ["***", "data:image/png;base64,%%%"])
def test_invalid_base64(value: str) -> None:
    with pytest.raises(ApiError) as raised:
        decode_image(value, None, 100)
    assert raised.value.code == "INVALID_BASE64"


def test_size_and_mime_limits() -> None:
    raw = base64.b64encode(PNG).decode()
    with pytest.raises(ApiError, match="vượt giới hạn"):
        decode_image(raw, None, 2)
    with pytest.raises(ApiError, match="MIME"):
        decode_image(raw, "image/jpeg", 100)
    with pytest.raises(ApiError, match="JPEG"):
        decode_image(base64.b64encode(b"hello").decode(), None, 100)


def test_local_storage_round_trip(tmp_path: object) -> None:
    storage = LocalImageStorage(str(tmp_path))
    image = decode_image(base64.b64encode(PNG).decode(), None, 100)
    key = storage.save(image)
    assert storage.read(key) == PNG
    storage.delete(key)
    with pytest.raises(FileNotFoundError):
        storage.read(key)
    with pytest.raises(ValueError):
        storage.read("../escape.png")
