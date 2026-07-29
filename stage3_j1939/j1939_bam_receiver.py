import can
from j1939_ids import decode_j1939_id
from j1939_bam import reassemble_message, PGN_TP_CM, PGN_TP_DT

CHANNEL = "vcan0"
BUSTYPE = "socketcan"

def main():
    bus = can.interface.Bus(channel=CHANNEL, interface=BUSTYPE)
    print(f"[bam receiver] listening on {CHANNEL} for J1939 BAM transfers")

    # State for an in-progress transfer (None until a TP.CM arrives)
    expected_total_size = None
    expected_num_packets = None
    collected_frames = []

    try:
        while True:
            msg = bus.recv()
            if not msg.is_extended_id:
                continue

            fields = decode_j1939_id(msg.arbitration_id)
            pgn = fields["pgn"]

            if pgn == PGN_TP_CM:
                # New transfer starting - reset state and read the announcement
                control_byte = msg.data[0]
                if control_byte != 0x20:
                    continue  # not a BAM (could be RTS/CTS) - skip, out of scope here
                expected_total_size = msg.data[1] | (msg.data[2] << 8)
                expected_num_packets = msg.data[3]
                collected_frames = []
                print(f"[bam receiver] TP.CM received: expecting {expected_total_size} bytes "
                      f"across {expected_num_packets} packets")

            elif pgn == PGN_TP_DT and expected_total_size is not None:
                collected_frames.append(bytes(msg.data))
                print(f"[bam receiver] TP.DT seq={msg.data[0]} received "
                      f"({len(collected_frames)}/{expected_num_packets})")

                if len(collected_frames) == expected_num_packets:
                    message = reassemble_message(collected_frames, expected_total_size)
                    print(f"[bam receiver] REASSEMBLED ({expected_total_size} bytes): {message}")
                    # Reset state, ready for next transfer
                    expected_total_size = None
                    expected_num_packets = None
                    collected_frames = []
    except KeyboardInterrupt:
        print("\n[bam receiver] stopped")
    finally:
        bus.shutdown()

if __name__ == "__main__":
    main()
