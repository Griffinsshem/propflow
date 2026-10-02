"""Opaque token helpers for sessions, CSRF and (later) invitations and password resets."""

from __future__ import annotations

import hashlib
import hmac
import secrets


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
