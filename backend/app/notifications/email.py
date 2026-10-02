"""Outbound email. Real delivery via the background worker arrives in Phase 9."""

from __future__ import annotations

from dataclasses import dataclass

import structlog
from flask import current_app

logger = structlog.get_logger("propflow.email")


@dataclass(frozen=True)
class EmailMessage:
    to: str
    subject: str
    body: str


def send_email(message: EmailMessage) -> None:
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
