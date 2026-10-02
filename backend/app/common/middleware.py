"""Per-request plumbing: request IDs, access logging, baseline security headers."""

from __future__ import annotations

import re
import time
import uuid

import structlog
from flask import Flask, Response, g, request

REQUEST_ID_HEADER = "X-Request-ID"
# Client-supplied IDs are accepted only if they look safe; this prevents log injection.
_SAFE_REQUEST_ID = re.compile(r"[A-Za-z0-9._-]{8,128}")

# setdefault() is used below, so individual endpoints can override these deliberately.
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store",
}

logger = structlog.get_logger("propflow.http")


def register_middleware(app: Flask) -> None:
    @app.before_request
    def _start_request() -> None:
        incoming = request.headers.get(REQUEST_ID_HEADER, "")
        g.request_id = incoming if _SAFE_REQUEST_ID.fullmatch(incoming) else uuid.uuid4().hex
        g.request_started = time.perf_counter()
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=g.request_id)

    @app.after_request
    def _finish_request(response: Response) -> Response:
        request_id = g.get("request_id")
        if request_id:
            response.headers[REQUEST_ID_HEADER] = request_id
        for name, value in SECURITY_HEADERS.items():
            response.headers.setdefault(name, value)

        started = g.get("request_started")
        duration_ms = round((time.perf_counter() - started) * 1000, 2) if started else None
        # Path only, never the query string: query strings can carry tokens.
        logger.info(
            "request_completed",
            method=request.method,
            route=request.url_rule.rule if request.url_rule else None,
            path=request.path,
            status=response.status_code,
            duration_ms=duration_ms,
        )
        return response
