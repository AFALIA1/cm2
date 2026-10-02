from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Optional

import psutil

from .. import storage
from ..models import Camera, RunningStream, new_id
from . import ffprobe_helpers, ports

DEFAULT_HLS_TIME = 2.0


def load_streams() -> list[RunningStream]:
    return [RunningStream.from_dict(d) for d in storage.load_json_list(storage.STREAMS_FILE)]


def save_streams(streams: list[RunningStream]) -> None:
    storage.save_json_list(storage.STREAMS_FILE, [s.to_dict() for s in streams])


def _pid_matches(pid: int, expected_create_time: float) -> bool:
    try:
        proc = psutil.Process(pid)
    except psutil.NoSuchProcess:
        return False
    return abs(proc.create_time() - expected_create_time) < 1.0


@dataclass
class Reconciled:
    alive: list[RunningStream]
    dead: list[RunningStream]
    orphans: list[int]  # ffmpeg pids whose worker is gone


def reconcile() -> Reconciled:
    with storage.locked():
        streams = load_streams()
        alive, dead = [], []
        for s in streams:
            if _pid_matches(s.pid, s.create_time):
                alive.append(s)
            else:
                dead.append(s)
        if dead:
            save_streams(alive)

    known_worker_pids = {s.pid for s in alive}
    workdirs_root = str(storage.STREAM_WORKDIRS_DIR)
    orphans = []
    for proc in psutil.process_iter(["pid", "ppid", "name", "cmdline"]):
        try:
            cmdline = proc.info["cmdline"] or []
            name = proc.info.get("name") or ""
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
        if "ffmpeg" not in name and not any("ffmpeg" in c for c in cmdline):
            continue
        if not any(workdirs_root in c for c in cmdline):
            continue  # not one of ours
        if proc.info.get("ppid") in known_worker_pids:
            continue  # still supervised by a live worker
        orphans.append(proc.info["pid"])

    return Reconciled(alive=alive, dead=dead, orphans=orphans)


def health(stream: RunningStream) -> str:
    if not _pid_matches(stream.pid, stream.create_time):
        return "dead"
    if ports.is_tcp_port_free(stream.port):
        return "port-down"
    return "running"


def kill_orphan(pid: int, timeout: float = 5.0) -> None:
    try:
        proc = psutil.Process(pid)
    except psutil.NoSuchProcess:
        return
    proc.terminate()
    try:
        proc.wait(timeout=timeout)
    except psutil.TimeoutExpired:
        proc.kill()


def _killpg(pid: int, timeout: float = 5.0) -> None:
    """The worker is launched with start_new_session=True, so pid is also its
    process group id — killpg reaches its ffmpeg child too, and keeps working
    even if the worker itself already died (the pgid stays valid as long as
    any member, e.g. an orphaned ffmpeg, is still alive)."""
    try:
        pgid = os.getpgid(pid)
    except ProcessLookupError:
        return
    try:
        os.killpg(pgid, signal.SIGTERM)
    except ProcessLookupError:
        return
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not psutil.pid_exists(pid):
            return
        time.sleep(0.2)
    try:
        os.killpg(pgid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def _decide_hls_encoding(source_kind: str, source: str) -> tuple[str, float]:
    if source_kind == "webcam":
        return "libx264", DEFAULT_HLS_TIME
    input_args = ["-rtsp_transport", "tcp", "-i", source]
    codec = ffprobe_helpers.probe_codec(input_args)
    if not ffprobe_helpers.is_h264_like(codec):
        return "libx264", DEFAULT_HLS_TIME
    gop_seconds = ffprobe_helpers.sample_keyframe_interval(input_args)
    if gop_seconds and gop_seconds > DEFAULT_HLS_TIME * 1.5:
        return "copy", round(gop_seconds, 1)
    return "copy", DEFAULT_HLS_TIME


def _worker_cmd() -> list[str]:
    # A packaged (PyInstaller) build has no `python -m`; its entry point
    # (packaging/cm2_entry.py) dispatches this hidden first argument instead.
    if getattr(sys, "frozen", False):
        return [sys.executable, "__worker__"]
    return [sys.executable, "-m", "cm2.streaming.worker"]


def start_stream(camera: Camera, protocol: str, display_protocol: str, port: int) -> RunningStream:
    if not ports.is_tcp_port_free(port):
        raise RuntimeError(f"port {port} is already in use")

    stream_id = new_id()
    workdir = storage.STREAM_WORKDIRS_DIR / stream_id
    workdir.mkdir(parents=True, exist_ok=True)

    source_kind = "webcam" if camera.kind == "webcam" else camera.kind
    source = camera.address if camera.kind == "webcam" else camera.rtsp_url

    cmd = _worker_cmd() + [
        "--protocol", protocol, "--source-kind", source_kind, "--source", source,
        "--port", str(port), "--workdir", str(workdir),
    ]

    hls_time: Optional[float] = None
    if protocol == "hls":
        video_codec, hls_time = _decide_hls_encoding(source_kind, source)
        cmd += ["--video-codec", video_codec, "--hls-time", str(hls_time)]

    proc = subprocess.Popen(cmd, start_new_session=True)
    ps = psutil.Process(proc.pid)

    host = ports.get_local_ip()
    url = f"http://{host}:{port}/index.m3u8" if protocol == "hls" else f"http://{host}:{port}/"

    stream = RunningStream(
        id=stream_id, camera_id=camera.id, camera_name=camera.name,
        protocol=protocol, display_protocol=display_protocol, port=port,
        pid=proc.pid, create_time=ps.create_time(), workdir=str(workdir), url=url,
        hls_time=hls_time,
    )

    with storage.locked():
        streams = load_streams()
        streams.append(stream)
        save_streams(streams)

    return stream


def stop_stream(stream_id: str) -> bool:
    with storage.locked():
        streams = load_streams()
        match = next((s for s in streams if s.id == stream_id), None)
        if match is None:
            return False
        remaining = [s for s in streams if s.id != stream_id]
        save_streams(remaining)

    _killpg(match.pid)
    shutil.rmtree(match.workdir, ignore_errors=True)
    return True
