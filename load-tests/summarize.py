"""Print a k6 JSON summary as the markdown tables used in docs/performance/.

Usage: python3 load-tests/summarize.py load-tests/results/<run>.json
"""

import json
import sys

PREFIX = "http_req_duration{name:"

data = json.load(open(sys.argv[1]))
metrics = data["metrics"]


def value(metric: str, key: str) -> float:
    return float(metrics.get(metric, {}).get("values", {}).get(key, 0))


seconds = data["state"]["testRunDurationMs"] / 1000
print(f"Duration: {seconds:.0f}s")
print(f"Requests: {value('http_reqs', 'count'):.0f} ({value('http_reqs', 'rate'):.1f}/s)")
print(f"Failed requests: {value('http_req_failed', 'rate') * 100:.2f}%")
print(f"Checks passed: {value('checks', 'rate') * 100:.2f}%")
print(f"429 responses: {value('rate_limited_responses', 'count'):.0f}")
print(f"409 responses: {value('conflict_responses', 'count'):.0f}\n")

print("| Endpoint | Requests | p50 (ms) | p95 (ms) | p99 (ms) | Max (ms) | Budget |")
print("|---|---:|---:|---:|---:|---:|---|")
rows = []
for key, metric in metrics.items():
    if not key.startswith(PREFIX):
        continue
    v = metric["values"]
    passed = all(t.get("ok", True) for t in metric.get("thresholds", {}).values())
    rows.append(
        (key[len(PREFIX) : -1], v.get("count", 0), v["med"], v["p(95)"], v["p(99)"], v["max"], passed)
    )
for name, count, med, p95, p99, top, passed in sorted(rows):
    status = "pass" if passed else "**FAIL**"
    print(f"| `{name}` | {count:.0f} | {med:.1f} | {p95:.1f} | {p99:.1f} | {top:.1f} | {status} |")
