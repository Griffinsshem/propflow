from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from flask import Flask
from flask_migrate import downgrade, upgrade

from app.extensions import db


def test_models_and_migrations_are_in_sync(app: Flask) -> None:
    """Fails if a model changed without a matching migration."""
    with app.app_context(), db.engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), db.metadata)
    assert diff == [], f"Models differ from migrations; run `flask db migrate`: {diff}"


def test_migrations_downgrade_and_upgrade_cleanly(app: Flask) -> None:
    with app.app_context():
        downgrade(revision="base")
        upgrade()
