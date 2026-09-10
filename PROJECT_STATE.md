# İddaa Takip - Proje Durumu ve Güncel Notlar (9 Eylül 2026)

## 📌 Canlı Sistem Bilgileri
- **GitHub Repo:** https://github.com/oktemonur7/iddaatakip.git (Branch: main)
- **Web Sitesi (GitHub Pages):** https://oktemonur7.github.io/iddaatakip/
- **Canlı Push & Sync Sunucusu (Render):** https://iddaatakip.onrender.com (Python 3)
- **Masaüstü Ana Dosya:** `/Users/onur/Desktop/futbol_ligleri.html`
- **Service Worker Önbellek Sürümü:** `iddaatakip-v43`
- **Kapsamlı Mimari & Referans Kılavuzu:** [PROJECT_ARCHITECTURE.md](./PROJECT_ARCHITECTURE.md)

---

## 🚀 Son Yapılan Kritik Düzeltmeler & Optimizasyonlar

1. **Golcü Tooltip'inde Sonsuz Bekleme Sorunu Çözüldü (CORS Hatası):**
   - `push_server.py` içinde `Access-Control-Allow-Origin: *` başlığının iki kez gönderilmesi (`*, *`) nedeniyle tarayıcıların `fetch` isteklerini engellediği tespit edildi.
   - Fazla başlık kaldırıldı, Render'a gönderildi. Artık sunucu standart tek CORS başlığı döndürüyor.

2. **Golcü Tarama Aralıkları ve Rate-Limit Koruması:**
   - İlk sorgu golden tam **10 saniye sonra** atılır (editöre yazma payı tanınır).
   - Sonraki sorgular **her 5 saniyede bir** tekrarlanır.
   - Maksimum **15 deneme** (~1.5 dk) yapılır, sonra sorgu kesilir.
   - Sunucu tarafındaki eksik maç önbelleği **5 saniye** olarak ayarlandı.

3. **Devre / Periyot Koruma Rütbesi (45+3 / İY Dalgalanması Çözüldü):**
   - Canlı soketten `İY` geldikten hemen sonra HTTP polling kanalından gelen bayat `45+3` paketlerinin devreyi geriye çekmesi engellendi (`getMatchPeriodRank`).
   - Maç zamanı tek yönlü akar: `1. Yarı -> İY -> 2. Yarı -> Uzatma -> Penaltı -> MS`.

4. **Şampiyonlar Ligi Fikstür Kilitlenmesi Çözüldü:**
   - `renderFixture` içinde `isLive` değişkeninin tanımlanmadan önce kullanılması (`ReferenceError`) düzeltildi.
   - Eleme turları açılır menüde `1. Eleme Turu`, `Play-off`, lig aşaması ise `Lig Aşaması 1. Hafta` olarak etiketlendi.

5. **Masaüstü Derlemesi & Tek Dosya Standalone Yapı:**
   - `build_desktop.py` ile `socket.io.v2.slim.js` doğrudan HTML içine gömülerek sıfır CDN bağımlılığı sağlandı.

6. **UptimeRobot & Render Uyanık Tutma (HEAD Metodu ve /health Rotası):**
   - UptimeRobot'un ücretsiz planındaki varsayılan `HEAD` sorguları için `push_server.py` RequestHandler'ına `do_HEAD` eklendi.
   - `/`, `""`, `/health` ve `/api/subscriptions` adreslerine gelen her türlü HEAD/GET sorgusu 200 OK dönecek şekilde optimize edildi. Render artık dışarıdan gelen pinglerle 7/24 kesintisiz uyanık kalır.

7. **Gol İptali (VAR) Gecikmesi Çözüldü:**
   - Gol sonrası bayat paket filtreleme süresinin (jitter koruması) hem `push_server.py` hem de `index.html` içinde 120 saniye (2 dakika) olarak tanımlandığı ve bu yüzden VAR gol iptallerini tam 2 dakika boyunca bloke ettiği tespit edildi.
   - Jitter koruma süresi 120 saniyeden 6 saniyeye çekildi. Hakem golü iptal edip Sahadan skoru düşürdüğü an sistem gecikmesiz olarak golü iptal eder, kırmızı neon flaş ve iptal sesini çalar.

8. **PWA İlk Açılışta Puan Durumu ve Fikstür Yüklenememe Sorunu Çözüldü:**
   - iPhone ve Mac PWA'larında uygulama ilk açıldığında `index.html` önbellekten (Service Worker Cache) hızlı geldiği için scriptler değerlendirilirken `document.readyState` çoktan `"interactive"` veya `"complete"` aşamasına geçmiş oluyordu.
   - Tüm ilk arayüz kurulumu (`initApp`, `loadCurrentLeague`, `renderStandings`, `renderFixture`) doğrudan `window.addEventListener("DOMContentLoaded", initApp);` dinleyicisine bağlı olduğu için `DOMContentLoaded` olayı kaçırılıyor ve tetiklenmiyordu.
   - `pageshow` ve `focus` eventleri çalıştığında ise `onAppResume` yalnızca `renderLiveScores()` çağırdığından, Ligler sekmesindeki puan durumu ve fikstür `<div class="loading-state">Puan durumu yükleniyor...</div>` durumunda asılı kalıyordu.
   - `document.readyState === "loading"` kontrolü eklendi; belge zaten yüklenmişse `initApp()` anında çalıştırılacak ve ayrıca yedek `window.addEventListener("load", ...)` koruması ile `switchMainView("leagues")` anında çağrılacak şekilde güncellendi.
   - Service Worker önbelleği `iddaatakip-v46` sürümüne yükseltildi.
