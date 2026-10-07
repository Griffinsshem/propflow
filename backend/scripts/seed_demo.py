"""Demo data for trying PropFlow by hand. Development only.

Everything is created through the API, in-process, with the same helpers the backend tests use,
so every rule applies (validation, permissions, occupancy, notifications). Refuses production
and any database that is not on this machine.

Usage, from backend/:  python scripts/seed_demo.py            (add demo data)
                       python scripts/seed_demo.py --reset    (wipe the local database first)
"""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from flask import Flask  # noqa: E402
from flask_migrate import upgrade  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.exc import ProgrammingError  # noqa: E402

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from tests import support  # noqa: E402

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", ""}
# Where scripts/dev.sh keeps local email and uploads (EMAIL_FILE_DIR, LOCAL_STORAGE_DIR).
LOCAL_DIRS = [Path(tempfile.gettempdir()) / name for name in ("propflow-mail", "propflow-storage")]


def require(condition: object, message: str) -> None:
    """Stop with a clear message. Unlike assert, this cannot be switched off with -O."""
    if not condition:
        sys.exit(f"✗ {message}")


def email(name: str) -> str:
    return f"demo-{name}@example.com"


def guard(app: Flask) -> None:
    if app.config.get("APP_ENV") == "production":
        sys.exit("✗ Refusing: APP_ENV is production.")
    with app.app_context():
        host = db.engine.url.host or ""
    if host not in LOCAL_HOSTS:
        sys.exit(f"✗ Refusing: the database is not on this machine ({host}).")


def reset(app: Flask) -> None:
    answer = input("This deletes ALL data in the local database. Type RESET to continue: ")
    if answer != "RESET":
        sys.exit("Cancelled: nothing was changed.")
    with app.app_context():
        db.session.execute(text("DROP SCHEMA public CASCADE"))
        db.session.execute(text("CREATE SCHEMA public"))
        db.session.commit()
        upgrade(directory=str(BACKEND / "migrations"))
    for folder in LOCAL_DIRS:
        shutil.rmtree(folder, ignore_errors=True)
    print("✓ Local database reset and migrated.")


def already_seeded(app: Flask) -> bool:
    with app.app_context():
        try:
            row = db.session.execute(
                text("SELECT 1 FROM users WHERE email = :email"), {"email": email("owner")}
            ).first()
        except ProgrammingError:  # no users table yet: nothing is seeded
            db.session.rollback()
            return False
    return row is not None


def seed(app: Flask) -> None:
    owner = support.sign_up(app, email("owner"), "Olivia Owner")
    support.create_organization(owner, "Riverside Estates")
    court = support.create_property(owner, "Riverside Court")
    hill = support.create_property(owner, "Hillside Homes")
    a1 = support.create_unit(owner, court["id"], "A1")
    a2 = support.create_unit(owner, court["id"], "A2")
    support.create_unit(owner, court["id"], "B1")
    support.create_unit(owner, hill["id"], "1")

    token = support.invite(owner, email("manager"), "manager")
    manager = support.sign_up(app, email("manager"), "Mary Manager")
    joined = manager.post(f"{support.INVITATIONS}/accept", json={"token": token})
    require(joined.status_code == 200, f"manager could not join: {joined.get_json()}")
    support.assign_manager(owner, court["id"], support.membership_id_of(owner, email("manager")))

    tom = support.place_tenant(owner, email("tenant"), a1["id"], "Tom Tenant")
    tia = support.place_tenant(owner, email("tenant2"), a2["id"], "Tia Tenant")

    fixit = support.create_contractor(owner, "Fixit Plumbing", phone="+254712345678")
    sparks = support.create_contractor(owner, "Bright Sparks Electrical", specialty="electrical")
    support.contractor_user(owner, fixit["id"], email("plumber"), "Fred Fixit")
    support.contractor_user(owner, sparks["id"], email("electrician"), "Elle Sparks")

    support.report_issue(tom, title="Leaking kitchen tap", description="It drips all night.")
    hot = support.report_issue(
        tia, title="No hot water", description="Since this morning.", priority="urgent"
    )
    triaged = support.move_request(owner, hot["id"], "triaged")
    require(triaged.status_code == 200, f"could not triage: {triaged.get_json()}")
    support.create_work_order(
        owner, hot["id"], fixit["id"], description="Check the boiler pressure first."
    )
    commented = owner.post(
        f"{support.MAINTENANCE}/{hot['id']}/comments",
        json={"body": "A plumber is booked for tomorrow morning."},
    )
    require(commented.status_code == 201, f"could not comment: {commented.get_json()}")
    support.report_issue(
        owner,
        property_id=hill["id"],
        title="Hallway light flickering",
        description="Ground floor, near the stairs.",
        category="electrical",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Demo data for local testing.")
    parser.add_argument("--reset", action="store_true", help="wipe the local database first")
    args = parser.parse_args()

    # In-process only: emails go to memory (the seed reads its own invitation links), tasks run
    # inline, and the running server's rate limits and proxy secret do not apply to this script.
    app = create_app(
        "development",
        overrides={
            "EMAIL_BACKEND": "memory",
            "BACKGROUND_TASKS": "sync",
            "RATELIMIT_ENABLED": False,
            "PROXY_SHARED_SECRET": None,
        },
    )
    guard(app)
    if args.reset:
        reset(app)
    if already_seeded(app):
        print(
            "Demo data is already present. For a fresh start: python scripts/seed_demo.py --reset"
        )
        return
    password = getattr(support, "PASSWORD", None)
    require(password, "tests/support.py has no PASSWORD constant: paste this output")
    seed(app)

    print("\n✓ Demo data created: organization 'Riverside Estates'\n")
    print(f"  Every account's password: {password}\n")
    for who, name, role in [
        ("owner", "Olivia Owner", "owner"),
        ("manager", "Mary Manager", "manager (assigned to Riverside Court)"),
        ("tenant", "Tom Tenant", "tenant, Riverside Court A1"),
        ("tenant2", "Tia Tenant", "tenant, Riverside Court A2"),
        ("plumber", "Fred Fixit", "contractor, Fixit Plumbing"),
        ("electrician", "Elle Sparks", "contractor, Bright Sparks Electrical"),
    ]:
        print(f"  {email(who):<34} {name:<14} {role}")


if __name__ == "__main__":
    main()
