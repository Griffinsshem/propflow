"""The demo API (ADR 0021): starting a sandbox, its rate limit, and who may switch person."""

from __future__ import annotations

import uuid

from flask import Flask

from tests import support

DEMO = "/api/v1/demo"


def test_starting_a_demo_signs_the_visitor_into_their_own_sandbox(app: Flask) -> None:
    client = app.test_client()
    response = client.post(DEMO, environ_base={"REMOTE_ADDR": "198.51.100.10"})
    assert response.status_code == 201, response.get_json()
    body = response.get_json()
    assert body["is_demo"] is True
    assert body["demo_expires_at"] is not None
    assert body["full_name"] == "Demo Owner"
    assert [m["role"] for m in body["memberships"]] == ["owner"]
    assert body["memberships"][0]["organization_name"].endswith("(demo)")
    assert response.headers.getlist("Set-Cookie"), "the demo must sign the visitor in"

    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.get_json()["is_demo"] is True


def test_starting_demos_is_rate_limited_per_visitor(rate_limited_app: Flask) -> None:
    # A fresh client per attempt: no cookies carried over, only the same IP address.
    visitor = {"REMOTE_ADDR": "198.51.100.11"}
    statuses = [
        rate_limited_app.test_client().post(DEMO, environ_base=visitor).status_code
        for _ in range(6)
    ]
    assert statuses == [201] * 5 + [429], statuses
    other = rate_limited_app.test_client().post(DEMO, environ_base={"REMOTE_ADDR": "198.51.100.12"})
    assert other.status_code == 201, "another visitor has their own allowance"


def test_real_accounts_cannot_switch_person(app: Flask) -> None:
    real = support.sign_up(app, f"real-{uuid.uuid4().hex}@example.com", "Real Person")
    refused = real.post(f"{DEMO}/view-as", json={"role": "tenant"})
    assert refused.status_code == 403
    assert refused.get_json()["error"]["code"] == "DEMO_RESTRICTED"
    invalid = real.post(f"{DEMO}/view-as", json={"role": "landlord"})
    assert invalid.status_code == 422


def test_real_accounts_see_no_demo_fields_set(app: Flask) -> None:
    real = support.sign_up(app, f"real-{uuid.uuid4().hex}@example.com", "Real Person")
    me = real.get("/api/v1/auth/me").get_json()
    assert me["is_demo"] is False
    assert me["demo_expires_at"] is None
