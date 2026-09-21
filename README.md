# ai-terminal

Terminalden konuşulan, tamamen yerelde çalışan küçük bir asistan. İnternet yok,
hesap yok, API anahtarı yok. Intel Core Ultra üzerinde **CPU** veya **NPU** ile çalışır.

```bash
ai "chmod 755 ne demek"                    # soru sor
ai -e 8080 portunu hangi program dinliyor  # komut üret, onayla, çalıştır
apt update 2>&1 | ai "bu hata neden oldu"  # çıktıyı modele ver
```

`-e` modu komutu **sen onaylamadan çalıştırmaz.** Ayrıntılı kullanım: [KULLANIM.md](KULLANIM.md)

## Kurulum

```bash
git clone https://github.com/miracmenekse/ai-terminal.git && cd ai-terminal
./install.sh CPU        # veya: ./install.sh NPU
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

`llmware/qwen-2.5-coder-instruct-npu-ov` (Qwen2.5-Coder 7B, INT4). 11 aday NPU'da
ölçüldü, 8 terminal görevinde doğru komut sayısı:

| model | doğru | not |
|---|---|---|
| **qwen2.5-coder 7B** | **8/8** | seçilen |
| qwen3-4b-instruct-2507 | 5/8 | olmayan parametre uyduruyor |
| qwen2.5-1.5b | 5/8 | en hızlısı |
| granite-4.1-3b-code | 4/8 | derlemesi 201 sn |
| qwen2.5-7b (genel) | 3/8 | çıktısı bozuk |
| phi-4-mini, qwen2.5-3b | 2/8 | istenmeden `rm` / `shred` üretti |
| llama-3.2 1B ve 3B, phi-3.5-mini | 0–2/8 | Türkçesi kullanılamaz |

**En büyük kazanç modelden değil sistem talimatından geldi.** `server.py` ve `bin/ai`
içindeki talimata şu dört kuralı eklemek aynı modeli 7/8'den 8/8'e çıkardı:
bulunduğun klasörde çalış ve uydurma yol yazma · `netstat` yerine `ss` · kullanıcı
servisi ise `systemctl --user` · istenmedikçe hiçbir şeyi silme veya üzerine yazma.
Model değiştirmeden önce talimata bakın.

## CPU mu NPU mu

Aynı model, aynı sorular, kelimesi kelimesine aynı cevaplar. Ölçüm: Core Ultra 7 255H.

| | NPU | CPU |
|---|---|---|
| boş makinede | 5–7 sn | **1,7–3,5 sn** |
| 16 çekirdek doluyken | 7,3–9,3 sn | **2–11,3 sn** |
| çalışırken CPU maliyeti | **~0 çekirdek** | 5,3 çekirdek |
| istem sınırı | ~900 token, fazlası kırpılır | **sınır yok** |
| kurulum | sürücü + Level-Zero + `render` grubu | **yok** |

CPU varsayılan: daha hızlı ve kurulum istemiyor. NPU'nun üstünlüğü hızda değil,
makineyi boş bırakmasında — uzun üretimde veya model sürekli arka planda çalışacaksa anlamlı.

Geçiş: `./install.sh NPU` (veya unit dosyasındaki `AI_NPU_DEVICE`).

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
