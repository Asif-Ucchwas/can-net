# CAN-Net DEVLOG

## Stage 1 — Networking Foundations

### Task 1: TCP client/server with length-prefix framing
- Implemented `recv_exact()` to guarantee reading exact byte counts from a TCP stream,
  since TCP is a byte stream with no built-in message boundaries.
- Used a 4-byte big-endian length header (`struct.pack("!I", len(body))`) before each
  JSON message body to solve the framing problem reliably.
- Verified end-to-end: client sent 5 structured JSON messages (fake IMU telemetry),
  server received all 5 in order, no merging/truncation.
- Environment: WSL2 Ubuntu 24.04, Python 3.12.3, personal laptop (i5-7300HQ/8GB RAM).

### Task 2: UDP with simulated drops/reordering (tc netem)
- Built a UDP sender/receiver pair (20 sequenced messages, fake_lidar payload).
- Baseline (no netem): all 20 messages received in order, 0% loss — expected on loopback.
- Injected `tc qdisc add dev lo root netem loss 20% delay 50ms 20ms reorder 25% 50%`.
- Result: 3/20 messages dropped (seq 1, 8, 10) and one out-of-order pair (seq 12 arrived
  before seq 11) — demonstrates UDP gives zero delivery/order guarantees, unlike TCP.
- Cleaned up with `tc qdisc del dev lo root` after test.
- Environment: WSL2 Ubuntu 24.04 kernel supports netem out of the box, no extra config needed.

### Task 3: Virtual serial pair (socat) streaming sensor-style data
- Created a virtual serial pair with `socat -d -d pty,raw,echo=0 pty,raw,echo=0`,
  producing two linked pseudo-terminals (/dev/pts/3, /dev/pts/4).
- Built sender/receiver using pyserial, streaming fake GPS telemetry (lat/lon, JSON
  newline-delimited) from one end to the other.
- Verified: all 10 messages arrived in order, no drops/corruption — expected since
  it's a direct byte pipe with no lossy network medium (unlike UDP over a real link).
- Environment: WSL2 Ubuntu 24.04, pyserial 3.5.

### Task 4: Benchmark table — TCP vs UDP vs Serial (latency/throughput)
- Built benchmark_transports.py: 100 messages, 64-byte payload, threaded sender/
  receiver per transport, timing send-call latency and derived throughput.
- Results: TCP 19,870.8 msg/s, UDP 10,438.1 msg/s, Serial 6,286.8 msg/s (see
  BENCHMARKS.md for full table).
- Noted limitation: TCP outperforming UDP is atypical, likely due to WSL2's
  virtualized network stack and GIL contention between threads in one process —
  not a true reflection of native Linux transport behavior. Documented as a caveat
  rather than treated as ground truth.
- Noted limitation: virtual pty serial doesn't enforce real UART baud-rate timing,
  so serial numbers here reflect software overhead only, not real 9600-baud physics.
  Real hardware in Stage 7 will give more accurate serial numbers.
- Full benchmark script will be extended in Stage 5 for CAN/J1939/RTOS comparisons.

## Stage 1 — COMPLETE (4/4 tasks)
