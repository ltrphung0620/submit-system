from __future__ import annotations

import re
from typing import Any, Literal, cast

from app.errors import ApiError, FieldError

QueryType = Literal["kis", "qa", "trake", "unknown"]


def canonical_file_name(file_name: str) -> str:
    return file_name.casefold()


def strip_txt_extension(file_name: str) -> str:
    return file_name[:-4] if file_name.casefold().endswith(".txt") else file_name


def infer_query_type(file_name: str) -> QueryType:
    value = strip_txt_extension(file_name).casefold()
    if value.endswith("-trake"):
        return "trake"
    if value.endswith("-kis"):
        return "kis"
    if value.endswith("-qa"):
        return "qa"
    return "unknown"


def natural_sort_key(value: str) -> list[tuple[int, int | str]]:
    parts = re.split(r"(\d+)", value.casefold())
    return [(0, int(part)) if part.isdigit() else (1, part) for part in parts]


def _field(path: str, code: str, message: str) -> ApiError:
    return ApiError(422, "STRUCTURAL_VALIDATION_FAILED", message, [FieldError(path, code, message)])


def _strict_int(value: Any, path: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise _field(path, "INVALID_TYPE", f"{path} phải là số nguyên")
    if value < 0:
        raise _field(path, "OUT_OF_RANGE", f"{path} không được âm")
    return cast(int, value)


def _nonblank_string(value: Any, path: str) -> str:
    if not isinstance(value, str):
        raise _field(path, "INVALID_TYPE", f"{path} phải là chuỗi")
    if not value.strip():
        raise _field(path, "EMPTY_VALUE", f"{path} không được rỗng")
    return value


def validate_query_content(value: Any) -> str:
    return _nonblank_string(value, "query_content").strip()


def validate_result_payload(
    query_type: str,
    *,
    file_name: Any,
    img_id: Any,
    video_id: Any,
    submitter: Any,
    answer: Any,
) -> tuple[list[int], str | None]:
    name = _nonblank_string(file_name, "file_name")
    if name.casefold().endswith(".txt"):
        raise _field("file_name", "EXTENSION_NOT_ALLOWED", "file_name không được chứa .txt")
    _nonblank_string(video_id, "video_id")
    _nonblank_string(submitter, "submitter")

    if query_type == "kis":
        frame_ids = [_strict_int(img_id, "img_id")]
        if answer is not None:
            raise _field("answer", "FIELD_NOT_ALLOWED", "KIS không nhận answer")
        return frame_ids, None
    if query_type == "qa":
        frame_ids = [_strict_int(img_id, "img_id")]
        return frame_ids, _nonblank_string(answer, "answer")
    if query_type == "trake":
        if not isinstance(img_id, list):
            raise _field("img_id", "INVALID_TYPE", "TRAKE yêu cầu img_id là mảng")
        if not img_id:
            raise _field("img_id", "EMPTY_ARRAY", "TRAKE yêu cầu ít nhất một frame")
        frame_ids = [_strict_int(frame, f"img_id.{index}") for index, frame in enumerate(img_id)]
        if answer is not None:
            raise _field("answer", "FIELD_NOT_ALLOWED", "TRAKE không nhận answer")
        return frame_ids, None
    raise _field("file_name", "UNKNOWN_QUERY_TYPE", "Query chưa xác định loại KIS, QA hoặc TRAKE")
