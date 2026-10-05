"""EXPLAIN (ANALYZE, BUFFERS) every SELECT the hot read paths actually run.

Calls the real service functions as members of the busiest seeded organization, captures the
exact SQL they send, then explains each statement. Nothing is reimplemented here, so the plans
are the plans production would get. Compact output by default; --full prints whole plans.

Usage: DATABASE_URL=<...>/propflow_load python -m scripts.explain_hot_queries
"""

from __future__ import annotations

import argparse
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any

from sqlalchemy import event, func, select

from app import create_app
from app.authz.context import OrgContext
from app.dashboards import service as dashboards
from app.extensions import db
from app.maintenance import service as maintenance
from app.maintenance.models import MaintenanceRequest
from app.notifications import service as notifications
from app.organizations.models import MembershipRole, OrganizationMembership
from app.work_orders import service as work_orders


def context_for(role: MembershipRole, organization_id: Any) -> OrgContext:
    member = db.session.execute(
        select(OrganizationMembership)
        .where(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.role == role,
        )
        .limit(1)
    ).scalar_one()
    return OrgContext(
        user_id=member.user_id,
        organization_id=organization_id,
        membership_id=member.id,
        role=role,
    )


@contextmanager
def captured_selects() -> Iterator[list[tuple[str, Any]]]:
    statements: list[tuple[str, Any]] = []

    def record(_conn: Any, _cursor: Any, statement: str, params: Any, *_rest: Any) -> None:
        if statement.lstrip().upper().startswith("SELECT"):
            statements.append((statement, params))

    event.listen(db.engine, "before_cursor_execute", record)
    try:
        yield statements
    finally:
        event.remove(db.engine, "before_cursor_execute", record)


def explain(label: str, call: Callable[[], Any], *, full: bool) -> None:
    with captured_selects() as statements:
        started = time.perf_counter()
        call()
        elapsed = (time.perf_counter() - started) * 1000
    print(f"\n### {label}: {len(statements)} queries, {elapsed:.1f} ms end-to-end")
    with db.engine.connect() as conn:
        for number, (statement, params) in enumerate(statements, 1):
            # Our own captured statement, re-run under EXPLAIN with its original parameters.
            sql = f"EXPLAIN (ANALYZE, BUFFERS) {statement}"
            plan = [row[0] for row in conn.exec_driver_sql(sql, params)]
            if full:
                print(f"\n  [{number}] {statement[:200]}")
                print("\n".join(f"      {line}" for line in plan))
                continue
            timing = next((line for line in plan if line.startswith("Execution Time")), "")
            print(f"  [{number}] {timing}")
            for line in [line.strip() for line in plan if "Scan" in line][:5]:
                print(f"        {line[:150]}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full", action="store_true", help="print complete plans")
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        name = db.engine.url.database or ""
        if not name.endswith("_load"):
            raise SystemExit(f"Refusing to run against {name!r}: use the seeded *_load database.")
        busiest = db.session.execute(
            select(MaintenanceRequest.organization_id)
            .group_by(MaintenanceRequest.organization_id)
            .order_by(func.count().desc())
            .limit(1)
        ).scalar_one()
        owner = context_for(MembershipRole.OWNER, busiest)
        manager = context_for(MembershipRole.MANAGER, busiest)
        tenant = context_for(MembershipRole.TENANT, busiest)
        contractor = context_for(MembershipRole.CONTRACTOR, busiest)
        total = db.session.execute(
            select(func.count()).select_from(MaintenanceRequest)
        ).scalar_one()
        print(f"Database holds {total:,} maintenance requests.")

        page: dict[str, Any] = {"limit": 25, "cursor": None}
        no_filters: dict[str, Any] = {"status": None, "property_id": None, "unit_id": None}
        explain(
            "operations dashboard (manager)",
            lambda: dashboards.operations(manager, property_id=None),
            full=args.full,
        )
        explain(
            "operations dashboard (owner)",
            lambda: dashboards.operations(owner, property_id=None),
            full=args.full,
        )
        explain(
            "organization dashboard (owner)", lambda: dashboards.organization(owner), full=args.full
        )
        explain(
            "maintenance list, first page (owner)",
            lambda: maintenance.list_requests(owner, priority=None, **no_filters, **page),
            full=args.full,
        )
        explain(
            "maintenance list, urgent only (manager)",
            lambda: maintenance.list_requests(manager, priority="urgent", **no_filters, **page),
            full=args.full,
        )
        explain(
            "overdue work orders (owner)",
            lambda: work_orders.list_work_orders(
                owner, status=None, contractor_id=None, request_id=None, overdue=True, **page
            ),
            full=args.full,
        )
        explain(
            "unread notification count (manager)",
            lambda: notifications.unread_count(manager),
            full=args.full,
        )
        explain("tenant dashboard", lambda: dashboards.tenant(tenant), full=args.full)
        explain("contractor dashboard", lambda: dashboards.contractor(contractor), full=args.full)


if __name__ == "__main__":
    main()
