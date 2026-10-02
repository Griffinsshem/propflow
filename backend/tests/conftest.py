from __future__ import annotations

from collections.abc import Iterator

import pytest
from flask import Flask
from flask.testing import FlaskClient

from app import create_app


@pytest.fixture()
def app() -> Iterator[Flask]:
    yield create_app("test")


@pytest.fixture()
def client(app: Flask) -> FlaskClient:
    return app.test_client()
