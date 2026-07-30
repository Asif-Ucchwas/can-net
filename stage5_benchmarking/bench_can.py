"""
Stage 5 CAN bus benchmark - implements TEST_PROTOCOL.md.

Note: benchmark frames use a dedicated CAN ID (0x7DF) whose 8-byte payload
is a raw perf_counter() timestamp (packed as a double), NOT a real J1939
signal encoding. This is a deliberate tradeoff: 8 bytes isn't enough room
for both a realistic signal value and precise latency data, so for pure
latency/throughput measurement we prioritize timing precision over semantic
realism (Stage 2/3 already validated real signal encoding separately).
"""

import can
import struct
import threading
import time
import statistics
import json

CHANNEL = "vcan0"
BUSTYPE = "socketcan"
BENCH_CAN_ID = 0x7DF

CONFIGS = [
    {"publishers": 1,  "rate_hz": 10},
    {"publishers": 1,  "rate_hz": 100},
    {"publishers": 5,  "rate_hz": 10},
    {"publishers": 5,  "rate_hz": 100},
    {"publishers": 15, "rate_hz": 10},
    {"publishers": 15, "rate_hz": 100},
]
TRIALS_PER_CONFIG = 20
TRIAL_DURATION = 2.0  # seconds


def publisher_thread(stop_event, rate_hz, sent_counter, lock):
    bus = can.interface.Bus(channel=CHANNEL, interface=BUSTYPE)
    period = 1.0 / rate_hz
    count = 0
    next_send = time.perf_counter()
    while not stop_event.is_set():
        now = time.perf_counter()
        if now >= next_send:
            payload = struct.pack("d", now)
            msg = can.Message(arbitration_id=BENCH_CAN_ID, data=payload, is_extended_id=False)
            try:
                bus.send(msg)
                count += 1
            except Exception:
                pass  # bus full under heavy load - dropped send, counts against throughput naturally
            next_send += period
        else:
            time.sleep(0.0005)
    bus.shutdown()
    with lock:
        sent_counter[0] += count


def receiver_thread(stop_event, latencies, recv_count, lock):
    bus = can.interface.Bus(
        channel=CHANNEL, interface=BUSTYPE,
        can_filters=[{"can_id": BENCH_CAN_ID, "can_mask": 0x7FF}],
    )
    while not stop_event.is_set():
        msg = bus.recv(timeout=0.1)
        if msg is None:
            continue
        recv_time = time.perf_counter()
        try:
            (send_time,) = struct.unpack("d", bytes(msg.data))
        except struct.error:
            continue
        latency = recv_time - send_time
        with lock:
            latencies.append(latency)
            recv_count[0] += 1
    bus.shutdown()


def run_trial(num_publishers, rate_hz):
    stop_event = threading.Event()
    lock = threading.Lock()
    latencies = []
    recv_count = [0]
    sent_counter = [0]

    recv_t = threading.Thread(target=receiver_thread, args=(stop_event, latencies, recv_count, lock))
    recv_t.start()
    time.sleep(0.05)  # let receiver bind before publishers start

    pub_threads = []
    for _ in range(num_publishers):
        t = threading.Thread(target=publisher_thread, args=(stop_event, rate_hz, sent_counter, lock))
        pub_threads.append(t)
        t.start()

    time.sleep(TRIAL_DURATION)
    stop_event.set()
    for t in pub_threads:
        t.join()
    time.sleep(0.1)  # drain remaining in-flight frames
    recv_t.join()

    sent = sent_counter[0]
    received = recv_count[0]
    drop_rate = (sent - received) / sent if sent > 0 else 0.0
    throughput = received / TRIAL_DURATION

    return {
        "sent": sent,
        "received": received,
        "drop_rate": drop_rate,
        "throughput": throughput,
        "latencies": latencies,
    }


def main():
    all_results = {}
    for cfg in CONFIGS:
        key = f"{cfg['publishers']}pub_{cfg['rate_hz']}hz"
        print(f"\n=== Config: {cfg['publishers']} publishers @ {cfg['rate_hz']}Hz ===")
        trial_results = []
        for trial_num in range(1, TRIALS_PER_CONFIG + 1):
            result = run_trial(cfg["publishers"], cfg["rate_hz"])
            trial_results.append(result)
            print(f"  trial {trial_num:2d}/{TRIALS_PER_CONFIG}: sent={result['sent']:4d} "
                  f"recv={result['received']:4d} drop={result['drop_rate']*100:5.1f}% "
                  f"throughput={result['throughput']:7.1f} msg/s")
        all_results[key] = trial_results

    with open("bench_results_raw.json", "w") as f:
        json.dump(all_results, f)
    print("\nAll trials complete. Raw results saved to bench_results_raw.json")


if __name__ == "__main__":
    main()
