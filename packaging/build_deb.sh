#!/usr/bin/env bash
# Builds dist/cm2_<version>_<arch>.deb from dist/cm2/ (run packaging/build_app.py first).
# Installs the app to /opt/cm2; apt pulls in ffmpeg. During install it asks whether to
# add cm2 to PATH automatically (/usr/bin/cm2 link) or leave PATH to the user.
# The arch is this machine's (amd64, arm64, ...) — build on each arch you want to ship.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="$(sed -n 's/^version = "\(.*\)"/\1/p' "$ROOT/pyproject.toml" | head -1)"
ARCH="$(dpkg --print-architecture)"
PKG="$ROOT/build/deb/cm2_${VERSION}_${ARCH}"
OUT="$ROOT/dist/cm2_${VERSION}_${ARCH}.deb"

[ -x "$ROOT/dist/cm2/cm2" ] || { echo "dist/cm2/cm2 missing - run packaging/build_app.py first" >&2; exit 1; }

rm -rf "$PKG"
mkdir -p "$PKG/DEBIAN" "$PKG/opt"
cp -a "$ROOT/dist/cm2" "$PKG/opt/cm2"
install -m 644 "$ROOT/packaging/deb/templates" "$PKG/DEBIAN/templates"
for script in config postinst postrm; do
    install -m 755 "$ROOT/packaging/deb/$script" "$PKG/DEBIAN/$script"
done

cat > "$PKG/DEBIAN/control" <<CONTROL
Package: cm2
Version: $VERSION
Section: video
Priority: optional
Architecture: $ARCH
Depends: ffmpeg, debconf (>= 0.5) | debconf-2.0
Maintainer: cm2 <noreply@localhost>
Installed-Size: $(du -sk "$PKG/opt" | cut -f1)
Description: Scan, test and stream RTSP/ONVIF cameras and webcams (ffmpeg only)
 Streams cameras out as HLS (M3U8) or browser-viewable MJPEG over HTTP.
 Run "cm2" for the interactive menu.
CONTROL

fakeroot dpkg-deb --build "$PKG" "$OUT"
echo "Built $OUT"
