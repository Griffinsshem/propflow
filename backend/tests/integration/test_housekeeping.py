import io
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from flask import Flask
from PIL import Image
from sqlalchemy import func, select, update

from app.auth.models import UserSession
from app.common.storage import MemoryStorage
from app.extensions import db
from app.housekeeping import service
from app.maintenance.models import MaintenanceAttachment
from app.notifications.models import Notification
from tests.support import (
    MAINTENANCE,
    Actor,
    create_organization,
    create_property,
    create_unit,
    place_tenant,
    report_issue,
    sign_up,
    upload_image,
)

LONG_AGO = datetime.now(UTC) - timedelta(days=200)


@dataclass
class Ground:
    app: Flask
    owner: Actor
    tenant: Actor


@pytest.fixture()
def ground(app: Flask) -> Ground:
    owner = sign_up(app, "owner@example.com", "Olivia Owner")
    create_organization(owner, "Riverside Estates")
    prop = create_property(owner)
    tenant = place_tenant(owner, "tenant@example.com", create_unit(owner, prop["id"])["id"])
    return Ground(app, owner, tenant)


def jpeg() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (16, 16), "teal").save(buffer, "JPEG")
    return buffer.getvalue()


def start_upload(actor: Actor, request: dict[str, Any]) -> dict[str, Any]:
    response = actor.post(
        f"{MAINTENANCE}/{request['id']}/attachments",
        json={"content_type": "image/jpeg", "size_bytes": 100},
    )
    assert response.status_code == 201
    return dict(response.get_json())


def statuses(app: Flask) -> dict[str, str]:
    with app.app_context():
        rows = db.session.execute(select(MaintenanceAttachment.id, MaintenanceAttachment.status))
        return {str(row[0]): row[1] for row in rows}


def test_abandoned_uploads_are_rejected_but_fresh_ones_are_kept(ground: Ground) -> None:
    request = report_issue(ground.tenant)
    old = start_upload(ground.tenant, request)["attachment"]["id"]
    fresh = start_upload(ground.tenant, request)["attachment"]["id"]
    with ground.app.app_context():
        db.session.execute(
            update(MaintenanceAttachment)
            .where(MaintenanceAttachment.id == uuid.UUID(old))
            .values(created_at=datetime.now(UTC) - timedelta(days=2))
        )
        db.session.commit()
        assert service.recover_unfinished_uploads() == {"abandoned": 1, "requeued": 0}
        assert service.recover_unfinished_uploads() == {"abandoned": 0, "requeued": 0}
    assert statuses(ground.app) == {old: "rejected", fresh: "pending"}


def test_stuck_processing_is_picked_up_again(ground: Ground) -> None:
    request = report_issue(ground.tenant)
    body = start_upload(ground.tenant, request)
    storage: MemoryStorage = ground.app.extensions["storage"]
    storage.write(body["upload"]["url"].removeprefix("memory://upload/"), jpeg(), "image/jpeg")
    with ground.app.app_context():
        db.session.execute(
            update(MaintenanceAttachment).values(
                status="processing", created_at=datetime.now(UTC) - timedelta(hours=1)
            )
        )
        db.session.commit()
        assert service.recover_unfinished_uploads() == {"abandoned": 0, "requeued": 1}
    assert statuses(ground.app) == {body["attachment"]["id"]: "ready"}


def test_expired_and_revoked_sessions_are_purged(ground: Ground) -> None:
    with ground.app.app_context():
        db.session.execute(
            update(UserSession)
            .where(UserSession.user_id == uuid.UUID(ground.tenant.user_id))
            .values(revoked_at=datetime.now(UTC) - timedelta(days=8))
        )
        db.session.commit()
        assert service.purge_expired_sessions() == 1
        assert service.purge_expired_sessions() == 0
    assert ground.owner.get("/api/v1/auth/me").status_code == 200


def test_old_read_notifications_are_purged_and_recent_ones_kept(ground: Ground) -> None:
    report_issue(ground.tenant)
    report_issue(ground.tenant, title="Second issue")  # both notify the owner
    with ground.app.app_context():
        oldest = db.session.execute(
            select(Notification.id).order_by(Notification.created_at).limit(1)
        ).scalar_one()
        db.session.execute(
            update(Notification)
            .where(Notification.id == oldest)
            .values(read_at=datetime.now(UTC), created_at=datetime.now(UTC) - timedelta(days=100))
        )
        db.session.commit()
        assert service.purge_old_notifications() == 1
        remaining = db.session.execute(select(func.count()).select_from(Notification)).scalar_one()
    assert remaining == 1


def test_only_old_orphaned_objects_matching_our_pattern_are_removed(ground: Ground) -> None:
    request = report_issue(ground.tenant)
    upload_image(ground.tenant, request["id"], jpeg())
    storage: MemoryStorage = ground.app.extensions["storage"]
    live = next(key for key in storage.objects if key.startswith("orgs/"))
    org = live.split("/")[1]
    old_orphan = f"orgs/{org}/maintenance/{uuid.uuid4()}/{uuid.uuid4()}.jpg"
    fresh_orphan = f"orgs/{org}/maintenance/{uuid.uuid4()}/{uuid.uuid4()}.jpg"
    unknown = "orgs/readme.txt"
    for key in (old_orphan, fresh_orphan, unknown):
        storage.write(key, b"x", "application/octet-stream")
    for key in (live, old_orphan, unknown):
        storage.modified[key] = LONG_AGO
    with ground.app.app_context():
        assert service.remove_orphaned_objects() == 1
    assert old_orphan not in storage.objects
    assert {live, fresh_orphan, unknown} <= set(storage.objects)
