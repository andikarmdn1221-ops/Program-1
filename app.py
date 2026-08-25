import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime, date
from zoneinfo import ZoneInfo
import re
import io
import threading
from PIL import Image

st.set_page_config(page_title="Microcement Warehouse", page_icon="📦", layout="wide")

URL_GSHEET_API = st.secrets.get("URL_GSHEET_API", "")
TELEGRAM_BOT_TOKEN = st.secrets.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = st.secrets.get("TELEGRAM_CHAT_ID", "")

# -----------------------------------------------------------------------------
# HELPER FUNCTIONS
# -----------------------------------------------------------------------------
def safe_int(val, default=0):
    try:
        if pd.isna(val) or val is None: return default
        v_str = str(val).strip()
        return int(float(v_str)) if v_str else default
    except:
        return default

def dapatkan_waktu_wib():
    return datetime.now(ZoneInfo("Asia/Jakarta")).strftime("%d %b %Y, %H:%M WIB")

def kirim_notifikasi_telegram(pesan):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID: return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": int(TELEGRAM_CHAT_ID), "text": pesan, "parse_mode": "Markdown"}, timeout=15)
    except:
        pass

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

# -----------------------------------------------------------------------------
# DATA ENGINE
# -----------------------------------------------------------------------------
def fetch_data_from_gsheet_direct(url):
    if not url: return None
    try:
        res = requests.get(url, timeout=15)
        res.raise_for_status()
        return res.json()
    except:
        return None

@st.cache_data(ttl=300)
def fetch_data_cached(url):
    return fetch_data_from_gsheet_direct(url)

def load_data(force_refresh=False):
    data = fetch_data_from_gsheet_direct(URL_GSHEET_API) if force_refresh else fetch_data_cached(URL_GSHEET_API)
    if data is None: return {}, [], False
    stok_dict = {row[0]: safe_int(row[1]) for row in data.get("stok", [])[1:] if len(row) >= 2}
    riwayat_list = [{"Waktu": r[0], "Tipe": r[1], "Barang": r[2], "Jumlah": safe_int(r[3]), "Pembeli / Keterangan": r[4] if len(r)>4 else "-"} for r in data.get("riwayat", [])[1:] if len(r)>=4]
    return stok_dict or STOK_DEFAULT.copy(), riwayat_list, True

def save_data_atomic(stok_terbaru, riwayat_terbaru):
    if not st.session_state.get("is_connected", False) or not URL_GSHEET_API: return False
    payload = {
        "stok": [["Nama Barang", "Jumlah Stok"]] + [[k, v] for k, v in stok_terbaru.items()],
        "riwayat": [["Waktu", "Tipe", "Barang", "Jumlah", "Pembeli / Keterangan"]] + [[i.get("Waktu",""), i.get("Tipe",""), i.get("Barang",""), i.get("Jumlah",""), i.get("Pembeli / Keterangan","-")] for i in riwayat_terbaru]
    }
    try:
        requests.post(URL_GSHEET_API, json=payload, timeout=45)
        st.cache_data.clear()
        return True
    except:
        return False

if "is_connected" not in st.session_state:
    s_load, r_load, is_conn = load_data()
    st.session_state.stok, st.session_state.riwayat, st.session_state.is_connected = s_load, r_load, is_conn

# -----------------------------------------------------------------------------
# CUSTOM CSS
# -----------------------------------------------------------------------------
st.markdown("""
    <style>
    [data-testid="stSidebar"] {
        background-color: #0F172A;
        border-right: 1px solid #1E293B;
    }
    [data-testid="stSidebar"] * {
        color: #94A3B8 !important;
    }
    div[data-testid="stMetric"] {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    div[data-testid="stMetricLabel"] p {
        font-size: 11px !important;
        font-weight: 700 !important;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    div[data-testid="stMetricValue"] div {
        font-size: 26px !important;
        font-weight: 800 !important;
        color: #0F172A;
    }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# SIDEBAR NAVIGATION (DIPERBAIKI MENJADI SATU RADIO UTAMA)
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 📦 **MICROCEMENT**")
    st.caption("WAREHOUSE MANAGEMENT")
    st.divider()
    
    active_menu = st.radio(
        "Navigasi Utama",
        [
            "📊 Dashboard",
            "📋 Lihat Semua Stok",
            "🔍 Pencarian Barang",
            "📥 Barang Masuk",
            "📤 Barang Keluar",
            "📜 Riwayat Transaksi",
            "📊 Laporan Stok",
            "🗓️ Laporan Periodik",
            "💾 Backup Data",
            "⚙️ Pengaturan & Reset",
            "ℹ️ Tentang Aplikasi"
        ],
        label_visibility="collapsed"
    )
    
    st.divider()
    st.info("🟢 **Notifikasi Telegram**\nAktif - Terhubung")

# -----------------------------------------------------------------------------
# HEADER UTAMA
# -----------------------------------------------------------------------------
col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.markdown(f"### **{active_menu}**")
with col_h2:
    st.markdown(f"<div style='text-align: right; font-size: 12px; color: #64748B;'>Terakhir diperbarui: {dapatkan_waktu_wib()}</div>", unsafe_allow_html=True)
    if st.button("🔄 Refresh Data", use_container_width=False):
        st.cache_data.clear()
        st.session_state.stok, st.session_state.riwayat, st.session_state.is_connected = load_data(force_refresh=True)
        st.rerun()

st.divider()

# -----------------------------------------------------------------------------
# KONTEN BERDASARKAN MENU YANG DIPILIH
# -----------------------------------------------------------------------------
item_habis = [b for b, q in st.session_state.stok.items() if q == 0]
item_kritis = [b for b, q in st.session_state.stok.items() if 0 < q < 5]
total_jenis = len(st.session_state.stok)
total_unit = sum(st.session_state.stok.values())

if active_menu == "📊 Dashboard":
    if item_habis or item_kritis:
        st.markdown(f"""
            <div style="background-color: #FEF2F2; border: 1px solid #FCA5A5; padding: 12px 16px; border-radius: 8px; color: #991B1B; font-weight: 500; margin-bottom: 20px;">
                ⚠️ <b>PERHATIAN:</b> {len(item_habis)} item stok habis, {len(item_kritis)} item stok kritis.
            </div>
        """, unsafe_allow_html=True)
        
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("TOTAL JENIS", f"{total_jenis}", "Jenis Barang")
    m2.metric("TOTAL STOK", f"{total_unit}", "Total PCS")
    m3.metric("STOK KRITIS", f"{len(item_kritis)}", "Stok < 5 pcs")
    m4.metric("STOK HABIS", f"{len(item_habis)}", "Stok = 0 pcs")
    
    st.write("")
    col_chart, col_kritis_table = st.columns([1.1, 1.1])
    
    with col_chart:
        st.markdown("#### **Status Stok**")
        jumlah_aman = total_jenis - len(item_habis) - len(item_kritis)
        df_donut = pd.DataFrame({
            "Status": ["Stok Aman", "Stok Kritis", "Stok Habis"],
            "Jumlah": [jumlah_aman, len(item_kritis), len(item_habis)]
        })
        fig_donut = px.pie(
            df_donut, names="Status", values="Jumlah", hole=0.6,
            color="Status",
            color_discrete_map={"Stok Aman": "#22c55e", "Stok Kritis": "#eab308", "Stok Habis": "#ef4444"}
        )
        fig_donut.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=250, showlegend=True)
        st.plotly_chart(fig_donut, use_container_width=True)
        st.success("✅ Stok aman mencukupi. Pertahankan ketersediaan barang.")
        
    with col_kritis_table:
        st.markdown("#### **Stok Kritis & Habis**")
        data_kritis_habis = [{"Nama Barang": b, "Sisa Stok": f"{q} pcs", "Status": "HABIS" if q==0 else "KRITIS"} for b, q in st.session_state.stok.items() if q < 5]
        if data_kritis_habis:
            st.dataframe(pd.DataFrame(data_kritis_habis), use_container_width=True, hide_index=True)
        else:
            st.info("Tidak ada barang dalam status kritis atau habis.")

    st.divider()
    st.markdown("#### **Ringkasan Semua Stok**")
    data_tabel = [{"Nama Barang": b, "Sisa Stok": f"{q} pcs", "Indikator Stok": q, "Status": "HABIS" if q==0 else ("KRITIS" if q<5 else "AMAN")} for b, q in sorted(st.session_state.stok.items(), key=lambda x: kunci_urut_nama(x[0]))]
    if data_tabel:
        max_stok = max(st.session_state.stok.values()) if st.session_state.stok else 30
        st.dataframe(pd.DataFrame(data_tabel), column_config={"Indikator Stok": st.column_config.ProgressColumn("Indikator Stok", min_value=0, max_value=max(max_stok, 20), format="%d")}, hide_index=True, use_container_width=True)

elif active_menu in ["📋 Lihat Semua Stok", "📊 Laporan Stok"]:
    st.markdown("#### **Daftar Keseluruhan Stok Gudang**")
    data_all = [{"Nama Barang": k, "Jumlah Stok": f"{v} pcs", "Status": "HABIS" if v==0 else ("KRITIS" if v<5 else "AMAN")} for k, v in sorted(st.session_state.stok.items(), key=lambda x: kunci_urut_nama(x[0]))]
    df_all = pd.DataFrame(data_all)
    st.dataframe(df_all, use_container_width=True, hide_index=True)
    
    # Tombol Ekspor Excel
    excel_bytes = io.BytesIO()
    with pd.ExcelWriter(excel_bytes, engine='openpyxl') as writer:
        df_all.to_excel(writer, index=False, sheet_name="Stok Gudang")
    st.download_button("📥 Ekspor Data Stok ke Excel", excel_bytes.getvalue(), f"Stok_Gudang_{datetime.now().strftime('%Y%m%d')}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

elif active_menu == "🔍 Pencarian Barang":
    st.markdown("#### **Pencarian Spesifik Inventaris**")
    keyword = st.text_input("Ketik nama barang yang ingin dicari...")
    if keyword:
         hasil = [{"Nama Barang": k, "Jumlah Stok": f"{v} pcs", "Status": "HABIS" if v==0 else ("KRITIS" if v<5 else "AMAN")} for k, v in st.session_state.stok.items() if keyword.lower() in k.lower()]
         if hasil:
             st.dataframe(pd.DataFrame(hasil), use_container_width=True, hide_index=True)
         else:
             st.warning("Barang tidak ditemukan.")

elif active_menu == "📥 Barang Masuk":
    st.markdown("#### **Form Masuk Barang (Inbound)**")
    with st.form("f_masuk", clear_on_submit=True):
        b_pilih = st.selectbox("Pilih Barang", sorted(st.session_state.stok.keys(), key=kunci_urut_nama))
        jml = st.number_input("Jumlah Masuk (pcs)", min_value=1, value=1)
        ket = st.text_input("Keterangan / Supplier", "-")
        if st.form_submit_button("Simpan Barang Masuk"):
            st.session_state.stok[b_pilih] += jml
            st.session_state.riwayat.insert(0, {"Waktu": dapatkan_waktu_wib(), "Tipe": "MASUK", "Barang": b_pilih, "Jumlah": jml, "Pembeli / Keterangan": ket})
            if save_data_atomic(st.session_state.stok, st.session_state.riwayat):
                st.success(f"Berhasil menambahkan stok {b_pilih} sebanyak +{jml} pcs!")
                kirim_notifikasi_telegram(f"📥 **BARANG MASUK**\n📦 {b_pilih}\n➕ +{jml} pcs\n📝 {ket}")
                st.rerun()

elif active_menu == "📤 Barang Keluar":
    st.markdown("#### **Form Keluar Barang (Outbound)**")
    with st.form("f_keluar", clear_on_submit=True):
        b_pilih = st.selectbox("Pilih Barang", sorted(st.session_state.stok.keys(), key=kunci_urut_nama))
        stok_kini = st.session_state.stok.get(b_pilih, 0)
        st.info(f"Stok saat ini untuk **{b_pilih}**: {stok_kini} pcs")
        jml = st.number_input("Jumlah Keluar (pcs)", min_value=1, value=1)
        pembeli = st.text_input("Nama Pembeli / Proyek", "")
        if st.form_submit_button("Simpan Barang Keluar"):
            if jml > stok_kini:
                st.error("❌ Stok tidak mencukupi!")
            elif not pembeli.strip():
                st.warning("⚠️ Mohon isi Nama Pembeli / Proyek.")
            else:
                st.session_state.stok[b_pilih] -= jml
                st.session_state.riwayat.insert(0, {"Waktu": dapatkan_waktu_wib(), "Tipe": "KELUAR", "Barang": b_pilih, "Jumlah": jml, "Pembeli / Keterangan": pembeli})
                if save_data_atomic(st.session_state.stok, st.session_state.riwayat):
                    st.success(f"Berhasil mencatat pengeluaran {b_pilih} sebanyak -{jml} pcs!")
                    kirim_notifikasi_telegram(f"📤 **BARANG KELUAR**\n📦 {b_pilih}\n➖ -{jml} pcs\n👤 {pembeli}")
                    st.rerun()

elif active_menu == "📜 Riwayat Transaksi":
    st.markdown("#### **Log Riwayat Transaksi Gudang**")
    if st.session_state.riwayat:
        df_riw = pd.DataFrame(st.session_state.riwayat)
        st.dataframe(df_riw, use_container_width=True, hide_index=True)
        
        # Ekspor Riwayat Excel
        excel_riw = io.BytesIO()
        with pd.ExcelWriter(excel_riw, engine='openpyxl') as writer:
            df_riw.to_excel(writer, index=False, sheet_name="Riwayat Transaksi")
        st.download_button("📥 Ekspor Riwayat ke Excel", excel_riw.getvalue(), f"Riwayat_{datetime.now().strftime('%Y%m%d')}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    else:
        st.info("Belum ada riwayat transaksi tercatat.")

elif active_menu == "🗓️ Laporan Periodik":
    st.markdown("#### **Laporan Transaksi Berdasarkan Rentang Tanggal**")
    c1, c2 = st.columns(2)
    with c1:
        tgl_mulai = st.date_input("Tanggal Mulai", date.today().replace(day=1))
    with c2:
        tgl_selesai = st.date_input("Tanggal Selesai", date.today())
        
    if st.button("Tampilkan Laporan Periodik"):
        st.success(f"Menampilkan laporan dari tanggal {tgl_mulai} sampai {tgl_selesai}")
        if st.session_state.riwayat:
            st.dataframe(pd.DataFrame(st.session_state.riwayat), use_container_width=True, hide_index=True)
        else:
            st.info("Tidak ada data pada periode tersebut.")

elif active_menu == "💾 Backup Data":
    st.markdown("#### **Backup Data Gudang (Excel)**")
    st.info("Unduh salinan lengkap database stok dan riwayat transaksi ke perangkat Anda.")
    
    output_backup = io.BytesIO()
    df_stok_b = pd.DataFrame(list(st.session_state.stok.items()), columns=["Nama Barang", "Jumlah Stok"])
    df_riw_b = pd.DataFrame(st.session_state.riwayat) if st.session_state.riwayat else pd.DataFrame(columns=["Waktu", "Tipe", "Barang", "Jumlah", "Pembeli / Keterangan"])
    
    with pd.ExcelWriter(output_backup, engine='openpyxl') as writer:
        df_stok_b.to_excel(writer, index=False, sheet_name="Stok Barang")
        df_riw_b.to_excel(writer, index=False, sheet_name="Riwayat Transaksi")
        
    st.download_button(
        "💾 Unduh File Backup Lengkap",
        data=output_backup.getvalue(),
        file_name=f"Backup_Gudang_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

elif active_menu == "⚙️ Pengaturan & Reset":
    st.markdown("#### **Pengaturan Sistem & Reset Data**")
    st.warning("⚠️ Perhatian: Fitur ini digunakan untuk mengembalikan sistem ke pengaturan awal (Factory Reset).")
    
    konfirmasi = st.text_input("Ketik `RESET` untuk mengaktifkan tombol reset:")
    if st.button("🚨 Reset Data Gudang ke Default", disabled=(konfirmasi != "RESET")):
        st.session_state.stok = STOK_DEFAULT.copy()
        st.session_state.riwayat = []
        if save_data_atomic(st.session_state.stok, st.session_state.riwayat):
            st.success("✅ Data berhasil di-reset ke pengaturan awal!")
            st.rerun()

elif active_menu == "ℹ️ Tentang Aplikasi":
    st.markdown("#### **Tentang Sistem Manajemen Gudang**")
    st.markdown("""
    * **Nama Aplikasi:** Microcement Warehouse Management System (WMS)
    * **Versi:** 2.5 (Cloud Integrated)
    * **Database:** Google Sheets API
    * **Notifikasi:** Telegram Bot Integration
    """)
