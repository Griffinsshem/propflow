"""Authentication endpoints: a thin HTTP layer over app.auth.service."""

from __future__ import annotations

from typing import Any

from flask import Response, after_this_request, g, request
from flask_smorest import Blueprint

from app.auth import service
from app.auth.cookies import clear_auth_cookies, set_auth_cookies
from app.auth.decorators import login_required
from app.auth.schemas import CurrentUserSchema, LoginSchema, RegisterSchema

blp = Blueprint(
    "auth", __name__, url_prefix="/api/v1/auth", description="Registration, login and sessions."
)


def _issue_cookies(issued: service.IssuedSession) -> None:
    @after_this_request
    def _set(response: Response) -> Response:
        set_auth_cookies(response, issued)
        return response


@blp.post("/register")
@blp.arguments(RegisterSchema)
@blp.response(201, CurrentUserSchema)
def register(payload: dict[str, Any]) -> dict[str, Any]:
    user, issued = service.register(
        payload["email"],
        payload["password"],
        payload["full_name"],
        ip_address=request.remote_addr,
        user_agent=request.headers.get("User-Agent"),
    )
    _issue_cookies(issued)
    return service.profile(user, issued.session)


@blp.post("/login")
@blp.arguments(LoginSchema)
@blp.response(200, CurrentUserSchema)
def login(payload: dict[str, Any]) -> dict[str, Any]:
    user, issued = service.login(
        payload["email"],
        payload["password"],
        ip_address=request.remote_addr,
        user_agent=request.headers.get("User-Agent"),
        previous_session=g.current_session,
    )
    _issue_cookies(issued)
    return service.profile(user, issued.session)


@blp.post("/logout")
@blp.response(204)
def logout() -> None:
    service.logout(g.current_session)

    @after_this_request
    def _clear(response: Response) -> Response:
        clear_auth_cookies(response)
        return response


@blp.get("/me")
@blp.response(200, CurrentUserSchema)
@login_required
def me() -> dict[str, Any]:
    return service.profile(g.current_user, g.current_session)
