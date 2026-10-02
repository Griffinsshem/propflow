"""Password hashing with Argon2id. Parameters come from config (cheap only in tests)."""

from __future__ import annotations

import secrets
from typing import cast

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from flask import Flask, current_app


def init_password_hasher(app: Flask) -> None:
    hasher = PasswordHasher(**app.config["ARGON2_PARAMS"])
    app.extensions["password_hasher"] = hasher
    # Verified against when an email is unknown, so timing never reveals which accounts exist.
    app.extensions["password_dummy_hash"] = hasher.hash(secrets.token_urlsafe(32))


def _hasher() -> PasswordHasher:
    return cast(PasswordHasher, current_app.extensions["password_hasher"])


def hash_password(password: str) -> str:
    return _hasher().hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher().verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    return _hasher().check_needs_rehash(password_hash)


def spend_verification_time(password: str) -> None:
    """Do the same work as a real check when there is no account to check against."""
    verify_password(cast(str, current_app.extensions["password_dummy_hash"]), password)
