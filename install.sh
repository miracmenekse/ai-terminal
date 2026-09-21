#!/usr/bin/env bash
# Yerel terminal asistanini kurar.  Kullanim:  ./install.sh [CPU|NPU]
# Tekrar calistirmak zararsiz: var olan venv ve modeli yeniden indirmez.
set -euo pipefail

DEVICE=${1:-CPU}
ROOT=$HOME/.local/share/ai-npu
MODEL_REPO=llmware/qwen-2.5-coder-instruct-npu-ov
MODEL=$ROOT/models/qwen25-coder-npu
SRC=$(cd "$(dirname "$0")" && pwd)

echo "==> $DEVICE icin kuruluyor"
mkdir -p "$ROOT/models" "$HOME/.local/bin" "$HOME/.config/systemd/user"

# 1) Python ortami
if [ ! -x "$ROOT/venv/bin/python" ]; then
    python3 -m venv "$ROOT/venv"
    "$ROOT/venv/bin/pip" install -q --upgrade pip
fi
"$ROOT/venv/bin/python" -c 'import openvino_genai, huggingface_hub' 2>/dev/null ||
    "$ROOT/venv/bin/pip" install -q openvino-genai huggingface-hub

# 2) Model (4.1 GB, sadece bir kez)
if [ ! -f "$MODEL/openvino_model.bin" ]; then
    echo "==> model indiriliyor, 4.1 GB"
    "$ROOT/venv/bin/python" - "$MODEL_REPO" "$MODEL" <<'PY'
import sys
from huggingface_hub import snapshot_download
snapshot_download(sys.argv[1], local_dir=sys.argv[2], max_workers=4)
PY
fi

# 3) NPU icin Level-Zero yukleyicisi (sudo istemez, .deb'i acar)
if [ "$DEVICE" = NPU ] && [ ! -f "$ROOT/lib/libze_loader.so.1" ]; then
    echo "==> Level-Zero yukleyicisi kuruluyor"
    tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
    deb=libze1_1.33.1+u22.04_amd64.deb
    curl -fsSL "https://github.com/oneapi-src/level-zero/releases/download/v1.33.1/$deb" -o "$tmp/$deb"
    ( cd "$tmp" && ar x "$deb" && tar -xf data.tar.* )
    mkdir -p "$ROOT/lib" && cp -a "$tmp"/usr/lib/x86_64-linux-gnu/. "$ROOT/lib/"
fi

# 4) Dosyalar
install -m 755 "$SRC/server.py" "$ROOT/server.py"
install -m 644 "$SRC/chat.html" "$ROOT/chat.html"
install -m 755 "$SRC/bin/ai" "$HOME/.local/bin/ai"
sed "s/^Environment=AI_NPU_DEVICE=.*/Environment=AI_NPU_DEVICE=$DEVICE/" \
    "$SRC/ai-npu.service" > "$HOME/.config/systemd/user/ai-npu.service"

# 5) Servis
systemctl --user daemon-reload
systemctl --user enable --now ai-npu

# 6) Kontrol
"$ROOT/venv/bin/python" "$ROOT/server.py" test
for _ in $(seq 30); do ss -ltn 2>/dev/null | grep -q 11435 && break; sleep 2; done
echo "==> deneme sorusu:"
"$HOME/.local/bin/ai" -e disk doluluk oranini goster </dev/null || true

case ":$PATH:" in *":$HOME/.local/bin:"*) ;;
  *) echo "!! ~/.local/bin PATH'te degil:  echo 'export PATH=\$HOME/.local/bin:\$PATH' >> ~/.bashrc" ;;
esac
if [ "$DEVICE" = NPU ]; then
cat <<'MSG'

!! NPU icin ayrica root gerekiyor (bir kez):
     sudo apt install -y libtbb12
     https://github.com/intel/linux-npu-driver/releases adresinden .deb'leri kurun
     sudo usermod -aG render $USER     # sonra cikis yapip tekrar girin
   `render` grubu yoksa OpenVINO bunu "libopenvino_intel_npu_compiler_loader.so
   bulunamadi" diye yanlis raporlar.
MSG
fi
