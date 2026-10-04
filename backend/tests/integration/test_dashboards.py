from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

import pytest
from flask import Flask
from sqlalchemy import event

from app.extensions import db
from tests.support import (
    Actor,
    assign_manager,
    contractor_user,
    create_contractor,
    create_organization,
    create_property,
    create_unit,
    create_work_order,
    join_via_invitation,
    membership_id_of,
    move_request,
    move_work_order,
    place_tenant,
    report_issue,
    sign_up,
)

DASHBOARD = "/api/v1/dashboard"


@dataclass
class Estate:
    app: Flask
    owner: Actor
    manager: Actor
    tenant: Actor
    fixer: Actor
    other_property: dict[str, Any]
    urgent: dict[str, Any]
    resolved: dict[str, Any]
    hidden: dict[str, Any]
    work_order: dict[str, Any]


@pytest.fixture()
def estate(app: Flask) -> Estate:
    owner = sign_up(app, "owner@example.com", "Olivia Owner")
    create_organization(owner, "Riverside Estates")
    assigned = create_property(owner, "Assigned Court")
    other = create_property(owner, "Other Court")
    manager = join_via_invitation(owner, "manager@example.com", "manager", "Mary Manager")
    assign_manager(owner, assigned["id"], membership_id_of(owner, "manager@example.com"))
    tenant = place_tenant(
        manager, "tenant@example.com", create_unit(owner, assigned["id"], "A1")["id"]
    )
    fixit = create_contractor(manager, "Fixit Plumbing")
    fixer = contractor_user(manager, fixit["id"], "fixer@example.com")

    urgent = report_issue(tenant, title="Burst pipe", priority="urgent")
    move_request(manager, urgent["id"], "triaged")
    overdue_since = (date.today() - timedelta(days=3)).isoformat()
    order = create_work_order(manager, urgent["id"], fixit["id"], due_date=overdue_since)
    move_work_order(fixer, order["id"], "accepted")

    resolved = report_issue(tenant, title="Loose door handle")
    for status in ["triaged", "assigned", "in_progress", "resolved"]:
        assert move_request(manager, resolved["id"], status).status_code == 200

    hidden_unit = create_unit(owner, other["id"], "B1")
    hidden = report_issue(owner, unit_id=hidden_unit["id"], title="Gate motor")
    return Estate(app, owner, manager, tenant, fixer, other, urgent, resolved, hidden, order)


def get(actor: Actor, path: str, **query: Any) -> dict[str, Any]:
    response = actor.get(f"{DASHBOARD}/{path}", query_string=query)
    assert response.status_code == 200, response.get_json()
    return dict(response.get_json())


def test_operations_dashboard_counts_only_what_the_manager_can_see(estate: Estate) -> None:
    board = get(estate.manager, "operations")
    assert board["requests"]["open"] == 1
    assert board["requests"]["urgent"] == 1
    assert board["requests"]["resolved_this_month"] == 1
    assert board["work_orders"]["accepted"] == 1
    assert board["work_orders"]["overdue"] == 1
    recent = [item["id"] for item in board["recent_requests"]]
    assert recent == [estate.resolved["id"], estate.urgent["id"]]
    assert estate.hidden["id"] not in [item["id"] for item in board["recently_updated"]]
    assert [item["id"] for item in board["overdue_work_orders"]] == [estate.work_order["id"]]


def test_owner_sees_the_whole_organization_and_can_filter_by_property(estate: Estate) -> None:
    assert get(estate.owner, "operations")["requests"]["open"] == 2
    filtered = get(estate.owner, "operations", property_id=estate.other_property["id"])
    assert filtered["requests"]["open"] == 1
    assert filtered["work_orders"]["active"] == 0


def test_manager_cannot_filter_by_a_property_they_do_not_manage(estate: Estate) -> None:
    response = estate.manager.get(
        f"{DASHBOARD}/operations", query_string={"property_id": estate.other_property["id"]}
    )
    assert response.status_code == 404


def test_organization_dashboard_totals_and_activity(estate: Estate) -> None:
    board = get(estate.owner, "organization")
    assert board["counts"] == {
        "properties": 2,
        "units": 2,
        "active_tenants": 1,
        "open_requests": 2,
        "active_work_orders": 1,
    }
    assert board["recent_activity"]
    assert estate.manager.get(f"{DASHBOARD}/organization").status_code == 403


def test_tenant_dashboard_shows_their_unit_requests_and_activity(estate: Estate) -> None:
    board = get(estate.tenant, "tenant")
    assert board["unit"]["label"] == "A1"
    assert board["requests"] == {
        "submitted": 0,
        "in_progress": 1,
        "waiting": 0,
        "resolved": 1,
        "closed": 0,
    }
    assert [item["id"] for item in board["recent_requests"]] == [
        estate.resolved["id"],
        estate.urgent["id"],
    ]
    assert board["recent_activity"]


def test_contractor_dashboard_lists_their_jobs_soonest_due_first(estate: Estate) -> None:
    board = get(estate.fixer, "contractor")
    assert board["work_orders"]["accepted"] == 1
    assert board["work_orders"]["overdue"] == 1
    assert [item["id"] for item in board["upcoming"]] == [estate.work_order["id"]]
    assert board["upcoming"][0]["is_overdue"] is True


def test_tenants_cannot_open_staff_dashboards(estate: Estate) -> None:
    assert estate.tenant.get(f"{DASHBOARD}/operations").status_code == 403
    assert estate.tenant.get(f"{DASHBOARD}/organization").status_code == 403


@contextmanager
def count_queries(app: Flask) -> Iterator[list[str]]:
    with app.app_context():
        engine = db.engine
    statements: list[str] = []

    def record(*args: Any) -> None:
        statements.append(str(args[2]))

    event.listen(engine, "before_cursor_execute", record)
    try:
        yield statements
    finally:
        event.remove(engine, "before_cursor_execute", record)


@pytest.mark.parametrize("path", ["operations", "organization"])
def test_dashboard_query_count_does_not_grow_with_data(estate: Estate, path: str) -> None:
    viewer = estate.manager if path == "operations" else estate.owner
    with count_queries(estate.app) as few:
        get(viewer, path)
    for index in range(6):
        report_issue(estate.tenant, title=f"Extra issue {index}")
    with count_queries(estate.app) as many:
        get(viewer, path)
    assert len(many) == len(few), "dashboard query count grew with data (N+1?)"
