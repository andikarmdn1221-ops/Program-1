"""Komponen dashboard, stok, riwayat, laporan, dan audit."""

import html

import pandas as pd
import plotly.express as px
import streamlit as st

from .config import (
    AUDIT_COLUMNS,
    AUTO_SYNC_ENABLED,
    AUTO_SYNC_SECONDS,
    RESTOCK_TARGET_MULTIPLIER,
    RIWAYAT_COLUMNS,
    SECONDARY_SYNC_SECONDS,
)
from .data import sync_if_changed
from .exports import excel_bytes, pdf_table
from .utils import (
    hari_ini_wib,
    natural_key,
    parse_tx_datetime,
    safe_int,
    sekarang_wib,
    status_stok,
)

def _live_fragment(run_every_seconds):
    if hasattr(st, "fragment"):
        return st.fragment(run_every=run_every_seconds)

    def decorator(func):
        return func
    return decorator


def _current_stock_view():
    stock_now = st.session_state.get("stok", {})
    master_now = st.session_state.get("master_info", {})
    active_now = {
        k: v for k, v in stock_now.items()
        if master_now.get(k, {}).get("status", "Aktif") == "Aktif"
    }
    critical_now = [
        k for k, v in active_now.items()
        if 0 < v <= master_now.get(k, {}).get("min_stok", 5)
    ]
    out_now = [k for k, v in active_now.items() if v <= 0]
    return stock_now, master_now, active_now, critical_now, out_now


def render_dashboard_kpis(active_count: int, total_stock: int, critical_count: int, out_count: int):
    """KPI berbasis HTML agar susunan 2x2 di HP tidak bergantung pada st.columns."""
    icons = {
        "package": (
            '<svg viewBox="0 0 24 24" aria-hidden="true">'
            '<path d="M21 8 12 3 3 8l9 5 9-5Z"/>'
            '<path d="m3 8 9 5 9-5v8l-9 5-9-5V8Z"/>'
            '<path d="M12 13v8"/></svg>'
        ),
        "stock": (
            '<svg viewBox="0 0 24 24" aria-hidden="true">'
            '<rect x="3" y="4" width="18" height="16" rx="2"/>'
            '<path d="M3 9h18M8 9v11M16 9v11"/></svg>'
        ),
        "critical": (
            '<svg viewBox="0 0 24 24" aria-hidden="true">'
            '<path d="M10.3 4.2 2.4 18a2 2 0 0 0 1.7 3h15.8a2 2 0 0 0 1.7-3L13.7 4.2a2 2 0 0 0-3.4 0Z"/>'
            '<path d="M12 9v4M12 17h.01"/></svg>'
        ),
        "empty": (
            '<svg viewBox="0 0 24 24" aria-hidden="true">'
            '<circle cx="12" cy="12" r="9"/>'
            '<path d="M12 7v6M12 17h.01"/></svg>'
        ),
    }
    cards = [
        ("wms-kpi-blue", icons["package"], "Barang Aktif", str(active_count)),
        ("wms-kpi-indigo", icons["stock"], "Total Stok", f"{total_stock} pcs"),
        ("wms-kpi-amber", icons["critical"], "Stok Kritis", str(critical_count)),
        ("wms-kpi-red", icons["empty"], "Stok Habis", str(out_count)),
    ]
    card_html = "".join(
        (
            f'<div class="wms-kpi-card {tone}">'
            f'<div class="wms-kpi-top">'
            f'<span class="wms-kpi-label">{html.escape(label)}</span>'
            f'<span class="wms-kpi-icon">{icon}</span>'
            f'</div>'
            f'<div class="wms-kpi-value">{html.escape(value)}</div>'
            f'</div>'
        )
        for tone, icon, label, value in cards
    )
    st.markdown(f'<div class="wms-kpi-grid">{card_html}</div>', unsafe_allow_html=True)


def render_stock_health(safe_count: int, critical_count: int, out_count: int):
    """Ringkasan status stok native HTML agar cepat dan stabil di semua perangkat."""
    total = safe_count + critical_count + out_count
    denominator = max(total, 1)
    safe_pct = round((safe_count / denominator) * 100, 2)
    critical_end = round(((safe_count + critical_count) / denominator) * 100, 2)
    chart_style = (
        f"--safe-end:{safe_pct}%;"
        f"--critical-end:{critical_end}%;"
    )
    st.markdown(
        f"""
        <div class="mirai-health-card">
            <div class="mirai-health-heading">
                <span class="mirai-health-title">Kesehatan Stok</span>
                <span class="mirai-health-badge">{total} item aktif</span>
            </div>
            <div class="mirai-health-content">
                <div class="mirai-donut" style="{chart_style}">
                    <div class="mirai-donut-center">
                        <strong>{total}</strong>
                        <span>Total Item</span>
                    </div>
                </div>
                <div class="mirai-health-legend">
                    <div><span class="mirai-dot mirai-dot-safe"></span><span>Aman</span><strong>{safe_count}</strong></div>
                    <div><span class="mirai-dot mirai-dot-critical"></span><span>Kritis</span><strong>{critical_count}</strong></div>
                    <div><span class="mirai-dot mirai-dot-empty"></span><span>Habis</span><strong>{out_count}</strong></div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


@_live_fragment(AUTO_SYNC_SECONDS if AUTO_SYNC_ENABLED else None)
def render_dashboard_live():
    sync_if_changed()
    stock_now, master_now, active_now, critical_now, out_now = _current_stock_view()

    sync_text = st.session_state.get("last_server_sync", "belum tersinkron")
    revision = st.session_state.get("server_revision", "-")
    if AUTO_SYNC_ENABLED:
        sync_label = (
            f"● Sinkron otomatis {AUTO_SYNC_SECONDS} dtk · "
            f"terakhir {sync_text} · rev {revision}"
        )
        st.markdown(
            f'<div class="wms-sync-pill">{html.escape(sync_label)}</div>',
            unsafe_allow_html=True,
        )

    connection_status = st.session_state.get("connection_status", "online")
    if connection_status == "recovering":
        st.warning(
            "Koneksi database sempat terlambat dan sedang dipulihkan otomatis. "
            "Data terakhir tetap ditampilkan; perubahan stok tetap diverifikasi ke server."
        )
    elif not st.session_state.get("is_connected"):
        st.error(
            "Database benar-benar tidak dapat dihubungi setelah beberapa percobaan. "
            "Dashboard menampilkan snapshot terakhir dan tidak boleh dianggap real-time."
        )

    if critical_now or out_now:
        alert_label = f"{len(out_now)} item habis · {len(critical_now)} item kritis"
        st.markdown(
            f'<div class="wms-alert-strip"><span>⚠️</span><span>{html.escape(alert_label)}</span></div>',
            unsafe_allow_html=True,
        )

    render_dashboard_kpis(
        active_count=len(active_now),
        total_stock=sum(active_now.values()),
        critical_count=len(critical_now),
        out_count=len(out_now),
    )

    st.markdown('<div class="mirai-section-divider"></div>', unsafe_allow_html=True)
    left, right = st.columns(2)
    with left:
        safe_count = len(active_now) - len(critical_now) - len(out_now)
        render_stock_health(safe_count, len(critical_now), len(out_now))

    with right:
        st.markdown(
            '<div class="mirai-section-heading"><span class="mirai-section-icon mirai-section-icon-red">!</span>'
            '<div><strong>Perlu Perhatian</strong><small>Item yang harus segera ditindaklanjuti</small></div></div>',
            unsafe_allow_html=True,
        )
        rows = []
        for nama in sorted(set(critical_now + out_now), key=natural_key):
            qty = active_now[nama]
            minimum = master_now.get(nama, {}).get("min_stok", 5)
            rows.append({
                "Nama Barang": nama,
                "Stok": qty,
                "Minimum": minimum,
                "Saran Restok": max((minimum * RESTOCK_TARGET_MULTIPLIER) - qty, 0),
                "Status": status_stok(qty, minimum),
            })
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.success("Semua stok aman.")

    st.markdown('<div class="mirai-section-divider"></div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="mirai-section-heading"><span class="mirai-section-icon">≡</span>'
        '<div><strong>Ringkasan Stok</strong><small>Cari dan periksa kondisi setiap barang</small></div></div>',
        unsafe_allow_html=True,
    )
    keyword = st.text_input("🔍 Cari barang", placeholder="Contoh: top coat", key="dashboard_search_live")
    rows = []
    for nama in sorted(stock_now, key=natural_key):
        if keyword and keyword.lower() not in nama.lower():
            continue
        info = master_now.get(nama, {})
        rows.append({
            "Nama Barang": nama,
            "Stok": stock_now[nama],
            "Batas Min": info.get("min_stok", 5),
            "Status Item": info.get("status", "Aktif"),
            "Status Stok": status_stok(stock_now[nama], info.get("min_stok", 5), info.get("status", "Aktif")),
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


@_live_fragment(AUTO_SYNC_SECONDS if AUTO_SYNC_ENABLED else None)
def render_stock_live():
    sync_if_changed()
    stock_now = st.session_state.get("stok", {})
    master_now = st.session_state.get("master_info", {})

    sync_text = st.session_state.get("last_server_sync", "belum tersinkron")
    if AUTO_SYNC_ENABLED:
        st.caption(f"🔄 Auto-sync aktif setiap {AUTO_SYNC_SECONDS} detik · sinkron terakhir {sync_text}")

    rows = []
    for nama in sorted(stock_now, key=natural_key):
        info = master_now.get(nama, {})
        rows.append({
            "Nama Barang": nama,
            "Jumlah Stok": stock_now[nama],
            "Batas Minimum": info.get("min_stok", 5),
            "Status Item": info.get("status", "Aktif"),
            "Indikator": status_stok(stock_now[nama], info.get("min_stok", 5), info.get("status", "Aktif")),
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)
    x1, x2 = st.columns(2)
    x1.download_button(
        "📥 Ekspor Excel", excel_bytes(df, "Stok"),
        f"Stok_{sekarang_wib().strftime('%Y%m%d')}.xlsx", use_container_width=True,
        key="download_stock_live",
    )
    pdf = pdf_table(
        "LAPORAN STOK GUDANG",
        ["Nama", "Stok", "Min", "Status Item", "Indikator"],
        [[r["Nama Barang"], r["Jumlah Stok"], r["Batas Minimum"], r["Status Item"], r["Indikator"]] for r in rows],
        [85, 25, 20, 30, 30],
    )
    x2.download_button(
        "📄 Cetak PDF", pdf,
        f"Stok_{sekarang_wib().strftime('%Y%m%d')}.pdf", use_container_width=True,
        key="download_stock_pdf_live",
    )



@_live_fragment(SECONDARY_SYNC_SECONDS if AUTO_SYNC_ENABLED else None)
def render_history_live():
    sync_if_changed()
    history_now = st.session_state.get("riwayat", [])
    sync_text = st.session_state.get("last_server_sync", "belum tersinkron")
    if AUTO_SYNC_ENABLED:
        st.caption(f"🔄 Riwayat sinkron otomatis tiap {SECONDARY_SYNC_SECONDS} detik · terakhir {sync_text}")
    if not st.session_state.get("is_connected"):
        st.warning("⚠️ Database offline. Riwayat yang tampil adalah snapshot sesi terakhir.")
    if not history_now:
        st.info("Belum ada riwayat transaksi.")
        return

    df = pd.DataFrame(history_now, columns=RIWAYAT_COLUMNS)
    f1, f2, f3 = st.columns(3)
    tipe_filter = f1.selectbox(
        "Tipe", ["SEMUA", "MASUK", "KELUAR", "PENYESUAIAN", "BARANG BARU"],
        key="history_type_live",
    )
    status_filter = f2.selectbox(
        "Status", ["SEMUA", "AKTIF", "VOID", "DIKOREKSI"],
        key="history_status_live",
    )
    search = f3.text_input("Cari barang / keterangan", key="history_search_live")

    if tipe_filter != "SEMUA":
        df = df[df["Tipe"] == tipe_filter]
    if status_filter != "SEMUA":
        df = df[df["Status"] == status_filter]
    if search:
        mask = (
            df["Barang"].astype(str).str.contains(search, case=False, na=False)
            | df["Pembeli / Keterangan"].astype(str).str.contains(search, case=False, na=False)
            | df["ID Transaksi"].astype(str).str.contains(search, case=False, na=False)
        )
        df = df[mask]

    column_config = {}
    if "Bukti URL" in df.columns:
        column_config["Bukti URL"] = st.column_config.LinkColumn("Bukti", display_text="📷 Buka Bukti")
    st.dataframe(df, use_container_width=True, hide_index=True, column_config=column_config)

    x1, x2 = st.columns(2)
    x1.download_button(
        "📥 Ekspor Riwayat Excel",
        excel_bytes(df, "Riwayat"),
        f"Riwayat_{sekarang_wib().strftime('%Y%m%d')}.xlsx",
        use_container_width=True,
        key="download_history_live",
    )
    pdf_rows = [
        [r["Waktu"], r["Tipe"], r["Barang"], r["Jumlah"], r["Pembeli / Keterangan"], r["Status"]]
        for _, r in df.iterrows()
    ]
    pdf = pdf_table(
        "RIWAYAT TRANSAKSI",
        ["Waktu", "Tipe", "Barang", "Qty", "Keterangan", "Status"],
        pdf_rows,
        [40, 25, 65, 20, 95, 30],
    )
    x2.download_button(
        "📄 Cetak Riwayat PDF",
        pdf,
        f"Riwayat_{sekarang_wib().strftime('%Y%m%d')}.pdf",
        use_container_width=True,
        key="download_history_pdf_live",
    )


@_live_fragment(SECONDARY_SYNC_SECONDS if AUTO_SYNC_ENABLED else None)
def render_reports_live():
    sync_if_changed()
    history_now = st.session_state.get("riwayat", [])
    sync_text = st.session_state.get("last_server_sync", "belum tersinkron")
    if AUTO_SYNC_ENABLED:
        st.caption(f"🔄 Laporan sinkron otomatis tiap {SECONDARY_SYNC_SECONDS} detik · terakhir {sync_text}")
    if not st.session_state.get("is_connected"):
        st.warning("⚠️ Database offline. Laporan menggunakan snapshot sesi terakhir.")

    d1, d2 = st.columns(2)
    today = hari_ini_wib()
    start = d1.date_input("Tanggal Mulai", value=today.replace(day=1), key="report_start_live")
    end = d2.date_input("Tanggal Selesai", value=today, key="report_end_live")
    if start > end:
        st.error("Tanggal mulai tidak boleh melebihi tanggal selesai.")
        return

    selected = []
    for tx in history_now:
        if tx.get("Status", "AKTIF") != "AKTIF":
            continue
        parsed = parse_tx_datetime(tx.get("Waktu", ""))
        if parsed and start <= parsed.date() <= end:
            selected.append(tx)
    if not selected:
        st.info("Tidak ada transaksi aktif pada periode ini.")
        return

    df = pd.DataFrame(selected, columns=RIWAYAT_COLUMNS)
    masuk = df.loc[df["Tipe"] == "MASUK", "Jumlah"].apply(safe_int).sum()
    keluar = df.loc[df["Tipe"] == "KELUAR", "Jumlah"].apply(safe_int).sum()
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Masuk", f"{masuk} pcs")
    m2.metric("Total Keluar", f"{keluar} pcs")
    m3.metric("Total Transaksi", len(df))

    movement = (
        df[df["Tipe"].isin(["MASUK", "KELUAR"])]
        .groupby(["Tanggal", "Tipe"], as_index=False)["Jumlah"]
        .sum()
    )
    if not movement.empty:
        movement["Tanggal Urut"] = pd.to_datetime(movement["Tanggal"], format="%d-%m-%Y", errors="coerce")
        movement = movement.sort_values("Tanggal Urut")
        fig = px.bar(
            movement,
            x="Tanggal",
            y="Jumlah",
            color="Tipe",
            barmode="group",
            color_discrete_map={"MASUK": "#22c55e", "KELUAR": "#ef4444"},
            title="Pergerakan Barang",
        )
        fig.update_layout(margin=dict(l=10, r=10, t=45, b=10), legend_orientation="h")
        st.plotly_chart(fig, use_container_width=True)

    top_out = (
        df[df["Tipe"] == "KELUAR"]
        .groupby("Barang", as_index=False)["Jumlah"]
        .sum()
        .sort_values("Jumlah", ascending=False)
        .head(10)
    )
    if not top_out.empty:
        st.subheader("📦 Barang Keluar Terbanyak")
        st.dataframe(top_out, use_container_width=True, hide_index=True)
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.download_button(
        "📥 Ekspor Laporan Excel",
        excel_bytes(df, "Laporan Periodik"),
        f"Laporan_{start}_{end}.xlsx",
        use_container_width=True,
        key="download_report_live",
    )


@_live_fragment(SECONDARY_SYNC_SECONDS if AUTO_SYNC_ENABLED else None)
def render_audit_live():
    sync_if_changed()
    audit_rows = st.session_state.get("audit", [])
    sync_text = st.session_state.get("last_server_sync", "belum tersinkron")
    if AUTO_SYNC_ENABLED:
        st.caption(f"🔄 Audit sinkron otomatis tiap {SECONDARY_SYNC_SECONDS} detik · terakhir {sync_text}")
    if not st.session_state.get("is_connected"):
        st.warning("⚠️ Database offline. Audit yang tampil adalah snapshot sesi terakhir.")
    if not audit_rows:
        st.info("Belum ada audit log.")
        return

    df_audit = pd.DataFrame(audit_rows, columns=AUDIT_COLUMNS)
    a1, a2, a3 = st.columns(3)
    users = [x for x in df_audit["User"].dropna().astype(str).unique() if x]
    roles = [x for x in df_audit["Role"].dropna().astype(str).unique() if x]
    user_filter = a1.selectbox("User", ["SEMUA"] + sorted(users), key="audit_user_live")
    role_filter = a2.selectbox("Role", ["SEMUA"] + sorted(roles), key="audit_role_live")
    audit_search = a3.text_input("Cari aksi / detail", key="audit_search_live")
    if user_filter != "SEMUA":
        df_audit = df_audit[df_audit["User"].astype(str) == user_filter]
    if role_filter != "SEMUA":
        df_audit = df_audit[df_audit["Role"].astype(str) == role_filter]
    if audit_search:
        mask = (
            df_audit["Aksi"].astype(str).str.contains(audit_search, case=False, na=False)
            | df_audit["Detail"].astype(str).str.contains(audit_search, case=False, na=False)
            | df_audit["ID Transaksi"].astype(str).str.contains(audit_search, case=False, na=False)
        )
        df_audit = df_audit[mask]
    st.dataframe(df_audit, use_container_width=True, hide_index=True)
    st.download_button(
        "📥 Ekspor Audit Excel",
        excel_bytes(df_audit, "Audit"),
        f"Audit_{sekarang_wib().strftime('%Y%m%d')}.xlsx",
        use_container_width=True,
        key="download_audit_live",
    )
