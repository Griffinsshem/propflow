"""Authorization guard for organization-scoped endpoints."""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps

from app.authz.context import current_org_context
from app.authz.permissions import Permission, has_permission
from app.common.errors import PermissionDeniedError


def require_permission[**P, R](
    permission: Permission,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Requires login, a valid organization context, and a role holding `permission`."""

    def decorator(view: Callable[P, R]) -> Callable[P, R]:
        @wraps(view)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            context = current_org_context()
            if not has_permission(context.role, permission):
                raise PermissionDeniedError()
            return view(*args, **kwargs)

        return wrapper

    return decorator
