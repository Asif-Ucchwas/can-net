import socket
import json

HOST = "127.0.0.1"
PORT = 65433

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind((HOST, PORT))
        print(f"[udp receiver] listening on {HOST}:{PORT}")
        while True:
            data, addr = s.recvfrom(2048)
            msg = json.loads(data.decode("utf-8"))
            print(f"[udp receiver] received: {msg}")

if __name__ == "__main__":
    main()
