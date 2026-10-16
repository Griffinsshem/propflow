"""PropFlow API application factory."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import redis
from flask import Flask
from flask_smorest import Api
from werkzeug.middleware.proxy_fix import ProxyFix

from app.api.v1 import register_v1
from app.auth.middleware import register_auth_middleware
from app.auth.passwords import init_password_hasher
from app.common.client_ip import ProxiedClientIP
from app.common.db_timing import register_db_timing
from app.common.errors import register_error_handlers
from app.common.health import health_bp
from app.common.logging import configure_logging
from app.common.middleware import register_middleware
from app.common.rate_limit import limiter
from app.common.storage import init_storage
from app.config import build_config
from app.extensions import db, migrate
from app.worker import init_celery

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"


def create_app(app_env: str | None = None, overrides: Mapping[str, Any] | None = None) -> Flask:
    config = build_config(app_env)
    if overrides:
        config.update(overrides)  # used by tests to opt into specific behaviour
    configure_logging(config["APP_ENV"])

    app = Flask(__name__)
    app.config.from_mapping(config)

    if app.config["PROXY_SHARED_SECRET"]:
        # Innermost, so it has the final say on REMOTE_ADDR for proxied requests (ADR 0020).
        app.wsgi_app = ProxiedClientIP(app.wsgi_app, app.config["PROXY_SHARED_SECRET"])  # type: ignore[method-assign]
    proxy_hops = app.config["TRUSTED_PROXY_COUNT"]
    if proxy_hops > 0:
        # Read the client IP from exactly N trusted hops; anything further left is spoofable.
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=proxy_hops)  # type: ignore[method-assign]

    # Registers every model on db.metadata before migrations or queries run.
    from app import models  # noqa: F401

    db.init_app(app)
    register_db_timing(app)
    migrate.init_app(app, db, directory=str(MIGRATIONS_DIR))
    api = Api(app)
    app.extensions["api"] = api
    # Connects lazily; short timeouts so a Redis outage never stalls requests.
    app.extensions["redis"] = redis.Redis.from_url(
        app.config["REDIS_URL"], socket_connect_timeout=1, socket_timeout=1
    )
    app.extensions["outbox"] = []  # only used by the "memory" email backend
    init_storage(app)
    init_celery(app)
    init_password_hasher(app)

    # Order matters: request IDs, then session loading, then CSRF, then rate limits
    # (limits run after session loading so logged-in users are keyed by account).
    register_middleware(app)
    register_auth_middleware(app)
    limiter.init_app(app)
    limiter.exempt(health_bp)

    app.register_blueprint(health_bp)
    from app.housekeeping.cli import cli as housekeeping_cli

    app.cli.add_command(housekeeping_cli)
    register_v1(api)
    # Must come after Api(app) so these handlers replace flask-smorest's defaults.
    register_error_handlers(app)
    return app
