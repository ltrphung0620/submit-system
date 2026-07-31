from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.realtime


def test_created_updated_deleted_events_use_versioned_schema(imported_client: TestClient) -> None:
    client = imported_client
    with client.websocket_connect("/api/v1/ws") as websocket:
        created = client.post(
            "/api/v1/results",
            json={
                "file_name": "query-p1-1-kis",
                "query_content": "Tìm khoảnh khắc KIS",
                "img_id": 1,
                "video_id": "v",
                "submitter": "Định",
            },
        )
        event = websocket.receive_json()
        assert event["schema_version"] == 1
        assert event["event"] == "created"
        assert event["data"]["id"] == created.json()["id"]
        updated = client.patch(
            f"/api/v1/results/{created.json()['id']}",
            json={"expected_version": 1, "img_id": 2},
        )
        event = websocket.receive_json()
        assert event["event"] == "updated"
        assert event["data"]["version"] == 2
        client.delete(f"/api/v1/results/{updated.json()['id']}?expected_version=2")
        event = websocket.receive_json()
        assert event["event"] == "deleted"
        assert event["data"]["id"] == updated.json()["id"]
