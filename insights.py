# -*- coding: utf-8 -*-
"""
E-Ticaret Akıllı Bulgular ve İstatistiksel Analiz Motoru (insights.py)
Verilerdeki gizli örüntüleri, anomalileri ve kritik iş fırsatlarını ortaya çıkarır.
Her bulgunun veri dayanağını, incelenen dönemi ve eşik değerini şeffaf şekilde belgeler.
"""
import numpy as np
import pandas as pd

# -------------------------------------------------------------
# 1. Satış Sıçramaları ve Anomali Tespiti
# -------------------------------------------------------------
def detect_sales_spikes(orders: pd.DataFrame, threshold_multiple: float = 2.0) -> dict:
    """
    Günlük toplam sipariş tutarını 7 günlük hareketli medyan ile karşılaştırır.
    Eşik değer (ör. 2x ve üzeri) sıçramaları tespit eder.
    """
    if orders.empty or len(orders) < 8:
        return {"data": pd.DataFrame(), "summary": "Yetersiz veri", "threshold": f"{threshold_multiple}x"}

    daily = orders.groupby("gun", as_index=False).agg(
        siparis_sayisi=("siparis_id", "nunique"),
        toplam_tutar=("toplam_tutar", "sum"),
        kuponlu_siparis=("kupon_kodu", lambda s: (s.str.strip().str.len() > 0).sum())
    ).sort_values("gun")

    daily["hareketli_medyan"] = daily["toplam_tutar"].rolling(window=7, min_periods=4).median()
    daily["sicrama_orani"] = daily["toplam_tutar"] / daily["hareketli_medyan"].replace(0, np.nan)

    spikes = daily[daily["sicrama_orani"] >= threshold_multiple].sort_values("sicrama_orani", ascending=False).copy()
    spikes["kupon_kullanim_orani"] = (spikes["kuponlu_siparis"] / spikes["siparis_sayisi"] * 100).round(1)

    return {
        "data": spikes,
        "threshold": f"Önceki 7 aktif günün hareketli medyanının en az {threshold_multiple:.1f} katı",
        "period": f"{orders['gun'].min()} ile {orders['gun'].max()} arası",
        "count": len(spikes)
    }


# -------------------------------------------------------------
# 2. Kritik Stok Tükenme Riski (Runout Velocity)
# -------------------------------------------------------------
def detect_stockout_risk(
    products: pd.DataFrame,
    enriched_items: pd.DataFrame,
    max_date,
    lookback_days: int = 30,
    critical_days_threshold: int = 15
) -> dict:
    """
    Son N gündeki (varsayılan 30 gün) satış hızına göre mevcut stokların
    kaç günde tükeneceğini tahmin eder.
    Uyarı: Stok değeri anlık veri setinden alınır; geçmiş stok geçmişi mevcut değildir.
    """
    if enriched_items.empty:
        return {"data": pd.DataFrame(), "threshold": f"<{critical_days_threshold} gün"}

    cutoff_date = pd.Timestamp(max_date) - pd.Timedelta(days=lookback_days - 1)
    recent_items = enriched_items[enriched_items["siparis_tarihi"] >= cutoff_date]

    if recent_items.empty:
        return {"data": pd.DataFrame(), "threshold": f"<{critical_days_threshold} gün"}

    velocity = recent_items.groupby("urun_id", as_index=False).agg(
        son_donem_satilan_adet=("adet", "sum"),
        son_donem_siparis_sayisi=("siparis_id", "nunique")
    )

    actual_days = max(1, (pd.Timestamp(max_date) - cutoff_date).days + 1)
    velocity["gunluk_ortalama_satis"] = velocity["son_donem_satilan_adet"] / actual_days

    risk_df = products[[
        "urun_id", "urun_adi", "marka", "ana_kategori", "satici_adi", "stok_adedi"
    ]].merge(velocity, on="urun_id", how="left").fillna({
        "son_donem_satilan_adet": 0,
        "son_donem_siparis_sayisi": 0,
        "gunluk_ortalama_satis": 0.0
    })

    # Stok tükenme süresi
    risk_df["tahmini_stok_tukenme_gunu"] = np.where(
        risk_df["gunluk_ortalama_satis"] > 0,
        risk_df["stok_adedi"] / risk_df["gunluk_ortalama_satis"],
        np.nan
    )

    critical_df = risk_df[
        (risk_df["gunluk_ortalama_satis"] > 0) &
        (risk_df["tahmini_stok_tukenme_gunu"] <= critical_days_threshold)
    ].sort_values("tahmini_stok_tukenme_gunu", ascending=True).copy()

    return {
        "data": critical_df,
        "threshold": f"Son {lookback_days} gün satış hızına göre tahmini stok tükenme süresi ≤ {critical_days_threshold} gün",
        "period": f"{cutoff_date.date()} ile {max_date} arası ({actual_days} gün)",
        "count": len(critical_df)
    }


# -------------------------------------------------------------
# 3. Yüksek İade & Düşük Puan Uyuşmazlığı (Ürün Kalite Alarmları)
# -------------------------------------------------------------
def detect_high_return_low_rating_products(
    enriched_items: pd.DataFrame,
    min_orders: int = 15,
    return_rate_threshold: float = 8.0,
    max_rating_threshold: float = 3.6
) -> dict:
    """
    En az belirli sayıda sipariş edilmiş, iade oranı yüksek (> %8) ve
    ortalama müşteri değerlendirme puanı düşük (<= 3.6) ürünleri tespit eder.
    Bu durum ürün açıklamasında yanıltıcılık, kalite kusuru veya beden problemine işaret eder.
    """
    if enriched_items.empty:
        return {"data": pd.DataFrame()}

    prod_stats = enriched_items.groupby(
        ["urun_id", "urun_adi", "marka", "ana_kategori", "satici_adi", "ortalama_puan", "yorum_sayisi"],
        as_index=False
    ).agg(
        toplam_siparis=("siparis_id", "nunique"),
        toplam_satilan_adet=("adet", "sum"),
        toplam_iade_adedi=("tamamlanan_iade_adedi", "sum"),
        toplam_iade_tutari=("tamamlanan_iade_tutari", "sum")
    )

    prod_stats["iade_orani"] = np.where(
        prod_stats["toplam_satilan_adet"] > 0,
        prod_stats["toplam_iade_adedi"] / prod_stats["toplam_satilan_adet"] * 100,
        0.0
    )

    flagged = prod_stats[
        (prod_stats["toplam_siparis"] >= min_orders) &
        (prod_stats["iade_orani"] >= return_rate_threshold) &
        (prod_stats["ortalama_puan"] > 0) &
        (prod_stats["ortalama_puan"] <= max_rating_threshold)
    ].sort_values(["iade_orani", "ortalama_puan"], ascending=[False, True]).copy()

    return {
        "data": flagged,
        "threshold": f"Sipariş sayısı ≥ {min_orders}, İade oranı ≥ %{return_rate_threshold}, Ortalama puan ≤ {max_rating_threshold}",
        "count": len(flagged)
    }


# -------------------------------------------------------------
# 4. Yüksek İlgi - Düşük Dönüşüm (Kaçan Satış Fırsatları)
# -------------------------------------------------------------
def detect_high_traffic_low_conversion(
    events: pd.DataFrame,
    products: pd.DataFrame,
    start_date,
    end_date
) -> dict:
    """
    Olaylar tablosunda görüntülenme oturumu yüksek (75. yüzdelik dilim ve üzeri)
    olmasına rağmen satın alma oturumu oranı en düşük olan ürünleri listeler.
    Not: Bu oran kesin dönüşüm hunisi değil, oturum bazlı göreli bir sinyaldir.
    """
    if events.empty:
        return {"data": pd.DataFrame()}

    ev = events[(events["gun"] >= start_date) & (events["gun"] <= end_date)]
    if ev.empty:
        return {"data": pd.DataFrame()}

    views = ev[ev["olay_tipi"] == "urun_goruntuleme"].groupby("urun_id")["oturum_id"].nunique().rename("goruntuleme_oturum")
    carts = ev[ev["olay_tipi"] == "sepete_ekleme"].groupby("urun_id")["oturum_id"].nunique().rename("sepete_ekleme_oturum")
    buys = ev[ev["olay_tipi"] == "satin_alma"].groupby("urun_id")["oturum_id"].nunique().rename("satin_alma_oturum")

    merged = pd.concat([views, carts, buys], axis=1).fillna(0).reset_index()
    merged = merged.merge(
        products[["urun_id", "urun_adi", "marka", "ana_kategori", "satici_adi", "guncel_liste_fiyati", "stok_adedi"]],
        on="urun_id",
        how="inner"
    )

    merged["donusum_gostergesi"] = np.where(
        merged["goruntuleme_oturum"] > 0,
        merged["satin_alma_oturum"] / merged["goruntuleme_oturum"] * 100,
        0.0
    )
    merged["sepet_terk_gostergesi"] = np.where(
        merged["sepete_ekleme_oturum"] > 0,
        (merged["sepete_ekleme_oturum"] - merged["satin_alma_oturum"]) / merged["sepete_ekleme_oturum"] * 100,
        0.0
    )

    p75_view = merged["goruntuleme_oturum"].quantile(0.75)
    cutoff = max(15, int(p75_view))

    candidates = merged[merged["goruntuleme_oturum"] >= cutoff].sort_values("donusum_gostergesi", ascending=True).head(15).copy()

    return {
        "data": candidates,
        "threshold": f"Oturum görüntüleme sayısı ≥ {cutoff} (Top %25 dilim)",
        "period": f"{start_date} ile {end_date} arası",
        "count": len(candidates)
    }


# -------------------------------------------------------------
# 5. Kupon Kullanımı & Ortalama Sepet Analizi
# -------------------------------------------------------------
def analyze_coupon_basket_impact(orders: pd.DataFrame) -> dict:
    """
    Kupon kullanılan siparişler ile kupon kullanılmayan siparişleri karşılaştırır.
    Ortalama sepet tutarı (AOV), indirim erozyonu ve net katkıyı ölçer.
    """
    if orders.empty:
        return {"summary": {}, "comparison": pd.DataFrame()}

    orders_copy = orders.copy()
    orders_copy["kuponlu"] = orders_copy["kupon_kodu"].fillna("").str.strip().str.len() > 0

    grouped = orders_copy.groupby("kuponlu", as_index=False).agg(
        siparis_sayisi=("siparis_id", "nunique"),
        toplam_ara_toplam=("ara_toplam", "sum"),
        toplam_kupon_indirimi=("kupon_indirimi", "sum"),
        toplam_tutar=("toplam_tutar", "sum")
    )

    grouped["durum_adi"] = grouped["kuponlu"].map({True: "Kuponlu Siparişler", False: "Kuponsuz Siparişler"})
    grouped["ortalama_ara_toplam"] = grouped["toplam_ara_toplam"] / grouped["siparis_sayisi"]
    grouped["ortalama_net_tutar"] = grouped["toplam_tutar"] / grouped["siparis_sayisi"]
    grouped["ortalama_indirim"] = grouped["toplam_kupon_indirimi"] / grouped["siparis_sayisi"]
    grouped["indirim_orani"] = np.where(
        grouped["toplam_ara_toplam"] > 0,
        grouped["toplam_kupon_indirimi"] / grouped["toplam_ara_toplam"] * 100,
        0.0
    )

    with_coupon = grouped[grouped["kuponlu"] == True]
    without_coupon = grouped[grouped["kuponlu"] == False]

    aov_with = with_coupon["ortalama_net_tutar"].iloc[0] if not with_coupon.empty else 0.0
    aov_without = without_coupon["ortalama_net_tutar"].iloc[0] if not without_coupon.empty else 0.0
    diff_pct = ((aov_with - aov_without) / aov_without * 100) if aov_without > 0 else 0.0

    return {
        "comparison": grouped,
        "aov_with_coupon": aov_with,
        "aov_without_coupon": aov_without,
        "diff_pct": diff_pct,
        "total_coupons_applied": int(with_coupon["siparis_sayisi"].iloc[0]) if not with_coupon.empty else 0
    }


# -------------------------------------------------------------
# 6. Resmi Mağaza vs Pazaryeri Satıcı Analizi
# -------------------------------------------------------------
def analyze_official_vs_marketplace_sellers(enriched_items: pd.DataFrame) -> pd.DataFrame:
    """
    Resmi mağazalar ile normal pazaryeri satıcılarının iade oranları,
    satış hacimleri ve ortalama puanlarını karşılaştırır.
    """
    if enriched_items.empty:
        return pd.DataFrame()

    res = enriched_items.groupby("resmi_magaza", as_index=False).agg(
        satici_sayisi=("satici_id", "nunique"),
        toplam_urun_adedi=("adet", "sum"),
        net_satis=("urun_net_satis", "sum"),
        tamamlanan_iade_adedi=("tamamlanan_iade_adedi", "sum"),
        tamamlanan_iade_tutari=("tamamlanan_iade_tutari", "sum"),
        ortalama_puan=("ortalama_puan", "mean")
    )
    res["magaza_tipi"] = res["resmi_magaza"].map({1: "Resmi Mağaza (Yetkili)", 0: "Pazaryeri Satıcısı"})
    res["iade_orani_adet"] = np.where(res["toplam_urun_adedi"] > 0, res["tamamlanan_iade_adedi"] / res["toplam_urun_adedi"] * 100, 0.0)
    res["ortalama_puan"] = res["ortalama_puan"].round(2)
    return res
