import pytest
from flask import Flask

from tests.support import MEMBERS, ORGS, Actor, create_organization, join_via_invitation, sign_up

AUDIT = "/api/v1/audit-log"


def owner_with_org(app: Flask) -> tuple[Actor, str]:
    owner = sign_up(app, "owner@example.com", "Olivia Owner")
    return owner, create_organization(owner, "Riverside Estates")


def membership_id(viewer: Actor, email: str) -> str:
    items = viewer.get(MEMBERS).get_json()["items"]
    return str(next(member["id"] for member in items if member["email"] == email))


def test_owner_lists_members_with_roles(app: Flask) -> None:
    owner, _ = owner_with_org(app)
    join_via_invitation(owner, "manager@example.com", "manager", "Mary Manager")
    items = owner.get(MEMBERS).get_json()["items"]
    assert {(m["email"], m["role"]) for m in items} == {
        ("owner@example.com", "owner"),
        ("manager@example.com", "manager"),
    }


def test_member_list_is_owner_only(app: Flask) -> None:
    owner, _ = owner_with_org(app)
    manager = join_via_invitation(owner, "manager@example.com", "manager")
    assert manager.get(MEMBERS).status_code == 403


def test_owner_can_change_a_members_role_and_it_is_audited(app: Flask) -> None:
    owner, _ = owner_with_org(app)
    join_via_invitation(owner, "manager@example.com", "manager")
    target = membership_id(owner, "manager@example.com")
    response = owner.patch(f"{MEMBERS}/{target}", json={"role": "tenant"})
    assert response.status_code == 200
    assert response.get_json()["role"] == "tenant"
    actions = [item["action"] for item in owner.get(AUDIT).get_json()["items"]]
    assert "membership.role_changed" in actions


def test_last_owner_cannot_be_demoted(app: Flask) -> None:
    owner, _ = owner_with_org(app)
    target = membership_id(owner, "owner@example.com")
    response = owner.patch(f"{MEMBERS}/{target}", json={"role": "manager"})
    assert response.status_code == 409


def test_one_of_two_owners_can_step_down_but_not_both(app: Flask) -> None:
    owner, _ = owner_with_org(app)
    second = join_via_invitation(owner, "second@example.com", "owner")
    first_id = membership_id(owner, "owner@example.com")
    assert owner.patch(f"{MEMBERS}/{first_id}", json={"role": "manager"}).status_code == 200
    second_id = membership_id(second, "second@example.com")
    assert second.patch(f"{MEMBERS}/{second_id}", json={"role": "manager"}).status_code == 409


def test_manager_can_deactivate_a_tenant_who_then_loses_access(app: Flask) -> None:
    owner, org_id = owner_with_org(app)
    manager = join_via_invitation(owner, "manager@example.com", "manager")
    tenant = join_via_invitation(owner, "tenant@example.com", "tenant")
    target = membership_id(owner, "tenant@example.com")
    response = manager.post(f"{MEMBERS}/{target}/deactivate")
    assert response.status_code == 200
    assert response.get_json()["status"] == "deactivated"
    assert tenant.get(f"{ORGS}/{org_id}").status_code == 404


@pytest.mark.parametrize("target_role", ["owner", "manager"])
def test_manager_cannot_deactivate_staff(app: Flask, target_role: str) -> None:
    owner, _ = owner_with_org(app)
    manager = join_via_invitation(owner, "manager@example.com", "manager")
    join_via_invitation(owner, "staff@example.com", target_role)
    target = membership_id(owner, "staff@example.com")
    assert manager.post(f"{MEMBERS}/{target}/deactivate").status_code == 403


def test_last_owner_cannot_be_deactivated(app: Flask) -> None:
    owner, _ = owner_with_org(app)
    target = membership_id(owner, "owner@example.com")
    assert owner.post(f"{MEMBERS}/{target}/deactivate").status_code == 409


def test_deactivation_is_idempotent(app: Flask) -> None:
    owner, _ = owner_with_org(app)
    join_via_invitation(owner, "tenant@example.com", "tenant")
    target = membership_id(owner, "tenant@example.com")
    assert owner.post(f"{MEMBERS}/{target}/deactivate").status_code == 200
    assert owner.post(f"{MEMBERS}/{target}/deactivate").status_code == 200


def test_tenants_cannot_deactivate_members(app: Flask) -> None:
    owner, _ = owner_with_org(app)
    tenant = join_via_invitation(owner, "tenant@example.com", "tenant")
    join_via_invitation(owner, "neighbour@example.com", "tenant")
    target = membership_id(owner, "neighbour@example.com")
    assert tenant.post(f"{MEMBERS}/{target}/deactivate").status_code == 403
