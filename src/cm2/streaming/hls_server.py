from __future__ import annotations

import functools
import mimetypes
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

EXTRA_MIME_TYPES = {
    ".m3u8": "application/vnd.apple.mpegurl",
    ".ts": "video/mp2t",
}


class HLSRequestHandler(SimpleHTTPRequestHandler):
    def guess_type(self, path: str) -> str:
        for ext, mime in EXTRA_MIME_TYPES.items():
            if path.endswith(ext):
                return mime
        return super().guess_type(path)

    def end_headers(self) -> None:
        # The playlist rewrites constantly; segments are immutable once written.
        if self.path.endswith(".m3u8"):
            self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def log_message(self, format: str, *args) -> None:
        pass  # keep worker logs to ffmpeg/lifecycle events, not per-request noise


def serve_directory(workdir: str, port: int) -> ThreadingHTTPServer:
    handler = functools.partial(HLSRequestHandler, directory=workdir)
    server = ThreadingHTTPServer(("0.0.0.0", port), handler)
    return server
