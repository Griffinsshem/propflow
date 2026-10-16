"""Demo sandboxes (ADR 0021): contents, email and audit guards, restrictions, switching, purge."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from flask import Flask
from sqlalchemy import func, select, text

from app.auth import service as auth_service
from app.auth.models import User, UserSession
from app.authz.context import OrgContext
from app.common.errors import DemoRestrictedError
from app.demo import service as demo
from app.demo.guards import DEMO_EMAIL_DOMAIN
from app.extensions import db
from app.maintenance import attachments
from app.notifications.email import EmailMessage, send_email
from app.organizations import invitations
from app.organizations import service as organizations
from app.organizations.models import MembershipRole, Organization, OrganizationMembership

PASSWORD = "correct horse battery staple"


def _sandbox() -> tuple[Organization, User, UserSession]:
    owner, issued = demo.create_sandbox(ip_address="203.0.113.9", user_agent="pytest")
    organization = db.session.get(Organization, issued.session.active_organization_id)
    assert organization is not None
    return organization, owner, issued.session


def _context(organization: Organization, role: MembershipRole) -> tuple[OrgContext, User]:
    membership, user = db.session.execute(
        select(OrganizationMembership, User)
        .join(User, User.id == OrganizationMembership.user_id)
        .where(
            OrganizationMembership.organization_id == organization.id,
            OrganizationMembership.role == role,
        )
        .limit(1)
    ).one()
    context = OrgContext(
        user_id=user.id, organization_id=organization.id, membership_id=membership.id, role=role
    )
    return context, user


def _count(sql: str, **params: Any) -> int:
    return int(db.session.execute(text(sql), params).scalar_one())


def _real_user() -> tuple[User, UserSession]:
    user, issued = auth_service.register(
        f"real-{uuid.uuid4().hex}@example.com",
        PASSWORD,
        "Real Person",
        ip_address=None,
        user_agent=None,
    )
    return user, issued.session


def test_a_sandbox_is_private_furnished_and_short_lived(app: Flask) -> None:
    with app.test_request_context("/"):
        organization, owner, session = _sandbox()
        assert organization.is_demo and organization.demo_expires_at is not None
        assert session.expires_at == organization.demo_expires_at
        assert owner.full_name == "Demo Owner" and owner.is_demo
        emails = (
            db.session.execute(
                select(User.email)
                .join(OrganizationMembership, OrganizationMembership.user_id == User.id)
                .where(OrganizationMembership.organization_id == organization.id)
            )
            .scalars()
            .all()
        )
        assert len(emails) == 5
        assert all(email.endswith("@" + DEMO_EMAIL_DOMAIN) for email in emails)
        statuses = (
            db.session.execute(
                text("SELECT status FROM maintenance_requests WHERE organization_id = :id"),
                {"id": organization.id},
            )
            .scalars()
            .all()
        )
        assert sorted(statuses) == ["in_progress", "resolved", "submitted"]
        assert (
            _count(
                "SELECT count(*) FROM audit_logs WHERE organization_id = :id", id=organization.id
            )
            == 0
        )


def test_email_to_demo_people_never_leaves(app: Flask, monkeypatch: pytest.MonkeyPatch) -> None:
    dispatched: list[Any] = []
    monkeypatch.setattr("app.worker.dispatch", lambda *args, **kwargs: dispatched.append(args))
    with app.test_request_context("/"):
        send_email(EmailMessage(to=f"someone@{DEMO_EMAIL_DOMAIN}", subject="Hi", body="Hello"))
        send_email(EmailMessage(to="someone@example.com", subject="Hi", body="Hello"))
    assert len(dispatched) == 1


def test_demos_cannot_invite_upload_or_create_organizations(app: Flask) -> None:
    with app.test_request_context("/"):
        organization, owner, session = _sandbox()
        as_owner, _ = _context(organization, MembershipRole.OWNER)
        with pytest.raises(DemoRestrictedError):
            invitations.create(as_owner, owner, "friend@example.com", "manager")
        request_id = db.session.execute(
            text("SELECT id FROM maintenance_requests WHERE organization_id = :id LIMIT 1"),
            {"id": organization.id},
        ).scalar_one()
        with pytest.raises(DemoRestrictedError):
            attachments.start_upload(
                as_owner, request_id, content_type="image/jpeg", size_bytes=1024
            )
        with pytest.raises(DemoRestrictedError):
            organizations.create(owner, session, "Another organization")


def test_view_as_switches_person_inside_the_sandbox_only(app: Flask) -> None:
    with app.test_request_context("/"):
        organization, owner, session = _sandbox()
        tenant, issued = demo.view_as(session, owner, "tenant", ip_address=None, user_agent=None)
        assert tenant.full_name == "Tom Tenant" and tenant.is_demo
        assert issued.session.active_organization_id == organization.id
        assert issued.session.expires_at == organization.demo_expires_at
        assert session.revoked_at is not None
        real, real_session = _real_user()
        with pytest.raises(DemoRestrictedError):
            demo.view_as(real_session, real, "tenant", ip_address=None, user_agent=None)


def test_purge_leaves_no_trace_and_refuses_real_organizations(app: Flask) -> None:
    with app.test_request_context("/"):
        organization, _, _ = _sandbox()
        organization_id = organization.id
        people = (
            db.session.execute(
                select(OrganizationMembership.user_id).where(
                    OrganizationMembership.organization_id == organization_id
                )
            )
            .scalars()
            .all()
        )
        organization.demo_expires_at = datetime.now(UTC) - timedelta(minutes=1)
        db.session.commit()

        assert demo.purge_expired() >= 1
        db.session.expire_all()
        for table in db.metadata.sorted_tables:
            if "organization_id" in table.c:
                remaining = db.session.execute(
                    select(func.count())
                    .select_from(table)
                    .where(table.c.organization_id == organization_id)
                ).scalar_one()
                assert remaining == 0, f"{table.name} still references the purged sandbox"
        assert db.session.get(Organization, organization_id) is None
        assert (
            db.session.execute(
                select(func.count()).select_from(User).where(User.id.in_(people))
            ).scalar_one()
            == 0
        )

        real, real_session = _real_user()
        organizations.create(real, real_session, "Real Estates")
        assert real_session.active_organization_id is not None
        with pytest.raises(RuntimeError):
            demo.purge_sandbox(real_session.active_organization_id)
