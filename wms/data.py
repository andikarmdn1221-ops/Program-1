"""Normalisasi data, cache, health check, dan sinkronisasi sesi."""

import hashlib
import re
import time

import streamlit as st

from .api import api_get, api_health, show_api_error
from .config import (
    API_SHARED_KEY,
    AUDIT_COLUMNS,
    AUTH_SIGNING_KEY,
    AUTO_SYNC_ENABLED,
    DATA_CACHE_TTL_SECONDS,
    EXPECTED_BACKEND_VERSION,
    HEALTH_CACHE_SECONDS,
    MASTER_DEFAULT,
    OFFLINE_USE_DEFAULT_STOCK,
    REQUIRE_HMAC,
    RIWAYAT_COLUMNS,
    SERVER_EMPTY_USE_DEFAULT_STOCK,
    STOK_DEFAULT,
    URL_GSHEET_API,
    WRITE_BLOCK_WHEN_OFFLINE,
)
from .utils import parse_tx_datetime, safe_int, waktu_display

def normalize_stock_rows(raw_rows):
    stock = {}
    master = {}
    rows = raw_rows or []
    if rows and isinstance(rows[0], list):
        rows = rows[1:]

    for row in rows:
        if not isinstance(row, list) or len(row) < 2:
            continue
        nama = str(row[0]).strip()
        if not nama:
            continue
        raw_stock = str(row[1]).strip()
        if not raw_stock or not re.fullmatch(r"-?\d+(?:\.0+)?", raw_stock):
            raise RuntimeError(f"Jumlah stok untuk '{nama}' bukan angka yang valid")
        stock[nama] = safe_int(row[1])
        master[nama] = {
            "status": str(row[2]).strip() if len(row) > 2 and str(row[2]).strip() else "Aktif",
            "min_stok": safe_int(row[3], 5) if len(row) > 3 else 5,
        }

    return stock, master


def normalize_history_rows(raw_rows):
    result = []
    rows = raw_rows or []
    if rows and isinstance(rows[0], list):
        header = [str(x).strip() for x in rows[0]]
        data_rows = rows[1:]
    else:
        header = []
        data_rows = rows

    # Dukungan schema baru dari Code.gs yang disertakan.
    if header and "ID Transaksi" in header:
        for row in data_rows:
            row = list(row) + [""] * max(0, len(header) - len(row))
            item = {header[i]: row[i] for i in range(len(header))}
            item["Jumlah"] = safe_int(item.get("Jumlah"))
            result.append({col: item.get(col, "") for col in RIWAYAT_COLUMNS})
        return result

    # Kompatibilitas dengan schema lama pengguna.
    for row in data_rows:
        if not isinstance(row, list) or len(row) < 4:
            continue
        waktu = str(row[0])
        dt = parse_tx_datetime(waktu)
        result.append(
            {
                "ID Transaksi": "LEGACY-" + hashlib.sha1("|".join(map(str, row[:5])).encode()).hexdigest()[:10].upper(),
                "Waktu": waktu,
                "Tanggal": dt.strftime("%d-%m-%Y") if dt else "",
                "Tipe": str(row[1]),
                "Barang": str(row[2]),
                "Jumlah": safe_int(row[3]),
                "Pembeli / Keterangan": row[4] if len(row) > 4 else "-",
                "Bukti URL": row[5] if len(row) > 5 else "",
                "Status": row[6] if len(row) > 6 and row[6] else "AKTIF",
                "Referensi": row[7] if len(row) > 7 else "",
            }
        )
    return result


def normalize_audit_rows(raw_rows):
    rows = raw_rows or []
    if not rows:
        return []

    if isinstance(rows[0], list):
        header = [str(x).strip() for x in rows[0]]
        data_rows = rows[1:]
    else:
        header = []
        data_rows = rows

    if header and "Aksi" in header:
        result = []
        for row in data_rows:
            row = list(row) + [""] * max(0, len(header) - len(row))
            item = {header[i]: row[i] for i in range(len(header))}
            result.append({col: item.get(col, "") for col in AUDIT_COLUMNS})
        return result

    # Kompatibilitas audit lama: Waktu, Aksi, ID Transaksi, Detail
    result = []
    for row in data_rows:
        if not isinstance(row, list) or len(row) < 1:
            continue
        result.append({
            "Waktu": row[0] if len(row) > 0 else "",
            "User": "",
            "Role": "",
            "Aksi": row[1] if len(row) > 1 else "",
            "ID Transaksi": row[2] if len(row) > 2 else "",
            "Detail": row[3] if len(row) > 3 else "",
        })
    return result


def normalize_server_data(data):
    if not isinstance(data, dict):
        raise RuntimeError("Format data server tidak valid; objek JSON diharapkan.")

    stock, master = normalize_stock_rows(data.get("stok", []))
    history = normalize_history_rows(data.get("riwayat", []))
    audit = normalize_audit_rows(data.get("audit", []))

    # Jangan diam-diam mengubah database kosong menjadi stok dummy.
    # Jika instalasi lama memang membutuhkan perilaku tersebut, aktifkan secret ini secara eksplisit.
    if not stock and SERVER_EMPTY_USE_DEFAULT_STOCK:
        stock = STOK_DEFAULT.copy()
        master = {k: v.copy() for k, v in MASTER_DEFAULT.items()}
    return stock, master, history, audit


@st.cache_data(ttl=DATA_CACHE_TTL_SECONDS, show_spinner=False)
def load_data_cached(api_url: str):
    del api_url  # cache key berubah bila URL deployment berubah
    return api_get()


def refresh_data(force=False, quiet=False):
    try:
        raw = api_get() if force else load_data_cached(URL_GSHEET_API)
        stock, master, history, audit = normalize_server_data(raw)
        st.session_state.stok = stock
        st.session_state.master_info = master
        st.session_state.riwayat = history
        st.session_state.audit = audit
        st.session_state.is_connected = True
        st.session_state.data_source = "server"
        st.session_state.last_server_sync = waktu_display()
        st.session_state.last_server_sync_epoch = time.time()
        revision = str(raw.get("data_revision", "") or "") if isinstance(raw, dict) else ""
        backend_version = str(raw.get("backend_version", "") or "") if isinstance(raw, dict) else ""
        if revision:
            st.session_state.server_revision = revision
        if backend_version:
            st.session_state.backend_version = backend_version
            st.session_state.backend_version_mismatch = backend_version != EXPECTED_BACKEND_VERSION
        st.session_state.health_cache = {
            "ok": True,
            "backend_version": backend_version,
            "data_revision": revision,
        }
        st.session_state.last_health_epoch = time.time()
        st.session_state.last_health_check = waktu_display()
        return True
    except Exception as exc:
        st.session_state.is_connected = False
        if "stok" not in st.session_state:
            if OFFLINE_USE_DEFAULT_STOCK:
                st.session_state.stok = STOK_DEFAULT.copy()
                st.session_state.master_info = {k: v.copy() for k, v in MASTER_DEFAULT.items()}
                st.session_state.data_source = "default_offline"
            else:
                st.session_state.stok = {}
                st.session_state.master_info = {}
                st.session_state.data_source = "offline_empty"
            st.session_state.riwayat = []
            st.session_state.audit = []
        else:
            st.session_state.data_source = "last_known_session"
        if not quiet:
            show_api_error("Gagal mengambil data", exc)
        return False


def clear_and_refresh():
    # Bersihkan hanya cache pembacaan database; cache ekspor pengguna lain tidak ikut terhapus.
    load_data_cached.clear()
    refresh_data(force=True)


def _apply_health_to_session(health: dict):
    """Simpan hasil health check agar rerun Streamlit tidak memanggil Apps Script berulang."""
    health = health or {}
    revision = str(health.get("data_revision", "") or "")
    backend_version = str(health.get("backend_version", "") or "")
    st.session_state.health_cache = dict(health)
    st.session_state.last_health_epoch = time.time()
    st.session_state.last_health_check = waktu_display()
    st.session_state.is_connected = True
    if backend_version:
        st.session_state.backend_version = backend_version
        st.session_state.backend_version_mismatch = backend_version != EXPECTED_BACKEND_VERSION
    return revision


def get_server_health(force=False):
    """Health-check bertingkat: gunakan hasil sesi singkat sebelum meminta Apps Script lagi."""
    now = time.time()
    cached = st.session_state.get("health_cache")
    last = float(st.session_state.get("last_health_epoch", 0) or 0)
    if not force and isinstance(cached, dict) and (now - last) < HEALTH_CACHE_SECONDS:
        return cached
    health = api_health()
    _apply_health_to_session(health)
    return health


def sync_if_changed(force_health=False):
    """Polling ringan; full read hanya saat revision backend berubah."""
    if not AUTO_SYNC_ENABLED and not force_health:
        return False
    try:
        health = get_server_health(force=force_health)
        revision = str(health.get("data_revision", "") or "")
        current_revision = str(st.session_state.get("server_revision", "") or "")
        if not revision or revision != current_revision:
            return refresh_data(force=True, quiet=True)
        return False
    except Exception:
        st.session_state.is_connected = False
        if "stok" in st.session_state:
            st.session_state.data_source = "last_known_session"
        return False


def require_online_operation():
    """Gunakan health terbaru bila masih fresh; server tetap memvalidasi setiap mutation saat submit."""
    if not WRITE_BLOCK_WHEN_OFFLINE:
        return
    try:
        get_server_health(force=False)
    except Exception:
        st.session_state.is_connected = False
        if "stok" in st.session_state:
            st.session_state.data_source = "last_known_session"

    if not st.session_state.get("is_connected"):
        st.error("⛔ Operasi perubahan stok dinonaktifkan karena database sedang offline. Segarkan koneksi terlebih dahulu.")
        st.stop()


def validate_runtime_security():
    """Fail-closed untuk konfigurasi yang seharusnya wajib pada deployment production."""
    missing = []
    if not URL_GSHEET_API:
        missing.append("URL_GSHEET_API")
    if not API_SHARED_KEY:
        missing.append("API_SHARED_KEY")
    if REQUIRE_HMAC and not AUTH_SIGNING_KEY:
        missing.append("AUTH_SIGNING_KEY")
    if missing:
        st.error("⛔ Konfigurasi production belum lengkap: " + ", ".join(missing))
        st.stop()
