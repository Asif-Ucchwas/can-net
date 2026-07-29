import can
import threading
import time

CHANNEL = "vcan0"
BUSTYPE = "socketcan"

# Three nodes with different priority IDs (lower ID = higher real-world priority)
NODES = [
    {"name": "high_priority_brake",  "id": 0x010, "count": 50},
    {"name": "medium_priority_engine", "id": 0x100, "count": 50},
    {"name": "low_priority_infotainment", "id": 0x500, "count": 50},
]

def node_sender(node, bus, results, lock):
    sent = 0
    for i in range(node["count"]):
        data = [i % 256] + [0]*7
        msg = can.Message(arbitration_id=node["id"], data=data, is_extended_id=False)
        bus.send(msg)
        sent += 1
    with lock:
        results[node["name"]] = sent

def main():
    bus = can.interface.Bus(channel=CHANNEL, interface=BUSTYPE)
    results = {}
    lock = threading.Lock()

    print("[contention] launching 3 nodes simultaneously, flooding vcan0...")
    threads = []
    start = time.perf_counter()
    for node in NODES:
        t = threading.Thread(target=node_sender, args=(node, bus, results, lock))
        threads.append(t)

    # Start all threads as close to simultaneously as possible
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    elapsed = time.perf_counter() - start

    bus.shutdown()

    print(f"\n[contention] all nodes finished in {elapsed*1000:.2f} ms")
    for node in NODES:
        print(f"  {node['name']:28s} (id=0x{node['id']:03X}) sent {results[node['name']]} frames")

    print("\n[contention] Arbitration note:")
    print("  On real CAN hardware, simultaneous transmission is resolved by the ID")
    print("  itself - lower numeric ID wins arbitration non-destructively, higher")
    print("  IDs back off and retry with zero data loss/corruption. On this virtual")
    print("  vcan0 bus, the kernel simply queues frames from all three threads with")
    print("  no real electrical contention, so true arbitration timing can't be")
    print("  observed here - that requires real hardware (Stage 7).")

if __name__ == "__main__":
    main()
