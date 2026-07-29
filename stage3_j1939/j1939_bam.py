"""
Minimal J1939 BAM (Broadcast Announce Message) transport protocol.
Handles fragmenting a message >8 bytes into TP.CM + TP.DT frames, and
reassembling them back on the receive side.

PGN 60416 = TP.CM (Connection Management) - one announcement frame
PGN 60160 = TP.DT (Data Transfer) - the actual fragmented data, 7 bytes/frame
            (byte 0 of each TP.DT frame is a 1-indexed sequence number)
"""

import struct

PGN_TP_CM = 60416
PGN_TP_DT = 60160

BAM_CONTROL_BYTE = 0x20  # identifies this TP.CM frame as a BAM (not RTS/CTS)

def build_bam_cm_frame(total_size: int, target_pgn: int) -> bytes:
    """Build the single TP.CM announcement frame for a BAM transfer."""
    num_packets = (total_size + 6) // 7  # 7 data bytes per TP.DT frame, round up
    pgn_bytes = struct.pack("<I", target_pgn)[:3]  # PGN is 3 bytes in TP.CM
    payload = bytes([
        BAM_CONTROL_BYTE,
        total_size & 0xFF,
        (total_size >> 8) & 0xFF,
        num_packets,
        0xFF,  # reserved
    ]) + pgn_bytes
    return payload

def fragment_message(data: bytes) -> list:
    """Split arbitrary-length data into a list of 7-byte chunks, each
    prefixed with a 1-indexed sequence number, as TP.DT requires."""
    frames = []
    seq = 1
    for i in range(0, len(data), 7):
        chunk = data[i:i+7]
        chunk = chunk + b"\xFF" * (7 - len(chunk))  # pad last frame with 0xFF
        frames.append(bytes([seq]) + chunk)
        seq += 1
    return frames

def reassemble_message(dt_frames: list, total_size: int) -> bytes:
    """Reassemble TP.DT frames (already sorted by sequence number) back
    into the original message, trimmed to the announced total_size."""
    # Sort by sequence number (byte 0) in case frames arrived out of order
    sorted_frames = sorted(dt_frames, key=lambda f: f[0])
    data = b"".join(f[1:] for f in sorted_frames)
    return data[:total_size]

if __name__ == "__main__":
    # Self-test: fragment and reassemble a message longer than 8 bytes
    original = b"ENGINE_FAULT_CODE_P0301_CYLINDER_1_MISFIRE_DETECTED"
    print(f"Original message ({len(original)} bytes): {original}")

    cm_frame = build_bam_cm_frame(len(original), target_pgn=65226)  # DM1 diagnostic PGN
    print(f"TP.CM announcement frame: {cm_frame.hex()}")

    dt_frames = fragment_message(original)
    print(f"Fragmented into {len(dt_frames)} TP.DT frames:")
    for f in dt_frames:
        print(f"  seq={f[0]}: {f.hex()}")

    reassembled = reassemble_message(dt_frames, len(original))
    print(f"Reassembled: {reassembled}")
    assert reassembled == original
    print("Self-test passed: reassembled message matches original exactly.")
