# Sık kullanılanlar

Ubuntu 22.04 · bu makine. `ai help <kelime>` ile tek bölüm getirilir:
`ai help ses`, `ai help paket`, `ai help disk`.

`[kurulu değil]` yazan araçlar bu makinede yok, yanındaki komutla kurulur.

## paket — uygulama kurma, kaldırma, arama

    sudo apt update                 # paket listesini tazele (kurulumdan önce)
    sudo apt install vlc            # kur
    sudo apt remove vlc             # kaldır (ayarları bırakır)
    sudo apt purge vlc              # kaldır + ayarlarını da sil
    sudo apt upgrade                # kurulu her şeyi güncelle
    apt search pdf                  # adında/açıklamasında geçenleri ara
    apt show vlc                    # sürüm, boyut, bağımlılık
    apt list --installed            # kurulu olanların listesi
    dpkg -l | grep vlc              # kurulu mu, hangi sürüm
    sudo dpkg -i dosya.deb          # indirdiğin .deb'i kur
    sudo apt install -f             # bozuk bağımlılığı onar

    snap list                       # snap ile kurulular
    sudo snap install spotify       # snap'ten kur
    sudo snap remove spotify

`apt` ile `snap` farkı: `apt` Ubuntu deposundan, sisteme entegre, küçük.
`snap` kendi içinde paketli, daha güncel ama daha ağır ve yavaş açılır.

## dosya — gezinme, kopyalama, taşıma, silme

    pwd                             # neredeyim
    ls -la                          # gizliler dahil, ayrıntılı listele
    ls -lt                          # en yeniden eskiye sırala
    cd /yol/klasor                  # klasöre gir      cd ..  üst klasör    cd ~  ev
    cp dosya.txt yedek.txt          # kopyala
    cp -r klasor/ hedef/            # klasörü kopyala
    mv eski.txt yeni.txt            # taşı veya yeniden adlandır
    rm dosya.txt                    # sil (çöp kutusu YOK, geri gelmez)
    rm -r klasor/                   # klasörü içeriğiyle sil
    mkdir -p a/b/c                  # iç içe klasör oluştur
    touch dosya.txt                 # boş dosya oluştur
    xdg-open dosya.pdf              # varsayılan programla aç
    realpath dosya.txt              # tam yolunu yaz

Silmeden önce `ls` ile ne sileceğini gör. `rm` geri alınamaz.

## ara — dosya ve metin arama

    find . -name "*.log"            # bu klasör ve altında ada göre
    find . -size +100M              # 100 MB'dan büyükler
    find . -mtime -1                # son 24 saatte değişenler
    grep "hata" dosya.log           # dosya içinde kelime ara
    grep -r "hata" .                # klasör ağacında ara
    grep -i "hata" -n dosya.log     # büyük/küçük harf ayırmadan, satır numaralı
    locate dosya.txt                # hızlı ara (önce: sudo updatedb)

## metin — dosya içeriğini görme ve değiştirme

    cat dosya.txt                   # tamamını bas
    less dosya.txt                  # sayfa sayfa oku (q ile çık, / ile ara)
    head -20 dosya.txt              # ilk 20 satır
    tail -20 dosya.txt              # son 20 satır
    tail -f /var/log/syslog         # canlı takip et (Ctrl-C ile çık)
    wc -l dosya.txt                 # satır say
    nano dosya.txt                  # düzenle (Ctrl-O kaydet, Ctrl-X çık)
    sed -i 's/eski/yeni/g' dosya    # dosyadaki her "eski"yi "yeni" yap
    sort dosya.txt | uniq           # sırala, tekrarları at

## disk — yer durumu

    df -h                           # bölümlerin doluluk oranı
    du -sh *                        # bu klasördeki her şeyin boyutu
    du -sh * | sort -hr | head -10  # en çok yer kaplayan 10 şey
    lsblk                           # diskler ve bölümler
    sudo apt clean                  # indirilmiş paket önbelleğini boşalt
    journalctl --vacuum-time=7d     # 7 günden eski sistem günlüklerini sil

## süreç — çalışan programlar

    ps aux | grep firefox           # bir programı bul
    ps -eo pid,pcpu,pmem,comm --sort=-pmem | head   # en çok RAM yiyen 10
    top                             # canlı izle (q ile çık)
    kill 1234                       # PID ile kapat (nazikçe)
    kill -9 1234                    # zorla kapat (son çare)
    pkill firefox                   # ada göre kapat
    free -h                         # bellek durumu
    uptime                          # ne kadardır açık, yük ortalaması

    sudo apt install htop           # [kurulu değil] top'un okunaklı hâli

## servis — arka planda çalışanlar

Sistem servisleri (bluetooth, ağ, ssh) `sudo` ister:

    systemctl status bluetooth --no-pager
    sudo systemctl restart bluetooth
    sudo systemctl enable  bluetooth    # açılışta başlasın
    sudo systemctl disable bluetooth
    journalctl -u bluetooth -n 50       # son 50 günlük satırı

Kullanıcı servisleri (`~/.config/systemd/user` altındakiler) `--user` ister
ve **asla `sudo` ile birlikte kullanılmaz**:

    systemctl --user status ai-npu --no-pager
    systemctl --user restart ai-npu
    journalctl --user -u ai-npu -n 50

## ağ — bağlantı ve portlar

    nmcli device status             # arayüzler ve bağlı olup olmadıkları
    nmcli device wifi list          # görünen wifi ağları
    nmcli device wifi connect "AğAdı" password "parola"
    ip -brief addr                  # IP adreslerim
    ping -c 4 1.1.1.1               # internet var mı (IP ile)
    ping -c 4 google.com            # DNS çalışıyor mu
    sudo ss -tulnp                  # dinlenen portlar ve hangi program
    sudo ss -tulnp | grep :8080     # 8080'i kim dinliyor
    curl -I https://example.com     # sadece başlıkları çek

## ses — PipeWire (bu makinede PulseAudio değil, PipeWire var)

    wpctl status                    # tüm ses aygıtları, varsayılanlar
    pactl list sinks short          # hoparlörler/çıkışlar
    pactl list sources short        # mikrofonlar/girişler
    pactl info                      # sunucu ve varsayılan aygıt
    pactl set-default-sink <ad>     # varsayılan hoparlörü değiştir
    wpctl set-volume @DEFAULT_AUDIO_SINK@ 50%
    wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle
    alsamixer                       # donanım seviyeleri (F6 kart seç, Esc çık)
    systemctl --user restart pipewire wireplumber   # ses takılırsa

## bluetooth

    systemctl status bluetooth --no-pager
    rfkill list                     # kapatılmış (blocked) mı
    sudo rfkill unblock bluetooth
    bluetoothctl devices            # eşleşmiş cihazlar
    bluetoothctl connect AA:BB:CC:DD:EE:FF
    bluetoothctl                    # etkileşimli kabuk (scan on, pair, quit)

## donanım

    lscpu                           # işlemci
    free -h                         # bellek
    lsblk                           # diskler
    lsusb                           # USB aygıtlar
    lspci                           # PCI aygıtlar (ekran kartı dahil)
    uname -r                        # çekirdek sürümü
    lsb_release -a                  # Ubuntu sürümü
    hostnamectl                     # makine adı, sürüm, çekirdek bir arada
    gpu-izle                        # Intel iGPU çalışıyor mu (bu depoya ait)
    sudo apt install lm-sensors     # [kurulu değil] sıcaklık için; sonra: sensors

## izin — kim neyi okuyabilir/çalıştırabilir

    ls -l dosya.txt                 # izinleri gör: -rw-r--r--
    chmod +x betik.sh               # çalıştırılabilir yap
    chmod 644 dosya.txt             # sahibi yaz/oku, diğerleri oku
    chmod 755 klasor                # sahibi her şey, diğerleri oku+gir
    sudo chown mirac:mirac dosya    # sahipliği değiştir
    sudo -v                         # parolayı önceden gir

755/644 ne demek: 3 hane sırayla **sahip · grup · diğerleri**.
4 oku + 2 yaz + 1 çalıştır. 7 = 4+2+1 (hepsi), 6 = 4+2, 5 = 4+1.

## arşiv — sıkıştırma

    tar -czf yedek.tar.gz klasor/   # klasörü sıkıştır
    tar -xzf yedek.tar.gz           # aç
    tar -tzf yedek.tar.gz           # açmadan içindekileri listele
    zip -r yedek.zip klasor/
    unzip yedek.zip

## tarih ve zamanlama

    date                            # şu an
    timedatectl                     # saat dilimi, NTP durumu
    crontab -e                      # zamanlanmış görev düzenle
    crontab -l                      # zamanlanmış görevleri listele

crontab satırı: `dakika saat gün ay haftagünü komut`
Örnek — her gün 03:00'te yedek al:

    0 3 * * * /home/mirac/yedekle.sh

## terminal — işini kolaylaştıranlar

    Tab                             # komut/dosya adını tamamla
    Yukarı ok                       # önceki komut
    Ctrl-R                          # geçmişte ara
    Ctrl-C                          # çalışan komutu durdur
    Ctrl-L                          # ekranı temizle
    history | grep apt              # geçmişte apt geçen komutlar
    !!                              # son komutu tekrarla (sudo !! işe yarar)

    komut > dosya                   # çıktıyı dosyaya yaz (üzerine)
    komut >> dosya                  # çıktıyı dosyaya ekle
    komut 2>&1                      # hata mesajlarını da dahil et
    komut1 | komut2                 # birinin çıktısını ötekine ver
    komut &                         # arka planda çalıştır

## ai — bu asistanın kendisi

    ai chmod 755 ne demek           # soru sor
    ai -e 8080 portunu kim dinliyor # komut üret, onayla, çalıştır
    ai -i                           # sürekli oturum (teşhis için asıl mod)
    free -h | ai belleğim yetiyor mu    # çıktıyı modele ver
    ai help                         # bu sayfa
    ai help ses                     # tek bölüm

    systemctl --user restart ai-npu # takılırsa
    systemctl --user stop ai-npu    # belleği boşalt (~15 GB)
