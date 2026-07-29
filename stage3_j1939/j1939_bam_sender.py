import can
import time
from j1939_ids import build_j1939_id
from j1939_bam import build_bam_cm_frame, fragment_message, PGN_TP_CM, PGN_TP_DT

CHANNEL = "vcan0"
BUSTYPE = "socketcan"
SOURCE_ADDRESS = 0x00
TARGET_PGN = 65226  # DM1 - Active Diagnostic Trouble Codes (a real J1939 PGN)

def main():
    bus = can.interface.Bus(channel=CHANNEL, interface=BUSTYPE)

    message = b"ENGINE_FAULT_CODE_P0301_CYLINDER_1_MISFIRE_DETECTED"
    print(f"[bam sender] sending multi-packet message ({len(message)} bytes): {message}")

    cm_id = build_j1939_id(priority=6, pgn=PGN_TP_CM, source_address=SOURCE_ADDRESS)
    dt_id = build_j1939_id(priority=6, pgn=PGN_TP_DT, source_address=SOURCE_ADDRESS)

    # Step 1: send the TP.CM announcement frame
    cm_payload = build_bam_cm_frame(len(message), TARGET_PGN)
    bus.send(can.Message(arbitration_id=cm_id, data=cm_payload, is_extended_id=True))
    print(f"[bam sender] sent TP.CM announcement (total_size={len(message)})")

    time.sleep(0.05)  # small gap, mimics real BAM timing between CM and first DT frame

    # Step 2: send each TP.DT data frame in sequence
    dt_frames = fragment_message(message)
    for frame in dt_frames:
        bus.send(can.Message(arbitration_id=dt_id, data=frame, is_extended_id=True))
        print(f"[bam sender] sent TP.DT seq={frame[0]}")
        time.sleep(0.05)  # BAM frames are typically spaced ~50-200ms apart

    bus.shutdown()
    print("[bam sender] done")

if __name__ == "__main__":
    main()
