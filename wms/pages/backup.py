"""Halaman backup lokal, Telegram, dan Google Drive."""

import time

import streamlit as st

from ..api import show_api_error
from ..auth import current_role, require_permission
from ..config import ROLE_DEVELOPER
from ..exports import full_backup_bytes
from ..notifications import record_notification, send_telegram_document_detailed
from ..operations import (
    backup_server_status_cached,
    install_backup_trigger,
    remove_backup_trigger,
    server_backup_now,
)
from ..utils import api_error_detail, sekarang_wib, waktu_display

def render_backup_page():
    require_permission("backup")
    st.write("Backup berisi stok, riwayat transaksi, audit log, serta manifest URL bukti transaksi.")
    st.caption("Catatan: gambar/nota asli tetap berada di Google Drive; workbook menyimpan daftar URL-nya.")

    backup_is_snapshot = not st.session_state.get("is_connected")
    if backup_is_snapshot:
        st.warning("⚠️ Database offline. File lokal di bawah adalah SNAPSHOT sesi terakhir, bukan backup database real-time.")

    # full_backup_bytes dicache berdasarkan isi data sehingga rerun tombol tidak membuat XLSX berulang-ulang.
    backup = full_backup_bytes(
        st.session_state.get("stok", {}),
        st.session_state.get("master_info", {}),
        st.session_state.get("riwayat", []),
        st.session_state.get("audit", []),
    )
    prefix = "SNAPSHOT_WMS" if backup_is_snapshot else "BACKUP_WMS"
    filename = f"{prefix}_{sekarang_wib().strftime('%Y%m%d_%H%M%S')}.xlsx"
    b1, b2 = st.columns(2)
    b1.download_button("💾 Download Backup", backup, filename, use_container_width=True)
    if b2.button("📤 Kirim Backup ke Telegram", use_container_width=True):
        ok, detail = send_telegram_document_detailed(
            f"💾 BACKUP WMS\n{waktu_display()}",
            backup,
            filename,
        )
        record_notification("Backup manual", ok, detail)
        if ok:
            st.success(detail)
        else:
            st.error(f"Backup gagal dikirim ke Telegram — {detail}")

    st.divider()
    st.subheader("☁️ Backup Database Otomatis")
    st.caption("Backup server membuat salinan Google Spreadsheet langsung ke folder WMS_Backups di Google Drive.")

    backup_flash = st.session_state.pop("backup_flash", None)
    if backup_flash:
        level, message = backup_flash
        if level == "success":
            st.success(message)
        elif level == "warning":
            st.warning(message)
        else:
            st.info(message)

    backup_status = {}
    backup_status_error = None
    if st.session_state.get("is_connected"):
        try:
            backup_status = backup_server_status_cached(force=False)
            st.session_state.backup_last_time = backup_status.get("last_backup_time") or st.session_state.get("backup_last_time", "")
            st.session_state.backup_last_url = backup_status.get("last_backup_url") or st.session_state.get("backup_last_url", "")
            st.session_state.backup_last_name = backup_status.get("last_backup_name") or st.session_state.get("backup_last_name", "")
            st.session_state.backup_trigger_active = bool(backup_status.get("trigger_installed", False))
        except Exception as exc:
            backup_status_error = api_error_detail(exc)
    else:
        backup_status_error = "database sedang offline"

    last_backup = backup_status.get("last_backup_time") or st.session_state.get("backup_last_time") or "Belum ada"
    last_backup_name = backup_status.get("last_backup_name") or st.session_state.get("backup_last_name") or ""
    last_backup_url = backup_status.get("last_backup_url") or st.session_state.get("backup_last_url") or ""
    trigger_active = bool(backup_status.get("trigger_installed", st.session_state.get("backup_trigger_active", False)))

    if backup_status_error:
        st.warning(f"Status backup server belum dapat diperbarui: {backup_status_error}. Status terakhir yang tersimpan tetap ditampilkan.")

    bs1, bs2 = st.columns(2)
    bs1.metric("Backup terakhir", last_backup)
    bs2.metric("Backup harian", "Aktif" if trigger_active else "Belum aktif")
    if last_backup_name:
        st.caption(f"Backup terakhir: {last_backup_name}")
    if last_backup_url:
        st.link_button("📂 Buka Backup Terakhir di Google Drive", last_backup_url, use_container_width=True)

    if st.button("☁️ Buat Backup Server Sekarang", use_container_width=True, disabled=not st.session_state.get("is_connected")):
        try:
            result = server_backup_now()
            backup_time = result.get("backup_time") or waktu_display()
            backup_name = result.get("backup_name") or "WMS backup"
            backup_url = result.get("backup_url") or ""
            st.session_state.backup_last_time = backup_time
            st.session_state.backup_last_name = backup_name
            st.session_state.backup_last_url = backup_url
            st.session_state.backup_status_cache = {
                **st.session_state.get("backup_status_cache", {}),
                "last_backup_time": backup_time,
                "last_backup_name": backup_name,
                "last_backup_url": backup_url,
                "trigger_installed": trigger_active,
            }
            st.session_state.backup_status_epoch = time.time()
            st.session_state.backup_flash = ("success", f"Backup server berhasil: {backup_name}")
            st.rerun()
        except Exception as exc:
            show_api_error("Backup server gagal", exc)

    if current_role() == ROLE_DEVELOPER:
        bt1, bt2 = st.columns(2)
        if bt1.button("🕑 Aktifkan Backup Harian", use_container_width=True, disabled=trigger_active or not st.session_state.get("is_connected")):
            try:
                result = install_backup_trigger()
                st.session_state.backup_trigger_active = bool(result.get("trigger_installed", True)) if isinstance(result, dict) else True
                st.session_state.backup_status_cache = {
                    **st.session_state.get("backup_status_cache", {}),
                    "trigger_installed": st.session_state.backup_trigger_active,
                }
                st.session_state.backup_status_epoch = time.time()
                st.session_state.backup_flash = ("success", "Backup otomatis harian berhasil diaktifkan.")
                st.rerun()
            except Exception as exc:
                show_api_error("Gagal mengaktifkan backup harian", exc)
        if bt2.button("⏹️ Nonaktifkan Backup Harian", use_container_width=True, disabled=(not trigger_active) or not st.session_state.get("is_connected")):
            try:
                result = remove_backup_trigger()
                st.session_state.backup_trigger_active = bool(result.get("trigger_installed", False)) if isinstance(result, dict) else False
                st.session_state.backup_status_cache = {
                    **st.session_state.get("backup_status_cache", {}),
                    "trigger_installed": st.session_state.backup_trigger_active,
                }
                st.session_state.backup_status_epoch = time.time()
                st.session_state.backup_flash = ("success", "Backup otomatis harian dinonaktifkan.")
                st.rerun()
            except Exception as exc:
                show_api_error("Gagal menonaktifkan backup harian", exc)
