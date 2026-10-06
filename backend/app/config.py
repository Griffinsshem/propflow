"""Application configuration, built from environment variables and validated at startup."""

from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
VALID_ENVS = frozenset({"development", "test", "production"})
INSECURE_SECRET_PLACEHOLDERS = frozenset({"", "replace-me", "change-me"})
MIN_SECRET_LENGTH = 32
EMAIL_BACKENDS = frozenset({"console", "memory", "disabled", "smtp", "file"})
SMTP_SECURITY_MODES = frozenset({"starttls", "ssl", "none"})
# These backends print or retain message bodies, which contain account-recovery tokens.
NON_PRODUCTION_EMAIL_BACKENDS = frozenset({"console", "memory", "file"})
STORAGE_BACKENDS = frozenset({"s3", "memory"})

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


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be an integer") from exc


def _redis_url(name: str, *, database: int) -> str:
    """An explicit URL wins; otherwise REDIS_URL with its own logical database.

    Hosting platforms hand out a single Redis URL and blueprints cannot build strings, so
    the Celery broker and the rate limiter derive separate databases from it.
    """
    explicit = os.environ.get(name, "").strip()
    if explicit:
        return explicit
    base = urlsplit(_require("REDIS_URL"))
    return urlunsplit(base._replace(path=f"/{database}"))


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
    is_test = env == "test"

    secret_key = _require("SECRET_KEY")
    if secret_key in INSECURE_SECRET_PLACEHOLDERS or len(secret_key) < MIN_SECRET_LENGTH:
        raise ConfigError(f"SECRET_KEY must be random and at least {MIN_SECRET_LENGTH} characters")

    database_url = _require("TEST_DATABASE_URL" if is_test else "DATABASE_URL")

    frontend_origin = os.environ.get("FRONTEND_ORIGIN", "http://localhost:3000").strip().rstrip("/")
    if is_production and not frontend_origin.startswith("https://"):
        raise ConfigError("FRONTEND_ORIGIN must be an https:// origin in production")

    email_backend = (
        "memory" if is_test else os.environ.get("EMAIL_BACKEND", "console").strip().lower()
    )
    if email_backend not in EMAIL_BACKENDS:
        raise ConfigError(f"EMAIL_BACKEND must be one of {sorted(EMAIL_BACKENDS)}")
    if is_production and email_backend in NON_PRODUCTION_EMAIL_BACKENDS:
        raise ConfigError("EMAIL_BACKEND console/memory/file would expose tokens in production")

    proxy_secret = os.environ.get("PROXY_SHARED_SECRET", "").strip() or None
    trusts_proxy_headers = is_production and _int_env("TRUSTED_PROXY_COUNT", 0) > 0
    if trusts_proxy_headers and (proxy_secret is None or len(proxy_secret) < MIN_SECRET_LENGTH):
        raise ConfigError(
            "PROXY_SHARED_SECRET (32+ characters) is required when trusting proxy headers"
        )

    background_tasks = (
        "sync"
        if is_test
        else os.environ.get("BACKGROUND_TASKS", "async" if is_production else "sync")
        .strip()
        .lower()
    )
    if background_tasks not in {"sync", "async"}:
        raise ConfigError("BACKGROUND_TASKS must be sync or async")

    storage_backend = (
        "memory" if is_test else os.environ.get("STORAGE_BACKEND", "s3").strip().lower()
    )
    if storage_backend not in STORAGE_BACKENDS:
        raise ConfigError(f"STORAGE_BACKEND must be one of {sorted(STORAGE_BACKENDS)}")
    if is_production and storage_backend != "s3":
        raise ConfigError("STORAGE_BACKEND must be s3 in production")
    storage_settings: dict[str, Any] = {}
    if storage_backend == "s3":
        storage_settings = {
            "S3_ENDPOINT_URL": os.environ.get("S3_ENDPOINT_URL", "").strip() or None,
            "S3_ACCESS_KEY_ID": _require("S3_ACCESS_KEY_ID"),
            "S3_SECRET_ACCESS_KEY": _require("S3_SECRET_ACCESS_KEY"),
            "S3_BUCKET": _require("S3_BUCKET"),
            "S3_REGION": os.environ.get("S3_REGION", "auto").strip() or "auto",
        }

    smtp_settings: dict[str, Any] = {}
    if email_backend == "smtp":
        security = os.environ.get("SMTP_SECURITY", "starttls").strip().lower()
        if security not in SMTP_SECURITY_MODES:
            raise ConfigError(f"SMTP_SECURITY must be one of {sorted(SMTP_SECURITY_MODES)}")
        if is_production and security == "none":
            raise ConfigError("SMTP_SECURITY=none would send credentials and links unencrypted")
        sender = os.environ.get("MAIL_FROM", "").strip()
        if "@" not in sender or sender.rstrip(">").endswith(".local"):
            raise ConfigError("MAIL_FROM must be a real sender address when EMAIL_BACKEND=smtp")
        username = os.environ.get("SMTP_USERNAME", "").strip() or None
        password = os.environ.get("SMTP_PASSWORD", "")
        if username and not password:
            raise ConfigError("SMTP_PASSWORD is required when SMTP_USERNAME is set")
        smtp_settings = {
            "SMTP_HOST": _require("SMTP_HOST"),
            "SMTP_PORT": _int_env("SMTP_PORT", 465 if security == "ssl" else 587),
            "SMTP_SECURITY": security,
            "SMTP_USERNAME": username,
            "SMTP_PASSWORD": password,
            "SMTP_TIMEOUT_SECONDS": _int_env("SMTP_TIMEOUT_SECONDS", 15),
        }

    email_file_dir = os.environ.get("EMAIL_FILE_DIR", "").strip() or None
    if email_backend == "file" and email_file_dir is None:
        raise ConfigError("EMAIL_FILE_DIR is required when EMAIL_BACKEND=file")

    return {
        "APP_ENV": env,
        "TESTING": is_test,
        "SECRET_KEY": secret_key,
        # API bodies are small JSON. Files go straight to object storage via presigned URLs.
        "MAX_CONTENT_LENGTH": 1 * 1024 * 1024,
        "SQLALCHEMY_DATABASE_URI": normalize_database_url(database_url),
        # Pools are per worker process: total connections =
        # instances x gunicorn workers x (pool_size + max_overflow). Keep within the DB plan limit.
        "SQLALCHEMY_ENGINE_OPTIONS": {
            "pool_pre_ping": True,
            "pool_size": _int_env("DB_POOL_SIZE", 5),
            "max_overflow": _int_env("DB_MAX_OVERFLOW", 5),
            "pool_recycle": 1800,
            # Tests only: commits don't wait for the WAL flush. Correctness is unchanged
            # (constraints, locks, transactions); only crash durability, irrelevant here.
            **({"connect_args": {"options": "-c synchronous_commit=off"}} if is_test else {}),
        },
        "REDIS_URL": _require("REDIS_URL"),
        "FRONTEND_ORIGIN": frontend_origin,
        # Number of reverse-proxy hops to trust for the client IP (0 = trust none).
        "TRUSTED_PROXY_COUNT": _int_env("TRUSTED_PROXY_COUNT", 0),
        # When set, /api requests must carry X-Proxy-Secret: only our frontend proxy knows it,
        # so requests that bypass it (and could spoof X-Forwarded-For) are refused.
        "PROXY_SHARED_SECRET": proxy_secret,
        "HSTS_ENABLED": is_production,
        # Sessions: opaque server-side tokens in HttpOnly cookies (ADR 0003).
        # The __Host- prefix forces Secure, Path=/ and no Domain: blocks subdomain cookie injection.
        "AUTH_SESSION_COOKIE": "__Host-propflow_session" if is_production else "propflow_session",
        "AUTH_CSRF_COOKIE": "__Host-propflow_csrf" if is_production else "propflow_csrf",
        "AUTH_COOKIE_SECURE": is_production,
        "SESSION_IDLE_TIMEOUT": timedelta(
            seconds=_int_env("SESSION_IDLE_TIMEOUT_SECONDS", 3 * 24 * 3600)
        ),
        "SESSION_ABSOLUTE_TIMEOUT": timedelta(
            seconds=_int_env("SESSION_ABSOLUTE_TIMEOUT_SECONDS", 14 * 24 * 3600)
        ),
        # argon2-cffi defaults (RFC 9106 profile) everywhere except tests, where cheap
        # parameters keep the suite fast. Never use the test parameters in production.
        "ARGON2_PARAMS": {"time_cost": 1, "memory_cost": 1024, "parallelism": 1} if is_test else {},
        "EMAIL_BACKEND": email_backend,
        "BACKGROUND_TASKS": background_tasks,
        # Celery: tasks are acknowledged only after they finish (crash = redelivery),
        # one task prefetched at a time, JSON only, no result storage.
        "CELERY": {
            "broker_url": "memory://" if is_test else _redis_url("CELERY_BROKER_URL", database=1),
            "task_ignore_result": True,
            "task_acks_late": True,
            "task_reject_on_worker_lost": True,
            "worker_prefetch_multiplier": 1,
            "task_serializer": "json",
            "accept_content": ["json"],
            "timezone": "UTC",
            "broker_connection_retry_on_startup": True,
            "broker_transport_options": {"visibility_timeout": 3600},
            "task_always_eager": is_test,
            "task_eager_propagates": is_test,
            # Keep structured log levels honest: don't relabel worker stdout as WARNING.
            "worker_redirect_stdouts": False,
            # Exactly one beat process should run; jobs are idempotent if two ever do.
            "beat_schedule": {
                "recover-unfinished-uploads": {
                    "task": "housekeeping.recover_unfinished_uploads",
                    "schedule": 15 * 60,
                },
                "purge-expired-sessions": {
                    "task": "housekeeping.purge_expired_sessions",
                    "schedule": 24 * 3600,
                },
                "purge-old-notifications": {
                    "task": "housekeeping.purge_old_notifications",
                    "schedule": 24 * 3600,
                },
                "remove-orphaned-objects": {
                    "task": "housekeeping.remove_orphaned_objects",
                    "schedule": 24 * 3600,
                },
            },
        },
        "STORAGE_BACKEND": storage_backend,
        **storage_settings,
        **smtp_settings,
        "EMAIL_FILE_DIR": email_file_dir,
        "MAIL_FROM": os.environ.get("MAIL_FROM", "no-reply@propflow.local"),
        # Rate limiting (ADR 0004). Off in tests unless a test opts in.
        "RATELIMIT_ENABLED": not is_test,
        "RATELIMIT_STORAGE_URI": "memory://"
        if is_test
        else _redis_url("RATELIMIT_STORAGE_URI", database=2),
        "RATELIMIT_STRATEGY": "sliding-window-counter",
        "RATELIMIT_KEY_PREFIX": "propflow",
        "RATELIMIT_DEFAULT": "1000 per minute",
        "RATELIMIT_HEADERS_ENABLED": True,
        # A Redis outage must not lock everyone out: fall back to per-process limits.
        "RATELIMIT_SWALLOW_ERRORS": True,
        "RATELIMIT_IN_MEMORY_FALLBACK_ENABLED": True,
        # OpenAPI via flask-smorest. Interactive docs are disabled in production.
        "API_TITLE": "PropFlow API",
        "API_VERSION": "v1",
        "OPENAPI_VERSION": "3.1.0",
        "OPENAPI_URL_PREFIX": None if is_production else "/api/docs",
        "OPENAPI_SWAGGER_UI_PATH": "/swagger",
        "OPENAPI_SWAGGER_UI_URL": "https://cdn.jsdelivr.net/npm/swagger-ui-dist/",
    }
