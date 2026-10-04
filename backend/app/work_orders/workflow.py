"""The work order status machine and its effect on the linked maintenance request.

Contractor-side moves need WORKORDER_UPDATE (contractors, and managers acting on their
behalf); cancellation needs WORKORDER_ASSIGN (managers). Request effects are applied through
maintenance.service.apply_linked_status, which still validates against the request workflow.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from app.authz.permissions import Permission, has_permission
from app.maintenance.models import MaintenanceStatus
from app.maintenance.workflow import Transition
from app.work_orders.models import WorkOrderStatus as W

P = Permission

TRANSITIONS: Mapping[tuple[str, str], Transition] = MappingProxyType(
    {
        (W.ASSIGNED, W.ACCEPTED): Transition(P.WORKORDER_UPDATE),
        (W.ASSIGNED, W.DECLINED): Transition(P.WORKORDER_UPDATE, reason_required=True),
        (W.ACCEPTED, W.IN_PROGRESS): Transition(P.WORKORDER_UPDATE),
        (W.IN_PROGRESS, W.COMPLETED): Transition(P.WORKORDER_UPDATE),
        (W.ASSIGNED, W.CANCELLED): Transition(P.WORKORDER_ASSIGN, reason_required=True),
        (W.ACCEPTED, W.CANCELLED): Transition(P.WORKORDER_ASSIGN, reason_required=True),
        (W.IN_PROGRESS, W.CANCELLED): Transition(P.WORKORDER_ASSIGN, reason_required=True),
    }
)

# Completion deliberately has no effect: the manager verifies the work and resolves it.
REQUEST_EFFECTS: Mapping[str, str] = MappingProxyType(
    {
        W.IN_PROGRESS: MaintenanceStatus.IN_PROGRESS,
        W.DECLINED: MaintenanceStatus.TRIAGED,
        W.CANCELLED: MaintenanceStatus.TRIAGED,
    }
)


def get_transition(from_status: str, to_status: str) -> Transition | None:
    return TRANSITIONS.get((from_status, to_status))


def allowed_next(from_status: str, role: str) -> list[str]:
    return sorted(
        to_status
        for (current, to_status), transition in TRANSITIONS.items()
        if current == from_status and has_permission(role, transition.permission)
    )
