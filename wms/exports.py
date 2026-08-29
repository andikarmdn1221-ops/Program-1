"""Pembuatan ekspor Excel, PDF, dan backup lengkap."""

import io

import pandas as pd
import streamlit as st
from fpdf import FPDF

from .config import APP_VERSION, AUDIT_COLUMNS, RIWAYAT_COLUMNS
from .utils import natural_key, sanitize_pdf_text, waktu_display

@st.cache_data(ttl=180, show_spinner=False)
def excel_bytes(df, sheet_name="Data"):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    return output.getvalue()


@st.cache_data(ttl=180, show_spinner=False)
def full_backup_bytes(stock, master, history, audit):
    stock_rows = []
    for nama in sorted(stock, key=natural_key):
        info = master.get(nama, {})
        stock_rows.append(
            {
                "Nama Barang": nama,
                "Jumlah Stok": stock[nama],
                "Status": info.get("status", "Aktif"),
                "Batas Minimum": info.get("min_stok", 5),
            }
        )

    evidence_rows = []
    for tx in history:
        proof_url = str(tx.get("Bukti URL", "") or "").strip()
        if proof_url:
            evidence_rows.append({
                "ID Transaksi": tx.get("ID Transaksi", ""),
                "Waktu": tx.get("Waktu", ""),
                "Barang": tx.get("Barang", ""),
                "Bukti URL": proof_url,
            })

    readme_rows = [
        {"Keterangan": "Backup dibuat", "Nilai": waktu_display()},
        {"Keterangan": "Versi aplikasi", "Nilai": APP_VERSION},
        {"Keterangan": "Catatan bukti", "Nilai": "File Excel menyimpan manifest/URL bukti. File gambar asli tetap berada di Google Drive dan harus dibackup terpisah."},
    ]

    out = io.BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        pd.DataFrame(stock_rows).to_excel(writer, index=False, sheet_name="Stok Barang")
        pd.DataFrame(history, columns=RIWAYAT_COLUMNS).to_excel(writer, index=False, sheet_name="Riwayat")
        pd.DataFrame(audit, columns=AUDIT_COLUMNS).to_excel(writer, index=False, sheet_name="Audit")
        pd.DataFrame(evidence_rows, columns=["ID Transaksi", "Waktu", "Barang", "Bukti URL"]).to_excel(
            writer, index=False, sheet_name="Manifest Bukti"
        )
        pd.DataFrame(readme_rows).to_excel(writer, index=False, sheet_name="README")
    return out.getvalue()


@st.cache_data(ttl=180, show_spinner=False)
def pdf_table(title, headers, rows, col_widths, subtitle=""):
    pdf = FPDF(orientation="L" if sum(col_widths) > 195 else "P")
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, sanitize_pdf_text(title), ln=True, align="C")
    if subtitle:
        pdf.set_font("Helvetica", "I", 9)
        pdf.cell(0, 6, sanitize_pdf_text(subtitle), ln=True, align="C")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 6, f"Dicetak: {sanitize_pdf_text(waktu_display())}", ln=True, align="C")
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 8)
    for i, header in enumerate(headers):
        pdf.cell(col_widths[i], 8, sanitize_pdf_text(header), border=1, align="C")
    pdf.ln()
    pdf.set_font("Helvetica", "", 7)
    for row in rows:
        for i, value in enumerate(row):
            pdf.cell(col_widths[i], 7, sanitize_pdf_text(value)[:60], border=1)
        pdf.ln()
    return bytes(pdf.output())
