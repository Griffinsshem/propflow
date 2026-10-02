"""Liveness and readiness probes. They report status only, never hosts or versions."""

from __future__ import annotations

import structlog
from flask import Blueprint, current_app
from flask.typing import ResponseReturnValue
from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db

health_bp = Blueprint("health", __name__)
logger = structlog.get_logger("propflow.health")


@health_bp.get("/health")
def health() -> ResponseReturnValue:
    """Liveness: the process is running. Never touches dependencies."""
    return {"status": "ok"}, 200


def _database_ok() -> bool:
    try:
        db.session.execute(text("SELECT 1"))
        return True
    except SQLAlchemyError as exc:
        db.session.rollback()
        logger.warning("readiness_failed", dependency="database", error_type=type(exc).__name__)
        return False


def _redis_ok() -> bool:
    client: Redis = current_app.extensions["redis"]
    try:
        return bool(client.ping())
    except RedisError as exc:
        logger.warning("readiness_failed", dependency="redis", error_type=type(exc).__name__)
        return False


@health_bp.get("/ready")
def ready() -> ResponseReturnValue:
    """Readiness: the database is required; Redis is reported but degrades gracefully."""
    database = _database_ok()
    redis_ok = _redis_ok()
    body = {
        "status": "ready" if database else "not_ready",
        "checks": {
            "database": "ok" if database else "unavailable",
            "redis": "ok" if redis_ok else "degraded",
        },
    }
    return body, 200 if database else 503
