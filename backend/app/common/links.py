"""Links to the frontend that carry a secret token."""

from __future__ import annotations

from flask import current_app


def frontend_link(path: str, token: str) -> str:
    """Token in the URL fragment: never sent to servers, logged, or leaked via Referer."""
    return f"{current_app.config['FRONTEND_ORIGIN']}{path}#token={token}"
