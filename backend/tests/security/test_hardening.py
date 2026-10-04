from collections.abc import Iterator

import pytest
from flask import Flask
from flask.testing import FlaskClient

from app import create_app
from app.common.middleware import API_CSP
from app.extensions import db

PROXY_SECRET = "proxy-secret-for-tests-" + "x" * 20


@pytest.fixture()
def hardened_app(migrated_database: None) -> Iterator[Flask]:
    application = create_app(
        "test", overrides={"HSTS_ENABLED": True, "PROXY_SHARED_SECRET": PROXY_SECRET}
    )
    yield application
    with application.app_context():
        db.engine.dispose()


def test_api_responses_carry_a_locked_down_policy(client: FlaskClient) -> None:
    headers = client.get("/api/v1/auth/me").headers
    assert headers["Content-Security-Policy"] == API_CSP
    assert headers["Cross-Origin-Opener-Policy"] == "same-origin"
    assert headers["Cross-Origin-Resource-Policy"] == "same-origin"
    assert "geolocation=()" in headers["Permissions-Policy"]
    assert "Strict-Transport-Security" not in headers  # never over plain-HTTP development


def test_hsts_is_sent_when_enabled(hardened_app: Flask) -> None:
    headers = hardened_app.test_client().get("/health").headers
    assert headers["Strict-Transport-Security"].startswith("max-age=")


def test_requests_that_bypass_the_proxy_are_refused(hardened_app: Flask) -> None:
    client = hardened_app.test_client()
    assert client.get("/api/v1/auth/me").status_code == 403
    wrong = client.get("/api/v1/auth/me", headers={"X-Proxy-Secret": "guess"})
    assert wrong.status_code == 403
    # With the secret the request reaches the API (and is then simply unauthenticated).
    right = client.get("/api/v1/auth/me", headers={"X-Proxy-Secret": PROXY_SECRET})
    assert right.status_code == 401


def test_health_checks_do_not_need_the_proxy_secret(hardened_app: Flask) -> None:
    assert hardened_app.test_client().get("/health").status_code == 200
