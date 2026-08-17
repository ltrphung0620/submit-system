from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Literal, Self

from pydantic import SecretStr, field_validator, model_validator
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
    salamanders_key: SecretStr = SecretStr("")
    ui_shared_key: SecretStr = SecretStr("")
    permission_mode: Literal["all_members", "owner_only"] = "all_members"
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

    @model_validator(mode="after")
    def validate_api_keys(self) -> Self:
        if self.auth_mode != "api_key":
            return self
        salamanders_key = self.salamanders_key.get_secret_value()
        ui_shared_key = self.ui_shared_key.get_secret_value()
        if not salamanders_key or not ui_shared_key:
            raise ValueError(
                "SALAMANDERS_KEY and UI_SHARED_KEY are required when AUTH_MODE=api_key"
            )
        if salamanders_key == ui_shared_key:
            raise ValueError("SALAMANDERS_KEY and UI_SHARED_KEY must be different")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
