"""
Minimal J1939 29-bit CAN ID encoder/decoder.

J1939 extended CAN ID layout (29 bits total):
  bits 28-26 : Priority       (3 bits, 0=highest ... 7=lowest)
  bits 25-8  : PGN            (18 bits - Parameter Group Number)
  bits 7-0   : Source Address (8 bits - which ECU sent it)

We're building this manually (not using a full j1939 library) so the bit
math is visible and understood, not hidden behind a black box.
"""

def build_j1939_id(priority: int, pgn: int, source_address: int) -> int:
    """Pack priority + PGN + source address into a 29-bit extended CAN ID."""
    if not (0 <= priority <= 7):
        raise ValueError("priority must be 0-7 (3 bits)")
    if not (0 <= pgn <= 0x3FFFF):
        raise ValueError("PGN must fit in 18 bits (0-262143)")
    if not (0 <= source_address <= 0xFF):
        raise ValueError("source_address must fit in 8 bits (0-255)")

    can_id = (priority << 26) | (pgn << 8) | source_address
    return can_id

def decode_j1939_id(can_id: int) -> dict:
    """Unpack a 29-bit extended CAN ID back into its J1939 fields."""
    priority = (can_id >> 26) & 0x7
    pgn = (can_id >> 8) & 0x3FFFF
    source_address = can_id & 0xFF
    return {"priority": priority, "pgn": pgn, "source_address": source_address}

# Well-known standard J1939 PGNs we'll use in this stage
PGN_ENGINE_SPEED = 61444    # "Electronic Engine Controller 1" (EEC1) - contains SPN 190 Engine Speed
PGN_VEHICLE_SPEED = 65265   # "Cruise Control/Vehicle Speed" (CCVS1) - contains SPN 84 Vehicle Speed

if __name__ == "__main__":
    # Quick self-test
    test_id = build_j1939_id(priority=3, pgn=PGN_ENGINE_SPEED, source_address=0x00)
    print(f"Built J1939 ID: 0x{test_id:08X}")
    decoded = decode_j1939_id(test_id)
    print(f"Decoded back: {decoded}")
    assert decoded["pgn"] == PGN_ENGINE_SPEED
    print("Self-test passed: round-trip encode/decode matches.")
