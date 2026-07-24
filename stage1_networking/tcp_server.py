import socket
import struct
import json

HOST = "127.0.0.1"
PORT = 65432

def recv_exact(conn, n):
    """Read exactly n bytes or raise if connection closes early."""
    buf = b""
    while len(buf) < n:
        chunk = conn.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("Socket closed before expected data arrived")
        buf += chunk
    return buf

def recv_message(conn):
    header = recv_exact(conn, 4)
    (length,) = struct.unpack("!I", header)
    body = recv_exact(conn, length)
    return json.loads(body.decode("utf-8"))

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen(1)
        print(f"[server] listening on {HOST}:{PORT}")
        conn, addr = s.accept()
        with conn:
            print(f"[server] connected by {addr}")
            while True:
                try:
                    msg = recv_message(conn)
                except ConnectionError:
                    print("[server] client disconnected")
                    break
                print(f"[server] received: {msg}")

if __name__ == "__main__":
    main()
