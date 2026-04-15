"""In-memory rate limiter for login (anti brute-force).

Single-process, TTL based. For multi-worker prod → swap to Redis-backed.
Tests can disable via `set_enabled(False)` in conftest.
"""

from __future__ import annotations

import threading
from collections import defaultdict
from time import monotonic

from fastapi import HTTPException, Request, status

_WINDOW_SECONDS = 60.0
_MAX_ATTEMPTS = 5
_attempts: dict[str, list[float]] = defaultdict(list)
_lock = threading.Lock()
_enabled = True


def set_enabled(flag: bool) -> None:
    """Toggle rate limiting — used by tests."""
    global _enabled
    _enabled = flag


def _client_ip(request: Request) -> str:
    if request.client and request.client.host:
        return request.client.host
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return "unknown"


def login_rate_limit(request: Request) -> None:
    """FastAPI dependency: 5 requests / 60s / IP. Raises 429 on overflow."""
    if not _enabled:
        return
    ip = _client_ip(request)
    now = monotonic()
    with _lock:
        bucket = _attempts[ip]
        # Drop entries older than window.
        fresh = [t for t in bucket if now - t < _WINDOW_SECONDS]
        if len(fresh) >= _MAX_ATTEMPTS:
            _attempts[ip] = fresh
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={"error": "Забагато спроб", "code": "RATE_LIMIT"},
            )
        fresh.append(now)
        _attempts[ip] = fresh
