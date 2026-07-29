import can
import cantools

CHANNEL = "vcan0"
BUSTYPE = "socketcan"
DBC_FILE = "vehicle.dbc"

def main():
    db = cantools.database.load_file(DBC_FILE)

    bus = can.interface.Bus(channel=CHANNEL, interface=BUSTYPE)
    print(f"[dbc decoder] listening on {CHANNEL}, decoding using {DBC_FILE}")

    try:
        while True:
            msg = bus.recv()
            try:
                decoded = db.decode_message(msg.arbitration_id, msg.data)
                print(f"[dbc decoder] id=0x{msg.arbitration_id:X} -> {decoded}")
            except KeyError:
                # This CAN ID isn't defined in our DBC - skip it silently
                pass
    except KeyboardInterrupt:
        print("\n[dbc decoder] stopped")
    finally:
        bus.shutdown()

if __name__ == "__main__":
    main()
