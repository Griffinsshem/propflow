"""Cross-tenant suite for maintenance requests (spec section 54)."""

from typing import Any

from tests.support import MAINTENANCE, TwoOrgs, create_property, create_unit, report_issue


def b_request(two_orgs: TwoOrgs) -> tuple[dict[str, Any], dict[str, Any]]:
    prop = create_property(two_orgs.b_owner, "B Court")
    unit = create_unit(two_orgs.b_owner, prop["id"], "B1")
    return report_issue(two_orgs.b_owner, unit_id=unit["id"]), unit


def test_cannot_read_or_modify_another_orgs_request(two_orgs: TwoOrgs) -> None:
    request, _ = b_request(two_orgs)
    base = f"{MAINTENANCE}/{request['id']}"
    a = two_orgs.a_owner
    assert a.get(base).status_code == 404
    assert a.patch(base, json={"title": "Pwned", "version": 1}).status_code == 404
    assert a.post(f"{base}/status", json={"status": "triaged", "version": 1}).status_code == 404
    assert a.get(f"{base}/history").status_code == 404
    assert a.get(f"{base}/comments").status_code == 404
    assert a.post(f"{base}/comments", json={"body": "Injected"}).status_code == 404
    assert two_orgs.b_owner.get(base).get_json()["status"] == "submitted"


def test_request_lists_do_not_leak(two_orgs: TwoOrgs) -> None:
    b_request(two_orgs)
    assert two_orgs.a_owner.get(MAINTENANCE).get_json()["items"] == []


def test_cannot_report_into_another_orgs_unit(two_orgs: TwoOrgs) -> None:
    _, unit = b_request(two_orgs)
    response = two_orgs.a_owner.post(
        MAINTENANCE,
        json={"category": "other", "title": "Injected", "description": "x", "unit_id": unit["id"]},
    )
    assert response.status_code == 404
