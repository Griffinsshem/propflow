"""Contractor record endpoints (owners and managers)."""

from __future__ import annotations

import uuid
from typing import Any

from flask import g
from flask_smorest import Blueprint

from app.authz.context import current_org_context
from app.authz.decorators import require_permission
from app.authz.permissions import Permission
from app.common.rate_limit import client_key, limiter
from app.contractors import service
from app.contractors.schemas import (
    ContractorCreateSchema,
    ContractorInviteSchema,
    ContractorListQuerySchema,
    ContractorPageSchema,
    ContractorSchema,
    ContractorUpdateSchema,
)
from app.organizations import invitations
from app.organizations.models import Invitation, MembershipRole
from app.organizations.schemas import InvitationSchema

blp = Blueprint(
    "contractors", __name__, url_prefix="/api/v1/contractors", description="Contractor records."
)


@blp.get("")
@blp.arguments(ContractorListQuerySchema, location="query")
@blp.response(200, ContractorPageSchema)
@require_permission(Permission.CONTRACTOR_READ)
def list_contractors(query: dict[str, Any]) -> dict[str, Any]:
    items, next_cursor = service.list_contractors(
        current_org_context(),
        status=query["status"],
        specialty=query["specialty"],
        limit=query["limit"],
        cursor=query["cursor"],
    )
    return {"items": items, "next_cursor": next_cursor}


@blp.post("")
@blp.arguments(ContractorCreateSchema)
@blp.response(201, ContractorSchema)
@require_permission(Permission.CONTRACTOR_CREATE)
def create_contractor(payload: dict[str, Any]) -> dict[str, Any]:
    return service.create_contractor(current_org_context(), payload)


@blp.get("/<uuid:contractor_id>")
@blp.response(200, ContractorSchema)
@require_permission(Permission.CONTRACTOR_READ)
def get_contractor(contractor_id: uuid.UUID) -> dict[str, Any]:
    return service.get_contractor(current_org_context(), contractor_id)


@blp.patch("/<uuid:contractor_id>")
@blp.arguments(ContractorUpdateSchema)
@blp.response(200, ContractorSchema)
@require_permission(Permission.CONTRACTOR_UPDATE)
def update_contractor(payload: dict[str, Any], contractor_id: uuid.UUID) -> dict[str, Any]:
    return service.update_contractor(current_org_context(), contractor_id, payload)


@blp.post("/<uuid:contractor_id>/invite")
@limiter.limit("30 per hour", key_func=client_key)
@blp.arguments(ContractorInviteSchema)
@blp.response(201, InvitationSchema)
@require_permission(Permission.CONTRACTOR_CREATE)
def invite_contractor_login(payload: dict[str, Any], contractor_id: uuid.UUID) -> Invitation:
    """Invites a person to log in as this contractor; acceptance links the login."""
    return invitations.create(
        current_org_context(),
        g.current_user,
        payload["email"],
        MembershipRole.CONTRACTOR,
        contractor_id=contractor_id,
    )
