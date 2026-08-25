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

st.set_page_config(page_title="Microcement Warehouse", page_icon="📦", layout="wide")

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
# HELPER FUNCTIONS
# -----------------------------------------------------------------------------

def safe_int(val, default=0):
    """Konversi nilai ke integer secara aman tanpa memicu ValueError."""
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
    """Mekompresi gambar untuk dikirim via Telegram."""
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
    """Mengirim file dokumen (Excel backup) ke Telegram."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
        payload = {"chat_id": int(TELEGRAM_CHAT_ID), "caption": pesan}
        files = {"document": (file_name, file_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        requests.post(url, data=payload, files=files, timeout=30)
    except Exception as e:
        print(f"Gagal mengirim dokumen backup ke Telegram: {e}")

def cek_dan_kirim_stok_kritis_manual():
    """Memeriksa stok kritis/habis dan mengirimkannya ke Telegram secara instan."""
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
    """Membuat 1 file Excel berisi 2 sheet: Stok dan Riwayat Transaksi."""
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
        st.error(f"⚠️ Gagal memuat data dari Google Sheets: {e}")
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
                    "Waktu": row[0], 
                    "Tipe": row[1], 
                    "Barang": row[2], 
                    "Jumlah": safe_int(row[3]), 
                    "Pembeli / Keterangan": pembeli
                })
                
    if not stok_dict and len(raw_stok) <= 1:
        stok_dict = STOK_DEFAULT.copy()
        
    return stok_dict, riwayat_list, True

def save_data_atomic(stok_terbaru, riwayat_terbaru):
    if not st.session_state.get("is_connected", False):
        st.error("❌ Transaksi dibatalkan karena koneksi ke database terputus.")
        return False

    if not URL_GSHEET_API:
        st.warning("URL Google Sheets API belum dikonfigurasi.")
        return False
        
    stok_payload = [["Nama Barang", "Jumlah Stok"]] + [[k, v] for k, v in stok_terbaru.items()]
    
    riwayat_payload = [["Waktu", "Tipe", "Barang", "Jumlah", "Pembeli / Keterangan"]]
    for item in riwayat_terbaru:
        riwayat_payload.append([
            item.get("Waktu", ""),
            item.get("Tipe", ""),
            item.get("Barang", ""),
            item.get("Jumlah", ""),
            item.get("Pembeli / Keterangan", "-")
        ])

    payload = {
        "stok": stok_payload,
        "riwayat": riwayat_payload
    }
    try:
        res = requests.post(URL_GSHEET_API, json=payload, timeout=45)
        res.raise_for_status()
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Gagal menyimpan data ke database: {e}")
        return False

if "is_connected" not in st.session_state:
    stok_loaded, riwayat_loaded, is_conn = load_data()
    st.session_state.stok = stok_loaded
    st.session_state.riwayat = riwayat_loaded
    st.session_state.is_connected = is_conn

# -----------------------------------------------------------------------------
# UI STREAMLIT
# -----------------------------------------------------------------------------

st.sidebar.title("⚙️ Pengaturan")
dark_mode = st.sidebar.toggle("🌙 Mode Gelap Modern", value=False)

if st.sidebar.button("🔄 Refresh / Sinkronkan Data", use_container_width=True):
    st.cache_data.clear()
    stok_ref, riwayat_ref, is_conn = load_data(force_refresh=True)
    st.session_state.stok = stok_ref
    st.session_state.riwayat = riwayat_ref
    st.session_state.is_connected = is_conn
    if is_conn:
        st.toast("Data berhasil disinkronkan dari Google Sheets!", icon="✅")
    else:
        st.error("Gagal menyinkronkan data dari Google Sheets.")
    st.rerun()

st.sidebar.divider()
st.sidebar.subheader("📡 Laporan Otomatis Telegram")
if st.sidebar.button("🚨 Cek & Kirim Daftar Stok Kritis", use_container_width=True):
    status_kirim = cek_dan_kirim_stok_kritis_manual()
    if status_kirim == "AMAN":
        st.sidebar.success("✅ Semua stok aman / tidak ada yang kritis!")
    else:
        st.sidebar.warning("📤 Daftar stok kritis berhasil dikirim ke Telegram!")

st.sidebar.divider()

if dark_mode:
    st.markdown("""
        <style>
        .stApp { background-color: #0F172A !important; color: #F8FAFC !important; }
        .stSidebar { background-color: #1E293B !important; border-right: 1px solid #334155 !important; }
        div[data-testid="stMetric"] { background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%) !important; border: 1px solid #334155 !important; border-radius: 14px !important; padding: 18px !important; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25) !important; }
        div[data-testid="stMetricLabel"] p { color: #94A3B8 !important; font-size: 13px !important; font-weight: 600 !important; text-transform: uppercase; letter-spacing: 0.5px; }
        div[data-testid="stMetricValue"] div { color: #38BDF8 !important; font-size: 30px !important; font-weight: 800 !important; }
        .stTextInput input, .stNumberInput input, .stDateInput input { background-color: #1E293B !important; color: #FFFFFF !important; border: 1px solid #475569 !important; border-radius: 8px !important; }
        div[data-baseweb="select"] > div { background-color: #1E293B !important; color: #FFFFFF !important; border-color: #475569 !important; border-radius: 8px !important; }
        div[data-baseweb="select"] span { color: #FFFFFF !important; }
        div[data-testid="stDataFrame"], div[data-testid="stTable"] { background-color: #1E293B !important; border: 1px solid #334155 !important; border-radius: 12px !important; overflow: hidden !important; }
        div[data-testid="stDataFrame"] * { color: #F8FAFC !important; }
        .stButton button, .stDownloadButton button { background: linear-gradient(135deg, #0284C7 0%, #0369A1 100%) !important; color: #FFFFFF !important; font-weight: 600 !important; border: none !important; border-radius: 8px !important; padding: 10px 20px !important; transition: all 0.2s ease-in-out !important; }
        .stButton button:hover, .stDownloadButton button:hover { transform: translateY(-1px); box-shadow: 0 4px 14px rgba(2, 132, 199, 0.45) !important; }
        label, .stMarkdown p, h1, h2, h3, h4, h5, h6, span { color: #F8FAFC !important; }
        div[data-testid="stFileUploader"] { background-color: #1E293B !important; border: 1px dashed #475569 !important; border-radius: 10px !important; padding: 8px !important; }
        div[data-testid="stFileUploaderDropzone"] { background-color: #1E293B !important; }
        div[data-testid="stFileUploaderDropzone"] * { color: #F8FAFC !important; }
        div[data-testid="stFileUploader"] button { background-color: #334155 !important; color: #FFFFFF !important; border: 1px solid #475569 !important; }
        </style>
    """, unsafe_allow_html=True)

st.title("📦 Sistem Gudang Microcement")

if not st.session_state.is_connected:
    st.error("🚨 **KONEKSI DATABASE TERPUTUS / GAGAL DIMUAT!**\n\nSistem mengunci fungsi penyimpanan transaksi untuk mencegah data asli di Google Sheets tertimpa data kosong. Silakan periksa koneksi internet Anda lalu klik tombol **🔄 Refresh / Sinkronkan Data** di menu sebelah kiri.")

item_habis = [b for b, q in st.session_state.stok.items() if q == 0]
item_kritis = [b for b, q in st.session_state.stok.items() if 0 < q < 5]

if item_habis:
    st.error(f"⚠️ **PERHATIAN:** Ada {len(item_habis)} item habis: {', '.join(item_habis[:3])}")

menu = st.sidebar.selectbox("Pilih Menu", [
    "📊 Lihat Semua Stok", 
    "📥 Restok Barang Masuk", 
    "📤 Pengiriman Barang Keluar", 
    "➕ Tambah Jenis Barang", 
    "📜 Riwayat Transaksi",
    "🗓️ Laporan Periodik (Custom Tanggal)",
    "⚙️ Reset & Backup Data"
])

if menu == "📊 Lihat Semua Stok":
    st.header("📊 Ringkasan Dashboard & Stok Gudang")
    total_jenis = len(st.session_state.stok)
    total_unit = sum(st.session_state.stok.values())
    
    if IS_MOBILE:
        with st.container():
            st.metric("📦 Total Jenis", f"{total_jenis} Item")
            st.metric("📊 Total Stok", f"{total_unit} pcs")
            st.metric("🟡 Kritis (<5)", f"{len(item_kritis)} Item")
            st.metric("🔴 Habis (0)", f"{len(item_habis)} Item")
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📦 Total Jenis", f"{total_jenis} Item")
        c2.metric("📊 Total Stok", f"{total_unit} pcs")
        c3.metric("🟡 Kritis (<5)", f"{len(item_kritis)} Item")
        c4.metric("🔴 Habis (0)", f"{len(item_habis)} Item")
    
    st.divider()
    keyword = st.text_input("🔍 Cari Nama Barang...", "")
    
    data_tabel = []
    max_stok_val = max(st.session_state.stok.values()) if st.session_state.stok else 30
    
    for barang in sorted(st.session_state.stok.keys(), key=kunci_urut_nama):
        jumlah = st.session_state.stok[barang]
        if keyword.lower() in barang.lower():
            status = "🔴 HABIS!" if jumlah == 0 else ("🟡 KRITIS" if jumlah < 5 else "🟢 AMAN")
            data_tabel.append({
                "Nama Barang": barang,
                "Jumlah Stok": jumlah,
                "Progress Visual": jumlah,
                "Status": status
            })
    
    if data_tabel:
        df = pd.DataFrame(data_tabel)
        
        config_tabel = {
            "Nama Barang": st.column_config.TextColumn("Nama Barang", help="Jenis produk mikrosemen"),
            "Jumlah Stok": st.column_config.NumberColumn("Sisa Stok", format="%d pcs"),
            "Progress Visual": st.column_config.ProgressColumn(
                "Indikator Level Stok",
                help="Visualisasi sisa stok relatif terhadap item terbanyak",
                format="%d pcs",
                min_value=0,
                max_value=max(max_stok_val, 20),
            ),
            "Status": st.column_config.TextColumn("Status Stok"),
        }

        if IS_MOBILE:
            with st.expander("📊 Lihat Tabel Stok Lengkap", expanded=False):
                st.dataframe(df, column_config=config_tabel, hide_index=True, use_container_width=True)
        else:
            st.dataframe(df, column_config=config_tabel, hide_index=True, use_container_width=True)
            
        col_exp1, col_exp2 = st.columns(2)
        with col_exp1:
            excel_bytes = buat_excel_bytes(df[["Nama Barang", "Jumlah Stok", "Status"]], "Stok Gudang")
            st.download_button("📥 Ekspor Rekap Stok (Excel)", excel_bytes, f"Stok_Gudang_{datetime.now().strftime('%Y%m%d')}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
        with col_exp2:
            headers_pdf = ["No", "Nama Barang", "Sisa Stok", "Status"]
            data_pdf = [[str(i+1), r["Nama Barang"], f"{r['Jumlah Stok']} pcs", r["Status"]] for i, r in enumerate(data_tabel)]
            pdf_bytes = buat_pdf_tabel("LAPORAN STOK GUDANG MICROCEMENT", headers_pdf, data_pdf, [15, 95, 35, 45])
            st.download_button("📄 Cetak Rekap Stok (PDF)", pdf_bytes, f"Stok_Gudang_{datetime.now().strftime('%Y%m%d')}.pdf", "application/pdf", use_container_width=True)

elif menu == "📥 Restok Barang Masuk":
    st.header("📥 Form Restok Barang Masuk")
    with st.form("form_masuk", clear_on_submit=True):
        barang_pilihan = st.selectbox("Pilih Barang", sorted(st.session_state.stok.keys(), key=kunci_urut_nama))
        jumlah_masuk = st.number_input("Jumlah Masuk (pcs)", min_value=1, value=1, step=1)
        foto_bukti = st.file_uploader("Upload Bukti / Foto Nota (Opsional)", type=["jpg", "jpeg", "png"])
        catatan_masuk = st.text_input("Catatan / Supplier (Opsional)", "-")
        
        submitted = st.form_submit_button("📥 Simpan Restok")
        
        if submitted:
            waktu_sekarang = dapatkan_waktu_wib()
            st.session_state.stok[barang_pilihan] += jumlah_masuk
            st.session_state.riwayat.insert(0, {
                "Waktu": waktu_sekarang,
                "Tipe": "MASUK",
                "Barang": barang_pilihan,
                "Jumlah": jumlah_masuk,
                "Pembeli / Keterangan": catatan_masuk
            })
            
            if save_data_atomic(st.session_state.stok, st.session_state.riwayat):
                st.success(f"✅ Stok {barang_pilihan} berhasil bertambah +{jumlah_masuk} pcs!")
                pesan_tg = f"📥 **RESTOK BARANG MASUK**\n\n📦 Barang: {barang_pilihan}\n➕ Jumlah: +{jumlah_masuk} pcs\n📊 Sisa Stok Sekarang: {st.session_state.stok[barang_pilihan]} pcs\n📝 Catatan: {catatan_masuk}\n⏰ Waktu: {waktu_sekarang}"
                foto_kompresed = kompres_gambar(foto_bukti)
                threading.Thread(target=kirim_notifikasi_telegram, args=(pesan_tg, foto_kompresed)).start()
                st.rerun()

elif menu == "📤 Pengiriman Barang Keluar":
    st.header("📤 Form Pengiriman Barang Keluar")
    with st.form("form_keluar", clear_on_submit=True):
        barang_pilihan = st.selectbox("Pilih Barang", sorted(st.session_state.stok.keys(), key=kunci_urut_nama))
        stok_saat_ini = st.session_state.stok.get(barang_pilihan, 0)
        st.info(f"Sisa Stok `{barang_pilihan}` saat ini: **{stok_saat_ini} pcs**")
        
        jumlah_keluar = st.number_input("Jumlah Keluar (pcs)", min_value=1, value=1, step=1)
        nama_pembeli = st.text_input("Nama Pembeli / Proyek", "")
        foto_bukti = st.file_uploader("Upload Surat Jalan / Bukti (Opsional)", type=["jpg", "jpeg", "png"])
        
        submitted = st.form_submit_button("📤 Simpan Pengiriman")
        
        if submitted:
            if jumlah_keluar > stok_saat_ini:
                st.error(f"❌ Stok tidak cukup! Stok hanya ada {stok_saat_ini} pcs.")
            elif not nama_pembeli.strip():
                st.warning("⚠️ Mohon isi Nama Pembeli / Proyek terlebih dahulu.")
            else:
                waktu_sekarang = dapatkan_waktu_wib()
                st.session_state.stok[barang_pilihan] -= jumlah_keluar
                st.session_state.riwayat.insert(0, {
                    "Waktu": waktu_sekarang,
                    "Tipe": "KELUAR",
                    "Barang": barang_pilihan,
                    "Jumlah": jumlah_keluar,
                    "Pembeli / Keterangan": nama_pembeli.strip()
                })
                
                if save_data_atomic(st.session_state.stok, st.session_state.riwayat):
                    st.success(f"✅ Pengiriman {barang_pilihan} sebanyak {jumlah_keluar} pcs berhasil dicatat!")
                    pesan_tg = f"📤 **PENGIRIMAN BARANG KELUAR**\n\n📦 Barang: {barang_pilihan}\n➖ Jumlah: -{jumlah_keluar} pcs\n👤 Pembeli: {nama_pembeli.strip()}\n📊 Sisa Stok Sekarang: {st.session_state.stok[barang_pilihan]} pcs\n⏰ Waktu: {waktu_sekarang}"
                    foto_kompresed = kompres_gambar(foto_bukti)
                    threading.Thread(target=kirim_notifikasi_telegram, args=(pesan_tg, foto_kompresed)).start()
                    st.rerun()

elif menu == "➕ Tambah Jenis Barang":
    st.header("➕ Tambah Jenis Barang Baru")
    with st.form("form_tambah_barang", clear_on_submit=True):
        nama_baru = st.text_input("Nama Barang Baru")
        stok_awal = st.number_input("Stok Awal (pcs)", min_value=0, value=0, step=1)
        
        submitted = st.form_submit_button("➕ Tambah Barang")
        if submitted:
            nama_clean = nama_baru.strip()
            if not nama_clean:
                st.warning("⚠️ Nama barang tidak boleh kosong!")
            elif nama_clean in st.session_state.stok:
                st.error("❌ Nama barang sudah ada di dalam database!")
            else:
                waktu_sekarang = dapatkan_waktu_wib()
                st.session_state.stok[nama_clean] = stok_awal
                st.session_state.riwayat.insert(0, {
                    "Waktu": waktu_sekarang,
                    "Tipe": "BARANG BARU",
                    "Barang": nama_clean,
                    "Jumlah": stok_awal,
                    "Pembeli / Keterangan": "Penambahan item baru ke database"
                })
                if save_data_atomic(st.session_state.stok, st.session_state.riwayat):
                    st.success(f"✅ Jenis barang `{nama_clean}` berhasil ditambahkan!")
                    pesan_tg = f"✨ **JENIS BARANG BARU**\n\n📦 Barang: {nama_clean}\n📊 Stok Awal: {stok_awal} pcs\n⏰ Waktu: {waktu_sekarang}"
                    threading.Thread(target=kirim_notifikasi_telegram, args=(pesan_tg,)).start()
                    st.rerun()

elif menu == "📜 Riwayat Transaksi":
    st.header("📜 Riwayat Transaksi")
    if not st.session_state.riwayat:
        st.info("Belum ada riwayat transaksi yang tercatat.")
    else:
        df_riwayat = pd.DataFrame(st.session_state.riwayat)
        
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            filter_tipe = st.selectbox("Filter Jenis Transaksi", ["SEMUA", "MASUK", "KELUAR", "BARANG BARU"])
        with col_f2:
            search_item = st.text_input("🔍 Cari Barang / Pembeli...", "")
            
        df_filtered = df_riwayat.copy()
        if filter_tipe != "SEMUA":
            df_filtered = df_filtered[df_filtered["Tipe"] == filter_tipe]
        if search_item:
            mask = df_filtered["Barang"].astype(str).str.contains(search_item, case=False, na=False) | df_filtered["Pembeli / Keterangan"].astype(str).str.contains(search_item, case=False, na=False)
            df_filtered = df_filtered[mask]
            
        st.dataframe(df_filtered, use_container_width=True, hide_index=True)
        
        col_ex1, col_ex2 = st.columns(2)
        with col_ex1:
            excel_bytes = buat_excel_bytes(df_filtered, "Riwayat Transaksi")
            st.download_button("📥 Ekspor Riwayat (Excel)", excel_bytes, f"Riwayat_Transaksi_{datetime.now().strftime('%Y%m%d')}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
        with col_ex2:
            headers_pdf = ["Waktu", "Tipe", "Nama Barang", "Jumlah", "Keterangan"]
            data_pdf = [[str(r["Waktu"]), str(r["Tipe"]), str(r["Barang"]), f"{r['Jumlah']} pcs", str(r["Pembeli / Keterangan"])] for _, r in df_filtered.iterrows()]
            pdf_bytes = buat_pdf_tabel("RIWAYAT TRANSAKSI GUDANG", headers_pdf, data_pdf, [35, 25, 60, 20, 50])
            st.download_button("📄 Cetak Riwayat (PDF)", pdf_bytes, f"Riwayat_Transaksi_{datetime.now().strftime('%Y%m%d')}.pdf", "application/pdf", use_container_width=True)

elif menu == "🗓️ Laporan Periodik (Custom Tanggal)":
    st.header("🗓️ Laporan Periodik Rekap Transaksi")
    
    tgl_hari_ini = date.today()
    tgl_awal_bulan = tgl_hari_ini.replace(day=1)
    
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        tgl_mulai = st.date_input("Tanggal Mulai", tgl_awal_bulan)
    with col_d2:
        tgl_selesai = st.date_input("Tanggal Selesai", tgl_hari_ini)
        
    if tgl_mulai > tgl_selesai:
        st.error("❌ Tanggal mulai tidak boleh melebihi tanggal selesai!")
    else:
        riwayat_filtered = filter_riwayat_berdasarkan_rentang(st.session_state.riwayat, tgl_mulai, tgl_selesai)
        
        if not riwayat_filtered:
            st.warning("Tidak ada transaksi pada rentang tanggal yang dipilih.")
        else:
            df_periodik = pd.DataFrame(riwayat_filtered)
            
            masuk_count = sum(safe_int(item.get("Jumlah", 0)) for item in riwayat_filtered if item.get("Tipe") == "MASUK")
            keluar_count = sum(safe_int(item.get("Jumlah", 0)) for item in riwayat_filtered if item.get("Tipe") == "KELUAR")
            
            c_m1, c_m2, c_m3 = st.columns(3)
            c_m1.metric("📥 Total Barang Masuk", f"{masuk_count} pcs")
            c_m2.metric("📤 Total Barang Keluar", f"{keluar_count} pcs")
            c_m3.metric("📑 Total Transaksi", f"{len(riwayat_filtered)} Transaksi")
            
            st.divider()
            st.subheader("Detail Transaksi Periodik")
            st.dataframe(df_periodik, use_container_width=True, hide_index=True)
            
            info_tgl = f"Periode: {tgl_mulai.strftime('%d-%m-%Y')} s/d {tgl_selesai.strftime('%d-%m-%Y')}"
            
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                excel_bytes = buat_excel_bytes(df_periodik, "Laporan Periodik")
                st.download_button("📥 Ekspor Laporan Periodik (Excel)", excel_bytes, f"Laporan_Periodik_{tgl_mulai}_{tgl_selesai}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
            with col_p2:
                headers_pdf = ["Waktu", "Tipe", "Nama Barang", "Jumlah", "Keterangan"]
                data_pdf = [[str(r["Waktu"]), str(r["Tipe"]), str(r["Barang"]), f"{r['Jumlah']} pcs", str(r["Pembeli / Keterangan"])] for _, r in df_periodik.iterrows()]
                pdf_bytes = buat_pdf_tabel("LAPORAN TRANSAKSI PERIODIK GUDANG", headers_pdf, data_pdf, [35, 25, 60, 20, 50], info_tambahan=info_tgl)
                st.download_button("📄 Cetak Laporan Periodik (PDF)", pdf_bytes, f"Laporan_Periodik_{tgl_mulai}_{tgl_selesai}.pdf", "application/pdf", use_container_width=True)

elif menu == "⚙️ Reset & Backup Data":
    st.header("⚙️ Reset & Manual Backup Data Gudang")
    st.warning("⚠️ **Tindakan Berbahaya:** Fitur reset ini akan mengosongkan seluruh riwayat dan mengembalikan stok ke kondisi awal default.")
    
    excel_backup = buat_excel_backup_lengkap(st.session_state.stok, st.session_state.riwayat)
    st.download_button(
        "💾 Unduh Manual Backup Lengkap (Excel)",
        data=excel_backup,
        file_name=f"MANUAL_BACKUP_GUDANG_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )
    
    st.divider()
    
    # --- LAPISAN KEAMANAN BERLAPIS (2-STEP VERIFICATION) ---
    st.subheader("🔒 Konfirmasi Keamanan Berlapis")
    
    # Langkah 1: Centang Persetujuan
    langkah1_persetujuan = st.checkbox("Langkah 1: Saya memahami risiko ini dan ingin mereset seluruh database")
    
    # Langkah 2: Ketik Kata Kunci Konfirmasi
    teks_konfirmasi = st.text_input(
        "Langkah 2: Ketik kata kunci `RESET-DATABASE` di bawah untuk mengonfirmasi:",
        placeholder="RESET-DATABASE",
        disabled=not langkah1_persetujuan
    )
    
    # Validasi Keamanan 2 Langkah
    is_valid_reset = langkah1_persetujuan and (teks_konfirmasi.strip() == "RESET-DATABASE")
    
    if langkah1_persetujuan and teks_konfirmasi.strip() != "RESET-DATABASE" and teks_konfirmasi.strip() != "":
        st.caption("❌ Kata kunci konfirmasi tidak cocok. Ketik tepat: `RESET-DATABASE`")
        
    if st.button("🚨 Ya, Reset Semua Data Sekarang", disabled=not is_valid_reset):
        with st.spinner("📦 Membuat auto-backup dan memproses reset database..."):
            backup_bytes = buat_excel_backup_lengkap(st.session_state.stok, st.session_state.riwayat)
            waktu_str = datetime.now(ZoneInfo('Asia/Jakarta')).strftime('%Y%m%d_%H%M%S')
            nama_file_backup = f"AUTO_BACKUP_GUDANG_{waktu_str}.xlsx"
            
            pesan_tg = f"🚨 **AUTOBACKUP SEBELUM RESET**\nWaktu: {dapatkan_waktu_wib()}\n\nFile terlampir adalah backup data stok & riwayat transaksi sebelum sistem di-reset."
            kirim_dokumen_telegram(pesan_tg, backup_bytes, nama_file_backup)
            
            stok_reset = STOK_DEFAULT.copy()
            riwayat_reset = []
            if save_data_atomic(stok_reset, riwayat_reset):
                st.session_state.stok = stok_reset
                st.session_state.riwayat = riwayat_reset
                st.success("✅ File backup otomatis telah dikirim ke Telegram & data gudang berhasil di-reset!")
                st.rerun()
            else:
                st.error("Gagal melakukan reset data. Silakan coba lagi nanti.")
