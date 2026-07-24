# CAN-Net Benchmarks

## Stage 1 — Transport Comparison (TCP vs UDP vs Serial)

**Test setup:** 100 messages, 64-byte fixed payload, loopback (127.0.0.1) for TCP/UDP,
virtual pty pair (socat) for serial at 9600 baud. WSL2 Ubuntu 24.04, i5-7300HQ/8GB RAM.

| Transport | Avg Latency (ms) | Total Time (ms) | Throughput (msg/s) |
|-----------|-------------------|-------------------|----------------------|
| TCP       | 0.0503            | 5.03              | 19,870.8             |
| UDP       | 0.0958            | 9.58              | 10,438.1             |
| Serial    | 0.1591            | 15.91             | 6,286.8              |

## Observations
- TCP outperformed UDP in this run, which is not the textbook expectation (UDP is
  usually lower-overhead). Likely causes: WSL2's virtualized network stack, Python's
  GIL causing sender/receiver thread contention in the same process, and small sample
  size (100 msgs) not averaging out system jitter. Flagged as a limitation, not a bug.
- Serial numbers reflect **software call overhead only** — a virtual pty does not
  enforce real UART bit-rate timing. A real 9600 baud link would show ~6.7ms/message
  minimum from physics alone (64 bytes x 10 bits/byte / 9600 baud), regardless of
  software speed. Real serial hardware in Stage 7 will produce far more realistic
  numbers than this emulated result.
- This benchmark script (`benchmark_transports.py`) is reused/extended in Stage 5 for
  the full CAN/J1939/RTOS benchmark suite.
