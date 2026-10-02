from __future__ import annotations

import questionary

from cm2 import menu
from cm2.models import RunningStream
from cm2.streaming import manager as manager_module


class _Scripted:
    def __init__(self, value):
        self._value = value

    def ask(self):
        return self._value


def _scripted_calls(monkeypatch, target, name, values):
    """Patch questionary.<name> so each call pops the next scripted answer."""
    it = iter(values)

    def fake(*args, **kwargs):
        try:
            return _Scripted(next(it))
        except StopIteration:
            raise AssertionError(f"questionary.{name} called more times than scripted") from None

    monkeypatch.setattr(target, name, fake)
    return it


def test_scan_flow_back_and_forth_reaches_done(isolated_home, monkeypatch):
    webcam_candidate = {"kind": "webcam", "name": "Cam", "address": "/dev/video0"}
    candidate_label = "[WEBCAM] Cam (/dev/video0)"

    monkeypatch.setattr(menu, "run_scan", lambda: [webcam_candidate])
    monkeypatch.setattr(menu, "_test_camera", lambda camera: True)

    started = {}

    def fake_start_stream(camera, protocol, display_protocol, port, height=None, crf=None):
        stream = RunningStream(
            id="abc123", camera_id=camera.id, camera_name=camera.name,
            protocol=protocol, display_protocol=display_protocol, port=port,
            pid=1, create_time=0.0, workdir="/tmp/x", url=f"http://x:{port}/",
        )
        started["stream"] = stream
        started["height"], started["crf"] = height, crf
        return stream

    monkeypatch.setattr(manager_module, "start_stream", fake_start_stream)

    # Selects, in call order: pick the webcam, choose protocol, resolution and
    # quality; going BACK from port re-asks quality; then end at the "done" menu.
    _scripted_calls(monkeypatch, questionary, "select", [
        candidate_label,        # candidate step
        "M3U8",                 # protocol step
        "Original",             # resolution step
        menu.ORIGINAL_QUALITY,  # quality step (first attempt)
        "Low",                  # quality step (re-asked after backing out of port)
        "End",                  # done step
    ])
    # Texts, in call order: back out of the very first port prompt (None), then
    # supply a real port on the second attempt.
    _scripted_calls(monkeypatch, questionary, "text", [None, "18000"])

    menu.scan_flow()

    assert started["stream"].port == 18000
    assert started["stream"].protocol == "hls"
    assert started["stream"].display_protocol == "M3U8"
    assert (started["height"], started["crf"]) == (None, manager_module.HLS_QUALITY_CRF["Low"])


def test_scan_flow_m3u8_scale_and_back_to_resolution(isolated_home, monkeypatch):
    monkeypatch.setattr(menu, "run_scan", lambda: [{"kind": "webcam", "name": "Cam", "address": "/dev/video0"}])
    monkeypatch.setattr(menu, "_test_camera", lambda camera: True)
    started = {}

    def fake_start_stream(camera, protocol, display_protocol, port, height=None, crf=None):
        started.update(height=height, crf=crf)
        return RunningStream(
            id="abc123", camera_id=camera.id, camera_name=camera.name,
            protocol=protocol, display_protocol=display_protocol, port=port,
            pid=1, create_time=0.0, workdir="/tmp/x", url=f"http://x:{port}/",
        )

    monkeypatch.setattr(manager_module, "start_stream", fake_start_stream)
    _scripted_calls(monkeypatch, questionary, "select", [
        "[WEBCAM] Cam (/dev/video0)",
        "M3U8",
        "1080p",
        menu.BACK,   # quality -> back to resolution
        "720p",
        "Medium",
        "End",
    ])
    _scripted_calls(monkeypatch, questionary, "text", ["18001"])

    menu.scan_flow()

    assert started == {"height": 720, "crf": 23}


def test_scan_flow_mjpeg_skips_quality(isolated_home, monkeypatch):
    monkeypatch.setattr(menu, "run_scan", lambda: [{"kind": "webcam", "name": "Cam", "address": "/dev/video0"}])
    monkeypatch.setattr(menu, "_test_camera", lambda camera: True)
    started = {}

    def fake_start_stream(camera, protocol, display_protocol, port, height=None, crf=None):
        started.update(protocol=protocol, height=height, crf=crf)
        return RunningStream(
            id="abc123", camera_id=camera.id, camera_name=camera.name,
            protocol=protocol, display_protocol=display_protocol, port=port,
            pid=1, create_time=0.0, workdir="/tmp/x", url=f"http://x:{port}/",
        )

    monkeypatch.setattr(manager_module, "start_stream", fake_start_stream)
    _scripted_calls(monkeypatch, questionary, "select", ["[WEBCAM] Cam (/dev/video0)", "any http", "End"])
    _scripted_calls(monkeypatch, questionary, "text", ["18002"])

    menu.scan_flow()

    assert started == {"protocol": "mjpeg", "height": None, "crf": None}


def test_choose_candidate_recovers_from_invalid_manual_ip(monkeypatch):
    _scripted_calls(monkeypatch, questionary, "select", [
        menu.MANUAL_ENTRY,  # first attempt: go to manual entry
        menu.RESCAN,        # after the bad IP bounces back to the list, pick rescan
    ])
    _scripted_calls(monkeypatch, questionary, "text", ["not-an-ip"])

    result = menu._choose_candidate([])

    assert result == {"_rescan": True}
