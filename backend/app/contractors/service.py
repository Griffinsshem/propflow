"""Contractor record use cases (spec 3.8). One transaction each."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError

from app.audit import service as audit
from app.authz.context import OrgContext
from app.common.errors import ConflictError, NotFoundError
from app.common.pagination import paginate
from app.contractors import repository
from app.contractors.models import Contractor
from app.extensions import db

STALE = "This contractor was changed by someone else. Reload it and try again."
DUPLICATE = "A contractor with this business name already exists."
PRIVATE_FIELDS = frozenset({"phone", "email"})  # changes are audited without their values


def _clean(value: Any) -> Any:
    return (value.strip() or None) if isinstance(value, str) else value


def contractor_view(contractor: Contractor) -> dict[str, Any]:
    return {
        "id": contractor.id,
        "business_name": contractor.business_name,
        "contact_name": contractor.contact_name,
        "phone": contractor.phone,
        "email": contractor.email,
        "specialty": contractor.specialty,
        "status": contractor.status,
        "has_login": contractor.membership_id is not None,
        "version": contractor.version,
        "created_at": contractor.created_at,
        "updated_at": contractor.updated_at,
    }


def _commit() -> None:
    try:
        db.session.commit()
    except StaleDataError as exc:
        db.session.rollback()
        raise ConflictError(STALE) from exc
    except IntegrityError as exc:
        db.session.rollback()
        raise ConflictError(DUPLICATE) from exc


def _contractor_or_404(context: OrgContext, contractor_id: uuid.UUID) -> Contractor:
    contractor = repository.get_contractor(context.organization_id, contractor_id)
    if contractor is None:
        raise NotFoundError()
    return contractor


def list_contractors(
    context: OrgContext,
    *,
    status: str | None,
    specialty: str | None,
    limit: int,
    cursor: str | None,
) -> tuple[list[dict[str, Any]], str | None]:
    stmt = repository.contractors_query(context.organization_id)
    if status is not None:
        stmt = stmt.where(Contractor.status == status)
    if specialty is not None:
        stmt = stmt.where(Contractor.specialty == specialty)
    items, next_cursor = paginate(
        stmt,
        created_column=Contractor.created_at,
        id_column=Contractor.id,
        limit=limit,
        cursor=cursor,
    )
    return [contractor_view(item) for item in items], next_cursor


def get_contractor(context: OrgContext, contractor_id: uuid.UUID) -> dict[str, Any]:
    return contractor_view(_contractor_or_404(context, contractor_id))


def create_contractor(context: OrgContext, data: dict[str, Any]) -> dict[str, Any]:
    email = _clean(data.get("email"))
    contractor = Contractor(
        organization_id=context.organization_id,
        business_name=data["business_name"].strip(),
        contact_name=_clean(data.get("contact_name")),
        phone=_clean(data.get("phone")),
        email=email.lower() if email else None,
        specialty=data["specialty"],
    )
    db.session.add(contractor)
    try:
        db.session.flush()
    except IntegrityError as exc:
        db.session.rollback()
        raise ConflictError(DUPLICATE) from exc
    audit.record(
        "contractor.created",
        "contractor",
        contractor.id,
        organization_id=context.organization_id,
        details={"business_name": contractor.business_name},
    )
    _commit()
    return contractor_view(contractor)


def update_contractor(
    context: OrgContext, contractor_id: uuid.UUID, data: dict[str, Any]
) -> dict[str, Any]:
    contractor = _contractor_or_404(context, contractor_id)
    if contractor.version != data.pop("version"):
        raise ConflictError(STALE)
    diff: dict[str, Any] = {}
    for field, raw in data.items():
        value = _clean(raw)
        if field == "email" and value:
            value = value.lower()
        current = getattr(contractor, field)
        if current != value:
            diff[field] = "changed" if field in PRIVATE_FIELDS else {"from": current, "to": value}
            setattr(contractor, field, value)
    if diff:
        audit.record(
            "contractor.updated",
            "contractor",
            contractor.id,
            organization_id=context.organization_id,
            details=diff,
        )
    _commit()
    return contractor_view(contractor)


def link_membership(
    organization_id: uuid.UUID, contractor_id: uuid.UUID, membership_id: uuid.UUID
) -> None:
    """Hook for invitation acceptance: the new contractor login represents this record."""
    contractor = repository.get_contractor(organization_id, contractor_id)
    if contractor is None:
        return
    previous = repository.get_by_membership(organization_id, membership_id)
    if previous is not None and previous.id != contractor.id:
        previous.membership_id = None
        db.session.flush()
    contractor.membership_id = membership_id
