import can
from j1939_ids import decode_j1939_id, PGN_ENGINE_SPEED, PGN_VEHICLE_SPEED
from j1939_signals import decode_engine_speed, decode_vehicle_speed

CHANNEL = "vcan0"
BUSTYPE = "socketcan"

def main():
    # J1939 uses extended (29-bit) IDs, so our filter mask must cover 29 bits
    bus = can.interface.Bus(channel=CHANNEL, interface=BUSTYPE)
    print(f"[j1939 subscriber] listening on {CHANNEL} for J1939 traffic")

    try:
        while True:
            msg = bus.recv()
            if not msg.is_extended_id:
                continue  # skip any non-J1939 (standard ID) traffic

            fields = decode_j1939_id(msg.arbitration_id)
            pgn = fields["pgn"]

            if pgn == PGN_ENGINE_SPEED:
                rpm = decode_engine_speed(msg.data)
                print(f"[j1939 subscriber] EngineSpeed (PGN {pgn}, src=0x{fields['source_address']:02X}) = {rpm} rpm")
            elif pgn == PGN_VEHICLE_SPEED:
                kmh = decode_vehicle_speed(msg.data)
                print(f"[j1939 subscriber] VehicleSpeed (PGN {pgn}, src=0x{fields['source_address']:02X}) = {kmh} km/h")
            else:
                print(f"[j1939 subscriber] Unknown PGN {pgn}, ignoring")
    except KeyboardInterrupt:
        print("\n[j1939 subscriber] stopped")
    finally:
        bus.shutdown()

if __name__ == "__main__":
    main()
