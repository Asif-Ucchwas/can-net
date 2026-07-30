import matplotlib
matplotlib.use('Agg')
"""
Stage 5 Task 19: turn bench_results_raw.json into plots + a summary table,
following the same conventions as the thesis's benchmark_50trials.py
(clear axis labels, saved PNG outputs, printed summary table).
"""

import json
import statistics
import matplotlib.pyplot as plt

with open("bench_results_raw.json") as f:
    data = json.load(f)

# Parse config keys back into (publishers, rate_hz) for sorting/plotting
def parse_key(key):
    pub_str, rate_str = key.split("_")
    publishers = int(pub_str.replace("pub", ""))
    rate_hz = int(rate_str.replace("hz", ""))
    return publishers, rate_hz

summary = []
for key, trials in data.items():
    publishers, rate_hz = parse_key(key)
    avg_drop = statistics.mean(t["drop_rate"] for t in trials) * 100
    avg_throughput = statistics.mean(t["throughput"] for t in trials)
    all_lat = [l for t in trials for l in t["latencies"]]
    avg_lat_ms = statistics.mean(all_lat) * 1000 if all_lat else 0
    max_lat_ms = max(all_lat) * 1000 if all_lat else 0
    summary.append({
        "publishers": publishers, "rate_hz": rate_hz,
        "avg_drop_pct": avg_drop, "avg_throughput": avg_throughput,
        "avg_latency_ms": avg_lat_ms, "max_latency_ms": max_lat_ms,
    })

summary.sort(key=lambda r: (r["publishers"], r["rate_hz"]))

# --- Print summary table ---
print(f"{'Publishers':<12}{'Rate(Hz)':<10}{'Drop%':<10}{'Throughput':<14}{'AvgLat(ms)':<12}{'MaxLat(ms)':<12}")
print("-" * 70)
for r in summary:
    print(f"{r['publishers']:<12}{r['rate_hz']:<10}{r['avg_drop_pct']:<10.2f}"
          f"{r['avg_throughput']:<14.1f}{r['avg_latency_ms']:<12.4f}{r['max_latency_ms']:<12.4f}")

# Also save as markdown table for the repo
with open("BENCHMARK_RESULTS.md", "w") as f:
    f.write("# Stage 5 CAN Bus Benchmark Results\n\n")
    f.write("| Publishers | Rate (Hz) | Drop % | Throughput (msg/s) | Avg Latency (ms) | Max Latency (ms) |\n")
    f.write("|---|---|---|---|---|---|\n")
    for r in summary:
        f.write(f"| {r['publishers']} | {r['rate_hz']} | {r['avg_drop_pct']:.2f} | "
                f"{r['avg_throughput']:.1f} | {r['avg_latency_ms']:.4f} | {r['max_latency_ms']:.4f} |\n")

# --- Plot 1: Drop rate vs publishers, grouped by rate ---
fig, ax = plt.subplots(figsize=(7, 5))
for rate in [10, 100]:
    rows = [r for r in summary if r["rate_hz"] == rate]
    ax.plot([r["publishers"] for r in rows], [r["avg_drop_pct"] for r in rows],
            marker="o", label=f"{rate} Hz")
ax.set_xlabel("Number of Concurrent Publishers")
ax.set_ylabel("Average Drop Rate (%)")
ax.set_title("CAN Bus Drop Rate vs Bus Load")
ax.legend()
ax.grid(True, alpha=0.3)
fig.tight_layout()
fig.savefig("plot_drop_rate.png", dpi=150)

# --- Plot 2: Latency vs publishers, grouped by rate ---
fig, ax = plt.subplots(figsize=(7, 5))
for rate in [10, 100]:
    rows = [r for r in summary if r["rate_hz"] == rate]
    ax.plot([r["publishers"] for r in rows], [r["avg_latency_ms"] for r in rows],
            marker="o", label=f"{rate} Hz")
ax.set_xlabel("Number of Concurrent Publishers")
ax.set_ylabel("Average Latency (ms)")
ax.set_title("CAN Bus Latency vs Bus Load")
ax.legend()
ax.grid(True, alpha=0.3)
fig.tight_layout()
fig.savefig("plot_latency.png", dpi=150)

# --- Plot 3: Throughput vs publishers, grouped by rate ---
fig, ax = plt.subplots(figsize=(7, 5))
for rate in [10, 100]:
    rows = [r for r in summary if r["rate_hz"] == rate]
    ax.plot([r["publishers"] for r in rows], [r["avg_throughput"] for r in rows],
            marker="o", label=f"{rate} Hz")
ax.set_xlabel("Number of Concurrent Publishers")
ax.set_ylabel("Throughput (msg/s)")
ax.set_title("CAN Bus Throughput vs Bus Load")
ax.legend()
ax.grid(True, alpha=0.3)
fig.tight_layout()
fig.savefig("plot_throughput.png", dpi=150)

print("\nSaved: BENCHMARK_RESULTS.md, plot_drop_rate.png, plot_latency.png, plot_throughput.png")
