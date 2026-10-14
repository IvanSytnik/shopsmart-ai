"""Error responses: every error is `{"detail": "<generic text>", "code": "<machine code>"}`.

Clients branch on `code`; `detail` is a human-readable fallback and never carries internals.
"""

import logging
from typing import Literal

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

logger = logging.getLogger(__name__)

ErrorCode = Literal[
    "validation_error",
    "rate_limited",
    "daily_limit",
    "ai_unavailable",
    "ai_timeout",
    "generation_failed",
]


class AppError(Exception):
    def __init__(self, status_code: int, code: ErrorCode, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.code = code
        self.detail = detail


def error_response(status_code: int, code: ErrorCode, detail: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"detail": detail, "code": code})


async def app_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)
    return error_response(exc.status_code, exc.code, exc.detail)


async def validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    # Field locations and messages only; `input` is left out so user data isn't echoed back.
    errors = [{"loc": list(e["loc"]), "msg": e["msg"]} for e in exc.errors()]
    return JSONResponse(
        status_code=422,
        content={"detail": "Invalid request", "code": "validation_error", "errors": errors},
    )


async def rate_limited_handler(request: Request, exc: Exception) -> JSONResponse:
    # slowapi already logs the exceeded limit with the client key.
    return error_response(429, "rate_limited", "Too many requests, please try again later")


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(RateLimitExceeded, rate_limited_handler)
