"""ADR 0010 / ADR 0018: contractors read their jobs' requests, photos included, and only
while the job is theirs."""

import io

from flask import Flask
from PIL import Image

from tests.support import (
    MAINTENANCE,
    WORK_ORDERS,
    Actor,
    contractor_user,
    create_contractor,
    create_organization,
    create_property,
    create_unit,
    create_work_order,
    move_request,
    place_tenant,
    report_issue,
    sign_up,
    upload_image,
)


def jpeg() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), "blue").save(buffer, "JPEG")
    return buffer.getvalue()


def test_contractors_see_their_jobs_photos_only_while_the_job_is_theirs(app: Flask) -> None:
    owner = sign_up(app, "owner@example.com", "Olivia Owner")
    create_organization(owner, "Riverside Estates")
    prop = create_property(owner, "Riverside Court")
    tenant = place_tenant(owner, "tenant@example.com", create_unit(owner, prop["id"], "A1")["id"])
    request = report_issue(tenant, title="Leaking pipe")
    assert upload_image(tenant, request["id"], jpeg()).status_code in (200, 202)
    assert move_request(owner, request["id"], "triaged").status_code == 200

    fixit = create_contractor(owner, "Fixit Plumbing")
    other = create_contractor(owner, "Other Fix")
    fixer = contractor_user(owner, fixit["id"], "fixer@example.com")
    stranger = contractor_user(owner, other["id"], "stranger@example.com")
    order = create_work_order(owner, request["id"], fixit["id"])

    def photos(actor: Actor) -> int:
        return int(actor.get(f"{MAINTENANCE}/{request['id']}/attachments").status_code)

    listed = fixer.get(f"{MAINTENANCE}/{request['id']}/attachments")
    assert listed.status_code == 200
    assert len(listed.get_json()) == 1
    assert listed.get_json()[0]["download_url"]
    # Another contractor cannot see the request at all.
    assert photos(stranger) == 404

    # Declining the job ends access to its request, photos included.
    declined = fixer.post(
        f"{WORK_ORDERS}/{order['id']}/status",
        json={"status": "declined", "reason": "Too far away", "version": order["version"]},
    )
    assert declined.status_code == 200, declined.get_json()
    assert photos(fixer) == 404
