"""Composite foreign keys: the database rejects cross-organization links even if code is buggy."""

import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.properties.models import Building, Unit
from tests.support import PROPERTIES, TwoOrgs, create_property


def test_building_cannot_reference_another_organizations_property(two_orgs: TwoOrgs) -> None:
    prop_b = create_property(two_orgs.b_owner, "B Court")
    with two_orgs.app.app_context():
        db.session.add(
            Building(
                organization_id=uuid.UUID(two_orgs.org_a),
                property_id=uuid.UUID(prop_b["id"]),
                name="Sneaky",
            )
        )
        with pytest.raises(IntegrityError):
            db.session.flush()
        db.session.rollback()


def test_unit_cannot_reference_another_organizations_property(two_orgs: TwoOrgs) -> None:
    prop_b = create_property(two_orgs.b_owner, "B Court")
    with two_orgs.app.app_context():
        db.session.add(
            Unit(
                organization_id=uuid.UUID(two_orgs.org_a),
                property_id=uuid.UUID(prop_b["id"]),
                label="X1",
            )
        )
        with pytest.raises(IntegrityError):
            db.session.flush()
        db.session.rollback()


def test_unit_cannot_use_a_building_from_another_property(two_orgs: TwoOrgs) -> None:
    owner = two_orgs.a_owner
    first = create_property(owner, "First Court")
    second = create_property(owner, "Second Court")
    building = owner.post(
        f"{PROPERTIES}/{first['id']}/buildings", json={"name": "Block A"}
    ).get_json()
    with two_orgs.app.app_context():
        db.session.add(
            Unit(
                organization_id=uuid.UUID(two_orgs.org_a),
                property_id=uuid.UUID(second["id"]),
                building_id=uuid.UUID(building["id"]),
                label="X1",
            )
        )
        with pytest.raises(IntegrityError):
            db.session.flush()
        db.session.rollback()
