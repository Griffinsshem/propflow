import pytest

from app.config import ConfigError, build_config, normalize_database_url


@pytest.fixture()
def production_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FRONTEND_ORIGIN", "https://app.example.com")
    monkeypatch.setenv("EMAIL_BACKEND", "disabled")
    monkeypatch.setenv("STORAGE_BACKEND", "s3")
    monkeypatch.setenv("S3_ACCESS_KEY_ID", "test-key")
    monkeypatch.setenv("S3_SECRET_ACCESS_KEY", "test-secret")
    monkeypatch.setenv("S3_BUCKET", "test-bucket")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("postgres://u:p@h:5432/d", "postgresql+psycopg://u:p@h:5432/d"),
        ("postgresql://u:p@h/d", "postgresql+psycopg://u:p@h/d"),
        ("postgresql+psycopg://u:p@h/d", "postgresql+psycopg://u:p@h/d"),
    ],
)
def test_database_url_uses_psycopg3_driver(raw: str, expected: str) -> None:
    assert normalize_database_url(raw) == expected


@pytest.mark.parametrize("secret", ["replace-me", "too-short-secret"])
def test_weak_secret_key_refuses_to_start(monkeypatch: pytest.MonkeyPatch, secret: str) -> None:
    monkeypatch.setenv("SECRET_KEY", secret)
    with pytest.raises(ConfigError):
        build_config("test")


def test_unknown_environment_refuses_to_start() -> None:
    with pytest.raises(ConfigError):
        build_config("staging-typo")


@pytest.mark.usefixtures("production_env")
def test_production_requires_https_frontend_origin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FRONTEND_ORIGIN", "http://app.example.com")
    with pytest.raises(ConfigError, match="FRONTEND_ORIGIN"):
        build_config("production")


@pytest.mark.usefixtures("production_env")
@pytest.mark.parametrize("backend", ["console", "memory"])
def test_production_rejects_token_exposing_email_backends(
    monkeypatch: pytest.MonkeyPatch, backend: str
) -> None:
    monkeypatch.setenv("EMAIL_BACKEND", backend)
    with pytest.raises(ConfigError, match="EMAIL_BACKEND"):
        build_config("production")


@pytest.mark.usefixtures("production_env")
def test_production_disables_interactive_api_docs() -> None:
    assert build_config("production")["OPENAPI_URL_PREFIX"] is None


@pytest.mark.usefixtures("production_env")
def test_production_uses_host_prefixed_secure_cookies() -> None:
    config = build_config("production")
    assert config["AUTH_SESSION_COOKIE"].startswith("__Host-")
    assert config["AUTH_CSRF_COOKIE"].startswith("__Host-")
    assert config["AUTH_COOKIE_SECURE"] is True


@pytest.mark.usefixtures("production_env")
def test_production_uses_full_strength_password_hashing() -> None:
    assert build_config("production")["ARGON2_PARAMS"] == {}


@pytest.mark.usefixtures("production_env")
def test_production_requires_object_storage(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STORAGE_BACKEND", "memory")
    with pytest.raises(ConfigError, match="STORAGE_BACKEND"):
        build_config("production")


def test_only_tests_relax_commit_durability(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STORAGE_BACKEND", "memory")
    assert "connect_args" not in build_config("development")["SQLALCHEMY_ENGINE_OPTIONS"]
    assert build_config("test")["SQLALCHEMY_ENGINE_OPTIONS"]["connect_args"] == {
        "options": "-c synchronous_commit=off"
    }


@pytest.mark.usefixtures("production_env")
def test_trusting_proxy_headers_requires_a_strong_proxy_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TRUSTED_PROXY_COUNT", "2")
    monkeypatch.delenv("PROXY_SHARED_SECRET", raising=False)
    with pytest.raises(ConfigError, match="PROXY_SHARED_SECRET"):
        build_config("production")
    monkeypatch.setenv("PROXY_SHARED_SECRET", "x" * 40)
    assert build_config("production")["PROXY_SHARED_SECRET"] == "x" * 40


@pytest.mark.usefixtures("production_env")
def test_hsts_is_enabled_only_in_production() -> None:
    assert build_config("production")["HSTS_ENABLED"] is True
    assert build_config("test")["HSTS_ENABLED"] is False


@pytest.mark.usefixtures("production_env")
def test_broker_and_rate_limit_urls_derive_from_redis_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("REDIS_URL", "redis://user:pass@red-abc:6379")
    monkeypatch.delenv("CELERY_BROKER_URL", raising=False)
    monkeypatch.delenv("RATELIMIT_STORAGE_URI", raising=False)
    config = build_config("production")
    assert config["CELERY"]["broker_url"] == "redis://user:pass@red-abc:6379/1"
    assert config["RATELIMIT_STORAGE_URI"] == "redis://user:pass@red-abc:6379/2"


@pytest.mark.usefixtures("production_env")
def test_explicit_broker_url_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CELERY_BROKER_URL", "redis://broker:6379/5")
    assert build_config("production")["CELERY"]["broker_url"] == "redis://broker:6379/5"


@pytest.fixture()
def smtp_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EMAIL_BACKEND", "smtp")
    monkeypatch.setenv("SMTP_HOST", "smtp.provider.example")
    monkeypatch.setenv("SMTP_USERNAME", "apikey")
    monkeypatch.setenv("SMTP_PASSWORD", "x" * 32)
    monkeypatch.setenv("MAIL_FROM", "PropFlow <no-reply@propflow.example>")


@pytest.mark.usefixtures("production_env", "smtp_env")
def test_smtp_defaults_to_starttls_on_587() -> None:
    config = build_config("production")
    assert config["SMTP_SECURITY"] == "starttls"
    assert config["SMTP_PORT"] == 587


@pytest.mark.usefixtures("production_env", "smtp_env")
def test_production_refuses_unencrypted_smtp(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SMTP_SECURITY", "none")
    with pytest.raises(ConfigError, match="unencrypted"):
        build_config("production")


@pytest.mark.usefixtures("production_env", "smtp_env")
def test_smtp_requires_a_real_sender_and_a_host(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MAIL_FROM", "no-reply@propflow.local")
    with pytest.raises(ConfigError, match="MAIL_FROM"):
        build_config("production")
    monkeypatch.setenv("MAIL_FROM", "no-reply@propflow.example")
    monkeypatch.delenv("SMTP_HOST")
    with pytest.raises(ConfigError, match="SMTP_HOST"):
        build_config("production")


@pytest.mark.usefixtures("production_env")
def test_production_refuses_the_file_email_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EMAIL_BACKEND", "file")
    monkeypatch.setenv("EMAIL_FILE_DIR", "/var/propflow-mail")
    with pytest.raises(ConfigError, match="expose tokens"):
        build_config("production")


@pytest.mark.usefixtures("production_env")
def test_production_refuses_local_storage(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    monkeypatch.setenv("LOCAL_STORAGE_DIR", "/var/propflow-storage")
    with pytest.raises(ConfigError, match="STORAGE_BACKEND must be s3"):
        build_config("production")
