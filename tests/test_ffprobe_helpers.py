from __future__ import annotations

import subprocess
from unittest.mock import MagicMock

from cm2.streaming import ffprobe_helpers


def test_is_h264_like():
    assert ffprobe_helpers.is_h264_like("h264")
    assert ffprobe_helpers.is_h264_like("HEVC")
    assert not ffprobe_helpers.is_h264_like("mjpeg")
    assert not ffprobe_helpers.is_h264_like(None)


def test_probe_codec_parses_stdout(monkeypatch):
    monkeypatch.setattr(
        subprocess, "run",
        lambda *a, **k: MagicMock(stdout="h264\n", returncode=0),
    )
    assert ffprobe_helpers.probe_codec(["-i", "rtsp://x"]) == "h264"


def test_probe_codec_returns_none_on_missing_ffprobe(monkeypatch):
    def raise_missing(*a, **k):
        raise FileNotFoundError

    monkeypatch.setattr(subprocess, "run", raise_missing)
    assert ffprobe_helpers.probe_codec(["-i", "rtsp://x"]) is None


def test_sample_keyframe_interval_averages_gaps(monkeypatch):
    # key_frame,pts_time rows: keyframes at t=0, t=2, t=4 -> average gap 2.0s
    csv = "1,0.0\n0,0.5\n0,1.0\n1,2.0\n0,2.5\n1,4.0\n"
    monkeypatch.setattr(
        subprocess, "run",
        lambda *a, **k: MagicMock(stdout=csv, returncode=0),
    )
    assert ffprobe_helpers.sample_keyframe_interval(["-i", "rtsp://x"]) == 2.0


def test_sample_keyframe_interval_returns_none_with_fewer_than_two_keyframes(monkeypatch):
    monkeypatch.setattr(
        subprocess, "run",
        lambda *a, **k: MagicMock(stdout="1,0.0\n0,0.5\n", returncode=0),
    )
    assert ffprobe_helpers.sample_keyframe_interval(["-i", "rtsp://x"]) is None
