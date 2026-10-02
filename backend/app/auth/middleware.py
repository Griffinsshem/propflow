"""Loads the session from its cookie; enforces Origin and CSRF checks on unsafe API calls."""

from __future__ import annotations

import structlog
from flask import Flask, current_app, g, request

from app.auth.service import resolve_session
from app.auth.tokens import csrf_token_for, tokens_match
from app.common.errors import PermissionDeniedError

UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
CSRF_HEADER = "X-CSRF-Token"
_UNVERIFIED = "The request could not be verified."


def register_auth_middleware(app: Flask) -> None:
    @app.before_request
    def _load_session() -> None:
        g.current_user = None
        g.current_session = None
        if not request.path.startswith("/api/"):
            return  # health checks must never depend on the database
        token = request.cookies.get(current_app.config["AUTH_SESSION_COOKIE"])
        if token:
            resolved = resolve_session(token)
            if resolved is not None:
                g.current_session, g.current_user = resolved
                structlog.contextvars.bind_contextvars(user_id=str(g.current_user.id))

    @app.before_request
    def _verify_unsafe_request() -> None:
        if request.method not in UNSAFE_METHODS or not request.path.startswith("/api/"):
            return
        origin = request.headers.get("Origin")
        if origin is not None and origin != current_app.config["FRONTEND_ORIGIN"]:
            raise PermissionDeniedError(_UNVERIFIED)
        if g.current_session is not None:
            expected = csrf_token_for(
                g.current_session.token_hash, current_app.config["SECRET_KEY"]
            )
            if not tokens_match(request.headers.get(CSRF_HEADER, ""), expected):
                raise PermissionDeniedError(_UNVERIFIED)
