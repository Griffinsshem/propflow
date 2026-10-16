"""Checks shared by the modules that behave differently inside demo sandboxes (ADR 0021)."""

from __future__ import annotations

import uuid

import structlog

from app.common.errors import DemoRestrictedError
from app.extensions import db
from app.organizations.models import Organization

# The reserved .invalid top-level domain can never receive mail (RFC 2606).
DEMO_EMAIL_DOMAIN = "demo.propflow.invalid"

logger = structlog.get_logger(__name__)


def is_demo_organization(organization_id: uuid.UUID | None) -> bool:
    if organization_id is None:
        return False
    organization = db.session.get(Organization, organization_id)
    return organization is not None and organization.is_demo


def ensure_not_demo(organization_id: uuid.UUID) -> None:
    if is_demo_organization(organization_id):
        raise DemoRestrictedError()


def is_demo_address(email: str) -> bool:
    return email.strip().lower().endswith(".invalid")


def log_suppressed_email(subject: str) -> None:
    logger.info("demo_email_suppressed", subject=subject)
