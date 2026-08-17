from __future__ import annotations

import hmac
from dataclasses import dataclass
from typing import Literal

from fastapi import Depends, Security
from fastapi.security import APIKeyHeader

from app.config import Settings, get_settings
from app.errors import ApiError


@dataclass(frozen=True)
class Actor:
    name: str | None
    authenticated: bool
    client_type: Literal["anonymous", "salamanders", "ui"]


api_key_header = APIKeyHeader(
    name="X-API-Key",
    scheme_name="ApiKeyAuth",
    description=("Salamanders or shared UI API key. Optional only when AUTH_MODE=disabled."),
    auto_error=False,
)


def get_actor(
    x_api_key: str | None = Security(api_key_header),
    settings: Settings = Depends(get_settings),
) -> Actor:
    if settings.auth_mode == "disabled":
        return Actor(name=None, authenticated=False, client_type="anonymous")
    if not x_api_key:
        raise ApiError(401, "AUTHENTICATION_REQUIRED", "Thiếu X-API-Key")
    is_salamanders = hmac.compare_digest(settings.salamanders_key.get_secret_value(), x_api_key)
    is_ui = hmac.compare_digest(settings.ui_shared_key.get_secret_value(), x_api_key)
    if is_salamanders:
        return Actor(name="Salamanders", authenticated=True, client_type="salamanders")
    if is_ui:
        return Actor(name="UI", authenticated=True, client_type="ui")
    raise ApiError(401, "INVALID_API_KEY", "API key không hợp lệ")


def require_submitter(actor: Actor, submitter: str) -> str:
    return actor.name or submitter


def require_mutation_permission(actor: Actor, owner: str, settings: Settings) -> str:
    acting_name = actor.name or owner
    if (
        settings.auth_mode == "api_key"
        and settings.permission_mode == "owner_only"
        and actor.name != owner
    ):
        raise ApiError(403, "RESULT_PERMISSION_DENIED", "Chỉ người tạo được sửa hoặc xóa")
    return acting_name
