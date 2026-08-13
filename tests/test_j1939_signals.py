import struct
import pytest
from j1939_signals import (
    encode_engine_speed, decode_engine_speed,
    encode_vehicle_speed, decode_vehicle_speed,
)


def test_engine_speed_roundtrip():
    payload = encode_engine_speed(2500.0)
    assert decode_engine_speed(payload) == pytest.approx(2500.0)


def test_vehicle_speed_roundtrip():
    payload = encode_vehicle_speed(88.5)
    assert decode_vehicle_speed(payload) == pytest.approx(88.5, abs=1/256)


def test_engine_speed_known_value():
    # 100 rpm / 0.125 = 800 raw -> little-endian bytes at offset 3-4
    payload = encode_engine_speed(100.0)
    raw = struct.unpack("<H", payload[3:5])[0]
    assert raw == 800


def test_engine_speed_byte_placement():
    payload = encode_engine_speed(2500.0)
    assert len(payload) == 8
    # bytes 0-2 and 5-7 must stay zero - only bytes 3-4 carry this signal
    assert payload[0:3] == b"\x00\x00\x00"
    assert payload[5:8] == b"\x00\x00\x00"


def test_vehicle_speed_known_value():
    # 10 km/h / (1/256) = 2560 raw -> little-endian bytes at offset 1-2
    payload = encode_vehicle_speed(10.0)
    raw = struct.unpack("<H", payload[1:3])[0]
    assert raw == 2560


def test_vehicle_speed_byte_placement():
    payload = encode_vehicle_speed(88.5)
    assert len(payload) == 8
    assert payload[0:1] == b"\x00"
    assert payload[3:8] == b"\x00\x00\x00\x00\x00"


def test_engine_speed_clamps_negative():
    payload = encode_engine_speed(-500.0)
    assert decode_engine_speed(payload) == 0.0


def test_engine_speed_clamps_above_max():
    # 0xFFFF * 0.125 = 8191.875 is the max representable rpm
    payload = encode_engine_speed(999999.0)
    raw = struct.unpack("<H", payload[3:5])[0]
    assert raw == 0xFFFF


def test_vehicle_speed_clamps_negative():
    payload = encode_vehicle_speed(-50.0)
    assert decode_vehicle_speed(payload) == 0.0


def test_vehicle_speed_clamps_above_max():
    payload = encode_vehicle_speed(999999.0)
    raw = struct.unpack("<H", payload[1:3])[0]
    assert raw == 0xFFFF
