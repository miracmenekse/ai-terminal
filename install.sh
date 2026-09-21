#!/usr/bin/env bash
# Yerel terminal asistanini kurar.  Kullanim:  ./install.sh [GPU|CPU|NPU]
# Tekrar calistirmak zararsiz: var olan venv ve modeli yeniden indirmez.
set -euo pipefail

DEVICE=${1:-GPU}
ROOT=$HOME/.local/share/ai-npu
# Model iki yerden secilir: burasi varsayilan, ${2} ile gecici olarak degistirilebilir.
# GPU/CPU varsayilani: Qwen3-Coder-30B-A3B (MoE, 3B aktif) - 16 GB indirme, ~15 GB RAM.
# Az bellekli makinede:  ./install.sh GPU llmware/qwen-2.5-coder-instruct-npu-ov  (4,1 GB)
# NPU channel-wise INT4 sart (-cw- / -npu-ov depolari), yani NPU'da ikinci komutu kullanin.
MODEL_REPO=${2:-OpenVINO/Qwen3-Coder-30B-A3B-Instruct-int4-ov}
MODEL=$ROOT/models/$(basename "$MODEL_REPO")
SRC=$(cd "$(dirname "$0")" && pwd)

# Intel compute runtime. Ubuntu 22.04'un kendi paketleri iGPU'yu OpenVINO'ya
# ACMIYOR; Intel'in deposu sart. libigdfcl1 pinlenmezse apt "tutulan bozuk
# paketler" diye reddediyor.
gpu_kur() {
    [ -f /usr/lib/x86_64-linux-gnu/libze_intel_gpu.so.1 ] && { echo "  iGPU surucusu zaten kurulu"; return 0; }
    echo "==> Intel iGPU surucusu kuruluyor (sudo gerekiyor)"
    sudo apt-get install -y -qq gpg-agent wget >/dev/null 2>&1 || true
    curl -fsSL https://repositories.intel.com/gpu/intel-graphics.key \
      | sudo gpg --yes --dearmor -o /usr/share/keyrings/intel-graphics.gpg || return 1
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/intel-graphics.gpg] https://repositories.intel.com/gpu/ubuntu jammy client" \
      | sudo tee /etc/apt/sources.list.d/intel-gpu-jammy.list >/dev/null
    printf 'Package: intel-opencl-icd libze-intel-gpu1 libze1 libigc1 libigdfcl1 libigdgmm12 intel-ocloc libigc-tools\nPin: origin repositories.intel.com\nPin-Priority: 1001\n\nPackage: *\nPin: origin repositories.intel.com\nPin-Priority: 100\n' \
      | sudo tee /etc/apt/preferences.d/intel-gpu >/dev/null
    sudo apt-get update -qq || return 1
    sudo apt-get install -y -qq --no-install-recommends \
      intel-opencl-icd libze-intel-gpu1 libze1 clinfo || return 1
    clinfo -l 2>/dev/null | grep -qi intel
}

# GPU istendiginde surucu kurulsa bile derleme patlayabilir (depoya erisilemedi,
# eski cekirdek, sanal makine). Tek token uretmeyi deneyip olmazsa CPU'ya duser.
probe_gpu() {
    # Modeli yuklemeyi denemiyorum: 30B'yi ikinci kez derlemek hem uzun suruyor
    # hem de servisin GPU belleğiyle cakisip yanlis negatif veriyordu.
    # Surucu dosyasi + OpenVINO'nun cihaz listesi yeterli isaret.
    [ -f /usr/lib/x86_64-linux-gnu/libze_intel_gpu.so.1 ] || { echo CPU; return; }
    "$ROOT/venv/bin/python" - 2>/dev/null <<'PROBE' || echo CPU
import openvino as ov
print("GPU" if "GPU" in ov.Core().available_devices else "CPU")
PROBE
}

echo "==> $DEVICE icin kuruluyor"
mkdir -p "$ROOT/models" "$HOME/.local/bin" "$HOME/.config/systemd/user"

# 1) Python ortami
if [ ! -x "$ROOT/venv/bin/python" ]; then
    python3 -m venv "$ROOT/venv"
    "$ROOT/venv/bin/pip" install -q --upgrade pip
fi
"$ROOT/venv/bin/python" -c 'import openvino_genai, huggingface_hub' 2>/dev/null ||
    "$ROOT/venv/bin/pip" install -q openvino-genai huggingface-hub

# 2) Model (birkac GB, sadece bir kez)
if [ ! -f "$MODEL/openvino_model.bin" ]; then
    echo "==> model indiriliyor: $MODEL_REPO"
    "$ROOT/venv/bin/python" - "$MODEL_REPO" "$MODEL" <<'PY'
import sys
from huggingface_hub import snapshot_download
snapshot_download(sys.argv[1], local_dir=sys.argv[2], max_workers=4)
PY
fi

# 3) GPU: surucu + gercek deneme. Olmazsa CPU'ya duser, kurulum yarida kalmaz.
if [ "$DEVICE" = GPU ]; then
    gpu_kur || echo "  !! surucu kurulamadi, GPU yine de denenecek"
    echo "==> GPU kontrol ediliyor"
    DEVICE=$(probe_gpu)
    [ "$DEVICE" = CPU ] && echo "  !! GPU kullanilamadi, CPU ile devam" || echo "  GPU calisiyor"
fi

# 4) NPU icin Level-Zero yukleyicisi (sudo istemez, .deb'i acar)
if [ "$DEVICE" = NPU ] && [ ! -f "$ROOT/lib/libze_loader.so.1" ]; then
    echo "==> Level-Zero yukleyicisi kuruluyor"
    tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
    deb=libze1_1.33.1+u22.04_amd64.deb
    curl -fsSL "https://github.com/oneapi-src/level-zero/releases/download/v1.33.1/$deb" -o "$tmp/$deb"
    ( cd "$tmp" && ar x "$deb" && tar -xf data.tar.* )
    mkdir -p "$ROOT/lib" && cp -a "$tmp"/usr/lib/x86_64-linux-gnu/. "$ROOT/lib/"
fi

# 5) Dosyalar
install -m 755 "$SRC/server.py" "$ROOT/server.py"
install -m 644 "$SRC/chat.html" "$ROOT/chat.html"
install -m 644 "$SRC/sik-kullanilanlar.md" "$ROOT/sik-kullanilanlar.md"
install -m 755 "$SRC/bin/ai" "$HOME/.local/bin/ai"
install -m 755 "$SRC/bin/gpu-izle" "$HOME/.local/bin/gpu-izle"
sed -e "s/^Environment=AI_NPU_DEVICE=.*/Environment=AI_NPU_DEVICE=$DEVICE/" \
    -e "s|^Environment=AI_NPU_MODEL=.*|Environment=AI_NPU_MODEL=$MODEL|" \
    "$SRC/ai-npu.service" > "$HOME/.config/systemd/user/ai-npu.service"

# 6) Servis
systemctl --user daemon-reload
systemctl --user enable --now ai-npu

# 7) Kontrol
"$ROOT/venv/bin/python" "$ROOT/server.py" test
for _ in $(seq 30); do ss -ltn 2>/dev/null | grep -q 11435 && break; sleep 2; done
echo "==> deneme sorusu:"
"$HOME/.local/bin/ai" -e disk doluluk oranini goster </dev/null || true

case ":$PATH:" in *":$HOME/.local/bin:"*) ;;
  *) echo "!! ~/.local/bin PATH'te degil:  echo 'export PATH=\$HOME/.local/bin:\$PATH' >> ~/.bashrc" ;;
esac
if [ "$DEVICE" != GPU ] && [ "${1:-GPU}" = GPU ]; then
cat <<'MSG'

!! GPU acilamadi. Elle denemek icin (bir kez, root):
     curl -fsSL https://repositories.intel.com/gpu/intel-graphics.key \
       | sudo gpg --yes --dearmor -o /usr/share/keyrings/intel-graphics.gpg
     echo "deb [arch=amd64 signed-by=/usr/share/keyrings/intel-graphics.gpg] \
https://repositories.intel.com/gpu/ubuntu jammy client" \
       | sudo tee /etc/apt/sources.list.d/intel-gpu-jammy.list
     # Ubuntu'nun 2022 tarihli libigdfcl1'i yerine Intel'inki gelsin diye pin sart,
     # pin olmadan apt "tutulan bozuk paketler" diye reddeder:
     printf 'Package: intel-opencl-icd libze-intel-gpu1 libze1 libigc1 libigdfcl1 libigdgmm12 intel-ocloc libigc-tools\nPin: origin repositories.intel.com\nPin-Priority: 1001\n\nPackage: *\nPin: origin repositories.intel.com\nPin-Priority: 100\n' \
       | sudo tee /etc/apt/preferences.d/intel-gpu
     sudo apt update && sudo apt install -y --no-install-recommends \
       intel-opencl-icd libze-intel-gpu1 libze1 clinfo
   Dogrulama:  clinfo -l    (Intel(R) Graphics gorunmeli)
MSG
fi
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
