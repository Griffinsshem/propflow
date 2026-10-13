from typing import Any

from app.common.client_ip import CLIENT_IP_HEADER, PROXY_AUTH_HEADER, ProxiedClientIP, environ_key

SECRET = "s" * 48
EDGE = "172.68.194.174"  # what ProxyFix recorded: a Cloudflare edge server


def call(headers: dict[str, str]) -> dict[str, Any]:
    seen: dict[str, Any] = {}

    def app(environ: dict[str, Any], start_response: Any) -> list[bytes]:
        seen["ip"] = environ["REMOTE_ADDR"]
        seen["named"] = environ.get(environ_key(CLIENT_IP_HEADER))
        return [b""]

    environ: dict[str, Any] = {"REMOTE_ADDR": EDGE}
    environ.update({environ_key(name): value for name, value in headers.items()})
    ProxiedClientIP(app, SECRET)(environ, lambda *_: None)
    return seen


def test_the_proxy_names_the_visitor_when_the_secret_is_valid() -> None:
    assert call({PROXY_AUTH_HEADER: SECRET, CLIENT_IP_HEADER: "203.0.113.9"})["ip"] == "203.0.113.9"


def test_ipv6_visitors_are_named_too() -> None:
    seen = call({PROXY_AUTH_HEADER: SECRET, CLIENT_IP_HEADER: "2001:db8::7"})
    assert seen["ip"] == "2001:db8::7"


def test_without_the_secret_the_header_is_ignored() -> None:
    assert call({CLIENT_IP_HEADER: "203.0.113.9"})["ip"] == EDGE


def test_a_wrong_secret_cannot_name_an_ip() -> None:
    seen = call({PROXY_AUTH_HEADER: "x" * 48, CLIENT_IP_HEADER: "203.0.113.9"})
    assert seen["ip"] == EDGE


def test_a_malformed_ip_is_ignored() -> None:
    seen = call({PROXY_AUTH_HEADER: SECRET, CLIENT_IP_HEADER: "203.0.113.9, 10.0.0.1"})
    assert seen["ip"] == EDGE


def test_the_header_never_reaches_the_application() -> None:
    assert call({CLIENT_IP_HEADER: "203.0.113.9"})["named"] is None
    assert call({PROXY_AUTH_HEADER: SECRET, CLIENT_IP_HEADER: "203.0.113.9"})["named"] is None
