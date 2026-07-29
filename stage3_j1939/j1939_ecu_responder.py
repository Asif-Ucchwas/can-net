import can
import struct
import random
from j1939_ids import build_j1939_id, decode_j1939_id, PGN_ENGINE_SPEED, PGN_VEHICLE_SPEED
from j1939_signals import encode_engine_speed, encode_vehicle_speed

CHANNEL = "vcan0"
BUSTYPE = "socketcan"
SOURCE_ADDRESS = 0x00
PGN_REQUEST = 59904  # Standard J1939 Request PGN

def parse_requested_pgn(data: bytes) -> int:
    """Request PGN payload is 3 bytes, little-endian, holding the requested PGN."""
    return data[0] | (data[1] << 8) | (data[2] << 16)

def main():
    bus = can.interface.Bus(channel=CHANNEL, interface=BUSTYPE)
    print(f"[ecu responder] listening on {CHANNEL} for PGN requests, ready to respond on demand")

    try:
        while True:
            msg = bus.recv()
            if not msg.is_extended_id:
                continue

            fields = decode_j1939_id(msg.arbitration_id)
            if fields["pgn"] != PGN_REQUEST:
                continue  # not a request, ignore

            requested_pgn = parse_requested_pgn(msg.data)
            print(f"[ecu responder] received request for PGN {requested_pgn}")

            if requested_pgn == PGN_ENGINE_SPEED:
                rpm = round(random.uniform(700, 3500), 3)
                response_id = build_j1939_id(priority=3, pgn=PGN_ENGINE_SPEED, source_address=SOURCE_ADDRESS)
                bus.send(can.Message(arbitration_id=response_id, data=encode_engine_speed(rpm), is_extended_id=True))
                print(f"[ecu responder] responded with EngineSpeed={rpm} rpm")

            elif requested_pgn == PGN_VEHICLE_SPEED:
                kmh = round(random.uniform(0, 110), 3)
                response_id = build_j1939_id(priority=6, pgn=PGN_VEHICLE_SPEED, source_address=SOURCE_ADDRESS)
                bus.send(can.Message(arbitration_id=response_id, data=encode_vehicle_speed(kmh), is_extended_id=True))
                print(f"[ecu responder] responded with VehicleSpeed={kmh} km/h")

            else:
                print(f"[ecu responder] PGN {requested_pgn} not supported by this ECU, ignoring")
    except KeyboardInterrupt:
        print("\n[ecu responder] stopped")
    finally:
        bus.shutdown()

if __name__ == "__main__":
    main()
