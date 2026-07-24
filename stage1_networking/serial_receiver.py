import serial

PORT = "/dev/pts/4"
BAUD = 9600

def main():
    ser = serial.Serial(PORT, BAUD, timeout=1)
    print(f"[serial receiver] listening on {PORT}")
    while True:
        line = ser.readline()
        if line:
            print(f"[serial receiver] received: {line.decode('utf-8').strip()}")

if __name__ == "__main__":
    main()
