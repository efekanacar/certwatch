# CertWatch

Python standart kütüphanesiyle çalışan, komut satırından SSL/TLS sertifikası kontrol aracı.

## Özellikler

- Bir veya birden fazla domainin TLS sertifikasını kontrol eder.
- Sistem güven deposuyla sertifika zincirini ve domain eşleşmesini doğrular; SNI kullanır.
- Sertifikanın bitiş tarihini UTC olarak ve kalan tam gün sayısını gösterir.
- Varsayılan olarak bitişine 30 gün veya daha az kalan sertifikalarda uyarır.
- DNS, bağlantı reddi, zaman aşımı ve sertifika hatalarını anlaşılır mesajlarla gösterir.
- Bir domainde hata olsa bile diğer domainlere devam eder.
- Makine tarafından işlenebilir JSON çıktısı sağlar.

## Kurulum

Python 3.9 veya üzeri ve SSL desteği gerekir. Harici paket veya pip kurulumu gerekmez.
`certwatch.py` dosyasını kaydedip terminalden çalıştırın:

```console
python certwatch.py --help
```

Windows'ta gerekirse `python` yerine `py` kullanın.

## Kullanım

Tek domain:

```console
python certwatch.py example.com
```

Birden fazla domain ve 14 günlük uyarı eşiği:

```console
python certwatch.py example.com python.org --warn-days 14
```

Özel TLS portu ve saniye cinsinden zaman aşımı:

```console
python certwatch.py example.com --port 8443 --timeout 5
```

JSON çıktısı ve dosyaya yönlendirme:

```console
python certwatch.py example.com python.org --json
python certwatch.py example.com --json > sonuc.json
```

Domainleri boşlukla ayırın; `https://`, yol veya `:port` eklemeyin.
Uluslararası domain adları IDNA ile dönüştürülür. Port ve diğer seçenekler tüm domainlere uygulanır.
Doğrudan TLS bağlantısı kullanılır; STARTTLS ve HTTP proxy desteği yoktur.

## Çıktı ve hata davranışı

JSON çıktısı her domain için `domain`, `port`, `status`, `expires_at`,
`days_remaining` ve `message` alanlarını içeren bir listedir.
`expires_at`, UTC ISO 8601 biçimindedir; kalan gün sayısı aşağı yuvarlanır.
Uyarı eşiği tam gün sayısına değil, kalan gerçek süreye göre değerlendirilir.

Durumlar: `ok` (geçerli), `warning` (eşik içinde), `expired` (süresi dolmuş),
`error` (kontrol başarısız). Doğrulama başarısızsa tarih ve kalan gün `null` olur.
Süresi dolmuş, kendinden imzalı, güvenilmeyen veya domaini uyuşmayan sertifikalar
genellikle TLS doğrulamasında reddedilir ve nedenini açıklayan `error` döner.
Doğrulama kapatılmaz. Araç sertifika iptal durumunu (OCSP/CRL) kontrol etmez.

Domainler sırayla kontrol edilir. Zaman aşımı her ağ işlemine uygulanır;
DNS çözümlemesi işletim sistemine bağlı olarak bu süreyi aşabilir.

Çıkış kodları:

- `0`: Tüm sertifikalar geçerli ve uyarı eşiğinin dışında.
- `1`: En az bir uyarı, süresi dolmuş sertifika veya kontrol hatası var.
- `2`: Komut satırı kullanımı hatalı (bu durumda JSON yerine argparse hata mesajı gelir).
- `130`: Kullanıcı işlemi Ctrl+C ile durdurdu.
