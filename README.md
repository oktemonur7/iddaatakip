# Premier Lig Puan Durumu & Fikstür Uygulaması

Sahadan.com üzerindeki güncel Premier Lig verilerini çeken, canlı puan durumu ve interaktif fikstür sunan web uygulaması.

## Özellikler
- **Canlı Veri:** Sayfayı her açtığınızda veya "Yenile" butonuna bastığınızda Sahadan linkinden (`round_id=94794`) güncel veriler çekilir.
- **İnteraktif Highlight:** Fikstürde herhangi bir maç kartının üzerine geldiğinizde (hover):
  - **Ev sahibi takım** puan tablosunda **Mavi** renkle vurgulanır.
  - **Deplasman takımı** puan tablosunda **Pembe** renkle vurgulanır.
- **Haftalık Fikstür Gezinimi:** İleri/Geri butonları veya açılır menü ile ligdeki tüm haftalar arasında geçiş yapabilirsiniz.
- **Modern & Şık Arayüz:** Premier Lig temalı, responsive ve hızlı arayüz.

## Çalıştırma

Terminalden proje dizinine gidip sunucuyu başlatın:

```bash
cd premier-league-app
python3 server.py
```

Ardından tarayıcınızda açın:
👉 **[http://localhost:8080](http://localhost:8080)**
