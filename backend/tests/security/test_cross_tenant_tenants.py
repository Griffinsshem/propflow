"""Cross-tenant suite for tenant profiles (spec section 54)."""

import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.tenants.models import TenantProfile
from tests.support import (
    TENANTS,
    TwoOrgs,
    create_property,
    create_unit,
    membership_id_of,
    place_tenant,
    tenant_id_of,
)


def b_unit(two_orgs: TwoOrgs) -> str:
    prop = create_property(two_orgs.b_owner, "B Court")
    return str(create_unit(two_orgs.b_owner, prop["id"], "B1")["id"])


def test_cannot_read_update_or_deactivate_another_orgs_tenant(two_orgs: TwoOrgs) -> None:
    place_tenant(two_orgs.b_owner, "b.tenant@example.com", b_unit(two_orgs))
    tenant_id = tenant_id_of(two_orgs.b_owner, "b.tenant@example.com")
    url = f"{TENANTS}/{tenant_id}"
    a = two_orgs.a_owner
    assert a.get(url).status_code == 404
    assert a.patch(url, json={"phone": "+254700000000", "version": 1}).status_code == 404
    assert a.post(f"{url}/deactivate").status_code == 404
    assert a.get(TENANTS).get_json()["items"] == []


def test_cannot_invite_a_tenant_into_another_orgs_unit(two_orgs: TwoOrgs) -> None:
    response = two_orgs.a_owner.post(
        TENANTS, json={"email": "x@example.com", "unit_id": b_unit(two_orgs)}
    )
    assert response.status_code == 404


def test_cannot_move_own_tenant_into_another_orgs_unit(two_orgs: TwoOrgs) -> None:
    own_prop = create_property(two_orgs.a_owner, "A Court")
    own_unit = create_unit(two_orgs.a_owner, own_prop["id"], "A1")
    place_tenant(two_orgs.a_owner, "a.tenant@example.com", own_unit["id"])
    tenant_id = tenant_id_of(two_orgs.a_owner, "a.tenant@example.com")
    version = two_orgs.a_owner.get(f"{TENANTS}/{tenant_id}").get_json()["version"]
    response = two_orgs.a_owner.patch(
        f"{TENANTS}/{tenant_id}", json={"unit_id": b_unit(two_orgs), "version": version}
    )
    assert response.status_code == 404


def test_database_rejects_profile_pointing_at_another_orgs_unit(two_orgs: TwoOrgs) -> None:
    foreign_unit = b_unit(two_orgs)
    own_membership = membership_id_of(two_orgs.a_owner, "owner.a@example.com")
    with two_orgs.app.app_context():
        db.session.add(
            TenantProfile(
                organization_id=uuid.UUID(two_orgs.org_a),
                membership_id=uuid.UUID(own_membership),
                unit_id=uuid.UUID(foreign_unit),
            )
        )
        with pytest.raises(IntegrityError):
            db.session.flush()
        db.session.rollback()
