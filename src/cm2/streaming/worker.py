from __future__ import annotations

import argparse
import signal
import subprocess
import sys
import threading
from pathlib import Path

from . import hls_server, mjpeg_server


def _build_input_args(source_kind: str, source: str) -> list[str]:
    if source_kind == "webcam":
        return ["-f", "v4l2", "-i", source]
    return ["-rtsp_transport", "tcp", "-i", source]


def _write_endlist(workdir: Path) -> None:
    playlist = workdir / "index.m3u8"
    try:
        with open(playlist, "a") as f:
            f.write("#EXT-X-ENDLIST\n")
    except OSError:
        pass


def _install_shutdown_handler(server, ffmpeg_proc: subprocess.Popen) -> None:
    def shutdown(*_a):
        server.shutdown()
        if ffmpeg_proc.poll() is None:
            ffmpeg_proc.terminate()
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)


def _hls_cmd(args: argparse.Namespace, workdir: Path) -> list[str]:
    input_args = _build_input_args(args.source_kind, args.source)

    if args.video_codec == "copy":
        codec_args = ["-c:v", "copy"]
    else:
        # Keyframe on every segment boundary, whatever the source fps is.
        codec_args = [
            "-c:v", "libx264", "-preset", "veryfast", "-crf", str(args.crf),
            "-pix_fmt", "yuv420p",
            "-force_key_frames", f"expr:gte(t,n_forced*{args.hls_time})",
        ]
        if args.height:
            # Downscale only; -2 keeps the aspect ratio with an even width.
            codec_args += ["-vf", f"scale=-2:'min({args.height},ih)'"]

    return [
        "ffmpeg", "-nostdin", "-loglevel", "warning",
        *input_args,
        "-fflags", "+genpts", "-avoid_negative_ts", "make_zero",
        *codec_args,
        "-f", "hls", "-hls_time", str(args.hls_time), "-hls_list_size", "6",
        "-hls_flags", "delete_segments+temp_file",
        "-progress", str(workdir / "progress.txt"),
        "-hls_segment_filename", str(workdir / "seg_%05d.ts"),
        str(workdir / "index.m3u8"),
    ]


def run_hls(args: argparse.Namespace) -> None:
    workdir = Path(args.workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    cmd = _hls_cmd(args, workdir)
    log_file = open(workdir / "ffmpeg.log", "a")
    ffmpeg_proc = subprocess.Popen(cmd, stdout=log_file, stderr=subprocess.STDOUT)

    server = hls_server.serve_directory(str(workdir), args.port)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    _install_shutdown_handler(server, ffmpeg_proc)

    ffmpeg_proc.wait()
    # Reached without a signal: ffmpeg exited on its own (camera dropped, or
    # something killed just the ffmpeg pid). Say so instead of serving a
    # frozen playlist forever, then follow it down.
    _write_endlist(workdir)
    server.shutdown()


def run_mjpeg(args: argparse.Namespace) -> None:
    workdir = Path(args.workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    input_args = _build_input_args(args.source_kind, args.source)

    cmd = [
        "ffmpeg", "-nostdin", "-loglevel", "warning",
        *input_args,
        "-f", "mpjpeg", "-q:v", "5", "-r", "10",
        "-progress", str(workdir / "progress.txt"),
        "pipe:1",
    ]
    log_file = open(workdir / "ffmpeg.log", "a")
    ffmpeg_proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=log_file)

    frame_bus = mjpeg_server.FrameBus()
    threading.Thread(
        target=mjpeg_server.read_mpjpeg_stream, args=(ffmpeg_proc.stdout, frame_bus), daemon=True,
    ).start()

    server = mjpeg_server.serve_mjpeg(frame_bus, args.port)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    _install_shutdown_handler(server, ffmpeg_proc)

    ffmpeg_proc.wait()
    server.shutdown()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", choices=["hls", "mjpeg"], required=True)
    parser.add_argument("--source-kind", choices=["webcam", "rtsp", "onvif"], required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--workdir", required=True)
    parser.add_argument("--video-codec", choices=["copy", "libx264"], default="libx264")
    parser.add_argument("--hls-time", type=float, default=2.0)
    parser.add_argument("--height", type=int, default=None, help="downscale to this height (libx264 only)")
    parser.add_argument("--crf", type=int, default=23, help="libx264 quality: lower = better")
    args = parser.parse_args()

    if args.protocol == "hls":
        run_hls(args)
    else:
        run_mjpeg(args)


if __name__ == "__main__":
    main()
