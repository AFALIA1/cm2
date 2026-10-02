#!/usr/bin/env bash
# Builds dist/cm2-<version>-macos-<arch>.pkg on a Mac (run packaging/build_app.py first).
# Bundles static ffmpeg + ffprobe and installs the app to /usr/local/cm2. The
# installer's "Customize" step asks whether to add cm2 to PATH automatically
# (/usr/local/bin/cm2 link) or leave PATH to the user. Arch is this Mac's.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="$(sed -n 's/^version = "\(.*\)"/\1/p' "$ROOT/pyproject.toml" | head -1)"
ARCH="$(uname -m)"
case "$ARCH" in
    arm64)  FFARCH=arm64 ;;
    x86_64) FFARCH=amd64 ;;
    *) echo "unsupported arch $ARCH" >&2; exit 1 ;;
esac
APP="$ROOT/dist/cm2"
WORK="$ROOT/build/macpkg"
OUT="$ROOT/dist/cm2-${VERSION}-macos-${ARCH}.pkg"

[ -x "$APP/cm2" ] || { echo "dist/cm2/cm2 missing - run packaging/build_app.py first" >&2; exit 1; }

# Static builds (no Homebrew needed on the user's Mac).
DL="$WORK/dl"
mkdir -p "$DL"
for tool in ffmpeg ffprobe; do
    curl -fL --retry 3 -o "$DL/$tool.zip" \
        "https://ffmpeg.martin-riedl.de/redirect/latest/macos/$FFARCH/release/$tool.zip"
    unzip -o -q "$DL/$tool.zip" -d "$DL"
    install -m 755 "$DL/$tool" "$APP/$tool"
done

rm -rf "$WORK/app-root" "$WORK/path-root" "$WORK/pkgs" "$WORK/resources"
mkdir -p "$WORK/app-root/usr/local" "$WORK/path-root/usr/local/bin" "$WORK/pkgs" "$WORK/resources"
cp -a "$APP" "$WORK/app-root/usr/local/cm2"
ln -s /usr/local/cm2/cm2 "$WORK/path-root/usr/local/bin/cm2"

pkgbuild --root "$WORK/app-root" --install-location / \
    --identifier com.cm2.cli.app --version "$VERSION" "$WORK/pkgs/cm2-app.pkg"
pkgbuild --root "$WORK/path-root" --install-location / \
    --identifier com.cm2.cli.path --version "$VERSION" "$WORK/pkgs/cm2-path.pkg"

cp "$ROOT/packaging/macos/welcome.html" "$ROOT/packaging/macos/conclusion.html" "$WORK/resources/"
sed -e "s/__VERSION__/$VERSION/g" -e "s/__ARCH__/$ARCH/g" \
    "$ROOT/packaging/macos/distribution.xml" > "$WORK/distribution.xml"

productbuild --distribution "$WORK/distribution.xml" --package-path "$WORK/pkgs" \
    --resources "$WORK/resources" "$OUT"
echo "Built $OUT"
