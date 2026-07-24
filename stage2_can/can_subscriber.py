import can

CHANNEL = "vcan0"
BUSTYPE = "socketcan"

# Only listen for CAN ID 0x100 - ignore 0x200 entirely
FILTER_ID = 0x100

def main():
    can_filters = [{"can_id": FILTER_ID, "can_mask": 0x7FF}]
    bus = can.interface.Bus(channel=CHANNEL, interface=BUSTYPE, can_filters=can_filters)
    print(f"[subscriber] listening on {CHANNEL}, filtering for id=0x{FILTER_ID:X} only")

    try:
        while True:
            msg = bus.recv()
            print(f"[subscriber] received id=0x{msg.arbitration_id:X} data={list(msg.data)}")
    except KeyboardInterrupt:
        print("\n[subscriber] stopped")
    finally:
        bus.shutdown()

if __name__ == "__main__":
    main()
