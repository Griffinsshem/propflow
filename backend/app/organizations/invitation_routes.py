"""Invitation endpoints.

TENANT_CREATE (owners and managers) is the baseline for managing invitations;
app.authz.policies.can_invite then restricts which roles each may invite or revoke.
"""

from __future__ import annotations

import uuid
from typing import Any

from flask import g
from flask_smorest import Blueprint

from app.auth.decorators import login_required
from app.authz.context import current_org_context
from app.authz.decorators import require_permission
from app.authz.permissions import Permission
from app.common.pagination import PageQuerySchema
from app.common.rate_limit import client_key, ip_key, limiter
from app.organizations import invitations
from app.organizations.models import Invitation
from app.organizations.schemas import (
    InvitationCreateSchema,
    InvitationPageSchema,
    InvitationPreviewSchema,
    InvitationSchema,
    InvitationTokenSchema,
    OrganizationSchema,
)

blp = Blueprint(
    "invitations", __name__, url_prefix="/api/v1/invitations", description="Invitations."
)


@blp.get("")
@blp.arguments(PageQuerySchema, location="query")
@blp.response(200, InvitationPageSchema)
@require_permission(Permission.TENANT_CREATE)
def list_invitations(query: dict[str, Any]) -> dict[str, Any]:
    items, next_cursor = invitations.list_pending(
        current_org_context(), limit=query["limit"], cursor=query["cursor"]
    )
    return {"items": items, "next_cursor": next_cursor}


@blp.post("")
@limiter.limit("30 per hour", key_func=client_key)
@blp.arguments(InvitationCreateSchema)
@blp.response(201, InvitationSchema)
@require_permission(Permission.TENANT_CREATE)
def create_invitation(payload: dict[str, Any]) -> Invitation:
    return invitations.create(
        current_org_context(), g.current_user, payload["email"], payload["role"]
    )


@blp.post("/<uuid:invitation_id>/revoke")
@blp.response(200, InvitationSchema)
@require_permission(Permission.TENANT_CREATE)
def revoke_invitation(invitation_id: uuid.UUID) -> Invitation:
    return invitations.revoke(current_org_context(), invitation_id)


@blp.post("/preview")
@limiter.limit("30 per hour", key_func=ip_key)
@blp.arguments(InvitationTokenSchema)
@blp.response(200, InvitationPreviewSchema)
def preview_invitation(payload: dict[str, Any]) -> dict[str, Any]:
    return invitations.preview(payload["token"])


@blp.post("/accept")
@limiter.limit("20 per hour", key_func=client_key)
@blp.arguments(InvitationTokenSchema)
@blp.response(200, OrganizationSchema)
@login_required
def accept_invitation(payload: dict[str, Any]) -> dict[str, Any]:
    return invitations.accept(g.current_user, g.current_session, payload["token"])
