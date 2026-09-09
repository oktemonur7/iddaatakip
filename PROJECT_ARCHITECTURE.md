# İddaa Takip & Canlı Skor - Proje Mimari ve Referans Kılavuzu

Bu belge, projenin tüm iç işleyişini, veri akışını, bileşenlerini, zamanlamalarını ve dikkat edilmesi gereken kritik kuralları eksiksiz açıklar. Yeni bir geliştirme yaparken veya sorun çözerken onlarca dosyayı tekrar tekrar okumak yerine doğrudan bu referans belgesine başvurulur.

---

## 1. Sisteme Genel Bakış ve Mimari

Proje 3 temel bacaktan oluşur:
1. **İstemci (Client / Standalone Desktop & PWA):** Tek dosyalık (`index.html`), sıfır dış kütüphane bağımlılığı olan (Socket.io dahi içine gömülü), neon koyu temalı modern canlı skor ve lig takip paneli.
2. **Push & Senkronizasyon Sunucusu (`push_server.py`):** Render üzerinde (`https://iddaatakip.onrender.com`) çalışan Python HTTP/WebSocket sunucusu. WebPush bildirimlerini yönetir, Sahadan/Mackolik verilerini arka planda tarar, canlı yayın ve golcü verilerini proxy/cache olarak istemciye sunar.
3. **Derleyici & Veri Kazıyıcı (`build_desktop.py`):** 19 ligin puan durumu, fikstür, oranlar, TV yayınları ve golcü bilgilerini Sahadan/Nesine/İddaa sitelerinden çekip tek bir HTML dosyasına paketleyen betik. Masaüstündeki `futbol_ligleri.html` dosyasını üretir.

```
                    ┌─────────────────────────────────────────────────────────┐
                    │      Sahadan.com & Mackolik Canlı Veri Kaynakları       │
                    │  (socket.mackolikfeeds.com / soccer-sync-data / Nuxt)   │
                    └──────────────┬────────────────────────────┬─────────────┘
                                   │                            │
                   Canlı WebSocket │                            │ HTTP / Nuxt Scrape
                   (Doğrudan İstemci)                           ▼
                                   │                   ┌─────────────────────────────┐
                                   │                   │   build_desktop.py          │
                                   │                   │   (Veri Kazıma & Derleme)   │
                                   └──────────────┬────┴──────────────┬──────────────┘
                                                  │                   │
                                   Derlenmiş HTML │                   │
                               ┌──────────────────┴───────────────┐   │
                               ▼                                  ▼   ▼
                ┌───────────────────────────────┐       ┌───────────────────────────────┐
                │  Desktop / Web İstemcisi      │       │  Render Canlı Push Sunucusu   │
                │  (futbol_ligleri.html / PWA)  │◄─REST─┤  (push_server.py : 8080)      │
                │  - Puan Durumu & Fikstür      │       │  - WebPush Bildirimleri       │
                │  - Canlı Skor Barı            │       │  - /api/match-goals           │
                │  - Golcü & TV Tooltip'leri    │       │  - /api/live-sync             │
                │  - NTV / Falcon Canlı Yayın   │       │  - /api/stream-player         │
                └───────────────────────────────┘       └───────────────────────────────┘
```

---

## 2. Dosya Haritası ve Görev Dağılımı

| Dosya Adı | Konum / Hedef | Rol ve Açıklama |
|---|---|---|
| `index.html` | Proje kök dizini | Ana uygulama şablonu. CSS stilleri, UI panelleri, Web Audio ses sentezleyici, Socket.io istemcisi, lig/fikstür render mantığı. |
| `push_server.py` | Render Cloud | Python 3 sunucusu. Canlı soket dinleyicisi, arka plan sync işçisi, WebPush gönderici, golcü ve canlı yayın endpoint'leri. |
| `build_desktop.py` | Yerel / Derleyici | 19 ligi Sahadan'dan kazır, önbelleğe yazar, `window.INITIAL_ALL_LEAGUES` verisini enjekte ederek masaüstü ve `dist/` çıktılarını üretir. |
| `sw.js` | Web İstemcisi / PWA | Service Worker (`iddaatakip-v43`). Network-First (2.5s zaman aşımıyla önbellek fallback) ve WebPush kilit ekranı bildirimlerini yakalar. |
| `manifest.json` | Web / PWA | PWA manifestosu (standalone açılış, ikonlar, koyu tema). |
| `socket.io.v2.slim.js`| Derleme girdisi | `build_desktop.py` tarafından derlenen HTML içine gömülen Socket.io v2 istemci kütüphanesi (CDN bağımlılığını sıfırlar). |
| `leagues_cache.json` | Yerel önbellek | 19 ligin puan durumları, haftaları ve maçlarının disk önbelleği. |
| `all_goals_cache.json`| Yerel önbellek | UUID bazlı maç gol bilgileri önbelleği (dakika, golcü, asist, skor). |
| `all_tv_cache.json` | Yerel önbellek | UUID bazlı TV yayın kanalları önbelleği (tabii spor, S Sport, beIN vb.). |
| `vapid_keys.json` | Sunucu güvenliği | WebPush için VAPID anahtarları (public & private key). |
| `/Users/onur/Desktop/futbol_ligleri.html` | Masaüstü Çıktısı | Kullanıcının günlük kullandığı ana masaüstü dosyası. |
| `dist/index.html` | GitHub Pages | GitHub Pages için derlenmiş web sürümü. |

---

## 3. Desteklenen Ligler (Toplam 19 Lig / Turnuva)

`build_desktop.py` ve `index.html` içinde 19 lig tanımlıdır:
1. `super-lig-tr`: Trendyol Süper Lig (Türkiye) - **Varsayılan Lig**
2. `trendyol-1-lig`: Trendyol 1. Lig (Türkiye)
3. `sampiyonlar-ligi`: UEFA Şampiyonlar Ligi (`round_id=95533`, 36 takımlı lig aşaması)
4. `avrupa-ligi`: UEFA Avrupa Ligi (`round_id=94654`)
5. `konferans-ligi`: UEFA Konferans Ligi (`round_id=95377`)
6. `premier-lig-en`: Premier Lig (İngiltere)
7. `championship`: Championship (İngiltere)
8. `laliga`: LaLiga (İspanya)
9. `serie-a`: Serie A (İtalya)
10. `bundesliga`: Bundesliga (Almanya)
11. `ligue-1`: Ligue 1 (Fransa)
12. `eredivisie`: Eredivisie (Hollanda)
13. `premier-lig-pt`: Primeira Liga (Portekiz)
14. `pro-lig-be`: Pro Lig (Belçika)
15. `premiership-sc`: Premiership (İskoçya)
16. `super-lig-dk`: Superliga (Danimarka)
17. `super-lig-ch`: Super League (İsviçre)
18. `eliteserien`: Eliteserien (Norveç)
19. `czech-liga`: Chance Liga (Çekya)

---

## 4. İstemci Durum Yönetimi ve Yaşam Döngüsü (`index.html`)

### Ana Değişkenler ve Bellek Durumu
- `allLeaguesState`: `window.INITIAL_ALL_LEAGUES` üzerinden gelen tüm statik/önbellek lig verisi.
- `currentLeagueId`: Seçili lig kimliği (`"super-lig-tr"` vb.).
- `currentLeagueData`: `allLeaguesState.data[currentLeagueId]` (puan durumu, haftalar, aktif hafta).
- `selectedWeekIndex`: Fikstür panelinde seçili olan hafta dizini.
- `todayOnlyFilter`: Fikstürde sadece bugünün maçlarını gösteren toggle (`true`/`false`).
- `liveScoresList`: Bugünün canlı/bitmiş maçlarının listesi (`allLeaguesState.live_scores_today`).
- `favoriteMatchIds`: Kullanıcının yıldızladığı favori maç kimlikleri (`Set`, `localStorage["agy_fav_matches"]`).
- `GOALS_CLIENT_CACHE`: `{ [uuid]: [ { minute, type, scorer, assist, score_A, score_B } ] }`.
- `GOALS_FETCH_IN_FLIGHT`: Aynı maç için aynı anda birden fazla network isteği atılmasını engelleyen kilit tablosu.
- `GOALS_PENDING_RETRY`: Yeni gol olduğunda golcüyü arayan periyodik retry tablosu.

### Lig Değiştirme Akışı (`onLeagueChanged`)
```javascript
onLeagueChanged(leagueId)
  └── currentLeagueId = leagueId
  └── loadCurrentLeague()
        ├── currentLeagueData = allLeaguesState.data[currentLeagueId]
        ├── selectedWeekIndex = currentLeagueData.current_week_index || 0
        ├── renderStandings()     // Sol panel: Puan durumu ve form rehberi
        ├── renderWeekSelector()  // Sağ panel: Hafta açılır menüsü
        └── renderFixture()       // Sağ panel: Seçili haftanın maçları
```

### Devre / Periyot Koruma Hiyerarşisi (`getMatchPeriodRank`)
Bayat HTTP polling paketlerinin canlı soket verisini geriye almasını (örn: `İY` iken `45+3`'e geri dönmesini) engellemek için tek yönlü rütbe sistemi kullanılır:
$$\text{Başlamadı (0)} \longrightarrow \text{1. Yarı (1)} \longrightarrow \text{Devre Arası / İY (2)} \longrightarrow \text{2. Yarı (3)} \longrightarrow \text{Uzatma (4)} \longrightarrow \text{Penaltılar (5)} \longrightarrow \text{MS / Bitti (6)}$$
- `newRank < currentRank && currentRank >= 2` ise paket **yoksayılır**; maç periyodu ve dakikası geriye çekilmez.

---

## 5. Canlı Skor ve Çift Kanal Senkronizasyonu

Canlı skorlar iki paralel kaynaktan beslenir:
1. **Birincil Hızlı Kanal:** Sahadan resmi WebSocket sunucusu (`https://socket.mackolikfeeds.com/mksh`, oda: `soccer`). Anlık gol, dakika ve kırmızı kart olayları milisaniyeler içinde gelir.
2. **İkincil Yedek Kanal (`pollLiveScoresFromServer`):** Her 5 saniyede bir Render sunucusuna (`/api/live-sync?_t=...`) sorgu atılır. WebSocket kopsa dahi maçlar güncel kalır.

### Skor Değişimi & Gol Mekanizması (`applyLiveMatchUpdate`)
- **Skor Artışı (Gol):**
  1. `m._notifiedScores` kontrol edilir (mükerrer ses/animasyon engellenir).
  2. `playGoalSound()` tetiklenir (Web Audio API: 880 Hz + 1320 Hz çift ton, 2x ses seviyesi).
  3. Skor kutusuna 12 saniye süren yeşil neon parlama (`goal-flash`) sınıfı eklenir.
  4. İlgili maç için eski gol önbelleği temizlenir ve `scheduleGoalRetry` başlatılır.
- **Skor Düşüşü (VAR / Gol İptali):**
  1. **Jitter Koruması:** Golden sonraki ilk 120 saniye içinde gelen anlık skor düşüşleri bayat paket kabul edilip yoksayılır.
  2. 120 saniyeden sonra gerçek bir düşüş olursa VAR iptali sayılır:
     - `playCancelSound()` çalar (alçalan çift ton).
     - Skor kutusu 10 saniye kırmızı neon yanıp söner (`goal-cancel-flash`).
- **Kırmızı Kart:**
  - `rc_home` veya `rc_away` arttığında 10 saniye kırmızı flaş (`red-card-flash`) tetiklenir.

---

## 6. Golcü Bilgisi Çekme Stratejisi (Retry & Rate-Limit Koruması)

Sahadan editörünün golcüyü sisteme girmesini bekleyen optimize edilmiş sorgu mekanizması:
- **İlk Sorgu:** Gol olduktan tam **10 saniye sonra** atılır (editöre doğal yazma payı bırakılır, gereksiz ilk saniye yükü kesilir).
- **Tekrar Aralığı:** İlk sorgudan sonra **her 5 saniyede bir** tekrarlanır.
- **Maksimum Deneme:** Toplam **15 deneme** (~1 dakika 20 saniye). 15 deneme bittiğinde sorgu kesilir ve "bekleniyor" ibaresi kaldırılarak sistem dinlenmeye alınır.
- **Sunucu Önbelleği (TTL):** Eksik/girilmemiş golcüsü olan maçlar için sunucu tarafı önbelleği **5 saniye** tutulur (`now - 10`). Sahadan'a dakikada maksimum 12 istek gidebilir; Cloudflare rate-limit riski sıfırlanmıştır.
- **Hover / Click Anında:** Kullanıcı fareyle skor kutusunun üstüne geldiğinde beklemeden **anında taze sorgu** (`loadScoreGoalTooltip`) atılır.

---

## 7. Render Backend API Uç Noktaları (`push_server.py`)

Sunucu `ThreadedTCPServer` olarak `8080` portunda çalışır.

| Uç Nokta | Metot | Parametreler | Görev ve Açıklama |
|---|---|---|---|
| `/api/match-goals` | `GET` | `uuid`, `home`, `away`, `min_goals` | Sahadan maç detayından (`__NUXT_DATA__`) golcüler, asistler ve dakikaları döner. |
| `/api/live-sync` | `GET` | `_t` (timestamp) | Sunucudaki en güncel canlı ve bitmiş maç listesini (`latest_matches_summary`) döner. |
| `/api/stream-player` | `GET` | `id`, `server` (`falcon`/`kobra`) | NTV canlı yayın iframe HTML'ini döner (120 sn önbellekli). |
| `/api/stream-embed` | `GET` | `server`, `id` | Canlı yayın gömme URL'sini çözer. |
| `/api/vapid-key` | `GET` | - | WebPush için genel anahtarı (`vapid_keys.json`) döner. |
| `/api/subscribe` | `POST` | JSON: `{ endpoint, keys, favorites }` | WebPush aboneliğini kaydeder / günceller. |
| `/api/unsubscribe` | `POST` | JSON: `{ endpoint }` | WebPush aboneliğini siler. |
| `/api/update-favorites` | `POST` | JSON: `{ endpoint, favorites }` | Abonenin bildirim almak istediği maç ID'lerini günceller. |
| `/api/diagnose` | `GET` | - | Canlı sistem tanı bilgileri (abone sayısı, endpoint önizlemeleri). |

### ⚠️ Kritik CORS Kuralı
`RequestHandler.end_headers()` zaten otomatik olarak:
```python
self.send_header("Access-Control-Allow-Origin", "*")
self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
self.send_header("Access-Control-Allow-Headers", "Content-Type")
```
başlıklarını ekler. **ASLA** endpoint'ler (`/api/match-goals` vb.) içinde manuel olarak `send_header("Access-Control-Allow-Origin", "*")` çağrılmamalıdır! Aksi takdirde HTTP cevabında `*, *` mükerrer başlığı oluşur ve tarayıcılar CORS hatasıyla isteği çöpe atar.

---

## 8. Canlı Yayın Entegrasyonu (NTV / Falcon / Kobra)

- Maç kutucuğundaki **▶ Canlı İzle** butonu sadece devam etmekte olan canlı maçlarda (`isLive`) görünür; bitmiş maçlarda gizlenir.
- Butona tıklandığında `openMatchStream(homeTeam, awayTeam)` çalışır.
- Falcon ve Kobra sunucuları taranarak ilgili takımların maçı bulunur.
- Bulunan maç `stream-modal` içinde iframe olarak açılır; kullanıcı modal üzerinden sunucu değiştirebilir (`falcon` / `kobra`).

---

## 9. Geliştirme & Dağıtım Rutinleri (Nasıl Güncellenir?)

Bir değişiklik yapıldığında izlenmesi gereken standart sıra:

1. **Kaynak Dosyayı Düzenle:** `index.html` veya `push_server.py` üzerinde gerekli düzeltmeyi yap.
2. **Masaüstü ve Dist Dosyalarını Derle:**
   ```bash
   python3 build_desktop.py
   ```
   Bu komut `leagues_cache.json` ve `all_goals_cache.json` verilerini tazeleyerek `/Users/onur/Desktop/futbol_ligleri.html` ve `dist/index.html` dosyalarını yeniden üretir.
3. **Git Commit & Push (Render ve GitHub Pages):**
   ```bash
   git add index.html push_server.py leagues_cache.json all_goals_cache.json PROJECT_ARCHITECTURE.md
   git commit -m "fix/feat: açıklama"
   git push origin main
   ```
   Push işlemi Render sunucusunu otomatik tetikler (~45-60 saniye içinde yayına girer).
4. **Doğrulama:**
   - Render CORS testi: `curl -i -s "https://iddaatakip.onrender.com/api/match-goals?uuid=123" | grep -i access-control` (Tek `*` olmalı).
   - Masaüstü dosyasında tarayıcıda `Cmd + Shift + R` ile test et.

---

## 10. Geçmiş Hatalar ve Altın Kurallar (Asla Tekrarlanmayacaklar)

1. **Değişken Sıralaması (`renderFixture`):** `isPlayed` ve `isLive` değişkenleri maç döngüsünün (`matchesToShow.forEach`) en başında tanımlanmalıdır. Tooltip veya skor kutusu içinde kullanılmadan önce tanımlanmazsa `ReferenceError: Cannot access 'isLive' before initialization` hatası fırlatır ve lig geçişleri kilitlenir.
2. **Çift CORS Başlığı:** `push_server.py` içinde endpoint'lere manuel CORS başlığı ekleme. Tek yetkili `end_headers()` fonksiyonudur.
3. **Periyot Regresyonu:** `applyLiveMatchUpdate` içinde devre rütbesi kontrol edilmeden `m.period` güncellenmemelidir (`1.Yarı` devresi `İY`'yi ezemez).
4. **Hafta İsimlendirmesi:** Turnuva maçlarında (Şampiyonlar Ligi, Avrupa Ligi) eleme turları `1. Eleme Turu`, `Play-off`; lig aşaması ise `Lig Aşaması X. Hafta` olarak etiketlenmelidir (`Hafta Play-off` gibi hatalı string birleştirmeler yapılmamalıdır).
5. **UUID vs ID:** Canlı maçlarda `match_id` ve `match_uuid`, fikstür maçlarında `id` ve `uuid` kullanılır. Kod içinde daima `m.uuid || m.match_uuid || m.match_id || m.id` kontrolü yapılmalı ve DOM elemanlarına `data-match-uuid` bağlanmalıdır.
