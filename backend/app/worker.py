"""Celery integration and the single entry point for running background jobs."""

from __future__ import annotations

import importlib
from typing import Any

import structlog
from celery import Celery, Task
from flask import Flask, current_app, g
from kombu.exceptions import KombuError

logger = structlog.get_logger("propflow.worker")

TASK_MODULES = ("app.notifications.tasks", "app.maintenance.tasks", "app.housekeeping.tasks")


def init_celery(app: Flask) -> Celery:
    class FlaskTask(Task):
        def __call__(self, *args: Any, **kwargs: Any) -> Any:
            with app.app_context():
                return self.run(*args, **kwargs)

    celery_app = Celery(app.import_name, task_cls=FlaskTask)
    celery_app.config_from_object(app.config["CELERY"])
    celery_app.set_default()
    app.extensions["celery"] = celery_app
    for module in TASK_MODULES:
        importlib.import_module(module)  # registers the module's tasks
    return celery_app


def dispatch(task: Any, *args: Any, **kwargs: Any) -> bool:
    """Runs a background job: inline in sync mode (tests, local dev without a worker) or
    enqueued for the worker in async mode. Call only after the triggering transaction has
    committed. Returns False if the job could not be enqueued (broker outage)."""
    if current_app.config["BACKGROUND_TASKS"] != "async":
        task.run(*args, **kwargs)
        return True
    try:
        task.delay(*args, **kwargs)
    except KombuError as exc:
        # A broker outage must not fail the user's request; housekeeping recovers what it can.
        logger.error(
            "task_enqueue_failed",
            task=getattr(task, "name", repr(task)),
            error_type=type(exc).__name__,
        )
        return False
    return True


def bind_task_context(task: Any, request_id: str | None) -> None:
    """Ties worker logs and audit entries back to the originating API request.

    A no-op when a job runs inline (sync mode): the request's own context already applies,
    and binding here would mislabel the rest of that request's log lines.
    """
    task_id = getattr(getattr(task, "request", None), "id", None)
    if task_id is None:
        return
    g.request_id = request_id
    structlog.contextvars.bind_contextvars(
        request_id=request_id, task=getattr(task, "name", None), task_id=task_id
    )
