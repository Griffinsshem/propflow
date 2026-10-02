from flask import Flask

from tests.support import (
    PROPERTIES,
    UNITS,
    Actor,
    assign_manager,
    create_organization,
    create_property,
    create_unit,
    join_via_invitation,
    membership_id_of,
    sign_up,
)


def setup_org(app: Flask) -> tuple[Actor, Actor, dict, dict]:
    owner = sign_up(app, "owner@example.com", "Olivia Owner")
    create_organization(owner, "Riverside Estates")
    assigned = create_property(owner, "Assigned Court")
    other = create_property(owner, "Other Court")
    manager = join_via_invitation(owner, "manager@example.com", "manager")
    assign_manager(owner, assigned["id"], membership_id_of(owner, "manager@example.com"))
    return owner, manager, assigned, other


def test_manager_creates_units_only_in_assigned_properties(app: Flask) -> None:
    _, manager, assigned, other = setup_org(app)
    ok = manager.post(UNITS, json={"property_id": assigned["id"], "label": "A101"})
    assert ok.status_code == 201
    denied = manager.post(UNITS, json={"property_id": other["id"], "label": "A101"})
    assert denied.status_code == 404


def test_manager_sees_only_units_in_assigned_properties(app: Flask) -> None:
    owner, manager, assigned, other = setup_org(app)
    create_unit(owner, assigned["id"], "A1")
    hidden = create_unit(owner, other["id"], "B1")
    assert [u["label"] for u in manager.get(UNITS).get_json()["items"]] == ["A1"]
    assert manager.get(f"{UNITS}/{hidden['id']}").status_code == 404


def test_unit_labels_are_unique_per_property(app: Flask) -> None:
    owner, _, assigned, other = setup_org(app)
    create_unit(owner, assigned["id"], "A101")
    duplicate = owner.post(UNITS, json={"property_id": assigned["id"], "label": "A101"})
    assert duplicate.status_code == 409
    create_unit(owner, other["id"], "A101")


def test_building_must_belong_to_the_units_property(app: Flask) -> None:
    owner, _, assigned, other = setup_org(app)
    building = owner.post(
        f"{PROPERTIES}/{assigned['id']}/buildings", json={"name": "Block A"}
    ).get_json()
    mismatched = owner.post(
        UNITS, json={"property_id": other["id"], "label": "X1", "building_id": building["id"]}
    )
    assert mismatched.status_code == 422
    unit = create_unit(owner, assigned["id"], "A101", building_id=building["id"])
    assert unit["building_id"] == building["id"]


def test_units_can_be_filtered_by_property(app: Flask) -> None:
    owner, _, assigned, other = setup_org(app)
    create_unit(owner, assigned["id"], "A1")
    create_unit(owner, other["id"], "B1")
    items = owner.get(UNITS, query_string={"property_id": other["id"]}).get_json()["items"]
    assert [u["label"] for u in items] == ["B1"]


def test_stale_unit_update_is_rejected(app: Flask) -> None:
    owner, _, assigned, _ = setup_org(app)
    unit = create_unit(owner, assigned["id"])
    url = f"{UNITS}/{unit['id']}"
    assert owner.patch(url, json={"status": "occupied", "version": 1}).status_code == 200
    assert owner.patch(url, json={"status": "unavailable", "version": 1}).status_code == 409


def test_tenants_see_no_units_until_tenancies_exist(app: Flask) -> None:
    owner, _, assigned, _ = setup_org(app)
    create_unit(owner, assigned["id"])
    tenant = join_via_invitation(owner, "tenant@example.com", "tenant")
    response = tenant.get(UNITS)
    assert response.status_code == 200
    assert response.get_json()["items"] == []
