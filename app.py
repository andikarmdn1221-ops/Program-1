import streamlit as st
import pandas as pd
import json
import requests
import plotly.express as px
from datetime import datetime, timedelta

st.set_page_config(page_title="Microcement Warehouse", page_icon="📦", layout="wide")

# --- URL GOOGLE APPS SCRIPT ---
URL_GSHEET_API = "https://script.google.com/macros/s/AKfycbyudM_n5g9O2S88pconh7dJHp0oeEJ0D400dG26wKkysNazniISvSXbNT5ArWL_xY04jg/exec"

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

# --- IDENTITAS PETUGAS / PENGGUNA ---
st.sidebar.divider()
st.sidebar.subheader("👤 Identitas Pengguna")
nama_petugas = st.sidebar.text_input("Nama Petugas / Pengguna", value="Admin Gudang")

# --- FUNGSI LOAD & SAVE DATA VIA API GOOGLE APPS SCRIPT ---
def load_data():
    try:
        res = requests.get(URL_GSHEET_API)
        data = res.json()
        
        # Ambil data dari Sheet Stock
        raw_stok = data.get("stok", [])
        stok_dict = {}
        if len(raw_stok) > 1:
            for row in raw_stok[1:]:
                if len(row) >= 2 and str(row[1]).isdigit():
                    stok_dict[row[0]] = int(row[1])
        
        # Ambil data dari Sheet riwayat / Audit Trail
        raw_riwayat = data.get("riwayat", [])
        riwayat_list = []
        if len(raw_riwayat) > 1:
            for row in raw_riwayat[1:]:
                if len(row) >= 4:
                    # Menyesuaikan kolom jika ada data lama
                    petugas = row[4] if len(row) >= 5 else "Sistem"
                    riwayat_list.append({
                        "Waktu": row[0], 
                        "Petugas": petugas,
                        "Tipe": row[1], 
                        "Barang": row[2], 
                        "Jumlah": row[3]
                    })
                    
        if not stok_dict:
            stok_dict = {
                "Microcement base": 16, "Ready to use": 15, "Mixed resin A": 12,
                "Ceramic microcement": 4, "Microrock": 17, "Primer ordinary": 7,
                "Epoxy primer": 3, "Self leveling white finish": 4, "Top coat A": 15,
                "Top coat B": 1, "Top coat C": 5, "Pewarna no 1": 3,
                "Pewarna no 2": 10, "Pewarna no 3": 0, "Pewarna no 4": 9, "Metal glaze wax": 0
            }
            
        return stok_dict, riwayat_list
    except Exception:
        return {
            "Microcement base": 16, "Ready to use": 15, "Mixed resin A": 12,
            "Ceramic microcement": 4, "Microrock": 17, "Primer ordinary": 7,
            "Epoxy primer": 3, "Self leveling white finish": 4, "Top coat A": 15,
            "Top coat B": 1, "Top coat C": 5, "Pewarna no 1": 3,
            "Pewarna no 2": 10, "Pewarna no 3": 0, "Pewarna no 4": 9, "Metal glaze wax": 0
        }, []

def save_data():
    payload = {
        "stok": [[k, v] for k, v in st.session_state.stok.items()],
        "riwayat": st.session_state.riwayat
    }
    try:
        requests.post(URL_GSHEET_API, json=payload)
    except Exception as e:
        st.error(f"Gagal menyimpan data: {e}")

# Inisialisasi Data
if "stok" not in st.session_state or "riwayat" not in st.session_state:
    st.session_state.stok, st.session_state.riwayat = load_data()

st.title("📦 Sistem Gudang Mikrosemen")

menu = st.sidebar.selectbox("Pilih Menu", [
    "📊 Lihat Semua Stok", 
    "📥 Restok Barang Masuk", 
    "📤 Pengiriman Barang Keluar", 
    "➕ Tambah Jenis Barang", 
    "🕵️ Audit Log / Activity Log",
    "⚙️ Reset & Backup Data"
])

def dapatkan_waktu_wib():
    waktu_wib = datetime.utcnow() + timedelta(hours=7)
    return waktu_wib.strftime("%d-%m-%Y %H:%M:%S")

# 1. LIHAT STOK
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
    kata_kunci = st.text_input("🔍 Cari Nama Barang...", "")
    
    data_tabel = []
    for barang, jumlah in st.session_state.stok.items():
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
        st.dataframe(df_stok[["Nama Barang", "Jumlah Stok (pcs)", "Status"]], use_container_width=True)
        
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
    barang = st.selectbox("Pilih Barang", list(st.session_state.stok.keys()))
    jumlah = st.number_input("Jumlah Masuk", min_value=1, step=1)
    
    if st.button("Simpan Barang Masuk"):
        waktu_sekarang = dapatkan_waktu_wib()
        st.session_state.stok[barang] += jumlah
        
        # Pencatatan Activity Log / Audit Trail
        st.session_state.riwayat.append({
            "Waktu": waktu_sekarang, 
            "Petugas": nama_petugas,
            "Tipe": "RESTOK MASUK", 
            "Barang": barang, 
            "Jumlah": f"+{jumlah} pcs"
        })
        save_data()
        st.success(f"Berhasil ditambahkan oleh {nama_petugas}: +{jumlah} pcs {barang}!")

# 3. BARANG KELUAR
elif menu == "📤 Pengiriman Barang Keluar":
    st.header("📤 Pengurangan Stok (Barang Keluar)")
    barang = st.selectbox("Pilih Barang", list(st.session_state.stok.keys()))
    jumlah = st.number_input("Jumlah Keluar", min_value=1, step=1)
    
    if st.button("Proses Pengiriman"):
        if jumlah <= st.session_state.stok[barang]:
            waktu_sekarang = dapatkan_waktu_wib()
            st.session_state.stok[barang] -= jumlah
            
            # Pencatatan Activity Log / Audit Trail
            st.session_state.riwayat.append({
                "Waktu": waktu_sekarang, 
                "Petugas": nama_petugas,
                "Tipe": "BARANG KELUAR", 
                "Barang": barang, 
                "Jumlah": f"-{jumlah} pcs"
            })
            save_data()
            st.success(f"Berhasil diproses oleh {nama_petugas}: -{jumlah} pcs {barang}!")
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
            
            # Pencatatan Activity Log / Audit Trail
            st.session_state.riwayat.append({
                "Waktu": waktu_sekarang, 
                "Petugas": nama_petugas,
                "Tipe": "ITEM BARU", 
                "Barang": nama_baru, 
                "Jumlah": f"{stok_awal} pcs"
            })
            save_data()
            st.success(f"{nama_baru} berhasil didaftarkan oleh {nama_petugas}!")

# 5. AUDIT LOG / ACTIVITY LOG
elif menu == "🕵️ Audit Log / Activity Log":
    st.header("🕵️ Catatan Aktivitas Pengguna (Audit Trail)")
    st.write("Melacak riwayat siapa yang melakukan perubahan data, kapan, dan jenis transaksinya.")
    
    if not st.session_state.riwayat:
        st.info("Belum ada catatan aktivitas pengguna.")
    else:
        df_log = pd.DataFrame(st.session_state.riwayat)
        
        # Filter berdasarkan Nama Petugas
        list_petugas = ["Semua Petugas"] + list(df_log["Petugas"].unique()) if "Petugas" in df_log.columns else ["Semua Petugas"]
        pilihan_filter = st.selectbox("🔍 Filter Berdasarkan Petugas:", list_petugas)
        
        if pilihan_filter != "Semua Petugas":
            df_log = df_log[df_log["Petugas"] == pilihan_filter]
            
        # Urutkan dari aktivitas paling terbaru
        st.dataframe(df_log.iloc[::-1], use_container_width=True)
        
        csv_log = df_log.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Audit Log (CSV/Excel)",
            data=csv_log,
            file_name=f"Audit_Log_Gudang_{dapatkan_waktu_wib()[:10]}.csv",
            mime="text/csv"
        )

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
        
