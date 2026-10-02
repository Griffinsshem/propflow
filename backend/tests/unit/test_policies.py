import pytest

from app.authz.policies import can_deactivate, can_invite
from app.organizations.models import MembershipRole as R

ALL_ROLES = list(R)


@pytest.mark.parametrize("target", ALL_ROLES)
def test_owner_can_invite_and_deactivate_every_role(target: R) -> None:
    assert can_invite(R.OWNER, target)
    assert can_deactivate(R.OWNER, target)


@pytest.mark.parametrize(
    ("target", "allowed"),
    [(R.OWNER, False), (R.MANAGER, False), (R.TENANT, True), (R.CONTRACTOR, True)],
)
def test_manager_can_only_manage_tenants_and_contractors(target: R, allowed: bool) -> None:
    assert can_invite(R.MANAGER, target) is allowed
    assert can_deactivate(R.MANAGER, target) is allowed


@pytest.mark.parametrize("actor", [R.TENANT, R.CONTRACTOR])
@pytest.mark.parametrize("target", ALL_ROLES)
def test_tenants_and_contractors_manage_nobody(actor: R, target: R) -> None:
    assert not can_invite(actor, target)
    assert not can_deactivate(actor, target)
