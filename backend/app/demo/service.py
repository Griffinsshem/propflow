"""Private demo sandboxes (ADR 0021): build one per visitor, switch person inside it, purge it.

Everything is built through the services, as the people it names, so every rule applies and
the timelines and notifications read like real use. The organization is committed first, with
its expiry, so even a sandbox that fails halfway is deleted on schedule.
"""

from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Any

from sqlalchemy import delete, select

from app.auth import service as auth_service
from app.auth.models import User, UserSession
from app.auth.passwords import hash_password
from app.authz.context import OrgContext
from app.common.errors import DemoRestrictedError, NotFoundError
from app.contractors import service as contractors
from app.demo.guards import DEMO_EMAIL_DOMAIN
from app.extensions import db
from app.maintenance import service as maintenance
from app.organizations.models import MembershipRole, Organization, OrganizationMembership
from app.properties import service as properties
from app.tenants import service as tenants
from app.work_orders import service as work_orders

DEMO_LIFETIME = timedelta(hours=24)
NEVER_PURGED = frozenset({"audit_logs"})  # append-only; demos never write to it (ADR 0021)


def _now() -> datetime:
    return datetime.now(UTC)


def _uuid(value: Any) -> uuid.UUID:
    return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))


@lru_cache(maxsize=1)
def _unusable_password_hash() -> str:
    """A properly hashed random password nobody ever learns: once per process, it is slow."""
    return hash_password(secrets.token_urlsafe(32))


def _person(
    organization: Organization, role: MembershipRole, full_name: str
) -> tuple[User, OrganizationMembership]:
    user = User(
        email=f"demo-{uuid.uuid4().hex}@{DEMO_EMAIL_DOMAIN}",
        password_hash=_unusable_password_hash(),
        full_name=full_name,
        is_demo=True,
        email_verified_at=_now(),
    )
    db.session.add(user)
    db.session.flush()
    membership = OrganizationMembership(organization_id=organization.id, user_id=user.id, role=role)
    db.session.add(membership)
    db.session.flush()
    return user, membership


def _context(
    organization: Organization, user: User, membership: OrganizationMembership
) -> OrgContext:
    return OrgContext(
        user_id=user.id,
        organization_id=organization.id,
        membership_id=membership.id,
        role=MembershipRole(membership.role),
    )


def create_sandbox(
    *, ip_address: str | None, user_agent: str | None
) -> tuple[User, auth_service.IssuedSession]:
    now = _now()
    organization = Organization(
        name="Riverside Estates (demo)", is_demo=True, demo_expires_at=now + DEMO_LIFETIME
    )
    db.session.add(organization)
    db.session.flush()
    owner, owner_m = _person(organization, MembershipRole.OWNER, "Demo Owner")
    _manager, manager_m = _person(organization, MembershipRole.MANAGER, "Mary Manager")
    tom, tom_m = _person(organization, MembershipRole.TENANT, "Tom Tenant")
    tia, tia_m = _person(organization, MembershipRole.TENANT, "Tia Tenant")
    fred, fred_m = _person(organization, MembershipRole.CONTRACTOR, "Fred Fixit")
    db.session.commit()

    as_owner = _context(organization, owner, owner_m)
    as_tom = _context(organization, tom, tom_m)
    as_tia = _context(organization, tia, tia_m)
    as_fred = _context(organization, fred, fred_m)

    def place(name: str, address: str, description: str) -> uuid.UUID:
        created = properties.create_property(
            as_owner,
            {
                "name": name,
                "property_type": "residential",
                "address_line": address,
                "city": "Nairobi",
                "region": "Nairobi",
                "country_code": "KE",
                "description": description,
            },
        )
        return created.id

    def unit(property_id: uuid.UUID, label: str, floor: int, bedrooms: int) -> uuid.UUID:
        created = properties.create_unit(
            as_owner,
            {
                "property_id": property_id,
                "building_id": None,
                "label": label,
                "floor": floor,
                "bedrooms": bedrooms,
                "status": "vacant",
            },
        )
        return created.id

    court = place("Riverside Court", "12 Riverside Drive", "Three flats by the river.")
    hillside = place("Hillside Homes", "4 Hill Lane", "A family house with a shared hallway.")
    a1, a2 = unit(court, "A1", 1, 2), unit(court, "A2", 1, 1)
    unit(court, "B1", 2, 3)
    unit(hillside, "1", 0, 4)
    properties.assign_manager(as_owner, court, manager_m.id)
    tenants.place_tenant(organization.id, tom_m.id, a1)
    tenants.place_tenant(organization.id, tia_m.id, a2)
    plumbing = contractors.create_contractor(
        as_owner,
        {
            "business_name": "Fixit Plumbing",
            "contact_name": "Fred Fixit",
            "phone": "+254712000000",
            "email": None,
            "specialty": "plumbing",
        },
    )
    plumber_id = _uuid(plumbing["id"])
    contractors.link_membership(organization.id, plumber_id, fred_m.id)
    db.session.commit()

    # Tom's tap: reported, triaged, fixed by Fred, resolved by the owner.
    tap = maintenance.create_request(
        as_tom,
        {
            "category": "plumbing",
            "priority": "normal",
            "title": "Leaking kitchen tap",
            "description": "It drips all night and the cupboard under the sink is getting damp.",
        },
    )
    tap = maintenance.change_status(
        as_owner, _uuid(tap["id"]), to_status="triaged", reason=None, version=tap["version"]
    )
    job = work_orders.create_work_order(
        as_owner,
        {
            "request_id": _uuid(tap["id"]),
            "contractor_id": plumber_id,
            "description": "Replace the tap washer.",
            "due_date": (now + timedelta(days=2)).date(),
        },
    )
    for status in ("accepted", "in_progress", "completed"):
        job = work_orders.change_status(
            as_fred, _uuid(job["id"]), to_status=status, reason=None, version=job["version"]
        )
    maintenance.add_comment(as_tom, _uuid(tap["id"]), "All fixed, thank you!")
    tap = maintenance.get_request(as_owner, _uuid(tap["id"]))
    maintenance.change_status(
        as_owner, _uuid(tap["id"]), to_status="resolved", reason=None, version=tap["version"]
    )

    # Tia's hot water: urgent, accepted by Fred and in progress.
    hot = maintenance.create_request(
        as_tia,
        {
            "category": "plumbing",
            "priority": "urgent",
            "title": "No hot water",
            "description": "The water has been cold since this morning.",
        },
    )
    hot = maintenance.change_status(
        as_owner, _uuid(hot["id"]), to_status="triaged", reason=None, version=hot["version"]
    )
    job = work_orders.create_work_order(
        as_owner,
        {
            "request_id": _uuid(hot["id"]),
            "contractor_id": plumber_id,
            "description": "Check the boiler pressure first.",
            "due_date": (now + timedelta(days=1)).date(),
        },
    )
    for status in ("accepted", "in_progress"):
        job = work_orders.change_status(
            as_fred, _uuid(job["id"]), to_status=status, reason=None, version=job["version"]
        )
    maintenance.add_comment(
        as_fred, _uuid(hot["id"]), "On site. The boiler pressure was low; refilling and testing."
    )

    # The owner's own report: a common-area issue, waiting for triage.
    maintenance.create_request(
        as_owner,
        {
            "property_id": hillside,
            "category": "electrical",
            "priority": "normal",
            "title": "Hallway light flickering",
            "description": "Ground floor, near the stairs.",
        },
    )

    issued = auth_service.start_session(
        owner,
        ip_address=ip_address,
        user_agent=user_agent,
        expires_at=organization.demo_expires_at,
    )
    db.session.commit()
    return owner, issued


def view_as(
    current_session: UserSession,
    current_user: User,
    role: str,
    *,
    ip_address: str | None,
    user_agent: str | None,
) -> tuple[User, auth_service.IssuedSession]:
    """Switch the visitor to another person in their own sandbox, and nowhere else."""
    organization = (
        db.session.get(Organization, current_session.active_organization_id)
        if current_session.active_organization_id is not None
        else None
    )
    if not current_user.is_demo or organization is None or not organization.is_demo:
        raise DemoRestrictedError("Switching people is only available inside a demo.")
    target = db.session.execute(
        select(User)
        .join(OrganizationMembership, OrganizationMembership.user_id == User.id)
        .where(
            OrganizationMembership.organization_id == organization.id,
            OrganizationMembership.role == MembershipRole(role),
            User.is_demo.is_(True),
        )
        .order_by(User.full_name.desc())  # Tom before Tia: the tenant with the resolved repair
        .limit(1)
    ).scalar_one_or_none()
    if target is None:
        raise NotFoundError()
    auth_service.logout(current_session)
    issued = auth_service.start_session(
        target,
        ip_address=ip_address,
        user_agent=user_agent,
        expires_at=organization.demo_expires_at,
    )
    db.session.commit()
    return target, issued


def purge_sandbox(organization_id: uuid.UUID) -> None:
    """Delete one sandbox, children first (RESTRICT keys), then its demo people."""
    organization = db.session.get(Organization, organization_id)
    if organization is None:
        return
    if not organization.is_demo:
        raise RuntimeError(f"refusing to purge organization {organization_id}: not a demo")
    people = (
        db.session.execute(
            select(OrganizationMembership.user_id).where(
                OrganizationMembership.organization_id == organization_id
            )
        )
        .scalars()
        .all()
    )
    for table in reversed(db.metadata.sorted_tables):
        if table.name in NEVER_PURGED or table.name == "organizations":
            continue
        if "organization_id" in table.c:
            db.session.execute(delete(table).where(table.c.organization_id == organization_id))
    db.session.execute(delete(Organization).where(Organization.id == organization_id))
    if people:
        db.session.execute(delete(User).where(User.id.in_(people), User.is_demo.is_(True)))
    db.session.commit()


def purge_expired(now: datetime | None = None) -> int:
    expired = (
        db.session.execute(
            select(Organization.id).where(
                Organization.is_demo.is_(True), Organization.demo_expires_at <= (now or _now())
            )
        )
        .scalars()
        .all()
    )
    for organization_id in expired:
        purge_sandbox(organization_id)
    return len(expired)
