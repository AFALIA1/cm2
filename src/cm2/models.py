from __future__ import annotations

import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Optional


def new_id() -> str:
    return uuid.uuid4().hex[:12]


@dataclass
class Camera:
    id: str
    kind: str  # "webcam" | "rtsp" | "onvif"
    name: str
    address: str  # /dev/videoN for webcam, IP for rtsp/onvif
    port: Optional[int] = None
    brand: Optional[str] = None  # brand key, or "auto" for ONVIF auto-detect
    username: Optional[str] = None
    password: Optional[str] = None
    channel: Optional[int] = None
    rtsp_url: Optional[str] = None  # resolved, final source URL (webcam: not used)
    discovered_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Camera":
        return cls(**data)


@dataclass
class RunningStream:
    id: str
    camera_id: str
    camera_name: str
    protocol: str  # "hls" | "mjpeg"
    display_protocol: str  # "M3U8" | "HTTP"
    port: int
    pid: int  # the stream worker process's pid (ffmpeg is its child, same process group)
    create_time: float
    workdir: str  # per-stream dir: hls segments/playlist, or just the progress file for mjpeg
    url: str
    started_at: float = field(default_factory=time.time)
    hls_time: Optional[float] = None  # actual segment length used (hls only)
    hls_quality: Optional[str] = None  # e.g. "720p, Medium" (hls only)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RunningStream":
        return cls(**data)
