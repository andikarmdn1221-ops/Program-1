"""Halaman status pengiriman Telegram pada sesi aktif."""

import pandas as pd
import streamlit as st

from ..auth import actor_label, current_role
from ..config import ROLE_BOSS, ROLE_DEVELOPER, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from ..notifications import deliver_notification
from ..utils import waktu_display

def render_notification_status_page():
    st.write("Hasil pengiriman Telegram selama sesi login ini. Transaksi database tetap dicatat meskipun Telegram gagal.")
    n1, n2, n3 = st.columns(3)
    notification_rows = list(st.session_state.get("notification_log", []))
    sent_count = sum(1 for row in notification_rows if row.get("Status") == "TERKIRIM")
    failed_count = sum(1 for row in notification_rows if row.get("Status") == "GAGAL")
    n1.metric("Dicatat", len(notification_rows))
    n2.metric("Terkirim", sent_count)
    n3.metric("Gagal", failed_count)

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        st.warning("Telegram belum dikonfigurasi di Streamlit Secrets.")
    elif notification_rows:
        st.dataframe(pd.DataFrame(notification_rows), use_container_width=True, hide_index=True)
    else:
        st.info("Belum ada pengiriman notifikasi pada sesi ini.")

    if current_role() in {ROLE_DEVELOPER, ROLE_BOSS} and TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        if st.button("🧪 Kirim Pesan Tes Sekarang", use_container_width=True):
            ok, detail = deliver_notification(
                f"✅ Tes notifikasi Mirai\n{waktu_display()}\n👤 {actor_label()}",
                "Tes manual",
            )
            if ok:
                st.success(detail)
            else:
                st.error(f"Tes Telegram gagal: {detail}")
