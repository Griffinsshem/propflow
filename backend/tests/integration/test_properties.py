import pytest
from flask import Flask

from tests.support import (
    PROPERTIES,
    Actor,
    assign_manager,
    create_organization,
    create_property,
    create_unit,
    join_via_invitation,
    membership_id_of,
    sign_up,
)

AUDIT = "/api/v1/audit-log"
VALID = {
    "name": "Riverside Court",
    "property_type": "residential",
    "address_line": "12 Riverside Drive",
    "city": "Nairobi",
}


def owner_with_org(app: Flask) -> Actor:
    owner = sign_up(app, "owner@example.com", "Olivia Owner")
    create_organization(owner, "Riverside Estates")
    return owner


def manager_of(owner: Actor) -> tuple[Actor, str]:
    manager = join_via_invitation(owner, "manager@example.com", "manager", "Mary Manager")
    return manager, membership_id_of(owner, "manager@example.com")


def test_owner_creates_property_with_defaults_and_audit(app: Flask) -> None:
    owner = owner_with_org(app)
    prop = create_property(owner)
    assert prop["status"] == "active"
    assert prop["country_code"] == "KE"
    assert prop["version"] == 1
    actions = [item["action"] for item in owner.get(AUDIT).get_json()["items"]]
    assert "property.created" in actions


@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"name": "  "}, "name"),
        ({"property_type": "castle"}, "property_type"),
        ({"country_code": "Kenya"}, "country_code"),
        ({"organization_id": "00000000-0000-0000-0000-000000000000"}, "organization_id"),
        ({"status": "archived"}, "status"),
    ],
)
def test_invalid_or_server_controlled_fields_are_rejected(
    app: Flask, overrides: dict[str, str], field: str
) -> None:
    owner = owner_with_org(app)
    response = owner.post(PROPERTIES, json=VALID | overrides)
    assert response.status_code == 422
    assert field in response.get_json()["error"]["details"]["json"]


def test_managers_see_only_assigned_properties(app: Flask) -> None:
    owner = owner_with_org(app)
    assigned = create_property(owner, "Assigned Court")
    other = create_property(owner, "Other Court")
    manager, manager_membership = manager_of(owner)
    assign_manager(owner, assigned["id"], manager_membership)
    names = [p["name"] for p in manager.get(PROPERTIES).get_json()["items"]]
    assert names == ["Assigned Court"]
    assert manager.get(f"{PROPERTIES}/{other['id']}").status_code == 404
    unassign = owner.delete(f"{PROPERTIES}/{assigned['id']}/managers/{manager_membership}")
    assert unassign.status_code == 204
    assert manager.get(PROPERTIES).get_json()["items"] == []


def test_only_active_managers_can_be_assigned(app: Flask) -> None:
    owner = owner_with_org(app)
    prop = create_property(owner)
    join_via_invitation(owner, "tenant@example.com", "tenant")
    tenant_membership = membership_id_of(owner, "tenant@example.com")
    response = owner.post(
        f"{PROPERTIES}/{prop['id']}/managers", json={"membership_id": tenant_membership}
    )
    assert response.status_code == 422


def test_managers_cannot_create_change_or_delete_properties(app: Flask) -> None:
    owner = owner_with_org(app)
    prop = create_property(owner)
    manager, manager_membership = manager_of(owner)
    assign_manager(owner, prop["id"], manager_membership)
    url = f"{PROPERTIES}/{prop['id']}"
    assert manager.post(PROPERTIES, json=VALID).status_code == 403
    assert manager.patch(url, json={"name": "Hijacked", "version": 1}).status_code == 403
    assert manager.delete(url).status_code == 403


@pytest.mark.parametrize("role", ["tenant", "contractor"])
def test_tenants_and_contractors_cannot_list_properties(app: Flask, role: str) -> None:
    owner = owner_with_org(app)
    member = join_via_invitation(owner, f"{role}@example.com", role)
    assert member.get(PROPERTIES).status_code == 403


def test_stale_version_cannot_overwrite_newer_changes(app: Flask) -> None:
    owner = owner_with_org(app)
    prop = create_property(owner)
    url = f"{PROPERTIES}/{prop['id']}"
    first = owner.patch(url, json={"name": "Renamed", "version": 1})
    assert first.status_code == 200
    assert first.get_json()["version"] == 2
    stale = owner.patch(url, json={"name": "Lost update", "version": 1})
    assert stale.status_code == 409
    assert owner.get(url).get_json()["name"] == "Renamed"


def test_archived_properties_leave_the_default_list(app: Flask) -> None:
    owner = owner_with_org(app)
    prop = create_property(owner)
    owner.patch(f"{PROPERTIES}/{prop['id']}", json={"status": "archived", "version": 1})
    assert owner.get(PROPERTIES).get_json()["items"] == []
    archived = owner.get(PROPERTIES, query_string={"status": "archived"}).get_json()["items"]
    assert [p["id"] for p in archived] == [prop["id"]]


def test_empty_property_can_be_deleted_but_not_one_with_units(app: Flask) -> None:
    owner = owner_with_org(app)
    empty = create_property(owner, "Empty Court")
    used = create_property(owner, "Used Court")
    create_unit(owner, used["id"])
    assert owner.delete(f"{PROPERTIES}/{empty['id']}").status_code == 204
    assert owner.delete(f"{PROPERTIES}/{used['id']}").status_code == 409
    assert owner.get(f"{PROPERTIES}/{used['id']}").status_code == 200


def test_building_names_are_unique_per_property(app: Flask) -> None:
    owner = owner_with_org(app)
    prop = create_property(owner)
    url = f"{PROPERTIES}/{prop['id']}/buildings"
    assert owner.post(url, json={"name": "Block A"}).status_code == 201
    assert owner.post(url, json={"name": "Block A"}).status_code == 409
    assert [b["name"] for b in owner.get(url).get_json()] == ["Block A"]
