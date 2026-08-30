from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.datastructures import Headers
from starlette.types import ASGIApp, Receive, Scope, Send

from src.api.dependencies import open_connection
from src.api.routes import router
from src.db.repository import create_schema
from src.errors import NotFoundError, SupportAgentError, ValidationError

_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


def _load_local_env(env_file: Path | None = None) -> None:
    """Load the repo-root `.env` so `uvicorn src.api.main:app` picks up
    ANTHROPIC_API_KEY without a manual export (dev/demo convenience, mirrors
    tests/conftest.py; `.env` is gitignored, so no secrets are committed).
    Never overrides already-exported variables, and is a no-op if the file
    is missing.
    """
    load_dotenv(env_file or _ENV_FILE)


_load_local_env()

logger = logging.getLogger(__name__)

MAX_REQUEST_BYTES = 64 * 1024

_ERROR_RESPONSES: dict[type[SupportAgentError], tuple[int, str]] = {
    NotFoundError: (404, "Resource not found"),
    ValidationError: (422, "Invalid request"),
}
_FALLBACK_RESPONSE = (500, "Internal server error")


def _too_large_response() -> JSONResponse:
    return JSONResponse(status_code=413, content={"detail": "Request too large"})


class RequestSizeLimitMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        declared = Headers(scope=scope).get("content-length")
        if declared is not None:
            if declared.isdigit() and int(declared) > MAX_REQUEST_BYTES:
                await _too_large_response()(scope, receive, send)
                return
            await self._app(scope, receive, send)
            return

        body, too_large = await _read_capped(receive)
        if too_large:
            await _too_large_response()(scope, receive, send)
            return
        await self._app(scope, _replay(body), send)


async def _read_capped(receive: Receive) -> tuple[bytes, bool]:
    chunks: list[bytes] = []
    size = 0
    more_body = True
    while more_body:
        message = await receive()
        if message["type"] != "http.request":
            break
        chunks.append(message.get("body", b""))
        size += len(chunks[-1])
        if size > MAX_REQUEST_BYTES:
            return b"", True
        more_body = message.get("more_body", False)
    return b"".join(chunks), False


class _ReplayReceive:
    def __init__(self, body: bytes) -> None:
        self._body = body
        self._sent = False

    async def __call__(self) -> dict[str, object]:
        if self._sent:
            return {"type": "http.disconnect"}
        self._sent = True
        return {"type": "http.request", "body": self._body, "more_body": False}


def _replay(body: bytes) -> Receive:
    return _ReplayReceive(body)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    connection = open_connection()
    try:
        create_schema(connection)
    finally:
        connection.close()
    yield


app = FastAPI(
    title="IT Support Agent",
    description="Proposes answer / ask / escalate for one ticket at a time.",
    version="0.1.0",
    lifespan=lifespan,
)
app.include_router(router)
app.add_middleware(RequestSizeLimitMiddleware)


@app.exception_handler(SupportAgentError)
def handle_support_agent_error(
    request: Request, exc: SupportAgentError
) -> JSONResponse:
    mapped = next(
        (
            response
            for error_type, response in _ERROR_RESPONSES.items()
            if isinstance(exc, error_type)
        ),
        None,
    )
    if mapped is None:
        logger.error("Request to %s failed: %s", request.url.path, exc, exc_info=exc)
        status_code, detail = _FALLBACK_RESPONSE
    else:
        logger.warning("Request to %s failed: %s", request.url.path, exc)
        status_code, detail = mapped
    return JSONResponse(status_code=status_code, content={"detail": detail})


@app.exception_handler(RequestValidationError)
def handle_request_validation_error(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    logger.warning("Invalid request to %s: %s", request.url.path, exc)
    return JSONResponse(status_code=422, content={"detail": "Invalid request"})


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
