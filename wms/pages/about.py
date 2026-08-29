"""Halaman informasi aplikasi."""

import streamlit as st

from ..config import APP_VERSION

def render_about_page():
    st.subheader("WMS Microcement")
    st.write(
        "Aplikasi manajemen gudang berbasis Streamlit dengan Google Sheets sebagai penyimpanan data, "
        "Google Drive untuk bukti transaksi, dan Telegram untuk notifikasi operasional."
    )
    st.info(f"Versi {APP_VERSION} · Internal WMS")
    st.caption("Role: Developer, Boss, Admin, Staff. Boss dapat mengelola dan menyesuaikan stok, sedangkan reset database hanya Developer.")
    st.caption(
        "Transaksi, penyesuaian, koreksi, void, dan master item diproses server-side. "
        "Versi Pro menambahkan UI responsif seluruh ukuran HP, sinkronisasi sebelum operasi, "
        "status pengiriman Telegram, validasi bukti, saran restok, analisis pergerakan, "
        "tanggal operasional WIB, PBKDF2, HMAC end-to-end, audit, serta backup berlapis."
    )
