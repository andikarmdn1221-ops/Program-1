"""Halaman hardening, generator password, dan reset database."""

import streamlit as st

from ..api import show_api_error
from ..auth import account_security_report, generate_pbkdf2_hash, notification_flash, require_permission
from ..config import (
    ALLOW_LEGACY_PASSWORDS,
    AUTH_SIGNING_KEY,
    AUTO_SYNC_ENABLED,
    AUTO_SYNC_SECONDS,
    DATA_CACHE_TTL_SECONDS,
    HEALTH_CACHE_SECONDS,
    LOGIN_LOCK_SECONDS,
    LOGIN_MAX_ATTEMPTS,
    MAX_UPLOAD_MB,
    REQUIRE_HMAC,
    REQUIRE_SERVER_BACKUP_BEFORE_RESET,
    SECONDARY_SYNC_SECONDS,
    SESSION_TIMEOUT_MINUTES,
)
from ..data import require_online_operation, sync_if_changed
from ..exports import full_backup_bytes
from ..notifications import record_notification, send_telegram_document_detailed
from ..operations import reset_database, server_backup_now
from ..utils import sekarang_wib

def render_settings_page():
    require_permission("reset")
    sync_if_changed()

    with st.expander("🔐 Generator Password Hash PBKDF2", expanded=False):
        st.caption("Gunakan hasil ini sebagai password_hash di secrets.toml. Password tidak disimpan oleh aplikasi.")
        new_password = st.text_input("Password baru", type="password", key="pbkdf2_password")
        confirm_password = st.text_input("Ulangi password", type="password", key="pbkdf2_password_confirm")
        if st.button("Buat Password Hash", use_container_width=True):
            if len(new_password) < 8:
                st.warning("Gunakan password minimal 8 karakter.")
            elif new_password != confirm_password:
                st.error("Konfirmasi password tidak sama.")
            else:
                generated_hash = generate_pbkdf2_hash(new_password)
                st.code(generated_hash, language=None)
                st.success("Hash berhasil dibuat. Salin ke password_hash pada akun yang sesuai di Streamlit Secrets.")

    with st.expander("🛡️ Status Hardening", expanded=False):
        st.write(f"Cache data: **{DATA_CACHE_TTL_SECONDS} detik**")
        st.write(f"Session timeout: **{SESSION_TIMEOUT_MINUTES} menit**")
        st.write(f"Login lock: **{LOGIN_MAX_ATTEMPTS} percobaan / {LOGIN_LOCK_SECONDS} detik**")
        st.write(f"Auto-sync Dashboard/Stok: **{'Aktif' if AUTO_SYNC_ENABLED else 'Nonaktif'} / {AUTO_SYNC_SECONDS} detik**")
        st.write(f"Auto-sync Riwayat/Laporan/Audit: **{SECONDARY_SYNC_SECONDS} detik**")
        st.write(f"Health cache: **{HEALTH_CACHE_SECONDS} detik**")
        st.write(f"Batas upload bukti: **{MAX_UPLOAD_MB} MB**")
        st.write(f"Revision backend: **{st.session_state.get('server_revision', '-')}**")
        st.write(f"Backend: **{st.session_state.get('backend_version', 'belum diketahui')}**")
        st.write(f"Mode HMAC wajib: **{'Ya' if REQUIRE_HMAC else 'Tidak'}**")
        st.write(f"Password legacy diizinkan: **{'Ya' if ALLOW_LEGACY_PASSWORDS else 'Tidak'}**")
        if AUTH_SIGNING_KEY and REQUIRE_HMAC:
            st.success("AUTH_SIGNING_KEY aktif dan mode fail-closed HMAC aktif.")
        elif AUTH_SIGNING_KEY:
            st.info("AUTH_SIGNING_KEY tersedia, tetapi REQUIRE_HMAC=false.")
        else:
            st.error("AUTH_SIGNING_KEY belum diisi.")

        account_report = account_security_report()
        weak_accounts = [name for name, status in account_report if status != "PBKDF2"]
        if weak_accounts:
            st.warning("Akun belum PBKDF2: " + ", ".join(weak_accounts))
        else:
            st.success("Semua akun menggunakan PBKDF2.")

    st.warning("Reset menghapus data operasional dan mengembalikan master awal. Backup dahulu.")
    backup = full_backup_bytes(
        st.session_state.get("stok", {}),
        st.session_state.get("master_info", {}),
        st.session_state.get("riwayat", []),
        st.session_state.get("audit", []),
    )
    st.download_button("💾 Download Backup Sebelum Reset", backup, f"PRE_RESET_{sekarang_wib().strftime('%Y%m%d_%H%M%S')}.xlsx")
    understood = st.checkbox("Saya memahami bahwa data operasional akan di-reset")
    confirm = st.text_input("Ketik RESET-DATABASE", disabled=not understood)
    if st.button("🚨 Reset Database", disabled=not (understood and confirm == "RESET-DATABASE")):
        try:
            require_online_operation()
            if REQUIRE_SERVER_BACKUP_BEFORE_RESET:
                result_backup = server_backup_now()
                st.info(f"Backup server sebelum reset berhasil: {result_backup.get('backup_name', 'WMS backup')}")
            telegram_ok, telegram_detail = send_telegram_document_detailed(
                "🚨 AUTO BACKUP SEBELUM RESET",
                backup,
                f"PRE_RESET_{sekarang_wib().strftime('%Y%m%d_%H%M%S')}.xlsx",
            )
            record_notification("Backup sebelum reset", telegram_ok, telegram_detail)
            reset_database()
            notification_flash(
                "Database berhasil di-reset setelah prosedur pengamanan.",
                [(telegram_ok, telegram_detail)],
            )
            st.rerun()
        except Exception as exc:
            show_api_error("Reset gagal", exc)
