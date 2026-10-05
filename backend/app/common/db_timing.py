"""Per-request database timing: how many queries a request ran and how long they took.

Logged on every request_completed line, so a slow endpoint can be split into database time
and application time straight from the logs, in production as well as in load tests.
"""

from __future__ import annotations

import time
from typing import Any

from flask import Flask, g, has_request_context
from sqlalchemy import event

from app.extensions import db

_STARTED = "propflow_query_started"


def register_db_timing(app: Flask) -> None:
    # Each app has its own engine, so listeners are never registered twice on one engine.
    with app.app_context():
        engine = db.engine

    def _before(conn: Any, _cursor: Any, _statement: Any, *_args: Any) -> None:
        conn.info[_STARTED] = time.perf_counter()

    def _after(conn: Any, _cursor: Any, _statement: Any, *_args: Any) -> None:
        started = conn.info.pop(_STARTED, None)
        if started is None or not has_request_context():
            return  # background jobs and CLI commands are not attributed to a request
        g.db_queries = g.get("db_queries", 0) + 1
        g.db_ms = g.get("db_ms", 0.0) + (time.perf_counter() - started) * 1000

    event.listen(engine, "before_cursor_execute", _before)
    event.listen(engine, "after_cursor_execute", _after)
