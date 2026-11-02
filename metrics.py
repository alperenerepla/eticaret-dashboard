# -*- coding: utf-8 -*-
"""
E-Ticaret Metrik ve Hesaplama Modülü (metrics.py)
Kritik iş kurallarına tam uyumlu finansal, ürün, müşteri ve iade metriklerini hesaplar.
"""
import numpy as np
import pandas as pd

# -------------------------------------------------------------
# Biçimlendirme Yardımcıları (Türkçe Yerelleştirme)
# -------------------------------------------------------------
def format_currency(val: float | int | None) -> str:
    """Türk Lirası biçimlendirmesi: 24.588.466,13 TL"""
    if val is None or pd.isna(val):
        return "0,00 TL"
    s = f"{float(val):,.2f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".") + " TL"

def format_integer(val: float | int | None) -> str:
    """Tam sayı biçimlendirmesi: 7.644"""
    if val is None or pd.isna(val):
        return "0"
    s = f"{int(val):,}"
    return s.replace(",", ".")

def format_percent(val: float | int | None) -> str:
    """Yüzde biçimlendirmesi: %18,5"""
    if val is None or pd.isna(val):
        return "%0,0"
    s = f"{float(val):.1f}"
    return f"%{s.replace('.', ',')}"

def format_decimal(val: float | int | None, decimals: int = 2) -> str:
    """Ondalık sayı biçimlendirmesi: 1.234,56"""
    if val is None or pd.isna(val):
        return "0,00"
    fmt = f"{{:,.{decimals}f}}"
    s = fmt.format(float(val))
    return s.replace(",", "X").replace(".", ",").replace("X", ".")

def mask_name(name: str | None) -> str:
    """KVKK uyumlu ad maskeleme: 'Ahmet Yılmaz' -> 'A*** Y***'"""
    if not name or pd.isna(name):
        return "***"
    parts = str(name).strip().split()
    masked = [p[0].upper() + "***" if len(p) > 0 else "***" for p in parts]
    return " ".join(masked)

def mask_email(email: str | None) -> str:
    """KVKK uyumlu e-posta maskeleme: 'ahmet@example.com' -> 'a***@e***.com'"""
    if not email or pd.isna(email) or "@" not in str(email):
        return "***@***.com"
    parts = str(email).strip().split("@")
    user = parts[0]
    domain_parts = parts[1].split(".")
    masked_user = user[0] + "***" if len(user) > 0 else "***"
    masked_domain = domain_parts[0][0] + "***" if len(domain_parts[0]) > 0 else "***"
    ext = ".".join(domain_parts[1:]) if len(domain_parts) > 1 else "com"
    return f"{masked_user}@{masked_domain}.{ext}"


# -------------------------------------------------------------
# Sipariş ve Kalem Filtreleme & Birleştirme
# -------------------------------------------------------------
def filter_and_enrich_orders(
    orders: pd.DataFrame,
    items: pd.DataFrame,
    start_date,
    end_date,
    statuses: list[str],
    cities: list[str] | None = None,
    platforms: list[str] | None = None,
    categories: list[str] | None = None,
    sellers: list[str] | None = None
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Kullanıcı filtrelerine göre sipariş ve kalemleri filtreler.
    Kritik kural: Kupon indirimi sipariş kalemlerine 'kalem_tutari / ara_toplam' oranında dağıtılır.
    Kritik kural: Yalnızca teslim edilen siparişler ve tamamlanan iadeler finansal ciroya yansır.
    """
    # Sipariş seviyesi filtre
    mask = (orders["gun"] >= start_date) & (orders["gun"] <= end_date)
    if statuses:
        mask &= orders["durum"].isin(statuses)
    if cities:
        mask &= orders["teslimat_il"].isin(cities)
    if platforms:
        mask &= orders["platform"].isin(platforms)

    filtered_orders = orders.loc[mask].copy()

    if filtered_orders.empty:
        return filtered_orders, pd.DataFrame()

    # Kalemleri bağla
    order_cols = [
        "siparis_id", "musteri_id", "siparis_tarihi", "gun", "ay", "hafta",
        "durum", "teslimat_il", "teslimat_ilce", "platform", "odeme_yontemi",
        "ara_toplam", "kupon_indirimi", "kargo_ucreti", "toplam_tutar"
    ]
    enriched_items = items.merge(
        filtered_orders[order_cols],
        on="siparis_id",
        how="inner"
    )

    # İsteğe bağlı kategori ve satıcı filtresi
    if categories:
        enriched_items = enriched_items[enriched_items["ana_kategori"].isin(categories) | enriched_items["alt_kategori"].isin(categories)]
    if sellers:
        enriched_items = enriched_items[enriched_items["satici_adi"].isin(sellers)]

    # Kupon dağıtımı (Kritik kural 2):
    # Sipariş kuponunu satırlara kalem_tutari / ara_toplam oranında dağıt
    safe_ratio = np.where(enriched_items["ara_toplam"] > 0, enriched_items["kalem_tutari"] / enriched_items["ara_toplam"], 0.0)
    enriched_items["dagitilan_kupon"] = safe_ratio * enriched_items["kupon_indirimi"]

    # Ürün net satışı (Kritik kural 3):
    # Bir kalemin net geliri = kalem_tutari - dagitilan_kupon - tamamlanan_iade
    enriched_items["urun_net_satis"] = enriched_items["kalem_tutari"] - enriched_items["dagitilan_kupon"] - enriched_items["tamamlanan_iade_tutari"]

    # Tahmini brüt kâr katkısı (birim maliyet bilindiği kadarıyla)
    enriched_items["tahmini_katki"] = enriched_items["urun_net_satis"] - (enriched_items["adet"] * enriched_items["birim_maliyet"])

    return filtered_orders, enriched_items


# -------------------------------------------------------------
# Özet KPI Hesaplama
# -------------------------------------------------------------
def calculate_executive_kpis(filtered_orders: pd.DataFrame, enriched_items: pd.DataFrame) -> dict:
    """
    Yönetici paneli için temel finansal ve operasyonel KPI'ları hesaplar.
    """
    if filtered_orders.empty:
        return {
            "net_urun_satisi": 0.0,
            "brut_urun_satisi": 0.0,
            "toplam_siparis_sayisi": 0,
            "satilan_toplam_adet": 0,
            "ortalama_sepet": 0.0,
            "tamamlanan_iade_tutari": 0.0,
            "tamamlanan_iade_adedi": 0,
            "incelenen_iade_tutari": 0.0,
            "toplam_kupon_indirimi": 0.0,
            "kargo_ucreti_toplami": 0.0,
            "toplam_tutar_musteri": 0.0,
            "iade_orani_ciro": 0.0,
            "iade_orani_adet": 0.0,
            "tahmini_katki_payi": 0.0
        }

    # Sipariş tablosundan hesaplananlar (Çifte sayım engellenir)
    order_count = filtered_orders["siparis_id"].nunique()
    total_order_value = float(filtered_orders["toplam_tutar"].sum())
    total_subtotal = float(filtered_orders["ara_toplam"].sum())
    total_coupon_discount = float(filtered_orders["kupon_indirimi"].sum())
    total_shipping = float(filtered_orders["kargo_ucreti"].sum())

    # Kalem tablosundan hesaplananlar
    if not enriched_items.empty:
        total_items_sold = int(enriched_items["adet"].sum())
        gross_product_sales = float(enriched_items["kalem_tutari"].sum())
        completed_refund_total = float(enriched_items["tamamlanan_iade_tutari"].sum())
        completed_refund_items = int(enriched_items["tamamlanan_iade_adedi"].sum())
        pending_refund_total = float(enriched_items["incelenen_iade_tutari"].sum())
        tahmini_katki = float(enriched_items["tahmini_katki"].sum())
    else:
        total_items_sold = 0
        gross_product_sales = 0.0
        completed_refund_total = 0.0
        completed_refund_items = 0
        pending_refund_total = 0.0
        tahmini_katki = 0.0

    # Net ürün satışı = Teslim edilmiş siparişlerin (ara_toplam - kupon_indirimi) - tamamlanan iadeler
    # (Kargo hariç, kural 3)
    net_product_sales = (total_subtotal - total_coupon_discount) - completed_refund_total

    aov = total_order_value / order_count if order_count > 0 else 0.0
    refund_rate_rev = (completed_refund_total / (total_subtotal - total_coupon_discount) * 100) if (total_subtotal - total_coupon_discount) > 0 else 0.0
    refund_rate_qty = (completed_refund_items / total_items_sold * 100) if total_items_sold > 0 else 0.0

    return {
        "net_urun_satisi": net_product_sales,
        "brut_urun_satisi": gross_product_sales,
        "toplam_siparis_sayisi": order_count,
        "satilan_toplam_adet": total_items_sold,
        "ortalama_sepet": aov,
        "tamamlanan_iade_tutari": completed_refund_total,
        "tamamlanan_iade_adedi": completed_refund_items,
        "incelenen_iade_tutari": pending_refund_total,
        "toplam_kupon_indirimi": total_coupon_discount,
        "kargo_ucreti_toplami": total_shipping,
        "toplam_tutar_musteri": total_order_value,
        "iade_orani_ciro": refund_rate_rev,
        "iade_orani_adet": refund_rate_qty,
        "tahmini_katki_payi": tahmini_katki
    }


# -------------------------------------------------------------
# ABC / Pareto Analizi
# -------------------------------------------------------------
def calculate_abc_pareto(enriched_items: pd.DataFrame) -> pd.DataFrame:
    """
    Ürünleri net satış tutarına göre sıralar, kümülatif payı hesaplar ve
    ABC segmentlerine ayırır:
    A: Cironun ilk %80'ini oluşturan hayati ürünler
    B: Sonraki %15'i oluşturan ürünler (%80-%95)
    C: Kalan %5'i oluşturan kuyruktaki ürünler
    """
    if enriched_items.empty:
        return pd.DataFrame()

    prod_summary = enriched_items.groupby(
        ["urun_id", "urun_adi", "marka", "ana_kategori", "alt_kategori", "satici_adi", "stok_adedi", "ortalama_puan"],
        as_index=False
    ).agg(
        toplam_adet=("adet", "sum"),
        brut_satis=("kalem_tutari", "sum"),
        net_satis=("urun_net_satis", "sum"),
        iade_adedi=("tamamlanan_iade_adedi", "sum"),
        iade_tutari=("tamamlanan_iade_tutari", "sum")
    ).sort_values("net_satis", ascending=False)

    total_net = prod_summary["net_satis"].sum()
    if total_net > 0:
        prod_summary["ciro_payi"] = prod_summary["net_satis"] / total_net
        prod_summary["kumulatif_pay"] = prod_summary["ciro_payi"].cumsum()
    else:
        prod_summary["ciro_payi"] = 0.0
        prod_summary["kumulatif_pay"] = 0.0

    def assign_abc(kum_pay):
        if kum_pay <= 0.80:
            return "A (Hayati %80)"
        elif kum_pay <= 0.95:
            return "B (Önemli %15)"
        else:
            return "C (Kuyruk %5)"

    prod_summary["abc_sinifi"] = prod_summary["kumulatif_pay"].apply(assign_abc)
    prod_summary["iade_orani"] = np.where(
        prod_summary["toplam_adet"] > 0,
        prod_summary["iade_adedi"] / prod_summary["toplam_adet"] * 100,
        0.0
    )

    return prod_summary


# -------------------------------------------------------------
# RFM Segmentasyonu
# -------------------------------------------------------------
def calculate_rfm_segments(orders: pd.DataFrame, customers: pd.DataFrame) -> pd.DataFrame:
    """
    Müşterileri Recency (Yenilik), Frequency (Sıklık) ve Monetary (Parasal Değer)
    metriklerine göre skorlar ve Türkçe segmentlere ayırır.
    Kişisel veriler (ad, soyad, e-posta) maskelenir.
    """
    if orders.empty:
        return pd.DataFrame()

    # Referans tarih siparişlerin en son tarihi
    ref_date = orders["siparis_tarihi"].max()

    rfm = orders.groupby("musteri_id", as_index=False).agg(
        son_siparis=("siparis_tarihi", "max"),
        siparis_sayisi=("siparis_id", "nunique"),
        toplam_harcama=("toplam_tutar", "sum")
    )

    rfm["recency_gun"] = (ref_date - rfm["son_siparis"]).dt.days
    rfm["frequency"] = rfm["siparis_sayisi"]
    rfm["monetary"] = rfm["toplam_harcama"]

    # 1-5 arası skorlama (qcut veya rank tabanlı)
    # Recency: daha az gün daha yüksek skor (5)
    rfm["r_skor"] = pd.qcut(rfm["recency_gun"].rank(method="first", ascending=False), 5, labels=[1, 2, 3, 4, 5]).astype(int)
    rfm["f_skor"] = pd.qcut(rfm["frequency"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
    rfm["m_skor"] = pd.qcut(rfm["monetary"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
    rfm["rfm_skor"] = rfm["r_skor"].astype(str) + rfm["f_skor"].astype(str) + rfm["m_skor"].astype(str)

    # Segment atama
    def assign_segment(row):
        r, f = row["r_skor"], row["f_skor"]
        if r >= 4 and f >= 4:
            return "Şampiyonlar"
        elif r >= 3 and f >= 3:
            return "Sadık Müşteriler"
        elif r >= 4 and f <= 2:
            return "Yeni Müşteriler"
        elif r >= 3 and f <= 2:
            return "Potansiyel Sadık"
        elif r <= 2 and f >= 4:
            return "Kaybetme Riski Olanlar"
        elif r <= 2 and f >= 2:
            return "Uyuyan Müşteriler"
        else:
            return "Terk Edenler"

    rfm["segment"] = rfm.apply(assign_segment, axis=1)

    # Müşteri detaylarını bağla ve maskele
    rfm = rfm.merge(customers, on="musteri_id", how="left")
    rfm["ad_maskeli"] = rfm["ad"].apply(mask_name)
    rfm["soyad_maskeli"] = rfm["soyad"].apply(mask_name)
    rfm["musteri_gorunen_ad"] = rfm["ad_maskeli"] + " " + rfm["soyad_maskeli"]
    rfm["eposta_maskeli"] = rfm["e_posta"].apply(mask_email)

    return rfm
