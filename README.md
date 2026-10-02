# cm2

CLI to scan for webcams and network RTSP/ONVIF cameras, test the connection, and stream them
out on a port you choose — **ffmpeg only**, no MediaMTX/nginx/Caddy or any other service
binary. This is the ffmpeg-only sibling of `camerasmanager` (which uses MediaMTX and also
supports WebRTC).

Only 2 output protocols are offered, both real ffmpeg-native outputs:
- **M3U8** — ffmpeg writes an HLS playlist + segments; a small built-in Python HTTP server
  (stdlib `http.server`, no extra dependency) serves them.
- **any http** — a genuine browser-viewable MJPEG stream (`multipart/x-mixed-replace`) built
  on ffmpeg's own `mpjpeg` muxer, which already emits correct multipart framing — a small
  built-in Python relay just fans that single ffmpeg stream out to multiple simultaneous
  viewers (ffmpeg's own HTTP output can only handle one client at a time).

WebRTC is intentionally not offered: ffmpeg has no ability to terminate a browser-facing
WebRTC connection in any version (WHIP, upstream since ffmpeg 7.0, only lets ffmpeg *push*
to a WebRTC server; the server/playback side, WHEP, isn't in upstream ffmpeg at all). If you
need WebRTC, use `camerasmanager` instead.

## Download

| OS | Installer |
|---|---|
| Windows 10/11 | [cm2-0.1.2-windows-x64-setup.exe](https://github.com/AFALIA1/cm2/releases/latest/download/cm2-0.1.2-windows-x64-setup.exe) |
| macOS (Apple Silicon M1–M4) | [cm2-0.1.2-macos-arm64.pkg](https://github.com/AFALIA1/cm2/releases/latest/download/cm2-0.1.2-macos-arm64.pkg) |
| macOS (Intel) | [cm2-0.1.2-macos-x86_64.pkg](https://github.com/AFALIA1/cm2/releases/latest/download/cm2-0.1.2-macos-x86_64.pkg) |
| Linux PC (Ubuntu/Debian) | [cm2_0.1.2_amd64.deb](https://github.com/AFALIA1/cm2/releases/latest/download/cm2_0.1.2_amd64.deb) |
| Linux ARM (Jetson, Raspberry Pi 64-bit) | [cm2_0.1.2_arm64.deb](https://github.com/AFALIA1/cm2/releases/latest/download/cm2_0.1.2_arm64.deb) |

All versions: [Releases](https://github.com/AFALIA1/cm2/releases)

## Install (one file per OS)

Each installer is a single file containing the whole app: Python and every dependency are
bundled, so nothing else is needed. The Windows and macOS installers also include ffmpeg;
on Linux, apt installs it. Every installer asks whether to **add cm2 to PATH automatically**
or leave PATH for you to set up manually.

| OS | File | How |
|---|---|---|
| Windows 10/11 (x64) | `cm2-<ver>-windows-x64-setup.exe` | Double-click. Leave "Add cm2 to the PATH…" ticked, or untick it to set PATH yourself. |
| Linux (Debian/Ubuntu/Jetson) | `cm2_<ver>_<amd64\|arm64>.deb` | `sudo apt install ./cm2_<ver>_<arch>.deb`, then answer the PATH question. |
| macOS (Apple Silicon / Intel) | `cm2-<ver>-macos-<arm64\|x86_64>.pkg` | Double-click. For manual PATH: **Customize** → untick "Add cm2 to PATH automatically". |

**Upgrading:** just run the newer installer over the old one; it replaces the old
version in place, keeps your PATH choice, and keeps your saved cameras (`~/.cm2`). Stop
running streams first (`cm2 stop`).

The installers are unsigned. On Windows, SmartScreen may show "More info → Run anyway". On
macOS, right-click the .pkg → Open, or allow it under System Settings → Privacy & Security.

### Building the installers

Push the project to GitHub and run the **build-installers** workflow (Actions tab), or push a
`v*` tag to publish a Release. Either way, all of them are built on real Windows, macOS and
Linux runners. To build one by hand on that OS:

```bash
python -m pip install . pyinstaller
python packaging/build_app.py          # -> dist/cm2/ (standalone app)
packaging/build_deb.sh                 # Linux  -> dist/*.deb
packaging/build_macos_pkg.sh           # macOS  -> dist/*.pkg
pwsh packaging/build_windows.ps1       # Windows (needs Inno Setup 6) -> dist/*.exe
```

### From source (development)

`./install.sh` (Linux/macOS) or `install.bat` (Windows) sets up a `venv/` with cm2 installed
in editable mode.

## Usage

```bash
cm2            # interactive menu: Scan / Status / Stop a stream / Exit
cm2 scan       # scan for cameras, configure, test, and start a stream
cm2 status     # show currently running streams
cm2 stop [id]  # stop a running stream
cm2 help       # list every command with examples (cm2 help <command> for details)
```

When you choose **M3U8**, cm2 also asks for a **resolution** (Original / 1080p / 720p /
480p / 360p, downscale only) and a **quality** (High / Medium / Low). "Original" for both
keeps the camera's own H.264 untouched (no re-encode, least CPU).

The scan flow (brand presets, ONVIF auto-detect, connection testing, back-navigation on
every prompt) matches `camerasmanager`'s — only the streaming backend differs.

### How streaming works

Each active stream is one background "worker" process (`python -m cm2.streaming.worker`,
survives the CLI exiting) that spawns ffmpeg as its own child and serves the result itself:
- HLS: ffmpeg writes segments to a per-stream directory; the worker serves that directory.
- MJPEG: ffmpeg pipes `-f mpjpeg` frames to the worker's stdin; the worker relays them to
  every connected HTTP client.

State (which streams are running, on which ports) lives in `~/.cm2/streams.json`. `cm2
status` reconciles that against what's actually still alive, and reports any orphaned ffmpeg
process left over from a crash (with an option to clean it up).

## Tests

```bash
pip install pytest
pytest
```
