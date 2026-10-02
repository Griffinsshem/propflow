"""Organizations and the caller's membership in them."""

from __future__ import annotations

import uuid
from typing import Any

from flask import g
from flask_smorest import Blueprint

from app.auth.decorators import login_required
from app.common.rate_limit import client_key, limiter
from app.organizations import service
from app.organizations.schemas import OrganizationSchema, OrganizationWriteSchema

blp = Blueprint(
    "organizations", __name__, url_prefix="/api/v1/organizations", description="Organizations."
)


@blp.get("")
@blp.response(200, OrganizationSchema(many=True))
@login_required
def list_organizations() -> list[dict[str, Any]]:
    return service.list_for_user(g.current_user.id)


@blp.post("")
@limiter.limit("10 per hour", key_func=client_key)
@blp.arguments(OrganizationWriteSchema)
@blp.response(201, OrganizationSchema)
@login_required
def create_organization(payload: dict[str, Any]) -> dict[str, Any]:
    return service.create(g.current_user, g.current_session, payload["name"])


@blp.get("/<uuid:organization_id>")
@blp.response(200, OrganizationSchema)
@login_required
def get_organization(organization_id: uuid.UUID) -> dict[str, Any]:
    return service.get_for_member(g.current_user.id, organization_id)


@blp.patch("/<uuid:organization_id>")
@blp.arguments(OrganizationWriteSchema)
@blp.response(200, OrganizationSchema)
@login_required
def update_organization(payload: dict[str, Any], organization_id: uuid.UUID) -> dict[str, Any]:
    return service.rename(g.current_user.id, organization_id, payload["name"])


@blp.post("/<uuid:organization_id>/activate")
@blp.response(200, OrganizationSchema)
@login_required
def activate_organization(organization_id: uuid.UUID) -> dict[str, Any]:
    return service.activate(g.current_user.id, g.current_session, organization_id)
