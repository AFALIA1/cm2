from __future__ import annotations

import io

from cm2.streaming.mjpeg_server import FrameBus, read_mpjpeg_stream


def _mpjpeg_bytes(frames: list[bytes]) -> bytes:
    out = b""
    for frame in frames:
        out += (
            f"--ffmpeg\r\nContent-type: image/jpeg\r\nContent-length: {len(frame)}\r\n\r\n"
        ).encode("ascii")
        out += frame + b"\r\n"
    return out


def test_read_mpjpeg_stream_publishes_each_frame_in_order():
    data = _mpjpeg_bytes([b"AAAA", b"BBBBB", b"C"])
    bus = FrameBus()

    read_mpjpeg_stream(io.BytesIO(data), bus)

    frame, seq = bus.wait_for_next(last_seq=0, timeout=0.01)
    assert frame == b"C"  # last published frame
    assert seq == 3  # three frames were published


def test_read_mpjpeg_stream_stops_cleanly_on_short_read():
    # A Content-Length that promises more bytes than are actually present
    # (pipe closed mid-frame) must not hang or raise.
    truncated = b"--ffmpeg\r\nContent-type: image/jpeg\r\nContent-length: 100\r\n\r\nshort"
    bus = FrameBus()

    read_mpjpeg_stream(io.BytesIO(truncated), bus)

    frame, seq = bus.wait_for_next(last_seq=0, timeout=0.01)
    assert frame is None
    assert seq == 0


def test_read_mpjpeg_stream_ignores_blank_lines_between_parts():
    data = b"\r\n" + _mpjpeg_bytes([b"X"])
    bus = FrameBus()

    read_mpjpeg_stream(io.BytesIO(data), bus)

    frame, _ = bus.wait_for_next(last_seq=0, timeout=0.01)
    assert frame == b"X"
