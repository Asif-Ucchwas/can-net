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

## Stage 2 — CAN Bus Fundamentals

### Task 5: Virtual CAN interface (vcan0) via SocketCAN
- Loaded vcan kernel module (`sudo modprobe vcan`) — confirmed native support in
  WSL2 Ubuntu 24.04 kernel, no custom kernel build needed.
- Created and activated virtual CAN interface: `ip link add dev vcan0 type vcan`
  + `ip link set up vcan0`.
- Installed can-utils (cansend, candump).
- Verified end-to-end: `cansend vcan0 123#DEADBEEF` -> immediately visible via
  `candump vcan0` as `vcan0  123   [4]  DE AD BE EF`.
- Environment: WSL2 Ubuntu 24.04, can-utils 2023.03-1.

### Task 6: Python pub/sub nodes (python-can) with CAN ID filtering
- Installed python-can 4.6.1 via pip3 (--break-system-packages, per Ubuntu 24.04's
  externally-managed-environment restriction).
- Built can_publisher.py: sends fixed-rate frames on two CAN IDs (0x100, 0x200)
  every 0.5s, alternating payload counters.
- Built can_subscriber.py: uses SocketCAN's kernel-level can_filters (can_mask
  0x7FF, full 11-bit match) to only receive 0x100 - filtering happens in the
  kernel, not by checking every message in Python.
- Verified end-to-end: publisher sent both IDs continuously; subscriber received
  only 0x100 frames (61 messages, seq 0-60), 0x200 never surfaced - confirms
  kernel-level filtering works correctly.
- Fixed deprecation warning (bustype= -> interface=) and added bus.shutdown() in
  a finally block for clean socket teardown on exit.

### Task 7: DBC file + cantools decoding
- Wrote vehicle.dbc defining VEHICLE_STATUS (id=0x100, 8 bytes) with three signals:
  Speed (scale 0.01, km/h), RPM (scale 0.25, rpm), BatteryTemp (scale 1, offset -40,
  degC) - validated parse-clean with cantools.database.load_file().
- Built can_dbc_publisher.py: encodes realistic random values using message.encode(),
  which handles scale/offset math automatically per the DBC definition.
- Built can_dbc_decoder.py: uses db.decode_message() to turn raw CAN bytes back into
  human-readable signal values; wrapped in try/except KeyError to skip any CAN ID
  not defined in the DBC.
- Verified end-to-end: every decoded value matched the publisher's sent value within
  expected DBC quantization (e.g., RPM's 0.25 scale rounds to nearest quarter -
  genuine precision limit of the signal definition, not a bug).
- Note: minor floating-point display artifacts (e.g. 21.400000000000002) are normal
  binary float representation quirks from the 0.01 scale factor, not decode errors.
- Also added setup_vcan.sh - vcan0 doesn't persist across WSL2 restarts, so this
  script recreates it at the start of any new session.


### Task 8: Bus contention with multiple nodes, document arbitration
- Built can_bus_contention.py: 3 simulated nodes (high_priority_brake id=0x010,
  medium_priority_engine id=0x100, low_priority_infotainment id=0x500) each
  flooding 50 frames simultaneously via separate threads on the same vcan0 bus.
- Captured full bus traffic with `candump vcan0 -l` (150 frames logged, confirmed
  50/50/50 split across the three IDs via awk/uniq -c analysis).
- Observed interleaving: early burst where 0x010 sent 8 consecutive frames before
  0x500's second frame appeared, settling into a roughly even interleaved pattern
  by mid-log. This reflects Python thread/GIL scheduling behavior, NOT real CAN
  arbitration.
- Key distinction documented: on real CAN hardware, simultaneous transmission is
  resolved by the CAN ID itself during the arbitration field of the frame - lower
  numeric ID wins non-destructively (dominant bit dominates recessive bit during
  bitwise arbitration), and losing nodes back off and automatically retry with
  zero data corruption or restart delay. This happens at the physical/electrical
  layer in real hardware and cannot be observed on a virtual vcan0 interface,
  since the kernel just queues frames from whichever thread submits first - no
  real electrical contention exists in software emulation.
- This is a genuine limitation of Stage 2 (software-only) - true arbitration
  timing validation is deferred to Stage 7 (real hardware, oscilloscope capture
  of the CAN bus during simultaneous transmission from multiple physical nodes).

## Stage 2 — COMPLETE (4/4 tasks)
