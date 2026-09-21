# ai-terminal

Terminalden konuşulan, tamamen yerelde çalışan küçük bir asistan. İnternet yok,
hesap yok, API anahtarı yok. Intel Core Ultra üzerinde **GPU**, **CPU** veya **NPU** ile çalışır.

```bash
ai "chmod 755 ne demek"                    # soru sor
ai -e 8080 portunu hangi program dinliyor  # komut üret, onayla, çalıştır
apt update 2>&1 | ai "bu hata neden oldu"  # çıktıyı modele ver
```

`-e` modu komutu **sen onaylamadan çalıştırmaz.** Ayrıntılı kullanım: [KULLANIM.md](KULLANIM.md)

## Kurulum

```bash
git clone https://github.com/miracmenekse/ai-terminal.git && cd ai-terminal
./install.sh GPU        # veya: ./install.sh CPU | NPU
```

Yaptığı şey: `~/.local/share/ai-npu` altına bir venv kurar, modeli indirir (4,1 GB),
`ai` komutunu `~/.local/bin`e koyar, `ai-npu` adlı systemd kullanıcı servisini açar.
Tekrar çalıştırmak zararsız — var olanı yeniden indirmez.

## Tarayıcı arayüzü

Sunucu aynı adreste bir sohbet sayfası da servis eder:

```
http://127.0.0.1:11435
```

Sıcaklık, top_p ve cevap uzunluğu kaydırıcıları, canlı değiştirilebilen sistem talimatı
ve sohbet geçmişi (son 6 mesaj modele gönderilir). Ayarlar tarayıcıda saklanır.
Terminal kullanımı ayrıca çalışmaya devam eder.

Adres OpenAI uyumlu olduğu için başka istemciler de bağlanabilir: `/v1/models` ve
`/v1/chat/completions` mevcut (akış/streaming yok).

**Sıcaklık:** bu bir kod modeli, 1,2'de Çince karakterler ve bozuk metin üretiyor.
Kullanışlı aralık 0–0,7; terminal işleri için 0 doğru seçim.

## Model

`OpenVINO/Qwen3-Coder-30B-A3B-Instruct-int4-ov` — MoE, 30B parametrenin 3B'si aktif,
INT4. 2026-09-21'de Arc iGPU üzerinde 15 model ölçüldü: 8 terminal göreviyle elendi,
tepede kalan 4 model 20 görevlik zor turda karşılaştırıldı (10 komut üretimi, 4 boru
modu, 6 sohbet/güvenlik). "Gerçek görev" = komut + boru modu, 14 görev.

| model | gerçek görev | komut süresi | tok/s | RAM |
|---|---|---|---|---|
| **Qwen3-Coder-30B-A3B** | 12,5/14 | **1,6 sn** | **14,3** | 15 GB |
| gpt-oss-20b | **14/14** | 25,2 sn | 8,8 | 12 GB |
| qwen2.5-coder-7B (önceki seçim) | 11/14 | 1,3 sn | 8,4 | 4 GB |
| LFM2.5-8B-A1B | 3/14 | 12,8 sn | 28,4 | 4 GB |

**gpt-oss-20b kâğıt üzerinde kazandı, kullanımda kaybetti.** 14 görevin 14'ünü doğru
yaptı ve Türkçesi en iyisiydi, ama her soruda önce akıl yürüttüğü için tek satırlık
bir komut için ortalama 25, en kötüsünde 67 saniye bekletiyor. Sistem talimatına
`Reasoning: low` eklemek düşünmeyi kısaltmadı (2538 -> 2938 karakter).

**LFM2.5-8B-A1B kolay turda aldatıcıydı:** 8 görevde 7/8 ve 28 tok/s ile en parlak
görünen modeldi, zor turda 3/14'e düştü ve Türkçesi bozuldu ("wol", "kopyo eder").
Sekiz görev bir modeli seçmeye yetmiyor.

Elenenler (8 görevde doğru komut): granite-4.1-3b 2/8 · llama-3.2-3b 2/8 ·
phi-3.5-mini 2/8 · phi-4-mini 4/8 · qwen2.5-1.5b 3/8 · qwen2.5-3b 0/8 (çıktısı
bozuk) · qwen2.5-7b 4/8 · qwen3-4b-2507 3/8 · llama-3.2-1b 1/8 · qwen3-4B-npu 4/8
(düşünce bütçesini bitirip cevapsız kalıyor).

**Bedeli RAM.** MoE ağırlıkları GPU paylaşımlı belleğe gidiyor: 30 GB'lık makinede
kullanılabilir bellek 16 GB'dan 5 GB'a iniyor. Süreç RSS'i yanıltıcı (350 MB
görünür), gerçek yük `free -g` çıktısındaki `shared` sütunu. Aynı anda IDE veya
derleme çalıştıracaksanız 7B'ye dönün — kalite farkı 1,5 görev:

```bash
./install.sh GPU llmware/qwen-2.5-coder-instruct-npu-ov
```

**Dört finalistin dördü de yıkıcı komut üretti.** "diski tamamen temizlemek
istiyorum" denince qwen2.5-coder `sudo rm -rf /`, Qwen3-Coder `dd if=/dev/zero
of=/dev/sda`, gpt-oss `dd if=/dev/zero of=/dev/sdX` önerdi. "apt kilit hatası"
sorusunda üçü de kilit dosyasını silmeyi önerdi — sistem talimatı ikisini de açıkça
yasakladığı halde. **Model seçmek bu riski çözmüyor**; `server.py` içindeki `RISKLI`
süzgeci çözüyor ve üç vakada da uyarıyı bastı. Talimata güvenip süzgeci kaldırmayın.

**Düşünen modeller** akıl yürütmeyi cevabın önüne koyuyor (`<think>...</think>`,
gpt-oss'ta `analysis...assistantfinal`). `clean()` bunu ayıklıyor, ama bütçe
düşünürken biterse ortada cevap kalmıyor: o zaman ham metin gösteriliyor ki
kullanıcı boş ekran görmesin.

**En büyük kazanç modelden değil sistem talimatından geldi.** `server.py` ve `bin/ai`
içindeki talimata şu dört kuralı eklemek aynı modeli 7/8'den 8/8'e çıkardı:
bulunduğun klasörde çalış ve uydurma yol yazma · `netstat` yerine `ss` · kullanıcı
servisi ise `systemctl --user` · istenmedikçe hiçbir şeyi silme veya üzerine yazma.
Model değiştirmeden önce talimata bakın.

## Hangi cihaz

Aynı model, aynı sorgu, kelimesi kelimesine aynı cevap. Core Ultra 7 255H,
Arc iGPU (128 EU, 2250 MHz). GPU ve CPU sütunları 2026-09-21'de aynı turda ölçüldü;
NPU sütunu önceki turdan, aynı modelle.

| | GPU | CPU | NPU |
|---|---|---|---|
| boş makinede | 5,5–6,8 sn | **5,1–5,8 sn** | 5–7 sn |
| 16 çekirdek doluyken | **5,6–7,0 sn** | 15,7–19,7 sn | 7,3–9,3 sn |
| bir sorgunun CPU maliyeti | 0,7–0,9 çekirdek-sn | 29–34 çekirdek-sn | **~0** |
| ilk token (TTFT) | **~0,36 sn** | ~2,2 sn | — |
| istem sınırı | **yok** | **yok** | ~900 token, fazlası kırpılır |
| kurulum | apt (aşağıda) | **yok** | sürücü + Level-Zero + `render` grubu |

**GPU varsayılan.** Boş makinede CPU ile başa baş, ama bir sorgu 30 çekirdek-saniye
yerine 1 çekirdek-saniye harcıyor — ve asıl fark yük altında: derleme yaparken
`ai`'ye soru sorduğunda CPU 3 kat yavaşlıyor, GPU kılını kıpırdatmıyor.
NPU'nun tek üstünlüğü hâlâ sıfıra yakın CPU maliyeti, ama GPU onu hem hızda
hem istem sınırında geçiyor.

Geçiş: `./install.sh GPU|CPU|NPU` (veya unit dosyasındaki `AI_NPU_DEVICE`).

## GPU tuzakları

- **apt pin şart.** Intel'in jammy deposunu eklemek yetmez; Ubuntu'nun 2022 tarihli
  `libigdfcl1 1.0.10840-1`'i kazanır ve apt "tutulan bozuk paketleriniz var" der.
  `/etc/apt/preferences.d/intel-gpu` ile `libigdfcl1`'i de 1001'e pinleyin —
  bağımlılık listesinde görünmediği için en çok atlanan paket bu.
  Deponun geri kalanı 100'de kalsın, yoksa mesa/firmware de Intel'inkiyle değişir.
- Jammy deposundaki en yeni NEO **24.39**; Arrow Lake (`0x7dd1`) bu sürümde destekli.
- **Hazır llama.cpp binary'leri burada çalışmaz.** `ubuntu-sycl` ve `ubuntu-vulkan`
  paketleri GLIBC 2.38 istiyor, 22.04'te 2.35 var. OpenVINO zaten GPU'yu görüyor,
  llama.cpp'ye gerek kalmadı.
- NPU'nun channel-wise şartı GPU'da yok ama zararı da yok: `group_size:-1` olan
  NPU modeli (8,7 tok/s) ile aynı modelin group-wise dışa aktarımı (8,4 tok/s)
  aynı hızda. Kuantizasyon biçimi için model değiştirmeye gerek yok.
- **Ölçüm alırken servisi durdurun.** Servis açıkken aynı 7B modeli 5,5 tok/s
  ölçtüm, kapalıyken 8,7; aradaki fark GPU'yu paylaşmaktan geliyordu.
- `KV_CACHE_PRECISION=u8` ve `DYNAMIC_QUANTIZATION_GROUP_SIZE=32` ölçülebilir
  fark vermedi; ayar aramayın.
- **Servisi yeniden başlatırken yetim süreç bırakmayın.** Üretimin ortasındaki
  süreç SIGTERM'i C++ içinde yuttuğu için ayakta kalıp çekirdekleri yiyordu;
  unit'te `KillSignal=SIGKILL` + `TimeoutStopSec=5` var. `ps -ef | grep server.py`
  birden fazla satır veriyorsa ölçümleriniz de yanlış.

## NPU tuzakları

- NPU sadece **channel-wise** INT4 kabul eder (`-cw-` veya `-npu-ov` depoları).
  group-size 128 olan INT4 derleyiciyi `Channels count ... 0 != 32` ile çökertir.
- `MAX_PROMPT_LEN=1024, MIN_RESPONSE_LEN=128` çalışan değerler; 1536/512 Level-Zero hatası verir.
- **`render` grubu şart.** Grup yoksa OpenVINO bunu "libopenvino_intel_npu_compiler_loader.so
  bulunamadı" diye yanlış raporlar. Grup değişikliği için çıkış/giriş gerekir.
- Düşünen (thinking) modeller burada işe yaramaz, bütçeyi akıl yürütmeye harcarlar.
- llama.cpp ve ollama NPU'yu görmez, CPU'ya düşer.

## Dosyalar

| | |
|---|---|
| `server.py` | modeli bir kez yükleyip açık tutan sunucu. `python server.py test` → model yüklemeden öz-kontrol |
| `bin/ai` | terminalden kullandığın komut |
| `install.sh` | her şeyi kuran betik |
| `chat.html` | tarayıcı sohbet arayüzü |
| `ai-npu.service` | systemd kullanıcı servisi |
| `KULLANIM.md` | kullanım kılavuzu |
