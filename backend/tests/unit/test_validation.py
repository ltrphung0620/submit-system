from __future__ import annotations

import pytest

from app.errors import ApiError
from app.services.validation import (
    infer_query_type,
    natural_sort_key,
    strip_txt_extension,
    validate_query_content,
    validate_result_payload,
)


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("query-1-KIS.txt", "kis"),
        ("query-2-qa", "qa"),
        ("query-3-TrAkE", "trake"),
        ("query-4", "unknown"),
    ],
)
def test_infer_query_type(name: str, expected: str) -> None:
    assert infer_query_type(name) == expected


def test_strip_txt_extension_only_removes_suffix() -> None:
    assert strip_txt_extension("a.TXT") == "a"


def test_query_content_is_trimmed_and_cannot_be_blank() -> None:
    assert validate_query_content("  Nội dung query  ") == "Nội dung query"
    with pytest.raises(ApiError) as error:
        validate_query_content("   ")
    assert error.value.code == "STRUCTURAL_VALIDATION_FAILED"
    assert error.value.field_errors[0].path == "query_content"
    assert strip_txt_extension("a.txt.backup") == "a.txt.backup"


def test_natural_sort() -> None:
    values = ["query-10-kis", "query-2-kis", "query-1-kis"]
    assert sorted(values, key=natural_sort_key) == ["query-1-kis", "query-2-kis", "query-10-kis"]


def test_kis_structural_validation() -> None:
    assert validate_result_payload(
        "kis", file_name="q-kis", img_id=2, video_id="v", submitter="Định", answer=None
    ) == ([2], None)
    with pytest.raises(ApiError, match="KIS không nhận answer"):
        validate_result_payload(
            "kis", file_name="q-kis", img_id=2, video_id="v", submitter="Định", answer="x"
        )


def test_qa_preserves_vietnamese_answer() -> None:
    frames, answer = validate_result_payload(
        "qa",
        file_name="q-qa",
        img_id=24834,
        video_id="L21_V001",
        submitter="Định",
        answer="  Bình Định  ",
    )
    assert frames == [24834]
    assert answer == "  Bình Định  "


def test_trake_requires_nonempty_integer_array() -> None:
    assert validate_result_payload(
        "trake",
        file_name="q-trake",
        img_id=[1, 2, 3],
        video_id="v",
        submitter="Định",
        answer=None,
    )[0] == [1, 2, 3]
    for invalid in (1, [], [1, "2"], [True]):
        with pytest.raises(ApiError):
            validate_result_payload(
                "trake",
                file_name="q-trake",
                img_id=invalid,
                video_id="v",
                submitter="Định",
                answer=None,
            )


@pytest.mark.parametrize("invalid", [True, False, "123", 2.5, -1])
def test_integer_is_strict_and_nonnegative(invalid: object) -> None:
    with pytest.raises(ApiError):
        validate_result_payload(
            "kis",
            file_name="q-kis",
            img_id=invalid,
            video_id="v",
            submitter="Định",
            answer=None,
        )


def test_common_fields_and_unknown_type() -> None:
    cases = [
        dict(
            query_type="kis",
            file_name="q-kis.txt",
            img_id=1,
            video_id="v",
            submitter="a",
            answer=None,
        ),
        dict(
            query_type="kis", file_name="q-kis", img_id=1, video_id=" ", submitter="a", answer=None
        ),
        dict(
            query_type="unknown", file_name="q", img_id=1, video_id="v", submitter="a", answer=None
        ),
    ]
    for case in cases:
        with pytest.raises(ApiError):
            validate_result_payload(**case)
