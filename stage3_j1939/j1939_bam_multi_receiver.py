import can
from j1939_ids import decode_j1939_id
from j1939_bam import reassemble_message, PGN_TP_CM, PGN_TP_DT

CHANNEL = "vcan0"
BUSTYPE = "socketcan"

def main():
    bus = can.interface.Bus(channel=CHANNEL, interface=BUSTYPE)
    print(f"[multi receiver] listening on {CHANNEL}, tracking transfers per source ECU")

    # Key change from Task 10: state is now keyed by source_address, not global.
    # This lets multiple ECUs have in-progress BAM transfers simultaneously
    # without corrupting each other's reassembly.
    transfers = {}  # { source_address: {"total_size": int, "num_packets": int, "frames": []} }

    try:
        while True:
            msg = bus.recv()
            if not msg.is_extended_id:
                continue

            fields = decode_j1939_id(msg.arbitration_id)
            pgn = fields["pgn"]
            src = fields["source_address"]

            if pgn == PGN_TP_CM:
                if msg.data[0] != 0x20:
                    continue  # not BAM, skip (RTS/CTS out of scope)
                total_size = msg.data[1] | (msg.data[2] << 8)
                num_packets = msg.data[3]
                transfers[src] = {"total_size": total_size, "num_packets": num_packets, "frames": []}
                print(f"[multi receiver] TP.CM from src=0x{src:02X}: expecting {total_size} bytes / {num_packets} packets")

            elif pgn == PGN_TP_DT and src in transfers:
                t = transfers[src]
                t["frames"].append(bytes(msg.data))
                print(f"[multi receiver] TP.DT from src=0x{src:02X} seq={msg.data[0]} "
                      f"({len(t['frames'])}/{t['num_packets']})")

                if len(t["frames"]) == t["num_packets"]:
                    message = reassemble_message(t["frames"], t["total_size"])
                    print(f"[multi receiver] REASSEMBLED from src=0x{src:02X}: {message}")
                    del transfers[src]  # done, free this ECU's tracking slot

    except KeyboardInterrupt:
        print("\n[multi receiver] stopped")
    finally:
        bus.shutdown()

if __name__ == "__main__":
    main()
