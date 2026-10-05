import smtplib
from collections.abc import Iterator
from typing import Any

import pytest
from flask import Flask

from app import create_app
from app.extensions import db
from app.notifications.email import EmailMessage, EmailTransportError, deliver_now

SMTP_CONFIG = {
    "EMAIL_BACKEND": "smtp",
    "SMTP_HOST": "smtp.provider.example",
    "SMTP_PORT": 587,
    "SMTP_SECURITY": "starttls",
    "SMTP_USERNAME": "apikey",
    "SMTP_PASSWORD": "secret-for-tests",
    "SMTP_TIMEOUT_SECONDS": 5,
    "MAIL_FROM": "PropFlow <no-reply@propflow.example>",
}
MESSAGE = EmailMessage(
    to="tenant@example.com", subject="Reset your password", body="Reset link: https://x/y"
)


class FakeSMTP:
    """Stands in for smtplib.SMTP: records calls, optionally fails like a real server."""

    def __init__(self, connect_error: BaseException | None, send_error: BaseException | None):
        self.connect_error = connect_error
        self.send_error = send_error
        self.calls: list[Any] = []
        self.sent: Any = None

    def __call__(self, host: str, port: int, timeout: int) -> "FakeSMTP":
        if self.connect_error is not None:
            raise self.connect_error
        self.calls.append(("connect", host, port, timeout))
        return self

    def __enter__(self) -> "FakeSMTP":
        return self

    def __exit__(self, *exc: object) -> None:
        self.calls.append("quit")

    def starttls(self, context: Any) -> None:
        assert context is not None
        self.calls.append("starttls")

    def login(self, username: str, password: str) -> None:
        self.calls.append(("login", username))

    def send_message(self, message: Any) -> None:
        if self.send_error is not None:
            raise self.send_error
        self.calls.append("send")
        self.sent = message


@pytest.fixture()
def smtp_app(migrated_database: None) -> Iterator[Flask]:
    application = create_app("test", overrides=SMTP_CONFIG)
    yield application
    with application.app_context():
        db.engine.dispose()


def fake_server(
    monkeypatch: pytest.MonkeyPatch,
    *,
    connect_error: BaseException | None = None,
    send_error: BaseException | None = None,
) -> FakeSMTP:
    server = FakeSMTP(connect_error, send_error)
    monkeypatch.setattr(smtplib, "SMTP", server)
    return server


def test_delivers_over_starttls_with_login(
    smtp_app: Flask, monkeypatch: pytest.MonkeyPatch
) -> None:
    server = fake_server(monkeypatch)
    with smtp_app.app_context():
        deliver_now(MESSAGE)
    assert server.calls == [
        ("connect", "smtp.provider.example", 587, 5),
        "starttls",
        ("login", "apikey"),
        "send",
        "quit",
    ]
    assert server.sent["To"] == "tenant@example.com"
    assert server.sent["From"] == "PropFlow <no-reply@propflow.example>"
    assert server.sent["Subject"] == "Reset your password"
    assert server.sent["Message-ID"].endswith("@propflow.example>")
    assert server.sent.get_content().rstrip("\n") == MESSAGE.body


@pytest.mark.parametrize(
    "error",
    [
        smtplib.SMTPResponseException(451, b"Try again later"),
        smtplib.SMTPAuthenticationError(535, b"Bad credentials"),
        smtplib.SMTPServerDisconnected("connection lost"),
    ],
)
def test_temporary_failures_are_retried(
    smtp_app: Flask, monkeypatch: pytest.MonkeyPatch, error: BaseException
) -> None:
    fake_server(monkeypatch, send_error=error)
    with smtp_app.app_context(), pytest.raises(EmailTransportError):
        deliver_now(MESSAGE)


def test_unreachable_server_is_retried(smtp_app: Flask, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_server(monkeypatch, connect_error=ConnectionRefusedError())
    with smtp_app.app_context(), pytest.raises(EmailTransportError):
        deliver_now(MESSAGE)


@pytest.mark.parametrize(
    "error",
    [
        smtplib.SMTPRecipientsRefused({"tenant@example.com": (550, b"No such user")}),
        smtplib.SMTPSenderRefused(550, b"Sender not verified", "no-reply@propflow.example"),
    ],
)
def test_permanent_rejections_are_not_retried(
    smtp_app: Flask, monkeypatch: pytest.MonkeyPatch, error: BaseException
) -> None:
    fake_server(monkeypatch, send_error=error)
    with smtp_app.app_context():
        deliver_now(MESSAGE)  # logged, not raised: retrying cannot succeed


def test_header_injection_is_refused(smtp_app: Flask, monkeypatch: pytest.MonkeyPatch) -> None:
    server = fake_server(monkeypatch)
    injected = EmailMessage(to="tenant@example.com", subject="Hi\nBcc: x@evil.example", body=".")
    with smtp_app.app_context(), pytest.raises(ValueError):
        deliver_now(injected)
    assert "send" not in server.calls
