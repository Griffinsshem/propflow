import uuid

import pytest
from flask import Flask
from sqlalchemy import update

from app.extensions import db
from app.organizations.models import OrganizationMembership
from tests.support import ORGS, activate, add_member, create_organization, sign_up

ME = "/api/v1/auth/me"
AUDIT = "/api/v1/audit-log"


def test_creating_an_organization_makes_caller_owner_and_activates_it(app: Flask) -> None:
    owner = sign_up(app, "owner@example.com")
    response = owner.post(ORGS, json={"name": "Kilimani Heights Ltd"})
    assert response.status_code == 201
    org = response.get_json()
    assert org["role"] == "owner" and org["status"] == "active"
    me = owner.get(ME).get_json()
    assert me["active_organization_id"] == org["id"]
    assert me["memberships"] == [
        {"organization_id": org["id"], "organization_name": "Kilimani Heights Ltd", "role": "owner"}
    ]


def test_list_shows_only_the_callers_organizations(app: Flask) -> None:
    a, b = sign_up(app, "a@example.com"), sign_up(app, "b@example.com")
    create_organization(a, "A Properties")
    create_organization(b, "B Properties")
    assert [org["name"] for org in a.get(ORGS).get_json()] == ["A Properties"]


def test_owner_can_rename_organization(app: Flask) -> None:
    owner = sign_up(app, "owner@example.com")
    org_id = create_organization(owner, "Old Name")
    response = owner.patch(f"{ORGS}/{org_id}", json={"name": "New Name"})
    assert response.status_code == 200
    assert response.get_json()["name"] == "New Name"


@pytest.mark.parametrize("role", ["manager", "tenant", "contractor"])
def test_non_owners_cannot_rename_organization(app: Flask, role: str) -> None:
    owner = sign_up(app, "owner@example.com")
    org_id = create_organization(owner, "Original Name")
    member = sign_up(app, "member@example.com")
    add_member(app, org_id, member, role)
    assert member.patch(f"{ORGS}/{org_id}", json={"name": "Hijacked"}).status_code == 403
    assert owner.get(f"{ORGS}/{org_id}").get_json()["name"] == "Original Name"


def test_clients_cannot_set_organization_status(app: Flask) -> None:
    owner = sign_up(app, "owner@example.com")
    org_id = create_organization(owner, "Org")
    response = owner.patch(f"{ORGS}/{org_id}", json={"name": "Org", "status": "suspended"})
    assert response.status_code == 422


def test_blank_name_is_rejected(app: Flask) -> None:
    owner = sign_up(app, "owner@example.com")
    assert owner.post(ORGS, json={"name": "   "}).status_code == 422


def test_user_can_switch_between_their_organizations(app: Flask) -> None:
    user = sign_up(app, "multi@example.com")
    first = create_organization(user, "First")
    create_organization(user, "Second")
    activate(user, first)
    assert user.get(ME).get_json()["active_organization_id"] == first


def test_deactivated_membership_loses_access_immediately(app: Flask) -> None:
    owner = sign_up(app, "owner@example.com")
    org_id = create_organization(owner, "Org")
    member = sign_up(app, "manager@example.com")
    add_member(app, org_id, member, "manager")
    activate(member, org_id)
    assert member.get(f"{ORGS}/{org_id}").status_code == 200
    with app.app_context():
        db.session.execute(
            update(OrganizationMembership)
            .where(OrganizationMembership.user_id == uuid.UUID(member.user_id))
            .values(status="deactivated")
        )
        db.session.commit()
    assert member.get(f"{ORGS}/{org_id}").status_code == 404


def test_org_scoped_endpoints_require_an_active_organization(app: Flask) -> None:
    user = sign_up(app, "loner@example.com")
    response = user.get(AUDIT)
    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "ORGANIZATION_CONTEXT_REQUIRED"
