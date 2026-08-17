from __future__ import annotations

import logging
import time
import uuid
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable
from threading import Lock
from typing import Any

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse, Response

from app.config import get_settings
from app.errors import ApiError
from app.realtime import hub
from app.routers import exports, queries, query_sets, results, system

settings = get_settings()
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("submission_api")

app = FastAPI(
    title="Submission Review System",
    version="1.1.0",
    description=(
        "Public KIS/QA/TRAKE submission API with realtime review UI. "
        "The operational history CSV is not an official competition submission; "
        "official export remains fail-closed."
    ),
    docs_url="/swagger.html",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    swagger_ui_parameters={
        "persistAuthorization": True,
        "tryItOutEnabled": True,
        "displayRequestDuration": True,
    },
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Key", "X-Request-ID"],
)

rate_buckets: dict[str, deque[float]] = defaultdict(deque)
rate_lock = Lock()


@app.get("/", include_in_schema=False)
def swagger_redirect() -> RedirectResponse:
    return RedirectResponse(url=app.docs_url or "/swagger.html")


@app.get("/docs", include_in_schema=False)
def legacy_docs_redirect() -> RedirectResponse:
    return RedirectResponse(url=app.docs_url or "/swagger.html")


def error_body(
    request: Request, code: str, message: str, field_errors: list[dict[str, str]] | None = None
) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "field_errors": field_errors or [],
            "request_id": getattr(request.state, "request_id", "unknown"),
        }
    }


@app.middleware("http")
async def request_controls(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id
    content_length = request.headers.get("content-length")
    if (
        content_length
        and content_length.isdigit()
        and int(content_length) > settings.max_request_bytes
    ):
        return JSONResponse(
            error_body(request, "REQUEST_TOO_LARGE", "Request vượt giới hạn"), status_code=413
        )
    if request.method == "POST" and request.url.path in {
        "/api/v1/results",
        "/api/v1/submissions",
    }:
        client = request.client.host if request.client else "unknown"
        now = time.monotonic()
        with rate_lock:
            bucket = rate_buckets[client]
            while bucket and bucket[0] < now - 60:
                bucket.popleft()
            if len(bucket) >= settings.result_rate_limit_per_minute:
                return JSONResponse(
                    error_body(request, "RATE_LIMITED", "Quá nhiều request"), status_code=429
                )
            bucket.append(now)
    started = time.monotonic()
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    logger.info(
        "request_complete request_id=%s method=%s path=%s status=%s duration_ms=%d",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        int((time.monotonic() - started) * 1000),
    )
    return response


@app.exception_handler(ApiError)
async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    body = error_body(
        request,
        exc.code,
        exc.message,
        [field_error.__dict__ for field_error in exc.field_errors],
    )
    if exc.details is not None:
        body["error"]["details"] = exc.details
    return JSONResponse(body, status_code=exc.status_code)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    malformed = any(error["type"] == "json_invalid" for error in exc.errors())
    field_errors = [
        {
            "path": ".".join(str(part) for part in error["loc"] if part != "body"),
            "code": error["type"].upper(),
            "message": error["msg"],
        }
        for error in exc.errors()
    ]
    return JSONResponse(
        error_body(
            request,
            "MALFORMED_REQUEST" if malformed else "SCHEMA_VALIDATION_FAILED",
            "JSON không hợp lệ" if malformed else "Request không đúng schema",
            field_errors,
        ),
        status_code=400 if malformed else 422,
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "unhandled_error request_id=%s", getattr(request.state, "request_id", "unknown")
    )
    return JSONResponse(
        error_body(request, "INTERNAL_ERROR", "Lỗi nội bộ"),
        status_code=500,
    )


app.include_router(query_sets.router, prefix="/api/v1")
app.include_router(queries.router, prefix="/api/v1")
app.include_router(results.router, prefix="/api/v1")
app.include_router(results.public_router, prefix="/api/v1")
app.include_router(exports.router, prefix="/api/v1")
app.include_router(system.router, prefix="/api/v1")


@app.websocket("/api/v1/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await hub.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await hub.disconnect(websocket)
