import pytest

from app.config import ConfigError, build_config, normalize_database_url


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


def test_production_disables_interactive_api_docs() -> None:
    assert build_config("production")["OPENAPI_URL_PREFIX"] is None
