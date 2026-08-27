import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime, date
from zoneinfo import ZoneInfo
import re
import io
import threading
from fpdf import FPDF
from PIL import Image

st.set_page_config(page_title="Microcement Warehouse", page_icon="📦", layout="wide")

URL_GSHEET_API = st.secrets.get("URL_GSHEET_API", "")
TELEGRAM_BOT_TOKEN = st.secrets.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = st.secrets.get("TELEGRAM_CHAT_ID", "")

# -----------------------------------------------------------------------------
# CENTRALIZED ERROR HANDLING & HELPER FUNCTIONS
# -----------------------------------------------------------------------------
def safe_api_call(func, *args, default_return=None, error_message="Terjadi kesalahan sistem.", **kwargs):
    try:
        return func(*args, **kwargs)
    except requests.exceptions.Timeout:
        st.error(f"{error_message} (Koneksi Timeout / Waktu Habis)")
        return default_return
    except requests.exceptions.RequestException as e:
        st.error(f"{error_message} (Masalah Jaringan: {e})")
        return default_return
    except Exception as e:
        st.error(f"{error_message} (Detail: {e})")
        return default_return

def safe_int(val, default=0):
    try:
        if pd.isna(val) or val is None: return default
        v_str = str(val).strip()
        return int(float(v_str)) if v_str else default
    except:
        return default

def dapatkan_waktu_wib():
    return datetime.now(ZoneInfo("Asia/Jakarta")).strftime("%d %b %Y, %H:%M WIB")

def kompres_gambar(file_uploaded, max_size=(600, 600), quality=70):
    if file_uploaded is None: return None
    def _process():
        file_uploaded.seek(0)
        img = Image.open(file_uploaded)
        if img.mode in ("RGBA", "P"): img = img.convert("RGB")
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=quality, optimize=True)
        return buffer.getvalue()
    return safe_api_call(_process, default_return=file_uploaded.getvalue(), error_message="Gagal kompres gambar")

def _request_telegram(url, payload=None, files=None, timeout=15):
    if files:
        return requests.post(url, data=payload, files=files, timeout=timeout)
    else:
        return requests.post(url, json=payload, timeout=timeout)

def kirim_notifikasi_telegram(pesan, foto_bytes=None):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID: return
    try:
        if foto_bytes:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
            safe_api_call(_request_telegram, url, payload={"chat_id": int(TELEGRAM_CHAT_ID), "caption": pesan}, files={"photo": ("bukti.jpg", foto_bytes, "image/jpeg")}, timeout=15)
        else:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            safe_api_call(_request_telegram, url, payload={"chat_id": int(TELEGRAM_CHAT_ID), "text": pesan, "parse_mode": "Markdown"}, timeout=15)
    except:
        pass

def kirim_dokumen_telegram(pesan, file_bytes, file_name):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID: return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
    res = safe_api_call(_request_telegram, url, payload={"chat_id": int(TELEGRAM_CHAT_ID), "caption": pesan}, files={"document": (file_name, file_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}, timeout=30)
    return res is not None and res.status_code == 200

def buat_excel_bytes(df, sheet_name="Data"):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    return output.getvalue()

def buat_excel_backup_lengkap(stok_dict, master_info, riwayat_list):
    output = io.BytesIO()
    data_stok = []
    for k, v in stok_dict.items():
        st_info = master_info.get(k, {})
        data_stok.append([k, v, st_info.get("status", "Aktif"), st_info.get("min_stok", 5)])
    
    df_stok = pd.DataFrame(data_stok, columns=["Nama Barang", "Jumlah Stok", "Status", "Batas Minimum"])
    df_riwayat = pd.DataFrame(riwayat_list) if riwayat_list else pd.DataFrame(columns=["Waktu", "Tipe", "Barang", "Jumlah", "Pembeli / Keterangan"])
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_stok.to_excel(writer, index=False, sheet_name="Stok Barang")
        df_riwayat.to_excel(writer, index=False, sheet_name="Riwayat Transaksi")
    return output.getvalue()

def bersihkan_teks_pdf(teks):
    return str(teks).strip().encode('latin-1', 'replace').decode('latin-1')

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
            pdf.cell(col_widths[i], 7, bersihkan_teks_pdf(val), border=1, align="C" if i in [0, 1, 3] else "L")
        pdf.ln()
    return bytes(pdf.output())

def filter_riwayat_berdasarkan_rentang(riwayat_list, tgl_mulai, tgl_selesai):
    if not riwayat_list: return []
    dt_mulai = datetime.combine(tgl_mulai, datetime.min.time())
    dt_selesai = datetime.combine(tgl_selesai, datetime.max.time())
    hasil = []
    for item in riwayat_list:
        waktu_str = str(item.get("Waktu", ""))
        try:
            tgl = datetime.strptime(waktu_str[:16], "%d-%m-%Y %H:%M")
        except:
            try:
                tgl = datetime.fromisoformat(waktu_str.replace('Z', '+00:00')).replace(tzinfo=None)
            except:
                continue
        if dt_mulai <= tgl <= dt_selesai:
            item_formatted = item.copy()
            item_formatted["Waktu"] = tgl.strftime("%d-%m-%Y %H:%M")
            hasil.append(item_formatted)
    return hasil

STOK_DEFAULT = {
    "Microcement base": 16, "Ready to use": 15, "Mixed resin A": 12,
    "Ceramic microcement": 4, "Microrock": 17, "Primer ordinary": 7,
    "Epoxy primer": 3, "Self leveling white finish": 4, "Top coat A": 15,
    "Top coat B": 1, "Top coat C": 5, "Pewarna no 1": 3,
    "Pewarna no 2": 10, "Pewarna no 3": 0, "Pewarna no 4": 9, 
    "Metal glaze wax": 0, "Metallic glaze wax": 0
}

MASTER_DEFAULT = {k: {"status": "Aktif", "min_stok": 5} for k in STOK_DEFAULT}

def kunci_urut_nama(nama):
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', nama)]

# -----------------------------------------------------------------------------
# DATA ENGINE (MULTI-USER SAFE, ANTI-SPAM, & KOREKSI)
# -----------------------------------------------------------------------------
def fetch_data_from_gsheet_direct(url):
    if not url: return None
    def _get():
        res = requests.get(url, timeout=15)
        res.raise_for_status()
        return res.json()
    return safe_api_call(_get, default_return=None, error_message="Gagal mengambil data dari Google Sheets.")

def parse_server_data(server_data):
    server_stok = {}
    server_master = {}
    for row in server_data.get("stok", [])[1:]:
        if len(row) >= 2:
            nama = row[0]
            server_stok[nama] = safe_int(row[1])
            status = row[2] if len(row) >= 3 else "Aktif"
            min_stok = safe_int(row[3], 5) if len(row) >= 4 else 5
            server_master[nama] = {"status": status, "min_stok": min_stok}
            
    server_riwayat = [{"Waktu": r[0], "Tipe": r[1], "Barang": r[2], "Jumlah": safe_int(r[3]), "Pembeli / Keterangan": r[4] if len(r)>4 else "-"} for r in server_data.get("riwayat", [])[1:] if len(r)>=4]
    
    if not server_stok:
        server_stok = STOK_DEFAULT.copy()
        server_master = MASTER_DEFAULT.copy()
        
    return server_stok, server_master, server_riwayat

def payload_generator(server_stok, server_master, server_riwayat):
    return {
        "stok": [["Nama Barang", "Jumlah Stok", "Status", "Batas Minimum"]] + [[k, v, server_master.get(k, {}).get("status", "Aktif"), server_master.get(k, {}).get("min_stok", 5)] for k, v in server_stok.items()],
        "riwayat": [["Waktu", "Tipe", "Barang", "Jumlah", "Pembeli / Keterangan"]] + [[i.get("Waktu",""), i.get("Tipe",""), i.get("Barang",""), i.get("Jumlah",""), i.get("Pembeli / Keterangan","-")] for i in server_riwayat]
    }

def load_data(force_refresh=False):
    if force_refresh:
        data = fetch_data_from_gsheet_direct(URL_GSHEET_API)
    else:
        @st.cache_data(ttl=300)
        def _cached(u):
            return fetch_data_from_gsheet_direct(u)
        data = _cached(URL_GSHEET_API)

    if data is None: return {}, {}, [], False
    s_stok, s_master, s_riwayat = parse_server_data(data)
    return s_stok, s_master, s_riwayat, True

def cek_dan_kirim_stok_kritis(stok_dict, master_info):
    # Hanya cek barang yang statusnya "Aktif"
    habis = frozenset([b for b, q in stok_dict.items() if q == 0 and master_info.get(b, {}).get("status", "Aktif") == "Aktif"])
    kritis = frozenset([b for b, q in stok_dict.items() if 0 < q <= master_info.get(b, {}).get("min_stok", 5) and master_info.get(b, {}).get("status", "Aktif") == "Aktif"])
    
    if "notif_terkirim_habis" not in st.session_state:
        st.session_state.notif_terkirim_habis = frozenset()
    if "notif_terkirim_kritis" not in st.session_state:
        st.session_state.notif_terkirim_kritis = frozenset()

    item_habis_baru = habis - st.session_state.notif_terkirim_habis
    item_kritis_baru = kritis - st.session_state.notif_terkirim_kritis

    if item_habis_baru or item_kritis_baru:
        pesan_auto = f"🚨 **LAPORAN OTOMATIS: STOK KRITIS & HABIS**\n📅 {dapatkan_waktu_wib()}\n\n"
        if habis:
            pesan_auto += "🔴 *Stok Habis (0 pcs)*:\n" + "".join([f"• {b}\n" for b in habis]) + "\n"
        if kritis:
            pesan_auto += "🟡 *Stok Kritis / Mendekati Batas*:\n" + "".join([f"• {b}: {stok_dict[b]} pcs (Min: {master_info.get(b, {}).get('min_stok', 5)})\n" for b in kritis])
        
        threading.Thread(target=kirim_notifikasi_telegram, args=(pesan_auto,)).start()
        
        st.session_state.notif_terkirim_habis = habis
        st.session_state.notif_terkirim_kritis = kritis

def save_data_atomic(tipe_transaksi, barang, jumlah, keterangan_atau_pembeli):
    if not st.session_state.get("is_connected", False) or not URL_GSHEET_API: 
        st.error("Koneksi database terputus.")
        return False
    
    def _process_save():
        res_fresh = requests.get(URL_GSHEET_API, timeout=15)
        res_fresh.raise_for_status()
        server_data = res_fresh.json()
        
        server_stok, server_master, server_riwayat = parse_server_data(server_data)

        waktu_sekarang = dapatkan_waktu_wib()
        if tipe_transaksi == "KELUAR":
            stok_terkini = server_stok.get(barang, 0)
            if jumlah > stok_terkini:
                st.error(f"Gagal! Stok `{barang}` sisa {stok_terkini} pcs (telah berubah karena transaksi pengguna lain). Silakan refresh.")
                return False
            server_stok[barang] -= jumlah
        elif tipe_transaksi == "MASUK":
            server_stok[barang] = server_stok.get(barang, 0) + jumlah
        elif tipe_transaksi == "BARANG BARU":
            server_stok[barang] = jumlah
            server_master[barang] = {"status": "Aktif", "min_stok": 5}

        server_riwayat.insert(0, {
            "Waktu": waktu_sekarang, 
            "Tipe": tipe_transaksi, 
            "Barang": barang, 
            "Jumlah": jumlah, 
            "Pembeli / Keterangan": keterangan_atau_pembeli
        })

        payload = payload_generator(server_stok, server_master, server_riwayat)
        res_post = requests.post(URL_GSHEET_API, json=payload, timeout=45)
        res_post.raise_for_status()
        
        st.session_state.stok = server_stok
        st.session_state.master_info = server_master
        st.session_state.riwayat = server_riwayat
        st.cache_data.clear()
        
        st.session_state.notif_terkirim_habis = frozenset()
        st.session_state.notif_terkirim_kritis = frozenset()
        cek_dan_kirim_stok_kritis(server_stok, server_master)
        return True

    return safe_api_call(_process_save, default_return=False, error_message="Gagal menyimpan data ke database server.")

def update_master_item_atomic(old_nama, new_nama, new_status, new_min, is_delete=False):
    if not st.session_state.get("is_connected", False) or not URL_GSHEET_API:
        st.error("Koneksi database terputus.")
        return False
        
    def _process_update():
        res_fresh = requests.get(URL_GSHEET_API, timeout=15)
        res_fresh.raise_for_status()
        server_data = res_fresh.json()
        
        server_stok, server_master, server_riwayat = parse_server_data(server_data)
        
        if old_nama not in server_stok:
            st.error("Gagal: Barang tidak ditemukan di server (Mungkin sudah dihapus orang lain).")
            return False

        if is_delete:
            del server_stok[old_nama]
            if old_nama in server_master: del server_master[old_nama]
            # Hapus dari riwayat (opsional, tapi disarankan jika dihapus permanen agar rapi)
            server_riwayat = [tx for tx in server_riwayat if tx['Barang'] != old_nama]
        else:
            if old_nama != new_nama:
                if new_nama in server_stok:
                    st.error("Gagal: Nama barang baru sudah digunakan!")
                    return False
                # Ganti kunci dict
                server_stok[new_nama] = server_stok.pop(old_nama)
                server_master[new_nama] = server_master.pop(old_nama, {})
                # Ubah nama di seluruh riwayat transaksi
                for tx in server_riwayat:
                    if tx['Barang'] == old_nama:
                        tx['Barang'] = new_nama
            
            # Update properti
            server_master[new_nama]["status"] = new_status
            server_master[new_nama]["min_stok"] = new_min

        payload = payload_generator(server_stok, server_master, server_riwayat)
        res_post = requests.post(URL_GSHEET_API, json=payload, timeout=45)
        res_post.raise_for_status()
        
        st.session_state.stok = server_stok
        st.session_state.master_info = server_master
        st.session_state.riwayat = server_riwayat
        st.cache_data.clear()
        
        st.session_state.notif_terkirim_habis = frozenset()
        st.session_state.notif_terkirim_kritis = frozenset()
        cek_dan_kirim_stok_kritis(server_stok, server_master)
        return True

    return safe_api_call(_process_update, default_return=False, error_message="Gagal memodifikasi master item di server.")

def koreksi_transaksi_atomic(old_tx, new_tx, is_delete=False):
    if not st.session_state.get("is_connected", False) or not URL_GSHEET_API:
        st.error("Koneksi database terputus.")
        return False

    def _process_koreksi():
        res_fresh = requests.get(URL_GSHEET_API, timeout=15)
        res_fresh.raise_for_status()
        server_data = res_fresh.json()

        server_stok, server_master, server_riwayat = parse_server_data(server_data)

        # Cari Index transaksi
        idx_found = -1
        for i, tx in enumerate(server_riwayat):
            if (tx['Waktu'] == old_tx['Waktu'] and tx['Tipe'] == old_tx['Tipe'] and
                tx['Barang'] == old_tx['Barang'] and tx['Jumlah'] == old_tx['Jumlah'] and
                tx['Pembeli / Keterangan'] == old_tx['Pembeli / Keterangan']):
                idx_found = i
                break

        if idx_found == -1:
            st.error("Transaksi asli tidak ditemukan di server.")
            return False

        # Reverse transaksi lama
        if old_tx['Tipe'] == 'MASUK':
            server_stok[old_tx['Barang']] -= old_tx['Jumlah']
        elif old_tx['Tipe'] == 'KELUAR':
            server_stok[old_tx['Barang']] += old_tx['Jumlah']
        elif old_tx['Tipe'] == 'BARANG BARU':
            server_stok[old_tx['Barang']] -= old_tx['Jumlah']

        if is_delete:
            server_riwayat.pop(idx_found)
        else:
            # Apply transaksi baru
            if new_tx['Tipe'] == 'MASUK':
                server_stok[new_tx['Barang']] = server_stok.get(new_tx['Barang'], 0) + new_tx['Jumlah']
            elif new_tx['Tipe'] == 'KELUAR':
                if server_stok.get(new_tx['Barang'], 0) < new_tx['Jumlah']:
                    st.error(f"Koreksi gagal! Sisa stok `{new_tx['Barang']}` tidak mencukupi.")
                    return False
                server_stok[new_tx['Barang']] -= new_tx['Jumlah']
            elif new_tx['Tipe'] == 'BARANG BARU':
                server_stok[new_tx['Barang']] = server_stok.get(new_tx['Barang'], 0) + new_tx['Jumlah']

            server_riwayat[idx_found] = new_tx

        # Validasi stok minus
        for k, v in server_stok.items():
            if v < 0:
                st.error(f"Koreksi gagal! Stok `{k}` akan menjadi minus ({v} pcs).")
                return False

        payload = payload_generator(server_stok, server_master, server_riwayat)
        res_post = requests.post(URL_GSHEET_API, json=payload, timeout=45)
        res_post.raise_for_status()

        st.session_state.stok = server_stok
        st.session_state.master_info = server_master
        st.session_state.riwayat = server_riwayat
        st.cache_data.clear()
        
        st.session_state.notif_terkirim_habis = frozenset()
        st.session_state.notif_terkirim_kritis = frozenset()
        cek_dan_kirim_stok_kritis(server_stok, server_master)
        return True

    return safe_api_call(_process_koreksi, default_return=False, error_message="Gagal menyimpan koreksi ke server.")


if "is_connected" not in st.session_state or "master_info" not in st.session_state:
    s_stok, s_master, s_riwayat, is_conn = load_data(force_refresh=True)
    st.session_state.stok = s_stok
    st.session_state.master_info = s_master
    st.session_state.riwayat = s_riwayat
    st.session_state.is_connected = is_conn
    cek_dan_kirim_stok_kritis(s_stok, s_master)

# -----------------------------------------------------------------------------
# SIDEBAR NAVIGATION
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 📦 WMS Microcement")
    st.markdown("---")
    
    m_utama = st.radio("MENU UTAMA", ["🏠 Dashboard", "📋 Lihat Semua Stok", "➕ Kelola Master Item"])
    st.markdown("---")
    m_transaksi = st.radio("TRANSAKSI", ["📥 Barang Masuk", "📤 Barang Keluar", "✏️ Koreksi Transaksi"])
    st.markdown("---")
    m_laporan = st.radio("LAPORAN", ["📊 Riwayat Transaksi", "📈 Laporan Periodik"])
    st.markdown("---")
    m_sistem = st.radio("SISTEM", ["💾 Backup Data", "⚙️ Pengaturan & Reset", "ℹ️ Tentang Aplikasi"])
    
    st.markdown("---")
    st.info("🟢 Notifikasi Telegram: Aktif")

if "prev_utama" not in st.session_state: st.session_state.prev_utama = m_utama
if "prev_transaksi" not in st.session_state: st.session_state.prev_transaksi = m_transaksi
if "prev_laporan" not in st.session_state: st.session_state.prev_laporan = m_laporan
if "prev_sistem" not in st.session_state: st.session_state.prev_sistem = m_sistem
if "active_tab" not in st.session_state: st.session_state.active_tab = "🏠 Dashboard"

if m_utama != st.session_state.prev_utama:
    st.session_state.active_tab = m_utama
    st.session_state.prev_utama = m_utama
elif m_transaksi != st.session_state.prev_transaksi:
    st.session_state.active_tab = m_transaksi
    st.session_state.prev_transaksi = m_transaksi
elif m_laporan != st.session_state.prev_laporan:
    st.session_state.active_tab = m_laporan
    st.session_state.prev_laporan = m_laporan
elif m_sistem != st.session_state.prev_sistem:
    st.session_state.active_tab = m_sistem
    st.session_state.prev_sistem = m_sistem

active_menu_raw = st.session_state.active_tab
active_menu = active_menu_raw.split(" ", 1)[1] if " " in active_menu_raw else active_menu_raw

# -----------------------------------------------------------------------------
# HEADER & KONTROL UTAMA
# -----------------------------------------------------------------------------
col_h1, col_h2, col_h3 = st.columns([3, 1.5, 1])
with col_h1:
    st.title(f"📦 {active_menu}")
with col_h2:
    st.markdown(f"<div style='text-align: right; font-size:12px; color:gray;'>Waktu: {dapatkan_waktu_wib()}</div>", unsafe_allow_html=True)
with col_h3:
    if st.button("🔄 Refresh"):
        st.cache_data.clear()
        s_stok, s_master, s_riwayat, is_conn_fresh = load_data(force_refresh=True)
        st.session_state.stok = s_stok
        st.session_state.master_info = s_master
        st.session_state.riwayat = s_riwayat
        st.session_state.is_connected = is_conn_fresh
        st.session_state.notif_terkirim_habis = frozenset()
        st.session_state.notif_terkirim_kritis = frozenset()
        cek_dan_kirim_stok_kritis(s_stok, s_master)
        st.rerun()

st.markdown("---")

if not st.session_state.is_connected:
    st.error("🚨 KONEKSI DATABASE TERPUTUS! Periksa koneksi internet / URL Google Sheets Anda.")

# Statistik global (hanya menghitung yang Aktif)
item_aktif = {k: v for k, v in st.session_state.stok.items() if st.session_state.master_info.get(k, {}).get("status", "Aktif") == "Aktif"}
item_habis = [b for b, q in item_aktif.items() if q == 0]
item_kritis = [b for b, q in item_aktif.items() if 0 < q <= st.session_state.master_info.get(b, {}).get("min_stok", 5)]
total_jenis = len(item_aktif)
total_unit = sum(item_aktif.values())

# -----------------------------------------------------------------------------
# ROUTING HALAMAN
# -----------------------------------------------------------------------------
if active_menu == "Dashboard":
    if item_habis or item_kritis:
        st.warning(f"⚠️ **PERHATIAN:** {len(item_habis)} item stok habis, {len(item_kritis)} item stok mendekati batas minimum.")
        
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Jenis (Aktif)", f"{total_jenis}")
    m2.metric("Total Keseluruhan Stok", f"{total_unit} pcs")
    m3.metric("Stok Kritis/Limit", f"{len(item_kritis)}")
    m4.metric("Stok Habis (0)", f"{len(item_habis)}")
    
    st.markdown("---")
    col_chart, col_kritis_table = st.columns([1, 1])
    
    with col_chart:
        st.subheader("📊 Status Stok Aktif")
        jumlah_aman = total_jenis - len(item_habis) - len(item_kritis)
        df_donut = pd.DataFrame({
            "Status": ["Stok Aman", "Stok Kritis", "Stok Habis"],
            "Jumlah": [jumlah_aman, len(item_kritis), len(item_habis)]
        })
        fig_donut = px.pie(df_donut, names="Status", values="Jumlah", hole=0.5, color="Status",
                           color_discrete_map={"Stok Aman": "#2ecc71", "Stok Kritis": "#f1c40f", "Stok Habis": "#e74c3c"})
        st.plotly_chart(fig_donut, use_container_width=True)
        
    with col_kritis_table:
        st.subheader("🚨 Stok Kritis & Habis")
        data_kritis_habis = []
        for b, q in item_aktif.items():
            batas = st.session_state.master_info.get(b, {}).get("min_stok", 5)
            if q <= batas:
                data_kritis_habis.append({"Nama Barang": b, "Sisa Stok": f"{q} pcs", "Batas": f"{batas}", "Status": "HABIS" if q == 0 else "KRITIS"})
        if data_kritis_habis:
            st.dataframe(pd.DataFrame(data_kritis_habis), use_container_width=True, hide_index=True)
        else:
            st.success("Semua stok dalam kondisi aman!")

    st.markdown("---")
    st.subheader("📋 Ringkasan Semua Stok (Aktif & Nonaktif)")
    keyword = st.text_input("🔍 Cari nama barang...", "")
    
    data_tabel = []
    for barang in sorted(st.session_state.stok.keys(), key=kunci_urut_nama):
        jumlah = st.session_state.stok[barang]
        info = st.session_state.master_info.get(barang, {})
        batas = info.get("min_stok", 5)
        status_aktif = info.get("status", "Aktif")
        
        status_stok = "NONAKTIF" if status_aktif == "Nonaktif" else ("HABIS" if jumlah == 0 else ("KRITIS" if jumlah <= batas else "AMAN"))
        if keyword.lower() in barang.lower():
            data_tabel.append({"Nama Barang": barang, "Stok": f"{jumlah} pcs", "Batas Min": batas, "Status Item": status_aktif, "Status Stok": status_stok})
            
    if data_tabel:
        st.dataframe(pd.DataFrame(data_tabel), use_container_width=True, hide_index=True)

elif active_menu == "Lihat Semua Stok":
    st.subheader("Daftar Keseluruhan Stok Gudang")
    data_all = []
    for k, v in sorted(st.session_state.stok.items(), key=lambda x: kunci_urut_nama(x[0])):
        info = st.session_state.master_info.get(k, {})
        batas = info.get("min_stok", 5)
        status_aktif = info.get("status", "Aktif")
        status_stok = "NONAKTIF" if status_aktif == "Nonaktif" else ("HABIS" if v == 0 else ("KRITIS" if v <= batas else "AMAN"))
        data_all.append({"Nama Barang": k, "Jumlah Stok": f"{v} pcs", "Batas Min": batas, "Status Item": status_aktif, "Indikator": status_stok})
        
    df_all = pd.DataFrame(data_all)
    st.dataframe(df_all, use_container_width=True, hide_index=True)
    
    c_ex1, c_ex2 = st.columns(2)
    with c_ex1:
        st.download_button("📥 Ekspor Excel", buat_excel_bytes(df_all, "Stok"), f"Stok_{datetime.now().strftime('%Y%m%d')}.xlsx", use_container_width=True)
    with c_ex2:
        pdf_bytes = buat_pdf_tabel("LAPORAN STOK GUDANG", ["No", "Nama Barang", "Jumlah", "Min", "Status", "Indikator"], [[str(i+1), r["Nama Barang"], r["Jumlah Stok"], str(r["Batas Min"]), r["Status Item"], r["Indikator"]] for i, r in enumerate(data_all)], [10, 80, 25, 20, 25, 30])
        st.download_button("📄 Cetak PDF", pdf_bytes, f"Stok_{datetime.now().strftime('%Y%m%d')}.pdf", use_container_width=True)

elif active_menu == "Kelola Master Item":
    tab1, tab2 = st.tabs(["➕ Tambah Barang Baru", "⚙️ Edit / Kelola Barang"])
    
    with tab1:
        st.subheader("Tambah Jenis Barang Baru")
        with st.form("form_tambah_barang", clear_on_submit=True):
            nama_baru = st.text_input("Nama Barang Baru")
            col_t1, col_t2 = st.columns(2)
            stok_awal = col_t1.number_input("Stok Awal (pcs)", min_value=0, value=0, step=1)
            batas_min = col_t2.number_input("Batas Stok Minimum (Notifikasi)", min_value=1, value=5, step=1)
            
            if st.form_submit_button("➕ Tambah Barang"):
                nama_clean = nama_baru.strip()
                if not nama_clean: 
                    st.warning("Nama barang tidak boleh kosong!")
                elif nama_clean in st.session_state.stok: 
                    st.error("Barang sudah ada di database!")
                else:
                    berhasil = save_data_atomic("BARANG BARU", nama_clean, stok_awal, "Item baru")
                    if berhasil:
                        update_master_item_atomic(nama_clean, nama_clean, "Aktif", batas_min)
                        st.success(f"Item `{nama_clean}` berhasil ditambahkan!")
                        threading.Thread(target=kirim_notifikasi_telegram, args=(f"✨ **ITEM BARU**\n📦 {nama_clean} | Stok Awal: {stok_awal} pcs | Min Stok: {batas_min}",)).start()
                        st.rerun()
                        
    with tab2:
        st.subheader("Edit Data atau Hapus Barang")
        list_semua_barang = sorted(st.session_state.stok.keys(), key=kunci_urut_nama)
        if not list_semua_barang:
            st.info("Belum ada barang di database.")
        else:
            pilih_barang = st.selectbox("Pilih Barang yang Ingin Dikelola:", list_semua_barang)
            info_barang = st.session_state.master_info.get(pilih_barang, {})
            
            with st.form("form_edit_barang"):
                edit_nama = st.text_input("Ubah Nama Barang", value=pilih_barang)
                
                col_e1, col_e2 = st.columns(2)
                edit_status = col_e1.selectbox("Status Barang", ["Aktif", "Nonaktif"], index=0 if info_barang.get("status", "Aktif") == "Aktif" else 1)
                edit_min = col_e2.number_input("Batas Stok Minimum", min_value=1, value=info_barang.get("min_stok", 5), step=1)
                
                st.markdown("---")
                c_btn1, c_btn2 = st.columns(2)
                simpan_master = c_btn1.form_submit_button("💾 Simpan Perubahan Master")
                hapus_master = c_btn2.form_submit_button("🗑️ Hapus Barang Ini (Permanen)")
                
                if simpan_master:
                    edit_nama_clean = edit_nama.strip()
                    if not edit_nama_clean:
                        st.warning("Nama barang tidak boleh kosong!")
                    else:
                        if update_master_item_atomic(pilih_barang, edit_nama_clean, edit_status, edit_min, is_delete=False):
                            st.success(f"Data master `{edit_nama_clean}` berhasil diperbarui!")
                            st.rerun()
                            
                if hapus_master:
                    if update_master_item_atomic(pilih_barang, "", "", 0, is_delete=True):
                        st.success(f"Barang `{pilih_barang}` dan seluruh log transaksinya berhasil dihapus!")
                        st.rerun()

elif active_menu == "Barang Masuk":
    st.subheader("Form Transaksi Barang Masuk (Inbound)")
    barang_aktif_list = sorted([k for k, v in st.session_state.master_info.items() if v.get("status", "Aktif") == "Aktif"], key=kunci_urut_nama)
    
    if not barang_aktif_list:
        st.warning("Tidak ada barang dengan status 'Aktif'. Silakan tambahkan atau aktifkan barang di menu Kelola Master Item.")
    else:
        with st.form("form_masuk", clear_on_submit=True):
            barang_pilihan = st.selectbox("Pilih Barang", barang_aktif_list)
            jumlah_masuk = st.number_input("Jumlah Masuk (pcs)", min_value=1, value=1, step=1)
            
            tgl_transaksi = st.date_input("Tanggal Transaksi", value=date.today())
            foto_bukti = st.file_uploader("Upload Bukti / Nota (Opsional)", type=["jpg", "jpeg", "png"])
            catatan_masuk = st.text_input("Supplier / Keterangan", "-")
            
            if st.form_submit_button("📥 Simpan Barang Masuk"):
                berhasil = save_data_atomic("MASUK", barang_pilihan, jumlah_masuk, catatan_masuk)
                if berhasil:
                    st.success(f"Berhasil menambah stok {barang_pilihan} (+{jumlah_masuk} pcs) untuk tanggal {tgl_transaksi.strftime('%d-%m-%Y')}!")
                    pesan_tg = f"📥 **BARANG MASUK**\n📦 {barang_pilihan}\n➕ +{jumlah_masuk} pcs\n📅 Tanggal: {tgl_transaksi.strftime('%d-%m-%Y')}\n📊 Sisa: {st.session_state.stok[barang_pilihan]} pcs\n📝 {catatan_masuk}"
                    threading.Thread(target=kirim_notifikasi_telegram, args=(pesan_tg, kompres_gambar(foto_bukti))).start()
                    st.rerun()

elif active_menu == "Barang Keluar":
    st.subheader("Form Transaksi Barang Keluar (Outbound)")
    barang_aktif_list = sorted([k for k, v in st.session_state.master_info.items() if v.get("status", "Aktif") == "Aktif"], key=kunci_urut_nama)
    
    if not barang_aktif_list:
        st.warning("Tidak ada barang dengan status 'Aktif'. Silakan tambahkan atau aktifkan barang di menu Kelola Master Item.")
    else:
        with st.form("form_keluar", clear_on_submit=True):
            barang_pilihan = st.selectbox("Pilih Barang", barang_aktif_list)
            stok_saat_ini = st.session_state.stok.get(barang_pilihan, 0)
            st.info(f"Sisa Stok `{barang_pilihan}` saat ini: **{stok_saat_ini} pcs**")
            
            jumlah_keluar = st.number_input("Jumlah Keluar (pcs)", min_value=1, value=1, step=1)
            tgl_transaksi = st.date_input("Tanggal Transaksi", value=date.today())
            nama_pembeli = st.text_input("Nama Pembeli / Proyek", "")
            foto_bukti = st.file_uploader("Upload Surat Jalan (Opsional)", type=["jpg", "jpeg", "png"])
            
            if st.form_submit_button("📤 Simpan Pengiriman"):
                if not nama_pembeli.strip(): 
                    st.warning("⚠️ Mohon isi Nama Pembeli / Proyek!")
                else:
                    berhasil = save_data_atomic("KELUAR", barang_pilihan, jumlah_keluar, nama_pembeli.strip())
                    if berhasil:
                        st.success(f"Pengiriman {barang_pilihan} sebanyak {jumlah_keluar} pcs berhasil dicatat!")
                        pesan_tg = f"📤 **BARANG KELUAR**\n📦 {barang_pilihan}\n➖ -{jumlah_keluar} pcs\n📅 Tanggal: {tgl_transaksi.strftime('%d-%m-%Y')}\n👤 Pembeli: {nama_pembeli}\n📊 Sisa: {st.session_state.stok[barang_pilihan]} pcs"
                        threading.Thread(target=kirim_notifikasi_telegram, args=(pesan_tg, kompres_gambar(foto_bukti))).start()
                        st.rerun()

elif active_menu == "Koreksi Transaksi":
    st.subheader("✏️ Koreksi / Hapus Transaksi")
    st.info("Fitur ini memungkinkan Anda mengubah atau menghapus data transaksi jika terjadi salah input. Stok barang akan dihitung ulang secara otomatis.")
    
    if not st.session_state.riwayat:
        st.warning("Belum ada riwayat transaksi yang dapat dikoreksi.")
    else:
        riwayat_options = st.session_state.riwayat[:150]
        
        def format_tx(tx):
            return f"[{tx['Waktu']}] | {tx['Tipe']} - {tx['Barang']} ({tx['Jumlah']} pcs) | {tx['Pembeli / Keterangan']}"
            
        pilihan_tx_str = st.selectbox("Cari & Pilih Transaksi yang Ingin Dikoreksi:", [format_tx(tx) for tx in riwayat_options])
        old_tx = next((tx for tx in riwayat_options if format_tx(tx) == pilihan_tx_str), None)
        
        if old_tx:
            st.markdown("---")
            with st.form("form_koreksi"):
                st.write("**Form Edit Transaksi**")
                
                new_waktu = st.text_input("Waktu Transaksi", old_tx['Waktu'])
                new_tipe = st.selectbox("Tipe Transaksi", ["MASUK", "KELUAR", "BARANG BARU"], index=["MASUK", "KELUAR", "BARANG BARU"].index(old_tx['Tipe']))
                
                list_barang = sorted(st.session_state.stok.keys(), key=kunci_urut_nama)
                idx_barang = list_barang.index(old_tx['Barang']) if old_tx['Barang'] in list_barang else 0
                new_barang = st.selectbox("Barang", list_barang, index=idx_barang)
                
                new_jumlah = st.number_input("Jumlah (pcs)", min_value=1, value=old_tx['Jumlah'], step=1)
                new_ket = st.text_input("Keterangan / Pembeli", old_tx['Pembeli / Keterangan'])
                
                c1, c2 = st.columns(2)
                with c1:
                    btn_simpan = st.form_submit_button("💾 Simpan Perubahan")
                with c2:
                    btn_hapus = st.form_submit_button("🗑️ Hapus Transaksi Ini")
                    
                if btn_simpan:
                    new_tx = {
                        "Waktu": new_waktu,
                        "Tipe": new_tipe,
                        "Barang": new_barang,
                        "Jumlah": new_jumlah,
                        "Pembeli / Keterangan": new_ket
                    }
                    if new_tx == old_tx:
                        st.warning("Tidak ada perubahan yang dilakukan.")
                    else:
                        if koreksi_transaksi_atomic(old_tx, new_tx, is_delete=False):
                            st.success("Koreksi berhasil disimpan dan stok telah diperbarui!")
                            pesan_koreksi = f"✏️ **KOREKSI TRANSAKSI**\n*Data Lama:* {old_tx['Tipe']} {old_tx['Barang']} ({old_tx['Jumlah']} pcs)\n*Data Baru:* {new_tipe} {new_barang} ({new_jumlah} pcs)"
                            threading.Thread(target=kirim_notifikasi_telegram, args=(pesan_koreksi,)).start()
                            st.rerun()
                            
                if btn_hapus:
                    if koreksi_transaksi_atomic(old_tx, None, is_delete=True):
                        st.success("Transaksi berhasil dihapus dan stok telah dikembalikan!")
                        pesan_hapus = f"🗑️ **HAPUS TRANSAKSI**\nData {old_tx['Tipe']} {old_tx['Barang']} ({old_tx['Jumlah']} pcs) telah dihapus dari sistem."
                        threading.Thread(target=kirim_notifikasi_telegram, args=(pesan_hapus,)).start()
                        st.rerun()

elif active_menu == "Riwayat Transaksi":
    st.subheader("Riwayat Log Transaksi Gudang")
    if not st.session_state.riwayat:
        st.info("Belum ada riwayat transaksi.")
    else:
        df_riwayat = pd.DataFrame(st.session_state.riwayat)
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            filter_tipe = st.selectbox("Filter Tipe", ["SEMUA", "MASUK", "KELUAR", "BARANG BARU"])
        with col_f2:
            search_item = st.text_input("Cari Barang / Keterangan", "")
            
        df_filtered = df_riwayat.copy()
        if filter_tipe != "SEMUA":
            df_filtered = df_filtered[df_filtered["Tipe"] == filter_tipe]
        if search_item:
            mask = df_filtered["Barang"].astype(str).str.contains(search_item, case=False, na=False) | df_filtered["Pembeli / Keterangan"].astype(str).str.contains(search_item, case=False, na=False)
            df_filtered = df_filtered[mask]
            
        st.dataframe(df_filtered, use_container_width=True, hide_index=True)
        
        c_ex1, c_ex2 = st.columns(2)
        with c_ex1:
            st.download_button("📥 Ekspor Riwayat Excel", buat_excel_bytes(df_filtered, "Riwayat"), f"Riwayat_{datetime.now().strftime('%Y%m%d')}.xlsx", use_container_width=True)
        with c_ex2:
            pdf_bytes = buat_pdf_tabel("RIWAYAT TRANSAKSI", ["Waktu", "Tipe", "Barang", "Jumlah", "Keterangan"], [[str(r["Waktu"]), str(r["Tipe"]), str(r["Barang"]), f"{r['Jumlah']} pcs", str(r["Pembeli / Keterangan"])] for _, r in df_filtered.iterrows()], [35, 25, 60, 20, 50])
            st.download_button("📄 Cetak Riwayat PDF", pdf_bytes, f"Riwayat_{datetime.now().strftime('%Y%m%d')}.pdf", use_container_width=True)

elif active_menu == "Laporan Periodik":
    st.subheader("Laporan Transaksi Berdasarkan Rentang Tanggal")
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        tgl_mulai = st.date_input("Tanggal Mulai", date.today().replace(day=1))
    with col_d2:
        tgl_selesai = st.date_input("Tanggal Selesai", date.today())
        
    if tgl_mulai > tgl_selesai:
        st.error("Tanggal mulai tidak boleh melebihi tanggal selesai!")
    else:
        riwayat_filtered = filter_riwayat_berdasarkan_rentang(st.session_state.riwayat, tgl_mulai, tgl_selesai)
        if not riwayat_filtered:
            st.warning("Tidak ada transaksi pada rentang tanggal tersebut.")
        else:
            df_periodik = pd.DataFrame(riwayat_filtered)
            m_in = sum(safe_int(x.get("Jumlah", 0)) for x in riwayat_filtered if x.get("Tipe") == "MASUK")
            m_out = sum(safe_int(x.get("Jumlah", 0)) for x in riwayat_filtered if x.get("Tipe") == "KELUAR")
            
            mc1, mc2, mc3 = st.columns(3)
            mc1.metric("Total Masuk", f"{m_in} pcs")
            mc2.metric("Total Keluar", f"{m_out} pcs")
            mc3.metric("Total Transaksi", f"{len(riwayat_filtered)}")
            
            st.dataframe(df_periodik, use_container_width=True, hide_index=True)
            info_tgl = f"Periode: {tgl_mulai.strftime('%d-%m-%Y')} s/d {tgl_selesai.strftime('%d-%m-%Y')}"
            
            c_ex1, c_ex2 = st.columns(2)
            with c_ex1:
                st.download_button("📥 Ekspor Laporan Excel", buat_excel_bytes(df_periodik, "Periodik"), f"Laporan_{tgl_mulai}_{tgl_selesai}.xlsx", use_container_width=True)
            with c_ex2:
                pdf_bytes = buat_pdf_tabel("LAPORAN PERIODIK", ["Waktu", "Tipe", "Barang", "Jumlah", "Keterangan"], [[str(r["Waktu"]), str(r["Tipe"]), str(r["Barang"]), f"{r['Jumlah']} pcs", str(r["Pembeli / Keterangan"])] for _, r in df_periodik.iterrows()], [35, 25, 60, 20, 50], info_tambahan=info_tgl)
                st.download_button("📄 Cetak Laporan PDF", pdf_bytes, f"Laporan_{tgl_mulai}_{tgl_selesai}.pdf", use_container_width=True)

elif active_menu == "Backup Data":
    st.subheader("Kirim Backup Database ke Telegram")
    st.write("Klik tombol di bawah untuk membuat file backup lengkap database (stok & riwayat) dan mengirimkannya langsung ke Telegram.")
    
    if st.button("📤 Kirim Backup ke Telegram", use_container_width=True):
        with st.spinner("Sedang memproses dan mengirim file backup ke Telegram..."):
            excel_backup = buat_excel_backup_lengkap(st.session_state.stok, st.session_state.master_info, st.session_state.riwayat)
            nama_file = f"BACKUP_GUDANG_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            pesan_backup = f"💾 **MANUAL BACKUP DATABASE GUDANG**\n📅 {dapatkan_waktu_wib()}"
            
            berhasil = kirim_dokumen_telegram(pesan_backup, excel_backup, nama_file)
            if berhasil:
                st.success("✅ File backup database berhasil dikirim ke Telegram!")
            else:
                st.error("❌ Gagal mengirim file ke Telegram. Periksa kembali token bot dan chat ID Anda.")

elif active_menu == "Pengaturan & Reset":
    st.subheader("Pengaturan & Reset Pabrik")
    st.warning("⚠️ **Zona Bahaya:** Tindakan ini akan mengosongkan riwayat dan mengembalikan stok ke kondisi default awal.")
    
    langkah1 = st.checkbox("Saya memahami risiko ini")
    teks_konfirmasi = st.text_input("Ketik `RESET-DATABASE` untuk mengonfirmasi:", disabled=not langkah1)
    
    if st.button("🚨 Reset Semua Data", disabled=not (langkah1 and teks_konfirmasi.strip() == "RESET-DATABASE")):
        backup_bytes = buat_excel_backup_lengkap(st.session_state.stok, st.session_state.master_info, st.session_state.riwayat)
        kirim_dokumen_telegram(f"🚨 **AUTO-BACKUP SEBELUM RESET**\n{dapatkan_waktu_wib()}", backup_bytes, f"Backup_Reset_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
        
        stok_reset = STOK_DEFAULT.copy()
        master_reset = MASTER_DEFAULT.copy()
        riwayat_reset = []
        payload_reset = payload_generator(stok_reset, master_reset, riwayat_reset)
        
        def _reset_db():
            res = requests.post(URL_GSHEET_API, json=payload_reset, timeout=45)
            res.raise_for_status()
            st.session_state.stok = stok_reset
            st.session_state.master_info = master_reset
            st.session_state.riwayat = riwayat_reset
            st.session_state.notif_terkirim_habis = frozenset()
            st.session_state.notif_terkirim_kritis = frozenset()
            st.cache_data.clear()
            st.success("Data berhasil di-reset!")
            st.rerun()

        safe_api_call(_reset_db, error_message="Gagal meriset data server.")

elif active_menu == "Tentang Aplikasi":
    st.subheader("Tentang Aplikasi WMS Microcement")
    st.write("Aplikasi Manajemen Gudang berbasis Streamlit yang terintegrasi dengan Google Sheets sebagai Database dan Telegram Bot sebagai sistem notifikasi otomatis.")
    st.info("Versi: 4.5.1 Pro Enterprise (Patch Fix: KeyError master_info)")
