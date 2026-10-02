from __future__ import annotations

from collections.abc import Iterator

import pytest
from flask import Flask
from flask.testing import FlaskClient
from flask_migrate import upgrade
from sqlalchemy import text

from app import create_app
from app.common.rate_limit import limiter
from app.extensions import db
from tests.support import TwoOrgs, create_organization, sign_up


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


def _teardown(application: Flask) -> None:
    with application.app_context():
        # The audit trigger permits DELETE only with this transaction-local flag.
        db.session.execute(text("SET LOCAL propflow.audit_maintenance = 'on'"))
        # DELETE beats TRUNCATE for the few rows a test creates. Reverse order satisfies FKs.
        for table in reversed(db.metadata.sorted_tables):
            db.session.execute(table.delete())
        db.session.commit()
        db.session.remove()
        db.engine.dispose()


@pytest.fixture()
def app(migrated_database: None) -> Iterator[Flask]:
    application = create_app("test")
    yield application
    _teardown(application)


@pytest.fixture()
def rate_limited_app(migrated_database: None) -> Iterator[Flask]:
    application = create_app("test", overrides={"RATELIMIT_ENABLED": True})
    with application.app_context():
        limiter.reset()
    yield application
    _teardown(application)


@pytest.fixture()
def client(app: Flask) -> FlaskClient:
    return app.test_client()


@pytest.fixture()
def two_orgs(app: Flask) -> TwoOrgs:
    a_owner = sign_up(app, "owner.a@example.com", "Owner A")
    org_a = create_organization(a_owner, "Org A")
    b_owner = sign_up(app, "owner.b@example.com", "Owner B")
    org_b = create_organization(b_owner, "Org B")
    return TwoOrgs(app=app, a_owner=a_owner, b_owner=b_owner, org_a=org_a, org_b=org_b)
