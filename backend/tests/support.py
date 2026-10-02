"""Shared test helpers: authenticated actors and multi-tenant setup."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from typing import Any

from flask import Flask
from flask.testing import FlaskClient
from werkzeug.test import TestResponse

from app.extensions import db
from app.organizations.models import OrganizationMembership

PASSWORD = "correct horse battery staple"
CSRF_COOKIE = "propflow_csrf"
ORGS = "/api/v1/organizations"
INVITATIONS = "/api/v1/invitations"
MEMBERS = "/api/v1/members"
TOKEN_IN_LINK = re.compile(r"#token=([A-Za-z0-9_.\-]+)")


@dataclass
class Actor:
    """A logged-in browser: sends the CSRF header automatically on unsafe requests."""

    app: Flask
    client: FlaskClient
    user_id: str
    email: str

    def _csrf(self) -> dict[str, str]:
        cookie = self.client.get_cookie(CSRF_COOKIE)
        return {"X-CSRF-Token": cookie.value} if cookie else {}

    def get(self, path: str, **kwargs: Any) -> TestResponse:
        return self.client.get(path, **kwargs)

    def post(self, path: str, json: Any = None) -> TestResponse:
        return self.client.post(path, json=json, headers=self._csrf())

    def patch(self, path: str, json: Any = None) -> TestResponse:
        return self.client.patch(path, json=json, headers=self._csrf())

    def delete(self, path: str) -> TestResponse:
        return self.client.delete(path, headers=self._csrf())


@dataclass
class TwoOrgs:
    app: Flask
    a_owner: Actor
    b_owner: Actor
    org_a: str
    org_b: str


def sign_up(app: Flask, email: str, full_name: str = "Test User") -> Actor:
    client = app.test_client()
    payload = {"email": email, "password": PASSWORD, "full_name": full_name}
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201, response.get_json()
    return Actor(app=app, client=client, user_id=response.get_json()["id"], email=email)


def create_organization(owner: Actor, name: str) -> str:
    response = owner.post(ORGS, json={"name": name})
    assert response.status_code == 201, response.get_json()
    return str(response.get_json()["id"])


def add_member(app: Flask, organization_id: str, actor: Actor, role: str) -> None:
    """Fast path for tests whose subject isn't invitations; skips the real flow."""
    with app.app_context():
        db.session.add(
            OrganizationMembership(
                organization_id=uuid.UUID(organization_id),
                user_id=uuid.UUID(actor.user_id),
                role=role,
            )
        )
        db.session.commit()


def activate(actor: Actor, organization_id: str) -> None:
    response = actor.post(f"{ORGS}/{organization_id}/activate")
    assert response.status_code == 200, response.get_json()


def last_link_token(app: Flask) -> str:
    match = TOKEN_IN_LINK.search(app.extensions["outbox"][-1].body)
    assert match is not None
    return match.group(1)


def invite(inviter: Actor, email: str, role: str) -> str:
    """Creates an invitation and returns the token from the emailed link."""
    response = inviter.post(INVITATIONS, json={"email": email, "role": role})
    assert response.status_code == 201, response.get_json()
    return last_link_token(inviter.app)


def join_via_invitation(
    inviter: Actor, email: str, role: str, full_name: str = "Invited User"
) -> Actor:
    token = invite(inviter, email, role)
    member = sign_up(inviter.app, email, full_name)
    response = member.post(f"{INVITATIONS}/accept", json={"token": token})
    assert response.status_code == 200, response.get_json()
    return member
