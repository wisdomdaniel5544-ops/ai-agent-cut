#!/usr/bin/env bash
# Cross-builds the Windows installer on Linux: official embeddable CPython 3.12 + win_amd64 wheels + ffmpeg + models, packed with NSIS.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd); APP=$(cd "$HERE/../.." && pwd)
B=${BUILD:-/opt/build}; ST=$B/stage; OUT=${OUT:-$APP/dist}; VER=${VERSION:-2.0.0}; MODEL=${MODEL:-small}
mkdir -p "$B" "$OUT"; cd "$B"
[ -f pyembed.zip ] || curl -sSL -o pyembed.zip https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip
[ -f ffmpeg-win.zip ] || curl -sSL -o ffmpeg-win.zip https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip
pip download -q --only-binary=:all: --platform win_amd64 --python-version 3.12 --implementation cp -d wheels \
  faster-whisper opencv-python-headless numpy fastapi uvicorn python-multipart yt-dlp pillow mcp
rm -rf "$ST"; mkdir -p "$ST/python/Lib/site-packages" "$ST/app" "$ST/ffmpeg" "$ST/models"
unzip -q pyembed.zip -d "$ST/python"
printf 'python312.zip\n.\nLib\\site-packages\n..\\app\nimport site\n' > "$ST/python/python312._pth"
for w in wheels/*.whl; do unzip -q -o "$w" -d "$ST/python/Lib/site-packages"; done
unzip -q -j -o ffmpeg-win.zip '*/bin/ffmpeg.exe' '*/bin/ffprobe.exe' -d "$ST/ffmpeg"
cp -r "$APP/aiagentcut" "$APP/web" "$ST/app/"; find "$ST/app" -name __pycache__ -prune -exec rm -rf {} +
cp "$APP/models/face_detection_yunet_2023mar.onnx" "$ST/models/"
SNAP=$(ls -d ~/.cache/huggingface/hub/models--Systran--faster-whisper-$MODEL/snapshots/*/ | head -1)
mkdir -p "$ST/models/faster-whisper-$MODEL"; cp -L "$SNAP"/* "$ST/models/faster-whisper-$MODEL/"
cp "$HERE/launcher.pyw" "$ST/"; cp "$HERE/app.ico" "$ST/"
cp "$APP/LICENSE-NOTICES.txt" "$ST/" 2>/dev/null || true
cp "$HERE/app.ico" "$B/"
makensis -V2 -DSTAGE="$ST" -DOUTDIR="$OUT" -DVERSION="$VER" "-X!cd $HERE" "$HERE/installer.nsi"
ls -la "$OUT"
