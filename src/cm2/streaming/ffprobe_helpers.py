from __future__ import annotations

import subprocess

H264_LIKE_CODECS = {"h264", "hevc", "h265"}


def probe_codec(input_args: list[str], timeout: float = 6.0) -> str | None:
    """input_args is an ffprobe-style input spec ending in ["-i", url_or_device]
    (optionally preceded by e.g. ["-rtsp_transport", "tcp"] or ["-f", "v4l2"])."""
    try:
        proc = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=codec_name", "-of", "csv=p=0", *input_args],
            capture_output=True, text=True, timeout=timeout,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    codec = proc.stdout.strip()
    return codec or None


def sample_keyframe_interval(input_args: list[str], sample_frames: int = 120, timeout: float = 10.0) -> float | None:
    """Average seconds between keyframes, sampled from the first `sample_frames`
    video frames. Returns None if fewer than 2 keyframes were seen in the sample
    (source too short/slow to tell, or an unreadable/non-monotonic timestamp)."""
    try:
        proc = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "frame=key_frame,pts_time",
             "-read_intervals", f"%+#{sample_frames}",
             "-of", "csv=p=0", *input_args],
            capture_output=True, text=True, timeout=timeout,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None

    keyframe_times = []
    for line in proc.stdout.strip().splitlines():
        parts = line.split(",")
        if len(parts) != 2:
            continue
        is_key, pts_time = parts
        if is_key == "1":
            try:
                keyframe_times.append(float(pts_time))
            except ValueError:
                continue

    if len(keyframe_times) < 2:
        return None
    gaps = [b - a for a, b in zip(keyframe_times, keyframe_times[1:]) if b > a]
    if not gaps:
        return None
    return sum(gaps) / len(gaps)


def is_h264_like(codec_name: str | None) -> bool:
    return (codec_name or "").lower() in H264_LIKE_CODECS
