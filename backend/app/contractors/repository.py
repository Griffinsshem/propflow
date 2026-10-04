"""Data access for contractor records. Every query is organization-scoped."""

from __future__ import annotations

import uuid

from sqlalchemy import Select, select

from app.contractors.models import Contractor
from app.extensions import db


def contractors_query(organization_id: uuid.UUID) -> Select[Contractor]:
    return select(Contractor).where(Contractor.organization_id == organization_id)


def get_contractor(organization_id: uuid.UUID, contractor_id: uuid.UUID) -> Contractor | None:
    stmt = contractors_query(organization_id).where(Contractor.id == contractor_id)
    return db.session.execute(stmt).scalar_one_or_none()


def get_by_membership(organization_id: uuid.UUID, membership_id: uuid.UUID) -> Contractor | None:
    stmt = contractors_query(organization_id).where(Contractor.membership_id == membership_id)
    return db.session.execute(stmt).scalar_one_or_none()
