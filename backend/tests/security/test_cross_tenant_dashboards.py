"""Dashboards must never count another organization's data (spec section 54)."""

from tests.support import (
    TwoOrgs,
    create_property,
    create_unit,
    place_tenant,
    report_issue,
)

DASHBOARD = "/api/v1/dashboard"


def test_dashboards_ignore_other_organizations(two_orgs: TwoOrgs) -> None:
    prop = create_property(two_orgs.b_owner, "B Court")
    tenant = place_tenant(
        two_orgs.b_owner, "b.tenant@example.com", create_unit(two_orgs.b_owner, prop["id"])["id"]
    )
    report_issue(tenant)

    operations = two_orgs.a_owner.get(f"{DASHBOARD}/operations").get_json()
    organization = two_orgs.a_owner.get(f"{DASHBOARD}/organization").get_json()
    assert operations["requests"]["open"] == 0
    assert operations["recent_requests"] == []
    assert organization["counts"]["properties"] == 0
    assert organization["counts"]["open_requests"] == 0


def test_cannot_filter_a_dashboard_by_another_orgs_property(two_orgs: TwoOrgs) -> None:
    prop = create_property(two_orgs.b_owner, "B Court")
    response = two_orgs.a_owner.get(
        f"{DASHBOARD}/operations", query_string={"property_id": prop["id"]}
    )
    assert response.status_code == 404
