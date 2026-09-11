# FootFlow — Proje Durumu (Güncel)

> Son güncelleme: 2026-09-11

## Canlı Ortam Bilgileri

| Özellik | Değer |
|---|---|
| **Uygulama Adı** | FootFlow |
| **Önceki Adlar** | iddaatakip → FootFollow → FootFlow |
| **GitHub Repo** | https://github.com/oktemonur7/FootFlow.git (Branch: main) |
| **Web Sitesi (GitHub Pages)** | https://oktemonur7.github.io/FootFlow/ |
| **Push & Sync Sunucusu (Render)** | https://footflow-6550.onrender.com (Python 3, Free Plan, Virginia) |
| **UptimeRobot İzleme** | https://footflow-6550.onrender.com/api/subscriptions (Her 5 dk) |
| **Service Worker Önbellek** | `footflow-v50` |
| **PWA Manifest Adı** | FootFlow |
| **Render Plan** | Free (750 saat/ay) — tek servis yeterli |

## Son Commit Geçmişi

| Hash | Mesaj |
|---|---|
| `a6d5a9c` | feat: Render URL guncellendi (footflow-6550) ve remote repo ayarlandi |
| `3663573` | feat: uygulama adi FootFlow olarak guncellendi |
| `512ada2` | feat: 7 ulusal kupa eklendi (FA Cup, Lig Kupasi, Kral Kupasi, Coppa Italia, Fransa, Almanya, Turkiye) |
| `e531309` | feat: lig secim listboxina bugun maci olan ligler filtresi toggle eklendi |
| `6ce6abf` | fix: resolve 429 Too Many Requests with retry logic, browser headers and disabling auto-prefetch flood |
| `547b643` | style: enlarge pitch player dots and names for better readability |
| `e4dce55` | feat: cache match lineups for 10 days with auto-prune on 7 AM reset |
| `eeda8a4` | feat: add Kadrolar (match lineup) feature with pitch visualization |
| `0e3900a` | feat: add 3m periodic red card monitor with 5s stagger for favorite live matches |
| `123aef0` | feat: rename to FootFollow; fix goal scorer consistency and cancel loop |

## Lig & Kupa Listesi (26 Toplam)

### Ligler (19)
| No | Ad | Ülke |
|---|---|---|
| 1 | Trendyol Süper Lig | Türkiye |
| 2 | Trendyol 1. Lig | Türkiye |
| 3 | Şampiyonlar Ligi | Avrupa |
| 4 | Avrupa Ligi | Avrupa |
| 5 | Konferans Ligi | Avrupa |
| 6 | Premier Lig | İngiltere |
| 7 | Championship | İngiltere |
| 8 | LaLiga | İspanya |
| 9 | Serie A | İtalya |
| 10 | Bundesliga | Almanya |
| 11 | Ligue 1 | Fransa |
| 12 | Eredivisie | Hollanda |
| 13 | Primeira Liga | Portekiz |
| 14 | Pro Lig | Belçika |
| 15 | Premiership | İskoçya |
| 16 | Superliga | Danimarka |
| 17 | Super League | İsviçre |
| 18 | Eliteserien | Norveç |
| 19 | Chance Liga | Çekya |

### Kupalar (7 — Fikstür Görünümü)
| No | Ad | Ülke |
|---|---|---|
| 1 | FA Cup | İngiltere |
| 2 | Lig Kupası | İngiltere |
| 3 | Kral Kupası | İspanya |
| 4 | İtalya Kupası (Coppa Italia) | İtalya |
| 5 | Fransa Kupası | Fransa |
| 6 | Almanya Kupası | Almanya |
| 7 | Ziraat Türkiye Kupası | Türkiye |

> **NOT:** Kupalar fikstür formatında gösterilir (puan durumu yok). "type": "cup" alanı leagues_cache.json'da kupaya özel set edilir.

## İsim Değişikliği Geçmişi & Kalan İzler

### Güvenli İzler (Silinmesi Gerekmiyor)
- `index.html` L5377: localStorage fallback zinciri (footfollow → iddaatakip) — geriye dönük uyumluluk için kasıtlı bırakıldı
- `build_desktop.py`: `fetch_iddaa_odds()` fonksiyon adı — fonksiyon tarif eden isim, değiştirilmemeli
- `index.html` meta description: "iddaa oranları" ifadesi — fonksiyonel tanım, marka adı değil

### Güncellendi
- `manifest.json`: name/short_name → "FootFlow"
- `sw.js`: cache → "footflow-v50", bildirim tag/başlık → "footflow-"
- `index.html`: Başlık, apple-title, tüm server URL referansları
- `push_server.py`: Keep-alive URL, startup log
- Git remote: FootFlow repo'ya taşındı

## Bilinen Kısıtlamalar

1. **Push Abonelik Sıfırlanması:** Eski iddaatakip.onrender.com'a kayıtlı push aboneleri yeni sunucuda geçersiz. Bu kullanıcıların bildirimleri almak için yeniden abone olması gerekir.
2. **Render Free Plan Uyku:** 15 dk hareketsizlik sonrası uyur. Keep-alive (9 dk iç ping) + UptimeRobot (5 dk dış ping) çift güvence ile çözülmüş.
3. **Monolitik Frontend:** index.html 3.2 MB, build script tarafından üretilir. Doğrudan düzenleme build_desktop.py çalıştırıldığında ezilir.
4. **Sahadan Rate Limiting:** Çok hızlı istek 429 hatası verir. Retry logic ve browser başlıkları eklendi.
