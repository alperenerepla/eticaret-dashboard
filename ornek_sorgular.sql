-- 1) Gerçekleşmiş siparişlerin net ürün satışı (kargo hariç, iadeler düşülmüş)
WITH tamamlanan_iadeler AS (
 SELECT i.siparis_id, SUM(i.iade_tutari) AS iade_tutari
 FROM iadeler AS i WHERE i.durum = 'tamamlandi'
 GROUP BY i.siparis_id
)
SELECT COUNT(*) AS teslim_edilen_siparis_sayisi,
 ROUND(SUM(s.ara_toplam - s.kupon_indirimi),2) AS kupon_sonrasi_urun_satisi,
 ROUND(SUM(COALESCE(i.iade_tutari, 0)),2) AS tamamlanan_iadeler,
 ROUND(SUM(s.ara_toplam - s.kupon_indirimi - COALESCE(i.iade_tutari, 0)),2) AS net_urun_satisi
FROM siparisler s
LEFT JOIN tamamlanan_iadeler i ON i.siparis_id = s.siparis_id
WHERE s.durum='teslim_edildi';

-- 2) Adet ve brüt ürün satış tutarına göre ilk 10 ürün
SELECT u.urun_id, u.urun_adi, SUM(k.adet) AS satilan_adet,
 ROUND(SUM(k.kalem_tutari),2) AS brut_urun_satisi
FROM siparis_kalemleri k
JOIN siparisler s ON s.siparis_id=k.siparis_id
JOIN urunler u ON u.urun_id=k.urun_id
WHERE s.durum='teslim_edildi'
GROUP BY u.urun_id, u.urun_adi
ORDER BY brut_urun_satisi DESC LIMIT 10;

-- 3) Teslimat iline göre gerçekleşmiş siparişler
SELECT teslimat_il, COUNT(*) AS siparis_sayisi,
 ROUND(SUM(toplam_tutar),2) AS toplam_siparis_tutari
FROM siparisler WHERE durum='teslim_edildi'
GROUP BY teslimat_il ORDER BY toplam_siparis_tutari DESC;

-- 4) İade sebepleri: tamamlanma durumu ayrı gösterilir
SELECT durum, iade_nedeni, COUNT(*) AS basvuru,
 SUM(iade_adedi) AS iade_adedi, ROUND(SUM(iade_tutari),2) AS iade_tutari
FROM iadeler GROUP BY durum, iade_nedeni ORDER BY basvuru DESC;

-- 5) Olay türü bazında olay ve BENZERSİZ oturum sayısı
SELECT olay_tipi, COUNT(*) AS olay_sayisi,
 COUNT(DISTINCT oturum_id) AS oturum_sayisi
FROM olaylar GROUP BY olay_tipi ORDER BY olay_sayisi DESC;
