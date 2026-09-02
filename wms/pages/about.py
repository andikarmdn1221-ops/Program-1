"""Halaman informasi produk Mirai."""

import streamlit as st

from ..config import APP_VERSION


def render_about_page():
    st.subheader("Mirai")
    st.caption("Inventory Operations · Warehouse Management System")
    st.write(
        "Mirai membantu tim gudang mencatat pergerakan barang, memantau stok, "
        "mengelola akses pengguna, dan menerima notifikasi operasional dalam "
        "satu aplikasi."
    )

    version_col, storage_col, notification_col = st.columns(3)
    version_col.metric("Versi aplikasi", APP_VERSION)
    storage_col.metric("Penyimpanan", "Google Sheets")
    notification_col.metric("Notifikasi", "Telegram")

    st.markdown("#### Kemampuan utama")
    st.markdown(
        """
        - Pencatatan barang masuk, barang keluar, dan penyesuaian stok.
        - Dashboard stok kritis dan saran jumlah restok.
        - Hak akses Developer, Boss, Admin, dan Staff.
        - Riwayat transaksi, laporan periodik, audit, dan backup.
        - Notifikasi Telegram untuk aktivitas penting.
        - Tampilan responsif untuk komputer dan telepon seluler.
        """
    )

    st.markdown("#### Perlindungan operasional")
    st.markdown(
        """
        - Perubahan stok ditahan saat server tidak dapat diverifikasi.
        - Password menggunakan PBKDF2 dan sesi akun diperiksa ulang.
        - Permintaan penting ditandatangani dan seluruh tindakan sensitif diaudit.
        - Snapshot lama diberi peringatan agar tidak dianggap sebagai data real-time.
        """
    )

    st.info(
        "Mirai membutuhkan koneksi internet dan konfigurasi Google Apps Script "
        "yang aktif. Status koneksi pada sidebar menunjukkan kondisi sistem saat ini."
    )
    st.caption(
        "Lisensi, konfigurasi database, akun, dan dukungan mengikuti perjanjian "
        "pada setiap instalasi."
    )
