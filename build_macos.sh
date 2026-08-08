#!/bin/bash
set -e

echo "========================================"
echo "  VideoDownloader macOS Build Script"
echo "========================================"

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# 检查操作系统
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "Error: This script must be run on macOS"
    exit 1
fi

# 版本号：优先命令行参数，其次最近 git tag，默认 1.0.0
VERSION="${1:-$(git describe --tags --abbrev=0 2>/dev/null || echo 1.0.0)}"
echo "Building version: $VERSION"

# 检测本机架构并选对应 FFmpeg
case "$(uname -m)" in
    arm64) FF_ARCH="arm64" ;;
    x86_64) FF_ARCH="amd64" ;;
    *) echo "Error: unsupported arch: $(uname -m)"; exit 1 ;;
esac
FF_BASE="https://ffmpeg.martin-riedl.de/redirect/latest/macos/${FF_ARCH}/release"
echo "FFmpeg arch: $FF_ARCH"

echo "[1/6] Installing dependencies..."
pip install -r requirements-build.txt
pip install pyinstaller

echo "[2/6] Cleaning previous builds..."
rm -rf build dist

echo "[3/6] Downloading FFmpeg..."
mkdir -p build/ffmpeg
cd build/ffmpeg
curl -fL -o ffmpeg.zip "$FF_BASE/ffmpeg.zip"
unzip -o ffmpeg.zip
rm ffmpeg.zip
curl -fL -o ffprobe.zip "$FF_BASE/ffprobe.zip"
unzip -o ffprobe.zip
rm ffprobe.zip
cd "$SCRIPT_DIR"

echo "[4/6] Building application..."
APP_VERSION="$VERSION" FFMPEG_DIR="build/ffmpeg" pyinstaller VideoDownloader.spec --noconfirm

echo "[5/6] Verifying output..."
if [ ! -d "dist/VideoDownloader.app" ]; then
    echo "Error: Build failed - VideoDownloader.app not found"
    exit 1
fi
if [ ! -f "dist/VideoDownloader.app/Contents/Resources/ffmpeg/ffmpeg" ]; then
    echo "Error: ffmpeg not bundled in dist/VideoDownloader.app"
    exit 1
fi

echo "[6/6] Getting size..."
APP_SIZE=$(du -sh dist/VideoDownloader.app | cut -f1)
echo ""
echo "========================================"
echo "  Build Complete!"
echo "========================================"
echo "Output: dist/VideoDownloader.app"
echo "Version: $VERSION"
echo "Size: $APP_SIZE"
echo ""
echo "To run the app:"
echo "  open dist/VideoDownloader.app"
echo ""
echo "To create a dmg:"
echo "  hdiutil create -volname VideoDownloader -srcfolder dist/VideoDownloader.app -ov -format UDZO dist/VideoDownloader-$VERSION.dmg"
echo ""
