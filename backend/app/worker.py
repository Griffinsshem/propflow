"""Celery integration: tasks run inside a Flask app context, configured from app config."""

from __future__ import annotations

import importlib
from typing import Any

from celery import Celery, Task
from flask import Flask

TASK_MODULES = ("app.notifications.tasks",)


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
