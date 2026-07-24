import socket
import struct
import json
import time

HOST = "127.0.0.1"
PORT = 65432

def send_message(sock, obj):
    body = json.dumps(obj).encode("utf-8")
    header = struct.pack("!I", len(body))
    sock.sendall(header + body)

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        print("[client] connected")
        for i in range(5):
            msg = {"seq": i, "sensor": "fake_imu", "value": 3.14 * i}
            send_message(s, msg)
            print(f"[client] sent: {msg}")
            time.sleep(0.3)

if __name__ == "__main__":
    main()
