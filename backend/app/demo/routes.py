"""Private demo sandboxes (ADR 0021): a thin HTTP layer over app.demo.service."""

from __future__ import annotations

from typing import Any

from flask import Response, after_this_request, g, request
from flask_smorest import Blueprint

from app.auth import service as auth_service
from app.auth.cookies import set_auth_cookies
from app.auth.decorators import login_required
from app.auth.schemas import CurrentUserSchema
from app.common.rate_limit import ip_key, limiter
from app.demo import service
from app.demo.schemas import ViewAsSchema

blp = Blueprint("demo", __name__, url_prefix="/api/v1/demo", description="Private demo sandboxes.")


def _issue_cookies(issued: auth_service.IssuedSession) -> None:
    @after_this_request
    def _set(response: Response) -> Response:
        set_auth_cookies(response, issued)
        return response


@blp.post("")
@limiter.limit("5 per hour;20 per day", key_func=ip_key)
@blp.response(201, CurrentUserSchema)
def start_demo() -> dict[str, Any]:
    previous = g.get("current_session")
    if previous is not None:  # one browser, one session: as signing in does
        auth_service.logout(previous)
    user, issued = service.create_sandbox(
        ip_address=request.remote_addr, user_agent=request.headers.get("User-Agent")
    )
    _issue_cookies(issued)
    return auth_service.profile(user, issued.session)


@blp.post("/view-as")
@limiter.limit("60 per hour")
@blp.arguments(ViewAsSchema)
@blp.response(200, CurrentUserSchema)
@login_required
def view_as(payload: dict[str, Any]) -> dict[str, Any]:
    user, issued = service.view_as(
        g.current_session,
        g.current_user,
        payload["role"],
        ip_address=request.remote_addr,
        user_agent=request.headers.get("User-Agent"),
    )
    _issue_cookies(issued)
    return auth_service.profile(user, issued.session)
