"""Password reset and email verification use cases (stateless signed tokens; ADR 0004)."""

from __future__ import annotations

from datetime import UTC, datetime

from flask import current_app

from app.auth import repository
from app.auth.models import User
from app.auth.passwords import hash_password
from app.auth.service import normalize_email
from app.auth.tokens import (
    EMAIL_VERIFICATION_MAX_AGE,
    PASSWORD_RESET_MAX_AGE,
    make_email_verification_token,
    make_password_reset_token,
    password_fingerprint,
    read_email_verification_token,
    read_password_reset_token,
    tokens_match,
)
from app.common.errors import AppError
from app.extensions import db
from app.notifications.email import EmailMessage, send_email


class InvalidTokenError(AppError):
    status_code = 400
    code = "INVALID_TOKEN"
    message = "This link is invalid or has expired."


def _link(path: str, token: str) -> str:
    # URL fragment, not query string: never sent to servers, logged, or leaked via Referer.
    return f"{current_app.config['FRONTEND_ORIGIN']}{path}#token={token}"


def request_password_reset(email: str) -> None:
    """Same outcome for unknown accounts: the caller always returns an identical response."""
    user = repository.get_user_by_email(normalize_email(email))
    if user is None or not user.is_active:
        return
    token = make_password_reset_token(user.id, user.password_hash)
    send_email(
        EmailMessage(
            to=user.email,
            subject="Reset your PropFlow password",
            body=(
                "Use this link to choose a new password:\n\n"
                f"{_link('/reset-password', token)}\n\n"
                f"It expires in {PASSWORD_RESET_MAX_AGE // 60} minutes and works once. "
                "If you did not request this, you can ignore this email."
            ),
        )
    )


def reset_password(token: str, new_password: str) -> None:
    parsed = read_password_reset_token(token)
    if parsed is None:
        raise InvalidTokenError()
    user_id, fingerprint = parsed
    user = repository.get_user(user_id)
    if (
        user is None
        or not user.is_active
        or not tokens_match(fingerprint, password_fingerprint(user.password_hash))
    ):
        raise InvalidTokenError()
    user.password_hash = hash_password(new_password)
    # Anyone holding an old session (possibly an attacker) is logged out.
    repository.revoke_all_sessions(user.id, datetime.now(UTC))
    db.session.commit()


def send_verification_email(user: User) -> None:
    if user.email_verified_at is not None:
        return
    token = make_email_verification_token(user.id, user.email)
    send_email(
        EmailMessage(
            to=user.email,
            subject="Verify your PropFlow email address",
            body=(
                "Confirm your email address with this link:\n\n"
                f"{_link('/verify-email', token)}\n\n"
                f"It expires in {EMAIL_VERIFICATION_MAX_AGE // 3600} hours."
            ),
        )
    )


def verify_email(token: str) -> None:
    parsed = read_email_verification_token(token)
    if parsed is None:
        raise InvalidTokenError()
    user_id, email = parsed
    user = repository.get_user(user_id)
    if user is None or not user.is_active or user.email != email:
        raise InvalidTokenError()
    if user.email_verified_at is None:
        user.email_verified_at = datetime.now(UTC)
        db.session.commit()
