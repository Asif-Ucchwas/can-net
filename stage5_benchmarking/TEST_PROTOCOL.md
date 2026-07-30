# Stage 5 Benchmark Test Protocol

## Objective
Quantify CAN bus performance (latency, drop rate, throughput) under varying
load conditions, using the real J1939 signals validated in Stage 3, and
compare against Stage 1's TCP/UDP/Serial baseline.

## Fixed Message Set
- EngineSpeed (PGN 61444/EEC1) and VehicleSpeed (PGN 65265/CCVS1) - the same
  validated J1939 encodings from Stage 3, not new/arbitrary test data.
- Fixed 8-byte payload per message (standard CAN frame size).

## Independent Variables
| Variable | Levels |
|---|---|
| Bus load (concurrent publishers) | 1 (light), 5 (medium), 15 (heavy) |
| Message rate per publisher | 10 Hz, 100 Hz |

-> 3 x 2 = 6 configurations total.

## Trials
- 20 trials per configuration (120 total runs).
- Documented methodology choice: this is fewer than the thesis's 50-trial
  standard, which was calibrated for different hardware/domain constraints.
  20 trials on this software-only virtual bus, on an 8GB RAM laptop, is judged
  sufficient for stable averages without an excessive total runtime - not
  presented as equivalent statistical rigor to the thesis work.
- Each trial runs for 2 seconds of steady-state traffic.

## Metrics Captured (per trial)
1. **Latency** - time from send to receive, per message (mean, min, max).
2. **Drop rate** - (sent count - received count) / sent count.
3. **Throughput** - successfully received messages per second.

## Fixed (Non-Varied) Elements
- Payload size: 8 bytes (standard CAN frame).
- Trial duration: 2 seconds.
- Environment: WSL2 Ubuntu 24.04, vcan0, personal laptop (i5-7300HQ/8GB RAM).

## Comparison Baseline (Task 20)
Results will be compared against Stage 1's TCP/UDP/Serial benchmark
(BENCHMARKS.md) using the same latency/throughput metric definitions, to
quantify CAN's tradeoffs vs general-purpose networking transports for a
simulated telemetry task.
