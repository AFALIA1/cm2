from __future__ import annotations

import argparse
from pathlib import Path

from cm2.streaming import worker


def _args(**overrides) -> argparse.Namespace:
    base = dict(
        protocol="hls", source_kind="rtsp", source="rtsp://cam/1", port=18000,
        workdir="/tmp/w", video_codec="libx264", hls_time=2.0, height=None, crf=23,
    )
    base.update(overrides)
    return argparse.Namespace(**base)


def _value_after(cmd: list[str], flag: str) -> str:
    return cmd[cmd.index(flag) + 1]


def test_hls_cmd_copy_ignores_scale_and_crf():
    cmd = worker._hls_cmd(_args(video_codec="copy", height=720, crf=28), Path("/tmp/w"))
    assert _value_after(cmd, "-c:v") == "copy"
    assert "-crf" not in cmd and "-vf" not in cmd


def test_hls_cmd_reencode_sets_crf_without_scaling_at_original_size():
    cmd = worker._hls_cmd(_args(crf=28), Path("/tmp/w"))
    assert _value_after(cmd, "-c:v") == "libx264"
    assert _value_after(cmd, "-crf") == "28"
    assert "-vf" not in cmd


def test_hls_cmd_scales_down_only_keeping_aspect():
    cmd = worker._hls_cmd(_args(height=480), Path("/tmp/w"))
    assert _value_after(cmd, "-vf") == "scale=-2:'min(480,ih)'"
