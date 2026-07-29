import can
import threading
import time
from j1939_ids import build_j1939_id
from j1939_bam import build_bam_cm_frame, fragment_message, PGN_TP_CM, PGN_TP_DT

CHANNEL = "vcan0"
BUSTYPE = "socketcan"

# Three simulated ECUs, each with a different source address and message
ECUS = [
    {"name": "Engine_ECU",  "src": 0x00, "message": b"ENGINE_TEMP_HIGH_WARNING_COOLANT_LOW"},
    {"name": "Trans_ECU",   "src": 0x03, "message": b"TRANSMISSION_GEAR_SLIP_DETECTED_CODE_P0730"},
    {"name": "Brake_ECU",   "src": 0x0B, "message": b"ABS_SENSOR_FAULT_REAR_LEFT_WHEEL_SPEED"},
]

def ecu_send(ecu, bus):
    cm_id = build_j1939_id(priority=6, pgn=PGN_TP_CM, source_address=ecu["src"])
    dt_id = build_j1939_id(priority=6, pgn=PGN_TP_DT, source_address=ecu["src"])

    cm_payload = build_bam_cm_frame(len(ecu["message"]), target_pgn=65226)
    bus.send(can.Message(arbitration_id=cm_id, data=cm_payload, is_extended_id=True))
    print(f"[{ecu['name']}] sent TP.CM (src=0x{ecu['src']:02X}, {len(ecu['message'])} bytes)")

    dt_frames = fragment_message(ecu["message"])
    for frame in dt_frames:
        # Small random-ish stagger by using a short fixed delay - deliberately
        # short enough that frames from different ECUs genuinely interleave
        time.sleep(0.02)
        bus.send(can.Message(arbitration_id=dt_id, data=frame, is_extended_id=True))
    print(f"[{ecu['name']}] finished sending all {len(dt_frames)} TP.DT frames")

def main():
    bus = can.interface.Bus(channel=CHANNEL, interface=BUSTYPE)
    print(f"[stress sender] launching {len(ECUS)} simulated ECUs concurrently on {CHANNEL}")

    threads = [threading.Thread(target=ecu_send, args=(ecu, bus)) for ecu in ECUS]
    for t in threads:
        t.start()
        time.sleep(0.01)  # tiny stagger so TP.CM frames don't literally collide in Python
    for t in threads:
        t.join()

    bus.shutdown()
    print("[stress sender] all ECUs done")

if __name__ == "__main__":
    main()
