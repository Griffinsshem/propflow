"""Cross-tenant suite for maintenance attachments (spec section 54)."""

import io

from PIL import Image

from tests.support import (
    MAINTENANCE,
    TwoOrgs,
    create_property,
    create_unit,
    report_issue,
    upload_image,
)


def _jpeg() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (16, 16), "teal").save(buffer, "JPEG")
    return buffer.getvalue()


def test_cannot_list_upload_to_or_complete_another_orgs_attachments(two_orgs: TwoOrgs) -> None:
    prop = create_property(two_orgs.b_owner, "B Court")
    unit = create_unit(two_orgs.b_owner, prop["id"], "B1")
    request = report_issue(two_orgs.b_owner, unit_id=unit["id"])
    attachment = upload_image(two_orgs.b_owner, request["id"], _jpeg()).get_json()
    base = f"{MAINTENANCE}/{request['id']}/attachments"
    a = two_orgs.a_owner
    assert a.get(base).status_code == 404
    assert a.post(base, json={"content_type": "image/jpeg", "size_bytes": 10}).status_code == 404
    assert a.post(f"{base}/{attachment['id']}/complete").status_code == 404
    assert len(two_orgs.b_owner.get(base).get_json()) == 1
