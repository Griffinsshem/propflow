import pytest
from flask import Flask, request
from flask.testing import FlaskClient


def test_health_is_ok(client: FlaskClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_ready_checks_database(client: FlaskClient) -> None:
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.get_json()["checks"]["database"] == "ok"


def test_request_id_generated_when_absent(client: FlaskClient) -> None:
    assert len(client.get("/health").headers["X-Request-ID"]) == 32


def test_valid_request_id_is_propagated(client: FlaskClient) -> None:
    rid = "client-req-12345678"
    assert client.get("/health", headers={"X-Request-ID": rid}).headers["X-Request-ID"] == rid


@pytest.mark.parametrize("bad", ["short", "x" * 200, "has spaces in it", "<script>x</script>"])
def test_unsafe_request_id_is_replaced(client: FlaskClient, bad: str) -> None:
    assert client.get("/health", headers={"X-Request-ID": bad}).headers["X-Request-ID"] != bad


def test_unknown_route_returns_structured_404(client: FlaskClient) -> None:
    response = client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    error = response.get_json()["error"]
    assert error["code"] == "RESOURCE_NOT_FOUND"
    assert error["request_id"] == response.headers["X-Request-ID"]


def test_unhandled_exception_hides_internal_details(fresh_app: Flask) -> None:
    app = fresh_app

    @app.get("/__boom")
    def boom() -> str:
        raise RuntimeError("db password is hunter2")

    response = app.test_client().get("/__boom")
    assert response.status_code == 500
    assert "hunter2" not in response.get_data(as_text=True)
    assert response.get_json()["error"]["code"] == "INTERNAL_ERROR"


def test_oversized_body_is_rejected(fresh_app: Flask) -> None:
    app = fresh_app

    @app.post("/__echo")
    def echo() -> dict[str, int]:
        return {"size": len(request.get_data())}

    response = app.test_client().post("/__echo", data=b"x" * (1024 * 1024 + 1))
    assert response.status_code == 413
    assert response.get_json()["error"]["code"] == "PAYLOAD_TOO_LARGE"


def test_security_headers_present(client: FlaskClient) -> None:
    headers = client.get("/health").headers
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"
    assert headers["Cache-Control"] == "no-store"
