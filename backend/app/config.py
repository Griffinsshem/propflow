"""Application configuration, built from environment variables and validated at startup."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
VALID_ENVS = frozenset({"development", "test", "production"})
INSECURE_SECRET_PLACEHOLDERS = frozenset({"", "replace-me", "change-me"})
MIN_SECRET_LENGTH = 32

# Local convenience: load the repo-root .env if it exists.
# override=False means real environment variables (Render, CI) always win.
load_dotenv(REPO_ROOT / ".env", override=False)


class ConfigError(RuntimeError):
    """Raised when required configuration is missing or unsafe."""


def _require(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ConfigError(f"Missing required environment variable: {name}")
    return value


def normalize_database_url(url: str) -> str:
    """Force the psycopg 3 driver; hosting providers usually issue postgres:// URLs."""
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix) :]
    return url


def build_config(app_env: str | None = None) -> dict[str, Any]:
    env = (app_env or os.environ.get("APP_ENV", "development")).strip().lower()
    if env not in VALID_ENVS:
        raise ConfigError(f"APP_ENV must be one of {sorted(VALID_ENVS)}, got {env!r}")
    is_production = env == "production"

    secret_key = _require("SECRET_KEY")
    if secret_key in INSECURE_SECRET_PLACEHOLDERS or len(secret_key) < MIN_SECRET_LENGTH:
        raise ConfigError(f"SECRET_KEY must be random and at least {MIN_SECRET_LENGTH} characters")

    database_url = _require("TEST_DATABASE_URL" if env == "test" else "DATABASE_URL")

    return {
        "APP_ENV": env,
        "TESTING": env == "test",
        "SECRET_KEY": secret_key,
        # API bodies are small JSON. Files go straight to object storage via presigned URLs.
        "MAX_CONTENT_LENGTH": 1 * 1024 * 1024,
        "SQLALCHEMY_DATABASE_URI": normalize_database_url(database_url),
        # Pools are per worker process: total connections =
        # instances x gunicorn workers x (pool_size + max_overflow). Keep within the DB plan limit.
        "SQLALCHEMY_ENGINE_OPTIONS": {
            "pool_pre_ping": True,
            "pool_size": int(os.environ.get("DB_POOL_SIZE", "5")),
            "max_overflow": int(os.environ.get("DB_MAX_OVERFLOW", "5")),
            "pool_recycle": 1800,
        },
        "REDIS_URL": _require("REDIS_URL"),
        "FRONTEND_ORIGIN": os.environ.get("FRONTEND_ORIGIN", "http://localhost:3000"),
        # OpenAPI via flask-smorest. Interactive docs are disabled in production.
        "API_TITLE": "PropFlow API",
        "API_VERSION": "v1",
        "OPENAPI_VERSION": "3.1.0",
        "OPENAPI_URL_PREFIX": None if is_production else "/api/docs",
        "OPENAPI_SWAGGER_UI_PATH": "/swagger",
        "OPENAPI_SWAGGER_UI_URL": "https://cdn.jsdelivr.net/npm/swagger-ui-dist/",
    }
