from typing import Any

import pytest
from flask import Flask
from kombu.exceptions import OperationalError

from app.notifications import tasks
from app.notifications.email import EmailTransportError
from tests.support import sign_up


def test_async_delivery_runs_through_the_worker(async_email_app: Flask) -> None:
    sign_up(async_email_app, "new.user@example.com")
    assert async_email_app.extensions["outbox"][-1].to == "new.user@example.com"


class _BrokerDown:
    def delay(self, *args: Any, **kwargs: Any) -> None:
        raise OperationalError("broker unreachable")


def test_broker_outage_does_not_fail_the_users_request(
    async_email_app: Flask, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(tasks, "deliver_email", _BrokerDown())
    sign_up(async_email_app, "new.user@example.com")  # asserts 201 internally
    assert async_email_app.extensions["outbox"] == []


def test_delivery_task_is_retried_and_acknowledged_late() -> None:
    assert tasks.deliver_email.acks_late is True
    assert EmailTransportError in tasks.deliver_email.autoretry_for
