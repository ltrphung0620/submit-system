from __future__ import annotations

import base64
import csv
import io
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect

from app.config import Settings, get_settings
from app.database import engine
from app.main import app
from tests.conftest import TEST_DATABASE_URL, synthetic_query_zip

pytestmark = pytest.mark.integration

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def test_clean_migration_contains_expected_tables(db_clean: None) -> None:
    inspector = inspect(engine)
    assert {
        "query_sets",
        "queries",
        "result_candidates",
        "image_attachments",
        "audit_logs",
        "export_snapshots",
    }.issubset(set(inspector.get_table_names()))
    indexes = inspector.get_indexes("queries")
    assert any(index["unique"] and index["column_names"] == ["file_name_key"] for index in indexes)
    result_columns = {
        column["name"]: column for column in inspector.get_columns("result_candidates")
    }
    assert result_columns["priority"]["nullable"] is False
    result_indexes = inspector.get_indexes("result_candidates")
    assert any(
        index["unique"]
        and index["column_names"] == ["query_id", "priority"]
        and index["name"] == "ux_active_query_priority"
        for index in result_indexes
    )


def test_import_queries_natural_order_unknown_and_transactional_rollback(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/v1/query-sets/import",
        files={
            "upload": (
                "synthetic.zip",
                synthetic_query_zip(
                    {
                        "query-10-kis.txt": "mười",
                        "query-2-qa.txt": "hai",
                        "query-3-other.txt": "unknown",
                    }
                ),
                "application/zip",
            )
        },
    )
    assert response.status_code == 201
    queries = client.get("/api/v1/queries").json()
    assert [query["file_name"] for query in queries] == [
        "query-2-qa",
        "query-3-other",
        "query-10-kis",
    ]
    assert queries[1]["query_type"] == "unknown"
    unknown_result = client.post(
        "/api/v1/results",
        json={
            "file_name": "query-3-other",
            "query_content": "Nội dung query không xác định",
            "img_id": 1,
            "video_id": "v",
            "submitter": "Định",
        },
    )
    assert unknown_result.status_code == 422

    bad = io.BytesIO()
    with zipfile.ZipFile(bad, "w") as archive:
        archive.writestr("one-kis.txt", b"valid")
        archive.writestr("two-qa.txt", b"\xff")
    failed = client.post(
        "/api/v1/query-sets/import",
        files={"upload": ("bad.zip", bad.getvalue(), "application/zip")},
    )
    assert failed.status_code == 422
    sets = client.get("/api/v1/query-sets").json()
    assert len(sets) == 1
    assert sets[0]["is_active"] is True


def test_kis_qa_trake_crud_order_image_and_unicode(imported_client: TestClient) -> None:
    client = imported_client
    kis = client.post(
        "/api/v1/results",
        json={
            "file_name": "query-p1-1-kis",
            "query_content": "Tìm khoảnh khắc KIS",
            "img_id": 24834,
            "video_id": "L21_V001",
            "submitter": "Định",
            "image_base64": base64.b64encode(PNG).decode(),
            "image_mime_type": "image/png",
        },
    )
    assert kis.status_code == 201, kis.text
    second = client.post(
        "/api/v1/results",
        json={
            "file_name": "query-p1-1-kis",
            "query_content": "Tìm khoảnh khắc KIS",
            "img_id": 24835,
            "video_id": "L21_V001",
            "submitter": "Member 2",
        },
    )
    qa = client.post(
        "/api/v1/results",
        json={
            "file_name": "query-p1-2-qa",
            "query_content": "Câu hỏi QA",
            "img_id": 24834,
            "video_id": "L21_V001",
            "answer": "Bình Định",
            "submitter": "Định",
        },
    )
    trake = client.post(
        "/api/v1/results",
        json={
            "file_name": "query-p1-3-trake",
            "query_content": "Theo dõi đối tượng TRAKE",
            "img_id": [24834, 25230, 25432],
            "video_id": "L21_V001",
            "submitter": "Định",
        },
    )
    assert [second.status_code, qa.status_code, trake.status_code] == [201, 201, 201]
    assert [kis.json()["priority"], qa.json()["priority"], trake.json()["priority"]] == [
        1,
        1,
        1,
    ]
    assert qa.json()["answer"] == "Bình Định"
    image_response = client.get(kis.json()["image_url"])
    assert image_response.content == PNG
    assert image_response.headers["content-type"] == "image/png"

    edited = client.patch(
        f"/api/v1/results/{kis.json()['id']}",
        json={"expected_version": 1, "img_id": 200, "note": "đã kiểm tra"},
    )
    assert edited.status_code == 200
    assert edited.json()["arrival_seq"] == 1
    conflict = client.patch(
        f"/api/v1/results/{kis.json()['id']}",
        json={"expected_version": 1, "img_id": 201},
    )
    assert conflict.status_code == 409
    swapped = client.post(
        "/api/v1/results/priority/swap",
        json={
            "first_result_id": kis.json()["id"],
            "second_result_id": second.json()["id"],
            "expected_first_version": 2,
            "expected_second_version": 1,
        },
    )
    assert swapped.status_code == 200, swapped.text
    swapped_by_id = {item["id"]: item for item in swapped.json()}
    assert swapped_by_id[kis.json()["id"]]["arrival_seq"] == 1
    assert swapped_by_id[kis.json()["id"]]["priority"] == 2
    assert swapped_by_id[second.json()["id"]]["arrival_seq"] == 2
    assert swapped_by_id[second.json()["id"]]["priority"] == 1
    reordered = client.post(
        "/api/v1/results/priority/reorder",
        json={
            "query_id": kis.json()["query_id"],
            "ordered_result_ids": [kis.json()["id"], second.json()["id"]],
            "expected_versions": {
                kis.json()["id"]: 3,
                second.json()["id"]: 2,
            },
        },
    )
    assert reordered.status_code == 200, reordered.text
    assert [(item["id"], item["priority"], item["arrival_seq"]) for item in reordered.json()] == [
        (kis.json()["id"], 1, 1),
        (second.json()["id"], 2, 2),
    ]
    deleted = client.delete(f"/api/v1/results/{kis.json()['id']}?expected_version=4")
    assert deleted.status_code == 204
    remaining = client.get(f"/api/v1/queries/{kis.json()['query_id']}/results").json()
    assert [(item["id"], item["arrival_seq"], item["priority"]) for item in remaining] == [
        (second.json()["id"], 2, 1)
    ]
    third = client.post(
        "/api/v1/results",
        json={
            "file_name": "query-p1-1-kis",
            "query_content": "Tìm khoảnh khắc KIS",
            "img_id": 24836,
            "video_id": "L21_V001",
            "submitter": "Member 3",
        },
    )
    assert third.status_code == 201, third.text
    assert (third.json()["arrival_seq"], third.json()["priority"]) == (3, 2)


def test_public_submission_api_auto_groups_without_query_import(client: TestClient) -> None:
    first = client.post(
        "/api/v1/submissions",
        json={
            "file_name": "synthetic-external-query-kis",
            "query_content": "Tìm khoảnh khắc người đi vào cửa hàng",
            "img_id": 10,
            "video_id": "L01_V001",
            "submitter": "Member 1",
        },
    )
    second = client.post(
        "/api/v1/submissions",
        json={
            "file_name": "synthetic-external-query-kis",
            "query_content": "Tìm khoảnh khắc người đi vào cửa hàng",
            "img_id": 11,
            "video_id": "L01_V001",
            "submitter": "Member 2",
        },
    )
    qa = client.post(
        "/api/v1/submissions",
        json={
            "file_name": "synthetic-external-question-qa",
            "query_content": "Địa danh trong hình thuộc tỉnh nào?",
            "img_id": 12,
            "video_id": "L01_V002",
            "answer": "Bình Định",
            "submitter": "Member 1",
        },
    )
    assert [first.status_code, second.status_code, qa.status_code] == [201, 201, 201]

    groups = client.get("/api/v1/queries").json()
    assert [group["file_name"] for group in groups] == [
        "synthetic-external-query-kis",
        "synthetic-external-question-qa",
    ]
    assert [item["arrival_seq"] for item in groups[0]["results"]] == [1, 2]
    assert groups[0]["content"] == "Tìm khoảnh khắc người đi vào cửa hàng"
    assert groups[1]["content"] == "Địa danh trong hình thuộc tỉnh nào?"
    assert groups[1]["results"][0]["answer"] == "Bình Định"

    deleted = client.delete(f"/api/v1/results/{first.json()['id']}?expected_version=1")
    assert deleted.status_code == 204
    history = client.get("/api/v1/exports/history.csv")
    assert history.status_code == 200
    assert history.content.startswith(b"\xef\xbb\xbf")
    rows = list(csv.DictReader(io.StringIO(history.content.decode("utf-8-sig"))))
    assert len(rows) == 3
    assert [row["file_name"] for row in rows[:2]] == [
        "synthetic-external-query-kis",
        "synthetic-external-query-kis",
    ]
    assert rows[0]["status"] == "deleted"
    assert history.headers["x-submission-format"] == "operational-history-not-official"


def test_validation_auth_permissions_and_error_contract(client: TestClient, tmp_path: Path) -> None:
    auth_settings = Settings(
        database_url=TEST_DATABASE_URL,
        storage_root=str(tmp_path),
        auth_mode="api_key",
        api_keys_json='{"secret-a":"Định","secret-b":"Member 2"}',
        permission_mode="owner_only",
    )
    app.dependency_overrides[get_settings] = lambda: auth_settings
    imported = client.post(
        "/api/v1/query-sets/import",
        headers={"X-API-Key": "secret-a"},
        files={"upload": ("synthetic.zip", synthetic_query_zip(), "application/zip")},
    )
    assert imported.status_code == 201
    missing = client.post(
        "/api/v1/results",
        json={
            "file_name": "query-p1-1-kis",
            "query_content": "Tìm khoảnh khắc KIS",
            "img_id": 1,
            "video_id": "v",
            "submitter": "Định",
        },
    )
    assert missing.status_code == 401
    assert set(missing.json()["error"]) >= {"code", "message", "field_errors", "request_id"}
    mismatch = client.post(
        "/api/v1/results",
        headers={"X-API-Key": "secret-a"},
        json={
            "file_name": "query-p1-1-kis",
            "query_content": "Tìm khoảnh khắc KIS",
            "img_id": 1,
            "video_id": "v",
            "submitter": "Member 2",
        },
    )
    assert mismatch.status_code == 403
    created = client.post(
        "/api/v1/results",
        headers={"X-API-Key": "secret-a"},
        json={
            "file_name": "query-p1-1-kis",
            "query_content": "Tìm khoảnh khắc KIS",
            "img_id": 1,
            "video_id": "v",
            "submitter": "Định",
        },
    )
    forbidden = client.delete(
        f"/api/v1/results/{created.json()['id']}?expected_version=1",
        headers={"X-API-Key": "secret-b"},
    )
    assert forbidden.status_code == 403


def test_preview_export_roundtrip_and_official_block(imported_client: TestClient) -> None:
    client = imported_client
    kis_response = client.post(
        "/api/v1/results",
        json={
            "file_name": "query-p1-1-kis",
            "query_content": "Tìm khoảnh khắc KIS",
            "img_id": 2,
            "video_id": "v",
            "submitter": "Định",
        },
    )
    assert kis_response.status_code == 201
    kis_csv_response = client.get(f"/api/v1/exports/queries/{kis_response.json()['query_id']}.csv")
    assert kis_csv_response.status_code == 200
    assert kis_csv_response.content.startswith(b"\xef\xbb\xbf")
    assert 'filename="query-p1-1-kis.csv"' in kis_csv_response.headers["content-disposition"]
    kis_rows = list(csv.DictReader(io.StringIO(kis_csv_response.content.decode("utf-8-sig"))))
    assert len(kis_rows) == 1
    assert kis_rows[0]["file_name"] == "query-p1-1-kis"
    assert kis_rows[0]["submitter"] == "Định"
    response = client.post(
        "/api/v1/results",
        json={
            "file_name": "query-p1-2-qa",
            "query_content": "Câu hỏi QA",
            "img_id": 1,
            "video_id": "v",
            "answer": "Bình Định, Việt Nam",
            "submitter": "Định",
        },
    )
    assert response.status_code == 201
    validation = client.get("/api/v1/exports/validate")
    assert validation.status_code == 200
    preview = client.post("/api/v1/exports/preview")
    assert preview.status_code == 201, preview.text
    archive_response = client.get(preview.json()["download_url"])
    assert archive_response.status_code == 200
    assert 'filename="submission.zip"' in archive_response.headers["content-disposition"]
    assert archive_response.headers["x-submission-format"] == "preview-unverified-not-official"
    with zipfile.ZipFile(io.BytesIO(archive_response.content)) as archive:
        assert archive.namelist() == [
            "submission/query-p1-1-kis.csv",
            "submission/query-p1-2-qa.csv",
        ]
        qa_data = archive.read("submission/query-p1-2-qa.csv")
        assert qa_data.startswith(b"\xef\xbb\xbf")
        qa_csv = qa_data.decode("utf-8-sig")
        assert "Bình Định, Việt Nam" in qa_csv
    official = client.post("/api/v1/exports/official")
    assert official.status_code == 409
    assert official.json()["error"]["code"] == "OFFICIAL_FORMAT_NOT_VERIFIED"
