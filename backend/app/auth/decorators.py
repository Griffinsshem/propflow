"""Route guards. Authorization policies (Phase 4) build on these."""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps

from flask import g

from app.common.errors import AuthenticationError


def login_required[**P, R](view: Callable[P, R]) -> Callable[P, R]:
    @wraps(view)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        if g.get("current_user") is None:
            raise AuthenticationError()
        return view(*args, **kwargs)

    return wrapper
