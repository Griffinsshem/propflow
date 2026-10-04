"""Cross-tenant suite for contractors and work orders (spec section 54)."""

import uuid
from typing import Any

import pytest
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.work_orders.models import WorkOrder
from tests.support import (
    CONTRACTORS,
    WORK_ORDERS,
    Actor,
    TwoOrgs,
    create_contractor,
    create_property,
    create_unit,
    create_work_order,
    membership_id_of,
    move_request,
    report_issue,
)


def triaged_request(owner: Actor, name: str) -> dict[str, Any]:
    prop = create_property(owner, f"{name} Court")
    unit = create_unit(owner, prop["id"], "U1")
    request = report_issue(owner, unit_id=unit["id"])
    assert move_request(owner, request["id"], "triaged").status_code == 200
    return request


def b_world(two_orgs: TwoOrgs) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    request = triaged_request(two_orgs.b_owner, "B")
    contractor = create_contractor(two_orgs.b_owner, "B Builders")
    order = create_work_order(two_orgs.b_owner, request["id"], contractor["id"])
    return request, contractor, order


def test_cannot_touch_another_orgs_work_order(two_orgs: TwoOrgs) -> None:
    _, contractor, order = b_world(two_orgs)
    base = f"{WORK_ORDERS}/{order['id']}"
    a = two_orgs.a_owner
    assert a.get(base).status_code == 404
    assert a.patch(base, json={"priority": "urgent", "version": 1}).status_code == 404
    assert a.post(f"{base}/status", json={"status": "accepted", "version": 1}).status_code == 404
    assigned = a.post(f"{base}/assign", json={"contractor_id": contractor["id"], "version": 1})
    assert assigned.status_code == 404
    assert a.get(f"{base}/history").status_code == 404
    assert a.get(WORK_ORDERS).get_json()["items"] == []


def test_cannot_touch_another_orgs_contractor(two_orgs: TwoOrgs) -> None:
    _, contractor, _ = b_world(two_orgs)
    base = f"{CONTRACTORS}/{contractor['id']}"
    a = two_orgs.a_owner
    assert a.get(base).status_code == 404
    assert a.patch(base, json={"status": "inactive", "version": 1}).status_code == 404
    assert a.post(f"{base}/invite", json={"email": "x@example.com"}).status_code == 404
    assert a.get(CONTRACTORS).get_json()["items"] == []


def test_cannot_mix_requests_and_contractors_across_organizations(two_orgs: TwoOrgs) -> None:
    b_request, b_contractor, _ = b_world(two_orgs)
    own_request = triaged_request(two_orgs.a_owner, "A")
    own_contractor = create_contractor(two_orgs.a_owner, "A Builders")
    foreign_contractor = two_orgs.a_owner.post(
        WORK_ORDERS, json={"request_id": own_request["id"], "contractor_id": b_contractor["id"]}
    )
    foreign_request = two_orgs.a_owner.post(
        WORK_ORDERS, json={"request_id": b_request["id"], "contractor_id": own_contractor["id"]}
    )
    assert foreign_contractor.status_code == 404
    assert foreign_request.status_code == 404


def test_database_rejects_work_order_with_another_orgs_contractor(two_orgs: TwoOrgs) -> None:
    _, b_contractor, _ = b_world(two_orgs)
    own_request = triaged_request(two_orgs.a_owner, "A")
    creator = membership_id_of(two_orgs.a_owner, "owner.a@example.com")
    with two_orgs.app.app_context():
        db.session.add(
            WorkOrder(
                organization_id=uuid.UUID(two_orgs.org_a),
                request_id=uuid.UUID(own_request["id"]),
                contractor_id=uuid.UUID(b_contractor["id"]),
                created_by_membership_id=uuid.UUID(creator),
                status="assigned",
                priority="normal",
            )
        )
        with pytest.raises(IntegrityError):
            db.session.flush()
        db.session.rollback()
