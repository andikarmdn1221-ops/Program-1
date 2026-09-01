"""Halaman persetujuan dan pengaturan role akun dinamis."""

import pandas as pd
import streamlit as st

from ..accounts import approve_account, list_accounts, reject_account, update_account
from ..api import show_api_error
from ..auth import require_permission
from ..config import ROLE_ADMIN, ROLE_BOSS, ROLE_DEVELOPER, ROLE_STAFF
from ..data import require_online_operation


ROLES = [ROLE_STAFF, ROLE_ADMIN, ROLE_BOSS, ROLE_DEVELOPER]


def _role_index(role: str) -> int:
    return ROLES.index(role) if role in ROLES else 0


def _same_username(left, right) -> bool:
    return str(left or "").strip().casefold() == str(right or "").strip().casefold()


def render_accounts_page():
    require_permission("manage_accounts")
    require_online_operation()
    st.caption(
        "Hanya Developer yang dapat menyetujui akun, menentukan role final, mengubah role, atau menonaktifkan akun. "
        "Status Dinonaktifkan dapat dipulihkan kembali kapan saja."
    )

    try:
        accounts = list(list_accounts())
    except Exception as exc:
        show_api_error("Daftar akun gagal dimuat", exc)
        return

    pending = [
        row for row in accounts if str(row.get("status", "")).upper() == "PENDING"
    ]
    managed = [
        row for row in accounts if str(row.get("status", "")).upper() != "PENDING"
    ]

    st.subheader(f"⏳ Menunggu Persetujuan ({len(pending)})")
    if not pending:
        st.success("Tidak ada permintaan akun yang menunggu.")

    for row in pending:
        username = str(row.get("username", ""))
        title = f"{row.get('full_name', username)} · @{username}"
        with st.expander(title, expanded=True):
            st.write(f"Jabatan: **{row.get('position') or '-'}**")
            st.write(
                f"Role yang diminta: **{row.get('requested_role') or ROLE_STAFF}**"
            )
            st.caption(f"Diajukan: {row.get('created_at') or '-'}")
            selected_role = st.selectbox(
                "Role final",
                ROLES,
                index=_role_index(str(row.get("requested_role") or ROLE_STAFF)),
                key=f"approve_role_{username}",
            )
            developer_confirmed = True
            if selected_role == ROLE_DEVELOPER:
                developer_confirmed = st.checkbox(
                    "Saya memahami akun Developer memiliki akses penuh",
                    key=f"approve_developer_confirm_{username}",
                )
            left, right = st.columns(2)
            if left.button(
                "✅ Setujui",
                use_container_width=True,
                disabled=not developer_confirmed,
                key=f"approve_{username}",
            ):
                try:
                    approve_account(username, selected_role)
                    st.success(f"Akun {username} aktif sebagai {selected_role}.")
                    st.rerun()
                except Exception as exc:
                    show_api_error("Persetujuan akun gagal", exc)
            if right.button(
                "❌ Tolak", use_container_width=True, key=f"reject_{username}"
            ):
                try:
                    reject_account(username)
                    st.warning(f"Permintaan akun {username} ditolak.")
                    st.rerun()
                except Exception as exc:
                    show_api_error("Penolakan akun gagal", exc)

    st.divider()
    st.subheader("👥 Akun yang Sudah Diproses")
    if not managed:
        st.info("Belum ada akun dinamis yang diproses.")
        return

    summary = [
        {
            "Nama": row.get("full_name", ""),
            "Username": row.get("username", ""),
            "Jabatan": row.get("position", ""),
            "Role": row.get("role", ""),
            "Status": row.get("status", ""),
        }
        for row in managed
    ]
    st.dataframe(pd.DataFrame(summary), use_container_width=True, hide_index=True)

    for row in managed:
        username = str(row.get("username", ""))
        is_current_account = _same_username(username, st.session_state.get("auth_user"))
        status_label = {
            "ACTIVE": "Aktif",
            "SUSPENDED": "Dinonaktifkan",
            "REJECTED": "Ditolak",
        }.get(str(row.get("status") or "").upper(), str(row.get("status") or "-"))
        with st.expander(f"Atur @{username} · {status_label}", expanded=False):
            if is_current_account:
                st.info(
                    "Ini adalah akun yang sedang digunakan. Role dan status akun sendiri dikunci "
                    "agar Developer tidak kehilangan akses. Gunakan akun Developer lain untuk mengubahnya."
                )
            new_role = st.selectbox(
                "Role",
                ROLES,
                index=_role_index(str(row.get("role") or ROLE_STAFF)),
                key=f"edit_role_{username}",
                disabled=is_current_account,
            )
            current_status = str(row.get("status") or "SUSPENDED").upper()
            status_options = ["ACTIVE", "SUSPENDED"]
            new_status = st.selectbox(
                "Status",
                status_options,
                index=0 if current_status == "ACTIVE" else 1,
                key=f"edit_status_{username}",
                format_func=lambda value: (
                    "Aktif" if value == "ACTIVE" else "Dinonaktifkan"
                ),
                disabled=is_current_account,
            )
            developer_confirmed = True
            if new_role == ROLE_DEVELOPER:
                developer_confirmed = st.checkbox(
                    "Saya memahami akun Developer memiliki akses penuh",
                    key=f"edit_developer_confirm_{username}",
                )
            if st.button(
                "💾 Simpan Perubahan",
                use_container_width=True,
                disabled=is_current_account or not developer_confirmed,
                key=f"save_account_{username}",
            ):
                try:
                    update_account(username, new_role, new_status)
                    st.success(f"Akun {username} berhasil diperbarui.")
                    st.rerun()
                except Exception as exc:
                    show_api_error("Perubahan akun gagal", exc)
