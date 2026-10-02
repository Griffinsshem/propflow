from flask import Flask

EMAIL = "target@example.com"
PASSWORD = "correct horse battery staple"
REGISTER = "/api/v1/auth/register"
LOGIN = "/api/v1/auth/login"
FORGOT = "/api/v1/auth/forgot-password"


def register(app: Flask) -> None:
    payload = {"email": EMAIL, "password": PASSWORD, "full_name": "Target User"}
    assert app.test_client().post(REGISTER, json=payload).status_code == 201


def test_repeated_failed_logins_for_one_account_are_blocked(rate_limited_app: Flask) -> None:
    register(rate_limited_app)
    client = rate_limited_app.test_client()
    wrong = {"email": EMAIL, "password": "definitely not the password"}
    statuses = [client.post(LOGIN, json=wrong).status_code for _ in range(11)]
    assert statuses[:10] == [401] * 10
    assert statuses[10] == 429
    # Even the correct password is refused while the account is throttled.
    blocked = client.post(LOGIN, json={"email": EMAIL, "password": PASSWORD})
    assert blocked.status_code == 429
    assert blocked.get_json()["error"]["code"] == "RATE_LIMITED"


def test_successful_logins_do_not_consume_the_account_limit(rate_limited_app: Flask) -> None:
    register(rate_limited_app)
    statuses = [
        rate_limited_app.test_client()
        .post(LOGIN, json={"email": EMAIL, "password": PASSWORD})
        .status_code
        for _ in range(12)
    ]
    assert statuses == [200] * 12


def test_password_reset_requests_are_limited_per_account(rate_limited_app: Flask) -> None:
    statuses = [
        rate_limited_app.test_client().post(FORGOT, json={"email": EMAIL}).status_code
        for _ in range(4)
    ]
    assert statuses == [202, 202, 202, 429]
