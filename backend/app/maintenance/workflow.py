"""The maintenance status machine: the only place status transitions are defined.

Anything not listed here is rejected. Each transition names the permission it requires,
so who-may-do-what stays derived from the central permission matrix.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from app.authz.permissions import Permission, has_permission
from app.common.errors import AppError
from app.maintenance.models import MaintenanceStatus as S


class InvalidStatusTransitionError(AppError):
    status_code = 409
    code = "INVALID_STATUS_TRANSITION"
    message = "This status change is not allowed."


@dataclass(frozen=True)
class Transition:
    permission: Permission
    reason_required: bool = False


P = Permission

TRANSITIONS: Mapping[tuple[str, str], Transition] = MappingProxyType(
    {
        (S.SUBMITTED, S.TRIAGED): Transition(P.MAINTENANCE_UPDATE),
        (S.TRIAGED, S.ASSIGNED): Transition(P.MAINTENANCE_ASSIGN),
        # Unassign: the contractor declined or the work order was cancelled.
        (S.ASSIGNED, S.TRIAGED): Transition(P.MAINTENANCE_ASSIGN, reason_required=True),
        (S.ASSIGNED, S.IN_PROGRESS): Transition(P.MAINTENANCE_UPDATE),
        (S.IN_PROGRESS, S.WAITING): Transition(P.MAINTENANCE_UPDATE, reason_required=True),
        (S.WAITING, S.IN_PROGRESS): Transition(P.MAINTENANCE_UPDATE),
        (S.IN_PROGRESS, S.RESOLVED): Transition(P.MAINTENANCE_UPDATE),
        # Reopen: the fix did not hold.
        (S.RESOLVED, S.IN_PROGRESS): Transition(P.MAINTENANCE_UPDATE, reason_required=True),
        (S.RESOLVED, S.CLOSED): Transition(P.MAINTENANCE_CLOSE),
        # Early close: duplicates and invalid reports.
        (S.SUBMITTED, S.CLOSED): Transition(P.MAINTENANCE_CLOSE, reason_required=True),
        (S.TRIAGED, S.CLOSED): Transition(P.MAINTENANCE_CLOSE, reason_required=True),
    }
)


def get_transition(from_status: str, to_status: str) -> Transition | None:
    return TRANSITIONS.get((from_status, to_status))


def allowed_next(from_status: str, role: str) -> list[str]:
    """Statuses this role may move a request to next (drives the UI's action buttons)."""
    return sorted(
        to_status
        for (current, to_status), transition in TRANSITIONS.items()
        if current == from_status and has_permission(role, transition.permission)
    )
