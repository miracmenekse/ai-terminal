#!/usr/bin/env bash
# Yerel terminal asistanini kurar.
#   ./install.sh          -> cihazi kendi secer (GPU varsa GPU, yoksa CPU)
#   ./install.sh GPU|CPU|NPU
# Tekrar calistirmak zararsiz: var olan venv ve modeli yeniden indirmez.
set -euo pipefail

DEVICE=${1:-auto}
ROOT=$HOME/.local/share/ai-npu
MODEL_REPO=llmware/qwen-2.5-coder-instruct-npu-ov
MODEL=$ROOT/models/qwen25-coder-npu
SRC=$(cd "$(dirname "$0")" && pwd)
PY=$ROOT/venv/bin/python

echo "==> hedef cihaz: $DEVICE"
mkdir -p "$ROOT/models" "$HOME/.local/bin" "$HOME/.config/systemd/user"

# 1) Python ortami
if [ ! -x "$PY" ]; then
    python3 -m venv "$ROOT/venv"
    "$ROOT/venv/bin/pip" install -q --upgrade pip
fi
"$PY" -c 'import openvino_genai, huggingface_hub' 2>/dev/null ||
    "$ROOT/venv/bin/pip" install -q openvino-genai huggingface-hub

# 2) Model (4.1 GB, sadece bir kez)
if [ ! -f "$MODEL/openvino_model.bin" ]; then
    echo "==> model indiriliyor, 4.1 GB"
    "$PY" - "$MODEL_REPO" "$MODEL" <<'PY'
import sys
from huggingface_hub import snapshot_download
snapshot_download(sys.argv[1], local_dir=sys.argv[2], max_workers=4)
PY
fi

# 3) iGPU surucusu. Ubuntu 22.04'un kendi paketleri BU ISI GORMEZ; Intel'in
#    kendi deposu gerekiyor (intel-opencl-icd 24.x + libze-intel-gpu1).
#    Bunlar olmadan OpenVINO GPU'yu hic gormez.
gpu_kur() {
    [ -f /usr/lib/x86_64-linux-gnu/libze_intel_gpu.so.1 ] && { echo "  iGPU surucusu zaten kurulu"; return 0; }
    echo "==> Intel iGPU surucusu kuruluyor (sudo gerekiyor)"
    sudo apt-get install -y -qq gpg-agent wget >/dev/null
    wget -qO- https://repositories.intel.com/gpu/intel-graphics.key \
      | sudo gpg --yes --dearmor -o /usr/share/keyrings/intel-graphics.gpg
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/intel-graphics.gpg] https://repositories.intel.com/gpu/ubuntu jammy client" \
      | sudo tee /etc/apt/sources.list.d/intel-gpu-jammy.list >/dev/null
    sudo apt-get update -qq
    sudo apt-get install -y -qq intel-opencl-icd libze-intel-gpu1 libze1 clinfo || return 1
    sudo usermod -aG render "$USER" || true
}

# 4) NPU icin Level-Zero yukleyicisi (sudo istemez, .deb'i acar)
npu_kur() {
    [ -f "$ROOT/lib/libze_loader.so.1" ] && return 0
    local tmp deb=libze1_1.33.1+u22.04_amd64.deb
    tmp=$(mktemp -d); trap 'rm -rf "$tmp"' RETURN
    curl -fsSL "https://github.com/oneapi-src/level-zero/releases/download/v1.33.1/$deb" -o "$tmp/$deb"
    ( cd "$tmp" && ar x "$deb" && tar -xf data.tar.* )
    mkdir -p "$ROOT/lib" && cp -a "$tmp"/usr/lib/x86_64-linux-gnu/. "$ROOT/lib/"
}

# 5) Cihaz secimi. "available_devices" GPU yazmasi yetmiyor, gercekten derleyip
#    tek token uretmeyi deniyorum; olmazsa CPU'ya duser.
probe() {
    LD_LIBRARY_PATH=$ROOT/lib "$PY" - "$MODEL" <<'PY' 2>/dev/null || echo CPU
import sys, openvino_genai as og
try:
    p = og.LLMPipeline(sys.argv[1], "GPU")
    c = og.GenerationConfig(); c.max_new_tokens = 1; c.do_sample = False
    p.generate("merhaba", c)
    print("GPU")
except Exception:
    print("CPU")
PY
}

case "$DEVICE" in
  auto) gpu_kur || true
        echo "==> cihaz deneniyor (model derlenecek, biraz surer)"
        DEVICE=$(probe); echo "==> secilen: $DEVICE" ;;
  GPU)  gpu_kur || { echo "!! iGPU surucusu kurulamadi, CPU'ya duyuluyor"; DEVICE=CPU; } ;;
  NPU)  npu_kur ;;
esac

# 6) Dosyalar
install -m 755 "$SRC/server.py" "$ROOT/server.py"
install -m 644 "$SRC/chat.html" "$ROOT/chat.html"
install -m 755 "$SRC/bin/ai" "$HOME/.local/bin/ai"
sed "s/^Environment=AI_NPU_DEVICE=.*/Environment=AI_NPU_DEVICE=$DEVICE/" \
    "$SRC/ai-npu.service" > "$HOME/.config/systemd/user/ai-npu.service"

# 7) Servis
systemctl --user daemon-reload
systemctl --user enable ai-npu >/dev/null 2>&1 || true
systemctl --user restart ai-npu

# 8) Kontrol
"$PY" "$ROOT/server.py" test
for _ in $(seq 40); do ss -ltn 2>/dev/null | grep -q 11435 && break; sleep 2; done
echo "==> deneme sorusu:"
"$HOME/.local/bin/ai" -e disk doluluk oranini goster </dev/null || true
echo "==> tarayici arayuzu: http://127.0.0.1:11435"

case ":$PATH:" in *":$HOME/.local/bin:"*) ;;
  *) echo "!! ~/.local/bin PATH'te degil:  echo 'export PATH=\$HOME/.local/bin:\$PATH' >> ~/.bashrc" ;;
esac
# /dev/dri erisimi ACL ile geliyor; render grubu genelde gerekmiyor, sadece
# erisim gercekten yoksa uyar.
if [ "$DEVICE" = GPU ] && ! [ -r /dev/dri/renderD128 ]; then
    echo "!! /dev/dri/renderD128 okunamiyor - 'render' grubuna eklendin, CIKIS YAPIP TEKRAR GIR"
fi
if [ "$DEVICE" = NPU ]; then
    echo "!! NPU icin ayrica: sudo apt install -y libtbb12, Intel NPU surucu .deb'leri, render grubu"
fi
exit 0
