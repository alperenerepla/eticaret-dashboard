# E-Ticaret 360 • İş Zekası ve Satış Dashboard'u

Bu proje, sağlanan `eticaret.sqlite` veritabanını **salt-okunur (read-only)** modda kullanarak gerçek e-ticaret satış, ürün, kategori, müşteri, coğrafi ve iade verilerini analiz eden profesyonel bir iş zekası (BI) panelidir.

Uygulama hiçbir yapay veri üretmez; tüm metrikler ve görselleştirmeler veritabanındaki 8.044 sipariş, 13.858 sipariş kalemi ve 105.136 olay kaydına dayanır.

---

## 🚀 Hızlı Başlangıç

### 1. Uygulamayı Başlatma
Proje dizininde PowerShell veya komut satırından:

```powershell
# Streamlit uygulamasını başlatma
python -m streamlit run app.py
```

Tarayıcınızda açılacak adres:
👉 **[http://localhost:8501](http://localhost:8501)**

### 2. Veri Bütünlüğü ve Testleri Çalıştırma
Tüm iş kuralları ve mutabakat testleri pytest ile denetlenir:

```powershell
python -m pytest tests/test_integrity.py -v
```

---

## 🏗️ Proje Mimarisi

- [app.py](file:///c:/Users/LAB-HERSEK/Desktop/satis_dashboard_YENI/eticaret_dashboard/app.py): Koyu lacivert glassmorphism temalı, 8 sekmeli profesyonel Streamlit dashboard arayüzü.
- [data_access.py](file:///c:/Users/LAB-HERSEK/Desktop/satis_dashboard_YENI/eticaret_dashboard/data_access.py): SQLite salt-okunur URI (`mode=ro`) bağlantısı, `@st.cache_data` önbellek yönetimi ve güvenli veri hazırlama katmanı.
- [metrics.py](file:///c:/Users/LAB-HERSEK/Desktop/satis_dashboard_YENI/eticaret_dashboard/metrics.py): Finansal KPI'lar, kupon dağıtımı, Pareto / ABC analizi, RFM skorlaması ve KVKK müşteri maskeleme fonksiyonları.
- [insights.py](file:///c:/Users/LAB-HERSEK/Desktop/satis_dashboard_YENI/eticaret_dashboard/insights.py): Satış sıçraması anomalileri, stok tükenme riski, iade-puan alarmları ve kaçan fırsat analiz motoru.
- [tests/test_integrity.py](file:///c:/Users/LAB-HERSEK/Desktop/satis_dashboard_YENI/eticaret_dashboard/tests/test_integrity.py): 9 maddelik otomatik doğrulama test süiti.

---

## 📊 Dashboard Sekmeleri ve Özellikler

1. **📈 Genel Bakış (Executive Overview)**:
   - Net Ürün Satışı, Toplam Sipariş, Ortalama Sepet (AOV), Satılan Adet ve Tamamlanan İadeler KPI kartları.
   - Aylık Ciro ve Sipariş Trendi (Çift eksenli Plotly grafiği).
   - Platform (Web, Android, iOS) ve Ödeme Yöntemi dağılımları.
   - Haftanın günlerine ve saatlere göre sipariş yoğunluğu.

2. **🛍️ Ürün ve Kategori Analizi**:
   - Ciro liderleri ve Adet liderleri (ayrı ve net).
   - **ABC / Pareto Analizi**: Cironun %80'ini oluşturan A Grubu ürünler, %15 B Grubu ve %5 C Grubu ürünlerin interaktif Pareto eğrisi.
   - Hiyerarşik Kategori Dağılımı (Ana Kategori -> Alt Kategori Sunburst).
   - Stok, ciro, iade ve müşteri puanlarını içeren detaylı ürün tablosu.

3. **🏙️ Şehir ve Coğrafya Analizi**:
   - Türkiye haritası üzerinde illere göre sipariş yoğunluğu ve ciro kabarcık haritası.
   - Marmara, İç Anadolu, Ege vb. coğrafi bölge pazar payları.
   - İller arası ortalama sepet büyüklüğü sıralaması.

4. **👥 Müşteri ve RFM Analizi**:
   - Aktif müşteri, tekrar satın alma oranı (%32+) ve ortalama harcama.
   - **RFM Segmentasyonu**: Şampiyonlar, Sadık, Potansiyel Sadık, Kaybetme Riski, Uyuyan Müşteriler.
   - Cinsiyet ve yaş grupları harcama dağılımı.
   - Premium üye kıyaslaması ve kayıt kanalları performansı.
   - **KVKK Maskeleme**: Müşteri adları (`A*** Y***`) ve e-postaları (`a***@d***.com`) gizlenmiştir.

5. **↩️ İade Analizleri**:
   - Tamamlanan vs İncelenen iade tutarları ve başvuru sayıları.
   - İade nedenleri analizi (Kusurlu ürün, beden/numara uyumsuzluğu vb.).
   - En yüksek iade oranına sahip ürünlerin listesi ve risk değerlendirmesi.

6. **🧭 Davranış ve Dönüşüm Hunisi**:
   - Görüntüleme -> Sepete Ekleme -> Satın Alma oturum göstergesi.
   - Trafik kaynağı ve cihaz türü etkileşim matrisi.
   - **Kaçan Fırsatlar**: Yüksek ziyaret alıp düşük satın alma oranına sahip optimizasyon adayı ürünler.

7. **💡 Akıllı Bulgular (İçgörü Motoru)**:
   - **Satış Sıçramaları**: 7 günlük hareketli medyanın 2x üzerine çıkan kampanya anomali günleri.
   - **Kritik Stok Tükenme Riski**: Son 30 gün satış hızına göre stok tükenme süresi < 15 gün olan ürünler.
   - **Yüksek İade & Düşük Puan Alarmı**: İade oranı > %8 ve ortalama puanı ≤ 3.6 olan kalite riski taşıyan ürünler.
   - **Kupon Etkisi**: Kuponlu siparişlerin kuponsuzlara kıyasla ortalama sepet büyüklüğüne (%54+ artış) etkisi.
   - **Resmi Mağaza Kıyaslaması**: Yetkili satıcılar ile pazaryeri satıcılarının iade ve puan farkları.

8. **🔍 Veri Kalitesi ve Sağlık Raporu**:
   - Canlı PK/FK denetimi, tutar eşitliği kontrolü.
   - Sipariş durumları dökümü ve finansal mutabakat.
   - Doğrudan panel üzerinden canlı `pytest` çalıştırma butonu.

---

## 🔒 Kritik İş Kuralları ve Finansal Hesaplamalar

- **Net Ürün Satışı Formülü**: `(ara_toplam - kupon_indirimi) - tamamlanan_iadeler` (Kargo ücreti hariçtir). Teslim edilmiş siparişler için kuruşu kuruşuna **24.588.466,13 TL**'ye eşittir.
- **Kupon Dağıtımı**: Sipariş kuponu kalemlere `kalem_tutari / ara_toplam` oranında yansıtılarak kalem net ciroları hesaplanmıştır.
- **Çifte Sayım Koruması**: Kalemler ve iadeler birleştirildiğinde sipariş KPI'ları sipariş tablosunda tekil olarak tutulmuştur.
- **İade Ayrımı**: Tamamlanan iadeler finansal cirodan düşülür; incelenen iadeler askıda gösterilir.
- **Dönem Sınırı**: 2025-01-03 ile 2026-10-31 arasındaki gerçek operasyonel veriler kapsanmaktadır.
