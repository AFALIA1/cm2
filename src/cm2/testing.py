from __future__ import annotations

import subprocess
from dataclasses import dataclass


@dataclass
class TestResult:
    success: bool
    message: str


def _run_ffprobe(args: list[str], timeout: float) -> TestResult:
    try:
        proc = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=codec_name", "-of", "csv=p=0", *args],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        return TestResult(False, "ffprobe not found — is ffmpeg installed? (see setup.sh)")
    except subprocess.TimeoutExpired:
        return TestResult(False, f"timed out after {timeout:.0f}s")

    if proc.returncode == 0 and proc.stdout.strip():
        return TestResult(True, f"codec: {proc.stdout.strip()}")
    return TestResult(False, (proc.stderr or "no video stream detected").strip().splitlines()[-1])


def test_rtsp(url: str, timeout: float = 6.0) -> TestResult:
    """Force TCP first (far more reliable for consumer/embedded cameras),
    fall back to UDP only if TCP outright fails."""
    # -rw_timeout (not the deprecated, listen-mode-triggering "-timeout") is the
    # portable I/O timeout across ffmpeg versions for an RTSP *client* connection.
    result = _run_ffprobe(
        ["-rtsp_transport", "tcp", "-rw_timeout", str(int(timeout * 1_000_000)), "-i", url],
        timeout=timeout + 3,
    )
    if result.success:
        return result
    return _run_ffprobe(
        ["-rtsp_transport", "udp", "-rw_timeout", str(int(timeout * 1_000_000)), "-i", url],
        timeout=timeout + 3,
    )


def test_webcam(device_path: str, timeout: float = 5.0) -> TestResult:
    return _run_ffprobe(["-f", "v4l2", "-i", device_path], timeout=timeout + 3)
