"""Authentication endpoints: a thin HTTP layer over the auth services."""

from __future__ import annotations

from typing import Any

from flask import Response, after_this_request, g, request
from flask_smorest import Blueprint

from app.auth import recovery, service
from app.auth.cookies import clear_auth_cookies, set_auth_cookies
from app.auth.decorators import login_required
from app.auth.schemas import (
    CurrentUserSchema,
    EmailTokenSchema,
    ForgotPasswordSchema,
    LoginSchema,
    MessageSchema,
    RegisterSchema,
    ResetPasswordSchema,
)
from app.common.rate_limit import account_key, client_key, failed_login, ip_key, limiter

blp = Blueprint(
    "auth", __name__, url_prefix="/api/v1/auth", description="Registration, login and sessions."
)

RESET_REQUESTED = "If an account exists for that email, a reset link has been sent."
VERIFICATION_SENT = "If your email is not yet verified, a new link has been sent."


def _issue_cookies(issued: service.IssuedSession) -> None:
    @after_this_request
    def _set(response: Response) -> Response:
        set_auth_cookies(response, issued)
        return response


@blp.post("/register")
@limiter.limit("20 per hour", key_func=ip_key)
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
    recovery.send_verification_email(user)
    _issue_cookies(issued)
    return service.profile(user, issued.session)


@blp.post("/login")
@limiter.limit("20 per minute;200 per hour", key_func=ip_key)
@limiter.limit("10 per 15 minutes", key_func=account_key, deduct_when=failed_login)
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


@blp.post("/forgot-password")
@limiter.limit("10 per hour", key_func=ip_key)
@limiter.limit("3 per hour", key_func=account_key)
@blp.arguments(ForgotPasswordSchema)
@blp.response(202, MessageSchema)
def forgot_password(payload: dict[str, Any]) -> dict[str, str]:
    recovery.request_password_reset(payload["email"])
    return {"message": RESET_REQUESTED}


@blp.post("/reset-password")
@limiter.limit("10 per hour", key_func=ip_key)
@blp.arguments(ResetPasswordSchema)
@blp.response(204)
def reset_password(payload: dict[str, Any]) -> None:
    recovery.reset_password(payload["token"], payload["new_password"])


@blp.post("/verify-email")
@limiter.limit("20 per hour", key_func=ip_key)
@blp.arguments(EmailTokenSchema)
@blp.response(204)
def verify_email(payload: dict[str, Any]) -> None:
    recovery.verify_email(payload["token"])


@blp.post("/resend-verification")
@limiter.limit("3 per hour", key_func=client_key)
@blp.response(202, MessageSchema)
@login_required
def resend_verification() -> dict[str, str]:
    recovery.send_verification_email(g.current_user)
    return {"message": VERIFICATION_SENT}
