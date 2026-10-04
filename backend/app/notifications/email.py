"""Outbound email: inline in tests and local development, through the worker in production."""

from __future__ import annotations

from dataclasses import dataclass

import structlog
from flask import current_app, g, has_request_context

logger = structlog.get_logger("propflow.email")


class EmailTransportError(Exception):
    """A transient delivery failure: the worker retries it with backoff."""


@dataclass(frozen=True)
class EmailMessage:
    to: str
    subject: str
    body: str


def deliver_now(message: EmailMessage) -> None:
    backend = current_app.config["EMAIL_BACKEND"]
    if backend == "memory":
        current_app.extensions["outbox"].append(message)
    elif backend == "console":
        # Development only (config forbids it in production): bodies contain token links.
        logger.info(
            "email_console_delivery", to=message.to, subject=message.subject, body=message.body
        )
    elif backend == "disabled":
        logger.warning("email_delivery_disabled", subject=message.subject)
    else:
        raise RuntimeError(f"Unsupported email backend: {backend}")


def send_email(message: EmailMessage) -> None:
    """Callers invoke this only after their transaction has committed."""
    from app.notifications import tasks  # local imports: both modules import this one
    from app.worker import dispatch

    request_id = g.get("request_id") if has_request_context() else None
    dispatch(tasks.deliver_email, message.to, message.subject, message.body, request_id=request_id)
