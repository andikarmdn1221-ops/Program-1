"""Halaman pengelolaan master barang."""

import streamlit as st

from ..api import show_api_error
from ..auth import actor_label, notification_flash, require_permission, set_flash
from ..data import require_online_operation, sync_if_changed
from ..notifications import deliver_notification
from ..operations import add_master, delete_master, update_master
from ..utils import clean_item_name, natural_key

def render_master_page():
    require_permission("manage_master")
    sync_if_changed()
    stock = st.session_state.get("stok", {})
    master = st.session_state.get("master_info", {})
    tab_add, tab_edit = st.tabs(["➕ Tambah Barang", "⚙️ Edit / Nonaktifkan"])

    with tab_add:
        with st.form("master_add", clear_on_submit=True):
            nama = st.text_input("Nama Barang")
            a, b = st.columns(2)
            stok_awal = a.number_input("Stok Awal", min_value=0, value=0, step=1)
            minimum = b.number_input("Batas Stok Minimum", min_value=1, value=5, step=1)
            submit = st.form_submit_button("➕ Tambah Barang", use_container_width=True)
        if submit:
            try:
                nama = clean_item_name(nama)
                if nama.casefold() in {item.casefold() for item in stock}:
                    st.error("Nama barang sudah ada, termasuk perbedaan huruf besar/kecil.")
                else:
                    require_online_operation()
                    add_master(nama, stok_awal, minimum)
                    notification = deliver_notification(
                        f"✨ *ITEM BARU*\n📦 {nama}\nStok awal: {stok_awal} pcs\nMinimum: {minimum} pcs\n👤 {actor_label()}",
                        "Barang baru",
                    )
                    notification_flash("Barang berhasil ditambahkan.", [notification])
                    st.rerun()
            except Exception as exc:
                show_api_error("Gagal menambah barang", exc)

    with tab_edit:
        names = sorted(stock, key=natural_key)
        if not names:
            st.info("Belum ada master barang.")
        else:
            selected = st.selectbox("Pilih Barang", names)
            info = master.get(selected, {})
            with st.form("master_edit"):
                new_name = st.text_input("Nama Barang", value=selected)
                a, b = st.columns(2)
                new_status = a.selectbox(
                    "Status",
                    ["Aktif", "Nonaktif"],
                    index=0 if info.get("status", "Aktif") == "Aktif" else 1,
                )
                new_min = b.number_input("Batas Minimum", min_value=1, value=info.get("min_stok", 5), step=1)
                save = st.form_submit_button("💾 Simpan Perubahan", use_container_width=True)
            if save:
                try:
                    cleaned_name = clean_item_name(new_name)
                    duplicates = {item.casefold() for item in stock if item != selected}
                    if cleaned_name.casefold() in duplicates:
                        raise ValueError("Nama barang sudah digunakan item lain")
                    require_online_operation()
                    update_master(selected, cleaned_name, new_status, new_min)
                    set_flash("success", "Master barang berhasil diperbarui.")
                    st.rerun()
                except Exception as exc:
                    show_api_error("Gagal memperbarui master", exc)

            with st.expander("🗑️ Hapus permanen (hanya jika belum pernah ditransaksikan)"):
                st.caption("Jika barang sudah memiliki riwayat, server akan menolak penghapusan. Gunakan status Nonaktif.")
                confirm = st.checkbox(f"Saya yakin ingin menghapus {selected}", key="confirm_delete_master")
                if st.button("Hapus Permanen", disabled=not confirm):
                    try:
                        require_online_operation()
                        delete_master(selected)
                        notification = deliver_notification(
                            f"🗑️ *ITEM DIHAPUS*\n📦 {selected}\n👤 {actor_label()}",
                            "Hapus item",
                        )
                        notification_flash("Barang berhasil dihapus.", [notification])
                        st.rerun()
                    except Exception as exc:
                        show_api_error("Barang tidak dapat dihapus", exc)
