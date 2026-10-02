"""Invitation use cases: invite, list, revoke, preview and accept."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from app.audit import service as audit
from app.auth import repository as auth_repository
from app.auth.models import User, UserSession
from app.auth.recovery import InvalidTokenError
from app.auth.service import normalize_email
from app.auth.tokens import generate_token, hash_token
from app.authz.context import OrgContext
from app.authz.policies import can_invite
from app.common.errors import (
    ConflictError,
    InvitationEmailMismatchError,
    NotFoundError,
    PermissionDeniedError,
)
from app.common.links import frontend_link
from app.common.pagination import paginate
from app.extensions import db
from app.notifications.email import EmailMessage, send_email
from app.organizations import repository
from app.organizations.models import (
    Invitation,
    MembershipRole,
    MembershipStatus,
    OrganizationMembership,
    OrganizationStatus,
)
from app.organizations.service import organization_view

INVITATION_TTL = timedelta(days=7)
MAX_TOKEN_LENGTH = 128


def _now() -> datetime:
    return datetime.now(UTC)


def create(context: OrgContext, inviter: User, email: str, role: str) -> Invitation:
    target_role = MembershipRole(role)
    if not can_invite(context.role, target_role):
        raise PermissionDeniedError()
    email = normalize_email(email)
    existing_user = auth_repository.get_user_by_email(email)
    if existing_user is not None and repository.get_active_membership(
        existing_user.id, context.organization_id
    ):
        raise ConflictError("This person is already an active member of the organization.")
    organization = repository.get_organization(context.organization_id)
    if organization is None:
        raise NotFoundError()

    now = _now()
    # Re-inviting replaces any pending link (the partial unique index allows only one).
    repository.revoke_pending_invitations(context.organization_id, email, now)
    token = generate_token()
    invitation = Invitation(
        organization_id=context.organization_id,
        email=email,
        role=target_role,
        token_hash=hash_token(token),
        invited_by_user_id=inviter.id,
        created_at=now,
        expires_at=now + INVITATION_TTL,
    )
    db.session.add(invitation)
    db.session.flush()
    audit.record(
        "invitation.created",
        "invitation",
        invitation.id,
        organization_id=context.organization_id,
        details={"email": email, "role": target_role.value},
    )
    organization_name, inviter_name = organization.name, inviter.full_name
    db.session.commit()

    # Only after commit: never email a link for an invitation that rolled back.
    send_email(
        EmailMessage(
            to=email,
            subject=f"You're invited to join {organization_name} on PropFlow",
            body=(
                f"{inviter_name} invited you to join {organization_name} on PropFlow "
                f"as a {target_role.value}.\n\n"
                f"Accept the invitation:\n{frontend_link('/accept-invite', token)}\n\n"
                f"This invitation expires in {INVITATION_TTL.days} days."
            ),
        )
    )
    return invitation


def list_pending(
    context: OrgContext, *, limit: int, cursor: str | None
) -> tuple[list[Invitation], str | None]:
    return paginate(
        repository.pending_invitations_query(context.organization_id, _now()),
        created_column=Invitation.created_at,
        id_column=Invitation.id,
        limit=limit,
        cursor=cursor,
    )


def revoke(context: OrgContext, invitation_id: uuid.UUID) -> Invitation:
    invitation = repository.get_invitation(context.organization_id, invitation_id)
    if invitation is None:
        raise NotFoundError()
    if not can_invite(context.role, invitation.role):
        raise PermissionDeniedError()
    if invitation.accepted_at is not None or invitation.revoked_at is not None:
        raise ConflictError("This invitation is no longer pending.")
    invitation.revoked_at = _now()
    audit.record(
        "invitation.revoked",
        "invitation",
        invitation.id,
        organization_id=context.organization_id,
        details={"email": invitation.email, "role": invitation.role},
    )
    db.session.commit()
    return invitation


def _pending_by_token(token: str, *, lock: bool = False) -> Invitation:
    if not token or len(token) > MAX_TOKEN_LENGTH:
        raise InvalidTokenError()
    invitation = repository.get_invitation_by_token_hash(hash_token(token), lock=lock)
    if (
        invitation is None
        or invitation.accepted_at is not None
        or invitation.revoked_at is not None
        or invitation.expires_at <= _now()
    ):
        raise InvalidTokenError()
    return invitation


def preview(token: str) -> dict[str, Any]:
    invitation = _pending_by_token(token)
    organization = repository.get_organization(invitation.organization_id)
    if organization is None or organization.status != OrganizationStatus.ACTIVE:
        raise InvalidTokenError()
    return {
        "organization_name": organization.name,
        "role": invitation.role,
        "email": invitation.email,
        "expires_at": invitation.expires_at,
    }


def accept(user: User, session: UserSession, token: str) -> dict[str, Any]:
    # Row lock: two concurrent accepts of the same token are serialized; the second fails.
    invitation = _pending_by_token(token, lock=True)
    if user.email != invitation.email:
        raise InvitationEmailMismatchError()
    organization = repository.lock_organization(invitation.organization_id)
    if organization is None or organization.status != OrganizationStatus.ACTIVE:
        raise InvalidTokenError()

    now = _now()
    membership = repository.get_membership(user.id, organization.id)
    if membership is not None and membership.status == MembershipStatus.ACTIVE:
        raise ConflictError("You are already a member of this organization.")
    if membership is None:
        membership = OrganizationMembership(
            organization_id=organization.id, user_id=user.id, role=invitation.role
        )
        db.session.add(membership)
    else:  # former member rejoining
        membership.role = invitation.role
        membership.status = MembershipStatus.ACTIVE
    db.session.flush()

    invitation.accepted_at = now
    invitation.accepted_by_user_id = user.id
    if user.email_verified_at is None:
        user.email_verified_at = now  # the token was delivered to this mailbox
    session.active_organization_id = organization.id
    audit.record(
        "invitation.accepted",
        "invitation",
        invitation.id,
        organization_id=organization.id,
        details={"role": invitation.role, "membership_id": str(membership.id)},
    )
    role = invitation.role
    db.session.commit()
    return organization_view(organization, role)
