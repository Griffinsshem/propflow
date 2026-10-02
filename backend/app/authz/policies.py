"""Rules about acting on other members, derived from the permission matrix (one source of truth).

Owners may invite/deactivate anyone; managers only tenants and contractors; others nobody.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from app.authz.permissions import Permission, has_permission
from app.organizations.models import MembershipRole

R = MembershipRole

_INVITE_REQUIRES: Mapping[MembershipRole, Permission] = MappingProxyType(
    {
        R.OWNER: Permission.ORGANIZATION_MANAGE_MEMBERS,
        R.MANAGER: Permission.ORGANIZATION_MANAGE_MEMBERS,
        R.TENANT: Permission.TENANT_CREATE,
        R.CONTRACTOR: Permission.CONTRACTOR_CREATE,
    }
)

_DEACTIVATE_REQUIRES: Mapping[MembershipRole, Permission] = MappingProxyType(
    {
        R.OWNER: Permission.ORGANIZATION_MANAGE_MEMBERS,
        R.MANAGER: Permission.ORGANIZATION_MANAGE_MEMBERS,
        R.TENANT: Permission.TENANT_UPDATE,
        R.CONTRACTOR: Permission.CONTRACTOR_UPDATE,
    }
)


def can_invite(actor_role: str, target_role: str) -> bool:
    return has_permission(actor_role, _INVITE_REQUIRES[MembershipRole(target_role)])


def can_deactivate(actor_role: str, target_role: str) -> bool:
    return has_permission(actor_role, _DEACTIVATE_REQUIRES[MembershipRole(target_role)])
