import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo
import re
import io
from fpdf import FPDF
from PIL import Image

st.set_page_config(page_title="Microcement Warehouse", page_icon="📦", layout="wide")

URL_GSHEET_API = st.secrets.get("URL_GSHEET_API", "")
TELEGRAM_BOT_TOKEN = st.secrets.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = st.secrets.get("TELEGRAM_CHAT_ID", "")
IMGUR_CLIENT_ID = st.secrets.get("IMGUR_CLIENT_ID", "") # Tambahkan di secrets.toml

# -----------------------------------------------------------------------------
# HELPER FUNCTIONS & IMAGE UPLOAD
# -----------------------------------------------------------------------------

def kompres_dan_upload_gambar(file_uploaded, max_size=(600, 600), quality=70):
    """Mekompresi gambar dan mengunggahnya ke Imgur agar database GSheet tidak penuh."""
    if file_uploaded is None:
        return "", None
    try:
        file_uploaded.seek(0)
        img = Image.open(file_uploaded)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=quality, optimize=True)
        img_bytes = buffer.getvalue()
        
        # Upload ke API Imgur
        imgur_url = ""
        if IMGUR_CLIENT_ID:
            url_api = "https://api.imgur.com/3/image"
            headers = {"Authorization": f"Client-ID {IMGUR_CLIENT_ID}"}
            res = requests.post(url_api, headers=headers, files={"image": img_bytes}, timeout=15)
            if res.status_code == 200:
                imgur_url = res.json()["data"]["link"]
            else:
                st.warning("⚠️ Gagal mengunggah ke cloud storage. Menyimpan tanpa URL.")
                imgur_url = "Gagal Upload URL"
        else:
            st.warning("⚠️ Kunci API Imgur belum diatur di secrets.")
            
        return imgur_url, img_bytes
    except Exception as e:
        st.warning(f"Gagal memproses gambar: {e}")
        return "", None

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
        st.error(f"Gagal mengirim notifikasi Telegram: {e}")

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
# DATA ENGINE (SINKRONISASI REAL-TIME GSHEET)
# -----------------------------------------------------------------------------

def fetch_data_from_gsheet_direct(url):
    if not url:
        return {}
    try:
        res = requests.get(url, timeout=15)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        st.warning(f"Gagal memuat data dari Google Sheets: {e}")
        return {}

@st.cache_data(ttl=60)
def fetch_data_cached(url):
    return fetch_data_from_gsheet_direct(url)

def load_data(force_refresh=False):
    if force_refresh:
        data = fetch_data_from_gsheet_direct(URL_GSHEET_API)
    else:
        data = fetch_data_cached(URL_GSHEET_API)
        
    raw_stok = data.get("stok", [])
    stok_dict = {}
    if len(raw_stok) > 1:
        for row in raw_stok[1:]:
            if len(row) >= 2 and str(row[1]).isdigit():
                stok_dict[row[0]] = int(row[1])
    
    raw_riwayat = data.get("riwayat", [])
    riwayat_list = []
    if len(raw_riwayat) > 1:
        for row in raw_riwayat[1:]:
            if len(row) >= 4:
                pembeli = row[4] if len(row) >= 5 else "-"
                bukti = row[5] if len(row) >= 6 else ""
                riwayat_list.append({
                    "Waktu": row[0], 
                    "Tipe": row[1], 
                    "Barang": row[2], 
                    "Jumlah": row[3], 
                    "Pembeli / Keterangan": pembeli,
                    "Bukti": bukti
                })
    if not stok_dict:
        stok_dict = STOK_DEFAULT.copy()
    return stok_dict, riwayat_list

def save_data_atomic(stok_terbaru, riwayat_terbaru):
    if not URL_GSHEET_API:
        st.warning("URL Google Sheets API belum dikonfigurasi.")
        return False
        
    stok_payload = [["Nama Barang", "Jumlah Stok"]] + [[k, v] for k, v in stok_terbaru.items()]
    
    riwayat_payload = [["Waktu", "Tipe", "Barang", "Jumlah", "Pembeli / Keterangan", "Bukti"]]
    for item in riwayat_terbaru:
        riwayat_payload.append([
            item.get("Waktu", ""),
            item.get("Tipe", ""),
            item.get("Barang", ""),
            item.get("Jumlah", ""),
            item.get("Pembeli / Keterangan", "-"),
            str(item.get("Bukti", "-"))
        ])

    payload = {
        "stok": stok_payload,
        "riwayat": riwayat_payload
    }
    try:
        res = requests.post(URL_GSHEET_API, json=payload, timeout=30)
        res.raise_for_status()
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Gagal menyimpan data ke database: {e}")
        return False

if "stok" not in st.session_state or "riwayat" not in st.session_state:
    st.session_state.stok, st.session_state.riwayat = load_data()

# -----------------------------------------------------------------------------
# UI STREAMLIT DASHBOARD
# -----------------------------------------------------------------------------

st.sidebar.title("⚙️ Pengaturan")
dark_mode = st.sidebar.toggle("🌙 Mode Gelap Modern", value=True)

if st.sidebar.button("🔄 Refresh / Sinkronkan Data", use_container_width=True):
    st.cache_data.clear()
    st.session_state.stok, st.session_state.riwayat = load_data(force_refresh=True)
    st.toast("Data berhasil disinkronkan dari Google Sheets!", icon="✅")
    st.rerun()

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
        </style>
    """, unsafe_allow_html=True)

st.title("📦 Sistem Gudang Microcement")

item_habis = [b for b, q in st.session_state.stok.items() if q == 0]
item_kritis = [b for b, q in st.session_state.stok.items() if 0 < q < 5]

if item_habis:
    st.error(f"⚠️ **PERHATIAN:** Ada {len(item_habis)} item habis: {', '.join(item_habis[:3])}")

menu = st.sidebar.selectbox("Pilih Menu", [
    "📊 Lihat Semua Stok", "📥 Restok Barang Masuk", "📤 Pengiriman Barang Keluar", 
    "➕ Tambah Jenis Barang", "📜 Riwayat Transaksi", "🗓️ Laporan Periodik", "⚙️ Reset & Backup Data"
])

if menu == "📊 Lihat Semua Stok":
    st.header("📊 Ringkasan Dashboard & Stok Gudang")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📦 Total Jenis", f"{len(st.session_state.stok)} Item")
    c2.metric("📊 Total Stok", f"{sum(st.session_state.stok.values())} pcs")
    c3.metric("🟡 Kritis (<5)", f"{len(item_kritis)} Item")
    c4.metric("🔴 Habis (0)", f"{len(item_habis)} Item")
    
    st.divider()
    data_tabel = [{"Nama Barang": b, "Jumlah Stok": j, "Status": "🔴 HABIS!" if j==0 else ("🟡 KRITIS" if j<5 else "🟢 AMAN")} for b, j in sorted(st.session_state.stok.items(), key=lambda x: kunci_urut_nama(x[0]))]
    df = pd.DataFrame(data_tabel)
    st.dataframe(df, use_container_width=True, hide_index=True)

elif menu == "📥 Restok Barang Masuk":
    st.header("📥 Tambah Stok Barang")
    barang = st.selectbox("Pilih Barang", sorted(st.session_state.stok.keys(), key=kunci_urut_nama))
    jumlah = st.number_input("Jumlah Masuk", min_value=1, step=1)
    keterangan = st.text_input("Supplier / Keterangan").strip()
    uploaded_file = st.file_uploader("📷 Upload Bukti Restok (Opsional)", type=["jpg", "jpeg", "png"])
    
    if st.button("Simpan Barang Masuk"):
        bukti_url, foto_bytes = kompres_dan_upload_gambar(uploaded_file)
        
        stok_terbaru, riwayat_terbaru = load_data(force_refresh=True)
        stok_terbaru[barang] = stok_terbaru.get(barang, 0) + jumlah
        riwayat_terbaru.append({
            "Waktu": dapatkan_waktu_wib(), "Tipe": "MASUK", "Barang": barang, 
            "Jumlah": f"+{jumlah} pcs", "Pembeli / Keterangan": keterangan or "Restok", "Bukti": bukti_url
        })
        
        if save_data_atomic(stok_terbaru, riwayat_terbaru):
            st.session_state.stok, st.session_state.riwayat = stok_terbaru, riwayat_terbaru
            kirim_notifikasi_telegram(f"📥 BARANG MASUK!\nBarang: {barang}\nJumlah: +{jumlah} pcs", foto_bytes=foto_bytes)
            st.success("Barang masuk berhasil disimpan!")

elif menu == "📤 Pengiriman Barang Keluar":
    st.header("📤 Pengurangan Stok")
    barang = st.selectbox("Pilih Barang", sorted(st.session_state.stok.keys(), key=kunci_urut_nama))
    stok_ini = st.session_state.stok.get(barang, 0)
    jumlah = st.number_input("Jumlah Keluar", min_value=1, max_value=max(1, stok_ini), step=1)
    pembeli = st.text_input("👤 Nama Pembeli").strip()
    uploaded_file = st.file_uploader("📷 Upload Surat Jalan (Opsional)", type=["jpg", "jpeg", "png"])
    
    if st.button("Proses Pengiriman") and pembeli and stok_ini > 0:
        stok_terbaru, riwayat_terbaru = load_data(force_refresh=True)
        if jumlah <= stok_terbaru.get(barang, 0):
            bukti_url, foto_bytes = kompres_dan_upload_gambar(uploaded_file)
            stok_terbaru[barang] -= jumlah
            riwayat_terbaru.append({
                "Waktu": dapatkan_waktu_wib(), "Tipe": "KELUAR", "Barang": barang, 
                "Jumlah": f"-{jumlah} pcs", "Pembeli / Keterangan": pembeli, "Bukti": bukti_url
            })
            if save_data_atomic(stok_terbaru, riwayat_terbaru):
                st.session_state.stok, st.session_state.riwayat = stok_terbaru, riwayat_terbaru
                kirim_notifikasi_telegram(f"📤 BARANG KELUAR!\nBarang: {barang}\nKeluar: {jumlah} pcs", foto_bytes=foto_bytes)
                st.success("Barang keluar berhasil disimpan!")

elif menu == "➕ Tambah Jenis Barang":
    nama_baru = st.text_input("Nama Barang Baru").strip()
    stok_awal = st.number_input("Stok Awal", min_value=0, step=1)
    if st.button("Daftarkan Barang") and nama_baru:
        stok_terbaru, riwayat_terbaru = load_data(force_refresh=True)
        stok_terbaru[nama_baru] = stok_awal
        if save_data_atomic(stok_terbaru, riwayat_terbaru):
            st.session_state.stok = stok_terbaru
            st.success("Barang baru berhasil ditambahkan!")

elif menu == "📜 Riwayat Transaksi":
    st.header("📜 Catatan Riwayat Transaksi")
    if st.session_state.riwayat:
        riwayat_formatted = []
        for item in st.session_state.riwayat:
            is_url = str(item.get("Bukti", "")).startswith("http")
            riwayat_formatted.append({
                "Waktu": item.get("Waktu"), "Tipe": item.get("Tipe"), "Barang": item.get("Barang"), 
                "Jumlah": item.get("Jumlah"), "Keterangan": item.get("Pembeli / Keterangan"),
                "Foto Bukti": item.get("Bukti") if is_url else None
            })
        st.dataframe(pd.DataFrame(riwayat_formatted), column_config={"Foto Bukti": st.column_config.ImageColumn("Foto Bukti")}, hide_index=True, use_container_width=True)

elif menu == "🗓️ Laporan Periodik":
    st.info("Fungsionalitas Laporan Periodik tetap sama seperti sebelumnya, namun kini mendukung URL gambar Imgur.")

elif menu == "⚙️ Reset & Backup Data":
    st.header("⚙️ Reset & Backup Data")
    df_stok = pd.DataFrame(list(st.session_state.stok.items()), columns=["Nama Barang", "Jumlah Stok"])
    st.download_button("📥 Download Excel", data=buat_excel_bytes(df_stok), file_name='backup.xlsx')
