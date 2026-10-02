"""Resolves the caller's organization context from the server-side session, never from input."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import cast

import structlog
from flask import g

from app.common.errors import AuthenticationError, OrganizationContextError
from app.organizations import repository
from app.organizations.models import MembershipRole


@dataclass(frozen=True)
class OrgContext:
    user_id: uuid.UUID
    organization_id: uuid.UUID
    membership_id: uuid.UUID
    role: MembershipRole


def current_org_context() -> OrgContext:
    cached = g.get("org_context")
    if cached is not None:
        return cast(OrgContext, cached)
    user = g.get("current_user")
    session = g.get("current_session")
    if user is None or session is None:
        raise AuthenticationError()
    organization_id = session.active_organization_id
    if organization_id is None:
        raise OrganizationContextError()
    # Re-verified on every request: removed members and suspended orgs lose access at once.
    membership = repository.get_active_membership(user.id, organization_id)
    if membership is None:
        raise OrganizationContextError()
    context = OrgContext(
        user_id=user.id,
        organization_id=organization_id,
        membership_id=membership.id,
        role=MembershipRole(membership.role),
    )
    g.org_context = context
    structlog.contextvars.bind_contextvars(organization_id=str(organization_id))
    return context
