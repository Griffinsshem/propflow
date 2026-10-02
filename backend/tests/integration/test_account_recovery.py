import re

import pytest
from flask import Flask
from flask.testing import FlaskClient

from app.auth import tokens
from app.notifications.email import EmailMessage

EMAIL = "tenant@example.com"
PASSWORD = "correct horse battery staple"
NEW_PASSWORD = "a brand new long password"
REGISTER = "/api/v1/auth/register"
LOGIN = "/api/v1/auth/login"
ME = "/api/v1/auth/me"
FORGOT = "/api/v1/auth/forgot-password"
RESET = "/api/v1/auth/reset-password"
VERIFY = "/api/v1/auth/verify-email"
TOKEN_IN_LINK = re.compile(r"#token=([A-Za-z0-9_.\-]+)")


def outbox(app: Flask) -> list[EmailMessage]:
    messages: list[EmailMessage] = app.extensions["outbox"]
    return messages


def token_from(message: EmailMessage) -> str:
    match = TOKEN_IN_LINK.search(message.body)
    assert match is not None
    return match.group(1)


def register(app: Flask) -> FlaskClient:
    client = app.test_client()
    payload = {"email": EMAIL, "password": PASSWORD, "full_name": "Test Tenant"}
    assert client.post(REGISTER, json=payload).status_code == 201
    return client


def request_reset_token(app: Flask) -> str:
    assert app.test_client().post(FORGOT, json={"email": EMAIL}).status_code == 202
    return token_from(outbox(app)[-1])


def login_status(app: Flask, password: str) -> int:
    response = app.test_client().post(LOGIN, json={"email": EMAIL, "password": password})
    return response.status_code


class TestPasswordReset:
    def test_unknown_email_gets_identical_response_and_no_email(self, app: Flask) -> None:
        register(app)
        outbox(app).clear()
        known = app.test_client().post(FORGOT, json={"email": EMAIL})
        unknown = app.test_client().post(FORGOT, json={"email": "nobody@example.com"})
        assert known.status_code == unknown.status_code == 202
        assert known.get_json() == unknown.get_json()
        assert [message.to for message in outbox(app)] == [EMAIL]

    def test_reset_link_keeps_token_out_of_query_string(self, app: Flask) -> None:
        register(app)
        request_reset_token(app)
        body = outbox(app)[-1].body
        assert "#token=" in body
        assert "?token=" not in body

    def test_reset_changes_password_and_revokes_existing_sessions(self, app: Flask) -> None:
        existing_session = register(app)
        token = request_reset_token(app)
        response = app.test_client().post(
            RESET, json={"token": token, "new_password": NEW_PASSWORD}
        )
        assert response.status_code == 204
        assert existing_session.get(ME).status_code == 401
        assert login_status(app, PASSWORD) == 401
        assert login_status(app, NEW_PASSWORD) == 200

    def test_reset_link_works_only_once(self, app: Flask) -> None:
        register(app)
        token = request_reset_token(app)
        first = app.test_client().post(RESET, json={"token": token, "new_password": NEW_PASSWORD})
        second = app.test_client().post(
            RESET, json={"token": token, "new_password": "yet another long password"}
        )
        assert first.status_code == 204
        assert second.status_code == 400
        assert second.get_json()["error"]["code"] == "INVALID_TOKEN"

    def test_expired_link_is_rejected(self, app: Flask, monkeypatch: pytest.MonkeyPatch) -> None:
        register(app)
        token = request_reset_token(app)
        monkeypatch.setattr(tokens, "PASSWORD_RESET_MAX_AGE", -1)
        response = app.test_client().post(
            RESET, json={"token": token, "new_password": NEW_PASSWORD}
        )
        assert response.status_code == 400

    def test_tampered_link_is_rejected(self, app: Flask) -> None:
        register(app)
        token = request_reset_token(app)
        tampered = token[:-2] + ("bb" if token.endswith("aa") else "aa")
        response = app.test_client().post(
            RESET, json={"token": tampered, "new_password": NEW_PASSWORD}
        )
        assert response.status_code == 400

    def test_new_password_must_meet_policy(self, app: Flask) -> None:
        register(app)
        token = request_reset_token(app)
        response = app.test_client().post(RESET, json={"token": token, "new_password": "short"})
        assert response.status_code == 422


class TestEmailVerification:
    def test_registration_sends_verification_link(self, app: Flask) -> None:
        register(app)
        assert outbox(app)[-1].to == EMAIL
        assert "/verify-email#token=" in outbox(app)[-1].body

    def test_verifying_marks_email_as_verified(self, app: Flask) -> None:
        client = register(app)
        token = token_from(outbox(app)[-1])
        assert app.test_client().post(VERIFY, json={"token": token}).status_code == 204
        assert client.get(ME).get_json()["email_verified"] is True

    def test_reset_token_cannot_be_used_as_verification_token(self, app: Flask) -> None:
        register(app)
        reset_token = request_reset_token(app)
        response = app.test_client().post(VERIFY, json={"token": reset_token})
        assert response.status_code == 400
