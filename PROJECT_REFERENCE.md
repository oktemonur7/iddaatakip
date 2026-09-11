# FootFlow — Geliştirici Referans Dökümanı

> Bu döküman tek referans noktasıdır. Yeni özellik eklemeden, hata ayıklamadan veya değişiklik yapmadan önce oku.
> Son güncelleme: 2026-09-11

---

## Hızlı Erişim

| Konu | Bak |
|---|---|
| Canlı URL'ler, servis durumu | [PROJECT_STATE.md](./PROJECT_STATE.md) |
| Mimari, dosya rolleri, thread yapısı | [PROJECT_ARCHITECTURE.md](./PROJECT_ARCHITECTURE.md) |
| Yeni lig/kupa ekleme | [PROJECT_ARCHITECTURE.md → Yeni Özellik](#) |
| Hata ayıklama | [PROJECT_ARCHITECTURE.md → Hata Ayıklama](#) |

---

## Kritik Kurallar

### 1. index.html'i DOĞRUDAN DÜZENLEME
`index.html` build script çıktısıdır. `python3 build_desktop.py` çalıştırıldığında sıfırlanır.
Frontend değişikliği → `build_desktop.py` içindeki şablon fonksiyonlarını düzenle.

### 2. vapid_keys.json'u ASLA SİLME/DEĞİŞTİRME
VAPID anahtarları değişirse tüm mevcut push abonelikleri geçersiz kalır.
Dosya git'te tracking edilmemeli bile olsa yedekle.

### 3. subscriptions.json Render Dosya Sistemininde
Push abonelik kayıtları Render'ın ephemeral dosya sisteminde durur.
Render servisi silinip yeniden oluşturulursa tüm abonelikler kaybolur.

### 4. Render Free Plan: 1 Servis Kural
Render Free planında 750 saat/ay hakkı var. 2 servis eş zamanlı çalışırsa aylık hak bitebilir.
Eski `iddaatakip.onrender.com` servisi silindi — sadece `footflow-6550` aktif olmalı.

---

## Sistem Mimarisi (Özet)

```
[Kullanıcı Tarayıcı]
      |
      | HTTPS (GitHub Pages)
      v
[index.html — 3.2 MB Monolitik PWA]
      |
      | Başlangıçta: window.INITIAL_ALL_LEAGUES (enjekte edilmiş veri)
      | Runtime: fetch() ile API çağrıları
      |
      | HTTPS (Render)
      v
[push_server.py — Python TCP Server]
      |
      +-- GET /api/vapid-key         → VAPID public key
      +-- GET /api/subscriptions     → Abone sayısı (UptimeRobot pinger)
      +-- GET /api/diagnose          → Sunucu durum raporu
      +-- GET /api/match-goals       → Gol olayları
      +-- GET /api/match-red-cards   → Kırmızı kartlar
      +-- GET /api/match-lineup      → Kadro/diziliş
      +-- GET /api/live-stream-player → TV player
      +-- GET /api/live-summary      → Tüm canlı maç özeti
      +-- POST /api/subscribe        → Push abonelik kaydet
      +-- POST /api/test-push        → Test bildirimi gönder
      |
      +-- [Thread] sahadan_http_sync_worker (her 30s)
      |     Sahadan API → canlı maç verisi → gol push
      +-- [Thread] start_socket_listener
      |     Mackolik WebSocket → gerçek zamanlı olaylar
      +-- [Thread] keep_alive_ping (her 9 dk)
      |     Kendi URL'ine ping → Render uykuya dalmasın
      +-- [Thread] red_card_monitor_worker (her 3 dk)
            Favori maçlarda kırmızı kart push
```

---

## Build → Deploy Akışı

```
1. build_desktop.py çalıştır (python3 build_desktop.py)
   → leagues_cache.json güncellenir
   → index.html güncellenir (data enjekte)
   → dist/index.html güncellenir (GitHub Pages için)

2. git add -A && git commit -m "feat: ..."
3. git push origin main
   → GitHub Actions tetiklenir
   → GitHub Pages otomatik deploy (~1-2 dk)
   → Render otomatik deploy (push_server.py değiştiyse, ~2-3 dk)

Render Deploy Tetikleyicisi: push_server.py değişikliği
GitHub Pages Deploy: dist/index.html + index.html değişikliği
```

---

## Veri Enjeksiyon Mekanizması

```python
# build_desktop.py içinde (L1192):
injected_js = f"window.INITIAL_ALL_LEAGUES = {json.dumps(payload, ensure_ascii=False)};\n"
modified_html = re.sub(r'window\.INITIAL_ALL_LEAGUES\s*=\s*\{.*?\};\n', lambda _: injected_js, template)
```

`index.html` şablonunda boş bir `window.INITIAL_ALL_LEAGUES = {};` satırı vardır.
Build script bu satırı gerçek veriyle değiştirir.
Bu sayede statik HTML dosyası tüm veriyi taşır — backend olmadan da çalışabilir.

---

## Push Bildirimi Akışı

```
Gol Olayı:
sahadan_http_sync_worker → skor değişikliği tespit
  → process_match_update() çağrılır
  → Maç ID'si favorilerde mi? → is_match_favorited() kontrolü
  → Evet → send_push_for_match() → her abonenin favorites listesi kontrol
  → webpush() ile browser push servise gönderilir
  → sw.js push event'i yakalar → notification gösterir

Kırmızı Kart:
red_card_monitor_worker → her 3 dk → fetch_match_red_cards(home, away, uuid)
  → Yeni kırmızı kart var mı? → Abone favorilerinde bu maç var mı?
  → Evet → send_push_for_match()
```

---

## Sahadan API Yapısı

```
Canlı maçlar:
GET https://www.sahadan.com/api/index/soccer-live-e?a=bs&e=sams&add_playing=1&extended_period=1&date=YYYY-MM-DD

Yanıt yapısı:
{
  "data": {
    "areas": [
      {
        "competitions": [
          {
            "matches": [
              {
                "id": "12345",
                "uuid": "abc-def-...",
                "team_A": {"name": "Galatasaray"},
                "team_B": {"name": "Fenerbahçe"},
                "status": "Playing",
                "period": "2. Yarı",
                "score": "2-1"
              }
            ]
          }
        ]
      }
    ]
  }
}

Gol olayları:
GET https://www.sahadan.com/mac/{home-slug}/{away-slug}/{uuid}/anlik
```

---

## Özellik Etki Haritası

Herhangi bir değişiklik yapmadan önce aşağıdaki tabloyu kontrol et:

| Değiştirmek İstediğin | Etkilenen Dosyalar | Dikkat Edilecek |
|---|---|---|
| Yeni lig ekle | `build_desktop.py` (LEAGUES), `leagues_cache.json` | Build sonrası index.html de güncellenir |
| Yeni kupa ekle | `build_desktop.py` (LEAGUES + type:"cup"), `leagues_cache.json` | Fikstür URL formatı farklı olabilir |
| Bildirim başlığı/içeriği | `push_server.py` (process_match_update) | sw.js'de tag ile özel davranış tanımlanabilir |
| Yeni API endpoint | `push_server.py` (do_GET/do_POST) | CORS otomatik, başka bir şey gerekmez |
| Frontend UI değişikliği | `build_desktop.py` (şablon fonksiyonları) | index.html'i elle düzenleme! |
| Push sunucu URL'i | `index.html` L3692, L5377-5380, L5648 | push_server.py L1513 de güncelle |
| Cache versiyonu | `sw.js` L1 | Kullanıcıların tarayıcısı eski cache'i temizler |
| PWA adı/ikonu | `manifest.json` | `icons/` klasöründe dosyalar olmalı |

---

## Bilinen Limitler & Teknik Borç

| Konu | Detay | Çözüm/Geçici Çözüm |
|---|---|---|
| Monolitik index.html | 3.2 MB tek dosya, bundle yok | Build script ile yönetiliyor, kabul edilebilir |
| Ephemeral subscriptions | Render silinirse push aboneleri gider | Yedek/export mekanizması yok (geliştirilmeli) |
| Tek point of failure | Render free plan servisi çökerse her şey durur | Keep-alive + UptimeRobot |
| Rate limit | Sahadan hızlı isteklerde 429 verir | 30s poll, browser headers, retry logic mevcut |
| Socket bağlantı kopması | WebSocket bağlantısı kopabilir | Otomatik yeniden bağlanma var (~30s) |
| 07:00 abone reset | Her gün 07:00'de favoriler temizleniyor | Tasarım gereği (güne özel favoriler) |
| Push abonelik taşıması | Sunucu değişiminde aboneler kaybolur | Eski abonelere yeniden kayıt uyarısı göster |
