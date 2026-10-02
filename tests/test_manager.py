from __future__ import annotations

from cm2.models import RunningStream
from cm2.streaming import manager


class FakeProcess:
    def __init__(self, create_time):
        self._create_time = create_time

    def create_time(self):
        return self._create_time


class FakeIterProc:
    def __init__(self, info):
        self.info = info


def test_decide_hls_encoding_webcam_always_reencodes(monkeypatch):
    codec, hls_time = manager._decide_hls_encoding("webcam", "/dev/video0")
    assert codec == "libx264"
    assert hls_time == manager.DEFAULT_HLS_TIME


def test_decide_hls_encoding_non_h264_reencodes(monkeypatch):
    monkeypatch.setattr(manager.ffprobe_helpers, "probe_codec", lambda args: "mjpeg")
    codec, hls_time = manager._decide_hls_encoding("rtsp", "rtsp://x")
    assert codec == "libx264"
    assert hls_time == manager.DEFAULT_HLS_TIME


def test_decide_hls_encoding_h264_short_gop_uses_default(monkeypatch):
    monkeypatch.setattr(manager.ffprobe_helpers, "probe_codec", lambda args: "h264")
    monkeypatch.setattr(manager.ffprobe_helpers, "sample_keyframe_interval", lambda args: 1.0)
    codec, hls_time = manager._decide_hls_encoding("rtsp", "rtsp://x")
    assert codec == "copy"
    assert hls_time == manager.DEFAULT_HLS_TIME


def test_decide_hls_encoding_h264_long_gop_bumps_hls_time(monkeypatch):
    monkeypatch.setattr(manager.ffprobe_helpers, "probe_codec", lambda args: "h264")
    monkeypatch.setattr(manager.ffprobe_helpers, "sample_keyframe_interval", lambda args: 8.0)
    codec, hls_time = manager._decide_hls_encoding("rtsp", "rtsp://x")
    assert codec == "copy"
    assert hls_time == 8.0


def test_reconcile_finds_orphan_ffmpeg_not_belonging_to_any_alive_worker(isolated_home, monkeypatch):
    workdir = str(isolated_home / "streams" / "s1")
    stream = RunningStream(
        id="s1", camera_id="c1", camera_name="Cam", protocol="hls", display_protocol="M3U8",
        port=8000, pid=111, create_time=1000.0, workdir=workdir, url="http://x/",
    )
    manager.save_streams([stream])

    def fake_process(pid):
        if pid == 111:
            return FakeProcess(1000.0)
        raise manager.psutil.NoSuchProcess(pid)

    monkeypatch.setattr(manager.psutil, "Process", fake_process)

    fake_procs = [
        # orphan: references one of our workdirs, but its parent isn't a live worker
        {"pid": 222, "ppid": 999, "name": "ffmpeg",
         "cmdline": ["ffmpeg", "-progress", f"{workdir}_orphan/progress.txt"]},
        # legitimate: still parented to the alive worker (pid 111)
        {"pid": 333, "ppid": 111, "name": "ffmpeg",
         "cmdline": ["ffmpeg", "-progress", f"{workdir}/progress.txt"]},
        # unrelated process entirely
        {"pid": 444, "ppid": 1, "name": "bash", "cmdline": ["bash"]},
    ]
    monkeypatch.setattr(manager.psutil, "process_iter", lambda attrs: [FakeIterProc(p) for p in fake_procs])

    result = manager.reconcile()

    assert [s.id for s in result.alive] == ["s1"]
    assert result.orphans == [222]


def test_reconcile_drops_dead_stream_and_saves(isolated_home, monkeypatch):
    stream = RunningStream(
        id="dead1", camera_id="c1", camera_name="Cam", protocol="hls", display_protocol="M3U8",
        port=8000, pid=999999, create_time=1000.0, workdir=str(isolated_home / "streams" / "dead1"),
        url="http://x/",
    )
    manager.save_streams([stream])

    def fake_process(pid):
        raise manager.psutil.NoSuchProcess(pid)

    monkeypatch.setattr(manager.psutil, "Process", fake_process)
    monkeypatch.setattr(manager.psutil, "process_iter", lambda attrs: [])

    result = manager.reconcile()

    assert result.alive == []
    assert [s.id for s in result.dead] == ["dead1"]
    assert manager.load_streams() == []


def _capture_worker_cmd(monkeypatch, tmp_path, **kwargs):
    from cm2 import storage
    from cm2.models import Camera

    captured = {}

    class FakePopen:
        pid = 4242

        def __init__(self, cmd, **_kw):
            captured["cmd"] = cmd

    monkeypatch.setattr(storage, "STREAM_WORKDIRS_DIR", tmp_path)
    monkeypatch.setattr(manager.ports, "is_tcp_port_free", lambda port: True)
    monkeypatch.setattr(manager.ports, "get_local_ip", lambda: "127.0.0.1")
    monkeypatch.setattr(manager.subprocess, "Popen", FakePopen)
    monkeypatch.setattr(manager.psutil, "Process", lambda pid: FakeProcess(1.0))
    monkeypatch.setattr(manager, "_decide_hls_encoding", lambda kind, src: ("copy", 2.0))
    camera = Camera(id="c1", kind="rtsp", name="Cam", address="1.2.3.4", rtsp_url="rtsp://x")
    stream = manager.start_stream(camera, "hls", "M3U8", 18000, **kwargs)
    return captured["cmd"], stream


def test_start_stream_hls_default_keeps_auto_copy(isolated_home, monkeypatch, tmp_path):
    cmd, stream = _capture_worker_cmd(monkeypatch, tmp_path)
    assert cmd[cmd.index("--video-codec") + 1] == "copy"
    assert "--height" not in cmd and "--crf" not in cmd
    assert stream.hls_quality == "original size, original quality"


def test_start_stream_hls_scale_forces_reencode(isolated_home, monkeypatch, tmp_path):
    cmd, stream = _capture_worker_cmd(monkeypatch, tmp_path, height=720, crf=28)
    assert cmd[cmd.index("--video-codec") + 1] == "libx264"
    assert cmd[cmd.index("--height") + 1] == "720"
    assert cmd[cmd.index("--crf") + 1] == "28"
    assert stream.hls_quality == "720p, Low"
