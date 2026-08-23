import streamlit as st
from datetime import datetime, timedelta

st.set_page_config(page_title="Microcement Warehouse", page_icon="📦", layout="wide")

if "stok" not in st.session_state:
    st.session_state.stok = {
        "Microcement base": 16, "Ready to use": 15, "Mixed resin A": 12,
        "Ceramic microcement": 4, "Microrock": 17, "Primer ordinary": 7,
        "Epoxy primer": 3, "Self leveling white finish": 4, "Top coat A": 15,
        "Top coat B": 1, "Top coat C": 5, "Pewarna no 1": 3,
        "Pewarna no 2": 10, "Pewarna no 3": 0, "Pewarna no 4": 9, "Metal glaze wax": 0
    }

if "riwayat" not in st.session_state:
    st.session_state.riwayat = []

st.title("📦 Sistem Gudang Mikrosemen")

menu = st.sidebar.selectbox("Pilih Menu", [
    "📊 Lihat Semua Stok", 
    "📥 Restok Barang Masuk", 
    "📤 Pengiriman Barang Keluar", 
    "➕ Tambah Jenis Barang", 
    "📜 Riwayat Transaksi"
])

# Fungsi untuk mendapatkan waktu WIB (UTC + 7)
def dapatkan_waktu_wib():
    waktu_wib = datetime.utcnow() + timedelta(hours=7)
    return waktu_wib.strftime("%d-%m-%Y %H:%M")

if menu == "📊 Lihat Semua Stok":
    st.header("📊 Daftar Stok Gudang")
    data_tabel = []
    for barang, jumlah in st.session_state.stok.items():
        status = "🔴 HABIS!" if jumlah == 0 else ("🟡 KRITIS" if jumlah < 5 else "🟢 AMAN")
        data_tabel.append({"Nama Barang": barang, "Jumlah Stok (pcs)": jumlah, "Status": status})
    st.dataframe(data_tabel, use_container_width=True)

elif menu == "📥 Restok Barang Masuk":
    st.header("📥 Tambah Stok Barang")
    barang = st.selectbox("Pilih Barang", list(st.session_state.stok.keys()))
    jumlah = st.number_input("Jumlah Masuk", min_value=1, step=1)
    
    if st.button("Simpan Barang Masuk"):
        waktu_sekarang = dapatkan_waktu_wib()
        st.session_state.stok[barang] += jumlah
        st.session_state.riwayat.append(f"[{waktu_sekarang}] MASUK: {barang} (+{jumlah} pcs)")
        st.success(f"Berhasil menambahkan {jumlah} pcs ke {barang}!")

elif menu == "📤 Pengiriman Barang Keluar":
    st.header("📤 Pengurangan Stok (Barang Keluar)")
    barang = st.selectbox("Pilih Barang", list(st.session_state.stok.keys()))
    jumlah = st.number_input("Jumlah Keluar", min_value=1, step=1)
    
    if st.button("Proses Pengiriman"):
        if jumlah <= st.session_state.stok[barang]:
            waktu_sekarang = dapatkan_waktu_wib()
            st.session_state.stok[barang] -= jumlah
            st.session_state.riwayat.append(f"[{waktu_sekarang}] KELUAR: {barang} (-{jumlah} pcs)")
            st.success(f"Berhasil mengeluarkan {jumlah} pcs dari {barang} pada {waktu_sekarang}!")
        else:
            st.error("Stok tidak mencukupi!")

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
            st.session_state.riwayat.append(f"[{waktu_sekarang}] TAMBAH BARU: {nama_baru} ({stok_awal} pcs)")
            st.success(f"{nama_baru} berhasil didaftarkan!")

elif menu == "📜 Riwayat Transaksi":
    st.header("📜 Catatan Riwayat Transaksi & Tanggal")
    if not st.session_state.riwayat:
        st.info("Belum ada riwayat transaksi.")
    else:
        for log in reversed(st.session_state.riwayat):
            st.write(f"- {log}")
            
