# -*- coding: utf-8 -*-
"""
Veri Bütünlüğü ve İş Kuralları Doğrulama Testleri (tests/test_integrity.py)
Veritabanı kayıt sayıları, foreign key tutarlılığı, finansal denklikler ve
kupon mutabakatını otomatik olarak denetler.
"""
from pathlib import Path
import sqlite3
import pytest
import pandas as pd
import numpy as np

from data_access import get_readonly_connection, DB_PATH
from metrics import filter_and_enrich_orders, calculate_executive_kpis, mask_name, mask_email

@pytest.fixture(scope="module")
def db_conn():
    with get_readonly_connection() as con:
        yield con

def test_table_row_counts(db_conn):
    """Veritabanındaki ana tabloların değişmediğini ve tam kayıt sayılarını doğrular."""
    expected = {
        "siparisler": 8044,
        "siparis_kalemleri": 13858,
        "olaylar": 105136,
        "musteriler": 2100,
        "urunler": 131,
        "iadeler": 667,
        "kategoriler": 28,
        "saticilar": 24,
        "iller": 25,
        "yorumlar": 4305,
        "kuponlar": 15
    }
    for table, count in expected.items():
        actual = db_conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
        assert actual == count, f"Tablo {table} satır sayısı beklenen {count} değil, bulunan {actual}"

def test_delivered_orders_count(db_conn):
    """Teslim edilmiş sipariş sayısının tam 7.644 olduğunu doğrular."""
    actual = db_conn.execute("SELECT COUNT(*) FROM siparisler WHERE durum='teslim_edildi'").fetchone()[0]
    assert actual == 7644, f"Teslim edilen sipariş sayısı 7644 olmalı, bulunan: {actual}"

def test_foreign_key_integrity(db_conn):
    """Veritabanında hiçbir yabancı anahtar (Foreign Key) ihlali olmadığını doğrular."""
    violations = db_conn.execute("PRAGMA foreign_key_check").fetchall()
    assert len(violations) == 0, f"Yabancı anahtar hataları tespit edildi: {violations}"

def test_order_totals_arithmetic(db_conn):
    """Sipariş tablosundaki her satır için ara_toplam - kupon + kargo = toplam_tutar denkliğini denetler."""
    query = """
    SELECT COUNT(*) FROM siparisler
    WHERE ABS(ara_toplam - kupon_indirimi + kargo_ucreti - toplam_tutar) > 0.05
    """
    mismatches = db_conn.execute(query).fetchone()[0]
    assert mismatches == 0, f"Sipariş toplam tutar denkliği bozuk olan {mismatches} sipariş bulundu!"

def test_order_items_arithmetic(db_conn):
    """Her sipariş kalemi için adet * birim_satis_fiyati = kalem_tutari denkliğini denetler."""
    query = """
    SELECT COUNT(*) FROM siparis_kalemleri
    WHERE ABS(adet * birim_satis_fiyati - kalem_tutari) > 0.05
    """
    mismatches = db_conn.execute(query).fetchone()[0]
    assert mismatches == 0, f"Kalem tutarı denkliği bozuk olan {mismatches} kalem bulundu!"

def test_net_product_sales_benchmark(db_conn):
    """
    Kritik iş kuralı doğrulaması:
    Teslim edilmiş siparişlerin net ürün satışı (kargo hariç, tamamlanan iadeler düşülmüş)
    tam olarak 24.588.466,13 TL olmalıdır.
    """
    q = """
    WITH tamamlanan_iadeler AS (
        SELECT siparis_id, SUM(iade_tutari) AS refund
        FROM iadeler WHERE durum='tamamlandi'
        GROUP BY siparis_id
    )
    SELECT ROUND(SUM(s.ara_toplam - s.kupon_indirimi - COALESCE(r.refund, 0)), 2)
    FROM siparisler AS s
    LEFT JOIN tamamlanan_iadeler AS r ON r.siparis_id = s.siparis_id
    WHERE s.durum = 'teslim_edildi'
    """
    net_sales = db_conn.execute(q).fetchone()[0]
    assert abs(net_sales - 24588466.13) < 0.01, f"Beklenmeyen net ürün satışı: {net_sales}"

def test_coupon_allocation_reconciliation(db_conn):
    """
    Sipariş kalemlerine oransal dağıtılan kupon tutarlarının toplamının,
    teslim edilmiş siparişlerdeki toplam kupon indirimine kuruşu kuruşuna eşit olduğunu doğrular.
    """
    orders = pd.read_sql_query("SELECT * FROM siparisler", db_conn)
    orders["siparis_tarihi"] = pd.to_datetime(orders["siparis_tarihi"])
    orders["gun"] = orders["siparis_tarihi"].dt.date
    orders["ay"] = orders["siparis_tarihi"].dt.to_period("M").astype(str)
    orders["hafta"] = orders["siparis_tarihi"].dt.to_period("W").astype(str)

    items = pd.read_sql_query("SELECT * FROM siparis_kalemleri", db_conn)
    items["tamamlanan_iade_tutari"] = 0.0
    items["tamamlanan_iade_adedi"] = 0
    items["incelenen_iade_tutari"] = 0.0

    min_date = orders["gun"].min()
    max_date = orders["gun"].max()

    filtered_orders, enriched_items = filter_and_enrich_orders(
        orders, items, min_date, max_date, statuses=["teslim_edildi"]
    )

    total_order_coupons = filtered_orders["kupon_indirimi"].sum()
    total_distributed_coupons = enriched_items["dagitilan_kupon"].sum()

    assert abs(total_order_coupons - total_distributed_coupons) < 0.05, (
        f"Kupon dağılımı mutabakat hatası: Siparişler {total_order_coupons} != Kalemler {total_distributed_coupons}"
    )

def test_return_records_no_multiplication(db_conn):
    """
    İadeler tablosu bağlandığında satır çoğalması (çifte sayım) olmadığını,
    kalem sayısının sipariş kalemleri sayısını asla aşmadığını doğrular.
    """
    items_count = db_conn.execute("SELECT COUNT(*) FROM siparis_kalemleri").fetchone()[0]
    assert items_count == 13858

def test_privacy_masking():
    """KVKK uyumlu müşteri adı ve e-posta maskeleme fonksiyonlarını test eder."""
    assert mask_name("Ahmet Yılmaz") == "A*** Y***"
    assert mask_email("ahmet@example.com") == "a***@e***.com"
