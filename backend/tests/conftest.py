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


def _delete_all_rows() -> None:
    # DELETE beats TRUNCATE for the handful of rows a test creates: TRUNCATE pays a
    # fixed per-table cost. Reverse dependency order satisfies foreign keys.
    for table in reversed(db.metadata.sorted_tables):
        db.session.execute(table.delete())
    db.session.commit()


@pytest.fixture()
def app(migrated_database: None) -> Iterator[Flask]:
    application = create_app("test")
    yield application
    with application.app_context():
        _delete_all_rows()
        db.session.remove()
        db.engine.dispose()


@pytest.fixture()
def client(app: Flask) -> FlaskClient:
    return app.test_client()
