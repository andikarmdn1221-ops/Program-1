"""Utilitas umum: waktu, validasi input, signature, dan gambar."""

import base64
import hashlib
import hmac
import io
import json
import re
import time
import uuid
from datetime import date, datetime

import pandas as pd
import requests
from PIL import Image

from .config import (
    API_SHARED_KEY,
    AUTH_SIGNING_KEY,
    MAX_UPLOAD_MB,
    TELEGRAM_BOT_TOKEN,
    WIB,
)

def sekarang_wib() -> datetime:
    return datetime.now(WIB)


def hari_ini_wib() -> date:
    """Tanggal operasional harus mengikuti WIB, bukan zona waktu server cloud."""
    return sekarang_wib().date()


def waktu_display() -> str:
    return sekarang_wib().strftime("%d %b %Y, %H:%M WIB")


def safe_int(value, default=0) -> int:
    try:
        if value is None or pd.isna(value):
            return default
        txt = str(value).strip()
        return int(float(txt)) if txt else default
    except (TypeError, ValueError):
        return default


def clean_item_name(value: str) -> str:
    """Rapikan nama item dan tolak input yang berisiko merusak tampilan/sheet."""
    name = re.sub(r"\s+", " ", str(value or "")).strip()
    if not name:
        raise ValueError("Nama barang wajib diisi")
    if len(name) > 80:
        raise ValueError("Nama barang maksimal 80 karakter")
    if any(ord(ch) < 32 for ch in name):
        raise ValueError("Nama barang mengandung karakter yang tidak valid")
    return name


def clean_note(value: str, *, required=False, max_length=240) -> str:
    note = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", str(value or "")).strip()
    if required and not note:
        raise ValueError("Keterangan wajib diisi")
    if len(note) > max_length:
        raise ValueError(f"Keterangan maksimal {max_length} karakter")
    return note or "-"


def redact_sensitive(value) -> str:
    """Hilangkan secret dari pesan error sebelum tampil ke UI/log."""
    text = str(value or "")
    for secret_value, label in (
        (API_SHARED_KEY, "***API_KEY***"),
        (AUTH_SIGNING_KEY, "***SIGNING_KEY***"),
        (TELEGRAM_BOT_TOKEN, "***TELEGRAM_TOKEN***"),
    ):
        if secret_value:
            text = text.replace(str(secret_value), label)
    # Redaksi key pada query URL jika exception requests menyertakan URL lengkap.
    text = re.sub(r"([?&](?:key|api_key)=)[^&\s]+", r"\1***REDACTED***", text, flags=re.I)
    return text


def api_error_detail(exc: Exception) -> str:
    """Pesan jaringan yang informatif tanpa membocorkan URL/secret."""
    if isinstance(exc, requests.exceptions.Timeout):
        return "koneksi ke server timeout"
    if isinstance(exc, requests.exceptions.HTTPError):
        status = getattr(getattr(exc, "response", None), "status_code", None)
        return f"server mengembalikan HTTP {status}" if status else "server mengembalikan HTTP error"
    if isinstance(exc, requests.exceptions.ConnectionError):
        return "server tidak dapat dijangkau"
    if isinstance(exc, requests.exceptions.RequestException):
        return "gangguan jaringan/API"
    return redact_sensitive(exc)


def make_request_signature(payload: dict) -> dict:
    """
    Tanda tangani SELURUH isi mutation payload (bukan hanya actor/role).
    Ini mencegah perubahan barang/jumlah/keterangan setelah request ditandatangani.
    AUTH_SIGNING_KEY wajib diisi bila backend Code.gs final-security digunakan.
    """
    if not AUTH_SIGNING_KEY:
        return payload

    ts = str(int(time.time()))
    nonce = uuid.uuid4().hex

    # Payload pada tahap ini belum berisi api_key / field auth.
    # Sort key + compact JSON dibuat sama dengan stableStringify_ di Code.gs.
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    body_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    message = f"{body_hash}|{ts}|{nonce}"
    signature = hmac.new(
        str(AUTH_SIGNING_KEY).encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return {
        **payload,
        "auth_ts": ts,
        "auth_nonce": nonce,
        "auth_body_sha256": body_hash,
        "auth_sig": signature,
    }


def natural_key(text: str):
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r"(\d+)", str(text))]


def make_tx_id(prefix="TRX") -> str:
    return f"{prefix}-{sekarang_wib().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"


def combine_manual_date(tgl: date) -> str:
    jam = sekarang_wib().strftime("%H:%M")
    return f"{tgl.strftime('%d-%m-%Y')} {jam}"


def parse_tx_datetime(value: str):
    txt = str(value or "").strip()
    for fmt in ("%d-%m-%Y %H:%M", "%d %b %Y, %H:%M WIB", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(txt, fmt)
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(txt.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def status_stok(jumlah: int, min_stok: int, status_item="Aktif") -> str:
    if status_item != "Aktif":
        return "NONAKTIF"
    if jumlah <= 0:
        return "HABIS"
    if jumlah <= min_stok:
        return "KRITIS"
    return "AMAN"


def sanitize_pdf_text(value) -> str:
    return str(value).strip().encode("latin-1", "replace").decode("latin-1")


def compress_image(uploaded_file, max_size=(1200, 1200), quality=80):
    if uploaded_file is None:
        return None
    try:
        file_size = getattr(uploaded_file, "size", None)
        if file_size is None and hasattr(uploaded_file, "getbuffer"):
            file_size = len(uploaded_file.getbuffer())
        if file_size and file_size > MAX_UPLOAD_MB * 1024 * 1024:
            raise ValueError(f"Ukuran gambar maksimal {MAX_UPLOAD_MB} MB")

        uploaded_file.seek(0)
        img = Image.open(uploaded_file)
        img.verify()
        uploaded_file.seek(0)
        img = Image.open(uploaded_file)
        if img.mode != "RGB":
            img = img.convert("RGB")
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        output = io.BytesIO()
        img.save(output, format="JPEG", quality=quality, optimize=True)
        return output.getvalue()
    except Exception as exc:
        raise ValueError(f"Bukti gambar tidak valid: {redact_sensitive(exc)}") from exc


def to_image_payload(uploaded_file, image_bytes=None):
    if uploaded_file is None:
        return {}
    raw = image_bytes if image_bytes is not None else compress_image(uploaded_file)
    if not raw:
        return {}
    original_name = re.sub(r"[^A-Za-z0-9._-]+", "_", str(getattr(uploaded_file, "name", "bukti")))
    original_stem = original_name.rsplit(".", 1)[0] or "bukti"
    return {
        "image_base64": base64.b64encode(raw).decode("utf-8"),
        "image_name": f"{sekarang_wib().strftime('%Y%m%d_%H%M%S')}_{original_stem}.jpg",
        "image_mime": "image/jpeg",
    }
