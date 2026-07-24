import socket
import json
import time

HOST = "127.0.0.1"
PORT = 65433

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        for i in range(20):
            msg = {"seq": i, "sensor": "fake_lidar", "value": i * 1.5}
            data = json.dumps(msg).encode("utf-8")
            s.sendto(data, (HOST, PORT))
            print(f"[udp sender] sent: {msg}")
            time.sleep(0.05)

if __name__ == "__main__":
    main()
