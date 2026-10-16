"""Scheduled clean-up without a Celery scheduler (ADR 0019, ADR 0021).

`flask housekeeping hourly` is run every hour by .github/workflows/housekeeping.yml.
"""

from __future__ import annotations

import click
from flask.cli import AppGroup

from app.demo import service as demo
from app.extensions import db
from app.housekeeping import service as housekeeping

cli = AppGroup("housekeeping", help="Scheduled clean-up jobs.")


@cli.command("hourly")
def hourly() -> None:
    """Purge expired demo sandboxes, expired sessions and old notifications."""
    sandboxes = demo.purge_expired()  # first: their sessions go with their people
    sessions = housekeeping.purge_expired_sessions()
    notifications = housekeeping.purge_old_notifications()
    db.session.commit()
    click.echo(
        f"demo sandboxes purged: {sandboxes}; expired sessions: {sessions}; "
        f"old notifications: {notifications}"
    )
