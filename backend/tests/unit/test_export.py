from __future__ import annotations

import csv
import io
import zipfile
from datetime import UTC, datetime

import pytest

from app.errors import ApiError
from app.models import Query, ResultCandidate
from app.services.export import (
    HISTORY_COLUMNS,
    PREVIEW_COLUMNS_BY_TYPE,
    PreviewCsvExporter,
    QaCsvExporter,
    SubmissionHistoryCsvExporter,
    SubmissionZipBuilder,
    UnverifiedOfficialFormatProvider,
    safe_csv_name,
    save_export,
)


def build_query() -> Query:
    query = Query(
        id="q1",
        query_set_id="s1",
        file_name="query-p1-2-qa",
        file_name_key="query-p1-2-qa",
        query_type="qa",
        content="question",
        display_order=1,
        source_path="query-p1-2-qa.txt",
    )
    query.results = [
        ResultCandidate(
            id="r2",
            query_id="q1",
            arrival_seq=2,
            priority=2,
            video_id="L21_V001",
            frame_ids=[2],
            answer='dòng 1, "quoted"\ndòng 2',
            submitter="Định",
            version=1,
            structural_validation_status="valid",
            official_validation_status="unverified",
        ),
        ResultCandidate(
            id="r1",
            query_id="q1",
            arrival_seq=1,
            priority=1,
            video_id="L21_V001",
            frame_ids=[1],
            answer="Bình Định",
            submitter="Định",
            version=1,
            structural_validation_status="valid",
            official_validation_status="unverified",
        ),
    ]
    return query


def test_preview_qa_csv_has_no_header_quotes_unicode_and_orders() -> None:
    data = PreviewCsvExporter().serialize(build_query())
    assert data.startswith(b"\xef\xbb\xbf")
    assert b"\r\n" in data
    text = data.decode("utf-8-sig")
    rows = list(csv.reader(io.StringIO(text)))
    assert rows[0] != list(PREVIEW_COLUMNS_BY_TYPE["qa"])
    assert rows == [
        ["L21_V001", "1", "Bình Định"],
        ["L21_V001", "2", 'dòng 1, "quoted"\ndòng 2'],
    ]


def test_preview_csv_uses_mutable_priority_instead_of_arrival_sequence() -> None:
    query = build_query()
    query.results[0].priority = 1
    query.results[1].priority = 2

    rows = list(csv.reader(io.StringIO(PreviewCsvExporter().serialize(query).decode("utf-8-sig"))))

    assert [row[2] for row in rows] == [
        'dòng 1, "quoted"\ndòng 2',
        "Bình Định",
    ]


def test_preview_kis_and_trake_rows_have_type_specific_columns_without_headers() -> None:
    kis = build_query()
    kis.file_name = "query-p1-1-kis"
    kis.file_name_key = kis.file_name
    kis.query_type = "kis"
    for result in kis.results:
        result.answer = None
    kis_rows = list(
        csv.reader(io.StringIO(PreviewCsvExporter().serialize(kis).decode("utf-8-sig")))
    )
    assert kis_rows == [["L21_V001", "1"], ["L21_V001", "2"]]

    trake = build_query()
    trake.file_name = "query-p1-3-trake"
    trake.file_name_key = trake.file_name
    trake.query_type = "trake"
    trake.results[0].frame_ids = [20, 21, 22]
    trake.results[1].frame_ids = [10, 11]
    for result in trake.results:
        result.answer = None
    trake_rows = list(
        csv.reader(io.StringIO(PreviewCsvExporter().serialize(trake).decode("utf-8-sig")))
    )
    assert trake_rows == [
        ["L21_V001", "10", "11"],
        ["L21_V001", "20", "21", "22"],
    ]


def test_operational_history_csv_has_bom_and_includes_deleted_results() -> None:
    query = build_query()
    first, second = query.results
    first.created_at = datetime(2026, 7, 24, 1, 2, tzinfo=UTC)
    first.updated_at = first.created_at
    second.created_at = datetime(2026, 7, 24, 1, 1, tzinfo=UTC)
    second.updated_at = datetime(2026, 7, 24, 1, 3, tzinfo=UTC)
    second.deleted_at = datetime(2026, 7, 24, 1, 4, tzinfo=UTC)

    data = SubmissionHistoryCsvExporter().serialize(query.results)

    assert data.startswith(b"\xef\xbb\xbf")
    rows = list(csv.DictReader(io.StringIO(data.decode("utf-8-sig"))))
    assert list(rows[0]) == HISTORY_COLUMNS
    assert [row["arrival_seq"] for row in rows] == ["1", "2"]
    assert [row["priority"] for row in rows] == ["1", "2"]
    assert rows[0]["status"] == "deleted"
    assert rows[1]["status"] == "active"
    assert rows[0]["received_at"].endswith("Z")


def test_zip_entry_name_determinism_and_self_validation() -> None:
    first = SubmissionZipBuilder().build_preview([build_query()])
    second = SubmissionZipBuilder().build_preview([build_query()])
    assert first.data == second.data
    assert first.entries == ["submission/query-p1-2-qa.csv"]
    with zipfile.ZipFile(io.BytesIO(first.data)) as archive:
        assert archive.namelist() == first.entries
        csv_data = archive.read(first.entries[0])
        assert csv_data.startswith(b"\xef\xbb\xbf")
        rows = list(csv.reader(io.StringIO(csv_data.decode("utf-8-sig"))))
        assert rows[0] == ["L21_V001", "1", "Bình Định"]


def test_safe_names_and_official_fail_closed() -> None:
    assert safe_csv_name("query 1/qa") == "query_1_qa.csv"
    with pytest.raises(ApiError) as invalid:
        safe_csv_name("...")
    assert invalid.value.code == "INVALID_EXPORT_FILE_NAME"
    provider = UnverifiedOfficialFormatProvider()
    assert provider.verified is False
    with pytest.raises(ApiError) as blocked:
        provider.require_verified()
    assert blocked.value.status_code == 409
    assert blocked.value.code == "OFFICIAL_FORMAT_NOT_VERIFIED"
    with pytest.raises(ApiError) as adapter_blocked:
        QaCsvExporter(provider).serialize(build_query())
    assert adapter_blocked.value.code == "OFFICIAL_FORMAT_NOT_VERIFIED"


def test_zip_rejects_file_names_that_collapse_to_the_same_csv_name() -> None:
    first = build_query()
    second = build_query()
    second.id = "q2"
    second.file_name = "query p1 2 qa"
    second.file_name_key = "query p1 2 qa"
    second.display_order = 2
    second.results = []
    first.file_name = "query/p1/2/qa"
    first.file_name_key = "query/p1/2/qa"

    with pytest.raises(ApiError) as collision:
        SubmissionZipBuilder().build_preview([first, second])

    assert collision.value.code == "EXPORT_FILE_NAME_COLLISION"


def zip_with(entry: str, data: bytes) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr(entry, data)
    return output.getvalue()


def test_export_self_validation_rejects_corruption_and_unsafe_layout() -> None:
    with pytest.raises(ApiError, match="không đọc được"):
        SubmissionZipBuilder.validate_preview(b"not-a-zip", [])
    normal = zip_with("submission/a.csv", b"file_name\r\nquery\r\n")
    with pytest.raises(ApiError, match="entry"):
        SubmissionZipBuilder.validate_preview(normal, ["submission/b.csv"])
    unsafe = zip_with("../escape.csv", b"file_name\r\nquery\r\n")
    with pytest.raises(ApiError, match="không an toàn"):
        SubmissionZipBuilder.validate_preview(unsafe, ["../escape.csv"])
    missing_bom = zip_with(
        "submission/a.csv",
        b"L21_V001,1\r\n",
    )
    with pytest.raises(ApiError, match="thiếu UTF-8 BOM"):
        SubmissionZipBuilder.validate_preview(missing_bom, ["submission/a.csv"])
    invalid_utf8 = zip_with("submission/a.csv", b"\xef\xbb\xbf\xff")
    with pytest.raises(ApiError, match="không đọc lại"):
        SubmissionZipBuilder.validate_preview(invalid_utf8, ["submission/a.csv"])
    header = zip_with(
        "submission/a.csv",
        b"\xef\xbb\xbfvideo_id,img_id\r\nL21_V001,1\r\n",
    )
    with pytest.raises(ApiError, match="không được có header"):
        SubmissionZipBuilder.validate_preview(
            header,
            ["submission/a.csv"],
            {"submission/a.csv": "kis"},
        )
    wrong_columns = zip_with(
        "submission/a.csv",
        b"\xef\xbb\xbfL21_V001,1,extra\r\n",
    )
    with pytest.raises(ApiError, match="Cột preview sai"):
        SubmissionZipBuilder.validate_preview(
            wrong_columns,
            ["submission/a.csv"],
            {"submission/a.csv": "kis"},
        )
    invalid_trake = zip_with(
        "submission/a.csv",
        b"\xef\xbb\xbfL21_V001,not-a-frame\r\n",
    )
    with pytest.raises(ApiError, match="Frame TRAKE sai"):
        SubmissionZipBuilder.validate_preview(
            invalid_trake,
            ["submission/a.csv"],
            {"submission/a.csv": "trake"},
        )


def test_save_export_uses_opaque_id_under_storage_root(tmp_path: object) -> None:
    relative = save_export(str(tmp_path), "safe-id", b"zip")
    assert relative == "exports/safe-id.zip"
    assert (tmp_path / "exports" / "safe-id.zip").read_bytes() == b"zip"
