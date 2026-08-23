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

# --- 1. KONFIGURASI URL, WAKTU & BOT TELEGRAM ---
URL_GSHEET_API = "https://script.google.com/macros/s/AKfycbyudM_n5g9O2S88pconh7dJHp0oeEJ0D400dG26wKkysNazniISvSXbNT5ArWL_xY04jg/exec"

# Masukkan Bot Token & Chat ID Telegram Anda di sini
TELEGRAM_BOT_TOKEN = "ISI_DENGAN_BOT_TOKEN_KAMU"
TELEGRAM_CHAT_ID = "ISI_DENGAN_CHAT_ID_KAMU"

def kirim_notifikasi_telegram(pesan):
    """Mengirim pesan notifikasi otomatis ke Telegram Bot"""
    if TELEGRAM_BOT_TOKEN == "ISI_DENGAN_BOT_TOKEN_KAMU" or not TELEGRAM_BOT_TOKEN:
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": pesan,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Gagal kirim notif Telegram: {e}")

def dapatkan_waktu_wib():
    return datetime.now(ZoneInfo("Asia/Jakarta")).strftime("%d-%m-%Y %H:%M")

# --- 2. CACHE FETCH DATA UNTUK PERFORMA LEBIH CEPAT ---
@st.cache_data(ttl=60)
def fetch_data_from_gsheet(url):
    try:
        res = requests.get(url, timeout=8)
        return res.json()
    except Exception as e:
        st.error(f"Gagal mengambil data dari server: {e}")
        return {}

# --- DATA DEFAULT AWAL ---
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
          confetti(Object.assign({}, defaults, opts, {
            particleCount: Math.floor(count * particleRatio)
          }));
        }

        fire(0.25, { spread: 26, startVelocity: 55, });
        fire(0.2, { spread: 60, });
        fire(0.35, { spread: 100, decay: 0.91, scalar: 0.8 });
        fire(0.1, { spread: 120, startVelocity: 25, decay: 0.92, scalar: 1.2 });
        fire(0.1, { spread: 120, startVelocity: 45, });
    </script>
    """
    components.html(confetti_html, height=0, width=0)

def bersihkan_teks_pdf(teks):
    teks_bersih = re.sub(r'[^\x00-\x7F]+', '', str(teks))
    return teks_bersih.strip()

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

# --- STYLING MODERN ---
st.sidebar.title("⚙️ Pengaturan Tampilan")
dark_mode = st.sidebar.toggle("🌙 Mode Gelap Premium", value=True)

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
                    "Waktu": row[0], 
                    "Tipe": row[1], 
                    "Barang": row[2], 
                    "Jumlah": row[3],
                    "Pembeli / Keterangan": pembeli
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
    except requests.exceptions.Timeout:
        st.error("⏰ Koneksi server timeout. Coba klik simpan kembali.")
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

# 1. LIHAT STOK
if menu == "📊 Lihat Semua Stok":
    st.header("📊 Ringkasan Dashboard & Stok Gudang")
    
    total_jenis = len(st.session_state.stok)
    total_unit = sum(st.session_state.stok.values())
    jumlah_kritis = len(item_kritis)
    jumlah_habis = len(item_habis)
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📦 Total Jenis Barang", f"{total_jenis} Item")
    col2.metric("📊 Total Stok Fisik", f"{total_unit} pcs")
    col3.metric("🟡 Stok Kritis (<5)", f"{jumlah_kritis} Item")
    col4.metric("🔴 Stok Habis (0)", f"{jumlah_habis} Item")
    
    st.divider()
    
    col_search, col_sort = st.columns([3, 1])
    with col_search:
        kata_kunci = st.text_input("🔍 Cari Nama Barang...", "")
    with col_sort:
        opsi_urut = st.selectbox("🔀 Urutkan Berdasarkan", [
            "Nama Barang (A-Z / Urut Angka)",
            "Nama Barang (Z-A)",
            "Stok Terbanyak",
            "Stok Terkecil"
        ])
    
    list_barang_terurut = sorted(st.session_state.stok.keys(), key=kunci_urut_nama)
    
    if opsi_urut == "Nama Barang (Z-A)":
        list_barang_terurut.reverse()
    elif opsi_urut == "Stok Terbanyak":
        list_barang_terurut = sorted(st.session_state.stok.keys(), key=lambda x: st.session_state.stok[x], reverse=True)
    elif opsi_urut == "Stok Terkecil":
        list_barang_terurut = sorted(st.session_state.stok.keys(), key=lambda x: st.session_state.stok[x])

    data_tabel = []
    for barang in list_barang_terurut:
        jumlah = st.session_state.stok[barang]
        if kata_kunci.lower() in barang.lower():
            status_tabel = "🔴 HABIS!" if jumlah == 0 else ("🟡 KRITIS" if jumlah < 5 else "🟢 AMAN")
            status_grafik = "HABIS!" if jumlah == 0 else ("KRITIS" if jumlah < 5 else "AMAN")
            data_tabel.append({
                "Nama Barang": barang, 
                "Jumlah Stok (pcs)": jumlah, 
                "Status": status_tabel,
                "StatusGrafik": status_grafik
            })
    
    if data_tabel:
        df_stok = pd.DataFrame(data_tabel)
        df_stok.index = range(1, len(df_stok) + 1)
        
        st.dataframe(
            df_stok[["Nama Barang", "Jumlah Stok (pcs)", "Status"]], 
            use_container_width=True,
            column_config={
                "Nama Barang": st.column_config.TextColumn("Nama Barang"),
                "Jumlah Stok (pcs)": st.column_config.NumberColumn("Jumlah Stok (pcs)", format="%d"),
                "Status": st.column_config.TextColumn("Status")
            }
        )
        
        col_dl1, col_dl2 = st.columns(2)
        with col_dl1:
            csv_stok = df_stok[["Nama Barang", "Jumlah Stok (pcs)", "Status"]].to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Excel / CSV",
                data=csv_stok,
                file_name=f"Laporan_Stok_{dapatkan_waktu_wib()[:10]}.csv",
                mime="text/csv",
                use_container_width=True
            )
        with col_dl2:
            data_pdf = []
            for idx, row in df_stok.iterrows():
                data_pdf.append([idx, row["Nama Barang"], f"{row['Jumlah Stok (pcs)']} pcs", row["Status"]])
            
            pdf_bytes = buat_pdf_tabel(
                "LAPORAN STOK GUDANG MIKROSEMEN", 
                ["No", "Nama Barang", "Jumlah Stok", "Status"], 
                data_pdf, 
                [15, 95, 40, 40]
            )
            
            st.download_button(
                label="📄 Download Laporan PDF",
                data=pdf_bytes,
                file_name=f"Laporan_Stok_{dapatkan_waktu_wib()[:10]}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        
        st.divider()
        st.subheader("📈 Visualisasi & Analisis Stok")
        col_chart1, col_chart2 = st.columns(2)
        
        theme_plotly = "plotly_dark" if dark_mode else "plotly"
        
        with col_chart1:
            st.markdown("##### 📊 Perbandingan Stok per Item")
            fig_bar = px.bar(
                df_stok, x="Nama Barang", y="Jumlah Stok (pcs)", color="StatusGrafik",
                color_discrete_map={"AMAN": "#2ecc71", "KRITIS": "#f1c40f", "HABIS!": "#e74c3c"},
                text="Jumlah Stok (pcs)", template=theme_plotly
            )
            fig_bar.update_layout(xaxis_tickangle=-45, showlegend=True, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_bar, use_container_width=True)
            
        with col_chart2:
            st.markdown("##### 🥧 Proporsi Status Stok Gudang")
            fig_pie = px.pie(
                df_stok, names="StatusGrafik", color="StatusGrafik",
                color_discrete_map={"AMAN": "#2ecc71", "KRITIS": "#f1c40f", "HABIS!": "#e74c3c"},
                hole=0.4, template=theme_plotly
            )
            fig_pie.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_pie, use_container_width=True)

# 2. RESTOK
elif menu == "📥 Restok Barang Masuk":
    st.header("📥 Tambah Stok Barang")
    list_pilihan = sorted(st.session_state.stok.keys(), key=kunci_urut_nama)
    barang = st.selectbox("Pilih Barang", list_pilihan)
    jumlah = st.number_input("Jumlah Masuk", min_value=1, step=1)
    keterangan = st.text_input("Supplier / Keterangan (Opsional)", placeholder="Misal: PT Supplier Utama")
    
    if st.button("Simpan Barang Masuk"):
        waktu_sekarang = dapatkan_waktu_wib()
        st.session_state.stok[barang] += jumlah
        ket_simpan = keterangan if keterangan.strip() != "" else "Restok Masuk"
        st.session_state.riwayat.append({
            "Waktu": waktu_sekarang, "Tipe": "MASUK", "Barang": barang, 
            "Jumlah": f"+{jumlah} pcs", "Pembeli / Keterangan": ket_simpan
        })
        save_data()
        panggil_confetti()
        st.toast(f"Restok Berhasil! +{jumlah} {barang}", icon="🎉")
        st.success(f"Berhasil menambahkan {jumlah} pcs ke {barang}!")

# 3. BARANG KELUAR
elif menu == "📤 Pengiriman Barang Keluar":
    st.header("📤 Pengurangan Stok (Barang Keluar)")
    list_pilihan = sorted(st.session_state.stok.keys(), key=kunci_urut_nama)
    barang = st.selectbox("Pilih Barang", list_pilihan)
    stok_saat_ini = st.session_state.stok.get(barang, 0)
    
    st.caption(f"Sisa stok tersedia untuk {barang}: **{stok_saat_ini} pcs**")
    jumlah = st.number_input("Jumlah Keluar", min_value=1, max_value=max(1, stok_saat_ini), step=1)
    pembeli = st.text_input("👤 Nama Pembeli / Nama Proyek / Klien", placeholder="Misal: Pak Budi / Proyek Villa Bali")
    
    if st.button("Proses Pengiriman"):
        if pembeli.strip() == "":
            st.warning("⚠️ Mohon isi nama pembeli atau nama proyek terlebih dahulu!")
        elif stok_saat_ini == 0:
            st.error("❌ Barang ini sedang habis, tidak bisa melakukan pengiriman!")
        elif jumlah <= stok_saat_ini:
            waktu_sekarang = dapatkan_waktu_wib()
            st.session_state.stok[barang] -= jumlah
            sisa_stok = st.session_state.stok[barang]
            
            st.session_state.riwayat.append({
                "Waktu": waktu_sekarang, "Tipe": "KELUAR", "Barang": barang, 
                "Jumlah": f"-{jumlah} pcs", "Pembeli / Keterangan": pembeli
            })
            save_data()
            
            # CEK DAN KIRIM NOTIFIKASI TELEGRAM JIKA STOK HABIS ATAU KRITIS
            if sisa_stok == 0:
                pesan_tg = f"🚨 *PERHATIAN: STOK HABIS!*\n\n📦 Barang: *{barang}*\n📉 Transaksi: Keluar {jumlah} pcs\n👤 Klien: {pembeli}\n⏰ Waktu: {waktu_sekarang}\n🔴 *Sisa Stok: 0 pcs*. Segera Restok!"
                kirim_notifikasi_telegram(pesan_tg)
            elif sisa_stok < 5:
                pesan_tg = f"🟡 *PERHATIAN: STOK KRITIS!*\n\n📦 Barang: *{barang}*\n📉 Transaksi: Keluar {jumlah} pcs\n👤 Klien: {pembeli}\n⏰ Waktu: {waktu_sekarang}\n⚠️ *Sisa Stok: {sisa_stok} pcs*. Harap re-order segera."
                kirim_notifikasi_telegram(pesan_tg)
            
            panggil_confetti()
            st.toast(f"Pengiriman Diproses! -{jumlah} {barang} ke {pembeli}", icon="🚀")
            st.success(f"Berhasil mengeluarkan {jumlah} pcs dari {barang} untuk {pembeli}!")
        else:
            st.error("Stok tidak mencukupi!")

# 4. TAMBAH BARANG BARU
elif menu == "➕ Tambah Jenis Barang":
    st.header("➕ Tambah Jenis Barang Baru")
    nama_baru = st.text_input("Nama Barang Baru")
    stok_awal = st.number_input("Stok Awal", min_value=0, step=1)
    
    if st.button("Daftarkan Barang"):
        if nama_baru in st.session_state.stok:
            st.warning("Barang sudah ada di dalam sistem!")
        elif nama_baru.strip() != "":
            waktu_sekarang = dapatkan_waktu_wib()
            st.session_state.stok[nama_baru] = stok_awal
            st.session_state.riwayat.append({
                "Waktu": waktu_sekarang, "Tipe": "TAMBAH BARU", "Barang": nama_baru, 
                "Jumlah": f"{stok_awal} pcs", "Pembeli / Keterangan": "Pendaftaran Barang Baru"
            })
            save_data()
            panggil_confetti()
            st.toast(f"Item Baru Terdaftar: {nama_baru}", icon="✨")
            st.success(f"{nama_baru} berhasil didaftarkan!")

# 5. RIWAYAT TRANSAKSI
elif menu == "📜 Riwayat Transaksi":
    st.header("📜 Catatan Riwayat Transaksi & Tanggal")
    if not st.session_state.riwayat:
        st.info("Belum ada riwayat transaksi.")
    else:
        df_riwayat = pd.DataFrame(st.session_state.riwayat)
        
        col_filter1, col_filter2 = st.columns([2, 2])
        with col_filter1:
            filter_tipe = st.multiselect("Filter Tipe Transaksi:", ["MASUK", "KELUAR", "TAMBAH BARU"], default=["MASUK", "KELUAR", "TAMBAH BARU"])
        with col_filter2:
            filter_item = st.selectbox("Filter Spesifik Barang:", ["Semua Barang"] + sorted(list(st.session_state.stok.keys()), key=kunci_urut_nama))
        
        df_filtered_rw = df_riwayat[df_riwayat["Tipe"].isin(filter_tipe)]
        if filter_item != "Semua Barang":
            df_filtered_rw = df_filtered_rw[df_filtered_rw["Barang"] == filter_item]
            
        df_filtered_rw.index = range(1, len(df_filtered_rw) + 1)
        
        st.dataframe(
            df_filtered_rw[["Waktu", "Tipe", "Barang", "Jumlah", "Pembeli / Keterangan"]], 
            use_container_width=True
        )
        
        col_rw1, col_rw2 = st.columns(2)
        with col_rw1:
            csv_riwayat = df_filtered_rw.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Excel / CSV",
                data=csv_riwayat,
                file_name=f"Riwayat_Transaksi_{dapatkan_waktu_wib()[:10]}.csv",
                mime="text/csv",
                use_container_width=True
            )
        with col_rw2:
            data_pdf_rw = []
            for idx, row in df_filtered_rw.iterrows():
                data_pdf_rw.append([row["Waktu"], row["Tipe"], row["Barang"], row["Jumlah"], row["Pembeli / Keterangan"]])
            
            pdf_bytes_rw = buat_pdf_tabel(
                "LAPORAN RIWAYAT TRANSAKSI GUDANG", 
                ["Waktu", "Tipe", "Barang", "Jumlah", "Pembeli / Keterangan"], 
                data_pdf_rw, 
                [30, 20, 50, 25, 65]
            )
            
            st.download_button(
                label="📄 Download Riwayat PDF",
                data=pdf_bytes_rw,
                file_name=f"Riwayat_Transaksi_{dapatkan_waktu_wib()[:10]}.pdf",
                mime="application/pdf",
                use_container_width=True
            )

# 6. LAPORAN MINGGUAN
elif menu == "📆 Laporan Mingguan":
    st.header("📆 Rekapitulasi Laporan Mingguan Gudang")
    
    if not st.session_state.riwayat:
        st.info("Belum ada transaksi yang tercatat untuk dibuatkan laporan mingguan.")
    else:
        df_rw_minggu = pd.DataFrame(st.session_state.riwayat)
        
        def konversi_minggu(waktu_str):
            try:
                dt = datetime.strptime(str(waktu_str)[:10], "%d-%m-%Y")
                minggu_ke = dt.isocalendar()[1]
                tahun = dt.year
                return f"Tahun {tahun} - Minggu ke-{minggu_ke:02d}"
            except Exception:
                return "Lainnya"

        df_rw_minggu["Minggu_Tahun"] = df_rw_minggu["Waktu"].apply(konversi_minggu)
        daftar_minggu = sorted(list(df_rw_minggu["Minggu_Tahun"].unique()), reverse=True)
        
        minggu_pilihan = st.selectbox("📆 Pilih Minggu Laporan:", daftar_minggu)
        df_filtered_mg = df_rw_minggu[df_rw_minggu["Minggu_Tahun"] == minggu_pilihan].copy()
        
        total_masuk_mg = sum(1 for t in df_filtered_mg["Tipe"] if t == "MASUK")
        total_keluar_mg = sum(1 for t in df_filtered_mg["Tipe"] if t == "KELUAR")
        
        c1, c2, c3 = st.columns(3)
        c1.metric("📋 Transaksi Minggu Ini", f"{len(df_filtered_mg)} Transaksi")
        c2.metric("📥 Barang Masuk", f"{total_masuk_mg} Kali")
        c3.metric("📤 Barang Keluar", f"{total_keluar_mg} Kali")
        
        st.divider()
        df_filtered_mg.index = range(1, len(df_filtered_mg) + 1)
        
        st.dataframe(
            df_filtered_mg[["Waktu", "Tipe", "Barang", "Jumlah", "Pembeli / Keterangan"]],
            use_container_width=True
        )
        
        col_mg1, col_mg2 = st.columns(2)
        with col_mg1:
            csv_filtered_mg = df_filtered_mg[["Waktu", "Tipe", "Barang", "Jumlah", "Pembeli / Keterangan"]].to_csv(index=False).encode('utf-8')
            st.download_button(
                label=f"📥 Download Excel Laporan {minggu_pilihan}",
                data=csv_filtered_mg,
                file_name=f"Laporan_{minggu_pilihan.replace(' ', '_')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        with col_mg2:
            data_pdf_mg = []
            for idx, row in df_filtered_mg.iterrows():
                data_pdf_mg.append([row["Waktu"], row["Tipe"], row["Barang"], row["Jumlah"], row["Pembeli / Keterangan"]])
            
            pdf_bytes_mg = buat_pdf_tabel(
                f"LAPORAN TRANSAKSI {minggu_pilihan.upper()}", 
                ["Waktu", "Tipe", "Barang", "Jumlah", "Pembeli / Keterangan"], 
                data_pdf_mg, 
                [30, 20, 50, 25, 65]
            )
            
            st.download_button(
                label=f"📄 Download PDF Laporan {minggu_pilihan}",
                data=pdf_bytes_mg,
                file_name=f"Laporan_{minggu_pilihan.replace(' ', '_')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )

# 7. LAPORAN BULANAN
elif menu == "📅 Laporan Bulanan":
    st.header("📅 Rekapitulasi Laporan Bulanan Gudang")
    
    if not st.session_state.riwayat:
        st.info("Belum ada transaksi yang tercatat untuk dibuatkan laporan bulanan.")
    else:
        df_rw_bulan = pd.DataFrame(st.session_state.riwayat)
        
        def ekstrak_bulan_tahun(waktu_str):
            try:
                dt = datetime.strptime(str(waktu_str)[:10], "%d-%m-%Y")
                return dt.strftime("%m-%Y")
            except Exception:
                return "Lainnya"

        df_rw_bulan["Bulan_Tahun"] = df_rw_bulan["Waktu"].apply(ekstrak_bulan_tahun)
        daftar_bulan = sorted(list(df_rw_bulan["Bulan_Tahun"].unique()), reverse=True)
        bulan_pilihan = st.selectbox("📆 Pilih Bulan & Tahun Laporan:", daftar_bulan)
        
        df_filtered = df_rw_bulan[df_rw_bulan["Bulan_Tahun"] == bulan_pilihan].copy()
        
        total_masuk = sum(1 for t in df_filtered["Tipe"] if t == "MASUK")
        total_keluar = sum(1 for t in df_filtered["Tipe"] if t == "KELUAR")
        
        c1, c2, c3 = st.columns(3)
        c1.metric("📋 Total Transaksi Bulan Ini", f"{len(df_filtered)} Transaksi")
        c2.metric("📥 Barang Masuk", f"{total_masuk} Kali")
        c3.metric("📤 Barang Keluar", f"{total_keluar} Kali")
        
        st.divider()
        df_filtered.index = range(1, len(df_filtered) + 1)
        
        st.dataframe(
            df_filtered[["Waktu", "Tipe", "Barang", "Jumlah", "Pembeli / Keterangan"]],
            use_container_width=True
        )
        
        col_bl1, col_bl2 = st.columns(2)
        with col_bl1:
            csv_filtered = df_filtered[["Waktu", "Tipe", "Barang", "Jumlah", "Pembeli / Keterangan"]].to_csv(index=False).encode('utf-8')
            st.download_button(
                label=f"📥 Download Excel Laporan {bulan_pilihan}",
                data=csv_filtered,
                file_name=f"Laporan_Bulanan_{bulan_pilihan}.csv",
                mime="text/csv",
                use_container_width=True
            )
        with col_bl2:
            data_pdf_bln = []
            for idx, row in df_filtered.iterrows():
                data_pdf_bln.append([row["Waktu"], row["Tipe"], row["Barang"], row["Jumlah"], row["Pembeli / Keterangan"]])
            
            pdf_bytes_bln = buat_pdf_tabel(
                f"LAPORAN TRANSAKSI BULAN {bulan_pilihan}", 
                ["Waktu", "Tipe", "Barang", "Jumlah", "Pembeli / Keterangan"], 
                data_pdf_bln, 
                [30, 20, 50, 25, 65]
            )
            
            st.download_button(
                label=f"📄 Download PDF Laporan {bulan_pilihan}",
                data=pdf_bytes_bln,
                file_name=f"Laporan_Bulanan_{bulan_pilihan}.pdf",
                mime="application/pdf",
                use_container_width=True
            )

# 8. RESET & BACKUP DATA
elif menu == "⚙️ Reset & Backup Data":
    st.header("⚙️ Pengelolaan Backup & Reset Sistem")
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("💾 Backup Data Manual")
        data_backup = {"stok": st.session_state.stok, "riwayat": st.session_state.riwayat}
        st.download_button(
            label="📥 Unduh Backup JSON",
            data=json.dumps(data_backup, indent=4),
            file_name=f"backup_gudang_{dapatkan_waktu_wib()[:10]}.json",
            mime="application/json"
        )

    with col2:
        st.subheader("⚠️ Reset Sistem Ke Awal")
        st.write("Fitur ini akan mengembalikan stok ke nilai standar dan mengosongkan riwayat transaksi baik di aplikasi maupun di Google Sheets.")
        
        konfirmasi = st.checkbox("Saya yakin ingin mereset seluruh data gudang")
        if st.button("🚨 Reset Semua Data", disabled=not konfirmasi):
            st.session_state.stok = STOK_DEFAULT.copy()
            st.session_state.riwayat = []
            save_data()
            st.success("✅ Seluruh data gudang berhasil di-reset ke awalan!")
            st.rerun()
