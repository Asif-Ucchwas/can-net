"""
Stage 5 Task 20: TCP/UDP benchmarked with the EXACT same methodology as
bench_can.py (real send-to-receive latency via perf_counter() timestamps,
same load levels, same trial count) so the CAN vs TCP vs UDP comparison is
methodologically fair - not just eyeballing two differently-measured numbers.
"""

import matplotlib
matplotlib.use('Agg')

import socket
import struct
import threading
import time
import statistics
import json

HOST = "127.0.0.1"
UDP_PORT = 65451

CONFIGS = [
    {"publishers": 1,  "rate_hz": 10},
    {"publishers": 1,  "rate_hz": 100},
    {"publishers": 5,  "rate_hz": 10},
    {"publishers": 5,  "rate_hz": 100},
    {"publishers": 15, "rate_hz": 10},
    {"publishers": 15, "rate_hz": 100},
]
TRIALS_PER_CONFIG = 20
TRIAL_DURATION = 2.0


def udp_publisher(stop_event, rate_hz, sent_counter, lock):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    period = 1.0 / rate_hz
    count = 0
    next_send = time.perf_counter()
    while not stop_event.is_set():
        now = time.perf_counter()
        if now >= next_send:
            payload = struct.pack("d", now)
            try:
                s.sendto(payload, (HOST, UDP_PORT))
                count += 1
            except Exception:
                pass
            next_send += period
        else:
            time.sleep(0.0005)
    s.close()
    with lock:
        sent_counter[0] += count


def udp_receiver(stop_event, latencies, recv_count, lock):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind((HOST, UDP_PORT))
    s.settimeout(0.1)
    while not stop_event.is_set():
        try:
            data, _ = s.recvfrom(64)
        except socket.timeout:
            continue
        recv_time = time.perf_counter()
        try:
            (send_time,) = struct.unpack("d", data)
        except struct.error:
            continue
        with lock:
            latencies.append(recv_time - send_time)
            recv_count[0] += 1
    s.close()


def run_udp_trial(num_publishers, rate_hz):
    stop_event = threading.Event()
    lock = threading.Lock()
    latencies, recv_count, sent_counter = [], [0], [0]

    recv_t = threading.Thread(target=udp_receiver, args=(stop_event, latencies, recv_count, lock))
    recv_t.start()
    time.sleep(0.05)

    pub_threads = [threading.Thread(target=udp_publisher, args=(stop_event, rate_hz, sent_counter, lock))
                   for _ in range(num_publishers)]
    for t in pub_threads:
        t.start()

    time.sleep(TRIAL_DURATION)
    stop_event.set()
    for t in pub_threads:
        t.join()
    time.sleep(0.1)
    recv_t.join()

    sent, received = sent_counter[0], recv_count[0]
    drop_rate = (sent - received) / sent if sent > 0 else 0.0
    throughput = received / TRIAL_DURATION
    return {"sent": sent, "received": received, "drop_rate": drop_rate,
            "throughput": throughput, "latencies": latencies}


def run_suite(transport_name, trial_fn):
    all_results = {}
    for cfg in CONFIGS:
        key = f"{cfg['publishers']}pub_{cfg['rate_hz']}hz"
        print(f"=== {transport_name} | {cfg['publishers']} publishers @ {cfg['rate_hz']}Hz ===")
        trial_results = [trial_fn(cfg["publishers"], cfg["rate_hz"]) for _ in range(TRIALS_PER_CONFIG)]
        all_results[key] = trial_results
        avg_drop = statistics.mean(t["drop_rate"] for t in trial_results) * 100
        avg_tp = statistics.mean(t["throughput"] for t in trial_results)
        print(f"  avg drop={avg_drop:.2f}%  avg throughput={avg_tp:.1f} msg/s")
    return all_results




TCP_PORT = 65452

def tcp_publisher(conn, stop_event, rate_hz, sent_counter, lock):
    period = 1.0 / rate_hz
    count = 0
    next_send = time.perf_counter()
    while not stop_event.is_set():
        now = time.perf_counter()
        if now >= next_send:
            payload = struct.pack("d", now)
            try:
                conn.sendall(payload)
                count += 1
            except Exception:
                break
            next_send += period
        else:
            time.sleep(0.0005)
    with lock:
        sent_counter[0] += count


def tcp_server_accept_loop(server_sock, stop_event, latencies, recv_count, lock, expected_clients):
    conns = []
    server_sock.settimeout(0.5)
    while len(conns) < expected_clients and not stop_event.is_set():
        try:
            conn, _ = server_sock.accept()
            conn.settimeout(0.1)
            conns.append(conn)
        except socket.timeout:
            continue

    def handle_conn(conn):
        while not stop_event.is_set():
            try:
                data = conn.recv(8)
            except socket.timeout:
                continue
            except Exception:
                break
            if not data or len(data) < 8:
                continue
            recv_time = time.perf_counter()
            try:
                (send_time,) = struct.unpack("d", data)
            except struct.error:
                continue
            with lock:
                latencies.append(recv_time - send_time)
                recv_count[0] += 1
        conn.close()

    handler_threads = [threading.Thread(target=handle_conn, args=(c,)) for c in conns]
    for t in handler_threads:
        t.start()
    for t in handler_threads:
        t.join()


def run_tcp_trial(num_publishers, rate_hz):
    stop_event = threading.Event()
    lock = threading.Lock()
    latencies, recv_count, sent_counter = [], [0], [0]

    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind((HOST, TCP_PORT))
    server_sock.listen(num_publishers)

    server_t = threading.Thread(target=tcp_server_accept_loop,
                                 args=(server_sock, stop_event, latencies, recv_count, lock, num_publishers))
    server_t.start()
    time.sleep(0.1)

    client_conns = []
    for _ in range(num_publishers):
        c = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        c.connect((HOST, TCP_PORT))
        client_conns.append(c)
    time.sleep(0.1)

    pub_threads = [threading.Thread(target=tcp_publisher, args=(conn, stop_event, rate_hz, sent_counter, lock))
                   for conn in client_conns]
    for t in pub_threads:
        t.start()

    time.sleep(TRIAL_DURATION)
    stop_event.set()
    for t in pub_threads:
        t.join()
    for c in client_conns:
        c.close()
    time.sleep(0.1)
    server_t.join()
    server_sock.close()

    sent, received = sent_counter[0], recv_count[0]
    drop_rate = (sent - received) / sent if sent > 0 else 0.0
    throughput = received / TRIAL_DURATION
    return {"sent": sent, "received": received, "drop_rate": drop_rate,
            "throughput": throughput, "latencies": latencies}


if __name__ == "__main__":
    tcp_results = run_suite("TCP", run_tcp_trial)
    with open("bench_tcp_results.json", "w") as f:
        json.dump(tcp_results, f)
    print("\nTCP suite complete. Saved to bench_tcp_results.json")
