"""Session and CSRF cookie handling."""

from __future__ import annotations

from flask import Response, current_app

from app.auth.service import IssuedSession


def set_auth_cookies(response: Response, issued: IssuedSession) -> None:
    config = current_app.config
    response.set_cookie(
        config["AUTH_SESSION_COOKIE"],
        issued.token,
        max_age=issued.max_age_seconds,
        secure=config["AUTH_COOKIE_SECURE"],
        httponly=True,
        samesite="Lax",
        path="/",
    )
    # Deliberately readable by the frontend, which echoes it in the X-CSRF-Token header.
    response.set_cookie(
        config["AUTH_CSRF_COOKIE"],
        issued.csrf_token,
        max_age=issued.max_age_seconds,
        secure=config["AUTH_COOKIE_SECURE"],
        httponly=False,
        samesite="Lax",
        path="/",
    )


def clear_auth_cookies(response: Response) -> None:
    config = current_app.config
    for name in (config["AUTH_SESSION_COOKIE"], config["AUTH_CSRF_COOKIE"]):
        response.delete_cookie(name, path="/", secure=config["AUTH_COOKIE_SECURE"], samesite="Lax")
