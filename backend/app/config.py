from __future__ import annotations

import json
from functools import lru_cache
from typing import Annotated, Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    app_env: Literal["development", "test", "production"] = "development"
    database_url: str = (
        "mssql+pyodbc://@ltrphung/submission"
        "?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes"
        "&TrustServerCertificate=yes"
    )
    storage_root: str = "./storage"
    cors_origins: Annotated[list[str], NoDecode] = [
        "http://localhost:5173",
        "http://localhost:8080",
    ]
    auth_mode: Literal["disabled", "api_key"] = "disabled"
    api_keys_json: str = "{}"
    permission_mode: Literal["all_members", "owner_only"] = "owner_only"
    database_pool_size: int = 20
    database_max_overflow: int = 10
    database_pool_timeout_seconds: int = 30
    max_request_bytes: int = 12 * 1024 * 1024
    max_zip_bytes: int = 5 * 1024 * 1024
    max_zip_entries: int = 500
    max_zip_extracted_bytes: int = 20 * 1024 * 1024
    max_image_bytes: int = 5 * 1024 * 1024
    result_rate_limit_per_minute: int = 120

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def api_keys(self) -> dict[str, str]:
        value = json.loads(self.api_keys_json)
        if not isinstance(value, dict) or not all(
            isinstance(key, str) and isinstance(owner, str) for key, owner in value.items()
        ):
            raise ValueError("API_KEYS_JSON must be a JSON object of API key to submitter")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
