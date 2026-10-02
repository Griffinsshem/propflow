from __future__ import annotations

from collections.abc import Iterator

import pytest
from flask import Flask
from flask.testing import FlaskClient
from flask_migrate import upgrade
from sqlalchemy import text

from app import create_app
from app.extensions import db


def _assert_is_test_database() -> None:
    """Safety guard: the suite drops schemas, so it must never touch a non-test database."""
    name = db.engine.url.database or ""
    if not name.endswith("_test"):
        raise RuntimeError(f"Refusing to run tests against non-test database {name!r}")


@pytest.fixture(scope="session")
def migrated_database() -> None:
    """Build the schema once per run from migrations, which also exercises them."""
    app = create_app("test")
    with app.app_context():
        _assert_is_test_database()
        with db.engine.begin() as conn:
            conn.execute(text("DROP SCHEMA public CASCADE"))
            conn.execute(text("CREATE SCHEMA public"))
        upgrade()
        db.engine.dispose()


def _truncate_all_tables() -> None:
    quote = db.engine.dialect.identifier_preparer.quote
    tables = [quote(table.name) for table in db.metadata.sorted_tables]
    if tables:
        # Table names come from our own model metadata, never from user input.
        db.session.execute(text(f"TRUNCATE {', '.join(tables)} RESTART IDENTITY CASCADE"))
        db.session.commit()


@pytest.fixture()
def app(migrated_database: None) -> Iterator[Flask]:
    application = create_app("test")
    yield application
    with application.app_context():
        _truncate_all_tables()
        db.session.remove()
        db.engine.dispose()


@pytest.fixture()
def client(app: Flask) -> FlaskClient:
    return app.test_client()
