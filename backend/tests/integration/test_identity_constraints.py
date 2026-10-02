"""The database must reject invalid data even if application code has a bug."""

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from flask import Flask
from sqlalchemy.exc import IntegrityError

from app.auth.models import User, UserSession
from app.extensions import db
from app.organizations.models import (
    Invitation,
    MembershipRole,
    Organization,
    OrganizationMembership,
)


@pytest.fixture()
def ctx(app: Flask) -> Iterator[None]:
    with app.app_context():
        yield
        db.session.rollback()


def make_user(email: str = "person@example.com") -> User:
    user = User(email=email, password_hash="not-a-real-hash", full_name="Test Person")
    db.session.add(user)
    db.session.flush()
    return user


def make_org(name: str = "Test Properties Ltd") -> Organization:
    org = Organization(name=name)
    db.session.add(org)
    db.session.flush()
    return org


def make_membership(org: Organization, user: User, role: str = "manager") -> None:
    db.session.add(OrganizationMembership(organization_id=org.id, user_id=user.id, role=role))
    db.session.flush()


def token_hash() -> str:
    return uuid.uuid4().hex * 2  # 64 hex characters


def make_invitation(org: Organization, inviter: User, **overrides: Any) -> Invitation:
    fields: dict[str, Any] = {
        "organization_id": org.id,
        "email": "invitee@example.com",
        "role": MembershipRole.TENANT,
        "token_hash": token_hash(),
        "invited_by_user_id": inviter.id,
        "expires_at": datetime.now(UTC) + timedelta(days=7),
    }
    invitation = Invitation(**(fields | overrides))
    db.session.add(invitation)
    db.session.flush()
    return invitation


@pytest.mark.usefixtures("ctx")
class TestUserConstraints:
    def test_email_is_unique(self) -> None:
        make_user("dup@example.com")
        with pytest.raises(IntegrityError):
            make_user("dup@example.com")

    def test_email_must_be_lowercase(self) -> None:
        with pytest.raises(IntegrityError):
            make_user("Mixed@Example.com")

    def test_user_with_memberships_cannot_be_hard_deleted(self) -> None:
        user = make_user()
        make_membership(make_org(), user)
        db.session.delete(user)
        with pytest.raises(IntegrityError):
            db.session.flush()


@pytest.mark.usefixtures("ctx")
class TestMembershipConstraints:
    def test_one_membership_per_user_per_organization(self) -> None:
        org, user = make_org(), make_user()
        make_membership(org, user, "manager")
        with pytest.raises(IntegrityError):
            make_membership(org, user, "tenant")

    def test_role_must_be_known(self) -> None:
        with pytest.raises(IntegrityError):
            make_membership(make_org(), make_user(), "superuser")

    def test_organization_must_exist(self) -> None:
        user = make_user()
        db.session.add(
            OrganizationMembership(organization_id=uuid.uuid4(), user_id=user.id, role="manager")
        )
        with pytest.raises(IntegrityError):
            db.session.flush()

    def test_same_user_can_belong_to_two_organizations(self) -> None:
        user = make_user()
        make_membership(make_org("Org A"), user, "manager")
        make_membership(make_org("Org B"), user, "tenant")


@pytest.mark.usefixtures("ctx")
class TestInvitationConstraints:
    def test_only_one_pending_invitation_per_email(self) -> None:
        org, inviter = make_org(), make_user()
        make_invitation(org, inviter)
        with pytest.raises(IntegrityError):
            make_invitation(org, inviter)

    def test_revoked_invitation_allows_reinvite(self) -> None:
        org, inviter = make_org(), make_user()
        make_invitation(org, inviter, revoked_at=datetime.now(UTC))
        make_invitation(org, inviter)

    def test_cannot_be_both_accepted_and_revoked(self) -> None:
        org, inviter = make_org(), make_user()
        now = datetime.now(UTC)
        with pytest.raises(IntegrityError):
            make_invitation(
                org, inviter, accepted_at=now, accepted_by_user_id=inviter.id, revoked_at=now
            )


@pytest.mark.usefixtures("ctx")
class TestSessionConstraints:
    def test_session_must_expire_after_creation(self) -> None:
        user = make_user()
        db.session.add(
            UserSession(
                user_id=user.id,
                token_hash=token_hash(),
                expires_at=datetime.now(UTC) - timedelta(hours=1),
            )
        )
        with pytest.raises(IntegrityError):
            db.session.flush()

    def test_token_hash_is_unique(self) -> None:
        user = make_user()
        shared = token_hash()
        expires = datetime.now(UTC) + timedelta(days=1)
        db.session.add(UserSession(user_id=user.id, token_hash=shared, expires_at=expires))
        db.session.flush()
        db.session.add(UserSession(user_id=user.id, token_hash=shared, expires_at=expires))
        with pytest.raises(IntegrityError):
            db.session.flush()
