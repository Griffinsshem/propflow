import io
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

import pytest
from flask import Flask
from PIL import Image

from tests.support import (
    CONTRACTORS,
    MAINTENANCE,
    WORK_ORDERS,
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
    upload_image,
)


@dataclass
class Yard:
    app: Flask
    owner: Actor
    manager: Actor
    tenant: Actor
    fixer: Actor
    fixit: dict[str, Any]
    sparks: dict[str, Any]
    request: dict[str, Any]


@pytest.fixture()
def yard(app: Flask) -> Yard:
    owner = sign_up(app, "owner@example.com", "Olivia Owner")
    create_organization(owner, "Riverside Estates")
    prop = create_property(owner, "Riverside Court")
    manager = join_via_invitation(owner, "manager@example.com", "manager", "Mary Manager")
    assign_manager(owner, prop["id"], membership_id_of(owner, "manager@example.com"))
    unit = create_unit(owner, prop["id"], "A1")
    tenant = place_tenant(manager, "tenant@example.com", unit["id"], "Tina Tenant")
    fixit = create_contractor(manager, "Fixit Plumbing")
    sparks = create_contractor(manager, "Sparks Electrical", specialty="electrical")
    fixer = contractor_user(manager, fixit["id"], "fixer@example.com", "Fred Fixer")
    request = report_issue(tenant)
    assert move_request(manager, request["id"], "triaged").status_code == 200
    return Yard(app, owner, manager, tenant, fixer, fixit, sparks, request)


def request_status(actor: Actor, request: dict[str, Any]) -> str:
    return str(actor.get(f"{MAINTENANCE}/{request['id']}").get_json()["status"])


def jpeg() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (32, 32), "teal").save(buffer, "JPEG")
    return buffer.getvalue()


def test_end_to_end_maintenance_workflow(yard: Yard) -> None:
    """Spec section 5: report -> review -> assign -> contractor works -> resolve -> tenant sees."""
    order = create_work_order(yard.manager, yard.request["id"], yard.fixit["id"])
    assert order["status"] == "assigned"
    assert request_status(yard.manager, yard.request) == "assigned"

    listed = yard.fixer.get(WORK_ORDERS).get_json()["items"]
    assert [item["id"] for item in listed] == [order["id"]]
    assert listed[0]["location"]["unit_label"] == "A1"

    for status in ["accepted", "in_progress", "completed"]:
        assert move_work_order(yard.fixer, order["id"], status).status_code == 200, status
    # Completion does not resolve the request: the manager verifies first.
    assert request_status(yard.manager, yard.request) == "in_progress"

    assert move_request(yard.manager, yard.request["id"], "resolved").status_code == 200
    seen_by_tenant = yard.tenant.get(f"{MAINTENANCE}/{yard.request['id']}").get_json()
    assert seen_by_tenant["status"] == "resolved"
    history = yard.tenant.get(f"{MAINTENANCE}/{yard.request['id']}/history").get_json()
    assert [entry["to_status"] for entry in history] == [
        "submitted",
        "triaged",
        "assigned",
        "in_progress",
        "resolved",
    ]


def test_contractors_see_only_their_own_work_orders(yard: Yard) -> None:
    order = create_work_order(yard.manager, yard.request["id"], yard.fixit["id"])
    sparky = contractor_user(yard.manager, yard.sparks["id"], "sparky@example.com")
    assert sparky.get(WORK_ORDERS).get_json()["items"] == []
    assert sparky.get(f"{WORK_ORDERS}/{order['id']}").status_code == 404
    assert sparky.get(f"{MAINTENANCE}/{yard.request['id']}").status_code == 404


def test_contractor_can_read_discuss_and_document_the_linked_request(yard: Yard) -> None:
    create_work_order(yard.manager, yard.request["id"], yard.fixit["id"])
    base = f"{MAINTENANCE}/{yard.request['id']}"
    assert yard.fixer.get(base).status_code == 200
    comment = yard.fixer.post(f"{base}/comments", json={"body": "Arriving at 10am."})
    assert comment.status_code == 201
    assert upload_image(yard.fixer, yard.request["id"], jpeg()).get_json()["status"] == "ready"
    unrelated = report_issue(yard.tenant, title="Broken window latch")
    assert yard.fixer.get(f"{MAINTENANCE}/{unrelated['id']}").status_code == 404
    visible = {item["id"] for item in yard.fixer.get(MAINTENANCE).get_json()["items"]}
    assert visible == {yard.request["id"]}


def test_declined_work_order_returns_request_to_triage_and_can_be_reassigned(yard: Yard) -> None:
    order = create_work_order(yard.manager, yard.request["id"], yard.fixit["id"])
    assert move_work_order(yard.fixer, order["id"], "declined").status_code == 422
    declined = move_work_order(yard.fixer, order["id"], "declined", reason="Fully booked")
    assert declined.status_code == 200
    assert request_status(yard.manager, yard.request) == "triaged"
    assert yard.fixer.get(f"{WORK_ORDERS}/{order['id']}").status_code == 404

    version = yard.manager.get(f"{WORK_ORDERS}/{order['id']}").get_json()["version"]
    reassigned = yard.manager.post(
        f"{WORK_ORDERS}/{order['id']}/assign",
        json={"contractor_id": yard.sparks["id"], "version": version},
    )
    assert reassigned.status_code == 200
    assert reassigned.get_json()["status"] == "assigned"
    assert reassigned.get_json()["contractor"]["business_name"] == "Sparks Electrical"
    assert request_status(yard.manager, yard.request) == "assigned"


def test_only_managers_cancel_and_they_must_say_why(yard: Yard) -> None:
    order = create_work_order(yard.manager, yard.request["id"], yard.fixit["id"])
    assert move_work_order(yard.fixer, order["id"], "cancelled", reason="x").status_code == 403
    assert move_work_order(yard.manager, order["id"], "cancelled").status_code == 422
    cancelled = move_work_order(yard.manager, order["id"], "cancelled", reason="Tenant fixed it")
    assert cancelled.status_code == 200
    assert request_status(yard.manager, yard.request) == "triaged"


def test_a_request_has_at_most_one_active_work_order(yard: Yard) -> None:
    create_work_order(yard.manager, yard.request["id"], yard.fixit["id"])
    second = yard.manager.post(
        WORK_ORDERS, json={"request_id": yard.request["id"], "contractor_id": yard.sparks["id"]}
    )
    assert second.status_code == 409


def test_untriaged_requests_cannot_get_work_orders(yard: Yard) -> None:
    fresh = report_issue(yard.tenant, title="New noise in the pipes")
    response = yard.manager.post(
        WORK_ORDERS, json={"request_id": fresh["id"], "contractor_id": yard.fixit["id"]}
    )
    assert response.status_code == 409


def test_inactive_contractors_cannot_be_assigned(yard: Yard) -> None:
    url = f"{CONTRACTORS}/{yard.sparks['id']}"
    version = yard.manager.get(url).get_json()["version"]
    assert (
        yard.manager.patch(url, json={"status": "inactive", "version": version}).status_code == 200
    )
    response = yard.manager.post(
        WORK_ORDERS, json={"request_id": yard.request["id"], "contractor_id": yard.sparks["id"]}
    )
    assert response.status_code == 422


def test_overdue_work_orders_are_flagged_and_filterable(yard: Yard) -> None:
    two_days_ago = (date.today() - timedelta(days=2)).isoformat()
    order = create_work_order(
        yard.manager, yard.request["id"], yard.fixit["id"], due_date=two_days_ago
    )
    assert order["is_overdue"] is True
    overdue = yard.manager.get(WORK_ORDERS, query_string={"overdue": "true"}).get_json()["items"]
    assert [item["id"] for item in overdue] == [order["id"]]


def test_stale_work_order_status_change_is_rejected(yard: Yard) -> None:
    order = create_work_order(yard.manager, yard.request["id"], yard.fixit["id"])
    url = f"{WORK_ORDERS}/{order['id']}/status"
    version = order["version"]
    assert yard.fixer.post(url, json={"status": "accepted", "version": version}).status_code == 200
    stale = yard.fixer.post(
        url, json={"status": "declined", "reason": "Changed my mind", "version": version}
    )
    assert stale.status_code == 409


def test_tenants_cannot_access_work_orders(yard: Yard) -> None:
    assert yard.tenant.get(WORK_ORDERS).status_code == 403


def test_contractor_names_are_unique_and_contacts_validated(yard: Yard) -> None:
    duplicate = yard.manager.post(
        CONTRACTORS, json={"business_name": "Fixit Plumbing", "specialty": "plumbing"}
    )
    assert duplicate.status_code == 409
    bad_phone = yard.manager.post(
        CONTRACTORS,
        json={"business_name": "New Co", "specialty": "general", "phone": "0712345678"},
    )
    assert bad_phone.status_code == 422


def test_invited_contractor_login_is_linked_to_the_record(yard: Yard) -> None:
    assert yard.manager.get(f"{CONTRACTORS}/{yard.fixit['id']}").get_json()["has_login"] is True
    assert yard.manager.get(f"{CONTRACTORS}/{yard.sparks['id']}").get_json()["has_login"] is False


def test_tenants_and_contractors_cannot_manage_contractor_records(yard: Yard) -> None:
    assert yard.tenant.get(CONTRACTORS).status_code == 403
    assert yard.fixer.get(CONTRACTORS).status_code == 403
