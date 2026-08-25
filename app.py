import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo
import re
import io
import threading
from fpdf import FPDF
from PIL import Image

st.set_page_config(page_title="WMS System", page_icon="📦", layout="wide")

URL_GSHEET_API = st.secrets.get("URL_GSHEET_API", "")
TELEGRAM_BOT_TOKEN = st.secrets.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = st.secrets.get("TELEGRAM_CHAT_ID", "")

# -----------------------------------------------------------------------------
# 📱 RESPONSIVE LAYOUT DETECTOR
# -----------------------------------------------------------------------------
scr_width = st.components.v1.html(
    """<script>
    var width = window.parent.screen.width;
    window.parent.postMessage({type: 'streamlit:set_query_params', query_params: {width: width}}, '*');
    </script>""",
    height=0,
)
width_str = st.query_params.get("width", "1024")
IS_MOBILE = int(width_str) < 768

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

def kompres_gambar(file_uploaded, max_size=(600, 600), quality=70):
    if file_uploaded is None: return None
    try:
        file_uploaded.seek(0)
        img = Image.open(file_uploaded)
        if img.mode in ("RGBA", "P"): img = img.convert("RGB")
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=quality, optimize=True)
        return buffer.getvalue()
    except:
        return file_uploaded.getvalue()

def kirim_notifikasi_telegram(pesan, foto_bytes=None):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID: return
    try:
        if foto_bytes:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
            requests.post(url, data={"chat_id": int(TELEGRAM_CHAT_ID), "caption": pesan}, files={"photo": ("bukti.jpg", foto_bytes, "image/jpeg")}, timeout=15)
        else:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            requests.post(url, json={"chat_id": int(TELEGRAM_CHAT_ID), "text": pesan}, timeout=15)
    except:
        pass

def dapatkan_waktu_wib():
    return datetime.now(ZoneInfo("Asia/Jakarta")).strftime("%d-%m-%Y %H:%M")

def cek_dan_kirim_stok_kritis_manual():
    stok_sekarang = st.session_state.get("stok", {})
    item_habis = [b for b, q in stok_sekarang.items() if q == 0]
    item_kritis = [b for b, q in stok_sekarang.items() if 0 < q < 5]
    if not item_habis and not item_kritis: return "AMAN"
    pesan = f"🚨 **LAPORAN OTOMATIS: STATUS STOK** 🚨\n⏰ {dapatkan_waktu_wib()}\n\n"
    if item_habis:
        pesan += "🔴 **BARANG HABIS:**\n" + "\n".join([f"• {i} (0 pcs)" for i in item_habis]) + "\n\n"
    if item_kritis:
        pesan += "🟡 **BARANG KRITIS:**\n" + "\n".join([f"• {i} ({stok_sekarang[i]} pcs)" for i in item_kritis])
    threading.Thread(target=kirim_notifikasi_telegram, args=(pesan,)).start()
    return "TERKIRIM"

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
    except Exception as e:
        st.error(f"⚠️ Gagal memuat data: {e}")
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
# UI SIDEBAR (SAMA PERSIS DENGAN GAMBAR)
# -----------------------------------------------------------------------------
st.sidebar.markdown("### 📦 WMS System")
st.sidebar.caption("Microcement Warehouse Mgt.")
st.sidebar.divider()

st.sidebar.markdown("#### 🛠️ Pengaturan Sistem")
dark_mode = st.sidebar.toggle("🌙 Aktifkan Dark Mode", value=False)
if st.sidebar.button("🔄 Sinkronisasi Data", type="primary", use_container_width=True):
    st.cache_data.clear()
    st.session_state.stok, st.session_state.riwayat, st.session_state.is_connected = load_data(force_refresh=True)
    st.rerun()

st.sidebar.write("")
st.sidebar.markdown("#### 🤖 Bot Notifikasi")
if st.sidebar.button("🚨 Broadcast Laporan Kritis", type="primary", use_container_width=True):
    status_kirim = cek_dan_kirim_stok_kritis_manual()
    if status_kirim == "AMAN": st.sidebar.success("✅ Stok aman!")
    else: st.sidebar.warning("📤 Dikirim ke Telegram!")

st.sidebar.write("")
st.sidebar.markdown("#### 📌 Navigasi Menu")
menu = st.sidebar.radio(
    "Pilih Menu",
    [
        "📊 Dashboard Stok", 
        "📥 Inbound (Barang Masuk)", 
        "📤 Outbound (Barang Keluar)", 
        "➕ Kelola Master Item", 
        "📜 Log Transaksi",
        "📅 Analytics & Laporan",
        "⚙️ Sistem & Keamanan"
    ],
    label_visibility="collapsed"
)

# -----------------------------------------------------------------------------
# CSS UNTUK MENIRU KARTU METRIK DI GAMBAR
# -----------------------------------------------------------------------------
if dark_mode:
    st.markdown("""
        <style>
        .stApp { background-color: #0F172A !important; color: #F8FAFC !important; }
        .stSidebar { background-color: #1E293B !important; }
        div[data-testid="stMetric"] { background-color: #1E293B; border: 1px solid #334155; border-radius: 10px; padding: 15px 20px; }
        div[data-testid="stMetricLabel"] p { font-size: 13px !important; font-weight: 600 !important; color: #94A3B8; }
        div[data-testid="stMetricValue"] div { font-size: 28px !important; font-weight: 700 !important; color: #38BDF8; }
        </style>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
        <style>
        div[data-testid="stMetric"] { background-color: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 10px; padding: 15px 20px; box-shadow: 0 1px 4px rgba(0,0,0,0.05); }
        div[data-testid="stMetricLabel"] p { font-size: 12px !important; font-weight: 700 !important; color: #6B7280; }
        div[data-testid="stMetricValue"] div { font-size: 32px !important; font-weight: 800 !important; color: #111827; }
        </style>
    """, unsafe_allow_html=True)

if not st.session_state.is_connected:
    st.error("🚨 KONEKSI DATABASE TERPUTUS. Klik Sinkronisasi Data.")

# -----------------------------------------------------------------------------
# MAIN CONTENT LENGKAP
# -----------------------------------------------------------------------------
if menu == "📊 Dashboard Stok":
    st.title("📊 Ringkasan Dashboard & Inventaris")
    
    item_habis = [b for b, q in st.session_state.stok.items() if q == 0]
    item_kritis = [b for b, q in st.session_state.stok.items() if 0 < q < 5]
    total_jenis = len(st.session_state.stok)
    total_unit = sum(st.session_state.stok.values())
    
    # Meniru persis Alert Box kuning di gambar
    if item_habis:
        nama_habis = ", ".join(item_habis)
        st.warning(f"⚠️ Perhatian: **{len(item_habis)} Item** kehabisan stok ({nama_habis}). Segera jadwalkan Restok.")
    
    # Meniru layout kotak angka
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📦 JENIS PRODUK", f"{total_jenis} SKU")
    c2.metric("📊 TOTAL VOLUME", f"{total_unit} Unit")
    c3.metric("🟡 STOK KRITIS (<5)", f"{len(item_kritis)} SKU")
    c4.metric("🔴 STOK KOSONG", f"{len(item_habis)} SKU")
    
    st.write("")
    keyword = st.text_input("🔍 Pencarian Inventaris", placeholder="Ketik nama produk...")
    
    data_tabel = []
    max_stok_val = max(st.session_state.stok.values()) if st.session_state.stok else 30
    
    for barang in sorted(st.session_state.stok.keys(), key=kunci_urut_nama):
        jumlah = st.session_state.stok[barang]
        if keyword.lower() in barang.lower():
            status = "🔴 HABIS" if jumlah == 0 else ("🟡 KRITIS" if jumlah < 5 else "🟢 AMAN")
            data_tabel.append({"Deskripsi Material": barang, "Sisa Stok": jumlah, "Indikator Ketersediaan": jumlah, "Status": status})
    
    if data_tabel:
        df = pd.DataFrame(data_tabel)
        config_tabel = {
            "Deskripsi Material": st.column_config.TextColumn("Deskripsi Material"),
            "Sisa Stok": st.column_config.NumberColumn("Sisa Stok", format="%d Pcs"),
            "Indikator Ketersediaan": st.column_config.ProgressColumn("Indikator Ketersediaan", format="%d", min_value=0, max_value=max(max_stok_val, 20)),
            "Status": st.column_config.TextColumn("Status"),
        }
        st.dataframe(df, column_config=config_tabel, hide_index=True, use_container_width=True)
        
        # --- GRAFIK KEMBALI DIMUNCULKAN DI SINI ---
        st.divider()
        st.subheader("📈 Visualisasi Grafik Stok")
        fig = px.bar(
            df.sort_values("Sisa Stok", ascending=False),
            x="Deskripsi Material",
            y="Sisa Stok",
            color="Status",
            color_discrete_map={"🟢 AMAN": "#22c55e", "🟡 KRITIS": "#eab308", "🔴 HABIS": "#ef4444"},
            text="Sisa Stok"
        )
        fig.update_traces(textposition='outside')
        fig.update_layout(xaxis_title="", yaxis_title="Jumlah (Pcs)", showlegend=True, margin=dict(t=30, b=0, l=0, r=0))
        st.plotly_chart(fig, use_container_width=True)

elif menu == "📥 Inbound (Barang Masuk)":
    st.header("📥 Inbound (Barang Masuk)")
    with st.form("form_masuk", clear_on_submit=True):
        barang_pilihan = st.selectbox("Pilih Barang", sorted(st.session_state.stok.keys(), key=kunci_urut_nama))
        jumlah_masuk = st.number_input("Jumlah Masuk (pcs)", min_value=1, value=1)
        catatan_masuk = st.text_input("Catatan / Supplier (Opsional)", "-")
        if st.form_submit_button("📥 Simpan Restok"):
            w_skrg = dapatkan_waktu_wib()
            st.session_state.stok[barang_pilihan] += jumlah_masuk
            st.session_state.riwayat.insert(0, {"Waktu": w_skrg, "Tipe": "MASUK", "Barang": barang_pilihan, "Jumlah": jumlah_masuk, "Pembeli / Keterangan": catatan_masuk})
            if save_data_atomic(st.session_state.stok, st.session_state.riwayat):
                st.success(f"Berhasil inbound {barang_pilihan} (+{jumlah_masuk} pcs)!")
                st.rerun()

elif menu == "📤 Outbound (Barang Keluar)":
    st.header("📤 Outbound (Barang Keluar)")
    with st.form("form_keluar", clear_on_submit=True):
        barang_pilihan = st.selectbox("Pilih Barang", sorted(st.session_state.stok.keys(), key=kunci_urut_nama))
        stok_saat_ini = st.session_state.stok.get(barang_pilihan, 0)
        st.info(f"Sisa Stok `{barang_pilihan}` saat ini: **{stok_saat_ini} pcs**")
        jumlah_keluar = st.number_input("Jumlah Keluar (pcs)", min_value=1, value=1)
        nama_pembeli = st.text_input("Nama Pembeli / Proyek", "")
        if st.form_submit_button("📤 Simpan Pengiriman"):
            if jumlah_keluar > stok_saat_ini: st.error("Stok tidak cukup!")
            elif not nama_pembeli: st.warning("Isi Nama Pembeli / Proyek!")
            else:
                w_skrg = dapatkan_waktu_wib()
                st.session_state.stok[barang_pilihan] -= jumlah_keluar
                st.session_state.riwayat.insert(0, {"Waktu": w_skrg, "Tipe": "KELUAR", "Barang": barang_pilihan, "Jumlah": jumlah_keluar, "Pembeli / Keterangan": nama_pembeli})
                if save_data_atomic(st.session_state.stok, st.session_state.riwayat):
                    st.success("Pengiriman berhasil dicatat!")
                    st.rerun()

elif menu == "➕ Kelola Master Item":
    st.header("➕ Kelola Master Item")
    with st.form("form_tambah_barang", clear_on_submit=True):
        nama_baru = st.text_input("Nama Barang Baru")
        stok_awal = st.number_input("Stok Awal (pcs)", min_value=0, value=0)
        if st.form_submit_button("➕ Tambah Barang"):
            if not nama_baru.strip(): st.warning("Nama kosong!")
            elif nama_baru.strip() in st.session_state.stok: st.error("Nama sudah ada!")
            else:
                st.session_state.stok[nama_baru.strip()] = stok_awal
                st.session_state.riwayat.insert(0, {"Waktu": dapatkan_waktu_wib(), "Tipe": "BARANG BARU", "Barang": nama_baru.strip(), "Jumlah": stok_awal, "Pembeli / Keterangan": "Item baru"})
                if save_data_atomic(st.session_state.stok, st.session_state.riwayat):
                    st.success("Item berhasil ditambah!")
                    st.rerun()

elif menu == "📜 Log Transaksi":
    st.header("📜 Log Transaksi")
    if st.session_state.riwayat:
        df_riwayat = pd.DataFrame(st.session_state.riwayat)
        st.dataframe(df_riwayat, use_container_width=True, hide_index=True)

elif menu == "📅 Analytics & Laporan":
    st.header("📅 Analytics & Laporan")
    tgl_mulai = st.date_input("Mulai", date.today().replace(day=1))
    tgl_selesai = st.date_input("Selesai", date.today())
    if st.button("Tampilkan Laporan"):
        st.info("Fitur filter laporan sesuai rentang tanggal sedang disiapkan.")

elif menu == "⚙️ Sistem & Keamanan":
    st.header("⚙️ Sistem & Keamanan")
    st.warning("Gunakan fitur ini hanya untuk Backup manual dan Reset Pabrik (Factory Reset).")
