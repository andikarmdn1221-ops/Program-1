"""Halaman barang masuk/keluar, penyesuaian, koreksi, dan void."""

from datetime import datetime

import streamlit as st

from ..api import show_api_error
from ..auth import actor_label, notification_flash, require_permission
from ..config import MAX_UPLOAD_MB
from ..data import require_online_operation, sync_if_changed
from ..notifications import deliver_notification
from ..operations import adjust_stock, correct_transaction, do_transaction, void_transaction
from ..utils import (
    combine_manual_date,
    compress_image,
    hari_ini_wib,
    natural_key,
    parse_tx_datetime,
    safe_int,
)

def render_transaction_page(active_menu):
    require_permission("transaction")
    sync_if_changed()
    stock = st.session_state.get("stok", {})
    master = st.session_state.get("master_info", {})
    tipe = "MASUK" if active_menu == "Barang Masuk" else "KELUAR"
    names = sorted(
        [k for k in stock if master.get(k, {}).get("status", "Aktif") == "Aktif"],
        key=natural_key,
    )
    if not names:
        st.warning("Tidak ada barang aktif.")
    else:
        # MENGELUARKAN SELECTBOX DARI FORM AGAR STOK SELALU UPDATE
        barang = st.selectbox("Pilih Barang", names)
        st.info(f"Stok saat ini: **{stock.get(barang, 0)} pcs**")

        with st.form(f"tx_{tipe.lower()}", clear_on_submit=True):
            jumlah = st.number_input("Jumlah (pcs)", min_value=1, value=1, step=1)
            tgl = st.date_input("Tanggal Transaksi", value=hari_ini_wib())
            label_ket = (
                "Pemasok / Keterangan"
                if tipe == "MASUK"
                else "Penerima / Keperluan"
            )
            keterangan = st.text_input(label_ket, "" if tipe == "KELUAR" else "-")
            bukti = st.file_uploader(
                "Upload Bukti / Nota (Opsional)" if tipe == "MASUK" else "Upload Surat Jalan (Opsional)",
                type=["jpg", "jpeg", "png", "jfif", "webp"],
            )
            st.caption(f"JPG/PNG/WEBP · maksimal {MAX_UPLOAD_MB} MB · otomatis dikompres")
            submit = st.form_submit_button(
                "📥 Simpan Barang Masuk" if tipe == "MASUK" else "📤 Simpan Pengiriman",
                use_container_width=True,
            )

        if submit:
            if tipe == "KELUAR" and not keterangan.strip():
                st.warning("Penerima atau keperluan barang wajib diisi.")
            else:
                try:
                    require_online_operation()
                    image_bytes = compress_image(bukti) if bukti else None
                    result = do_transaction(
                        tipe,
                        barang,
                        jumlah,
                        tgl,
                        keterangan,
                        bukti,
                        image_bytes=image_bytes,
                        expected_stock_before=stock.get(barang, 0),
                    )
                    proof_url = result.get("file_url", "")
                    remaining = result.get("stok_akhir", st.session_state.stok.get(barang, 0))
                    symbol = "➕" if tipe == "MASUK" else "➖"
                    msg = (
                        f"{'📥' if tipe == 'MASUK' else '📤'} *BARANG {tipe}*\n"
                        f"📦 {barang}\n{symbol} {jumlah} pcs\n"
                        f"📅 {tgl.strftime('%d-%m-%Y')}\n"
                        f"📝 {keterangan.strip() or '-'}\n📊 Sisa: {remaining} pcs\n👤 {actor_label()}"
                    )
                    if proof_url:
                        msg += f"\n📁 {proof_url}"
                    notification_results = [
                        deliver_notification(msg, f"Transaksi {tipe}", image_bytes)
                    ]
                    alert = result.get("alert")
                    if alert:
                        notification_results.append(
                            deliver_notification(alert, "Peringatan stok")
                        )
                    notification_flash(
                        f"Transaksi berhasil. Stok akhir: {remaining} pcs.",
                        notification_results,
                    )
                    st.rerun()
                except Exception as exc:
                    show_api_error("Transaksi gagal", exc)

def render_adjustment_page():
    require_permission("stock_adjust")
    sync_if_changed()
    stock = st.session_state.get("stok", {})
    master = st.session_state.get("master_info", {})
    st.info("Gunakan fitur ini saat stok fisik berbeda dari stok sistem. Semua perubahan dicatat di riwayat dan audit log.")
    names = sorted(
        [k for k in stock if master.get(k, {}).get("status", "Aktif") == "Aktif"],
        key=natural_key,
    )
    if not names:
        st.warning("Tidak ada barang aktif.")
    else:
        # MENGELUARKAN SELECTBOX DARI FORM AGAR STOK SELALU UPDATE
        barang = st.selectbox("Pilih Barang", names)
        stok_lama = stock.get(barang, 0)
        st.metric("Stok Sistem Saat Ini", f"{stok_lama} pcs")

        with st.form("stock_adjustment", clear_on_submit=False):
            stok_baru = st.number_input("Stok Fisik / Stok Baru", min_value=0, value=int(stok_lama), step=1)
            tgl = st.date_input("Tanggal Penyesuaian", value=hari_ini_wib())
            alasan = st.text_area("Alasan Penyesuaian", placeholder="Contoh: hasil stock opname / selisih pencatatan")
            submit_adjust = st.form_submit_button("🧮 Simpan Penyesuaian Stok", use_container_width=True)

        if submit_adjust:
            if int(stok_baru) == int(stok_lama):
                st.warning("Stok baru sama dengan stok saat ini. Tidak ada perubahan.")
            elif not alasan.strip():
                st.warning("Alasan penyesuaian wajib diisi.")
            else:
                try:
                    require_online_operation()
                    result = adjust_stock(barang, stok_baru, alasan, tgl, stok_lama)
                    delta = result.get("selisih", int(stok_baru) - int(stok_lama))
                    notification_results = [deliver_notification(
                        f"🧮 *PENYESUAIAN STOK*\n📦 {barang}\n"
                        f"Stok lama: {stok_lama} pcs\nStok baru: {stok_baru} pcs\n"
                        f"Selisih: {delta:+d} pcs\n📝 {alasan.strip()}\n👤 {actor_label()}",
                        "Penyesuaian stok",
                    )]
                    alert = result.get("alert")
                    if alert:
                        notification_results.append(deliver_notification(alert, "Peringatan stok"))
                    notification_flash(
                        "Penyesuaian stok berhasil dan tercatat di audit log.",
                        notification_results,
                    )
                    st.rerun()
                except Exception as exc:
                    show_api_error("Penyesuaian stok gagal", exc)

def render_correction_page():
    require_permission("correct_transaction")
    sync_if_changed()
    stock = st.session_state.get("stok", {})
    master = st.session_state.get("master_info", {})
    history = st.session_state.get("riwayat", [])
    editable = [tx for tx in history if tx.get("Status", "AKTIF") == "AKTIF" and tx.get("Tipe") in ("MASUK", "KELUAR")]
    editable.sort(
        key=lambda tx: parse_tx_datetime(tx.get("Waktu", "")) or datetime.min,
        reverse=True,
    )
    if not editable:
        st.info("Tidak ada transaksi aktif yang dapat dikoreksi.")
    else:
        labels = {
            tx["ID Transaksi"]: f"[{tx['Waktu']}] {tx['Tipe']} · {tx['Barang']} · {tx['Jumlah']} pcs · {tx['Pembeli / Keterangan']}"
            for tx in editable[:200]
        }
        selected_id = st.selectbox("Pilih Transaksi", list(labels), format_func=lambda x: labels[x])
        old = next(tx for tx in editable if tx["ID Transaksi"] == selected_id)

        with st.form("correct_tx"):
            st.caption(f"ID asli: {old['ID Transaksi']}")
            try:
                default_date = datetime.strptime(old.get("Tanggal", ""), "%d-%m-%Y").date()
            except ValueError:
                parsed = parse_tx_datetime(old.get("Waktu", ""))
                default_date = parsed.date() if parsed else hari_ini_wib()
            tgl = st.date_input("Tanggal", value=default_date)
            tipe = st.selectbox("Tipe", ["MASUK", "KELUAR"], index=0 if old["Tipe"] == "MASUK" else 1)
            names = sorted([k for k in stock if master.get(k, {}).get("status", "Aktif") == "Aktif"], key=natural_key)
            if old["Barang"] not in names:
                names.insert(0, old["Barang"])
            idx = names.index(old["Barang"]) if old["Barang"] in names else 0
            barang = st.selectbox("Barang", names, index=idx)
            jumlah = st.number_input("Jumlah", min_value=1, value=max(1, safe_int(old["Jumlah"])), step=1)
            ket = st.text_input(
                "Penerima / Keperluan",
                value=str(old["Pembeli / Keterangan"]),
            )
            save = st.form_submit_button("💾 Simpan Koreksi", use_container_width=True)

        if save:
            new_tx = {
                "Waktu": combine_manual_date(tgl),
                "Tanggal": tgl.strftime("%d-%m-%Y"),
                "Tipe": tipe,
                "Barang": barang,
                "Jumlah": jumlah,
                "Pembeli / Keterangan": ket.strip() or "-",
            }
            try:
                require_online_operation()
                result = correct_transaction(old, new_tx)
                notification = deliver_notification(
                    f"✏️ *KOREKSI TRANSAKSI*\nID: {old['ID Transaksi']}\n"
                    f"Lama: {old['Tipe']} {old['Barang']} {old['Jumlah']} pcs\n"
                    f"Baru: {tipe} {barang} {jumlah} pcs\n👤 {actor_label()}",
                    "Koreksi transaksi",
                )
                notification_flash(
                    f"Koreksi tersimpan sebagai transaksi baru {result.get('new_tx_id', '')}.",
                    [notification],
                )
                st.rerun()
            except Exception as exc:
                show_api_error("Koreksi gagal", exc)

        st.divider()
        st.warning("Void membatalkan transaksi tanpa menghapus jejak audit.")
        confirm_void = st.checkbox("Saya yakin ingin membatalkan transaksi ini")
        if st.button("🚫 Void Transaksi", disabled=not confirm_void):
            try:
                require_online_operation()
                void_transaction(old["ID Transaksi"])
                notification = deliver_notification(
                    f"🚫 *VOID TRANSAKSI*\nID: {old['ID Transaksi']}\n{old['Tipe']} {old['Barang']} {old['Jumlah']} pcs\n👤 {actor_label()}",
                    "Void transaksi",
                )
                notification_flash(
                    "Transaksi dibatalkan dan stok dikembalikan secara aman.",
                    [notification],
                )
                st.rerun()
            except Exception as exc:
                show_api_error("Void gagal", exc)
