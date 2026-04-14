"""X-Request-ID middleware — read or generate per-request id, propagate to logs."""

from __future__ import annotations

import uuid

from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

HEADER = "X-Request-ID"


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        req_id = request.headers.get(HEADER) or str(uuid.uuid4())
        request.state.request_id = req_id

        with logger.contextualize(request_id=req_id):
            response: Response = await call_next(request)

        response.headers[HEADER] = req_id
        return response
