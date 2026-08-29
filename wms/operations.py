"""Operasi mutasi stok, master item, koreksi, reset, dan backup server."""

import time

import streamlit as st

from .api import _post_json, api_post
from .auth import actor_payload
from .config import BACKUP_STATUS_TTL_SECONDS
from .data import clear_and_refresh
from .utils import (
    clean_note,
    combine_manual_date,
    hari_ini_wib,
    make_tx_id,
    to_image_payload,
)

def do_transaction(
    tipe,
    barang,
    jumlah,
    tgl_transaksi,
    keterangan,
    file_uploaded=None,
    image_bytes=None,
    expected_stock_before=None,
):
    payload = {
        "action": "transaction",
        "tx_id": make_tx_id(),
        "tanggal": tgl_transaksi.strftime("%d-%m-%Y"),
        "waktu": combine_manual_date(tgl_transaksi),
        "tipe": tipe,
        "barang": barang,
        "jumlah": int(jumlah),
        "keterangan": clean_note(keterangan, required=(tipe == "KELUAR")),
        **to_image_payload(file_uploaded, image_bytes),
        **actor_payload(),
    }
    if expected_stock_before is not None:
        # Backend baru dapat memakai nilai ini sebagai stale-stock guard;
        # backend 7.1 yang belum mendukung akan mengabaikan field tambahan ini.
        payload["expected_stock_before"] = int(expected_stock_before)
    result = api_post(payload)
    clear_and_refresh()
    return result


def add_master(nama, stok_awal, min_stok):
    result = api_post(
        {
            "action": "master_add",
            "nama": nama,
            "stok_awal": int(stok_awal),
            "min_stok": int(min_stok),
            "status": "Aktif",
            "tx_id": make_tx_id("NEW"),
            "waktu": combine_manual_date(hari_ini_wib()),
            **actor_payload(),
        }
    )
    clear_and_refresh()
    return result


def update_master(old_nama, new_nama, status, min_stok):
    result = api_post(
        {
            "action": "master_update",
            "old_nama": old_nama,
            "new_nama": new_nama,
            "status": status,
            "min_stok": int(min_stok),
            **actor_payload(),
        }
    )
    clear_and_refresh()
    return result


def delete_master(nama):
    result = api_post({"action": "master_delete", "nama": nama, **actor_payload()})
    clear_and_refresh()
    return result


def correct_transaction(old_tx, new_tx):
    result = api_post(
        {
            "action": "transaction_correct",
            "tx_id": old_tx["ID Transaksi"],
            "new_tx_id": make_tx_id("COR"),
            "new_waktu": new_tx["Waktu"],
            "new_tanggal": new_tx["Tanggal"],
            "new_tipe": new_tx["Tipe"],
            "new_barang": new_tx["Barang"],
            "new_jumlah": int(new_tx["Jumlah"]),
            "new_keterangan": clean_note(new_tx["Pembeli / Keterangan"]),
            **actor_payload(),
        }
    )
    clear_and_refresh()
    return result


def void_transaction(tx_id):
    result = api_post({"action": "transaction_void", "tx_id": tx_id, **actor_payload()})
    clear_and_refresh()
    return result


def adjust_stock(barang, stok_baru, alasan, tgl_transaksi, expected_stock_before):
    result = api_post(
        {
            "action": "stock_adjust",
            "tx_id": make_tx_id("ADJ"),
            "barang": barang,
            "stok_baru": int(stok_baru),
            "expected_stock_before": int(expected_stock_before),
            "alasan": clean_note(alasan, required=True),
            "tanggal": tgl_transaksi.strftime("%d-%m-%Y"),
            "waktu": combine_manual_date(tgl_transaksi),
            **actor_payload(),
        }
    )
    clear_and_refresh()
    return result


def reset_database():
    result = api_post({"action": "reset", "confirm": "RESET-DATABASE", **actor_payload()})
    clear_and_refresh()
    return result



# ============================================================
# BACKUP SERVER / AUTO-SYNC UI
# ============================================================
def server_backup_now():
    return api_post({"action": "server_backup", **actor_payload()}, timeout=90)


def install_backup_trigger():
    return api_post({"action": "install_backup_trigger", **actor_payload()}, timeout=60)


def remove_backup_trigger():
    return api_post({"action": "remove_backup_trigger", **actor_payload()}, timeout=60)


def backup_server_status():
    return _post_json({"action": "backup_status", **actor_payload()}, timeout=20)


def backup_server_status_cached(force=False):
    """Status backup tidak perlu dipanggil ulang pada setiap widget rerun."""
    now = time.time()
    cached = st.session_state.get("backup_status_cache")
    last = float(st.session_state.get("backup_status_epoch", 0) or 0)
    if not force and isinstance(cached, dict) and (now - last) < BACKUP_STATUS_TTL_SECONDS:
        return cached
    data = backup_server_status()
    st.session_state.backup_status_cache = dict(data or {})
    st.session_state.backup_status_epoch = now
    return data
