"""Entry point dan router WMS Microcement."""

import html

import streamlit as st

st.set_page_config(
    page_title="Mirai",
    page_icon="📦",
    layout="wide",
)

from wms.auth import clear_auth_session, current_role, get_users_config, has_permission, login_gate, render_flash
from wms.components import (
    render_audit_live,
    render_dashboard_live,
    render_history_live,
    render_reports_live,
    render_stock_live,
)
from wms.config import (
    APP_VERSION,
    EXPECTED_BACKEND_VERSION,
    ROLE_BOSS,
    ROLE_DEVELOPER,
    ROLE_LABEL,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
)
from wms.data import clear_and_refresh, refresh_data, validate_runtime_security
from wms.notifications import test_telegram_connection
from wms.pages.about import render_about_page
from wms.pages.accounts import render_accounts_page
from wms.pages.backup import render_backup_page
from wms.pages.master import render_master_page
from wms.pages.notification_status import render_notification_status_page
from wms.pages.settings import render_settings_page
from wms.pages.transactions import (
    render_adjustment_page,
    render_correction_page,
    render_transaction_page,
)
from wms.styles import inject_responsive_css
from wms.utils import waktu_display

inject_responsive_css()

login_gate()
validate_runtime_security()

if "stok" not in st.session_state:
    refresh_data(force=True)

with st.sidebar:
    role_now = current_role()
    display_name = st.session_state.get("auth_display_name") or st.session_state.get("auth_user")
    role_label = ROLE_LABEL.get(role_now, role_now)
    st.markdown(
        f"""
        <div class="mirai-sidebar-brand">
            <div class="mirai-sidebar-mark">M</div>
            <div>
                <div class="mirai-sidebar-name">Mirai</div>
                <div class="mirai-sidebar-tagline">Inventory Operations</div>
            </div>
        </div>
        <div class="mirai-user-card">
            <div class="mirai-user-avatar">{html.escape(str(display_name or "M"))[:1].upper()}</div>
            <div>
                <div class="mirai-user-name">{html.escape(str(display_name or "-"))}</div>
                <div class="mirai-user-role">{html.escape(str(role_label))}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("---")

    menu_options = [
        "🏠 Dashboard",
        "📋 Lihat Semua Stok",
    ]

    if has_permission("manage_master"):
        menu_options.append("➕ Kelola Master Item")

    if has_permission("manage_accounts"):
        menu_options.append("👥 Kelola Akun")

    if has_permission("transaction"):
        menu_options.extend(["📥 Barang Masuk", "📤 Barang Keluar"])

    if has_permission("stock_adjust"):
        menu_options.append("🧮 Penyesuaian Stok")

    if has_permission("correct_transaction"):
        menu_options.append("✏️ Koreksi Transaksi")

    menu_options.append("📊 Riwayat Transaksi")

    if has_permission("view_reports"):
        menu_options.append("📈 Laporan Periodik")

    if has_permission("view_audit"):
        menu_options.append("📜 Audit Log")

    if has_permission("backup"):
        menu_options.append("💾 Backup Data")

    menu_options.append("🔔 Status Notifikasi")

    if has_permission("reset"):
        menu_options.append("⚙️ Pengaturan & Reset")

    menu_options.append("ℹ️ Tentang Aplikasi")

    active_raw = st.radio("NAVIGASI", menu_options)
    active_menu = active_raw.split(" ", 1)[1]

    st.markdown("---")
    connection_status = st.session_state.get("connection_status", "online")
    if st.session_state.get("is_connected"):
        if connection_status == "recovering":
            st.warning("🟡 Koneksi sedang dipulihkan")
        else:
            st.success("🟢 Database terhubung")
        if st.session_state.get("last_server_sync"):
            st.caption(f"Sinkron: {st.session_state.get('last_server_sync')}")
    else:
        st.error("🔴 Database offline")
    if st.session_state.get("backend_version_mismatch"):
        st.warning(
            f"⚠️ Versi backend {st.session_state.get('backend_version', '?')} tidak sama dengan app {EXPECTED_BACKEND_VERSION}."
        )

    telegram_status = st.session_state.get("telegram_test_status")
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        st.warning("⚪ Telegram belum dikonfigurasi")
    elif telegram_status is True:
        st.success("🟢 Telegram terhubung")
    elif telegram_status is False:
        st.error("🔴 Telegram gagal terhubung")
    else:
        st.info("🟡 Telegram dikonfigurasi · belum diuji")

    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID and role_now in {ROLE_DEVELOPER, ROLE_BOSS}:
        if st.button("🧪 Tes Telegram", use_container_width=True):
            with st.spinner("Menguji Telegram..."):
                ok, detail = test_telegram_connection()
            st.session_state.telegram_test_status = ok
            st.session_state.telegram_test_detail = detail

        detail = st.session_state.get("telegram_test_detail")
        if detail:
            if st.session_state.get("telegram_test_status"):
                st.caption(f"✅ {detail}")
            else:
                st.caption(f"❌ {detail}")

    if get_users_config() and st.button("🚪 Keluar", use_container_width=True):
        clear_auth_session()
        st.rerun()

page_descriptions = {
    "Dashboard": "Pantau kondisi dan aktivitas gudang secara real-time.",
    "Lihat Semua Stok": "Lihat ketersediaan seluruh barang dalam satu tempat.",
    "Kelola Master Item": "Atur barang, satuan, batas minimum, dan status item.",
    "Kelola Akun": "Kelola akses pengguna dan keamanan akun.",
    "Barang Masuk": "Catat penerimaan barang ke gudang.",
    "Barang Keluar": "Catat pengeluaran barang dari gudang.",
    "Penyesuaian Stok": "Sesuaikan jumlah stok berdasarkan hasil pemeriksaan.",
    "Koreksi Transaksi": "Perbaiki transaksi dengan jejak audit yang jelas.",
    "Riwayat Transaksi": "Telusuri seluruh aktivitas barang masuk dan keluar.",
    "Laporan Periodik": "Analisis pergerakan barang berdasarkan periode.",
    "Audit Log": "Pantau aktivitas penting yang terjadi dalam sistem.",
    "Backup Data": "Amankan salinan data operasional gudang.",
    "Status Notifikasi": "Periksa koneksi dan pengiriman notifikasi.",
    "Pengaturan & Reset": "Kelola konfigurasi khusus Developer.",
    "Tentang Aplikasi": "Informasi versi dan kemampuan sistem Mirai.",
}
page_description = page_descriptions.get(active_menu, "Kelola operasional gudang dengan lebih teratur.")
st.markdown(
    f"""
    <div class="mirai-page-header">
        <div class="mirai-page-mark">M</div>
        <div class="mirai-page-copy">
            <div class="mirai-page-eyebrow">MIRAI · INVENTORY OPERATIONS</div>
            <h1>{html.escape(active_menu)}</h1>
            <p>{html.escape(page_description)}</p>
        </div>
        <div class="mirai-page-meta">
            <span>{html.escape(waktu_display())}</span>
            <span>v{html.escape(str(APP_VERSION))}</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)
if st.button("↻ Segarkan data", help="Ambil data terbaru dari server", key="main_refresh"):
    clear_and_refresh()
    st.rerun()

st.markdown('<div class="mirai-header-divider"></div>', unsafe_allow_html=True)
render_flash()

if not st.session_state.get("is_connected"):
    source = st.session_state.get("data_source", "offline")
    if source == "last_known_session":
        last_sync = st.session_state.get("last_server_sync", "tidak diketahui")
        st.error(f"🚨 Database tidak dapat dihubungi. Data yang tampil adalah snapshot sesi terakhir (sinkron terakhir: {last_sync}). Jangan anggap sebagai stok real-time.")
    elif source == "default_offline":
        st.error("🚨 Database offline. Yang tampil adalah STOK DEFAULT/DUMMY, bukan stok aktual. Jangan gunakan untuk keputusan operasional.")
    else:
        st.error("🚨 Database tidak dapat dihubungi. Data stok aktual tidak ditampilkan untuk mencegah penggunaan angka yang menyesatkan.")


# ============================================================
# ROUTING HALAMAN
# ============================================================
if active_menu == "Dashboard":
    render_dashboard_live()
elif active_menu == "Lihat Semua Stok":
    render_stock_live()
elif active_menu == "Kelola Master Item":
    render_master_page()
elif active_menu == "Kelola Akun":
    render_accounts_page()
elif active_menu in ("Barang Masuk", "Barang Keluar"):
    render_transaction_page(active_menu)
elif active_menu == "Penyesuaian Stok":
    render_adjustment_page()
elif active_menu == "Koreksi Transaksi":
    render_correction_page()
elif active_menu == "Riwayat Transaksi":
    render_history_live()
elif active_menu == "Laporan Periodik":
    render_reports_live()
elif active_menu == "Audit Log":
    render_audit_live()
elif active_menu == "Backup Data":
    render_backup_page()
elif active_menu == "Status Notifikasi":
    render_notification_status_page()
elif active_menu == "Pengaturan & Reset":
    render_settings_page()
elif active_menu == "Tentang Aplikasi":
    render_about_page()
