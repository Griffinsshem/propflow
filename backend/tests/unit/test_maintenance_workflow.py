from collections import deque

import pytest

from app.maintenance.models import MaintenanceStatus as S
from app.maintenance.workflow import TRANSITIONS, allowed_next, get_transition
from app.organizations.models import MembershipRole as R


def test_every_status_is_reachable_from_submitted() -> None:
    seen, queue = {S.SUBMITTED.value}, deque([S.SUBMITTED.value])
    while queue:
        current = queue.popleft()
        for from_status, to_status in TRANSITIONS:
            if from_status == current and to_status not in seen:
                seen.add(to_status)
                queue.append(to_status)
    assert seen == {status.value for status in S}


def test_closed_is_terminal() -> None:
    assert not [key for key in TRANSITIONS if key[0] == S.CLOSED]


@pytest.mark.parametrize("role", [R.TENANT, R.CONTRACTOR])
@pytest.mark.parametrize("status", list(S))
def test_tenants_and_contractors_cannot_move_requests(role: R, status: S) -> None:
    assert allowed_next(status, role) == []


@pytest.mark.parametrize(
    ("from_status", "to_status"),
    [
        (S.IN_PROGRESS, S.WAITING),
        (S.RESOLVED, S.IN_PROGRESS),
        (S.SUBMITTED, S.CLOSED),
        (S.TRIAGED, S.CLOSED),
    ],
)
def test_explanatory_transitions_require_a_reason(from_status: S, to_status: S) -> None:
    transition = get_transition(from_status, to_status)
    assert transition is not None and transition.reason_required


def test_skipping_steps_is_not_allowed() -> None:
    assert get_transition(S.SUBMITTED, S.RESOLVED) is None
    assert get_transition(S.CLOSED, S.IN_PROGRESS) is None
