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

st.set_page_config(page_title="Microcement Warehouse", page_icon="📦", layout="wide")

URL_GSHEET_API = st.secrets.get("URL_GSHEET_API", "")
TELEGRAM_BOT_TOKEN = st.secrets.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = st.secrets.get("TELEGRAM_CHAT_ID", "")

# -----------------------------------------------------------------------------
# CUSTOM MODERN SAAS CSS STYLING (MENYERupai TAMPILAN REFERENSI)
# -----------------------------------------------------------------------------
st.markdown("""
    <style>
    /* Global Styling & Background */
    .stApp {
        background-color: #F8FAFC !important;
        color: #1E293B !important;
        font-family: 'Inter', sans-serif;
    }
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
        border-right: 1px solid #E2E8F0 !important;
    }
    section[data-testid="stSidebar"] * {
        color: #334155 !important;
    }
    
    /* Modern Cards / Containers */
    div[data-testid="stMetric"] {
        background: #FFFFFF !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 12px !important;
        padding: 16px !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05) !important;
    }
    div[data-testid="stMetricLabel"] p {
        color: #64748B !important;
        font-size: 12px !important;
        font-weight: 600 !important;
        text-transform: uppercase;
    }
    div[data-testid="stMetricValue"] div {
        color: #0F172A !important;
        font-size: 24px !important;
        font-weight: 700 !important;
    }
    
    /* Dataframes & Tables */
    div[data-testid="stDataFrame"] {
        background: #FFFFFF !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 12px !important;
        padding: 8px !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02) !important;
    }
    
    /* Buttons Styling */
    .stButton button {
        background: #0284C7 !important;
        color: #FFFFFF !important;
        font-weight: 600 !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 8px 16px !important;
        transition: all 0.2s ease-in-out;
    }
    .stButton button:hover {
        background: #0369A1 !important;
        box-shadow: 0 4px 12px rgba(2, 132, 199, 0.2) !important;
    }
    
    /* Inputs & Selectboxes */
    .stTextInput input, .stNumberInput input, .stDateInput input, div[data-baseweb="select"] > div {
        background-color: #FFFFFF !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 8px !important;
        color: #1E293B !important;
    }
    </style>
""", unsafe_allow_html=True)

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
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID: return[cite: 2]
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

# -----------------------------------------------------------------------------
# DATA ENGINE[cite: 2]
# -----------------------------------------------------------------------------
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

# -----------------------------------------------------------------------------
# SIDEBAR NAVIGATION (MODERN STYLE)[cite: 2]
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### ⚡ Knowvio / WMS")
    st.caption("Microcement Enterprise Dashboard")
    st.markdown("---")
    
    m_utama = st.radio("DASHBOARD & UTAMA", ["🏠 Dashboard", "📋 Lihat Semua Stok", "➕ Kelola Master Item"])
    st.markdown("---")
    m_transaksi = st.radio("MANAJEMEN TRANSAKSI", ["📥 Barang Masuk", "📤 Barang Keluar"])
    st.markdown("---")
    m_laporan = st.radio("LAPORAN & ANALITIK", ["📊 Riwayat Transaksi", "📈 Laporan Periodik"])
    st.markdown("---")
    m_sistem = st.radio("SISTEM & PENGATURAN", ["💾 Backup Data", "⚙️ Pengaturan & Reset", "ℹ️ Tentang Aplikasi"])
    
    st.markdown("---")
    st.success("🟢 Telegram Bot: Connected")

if "prev_utama" not in st.session_state: st.session_state.prev_utama = m_utama
if "prev_transaksi" not in st.session_state: st.session_state.prev_transaksi = m_transaksi
if "prev_laporan" not in st.session_state: st.session_state.prev_laporan = m_laporan
if "prev_sistem" not in st.session_state: st.session_state.prev_sistem = m_sistem
if "active_tab" not in st.session_state: st.session_state.active_tab = "🏠 Dashboard"

if m_utama != st.session_state.prev_utama:
    st.session_state.active_tab = m_utama
    st.session_state.prev_utama = m_utama
elif m_transaksi != st.session_state.prev_transaksi:
    st.session_state.active_tab = m_transaksi
    st.session_state.prev_transaksi = m_transaksi
elif m_laporan != st.session_state.prev_laporan:
    st.session_state.active_tab = m_laporan
    st.session_state.prev_laporan = m_laporan
elif m_sistem != st.session_state.prev_sistem:
    st.session_state.active_tab = m_sistem
    st.session_state.prev_sistem = m_sistem

active_menu_raw = st.session_state.active_tab
active_menu = active_menu_raw.split(" ", 1)[1] if " " in active_menu_raw else active_menu_raw

# -----------------------------------------------------------------------------
# HEADER & KONTROL UTAMA[cite: 2]
# -----------------------------------------------------------------------------
col_h1, col_h2, col_h3 = st.columns([3, 1.5, 1])
with col_h1:
    st.title(f"📦 {active_menu}")
with col_h2:
    st.markdown(f"<div style='text-align: right; font-size:13px; color:#64748B; padding-top:10px;'>🕒 {dapatkan_waktu_wib()}</div>", unsafe_allow_html=True)
with col_h3:
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        s_fresh, r_fresh, is_conn_fresh = load_data(force_refresh=True)
        st.session_state.stok, st.session_state.riwayat, st.session_state.is_connected = s_fresh, r_fresh, is_conn_fresh
        cek_dan_kirim_stok_kritis(s_fresh)
        st.rerun()

st.markdown("---")

if not st.session_state.is_connected:
    st.error("🚨 KONEKSI DATABASE TERPUTUS! Periksa koneksi internet / URL Google Sheets Anda.")

item_habis = [b for b, q in st.session_state.stok.items() if q == 0]
item_kritis = [b for b, q in st.session_state.stok.items() if 0 < q < 5]
total_jenis = len(st.session_state.stok)
total_unit = sum(st.session_state.stok.values())

# -----------------------------------------------------------------------------
# ROUTING HALAMAN[cite: 2]
# -----------------------------------------------------------------------------
if active_menu == "Dashboard":
    if item_habis or item_kritis:
        st.warning(f"⚠️ **PERHATIAN SISTEM:** Ada {len(item_habis)} item habis dan {len(item_kritis)} item dalam status kritis.")
        
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Jenis Barang", f"{total_jenis} Item")
    m2.metric("Total Keseluruhan Stok", f"{total_unit} pcs")
    m3.metric("Stok Kritis (<5)", f"{len(item_kritis)} Item")
    m4.metric("Stok Habis (0)", f"{len(item_habis)} Item")
    
    st.markdown("---")
    col_chart, col_kritis_table = st.columns([1, 1])
    
    with col_chart:
        st.subheader("📊 Komposisi Level Stok")
        jumlah_aman = total_jenis - len(item_habis) - len(item_kritis)
        df_donut = pd.DataFrame({
            "Status": ["Stok Aman", "Stok Kritis", "Stok Habis"],
            "Jumlah": [jumlah_aman, len(item_kritis), len(item_habis)]
        })
        fig_donut = px.pie(df_donut, names="Status", values="Jumlah", hole=0.6, color="Status",
                           color_discrete_map={"Stok Aman": "#22c55e", "Stok Kritis": "#eab308", "Stok Habis": "#ef4444"})
        fig_donut.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(t=10, b=10, l=10, r=10))
        st.plotly_chart(fig_donut, use_container_width=True)
        
    with col_kritis_table:
        st.subheader("🚨 Peringatan Stok Kritis & Habis")
        data_kritis_habis = []
        for b, q in st.session_state.stok.items():
            if q < 5:
                data_kritis_habis.append({"Nama Barang": b, "Sisa Stok": f"{q} pcs", "Status": "HABIS" if q == 0 else "KRITIS"})
        if data_kritis_habis:
            st.dataframe(pd.DataFrame(data_kritis_habis), use_container_width=True, hide_index=True)
        else:
            st.success("🎉 Luar biasa! Semua item dalam kondisi stok aman.")

    st.markdown("---")
    st.subheader("📋 Pencarian & Ikhtisar Stok")
    keyword = st.text_input("🔍 Cari nama produk mikrosemen...", "")
    
    data_tabel = []
    for barang in sorted(st.session_state.stok.keys(), key=kunci_urut_nama):
        jumlah = st.session_state.stok[barang]
        status = "HABIS" if jumlah == 0 else ("KRITIS" if jumlah < 5 else "AMAN")
        if keyword.lower() in barang.lower():
            data_tabel.append({"Nama Barang": barang, "Jumlah Stok": f"{jumlah} pcs", "Status": status})
            
    if data_tabel:
        st.dataframe(pd.DataFrame(data_tabel), use_container_width=True, hide_index=True)

elif active_menu == "Lihat Semua Stok":
    st.subheader("Manajemen Daftar Keseluruhan Stok Gudang")
    data_all = [{"Nama Barang": k, "Jumlah Stok": f"{v} pcs", "Status": "HABIS" if v==0 else ("KRITIS" if v<5 else "AMAN")} for k,v in sorted(st.session_state.stok.items(), key=lambda x: kunci_urut_nama(x[0]))]
    df_all = pd.DataFrame(data_all)
    st.dataframe(df_all, use_container_width=True, hide_index=True)
    
    c_ex1, c_ex2 = st.columns(2)
    with c_ex1:
        st.download_button("📥 Ekspor ke Excel", buat_excel_bytes(df_all, "Stok"), f"Stok_{datetime.now().strftime('%Y%m%d')}.xlsx", use_container_width=True)
    with c_ex2:
        pdf_bytes = buat_pdf_tabel("LAPORAN STOK GUDANG", ["No", "Nama Barang", "Jumlah Stok", "Status"], [[str(i+1), r["Nama Barang"], r["Jumlah Stok"], r["Status"]] for i, r in enumerate(data_all)], [15, 95, 35, 45])
        st.download_button("📄 Cetak Laporan PDF", pdf_bytes, f"Stok_{datetime.now().strftime('%Y%m%d')}.pdf", use_container_width=True)

elif active_menu == "Kelola Master Item":
    st.subheader("Pendaftaran Jenis Barang Baru")
    with st.form("form_tambah_barang", clear_on_submit=True):
        nama_baru = st.text_input("Nama Produk Baru")
        stok_awal = st.number_input("Stok Awal (pcs)", min_value=0, value=0, step=1)
        if st.form_submit_button("➕ Daftarkan Item Baru"):
            nama_clean = nama_baru.strip()
            if not nama_clean: st.warning("Nama barang tidak boleh kosong!")
            elif nama_clean in st.session_state.stok: st.error("Barang sudah terdaftar di database!")
            else:
                waktu_sekarang = dapatkan_waktu_wib()
                st.session_state.stok[nama_clean] = stok_awal
                st.session_state.riwayat.insert(0, {"Waktu": waktu_sekarang, "Tipe": "BARANG BARU", "Barang": nama_clean, "Jumlah": stok_awal, "Pembeli / Keterangan": "Item baru"})
                if save_data_atomic(st.session_state.stok, st.session_state.riwayat):
                    st.success(f"Item `{nama_clean}` berhasil didaftarkan!")
                    threading.Thread(target=kirim_notifikasi_telegram, args=(f"✨ **ITEM BARU DITAMBAHKAN**\n📦 {nama_clean} | Stok Awal: {stok_awal} pcs",)).start()
                    st.rerun()

elif active_menu == "Barang Masuk":
    st.subheader("Pencatatan Transaksi Masuk (Inbound)")
    with st.form("form_masuk", clear_on_submit=True):
        barang_pilihan = st.selectbox("Pilih Produk", sorted(st.session_state.stok.keys(), key=kunci_urut_nama))
        jumlah_masuk = st.number_input("Jumlah Masuk (pcs)", min_value=1, value=1, step=1)
        foto_bukti = st.file_uploader("Upload Dokumen / Nota / Surat Jalan (Opsional)", type=["jpg", "jpeg", "png"])
        catatan_masuk = st.text_input("Supplier / Catatan Keterangan", "-")
        
        if st.form_submit_button("📥 Simpan & Kirim Notifikasi"):
            waktu_sekarang = dapatkan_waktu_wib()
            st.session_state.stok[barang_pilihan] += jumlah_masuk
            st.session_state.riwayat.insert(0, {"Waktu": waktu_sekarang, "Tipe": "MASUK", "Barang": barang_pilihan, "Jumlah": jumlah_masuk, "Pembeli / Keterangan": catatan_masuk})
            if save_data_atomic(st.session_state.stok, st.session_state.riwayat):
                st.success(f"Berhasil menambah stok {barang_pilihan} (+{jumlah_masuk} pcs)!")
                pesan_tg = f"📥 **BARANG MASUK**\n📦 {barang_pilihan}\n➕ +{jumlah_masuk} pcs\n📊 Sisa Stok: {st.session_state.stok[barang_pilihan]} pcs\n📝 {catatan_masuk}"
                threading.Thread(target=kirim_notifikasi_telegram, args=(pesan_tg, kompres_gambar(foto_bukti))).start()
                st.rerun()

elif active_menu == "Barang Keluar":
    st.subheader("Pencatatan Transaksi Pengiriman (Outbound)")
    with st.form("form_keluar", clear_on_submit=True):
        barang_pilihan = st.selectbox("Pilih Produk", sorted(st.session_state.stok.keys(), key=kunci_urut_nama))
        stok_saat_ini = st.session_state.stok.get(barang_pilihan, 0)
        st.info(f"Sisa Stok `{barang_pilihan}` di Sistem: **{stok_saat_ini} pcs**")
        
        jumlah_keluar = st.number_input("Jumlah Keluar (pcs)", min_value=1, value=1, step=1)
        nama_pembeli = st.text_input("Nama Klien / Pembeli / Proyek", "")
        foto_bukti = st.file_uploader("Upload Surat Jalan / Bukti Serah Terima (Opsional)", type=["jpg", "jpeg", "png"])
        
        if st.form_submit_button("📤 Proses & Kirim Pengiriman"):
            if jumlah_keluar > stok_saat_ini: st.error(f"Stok tidak mencukupi! Sisa stok hanya {stok_saat_ini} pcs.")
            elif not nama_pembeli.strip(): st.warning("Mohon isi Nama Klien / Pembeli / Proyek!")
            else:
                waktu_sekarang = dapatkan_waktu_wib()
                st.session_state.stok[barang_pilihan] -= jumlah_keluar
                st.session_state.riwayat.insert(0, {"Waktu": waktu_sekarang, "Tipe": "KELUAR", "Barang": barang_pilihan, "Jumlah": jumlah_keluar, "Pembeli / Keterangan": nama_pembeli.strip()})
                if save_data_atomic(st.session_state.stok, st.session_state.riwayat):
                    st.success(f"Pengiriman {barang_pilihan} sebanyak {jumlah_keluar} pcs berhasil dicatat!")
                    pesan_tg = f"📤 **BARANG KELUAR**\n📦 {barang_pilihan}\n➖ -{jumlah_keluar} pcs\n👤 Klien: {nama_pembeli}\n📊 Sisa Stok: {st.session_state.stok[barang_pilihan]} pcs"
                    threading.Thread(target=kirim_notifikasi_telegram, args=(pesan_tg, kompres_gambar(foto_bukti))).start()
                    st.rerun()

elif active_menu == "Riwayat Transaksi":
    st.subheader("Log Riwayat Aktivitas Gudang")
    if not st.session_state.riwayat:
        st.info("Belum ada riwayat transaksi tercatat.")
    else:
        df_riwayat = pd.DataFrame(st.session_state.riwayat)
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            filter_tipe = st.selectbox("Filter Berdasarkan Tipe", ["SEMUA", "MASUK", "KELUAR", "BARANG BARU"])
        with col_f2:
            search_item = st.text_input("Pencarian Cepat (Barang / Keterangan)", "")
            
        df_filtered = df_riwayat.copy()
        if filter_tipe != "SEMUA":
            df_filtered = df_filtered[df_filtered["Tipe"] == filter_tipe]
        if search_item:
            mask = df_filtered["Barang"].astype(str).str.contains(search_item, case=False, na=False) | df_filtered["Pembeli / Keterangan"].astype(str).str.contains(search_item, case=False, na=False)
            df_filtered = df_filtered[mask]
            
        st.dataframe(df_filtered, use_container_width=True, hide_index=True)
        
        c_ex1, c_ex2 = st.columns(2)
        with c_ex1:
            st.download_button("📥 Ekspor Riwayat ke Excel", buat_excel_bytes(df_filtered, "Riwayat"), f"Riwayat_{datetime.now().strftime('%Y%m%d')}.xlsx", use_container_width=True)
        with c_ex2:
            pdf_bytes = buat_pdf_tabel("RIWAYAT TRANSAKSI", ["Waktu", "Tipe", "Barang", "Jumlah", "Keterangan"], [[str(r["Waktu"]), str(r["Tipe"]), str(r["Barang"]), f"{r['Jumlah']} pcs", str(r["Pembeli / Keterangan"])] for _, r in df_filtered.iterrows()], [35, 25, 60, 20, 50])
            st.download_button("📄 Cetak Riwayat PDF", pdf_bytes, f"Riwayat_{datetime.now().strftime('%Y%m%d')}.pdf", use_container_width=True)

elif active_menu == "Laporan Periodik":
    st.subheader("Rekapitulasi Berdasarkan Rentang Tanggal")
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        tgl_mulai = st.date_input("Tanggal Mulai", date.today().replace(day=1))
    with col_d2:
        tgl_selesai = st.date_input("Tanggal Selesai", date.today())
        
    if tgl_mulai > tgl_selesai:
        st.error("Tanggal mulai tidak boleh melebihi tanggal selesai!")
    else:
        riwayat_filtered = filter_riwayat_berdasarkan_rentang(st.session_state.riwayat, tgl_mulai, tgl_selesai)
        if not riwayat_filtered:
            st.warning("Tidak ditemukan transaksi pada rentang tanggal tersebut.")
        else:
            df_periodik = pd.DataFrame(riwayat_filtered)
            m_in = sum(safe_int(x.get("Jumlah", 0)) for x in riwayat_filtered if x.get("Tipe") == "MASUK")
            m_out = sum(safe_int(x.get("Jumlah", 0)) for x in riwayat_filtered if x.get("Tipe") == "KELUAR")
            
            mc1, mc2, mc3 = st.columns(3)
            mc1.metric("Total Unit Masuk", f"{m_in} pcs")
            mc2.metric("Total Unit Keluar", f"{m_out} pcs")
            mc3.metric("Total Frekuensi Transaksi", f"{len(riwayat_filtered)}")
            
            st.dataframe(df_periodik, use_container_width=True, hide_index=True)
            info_tgl = f"Periode: {tgl_mulai.strftime('%d-%m-%Y')} s/d {tgl_selesai.strftime('%d-%m-%Y')}"
            
            c_ex1, c_ex2 = st.columns(2)
            with c_ex1:
                st.download_button("📥 Ekspor Laporan Excel", buat_excel_bytes(df_periodik, "Periodik"), f"Laporan_{tgl_mulai}_{tgl_selesai}.xlsx", use_container_width=True)
            with c_ex2:
                pdf_bytes = buat_pdf_tabel("LAPORAN PERIODIK", ["Waktu", "Tipe", "Barang", "Jumlah", "Keterangan"], [[str(r["Waktu"]), str(r["Tipe"]), str(r["Barang"]), f"{r['Jumlah']} pcs", str(r["Pembeli / Keterangan"])] for _, r in df_periodik.iterrows()], [35, 25, 60, 20, 50], info_tambahan=info_tgl)
                st.download_button("📄 Cetak Laporan PDF", pdf_bytes, f"Laporan_{tgl_mulai}_{tgl_selesai}.pdf", use_container_width=True)

elif active_menu == "Backup Data":
    st.subheader("Pusat Pencadangan Database")
    st.write("Unduh atau kirimkan cadangan file excel lengkap yang mencakup ringkasan stok dan seluruh histori riwayat transaksi.")
    
    if st.button("📤 Kirim Arsip Backup ke Telegram", use_container_width=True):
        with st.spinner("Mengemas dan mengirim arsip database ke Telegram..."):
            excel_backup = buat_excel_backup_lengkap(st.session_state.stok, st.session_state.riwayat)
            nama_file = f"BACKUP_GUDANG_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            pesan_backup = f"💾 **ARSIP MANUAL BACKUP DATABASE**\n📅 {dapatkan_waktu_wib()}"
            
            berhasil = kirim_dokumen_telegram(pesan_backup, excel_backup, nama_file)
            if berhasil:
                st.success("✅ Arsip database berhasil dikirim langsung ke Telegram Anda!")
            else:
                st.error("❌ Gagal mengirim dokumen ke Telegram. Periksa konfigurasi Bot Token / Chat ID.")

elif active_menu == "Pengaturan & Reset":
    st.subheader("Pengaturan Lanjutan & Reset Sistem")
    st.warning("⚠️ **Zona Berbahaya:** Tindakan ini akan mengosongkan seluruh riwayat dan memulihkan stok ke konfigurasi default.")
    
    langkah1 = st.checkbox("Saya memahami risiko kehilangan data transaksional")
    teks_konfirmasi = st.text_input("Ketik `RESET-DATABASE` untuk mengonfirmasi tindakan:", disabled=not langkah1)
    
    if st.button("🚨 Eksekusi Reset Sistem", disabled=not (langkah1 and teks_konfirmasi.strip() == "RESET-DATABASE")):
        backup_bytes = buat_excel_backup_lengkap(st.session_state.stok, st.session_state.riwayat)
        kirim_dokumen_telegram(f"🚨 **OTOMATIS BACKUP SEBELUM RESET**\n{dapatkan_waktu_wib()}", backup_bytes, f"Backup_Reset_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
        
        stok_reset = STOK_DEFAULT.copy()
        riwayat_reset = []
        if save_data_atomic(stok_reset, riwayat_reset):
            st.session_state.stok = stok_reset
            st.session_state.riwayat = riwayat_reset
            st.success("Sistem berhasil di-reset ke setelan awal pabrik!")
            st.rerun()

elif active_menu == "Tentang Aplikasi":
    st.subheader("Tentang Knowvio WMS Microcement")
    st.write("Aplikasi Manajemen Gudang Enterprise berbasis Streamlit yang terintegrasi penuh dengan Google Sheets API dan sistem otomatisasi Bot Telegram[cite: 2].")
    st.info("Versi: 4.0 Modern SaaS Dashboard Edition")
