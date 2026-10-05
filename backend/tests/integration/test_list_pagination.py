from flask import Flask

from tests.support import (
    MAINTENANCE,
    create_organization,
    create_property,
    create_unit,
    place_tenant,
    report_issue,
    sign_up,
)


def test_request_pages_return_every_request_once_newest_first(app: Flask) -> None:
    owner = sign_up(app, "owner@example.com", "Olivia Owner")
    create_organization(owner, "Paged Estates")
    prop = create_property(owner, "Paged Court")
    unit = create_unit(owner, prop["id"], "A1")
    tenant = place_tenant(owner, "tenant@example.com", unit["id"])
    created = [report_issue(tenant, title=f"Issue {index}")["id"] for index in range(5)]

    seen: list[str] = []
    cursor = None
    while True:
        query = {"limit": 2} | ({"cursor": cursor} if cursor else {})
        page = owner.get(MAINTENANCE, query_string=query).get_json()
        seen += [item["id"] for item in page["items"]]
        cursor = page["next_cursor"]
        if not cursor:
            break
    assert seen == list(reversed(created))
