"""
J1939 signal (SPN) encoding for two real, standardized signals:
  - SPN 190: Engine Speed, inside PGN 61444 (EEC1)
    Byte offset 3-4 (0-indexed), resolution 0.125 rpm/bit, range 0-8031.875 rpm
  - SPN 84: Vehicle Speed, inside PGN 65265 (CCVS1)
    Byte offset 1-2 (0-indexed), resolution 1/256 km/h per bit, range 0-250.996 km/h
"""

import struct

def encode_engine_speed(rpm: float) -> bytes:
    """Pack Engine Speed (SPN 190) into an 8-byte EEC1 payload."""
    raw = int(rpm / 0.125)
    raw = max(0, min(raw, 0xFFFF))  # clamp to 16-bit range
    payload = bytearray(8)
    payload[3:5] = struct.pack("<H", raw)  # little-endian, bytes 3-4
    return bytes(payload)

def decode_engine_speed(data: bytes) -> float:
    raw = struct.unpack("<H", data[3:5])[0]
    return raw * 0.125

def encode_vehicle_speed(kmh: float) -> bytes:
    """Pack Vehicle Speed (SPN 84) into an 8-byte CCVS1 payload."""
    raw = int(kmh / (1.0 / 256.0))
    raw = max(0, min(raw, 0xFFFF))
    payload = bytearray(8)
    payload[1:3] = struct.pack("<H", raw)  # little-endian, bytes 1-2
    return bytes(payload)

def decode_vehicle_speed(data: bytes) -> float:
    raw = struct.unpack("<H", data[1:3])[0]
    return raw / 256.0

if __name__ == "__main__":
    # Self-test both signals
    eng_payload = encode_engine_speed(2500.0)
    eng_back = decode_engine_speed(eng_payload)
    print(f"Engine speed: sent 2500.0 rpm -> payload {eng_payload.hex()} -> decoded {eng_back} rpm")

    veh_payload = encode_vehicle_speed(88.5)
    veh_back = decode_vehicle_speed(veh_payload)
    print(f"Vehicle speed: sent 88.5 km/h -> payload {veh_payload.hex()} -> decoded {veh_back} km/h")
