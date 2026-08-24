import streamlit as st
import pandas as pd
import json
import requests
import plotly.express as px
from datetime import datetime
from zoneinfo import ZoneInfo
import streamlit.components.v1 as components
import re
from fpdf import FPDF

st.set_page_config(page_title="Microcement Warehouse", page_icon="📦", layout="wide")

URL_GSHEET_API = "https://script.google.com/macros/s/AKfycbyudM_n5g9O2S88pconh7dJHp0oeEJ0D400dG26wKkysNazniISvSXbNT5ArWL_xY04jg/exec"

# --- TOKEN BOT & CHAT ID ---
TELEGRAM_BOT_TOKEN = "8849647370:AAESRwPya7DVJAYR7WgvxL8eESqIV81ZqpE"
TELEGRAM_CHAT_ID = 2106196278

def kirim_notifikasi_telegram(pesan):
    """Mengirim pesan notifikasi otomatis ke Bot Telegram"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        st.warning("⚠️ Token atau Chat ID Telegram kosong!")
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": int(TELEGRAM_CHAT_ID),
        "text": pesan,
    }
    try:
        response = requests.post(url, json=payload, timeout=15)
        st.write("🔍 **Debug Respon Telegram:**", response.text)
    except Exception as e:
        st.error(f"❌ Gagal koneksi ke Telegram: {e}")

def dapatkan_waktu_wib():
    return datetime.now(ZoneInfo("Asia/Jakarta")).strftime("%d-%m-%Y %H:%M")

@st.cache_data(ttl=60)
def fetch_data_from_gsheet(url):
    try:
        res = requests.get(url, timeout=15)
        return res.json()
    except Exception as e:
        st.error(f"Gagal mengambil data dari server: {e}")
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
    confetti_html = """
    <script src="https://cdn.jsdelivr.net/npm/canvas-confetti@1.6.0/dist/confetti.browser.min.js"></script>
    <script>
        var count = 200;
        var defaults = { origin: { y: 0.7 } };
        function fire(particleRatio, opts) {
          confetti(Object.assign({}, defaults, opts, { particleCount: Math.floor(count * particleRatio) }));
        }
        fire(0.25, { spread: 26, startVelocity: 55 });
        fire(0.2, { spread: 60 });
        fire(0.35, { spread: 100, decay: 0.91, scalar: 0.8 });
        fire(0.1, { spread: 120, startVelocity: 25, decay: 0.92, scalar: 1.2 });
        fire(0.1, { spread: 120, startVelocity: 45 });
    </script>
    """
    components.html(confetti_html, height=0, width=0)

def bersihkan_teks_pdf(teks):
    return re.sub(r'[^\x00-\x7F]+', '', str(teks)).strip()

def buat_pdf_tabel(judul, headers, data, col_widths):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, judul, ln=True, align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 8, f"Tanggal Cetak: {dapatkan_waktu_wib()}", ln=True, align="C")
    pdf.ln(5)
    
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(230, 230, 230)
    for i, h in enumerate(headers):
        pdf.cell(col_widths[i], 8, h, border=1, align="C", fill=True)
    pdf.ln()
    
    pdf.set_font("Helvetica", "", 9)
    for row in data:
        for i, val in enumerate(row):
            teks_bersih = bersihkan_teks_pdf(val)
            align_text = "C" if i == 0 or i == len(row)-1 else "L"
            pdf.cell(col_widths[i], 7, teks_bersih, border=1, align=align_text)
        pdf.ln()
    return bytes(pdf.output())

st.sidebar.title("⚙️ Pengaturan Tampilan")
dark_mode = st.sidebar.toggle("🌙 Mode Gelap Premium", value=True, key="setting_dark_mode")

if dark_mode:
    st.markdown(
        """
        <style>
        .stApp { background-color: #0F172A !important; color: #F8FAFC !important; }
        .stSidebar { background-color: #1E293B !important; }
        div[data-testid="stMetric"] { background-color: #1E293B !important; border: 1px solid #334155 !important; border-radius: 10px !important; padding: 15px !important; }
        div[data-testid="stMetricLabel"] p { color: #94A3B8 !important; font-size: 14px !important; font-weight: 600 !important; }
        div[data-testid="stMetricValue"] div { color: #38BDF8 !important; font-size: 28px !important; font-weight: 700 !important; }
        .stTextInput input, .stSelectbox div[role="combobox"] { background-color: #1E293B !important; color: #F8FAFC !important; border: 1px solid #475569 !important; border-radius: 8px !important; }
        label, .stMarkdown p, h1, h2, h3, h4, h5, h6, span { color: #F8FAFC !important; }
        div[data-testid="stDataFrame"] { border: 1px solid #334155 !important; border-radius: 8px !important; }
        </style>
        """,
        unsafe_allow_html=True
    )

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
                riwayat_list.append({
                    "Waktu": row[0], "Tipe": row[1], "Barang": row[2], 
                    "Jumlah": row[3], "Pembeli / Keterangan": pembeli
                })
    if not stok_dict:
        stok_dict = STOK_DEFAULT.copy()
    return stok_dict, riwayat_list

def save_data():
    payload = {
        "stok": [[k, v] for k, v in st.session_state.stok.items()],
        "riwayat": st.session_state.riwayat
    }
    try:
        res = requests.post(URL_GSHEET_API, json=payload, timeout=12)
        res.raise_for_status()
        st.cache_data.clear()
    except Exception as e:
        st.error(f"Gagal menyimpan data: {e}")

if "stok" not in st.session_state or "riwayat" not in st.session_state:
    st.session_state.stok, st.session_state.riwayat = load_data()

st.title("📦 Sistem Gudang Mikrosemen")

item_habis = [b for b, q in st.session_state.stok.items() if q == 0]
item_kritis = [b for b, q in st.session_state.stok.items() if 0 < q < 5]

if item_habis:
    st.error(f"⚠️ **PERHATIAN:** Ada {len(item_habis)} item habis: {', '.join(item_habis[:3])}{'...' if len(item_habis) > 3 else ''}")
elif item_kritis:
    st.warning(f"🔔 **INFORMASI:** Ada {len(item_kritis)} item kritis (<5 pcs): {', '.join(item_kritis[:3])}{'...' if len(item_kritis) > 3 else ''}")

menu = st.sidebar.selectbox("Pilih Menu", [
    "📊 Lihat Semua Stok", 
    "📥 Restok Barang Masuk", 
    "📤 Pengiriman Barang Keluar", 
    "➕ Tambah Jenis Barang", 
    "📜 Riwayat Transaksi",
    "📆 Laporan Mingguan",
    "📅 Laporan Bulanan",
    "⚙️ Reset & Backup Data"
])

if menu == "📊 Lihat Semua Stok":
    st.header("📊 Ringkasan Dashboard & Stok Gudang")
    total_jenis = len(st.session_state.stok)
    total_unit = sum(st.session_state.stok.values())
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📦 Total Jenis Barang", f"{total_jenis} Item")
    col2.metric("📊 Total Stok Fisik", f"{total_unit} pcs")
    col3.metric("🟡 Stok Kritis (<5)", f"{len(item_kritis)} Item")
    col4.metric("🔴 Stok Habis (0)", f"{len(item_habis)} Item")
    
    st.divider()
    kata_kunci = st.text_input("🔍 Cari Nama Barang...", "")
    
    list_barang_terurut = sorted(st.session_state.stok.keys(), key=kunci_urut_nama)
    data_tabel = []
    for barang in list_barang_terurut:
        jumlah = st.session_state.stok[barang]
        if kata_kunci.lower() in barang.lower():
            status_tabel = "🔴 HABIS!" if jumlah == 0 else ("🟡 KRITIS" if jumlah < 5 else "🟢 AMAN")
            status_grafik = "HABIS!" if jumlah == 0 else ("KRITIS" if jumlah < 5 else "AMAN")
            data_tabel.append({"Nama Barang": barang, "Jumlah Stok (pcs)": jumlah, "Status": status_tabel, "StatusGrafik": status_grafik})
    
    if data_tabel:
        df_stok = pd.DataFrame(data_tabel)
        df_stok.index = range(1, len(df_stok) + 1)
        st.dataframe(df_stok[["Nama Barang", "Jumlah Stok (pcs)", "Status"]], use_container_width=True)
        
        theme_plotly = "plotly_dark" if dark_mode else "plotly"
        fig_bar = px.bar(df_stok, x="Nama Barang", y="Jumlah Stok (pcs)", color="StatusGrafik",
                         color_discrete_map={"AMAN": "#2ecc71", "KRITIS": "#f1c40f", "HABIS!": "#e74c3c"}, template=theme_plotly)
        st.plotly_chart(fig_bar, use_container_width=True)

elif menu == "📥 Restok Barang Masuk":
    st.header("📥 Tambah Stok Barang")
    barang = st.selectbox("Pilih Barang", sorted(st.session_state.stok.keys(), key=kunci_urut_nama))
    jumlah = st.number_input("Jumlah Masuk", min_value=1, step=1)
    keterangan = st.text_input("Supplier / Keterangan (Opsional)")
    
    if st.button("Simpan Barang Masuk"):
        waktu_sekarang = dapatkan_waktu_wib()
        st.session_state.stok[barang] += jumlah
        st.session_state.riwayat.append({"Waktu": waktu_sekarang, "Tipe": "MASUK", "Barang": barang, "Jumlah": f"+{jumlah} pcs", "Pembeli / Keterangan": keterangan or "Restok Masuk"})
        save_data()
        panggil_confetti()
        st.success(f"Berhasil menambahkan {jumlah} pcs ke {barang}!")

elif menu == "📤 Pengiriman Barang Keluar":
    st.header("📤 Pengurangan Stok (Barang Keluar)")
    barang = st.selectbox("Pilih Barang", sorted(st.session_state.stok.keys(), key=kunci_urut_nama))
    stok_saat_ini = st.session_state.stok.get(barang, 0)
    st.caption(f"Sisa stok tersedia: **{stok_saat_ini} pcs**")
    
    jumlah = st.number_input("Jumlah Keluar", min_value=1, max_value=max(1, stok_saat_ini), step=1)
    pembeli = st.text_input("👤 Nama Pembeli / Klien")
    
    if st.button("Proses Pengiriman"):
        if not pembeli.strip():
            st.warning("⚠️ Mohon isi nama pembeli!")
        elif stok_saat_ini == 0:
            st.error("❌ Barang habis!")
        elif jumlah <= stok_saat_ini:
            waktu_sekarang = dapatkan_waktu_wib()
            st.session_state.stok[barang] -= jumlah
            sisa_stok = st.session_state.stok[barang]
            
            st.session_state.riwayat.append({"Waktu": waktu_sekarang, "Tipe": "KELUAR", "Barang": barang, "Jumlah": f"-{jumlah} pcs", "Pembeli / Keterangan": pembeli})
            save_data()
            
            if sisa_stok == 0:
                kirim_notifikasi_telegram(f"PERHATIAN: STOK HABIS!\n\nBarang: {barang}\nTransaksi: Keluar {jumlah} pcs\nKlien: {pembeli}\nSisa Stok: 0 pcs. Segera Restok!")
            elif sisa_stok < 5:
                kirim_notifikasi_telegram(f"PERHATIAN: STOK KRITIS!\n\nBarang: {barang}\nTransaksi: Keluar {jumlah} pcs\nKlien: {pembeli}\nSisa Stok: {sisa_stok} pcs. Harap re-order segera.")
                
            panggil_confetti()
            st.success(f"Berhasil mengeluarkan {jumlah} pcs untuk {pembeli}!")
        else:
            st.error("Stok tidak mencukupi!")

elif menu == "➕ Tambah Jenis Barang":
    st.header("➕ Tambah Jenis Barang Baru")
    nama_baru = st.text_input("Nama Barang Baru")
    stok_awal = st.number_input("Stok Awal", min_value=0, step=1)
    if st.button("Daftarkan Barang"):
        if nama_baru in st.session_state.stok:
            st.warning("Barang sudah ada!")
        elif nama_baru.strip():
            st.session_state.stok[nama_baru] = stok_awal
            st.session_state.riwayat.append({"Waktu": dapatkan_waktu_wib(), "Tipe": "TAMBAH BARU", "Barang": nama_baru, "Jumlah": f"{stok_awal} pcs", "Pembeli / Keterangan": "Barang Baru"})
            save_data()
            panggil_confetti()
            st.success(f"Barang {nama_baru} berhasil ditambahkan!")

elif menu == "📜 Riwayat Transaksi":
    st.header("📜 Catatan Riwayat Transaksi")
    if st.session_state.riwayat:
        st.dataframe(pd.DataFrame(st.session_state.riwayat), use_container_width=True)
    else:
        st.info("Belum ada riwayat transaksi.")

elif menu == "📆 Laporan Mingguan":
    st.header("📆 Rekapitulasi Laporan Mingguan Gudang")
    st.info("Menu laporan mingguan aktif.")

elif menu == "📅 Laporan Bulanan":
    st.header("📅 Rekapitulasi Laporan Bulanan Gudang")
    st.info("Menu laporan bulanan aktif.")

elif menu == "⚙️ Reset & Backup Data":
    st.header("⚙️ Reset & Backup Data")
    if st.button("🚨 Reset Semua Data"):
        st.session_state.stok = STOK_DEFAULT.copy()
        st.session_state.riwayat = []
        save_data()
        st.success("Data di-reset!")
        st.rerun()
