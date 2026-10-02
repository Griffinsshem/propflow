"""Distributed rate limiting (Flask-Limiter, Redis storage). Policy: ADR 0004."""

from __future__ import annotations

import hashlib

from flask import Response, g, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


def ip_key() -> str:
    return f"ip:{get_remote_address()}"


def client_key() -> str:
    """Logged-in users get their own bucket, so users sharing a carrier NAT IP don't collide."""
    user = g.get("current_user")
    return f"user:{user.id}" if user is not None else ip_key()


def account_key() -> str:
    """Bucket per *target* account, from the JSON email field. Hashed: Redis never holds emails."""
    data = request.get_json(silent=True)
    email = data.get("email") if isinstance(data, dict) else None
    if not isinstance(email, str) or not email.strip():
        return ip_key()
    digest = hashlib.sha256(email.strip().lower().encode()).hexdigest()[:32]
    return f"account:{digest}"


def failed_login(response: Response) -> bool:
    """Only failed attempts count against the per-account login limit."""
    return response.status_code == 401


limiter = Limiter(key_func=client_key)
