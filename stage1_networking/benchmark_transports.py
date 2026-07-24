import socket
import struct
import time
import threading
import statistics
import subprocess
import serial

N_MESSAGES = 100
PAYLOAD = b"X" * 64  # fixed 64-byte payload for fair comparison

def bench_tcp():
    HOST, PORT = "127.0.0.1", 65440
    latencies = []
    server_ready = threading.Event()

    def server():
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((HOST, PORT))
            s.listen(1)
            server_ready.set()
            conn, _ = s.accept()
            with conn:
                for _ in range(N_MESSAGES):
                    header = conn.recv(4)
                    (length,) = struct.unpack("!I", header)
                    body = b""
                    while len(body) < length:
                        body += conn.recv(length - len(body))

    t = threading.Thread(target=server, daemon=True)
    t.start()
    server_ready.wait()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        for _ in range(N_MESSAGES):
            start = time.perf_counter()
            header = struct.pack("!I", len(PAYLOAD))
            s.sendall(header + PAYLOAD)
            latencies.append(time.perf_counter() - start)
    t.join(timeout=1)
    return latencies

def bench_udp():
    HOST, PORT = "127.0.0.1", 65441
    latencies = []
    received = []

    def server():
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.bind((HOST, PORT))
            for _ in range(N_MESSAGES):
                data, _ = s.recvfrom(1024)
                received.append(data)

    t = threading.Thread(target=server, daemon=True)
    t.start()
    time.sleep(0.1)

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        for _ in range(N_MESSAGES):
            start = time.perf_counter()
            s.sendto(PAYLOAD, (HOST, PORT))
            latencies.append(time.perf_counter() - start)
    t.join(timeout=1)
    return latencies

def bench_serial():
    # Spin up a fresh socat pty pair just for this benchmark run
    proc = subprocess.Popen(
        ["socat", "-d", "-d", "pty,raw,echo=0", "pty,raw,echo=0"],
        stderr=subprocess.PIPE, text=True
    )
    time.sleep(0.3)  # give socat a moment to create the ptys

    ports = []
    for _ in range(2):
        line = proc.stderr.readline()
        ports.append(line.strip().split()[-1])

    tx_port, rx_port = ports[0], ports[1]
    latencies = []
    received = []

    def server():
        ser = serial.Serial(rx_port, 9600, timeout=2)
        for _ in range(N_MESSAGES):
            data = ser.read(len(PAYLOAD))
            received.append(data)

    t = threading.Thread(target=server, daemon=True)
    t.start()
    time.sleep(0.2)

    ser_tx = serial.Serial(tx_port, 9600, timeout=2)
    for _ in range(N_MESSAGES):
        start = time.perf_counter()
        ser_tx.write(PAYLOAD)
        latencies.append(time.perf_counter() - start)
    t.join(timeout=2)

    proc.terminate()
    return latencies

def print_stats(name, latencies):
    total_time = sum(latencies)
    avg_latency_ms = statistics.mean(latencies) * 1000
    throughput = N_MESSAGES / total_time if total_time > 0 else 0
    print(f"{name:10s} | avg latency: {avg_latency_ms:8.4f} ms | "
          f"total: {total_time*1000:8.2f} ms | throughput: {throughput:8.1f} msg/s")

def main():
    print(f"Benchmark: {N_MESSAGES} messages, {len(PAYLOAD)}-byte payload\n")
    print_stats("TCP", bench_tcp())
    print_stats("UDP", bench_udp())
    print_stats("Serial", bench_serial())

if __name__ == "__main__":
    main()
