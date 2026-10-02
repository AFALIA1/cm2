from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import BinaryIO, Optional

BOUNDARY = "ffmpeg"


class FrameBus:
    """One writer (the ffmpeg-stdout reader thread), many readers (HTTP clients).
    A sequence number, not just the condition variable, is what a waiting client
    checks — that's what makes a missed wakeup harmless instead of a dropped frame."""

    def __init__(self) -> None:
        self._cond = threading.Condition()
        self._frame: Optional[bytes] = None
        self._seq = 0

    def publish(self, frame: bytes) -> None:
        with self._cond:
            self._frame = frame
            self._seq += 1
            self._cond.notify_all()

    def wait_for_next(self, last_seq: int, timeout: float = 10.0) -> tuple[Optional[bytes], int]:
        with self._cond:
            if self._seq == last_seq:
                self._cond.wait(timeout=timeout)
            return self._frame, self._seq


def _read_headers(stream: BinaryIO) -> dict[str, str]:
    headers: dict[str, str] = {}
    while True:
        line = stream.readline()
        if not line or line in (b"\r\n", b"\n"):
            break
        if b":" in line:
            key, _, value = line.partition(b":")
            headers[key.strip().lower().decode("latin-1")] = value.strip().decode("latin-1")
    return headers


def read_mpjpeg_stream(stdout: BinaryIO, frame_bus: FrameBus) -> None:
    """Parses ffmpeg's own `-f mpjpeg` output, which is already correct
    length-prefixed multipart framing (`--ffmpeg\\r\\nContent-Length: N\\r\\n\\r\\n<N bytes>`)
    — no JPEG marker-scanning needed, just read what ffmpeg already tells us to read."""
    while True:
        boundary_line = stdout.readline()
        if not boundary_line:
            return  # ffmpeg exited / pipe closed
        if not boundary_line.strip():
            continue
        headers = _read_headers(stdout)
        length_str = headers.get("content-length")
        if length_str is None:
            continue
        try:
            length = int(length_str)
        except ValueError:
            continue
        payload = stdout.read(length)
        if len(payload) < length:
            return  # short read: pipe closed mid-frame
        frame_bus.publish(payload)
        stdout.readline()  # trailing \r\n after the payload


def _make_handler(frame_bus: FrameBus, semaphore: threading.Semaphore) -> type[BaseHTTPRequestHandler]:
    class MJPEGRequestHandler(BaseHTTPRequestHandler):
        def do_HEAD(self) -> None:
            self.send_response(200)
            self.send_header("Content-Type", f"multipart/x-mixed-replace; boundary={BOUNDARY}")
            self.end_headers()

        def do_GET(self) -> None:
            if not semaphore.acquire(blocking=False):
                self.send_error(503, "Too many viewers")
                return
            try:
                self.send_response(200)
                self.send_header("Age", "0")
                self.send_header("Cache-Control", "no-cache, private")
                self.send_header("Pragma", "no-cache")
                self.send_header("Content-Type", f"multipart/x-mixed-replace; boundary={BOUNDARY}")
                self.end_headers()
                last_seq = 0
                while True:
                    frame, seq = frame_bus.wait_for_next(last_seq, timeout=10.0)
                    if frame is None or seq == last_seq:
                        continue  # nothing published yet, or just a wait timeout — keep waiting
                    last_seq = seq
                    self.wfile.write(
                        f"--{BOUNDARY}\r\nContent-Type: image/jpeg\r\n"
                        f"Content-Length: {len(frame)}\r\n\r\n".encode("ascii")
                    )
                    self.wfile.write(frame)
                    self.wfile.write(b"\r\n")
            except (BrokenPipeError, ConnectionResetError):
                pass
            finally:
                semaphore.release()

        def log_message(self, format: str, *args) -> None:
            pass

    return MJPEGRequestHandler


def serve_mjpeg(frame_bus: FrameBus, port: int, max_clients: int = 6) -> ThreadingHTTPServer:
    semaphore = threading.Semaphore(max_clients)
    handler = _make_handler(frame_bus, semaphore)
    return ThreadingHTTPServer(("0.0.0.0", port), handler)
