import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo
import re
import io
import base64
import threading
from fpdf import FPDF
from PIL import Image

# -----------------------------------------------------------------------------
# KONFIGURASI HALAMAN UTAMA
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Microcement Warehouse Pro", page_icon="📦", layout="wide", initial_sidebar_state="expanded")

URL_GSHEET_API = st.secrets.get("URL_GSHEET_API", "")
TELEGRAM_BOT_TOKEN = st.secrets.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = st.secrets.get("TELEGRAM_CHAT_ID", "")

# -----------------------------------------------------------------------------
# 📱 RESPONSIVE LAYOUT HACK (Deteksi Ukuran Layar HP)
# -----------------------------------------------------------------------------
scr_width = st.components.v1.html(
    """
    <script>
    var width = window.parent.screen.width;
    window.parent.postMessage({
        type: 'streamlit:set_query_params',
        query_params: {width: width}
    }, '*');
    </script>
    """,
    height=0,
)

width_str = st.query_params.get("width", "1024")
SCREEN_WIDTH = int(width_str)
IS_MOBILE = SCREEN_WIDTH < 768

# -----------------------------------------------------------------------------
# 🎨 FUNGSI TEMA / UI KUSTOM (ENTERPRISE LOOK)
# -----------------------------------------------------------------------------
def terapkan_tema_profesional(dark_mode=False):
    font_url = "@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');"
    
    if dark_mode:
        theme = """
        :root {
            --bg-color: #0F172A;
            --text-main: #F8FAFC;
            --text-muted: #94A3B8;
            --card-bg: #1E293B;
            --sidebar-bg: #111827;
            --border-color: #334155;
            --accent-primary: #0284C7;
            --accent-hover: #0369A1;
            --success: #10B981;
            --danger: #EF4444;
            --warning: #F59E0B;
        }
        """
    else:
        theme = """
        :root {
            --bg-color: #F8FAFC;
            --text-main: #0F172A;
            --text-muted: #64748B;
            --card-bg: #FFFFFF;
            --sidebar-bg: #FFFFFF;
            --border-color: #E2E8F0;
            --accent-primary: #0EA5E9;
            --accent-hover: #0284C7;
            --success: #10B981;
            --danger: #EF4444;
            --warning: #F59E0B;
        }
        """

    css = f"""
    <style>
    {font_url}
    {theme}
    
    /* Global Typography */
    html, body, [class*="css"] {{
        font-family: 'Inter', sans-serif !important;
        color: var(--text-main) !important;
    }}
    
    /* Main App Background */
    .stApp {{
        background-color: var(--bg-color) !important;
    }}
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {{
        background-color: var(--sidebar-bg) !important;
        border-right: 1px solid var(--border-color) !important;
    }}
    
    /* Headers & Text */
    h1, h2, h3, h4, h5, h6, span, p, label {{
        color: var(--text-main) !important;
    }}
    
    /* Dashboard Metrics Cards */
    [data-testid="stMetric"] {{
        background-color: var(--card-bg) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 16px !important;
        padding: 20px 24px !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03) !important;
        transition: transform 0.2s ease, box-shadow 0.2s ease !important;
    }}
    [data-testid="stMetric"]:hover {{
        transform: translateY(-3px) !important;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.08), 0 4px 6px -2px rgba(0, 0, 0, 0.04) !important;
    }}
    [data-testid="stMetricLabel"] p {{
        color: var(--text-muted) !important;
        font-size: 13px !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}
    [data-testid="stMetricValue"] div {{
        color: var(--accent-primary) !important;
        font-size: 32px !important;
        font-weight: 800 !important;
        margin-top: 8px !important;
    }}
    
    /* Buttons */
    .stButton>button, .stDownloadButton>button, [data-testid="stFormSubmitButton"]>button {{
        background: linear-gradient(135deg, var(--accent-primary) 0%, var(--accent-hover) 100%) !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 10px 20px !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        letter-spacing: 0.3px !important;
        transition: all 0.2s ease-in-out !important;
        width: 100% !important;
    }}
    .stButton>button:hover, .stDownloadButton>button:hover, [data-testid="stFormSubmitButton"]>button:hover {{
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(2, 132, 199, 0.3) !important;
    }}
    
    /* Input Fields (Select, Text, Number, Date) */
    .stTextInput>div>div>input, .stNumberInput>div>div>input, .stDateInput>div>div>input {{
        background-color: var(--card-bg) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 8px !important;
        color: var(--text-main) !important;
        padding: 12px 14px !important;
    }}
    .stTextInput>div>div>input:focus, .stNumberInput>div>div>input:focus {{
        border-color: var(--accent-primary) !important;
        box-shadow: 0 0 0 1px var(--accent-primary) !important;
    }}
    
    /* Dataframes & Tables */
    [data-testid="stDataFrame"], [data-testid="stTable"] {{
        background-color: var(--card-bg) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 12px !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02) !important;
        padding: 8px !important;
    }}
    
    /* Forms */
    [data-testid="stForm"] {{
        background-color: var(--card-bg) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 16px !important;
        padding: 24px !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }}
    
    /* File Uploader */
    [data-testid="stFileUploader"] {{
        background-color: var(--bg-color) !important;
        border: 1px dashed var(--border-color) !important;
        border-radius: 12px !important;
        padding: 16px !important;
    }}
    
    /* Status Badges - You can inject HTML if needed, but styling st.info/warning */
    [data-testid="stAlert"] {{
        border-radius: 12px !important;
        border: none !important;
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# HELPER FUNCTIONS (Logika Bisnis Tidak Diubah)
# -----------------------------------------------------------------------------

def safe_int(val, default=0):
    try:
        if val is None or pd.isna(val):
            return default
        val_str = str(val).strip()
        if not val_str:
            return default
        return int(float(val_str))
    except Exception:
        return default

def kompres_gambar(file_uploaded, max_size=(600, 600), quality=70):
    if file_uploaded is None:
        return None
    try:
        file_uploaded.seek(0)
        img = Image.open(file_uploaded)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=quality, optimize=True)
        return buffer.getvalue()
    except Exception:
        return file_uploaded.getvalue()

def kirim_notifikasi_telegram(pesan, foto_bytes=None):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        if foto_bytes:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
            payload = {"chat_id": int(TELEGRAM_CHAT_ID), "caption": pesan}
            files = {"photo": ("bukti.jpg", foto_bytes, "image/jpeg")}
            requests.post(url, data=payload, files=files, timeout=15)
        else:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {"chat_id": int(TELEGRAM_CHAT_ID), "text": pesan}
            requests.post(url, json=payload, timeout=15)
    except Exception as e:
        print(f"Gagal mengirim notifikasi Telegram: {e}")

def kirim_dokumen_telegram(pesan, file_bytes, file_name):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
        payload = {"chat_id": int(TELEGRAM_CHAT_ID), "caption": pesan}
        files = {"document": (file_name, file_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        requests.post(url, data=payload, files=files, timeout=30)
    except Exception as e:
        print(f"Gagal mengirim dokumen backup: {e}")

def cek_dan_kirim_stok_kritis_manual():
    stok_sekarang = st.session_state.get("stok", {})
    item_habis = [b for b, q in stok_sekarang.items() if q == 0]
    item_kritis = [b for b, q in stok_sekarang.items() if 0 < q < 5]
    
    if not item_habis and not item_kritis:
        return "AMAN"
    
    pesan = "🚨 **LAPORAN OTOMATIS: STATUS STOK GUDANG** 🚨\n"
    pesan += f"⏰ Waktu Pengecekan: {dapatkan_waktu_wib()}\n\n"
    if item_habis:
        pesan += "🔴 **BARANG HABIS (Stok 0):**\n"
        for item in item_habis:
            pesan += f"• {item} (0 pcs)\n"
        pesan += "\n"
    if item_kritis:
        pesan += "🟡 **BARANG KRITIS (Stok < 5):**\n"
        for item in item_kritis:
            pesan += f"• {item} ({stok_sekarang[item]} pcs)\n"
    pesan += "\n⚠️ Mohon segera lakukan restok untuk item di atas."
    threading.Thread(target=kirim_notifikasi_telegram, args=(pesan,)).start()
    return "TERKIRIM"

def buat_excel_backup_lengkap(stok_dict, riwayat_list):
    output = io.BytesIO()
    df_stok = pd.DataFrame(list(stok_dict.items()), columns=["Nama Barang", "Jumlah Stok"])
    df_riwayat = pd.DataFrame(riwayat_list) if riwayat_list else pd.DataFrame(columns=["Waktu", "Tipe", "Barang", "Jumlah", "Pembeli / Keterangan"])
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_stok.to_excel(writer, index=False, sheet_name="Stok Barang")
        df_riwayat.to_excel(writer, index=False, sheet_name="Riwayat Transaksi")
    return output.getvalue()

def dapatkan_waktu_wib():
    return datetime.now(ZoneInfo("Asia/Jakarta")).strftime("%d-%m-%Y %H:%M")

def parse_waktu(waktu_str):
    if not waktu_str:
        return None
    waktu_str = str(waktu_str).strip()
    try:
        dt = datetime.fromisoformat(waktu_str.replace('Z', '+00:00'))
        return dt.replace(tzinfo=None)
    except Exception:
        pass
    formats = ["%d-%m-%Y %H:%M", "%d-%m-%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]
    for fmt in formats:
        try:
            return datetime.strptime(waktu_str, fmt)
        except ValueError:
            pass
    return None

def buat_excel_bytes(df, sheet_name="Data"):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    return output.getvalue()

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

def bersihkan_teks_pdf(teks):
    teks_str = str(teks).strip()
    return teks_str.encode('latin-1', 'replace').decode('latin-1')

def buat_pdf_tabel(judul, headers, data, col_widths, info_tambahan=""):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, judul, ln=True, align="C")
    if info_tambahan:
        pdf.set_font("Helvetica", "I", 9)
        pdf.cell(0, 6, info_tambahan, ln=True, align="C")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 6, f"Tanggal Cetak: {dapatkan_waktu_wib()}", ln=True, align="C")
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(230, 230, 230)
    for i, h in enumerate(headers):
        pdf.cell(col_widths[i], 8, h, border=1, align="C", fill=True)
    pdf.ln()
    pdf.set_font("Helvetica", "", 8)
    for row in data:
        for i, val in enumerate(row):
            teks_bersih = bersihkan_teks_pdf(val)
            align_text = "C" if i in [0, 1, 3] else "L"
            pdf.cell(col_widths[i], 7, teks_bersih, border=1, align=align_text)
        pdf.ln()
    return bytes(pdf.output())

def filter_riwayat_berdasarkan_rentang(riwayat_list, tgl_mulai, tgl_selesai):
    if not riwayat_list:
        return []
    dt_mulai = datetime.combine(tgl_mulai, datetime.min.time())
    dt_selesai = datetime.combine(tgl_selesai, datetime.max.time())
    hasil = []
    for item in riwayat_list:
        tgl = parse_waktu(item.get("Waktu", ""))
        if tgl and dt_mulai <= tgl <= dt_selesai:
            item_formatted = item.copy()
            item_formatted["Waktu"] = tgl.strftime("%d-%m-%Y %H:%M")
            hasil.append(item_formatted)
    return hasil

# -----------------------------------------------------------------------------
# DATA ENGINE
# -----------------------------------------------------------------------------

def fetch_data_from_gsheet_direct(url):
    if not url:
        return None
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
    if force_refresh:
        data = fetch_data_from_gsheet_direct(URL_GSHEET_API)
    else:
        data = fetch_data_cached(URL_GSHEET_API)
        
    if data is None:
        return {}, [], False

    raw_stok = data.get("stok", [])
    stok_dict = {}
    if len(raw_stok) > 1:
        for row in raw_stok[1:]:
            if len(row) >= 2:
                stok_dict[row[0]] = safe_int(row[1])
    
    raw_riwayat = data.get("riwayat", [])
    riwayat_list = []
    if len(raw_riwayat) > 1:
        for row in raw_riwayat[1:]:
            if len(row) >= 4:
                pembeli = row[4] if len(row) >= 5 else "-"
                riwayat_list.append({
                    "Waktu": row[0], "Tipe": row[1], "Barang": row[2], 
                    "Jumlah": safe_int(row[3]), "Pembeli / Keterangan": pembeli
                })
                
    if not stok_dict and len(raw_stok) <= 1:
        stok_dict = STOK_DEFAULT.copy()
        
    return stok_dict, riwayat_list, True

def save_data_atomic(stok_terbaru, riwayat_terbaru):
    if not st.session_state.get("is_connected", False):
        st.error("❌ Transaksi dibatalkan: Koneksi database terputus.")
        return False
    if not URL_GSHEET_API:
        st.warning("URL API belum dikonfigurasi.")
        return False
        
    stok_payload = [["Nama Barang", "Jumlah Stok"]] + [[k, v] for k, v in stok_terbaru.items()]
    riwayat_payload = [["Waktu", "Tipe", "Barang", "Jumlah", "Pembeli / Keterangan"]]
    for item in riwayat_terbaru:
        riwayat_payload.append([
            item.get("Waktu", ""), item.get("Tipe", ""), item.get("Barang", ""),
            item.get("Jumlah", ""), item.get("Pembeli / Keterangan", "-")
        ])

    payload = {"stok": stok_payload, "riwayat": riwayat_payload}
    try:
        res = requests.post(URL_GSHEET_API, json=payload, timeout=45)
        res.raise_for_status()
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Gagal menyimpan data: {e}")
        return False

if "is_connected" not in st.session_state:
    stok_loaded, riwayat_loaded, is_conn = load_data()
    st.session_state.stok = stok_loaded
    st.session_state.riwayat = riwayat_loaded
    st.session_state.is_connected = is_conn

# -----------------------------------------------------------------------------
# UI STREAMLIT (ENTERPRISE UPGRADE)
# -----------------------------------------------------------------------------

# Sidebar Panel Profile/Header
st.sidebar.markdown("""
<div style="text-align: center; margin-bottom: 20px;">
    <h2 style="margin-bottom: 0px; font-weight: 700; color: var(--accent-primary);">📦 WMS System</h2>
    <p style="color: var(--text-muted); font-size: 12px; margin-top: 0px;">Microcement Warehouse Mgt.</p>
</div>
""", unsafe_allow_html=True)

# App Theme Setup
st.sidebar.subheader("🛠️ Pengaturan Sistem")
dark_mode = st.sidebar.toggle("🌙 Aktifkan Dark Mode", value=False)
terapkan_tema_profesional(dark_mode)

if st.sidebar.button("🔄 Sinkronisasi Data", use_container_width=True):
    st.cache_data.clear()
    stok_ref, riwayat_ref, is_conn = load_data(force_refresh=True)
    st.session_state.stok = stok_ref
    st.session_state.riwayat = riwayat_ref
    st.session_state.is_connected = is_conn
    if is_conn:
        st.toast("Data tersinkronisasi dengan sukses!", icon="✅")
    else:
        st.error("Gagal menyinkronkan data.")
    st.rerun()

st.sidebar.divider()
st.sidebar.subheader("📡 Bot Notifikasi")
if st.sidebar.button("🚨 Broadcast Laporan Kritis", use_container_width=True):
    status_kirim = cek_dan_kirim_stok_kritis_manual()
    if status_kirim == "AMAN":
        st.sidebar.success("✅ Stok terpantau aman.")
    else:
        st.sidebar.warning("📤 Peringatan stok kritis telah dikirim.")

st.sidebar.divider()
menu = st.sidebar.radio("📌 Navigasi Menu", [
    "📊 Dashboard Stok", 
    "📥 Inbound (Barang Masuk)", 
    "📤 Outbound (Barang Keluar)", 
    "➕ Kelola Master Item", 
    "📜 Log Transaksi",
    "🗓️ Analytics & Laporan",
    "⚙️ Sistem & Keamanan"
])

# -----------------------------------------------------------------------------
# MAIN LAYOUT & LOGIC
# -----------------------------------------------------------------------------

if not st.session_state.is_connected:
    st.error("🚨 **KONEKSI DATABASE TERPUTUS!** Sistem beralih ke mode Read-Only. Periksa koneksi internet Anda.")

item_habis = [b for b, q in st.session_state.stok.items() if q == 0]
item_kritis = [b for b, q in st.session_state.stok.items() if 0 < q < 5]

if menu == "📊 Dashboard Stok":
    st.markdown("<h2 style='font-weight: 700; margin-bottom: 24px;'>📊 Ringkasan Dashboard & Inventaris</h2>", unsafe_allow_html=True)
    
    total_jenis = len(st.session_state.stok)
    total_unit = sum(st.session_state.stok.values())
    
    # Menampilkan peringatan elegan jika ada stok habis
    if item_habis:
        st.warning(f"⚠️ Perhatian: **{len(item_habis)} Item** kehabisan stok ({', '.join(item_habis[:3])}{'...' if len(item_habis)>3 else ''}). Segera jadwalkan Restok.")

    if IS_MOBILE:
        with st.container():
            st.metric("📦 Jenis Produk", f"{total_jenis} SKU")
            st.metric("📊 Total Volume", f"{total_unit} Unit")
            st.metric("🟡 Stok Kritis", f"{len(item_kritis)} SKU")
            st.metric("🔴 Stok Kosong", f"{len(item_habis)} SKU")
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📦 Jenis Produk", f"{total_jenis} SKU")
        c2.metric("📊 Total Volume", f"{total_unit} Unit")
        c3.metric("🟡 Stok Kritis (<5)", f"{len(item_kritis)} SKU")
        c4.metric("🔴 Stok Kosong", f"{len(item_habis)} SKU")
    
    st.markdown("<br>", unsafe_allow_html=True)
    keyword = st.text_input("🔍 Pencarian Inventaris", placeholder="Ketik nama produk...")
    
    data_tabel = []
    max_stok_val = max(st.session_state.stok.values()) if st.session_state.stok else 30
    
    for barang in sorted(st.session_state.stok.keys(), key=kunci_urut_nama):
        jumlah = st.session_state.stok[barang]
        if keyword.lower() in barang.lower():
            status = "🔴 HABIS" if jumlah == 0 else ("🟡 KRITIS" if jumlah < 5 else "🟢 AMAN")
            data_tabel.append({
                "Nama Barang": barang,
                "Jumlah Stok": jumlah,
                "Progress Visual": jumlah,
                "Status": status
            })
    
    if data_tabel:
        df = pd.DataFrame(data_tabel)
        config_tabel = {
            "Nama Barang": st.column_config.TextColumn("Deskripsi Material"),
            "Jumlah Stok": st.column_config.NumberColumn("Sisa Stok", format="%d Pcs"),
            "Progress Visual": st.column_config.ProgressColumn(
                "Indikator Ketersediaan",
                format="%d",
                min_value=0,
                max_value=max(max_stok_val, 20),
            ),
            "Status": st.column_config.TextColumn("Status"),
        }
        
        st.dataframe(df, column_config=config_tabel, hide_index=True, use_container_width=True)
            
        st.markdown("<br>", unsafe_allow_html=True)
        col_exp1, col_exp2 = st.columns(2)
        with col_exp1:
            excel_bytes = buat_excel_bytes(df[["Nama Barang", "Jumlah Stok", "Status"]], "Stok Gudang")
            st.download_button("📥 Ekspor ke Excel (.xlsx)", excel_bytes, f"Inventaris_{datetime.now().strftime('%Y%m%d')}.xlsx", use_container_width=True)
        with col_exp2:
            headers_pdf = ["No", "Deskripsi Material", "Sisa Stok", "Status"]
            data_pdf = [[str(i+1), r["Nama Barang"], f"{r['Jumlah Stok']} pcs", r["Status"]] for i, r in enumerate(data_tabel)]
            pdf_bytes = buat_pdf_tabel("LAPORAN INVENTARIS GUDANG", headers_pdf, data_pdf, [15, 95, 35, 45])
            st.download_button("📄 Cetak Dokumen PDF", pdf_bytes, f"Inventaris_{datetime.now().strftime('%Y%m%d')}.pdf", use_container_width=True)

elif menu == "📥 Inbound (Barang Masuk)":
    st.markdown("<h2 style='font-weight: 700; margin-bottom: 24px;'>📥 Registrasi Barang Masuk</h2>", unsafe_allow_html=True)
    with st.form("form_masuk", clear_on_submit=True):
        st.markdown("<p style='color: var(--text-muted); font-size: 14px;'>Catat penerimaan stok material baru dari supplier.</p>", unsafe_allow_html=True)
        barang_pilihan = st.selectbox("Pilih Material SKU", sorted(st.session_state.stok.keys(), key=kunci_urut_nama))
        jumlah_masuk = st.number_input("Kuantitas (Pcs)", min_value=1, value=1, step=1)
        catatan_masuk = st.text_input("Referensi / Vendor (Opsional)", placeholder="Nama supplier atau nomor DO...")
        foto_bukti = st.file_uploader("Upload Dokumen Penerimaan (Opsional)", type=["jpg", "jpeg", "png"])
        
        st.markdown("<br>", unsafe_allow_html=True)
        submitted = st.form_submit_button("Selesaikan Penerimaan")
        
        if submitted:
            waktu_sekarang = dapatkan_waktu_wib()
            st.session_state.stok[barang_pilihan] += jumlah_masuk
            st.session_state.riwayat.insert(0, {
                "Waktu": waktu_sekarang, "Tipe": "MASUK", "Barang": barang_pilihan,
                "Jumlah": jumlah_masuk, "Pembeli / Keterangan": catatan_masuk
            })
            
            if save_data_atomic(st.session_state.stok, st.session_state.riwayat):
                st.success(f"✅ Transaksi berhasil: {barang_pilihan} (+{jumlah_masuk} unit)")
                pesan_tg = f"📥 **INBOUND MATERIAL**\n\n📦 SKU: {barang_pilihan}\n➕ Vol: +{jumlah_masuk} Pcs\n📊 Stok Tersedia: {st.session_state.stok[barang_pilihan]} Pcs\n📝 Ref: {catatan_masuk}\n⏰ Tgl: {waktu_sekarang}"
                foto_kompresed = kompres_gambar(foto_bukti)
                threading.Thread(target=kirim_notifikasi_telegram, args=(pesan_tg, foto_kompresed)).start()
                st.rerun()

elif menu == "📤 Outbound (Barang Keluar)":
    st.markdown("<h2 style='font-weight: 700; margin-bottom: 24px;'>📤 Dispatch Barang Keluar</h2>", unsafe_allow_html=True)
    with st.form("form_keluar", clear_on_submit=True):
        st.markdown("<p style='color: var(--text-muted); font-size: 14px;'>Catat pengeluaran material untuk distribusi atau proyek.</p>", unsafe_allow_html=True)
        barang_pilihan = st.selectbox("Pilih Material SKU", sorted(st.session_state.stok.keys(), key=kunci_urut_nama))
        stok_saat_ini = st.session_state.stok.get(barang_pilihan, 0)
        st.info(f"Stok tersedia untuk diproses: **{stok_saat_ini} Unit**")
        
        jumlah_keluar = st.number_input("Kuantitas (Pcs)", min_value=1, value=1, step=1)
        nama_pembeli = st.text_input("Identitas Pemohon / ID Proyek", placeholder="Wajib diisi...")
        foto_bukti = st.file_uploader("Upload Bukti Surat Jalan (Opsional)", type=["jpg", "jpeg", "png"])
        
        st.markdown("<br>", unsafe_allow_html=True)
        submitted = st.form_submit_button("Proses Pengeluaran")
        
        if submitted:
            if jumlah_keluar > stok_saat_ini:
                st.error(f"❌ Transaksi ditolak: Stok tidak mencukupi (Tersedia {stok_saat_ini} unit).")
            elif not nama_pembeli.strip():
                st.warning("⚠️ Validasi gagal: Identitas pemohon/proyek wajib diisi.")
            else:
                waktu_sekarang = dapatkan_waktu_wib()
                st.session_state.stok[barang_pilihan] -= jumlah_keluar
                st.session_state.riwayat.insert(0, {
                    "Waktu": waktu_sekarang, "Tipe": "KELUAR", "Barang": barang_pilihan,
                    "Jumlah": jumlah_keluar, "Pembeli / Keterangan": nama_pembeli.strip()
                })
                
                if save_data_atomic(st.session_state.stok, st.session_state.riwayat):
                    st.success(f"✅ Pengeluaran {barang_pilihan} ({jumlah_keluar} unit) telah diotorisasi.")
                    pesan_tg = f"📤 **OUTBOUND MATERIAL**\n\n📦 SKU: {barang_pilihan}\n➖ Vol: -{jumlah_keluar} Pcs\n👤 Proyek: {nama_pembeli.strip()}\n📊 Stok Tersisa: {st.session_state.stok[barang_pilihan]} Pcs\n⏰ Tgl: {waktu_sekarang}"
                    foto_kompresed = kompres_gambar(foto_bukti)
                    threading.Thread(target=kirim_notifikasi_telegram, args=(pesan_tg, foto_kompresed)).start()
                    st.rerun()

elif menu == "➕ Kelola Master Item":
    st.markdown("<h2 style='font-weight: 700; margin-bottom: 24px;'>➕ Registrasi Master Item SKU</h2>", unsafe_allow_html=True)
    with st.form("form_tambah_barang", clear_on_submit=True):
        st.markdown("<p style='color: var(--text-muted); font-size: 14px;'>Tambahkan jenis produk/material baru ke dalam sistem basis data.</p>", unsafe_allow_html=True)
        nama_baru = st.text_input("Nama Deskripsi SKU Baru")
        stok_awal = st.number_input("Saldo Awal (Pcs)", min_value=0, value=0, step=1)
        
        st.markdown("<br>", unsafe_allow_html=True)
        submitted = st.form_submit_button("Simpan Master Data")
        if submitted:
            nama_clean = nama_baru.strip()
            if not nama_clean:
                st.warning("⚠️ Validasi gagal: Nama tidak boleh kosong.")
            elif nama_clean in st.session_state.stok:
                st.error("❌ Konflik data: Nama barang telah terdaftar di database.")
            else:
                waktu_sekarang = dapatkan_waktu_wib()
                st.session_state.stok[nama_clean] = stok_awal
                st.session_state.riwayat.insert(0, {
                    "Waktu": waktu_sekarang, "Tipe": "BARANG BARU", "Barang": nama_clean,
                    "Jumlah": stok_awal, "Pembeli / Keterangan": "Registrasi Item SKU"
                })
                if save_data_atomic(st.session_state.stok, st.session_state.riwayat):
                    st.success(f"✅ Master item `{nama_clean}` sukses diregistrasi.")
                    st.rerun()

elif menu == "📜 Log Transaksi":
    st.markdown("<h2 style='font-weight: 700; margin-bottom: 24px;'>📜 Sistem Log Transaksi</h2>", unsafe_allow_html=True)
    if not st.session_state.riwayat:
        st.info("Log aktivitas masih kosong.")
    else:
        df_riwayat = pd.DataFrame(st.session_state.riwayat)
        
        c1, c2 = st.columns(2)
        with c1:
            filter_tipe = st.selectbox("Klasifikasi Transaksi", ["SEMUA", "MASUK", "KELUAR", "BARANG BARU"])
        with c2:
            search_item = st.text_input("🔍 Filter (Barang / Proyek)", placeholder="Pencarian cepat...")
            
        df_filtered = df_riwayat.copy()
        if filter_tipe != "SEMUA":
            df_filtered = df_filtered[df_filtered["Tipe"] == filter_tipe]
        if search_item:
            mask = df_filtered["Barang"].astype(str).str.contains(search_item, case=False, na=False) | df_filtered["Pembeli / Keterangan"].astype(str).str.contains(search_item, case=False, na=False)
            df_filtered = df_filtered[mask]
            
        st.dataframe(df_filtered, use_container_width=True, hide_index=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        col_ex1, col_ex2 = st.columns(2)
        with col_ex1:
            excel_bytes = buat_excel_bytes(df_filtered, "Audit Log")
            st.download_button("📥 Ekspor Log (.xlsx)", excel_bytes, f"Audit_Log_{datetime.now().strftime('%Y%m%d')}.xlsx", use_container_width=True)
        with col_ex2:
            headers_pdf = ["Tanggal & Waktu", "Tipe", "SKU Material", "Vol", "Ref/Proyek"]
            data_pdf = [[str(r["Waktu"]), str(r["Tipe"]), str(r["Barang"]), f"{r['Jumlah']}", str(r["Pembeli / Keterangan"])] for _, r in df_filtered.iterrows()]
            pdf_bytes = buat_pdf_tabel("AUDIT LOG TRANSAKSI", headers_pdf, data_pdf, [35, 25, 60, 20, 50])
            st.download_button("📄 Cetak Laporan PDF", pdf_bytes, f"Audit_Log_{datetime.now().strftime('%Y%m%d')}.pdf", use_container_width=True)

elif menu == "🗓️ Analytics & Laporan":
    st.markdown("<h2 style='font-weight: 700; margin-bottom: 24px;'>🗓️ Analytics & Laporan Periodik</h2>", unsafe_allow_html=True)
    
    tgl_hari_ini = date.today()
    tgl_awal_bulan = tgl_hari_ini.replace(day=1)
    
    c1, c2 = st.columns(2)
    with c1:
        tgl_mulai = st.date_input("Periode Awal", tgl_awal_bulan)
    with c2:
        tgl_selesai = st.date_input("Periode Akhir", tgl_hari_ini)
        
    if tgl_mulai > tgl_selesai:
        st.error("❌ Kesalahan parameter: Tanggal awal tidak boleh melebihi tanggal akhir.")
    else:
        riwayat_filtered = filter_riwayat_berdasarkan_rentang(st.session_state.riwayat, tgl_mulai, tgl_selesai)
        
        if not riwayat_filtered:
            st.info("Tidak ada riwayat mutasi pada parameter rentang waktu yang diberikan.")
        else:
            df_periodik = pd.DataFrame(riwayat_filtered)
            masuk_count = sum(safe_int(item.get("Jumlah", 0)) for item in riwayat_filtered if item.get("Tipe") == "MASUK")
            keluar_count = sum(safe_int(item.get("Jumlah", 0)) for item in riwayat_filtered if item.get("Tipe") == "KELUAR")
            
            st.markdown("<br>", unsafe_allow_html=True)
            m1, m2, m3 = st.columns(3)
            m1.metric("📥 Total Inbound", f"{masuk_count} Unit")
            m2.metric("📤 Total Outbound", f"{keluar_count} Unit")
            m3.metric("📑 Total Frekuensi", f"{len(riwayat_filtered)} Mutasi")
            
            st.divider()
            st.subheader("Data Ekstraksi Periodik")
            st.dataframe(df_periodik, use_container_width=True, hide_index=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            info_tgl = f"Periode Audit: {tgl_mulai.strftime('%d-%m-%Y')} s/d {tgl_selesai.strftime('%d-%m-%Y')}"
            
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                excel_bytes = buat_excel_bytes(df_periodik, "Laporan Berkala")
                st.download_button("📥 Ekspor Analytics (.xlsx)", excel_bytes, f"Analytics_{tgl_mulai}_{tgl_selesai}.xlsx", use_container_width=True)
            with col_p2:
                headers_pdf = ["Tanggal & Waktu", "Tipe", "SKU Material", "Vol", "Ref/Proyek"]
                data_pdf = [[str(r["Waktu"]), str(r["Tipe"]), str(r["Barang"]), f"{r['Jumlah']}", str(r["Pembeli / Keterangan"])] for _, r in df_periodik.iterrows()]
                pdf_bytes = buat_pdf_tabel("LAPORAN ANALYTICS PERIODIK", headers_pdf, data_pdf, [35, 25, 60, 20, 50], info_tambahan=info_tgl)
                st.download_button("📄 Cetak Dokumen PDF", pdf_bytes, f"Analytics_{tgl_mulai}_{tgl_selesai}.pdf", use_container_width=True)

elif menu == "⚙️ Sistem & Keamanan":
    st.markdown("<h2 style='font-weight: 700; margin-bottom: 24px;'>⚙️ Pemeliharaan & Data Security</h2>", unsafe_allow_html=True)
    
    st.info("Fasilitas ini diperuntukkan untuk Administrator. Anda dapat melakukan backup data manual atau mereset instance basis data ke keadaan awal (Factory Reset).")
    
    excel_backup = buat_excel_backup_lengkap(st.session_state.stok, st.session_state.riwayat)
    st.download_button(
        "💾 Unduh Backup Enkripsi Lengkap (.xlsx)",
        data=excel_backup,
        file_name=f"BACKUP_DB_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )
    
    st.divider()
    
    st.markdown("<h4 style='color: var(--danger); font-weight: 600;'>🚨 Reset Data Basis Utama</h4>", unsafe_allow_html=True)
    
    # Keamanan Berlapis (2-Step Verification)
    langkah1_persetujuan = st.checkbox("Saya secara sadar memahami bahwa prosedur ini akan melakukan WIPE pada database.")
    
    teks_konfirmasi = st.text_input(
        "Konfirmasi Otorisasi: Ketik 'RESET-DATABASE'",
        placeholder="RESET-DATABASE",
        disabled=not langkah1_persetujuan
    )
    
    is_valid_reset = langkah1_persetujuan and (teks_konfirmasi.strip() == "RESET-DATABASE")
    
    if langkah1_persetujuan and teks_konfirmasi.strip() != "RESET-DATABASE" and teks_konfirmasi.strip() != "":
        st.caption("❌ Otorisasi gagal. Pastikan parameter input sesuai.")
        
    if st.button("Jalankan Factory Reset", disabled=not is_valid_reset, type="primary"):
        with st.spinner("📦 Menjalankan Auto-Dump Database..."):
            backup_bytes = buat_excel_backup_lengkap(st.session_state.stok, st.session_state.riwayat)
            waktu_str = datetime.now(ZoneInfo('Asia/Jakarta')).strftime('%Y%m%d_%H%M%S')
            nama_file_backup = f"AUTODUMP_{waktu_str}.xlsx"
            
            pesan_tg = f"🚨 **SISTEM RESET WARNING**\nTimestamps: {dapatkan_waktu_wib()}\n\nMelampirkan duplikat basis data terakhir sebelum prosedur reset."
            kirim_dokumen_telegram(pesan_tg, backup_bytes, nama_file_backup)
            
            stok_reset = STOK_DEFAULT.copy()
            riwayat_reset = []
            if save_data_atomic(stok_reset, riwayat_reset):
                st.session_state.stok = stok_reset
                st.session_state.riwayat = riwayat_reset
                st.success("✅ Factory reset berhasil dieksekusi. Arsip sistem terkirim via Telegram.")
                st.rerun()
            else:
                st.error("Prosedur gagal dijalankan.")
