from __future__ import annotations

import io
import zipfile

import pytest

from app.config import Settings
from app.errors import ApiError
from app.services.query_import import parse_query_zip


def make_zip(files: dict[str, bytes], compression: int = zipfile.ZIP_DEFLATED) -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    return stream.getvalue()


def test_recursive_utf8_bom_import_and_natural_order() -> None:
    data = make_zip(
        {
            "nested/query-10-kis.txt": "mười".encode(),
            "query-2-QA.TXT": b"\xef\xbb\xbfcau hoi",
            "ignore.json": b"{}",
        }
    )
    parsed = parse_query_zip(data, Settings())
    assert [item.file_name for item in parsed] == ["query-2-QA", "query-10-kis"]
    assert parsed[0].query_type == "qa"


@pytest.mark.parametrize(
    ("files", "code"),
    [
        ({"../evil-kis.txt": b"x"}, "ZIP_PATH_TRAVERSAL"),
        ({"a/query-kis.txt": b"1", "b/QUERY-KIS.TXT": b"2"}, "DUPLICATE_FILE_NAME"),
        ({"query-kis.txt": b"\xff"}, "QUERY_ENCODING_INVALID"),
        ({"readme.md": b"x"}, "NO_QUERY_FILES"),
    ],
)
def test_import_rejections(files: dict[str, bytes], code: str) -> None:
    with pytest.raises(ApiError) as raised:
        parse_query_zip(make_zip(files), Settings())
    assert raised.value.code == code


def test_malformed_and_limits() -> None:
    with pytest.raises(ApiError) as malformed:
        parse_query_zip(b"not zip", Settings())
    assert malformed.value.code == "MALFORMED_ZIP"
    with pytest.raises(ApiError) as too_large:
        parse_query_zip(make_zip({"query-kis.txt": b"12345"}), Settings(max_zip_extracted_bytes=4))
    assert too_large.value.status_code == 413
