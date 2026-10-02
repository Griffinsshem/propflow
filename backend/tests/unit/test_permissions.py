import pytest

from app.authz.permissions import ROLE_PERMISSIONS, Permission, has_permission
from app.organizations.models import MembershipRole

P = Permission


def test_every_role_has_an_explicit_permission_set() -> None:
    assert set(ROLE_PERMISSIONS) == set(MembershipRole)


def test_owner_holds_every_permission() -> None:
    assert ROLE_PERMISSIONS[MembershipRole.OWNER] == frozenset(Permission)


@pytest.mark.parametrize(
    "permission",
    [
        P.ORGANIZATION_UPDATE,
        P.ORGANIZATION_MANAGE_MEMBERS,
        P.AUDIT_READ,
        P.PROPERTY_CREATE,
        P.PROPERTY_UPDATE,
        P.PROPERTY_DELETE,
    ],
)
def test_manager_cannot_perform_owner_only_actions(permission: Permission) -> None:
    assert not has_permission(MembershipRole.MANAGER, permission)


@pytest.mark.parametrize("role", [MembershipRole.TENANT, MembershipRole.CONTRACTOR])
@pytest.mark.parametrize(
    "permission",
    [
        P.PROPERTY_CREATE,
        P.TENANT_READ,
        P.MAINTENANCE_ASSIGN,
        P.WORKORDER_ASSIGN,
        P.AUDIT_READ,
        P.ORGANIZATION_MANAGE_MEMBERS,
    ],
)
def test_tenants_and_contractors_cannot_manage(
    role: MembershipRole, permission: Permission
) -> None:
    assert not has_permission(role, permission)


def test_contractor_permissions_are_limited_to_work_orders() -> None:
    assert ROLE_PERMISSIONS[MembershipRole.CONTRACTOR] == {
        P.ORGANIZATION_READ,
        P.WORKORDER_READ,
        P.WORKORDER_UPDATE,
        P.MAINTENANCE_COMMENT,
    }


def test_unknown_role_has_no_permissions() -> None:
    assert not has_permission("superuser", Permission.PROPERTY_READ)
