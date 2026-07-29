import can
import time
from j1939_ids import build_j1939_id, decode_j1939_id, PGN_ENGINE_SPEED, PGN_VEHICLE_SPEED
from j1939_signals import decode_engine_speed, decode_vehicle_speed

CHANNEL = "vcan0"
BUSTYPE = "socketcan"
SOURCE_ADDRESS = 0xF9  # diagnostic tools conventionally use address 0xF9 in J1939
PGN_REQUEST = 59904

def build_request_frame(target_pgn: int) -> bytes:
    """Request PGN payload: 3 bytes, little-endian, holding the PGN being requested."""
    return bytes([
        target_pgn & 0xFF,
        (target_pgn >> 8) & 0xFF,
        (target_pgn >> 16) & 0xFF,
        0xFF, 0xFF, 0xFF, 0xFF, 0xFF,  # remaining bytes unused, padded
    ])

def request_pgn(bus, target_pgn: int, timeout=1.0):
    """Send a request for target_pgn, then wait up to `timeout` seconds for a response."""
    request_id = build_j1939_id(priority=6, pgn=PGN_REQUEST, source_address=SOURCE_ADDRESS)
    bus.send(can.Message(arbitration_id=request_id, data=build_request_frame(target_pgn), is_extended_id=True))
    print(f"[diag tool] sent request for PGN {target_pgn}")

    deadline = time.time() + timeout
    while time.time() < deadline:
        msg = bus.recv(timeout=deadline - time.time())
        if msg is None or not msg.is_extended_id:
            continue
        fields = decode_j1939_id(msg.arbitration_id)
        if fields["pgn"] == target_pgn:
            return msg  # got our response
    return None  # timed out, no response

def main():
    bus = can.interface.Bus(channel=CHANNEL, interface=BUSTYPE)
    print(f"[diag tool] ready on {CHANNEL}")

    try:
        # Request engine speed
        response = request_pgn(bus, PGN_ENGINE_SPEED)
        if response:
            rpm = decode_engine_speed(response.data)
            print(f"[diag tool] EngineSpeed response: {rpm} rpm")
        else:
            print("[diag tool] no response for EngineSpeed (timeout)")

        time.sleep(0.5)

        # Request vehicle speed
        response = request_pgn(bus, PGN_VEHICLE_SPEED)
        if response:
            kmh = decode_vehicle_speed(response.data)
            print(f"[diag tool] VehicleSpeed response: {kmh} km/h")
        else:
            print("[diag tool] no response for VehicleSpeed (timeout)")

        time.sleep(0.5)

        # Request a PGN the ECU doesn't support, to confirm timeout handling works
        response = request_pgn(bus, target_pgn=65226, timeout=1.0)
        if response:
            print(f"[diag tool] unexpected response for unsupported PGN: {response}")
        else:
            print("[diag tool] no response for unsupported PGN 65226 (expected - confirms timeout works)")

    finally:
        bus.shutdown()
        print("[diag tool] done")

if __name__ == "__main__":
    main()
