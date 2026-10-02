import pytest
from flask import Flask
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import DBAPIError

from app.audit import service as audit
from app.audit.models import AuditLog
from app.extensions import db
from tests.support import ORGS, activate, add_member, create_organization, sign_up

AUDIT = "/api/v1/audit-log"


def test_organization_changes_are_audited_with_actor_and_request_id(app: Flask) -> None:
    owner = sign_up(app, "owner@example.com")
    org_id = create_organization(owner, "Audited Ltd")
    owner.patch(f"{ORGS}/{org_id}", json={"name": "Audited Holdings"})
    items = owner.get(AUDIT).get_json()["items"]
    assert [item["action"] for item in items] == ["organization.updated", "organization.created"]
    updated = items[0]
    assert updated["actor_user_id"] == owner.user_id
    assert updated["details"] == {"name": {"from": "Audited Ltd", "to": "Audited Holdings"}}
    assert updated["request_id"]


def test_audit_log_is_owner_only(app: Flask) -> None:
    owner = sign_up(app, "owner@example.com")
    org_id = create_organization(owner, "Org")
    manager = sign_up(app, "manager@example.com")
    add_member(app, org_id, manager, "manager")
    activate(manager, org_id)
    assert manager.get(AUDIT).status_code == 403


def test_audit_entries_cannot_be_updated_or_deleted(app: Flask) -> None:
    owner = sign_up(app, "owner@example.com")
    create_organization(owner, "Org")
    with app.app_context():
        with pytest.raises(DBAPIError):
            db.session.execute(update(AuditLog).values(action="tampered.event"))
        db.session.rollback()
        with pytest.raises(DBAPIError):
            db.session.execute(delete(AuditLog))
        db.session.rollback()
        assert db.session.execute(select(func.count()).select_from(AuditLog)).scalar_one() == 1


def test_sensitive_detail_keys_are_never_stored(app: Flask) -> None:
    with app.test_request_context():
        entry = audit.record(
            "test.event",
            "test",
            details={"name": "kept", "password": "x", "reset_token": "y", "api_secret": "z"},
        )
        assert entry.details == {"name": "kept"}
        db.session.rollback()


def test_pagination_returns_every_entry_exactly_once(app: Flask) -> None:
    owner = sign_up(app, "owner@example.com")
    org_id = create_organization(owner, "Paged Ltd")
    for index in range(4):
        owner.patch(f"{ORGS}/{org_id}", json={"name": f"Name {index}"})
    seen: list[str] = []
    cursor = None
    while True:
        params = {"limit": 2} | ({"cursor": cursor} if cursor else {})
        page = owner.get(AUDIT, query_string=params).get_json()
        seen += [item["id"] for item in page["items"]]
        cursor = page["next_cursor"]
        if not cursor:
            break
    assert len(seen) == len(set(seen)) == 5


@pytest.mark.parametrize("params", [{"cursor": "not-a-cursor"}, {"limit": 0}, {"limit": 101}])
def test_invalid_pagination_parameters_are_rejected(app: Flask, params: dict[str, object]) -> None:
    owner = sign_up(app, "owner@example.com")
    create_organization(owner, "Org")
    assert owner.get(AUDIT, query_string=params).status_code == 422
