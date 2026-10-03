import io
from dataclasses import dataclass
from typing import Any

import pytest
from flask import Flask
from PIL import Image
from sqlalchemy import select

from app.common.storage import MemoryStorage, StorageUnavailableError
from app.extensions import db
from app.maintenance import attachments, images
from app.maintenance.models import MaintenanceAttachment
from tests.support import (
    MAINTENANCE,
    Actor,
    assign_manager,
    create_organization,
    create_property,
    create_unit,
    join_via_invitation,
    membership_id_of,
    place_tenant,
    report_issue,
    sign_up,
    upload_image,
)


@dataclass
class Scene:
    app: Flask
    manager: Actor
    tenant: Actor
    neighbour: Actor


@pytest.fixture()
def scene(app: Flask) -> Scene:
    owner = sign_up(app, "owner@example.com", "Olivia Owner")
    create_organization(owner, "Riverside Estates")
    prop = create_property(owner, "Riverside Court")
    manager = join_via_invitation(owner, "manager@example.com", "manager", "Mary Manager")
    assign_manager(owner, prop["id"], membership_id_of(owner, "manager@example.com"))
    tenant = place_tenant(manager, "tenant@example.com", create_unit(owner, prop["id"], "A1")["id"])
    neighbour = place_tenant(
        manager, "neighbour@example.com", create_unit(owner, prop["id"], "A2")["id"]
    )
    return Scene(app, manager, tenant, neighbour)


def jpeg(width: int = 64, height: int = 48, **save_options: Any) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), "teal").save(buffer, "JPEG", **save_options)
    return buffer.getvalue()


def stored(scene: Scene) -> MemoryStorage:
    storage: MemoryStorage = scene.app.extensions["storage"]
    return storage


def final_bytes(scene: Scene) -> bytes:
    finals = [data for key, (data, _) in stored(scene).objects.items() if key.startswith("orgs/")]
    assert len(finals) == 1
    return finals[0]


def attachments_url(request: dict[str, Any]) -> str:
    return f"{MAINTENANCE}/{request['id']}/attachments"


def test_tenant_photo_becomes_ready_and_is_listed_with_a_signed_link(scene: Scene) -> None:
    request = report_issue(scene.tenant)
    response = upload_image(scene.tenant, request["id"], jpeg())
    assert response.status_code == 200
    attachment = response.get_json()
    assert attachment["status"] == "ready"
    assert (attachment["width"], attachment["height"]) == (64, 48)
    listed = scene.manager.get(attachments_url(request)).get_json()
    assert [item["id"] for item in listed] == [attachment["id"]]
    assert listed[0]["download_url"].startswith("memory://download/orgs/")
    assert not [key for key in stored(scene).objects if key.startswith("pending/")]


def test_upload_instructions_are_short_lived_and_bound_to_the_content_type(scene: Scene) -> None:
    request = report_issue(scene.tenant)
    body = scene.tenant.post(
        attachments_url(request), json={"content_type": "image/png", "size_bytes": 100}
    ).get_json()
    assert body["upload"]["method"] == "PUT"
    assert body["upload"]["headers"] == {"Content-Type": "image/png"}
    assert body["upload"]["expires_in"] <= 300
    assert body["attachment"]["status"] == "pending"


def test_photo_metadata_is_stripped(scene: Scene) -> None:
    exif = Image.Exif()
    exif[0x0110] = "SecretCam 3000"  # camera model tag, standing in for GPS data
    request = report_issue(scene.tenant)
    assert upload_image(scene.tenant, request["id"], jpeg(exif=exif.tobytes())).status_code == 200
    data = final_bytes(scene)
    assert b"SecretCam" not in data
    assert 0x0110 not in Image.open(io.BytesIO(data)).getexif()


def test_payloads_appended_to_images_are_discarded(scene: Scene) -> None:
    request = report_issue(scene.tenant)
    polyglot = jpeg() + b"<script>alert(1)</script>"
    assert upload_image(scene.tenant, request["id"], polyglot).status_code == 200
    assert b"<script>" not in final_bytes(scene)


def test_content_must_match_the_declared_type(scene: Scene) -> None:
    request = report_issue(scene.tenant)
    response = upload_image(scene.tenant, request["id"], jpeg(), content_type="image/png")
    assert response.status_code == 422
    assert scene.tenant.get(attachments_url(request)).get_json() == []


def test_non_images_are_rejected_and_deleted(scene: Scene) -> None:
    request = report_issue(scene.tenant)
    response = upload_image(scene.tenant, request["id"], b"%PDF-1.7 definitely not an image")
    assert response.status_code == 422
    assert stored(scene).objects == {}


def test_oversized_dimensions_are_rejected(scene: Scene, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(images, "MAX_PIXELS", 1000)
    request = report_issue(scene.tenant)
    assert upload_image(scene.tenant, request["id"], jpeg(64, 48)).status_code == 422


@pytest.mark.parametrize(
    "payload",
    [
        {"content_type": "image/gif", "size_bytes": 10},
        {"content_type": "image/jpeg", "size_bytes": 10 * 1024 * 1024 + 1},
        {"content_type": "image/jpeg", "size_bytes": 0},
        {"content_type": "text/html", "size_bytes": 10},
    ],
)
def test_upload_requests_are_validated(scene: Scene, payload: dict[str, Any]) -> None:
    request = report_issue(scene.tenant)
    assert scene.tenant.post(attachments_url(request), json=payload).status_code == 422


def test_completing_before_uploading_is_a_conflict(scene: Scene) -> None:
    request = report_issue(scene.tenant)
    body = scene.tenant.post(
        attachments_url(request), json={"content_type": "image/jpeg", "size_bytes": 100}
    ).get_json()
    response = scene.tenant.post(f"{attachments_url(request)}/{body['attachment']['id']}/complete")
    assert response.status_code == 409


def test_only_the_uploader_can_complete_an_upload(scene: Scene) -> None:
    request = report_issue(scene.tenant)
    body = scene.tenant.post(
        attachments_url(request), json={"content_type": "image/jpeg", "size_bytes": 100}
    ).get_json()
    response = scene.manager.post(f"{attachments_url(request)}/{body['attachment']['id']}/complete")
    assert response.status_code == 404


def test_attachment_count_is_limited(scene: Scene, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(attachments, "MAX_ATTACHMENTS_PER_REQUEST", 1)
    request = report_issue(scene.tenant)
    payload = {"content_type": "image/jpeg", "size_bytes": 100}
    assert scene.tenant.post(attachments_url(request), json=payload).status_code == 201
    assert scene.tenant.post(attachments_url(request), json=payload).status_code == 409


def test_other_tenants_cannot_see_attachments(scene: Scene) -> None:
    request = report_issue(scene.tenant)
    upload_image(scene.tenant, request["id"], jpeg())
    assert scene.neighbour.get(attachments_url(request)).status_code == 404


class _UnreachableStorage(MemoryStorage):
    def size(self, key: str) -> int | None:
        raise StorageUnavailableError()


def test_storage_outage_fails_clearly_and_leaves_the_upload_pending(scene: Scene) -> None:
    request = report_issue(scene.tenant)
    body = scene.tenant.post(
        attachments_url(request), json={"content_type": "image/jpeg", "size_bytes": 100}
    ).get_json()
    scene.app.extensions["storage"] = _UnreachableStorage()
    response = scene.tenant.post(f"{attachments_url(request)}/{body['attachment']['id']}/complete")
    assert response.status_code == 503
    assert response.get_json()["error"]["code"] == "STORAGE_UNAVAILABLE"
    with scene.app.app_context():
        status = db.session.execute(select(MaintenanceAttachment.status)).scalar_one()
    assert status == "pending"
