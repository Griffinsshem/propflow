"""Load-test data generator (spec section 55).

Builds realistic volume with bulk inserts while respecting every constraint. Refuses to run
unless the database name ends in `_load`, so it can never touch development, test or
production data. All accounts share one password, hashed once with the real settings.

Usage: DATABASE_URL=<...>/propflow_load python -m scripts.seed_load_data --orgs 50
"""

from __future__ import annotations

import argparse
import json
import random
import time
import uuid
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import func, insert, select, text

from app import create_app
from app.auth.models import User
from app.auth.passwords import hash_password
from app.contractors.models import Contractor
from app.extensions import db
from app.maintenance.models import MaintenanceRequest, MaintenanceStatusHistory
from app.notifications.models import Notification
from app.organizations.models import Organization, OrganizationMembership
from app.properties.models import Property, PropertyAssignment, Unit
from app.tenants.models import TenantProfile
from app.work_orders.models import WorkOrder

PASSWORD = "load-test-password-123"  # noqa: S105 - shared password of generated local load-test accounts
DOMAIN = "load.propflow.test"  # .test is reserved: these addresses can never receive mail
BATCH = 5000
ACCOUNTS_FILE = Path(__file__).resolve().parents[2] / "load-tests" / "accounts.json"
INSERT_ORDER: list[Any] = [
    Organization,
    User,
    OrganizationMembership,
    Contractor,
    Property,
    PropertyAssignment,
    Unit,
    TenantProfile,
    MaintenanceRequest,
    MaintenanceStatusHistory,
    WorkOrder,
    Notification,
]
CATEGORIES = ["plumbing", "electrical", "water", "appliance", "security", "structural", "other"]
PRIORITIES = ["low"] * 2 + ["normal"] * 5 + ["high"] * 2 + ["urgent"]
# A long-running portfolio: most history is closed, a fraction is live.
STATUS_WEIGHTS = {
    "submitted": 8,
    "triaged": 7,
    "assigned": 10,
    "in_progress": 10,
    "waiting": 5,
    "resolved": 15,
    "closed": 45,
}
PATHS = {
    "submitted": ["submitted"],
    "triaged": ["submitted", "triaged"],
    "assigned": ["submitted", "triaged", "assigned"],
    "in_progress": ["submitted", "triaged", "assigned", "in_progress"],
    "waiting": ["submitted", "triaged", "assigned", "in_progress", "waiting"],
    "resolved": ["submitted", "triaged", "assigned", "in_progress", "resolved"],
    "closed": ["submitted", "triaged", "assigned", "in_progress", "resolved", "closed"],
}
WORK_ORDER_STATUS = {
    "assigned": "assigned",
    "in_progress": "in_progress",
    "waiting": "in_progress",
    "resolved": "completed",
    "closed": "completed",
}

Rows = dict[Any, list[dict[str, Any]]]


class Seeder:
    def __init__(self, args: argparse.Namespace, password_hash: str) -> None:
        self.args = args
        self.rng = random.Random(args.seed)  # noqa: S311 - generated load data, not security
        self.password_hash = password_hash
        self.now = datetime.now(UTC)
        self.accounts: list[dict[str, Any]] = []
        self.totals: dict[str, int] = defaultdict(int)

    def _ago(self, max_days: int = 365) -> datetime:
        return self.now - timedelta(seconds=self.rng.randint(3600, max_days * 86400))

    def _user(self, rows: Rows, email: str, name: str, created: datetime) -> dict[str, Any]:
        user = {
            "id": uuid.uuid4(),
            "email": email,
            "password_hash": self.password_hash,
            "full_name": name,
            "is_active": True,
            "email_verified_at": created,
            "created_at": created,
            "updated_at": created,
        }
        rows[User].append(user)
        return user

    def _member(
        self, rows: Rows, org_id: uuid.UUID, user: dict[str, Any], role: str, created: datetime
    ) -> dict[str, Any]:
        member = {
            "id": uuid.uuid4(),
            "organization_id": org_id,
            "user_id": user["id"],
            "role": role,
            "status": "active",
            "created_at": created,
            "updated_at": created,
        }
        rows[OrganizationMembership].append(member)
        return member

    def _request(
        self,
        rows: Rows,
        org_id: uuid.UUID,
        property_id: uuid.UUID,
        unit_id: uuid.UUID,
        reporter_id: uuid.UUID,
        manager_id: uuid.UUID,
        contractors: list[dict[str, Any]],
    ) -> None:
        status = self.rng.choices(list(STATUS_WEIGHTS), weights=list(STATUS_WEIGHTS.values()))[0]
        path = PATHS[status]
        created = self._ago()
        step = timedelta(hours=self.rng.randint(2, 72))
        times = [min(created + step * i, self.now) for i in range(len(path))]
        category = self.rng.choice(CATEGORIES)
        priority = self.rng.choice(PRIORITIES)
        title = f"{category.replace('_', ' ').title()} issue"
        request_id = uuid.uuid4()
        rows[MaintenanceRequest].append(
            {
                "id": request_id,
                "organization_id": org_id,
                "property_id": property_id,
                "unit_id": unit_id,
                "reported_by_membership_id": reporter_id,
                "category": category,
                "priority": priority,
                "status": status,
                "title": title,
                "description": "Generated for load testing.",
                "access_notes": None,
                "resolved_at": times[path.index("resolved")] if "resolved" in path else None,
                "closed_at": times[-1] if status == "closed" else None,
                "version": len(path),
                "created_at": created,
                "updated_at": times[-1],
            }
        )
        previous: str | None = None
        for to_status, at in zip(path, times, strict=True):
            rows[MaintenanceStatusHistory].append(
                {
                    "id": uuid.uuid4(),
                    "organization_id": org_id,
                    "request_id": request_id,
                    "from_status": previous,
                    "to_status": to_status,
                    "changed_by_membership_id": reporter_id if previous is None else manager_id,
                    "reason": "Waiting for parts" if to_status == "waiting" else None,
                    "created_at": at,
                }
            )
            previous = to_status
        order_status = WORK_ORDER_STATUS.get(status)
        if order_status is not None:
            assigned_at = times[path.index("assigned")]
            rows[WorkOrder].append(
                {
                    "id": uuid.uuid4(),
                    "organization_id": org_id,
                    "request_id": request_id,
                    "contractor_id": self.rng.choice(contractors)["id"],
                    "created_by_membership_id": manager_id,
                    "status": order_status,
                    "priority": priority,
                    "description": None,
                    "due_date": (assigned_at + timedelta(days=7)).date(),
                    "completed_at": times[-1] if order_status == "completed" else None,
                    "version": 1,
                    "created_at": assigned_at,
                    "updated_at": times[-1],
                }
            )
        rows[Notification].append(
            {
                "id": uuid.uuid4(),
                "organization_id": org_id,
                "recipient_membership_id": manager_id,
                "kind": "request_submitted",
                "title": "New maintenance request",
                "body": title,
                "resource_type": "maintenance_request",
                "resource_id": request_id,
                "read_at": None if status == "submitted" else times[-1],
                "created_at": created,
            }
        )

    def seed_organization(self, index: int) -> None:
        rows: Rows = defaultdict(list)
        created = self.now - timedelta(days=400)
        org_id = uuid.uuid4()
        rows[Organization].append(
            {
                "id": org_id,
                "name": f"Load Org {index:03d}",
                "status": "active",
                "created_at": created,
                "updated_at": created,
            }
        )
        owner = self._user(rows, f"owner.{index}@{DOMAIN}", f"Owner {index}", created)
        self._member(rows, org_id, owner, "owner", created)
        managers = [
            self._member(
                rows,
                org_id,
                self._user(rows, f"manager.{index}.{m}@{DOMAIN}", f"Manager {index}-{m}", created),
                "manager",
                created,
            )
            for m in range(2)
        ]
        contractors: list[dict[str, Any]] = []
        for c in range(3):
            login = self._user(
                rows, f"contractor.{index}.{c}@{DOMAIN}", f"Fixer {index}-{c}", created
            )
            member = self._member(rows, org_id, login, "contractor", created)
            contractor = {
                "id": uuid.uuid4(),
                "organization_id": org_id,
                "business_name": f"Contractor {index}-{c}",
                "contact_name": None,
                "phone": None,
                "email": None,
                "specialty": ["plumbing", "electrical", "general"][c],
                "status": "active",
                "membership_id": member["id"],
                "version": 1,
                "created_at": created,
                "updated_at": created,
            }
            rows[Contractor].append(contractor)
            contractors.append(contractor)

        tenant_emails: list[str] = []
        for p in range(self.args.properties):
            property_id = uuid.uuid4()
            rows[Property].append(
                {
                    "id": property_id,
                    "organization_id": org_id,
                    "name": f"Property {index}-{p}",
                    "property_type": "residential",
                    "status": "active",
                    "address_line": f"{p + 1} Load Test Road",
                    "city": "Nairobi",
                    "region": None,
                    "country_code": "KE",
                    "description": None,
                    "version": 1,
                    "created_at": created,
                    "updated_at": created,
                }
            )
            manager = managers[p % len(managers)]
            rows[PropertyAssignment].append(
                {
                    "id": uuid.uuid4(),
                    "organization_id": org_id,
                    "property_id": property_id,
                    "membership_id": manager["id"],
                    "created_at": created,
                }
            )
            for u in range(self.args.units):
                unit_id = uuid.uuid4()
                rows[Unit].append(
                    {
                        "id": unit_id,
                        "organization_id": org_id,
                        "property_id": property_id,
                        "building_id": None,
                        "label": f"U{u:03d}",
                        "floor": None,
                        "bedrooms": None,
                        "status": "occupied",
                        "version": 1,
                        "created_at": created,
                        "updated_at": created,
                    }
                )
                email = f"tenant.{index}.{p}.{u}@{DOMAIN}"
                tenant = self._member(
                    rows,
                    org_id,
                    self._user(rows, email, f"Tenant {index}-{p}-{u}", created),
                    "tenant",
                    created,
                )
                rows[TenantProfile].append(
                    {
                        "id": uuid.uuid4(),
                        "organization_id": org_id,
                        "membership_id": tenant["id"],
                        "unit_id": unit_id,
                        "phone": None,
                        "move_in_date": created.date(),
                        "version": 1,
                        "created_at": created,
                        "updated_at": created,
                    }
                )
                if len(tenant_emails) < 5:
                    tenant_emails.append(email)
                for _ in range(self.rng.randint(0, 2 * self.args.requests_per_unit)):
                    self._request(
                        rows, org_id, property_id, unit_id, tenant["id"], manager["id"], contractors
                    )

        for model in INSERT_ORDER:
            batch = rows[model]
            for start in range(0, len(batch), BATCH):
                db.session.execute(insert(model), batch[start : start + BATCH])
            self.totals[model.__tablename__] += len(batch)
        db.session.commit()
        self.accounts.append(
            {
                "organization": f"Load Org {index:03d}",
                "owner": f"owner.{index}@{DOMAIN}",
                "managers": [f"manager.{index}.{m}@{DOMAIN}" for m in range(2)],
                "contractors": [f"contractor.{index}.{c}@{DOMAIN}" for c in range(3)],
                "tenants": tenant_emails,
            }
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--orgs", type=int, default=50)
    parser.add_argument("--properties", type=int, default=8, help="per organization")
    parser.add_argument("--units", type=int, default=40, help="per property")
    parser.add_argument("--requests-per-unit", type=int, default=4, help="average")
    parser.add_argument("--seed", type=int, default=20261004, help="deterministic output")
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        name = db.engine.url.database or ""
        if not name.endswith("_load"):
            raise SystemExit(f"Refusing to seed {name!r}: only databases named *_load.")
        existing = db.session.execute(select(func.count()).select_from(Organization)).scalar_one()
        if existing:
            raise SystemExit("Already seeded. Drop and recreate the *_load database first.")

        seeder = Seeder(args, hash_password(PASSWORD))
        started = time.perf_counter()
        for index in range(args.orgs):
            seeder.seed_organization(index)
            if (index + 1) % 10 == 0 or index + 1 == args.orgs:
                print(f"  seeded {index + 1}/{args.orgs} organizations")
        db.session.execute(text("ANALYZE"))  # fresh planner statistics for EXPLAIN
        db.session.commit()

        ACCOUNTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        ACCOUNTS_FILE.write_text(
            json.dumps({"password": PASSWORD, "organizations": seeder.accounts}, indent=2)
        )
        print(f"\nDone in {time.perf_counter() - started:.0f}s. Rows inserted:")
        for table, count in seeder.totals.items():
            print(f"  {table:<30} {count:>10,}")
        print(f"Accounts written to {ACCOUNTS_FILE}")


if __name__ == "__main__":
    main()
