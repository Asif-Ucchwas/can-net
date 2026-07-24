import serial
import time
import json

PORT = "/dev/pts/3"
BAUD = 9600

def main():
    ser = serial.Serial(PORT, BAUD, timeout=1)
    print(f"[serial sender] connected on {PORT}")
    for i in range(10):
        msg = {"seq": i, "sensor": "fake_gps", "lat": 30.08 + i * 0.001, "lon": -94.10 - i * 0.001}
        line = json.dumps(msg) + "\n"
        ser.write(line.encode("utf-8"))
        print(f"[serial sender] sent: {msg}")
        time.sleep(0.3)

if __name__ == "__main__":
    main()
