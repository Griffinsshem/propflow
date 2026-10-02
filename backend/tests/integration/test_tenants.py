import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from flask import Flask
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.organizations.models import Invitation
from tests.support import (
    MEMBERS,
    TENANTS,
    UNITS,
    Actor,
    assign_manager,
    create_organization,
    create_property,
    create_unit,
    join_via_invitation,
    membership_id_of,
    place_tenant,
    sign_up,
    tenant_id_of,
)

ME = f"{TENANTS}/me"


@dataclass
class Estate:
    app: Flask
    owner: Actor
    manager: Actor
    org_id: str
    a1: dict[str, Any]
    a2: dict[str, Any]
    b1: dict[str, Any]


@pytest.fixture()
def estate(app: Flask) -> Estate:
    owner = sign_up(app, "owner@example.com", "Olivia Owner")
    org_id = create_organization(owner, "Riverside Estates")
    assigned = create_property(owner, "Assigned Court")
    other = create_property(owner, "Other Court")
    manager = join_via_invitation(owner, "manager@example.com", "manager", "Mary Manager")
    assign_manager(owner, assigned["id"], membership_id_of(owner, "manager@example.com"))
    return Estate(
        app=app,
        owner=owner,
        manager=manager,
        org_id=org_id,
        a1=create_unit(owner, assigned["id"], "A1"),
        a2=create_unit(owner, assigned["id"], "A2"),
        b1=create_unit(owner, other["id"], "B1"),
    )


def unit_status(estate: Estate, unit: dict[str, Any]) -> str:
    return str(estate.owner.get(f"{UNITS}/{unit['id']}").get_json()["status"])


def tenant_version(viewer: Actor, tenant_id: str) -> int:
    return int(viewer.get(f"{TENANTS}/{tenant_id}").get_json()["version"])


def test_tenant_invited_into_a_unit_is_placed_on_acceptance(estate: Estate) -> None:
    tenant = place_tenant(estate.manager, "tenant@example.com", estate.a1["id"])
    me = tenant.get(ME).get_json()
    assert me["unit"]["label"] == "A1"
    assert me["unit"]["property_name"] == "Assigned Court"
    assert unit_status(estate, estate.a1) == "occupied"
    assert [u["label"] for u in tenant.get(UNITS).get_json()["items"]] == ["A1"]
    assert tenant.get(f"{UNITS}/{estate.a2['id']}").status_code == 404


def test_manager_cannot_place_a_tenant_outside_assigned_properties(estate: Estate) -> None:
    response = estate.manager.post(
        TENANTS, json={"email": "x@example.com", "unit_id": estate.b1["id"]}
    )
    assert response.status_code == 404


def test_manager_lists_only_tenants_in_assigned_properties(estate: Estate) -> None:
    place_tenant(estate.owner, "b.tenant@example.com", estate.b1["id"])
    place_tenant(estate.manager, "a.tenant@example.com", estate.a1["id"])
    manager_view = {t["email"] for t in estate.manager.get(TENANTS).get_json()["items"]}
    owner_view = {t["email"] for t in estate.owner.get(TENANTS).get_json()["items"]}
    assert manager_view == {"a.tenant@example.com"}
    assert owner_view == {"a.tenant@example.com", "b.tenant@example.com"}


def test_moving_a_tenant_updates_both_units(estate: Estate) -> None:
    tenant = place_tenant(estate.manager, "tenant@example.com", estate.a1["id"])
    tenant_id = tenant_id_of(estate.manager, "tenant@example.com")
    response = estate.manager.patch(
        f"{TENANTS}/{tenant_id}",
        json={"unit_id": estate.a2["id"], "version": tenant_version(estate.manager, tenant_id)},
    )
    assert response.status_code == 200
    assert unit_status(estate, estate.a1) == "vacant"
    assert unit_status(estate, estate.a2) == "occupied"
    assert tenant.get(ME).get_json()["unit"]["label"] == "A2"


def test_stale_tenant_update_is_rejected(estate: Estate) -> None:
    place_tenant(estate.manager, "tenant@example.com", estate.a1["id"])
    tenant_id = tenant_id_of(estate.manager, "tenant@example.com")
    version = tenant_version(estate.manager, tenant_id)
    url = f"{TENANTS}/{tenant_id}"
    first = estate.manager.patch(url, json={"phone": "+254712345678", "version": version})
    stale = estate.manager.patch(url, json={"phone": "+254700000000", "version": version})
    assert first.status_code == 200
    assert stale.status_code == 409


@pytest.mark.parametrize(
    ("phone", "expected"), [("+254712345678", 200), ("0712345678", 422), ("+0712", 422)]
)
def test_phone_numbers_must_use_international_format(
    estate: Estate, phone: str, expected: int
) -> None:
    place_tenant(estate.manager, "tenant@example.com", estate.a1["id"])
    tenant_id = tenant_id_of(estate.manager, "tenant@example.com")
    response = estate.manager.patch(
        f"{TENANTS}/{tenant_id}",
        json={"phone": phone, "version": tenant_version(estate.manager, tenant_id)},
    )
    assert response.status_code == expected


def test_deactivating_a_tenant_frees_the_unit_and_revokes_access(estate: Estate) -> None:
    tenant = place_tenant(estate.manager, "tenant@example.com", estate.a1["id"])
    tenant_id = tenant_id_of(estate.manager, "tenant@example.com")
    assert estate.manager.post(f"{TENANTS}/{tenant_id}/deactivate").status_code == 204
    assert unit_status(estate, estate.a1) == "vacant"
    assert tenant.get(ME).status_code == 403


def test_changing_a_tenants_role_frees_their_unit(estate: Estate) -> None:
    place_tenant(estate.manager, "tenant@example.com", estate.a1["id"])
    membership = membership_id_of(estate.owner, "tenant@example.com")
    response = estate.owner.patch(f"{MEMBERS}/{membership}", json={"role": "contractor"})
    assert response.status_code == 200
    assert unit_status(estate, estate.a1) == "vacant"


def test_tenants_cannot_list_or_invite_tenants(estate: Estate) -> None:
    tenant = place_tenant(estate.manager, "tenant@example.com", estate.a1["id"])
    assert tenant.get(TENANTS).status_code == 403
    invite = tenant.post(TENANTS, json={"email": "friend@example.com", "unit_id": estate.a1["id"]})
    assert invite.status_code == 403


def test_database_allows_invitation_units_only_for_tenants(estate: Estate) -> None:
    with estate.app.app_context():
        db.session.add(
            Invitation(
                organization_id=uuid.UUID(estate.org_id),
                email="manager.two@example.com",
                role="manager",
                unit_id=uuid.UUID(estate.a1["id"]),
                token_hash="a" * 64,
                invited_by_user_id=uuid.UUID(estate.owner.user_id),
                expires_at=datetime.now(UTC) + timedelta(days=1),
            )
        )
        with pytest.raises(IntegrityError):
            db.session.flush()
        db.session.rollback()
