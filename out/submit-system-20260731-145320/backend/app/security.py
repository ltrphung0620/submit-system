from __future__ import annotations

import hmac
from dataclasses import dataclass

from fastapi import Depends, Security
from fastapi.security import APIKeyHeader

from app.config import Settings, get_settings
from app.errors import ApiError


@dataclass(frozen=True)
class Actor:
    name: str | None
    authenticated: bool


api_key_header = APIKeyHeader(
    name="X-API-Key",
    scheme_name="ApiKeyAuth",
    description="API key configured in API_KEYS_JSON. Optional when AUTH_MODE=disabled.",
    auto_error=False,
)


def get_actor(
    x_api_key: str | None = Security(api_key_header),
    settings: Settings = Depends(get_settings),
) -> Actor:
    if settings.auth_mode == "disabled":
        return Actor(name=None, authenticated=False)
    if not x_api_key:
        raise ApiError(401, "AUTHENTICATION_REQUIRED", "Thiếu X-API-Key")
    owner = next(
        (
            candidate_owner
            for key, candidate_owner in settings.api_keys.items()
            if hmac.compare_digest(key, x_api_key)
        ),
        None,
    )
    if owner is None:
        raise ApiError(401, "INVALID_API_KEY", "API key không hợp lệ")
    return Actor(name=owner, authenticated=True)


def require_submitter(actor: Actor, submitter: str) -> str:
    if actor.authenticated and actor.name != submitter:
        raise ApiError(403, "SUBMITTER_MISMATCH", "submitter không khớp chủ API key")
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
