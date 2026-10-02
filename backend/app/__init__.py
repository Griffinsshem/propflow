"""PropFlow API application factory."""

from __future__ import annotations

from pathlib import Path

import redis
from flask import Flask
from flask_smorest import Api

from app.api.v1 import register_v1
from app.auth.middleware import register_auth_middleware
from app.auth.passwords import init_password_hasher
from app.common.errors import register_error_handlers
from app.common.health import health_bp
from app.common.logging import configure_logging
from app.common.middleware import register_middleware
from app.config import build_config
from app.extensions import db, migrate

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"


def create_app(app_env: str | None = None) -> Flask:
    config = build_config(app_env)
    configure_logging(config["APP_ENV"])

    app = Flask(__name__)
    app.config.from_mapping(config)

    # Registers every model on db.metadata before migrations or queries run.
    from app import models  # noqa: F401

    db.init_app(app)
    migrate.init_app(app, db, directory=str(MIGRATIONS_DIR))
    api = Api(app)
    app.extensions["api"] = api
    # Connects lazily; short timeouts so a Redis outage never stalls requests.
    app.extensions["redis"] = redis.Redis.from_url(
        app.config["REDIS_URL"], socket_connect_timeout=1, socket_timeout=1
    )
    init_password_hasher(app)

    # Order matters: request IDs first, then session loading, then CSRF checks.
    register_middleware(app)
    register_auth_middleware(app)

    app.register_blueprint(health_bp)
    register_v1(api)
    # Must come after Api(app) so these handlers replace flask-smorest's defaults.
    register_error_handlers(app)
    return app
