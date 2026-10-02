"""Authentication use cases. Each public function is one database transaction."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from flask import current_app
from sqlalchemy.exc import IntegrityError

from app.auth import repository
from app.auth.models import User, UserSession
from app.auth.passwords import (
    hash_password,
    needs_rehash,
    spend_verification_time,
    verify_password,
)
from app.auth.tokens import csrf_token_for, generate_token, hash_token
from app.common.errors import AuthenticationError, ConflictError
from app.extensions import db

INVALID_CREDENTIALS = "Invalid email or password."
# Coarse accuracy is enough; avoids a database write on every request.
LAST_SEEN_WRITE_INTERVAL = timedelta(minutes=5)
MAX_TOKEN_LENGTH = 128


@dataclass(frozen=True)
class IssuedSession:
    session: UserSession
    token: str
    csrf_token: str
    max_age_seconds: int


def _now() -> datetime:
    return datetime.now(UTC)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def _start_session(user: User, *, ip_address: str | None, user_agent: str | None) -> IssuedSession:
    token = generate_token()
    now = _now()
    absolute: timedelta = current_app.config["SESSION_ABSOLUTE_TIMEOUT"]
    memberships = repository.list_active_memberships(user.id)
    session = UserSession(
        user_id=user.id,
        token_hash=hash_token(token),
        created_at=now,
        last_seen_at=now,
        expires_at=now + absolute,
        active_organization_id=memberships[0][1].id if memberships else None,
        ip_address=ip_address,
        user_agent=user_agent[:512] if user_agent else None,
    )
    db.session.add(session)
    return IssuedSession(
        session=session,
        token=token,
        csrf_token=csrf_token_for(session.token_hash, current_app.config["SECRET_KEY"]),
        max_age_seconds=int(absolute.total_seconds()),
    )


def register(
    email: str,
    password: str,
    full_name: str,
    *,
    ip_address: str | None,
    user_agent: str | None,
) -> tuple[User, IssuedSession]:
    user = User(
        email=normalize_email(email),
        password_hash=hash_password(password),
        full_name=full_name.strip(),
    )
    db.session.add(user)
    try:
        db.session.flush()
    except IntegrityError as exc:
        db.session.rollback()
        raise ConflictError("An account with this email already exists.") from exc
    issued = _start_session(user, ip_address=ip_address, user_agent=user_agent)
    db.session.commit()
    return user, issued


def login(
    email: str,
    password: str,
    *,
    ip_address: str | None,
    user_agent: str | None,
    previous_session: UserSession | None,
) -> tuple[User, IssuedSession]:
    user = repository.get_user_by_email(normalize_email(email))
    if user is None:
        spend_verification_time(password)
        raise AuthenticationError(INVALID_CREDENTIALS)
    # Verify before checking is_active so both failure paths cost the same time.
    if not verify_password(user.password_hash, password) or not user.is_active:
        raise AuthenticationError(INVALID_CREDENTIALS)
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
    if previous_session is not None:
        previous_session.revoked_at = _now()  # always a fresh token: no session fixation
    user.last_login_at = _now()
    issued = _start_session(user, ip_address=ip_address, user_agent=user_agent)
    db.session.commit()
    return user, issued


def resolve_session(token: str) -> tuple[UserSession, User] | None:
    """Return the live session and user for a cookie token, or None if unusable."""
    if not token or len(token) > MAX_TOKEN_LENGTH:
        return None
    session = repository.get_session_by_token_hash(hash_token(token))
    if session is None or session.revoked_at is not None:
        return None
    now = _now()
    idle: timedelta = current_app.config["SESSION_IDLE_TIMEOUT"]
    if session.expires_at <= now or session.last_seen_at + idle <= now:
        return None
    user = repository.get_user(session.user_id)
    if user is None or not user.is_active:
        return None
    if now - session.last_seen_at >= LAST_SEEN_WRITE_INTERVAL:
        session.last_seen_at = now
        db.session.commit()
    return session, user


def logout(session: UserSession | None) -> None:
    if session is not None and session.revoked_at is None:
        session.revoked_at = _now()
        db.session.commit()


def profile(user: User, session: UserSession | None) -> dict[str, Any]:
    memberships = repository.list_active_memberships(user.id)
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "email_verified": user.email_verified_at is not None,
        "active_organization_id": session.active_organization_id if session else None,
        "memberships": [
            {"organization_id": org.id, "organization_name": org.name, "role": membership.role}
            for membership, org in memberships
        ],
    }
