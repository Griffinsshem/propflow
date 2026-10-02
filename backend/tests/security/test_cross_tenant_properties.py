"""Cross-tenant suite for the property hierarchy (spec section 54)."""

from tests.support import (
    PROPERTIES,
    UNITS,
    TwoOrgs,
    create_property,
    create_unit,
    join_via_invitation,
    membership_id_of,
)


def b_resources(two_orgs: TwoOrgs) -> tuple[dict, dict]:
    prop = create_property(two_orgs.b_owner, "B Court")
    unit = create_unit(two_orgs.b_owner, prop["id"], "B1")
    return prop, unit


def test_cannot_read_update_or_delete_another_orgs_property(two_orgs: TwoOrgs) -> None:
    prop, _ = b_resources(two_orgs)
    url = f"{PROPERTIES}/{prop['id']}"
    assert two_orgs.a_owner.get(url).status_code == 404
    assert two_orgs.a_owner.patch(url, json={"name": "Pwned", "version": 1}).status_code == 404
    assert two_orgs.a_owner.delete(url).status_code == 404
    assert two_orgs.b_owner.get(url).get_json()["name"] == "B Court"


def test_property_and_unit_lists_do_not_leak(two_orgs: TwoOrgs) -> None:
    b_resources(two_orgs)
    assert two_orgs.a_owner.get(PROPERTIES).get_json()["items"] == []
    assert two_orgs.a_owner.get(UNITS).get_json()["items"] == []


def test_cannot_read_or_update_another_orgs_unit(two_orgs: TwoOrgs) -> None:
    _, unit = b_resources(two_orgs)
    url = f"{UNITS}/{unit['id']}"
    assert two_orgs.a_owner.get(url).status_code == 404
    assert two_orgs.a_owner.patch(url, json={"label": "Pwned", "version": 1}).status_code == 404


def test_cannot_create_units_or_buildings_in_another_orgs_property(two_orgs: TwoOrgs) -> None:
    prop, _ = b_resources(two_orgs)
    injected_unit = two_orgs.a_owner.post(
        UNITS, json={"property_id": prop["id"], "label": "Injected"}
    )
    injected_building = two_orgs.a_owner.post(
        f"{PROPERTIES}/{prop['id']}/buildings", json={"name": "Injected"}
    )
    assert injected_unit.status_code == 404
    assert injected_building.status_code == 404


def test_cannot_assign_a_foreign_manager_to_own_property(two_orgs: TwoOrgs) -> None:
    b_manager = join_via_invitation(two_orgs.b_owner, "b.manager@example.com", "manager")
    b_membership = membership_id_of(two_orgs.b_owner, "b.manager@example.com")
    own = create_property(two_orgs.a_owner, "A Court")
    response = two_orgs.a_owner.post(
        f"{PROPERTIES}/{own['id']}/managers", json={"membership_id": b_membership}
    )
    assert response.status_code == 404
    assert b_manager.get(PROPERTIES).get_json()["items"] == []


def test_unit_filter_with_foreign_property_returns_nothing(two_orgs: TwoOrgs) -> None:
    prop, _ = b_resources(two_orgs)
    items = two_orgs.a_owner.get(UNITS, query_string={"property_id": prop["id"]}).get_json()
    assert items["items"] == []
