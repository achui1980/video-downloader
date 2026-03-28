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

echo "[1/5] Installing dependencies..."
pip install -r requirements.txt
pip install pyinstaller

echo "[2/5] Cleaning previous builds..."
rm -rf build dist
rm -rf *.egg-info

echo "[3/5] Building application..."
pyinstaller VideoDownloader.spec --noconfirm

echo "[4/5] Verifying output..."
if [ ! -d "dist/VideoDownloader.app" ]; then
    echo "Error: Build failed - VideoDownloader.app not found"
    exit 1
fi

echo "[5/5] Getting size..."
APP_SIZE=$(du -sh dist/VideoDownloader.app | cut -f1)
echo ""
echo "========================================"
echo "  Build Complete!"
echo "========================================"
echo "Output: dist/VideoDownloader.app"
echo "Size: $APP_SIZE"
echo ""
echo "To run the app:"
echo "  open dist/VideoDownloader.app"
echo ""
echo "To codesign (optional):"
echo "  codesign -s -f dist/VideoDownloader.app"
echo ""
