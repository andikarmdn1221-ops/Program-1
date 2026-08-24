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

# --- TOKEN & CHAT ID DIMASUKKAN LANGSUNG (DIJAMIN TERBACA) ---
TELEGRAM_BOT_TOKEN = "8810239918:AAGBfJH1gOUc4d4172bpqhaaoMYORiJUl0gw"
TELEGRAM_CHAT_ID = 2106196278

def kirim_notifikasi_telegram(pesan):
    """Mengirim pesan notifikasi otomatis ke Telegram Bot"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": int(TELEGRAM_CHAT_ID),
        "text": pesan,
    }
    try:
        response = requests.post(url, json=payload, timeout=5)
        print("Response Telegram:", response.text)
    except Exception as e:
        print(f"Gagal kirim notif Telegram: {e}")

def dapatkan_waktu_wib():
    return datetime.now(ZoneInfo("Asia/Jakarta")).strftime("%d-%m-%Y %H:%M")

@st.cache_data(ttl=60)
def fetch_data_from_gsheet(url):
    try:
        res = requests.get(url, timeout=8)
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
    st.error(f"⚠️ **PERHATIAN:** Ada {len(item_habis)} item habis.")
elif item_kritis:
    st.warning(f"🔔 **INFORMASI:** Ada {len(item_kritis)} item kritis.")

menu = st.sidebar.selectbox("Pilih Menu", [
    "📊 Lihat Semua Stok", "📥 Restok Barang Masuk", "📤 Pengiriman Barang Keluar", 
    "➕ Tambah Jenis Barang", "📜 Riwayat Transaksi", "📆 Laporan Mingguan", 
    "📅 Laporan Bulanan", "⚙️ Reset & Backup Data"
])

if menu == "📤 Pengiriman Barang Keluar":
    st.header("📤 Pengurangan Stok (Barang Keluar)")
    list_pilihan = sorted(st.session_state.stok.keys(), key=kunci_urut_nama)
    barang = st.selectbox("Pilih Barang", list_pilihan)
    stok_saat_ini = st.session_state.stok.get(barang, 0)
    
    st.caption(f"Sisa stok tersedia untuk {barang}: **{stok_saat_ini} pcs**")
    jumlah = st.number_input("Jumlah Keluar", min_value=1, max_value=max(1, stok_saat_ini), step=1)
    pembeli = st.text_input("👤 Nama Pembeli / Klien", placeholder="Misal: Pak Budi")
    
    if st.button("Proses Pengiriman"):
        if pembeli.strip() == "":
            st.warning("⚠️ Mohon isi nama pembeli!")
        elif stok_saat_ini == 0:
            st.error("❌ Barang habis!")
        elif jumlah <= stok_saat_ini:
            waktu_sekarang = dapatkan_waktu_wib()
            st.session_state.stok[barang] -= jumlah
            sisa_stok = st.session_state.stok[barang]
            
            st.session_state.riwayat.append({
                "Waktu": waktu_sekarang, "Tipe": "KELUAR", "Barang": barang, 
                "Jumlah": f"-{jumlah} pcs", "Pembeli / Keterangan": pembeli
            })
            save_data()
            
            if sisa_stok == 0:
                kirim_notifikasi_telegram(f"PERHATIAN: STOK HABIS!\n\nBarang: {barang}\nSisa: 0 pcs. Segera Restok!")
            elif sisa_stok < 5:
                kirim_notifikasi_telegram(f"PERHATIAN: STOK KRITIS!\n\nBarang: {barang}\nSisa: {sisa_stok} pcs. Harap re-order segera.")
                
            st.success("Pengiriman diproses dan notifikasi dikirim!")
        else:
            st.error("Stok tidak mencukupi!")
