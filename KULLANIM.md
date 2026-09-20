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
- **Yargı cümleleri.** `df` çıktısına "Evet, diskiniz dolu. Kullanım %29, yani %71 boş"
  diyebiliyor — sayıyı doğru okuyup sonucu ters söylüyor. Sayılara bak, hükme bakma.
- **Güncel sürüm bilgisi.** İnterneti yok, bilgisi eskidir. Yeni paketleri bilmez.
- **Uzun metin.** Uzun logu `tail -30` ile kırp, yoksa hem yavaşlar hem dağılır.
- **Hafıza.** Her komut sıfırdan başlar; "az önce dediğin" diye devam edemezsin.
- **Dosyaların.** Kendiliğinden dosya okuyamaz: `cat dosya | ai "..."` diye vereceksin.

`-e` modunun onay sorması bu yüzden var. Komutu okumadan `e` deme.

## Bir şeyler ters giderse

| belirti | ne yap |
|---|---|
| `ai: sunucuya ulaşılamadı` | `systemctl --user start ai-npu` |
| İlk soru çok uzun sürüyor | Normal, model yükleniyor. Sonrakiler hızlı |
| Cevap alakasız | Soruyu kısalt, boruyla verdiğin metni `tail` ile kırp |
| `ai: command not found` | `export PATH=$HOME/.local/bin:$PATH` satırını `~/.bashrc`'ye ekle |
| Bellek lazım | `systemctl --user stop ai-npu` — 7,9 GB boşalır |
