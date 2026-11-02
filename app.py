# -*- coding: utf-8 -*-
"""
E-Ticaret 360: Profesyonel, Modern ve İnteraktif Satış Dashboard'u
SQLite veritabanı üzerinden gerçek zamanlı analitik, içgörüler ve veri kalitesi denetimi.
"""
from pathlib import Path
import subprocess
import sys
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from data_access import DB_PATH, get_prepared_data
from metrics import (
    format_currency, format_integer, format_percent, format_decimal,
    filter_and_enrich_orders, calculate_executive_kpis,
    calculate_abc_pareto, calculate_rfm_segments
)
from insights import (
    detect_sales_spikes, detect_stockout_risk,
    detect_high_return_low_rating_products, detect_high_traffic_low_conversion,
    analyze_coupon_basket_impact, analyze_official_vs_marketplace_sellers
)

# -------------------------------------------------------------
# Streamlit Sayfa Yapılandırması ve Premium Tema CSS
# -------------------------------------------------------------
st.set_page_config(
    page_title="E-Ticaret 360 • İş Zekası ve Satış Paneli",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded"
)

CUSTOM_CSS = """
<style>
/* Ana zemin ve genel tipografi */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    color: #f1f5f9;
}

.stApp {
    background: radial-gradient(circle at 15% 15%, #0f1c3d 0%, #091226 50%, #050a17 100%);
    color: #f8fafc;
}

/* Konteyner daraltma ve padding */
.block-container {
    padding-top: 1.4rem;
    padding-bottom: 3rem;
    max-width: 1580px;
}

/* Başlıklar - Yüksek Kontrast ve Belirgin Boyutlar */
h1 {
    color: #ffffff !important;
    font-size: 2.3rem !important;
    font-weight: 800 !important;
    letter-spacing: -0.6px !important;
}

h2 {
    color: #ffffff !important;
    font-size: 1.85rem !important;
    font-weight: 700 !important;
}

h3 {
    color: #38bdf8 !important;
    font-size: 1.5rem !important;
    font-weight: 700 !important;
    margin-top: 0.8rem !important;
}

h4 {
    color: #ffffff !important;
    font-size: 1.35rem !important;
    font-weight: 700 !important;
    margin-top: 0.6rem !important;
    margin-bottom: 0.6rem !important;
}

h5 {
    color: #38bdf8 !important;
    font-size: 1.18rem !important;
    font-weight: 600 !important;
}

/* Paragraf ve Genel Metinler - Okunabilir 16.5px */
p, .stMarkdown p {
    font-size: 1.04rem !important;
    color: #f1f5f9 !important;
    line-height: 1.65 !important;
    font-weight: 400 !important;
}

/* Açıklama ve Dipnotlar (Captions) - Solukluk giderildi */
.stCaption, [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {
    font-size: 0.95rem !important;
    color: #cbd5e1 !important;
    line-height: 1.55 !important;
    font-weight: 450 !important;
}

/* Üst Başlık Banner */
.main-header {
    background: linear-gradient(135deg, rgba(22, 40, 82, 0.95) 0%, rgba(13, 24, 54, 0.98) 100%);
    border: 1.5px solid rgba(56, 189, 248, 0.35);
    border-radius: 16px;
    padding: 24px 30px;
    margin-bottom: 1.6rem;
    backdrop-filter: blur(14px);
    box-shadow: 0 10px 35px 0 rgba(0, 0, 0, 0.55);
}

.main-title {
    font-size: 2.25rem !important;
    font-weight: 800 !important;
    letter-spacing: -0.6px;
    background: linear-gradient(90deg, #ffffff 0%, #38bdf8 65%, #a5b4fc 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 0;
    line-height: 1.25;
}

.sub-title {
    color: #e2e8f0 !important;
    font-size: 1.08rem !important;
    font-weight: 500 !important;
    margin-top: 8px;
    margin-bottom: 0;
    line-height: 1.5;
}

/* Özel KPI Metrik Kartları */
.kpi-card {
    background: linear-gradient(145deg, rgba(20, 36, 74, 0.95) 0%, rgba(11, 22, 48, 0.98) 100%);
    border: 1.5px solid rgba(56, 189, 248, 0.3);
    border-radius: 14px;
    padding: 20px 22px;
    box-shadow: 0 6px 24px 0 rgba(0, 0, 0, 0.4);
    transition: transform 0.2s ease, border-color 0.2s ease;
    height: 100%;
}
.kpi-card:hover {
    transform: translateY(-3px);
    border-color: rgba(56, 189, 248, 0.7);
    box-shadow: 0 8px 30px 0 rgba(56, 189, 248, 0.2);
}
.kpi-label {
    font-size: 0.92rem !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.7px !important;
    color: #38bdf8 !important;
    margin-bottom: 8px;
}
.kpi-value {
    font-size: 2.1rem !important;
    font-weight: 800 !important;
    color: #ffffff !important;
    line-height: 1.2 !important;
    letter-spacing: -0.5px;
    text-shadow: 0 2px 10px rgba(0, 0, 0, 0.5);
}
.kpi-caption {
    font-size: 0.9rem !important;
    color: #cbd5e1 !important;
    margin-top: 10px;
    font-weight: 500 !important;
    line-height: 1.4;
}

/* Standart Streamlit Metric Bileşeni */
[data-testid="stMetric"] {
    background: linear-gradient(145deg, rgba(20, 36, 74, 0.95) 0%, rgba(11, 22, 48, 0.98) 100%) !important;
    border: 1.5px solid rgba(56, 189, 248, 0.3) !important;
    border-radius: 14px !important;
    padding: 18px 20px !important;
}
[data-testid="stMetricLabel"] p {
    font-size: 0.95rem !important;
    font-weight: 700 !important;
    color: #38bdf8 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.5px !important;
}
[data-testid="stMetricValue"] div {
    font-size: 2.1rem !important;
    font-weight: 800 !important;
    color: #ffffff !important;
}

/* Bilgi ve Durum Rozetleri */
.badge-info {
    display: inline-block;
    padding: 5px 12px;
    border-radius: 8px;
    font-size: 0.88rem;
    font-weight: 700;
    background: rgba(56, 189, 248, 0.2);
    color: #38bdf8;
    border: 1px solid rgba(56, 189, 248, 0.45);
}

.badge-success {
    display: inline-block;
    padding: 5px 12px;
    border-radius: 8px;
    font-size: 0.88rem;
    font-weight: 700;
    background: rgba(52, 211, 153, 0.2);
    color: #34d399;
    border: 1px solid rgba(52, 211, 153, 0.45);
}

.badge-warning {
    display: inline-block;
    padding: 5px 12px;
    border-radius: 8px;
    font-size: 0.88rem;
    font-weight: 700;
    background: rgba(251, 191, 36, 0.2);
    color: #fbbf24;
    border: 1px solid rgba(251, 191, 36, 0.45);
}

.badge-danger {
    display: inline-block;
    padding: 5px 12px;
    border-radius: 8px;
    font-size: 0.88rem;
    font-weight: 700;
    background: rgba(248, 113, 113, 0.2);
    color: #f87171;
    border: 1px solid rgba(248, 113, 113, 0.45);
}

/* Akıllı İçgörü Kutuları */
.insight-card {
    background: rgba(16, 29, 60, 0.9) !important;
    border-left: 5px solid #38bdf8 !important;
    border-radius: 0 14px 14px 0 !important;
    padding: 18px 24px !important;
    margin-bottom: 1.3rem !important;
    border-top: 1px solid rgba(255, 255, 255, 0.08) !important;
    border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08) !important;
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3) !important;
}

.insight-card h5 {
    font-size: 1.25rem !important;
    font-weight: 700 !important;
    margin-bottom: 8px !important;
}

.insight-body {
    font-size: 1.02rem !important;
    color: #f1f5f9 !important;
    line-height: 1.65 !important;
}
.insight-body b {
    color: #ffffff !important;
    font-weight: 700 !important;
}

/* Sekme Başlıkları - Büyütülmüş ve Net */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    background: rgba(11, 22, 48, 0.75);
    padding: 8px 10px;
    border-radius: 14px;
    border: 1.5px solid rgba(255, 255, 255, 0.08);
}
.stTabs [data-baseweb="tab"] {
    padding: 12px 22px !important;
    color: #cbd5e1 !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 1.05rem !important;
    transition: all 0.2s ease;
}
.stTabs [data-baseweb="tab"]:hover {
    color: #ffffff !important;
    background: rgba(56, 189, 248, 0.1) !important;
}
.stTabs [aria-selected="true"] {
    background: #0284c7 !important;
    color: #ffffff !important;
    font-weight: 700 !important;
    box-shadow: 0 4px 14px rgba(2, 132, 199, 0.45) !important;
}

/* Kenar Çubuğu (Sidebar) - Belirgin Etiketler ve Metinler */
[data-testid="stSidebar"] {
    background: #081024 !important;
    border-right: 1.5px solid rgba(56, 189, 248, 0.25) !important;
}
[data-testid="stSidebar"] label, [data-testid="stSidebar"] .stSelectbox label, [data-testid="stSidebar"] .stMultiSelect label {
    font-size: 1.02rem !important;
    font-weight: 700 !important;
    color: #ffffff !important;
    margin-bottom: 4px !important;
}
[data-testid="stSidebar"] .stRadio label {
    font-size: 0.98rem !important;
    color: #f1f5f9 !important;
    font-weight: 500 !important;
}
[data-testid="stSidebar"] p {
    font-size: 0.96rem !important;
    color: #cbd5e1 !important;
    line-height: 1.5 !important;
}

/* Tablolar (Dataframe) */
[data-testid="stDataFrame"] {
    font-size: 0.98rem !important;
    border-radius: 10px !important;
}

/* Butonlar */
.stButton button, .stDownloadButton button {
    font-size: 1rem !important;
    font-weight: 600 !important;
    padding: 10px 22px !important;
    border-radius: 10px !important;
    background: #0284c7 !important;
    color: #ffffff !important;
    border: 1px solid #38bdf8 !important;
    transition: all 0.2s ease;
}
.stButton button:hover, .stDownloadButton button:hover {
    background: #0369a1 !important;
    box-shadow: 0 4px 16px rgba(56, 189, 248, 0.35) !important;
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# -------------------------------------------------------------
# Veri Yükleme ve Doğrulama
# -------------------------------------------------------------
if not DB_PATH.exists():
    st.error(f"Kritik Hata: Veritabanı dosyası bulunamadı ({DB_PATH}). Dosyanın mevcut olduğundan emin olun.")
    st.stop()

db_mtime = DB_PATH.stat().st_mtime
all_data = get_prepared_data(db_mtime)

orders_df = all_data["orders"]
items_df = all_data["items"]
products_df = all_data["products"]
categories_df = all_data["categories"]
customers_df = all_data["customers"]
cities_df = all_data["cities"]
events_df = all_data["events"]
returns_df = all_data["returns"]
coupons_df = all_data["coupons"]
sellers_df = all_data["sellers"]

# -------------------------------------------------------------
# Üst Başlık Banner
# -------------------------------------------------------------
st.markdown("""
<div class="main-header">
    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
        <div>
            <h1 class="main-title">E-TİCARET 360 • İŞ ZEKASI VE SATIŞ PANELİ</h1>
            <p class="sub-title">SQLite Doğrulanmış Kaynak • Gerçek Zamanlı Finansal & Müşteri Analitiği • Korumalı Veri Bütünlüğü</p>
        </div>
        <div style="margin-top: 8px;">
            <span class="badge-success">● Veri Kaynağı Aktif (Salt Okunur)</span>
            <span class="badge-info" style="margin-left: 8px;">Sipariş Kapsamı: 2025 - 2026</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# Kenar Çubuğu Filtreleri (Sidebar Filters)
# -------------------------------------------------------------
with st.sidebar:
    st.markdown("### 🎛️ Filtreleme Paneli")
    st.caption("Filtreler tüm sayfalardaki hesaplamaları anlık günceller.")

    min_date = orders_df["gun"].min()
    max_date = orders_df["gun"].max()

    # Hızlı Tarih Ön Ayarları
    preset = st.radio(
        "Hızlı Tarih Seçimi",
        ["Tümü (Tam Veri)", "Son 30 Gün", "Son 90 Gün", "2026 Yılı", "2025 Yılı"],
        horizontal=True
    )

    if preset == "Son 30 Gün":
        default_start = max_date - pd.Timedelta(days=29)
        default_end = max_date
    elif preset == "Son 90 Gün":
        default_start = max_date - pd.Timedelta(days=89)
        default_end = max_date
    elif preset == "2026 Yılı":
        default_start = max(min_date, pd.to_datetime("2026-01-01").date())
        default_end = max_date
    elif preset == "2025 Yılı":
        default_start = min_date
        default_end = pd.to_datetime("2025-12-31").date()
    else:
        default_start = min_date
        default_end = max_date

    selected_dates = st.date_input(
        "Sipariş Tarih Aralığı",
        value=(default_start, default_end),
        min_value=min_date,
        max_value=max_date
    )

    if not isinstance(selected_dates, (list, tuple)) or len(selected_dates) < 2:
        st.info("Lütfen başlangıç ve bitiş tarihlerini belirleyin.")
        st.stop()

    start_date, end_date = selected_dates[0], selected_dates[1]

    # Sipariş Durumu Filtresi (Kritik İş Kuralı 1)
    status_options = sorted(orders_df["durum"].unique())
    selected_statuses = st.multiselect(
        "Sipariş Durumu",
        options=status_options,
        default=["teslim_edildi"],
        help="Finansal net ciro varsayılan olarak yalnızca 'teslim_edildi' kayıtlarını kapsar. İptal ve hazırlık aşamaları ciroya katılmaz."
    )

    if not selected_statuses:
        st.warning("En az bir sipariş durumu seçmelisiniz.")
        st.stop()

    # Şehir ve Platform Filtreleri
    all_cities = sorted(orders_df["teslimat_il"].dropna().unique())
    selected_cities = st.multiselect("Teslimat İli", options=all_cities)

    all_platforms = sorted(orders_df["platform"].dropna().unique())
    selected_platforms = st.multiselect("Platform", options=all_platforms)

    # Kategori Filtresi
    all_categories = sorted(categories_df["ana_kategori"].dropna().unique())
    selected_categories = st.multiselect("Ana Kategori", options=all_categories)

    # Satıcı Filtresi
    all_sellers = sorted(sellers_df["satici_adi"].dropna().unique())
    selected_sellers = st.multiselect("Satıcı", options=all_sellers)

    st.divider()
    st.markdown("""
    <div style="font-size: 0.95rem; color: #cbd5e1; line-height: 1.6; background: rgba(15, 27, 54, 0.6); padding: 12px 14px; border-radius: 10px; border: 1px solid rgba(56, 189, 248, 0.2);">
        <b style="color: #38bdf8;">📌 İş Kuralları Notu:</b><br>
        • <b>Net ürün satışı:</b> Ara toplam − Kupon − Tamamlanan İadeler (Kargo hariç).<br>
        • Kuponlar satırlara kalem tutarı oranında dağıtılır.<br>
        • Çifte sayımı önlemek için sipariş KPI'ları tekil sipariş tablosundan beslenir.
    </div>
    """, unsafe_allow_html=True)

# -------------------------------------------------------------
# Filtrelerin Uygulanması ve Metriklerin Hazırlanması
# -------------------------------------------------------------
filtered_orders, enriched_items = filter_and_enrich_orders(
    orders=orders_df,
    items=items_df,
    start_date=start_date,
    end_date=end_date,
    statuses=selected_statuses,
    cities=selected_cities,
    platforms=selected_platforms,
    categories=selected_categories,
    sellers=selected_sellers
)

if filtered_orders.empty:
    st.warning("Seçilen filtre kriterlerine uygun sipariş kaydı bulunamadı. Lütfen filtrelerinizi genişletin.")
    st.stop()

kpis = calculate_executive_kpis(filtered_orders, enriched_items)

# -------------------------------------------------------------
# Üst Yönetici KPI Kartları
# -------------------------------------------------------------
k1, k2, k3, k4, k5 = st.columns(5)

with k1:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Net Ürün Satışı</div>
        <div class="kpi-value">{format_currency(kpis['net_urun_satisi'])}</div>
        <div class="kpi-caption">İadeler ve kuponlar düşülmüş, kargo hariç</div>
    </div>
    """, unsafe_allow_html=True)

with k2:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Toplam Sipariş</div>
        <div class="kpi-value">{format_integer(kpis['toplam_siparis_sayisi'])}</div>
        <div class="kpi-caption">Tekil sipariş adedi</div>
    </div>
    """, unsafe_allow_html=True)

with k3:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Ortalama Sepet (AOV)</div>
        <div class="kpi-value">{format_currency(kpis['ortalama_sepet'])}</div>
        <div class="kpi-caption">Sipariş başına müşteri ödemesi</div>
    </div>
    """, unsafe_allow_html=True)

with k4:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Satılan Ürün Adedi</div>
        <div class="kpi-value">{format_integer(kpis['satilan_toplam_adet'])}</div>
        <div class="kpi-caption">Toplam ürün hacmi</div>
    </div>
    """, unsafe_allow_html=True)

with k5:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Tamamlanan İadeler</div>
        <div class="kpi-value">{format_currency(kpis['tamamlanan_iade_tutari'])}</div>
        <div class="kpi-caption">Oran: {format_percent(kpis['iade_orani_ciro'])} ({format_integer(kpis['tamamlanan_iade_adedi'])} adet)</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)

# -------------------------------------------------------------
# Plotly Grafik Şablon Yardımcısı (Büyük ve Net Tipografi)
# -------------------------------------------------------------
def render_plotly(fig, height: int = 400):
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15, 27, 54, 0.4)",
        font=dict(family="Inter, sans-serif", color="#ffffff", size=13),
        title=dict(font=dict(size=16, color="#ffffff", family="Inter, sans-serif")),
        margin=dict(t=45, b=30, l=30, r=30),
        height=height,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor="rgba(0,0,0,0)",
            font=dict(size=12.5, color="#ffffff")
        )
    )
    fig.update_xaxes(
        showgrid=True,
        gridcolor="rgba(255,255,255,0.12)",
        title_font=dict(size=13.5, color="#38bdf8", family="Inter, sans-serif"),
        tickfont=dict(size=12, color="#f1f5f9", family="Inter, sans-serif")
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor="rgba(255,255,255,0.12)",
        title_font=dict(size=13.5, color="#38bdf8", family="Inter, sans-serif"),
        tickfont=dict(size=12, color="#f1f5f9", family="Inter, sans-serif")
    )
    st.plotly_chart(fig, use_container_width=True)

# -------------------------------------------------------------
# Sekmeler (8 Kapsamlı Modül)
# -------------------------------------------------------------
tabs = st.tabs([
    "📈 Genel Bakış",
    "🛍️ Ürün ve Kategori",
    "🏙️ Şehir ve Coğrafya",
    "👥 Müşteri ve RFM",
    "↩️ İade Analizleri",
    "🧭 Davranış ve Huni",
    "💡 Akıllı Bulgular",
    "🔍 Veri Kalitesi"
])

# =============================================================
# SEKME 1: GENEL BAKIŞ
# =============================================================
with tabs[0]:
    st.markdown("#### 📊 Satış Trendi ve Dağılımlar")

    c1, c2 = st.columns([2, 1])

    with c1:
        # Aylık Trend
        monthly = filtered_orders.groupby("ay", as_index=False).agg(
            siparis_sayisi=("siparis_id", "nunique"),
            toplam_tutar=("toplam_tutar", "sum")
        ).sort_values("ay")

        fig_trend = go.Figure()
        fig_trend.add_trace(go.Bar(
            x=monthly["ay"],
            y=monthly["siparis_sayisi"],
            name="Sipariş Sayısı",
            marker_color="rgba(56, 189, 248, 0.65)",
            yaxis="y2"
        ))
        fig_trend.add_trace(go.Scatter(
            x=monthly["ay"],
            y=monthly["toplam_tutar"],
            name="Toplam Tutar (TL)",
            mode="lines+markers",
            line=dict(color="#38bdf8", width=3),
            marker=dict(size=7, color="#818cf8")
        ))
        fig_trend.update_layout(
            title="Aylık Sipariş Hacmi ve Tutar Trendi",
            yaxis=dict(title="Toplam Tutar (TL)", tickformat=","),
            yaxis2=dict(title="Sipariş Sayısı", overlaying="y", side="right", showgrid=False)
        )
        render_plotly(fig_trend)

    with c2:
        # Platform Dağılımı Donut
        plat = filtered_orders.groupby("platform", as_index=False).agg(
            siparis=("siparis_id", "nunique"),
            tutar=("toplam_tutar", "sum")
        )
        fig_plat = px.pie(
            plat, names="platform", values="tutar",
            hole=0.6,
            title="Platform Bazında Gelir Dağılımı",
            color_discrete_sequence=["#38bdf8", "#818cf8", "#34d399", "#fbbf24"]
        )
        render_plotly(fig_plat)

    # İkinci Satır: Ödeme Yöntemi ve Gün/Saat Dağılımı
    r1, r2 = st.columns(2)

    with r1:
        pay = filtered_orders.groupby("odeme_yontemi", as_index=False).agg(
            siparis=("siparis_id", "nunique"),
            tutar=("toplam_tutar", "sum")
        ).sort_values("tutar", ascending=True)

        fig_pay = px.bar(
            pay, x="tutar", y="odeme_yontemi",
            orientation="h",
            title="Ödeme Yöntemine Göre Satış Tutarı",
            labels={"tutar": "Tutar (TL)", "odeme_yontemi": "Ödeme Yöntemi"},
            color="tutar",
            color_continuous_scale="Blues"
        )
        fig_pay.update_coloraxes(showscale=False)
        render_plotly(fig_pay)

    with r2:
        day_order = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
        days_df = filtered_orders.groupby("gun_adi_tr", as_index=False).agg(
            siparis=("siparis_id", "nunique"),
            aov=("toplam_tutar", "mean")
        )
        days_df["sirali"] = days_df["gun_adi_tr"].map(lambda d: day_order.index(d) if d in day_order else 99)
        days_df = days_df.sort_values("sirali")

        fig_days = px.bar(
            days_df, x="gun_adi_tr", y="siparis",
            title="Haftanın Günlerine Göre Sipariş Sayısı",
            labels={"gun_adi_tr": "Gün", "siparis": "Sipariş Sayısı"},
            color="siparis",
            color_continuous_scale="Teal"
        )
        fig_days.update_coloraxes(showscale=False)
        render_plotly(fig_days)

# =============================================================
# SEKME 2: ÜRÜN VE KATEGORİ
# =============================================================
with tabs[1]:
    st.markdown("#### 🛍️ Ürün ve Kategori Performansı")

    if not enriched_items.empty:
        pareto_df = calculate_abc_pareto(enriched_items)

        p1, p2 = st.columns(2)
        with p1:
            top_revenue = pareto_df.nlargest(10, "net_satis").sort_values("net_satis", ascending=True)
            fig_top_rev = px.bar(
                top_revenue, x="net_satis", y="urun_adi",
                orientation="h",
                title="En Çok Net Ciro Üreten İlk 10 Ürün",
                labels={"net_satis": "Net Satış (TL)", "urun_adi": "Ürün"},
                color="net_satis",
                color_continuous_scale="Viridis"
            )
            fig_top_rev.update_coloraxes(showscale=False)
            render_plotly(fig_top_rev, height=380)

        with p2:
            top_qty = pareto_df.nlargest(10, "toplam_adet").sort_values("toplam_adet", ascending=True)
            fig_top_qty = px.bar(
                top_qty, x="toplam_adet", y="urun_adi",
                orientation="h",
                title="En Çok Adet Satan İlk 10 Ürün",
                labels={"toplam_adet": "Satılan Adet", "urun_adi": "Ürün"},
                color="toplam_adet",
                color_continuous_scale="Cividis"
            )
            fig_top_qty.update_coloraxes(showscale=False)
            render_plotly(fig_top_qty, height=380)

        # ABC / Pareto Analizi Grafiği
        st.markdown("##### 📌 ABC / Pareto Analizi")
        st.caption("A Grubu: Toplam net cironun %80'ini oluşturan hayati ürünler. B Grubu: Sonraki %15. C Grubu: Kalan %5.")

        fig_pareto = go.Figure()
        fig_pareto.add_trace(go.Bar(
            x=pareto_df["urun_adi"],
            y=pareto_df["net_satis"],
            name="Net Satış (TL)",
            marker_color=pareto_df["abc_sinifi"].map({
                "A (Hayati %80)": "#38bdf8",
                "B (Önemli %15)": "#fbbf24",
                "C (Kuyruk %5)": "#f87171"
            })
        ))
        fig_pareto.add_trace(go.Scatter(
            x=pareto_df["urun_adi"],
            y=pareto_df["kumulatif_pay"] * 100,
            name="Kümülatif Ciro Payı (%)",
            yaxis="y2",
            mode="lines",
            line=dict(color="#34d399", width=3)
        ))
        fig_pareto.update_layout(
            title="Pareto Eğrisi ve Ürün Segmentasyonu",
            yaxis=dict(title="Net Satış (TL)"),
            yaxis2=dict(title="Kümülatif Pay (%)", overlaying="y", side="right", range=[0, 105], showgrid=False),
            xaxis=dict(showticklabels=False)
        )
        render_plotly(fig_pareto, height=350)

        # Hiyerarşik Kategori Performansı
        st.markdown("##### 🗂️ Hiyerarşik Kategori Dağılımı")
        cat_perf = enriched_items.groupby(["ana_kategori", "alt_kategori"], as_index=False).agg(
            net_satis=("urun_net_satis", "sum"),
            adet=("adet", "sum")
        )
        fig_cat = px.sunburst(
            cat_perf,
            path=["ana_kategori", "alt_kategori"],
            values="net_satis",
            title="Ana Kategori ve Alt Kategori Net Satış Dağılımı",
            color="net_satis",
            color_continuous_scale="Spectral"
        )
        render_plotly(fig_cat, height=450)

        # Ürün Detay Tablosu
        st.markdown("##### 📋 Ürün Performans Detay Tablosu")
        display_prod = pareto_df[[
            "urun_adi", "marka", "ana_kategori", "satici_adi", "abc_sinifi",
            "toplam_adet", "stok_adedi", "net_satis", "iade_orani", "ortalama_puan"
        ]].copy()
        display_prod["net_satis"] = display_prod["net_satis"].apply(format_currency)
        display_prod["iade_orani"] = display_prod["iade_orani"].apply(format_percent)
        display_prod = display_prod.rename(columns={
            "urun_adi": "Ürün Adı", "marka": "Marka", "ana_kategori": "Kategori",
            "satici_adi": "Satıcı", "abc_sinifi": "ABC Sınıfı", "toplam_adet": "Satılan Adet",
            "stok_adedi": "Stok", "net_satis": "Net Ciro", "iade_orani": "İade Oranı",
            "ortalama_puan": "Puan"
        })
        st.dataframe(display_prod, use_container_width=True, hide_index=True)

# =============================================================
# SEKME 3: ŞEHİR VE COĞRAFYA
# =============================================================
with tabs[2]:
    st.markdown("#### 🏙️ Teslimat İlleri ve Bölgesel Dağılım")
    st.caption("Not: Şehir bilgisi siparişin teslimat ilinden (teslimat_il) alınmaktadır.")

    city_orders = filtered_orders.groupby("teslimat_il", as_index=False).agg(
        siparis_sayisi=("siparis_id", "nunique"),
        toplam_tutar=("toplam_tutar", "sum")
    ).sort_values("toplam_tutar", ascending=False)

    geo_df = city_orders.merge(cities_df, left_on="teslimat_il", right_on="il", how="inner")

    g1, g2 = st.columns([3, 2])

    with g1:
        # Harita
        if not geo_df.empty:
            st.markdown("##### 🗺️ Türkiye Sipariş Yoğunluğu Haritası")
            fig_map = px.scatter_mapbox(
                geo_df,
                lat="enlem",
                lon="boylam",
                size="siparis_sayisi",
                color="toplam_tutar",
                hover_name="teslimat_il",
                hover_data={"siparis_sayisi": True, "toplam_tutar": ":,.2f", "enlem": False, "boylam": False},
                color_continuous_scale="Viridis",
                size_max=35,
                zoom=4.7,
                center=dict(lat=39.0, lon=35.0),
                mapbox_style="carto-darkmatter",
                title="İllere Göre Sipariş ve Ciro Dağılımı"
            )
            render_plotly(fig_map, height=450)

    with g2:
        # Bölgesel Dağılım
        st.markdown("##### 📍 Coğrafi Bölgelere Göre Ciro Payı")
        region_df = geo_df.groupby("bolge", as_index=False).agg(
            siparis=("siparis_sayisi", "sum"),
            tutar=("toplam_tutar", "sum")
        ).sort_values("tutar", ascending=False)

        fig_reg = px.bar(
            region_df, x="tutar", y="bolge",
            orientation="h",
            labels={"tutar": "Toplam Tutar (TL)", "bolge": "Bölge"},
            color="tutar",
            color_continuous_scale="Teal"
        )
        fig_reg.update_coloraxes(showscale=False)
        render_plotly(fig_reg, height=450)

    # İller Tablosu ve Ortalama Sepet
    st.markdown("##### 📊 İllerin Performans Sıralaması")
    city_orders["ortalama_sepet"] = city_orders["toplam_tutar"] / city_orders["siparis_sayisi"]
    city_display = city_orders.rename(columns={
        "teslimat_il": "Teslimat İli",
        "siparis_sayisi": "Sipariş Sayısı",
        "toplam_tutar": "Toplam Ciro (TL)",
        "ortalama_sepet": "Ortalama Sepet (TL)"
    }).copy()
    city_display["Toplam Ciro (TL)"] = city_display["Toplam Ciro (TL)"].apply(format_currency)
    city_display["Ortalama Sepet (TL)"] = city_display["Ortalama Sepet (TL)"].apply(format_currency)
    st.dataframe(city_display, use_container_width=True, hide_index=True)

# =============================================================
# SEKME 4: MÜŞTERİ VE RFM
# =============================================================
with tabs[3]:
    st.markdown("#### 👥 Müşteri Davranışı ve RFM Segmentasyonu")
    st.caption("KVKK gereği müşteri adı, soyadı ve e-posta adresleri otomatik olarak maskelenmiştir.")

    rfm_df = calculate_rfm_segments(filtered_orders, customers_df)

    if not rfm_df.empty:
        total_customers = len(rfm_df)
        repeat_customers = int((rfm_df["frequency"] >= 2).sum())
        repeat_rate = (repeat_customers / total_customers * 100) if total_customers > 0 else 0.0

        mc1, mc2, mc3, mc4 = st.columns(4)
        mc1.metric("Toplam Aktif Müşteri", format_integer(total_customers))
        mc2.metric("Tekrar Eden Müşteri", format_integer(repeat_customers))
        mc3.metric("Tekrar Satın Alma Oranı", format_percent(repeat_rate))
        mc4.metric("Müşteri Başına Ort. Ciro", format_currency(rfm_df["monetary"].mean()))

        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

        m1, m2 = st.columns(2)
        with m1:
            # RFM Segment Dağılımı
            seg_summary = rfm_df.groupby("segment", as_index=False).agg(
                musteri_sayisi=("musteri_id", "count"),
                toplam_harcama=("monetary", "sum"),
                ort_harcama=("monetary", "mean")
            ).sort_values("musteri_sayisi", ascending=False)

            fig_seg = px.bar(
                seg_summary, x="segment", y="musteri_sayisi",
                color="segment",
                title="Müşteri Segment Dağılımı (RFM)",
                labels={"segment": "Segment", "musteri_sayisi": "Müşteri Sayısı"}
            )
            render_plotly(fig_seg)

        with m2:
            # Kayıt Kanalı Performansı
            channel_df = rfm_df.groupby("kayit_kanali", as_index=False).agg(
                musteri_sayisi=("musteri_id", "count"),
                toplam_harcama=("monetary", "sum")
            ).sort_values("toplam_harcama", ascending=False)

            fig_chan = px.pie(
                channel_df, names="kayit_kanali", values="toplam_harcama",
                hole=0.55,
                title="Kayıt Kanalına Göre Harcama Payı"
            )
            render_plotly(fig_chan)

        # Demografik Kırılımlar
        d1, d2 = st.columns(2)
        with d1:
            gender_df = rfm_df.groupby("cinsiyet", as_index=False).agg(
                musteri=("musteri_id", "count"),
                harcama=("monetary", "sum")
            )
            gender_df["cinsiyet_tr"] = gender_df["cinsiyet"].map({"E": "Erkek", "K": "Kadın"}).fillna("Bilinmiyor")
            fig_gen = px.bar(
                gender_df, x="cinsiyet_tr", y="harcama",
                color="cinsiyet_tr",
                title="Cinsiyete Göre Toplam Harcama",
                labels={"cinsiyet_tr": "Cinsiyet", "harcama": "Harcama (TL)"}
            )
            render_plotly(fig_gen)

        with d2:
            age_df = rfm_df.groupby("yas_grubu", as_index=False, observed=False).agg(
                musteri=("musteri_id", "count"),
                harcama=("monetary", "sum")
            )
            fig_age = px.bar(
                age_df, x="yas_grubu", y="harcama",
                title="Yaş Gruplarına Göre Harcama Dağılımı",
                labels={"yas_grubu": "Yaş Grubu", "harcama": "Harcama (TL)"},
                color="harcama",
                color_continuous_scale="Purples"
            )
            fig_age.update_coloraxes(showscale=False)
            render_plotly(fig_age)

        # Maskeli Müşteri Listesi
        st.markdown("##### 🛡️ Maskelenmiş Müşteri Tablosu (KVKK Uyumlu)")
        display_cust = rfm_df[[
            "musteri_gorunen_ad", "eposta_maskeli", "il", "segment",
            "siparis_sayisi", "toplam_harcama", "recency_gun", "premium_uye"
        ]].sort_values("toplam_harcama", ascending=False).head(20).copy()
        display_cust["toplam_harcama"] = display_cust["toplam_harcama"].apply(format_currency)
        display_cust["premium_uye"] = display_cust["premium_uye"].map({1: "Evet ⭐", 0: "Hayır"})
        display_cust = display_cust.rename(columns={
            "musteri_gorunen_ad": "Müşteri", "eposta_maskeli": "E-Posta",
            "il": "İl", "segment": "Segment", "siparis_sayisi": "Sipariş",
            "toplam_harcama": "Toplam Harcama", "recency_gun": "Son Sipariş (Gün)",
            "premium_uye": "Premium"
        })
        st.dataframe(display_cust, use_container_width=True, hide_index=True)

# =============================================================
# SEKME 5: İADELER
# =============================================================
with tabs[4]:
    st.markdown("#### ↩️ İade ve Geri Ödeme Analizleri")

    order_ids = set(filtered_orders["siparis_id"])
    returns_scope = returns_df[returns_df["siparis_id"].isin(order_ids)].copy()

    ret1, ret2 = st.columns(2)

    with ret1:
        # İade Nedenleri
        reason_df = returns_scope.groupby("iade_nedeni", as_index=False).agg(
            basvuru=("iade_id", "count"),
            tutar=("iade_tutari", "sum"),
            adet=("iade_adedi", "sum")
        ).sort_values("basvuru", ascending=False)

        fig_reason = px.bar(
            reason_df, x="basvuru", y="iade_nedeni",
            orientation="h",
            title="İade Nedenleri Başvuru Dağılımı",
            labels={"basvuru": "Başvuru Sayısı", "iade_nedeni": "İade Nedeni"},
            color="basvuru",
            color_continuous_scale="Reds"
        )
        fig_reason.update_coloraxes(showscale=False)
        render_plotly(fig_reason)

    with ret2:
        # İade Durumu (Tamamlanan vs İncelenen)
        ret_status = returns_scope.groupby("durum", as_index=False).agg(
            basvuru=("iade_id", "count"),
            tutar=("iade_tutari", "sum")
        )
        ret_status["durum_tr"] = ret_status["durum"].map({
            "tamamlandi": "Tamamlanan (İade Edildi)",
            "inceleniyor": "İnceleniyor (Askıda)"
        }).fillna(ret_status["durum"])

        fig_rstatus = px.pie(
            ret_status, names="durum_tr", values="tutar",
            hole=0.55,
            title="İade Süreç Durumu ve Finansal Yük",
            color_discrete_sequence=["#f87171", "#fbbf24"]
        )
        render_plotly(fig_rstatus)

    # En Yüksek İade Oranlı Riskli Ürünler
    st.markdown("##### ⚠️ En Yüksek İade Oranına Sahip Ürünler")
    st.caption("En az 10 sipariş almış ürünler listelenmektedir.")

    prod_ret = enriched_items.groupby(["urun_adi", "marka", "ana_kategori", "satici_adi"], as_index=False).agg(
        siparis=("siparis_id", "nunique"),
        satis_adedi=("adet", "sum"),
        iade_adedi=("tamamlanan_iade_adedi", "sum"),
        iade_tutari=("tamamlanan_iade_tutari", "sum")
    )
    prod_ret["iade_orani"] = np.where(prod_ret["satis_adedi"] > 0, prod_ret["iade_adedi"] / prod_ret["satis_adedi"] * 100, 0.0)
    risky_prods = prod_ret[prod_ret["siparis"] >= 10].sort_values("iade_orani", ascending=False).head(15).copy()

    risky_prods["iade_tutari"] = risky_prods["iade_tutari"].apply(format_currency)
    risky_prods["iade_orani"] = risky_prods["iade_orani"].apply(format_percent)
    risky_prods = risky_prods.rename(columns={
        "urun_adi": "Ürün Adı", "marka": "Marka", "ana_kategori": "Kategori",
        "satici_adi": "Satıcı", "siparis": "Sipariş Sayısı", "satis_adedi": "Satılan Adet",
        "iade_adedi": "İade Adedi", "iade_tutari": "İade Tutarı", "iade_orani": "İade Oranı (%)"
    })
    st.dataframe(risky_prods, use_container_width=True, hide_index=True)

# =============================================================
# SEKME 6: DAVRANIŞ VE HUNİ
# =============================================================
with tabs[5]:
    st.markdown("#### 🧭 Web/Uygulama Olayları ve Dönüşüm Hunisi")
    st.markdown("""
    > [!NOTE]
    > **İş Kuralı Hatırlatması:** Olaylar tablosunda platform veya il bilgisi yer almadığından, bu sekmede yalnızca tarih filtresi işletilir.
    > Ayrıca hunideki aşamalar her olay tipine ait tekil oturum sayılarını göstermekte olup, 'Dönüşüm Göstergesi' olarak değerlendirilmelidir.
    """)

    ev_filtered = events_df[(events_df["gun"] >= start_date) & (events_df["gun"] <= end_date)].copy()

    bh1, bh2 = st.columns(2)

    with bh1:
        stages = ["urun_goruntuleme", "sepete_ekleme", "satin_alma"]
        stage_names = {
            "urun_goruntuleme": "1. Ürün Görüntüleme",
            "sepete_ekleme": "2. Sepete Ekleme",
            "satin_alma": "3. Satın Alma Sinyali"
        }
        funnel_data = ev_filtered[ev_filtered["olay_tipi"].isin(stages)].groupby("olay_tipi")["oturum_id"].nunique().reindex(stages, fill_value=0).reset_index()
        funnel_data["asama"] = funnel_data["olay_tipi"].map(stage_names)

        fig_funnel = px.funnel(
            funnel_data,
            x="oturum_id",
            y="asama",
            title="Oturum Bazlı Etkileşim Göstergesi",
            labels={"oturum_id": "Tekil Oturum Sayısı", "asama": "Aşama"},
            color_discrete_sequence=["#38bdf8"]
        )
        render_plotly(fig_funnel)

    with bh2:
        traffic_device = ev_filtered.groupby(["trafik_kaynagi", "cihaz"], as_index=False)["oturum_id"].nunique()
        fig_traffic = px.bar(
            traffic_device,
            x="trafik_kaynagi",
            y="oturum_id",
            color="cihaz",
            barmode="group",
            title="Trafik Kaynağı ve Cihaz Dağılımı",
            labels={"oturum_id": "Oturum Sayısı", "trafik_kaynagi": "Trafik Kaynağı", "cihaz": "Cihaz"}
        )
        render_plotly(fig_traffic)

    # Kaçan Fırsatlar (Yüksek Trafik - Düşük Dönüşüm)
    st.markdown("##### 🎯 Kaçan Fırsat Ürünleri (Yüksek Görüntülenme / Düşük Satın Alma)")
    st.caption("Çok ilgi gören fakat sepete ve satın almaya dönüşmekte zorlanan potansiyel ürünler.")

    opp_data = detect_high_traffic_low_conversion(events_df, products_df, start_date, end_date)
    if not opp_data["data"].empty:
        opp_df = opp_data["data"][[
            "urun_adi", "marka", "ana_kategori", "guncel_liste_fiyati",
            "goruntuleme_oturum", "sepete_ekleme_oturum", "satin_alma_oturum",
            "donusum_gostergesi", "sepet_terk_gostergesi"
        ]].copy()
        opp_df["guncel_liste_fiyati"] = opp_df["guncel_liste_fiyati"].apply(format_currency)
        opp_df["donusum_gostergesi"] = opp_df["donusum_gostergesi"].apply(format_percent)
        opp_df["sepet_terk_gostergesi"] = opp_df["sepet_terk_gostergesi"].apply(format_percent)
        opp_df = opp_df.rename(columns={
            "urun_adi": "Ürün", "marka": "Marka", "ana_kategori": "Kategori",
            "guncel_liste_fiyati": "Fiyat", "goruntuleme_oturum": "Görüntüleme (Oturum)",
            "sepete_ekleme_oturum": "Sepet (Oturum)", "satin_alma_oturum": "Satın Alma (Oturum)",
            "donusum_gostergesi": "Dönüşüm Oranı", "sepet_terk_gostergesi": "Sepet Terk Oranı"
        })
        st.dataframe(opp_df, use_container_width=True, hide_index=True)

# =============================================================
# SEKME 7: AKILLI BULGULAR VE İÇGÖRÜLER
# =============================================================
with tabs[6]:
    st.markdown("#### 💡 Algoritmik İçgörüler ve Gizli Örüntüler")
    st.caption("Veriler üzerinden istatistiksel modeller ve kural motoru tarafından otomatik olarak tespit edilen stratejik sinyaller.")

    # 1. Satış Sıçramaları
    spikes_res = detect_sales_spikes(filtered_orders)
    st.markdown(f"""
    <div class="insight-card">
        <h5 style="color: #38bdf8; margin: 0 0 8px 0;">🚀 1. Satış Sıçramaları ve Kampanya Anomalileri</h5>
        <div class="insight-body">
            <b>Dayanak Veri & Eşik:</b> {spikes_res['threshold']} ({spikes_res.get('period', '')})<br>
            <b>Tespit Edilen Anomali Sayısı:</b> {spikes_res['count']} gün.
        </div>
    </div>
    """, unsafe_allow_html=True)
    if not spikes_res["data"].empty:
        disp_spikes = spikes_res["data"][["gun", "siparis_sayisi", "toplam_tutar", "hareketli_medyan", "sicrama_orani", "kupon_kullanim_orani"]].head(5).copy()
        disp_spikes["toplam_tutar"] = disp_spikes["toplam_tutar"].apply(format_currency)
        disp_spikes["hareketli_medyan"] = disp_spikes["hareketli_medyan"].apply(format_currency)
        disp_spikes["sicrama_orani"] = disp_spikes["sicrama_orani"].map(lambda x: f"{x:.2f}x")
        disp_spikes["kupon_kullanim_orani"] = disp_spikes["kupon_kullanim_orani"].apply(format_percent)
        disp_spikes = disp_spikes.rename(columns={
            "gun": "Tarih", "siparis_sayisi": "Sipariş", "toplam_tutar": "Gerçekleşen Ciro",
            "hareketli_medyan": "7 Günlük Medyan", "sicrama_orani": "Kat Sıçrama", "kupon_kullanim_orani": "Kupon Kullanım Oranı"
        })
        st.dataframe(disp_spikes, use_container_width=True, hide_index=True)

    # 2. Stok Tükenme Riski
    stock_res = detect_stockout_risk(products_df, enriched_items, max_date=end_date)
    st.markdown(f"""
    <div class="insight-card">
        <h5 style="color: #fbbf24; margin: 0 0 8px 0;">📦 2. Kritik Stok Tükenme Riski (Runout Risk)</h5>
        <div class="insight-body">
            <b>Dayanak Veri & Eşik:</b> {stock_res['threshold']} ({stock_res.get('period', '')})<br>
            <b>Kritik Ürün Sayısı:</b> {stock_res['count']} ürün.<br>
            <i style="color: #cbd5e1;">Not: Stok miktarı tablodaki anlık değerdir; geçmiş satış hızına göre yapılan bu projeksiyon kesin garanti içermez.</i>
        </div>
    </div>
    """, unsafe_allow_html=True)
    if not stock_res["data"].empty:
        disp_stock = stock_res["data"][[
            "urun_adi", "marka", "satici_adi", "stok_adedi",
            "son_donem_satilan_adet", "gunluk_ortalama_satis", "tahmini_stok_tukenme_gunu"
        ]].head(8).copy()
        disp_stock["gunluk_ortalama_satis"] = disp_stock["gunluk_ortalama_satis"].map(lambda x: f"{x:.1f} adet/gün")
        disp_stock["tahmini_stok_tukenme_gunu"] = disp_stock["tahmini_stok_tukenme_gunu"].map(lambda x: f"{x:.1f} gün")
        disp_stock = disp_stock.rename(columns={
            "urun_adi": "Ürün", "marka": "Marka", "satici_adi": "Satıcı",
            "stok_adedi": "Kalan Stok", "son_donem_satilan_adet": "Dönem Satışı",
            "gunluk_ortalama_satis": "Günlük Hız", "tahmini_stok_tukenme_gunu": "Tahmini Kalan Gün"
        })
        st.dataframe(disp_stock, use_container_width=True, hide_index=True)

    # 3. Yüksek İade & Düşük Puan
    quality_res = detect_high_return_low_rating_products(enriched_items)
    st.markdown(f"""
    <div class="insight-card">
        <h5 style="color: #f87171; margin: 0 0 8px 0;">⚠️ 3. Yüksek İade & Düşük Müşteri Puanı Alarmı</h5>
        <div class="insight-body">
            <b>Dayanak Veri & Eşik:</b> {quality_res['threshold']}<br>
            <b>Kusurlu/Yanıltıcı Olabilecek Ürün Sayısı:</b> {quality_res['count']} ürün.
        </div>
    </div>
    """, unsafe_allow_html=True)
    if not quality_res["data"].empty:
        disp_qual = quality_res["data"][[
            "urun_adi", "marka", "satici_adi", "toplam_siparis",
            "toplam_satilan_adet", "toplam_iade_adedi", "iade_orani", "ortalama_puan"
        ]].head(8).copy()
        disp_qual["iade_orani"] = disp_qual["iade_orani"].apply(format_percent)
        disp_qual = disp_qual.rename(columns={
            "urun_adi": "Ürün", "marka": "Marka", "satici_adi": "Satıcı",
            "toplam_siparis": "Sipariş", "toplam_satilan_adet": "Satılan Adet",
            "toplam_iade_adedi": "İade Adedi", "iade_orani": "İade Oranı", "ortalama_puan": "Ort. Puan"
        })
        st.dataframe(disp_qual, use_container_width=True, hide_index=True)

    # 4. Kupon Etkinliği ve Sepet Analizi
    coupon_res = analyze_coupon_basket_impact(filtered_orders)
    st.markdown(f"""
    <div class="insight-card">
        <h5 style="color: #34d399; margin: 0 0 8px 0;">🎟️ 4. Kupon Kullanımı & Ortalama Sepet Büyüklüğü İlişkisi</h5>
        <div class="insight-body">
            <b>Kuponlu Sipariş Sayısı:</b> {format_integer(coupon_res['total_coupons_applied'])} adet<br>
            <b>Kuponlu Ortalama Sepet:</b> {format_currency(coupon_res['aov_with_coupon'])} |
            <b>Kuponsuz Ortalama Sepet:</b> {format_currency(coupon_res['aov_without_coupon'])}<br>
            <b>Sepet Tutarı Farkı:</b> Kuponlu siparişler kuponsuzlara göre <b>%{coupon_res['diff_pct']:.1f}</b> daha yüksek sepet tutarına sahiptir.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 5. Resmi Mağaza vs Pazaryeri Satıcı Performansı
    seller_comp = analyze_official_vs_marketplace_sellers(enriched_items)
    st.markdown(f"""
    <div class="insight-card">
        <h5 style="color: #818cf8; margin: 0 0 8px 0;">🏬 5. Resmi Mağaza vs Pazaryeri Satıcı Güven Analizi</h5>
        <div class="insight-body">
            Yetkili resmi mağazalar ile normal satıcıların iade oranları ve müşteri memnuniyeti kıyaslaması.
        </div>
    </div>
    """, unsafe_allow_html=True)
    if not seller_comp.empty:
        disp_seller_comp = seller_comp[[
            "magaza_tipi", "satici_sayisi", "toplam_urun_adedi", "net_satis", "iade_orani_adet", "ortalama_puan"
        ]].copy()
        disp_seller_comp["net_satis"] = disp_seller_comp["net_satis"].apply(format_currency)
        disp_seller_comp["iade_orani_adet"] = disp_seller_comp["iade_orani_adet"].apply(format_percent)
        disp_seller_comp = disp_seller_comp.rename(columns={
            "magaza_tipi": "Satıcı Türü", "satici_sayisi": "Satıcı Sayısı",
            "toplam_urun_adedi": "Satılan Ürün", "net_satis": "Net Ciro",
            "iade_orani_adet": "Adet İade Oranı", "ortalama_puan": "Ortalama Değerlendirme"
        })
        st.dataframe(disp_seller_comp, use_container_width=True, hide_index=True)

# =============================================================
# SEKME 8: VERİ KALİTESİ
# =============================================================
with tabs[7]:
    st.markdown("#### 🔍 Veri Kalitesi ve Sağlık Raporu")
    st.caption("Veritabanı referans bütünlüğü, tutar mutabakatları ve temel iş kuralı denetimleri.")

    raw = all_data["raw"]

    # Otomatik Kalite Kontrolleri Tablosu
    checks = [
        ("Mükerrer Sipariş ID (Primary Key)", int(raw["siparisler"]["siparis_id"].duplicated().sum()), "0 olmalı"),
        ("Mükerrer Ürün ID (Primary Key)", int(raw["urunler"]["urun_id"].duplicated().sum()), "0 olmalı"),
        ("Siparişe Bağlanamayan Kalem (Bozuk FK)", int((~raw["siparis_kalemleri"]["siparis_id"].isin(raw["siparisler"]["siparis_id"])).sum()), "0 olmalı"),
        ("Ürüne Bağlanamayan Kalem (Bozuk FK)", int((~raw["siparis_kalemleri"]["urun_id"].isin(raw["urunler"]["urun_id"])).sum()), "0 olmalı"),
        ("Sipariş Toplam Tutar Denkliği (|Ara - Kupon + Kargo - Toplam| > 0,05 TL)", int(((raw["siparisler"]["ara_toplam"] - raw["siparisler"]["kupon_indirimi"] + raw["siparisler"]["kargo_ucreti"] - raw["siparisler"]["toplam_tutar"]).abs() > 0.05).sum()), "0 olmalı"),
        ("Kalem Tutar Denkliği (|Adet * Liste/İndirimli - KalemTutarı| > 0,05 TL)", int(((raw["siparis_kalemleri"]["adet"] * raw["siparis_kalemleri"]["birim_satis_fiyati"] - raw["siparis_kalemleri"]["kalem_tutari"]).abs() > 0.05).sum()), "0 olmalı"),
        ("Eksik Teslimat İli Olan Siparişler", int(raw["siparisler"]["teslimat_il"].isna().sum()), "0 olmalı")
    ]

    checks_df = pd.DataFrame(checks, columns=["Bütünlük Kontrolü", "Hatalı / Şüpheli Kayıt", "Beklenen Değer"])
    checks_df["Durum"] = checks_df["Hatalı / Şüpheli Kayıt"].map(lambda x: "✅ Kusursuz" if x == 0 else "❌ Hata Var")
    st.dataframe(checks_df, use_container_width=True, hide_index=True)

    # Sipariş Durumları Dökümü
    st.markdown("##### 📦 Tüm Veritabanındaki Sipariş Durumları ve Finansal Ağırlıkları")
    st_summary = raw["siparisler"].groupby("durum", as_index=False).agg(
        siparis_sayisi=("siparis_id", "count"),
        toplam_tutar=("toplam_tutar", "sum"),
        ara_toplam=("ara_toplam", "sum"),
        kupon_indirimi=("kupon_indirimi", "sum")
    )
    st_summary["toplam_tutar"] = st_summary["toplam_tutar"].apply(format_currency)
    st_summary["ara_toplam"] = st_summary["ara_toplam"].apply(format_currency)
    st_summary["kupon_indirimi"] = st_summary["kupon_indirimi"].apply(format_currency)
    st_summary = st_summary.rename(columns={
        "durum": "Sipariş Durumu", "siparis_sayisi": "Kayıt Sayısı",
        "toplam_tutar": "Toplam Tutar (TL)", "ara_toplam": "Ara Toplam",
        "kupon_indirimi": "Kupon İndirimi"
    })
    st.dataframe(st_summary, use_container_width=True, hide_index=True)

    # Canlı Pytest Testi Çalıştırma Butonu
    st.markdown("##### 🧪 Otomatik Test Süitini Çalıştır")
    st.caption("Veritabanının 8.044 sipariş, 13.858 kalem ve net 24.588.466,13 TL ciro mutabakatını canlı test eder.")

    if st.button("🚀 Canlı Bütünlük Testlerini Çalıştır (pytest)"):
        with st.spinner("Testler çalıştırılıyor..."):
            res = subprocess.run(
                [sys.executable, "-m", "pytest", "tests/test_integrity.py", "-v"],
                capture_output=True,
                text=True
            )
            if res.returncode == 0:
                st.success("Tüm testler başarıyla geçti! Veri bütünlüğü %100 onaylandı.")
                st.code(res.stdout, language="bash")
            else:
                st.error("Bazı testler başarısız oldu!")
                st.code(res.stderr or res.stdout, language="bash")

# -------------------------------------------------------------
# Dışa Aktarma / İndirme Bölümü
# -------------------------------------------------------------
st.divider()
dcol1, dcol2, dcol3 = st.columns([1, 1, 2])

with dcol1:
    csv_orders = filtered_orders.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "⬇️ Filtreli Siparişleri İndir (CSV)",
        data=csv_orders,
        file_name="filtreli_siparisler.csv",
        mime="text/csv"
    )

with dcol2:
    if not enriched_items.empty:
        csv_items = enriched_items[[
            "siparis_id", "siparis_tarihi", "urun_adi", "marka", "ana_kategori",
            "satici_adi", "adet", "birim_satis_fiyati", "kalem_tutari",
            "dagitilan_kupon", "urun_net_satis", "tamamlanan_iade_tutari"
        ]].to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "⬇️ Filtreli Kalemleri İndir (CSV)",
            data=csv_items,
            file_name="filtreli_urun_kalemleri.csv",
            mime="text/csv"
        )

with dcol3:
    st.caption("İndirilen CSV dosyaları Türkçe Excel uyumlu UTF-8 BOM kodlamalıdır.")
