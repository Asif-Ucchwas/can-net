"""
Stage 5 Task 20: Final CAN vs UDP vs TCP comparison, all measured with the
same methodology (same load configs, same trial count, same latency
measurement approach via perf_counter() timestamps).
"""

import matplotlib
matplotlib.use('Agg')

import json
import statistics
import matplotlib.pyplot as plt

def load_and_summarize(filepath, transport_name):
    with open(filepath) as f:
        data = json.load(f)
    summary = {}
    for key, trials in data.items():
        pub_str, rate_str = key.split("_")
        publishers = int(pub_str.replace("pub", ""))
        rate_hz = int(rate_str.replace("hz", ""))
        avg_drop = statistics.mean(t["drop_rate"] for t in trials) * 100
        avg_tp = statistics.mean(t["throughput"] for t in trials)
        all_lat = [l for t in trials for l in t["latencies"]]
        avg_lat_ms = statistics.mean(all_lat) * 1000 if all_lat else 0
        max_lat_ms = max(all_lat) * 1000 if all_lat else 0
        summary[(publishers, rate_hz)] = {
            "drop": avg_drop, "throughput": avg_tp,
            "avg_lat": avg_lat_ms, "max_lat": max_lat_ms,
        }
    return summary

can_summary = load_and_summarize("bench_results_raw.json", "CAN")
udp_summary = load_and_summarize("bench_udp_results.json", "UDP")
tcp_summary = load_and_summarize("bench_tcp_results.json", "TCP")

configs = sorted(can_summary.keys())

# --- Combined markdown table ---
with open("COMPARISON_RESULTS.md", "w") as f:
    f.write("# Stage 5 Task 20: CAN vs UDP vs TCP Comparison\n\n")
    f.write("All measured with identical methodology: same load configs (1/5/15 concurrent\n")
    f.write("publishers x 10/100 Hz), same 20-trial count, same send-to-receive latency\n")
    f.write("measurement approach (perf_counter() timestamps).\n\n")
    f.write("| Publishers | Rate(Hz) | Transport | Drop% | Throughput(msg/s) | AvgLat(ms) | MaxLat(ms) |\n")
    f.write("|---|---|---|---|---|---|---|\n")
    for pub, rate in configs:
        for name, summary in [("CAN", can_summary), ("UDP", udp_summary), ("TCP", tcp_summary)]:
            r = summary[(pub, rate)]
            f.write(f"| {pub} | {rate} | {name} | {r['drop']:.2f} | {r['throughput']:.1f} | "
                    f"{r['avg_lat']:.4f} | {r['max_lat']:.4f} |\n")

print(open("COMPARISON_RESULTS.md").read())

# --- Comparison plot: avg latency across configs, one line per transport ---
fig, ax = plt.subplots(figsize=(9, 5))
labels = [f"{p}pub@{r}Hz" for p, r in configs]
x = range(len(configs))
for name, summary, marker in [("CAN", can_summary, "o"), ("UDP", udp_summary, "s"), ("TCP", tcp_summary, "^")]:
    y = [summary[c]["avg_lat"] for c in configs]
    ax.plot(x, y, marker=marker, label=name)
ax.set_xticks(list(x))
ax.set_xticklabels(labels, rotation=45, ha="right")
ax.set_ylabel("Average Latency (ms)")
ax.set_title("CAN vs UDP vs TCP: Average Latency Across Load Configurations")
ax.legend()
ax.grid(True, alpha=0.3)
fig.tight_layout()
fig.savefig("plot_transport_comparison_latency.png", dpi=150)

# --- Comparison plot: throughput ---
fig, ax = plt.subplots(figsize=(9, 5))
for name, summary, marker in [("CAN", can_summary, "o"), ("UDP", udp_summary, "s"), ("TCP", tcp_summary, "^")]:
    y = [summary[c]["throughput"] for c in configs]
    ax.plot(x, y, marker=marker, label=name)
ax.set_xticks(list(x))
ax.set_xticklabels(labels, rotation=45, ha="right")
ax.set_ylabel("Throughput (msg/s)")
ax.set_title("CAN vs UDP vs TCP: Throughput Across Load Configurations")
ax.legend()
ax.grid(True, alpha=0.3)
fig.tight_layout()
fig.savefig("plot_transport_comparison_throughput.png", dpi=150)

print("\nSaved: COMPARISON_RESULTS.md, plot_transport_comparison_latency.png, plot_transport_comparison_throughput.png")
