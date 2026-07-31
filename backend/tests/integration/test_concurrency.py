from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.concurrency


def test_fifty_concurrent_results_have_unique_stable_arrival_sequence(
    imported_client: TestClient,
) -> None:
    client = imported_client

    def create(frame: int) -> tuple[int, dict[str, object]]:
        response = client.post(
            "/api/v1/results",
            json={
                "file_name": "query-p1-1-kis",
                "query_content": "Tìm khoảnh khắc KIS",
                "img_id": frame,
                "video_id": "L21_V001",
                "submitter": "Định",
            },
        )
        return response.status_code, response.json()

    with ThreadPoolExecutor(max_workers=20) as pool:
        responses = list(pool.map(create, range(1000, 1050)))
    assert [status for status, _ in responses] == [201] * 50
    ids = {str(body["id"]) for _, body in responses}
    sequences = {int(body["arrival_seq"]) for _, body in responses}
    priorities = {int(body["priority"]) for _, body in responses}
    assert len(ids) == 50
    assert sequences == set(range(1, 51))
    assert priorities == set(range(1, 51))
    query_id = str(responses[0][1]["query_id"])
    stored = client.get(f"/api/v1/queries/{query_id}/results").json()
    assert len(stored) == 50
    assert [item["arrival_seq"] for item in stored] == list(range(1, 51))
    assert [item["priority"] for item in stored] == list(range(1, 51))


def test_concurrent_first_submissions_create_one_file_name_group(
    client: TestClient,
) -> None:
    def create(frame: int) -> tuple[int, dict[str, object]]:
        response = client.post(
            "/api/v1/submissions",
            json={
                "file_name": "synthetic-direct-feed-kis",
                "query_content": "Tìm khoảnh khắc người đi vào cửa hàng",
                "img_id": frame,
                "video_id": "L21_V001",
                "submitter": "Định",
            },
        )
        return response.status_code, response.json()

    with ThreadPoolExecutor(max_workers=12) as pool:
        responses = list(pool.map(create, range(2000, 2020)))

    assert [status for status, _ in responses] == [201] * 20
    groups = client.get("/api/v1/queries").json()
    assert len(groups) == 1
    assert groups[0]["file_name"] == "synthetic-direct-feed-kis"
    assert groups[0]["content"] == "Tìm khoảnh khắc người đi vào cửa hàng"
    assert [item["arrival_seq"] for item in groups[0]["results"]] == list(range(1, 21))
    assert [item["priority"] for item in groups[0]["results"]] == list(range(1, 21))
