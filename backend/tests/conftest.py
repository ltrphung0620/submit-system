from __future__ import annotations

import io
import os
import zipfile
from collections.abc import Generator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "mssql+pyodbc://@ltrphung/submission"
    "?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes"
    "&TrustServerCertificate=yes",
)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["APP_ENV"] = "test"

from app.config import Settings, get_settings  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402


def synthetic_query_zip(files: dict[str, str] | None = None) -> bytes:
    content = files or {
        "queries/query-p1-1-kis.txt": "Tìm xe buýt màu xanh",
        "queries/query-p1-2-qa.txt": "Địa danh thuộc tỉnh nào?",
        "queries/query-p1-3-trake.txt": "Theo dõi chuỗi sự kiện",
    }
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, value in content.items():
            archive.writestr(name, value.encode("utf-8"))
    return stream.getvalue()


_migrated = False


def migrate_once() -> None:
    global _migrated
    if _migrated:
        return
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    config.set_main_option(
        "script_location", str(Path(__file__).resolve().parents[1] / "migrations")
    )
    config.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    command.upgrade(config, "head")
    _migrated = True


@pytest.fixture
def db_clean() -> Generator[None, None, None]:
    migrate_once()
    with SessionLocal() as session:
        for table in (
            "export_snapshots",
            "audit_logs",
            "image_attachments",
            "result_candidates",
            "queries",
            "query_sets",
        ):
            session.execute(text(f"DELETE FROM {table}"))
        session.commit()
    yield


@pytest.fixture
def client(db_clean: None, tmp_path: Path) -> Generator[TestClient, None, None]:
    settings = Settings(
        database_url=TEST_DATABASE_URL, storage_root=str(tmp_path), auth_mode="disabled"
    )
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def imported_client(client: TestClient) -> TestClient:
    response = client.post(
        "/api/v1/query-sets/import",
        files={"upload": ("synthetic-query-pack.zip", synthetic_query_zip(), "application/zip")},
    )
    assert response.status_code == 201, response.text
    return client
