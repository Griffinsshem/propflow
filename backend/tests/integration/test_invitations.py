from datetime import UTC, datetime, timedelta

from flask import Flask
from sqlalchemy import update

from app.extensions import db
from app.organizations.models import Invitation
from tests.support import (
    INVITATIONS,
    MEMBERS,
    Actor,
    create_organization,
    invite,
    join_via_invitation,
    sign_up,
)

ME = "/api/v1/auth/me"
ACCEPT = f"{INVITATIONS}/accept"
PREVIEW = f"{INVITATIONS}/preview"


def owner_with_org(app: Flask) -> tuple[Actor, str]:
    owner = sign_up(app, "owner@example.com", "Olivia Owner")
    return owner, create_organization(owner, "Riverside Estates")


def test_invited_manager_accepts_and_joins(app: Flask) -> None:
    owner, org_id = owner_with_org(app)
    token = invite(owner, "manager@example.com", "manager")
    message = app.extensions["outbox"][-1]
    assert message.to == "manager@example.com"
    assert "Riverside Estates" in message.subject
    assert "/accept-invite#token=" in message.body
    manager = sign_up(app, "manager@example.com", "Mary Manager")
    response = manager.post(ACCEPT, json={"token": token})
    assert response.status_code == 200
    assert response.get_json()["role"] == "manager"
    me = manager.get(ME).get_json()
    assert me["active_organization_id"] == org_id
    assert me["email_verified"] is True


def test_manager_can_invite_tenants_and_contractors_but_not_staff(app: Flask) -> None:
    owner, _ = owner_with_org(app)
    manager = join_via_invitation(owner, "manager@example.com", "manager")
    for role, expected in [("tenant", 201), ("contractor", 201), ("manager", 403), ("owner", 403)]:
        response = manager.post(INVITATIONS, json={"email": f"{role}@example.com", "role": role})
        assert response.status_code == expected, role


def test_tenants_cannot_invite(app: Flask) -> None:
    owner, _ = owner_with_org(app)
    tenant = join_via_invitation(owner, "tenant@example.com", "tenant")
    response = tenant.post(INVITATIONS, json={"email": "friend@example.com", "role": "tenant"})
    assert response.status_code == 403


def test_invitation_is_bound_to_its_email_address(app: Flask) -> None:
    owner, _ = owner_with_org(app)
    token = invite(owner, "intended@example.com", "tenant")
    intruder = sign_up(app, "intruder@example.com")
    response = intruder.post(ACCEPT, json={"token": token})
    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "INVITATION_EMAIL_MISMATCH"
    intended = sign_up(app, "intended@example.com")
    assert intended.post(ACCEPT, json={"token": token}).status_code == 200


def test_invitation_can_be_accepted_only_once(app: Flask) -> None:
    owner, _ = owner_with_org(app)
    token = invite(owner, "tenant@example.com", "tenant")
    tenant = sign_up(app, "tenant@example.com")
    assert tenant.post(ACCEPT, json={"token": token}).status_code == 200
    second = tenant.post(ACCEPT, json={"token": token})
    assert second.status_code == 400
    assert second.get_json()["error"]["code"] == "INVALID_TOKEN"


def test_reinviting_invalidates_the_previous_link(app: Flask) -> None:
    owner, _ = owner_with_org(app)
    old_token = invite(owner, "tenant@example.com", "tenant")
    new_token = invite(owner, "tenant@example.com", "tenant")
    tenant = sign_up(app, "tenant@example.com")
    assert tenant.post(ACCEPT, json={"token": old_token}).status_code == 400
    assert tenant.post(ACCEPT, json={"token": new_token}).status_code == 200


def test_revoked_invitation_cannot_be_accepted(app: Flask) -> None:
    owner, _ = owner_with_org(app)
    token = invite(owner, "tenant@example.com", "tenant")
    invitation_id = owner.get(INVITATIONS).get_json()["items"][0]["id"]
    assert owner.post(f"{INVITATIONS}/{invitation_id}/revoke").status_code == 200
    tenant = sign_up(app, "tenant@example.com")
    assert tenant.post(ACCEPT, json={"token": token}).status_code == 400


def test_expired_invitation_cannot_be_accepted(app: Flask) -> None:
    owner, _ = owner_with_org(app)
    token = invite(owner, "tenant@example.com", "tenant")
    past = datetime.now(UTC) - timedelta(days=8)
    with app.app_context():
        db.session.execute(
            update(Invitation).values(created_at=past, expires_at=past + timedelta(days=7))
        )
        db.session.commit()
    tenant = sign_up(app, "tenant@example.com")
    assert tenant.post(ACCEPT, json={"token": token}).status_code == 400


def test_active_members_cannot_be_invited_again(app: Flask) -> None:
    owner, _ = owner_with_org(app)
    response = owner.post(INVITATIONS, json={"email": "owner@example.com", "role": "manager"})
    assert response.status_code == 409


def test_preview_describes_the_invitation(app: Flask) -> None:
    owner, _ = owner_with_org(app)
    token = invite(owner, "tenant@example.com", "tenant")
    body = app.test_client().post(PREVIEW, json={"token": token}).get_json()
    assert body["organization_name"] == "Riverside Estates"
    assert body["role"] == "tenant"
    assert body["email"] == "tenant@example.com"


def test_preview_rejects_unknown_tokens(app: Flask) -> None:
    response = app.test_client().post(PREVIEW, json={"token": "x" * 43})
    assert response.status_code == 400


def test_pending_list_excludes_accepted_invitations(app: Flask) -> None:
    owner, _ = owner_with_org(app)
    join_via_invitation(owner, "joined@example.com", "tenant")
    invite(owner, "pending@example.com", "tenant")
    emails = [item["email"] for item in owner.get(INVITATIONS).get_json()["items"]]
    assert emails == ["pending@example.com"]


def test_deactivated_member_can_rejoin_via_new_invitation(app: Flask) -> None:
    owner, _ = owner_with_org(app)
    tenant = join_via_invitation(owner, "tenant@example.com", "tenant")
    members = owner.get(MEMBERS).get_json()["items"]
    membership_id = next(m["id"] for m in members if m["email"] == "tenant@example.com")
    assert owner.post(f"{MEMBERS}/{membership_id}/deactivate").status_code == 200
    token = invite(owner, "tenant@example.com", "contractor")
    response = tenant.post(ACCEPT, json={"token": token})
    assert response.status_code == 200
    assert response.get_json()["role"] == "contractor"
