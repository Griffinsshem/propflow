"""The visitor's IP address, as named by the frontend proxy (ADR 0020).

Behind Vercel and Render's Cloudflare edge, the hops in X-Forwarded-For are not ours to count:
ProxyFix recorded an edge server instead of the visitor. The frontend proxy already proves itself
with the shared secret; it also names the visitor's IP in its own header. That header is trusted
only alongside a valid secret, and is removed from every request, so nobody else can supply it.
"""

from __future__ import annotations

import hmac
import ipaddress
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

    from _typeshed.wsgi import StartResponse, WSGIApplication, WSGIEnvironment

CLIENT_IP_HEADER = "X-PropFlow-Client-IP"
PROXY_AUTH_HEADER = "X-Proxy-Secret"


def environ_key(header: str) -> str:
    return "HTTP_" + header.upper().replace("-", "_")


class ProxiedClientIP:
    """WSGI middleware: REMOTE_ADDR becomes the proxy-named IP when the secret is valid."""

    def __init__(self, app: WSGIApplication, secret: str) -> None:
        self.app = app
        self.secret = secret.encode()

    def __call__(self, environ: WSGIEnvironment, start_response: StartResponse) -> Iterable[bytes]:
        named = str(environ.pop(environ_key(CLIENT_IP_HEADER), "")).strip()
        supplied = str(environ.get(environ_key(PROXY_AUTH_HEADER), "")).encode()
        if named and hmac.compare_digest(supplied, self.secret):
            try:
                address = ipaddress.ip_address(named)
            except ValueError:
                address = None
            if address is not None:
                environ["REMOTE_ADDR"] = str(address)
        return self.app(environ, start_response)
