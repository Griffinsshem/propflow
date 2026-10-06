"""Outbound email: inline in tests and local development, through the worker in production.

Production delivers over SMTP, which every major transactional provider offers, so the
provider can change without code changes (ADR 0015).
"""

from __future__ import annotations

import json
import smtplib
import ssl
import time
import uuid
from dataclasses import dataclass
from email.message import EmailMessage as MimeMessage
from email.utils import formatdate, make_msgid, parseaddr
from pathlib import Path

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


def _recipient_domain(address: str) -> str:
    # Logs carry the domain only: full addresses are personal data, bodies contain token links.
    return address.rpartition("@")[2] or "unknown"


def _build_mime(message: EmailMessage) -> MimeMessage:
    sender = current_app.config["MAIL_FROM"]
    mime = MimeMessage()  # default policy: header values containing CR/LF raise ValueError
    mime["From"] = sender
    mime["To"] = message.to
    mime["Subject"] = message.subject
    mime["Date"] = formatdate(usegmt=True)
    mime["Message-ID"] = make_msgid(domain=parseaddr(sender)[1].rpartition("@")[2] or None)
    mime.set_content(message.body)
    return mime


def _deliver_smtp(message: EmailMessage) -> None:
    config = current_app.config
    mime = _build_mime(message)
    security = config["SMTP_SECURITY"]
    timeout = config["SMTP_TIMEOUT_SECONDS"]
    context = ssl.create_default_context()
    domain = _recipient_domain(message.to)
    try:
        client: smtplib.SMTP
        if security == "ssl":
            client = smtplib.SMTP_SSL(
                config["SMTP_HOST"], config["SMTP_PORT"], timeout=timeout, context=context
            )
        else:
            client = smtplib.SMTP(config["SMTP_HOST"], config["SMTP_PORT"], timeout=timeout)
        with client:
            if security == "starttls":
                client.starttls(context=context)
            if config["SMTP_USERNAME"]:
                client.login(config["SMTP_USERNAME"], config["SMTP_PASSWORD"])
            client.send_message(mime)
    except smtplib.SMTPRecipientsRefused:
        # Permanent: the address does not exist or is blocked; retrying cannot help.
        logger.warning("email_recipient_refused", recipient_domain=domain, subject=message.subject)
        return
    except smtplib.SMTPResponseException as exc:
        if isinstance(exc, smtplib.SMTPAuthenticationError):
            # Retried: gives operators time to fix rotated or expired credentials.
            logger.error("email_authentication_failed", smtp_code=exc.smtp_code)
        elif 500 <= exc.smtp_code < 600:
            # Permanent rejection (e.g. unverified sender): log loudly, do not retry.
            logger.error(
                "email_rejected",
                smtp_code=exc.smtp_code,
                recipient_domain=domain,
                subject=message.subject,
            )
            return
        raise EmailTransportError(f"SMTP {exc.smtp_code}") from exc
    except OSError as exc:  # connection failures, timeouts and other SMTP errors
        raise EmailTransportError(type(exc).__name__) from exc
    logger.info("email_sent", recipient_domain=domain, subject=message.subject)


def _deliver_file(message: EmailMessage) -> None:
    """Development and end-to-end tests only (refused in production): one JSON file per email.

    Written to a temporary name and renamed, so a reader never sees a half-written file.
    """
    directory = Path(current_app.config["EMAIL_FILE_DIR"])
    directory.mkdir(parents=True, exist_ok=True)
    name = f"{time.time_ns()}-{uuid.uuid4().hex}"
    payload = {"to": message.to, "subject": message.subject, "body": message.body}
    temporary = directory / f"{name}.tmp"
    temporary.write_text(json.dumps(payload), encoding="utf-8")
    temporary.replace(directory / f"{name}.json")


def deliver_now(message: EmailMessage) -> None:
    backend = current_app.config["EMAIL_BACKEND"]
    if backend == "smtp":
        _deliver_smtp(message)
    elif backend == "file":
        _deliver_file(message)
    elif backend == "memory":
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
