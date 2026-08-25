import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo
import re
import io
import base64
from fpdf import FPDF
from PIL import Image

st.set_page_config(page_title="Microcement Warehouse", page_icon="📦", layout="wide")

URL_GSHEET_API = st.secrets.get("URL_GSHEET_API", "")
TELEGRAM_BOT_TOKEN = st.secrets.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = st.secrets.get("TELEGRAM_CHAT_ID", "")

# -----------------------------------------------------------------------------
# HELPER FUNCTIONS
# -----------------------------------------------------------------------------

def kompres_gambar(file_uploaded, max_size=(600, 600), quality=70):
    """Mekompresi gambar untuk dikirim via Telegram saja."""
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
# DATA ENGINE
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
                riwayat_list.append({
                    "Waktu": row[0], 
                    "Tipe": row[1], 
                    "Barang": row[2], 
                    "Jumlah": row[3], 
                    "Pembeli / Keterangan": pembeli
                })
    if not stok_dict:
        stok_dict = STOK_DEFAULT.copy()
    return stok_dict, riwayat_list

def save_data_atomic(stok_terbaru, riwayat_terbaru):
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

if "stok" not in st.session_state or "riwayat" not in st.session_state:
    st.session_state.stok, st.session_state.riwayat = load_data()

# -----------------------------------------------------------------------------
# UI STREAMLIT
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
        div[data-testid="stFileUploader"] { background-color: #1E293B !important; border: 1px dashed #475569 !important; border-radius: 10px !important; padding: 8px !important; }
        div[data-testid="stFileUploaderDropzone"] { background-color: #1E293B !important; }
        div[data-testid="stFileUploaderDropzone"] * { color: #F8FAFC !important; }
        div[data-testid="stFileUploader"] button { background-color: #334155 !important; color: #FFFFFF !important; border: 1px solid #475569 !important; }
        </style>
    """, unsafe_allow_html=True)
st.title("📦 Sistem Gudang Microcement")

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
        
        st.dataframe(
            df,
            column_config={
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
            },
            hide_index=True,
            use_container_width=True
        )
        
        c_dl1, c_dl2 = st.columns(2)
        excel_stok_bytes = buat_excel_bytes(df, sheet_name="Stok Barang")
        c_dl1.download_button("📊 Download Tabel Stok (Excel .xlsx)", data=excel_stok_bytes, file_name=f"Laporan_Stok_Gudang_{datetime.now().strftime('%d%m%Y')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
        
        data_pdf_stok = [[item["Nama Barang"], str(item["Jumlah Stok"]), item["Status"]] for item in data_tabel]
        pdf_bytes_stok = buat_pdf_tabel("Laporan Stok Gudang Mikrosemen", ["Nama Barang", "Jumlah Stok (pcs)", "Status"], data_pdf_stok, [90, 45, 45])
        c_dl2.download_button("📄 Download Tabel Stok (PDF)", data=pdf_bytes_stok, file_name=f"Laporan_Stok_Gudang_{datetime.now().strftime('%d%m%Y')}.pdf", mime="application/pdf", use_container_width=True)
        
        st.divider()
        st.subheader("📈 Visualisasi Grafik Stok")
        tipe_grafik = st.radio("Pilih Model Tampilan Grafik:", ["📊 Batang Tegak (Vertical)", "📉 Batang Mendatar (Horizontal)", "📈 Grafik Garis (Line Chart)"], horizontal=True)
        theme_plotly = "plotly_dark" if dark_mode else "plotly"
        
        if tipe_grafik == "📊 Batang Tegak (Vertical)":
            df_sorted = df.sort_values(by="Jumlah Stok", ascending=False)
            fig_bar = px.bar(df_sorted, x="Nama Barang", y="Jumlah Stok", color="Status", text="Jumlah Stok", color_discrete_map={"🟢 AMAN": "#2ecc71", "🟡 KRITIS": "#f1c40f", "🔴 HABIS!": "#e74c3c"}, template=theme_plotly)
            fig_bar.update_traces(textposition='outside')
            fig_bar.update_layout(xaxis_tickangle=-45, uniformtext_minsize=8, uniformtext_mode='hide')
        elif tipe_grafik == "📉 Batang Mendatar (Horizontal)":
            df_sorted = df.sort_values(by="Jumlah Stok", ascending=True)
            fig_bar = px.bar(df_sorted, x="Jumlah Stok", y="Nama Barang", color="Status", orientation='h', text="Jumlah Stok", color_discrete_map={"🟢 AMAN": "#2ecc71", "🟡 KRITIS": "#f1c40f", "🔴 HABIS!": "#e74c3c"}, template=theme_plotly)
            fig_bar.update_traces(textposition='outside')
            fig_bar.update_layout(height=650)
        else:
            df_sorted = df.sort_values(by="Nama Barang", ascending=True)
            fig_bar = px.line(df_sorted, x="Nama Barang", y="Jumlah Stok", markers=True, template=theme_plotly)
            fig_bar.update_traces(line_color="#38BDF8", marker_size=8)
            fig_bar.update_layout(xaxis_tickangle=-45)
            
        st.plotly_chart(fig_bar, use_container_width=True)

elif menu == "📥 Restok Barang Masuk":
    st.header("📥 Tambah Stok Barang")
    barang = st.selectbox("Pilih Barang", sorted(st.session_state.stok.keys(), key=kunci_urut_nama))
    jumlah = st.number_input("Jumlah Masuk", min_value=1, step=1)
    keterangan = st.text_input("Supplier / Keterangan (Opsional)").strip()
    uploaded_file = st.file_uploader("📷 Upload Bukti Restok / Surat Jalan (Opsional)", type=["jpg", "jpeg", "png"])
    
    if st.button("Simpan Barang Masuk"):
        with st.spinner('Menyimpan data...'):
            foto_bytes = kompres_gambar(uploaded_file)
            stok_terbaru, riwayat_terbaru = load_data(force_refresh=True)
            
            stok_terbaru[barang] = stok_terbaru.get(barang, 0) + jumlah
            riwayat_terbaru.append({
                "Waktu": dapatkan_waktu_wib(), 
                "Tipe": "MASUK", 
                "Barang": barang, 
                "Jumlah": f"+{jumlah} pcs", 
                "Pembeli / Keterangan": keterangan or "Restok"
            })
            
            if save_data_atomic(stok_terbaru, riwayat_terbaru):
                st.session_state.stok, st.session_state.riwayat = load_data(force_refresh=True)
                
                pesan_tg = f"📥 BARANG MASUK!\nBarang: {barang}\nJumlah: +{jumlah} pcs\nKeterangan: {keterangan or '-'}"
                kirim_notifikasi_telegram(pesan_tg, foto_bytes=foto_bytes)
                st.balloons()
                st.success(f"Berhasil menambahkan {jumlah} pcs ke {barang}!")
            else:
                st.error("Gagal memperbarui stok ke database. Silakan coba lagi.")

elif menu == "📤 Pengiriman Barang Keluar":
    st.header("📤 Pengurangan Stok (Barang Keluar)")
    barang = st.selectbox("Pilih Barang", sorted(st.session_state.stok.keys(), key=kunci_urut_nama))
    stok_ini = st.session_state.stok.get(barang, 0)
    st.caption(f"Sisa stok: **{stok_ini} pcs**")
    
    jumlah = st.number_input("Jumlah Keluar", min_value=1, max_value=max(1, stok_ini), step=1)
    pembeli = st.text_input("👤 Nama Pembeli / Klien").strip()
    uploaded_file = st.file_uploader("📷 Upload Surat Jalan / Bukti Terima (Opsional)", type=["jpg", "jpeg", "png"])
    
    if st.button("Proses Pengiriman"):
        if not pembeli:
            st.warning("⚠️ Mohon isi nama pembeli!")
        elif stok_ini == 0:
            st.error("❌ Barang habis!")
        else:
            with st.spinner('Memproses pengiriman dan menyimpan data...'):
                stok_terbaru, riwayat_terbaru = load_data(force_refresh=True)
                stok_saat_ini = stok_terbaru.get(barang, 0)
                
                if jumlah > stok_saat_ini:
                    st.error(f"❌ Stok terbaru di server ({stok_saat_ini} pcs) tidak mencukupi!")
                else:
                    foto_bytes = kompres_gambar(uploaded_file)
                    stok_terbaru[barang] = stok_saat_ini - jumlah
                    sisa = stok_terbaru[barang]
                    
                    riwayat_terbaru.append({
                        "Waktu": dapatkan_waktu_wib(), 
                        "Tipe": "KELUAR", 
                        "Barang": barang, 
                        "Jumlah": f"-{jumlah} pcs", 
                        "Pembeli / Keterangan": pembeli
                    })
                    
                    if save_data_atomic(stok_terbaru, riwayat_terbaru):
                        st.session_state.stok, st.session_state.riwayat = load_data(force_refresh=True)
                        
                        pesan_tg = f"📤 BARANG KELUAR!\nBarang: {barang}\nKeluar: {jumlah} pcs\nKlien: {pembeli}\nSisa Stok: {sisa} pcs"
                        if sisa == 0:
                            pesan_tg = "⚠️ PERHATIAN: STOK HABIS!\n" + pesan_tg
                        elif sisa < 5:
                            pesan_tg = "⚠️ PERHATIAN: STOK KRITIS!\n" + pesan_tg
                            
                        kirim_notifikasi_telegram(pesan_tg, foto_bytes=foto_bytes)
                        st.balloons()
                        st.success(f"Berhasil mengeluarkan {jumlah} pcs untuk {pembeli}!")
                    else:
                        st.error("Gagal memproses transaksi. Silakan coba lagi.")

elif menu == "➕ Tambah Jenis Barang":
    st.header("➕ Tambah Jenis Barang Baru")
    nama_baru = st.text_input("Nama Barang Baru").strip()
    stok_awal = st.number_input("Stok Awal", min_value=0, step=1)
    
    if st.button("Daftarkan Barang"):
        if not nama_baru:
            st.warning("⚠️ Nama barang tidak boleh kosong!")
        else:
            stok_terbaru, riwayat_terbaru = load_data(force_refresh=True)
            if nama_baru in stok_terbaru:
                st.warning("⚠️ Barang sudah ada di dalam daftar database!")
            else:
                stok_terbaru[nama_baru] = stok_awal
                riwayat_terbaru.append({
                    "Waktu": dapatkan_waktu_wib(), 
                    "Tipe": "TAMBAH BARU", 
                    "Barang": nama_baru, 
                    "Jumlah": f"{stok_awal} pcs", 
                    "Pembeli / Keterangan": "Baru"
                })
                
                if save_data_atomic(stok_terbaru, riwayat_terbaru):
                    st.session_state.stok = stok_terbaru
                    st.session_state.riwayat = riwayat_terbaru
                    st.balloons()
                    st.success(f"Barang {nama_baru} berhasil ditambahkan!")
                else:
                    st.error("Gagal menambahkan barang baru.")

elif menu == "📜 Riwayat Transaksi":
    st.header("📜 Catatan Riwayat Transaksi")
    if st.session_state.riwayat:
        riwayat_formatted = []
        for item in st.session_state.riwayat:
            dt = parse_waktu(item.get("Waktu", ""))
            waktu_str = dt.strftime("%d-%m-%Y %H:%M") if dt else item.get("Waktu", "")
            riwayat_formatted.append({
                "Waktu": waktu_str,
                "Tipe": item.get("Tipe", ""),
                "Barang": item.get("Barang", ""),
                "Jumlah": item.get("Jumlah", ""),
                "Pembeli / Keterangan": item.get("Pembeli / Keterangan", "-")
            })
        df_riwayat = pd.DataFrame(riwayat_formatted)
        st.dataframe(df_riwayat, hide_index=True, use_container_width=True)
    else:
        st.info("Belum ada riwayat.")

elif menu == "🗓️ Laporan Periodik (Custom Tanggal)":
    st.header("🗓️ Rekapitulasi Laporan Transaksi Periodik")
    
    col_preset, _ = st.columns([2, 2])
    with col_preset:
        preset = st.selectbox("⚡ Pilih Pintasan Waktu:", ["Rentang Tanggal Custom", "7 Hari Terakhir", "30 Hari Terakhir", "Bulan Ini"])
    
    hari_ini = date.today()
    if preset == "7 Hari Terakhir":
        tgl_mulai_default, tgl_selesai_default = hari_ini - timedelta(days=7), hari_ini
    elif preset == "30 Hari Terakhir":
        tgl_mulai_default, tgl_selesai_default = hari_ini - timedelta(days=30), hari_ini
    elif preset == "Bulan Ini":
        tgl_mulai_default, tgl_selesai_default = hari_ini.replace(day=1), hari_ini
    else:
        tgl_mulai_default, tgl_selesai_default = hari_ini - timedelta(days=7), hari_ini

    c_start, c_end = st.columns(2)
    tgl_mulai = c_start.date_input("📅 Tanggal Mulai:", value=tgl_mulai_default)
    tgl_selesai = c_end.date_input("📅 Tanggal Selesai:", value=tgl_selesai_default)
    
    if tgl_mulai > tgl_selesai:
        st.error("⚠️ Tanggal Mulai tidak boleh melebihi Tanggal Selesai!")
    else:
        riwayat_filtered = filter_riwayat_berdasarkan_rentang(st.session_state.riwayat, tgl_mulai, tgl_selesai)
        
        m1, m2, m3 = st.columns(3)
        m1.metric("📋 Total Transaksi", f"{len(riwayat_filtered)} Data")
        m2.metric("📥 Barang Masuk", f"{sum(1 for x in riwayat_filtered if x.get('Tipe') == 'MASUK')} Kali")
        m3.metric("📤 Barang Keluar", f"{sum(1 for x in riwayat_filtered if x.get('Tipe') == 'KELUAR')} Kali")
        
        st.divider()
        
        if riwayat_filtered:
            laporan_tabel = [[x["Waktu"], x["Tipe"], x["Barang"], x["Jumlah"], x["Pembeli / Keterangan"]] for x in riwayat_filtered]
            df_laporan = pd.DataFrame(laporan_tabel, columns=["Waktu", "Tipe", "Barang", "Jumlah", "Pembeli / Keterangan"])
            
            st.dataframe(df_laporan, hide_index=True, use_container_width=True)
            
            c_rep1, c_rep2 = st.columns(2)
            excel_laporan_bytes = buat_excel_bytes(df_laporan, sheet_name="Laporan Transaksi")
            c_rep1.download_button("📊 Download Laporan Excel (.xlsx)", data=excel_laporan_bytes, file_name=f"Laporan_Gudang_{tgl_mulai.strftime('%Y%m%d')}_{tgl_selesai.strftime('%Y%m%d')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
            
            pdf_bytes = buat_pdf_tabel("Laporan Transaksi Gudang", ["Waktu", "Tipe", "Barang", "Jumlah", "Keterangan"], laporan_tabel, [35, 25, 45, 25, 60], info_tambahan=f"Periode: {tgl_mulai.strftime('%d-%m-%Y')} s/d {tgl_selesai.strftime('%d-%m-%Y')}")
            c_rep2.download_button("📄 Download Laporan PDF", data=pdf_bytes, file_name=f"Laporan_Gudang_{tgl_mulai.strftime('%Y%m%d')}_{tgl_selesai.strftime('%Y%m%d')}.pdf", mime="application/pdf", use_container_width=True)
        else:
            st.info(f"Belum ada transaksi pada rentang tanggal {tgl_mulai.strftime('%d-%m-%Y')} s/d {tgl_selesai.strftime('%d-%m-%Y')}.")

elif menu == "⚙️ Reset & Backup Data":
    st.header("⚙️ Reset & Backup Data")
    st.subheader("💾 Backup Data Gudang")
    
    col1, col2, col3 = st.columns(3)
    df_stok_backup = pd.DataFrame(list(st.session_state.stok.items()), columns=["Nama Barang", "Jumlah Stok"])
    
    col1.download_button("📥 Download Stok (CSV)", data=df_stok_backup.to_csv(index=False).encode('utf-8'), file_name='backup_stok_mikrosemen.csv', mime='text/csv', use_container_width=True)
    col2.download_button("📊 Download Stok (Excel)", data=buat_excel_bytes(df_stok_backup, sheet_name="Backup Stok"), file_name='backup_stok_mikrosemen.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', use_container_width=True)
    
    pdf_bytes = buat_pdf_tabel("Laporan Stok Gudang", ["Nama Barang", "Jumlah Stok (pcs)"], [[k, str(v)] for k, v in st.session_state.stok.items()], [130, 50])
    col3.download_button("📄 Download Stok (PDF)", data=pdf_bytes, file_name="Laporan_Stok_Mikrosemen.pdf", mime="application/pdf", use_container_width=True)
    
    st.divider()
    st.subheader("🚨 Reset Data")
    st.warning("Tombol di bawah ini akan menghapus riwayat dan mengembalikan stok ke kondisi awal.")
    if st.button("🚨 Reset Semua Data"):
        stok_reset = STOK_DEFAULT.copy()
        riwayat_reset = []
        if save_data_atomic(stok_reset, riwayat_reset):
            st.session_state.stok = stok_reset
            st.session_state.riwayat = riwayat_reset
            st.success("Data berhasil di-reset!")
            st.rerun()
