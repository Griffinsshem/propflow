"""The single source of truth for what each role may do (spec: MVP roles, section 3.1).

Role-level permissions answer "may this role perform this kind of action?". Which specific
records a user may touch (own requests, assigned properties, assigned work orders) is
enforced separately by scoped queries in each feature module.
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum
from types import MappingProxyType

from app.organizations.models import MembershipRole


class Permission(StrEnum):
    ORGANIZATION_READ = "organization.read"
    ORGANIZATION_UPDATE = "organization.update"
    ORGANIZATION_MANAGE_MEMBERS = "organization.manage_members"
    AUDIT_READ = "audit.read"

    PROPERTY_READ = "property.read"
    PROPERTY_CREATE = "property.create"
    PROPERTY_UPDATE = "property.update"
    PROPERTY_DELETE = "property.delete"

    UNIT_READ = "unit.read"
    UNIT_CREATE = "unit.create"
    UNIT_UPDATE = "unit.update"

    TENANT_READ = "tenant.read"
    TENANT_CREATE = "tenant.create"
    TENANT_UPDATE = "tenant.update"

    CONTRACTOR_READ = "contractor.read"
    CONTRACTOR_CREATE = "contractor.create"
    CONTRACTOR_UPDATE = "contractor.update"

    MAINTENANCE_CREATE = "maintenance.create"
    MAINTENANCE_READ = "maintenance.read"
    MAINTENANCE_UPDATE = "maintenance.update"
    MAINTENANCE_ASSIGN = "maintenance.assign"
    MAINTENANCE_CLOSE = "maintenance.close"
    MAINTENANCE_COMMENT = "maintenance.comment"

    WORKORDER_CREATE = "workorder.create"
    WORKORDER_READ = "workorder.read"
    WORKORDER_ASSIGN = "workorder.assign"
    WORKORDER_UPDATE = "workorder.update"


P = Permission

_OWNER = frozenset(Permission)

_MANAGER = frozenset(Permission) - {
    P.ORGANIZATION_UPDATE,
    P.ORGANIZATION_MANAGE_MEMBERS,
    P.AUDIT_READ,
    P.PROPERTY_CREATE,
    P.PROPERTY_UPDATE,
    P.PROPERTY_DELETE,
}

_TENANT = frozenset(
    {
        P.ORGANIZATION_READ,
        P.UNIT_READ,
        P.MAINTENANCE_CREATE,
        P.MAINTENANCE_READ,
        P.MAINTENANCE_COMMENT,
    }
)

_CONTRACTOR = frozenset(
    {
        P.ORGANIZATION_READ,
        P.WORKORDER_READ,
        P.WORKORDER_UPDATE,
        P.MAINTENANCE_COMMENT,
    }
)

ROLE_PERMISSIONS: Mapping[MembershipRole, frozenset[Permission]] = MappingProxyType(
    {
        MembershipRole.OWNER: _OWNER,
        MembershipRole.MANAGER: _MANAGER,
        MembershipRole.TENANT: _TENANT,
        MembershipRole.CONTRACTOR: _CONTRACTOR,
    }
)


def has_permission(role: str, permission: Permission) -> bool:
    try:
        return permission in ROLE_PERMISSIONS[MembershipRole(role)]
    except ValueError:
        return False  # unknown role: deny
