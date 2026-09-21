#!/usr/bin/env python3
"""Otomasyon testi: python3 test-otomasyon.py [-v] [senaryo-adi ...]

Ucuncu kullanim amacini olcer: "verdigim promptla model terminali kullanip cok
adimli bir isi bitirebiliyor mu". test-senaryolar.py tek komut uretimini,
test-zincir.py teshisi olcer; bu dosya ISIN BITIP BITMEDIGINI olcer.

Her senaryo kendi gecici klasorunde kosar, HOME de oraya cevrilir, sistemi
degistiren komutlar reddedilir. Gecme olcutu modelin "tamam" demesi degil:
senaryonun DOGRULA kabugu 0 donmeli. Yani sonuc durumuna bakiyoruz.
"""
import json, os, re, shutil, subprocess, sys, tempfile, urllib.request

URL = "http://127.0.0.1:11435/v1/chat/completions"
BUTCE = int(os.environ.get("AI_TOKEN", 400))
ISARET = re.compile(r"^\s*`?\s*\$\s+(.+?)\s*`?\s*$")
ADIM = 8

# Kum havuzunu delen her sey. Testte modelin gercek sisteme dokunmasina izin yok;
# bir senaryo bunlari gerektiriyorsa senaryo yanlis secilmistir, koşum degil.
KACIS = re.compile(r"\bsudo\b|\bapt(-get)?\b|\bsystemctl\b|\bcrontab\b|\bdpkg\b|"
                   r"\b(reboot|shutdown|poweroff|halt|mkfs|fdisk)\b|\bdd\s+[^\n]*of=/dev/|"
                   r"(^|[\s'\"=:])/(etc|usr|var|boot|bin|sbin|lib|opt|srv|dev|proc|sys)\b|"
                   r"\bcurl\b|\bwget\b|\bpip\b|\bnpm\b|\bgit\s+(clone|push|pull|remote)\b")


def sonuc_metni(kod, cikti):
    """Komut sonucunu modelin yanlis okumayacagi bicimde anlat."""
    if cikti:
        return f"Komut çıktısı (çıkış kodu {kod}):\n{cikti[-1500:]}"
    if kod == 0:
        return ("Komut BAŞARIYLA çalıştı (çıkış kodu 0) ve ekrana hiçbir şey yazmadı. "
                "mv, cp, mkdir, printf, chmod gibi komutlar başarılı olduklarında sessizdir; "
                "bu bir başarısızlık DEĞİLDİR ve 'hiçbir şey bulunamadı' anlamına GELMEZ. "
                "Sonucu görmek istiyorsan ls veya cat ile ayrıca kontrol et.")
    return f"Komut HATA verdi (çıkış kodu {kod}) ve hiçbir çıktı üretmedi."


def sor(gecmis):
    req = urllib.request.Request(URL, json.dumps(
        {"messages": gecmis, "mode": "oturum", "max_tokens": BUTCE,
         "temperature": 0}).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.load(r)["choices"][0]["message"]["content"].strip()


def kos(ad, hazirlik, istek, dogrula, ayrinti=False):
    kutu = tempfile.mkdtemp(prefix=f"oto-{ad}-")
    ortam = dict(os.environ, HOME=kutu, PWD=kutu)
    sh = lambda c: subprocess.run(c, shell=True, cwd=kutu, env=ortam, text=True, timeout=60,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    sh(hazirlik)
    print(f"\n{'='*70}\n[{ad}] › {istek}\n{'='*70}")
    kok, gecmis, kosulan, kesildi = istek, [], [], None
    icerik = (f"Çalıştığın klasör: {kutu} (burası senin ev klasörün, ~ buraya işaret "
              f"ediyor). Görev: {istek}")
    for i in range(ADIM):
        gecmis.append({"role": "user", "content": icerik})
        # bin/ai ile ayni pencere: son 10 mesaj + basa sabitlenmis asil gorev
        pencere = gecmis[-9:] if i == 0 else (
            [{"role": "user", "content": f"Asıl görev: {kok}"}] + gecmis[-8:])
        cevap = sor(pencere)
        gecmis.append({"role": "assistant", "content": cevap})
        m = next((x for x in map(ISARET.match, cevap.split("\n")) if x), None)
        if not m:
            print(f"[bitti dedi, {i} komut sonra] {cevap[:200]}")
            break
        cmd = m.group(1)
        print(f"[adim {i+1}] $ {cmd}")
        if KACIS.search(cmd):
            print("  (kum havuzunu deliyor -> kesildi)")
            kesildi = "kum-havuzu"
            break
        if kosulan.count(cmd) >= 2:
            print("  (zaten calistirildi, tekrarlanmadi)")
            icerik = (f"Bu komutu zaten çalıştırdın ve çıktısını gördün: {cmd}\n"
                      "Aynı komut aynı sonucu verir. Bir şeyin değişmesini bekliyorsan "
                      "önce o değişikliği YAPAN komutu çalıştır: betik yazdıysan "
                      "./betik.sh ile çalıştır, dosya bekliyorsan onu üreten komutu ver. "
                      "Yapacak adım kalmadıysa sonucu özetle.")
            continue
        kosulan.append(cmd)
        r = sh(cmd)
        cikti = (r.stdout or "").rstrip()
        if ayrinti and cikti:
            print("  " + "\n  ".join(cikti.splitlines()[:6]))
        elif r.returncode:
            print(f"  cikis {r.returncode}: {cikti.splitlines()[:1]}")
        icerik = sonuc_metni(r.returncode, cikti)
    else:
        kesildi = "adim-doldu"
    d = sh(dogrula)
    ok = d.returncode == 0
    print(f">>> {'GECTI' if ok else 'KALDI'}  ({len(kosulan)} komut"
          + (f", {kesildi}" if kesildi else "") + ")")
    if not ok:
        print(f"    dogrulama: {(d.stdout or '').strip()[:300] or 'cikis kodu ' + str(d.returncode)}")
    shutil.rmtree(kutu, ignore_errors=True)
    return ok


# (ad, hazirlik, istek, dogrula) -- dogrula 0 donerse is gercekten bitmis demektir.
S = [
 ("log-tasi",
  "touch a.log b.log c.log nota.txt",
  "bu klasördeki bütün .log dosyalarını logs adlı yeni bir alt klasöre taşı",
  "test -f logs/a.log && test -f logs/b.log && test -f logs/c.log && test -f nota.txt && test ! -f a.log"),

 ("csv-topla",
  "printf 'ad,tutar\\nali,10\\nveli,25\\nayse,7\\n' > rapor.csv",
  "rapor.csv dosyasındaki tutar sütununun toplamını hesapla ve sadece sayıyı toplam.txt dosyasına yaz",
  "test \"$(tr -dc 0-9 < toplam.txt)\" = 42"),

 ("yedek-betigi",
  "mkdir -p notlar && echo merhaba > notlar/n1.txt",
  "notlar klasörünü tarih adıyla yedekleyen yedekle.sh adında bir betik yaz, çalıştırılabilir yap ve bir kez çalıştırıp işe yaradığını doğrula",
  "test -s yedekle.sh && test -x yedekle.sh && ls -A | grep -qE '20[0-9][0-9]'"),

 ("buyuk-bul",
  "mkdir -p veri && head -c 200000 /dev/zero > veri/buyuk.bin && head -c 100 /dev/zero > veri/kucuk.bin",
  "veri klasöründeki 100KB'dan büyük dosyaların adlarını buyukler.txt dosyasına yaz",
  "grep -q buyuk.bin buyukler.txt && ! grep -q kucuk.bin buyukler.txt"),

 ("git-baslat",
  "echo kod > main.py && mkdir -p build && touch build/cikti.o",
  "burada bir git deposu başlat, build klasörünü yok sayacak bir .gitignore ekle ve her şeyi ilk commit olarak kaydet",
  "test -d .git && grep -q build .gitignore && git log --oneline | grep -q . && ! git ls-files | grep -q build/"),

 ("jpg-ayir",
  "touch 2024-01-05.jpg 2024-03-11.jpg 2025-02-02.jpg okuma.txt",
  "buradaki jpg dosyalarını adlarındaki yıla göre 2024 ve 2025 adlı alt klasörlere ayır",
  "test -f 2024/2024-01-05.jpg && test -f 2024/2024-03-11.jpg && test -f 2025/2025-02-02.jpg && test -f okuma.txt"),
]

ayrinti = "-v" in sys.argv
secim = [a for a in sys.argv[1:] if a != "-v"]
sec = [s for s in S if not secim or s[0] in secim]
gecen = sum(kos(*s, ayrinti=ayrinti) for s in sec)
print(f"\n=== OTOMASYON SONUC  {gecen}/{len(sec)}")
