"""Token helpers: opaque random tokens (sessions, CSRF) and signed stateless email-link tokens."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from typing import Any

from flask import current_app
from itsdangerous import BadSignature, URLSafeTimedSerializer

PASSWORD_RESET_MAX_AGE = 30 * 60
EMAIL_VERIFICATION_MAX_AGE = 48 * 3600
MAX_LINK_TOKEN_LENGTH = 512
# Distinct salts: a token minted for one purpose can never be replayed for another.
_RESET_LINK_SALT = "propflow.password-reset"
_VERIFY_LINK_SALT = "propflow.email-verification"


def generate_token() -> str:
    """256 bits of randomness, URL-safe."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Tokens are high-entropy, so a fast deterministic hash is correct (unlike passwords)."""
    return hashlib.sha256(token.encode()).hexdigest()


def csrf_token_for(session_token_hash: str, secret_key: str) -> str:
    """CSRF token bound to one session; cannot be forged without the server secret."""
    message = f"csrf:{session_token_hash}".encode()
    return hmac.new(secret_key.encode(), message, hashlib.sha256).hexdigest()


def tokens_match(provided: str, expected: str) -> bool:
    # Compare as bytes: compare_digest raises TypeError on non-ASCII str input.
    return hmac.compare_digest(provided.encode(), expected.encode())


def password_fingerprint(password_hash: str) -> str:
    """Changes whenever the password changes, so a reset link can be used at most once."""
    return hashlib.sha256(password_hash.encode()).hexdigest()[:32]


def _serializer(salt: str) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt=salt)


def _load(salt: str, token: str, max_age: int) -> dict[str, Any] | None:
    if not token or len(token) > MAX_LINK_TOKEN_LENGTH:
        return None
    try:
        data = _serializer(salt).loads(token, max_age=max_age)
    except BadSignature:  # also covers SignatureExpired
        return None
    return data if isinstance(data, dict) else None


def _parse_uuid(value: object) -> uuid.UUID | None:
    if not isinstance(value, str):
        return None
    try:
        return uuid.UUID(value)
    except ValueError:
        return None


def make_password_reset_token(user_id: uuid.UUID, password_hash: str) -> str:
    payload = {"uid": str(user_id), "fp": password_fingerprint(password_hash)}
    return str(_serializer(_RESET_LINK_SALT).dumps(payload))


def read_password_reset_token(token: str) -> tuple[uuid.UUID, str] | None:
    data = _load(_RESET_LINK_SALT, token, PASSWORD_RESET_MAX_AGE)
    user_id = _parse_uuid(data.get("uid")) if data else None
    fingerprint = data.get("fp") if data else None
    if user_id is None or not isinstance(fingerprint, str):
        return None
    return user_id, fingerprint


def make_email_verification_token(user_id: uuid.UUID, email: str) -> str:
    return str(_serializer(_VERIFY_LINK_SALT).dumps({"uid": str(user_id), "email": email}))


def read_email_verification_token(token: str) -> tuple[uuid.UUID, str] | None:
    data = _load(_VERIFY_LINK_SALT, token, EMAIL_VERIFICATION_MAX_AGE)
    user_id = _parse_uuid(data.get("uid")) if data else None
    email = data.get("email") if data else None
    if user_id is None or not isinstance(email, str):
        return None
    return user_id, email
