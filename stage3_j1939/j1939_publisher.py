import can
import time
import random
from j1939_ids import build_j1939_id, PGN_ENGINE_SPEED, PGN_VEHICLE_SPEED
from j1939_signals import encode_engine_speed, encode_vehicle_speed

CHANNEL = "vcan0"
BUSTYPE = "socketcan"
SOURCE_ADDRESS = 0x00  # this fake ECU's address

def main():
    bus = can.interface.Bus(channel=CHANNEL, interface=BUSTYPE)
    print(f"[j1939 publisher] sending EEC1 (engine speed) + CCVS1 (vehicle speed) on {CHANNEL}")

    eec1_id = build_j1939_id(priority=3, pgn=PGN_ENGINE_SPEED, source_address=SOURCE_ADDRESS)
    ccvs1_id = build_j1939_id(priority=6, pgn=PGN_VEHICLE_SPEED, source_address=SOURCE_ADDRESS)

    try:
        while True:
            rpm = round(random.uniform(700, 3500), 3)
            kmh = round(random.uniform(0, 110), 3)

            eec1_msg = can.Message(
                arbitration_id=eec1_id,
                data=encode_engine_speed(rpm),
                is_extended_id=True,  # J1939 requires 29-bit extended IDs
            )
            ccvs1_msg = can.Message(
                arbitration_id=ccvs1_id,
                data=encode_vehicle_speed(kmh),
                is_extended_id=True,
            )

            bus.send(eec1_msg)
            bus.send(ccvs1_msg)
            print(f"[j1939 publisher] sent EngineSpeed={rpm} rpm, VehicleSpeed={kmh} km/h")
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n[j1939 publisher] stopped")
    finally:
        bus.shutdown()

if __name__ == "__main__":
    main()
