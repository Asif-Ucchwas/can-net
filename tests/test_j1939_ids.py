import pytest
from j1939_ids import build_j1939_id, decode_j1939_id, PGN_ENGINE_SPEED, PGN_VEHICLE_SPEED


def test_roundtrip_engine_speed_pgn():
    can_id = build_j1939_id(priority=3, pgn=PGN_ENGINE_SPEED, source_address=0x00)
    decoded = decode_j1939_id(can_id)
    assert decoded["priority"] == 3
    assert decoded["pgn"] == PGN_ENGINE_SPEED
    assert decoded["source_address"] == 0x00


def test_roundtrip_vehicle_speed_pgn():
    can_id = build_j1939_id(priority=6, pgn=PGN_VEHICLE_SPEED, source_address=0x17)
    decoded = decode_j1939_id(can_id)
    assert decoded["priority"] == 6
    assert decoded["pgn"] == PGN_VEHICLE_SPEED
    assert decoded["source_address"] == 0x17


def test_decode_against_manually_packed_bits():
    # Independently construct the 29-bit layout by hand (not via build_j1939_id)
    # priority=5, pgn=0x1234, source_address=0xAB
    manual_id = (5 << 26) | (0x1234 << 8) | 0xAB
    decoded = decode_j1939_id(manual_id)
    assert decoded == {"priority": 5, "pgn": 0x1234, "source_address": 0xAB}


@pytest.mark.parametrize("priority", [0, 7])
def test_priority_valid_edges(priority):
    can_id = build_j1939_id(priority=priority, pgn=100, source_address=1)
    assert decode_j1939_id(can_id)["priority"] == priority


@pytest.mark.parametrize("priority", [-1, 8])
def test_priority_out_of_range_raises(priority):
    with pytest.raises(ValueError):
        build_j1939_id(priority=priority, pgn=100, source_address=1)


@pytest.mark.parametrize("pgn", [0, 0x3FFFF])
def test_pgn_valid_edges(pgn):
    can_id = build_j1939_id(priority=1, pgn=pgn, source_address=1)
    assert decode_j1939_id(can_id)["pgn"] == pgn


def test_pgn_out_of_range_raises():
    with pytest.raises(ValueError):
        build_j1939_id(priority=1, pgn=0x40000, source_address=1)


@pytest.mark.parametrize("addr", [0, 0xFF])
def test_source_address_valid_edges(addr):
    can_id = build_j1939_id(priority=1, pgn=100, source_address=addr)
    assert decode_j1939_id(can_id)["source_address"] == addr


@pytest.mark.parametrize("addr", [-1, 0x100])
def test_source_address_out_of_range_raises(addr):
    with pytest.raises(ValueError):
        build_j1939_id(priority=1, pgn=100, source_address=addr)
