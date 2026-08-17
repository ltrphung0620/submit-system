from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FieldError:
    path: str
    code: str
    message: str


@dataclass
class ApiError(Exception):
    status_code: int
    code: str
    message: str
    field_errors: list[FieldError] = field(default_factory=list)
    details: dict[str, Any] | None = None
