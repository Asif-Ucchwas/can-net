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

## Stage 3 — J1939 Protocol Layer

### Task 9: J1939 PGN/SPN encoding on top of Stage 2 CAN nodes
- Built j1939_ids.py: manual 29-bit extended CAN ID encoder/decoder implementing
  the real J1939 layout (Priority[3 bits] + PGN[18 bits] + Source Address[8 bits]).
  Self-test confirmed round-trip encode/decode correctness (0x0CF00400 -> priority=3,
  pgn=61444, source=0).
- Built j1939_signals.py: real, standardized SPN byte layouts -
  SPN 190 (Engine Speed, PGN 61444/EEC1, bytes 3-4, 0.125 rpm/bit resolution) and
  SPN 84 (Vehicle Speed, PGN 65265/CCVS1, bytes 1-2, 1/256 km/h resolution).
- Built j1939_publisher.py / j1939_subscriber.py using is_extended_id=True (required
  for J1939's 29-bit IDs, vs Stage 2's 11-bit standard IDs).
- Verified end-to-end over vcan0: subscriber correctly identified messages by PGN
  and decoded both signals; all values matched sender within expected quantization
  (e.g., 3224.538 rpm sent -> 3224.5 decoded, matches 0.125 rpm resolution).

### Task 10: Multi-packet transport (BAM/TP.CM) for messages >8 bytes
- Implemented J1939's BAM (Broadcast Announce Message) transport protocol -
  the mechanism for sending messages larger than CAN's native 8-byte frame limit.
- j1939_bam.py: build_bam_cm_frame() constructs the TP.CM (PGN 60416) announcement
  frame (total size + packet count + target PGN); fragment_message()/
  reassemble_message() handle splitting into 7-byte TP.DT (PGN 60160) chunks
  (1 byte per frame reserved for sequence number) and reassembling them back.
  In-memory self-test passed first (51-byte fake diagnostic string -> 8 frames
  -> exact reassembly).
- j1939_bam_sender.py / j1939_bam_receiver.py: put this on the real vcan0 bus.
  Sender transmits one TP.CM + 8 TP.DT frames with realistic ~50ms inter-frame
  spacing. Receiver tracks transfer state (waiting for TP.CM -> collecting TP.DT
  frames by sequence -> reassemble once count matches announced total).
- Verified end-to-end over vcan0: receiver correctly reported "expecting 51 bytes
  across 8 packets" from TP.CM, tracked all 8 TP.DT frames in order, and printed
  the exact original message on reassembly - genuine live multi-frame CAN
  transport, not just an in-memory simulation.
- Scope limitation (documented, not implemented): only BAM (broadcast, no flow
  control) was built. RTS/CTS (Connection Mode - point-to-point with destination
  ECU pacing the sender via flow-control frames) was intentionally skipped as
  out of scope for this stage - BAM covers the core fragmentation/reassembly
  concept that "most tutorials skip," which was the goal of this task.

### Task 11: Diagnostic node requesting specific PGNs and parsing responses
- Implemented J1939's Request PGN pattern (PGN 59904) - the request/response
  mechanism used by real diagnostic tools, distinct from the broadcast-only
  traffic built in Tasks 9-10.
- j1939_ecu_responder.py: listens for Request PGN messages, parses the 3-byte
  little-endian requested-PGN payload, and responds on-demand only for PGNs it
  supports (EngineSpeed/61444, VehicleSpeed/65265) - ignores unsupported requests.
- j1939_diagnostic_tool.py: sends requests using source address 0xF9 (the
  conventional J1939 diagnostic tool address), with a timeout-based wait for
  matching-PGN responses.
- Verified end-to-end over vcan0, 3 test cases: (1) EngineSpeed request -> real
  response, values matched within 0.125 rpm quantization; (2) VehicleSpeed
  request -> real response, matched within 1/256 km/h quantization; (3) request
  for unsupported PGN 65226 -> correctly timed out with no response, proving
  the failure path works, not just the happy path.

## Stage 3 — Task 12 (up next): stress-test with multiple simulated ECUs

### Task 12: Stress-test with multiple simulated ECUs, verify interleaved multi-packet parsing
- Upgraded the BAM receiver from Task 10's single-transfer (global state) design
  to j1939_bam_multi_receiver.py, which tracks in-progress transfers keyed by
  source address (dict of {src: {total_size, num_packets, frames}}). This allows
  multiple ECUs to have simultaneous in-progress BAM transfers without one
  corrupting another's reassembly.
- Built j1939_bam_stress_sender.py: 3 simulated ECUs (Engine_ECU src=0x00,
  Trans_ECU src=0x03, Brake_ECU src=0x0B) launched concurrently via threads,
  each sending a distinct multi-packet fault message (36-42 bytes, 6 TP.DT
  frames each) with only 20ms between their own frames - short enough that
  frames from different ECUs genuinely interleave on the bus.
- Verified over vcan0: receiver log shows true interleaving (e.g. src=0x00 seq=1
  -> src=0x03 seq=1 -> src=0x00 seq=2 -> src=0x0B seq=1 -> src=0x03 seq=2...),
  NOT sequential per-ECU batches. All 3 messages reassembled correctly and
  independently despite the interleaving. Confirmed with candump capture: 21
  frames logged (3 TP.CM + 18 TP.DT), matching expected count exactly.
    src=0x00 -> "ENGINE_TEMP_HIGH_WARNING_COOLANT_LOW"
    src=0x03 -> "TRANSMISSION_GEAR_SLIP_DETECTED_CODE_P0730"
    src=0x0B -> "ABS_SENSOR_FAULT_REAR_LEFT_WHEEL_SPEED"
- This confirms the per-source-address state tracking design is correct under
  realistic concurrent multi-ECU bus load, which the single-transfer Task 10
  receiver could not have handled safely.

## Stage 3 — COMPLETE (4/4 tasks)

## Stage 4 — RTOS Integration

### Task 13: Zephyr RTOS running under QEMU
- Installed Zephyr toolchain from scratch: system build deps (cmake, ninja, dtc,
  gcc-multilib, etc.), west (Zephyr's meta build tool) in a dedicated Python venv
  (zephyr_venv, kept isolated from the python-can/cantools environment used in
  Stages 2-3), full Zephyr source tree via `west init` + `west update` (~884MB,
  dozens of HAL/module repos), and Zephyr SDK 1.0.1 (arm-zephyr-eabi toolchain)
  via `west sdk install`.
- Confirmed end-to-end with samples/hello_world targeting qemu_cortex_m3 (emulated
  ARM Cortex-M3, ti_lm3s6965 board): built successfully (134/134 targets, FLASH
  3.70% used, RAM 6.27% used) and ran under QEMU, printing
  "Hello World! qemu_cortex_m3/ti_lm3s6965" - confirms the full toolchain
  (cross-compiler, device tree, CMake/Ninja build, QEMU emulation) works
  end-to-end on this 8GB RAM laptop, no physical board required.
- Minor harmless warning noted: ccache 4.9.1 found but Zephyr wanted >=4.12,
  so ccache wasn't used for this build - doesn't affect correctness, only
  means rebuilds won't be cache-accelerated. Not worth fixing for this project.

### Task 14: Zephyr CAN driver task connected to Stage 2/3 traffic (vcan0)
- Investigated Zephyr's native_sim CAN support: found the built-in
  `socketcan-native-sim` snippet, which bridges native_sim's CAN driver to a
  real Linux SocketCAN interface via devicetree binding (zephyr,canbus -> can0,
  compatible = "zephyr,native-linux-can").
- Discovered native_sim's devicetree hardcodes the host interface name as
  "zcan0" (not configurable via build flag) - worked around this by adding
  zcan0 as a Linux altname on the existing vcan0 interface:
  `sudo ip link property add dev vcan0 altname zcan0`. This means Zephyr's CAN
  driver and all our Stage 2/3 Python tooling (python-can, cantools) now share
  the exact same underlying virtual bus.
- Built and ran samples/drivers/can/counter targeting native_sim with the
  socketcan-native-sim snippet applied:
  `west build -b native_sim -S socketcan-native-sim samples/drivers/can/counter`
- Verified genuine bidirectional bridging with a separate `candump vcan0`
  running concurrently: Zephyr's internal "Counter received: N" log values
  matched exactly, byte-for-byte, with real CAN frames observed on vcan0
  (id=0x00012345, incrementing hex payload 00 00 -> 00 F9 matching 0-249).
  This confirms Zephyr's RTOS-scheduled CAN task is writing to and reading
  from the real Linux SocketCAN interface, not an isolated internal loopback.
- Added zephyr_project/ and zephyr_venv/ to .gitignore - these are large
  (~1GB+) externally-reproducible directories (`west init` + `west update` +
  `west sdk install` recreates them exactly), not our own code, so only our
  custom application source will be tracked going forward.

### Task 15: Second task at different priority/period, demonstrate preemption
- Built stage4_rtos/preemption_demo/: standalone Zephyr app (own CMakeLists.txt +
  prj.conf, separate from zephyr_project's built-in samples) with two threads -
  high_priority_task (priority 2, wakes every 500ms) and low_priority_task
  (priority 5, runs an 800ms CPU-bound busy-wait each cycle - deliberately
  longer than HIGH's wake period, to force a preemption scenario).
- Important gotcha discovered and fixed: an initial version used a manual
  while-loop spinning on k_uptime_get() to busy-wait. This hung forever under
  native_sim, because native_sim's virtual clock only advances at kernel
  scheduling events (thread sleep/block) - a tight spin loop that never yields
  never lets simulated time progress, so the "800ms" wait never completed.
  Fixed by switching to Zephyr's own k_busy_wait() primitive, which correctly
  integrates with native_sim's virtual-time model (as well as real hardware).
  This is a genuine, documented native_sim nuance worth remembering for any
  future Zephyr work.
- Verified preemption with real timestamped evidence: e.g. LOW starts its
  800ms busy-wait at t=50ms (expected to run uninterrupted until t=850ms), but
  HIGH's log line appears at t=560ms - squarely inside LOW's busy-wait window -
  and LOW still finishes at exactly t=850ms (50+800), proving it was suspended
  and resumed correctly by the scheduler rather than corrupted or restarted.
  This pattern repeated consistently across dozens of cycles in a 37-second run.
- Learned west build-directory workaround for apps living outside zephyr_project:
  `west build -b <board> <app_path> -d <app_path>/build` lets west build our own
  app while still using the zephyr_project workspace/toolchain.

### Task 16: Document RTOS scheduling parameters
- Wrote docs/rtos_scheduling_notes.md covering thread priorities (Zephyr:
  lower number = higher priority, opposite of FreeRTOS's convention - worth
  knowing per-RTOS), stack sizing considerations (1024B per thread was
  generous for these simple demo tasks; real embedded work needs profiling,
  not guessing), and the three core timing primitives used across Stage 4
  (k_sleep for voluntary yield/periods, k_busy_wait for CPU-bound work,
  k_uptime_get for timestamping).
- Documented the native_sim virtual-clock gotcha discovered in Task 15 in
  detail, since it's a genuinely reusable lesson for any future Zephyr work
  on this simulator.
- Restated the Task 15 preemption evidence in writeup form with an
  interview-ready summary paragraph.

## Stage 4 — COMPLETE (4/4 tasks)

## Stage 5 — Benchmarking

### Task 17: Design a repeatable test protocol
- Wrote stage5_benchmarking/TEST_PROTOCOL.md defining the full methodology
  upfront, before running anything - fixed message set (real J1939 EEC1/CCVS1
  signals from Stage 3, not new test data), 2 independent variables (bus load:
  1/5/15 publishers; message rate: 10Hz/100Hz) giving 6 configurations, 20
  trials per configuration (120 total runs), 3 metrics per trial (latency,
  drop rate, throughput).
- Documented methodology choice explicitly: 20 trials is fewer than the
  thesis's 50-trial standard, calibrated instead for this software-only/8GB
  RAM laptop context - flagged as a deliberate scope decision, not silently
  presented as equivalent rigor.

### Task 18: Instrument and log latency, drop rate, throughput
- Built stage5_benchmarking/bench_can.py implementing TEST_PROTOCOL.md: threaded
  publisher(s)/receiver measuring real send-to-receive latency via perf_counter()
  timestamps packed into dedicated benchmark CAN frames (id=0x7DF).
- Documented deliberate tradeoff: benchmark frames carry a raw timestamp payload,
  not a real J1939-encoded signal, since 8 bytes can't hold both precise timing
  data and a realistic signal value - Stage 2/3 already validated real signal
  encoding separately, so this stage prioritizes timing precision instead.
- Validated logic with a reduced smoke test (1 config, 2 trials) before
  committing to the full run - confirmed 0% drop, sane sub-ms latency, correct
  throughput math, no hangs/errors.
- Ran full protocol: 6 configurations x 20 trials = 120 total trials, saved to
  bench_results_raw.json. Summary (avg across 20 trials per config):
    1 pub,  10Hz: 0.00% drop, 10.4 msg/s,   0.28ms avg latency
    1 pub, 100Hz: 0.00% drop, 100.4 msg/s,  0.24ms avg latency
    5 pub,  10Hz: 0.00% drop, 51.6 msg/s,   0.29ms avg latency
    5 pub, 100Hz: 0.00% drop, 501.8 msg/s,  0.24ms avg latency
    15 pub, 10Hz: 0.03% drop, 156.6 msg/s,  0.50ms avg latency
    15 pub,100Hz: 0.89% drop, 1499.8 msg/s, 5.17ms avg latency
- Result shows genuine, meaningful degradation under heavy load (15 publishers
  @ 100Hz) - both drop rate and latency increase noticeably, confirming the
  bus genuinely saturates under stress rather than scaling linearly forever.

### Task 19: Run full benchmark suite, produce plots/tables
- Built stage5_benchmarking/analyze_results.py: parses bench_results_raw.json,
  computes per-config averages, prints a summary table, and generates 3 plots
  (drop rate vs load, latency vs load, throughput vs load) plus a markdown
  table (BENCHMARK_RESULTS.md) for the repo.
- Gotcha hit and fixed: matplotlib's default backend tries to open an
  interactive display window, which hangs indefinitely under WSL2 (no display
  server). Fixed with `matplotlib.use('Agg')` (non-interactive, file-only
  backend) set before importing pyplot - a common headless-environment
  requirement worth remembering for any future matplotlib work in WSL2/CI.
- Key finding beyond the averages already noted in Task 18: MAX latency shows
  a striking tail-latency effect under heavy load - avg latency at 15
  publishers/10Hz is a modest 0.50ms, but MAX latency spikes to 38.5ms; at
  15 publishers/100Hz, avg is 5.17ms but MAX reaches 284.3ms. This means most
  messages stay fast even under heavy load, but a meaningful minority get
  significantly delayed - a real-time-systems-relevant nuance that averages
  alone would have hidden completely.
- Outputs: BENCHMARK_RESULTS.md, plot_drop_rate.png, plot_latency.png,
  plot_throughput.png - all saved in stage5_benchmarking/.

### Task 20: Compare CAN vs UDP vs TCP for the same simulated telemetry task
- Built bench_tcp_udp.py using the EXACT same methodology as bench_can.py
  (same 6 load configs, same 20-trial count, same perf_counter()-based
  send-to-receive latency measurement) so the comparison is methodologically
  fair, not just eyeballing differently-measured numbers from Stage 1.
- Hit and fixed a real bug: an in-place Python string-replace to update the
  __main__ block silently succeeded at the string level but left the block
  in the wrong location in the file (before, not after, the new TCP function
  definitions) - Python executed the stale block since it's top-to-bottom,
  causing the script to silently rerun UDP instead of TCP. Fixed by removing
  the misplaced block and appending a correct one at the true end of file.
  Lesson: str.replace() based code edits need the result verified, not
  assumed correct just because the script ran without erroring.
- Ran full comparison: CAN Task 18/19 results vs new UDP suite (120 trials)
  vs new TCP suite (120 trials). Saved to COMPARISON_RESULTS.md plus 2 plots
  (plot_transport_comparison_latency.png, plot_transport_comparison_throughput.png).
- KEY FINDING (with important caveat): on this virtual/software-only setup,
  UDP and TCP consistently outperformed CAN in both latency and drop rate,
  especially under heavy load - at 15 publishers/100Hz, CAN showed 0.89% drop
  and 284.3ms max latency, while UDP/TCP stayed near 0% drop with max latency
  under 50ms.
- IMPORTANT CAVEAT (documented explicitly, not glossed over): this result
  reflects vcan0's software queue implementation in the Linux kernel, NOT
  real CAN bus electrical arbitration. Real CAN hardware is chosen for
  safety-critical systems specifically because of hardware-level deterministic,
  bounded-worst-case-latency arbitration enforced by actual bit-timing on a
  physical wire - a virtual interface has none of that. This benchmark
  measures "Linux's CAN software stack overhead vs Linux's socket stack
  overhead on loopback," not "real CAN bus vs real network," and the paper
  draft (Stage 6) must state this limitation clearly rather than imply CAN
  is simply worse than UDP/TCP in general.

## Stage 5 — COMPLETE (4/4 tasks)

## DevOps-Rigor Retrofit — Coverage Snapshot (Bundle 5, Task 4)

Ran pytest-cov across all 28 non-test Python files (5 stage directories).
Blended total: 5% (1121 statements, 1061 uncovered) - this number alone
is misleading and shouldn't be quoted without the breakdown below, since
the vast majority of "uncovered" code is live I/O (sockets, vcan0,
serial) that pytest was never the right tool for.

**Unit-tested (pytest, 35 tests):**
- `stage3_j1939/j1939_ids.py` - 74% (PGN/SPN bit-packing, priority/source
  address encode-decode; untested lines are argument-validation edges
  not exercised by the current parametrized cases)
- `stage3_j1939/j1939_signals.py` - 77% (Engine Speed/Vehicle Speed
  signal encode-decode, clamping)
- `stage3_j1939/j1939_bam.py` - 66% (fragmentation/reassembly logic;
  untested lines are the live-transmission helper functions, not the
  pure fragment/reassemble math that the tests actually target)

**Verified by other means, not unit-tested (25 files, 0% by design):**
- `stage1_networking/*` - TCP/UDP/serial clients, servers, and
  benchmarking scripts; these are live network I/O, verified via the
  Stage 1 benchmark table (documented latency/throughput/loss numbers
  in BENCHMARKS.md) rather than pytest, which can't meaningfully unit
  test a live socket without extensive mocking that would test the mock,
  not the behavior
- `stage2_can/*` - CAN publisher/subscriber/DBC tooling against a real
  vcan0 interface; verified via live cansend/candump traffic and the
  documented bus-contention/arbitration analysis
- `stage3_j1939/j1939_bam_sender.py`, `_receiver.py`,
  `_multi_receiver.py`, `_stress_sender.py`, `j1939_publisher.py`,
  `j1939_subscriber.py`, `j1939_diagnostic_tool.py`,
  `j1939_ecu_responder.py` - these are the live-transmission wrappers
  around the pure BAM/PGN logic in j1939_bam.py/j1939_ids.py (which IS
  unit-tested); verified via the multi-ECU stress test and diagnostic
  request/response cycle documented in DEVLOG
- `stage5_benchmarking/*` - the 360-trial benchmark suite itself;
  verified by its own documented protocol (TEST_PROTOCOL.md, 6 configs x
  20 trials) and cross-checked results (COMPARISON_RESULTS.md), not unit
  tests
- `assets/generate_architecture_diagram.py` - one-off diagram-generation
  script, not part of the tested system

**Bottom line:** the pure protocol math (J1939 bit-packing, signal
encode/decode, BAM fragment/reassembly) is unit-tested at 66-77%
line coverage. The live I/O layer wrapping that math - sockets, vcan0,
serial - was verified end-to-end through the repo's own 360-trial
benchmark methodology instead, which is the more meaningful test for
code whose entire job is talking to a real (or virtual) bus correctly
under real timing and contention, not something a mocked-socket unit
test would actually prove.
