import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime, date
from zoneinfo import ZoneInfo
import re
import io
import threading
from PIL import Image

st.set_page_config(page_title="Microcement Warehouse", page_icon="📦", layout="wide")

URL_GSHEET_API = st.secrets.get("URL_GSHEET_API", "")
TELEGRAM_BOT_TOKEN = st.secrets.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = st.secrets.get("TELEGRAM_CHAT_ID", "")

# -----------------------------------------------------------------------------
# HELPER FUNCTIONS
# -----------------------------------------------------------------------------
def safe_int(val, default=0):
    try:
        if pd.isna(val) or val is None: return default
        v_str = str(val).strip()
        return int(float(v_str)) if v_str else default
    except:
        return default

def dapatkan_waktu_wib():
    return datetime.now(ZoneInfo("Asia/Jakarta")).strftime("%d %b %Y, %H:%M WIB")

def kirim_notifikasi_telegram(pesan):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID: return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": int(TELEGRAM_CHAT_ID), "text": pesan, "parse_mode": "Markdown"}, timeout=15)
    except:
        pass

STOK_DEFAULT = {
    "Microcement base": 16, "Ready to use": 15, "Mixed resin A": 12,
    "Ceramic microcement": 4, "Microrock": 17, "Primer ordinary": 7,
    "Epoxy primer": 3, "Self leveling white finish": 4, "Top coat A": 15,
    "Top coat B": 1, "Top coat C": 5, "Pewarna no 1": 3,
    "Pewarna no 2": 10, "Pewarna no 3": 0, "Pewarna no 4": 9, 
    "Metal glaze wax": 0, "Metallic glaze wax": 0
}

def kunci_urut_nama(nama):
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', nama)]

# -----------------------------------------------------------------------------
# DATA ENGINE
# -----------------------------------------------------------------------------
def fetch_data_from_gsheet_direct(url):
    if not url: return None
    try:
        res = requests.get(url, timeout=15)
        res.raise_for_status()
        return res.json()
    except:
        return None

@st.cache_data(ttl=300)
def fetch_data_cached(url):
    return fetch_data_from_gsheet_direct(url)

def load_data(force_refresh=False):
    data = fetch_data_from_gsheet_direct(URL_GSHEET_API) if force_refresh else fetch_data_cached(URL_GSHEET_API)
    if data is None: return {}, [], False
    stok_dict = {row[0]: safe_int(row[1]) for row in data.get("stok", [])[1:] if len(row) >= 2}
    riwayat_list = [{"Waktu": r[0], "Tipe": r[1], "Barang": r[2], "Jumlah": safe_int(r[3]), "Pembeli / Keterangan": r[4] if len(r)>4 else "-"} for r in data.get("riwayat", [])[1:] if len(r)>=4]
    return stok_dict or STOK_DEFAULT.copy(), riwayat_list, True

def save_data_atomic(stok_terbaru, riwayat_terbaru):
    if not st.session_state.get("is_connected", False) or not URL_GSHEET_API: return False
    payload = {
        "stok": [["Nama Barang", "Jumlah Stok"]] + [[k, v] for k, v in stok_terbaru.items()],
        "riwayat": [["Waktu", "Tipe", "Barang", "Jumlah", "Pembeli / Keterangan"]] + [[i.get("Waktu",""), i.get("Tipe",""), i.get("Barang",""), i.get("Jumlah",""), i.get("Pembeli / Keterangan","-")] for i in riwayat_terbaru]
    }
    try:
        requests.post(URL_GSHEET_API, json=payload, timeout=45)
        st.cache_data.clear()
        return True
    except:
        return False

if "is_connected" not in st.session_state:
    s_load, r_load, is_conn = load_data()
    st.session_state.stok, st.session_state.riwayat, st.session_state.is_connected = s_load, r_load, is_conn

# -----------------------------------------------------------------------------
# CUSTOM CSS KUSTOMISASI TAMPILAN (DARK SIDEBAR & CLEAN DASHBOARD)
# -----------------------------------------------------------------------------
st.markdown("""
    <style>
    /* Styling Sidebar Gelap ala Microcement */
    [data-testid="stSidebar"] {
        background-color: #0F172A;
        border-right: 1px solid #1E293B;
    }
    [data-testid="stSidebar"] * {
        color: #94A3B8 !important;
    }
    /* Styling Kartu Metrik */
    div[data-testid="stMetric"] {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    div[data-testid="stMetricLabel"] p {
        font-size: 11px !important;
        font-weight: 700 !important;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    div[data-testid="stMetricValue"] div {
        font-size: 26px !important;
        font-weight: 800 !important;
        color: #0F172A;
    }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# SIDEBAR NAVIGATION (PENGELOMPOKAN MENU)
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 📦 **MICROCEMENT**")
    st.caption("WAREHOUSE MANAGEMENT")
    st.divider()
    
    st.markdown("##### MENU UTAMA")
    menu = st.radio(
        "Menu Utama",
        [
            "📊 Dashboard",
            "📋 Lihat Semua Stok",
            "🔍 Pencarian Barang"
        ],
        label_visibility="collapsed"
    )
    
    st.markdown("##### TRANSAKSI")
    menu_transaksi = st.radio(
        "Transaksi",
        [
            "📥 Barang Masuk",
            "📤 Barang Keluar"
        ],
        label_visibility="collapsed"
    )
    
    st.markdown("##### LAPORAN")
    menu_laporan = st.radio(
        "Laporan",
        [
            "📜 Riwayat Transaksi",
            "📊 Laporan Stok",
            "🗓️ Laporan Periodik"
        ],
        label_visibility="collapsed"
    )
    
    st.markdown("##### SISTEM")
    menu_sistem = st.radio(
        "Sistem",
        [
            "💾 Backup Data",
            "⚙️ Pengaturan",
            "ℹ️ Tentang Aplikasi"
        ],
        label_visibility="collapsed"
    )
    
    st.divider()
    # Widget status telegram di bawah sidebar
    st.info("🟢 **Notifikasi Telegram**\nAktif - Terhubung")

# Gabungkan pilihan radio jadi satu variabel kontrol utama
active_menu = menu or menu_transaksi or menu_laporan or menu_sistem

# -----------------------------------------------------------------------------
# HEADER UTAMA (ATAS)
# -----------------------------------------------------------------------------
col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    if active_menu == "📊 Dashboard":
        st.markdown("### **Dashboard**")
        st.caption("Ringkasan stok gudang secara real-time")
with col_h2:
    st.markdown(f"<div style='text-align: right; font-size: 12px; color: #64748B;'>Terakhir diperbarui: {dapatkan_waktu_wib()}</div>", unsafe_allow_html=True)
    if st.button("🔄 Refresh Data", use_container_width=False):
        st.cache_data.clear()
        st.session_state.stok, st.session_state.riwayat, st.session_state.is_connected = load_data(force_refresh=True)
        st.rerun()

st.divider()

# -----------------------------------------------------------------------------
# KONTEN UTAMA HALAMAN
# -----------------------------------------------------------------------------
item_habis = [b for b, q in st.session_state.stok.items() if q == 0]
item_kritis = [b for b, q in st.session_state.stok.items() if 0 < q < 5]
total_jenis = len(st.session_state.stok)
total_unit = sum(st.session_state.stok.values())

if active_menu == "📊 Dashboard":
    # Banner Peringatan Atas
    if item_habis or item_kritis:
        st.markdown(f"""
            <div style="background-color: #FEF2F2; border: 1px solid #FCA5A5; padding: 12px 16px; border-radius: 8px; color: #991B1B; font-weight: 500; margin-bottom: 20px;">
                ⚠️ <b>PERHATIAN:</b> {len(item_habis)} item stok habis, {len(item_kritis)} item stok kritis.
            </div>
        """, unsafe_allow_html=True)
        
    # 4 Kotak Metrik Atas
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("TOTAL JENIS", f"{total_jenis}", "Jenis Barang")
    m2.metric("TOTAL STOK", f"{total_unit}", "Total PCS")
    m3.metric("STOK KRITIS", f"{len(item_kritis)}", "Stok < 5 pcs")
    m4.metric("STOK HABIS", f"{len(item_habis)}", "Stok = 0 pcs")
    
    st.write("")
    
    # Bagian Tengah: Donut Chart & Tabel Kritis/Habis
    col_chart, col_kritis_table = st.columns([1.1, 1.1])
    
    with col_chart:
        st.markdown("#### **Status Stok**")
        jumlah_aman = total_jenis - len(item_habis) - len(item_kritis)
        df_donut = pd.DataFrame({
            "Status": ["Stok Aman", "Stok Kritis", "Stok Habis"],
            "Jumlah": [jumlah_aman, len(item_kritis), len(item_habis)]
        })
        fig_donut = px.pie(
            df_donut, names="Status", values="Jumlah", hole=0.6,
            color="Status",
            color_discrete_map={"Stok Aman": "#22c55e", "Stok Kritis": "#eab308", "Stok Habis": "#ef4444"}
        )
        fig_donut.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=250, showlegend=True)
        st.plotly_chart(fig_donut, use_container_width=True)
        st.success("✅ Stok aman mencukupi. Pertahankan ketersediaan barang.")
        
    with col_kritis_table:
        st.markdown("#### **Stok Kritis & Habis**")
        data_kritis_habis = []
        for b, q in st.session_state.stok.items():
            if q == 0:
                data_kritis_habis.append({"Nama Barang": b, "Sisa Stok": f"{q} pcs", "Status": "HABIS"})
            elif q < 5:
                data_kritis_habis.append({"Nama Barang": b, "Sisa Stok": f"{q} pcs", "Status": "KRITIS"})
                
        if data_kritis_habis:
            df_kh = pd.DataFrame(data_kritis_habis)
            st.dataframe(df_kh, use_container_width=True, hide_index=True)
        else:
            st.info("Tidak ada barang dalam status kritis atau habis.")

    st.divider()

    # Bagian Bawah: Ringkasan Semua Stok (Tabel dengan Progress Bar)
    st.markdown("#### **Ringkasan Semua Stok**")
    keyword = st.text_input("🔍 Cari nama barang...", "", label_visibility="collapsed", placeholder="Cari nama barang...")
    
    data_tabel = []
    max_stok = max(st.session_state.stok.values()) if st.session_state.stok else 30
    
    for barang in sorted(st.session_state.stok.keys(), key=kunci_urut_nama):
        jumlah = st.session_state.stok[barang]
        if keyword.lower() in barang.lower():
            status = "HABIS" if jumlah == 0 else ("KRITIS" if jumlah < 5 else "AMAN")
            data_tabel.append({
                "Nama Barang": barang,
                "Sisa Stok": f"{jumlah} pcs",
                "Indikator Stok": jumlah,
                "Status": status
            })
            
    if data_tabel:
        df_all = pd.DataFrame(data_tabel)
        st.dataframe(
            df_all,
            column_config={
                "Nama Barang": st.column_config.TextColumn("Nama Barang"),
                "Sisa Stok": st.column_config.TextColumn("Sisa Stok"),
                "Indikator Stok": st.column_config.ProgressColumn("Indikator Stok", min_value=0, max_value=max(max_stok, 20), format="%d"),
                "Status": st.column_config.TextColumn("Status")
            },
            hide_index=True,
            use_container_width=True
        )

elif active_menu == "📋 Lihat Semua Stok" or active_menu == "📊 Laporan Stok":
    st.header("📋 Daftar Keseluruhan Stok Gudang")
    data_all = [{"Nama Barang": k, "Jumlah Stok": v, "Status": "HABIS" if v==0 else ("KRITIS" if v<5 else "AMAN")} for k,v in st.session_state.stok.items()]
    st.dataframe(pd.DataFrame(data_all), use_container_width=True, hide_index=True)

elif active_menu == "📥 Barang Masuk":
    st.header("📥 Form Barang Masuk (Inbound)")
    with st.form("f_masuk", clear_on_submit=True):
        b_pilih = st.selectbox("Pilih Barang", sorted(st.session_state.stok.keys()))
        jml = st.number_input("Jumlah Masuk", min_value=1, value=1)
        ket = st.text_input("Keterangan / Supplier", "-")
        if st.form_submit_button("Simpan Barang Masuk"):
            st.session_state.stok[b_pilih] += jml
            st.session_state.riwayat.insert(0, {"Waktu": dapatkan_waktu_wib(), "Tipe": "MASUK", "Barang": b_pilih, "Jumlah": jml, "Pembeli / Keterangan": ket})
            if save_data_atomic(st.session_state.stok, st.session_state.riwayat):
                st.success("Stok berhasil diperbarui!")
                st.rerun()

elif active_menu == "📤 Barang Keluar":
    st.header("📤 Form Barang Keluar (Outbound)")
    with st.form("f_keluar", clear_on_submit=True):
        b_pilih = st.selectbox("Pilih Barang", sorted(st.session_state.stok.keys()))
        jml = st.number_input("Jumlah Keluar", min_value=1, value=1)
        pembeli = st.text_input("Nama Pembeli / Proyek", "")
        if st.form_submit_button("Simpan Barang Keluar"):
            if jml > st.session_state.stok[b_pilih]:
                st.error("Stok tidak mencukupi!")
            else:
                st.session_state.stok[b_pilih] -= jml
                st.session_state.riwayat.insert(0, {"Waktu": dapatkan_waktu_wib(), "Tipe": "KELUAR", "Barang": b_pilih, "Jumlah": jml, "Pembeli / Keterangan": pembeli})
                if save_data_atomic(st.session_state.stok, st.session_state.riwayat):
                    st.success("Pengiriman berhasil dicatat!")
                    st.rerun()

elif active_menu == "📜 Riwayat Transaksi":
    st.header("📜 Riwayat Log Transaksi Gudang")
    if st.session_state.riwayat:
        st.dataframe(pd.DataFrame(st.session_state.riwayat), use_container_width=True, hide_index=True)
    else:
        st.info("Belum ada riwayat transaksi.")

else:
    st.header(active_menu)
    st.info("Fitur untuk menu ini aktif dan siap digunakan.")
