import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta

st.set_page_config(page_title="Microcement Warehouse", page_icon="📦", layout="wide")

# --- FITUR DARK MODE / LIGHT MODE ---
st.sidebar.title("⚙️ Pengaturan Tampilan")
dark_mode = st.sidebar.toggle("🌙 Mode Gelap (Dark Mode)", value=False)

if dark_mode:
    st.markdown(
        """
        <style>
        .stApp {
            background-color: #0E1117;
            color: #FAFAFA;
        }
        .stSidebar {
            background-color: #161B22;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

# --- DATA DEFAULT AWAL ---
STOK_DEFAULT = {
    "Microcement base": 16, "Ready to use": 15, "Mixed resin A": 12,
    "Ceramic microcement": 4, "Microrock": 17, "Primer ordinary": 7,
    "Epoxy primer": 3, "Self leveling white finish": 4, "Top coat A": 15,
    "Top coat B": 1, "Top coat C": 5, "Pewarna no 1": 3,
    "Pewarna no 2": 10, "Pewarna no 3": 0, "Pewarna no 4": 9, "Metal glaze wax": 0
}

# --- INISIALISASI SESSION STATE ---
if "stok" not in st.session_state:
    st.session_state.stok = STOK_DEFAULT.copy()

if "riwayat" not in st.session_state:
    st.session_state.riwayat = []

st.title("📦 Sistem Gudang Mikrosemen")

menu = st.sidebar.selectbox("Pilih Menu", [
    "📊 Lihat Semua Stok", 
    "📥 Restok Barang Masuk", 
    "📤 Pengiriman Barang Keluar", 
    "➕ Tambah Jenis Barang", 
    "📜 Riwayat Transaksi",
    "⚙️ Reset & Backup Data"
])

# Fungsi Waktu WIB
def dapatkan_waktu_wib():
    waktu_wib = datetime.utcnow() + timedelta(hours=7)
    return waktu_wib.strftime("%d-%m-%Y %H:%M")

# 1. LIHAT STOK & DASHBOARD STATISTIK
if menu == "📊 Lihat Semua Stok":
    st.header("📊 Ringkasan Dashboard & Stok Gudang")
    
    # --- PROSES PERHITUNGAN STATISTIK (METRICS) ---
    total_jenis = len(st.session_state.stok)
    total_unit = sum(st.session_state.stok.values())
    jumlah_kritis = sum(1 for qty in st.session_state.stok.values() if 0 < qty < 5)
    jumlah_habis = sum(1 for qty in st.session_state.stok.values() if qty == 0)
    
    # Tampilan Kotak Statistik (Key Metrics)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📦 Total Jenis Barang", f"{total_jenis} Item")
    col2.metric("📊 Total Stok Fisik", f"{total_unit} pcs")
    col3.metric("🟡 Stok Kritis (<5)", f"{jumlah_kritis} Item")
    col4.metric("🔴 Stok Habis (0)", f"{jumlah_habis} Item")
    
    # Peringatan Otomatis (Alerts)
    if jumlah_habis > 0:
        st.error(f"⚠️ **PERHATIAN:** Ada **{jumlah_habis} jenis barang HABIS!** Segera lakukan restok.")
    elif jumlah_kritis > 0:
        st.warning(f"🔔 **INFORMASI:** Ada **{jumlah_kritis} jenis barang STOK KRITIS!** Lakukan re-order dalam waktu dekat.")
    
    st.divider()
    
    # Fitur Search Bar
    kata_kunci = st.text_input("🔍 Cari Nama Barang...", "")
    
    data_tabel = []
    for barang, jumlah in st.session_state.stok.items():
        if kata_kunci.lower() in barang.lower():
            status = "🔴 HABIS!" if jumlah == 0 else ("🟡 KRITIS" if jumlah < 5 else "🟢 AMAN")
            data_tabel.append({"Nama Barang": barang, "Jumlah Stok (pcs)": jumlah, "Status": status})
    
    if data_tabel:
        df_stok = pd.DataFrame(data_tabel)
        st.dataframe(df_stok, use_container_width=True)
        
        csv_stok = df_stok.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Laporan Stok (CSV/Excel)",
            data=csv_stok,
            file_name=f"Laporan_Stok_{dapatkan_waktu_wib()[:10]}.csv",
            mime="text/csv"
        )
    else:
        st.warning(f"Barang dengan kata kunci '{kata_kunci}' tidak ditemukan.")

# 2. RESTOK
elif menu == "📥 Restok Barang Masuk":
    st.header("📥 Tambah Stok Barang")
    barang = st.selectbox("Pilih Barang", list(st.session_state.stok.keys()))
    jumlah = st.number_input("Jumlah Masuk", min_value=1, step=1)
    
    if st.button("Simpan Barang Masuk"):
        waktu_sekarang = dapatkan_waktu_wib()
        st.session_state.stok[barang] += jumlah
        st.session_state.riwayat.append({"Waktu": waktu_sekarang, "Tipe": "MASUK", "Barang": barang, "Jumlah": f"+{jumlah} pcs"})
        st.success(f"Berhasil menambahkan {jumlah} pcs ke {barang}!")

# 3. BARANG KELUAR
elif menu == "📤 Pengiriman Barang Keluar":
    st.header("📤 Pengurangan Stok (Barang Keluar)")
    barang = st.selectbox("Pilih Barang", list(st.session_state.stok.keys()))
    jumlah = st.number_input("Jumlah Keluar", min_value=1, step=1)
    
    if st.button("Proses Pengiriman"):
        if jumlah <= st.session_state.stok[barang]:
            waktu_sekarang = dapatkan_waktu_wib()
            st.session_state.stok[barang] -= jumlah
            st.session_state.riwayat.append({"Waktu": waktu_sekarang, "Tipe": "KELUAR", "Barang": barang, "Jumlah": f"-{jumlah} pcs"})
            st.success(f"Berhasil mengeluarkan {jumlah} pcs dari {barang} pada {waktu_sekarang}!")
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
            st.success(f"{nama_baru} berhasil didaftarkan!")

# 5. RIWAYAT
elif menu == "📜 Riwayat Transaksi":
    st.header("📜 Catatan Riwayat Transaksi & Tanggal")
    if not st.session_state.riwayat:
        st.info("Belum ada riwayat transaksi.")
    else:
        df_riwayat = pd.DataFrame(st.session_state.riwayat)
        st.dataframe(df_riwayat, use_container_width=True)
        
        csv_riwayat = df_riwayat.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Riwayat Transaksi (CSV/Excel)",
            data=csv_riwayat,
            file_name=f"Riwayat_Transaksi_{dapatkan_waktu_wib()[:10]}.csv",
            mime="text/csv"
        )

# 6. RESET & BACKUP DATA
elif menu == "⚙️ Reset & Backup Data":
    st.header("⚙️ Pengelolaan Backup & Reset Sistem")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("💾 Backup & Restore Data")
        
        data_backup = {
            "stok": st.session_state.stok,
            "riwayat": st.session_state.riwayat
        }
        json_string = json.dumps(data_backup, indent=4)
        
        st.download_button(
            label="📥 Unduh File Backup (JSON)",
            data=json_string,
            file_name=f"backup_gudang_{dapatkan_waktu_wib()[:10]}.json",
            mime="application/json"
        )
        
        st.divider()
        
        st.write("📂 Upload File Backup untuk Mengembalikan Data:")
        file_upload = st.file_uploader("Pilih file .json backup", type=["json"])
        if file_upload is not None:
            if st.button("Restore Data Sekarang"):
                data_restored = json.load(file_upload)
                st.session_state.stok = data_restored.get("stok", {})
                st.session_state.riwayat = data_restored.get("riwayat", [])
                st.success("✅ Data berhasil dipulihkan dari file backup!")
                st.rerun()

    with col2:
        st.subheader("⚠️ Reset Sistem Ke Awalan")
        st.write("Fitur ini akan menghapus seluruh data transaksi dan mengembalikan stok ke angka default awal.")
        
        konfirmasi = st.checkbox("Saya yakin ingin mereset seluruh data gudang")
        if st.button("🚨 Reset Semua Data", disabled=not konfirmasi):
            st.session_state.stok = STOK_DEFAULT.copy()
            st.session_state.riwayat = []
            st.success("✅ Seluruh sistem gudang berhasil di-reset!")
            st.rerun()
