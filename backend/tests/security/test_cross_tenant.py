"""Mandatory cross-tenant suite (spec section 54). Every new org-owned resource adds cases here."""

import uuid

import pytest
from sqlalchemy import update

from app.auth.models import UserSession
from app.extensions import db
from tests.support import INVITATIONS, MEMBERS, ORGS, TwoOrgs, invite, join_via_invitation

ME = "/api/v1/auth/me"
AUDIT = "/api/v1/audit-log"


def _b_owner_membership_id(two_orgs: TwoOrgs) -> str:
    return str(two_orgs.b_owner.get(MEMBERS).get_json()["items"][0]["id"])


def test_cannot_read_another_organization(two_orgs: TwoOrgs) -> None:
    assert two_orgs.a_owner.get(f"{ORGS}/{two_orgs.org_b}").status_code == 404


def test_foreign_and_nonexistent_organizations_are_indistinguishable(two_orgs: TwoOrgs) -> None:
    foreign = two_orgs.a_owner.get(f"{ORGS}/{two_orgs.org_b}")
    missing = two_orgs.a_owner.get(f"{ORGS}/{uuid.uuid4()}")
    assert foreign.status_code == missing.status_code == 404
    foreign_error, missing_error = foreign.get_json()["error"], missing.get_json()["error"]
    assert foreign_error["code"] == missing_error["code"]
    assert foreign_error["message"] == missing_error["message"]


def test_cannot_rename_another_organization(two_orgs: TwoOrgs) -> None:
    response = two_orgs.a_owner.patch(f"{ORGS}/{two_orgs.org_b}", json={"name": "Pwned"})
    assert response.status_code == 404
    assert two_orgs.b_owner.get(f"{ORGS}/{two_orgs.org_b}").get_json()["name"] == "Org B"


def test_cannot_switch_into_another_organization(two_orgs: TwoOrgs) -> None:
    assert two_orgs.a_owner.post(f"{ORGS}/{two_orgs.org_b}/activate").status_code == 404
    assert two_orgs.a_owner.get(ME).get_json()["active_organization_id"] == two_orgs.org_a


def test_audit_log_shows_only_own_organization(two_orgs: TwoOrgs) -> None:
    items = two_orgs.a_owner.get(AUDIT).get_json()["items"]
    assert items
    assert {item["resource_id"] for item in items} == {two_orgs.org_a}


def test_session_pointing_at_foreign_org_is_still_rejected(two_orgs: TwoOrgs) -> None:
    """Defense in depth: even if a bug wrote a foreign org into a session, membership wins."""
    with two_orgs.app.app_context():
        db.session.execute(
            update(UserSession)
            .where(UserSession.user_id == uuid.UUID(two_orgs.a_owner.user_id))
            .values(active_organization_id=uuid.UUID(two_orgs.org_b))
        )
        db.session.commit()
    response = two_orgs.a_owner.get(AUDIT)
    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "ORGANIZATION_CONTEXT_REQUIRED"


def test_member_lists_do_not_leak_across_organizations(two_orgs: TwoOrgs) -> None:
    emails = {m["email"] for m in two_orgs.a_owner.get(MEMBERS).get_json()["items"]}
    assert emails == {"owner.a@example.com"}


def test_cannot_change_role_in_another_organization(two_orgs: TwoOrgs) -> None:
    target = _b_owner_membership_id(two_orgs)
    response = two_orgs.a_owner.patch(f"{MEMBERS}/{target}", json={"role": "tenant"})
    assert response.status_code == 404
    assert two_orgs.b_owner.get(MEMBERS).get_json()["items"][0]["role"] == "owner"


def test_cannot_deactivate_member_of_another_organization(two_orgs: TwoOrgs) -> None:
    target = _b_owner_membership_id(two_orgs)
    assert two_orgs.a_owner.post(f"{MEMBERS}/{target}/deactivate").status_code == 404
    assert two_orgs.b_owner.get(MEMBERS).get_json()["items"][0]["status"] == "active"


def test_invitation_lists_do_not_leak_across_organizations(two_orgs: TwoOrgs) -> None:
    invite(two_orgs.b_owner, "someone@example.com", "tenant")
    assert two_orgs.a_owner.get(INVITATIONS).get_json()["items"] == []


def test_cannot_revoke_another_organizations_invitation(two_orgs: TwoOrgs) -> None:
    invite(two_orgs.b_owner, "someone@example.com", "tenant")
    target = two_orgs.b_owner.get(INVITATIONS).get_json()["items"][0]["id"]
    assert two_orgs.a_owner.post(f"{INVITATIONS}/{target}/revoke").status_code == 404
    assert len(two_orgs.b_owner.get(INVITATIONS).get_json()["items"]) == 1


@pytest.mark.parametrize("role", ["manager", "tenant", "contractor"])
def test_every_role_is_isolated_from_other_organizations(two_orgs: TwoOrgs, role: str) -> None:
    member = join_via_invitation(two_orgs.a_owner, f"{role}@example.com", role)
    assert member.get(f"{ORGS}/{two_orgs.org_b}").status_code == 404
    assert member.patch(f"{ORGS}/{two_orgs.org_b}", json={"name": "Pwned"}).status_code == 404
    assert member.post(f"{ORGS}/{two_orgs.org_b}/activate").status_code == 404
