from __future__ import annotations

import glob
from dataclasses import dataclass
from pathlib import Path


@dataclass
class WebcamDevice:
    path: str
    name: str


def _device_name(device_path: str) -> str:
    dev = Path(device_path).name  # e.g. "video0"
    name_file = Path(f"/sys/class/video4linux/{dev}/name")
    try:
        return name_file.read_text().strip()
    except OSError:
        return "Unknown webcam"


def scan_webcams() -> list[WebcamDevice]:
    devices = []
    for path in sorted(glob.glob("/dev/video*")):
        devices.append(WebcamDevice(path=path, name=_device_name(path)))
    return devices
