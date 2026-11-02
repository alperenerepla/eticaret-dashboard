# -*- coding: utf-8 -*-
"""
E-Ticaret Veri Erişim Modülü (data_access.py)
SQLite veritabanına salt-okunur (read-only) erişim sağlar ve
verileri bellek içi analiz için optimize edilmiş formatta sunar.
"""
from pathlib import Path
import sqlite3
import pandas as pd
import streamlit as st

DB_PATH = Path(__file__).parent / "eticaret.sqlite"

def get_readonly_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Veritabanına salt okunur URI bağlantısı açar."""
    if not db_path.exists():
        raise FileNotFoundError(f"Veritabanı dosyası bulunamadı: {db_path}")
    return sqlite3.connect(f"file:{db_path.resolve()}?mode=ro", uri=True)

@st.cache_data(show_spinner="Veritabanı yükleniyor...")
def load_raw_data(db_mtime: float) -> dict[str, pd.DataFrame]:
    """Tüm SQLite tablolarını salt okunur olarak okur ve DataFrame sözlüğü döner."""
    with get_readonly_connection() as con:
        tables = [
            "siparisler", "siparis_kalemleri", "urunler", "kategoriler",
            "saticilar", "musteriler", "iller", "iadeler", "olaylar",
            "yorumlar", "kuponlar"
        ]
        data = {}
        for table in tables:
            data[table] = pd.read_sql_query(f'SELECT * FROM "{table}"', con)
    return data

@st.cache_data(show_spinner="Veri modelleri hazırlanıyor...")
def get_prepared_data(db_mtime: float) -> dict[str, pd.DataFrame]:
    """
    İş kurallarına uygun olarak hazırlanmış, zenginleştirilmiş ve
    temizlenmiş tabloları döner.
    """
    raw = load_raw_data(db_mtime)

    # 1. Siparişler
    orders = raw["siparisler"].copy()
    orders["siparis_tarihi"] = pd.to_datetime(orders["siparis_tarihi"])
    orders["gun"] = orders["siparis_tarihi"].dt.date
    orders["ay"] = orders["siparis_tarihi"].dt.to_period("M").astype(str)
    orders["hafta"] = orders["siparis_tarihi"].dt.to_period("W").astype(str)
    orders["saat"] = orders["siparis_tarihi"].dt.hour
    orders["gun_adi"] = orders["siparis_tarihi"].dt.day_name()
    tr_days = {
        "Monday": "Pazartesi", "Tuesday": "Salı", "Wednesday": "Çarşamba",
        "Thursday": "Perşembe", "Friday": "Cuma", "Saturday": "Cumartesi", "Sunday": "Pazar"
    }
    orders["gun_adi_tr"] = orders["gun_adi"].map(tr_days)

    # 2. Kategoriler Hiyerarşisi
    cats = raw["kategoriler"].copy()
    parents = cats[cats["ust_kategori_id"].isna()][["kategori_id", "kategori_adi"]].rename(
        columns={"kategori_id": "ust_kat_id", "kategori_adi": "ust_kategori_adi"}
    )
    cats = cats.merge(parents, left_on="ust_kategori_id", right_on="ust_kat_id", how="left")
    cats["ana_kategori"] = cats["ust_kategori_adi"].fillna(cats["kategori_adi"])
    cats["alt_kategori"] = cats["kategori_adi"]

    # 3. Yorumlar Özeti (Ürün bazında ortalama puan ve yorum sayısı)
    reviews_summary = raw["yorumlar"].groupby("urun_id", as_index=False).agg(
        ortalama_puan=("puan", "mean"),
        yorum_sayisi=("yorum_id", "count")
    )
    reviews_summary["ortalama_puan"] = reviews_summary["ortalama_puan"].round(2)

    # 4. Ürünler
    products = raw["urunler"].copy()
    products = products.merge(cats[["kategori_id", "kategori_adi", "ana_kategori", "alt_kategori"]], on="kategori_id", how="left")
    products = products.merge(raw["saticilar"][["satici_id", "satici_adi", "resmi_magaza", "il"]].rename(columns={"il": "satici_ili"}), on="satici_id", how="left")
    products = products.merge(reviews_summary, on="urun_id", how="left")
    products["ortalama_puan"] = products["ortalama_puan"].fillna(0.0)
    products["yorum_sayisi"] = products["yorum_sayisi"].fillna(0).astype(int)

    # 5. İadeler (Kalem bazında gruplanmış - Çifte sayımı önlemek için kritik kural)
    returns_completed = raw["iadeler"].query("durum == 'tamamlandi'").groupby("kalem_id", as_index=False).agg(
        tamamlanan_iade_tutari=("iade_tutari", "sum"),
        tamamlanan_iade_adedi=("iade_adedi", "sum")
    )
    returns_pending = raw["iadeler"].query("durum == 'inceleniyor'").groupby("kalem_id", as_index=False).agg(
        incelenen_iade_tutari=("iade_tutari", "sum"),
        incelenen_iade_adedi=("iade_adedi", "sum")
    )
    returns_all_by_item = raw["iadeler"].groupby("kalem_id", as_index=False).agg(
        toplam_iade_talebi_tutari=("iade_tutari", "sum"),
        toplam_iade_talebi_adedi=("iade_adedi", "sum"),
        iade_kayit_sayisi=("iade_id", "count")
    )

    # 6. Sipariş Kalemleri
    items = raw["siparis_kalemleri"].copy()
    items = items.merge(
        products[[
            "urun_id", "urun_adi", "marka", "kategori_id", "ana_kategori", "alt_kategori",
            "satici_id", "satici_adi", "resmi_magaza", "stok_adedi", "guncel_liste_fiyati",
            "ortalama_puan", "yorum_sayisi"
        ]],
        on="urun_id",
        how="left"
    )
    # İade bilgilerini kalemlere bağla
    items = items.merge(returns_completed, on="kalem_id", how="left")
    items = items.merge(returns_pending, on="kalem_id", how="left")
    items = items.merge(returns_all_by_item, on="kalem_id", how="left")
    items["tamamlanan_iade_tutari"] = items["tamamlanan_iade_tutari"].fillna(0.0)
    items["tamamlanan_iade_adedi"] = items["tamamlanan_iade_adedi"].fillna(0).astype(int)
    items["incelenen_iade_tutari"] = items["incelenen_iade_tutari"].fillna(0.0)
    items["incelenen_iade_adedi"] = items["incelenen_iade_adedi"].fillna(0).astype(int)
    items["toplam_iade_talebi_tutari"] = items["toplam_iade_talebi_tutari"].fillna(0.0)
    items["toplam_iade_talebi_adedi"] = items["toplam_iade_talebi_adedi"].fillna(0).astype(int)

    # 7. Müşteriler (Yaş hesabı ve maskeleme hazırlığı)
    customers = raw["musteriler"].copy()
    # Referans veri yılı olarak siparişlerin son yılı olan 2026 alınır
    customers["yas"] = 2026 - customers["dogum_yili"]
    customers["yas_grubu"] = pd.cut(
        customers["yas"],
        bins=[0, 24, 34, 44, 54, 100],
        labels=["18-24", "25-34", "35-44", "45-54", "55+"]
    )

    # 8. İller ve Coğrafya
    cities = raw["iller"].copy()

    # 9. Olaylar
    events = raw["olaylar"].copy()
    events["olay_zamani"] = pd.to_datetime(events["olay_zamani"])
    events["gun"] = events["olay_zamani"].dt.date
    events["saat"] = events["olay_zamani"].dt.hour
    events["gun_adi"] = events["olay_zamani"].dt.day_name().map(tr_days)

    return {
        "raw": raw,
        "orders": orders,
        "items": items,
        "products": products,
        "categories": cats,
        "customers": customers,
        "cities": cities,
        "returns": raw["iadeler"].copy(),
        "events": events,
        "reviews": raw["yorumlar"].copy(),
        "coupons": raw["kuponlar"].copy(),
        "sellers": raw["saticilar"].copy()
    }
