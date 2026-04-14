"""Unified error response: {error, code, request_id}."""

from __future__ import annotations

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger
from starlette.exceptions import HTTPException as StarletteHTTPException


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def _code_for(status: int) -> str:
    return {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        429: "RATE_LIMITED",
        500: "INTERNAL_ERROR",
    }.get(status, "ERROR")


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    # Allow routers to raise HTTPException(detail={"error": ..., "code": ...})
    # for precise error codes; fall back to status-based mapping otherwise.
    if isinstance(exc.detail, dict):
        body = {
            "error": exc.detail.get("error", "error"),
            "code": exc.detail.get("code", _code_for(exc.status_code)),
            "request_id": _request_id(request),
        }
    else:
        body = {
            "error": exc.detail if isinstance(exc.detail, str) else "error",
            "code": _code_for(exc.status_code),
            "request_id": _request_id(request),
        }
    return JSONResponse(status_code=exc.status_code, content=body)


def _jsonable_errors(errors: list) -> list:
    out = []
    for err in errors:
        safe = {}
        for k, v in err.items():
            if k == "ctx" and isinstance(v, dict):
                safe[k] = {ck: str(cv) for ck, cv in v.items()}
            elif isinstance(v, str | int | float | bool | type(None) | list | dict):
                safe[k] = v
            else:
                safe[k] = str(v)
        out.append(safe)
    return out


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    body = {
        "error": "validation error",
        "code": "VALIDATION_ERROR",
        "request_id": _request_id(request),
        "details": _jsonable_errors(exc.errors()),
    }
    return JSONResponse(status_code=422, content=body)


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.opt(exception=exc).error("unhandled_exception")
    body = {
        "error": "internal server error",
        "code": "INTERNAL_ERROR",
        "request_id": _request_id(request),
    }
    return JSONResponse(status_code=500, content=body)


def register_error_handlers(app) -> None:
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
