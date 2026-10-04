from dataclasses import dataclass
from typing import Any

import pytest
from flask import Flask

from tests.support import (
    MAINTENANCE,
    NOTIFICATIONS,
    Actor,
    TwoOrgs,
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
    notifications_of,
    place_tenant,
    report_issue,
    sign_up,
)


@dataclass
class Hub:
    app: Flask
    owner: Actor
    manager: Actor
    tenant: Actor
    fixer: Actor
    fixit: dict[str, Any]
    unassigned_unit: dict[str, Any]


@pytest.fixture()
def hub(app: Flask) -> Hub:
    owner = sign_up(app, "owner@example.com", "Olivia Owner")
    create_organization(owner, "Riverside Estates")
    assigned = create_property(owner, "Assigned Court")
    other = create_property(owner, "Other Court")
    manager = join_via_invitation(owner, "manager@example.com", "manager", "Mary Manager")
    assign_manager(owner, assigned["id"], membership_id_of(owner, "manager@example.com"))
    unit = create_unit(owner, assigned["id"], "A1")
    tenant = place_tenant(manager, "tenant@example.com", unit["id"], "Tina Tenant")
    fixit = create_contractor(manager, "Fixit Plumbing")
    fixer = contractor_user(manager, fixit["id"], "fixer@example.com", "Fred Fixer")
    return Hub(app, owner, manager, tenant, fixer, fixit, create_unit(owner, other["id"], "B1"))


def kinds(actor: Actor) -> list[str]:
    return [item["kind"] for item in notifications_of(actor)]


def test_new_request_notifies_the_responsible_manager_only(hub: Hub) -> None:
    request = report_issue(hub.tenant)
    items = notifications_of(hub.manager)
    assert [(item["kind"], item["body"]) for item in items] == [
        ("request_submitted", request["title"])
    ]
    assert items[0]["resource_id"] == request["id"]
    assert kinds(hub.owner) == []
    assert kinds(hub.tenant) == []


def test_owners_are_notified_when_no_manager_is_assigned(hub: Hub) -> None:
    other_tenant = place_tenant(hub.owner, "b.tenant@example.com", hub.unassigned_unit["id"])
    report_issue(other_tenant)
    assert kinds(hub.owner) == ["request_submitted"]
    assert kinds(hub.manager) == []


def test_tenant_hears_about_status_changes(hub: Hub) -> None:
    request = report_issue(hub.tenant)
    move_request(hub.manager, request["id"], "triaged")
    latest = notifications_of(hub.tenant)[0]
    assert latest["kind"] == "request_status_changed"
    assert "triaged" in latest["body"]


def test_comments_notify_the_other_participants_but_not_the_author(hub: Hub) -> None:
    request = report_issue(hub.tenant)
    comments = f"{MAINTENANCE}/{request['id']}/comments"
    hub.tenant.post(comments, json={"body": "It is getting worse."})
    assert "request_commented" in kinds(hub.manager)
    assert "request_commented" not in kinds(hub.tenant)
    hub.manager.post(comments, json={"body": "Plumber booked."})
    assert "request_commented" in kinds(hub.tenant)


def test_work_order_events_reach_the_contractor_and_back(hub: Hub) -> None:
    request = report_issue(hub.tenant)
    move_request(hub.manager, request["id"], "triaged")
    order = create_work_order(hub.manager, request["id"], hub.fixit["id"])
    assert kinds(hub.fixer) == ["work_order_assigned"]
    move_work_order(hub.fixer, order["id"], "accepted")
    assert kinds(hub.manager)[0] == "work_order_status_changed"


def test_marking_notifications_read(hub: Hub) -> None:
    report_issue(hub.tenant)
    count_url = f"{NOTIFICATIONS}/unread-count"
    assert hub.manager.get(count_url).get_json() == {"unread": 1}
    first = notifications_of(hub.manager)[0]
    marked = hub.manager.post(f"{NOTIFICATIONS}/{first['id']}/read")
    assert marked.status_code == 200
    assert marked.get_json()["read"] is True
    assert hub.manager.get(count_url).get_json() == {"unread": 0}
    report_issue(hub.tenant, title="Second issue")
    assert hub.manager.post(f"{NOTIFICATIONS}/read-all").get_json() == {"updated": 1}
    assert notifications_of(hub.manager, unread_only="true") == []


def test_nobody_can_mark_someone_elses_notifications(hub: Hub) -> None:
    report_issue(hub.tenant)
    theirs = notifications_of(hub.manager)[0]["id"]
    assert hub.owner.post(f"{NOTIFICATIONS}/{theirs}/read").status_code == 404
    assert hub.tenant.post(f"{NOTIFICATIONS}/{theirs}/read").status_code == 404


def test_notifications_never_cross_organizations(two_orgs: TwoOrgs) -> None:
    prop = create_property(two_orgs.a_owner, "A Court")
    unit = create_unit(two_orgs.a_owner, prop["id"], "A1")
    tenant = place_tenant(two_orgs.a_owner, "a.tenant@example.com", unit["id"])
    report_issue(tenant)
    a_notification = notifications_of(two_orgs.a_owner)[0]["id"]
    assert notifications_of(two_orgs.b_owner) == []
    response = two_orgs.b_owner.post(f"{NOTIFICATIONS}/{a_notification}/read")
    assert response.status_code == 404
