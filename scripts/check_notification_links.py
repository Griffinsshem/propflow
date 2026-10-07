#!/usr/bin/env python3
"""Every resource type the API puts on a notification must have a page in the frontend.

Reads backend/app/notifications/service.py and frontend/src/features/notifications/links.ts,
and fails if a notification would link nowhere. It also fails if a notification is created in
a way this check cannot read, so it can never pass by not seeing anything.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
service = (ROOT / "backend/app/notifications/service.py").read_text()
links = (ROOT / "frontend/src/features/notifications/links.ts").read_text()

calls = len(re.findall(r"^\s+_add\(", service, re.M))
used = re.findall(r'"([a-z_]+)",\s*\w+\.id,\s*\)', service)
mapped = set(re.findall(r"^\s*([a-z_]+): \(id\) =>", links, re.M))

print(f"resource types used by notifications: {sorted(set(used))}")
print(f"resource types with a frontend page:  {sorted(mapped)}")
problems = []
if calls == 0:
    problems.append("no _add(...) calls found in notifications/service.py")
if len(used) != calls:
    problems.append(
        f"{calls} _add(...) calls but {len(used)} readable resource types: "
        "a notification passes its resource type in a way this check cannot read"
    )
missing = sorted(set(used) - mapped)
if missing:
    problems.append(f"no frontend page for: {missing}")
if problems:
    print("\n".join(f"✗ {problem}" for problem in problems))
    sys.exit(1)
print("✓ every notification resource type has a page")
