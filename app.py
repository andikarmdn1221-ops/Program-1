import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo
import streamlit.components.v1 as components
import re
from fpdf import FPDF

st.set_page_config(page_title="Microcement Warehouse", page_icon="📦", layout="wide")

# Mengambil kredensial dari st.secrets
URL_GSHEET_API = st.secrets.get("URL_GSHEET_API", "")
TELEGRAM_BOT_TOKEN = st.secrets.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = st.secrets.get("TELEGRAM_CHAT_ID", "")

def kirim_notifikasi_telegram(pesan):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": int(TELEGRAM_CHAT_ID), "text": pesan}
    try:
        requests.post(url, json=payload, timeout=15)
    except Exception as e:
        st.error(f"Gagal mengirim notifikasi Telegram: {e}")

def dapatkan_waktu_wib():
    return datetime.now(ZoneInfo("Asia/Jakarta")).strftime("%d-%m-%Y %H:%M")

def parse_waktu(waktu_str):
    try:
        return datetime.strptime(waktu_str, "%d-%m-%Y %H:%M")
    except Exception:
        return None

@st.cache_data(ttl=60)
def fetch_data_from_gsheet(url):
    if not url:
        return {}
    try:
        res = requests.get(url, timeout=15)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        st.warning(f"Gagal memuat data dari Google Sheets: {e}")
        return {}

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

def panggil_confetti():
    components.html("""
    <script src="https://cdn.jsdelivr.net/npm/canvas-confetti@1.6.0/dist/confetti.browser.min.js"></script>
    <script>
        confetti({ particleCount: 150, origin: { y: 0.7 } });
    </script>
    """, height=0)

def bersihkan_teks_pdf(teks):
    teks_str = str(teks)
    if len(teks_str) > 35:
        teks_str = teks_str[:32] + "..."
    return re.sub(r'[^\x00-\x7F]+', '', teks_str).strip()

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
    
    pdf.set_font("Helvetica", "", 9)
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
            hasil.append(item)
    return hasil

def load_data():
    data = fetch_data_from_gsheet(URL_GSHEET_API)
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
                riwayat_list.append({"Waktu": row[0], "Tipe": row[1], "Barang": row[2], "Jumlah": row[3], "Pembeli / Keterangan": pembeli})
    if not stok_dict:
        stok_dict = STOK_DEFAULT.copy()
    return stok_dict, riwayat_list

def save_data():
    if not URL_GSHEET_API:
        st.warning("URL Google Sheets API belum dikonfigurasi.")
        return False
    payload = {
        "stok": [[k, v] for k, v in st.session_state.stok.items()],
        "riwayat": st.session_state.riwayat
    }
    try:
        res = requests.post(URL_GSHEET_API, json=payload, timeout=30)
        res.raise_for_status()
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Gagal menyimpan data ke database: {e}")
        return False

# Inisialisasi Session State
if "stok" not in st.session_state or "riwayat" not in st.session_state:
    st.session_state.stok, st.session_state.riwayat = load_data()

# Pengaturan Sidebar
st.sidebar.title("⚙️ Pengaturan")
dark_mode = st.sidebar.toggle("🌙 Mode Gelap", value=True)

if st.sidebar.button("🔄 Refresh / Sinkronkan Data", use_container_width=True):
    st.cache_data.clear()
    st.session_state.stok, st.session_state.riwayat = load_data()
    st.toast("Data berhasil disinkronkan dari Google Sheets!", icon="✅")
    st.rerun()

st.sidebar.divider()

if dark_mode:
    st.markdown("""
        <style>
        .stApp { background-color: #0F172A !important; color: #F8FAFC !important; }
        .stSidebar { background-color: #1E293B !important; }
        div[data-testid="stMetric"] { background-color: #1E293B !important; border: 1px solid #334155 !important; border-radius: 10px !important; padding: 15px !important; }
        div[data-testid="stMetricLabel"] p { color: #94A3B8 !important; font-size: 14px !important; font-weight: 600 !important; }
        div[data-testid="stMetricValue"] div { color: #38BDF8 !important; font-size: 28px !important; font-weight: 700 !important; }
        .stTextInput input, .stNumberInput input, .stSelectbox div[role="combobox"], .stDateInput input { background-color: #1E293B !important; color: #F8FAFC !important; border: 1px solid #475569 !important; border-radius: 8px !important; }
        label, .stMarkdown p, h1, h2, h3, h4, h5, h6, span, div[data-baseweb="select"] { color: #F8FAFC !important; }
        div[data-testid="stDataFrame"] { border: 1px solid #334155 !important; border-radius: 8px !important; }
        .stButton button { background-color: #38BDF8 !important; color: #0F172A !important; font-weight: bold !important; border: none !important; }
        </style>
    """, unsafe_allow_html=True)

st.title("📦 Sistem Gudang Mikrosemen")

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
    for barang in sorted(st.session_state.stok.keys(), key=kunci_urut_nama):
        jumlah = st.session_state.stok[barang]
        if keyword.lower() in barang.lower():
            status = "🔴 HABIS!" if jumlah == 0 else ("🟡 KRITIS" if jumlah < 5 else "🟢 AMAN")
            data_tabel.append({"Nama Barang": barang, "Jumlah Stok (pcs)": jumlah, "Status": status})
    
    if data_tabel:
        df = pd.DataFrame(data_tabel)
        df.index = range(1, len(df) + 1)
        st.dataframe(df, use_container_width=True)
        
        data_pdf_stok = [[item["Nama Barang"], str(item["Jumlah Stok (pcs)"]), item["Status"]] for item in data_tabel]
        headers_stok = ["Nama Barang", "Jumlah Stok (pcs)", "Status"]
        col_widths_stok = [90, 45, 45]
        pdf_bytes_stok = buat_pdf_tabel("Laporan Stok Gudang Mikrosemen", headers_stok, data_pdf_stok, col_widths_stok)
        
        st.download_button(
            label="📄 Download Tabel Stok (PDF)",
            data=pdf_bytes_stok,
            file_name=f"Laporan_Stok_Gudang_{datetime.now().strftime('%d%m%Y')}.pdf",
            mime="application/pdf"
        )
        
        st.divider()
        st.subheader("📈 Visualisasi Grafik Stok")
        
        tipe_grafik = st.radio(
            "Pilih Model Tampilan Grafik:", 
            ["📊 Batang Tegak (Vertical)", "📉 Batang Mendatar (Horizontal)", "📈 Grafik Garis (Line Chart)"], 
            horizontal=True
        )
        
        theme_plotly = "plotly_dark" if dark_mode else "plotly"
        
        if tipe_grafik == "📊 Batang Tegak (Vertical)":
            df_sorted = df.sort_values(by="Jumlah Stok (pcs)", ascending=False)
            fig_bar = px.bar(df_sorted, x="Nama Barang", y="Jumlah Stok (pcs)", color="Status",
                             text="Jumlah Stok (pcs)",
                             color_discrete_map={"🟢 AMAN": "#2ecc71", "🟡 KRITIS": "#f1c40f", "🔴 HABIS!": "#e74c3c"}, 
                             template=theme_plotly)
            fig_bar.update_traces(textposition='outside')
            fig_bar.update_layout(xaxis_tickangle=-45, uniformtext_minsize=8, uniformtext_mode='hide')
            
        elif tipe_grafik == "📉 Batang Mendatar (Horizontal)":
            df_sorted = df.sort_values(by="Jumlah Stok (pcs)", ascending=True)
            fig_bar = px.bar(df_sorted, x="Jumlah Stok (pcs)", y="Nama Barang", color="Status",
                             orientation='h', text="Jumlah Stok (pcs)",
                             color_discrete_map={"🟢 AMAN": "#2ecc71", "🟡 KRITIS": "#f1c40f", "🔴 HABIS!": "#e74c3c"}, 
                             template=theme_plotly)
            fig_bar.update_traces(textposition='outside')
            fig_bar.update_layout(height=650)
            
        else:
            df_sorted = df.sort_values(by="Nama Barang", ascending=True)
            fig_bar = px.line(df_sorted, x="Nama Barang", y="Jumlah Stok (pcs)", markers=True,
                              template=theme_plotly)
            fig_bar.update_traces(line_color="#38BDF8", marker_size=8)
            fig_bar.update_layout(xaxis_tickangle=-45)
            
        st.plotly_chart(fig_bar, use_container_width=True)

elif menu == "📥 Restok Barang Masuk":
    st.header("📥 Tambah Stok Barang")
    barang = st.selectbox("Pilih Barang", sorted(st.session_state.stok.keys(), key=kunci_urut_nama))
    jumlah = st.number_input("Jumlah Masuk", min_value=1, step=1)
    keterangan = st.text_input("Supplier / Keterangan (Opsional)").strip()
    
    if st.button("Simpan Barang Masuk"):
        st.session_state.stok[barang] += jumlah
        st.session_state.riwayat.append({"Waktu": dapatkan_waktu_wib(), "Tipe": "MASUK", "Barang": barang, "Jumlah": f"+{jumlah} pcs", "Pembeli / Keterangan": keterangan or "Restok"})
        
        if save_data():
            panggil_confetti()
            st.success(f"Berhasil menambahkan {jumlah} pcs ke {barang}!")
        else:
            st.session_state.stok[barang] -= jumlah
            st.session_state.riwayat.pop()

elif menu == "📤 Pengiriman Barang Keluar":
    st.header("📤 Pengurangan Stok (Barang Keluar)")
    barang = st.selectbox("Pilih Barang", sorted(st.session_state.stok.keys(), key=kunci_urut_nama))
    stok_ini = st.session_state.stok.get(barang, 0)
    st.caption(f"Sisa stok: **{stok_ini} pcs**")
    
    jumlah = st.number_input("Jumlah Keluar", min_value=1, max_value=max(1, stok_ini), step=1)
    pembeli = st.text_input("👤 Nama Pembeli / Klien").strip()
    
    if st.button("Proses Pengiriman"):
        if not pembeli:
            st.warning("⚠️ Mohon isi nama pembeli!")
        elif stok_ini == 0:
            st.error("❌ Barang habis!")
        elif jumlah <= stok_ini:
            st.session_state.stok[barang] -= jumlah
            sisa = st.session_state.stok[barang]
            st.session_state.riwayat.append({"Waktu": dapatkan_waktu_wib(), "Tipe": "KELUAR", "Barang": barang, "Jumlah": f"-{jumlah} pcs", "Pembeli / Keterangan": pembeli})
            
            if save_data():
                if sisa == 0:
                    kirim_notifikasi_telegram(f"PERHATIAN: STOK HABIS!\nBarang: {barang}\nKeluar: {jumlah} pcs\nKlien: {pembeli}\nSisa: 0 pcs")
                elif sisa < 5:
                    kirim_notifikasi_telegram(f"PERHATIAN: STOK KRITIS!\nBarang: {barang}\nKeluar: {jumlah} pcs\nKlien: {pembeli}\nSisa: {sisa} pcs")
                    
                panggil_confetti()
                st.success(f"Berhasil mengeluarkan {jumlah} pcs untuk {pembeli}!")
            else:
                st.session_state.stok[barang] += jumlah
                st.session_state.riwayat.pop()
        else:
            st.error("Stok tidak mencukupi!")

elif menu == "➕ Tambah Jenis Barang":
    st.header("➕ Tambah Jenis Barang Baru")
    nama_baru = st.text_input("Nama Barang Baru").strip()
    stok_awal = st.number_input("Stok Awal", min_value=0, step=1)
    
    if st.button("Daftarkan Barang"):
        if not nama_baru:
            st.warning("⚠️ Nama barang tidak boleh kosong!")
        elif nama_baru in st.session_state.stok:
            st.warning("⚠️ Barang sudah ada di dalam daftar!")
        else:
            st.session_state.stok[nama_baru] = stok_awal
            st.session_state.riwayat.append({"Waktu": dapatkan_waktu_wib(), "Tipe": "TAMBAH BARU", "Barang": nama_baru, "Jumlah": f"{stok_awal} pcs", "Pembeli / Keterangan": "Baru"})
            
            if save_data():
                panggil_confetti()
                st.success(f"Barang {nama_baru} berhasil ditambahkan!")
            else:
                del st.session_state.stok[nama_baru]
                st.session_state.riwayat.pop()

elif menu == "📜 Riwayat Transaksi":
    st.header("📜 Catatan Riwayat Transaksi")
    if st.session_state.riwayat:
        st.dataframe(pd.DataFrame(st.session_state.riwayat), use_container_width=True)
    else:
        st.info("Belum ada riwayat.")

elif menu == "🗓️ Laporan Periodik (Custom Tanggal)":
    st.header("🗓️ Rekapitulasi Laporan Transaksi Periodik")
    
    col_preset, col_empty = st.columns([2, 2])
    with col_preset:
        preset = st.selectbox("⚡ Pilih Pintasan Waktu:", ["Rentang Tanggal Custom", "7 Hari Terakhir", "30 Hari Terakhir", "Bulan Ini"])
    
    hari_ini = date.today()
    if preset == "7 Hari Terakhir":
        tgl_mulai_default = hari_ini - timedelta(days=7)
        tgl_selesai_default = hari_ini
    elif preset == "30 Hari Terakhir":
        tgl_mulai_default = hari_ini - timedelta(days=30)
        tgl_selesai_default = hari_ini
    elif preset == "Bulan Ini":
        tgl_mulai_default = hari_ini.replace(day=1)
        tgl_selesai_default = hari_ini
    else:
        tgl_mulai_default = hari_ini - timedelta(days=7)
        tgl_selesai_default = hari_ini

    c_start, c_end = st.columns(2)
    tgl_mulai = c_start.date_input("📅 Tanggal Mulai:", value=tgl_mulai_default)
    tgl_selesai = c_end.date_input("📅 Tanggal Selesai:", value=tgl_selesai_default)
    
    if tgl_mulai > tgl_selesai:
        st.error("⚠️ Tanggal Mulai tidak boleh melebihi Tanggal Selesai!")
    else:
        riwayat_filtered = filter_riwayat_berdasarkan_rentang(st.session_state.riwayat, tgl_mulai, tgl_selesai)
        
        # Ringkasan Statistik Laporan
        total_transaksi = len(riwayat_filtered)
        total_masuk = sum(1 for x in riwayat_filtered if x.get("Tipe") == "MASUK")
        total_keluar = sum(1 for x in riwayat_filtered if x.get("Tipe") == "KELUAR")
        
        m1, m2, m3 = st.columns(3)
        m1.metric("📋 Total Transaksi", f"{total_transaksi} Data")
        m2.metric("📥 Barang Masuk", f"{total_masuk} Kali")
        m3.metric("📤 Barang Keluar", f"{total_keluar} Kali")
        
        st.divider()
        
        if riwayat_filtered:
            df_laporan = pd.DataFrame(riwayat_filtered)
            df_laporan.index = range(1, len(df_laporan) + 1)
            st.dataframe(df_laporan, use_container_width=True)
            
            data_pdf = df_laporan.values.tolist()
            headers = ["Waktu", "Tipe", "Barang", "Jumlah", "Keterangan"]
            col_widths = [35, 25, 45, 25, 60]
            
            rentang_str = f"Periode: {tgl_mulai.strftime('%d-%m-%Y')} s/d {tgl_selesai.strftime('%d-%m-%Y')}"
            pdf_bytes = buat_pdf_tabel("Laporan Transaksi Gudang", headers, data_pdf, col_widths, info_tambahan=rentang_str)
            
            st.download_button(
                label=f"📄 Download Laporan PDF ({tgl_mulai.strftime('%d/%m')} - {tgl_selesai.strftime('%d/%m')})",
                data=pdf_bytes,
                file_name=f"Laporan_Gudang_{tgl_mulai.strftime('%Y%m%d')}_{tgl_selesai.strftime('%Y%m%d')}.pdf",
                mime="application/pdf"
            )
        else:
            st.info(f"Belum ada transaksi pada rentang tanggal {tgl_mulai.strftime('%d-%m-%Y')} s/d {tgl_selesai.strftime('%d-%m-%Y')}.")

elif menu == "⚙️ Reset & Backup Data":
    st.header("⚙️ Reset & Backup Data")
    
    st.subheader("💾 Backup Data Gudang")
    st.write("Silakan unduh data stok Anda untuk cadangan (backup):")
    
    col1, col2 = st.columns(2)
    
    df_stok_backup = pd.DataFrame(list(st.session_state.stok.items()), columns=["Nama Barang", "Jumlah Stok"])
    csv_stok = df_stok_backup.to_csv(index=False).encode('utf-8')
    col1.download_button("📥 Download Data Stok (CSV)", data=csv_stok, file_name='backup_stok_mikrosemen.csv', mime='text/csv')
    
    data_pdf = [[k, str(v)] for k, v in st.session_state.stok.items()]
    pdf_bytes = buat_pdf_tabel("Laporan Stok Gudang", ["Nama Barang", "Jumlah Stok (pcs)"], data_pdf, [130, 50])
    col2.download_button("📄 Download Data Stok (PDF)", data=pdf_bytes, file_name="Laporan_Stok_Mikrosemen.pdf", mime="application/pdf")
    
    st.divider()
    
    st.subheader("🚨 Reset Data")
    st.warning("Tombol di bawah ini akan menghapus riwayat dan mengembalikan stok ke kondisi awal.")
    if st.button("🚨 Reset Semua Data"):
        st.session_state.stok = STOK_DEFAULT.copy()
        st.session_state.riwayat = []
        if save_data():
            st.success("Data berhasil di-reset!")
            st.rerun()
