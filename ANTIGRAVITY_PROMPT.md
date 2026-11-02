# Antigravity'ye doğrudan verilecek proje talimatı

Sen kıdemli bir Python/SQL veri mühendisi ve veri görselleştirme geliştiricisisin. Mevcut klasörde `eticaret.sqlite` veritabanı ve Python Streamlit başlangıç uygulaması `app.py` bulunuyor. Bu projeyi profesyonel, Türkçe ve etkileşimli bir e-ticaret Business Intelligence uygulamasına dönüştür. İlk önce veritabanını keşfet, tablo yapısını doğrula ve var olan uygulamayı çalıştır. Mevcut gerçek veriler dışında satış değeri **uydurma**. Veritabanına yazma ve veri üretme.

## Veri modelim

- `siparisler(siparis_id, musteri_id, siparis_tarihi, durum, iptal_nedeni, platform, odeme_yontemi, taksit_sayisi, kupon_kodu, ara_toplam, kupon_indirimi, kargo_ucreti, toplam_tutar, teslimat_il, teslimat_ilce, kargo_firmasi, kargo_tarihi, teslim_tarihi)` — 8.044 sipariş.
- `siparis_kalemleri(kalem_id, siparis_id, urun_id, adet, birim_liste_fiyati, indirim_orani, birim_satis_fiyati, kalem_tutari, kdv_orani, birim_maliyet)` — 13.858 kalem.
- `urunler(urun_id, urun_adi, marka, kategori_id, satici_id, guncel_liste_fiyati, kdv_orani, stok_adedi, eklenme_tarihi, aktif)` — 131 ürün.
- `kategoriler(kategori_id, kategori_adi, ust_kategori_id)` — 28 kategori, hiyerarşik.
- `saticilar(satici_id, satici_adi, il, katilim_tarihi, resmi_magaza)` — 24 satıcı.
- `musteriler(musteri_id, ad, soyad, cinsiyet, dogum_yili, e_posta, il, ilce, kayit_tarihi, kayit_kanali, premium_uye, eposta_izni)` — 2.100 müşteri.
- `iller(il, bolge, enlem, boylam)` — 25 il.
- `iadeler(iade_id, kalem_id, siparis_id, talep_tarihi, iade_nedeni, iade_adedi, iade_tutari, durum)` — 667 iade kaydı.
- `olaylar(olay_id, oturum_id, musteri_id, urun_id, olay_tipi, olay_zamani, cihaz, trafik_kaynagi, siparis_id)` — 105.136 olay.
- `yorumlar(yorum_id, urun_id, musteri_id, kalem_id, puan, yorum_metni, yorum_tarihi, faydali_oy_sayisi)` — 4.305 yorum.
- `kuponlar(kupon_kodu, aciklama, indirim_tipi, indirim_degeri, min_sepet_tutari, baslangic_tarihi, bitis_tarihi)` — 15 kupon.

## Uygulama hedefi

İlk aşamada mevcut **Python + Streamlit + Plotly + SQLite** kodunu iyileştir. Daha sonra gerekli olursa arayüzü ayrı React/Next.js frontend ve FastAPI backend olarak modülerleştirebiliriz; ancak veri doğruluğu ve çalışan basit proje önceliklidir. Koyu lacivert premium tema, okunaklı kartlar, mobil uyumlu tasarım, TL para birimi ve Türkçe sayı biçimi oluştur.

Dashboard sekmeleri:
1. Genel Bakış: net ürün satışı, sipariş sayısı, AOV, adet, aylık trend, dönem karşılaştırması.
2. Ürünler: adet ve ciro sıralaması ayrı; satıcı/kategori alt kırılımı; ABC/Pareto analizi; satış / stok ilişkisi.
3. Bölgeler: il ve bölge bazında sipariş, ciro, harita.
4. Müşteriler: yeni/tekrar müşteri, RFM (recency-frequency-monetary), satın alma tekrar oranı. Kişisel bilgileri gizle.
5. İadeler: tamamlanan vs incelenen, ürün bazlı iade adedi ve nedeni, en yüksek iade oranlı ürünler.
6. Davranış: oturum bazında görüntüleme, sepete ekleme, satın alma sinyalleri; trafik kaynağı / cihaz; yüksek ilgi–düşük dönüşüm adayları.
7. Akıllı Bulgular: sipariş tutarında ani sıçrama, stok tükenme riski, yüksek iade düşük puan, yüksek görüntülenme düşük satın alma, düşen kategori, kupon kullanımı ve ortalama sepet ilişkisi. Her bulguyu *hangi veriye, döneme, eşik değerine dayandırdığını* göster. Korelasyonu neden-sonuç diye sunma.
8. Veri Kalitesi: mükerrer PK, bozuk FK, eksik veri, sipariş ve kalem toplamı uyuşmazlıkları, sıra dışı tarih ve sayısal değerleri denetle.

Filtreler: sipariş başlangıç/bitiş tarihi, durum, şehir, platform; grafikteki veriye uygun kategori ve satıcı filtreleri. İlgili tablolara filtreler doğru uygulanmalı. CSV indirme ve isteğe bağlı PDF rapor eklenebilir.

## Kritik iş kuralları

1. **İptalleri ciroya katma.** Varsayılan yalnızca `durum='teslim_edildi'`. `hazirlaniyor` ve `kargoda` da gerçekleşmiş ciro sayılmamalı.
2. `siparis_kalemleri` ile join sonrasında `siparisler.toplam_tutar` veya `kupon_indirimi` tekrar toplanırsa çifte sayım olur. Sipariş KPI'sı sipariş tablosunda kalmalı. Ürün geliri için sipariş kuponunu satırlara `kalem_tutari / ara_toplam` oranında dağıt.
3. Net ürün satışı = teslim edilmiş siparişlerin `(ara_toplam - kupon_indirimi)` toplamı − **tamamlanan** iadelerin `iade_tutari` toplamı. Kargo hariç. Bunun için birim/maliyet, KDV, iadeli stok geri kazanımı vb. bilinmeden **muhasebesel net kâr** deme.
4. İade kayıtlarını `kalem_id` bazında gruplayıp sonra kalemler ile join et; satır çoğalmasını önle. İade talebi ve tamamlanan iade ayrımını koru.
5. `olaylar`'daki `satin_alma` kayıtları kalem/ürün bazlıdır; toplam satın alma olayını sipariş sayısı diye gösterme. Oturum hunisinin aşamalarını aynı oturumda, doğru sıralı olaylarla mümkünse doğrula. Eğer yalnızca ayrı oturum sayıları raporlanıyorsa buna **gösterge** de, doğrulanmış dönüşüm hunisi deme.
6. Veri tarihlerini veri setinden belirle, sistem tarihini değil. Siparişler 2025-01-03 ile 2026-10-31 arası. Bugün ile arada veri yoksa kesintiyi göster.
7. Kategoriler hiyerarşik; alt kategori ve üst kategori ayrımını açıkça etiketle.
8. Şehir bilgisi siparişin `teslimat_il` sütunundan gelmeli; müşteri kayıt ilinden değil. Olaylar tablosunda şehir/platform olmadığından oraya bu filtreyi otomatik uygulama.
9. Stok sayısı güncel bir anlık değer, geçmiş dönem stok bilgisi değil. Geçmiş satış hızına dayanan stok öngörüsü belirsiz olarak etiketlenmeli.
10. Her sorguda NULL güvenliği, temel testler, parametrik SQL veya güvenli DataFrame filtreleri kullan. SQLite veritabanını yalnızca salt okunur aç. Müşteri ad/e-postalarını gereksiz yere UI'da ifşa etme.

## İş sırası ve kabul ölçütleri

1. Tabloları, alanları, kayıt sayılarını, ilişkileri ve örnek sorguları incele.
2. Mevcut `app.py` uygulamasını çalıştır ve hataları gider.
3. Ayrı `data_access.py`, `metrics.py`, `insights.py` ve `tests/` modüllerine uygun şekilde ayır. İdeal olarak filtreler için tek, açık ve test edilebilir veri modeli kullan.
4. En az şu kontrolleri otomatik test et: 8.044 sipariş, 13.858 kalem, 105.136 olay, 7644 teslim edilmiş sipariş, tüm siparişlerin kalem-tutar eşitliği, iptallerin satış filtresine girmemesi, iadelerin çoğaltılmaması, kupon dağılımının sipariş indirimiyle mutabakatı, tarihin uç değerleri.
5. Gerçek veriyle etkileşimli dashboard'u aç ve filtreleri dene. Kullanıcıya tam çalıştırma komutlarını ve dosya yapısını README'de açıkla.
6. Sahte demo sayılarını kaldır; grafikler yalnızca kaynak SQLite'tan beslensin.

Beklenen çıktı: Hata vermeden açılan, hızlı çalışan, filtrelenebilir, veri doğruluğu belgelenmiş profesyonel e-ticaret analitik paneli. Sorunla karşılaşırsan hata mesajını göster, veriyi varsayarak düzeltme.
