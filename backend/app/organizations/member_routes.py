"""Member management endpoints for the active organization."""

from __future__ import annotations

import uuid
from typing import Any

from flask_smorest import Blueprint

from app.authz.context import current_org_context
from app.authz.decorators import require_permission
from app.authz.permissions import Permission
from app.common.pagination import PageQuerySchema
from app.organizations import members
from app.organizations.schemas import MemberPageSchema, MemberRoleUpdateSchema, MemberSchema

blp = Blueprint("members", __name__, url_prefix="/api/v1/members", description="Members.")


@blp.get("")
@blp.arguments(PageQuerySchema, location="query")
@blp.response(200, MemberPageSchema)
@require_permission(Permission.ORGANIZATION_MANAGE_MEMBERS)
def list_members(query: dict[str, Any]) -> dict[str, Any]:
    items, next_cursor = members.list_members(
        current_org_context(), limit=query["limit"], cursor=query["cursor"]
    )
    return {"items": items, "next_cursor": next_cursor}


@blp.patch("/<uuid:membership_id>")
@blp.arguments(MemberRoleUpdateSchema)
@blp.response(200, MemberSchema)
@require_permission(Permission.ORGANIZATION_MANAGE_MEMBERS)
def change_member_role(payload: dict[str, Any], membership_id: uuid.UUID) -> dict[str, Any]:
    return members.change_role(current_org_context(), membership_id, payload["role"])


@blp.post("/<uuid:membership_id>/deactivate")
@blp.response(200, MemberSchema)
@require_permission(Permission.TENANT_UPDATE)  # baseline; can_deactivate refines by target role
def deactivate_member(membership_id: uuid.UUID) -> dict[str, Any]:
    return members.deactivate(current_org_context(), membership_id)
