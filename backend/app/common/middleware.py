"""Per-request plumbing: request IDs, proxy verification, access logging, security headers."""

from __future__ import annotations

import hmac
import re
import time
import uuid

import structlog
from flask import Flask, Response, current_app, g, request

from app.common.errors import PermissionDeniedError

REQUEST_ID_HEADER = "X-Request-ID"
PROXY_AUTH_HEADER = "X-Proxy-Secret"
# Client-supplied IDs are accepted only if they look safe; this prevents log injection.
_SAFE_REQUEST_ID = re.compile(r"[A-Za-z0-9._-]{8,128}")
# Reachable without the proxy secret: the hosting platform's health checks call these directly.
_DIRECT_PATHS = frozenset({"/health", "/ready"})

# setdefault() is used below, so individual endpoints can override these deliberately.
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
}
# The API only ever returns JSON, so it can forbid everything a browser might otherwise do.
API_CSP = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
HSTS = "max-age=63072000; includeSubDomains"

logger = structlog.get_logger("propflow.http")


def register_middleware(app: Flask) -> None:
    @app.before_request
    def _start_request() -> None:
        incoming = request.headers.get(REQUEST_ID_HEADER, "")
        g.request_id = incoming if _SAFE_REQUEST_ID.fullmatch(incoming) else uuid.uuid4().hex
        g.request_started = time.perf_counter()
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=g.request_id)

    @app.before_request
    def _verify_proxy() -> None:
        """Refuses requests that bypassed the frontend proxy (they could spoof client IPs)."""
        secret = current_app.config["PROXY_SHARED_SECRET"]
        if not secret or request.path in _DIRECT_PATHS:
            return
        provided = request.headers.get(PROXY_AUTH_HEADER, "")
        if not hmac.compare_digest(provided.encode(), secret.encode()):
            logger.warning("proxy_verification_failed", path=request.path)
            raise PermissionDeniedError()

    @app.after_request
    def _finish_request(response: Response) -> Response:
        request_id = g.get("request_id")
        if request_id:
            response.headers[REQUEST_ID_HEADER] = request_id
        for name, value in SECURITY_HEADERS.items():
            response.headers.setdefault(name, value)
        if not request.path.startswith("/api/docs"):  # interactive docs exist only outside prod
            response.headers.setdefault("Content-Security-Policy", API_CSP)
        if current_app.config["HSTS_ENABLED"]:
            response.headers.setdefault("Strict-Transport-Security", HSTS)

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
