import streamlit as st
import pandas as pd
import json
import requests
import plotly.express as px
from datetime import datetime, timedelta
import streamlit.components.v1 as components
import re

st.set_page_config(page_title="Microcement Warehouse", page_icon="📦", layout="wide")

# --- URL GOOGLE APPS SCRIPT KAMU ---
URL_GSHEET_API = "https://script.google.com/macros/s/AKfycbyudM_n5g9O2S88pconh7dJHp0oeEJ0D400dG26wKkysNazniISvSXbNT5ArWL_xY04jg/exec"

# --- DATA DEFAULT AWAL ---
STOK_DEFAULT = {
    "Microcement base": 16, "Ready to use": 15, "Mixed resin A": 12,
    "Ceramic microcement": 4, "Microrock": 17, "Primer ordinary": 7,
    "Epoxy primer": 3, "Self leveling white finish": 4, "Top coat A": 15,
    "Top coat B": 1, "Top coat C": 5, "Pewarna no 1": 3,
    "Pewarna no 2": 10, "Pewarna no 3": 0, "Pewarna no 4": 9, 
    "Metal glaze wax": 0, "Metallic glaze wax": 0
}

# --- FUNGSI URUTKAN NAMA BARANG BERDASARKAN ANGKA DI BELAKANGNYA (NATURAL SORT) ---
def kunci_urut_nama(nama):
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', nama)]

# --- FUNGSI EFEK ANIMASI CONFETTI 🎉 ---
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

# --- FITUR DARK MODE / LIGHT MODE ---
st.sidebar.title("⚙️ Pengaturan Tampilan")
dark_mode = st.sidebar.toggle("🌙 Mode Gelap (Dark Mode)", value=False)

if dark_mode:
    st.markdown(
        """
        <style>
        .stApp { background-color: #0E1117; color: #FAFAFA; }
        .stSidebar { background-color: #161B22; }
        </style>
        """,
        unsafe_allow_html=True
    )

# --- FUNGSI LOAD & SAVE DATA VIA API GOOGLE APPS SCRIPT ---
def load_data():
    try:
        res = requests.get(URL_GSHEET_API)
        data = res.json()
        
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
                    riwayat_list.append({
                        "Waktu": row[0], "Tipe": row[1], "Barang": row[2], "Jumlah": row[3]
                    })
                    
        if not stok_dict:
            stok_dict = STOK_DEFAULT.copy()
            
        return stok_dict, riwayat_list
    except Exception:
        return STOK_DEFAULT.copy(), []

def save_data():
    payload = {
        "stok": [[k, v] for k, v in st.session_state.stok.items()],
        "riwayat": st.session_state.riwayat
    }
    try:
        requests.post(URL_GSHEET_API, json=payload)
    except Exception as e:
        st.error(f"Gagal menyimpan data: {e}")

# Inisialisasi Data awal dari Cloud
if "stok" not in st.session_state or "riwayat" not in st.session_state:
    st.session_state.stok, st.session_state.riwayat = load_data()

st.title("📦 Sistem Gudang Mikrosemen")

menu = st.sidebar.selectbox("Pilih Menu", [
    "📊 Lihat Semua Stok", 
    "📥 Restok Barang Masuk", 
    "📤 Pengiriman Barang Keluar", 
    "➕ Tambah Jenis Barang", 
    "📜 Riwayat Transaksi",
    "⚙️ Reset & Backup Data"
])

def dapatkan_waktu_wib():
    waktu_wib = datetime.utcnow() + timedelta(hours=7)
    return waktu_wib.strftime("%d-%m-%Y %H:%M")

# 1. LIHAT STOK & DASHBOARD STATISTIK & GRAFIK
if menu == "📊 Lihat Semua Stok":
    st.header("📊 Ringkasan Dashboard & Stok Gudang")
    
    total_jenis = len(st.session_state.stok)
    total_unit = sum(st.session_state.stok.values())
    jumlah_kritis = sum(1 for qty in st.session_state.stok.values() if 0 < qty < 5)
    jumlah_habis = sum(1 for qty in st.session_state.stok.values() if qty == 0)
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📦 Total Jenis Barang", f"{total_jenis} Item")
    col2.metric("📊 Total Stok Fisik", f"{total_unit} pcs")
    col3.metric("🟡 Stok Kritis (<5)", f"{jumlah_kritis} Item")
    col4.metric("🔴 Stok Habis (0)", f"{jumlah_habis} Item")
    
    if jumlah_habis > 0:
        st.error(f"🚨 **PERHATIAN:** Ada **{jumlah_habis} jenis barang HABIS!** Segera lakukan restok.")
    elif jumlah_kritis > 0:
        st.warning(f"🔔 **INFORMASI:** Ada **{jumlah_kritis} jenis barang STOK KRITIS!** Lakukan re-order dalam waktu dekat.")
    
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
    
    # PROSES SORTING / PENGURUTAN AUTOMATIS
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
        
        # Penomoran baris dimulai dari angka 1
        df_stok.index = range(1, len(df_stok) + 1)
        
        # TABEL DENGAN PENGATURAN LEBAR KOLOM (COLUMN WIDTH) AGAR PROPORSIONAL & TIDAK ADA WHITESPACE BERLEBIHAN
        st.dataframe(
            df_stok[["Nama Barang", "Jumlah Stok (pcs)", "Status"]], 
            use_container_width=True,
            column_config={
                "Nama Barang": st.column_config.TextColumn(
                    "Nama Barang",
                    width="large"
                ),
                "Jumlah Stok (pcs)": st.column_config.NumberColumn(
                    "Jumlah Stok (pcs)",
                    format="%d",
                    width="medium",
                    help="Jumlah unit fisik yang tersedia di gudang"
                ),
                "Status": st.column_config.TextColumn(
                    "Status",
                    width="small"
                )
            }
        )
        
        csv_stok = df_stok[["Nama Barang", "Jumlah Stok (pcs)", "Status"]].to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Laporan Stok (CSV/Excel)",
            data=csv_stok,
            file_name=f"Laporan_Stok_{dapatkan_waktu_wib()[:10]}.csv",
            mime="text/csv"
        )
        
        st.divider()
        st.subheader("📈 Visualisasi & Analisis Stok")
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            st.markdown("##### 📊 Perbandingan Stok per Item")
            fig_bar = px.bar(
                df_stok, x="Nama Barang", y="Jumlah Stok (pcs)", color="StatusGrafik",
                color_discrete_map={"AMAN": "#2ecc71", "KRITIS": "#f1c40f", "HABIS!": "#e74c3c"},
                text="Jumlah Stok (pcs)"
            )
            fig_bar.update_layout(xaxis_tickangle=-45, showlegend=True)
            st.plotly_chart(fig_bar, use_container_width=True)
            
        with col_chart2:
            st.markdown("##### 🥧 Proporsi Status Stok Gudang")
            fig_pie = px.pie(
                df_stok, names="StatusGrafik", color="StatusGrafik",
                color_discrete_map={"AMAN": "#2ecc71", "KRITIS": "#f1c40f", "HABIS!": "#e74c3c"},
                hole=0.4
            )
            st.plotly_chart(fig_pie, use_container_width=True)

# 2. RESTOK
elif menu == "📥 Restok Barang Masuk":
    st.header("📥 Tambah Stok Barang")
    
    list_pilihan = sorted(st.session_state.stok.keys(), key=kunci_urut_nama)
    barang = st.selectbox("Pilih Barang", list_pilihan)
    jumlah = st.number_input("Jumlah Masuk", min_value=1, step=1)
    
    if st.button("Simpan Barang Masuk"):
        waktu_sekarang = dapatkan_waktu_wib()
        st.session_state.stok[barang] += jumlah
        st.session_state.riwayat.append({"Waktu": waktu_sekarang, "Tipe": "MASUK", "Barang": barang, "Jumlah": f"+{jumlah} pcs"})
        save_data()
        
        panggil_confetti()
        st.toast(f"Restok Berhasil! +{jumlah} {barang}", icon="🎉")
        st.success(f"Berhasil menambahkan {jumlah} pcs ke {barang} dan tersimpan di Google Sheets!")

# 3. BARANG KELUAR
elif menu == "📤 Pengiriman Barang Keluar":
    st.header("📤 Pengurangan Stok (Barang Keluar)")
    
    list_pilihan = sorted(st.session_state.stok.keys(), key=kunci_urut_nama)
    barang = st.selectbox("Pilih Barang", list_pilihan)
    jumlah = st.number_input("Jumlah Keluar", min_value=1, step=1)
    
    if st.button("Proses Pengiriman"):
        if jumlah <= st.session_state.stok[barang]:
            waktu_sekarang = dapatkan_waktu_wib()
            st.session_state.stok[barang] -= jumlah
            st.session_state.riwayat.append({"Waktu": waktu_sekarang, "Tipe": "KELUAR", "Barang": barang, "Jumlah": f"-{jumlah} pcs"})
            save_data()
            
            panggil_confetti()
            st.toast(f"Pengiriman Diproses! -{jumlah} {barang}", icon="🚀")
            st.success(f"Berhasil mengeluarkan {jumlah} pcs dari {barang} dan tersimpan di Google Sheets!")
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
            st.session_state.riwayat.append({"Waktu": waktu_sekarang, "Tipe": "TAMBAH BARU", "Barang": nama_baru, "Jumlah": f"{stok_awal} pcs"})
            save_data()
            
            panggil_confetti()
            st.toast(f"Item Baru Terdaftar: {nama_baru}", icon="✨")
            st.success(f"{nama_baru} berhasil didaftarkan ke Google Sheets!")

# 5. RIWAYAT
elif menu == "📜 Riwayat Transaksi":
    st.header("📜 Catatan Riwayat Transaksi & Tanggal")
    if not st.session_state.riwayat:
        st.info("Belum ada riwayat transaksi.")
    else:
        df_riwayat = pd.DataFrame(st.session_state.riwayat)
        df_riwayat.index = range(1, len(df_riwayat) + 1)
        st.dataframe(df_riwayat, use_container_width=True)

# 6. RESET & BACKUP DATA
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
            st.success("✅ Seluruh data gudang berhasil di-reset ke awalan dan tersimpan di Google Sheets!")
            st.rerun()
