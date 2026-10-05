from flask import Flask, g
from sqlalchemy import text

from app.extensions import db


def test_queries_in_a_request_are_counted_and_timed(app: Flask) -> None:
    with app.test_request_context():
        db.session.execute(text("SELECT 0"))  # opens the connection first
        before = g.get("db_queries", 0)
        db.session.execute(text("SELECT 1"))
        db.session.execute(text("SELECT 2"))
        assert g.db_queries - before == 2
        assert g.db_ms > 0
        db.session.rollback()


def test_queries_outside_requests_are_not_attributed(app: Flask) -> None:
    with app.app_context():
        db.session.execute(text("SELECT 1"))
        assert "db_queries" not in g
        db.session.rollback()
