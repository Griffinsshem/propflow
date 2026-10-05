"""Split server-side request time into database time and application time, per route.

Reads request_completed lines from the API log (development key=value or production JSON).
Usage: python3 load-tests/route_timings.py /tmp/propflow-profile-server.log
"""

import json
import re
import statistics
import sys
from collections import defaultdict

ANSI = re.compile(r"\x1b\[[0-9;]*m")
FIELD = re.compile(r"(\w+)=('[^']*'|\"[^\"]*\"|\S+)")


def parse(line: str) -> dict[str, str]:
    line = ANSI.sub("", line).strip()
    if line.startswith("{"):
        try:
            return {key: str(value) for key, value in json.loads(line).items()}
        except json.JSONDecodeError:
            return {}
    return {key: value.strip("'\"") for key, value in FIELD.findall(line)}


def p95(values: list[float]) -> float:
    return statistics.quantiles(values, n=20)[18] if len(values) >= 2 else values[0]


samples: dict[str, list[tuple[float, float, int]]] = defaultdict(list)
for raw in open(sys.argv[1], errors="replace"):
    if "request_completed" not in raw:
        continue
    fields = parse(raw)
    try:
        key = f"{fields['method']} {fields['route']}"
        samples[key].append(
            (float(fields["duration_ms"]), float(fields["db_ms"]), int(fields["db_queries"]))
        )
    except (KeyError, ValueError):
        continue

print("| Route | Requests | Total p50 | DB p50 | App p50 | Queries p50 | Total p95 | DB p95 |")
print("|---|---:|---:|---:|---:|---:|---:|---:|")
rows = []
for key, values in samples.items():
    totals = [v[0] for v in values]
    dbs = [v[1] for v in values]
    apps = [v[0] - v[1] for v in values]
    queries = [v[2] for v in values]
    rows.append((statistics.median(totals), key, len(values), dbs, apps, queries, totals))
for median_total, key, count, dbs, apps, queries, totals in sorted(rows, reverse=True):
    print(
        f"| `{key}` | {count} | {median_total:.1f} | {statistics.median(dbs):.1f} | "
        f"{statistics.median(apps):.1f} | {statistics.median(queries):.0f} | "
        f"{p95(totals):.1f} | {p95(dbs):.1f} |"
    )
