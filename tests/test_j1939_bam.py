import random
import pytest
from j1939_bam import build_bam_cm_frame, fragment_message, reassemble_message, PGN_TP_DT, PGN_TP_CM


def test_fragment_exact_multiple_of_seven():
    data = b"A" * 14  # exactly 2 frames, no padding needed
    frames = fragment_message(data)
    assert len(frames) == 2
    assert frames[0][0] == 1
    assert frames[1][0] == 2
    assert frames[0][1:] == b"A" * 7
    assert frames[1][1:] == b"A" * 7


def test_fragment_short_message_pads_last_frame():
    data = b"HI"  # 2 bytes, needs padding to fill 7
    frames = fragment_message(data)
    assert len(frames) == 1
    assert frames[0][0] == 1
    assert frames[0][1:3] == b"HI"
    assert frames[0][3:] == b"\xFF" * 5


def test_fragment_sequence_numbers_increment():
    data = b"X" * 30  # 5 frames
    frames = fragment_message(data)
    seqs = [f[0] for f in frames]
    assert seqs == [1, 2, 3, 4, 5]


def test_reassemble_in_order():
    original = b"ENGINE_FAULT_CODE_P0301"
    frames = fragment_message(original)
    result = reassemble_message(frames, len(original))
    assert result == original


def test_reassemble_out_of_order():
    # This is the real-world case: frames arrive shuffled off the bus
    original = b"ENGINE_FAULT_CODE_P0301_CYLINDER_1_MISFIRE_DETECTED"
    frames = fragment_message(original)
    shuffled = frames.copy()
    random.seed(42)
    random.shuffle(shuffled)
    assert shuffled != frames  # sanity check the shuffle actually did something
    result = reassemble_message(shuffled, len(original))
    assert result == original


def test_reassemble_trims_padding():
    data = b"AB"  # will be padded to 7 bytes with 0xFF
    frames = fragment_message(data)
    result = reassemble_message(frames, len(data))
    assert result == data
    assert len(result) == 2  # padding correctly trimmed, not leaked into output


def test_bam_cm_frame_num_packets_exact_boundary():
    # 7 bytes = exactly 1 frame
    frame = build_bam_cm_frame(total_size=7, target_pgn=65226)
    assert frame[3] == 1  # num_packets byte


def test_bam_cm_frame_num_packets_one_over_boundary():
    # 8 bytes = needs 2 frames (7 + 1)
    frame = build_bam_cm_frame(total_size=8, target_pgn=65226)
    assert frame[3] == 2


def test_bam_cm_frame_control_byte_and_size():
    frame = build_bam_cm_frame(total_size=300, target_pgn=65226)
    assert frame[0] == 0x20  # BAM control byte
    assert frame[1] == 300 & 0xFF
    assert frame[2] == (300 >> 8) & 0xFF


def test_bam_cm_frame_length_is_eight_bytes():
    frame = build_bam_cm_frame(total_size=50, target_pgn=65226)
    assert len(frame) == 8


def test_end_to_end_fragment_shuffle_reassemble_multiple_sizes():
    random.seed(7)
    for size in [1, 6, 7, 8, 13, 14, 50, 100]:
        original = bytes(random.randint(0, 254) for _ in range(size))  # avoid 0xFF to not collide with padding
        frames = fragment_message(original)
        shuffled = frames.copy()
        random.shuffle(shuffled)
        result = reassemble_message(shuffled, size)
        assert result == original, f"failed at size={size}"
