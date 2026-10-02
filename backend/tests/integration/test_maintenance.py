import uuid
from dataclasses import dataclass
from typing import Any

import pytest
from flask import Flask
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.maintenance.models import MaintenanceRequest
from tests.support import (
    MAINTENANCE,
    Actor,
    assign_manager,
    create_organization,
    create_property,
    create_unit,
    join_via_invitation,
    membership_id_of,
    move_request,
    place_tenant,
    report_issue,
    sign_up,
)


@dataclass
class Site:
    app: Flask
    owner: Actor
    manager: Actor
    tenant: Actor
    neighbour: Actor
    org_id: str
    a1: dict[str, Any]
    a2: dict[str, Any]
    b1: dict[str, Any]


@pytest.fixture()
def site(app: Flask) -> Site:
    owner = sign_up(app, "owner@example.com", "Olivia Owner")
    org_id = create_organization(owner, "Riverside Estates")
    assigned = create_property(owner, "Assigned Court")
    other = create_property(owner, "Other Court")
    manager = join_via_invitation(owner, "manager@example.com", "manager", "Mary Manager")
    assign_manager(owner, assigned["id"], membership_id_of(owner, "manager@example.com"))
    a1 = create_unit(owner, assigned["id"], "A1")
    a2 = create_unit(owner, assigned["id"], "A2")
    b1 = create_unit(owner, other["id"], "B1")
    tenant = place_tenant(manager, "tenant@example.com", a1["id"], "Tina Tenant")
    neighbour = place_tenant(manager, "neighbour@example.com", a2["id"], "Ned Neighbour")
    return Site(app, owner, manager, tenant, neighbour, org_id, a1, a2, b1)


def url(request: dict[str, Any], suffix: str = "") -> str:
    return f"{MAINTENANCE}/{request['id']}{suffix}"


# --- Reporting ------------------------------------------------------------------------------


def test_tenant_report_is_tied_to_their_unit_and_starts_submitted(site: Site) -> None:
    request = report_issue(site.tenant)
    assert request["status"] == "submitted"
    assert request["unit"]["label"] == "A1"
    assert request["property"]["name"] == "Assigned Court"
    assert request["reported_by"]["full_name"] == "Tina Tenant"
    history = site.tenant.get(url(request, "/history")).get_json()
    assert [(h["from_status"], h["to_status"]) for h in history] == [(None, "submitted")]


def test_tenant_cannot_choose_a_unit(site: Site) -> None:
    response = site.tenant.post(
        MAINTENANCE,
        json={
            "category": "plumbing",
            "title": "Leak",
            "description": "Somewhere else",
            "unit_id": site.a2["id"],
        },
    )
    assert response.status_code == 422


def test_unplaced_tenant_cannot_report(site: Site) -> None:
    loose = join_via_invitation(site.owner, "loose@example.com", "tenant")
    response = loose.post(
        MAINTENANCE, json={"category": "other", "title": "Noise", "description": "Loud pipes"}
    )
    assert response.status_code == 409


def test_manager_reports_only_for_units_in_assigned_properties(site: Site) -> None:
    assert report_issue(site.manager, unit_id=site.a2["id"])["unit"]["label"] == "A2"
    response = site.manager.post(
        MAINTENANCE,
        json={
            "category": "other",
            "title": "Gate",
            "description": "Broken",
            "unit_id": site.b1["id"],
        },
    )
    assert response.status_code == 404


# --- Visibility -----------------------------------------------------------------------------


def test_tenants_see_only_their_own_requests(site: Site) -> None:
    mine = report_issue(site.tenant)
    theirs = report_issue(site.neighbour)
    assert [r["id"] for r in site.tenant.get(MAINTENANCE).get_json()["items"]] == [mine["id"]]
    assert site.tenant.get(url(theirs)).status_code == 404


def test_manager_sees_only_requests_in_assigned_properties(site: Site) -> None:
    hidden = report_issue(site.owner, unit_id=site.b1["id"])
    visible = report_issue(site.tenant)
    manager_ids = {r["id"] for r in site.manager.get(MAINTENANCE).get_json()["items"]}
    owner_ids = {r["id"] for r in site.owner.get(MAINTENANCE).get_json()["items"]}
    assert manager_ids == {visible["id"]}
    assert owner_ids == {visible["id"], hidden["id"]}
    assert site.manager.get(url(hidden)).status_code == 404


def test_contractors_cannot_read_requests_yet(site: Site) -> None:
    contractor = join_via_invitation(site.owner, "fixer@example.com", "contractor")
    assert contractor.get(MAINTENANCE).status_code == 403


# --- Workflow -------------------------------------------------------------------------------


def test_full_lifecycle_is_recorded_in_history(site: Site) -> None:
    request = report_issue(site.tenant)
    for status in ["triaged", "assigned", "in_progress", "resolved", "closed"]:
        response = move_request(site.manager, request["id"], status)
        assert response.status_code == 200, (status, response.get_json())
    history = site.manager.get(url(request, "/history")).get_json()
    assert [h["to_status"] for h in history] == [
        "submitted",
        "triaged",
        "assigned",
        "in_progress",
        "resolved",
        "closed",
    ]
    assert history[-1]["changed_by"]["full_name"] == "Mary Manager"
    final = site.manager.get(url(request)).get_json()
    assert final["resolved_at"] and final["closed_at"]
    assert final["allowed_transitions"] == []


def test_invalid_transition_is_rejected(site: Site) -> None:
    request = report_issue(site.tenant)
    response = move_request(site.manager, request["id"], "resolved")
    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "INVALID_STATUS_TRANSITION"


def test_tenant_cannot_change_status(site: Site) -> None:
    request = report_issue(site.tenant)
    assert move_request(site.tenant, request["id"], "triaged").status_code == 403


def test_waiting_requires_a_reason(site: Site) -> None:
    request = report_issue(site.tenant)
    for status in ["triaged", "assigned", "in_progress"]:
        move_request(site.manager, request["id"], status)
    assert move_request(site.manager, request["id"], "waiting").status_code == 422
    ok = move_request(site.manager, request["id"], "waiting", reason="Waiting for spare parts")
    assert ok.status_code == 200
    assert site.manager.get(url(request, "/history")).get_json()[-1]["reason"] == (
        "Waiting for spare parts"
    )


def test_stale_status_change_is_rejected(site: Site) -> None:
    request = report_issue(site.tenant)
    version = site.manager.get(url(request)).get_json()["version"]
    first = site.manager.post(
        url(request, "/status"), json={"status": "triaged", "version": version}
    )
    stale = site.manager.post(
        url(request, "/status"),
        json={"status": "closed", "reason": "Duplicate", "version": version},
    )
    assert first.status_code == 200
    assert stale.status_code == 409


def test_allowed_transitions_reflect_the_callers_role(site: Site) -> None:
    request = report_issue(site.tenant)
    assert site.tenant.get(url(request)).get_json()["allowed_transitions"] == []
    assert site.manager.get(url(request)).get_json()["allowed_transitions"] == [
        "closed",
        "triaged",
    ]


# --- Comments -------------------------------------------------------------------------------


def test_tenant_and_manager_can_converse(site: Site) -> None:
    request = report_issue(site.tenant)
    site.tenant.post(url(request, "/comments"), json={"body": "It is getting worse."})
    site.manager.post(url(request, "/comments"), json={"body": "Plumber booked for 10am."})
    items = site.tenant.get(url(request, "/comments")).get_json()["items"]
    assert [(c["author"]["role"], c["body"]) for c in items] == [
        ("tenant", "It is getting worse."),
        ("manager", "Plumber booked for 10am."),
    ]


def test_comment_markup_is_stored_verbatim_and_served_only_as_json(site: Site) -> None:
    request = report_issue(site.tenant)
    payload = '<script>alert("x")</script><img src=x onerror=alert(1)>'
    response = site.tenant.post(url(request, "/comments"), json={"body": payload})
    assert response.status_code == 201
    assert response.content_type.startswith("application/json")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.get_json()["body"] == payload


def test_control_characters_are_rejected(site: Site) -> None:
    request = report_issue(site.tenant)
    response = site.tenant.post(url(request, "/comments"), json={"body": "bad\u0000text"})
    assert response.status_code == 422


def test_neighbour_cannot_comment_on_someone_elses_request(site: Site) -> None:
    request = report_issue(site.tenant)
    response = site.neighbour.post(url(request, "/comments"), json={"body": "Hello"})
    assert response.status_code == 404


def test_closed_requests_accept_no_new_comments(site: Site) -> None:
    request = report_issue(site.tenant)
    move_request(site.manager, request["id"], "closed", reason="Duplicate report")
    response = site.tenant.post(url(request, "/comments"), json={"body": "Still broken"})
    assert response.status_code == 409


# --- Database integrity ---------------------------------------------------------------------


def test_database_keeps_a_requests_unit_inside_its_property(site: Site) -> None:
    other_property = site.owner.get(f"/api/v1/units/{site.b1['id']}").get_json()["property_id"]
    with site.app.app_context():
        db.session.add(
            MaintenanceRequest(
                organization_id=uuid.UUID(site.org_id),
                property_id=uuid.UUID(other_property),
                unit_id=uuid.UUID(site.a1["id"]),
                reported_by_membership_id=uuid.UUID(
                    membership_id_of(site.owner, "owner@example.com")
                ),
                category="other",
                priority="normal",
                status="submitted",
                title="Mismatch",
                description="Unit from another property",
            )
        )
        with pytest.raises(IntegrityError):
            db.session.flush()
        db.session.rollback()
