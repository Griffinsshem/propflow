import hashlib
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from flask import Flask
from flask.testing import FlaskClient
from sqlalchemy import select, update
from werkzeug.test import TestResponse

from app.auth.models import User, UserSession
from app.extensions import db

PASSWORD = "correct horse battery staple"
SESSION_COOKIE = "propflow_session"
CSRF_COOKIE = "propflow_csrf"
REGISTER = "/api/v1/auth/register"
LOGIN = "/api/v1/auth/login"
LOGOUT = "/api/v1/auth/logout"
ME = "/api/v1/auth/me"


def register(client: FlaskClient, **overrides: Any) -> TestResponse:
    payload = {"email": "manager@example.com", "password": PASSWORD, "full_name": "Test Manager"}
    return client.post(REGISTER, json=payload | overrides)


def csrf_headers(client: FlaskClient) -> dict[str, str]:
    cookie = client.get_cookie(CSRF_COOKIE)
    assert cookie is not None
    return {"X-CSRF-Token": cookie.value}


class TestRegistration:
    def test_creates_account_and_starts_session(self, client: FlaskClient) -> None:
        response = register(client)
        assert response.status_code == 201
        body = response.get_json()
        assert body["email"] == "manager@example.com"
        assert body["memberships"] == []
        assert "password" not in body and "password_hash" not in body
        cookies = " ".join(response.headers.getlist("Set-Cookie"))
        assert f"{SESSION_COOKIE}=" in cookies
        assert "HttpOnly" in cookies and "SameSite=Lax" in cookies

    def test_email_is_normalized_to_lowercase(self, client: FlaskClient) -> None:
        assert register(client, email="Mixed.Case@Example.COM").get_json()["email"] == (
            "mixed.case@example.com"
        )

    def test_password_is_stored_as_argon2id_hash(self, app: Flask, client: FlaskClient) -> None:
        register(client)
        with app.app_context():
            stored = db.session.execute(select(User)).scalar_one().password_hash
        assert stored.startswith("$argon2id$")
        assert PASSWORD not in stored

    def test_duplicate_email_conflicts_case_insensitively(self, app: Flask) -> None:
        register(app.test_client())
        response = register(app.test_client(), email="MANAGER@example.com")
        assert response.status_code == 409
        assert response.get_json()["error"]["code"] == "CONFLICT"

    @pytest.mark.parametrize(
        ("overrides", "field"),
        [
            ({"password": "short"}, "password"),
            ({"full_name": "   "}, "full_name"),
            ({"email": "not-an-email"}, "email"),
        ],
    )
    def test_invalid_input_is_rejected(
        self, client: FlaskClient, overrides: dict[str, str], field: str
    ) -> None:
        response = register(client, **overrides)
        assert response.status_code == 422
        error = response.get_json()["error"]
        assert error["code"] == "VALIDATION_ERROR"
        assert field in error["details"]["json"]

    def test_unknown_fields_are_rejected(self, client: FlaskClient) -> None:
        """Mass-assignment protection: clients cannot set server-controlled fields."""
        response = register(client, is_active=False, email_verified_at="2026-01-01T00:00:00Z")
        assert response.status_code == 422


class TestLogin:
    def test_valid_credentials_start_a_session(self, app: Flask) -> None:
        register(app.test_client())
        client = app.test_client()
        response = client.post(LOGIN, json={"email": "manager@example.com", "password": PASSWORD})
        assert response.status_code == 200
        assert client.get(ME).status_code == 200

    def test_wrong_password_and_unknown_email_are_indistinguishable(self, app: Flask) -> None:
        register(app.test_client())
        wrong = app.test_client().post(
            LOGIN, json={"email": "manager@example.com", "password": "not the password"}
        )
        unknown = app.test_client().post(
            LOGIN, json={"email": "nobody@example.com", "password": PASSWORD}
        )
        assert wrong.status_code == unknown.status_code == 401
        assert wrong.get_json()["error"]["message"] == unknown.get_json()["error"]["message"]

    def test_deactivated_user_cannot_log_in(self, app: Flask) -> None:
        register(app.test_client())
        with app.app_context():
            db.session.execute(update(User).values(is_active=False))
            db.session.commit()
        response = app.test_client().post(
            LOGIN, json={"email": "manager@example.com", "password": PASSWORD}
        )
        assert response.status_code == 401


class TestSessions:
    def test_me_requires_authentication(self, client: FlaskClient) -> None:
        response = client.get(ME)
        assert response.status_code == 401
        assert response.get_json()["error"]["code"] == "UNAUTHENTICATED"

    def test_session_token_is_stored_only_as_hash(self, app: Flask, client: FlaskClient) -> None:
        register(client)
        cookie = client.get_cookie(SESSION_COOKIE)
        assert cookie is not None
        with app.app_context():
            stored = db.session.execute(select(UserSession)).scalar_one().token_hash
        assert stored == hashlib.sha256(cookie.value.encode()).hexdigest()
        assert stored != cookie.value

    def test_logout_revokes_the_session_server_side(self, client: FlaskClient) -> None:
        register(client)
        cookie = client.get_cookie(SESSION_COOKIE)
        assert cookie is not None
        stolen_token = cookie.value
        assert client.post(LOGOUT, headers=csrf_headers(client)).status_code == 204
        client.set_cookie(SESSION_COOKIE, stolen_token)  # replay the old cookie
        assert client.get(ME).status_code == 401

    def test_idle_session_expires(self, app: Flask, client: FlaskClient) -> None:
        register(client)
        with app.app_context():
            db.session.execute(
                update(UserSession).values(last_seen_at=datetime.now(UTC) - timedelta(days=4))
            )
            db.session.commit()
        assert client.get(ME).status_code == 401


class TestCsrfAndOrigin:
    def test_authenticated_unsafe_request_without_token_is_rejected(
        self, client: FlaskClient
    ) -> None:
        register(client)
        response = client.post(LOGOUT)
        assert response.status_code == 403
        assert response.get_json()["error"]["code"] == "FORBIDDEN"

    def test_forged_token_is_rejected(self, client: FlaskClient) -> None:
        register(client)
        assert client.post(LOGOUT, headers={"X-CSRF-Token": "0" * 64}).status_code == 403

    def test_cross_origin_request_is_rejected(self, client: FlaskClient) -> None:
        response = client.post(
            LOGIN,
            json={"email": "manager@example.com", "password": PASSWORD},
            headers={"Origin": "https://evil.example"},
        )
        assert response.status_code == 403
