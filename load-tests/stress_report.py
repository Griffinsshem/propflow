"""Per-step view of a stress run: achieved throughput, latency and errors as load rises.

Usage: python3 load-tests/stress_report.py <k6 csv(.gz)> [vmstat -t output]
"""

import csv
import gzip
import statistics
import sys
from collections import defaultdict
from datetime import datetime

STEPS = [5, 10, 15, 20, 30, 40, 50, 60]  # must match STRESS.steps in journeys.js
STEP_SECONDS = 75  # 15 s ramp + 60 s hold


def open_any(path: str):  # noqa: ANN201
    return gzip.open(path, "rt", newline="") if path.endswith(".gz") else open(path, newline="")


def pct(values: list[float], q: int) -> float:
    if len(values) < 2:
        return values[0] if values else 0.0
    return statistics.quantiles(values, n=100)[q - 1]


samples = []
with open_any(sys.argv[1]) as handle:
    for row in csv.DictReader(handle):
        if row["metric_name"] in ("http_req_duration", "dropped_iterations"):
            samples.append(
                (int(float(row["timestamp"])), row["metric_name"], float(row["metric_value"]),
                 row.get("status", ""))
            )
start = min(sample[0] for sample in samples)

durations: dict[int, list[float]] = defaultdict(list)
statuses: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
dropped: dict[int, int] = defaultdict(int)
seen: dict[int, list[int]] = defaultdict(list)  # first/last timestamp per step
for timestamp, metric, value, status in samples:
    step = (timestamp - start) // STEP_SECONDS
    if metric == "dropped_iterations":
        dropped[step] += int(value)
    else:
        durations[step].append(value)
        seen[step] = [min(seen[step][0], timestamp), max(seen[step][1], timestamp)] if seen[step] else [timestamp, timestamp]
        statuses[step][status] += 1

cpu: dict[int, list[tuple[int, int]]] = defaultdict(list)
if len(sys.argv) > 2:
    for line in open(sys.argv[2]):
        parts = line.split()
        if len(parts) < 17 or not parts[0].isdigit():
            continue
        try:
            moment = datetime.strptime(f"{parts[-2]} {parts[-1]}", "%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
        offset = int(moment.timestamp()) - start
        if offset >= 0:
            busy = int(parts[12]) + int(parts[13])  # us + sy
            swap = int(parts[6]) + int(parts[7])  # si + so
            cpu[offset // STEP_SECONDS].append((busy, swap))

print("| Step | Target journeys/s | Achieved req/s | p50 ms | p95 ms | p99 ms | 5xx | Timeouts | 429 | 409 | Dropped | CPU busy % | Swap KiB/s |")
print("|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
for step in sorted(durations):
    values = durations[step]
    counts = statuses[step]
    server_errors = sum(n for code, n in counts.items() if code.startswith("5"))
    timeouts = counts.get("0", 0) + counts.get("", 0)
    target = STEPS[step] if step < len(STEPS) else "(ramp-down)"
    usage = cpu.get(step, [])
    busy = f"{statistics.mean(u[0] for u in usage):.0f}" if usage else "-"
    swap = f"{max(u[1] for u in usage)}" if usage else "-"
    print(
        f"| {step + 1} | {target} | {len(values) / (seen[step][1] - seen[step][0] + 1):.1f} | {statistics.median(values):.0f} | "
        f"{pct(values, 95):.0f} | {pct(values, 99):.0f} | {server_errors} | {timeouts} | "
        f"{counts.get('429', 0)} | {counts.get('409', 0)} | {dropped.get(step, 0)} | {busy} | {swap} |"
    )
