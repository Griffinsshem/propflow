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
