# Kullanım kılavuzu

Komutu argümansız çalıştırınca kısa özet zaten ekrana gelir:

```bash
ai
```

## Üç kullanım şekli

**1. Soru sor** — cevabı yazar.

```bash
ai chmod 755 ne demek
ai apt ile snap arasındaki fark ne
ai systemd kullanıcı servisi nedir
```

**2. `-e` ile komut üret** — komutu gösterir, **sen onaylamadan çalıştırmaz**.

```bash
ai -e 8080 portunu hangi program dinliyor
ai -e bu klasörde en çok yer kaplayan 10 şeyi listele
ai -e rapor klasörünü tarih adıyla yedekle
```

Ekranda komut belirir, altında `çalıştır? [e/H]` sorusu çıkar. `e` + Enter çalıştırır,
başka her şey (veya sadece Enter) iptal eder. Komutu beğenmezsen Enter'a bas, hiçbir şey olmaz.

**2b. Sürekli oturum — `ai -i`**

Claude'daki gibi: sorarsın, komutu gösterir, onaylarsın, çalıştırır, çıktıyı gösterir
ve **çıktıyı modele okutur** — teşhisi model koyar, gerekiyorsa kendiliğinden bir
sonraki komutu önerir. Linux bilmene gerek kalmasın diye asıl mod bu.

```
$ ai -i
› mikrofonum çalışmıyor
  wpctl status
  çalıştır? [e/H] e
  ...
  pactl list sources short          <- ilkini okuyup kendisi karar verdi
  çalıştır? [e/H] e
  ...
alsa_input...hw_sofhdadsp_6__source RUNNING — mikrofon donanımsal olarak çalışıyor.
```

Bir istekte en fazla 5 komut zincirler; teşhis uzarsa "devam" diye tekrar sorarsın.
Sistemi değiştiren komut önerdiğinde de aynı onay sorulur, okumadan `e` deme.

```
$ ai -i
Sürekli oturum. Çıkmak için Ctrl-D veya 'q'.

› ubuntu sürümümü göster
  lsb_release -a
  çalıştır? [e/H] e
Description: Ubuntu 22.04.5 LTS

› peki çekirdek sürümü
  uname -r
  çalıştır? [e/H] e
6.12.110-0612110-generic
```

Soru sorarsan komut önermez, cevaplar:

```
› chmod 755 ne demek
chmod 755, dosyanın sahibine okuma+yazma+çalıştırma, diğerlerine okuma+çalıştırma verir.

› napıyorsun
Ubuntu 22.04 ortamında komut satırında yardımcı oluyorum. Sizin için ne yapabilirim?
```

Komut mu cevap mı olduğuna model karar veriyor: çalıştırılacak komutu `$ ` işaretiyle
gönderiyor, işaret yoksa düz cevap sayılıyor ve onay sorulmuyor.

`sudo` gereken komutlarda parolayı **ekranda sorar**, yazarsın, devam eder.
`htop`, `nano`, `watch`, `intel_gpu_top` gibi kendi ekranını yöneten programlar
doğrudan terminale açılır; diğerlerinin çıktısı yakalanıp modele geri verilir.

**3. Çıktıyı boruyla ver** — gerçek sayıları okuyup yorumlar.

```bash
free -h | ai belleğim yetiyor mu
df -h / | ai diskim doluyor mu
apt update 2>&1 | ai bu hata neden oldu
journalctl --user -u ai-npu -n 30 | ai servis neden çalışmıyor
make 2>&1 | tail -30 | ai derleme neden patladı
```

`2>&1` kısmı önemli: hata mesajları normalde boruya girmez, bu onları da aktarır.

## Tırnak ne zaman gerekir

Genelde gerekmez. Şu karakterler sorudaysa tek tırnak kullan: `' " \` $ ! ( ) ; | & > <`

```bash
ai '$PATH değişkeni ne işe yarar'
ai "bu ne demek: Permission denied"
```

## Tarayıcıdan kullanmak

Tarayıcı arayüzü **komut çalıştırmaz** — bu bilinçli. Sunucuya komut çalıştıran bir uç
eklemek, makinede dinleyen her şeyin ulaşabileceği bir kapı açardı. Arayüzdeki
"⧉ ilk satırı kopyala" düğmesiyle komutu alıp terminale yapıştırırsın; çalıştırmak
istediğinde `ai -i` kullan.

```
http://127.0.0.1:11435
```

Terminal yerine sohbet penceresi. Farkı: **geçmişi hatırlar** (son 6 mesaj),
ve alttaki kaydırıcılardan model davranışını değiştirebilirsin.

| ayar | ne yapar |
|---|---|
| sıcaklık | 0 = hep aynı cevap, kesin işler için doğrusu. Yükseldikçe çeşitlenir. **1,0 üstünde bu model bozuluyor**, Çince karakterler üretiyor |
| top_p | kelime havuzunun genişliği. Sıcaklık 0 iken etkisi yok |
| uzunluk | cevabın azami token sayısı. Uzun betik isteyeceksen yükselt |
| talimat | modelin kim olduğunu söyleyen metin. Değiştirip deneyebilirsin, tarayıcıda saklanır. **sıfırla** düğmesi sunucudaki güncel varsayılana döndürür |

"temizle" düğmesi geçmişi siler. Sayfayı kapatınca sohbet kaybolur, ayarlar kalır.

## GPU çalışıyor mu görmek

`gpu-izle` komutu, model cevap verirken iGPU'nun uyanıp uyanmadığını gösterir:

```
$ gpu-izle
  saat   uyanık                  Render  Blit  Video  VidEnh  HESAPLAMA
    0 MHz  %0                      0,00  0,00   0,00    0,00       0,00
 1540 MHz  %100 ####################  0,00  0,00   0,00    0,00      94,00   <- cevap üretiliyor
 1478 MHz  %100 ####################  0,00  0,00   0,00    0,00      95,00
    0 MHz  %0                      0,00  0,00   0,00    0,00       0,00
```

`gpu-izle -t` ham `intel_gpu_top` tablosunu açar.

**HESAPLAMA sütunu** `intel_gpu_top`'ta `[unknown]` diye geçer — Arrow Lake'in compute
motorunun adı bu sürümde tanımlı değil, ama yüzdesi doğru. Model cevap üretirken
%80-96'ya çıkar. `Render/Blit/Video` sıfırda kalır, onlar oyun ve video için.

Gereken: `sudo apt install -y intel-gpu-tools` ve bir kez şu ayar —
```
echo kernel.perf_event_paranoid=0 | sudo tee /etc/sysctl.d/60-perf.conf
sudo sysctl -p /etc/sysctl.d/60-perf.conf
```
(yoksa `sudo gpu-izle` diye çalıştır.)

**gnome-system-monitor GPU/NPU göstermez** — o pencerede öyle bir sekme yok, eksik
kurulum değil.

## Servis

Model arka planda açık durur, ilk soruda beklemezsin.

```bash
systemctl --user status ai-npu     # çalışıyor mu
systemctl --user restart ai-npu    # takılırsa
systemctl --user stop ai-npu       # belleği boşalt (7,9 GB RAM tutuyor)
systemctl --user start ai-npu
```

Bilgisayar açıldığında kendiliğinden başlar. İlk soru model belleğe yüklenirken
biraz uzun sürer, sonrakiler 2-3 saniye.

## Neye güvenilir, neye güvenilmez

**Güvenilir:** komut sözdizimi, parametre hatırlatma, hata mesajı çevirme,
kısa betik yazdırma, çıktıdaki sayıları okuma.

**Güvenilmez:**
- **Israr.** Tek atışlık modlarda (`ai <soru>`, `ai -e`) komut hata verdiğinde aynı komutu
  tekrar edebilir; hata metnini okumaz. **Teşhis için `ai -i` kullan** — orada çıktıyı
  modele geri veriyor, o okuyup sonraki adıma karar veriyor (aşağıdaki teşhis döngüsü).
- **Yargı cümleleri.** `df` çıktısına "Evet, diskiniz dolu. Kullanım %29, yani %71 boş"
  diyebiliyor — sayıyı doğru okuyup sonucu ters söylüyor. Sayılara bak, hükme bakma.
- **Güncel sürüm bilgisi.** İnterneti yok, bilgisi eskidir. Yeni paketleri bilmez.
- **Uzun metin.** Uzun logu `tail -30` ile kırp, yoksa hem yavaşlar hem dağılır.
- **Hafıza.** `ai -i` dışında her komut sıfırdan başlar; "az önce dediğin" diye devam
  edemezsin. Süreklilik isteyen her iş `-i` içinde yapılmalı.
- **Dosyaların.** Kendiliğinden dosya okuyamaz: `cat dosya | ai "..."` diye vereceksin.

`-e` modunun onay sorması bu yüzden var. Komutu okumadan `e` deme.

Cevapta geri dönüşü olmayan bir komut geçerse (silme, biçimlendirme, `reboot`,
`apt purge`) terminal sarı bir uyarı basar, tarayıcı arayüzü kırmızı şerit gösterir.
Uyarı komutu engellemez — kararı sen verirsin, ama farkında olmadan uygulamayasın diye.

## Bir şeyler ters giderse

| belirti | ne yap |
|---|---|
| `ai: sunucuya ulaşılamadı` | `systemctl --user start ai-npu` |
| İlk soru çok uzun sürüyor | Normal, model yükleniyor. Sonrakiler hızlı |
| Cevap alakasız | Soruyu kısalt, boruyla verdiğin metni `tail` ile kırp |
| `ai: command not found` | `export PATH=$HOME/.local/bin:$PATH` satırını `~/.bashrc`'ye ekle |
| Cevap yarıda kesiliyor | `AI_TOKEN=1200 ai -i` — akıl yürüten modellerde 400 token yetmez |
| Bellek lazım | `systemctl --user stop ai-npu` — 7,9 GB boşalır |
