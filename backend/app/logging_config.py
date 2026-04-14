"""Structured JSON logging via loguru."""

from __future__ import annotations

import json
import logging
import sys
from typing import Any

from loguru import logger

from app.config import get_settings

_SENSITIVE_KEYS = {"password", "password_hash", "authorization", "token", "jwt", "secret"}


def _serialize(record: dict[str, Any]) -> str:
    extra = record.get("extra", {}) or {}
    payload = {
        "timestamp": record["time"].isoformat(),
        "level": record["level"].name,
        "message": record["message"],
        "module": record["name"],
        "request_id": extra.get("request_id"),
    }
    for k, v in extra.items():
        if k in ("request_id",):
            continue
        if k.lower() in _SENSITIVE_KEYS:
            payload[k] = "***"
        else:
            payload[k] = v
    if record["exception"] is not None:
        payload["exception"] = str(record["exception"])
    return json.dumps(payload, ensure_ascii=False, default=str)


def _sink(message: Any) -> None:
    record = message.record
    sys.stdout.write(_serialize(record) + "\n")


class InterceptHandler(logging.Handler):
    """Route stdlib logging into loguru."""

    def emit(self, record: logging.LogRecord) -> None:  # pragma: no cover
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def setup_logging() -> None:
    settings = get_settings()
    logger.remove()
    logger.add(_sink, level=settings.log_level.upper(), enqueue=False, backtrace=False)

    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "sqlalchemy.engine"):
        lg = logging.getLogger(name)
        lg.handlers = [InterceptHandler()]
        lg.propagate = False
