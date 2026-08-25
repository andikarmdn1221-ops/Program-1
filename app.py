import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime, date
from zoneinfo import ZoneInfo
import re
import io
import threading
from fpdf import FPDF
from PIL import Image

st.set_page_config(page_title="Microcement Warehouse", page_icon="📦", layout="wide", initial_sidebar_state="expanded")

# =============================================================================
# 🎨 CSS KUSTOM: TEMA SAAS MODERN & MENU NAVIGASI KEREN
# =============================================================================
st.markdown("""
<style>
    /* Latar Belakang Utama */
    .stApp {
        background-color: #F4F7FE;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    h1, h2, h3 { color: #1A202C !important; font-weight: 800 !important; }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
        border-right: 1px solid #E2E8F0 !important;
    }
    
    /* Styling Menu Radio Navigation */
    [data-testid="stSidebar"] div[role="radiogroup"] {
        gap: 8px;
    }
    
    [data-testid="stSidebar"] div[role="radiogroup"] label {
        background-color: #F8FAFC !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 12px !important;
        padding: 10px 16px !important;
        margin: 0 !important;
        transition: all 0.2s ease-in-out !important;
        cursor: pointer !important;
    }
    
    [data-testid="stSidebar"] div[role="radiogroup"] label:hover {
        background-color: #EDF2F7 !important;
        border-color: #CBD5E0 !important;
        transform: translateX(4px);
    }
    
    /* Menu Aktif (Terpilih) */
    [data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
        background-color: #1A202C !important;
        box-shadow: 0 4px 10px rgba(26, 32, 44, 0.2);
    }
    [data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) p {
        color: #FFFFFF !important;
    }
    
    /* Teks Menu Umum */
    [data-testid="stSidebar"] div[role="radiogroup"] label p {
        color: #2D3748 !important;
        font-size: 14px !important;
        font-weight: 600 !important;
    }
    
    /* Metrik & Card */
    [data-testid="stMetric"] {
        background-color: #FFFFFF !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 16px !important;
        padding: 20px !important;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.02) !important;
    }
    [data-testid="stMetricLabel"] p { color: #718096 !important; font-size: 13px !important; font-weight: 700 !important; }
    [data-testid="stMetricValue"] div { color: #1A202C !important; font-size: 32px !important; font-weight: 800 !important; }
    
    [data-testid="stForm"], [data-testid="stDataFrame"], [data-testid="stTable"] {
        background-color: #FFFFFF !important;
        border-radius: 16px !important;
        padding: 15px !important;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.02) !important;
        border: 1px solid #E2E8F0 !important;
    }

    .stButton button, .stDownloadButton button {
        background-color: #1A202C !important;
        color: #FFFFFF !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        border: none !important;
        padding: 10px 24px !important;
        width: 100%;
    }
    
    .stButton button:hover, .stDownloadButton button:hover {
        background-color: #2D3748 !important;
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(26, 32, 44, 0.2) !important;
    }
    
    .stTextInput input, .stNumberInput input, .stDateInput input {
        background-color: #F8FAFC !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 10px !important;
        color: #1A202C !important;
    }
    div[data-baseweb="select"] > div {
        background-color: #F8FAFC !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 10px !important;
        color: #1A202C !important;
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# KONFIGURASI SECRETS & FUNGSI BANTUAN
# =============================================================================
URL_GSHEET_API = st.secrets.get("URL_GSHEET_API", "")
TELEGRAM_BOT_TOKEN = st.secrets.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = st.secrets.get("TELEGRAM_CHAT_ID", "")

def safe_int(val, default=0):
    try:
        if pd.isna(val) or val is None: return default
        v_str = str(val).strip()
        return int(float(v_str)) if v_str else default
    except:
        return default

def dapatkan_waktu_wib():
    return datetime.now(ZoneInfo("Asia/Jakarta")).strftime("%d %b %Y, %H:%M WIB")

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
            requests.post(url, json={"chat_id": int(TELEGRAM_CHAT_ID), "text": pesan, "parse_mode": "Markdown"}, timeout=15)
    except:
        pass

def kirim_dokumen_telegram(pesan, file_bytes, file_name):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID: return False
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
        res = requests.post(url, data={"chat_id": int(TELEGRAM_CHAT_ID), "caption": pesan}, files={"document": (file_name, file_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}, timeout=30)
        return res.status_code == 200
    except:
        return False

def buat_excel_bytes(df, sheet_name="Data"):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    return output.getvalue()

def buat_excel_backup_lengkap(stok_dict, riwayat_list):
    output = io.BytesIO()
    df_stok = pd.DataFrame(list(stok_dict.items()), columns=["Nama Barang", "Jumlah Stok"])
    df_riwayat = pd.DataFrame(riwayat_list) if riwayat_list else pd.DataFrame(columns=["Waktu", "Tipe", "Barang", "Jumlah", "Pembeli / Keterangan"])
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_stok.to_excel(writer, index=False, sheet_name="Stok Barang")
        df_riwayat.to_excel(writer, index=False, sheet_name="Riwayat Transaksi")
    return output.getvalue()

def bersihkan_teks_pdf(teks):
    return str(teks).strip().encode('latin-1', 'replace').decode('latin-1')

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
            pdf.cell(col_widths[i], 7, bersihkan_teks_pdf(val), border=1, align="C" if i in [0, 1, 3] else "L")
        pdf.ln()
    return bytes(pdf.output())

def filter_riwayat_berdasarkan_rentang(riwayat_list, tgl_mulai, tgl_selesai):
    if not riwayat_list: return []
    dt_mulai = datetime.combine(tgl_mulai, datetime.min.time())
    dt_selesai = datetime.combine(tgl_selesai, datetime.max.time())
    hasil = []
    for item in riwayat_list:
        waktu_str = str(item.get("Waktu", ""))
        try:
            tgl = datetime.strptime(waktu_str[:16], "%d-%m-%Y %H:%M")
        except:
            try:
                tgl = datetime.fromisoformat(waktu_str.replace('Z', '+00:00')).replace(tzinfo=None)
            except:
                continue
        if dt_mulai <= tgl <= dt_selesai:
            item_formatted = item.copy()
            item_formatted["Waktu"] = tgl.strftime("%d-%m-%Y %H:%M")
            hasil.append(item_formatted)
    return hasil

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

# =============================================================================
# DATA ENGINE & SINKRONISASI GSHEET
# =============================================================================
def fetch_data_from_gsheet_direct(url):
    if not url: return None
    try:
        res = requests.get(url, timeout=15)
        res.raise_for_status()
        return res.json()
    except:
        return None

def load_data(force_refresh=False):
    if force_refresh:
        data = fetch_data_from_gsheet_direct(URL_GSHEET_API)
    else:
        @st.cache_data(ttl=300)
        def _cached(u):
            return fetch_data_from_gsheet_direct(u)
        data = _cached(URL_GSHEET_API)

    if data is None: return {}, [], False
    stok_dict = {row[0]: safe_int(row[1]) for row in data.get("stok", [])[1:] if len(row) >= 2}
    riwayat_list = [{"Waktu": r[0], "Tipe": r[1], "Barang": r[2], "Jumlah": safe_int(r[3]), "Pembeli / Keterangan": r[4] if len(r)>4 else "-"} for r in data.get("riwayat", [])[1:] if len(r)>=4]
    return stok_dict or STOK_DEFAULT.copy(), riwayat_list, True

def cek_dan_kirim_stok_kritis(stok_dict):
    habis = [b for b, q in stok_dict.items() if q == 0]
    kritis = [b for b, q in stok_dict.items() if 0 < q < 5]
    
    if habis or kritis:
        pesan_auto = f"🚨 **LAPORAN OTOMATIS: STOK KRITIS & HABIS**\n📅 {dapatkan_waktu_wib()}\n\n"
        if habis:
            pesan_auto += "🔴 *Stok Habis (0 pcs)*:\n" + "".join([f"• {b}\n" for b in habis]) + "\n"
        if kritis:
            pesan_auto += "🟡 *Stok Kritis (< 5 pcs)*:\n" + "".join([f"• {b}: {stok_dict[b]} pcs\n" for b in kritis])
        
        threading.Thread(target=kirim_notifikasi_telegram, args=(pesan_auto,)).start()

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
    s_load, r_load, is_conn = load_data(force_refresh=True)
    st.session_state.stok, st.session_state.riwayat, st.session_state.is_connected = s_load, r_load, is_conn
    cek_dan_kirim_stok_kritis(s_load)

# =============================================================================
# 📱 SIDEBAR NAVIGATION
# =============================================================================
with st.sidebar:
    st.markdown("""
        <div style='text-align: center; padding: 10px 0 20px 0;'>
            <div style='background-color: #1A202C; border-radius: 50%; width: 60px; height: 60px; margin: 0 auto; display: flex; align-items: center; justify-content: center; font-size: 28px; box-shadow: 0 4px 10px rgba(0,0,0,0.1);'>
                📦
            </div>
            <h3 style='color: #1A202C; margin-top: 15px; margin-bottom: 0; font-size: 18px;'>WMS Microcement</h3>
            <p style='color: #718096; font-size: 12px; margin-top: 0;'>Pro Dashboard v5.0</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<hr style='margin: 0 0 15px 0;'>", unsafe_allow_html=True)
    
    menu_pilihan = st.radio(
        "Navigasi",
        [
            "🏠 Dashboard Utama", 
            "📥 Form Barang Masuk", 
            "📤 Form Barang Keluar", 
            "📋 Lihat Semua Stok", 
            "📊 Riwayat Transaksi",
            "📈 Laporan Periodik",
            "➕ Kelola Master Item",
            "💾 Backup Database",
            "⚙️ Pengaturan & Reset"
        ],
        label_visibility="collapsed" 
    )
    
    active_menu = menu_pilihan.split(" ", 1)[1]
    
    st.markdown("<hr style='margin: 20px 0 15px 0;'>", unsafe_allow_html=True)
    
    st.markdown("""
        <div style='background-color: #F8FAFC; padding: 12px; border-radius: 10px; border: 1px solid #E2E8F0; text-align: center;'>
            <span style='color: #38A169; font-size: 12px; font-weight: 700;'>● TELEGRAM BOT ONLINE</span>
        </div>
    """, unsafe_allow_html=True)

# =============================================================================
# HEADER & KONTROL UTAMA
# =============================================================================
col_h1, col_h2, col_h3 = st.columns([3, 1.5, 1])
with col_h1:
    st.title(f"{active_menu}")
with col_h2:
    st.markdown(f"<div style='text-align: right; font-size:13px; color:#718096; margin-top: 15px; font-weight: 500;'>{dapatkan_waktu_wib()}</div>", unsafe_allow_html=True)
with col_h3:
    if st.button("🔄 Sync Data"):
        st.cache_data.clear()
        s_fresh, r_fresh, is_conn_fresh = load_data(force_refresh=True)
        st.session_state.stok, st.session_state.riwayat, st.session_state.is_connected = s_fresh, r_fresh, is_conn_fresh
        cek_dan_kirim_stok_kritis(s_fresh)
        st.rerun()

st.markdown("<hr style='margin-top: 10px; margin-bottom: 30px;'>", unsafe_allow_html=True)

if not st.session_state.is_connected:
    st.error("🚨 KONEKSI DATABASE TERPUTUS! Periksa koneksi internet / URL Google Sheets Anda.")

item_habis = [b for b, q in st.session_state.stok.items() if q == 0]
item_kritis = [b for b, q in st.session_state.stok.items() if 0 < q < 5]
total_jenis = len(st.session_state.stok)
total_unit = sum(st.session_state.stok.values())

# =============================================================================
# ROUTING HALAMAN
# =============================================================================
if active_menu == "Dashboard Utama":
    if item_habis or item_kritis:
        st.warning(f"⚠️ **PERHATIAN:** {len(item_habis)} item stok habis, {len(item_kritis)} item stok kritis.")
        
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Jenis Barang", f"{total_jenis} SKU")
    m2.metric("Total Volume Stok", f"{total_unit} pcs")
    m3.metric("Stok Kritis (<5)", f"{len(item_kritis)} Item")
    m4.metric("Stok Habis (0)", f"{len(item_habis)} Item")
    
    st.markdown("<br>", unsafe_allow_html=True)
    col_chart, col_kritis_table = st.columns([1, 1.2])
    
    with col_chart:
        st.markdown("### 📊 Status Rasio Stok")
        jumlah_aman = total_jenis - len(item_habis) - len(item_kritis)
        df_donut = pd.DataFrame({
            "Status": ["Stok Aman", "Stok Kritis", "Stok Habis"],
            "Jumlah": [jumlah_aman, len(item_kritis), len(item_habis)]
        })
        fig_donut = px.pie(df_donut, names="Status", values="Jumlah", hole=0.5, color="Status",
                           color_discrete_map={"Stok Aman": "#2ecc71", "Stok Kritis": "#f1c40f", "Stok Habis": "#e74c3c"})
        fig_donut.update_layout(margin=dict(t=20, b=20, l=20, r=20), paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_donut, use_container_width=True)
        
    with col_kritis_table:
        st.markdown("### 🚨 Peringatan Habis/Kritis")
        data_kritis_habis = []
        for b, q in st.session_state.stok.items():
            if q < 5:
                data_kritis_habis.append({"Nama Barang": b, "Sisa Stok": f"{q} pcs", "Status": "🔴 HABIS" if q == 0 else "🟡 KRITIS"})
        if data_kritis_habis:
            st.dataframe(pd.DataFrame(data_kritis_habis), use_container_width=True, hide_index=True)
        else:
            st.success("Tebak apa? Semua stok dalam kondisi sangat aman! 🎉")

elif active_menu == "Lihat Semua Stok":
    st.markdown("### 📋 Direktori Stok Gudang")
    keyword = st.text_input("🔍 Cari berdasarkan nama produk...", "")
    
    data_all = []
    for k, v in sorted(st.session_state.stok.items(), key=lambda x: kunci_urut_nama(x[0])):
        if keyword.lower() in k.lower():
            data_all.append({"Nama Barang": k, "Jumlah Stok": f"{v} pcs", "Status": "🔴 HABIS" if v==0 else ("🟡 KRITIS" if v<5 else "🟢 AMAN")})
            
    df_all = pd.DataFrame(data_all)
    st.dataframe(df_all, use_container_width=True, hide_index=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    c_ex1, c_ex2 = st.columns(2)
    with c_ex1:
        st.download_button("📥 Ekspor Format Excel (.xlsx)", buat_excel_bytes(df_all, "Stok"), f"Stok_{datetime.now().strftime('%Y%m%d')}.xlsx", use_container_width=True)
    with c_ex2:
        pdf_bytes = buat_pdf_tabel("LAPORAN STOK GUDANG", ["No", "Nama Barang", "Jumlah Stok", "Status"], [[str(i+1), r["Nama Barang"], r["Jumlah Stok"], r["Status"]] for i, r in enumerate(data_all)], [15, 95, 35, 45])
        st.download_button("📄 Cetak Format Laporan PDF", pdf_bytes, f"Stok_{datetime.now().strftime('%Y%m%d')}.pdf", use_container_width=True)

elif active_menu == "Kelola Master Item":
    st.markdown("### ➕ Daftarkan Produk Baru")
    with st.form("form_tambah_barang", clear_on_submit=True):
        nama_baru = st.text_input("Nama Produk Baru")
        stok_awal = st.number_input("Stok Awal Fisik (pcs)", min_value=0, value=0, step=1)
        st.markdown("<br>", unsafe_allow_html=True)
        if st.form_submit_button("Simpan Produk ke Database"):
            nama_clean = nama_baru.strip()
            if not nama_clean: st.warning("Nama barang tidak boleh kosong!")
            elif nama_clean in st.session_state.stok: st.error("Barang sudah ada di database!")
            else:
                waktu_sekarang = dapatkan_waktu_wib()
                st.session_state.stok[nama_clean] = stok_awal
                st.session_state.riwayat.insert(0, {"Waktu": waktu_sekarang, "Tipe": "BARANG BARU", "Barang": nama_clean, "Jumlah": stok_awal, "Pembeli / Keterangan": "Pendaftaran Item Baru"})
                if save_data_atomic(st.session_state.stok, st.session_state.riwayat):
                    st.success(f"Item `{nama_clean}` berhasil didaftarkan!")
                    threading.Thread(target=kirim_notifikasi_telegram, args=(f"✨ **ITEM BARU**\n📦 {nama_clean} | Stok Awal: {stok_awal} pcs",)).start()
                    st.rerun()

elif active_menu == "Form Barang Masuk":
    st.markdown("### 📥 Pencatatan Inbound (Restok)")
    with st.form("form_masuk", clear_on_submit=True):
        barang_pilihan = st.selectbox("Pilih Produk", sorted(st.session_state.stok.keys(), key=kunci_urut_nama))
        jumlah_masuk = st.number_input("Kuantitas Masuk (pcs)", min_value=1, value=1, step=1)
        
        # FITUR BARU: Pilih Tanggal Transaksi Manual
        tgl_transaksi = st.date_input("Tanggal Transaksi", value=date.today())
        
        catatan_masuk = st.text_input("Nama Supplier / Referensi Pengiriman", "-")
        foto_bukti = st.file_uploader("📷 Upload Nota / Surat Jalan (Opsional)", type=["jpg", "jpeg", "png"])
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.form_submit_button("Simpan Transaksi Masuk"):
            # Format waktu gabungan tanggal manual dengan jam real-time sekarang
            jam_sekarang = datetime.now(ZoneInfo("Asia/Jakarta")).strftime("%H:%M")
            waktu_final = f"{tgl_transaksi.strftime('%d-%m-%Y')} {jam_sekarang}"
            
            st.session_state.stok[barang_pilihan] += jumlah_masuk
            st.session_state.riwayat.insert(0, {"Waktu": waktu_final, "Tipe": "MASUK", "Barang": barang_pilihan, "Jumlah": jumlah_masuk, "Pembeli / Keterangan": catatan_masuk})
            if save_data_atomic(st.session_state.stok, st.session_state.riwayat):
                st.success(f"Berhasil merestok {barang_pilihan} (+{jumlah_masuk} pcs) untuk tanggal {tgl_transaksi.strftime('%d-%m-%Y')}!")
                pesan_tg = f"📥 **BARANG MASUK**\n📦 {barang_pilihan}\n➕ +{jumlah_masuk} pcs\n📅 Tanggal: {tgl_transaksi.strftime('%d-%m-%Y')}\n📊 Sisa: {st.session_state.stok[barang_pilihan]} pcs\n📝 {catatan_masuk}"
                threading.Thread(target=kirim_notifikasi_telegram, args=(pesan_tg, kompres_gambar(foto_bukti))).start()
                st.rerun()

elif active_menu == "Form Barang Keluar":
    st.markdown("### 📤 Pencatatan Outbound (Penjualan/Pemakaian)")
    with st.form("form_keluar", clear_on_submit=True):
        barang_pilihan = st.selectbox("Pilih Produk", sorted(st.session_state.stok.keys(), key=kunci_urut_nama))
        stok_saat_ini = st.session_state.stok.get(barang_pilihan, 0)
        
        st.markdown(f"<div style='background-color: #EBF8FF; color: #2B6CB0; padding: 10px; border-radius: 8px; margin-bottom: 20px; font-weight: 600;'>💡 Ketersediaan Fisik: {stok_saat_ini} pcs</div>", unsafe_allow_html=True)
        
        jumlah_keluar = st.number_input("Kuantitas Keluar (pcs)", min_value=1, value=1, step=1)
        
        # FITUR BARU: Pilih Tanggal Transaksi Manual
        tgl_transaksi = st.date_input("Tanggal Transaksi", value=date.today())
        
        nama_pembeli = st.text_input("Nama Pembeli / Proyek Tujuan", "")
        foto_bukti = st.file_uploader("📷 Upload Surat Jalan / Bukti Terima (Opsional)", type=["jpg", "jpeg", "png"])
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.form_submit_button("Simpan Transaksi Keluar"):
            if jumlah_keluar > stok_saat_ini: st.error(f"Gagal: Sisa stok tidak mencukupi (Hanya {stok_saat_ini} pcs).")
            elif not nama_pembeli.strip(): st.warning("Gagal: Identitas pembeli wajib diisi!")
            else:
                jam_sekarang = datetime.now(ZoneInfo("Asia/Jakarta")).strftime("%H:%M")
                waktu_final = f"{tgl_transaksi.strftime('%d-%m-%Y')} {jam_sekarang}"
                
                st.session_state.stok[barang_pilihan] -= jumlah_keluar
                st.session_state.riwayat.insert(0, {"Waktu": waktu_final, "Tipe": "KELUAR", "Barang": barang_pilihan, "Jumlah": jumlah_keluar, "Pembeli / Keterangan": nama_pembeli.strip()})
                if save_data_atomic(st.session_state.stok, st.session_state.riwayat):
                    st.success(f"Pengiriman {barang_pilihan} sebanyak {jumlah_keluar} pcs untuk tanggal {tgl_transaksi.strftime('%d-%m-%Y')} berhasil dieksekusi!")
                    pesan_tg = f"📤 **BARANG KELUAR**\n📦 {barang_pilihan}\n➖ -{jumlah_keluar} pcs\n📅 Tanggal: {tgl_transaksi.strftime('%d-%m-%Y')}\n👤 Klien: {nama_pembeli}\n📊 Sisa: {st.session_state.stok[barang_pilihan]} pcs"
                    threading.Thread(target=kirim_notifikasi_telegram, args=(pesan_tg, kompres_gambar(foto_bukti))).start()
                    st.rerun()

elif active_menu == "Riwayat Transaksi":
    st.markdown("### 📊 Log Aktivitas Gudang")
    if not st.session_state.riwayat:
        st.info("Log aktivitas masih kosong.")
    else:
        df_riwayat = pd.DataFrame(st.session_state.riwayat)
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            filter_tipe = st.selectbox("Filter Kategori Transaksi", ["SEMUA", "MASUK", "KELUAR", "BARANG BARU"])
        with col_f2:
            search_item = st.text_input("Pencarian Global (Item/Keterangan)", "")
            
        df_filtered = df_riwayat.copy()
        if filter_tipe != "SEMUA":
            df_filtered = df_filtered[df_filtered["Tipe"] == filter_tipe]
        if search_item:
            mask = df_filtered["Barang"].astype(str).str.contains(search_item, case=False, na=False) | df_filtered["Pembeli / Keterangan"].astype(str).str.contains(search_item, case=False, na=False)
            df_filtered = df_filtered[mask]
            
        st.dataframe(df_filtered, use_container_width=True, hide_index=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        c_ex1, c_ex2 = st.columns(2)
        with c_ex1:
            st.download_button("📥 Unduh Log (Excel)", buat_excel_bytes(df_filtered, "Riwayat"), f"Riwayat_{datetime.now().strftime('%Y%m%d')}.xlsx", use_container_width=True)
        with c_ex2:
            pdf_bytes = buat_pdf_tabel("RIWAYAT TRANSAKSI", ["Waktu", "Tipe", "Barang", "Jumlah", "Keterangan"], [[str(r["Waktu"]), str(r["Tipe"]), str(r["Barang"]), f"{r['Jumlah']} pcs", str(r["Pembeli / Keterangan"])] for _, r in df_filtered.iterrows()], [35, 25, 60, 20, 50])
            st.download_button("📄 Cetak Dokumen (PDF)", pdf_bytes, f"Riwayat_{datetime.now().strftime('%Y%m%d')}.pdf", use_container_width=True)

elif active_menu == "Laporan Periodik":
    st.markdown("### 📈 Penarikan Laporan Berdasarkan Waktu")
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        tgl_mulai = st.date_input("Dari Tanggal", date.today().replace(day=1))
    with col_d2:
        tgl_selesai = st.date_input("Hingga Tanggal", date.today())
        
    if tgl_mulai > tgl_selesai:
        st.error("Gagal: Tanggal awal tidak boleh lebih maju dari tanggal akhir.")
    else:
        riwayat_filtered = filter_riwayat_berdasarkan_rentang(st.session_state.riwayat, tgl_mulai, tgl_selesai)
        if not riwayat_filtered:
            st.warning("Tidak ditemukan riwayat transaksi pada jendela waktu tersebut.")
        else:
            df_periodik = pd.DataFrame(riwayat_filtered)
            m_in = sum(safe_int(x.get("Jumlah", 0)) for x in riwayat_filtered if x.get("Tipe") == "MASUK")
            m_out = sum(safe_int(x.get("Jumlah", 0)) for x in riwayat_filtered if x.get("Tipe") == "KELUAR")
            
            st.markdown("<br>", unsafe_allow_html=True)
            mc1, mc2, mc3 = st.columns(3)
            mc1.metric("Volume Masuk", f"{m_in} pcs")
            mc2.metric("Volume Keluar", f"{m_out} pcs")
            mc3.metric("Frekuensi Transaksi", f"{len(riwayat_filtered)} Kali")
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.dataframe(df_periodik, use_container_width=True, hide_index=True)
            info_tgl = f"Periode Laporan: {tgl_mulai.strftime('%d-%m-%Y')} s/d {tgl_selesai.strftime('%d-%m-%Y')}"
            
            st.markdown("<br>", unsafe_allow_html=True)
            c_ex1, c_ex2 = st.columns(2)
            with c_ex1:
                st.download_button("📥 Proses Export Excel", buat_excel_bytes(df_periodik, "Periodik"), f"Laporan_{tgl_mulai}_{tgl_selesai}.xlsx", use_container_width=True)
            with c_ex2:
                pdf_bytes = buat_pdf_tabel("LAPORAN PERIODIK", ["Waktu", "Tipe", "Barang", "Jumlah", "Keterangan"], [[str(r["Waktu"]), str(r["Tipe"]), str(r["Barang"]), f"{r['Jumlah']} pcs", str(r["Pembeli / Keterangan"])] for _, r in df_periodik.iterrows()], [35, 25, 60, 20, 50], info_tambahan=info_tgl)
                st.download_button("📄 Proses Cetak PDF", pdf_bytes, f"Laporan_{tgl_mulai}_{tgl_selesai}.pdf", use_container_width=True)

elif active_menu == "Backup Database":
    st.markdown("### 💾 Pemulihan & Backup Cepat")
    st.write("Sistem akan merangkum seluruh tabel master stok dan riwayat log menjadi satu dokumen Excel yang rapi, lalu mengunggahnya secara aman ke chat Telegram Anda.")
    
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("📤 Eksekusi Backup ke Telegram", use_container_width=True):
        with st.spinner("Menyiapkan dokumen dan membangun koneksi ke Telegram..."):
            excel_backup = buat_excel_backup_lengkap(st.session_state.stok, st.session_state.riwayat)
            nama_file = f"BACKUP_GUDANG_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            pesan_backup = f"💾 **MANUAL BACKUP DATABASE GUDANG**\n📅 {dapatkan_waktu_wib()}"
            
            berhasil = kirim_dokumen_telegram(pesan_backup, excel_backup, nama_file)
            if berhasil:
                st.success("✅ Sukses! File master backup telah diamankan ke Telegram.")
            else:
                st.error("❌ Transmisi gagal. Silakan verifikasi Token Bot & Chat ID Anda.")

elif active_menu == "Pengaturan & Reset":
    st.markdown("### ⚙️ Sistem Operasi & Factory Reset")
    st.markdown("<div style='background-color: #FFF5F5; border-left: 4px solid #E53E3E; padding: 15px; border-radius: 4px; margin-bottom: 20px;'><h4 style='color: #E53E3E; margin-top: 0;'>Peringatan Keamanan</h4><p style='color: #742A2A; margin-bottom: 0;'>Eksekusi perintah di bawah ini akan menghancurkan log riwayat dan memutar balik master data ke pengaturan pabrik.</p></div>", unsafe_allow_html=True)
    
    langkah1 = st.checkbox("SAYA MENGERTI DAN BERTANGGUNG JAWAB ATAS RISIKO INI")
    teks_konfirmasi = st.text_input("Protokol Keamanan: Ketik 'RESET-DATABASE' untuk membuka kunci:", disabled=not langkah1)
    
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🧨 Format Ulang Sistem", disabled=not (langkah1 and teks_konfirmasi.strip() == "RESET-DATABASE")):
        backup_bytes = buat_excel_backup_lengkap(st.session_state.stok, st.session_state.riwayat)
        kirim_dokumen_telegram(f"🚨 **FAILSAFE BACKUP (PRE-RESET)**\n{dapatkan_waktu_wib()}", backup_bytes, f"Failsafe_Reset_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
        
        stok_reset = STOK_DEFAULT.copy()
        riwayat_reset = []
        if save_data_atomic(stok_reset, riwayat_reset):
            st.session_state.stok = stok_reset
            st.session_state.riwayat = riwayat_reset
            st.success("Sistem operasi berhasil diremajakan!")
            st.rerun()
