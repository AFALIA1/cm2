#!/usr/bin/env bash
# cm2 installer for Linux and macOS.
# Installs ffmpeg + Python 3.9+, creates ./venv, and installs cm2 into it.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"
OS="$(uname -s)"

info() { printf '==> %s\n' "$*"; }
die()  { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
have() { command -v "$1" >/dev/null 2>&1; }

SUDO=""
if [ "$(id -u)" -ne 0 ] && have sudo; then
    SUDO="sudo"
fi

install_linux_deps() {
    if have apt-get; then
        info "Installing ffmpeg and Python via apt..."
        $SUDO apt-get update
        $SUDO apt-get install -y ffmpeg python3 python3-venv python3-pip
    elif have dnf; then
        info "Installing ffmpeg and Python via dnf..."
        # ffmpeg on Fedora/RHEL may need RPM Fusion; ffmpeg-free is the in-repo fallback.
        $SUDO dnf install -y python3 python3-pip ffmpeg || $SUDO dnf install -y python3 python3-pip ffmpeg-free
    elif have pacman; then
        info "Installing ffmpeg and Python via pacman..."
        $SUDO pacman -Sy --needed --noconfirm ffmpeg python python-pip
    elif have zypper; then
        info "Installing ffmpeg and Python via zypper..."
        $SUDO zypper --non-interactive install ffmpeg python3 python3-pip
    elif have apk; then
        info "Installing ffmpeg and Python via apk..."
        $SUDO apk add --no-cache ffmpeg python3 py3-pip
    else
        echo "WARNING: no supported package manager found (apt/dnf/pacman/zypper/apk)."
        echo "         Install ffmpeg and Python 3.9+ yourself, then re-run this script."
    fi
}

install_macos_deps() {
    if ! have brew; then
        die "Homebrew is required on macOS. Install it from https://brew.sh then re-run this script."
    fi
    info "Installing ffmpeg and Python via Homebrew..."
    have ffmpeg || brew install ffmpeg
    have python3 || brew install python
}

case "$OS" in
    Linux)  install_linux_deps ;;
    Darwin) install_macos_deps ;;
    *)      die "Unsupported OS '$OS'. On Windows, run install.bat instead." ;;
esac

have ffmpeg  || die "ffmpeg not found on PATH after install."
have ffprobe || die "ffprobe not found on PATH after install."

PYTHON=""
for candidate in python3 python; do
    if have "$candidate" && "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null; then
        PYTHON="$candidate"
        break
    fi
done
[ -n "$PYTHON" ] || die "Python 3.9 or newer is required."
info "Using $($PYTHON --version) at $(command -v "$PYTHON")"

info "Creating Python virtual environment in $VENV_DIR..."
"$PYTHON" -m venv "$VENV_DIR"
"$VENV_DIR/bin/python" -m pip install --upgrade pip
"$VENV_DIR/bin/python" -m pip install -e "$SCRIPT_DIR"

echo
echo "Setup complete. Activate with:"
echo "  source $VENV_DIR/bin/activate"
echo "Then run: cm2"
