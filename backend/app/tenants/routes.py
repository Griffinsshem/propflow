"""Tenant endpoints. Inviting a tenant (POST) places them in a unit on acceptance."""

from __future__ import annotations

import uuid
from typing import Any

from flask import g
from flask_smorest import Blueprint

from app.authz.context import current_org_context
from app.authz.decorators import require_permission
from app.authz.permissions import Permission
from app.common.rate_limit import client_key, limiter
from app.organizations import invitations, members
from app.organizations.models import Invitation, MembershipRole
from app.organizations.schemas import InvitationSchema
from app.tenants import service
from app.tenants.schemas import (
    TenantInviteSchema,
    TenantListQuerySchema,
    TenantPageSchema,
    TenantSchema,
    TenantUpdateSchema,
)

blp = Blueprint(
    "tenants", __name__, url_prefix="/api/v1/tenants", description="Tenants and unit placement."
)


@blp.get("")
@blp.arguments(TenantListQuerySchema, location="query")
@blp.response(200, TenantPageSchema)
@require_permission(Permission.TENANT_READ)
def list_tenants(query: dict[str, Any]) -> dict[str, Any]:
    items, next_cursor = service.list_tenants(
        current_org_context(),
        status=query["status"],
        unit_id=query["unit_id"],
        property_id=query["property_id"],
        limit=query["limit"],
        cursor=query["cursor"],
    )
    return {"items": items, "next_cursor": next_cursor}


@blp.post("")
@limiter.limit("30 per hour", key_func=client_key)
@blp.arguments(TenantInviteSchema)
@blp.response(201, InvitationSchema)
@require_permission(Permission.TENANT_CREATE)
def invite_tenant(payload: dict[str, Any]) -> Invitation:
    return invitations.create(
        current_org_context(),
        g.current_user,
        payload["email"],
        MembershipRole.TENANT,
        unit_id=payload["unit_id"],
    )


@blp.get("/me")
@blp.response(200, TenantSchema)
@require_permission(Permission.UNIT_READ)
def my_tenancy() -> dict[str, Any]:
    return service.my_tenancy(current_org_context())


@blp.get("/<uuid:tenant_id>")
@blp.response(200, TenantSchema)
@require_permission(Permission.TENANT_READ)
def get_tenant(tenant_id: uuid.UUID) -> dict[str, Any]:
    return service.get_tenant(current_org_context(), tenant_id)


@blp.patch("/<uuid:tenant_id>")
@blp.arguments(TenantUpdateSchema)
@blp.response(200, TenantSchema)
@require_permission(Permission.TENANT_UPDATE)
def update_tenant(payload: dict[str, Any], tenant_id: uuid.UUID) -> dict[str, Any]:
    return service.update_tenant(current_org_context(), tenant_id, payload)


@blp.post("/<uuid:tenant_id>/deactivate")
@blp.response(204)
@require_permission(Permission.TENANT_UPDATE)
def deactivate_tenant(tenant_id: uuid.UUID) -> None:
    """Ends access and frees the unit (via the membership deactivation hook)."""
    context = current_org_context()
    members.deactivate(context, service.membership_id_of(context, tenant_id))
