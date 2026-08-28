import base64
import hashlib
import hmac
import html
import io
import json
import re
import secrets
import time
import uuid
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.express as px
import requests
import streamlit as st
from fpdf import FPDF
from PIL import Image


# ============================================================
# KONFIGURASI
# ============================================================
st.set_page_config(
    page_title="Microcement Warehouse",
    page_icon="📦",
    layout="wide",
)


# ============================================================
# RESPONSIVE UI (MOBILE / TABLET)
# Hanya mengatur tampilan pada layar kecil.
# Fitur dan logika stok tetap sama.
# ============================================================
def inject_responsive_css():
    st.markdown(
        r"""
        <style>
        /* =====================================================
           v8.0 PRODUCTION + MOBILE
           Desktop tetap lebar; iPhone/Android dibuat touch-safe.
           ===================================================== */
        html, body, [class*="css"] {
            -webkit-text-size-adjust: 100%;
        }

        /* Tampilan lebih bersih tanpa mengubah komponen bawaan Streamlit. */
        .block-container {
            padding-top: 2rem;
            max-width: 1440px;
        }
        [data-testid="stMetric"] {
            border: 1px solid rgba(128, 128, 128, 0.18);
            border-radius: 0.85rem;
            padding: 0.75rem 0.9rem;
            background: rgba(128, 128, 128, 0.035);
        }

        /* Kartu KPI khusus dashboard: stabil di desktop dan ringkas di HP. */
        .wms-kpi-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 0.8rem;
            margin: 0.75rem 0 1.15rem 0;
        }
        .wms-kpi-card {
            position: relative;
            overflow: hidden;
            min-width: 0;
            min-height: 7rem;
            padding: 1rem 1.05rem;
            border: 1px solid rgba(15, 23, 42, 0.10);
            border-radius: 1rem;
            background: #ffffff;
            box-shadow: 0 4px 16px rgba(15, 23, 42, 0.055);
        }
        .wms-kpi-card::after {
            content: "";
            position: absolute;
            right: -1.5rem;
            bottom: -2.2rem;
            width: 6rem;
            height: 6rem;
            border-radius: 999px;
            background: var(--kpi-soft);
        }
        .wms-kpi-top {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 0.5rem;
            margin-bottom: 0.55rem;
        }
        .wms-kpi-label {
            min-width: 0;
            color: #64748b;
            font-size: 0.82rem;
            font-weight: 650;
            line-height: 1.25;
        }
        .wms-kpi-icon {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            flex: 0 0 2rem;
            width: 2rem;
            height: 2rem;
            border-radius: 0.65rem;
            background: var(--kpi-soft);
            color: var(--kpi-color);
            font-size: 1rem;
        }
        .wms-kpi-value {
            position: relative;
            z-index: 1;
            color: #0f172a;
            font-size: 1.9rem;
            font-weight: 750;
            line-height: 1.08;
            letter-spacing: -0.035em;
            white-space: nowrap;
        }
        .wms-kpi-blue { --kpi-color: #2563eb; --kpi-soft: #dbeafe; border-top: 3px solid #3b82f6; }
        .wms-kpi-indigo { --kpi-color: #4f46e5; --kpi-soft: #e0e7ff; border-top: 3px solid #6366f1; }
        .wms-kpi-amber { --kpi-color: #b45309; --kpi-soft: #fef3c7; border-top: 3px solid #f59e0b; }
        .wms-kpi-red { --kpi-color: #dc2626; --kpi-soft: #fee2e2; border-top: 3px solid #ef4444; }

        .wms-sync-pill {
            display: inline-flex;
            align-items: center;
            max-width: 100%;
            margin: 0.1rem 0 0.65rem 0;
            padding: 0.36rem 0.65rem;
            border: 1px solid #dbeafe;
            border-radius: 999px;
            background: #eff6ff;
            color: #475569;
            font-size: 0.78rem;
            line-height: 1.25;
            overflow-wrap: anywhere;
        }
        .wms-alert-strip {
            display: flex;
            align-items: center;
            gap: 0.7rem;
            margin: 0.15rem 0 0.75rem 0;
            padding: 0.78rem 0.9rem;
            border: 1px solid #fde68a;
            border-left: 4px solid #f59e0b;
            border-radius: 0.85rem;
            background: #fffbeb;
            color: #92400e;
            font-weight: 650;
            line-height: 1.3;
        }
        .wms-refresh-anchor { display: none; }
        [data-testid="stAlert"] {
            border-radius: 0.8rem;
        }

        /* Tombol/link tidak memotong label panjang. */
        .stButton > button,
        .stDownloadButton > button,
        [data-testid="stFormSubmitButton"] > button,
        [data-testid="stLinkButton"] a {
            white-space: normal !important;
            overflow-wrap: anywhere !important;
        }

        @media (max-width: 768px) {
            /* Rapikan chrome Streamlit tanpa menghilangkan tombol sidebar. */
            [data-testid="stToolbar"],
            [data-testid="stDecoration"],
            #MainMenu {
                display: none !important;
            }

            /* Safe-area penting untuk iPhone dengan notch / Dynamic Island. */
            .block-container {
                padding-top: max(2.9rem, calc(2.45rem + env(safe-area-inset-top))) !important;
                padding-left: max(0.72rem, env(safe-area-inset-left)) !important;
                padding-right: max(0.72rem, env(safe-area-inset-right)) !important;
                padding-bottom: max(1.4rem, env(safe-area-inset-bottom)) !important;
                max-width: 100% !important;
            }

            /* Sidebar menjadi panel yang muat di iPhone/Android kecil. */
            section[data-testid="stSidebar"] {
                width: min(88vw, 320px) !important;
                min-width: min(88vw, 320px) !important;
            }
            section[data-testid="stSidebar"] > div {
                width: min(88vw, 320px) !important;
            }

            /* Kolom ditumpuk supaya form tidak terpotong. */
            [data-testid="stHorizontalBlock"] {
                flex-wrap: wrap !important;
                gap: 0.55rem !important;
            }
            [data-testid="column"] {
                flex: 1 1 100% !important;
                width: 100% !important;
                min-width: 0 !important;
            }

            /* Header tetap satu baris: judul di kiri, refresh ringkas di kanan. */
            [data-testid="stHorizontalBlock"]:has(.wms-refresh-anchor) {
                display: flex !important;
                flex-wrap: nowrap !important;
                align-items: center !important;
                gap: 0.45rem !important;
                margin-bottom: -0.25rem !important;
            }
            [data-testid="stHorizontalBlock"]:has(.wms-refresh-anchor) > [data-testid="column"]:first-child {
                flex: 1 1 auto !important;
                width: calc(100% - 3.45rem) !important;
            }
            [data-testid="stHorizontalBlock"]:has(.wms-refresh-anchor) > [data-testid="column"]:last-child {
                flex: 0 0 3rem !important;
                width: 3rem !important;
            }
            [data-testid="stHorizontalBlock"]:has(.wms-refresh-anchor) [data-testid="stMarkdownContainer"]:has(.wms-refresh-anchor) {
                display: none !important;
            }
            [data-testid="stHorizontalBlock"]:has(.wms-refresh-anchor) .stButton > button {
                width: 3rem !important;
                min-height: 2.8rem !important;
                height: 2.8rem !important;
                padding: 0 !important;
                border-radius: 0.8rem !important;
                font-size: 1.05rem !important;
            }

            /* Metric bawaan pada halaman lain menjadi grid 2 kolom. */
            [data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]) {
                display: grid !important;
                grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
                gap: 0.55rem !important;
            }
            [data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]) > [data-testid="column"] {
                width: auto !important;
                min-width: 0 !important;
                flex: none !important;
            }

            h1 {
                font-size: 1.52rem !important;
                line-height: 1.18 !important;
                overflow-wrap: anywhere !important;
                margin-top: 0 !important;
            }
            h2 { font-size: 1.28rem !important; line-height: 1.2 !important; }
            h3 { font-size: 1.08rem !important; }
            hr {
                margin-top: 0.6rem !important;
                margin-bottom: 0.65rem !important;
            }

            /* 16px mencegah Safari iOS melakukan zoom otomatis saat input fokus. */
            input, textarea, select,
            [data-baseweb="select"] input {
                font-size: 16px !important;
            }

            /* Target sentuh minimal ~48px. */
            .stButton > button,
            .stDownloadButton > button,
            [data-testid="stFormSubmitButton"] > button,
            [data-testid="stLinkButton"] a {
                width: 100% !important;
                min-height: 3rem !important;
                font-size: 0.95rem !important;
                padding: 0.55rem 0.75rem !important;
            }

            [data-testid="stMetric"] {
                min-height: 5.6rem !important;
                padding: 0.7rem 0.75rem !important;
                border-radius: 0.85rem !important;
            }
            [data-testid="stMetricValue"] {
                font-size: 1.4rem !important;
                line-height: 1.12 !important;
            }

            .wms-kpi-grid {
                grid-template-columns: repeat(2, minmax(0, 1fr));
                gap: 0.55rem;
                margin: 0.55rem 0 0.8rem 0;
            }
            .wms-kpi-card {
                min-height: 6.05rem;
                padding: 0.72rem 0.75rem;
                border-radius: 0.85rem;
                box-shadow: 0 3px 11px rgba(15, 23, 42, 0.045);
            }
            .wms-kpi-top { margin-bottom: 0.4rem; }
            .wms-kpi-label { font-size: 0.74rem; }
            .wms-kpi-icon {
                flex-basis: 1.75rem;
                width: 1.75rem;
                height: 1.75rem;
                border-radius: 0.55rem;
                font-size: 0.88rem;
            }
            .wms-kpi-value { font-size: 1.52rem; }
            .wms-sync-pill {
                display: flex;
                width: fit-content;
                margin-bottom: 0.55rem;
                padding: 0.32rem 0.55rem;
                border-radius: 0.65rem;
                font-size: 0.72rem;
            }
            .wms-alert-strip {
                gap: 0.55rem;
                margin-bottom: 0.65rem;
                padding: 0.66rem 0.72rem;
                border-radius: 0.72rem;
                font-size: 0.86rem;
            }

            /* Tabs dapat digeser horizontal, tidak memaksa layar melebar. */
            [data-baseweb="tab-list"] {
                overflow-x: auto !important;
                scrollbar-width: thin;
                white-space: nowrap !important;
            }

            /* Dataframe & chart tidak membuat horizontal page overflow. */
            [data-testid="stDataFrame"],
            [data-testid="stPlotlyChart"],
            [data-testid="stPlotlyChart"] > div {
                width: 100% !important;
                max-width: 100% !important;
            }
            [data-testid="stDataFrame"] {
                overflow-x: auto !important;
            }

            /* Uploader tetap berada di viewport HP. */
            [data-testid="stFileUploader"],
            [data-testid="stFileUploaderDropzone"] {
                max-width: 100% !important;
                min-width: 0 !important;
            }
            [data-testid="stFileUploaderDropzone"] {
                padding: 0.75rem !important;
            }

            [data-testid="stAlert"],
            [data-testid="stCaptionContainer"] {
                line-height: 1.35 !important;
                overflow-wrap: anywhere !important;
            }

            /* Navigasi sidebar lebih enak disentuh. */
            section[data-testid="stSidebar"] [role="radiogroup"] label {
                min-height: 2.2rem !important;
                padding-top: 0.15rem !important;
                padding-bottom: 0.15rem !important;
            }
        }

        @media (max-width: 430px) {
            .block-container {
                padding-top: max(2.7rem, calc(2.25rem + env(safe-area-inset-top))) !important;
                padding-left: max(0.52rem, env(safe-area-inset-left)) !important;
                padding-right: max(0.52rem, env(safe-area-inset-right)) !important;
            }
            h1 { font-size: 1.36rem !important; }
            [data-testid="stMetricValue"] { font-size: 1.30rem !important; }
            .wms-kpi-card { min-height: 5.8rem; padding: 0.66rem 0.68rem; }
            .wms-kpi-label { font-size: 0.7rem; }
            .wms-kpi-value { font-size: 1.4rem; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

inject_responsive_css()

WIB = ZoneInfo("Asia/Jakarta")
APP_VERSION = "8.0-pro-mobile"
EXPECTED_BACKEND_VERSION = "7.1-production"
URL_GSHEET_API = st.secrets.get("URL_GSHEET_API", "")
API_SHARED_KEY = st.secrets.get("API_SHARED_KEY", "")
AUTH_SIGNING_KEY = st.secrets.get("AUTH_SIGNING_KEY", "")
TELEGRAM_BOT_TOKEN = st.secrets.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = st.secrets.get("TELEGRAM_CHAT_ID", "")
ALLOW_NO_LOGIN = bool(st.secrets.get("ALLOW_NO_LOGIN", False))

# Pengaturan keamanan / reliabilitas. Semua punya default aman dan tetap kompatibel.
DATA_CACHE_TTL_SECONDS = max(15, int(st.secrets.get("DATA_CACHE_TTL_SECONDS", 30)))
LOGIN_MAX_ATTEMPTS = max(3, int(st.secrets.get("LOGIN_MAX_ATTEMPTS", 5)))
LOGIN_LOCK_SECONDS = max(30, int(st.secrets.get("LOGIN_LOCK_SECONDS", 300)))
SESSION_TIMEOUT_MINUTES = max(5, int(st.secrets.get("SESSION_TIMEOUT_MINUTES", 60)))
TELEGRAM_RETRY_ATTEMPTS = max(1, min(5, int(st.secrets.get("TELEGRAM_RETRY_ATTEMPTS", 3))))
OFFLINE_USE_DEFAULT_STOCK = bool(st.secrets.get("OFFLINE_USE_DEFAULT_STOCK", False))
SERVER_EMPTY_USE_DEFAULT_STOCK = bool(st.secrets.get("SERVER_EMPTY_USE_DEFAULT_STOCK", False))
PBKDF2_ITERATIONS = max(200_000, int(st.secrets.get("PBKDF2_ITERATIONS", 310_000)))
AUTO_SYNC_ENABLED = bool(st.secrets.get("AUTO_SYNC_ENABLED", True))
AUTO_SYNC_SECONDS = max(20, int(st.secrets.get("AUTO_SYNC_SECONDS", 30)))
HEALTH_TIMEOUT_SECONDS = max(3, min(12, int(st.secrets.get("HEALTH_TIMEOUT_SECONDS", 5))))
WRITE_BLOCK_WHEN_OFFLINE = bool(st.secrets.get("WRITE_BLOCK_WHEN_OFFLINE", True))
REQUIRE_HMAC = bool(st.secrets.get("REQUIRE_HMAC", True))
ALLOW_LEGACY_PASSWORDS = bool(st.secrets.get("ALLOW_LEGACY_PASSWORDS", False))
REQUIRE_SERVER_BACKUP_BEFORE_RESET = bool(st.secrets.get("REQUIRE_SERVER_BACKUP_BEFORE_RESET", True))
# Performance mode: health-check berulang pada rerun cepat menggunakan hasil sesi terbaru.
HEALTH_CACHE_SECONDS = max(5, int(st.secrets.get("HEALTH_CACHE_SECONDS", 20)))
SECONDARY_SYNC_SECONDS = max(AUTO_SYNC_SECONDS, int(st.secrets.get("SECONDARY_SYNC_SECONDS", 60)))
BACKUP_STATUS_TTL_SECONDS = max(20, int(st.secrets.get("BACKUP_STATUS_TTL_SECONDS", 60)))
MAX_UPLOAD_MB = max(1, min(15, int(st.secrets.get("MAX_UPLOAD_MB", 6))))
RESTOCK_TARGET_MULTIPLIER = max(1, min(5, int(st.secrets.get("RESTOCK_TARGET_MULTIPLIER", 2))))
NOTIFICATION_LOG_LIMIT = max(10, min(100, int(st.secrets.get("NOTIFICATION_LOG_LIMIT", 30))))

STOK_DEFAULT = {
    "Microcement base": 16,
    "Ready to use": 15,
    "Mixed resin A": 12,
    "Ceramic microcement": 4,
    "Microrock": 17,
    "Primer ordinary": 7,
    "Epoxy primer": 3,
    "Self leveling white finish": 4,
    "Top coat A": 15,
    "Top coat B": 1,
    "Top coat C": 5,
    "Pewarna no 1": 3,
    "Pewarna no 2": 10,
    "Pewarna no 3": 0,
    "Pewarna no 4": 9,
    "Metal glaze wax": 0,
    "Metallic glaze wax": 0,
}

MASTER_DEFAULT = {
    nama: {"status": "Aktif", "min_stok": 5}
    for nama in STOK_DEFAULT
}

RIWAYAT_COLUMNS = [
    "ID Transaksi",
    "Waktu",
    "Tanggal",
    "Tipe",
    "Barang",
    "Jumlah",
    "Pembeli / Keterangan",
    "Bukti URL",
    "Status",
    "Referensi",
]

AUDIT_COLUMNS = ["Waktu", "User", "Role", "Aksi", "ID Transaksi", "Detail"]

ROLE_DEVELOPER = "Developer"
ROLE_BOSS = "Boss"
ROLE_ADMIN = "Admin"
ROLE_STAFF = "Staff"
VALID_ROLES = {ROLE_DEVELOPER, ROLE_BOSS, ROLE_ADMIN, ROLE_STAFF}

ROLE_LABEL = {
    ROLE_DEVELOPER: "👨‍💻 Developer",
    ROLE_BOSS: "👔 Boss",
    ROLE_ADMIN: "👑 Admin",
    ROLE_STAFF: "👷 Staff",
}

PERMISSIONS = {
    "view_stock": VALID_ROLES,
    "transaction": VALID_ROLES,
    "manage_master": {ROLE_DEVELOPER, ROLE_BOSS, ROLE_ADMIN},
    "stock_adjust": {ROLE_DEVELOPER, ROLE_BOSS, ROLE_ADMIN},
    "correct_transaction": {ROLE_DEVELOPER, ROLE_BOSS, ROLE_ADMIN},
    "view_reports": {ROLE_DEVELOPER, ROLE_BOSS, ROLE_ADMIN},
    "view_audit": {ROLE_DEVELOPER, ROLE_BOSS},
    "backup": {ROLE_DEVELOPER, ROLE_BOSS, ROLE_ADMIN},
    "reset": {ROLE_DEVELOPER},
}


# ============================================================
# UTILITAS
# ============================================================
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


# ============================================================
# API CLIENT
# ============================================================
def _post_json(payload: dict, timeout=60):
    """POST JSON bertanda tangan. API key berada di body, bukan query URL."""
    if not URL_GSHEET_API:
        raise RuntimeError("URL_GSHEET_API belum diatur di Streamlit Secrets.")
    if not API_SHARED_KEY:
        raise RuntimeError("API_SHARED_KEY belum diatur di Streamlit Secrets.")
    if REQUIRE_HMAC and not AUTH_SIGNING_KEY:
        raise RuntimeError("AUTH_SIGNING_KEY wajib diisi karena REQUIRE_HMAC=true.")

    signed_payload = make_request_signature(payload)
    signed_payload = {**signed_payload, "api_key": API_SHARED_KEY}
    response = requests.post(URL_GSHEET_API, json=signed_payload, timeout=timeout)
    response.raise_for_status()
    try:
        data = response.json()
    except ValueError as exc:
        raise RuntimeError("Respons server bukan JSON yang valid.") from exc
    if not isinstance(data, dict):
        raise RuntimeError("Respons server tidak valid.")
    if data.get("ok") is False:
        raise RuntimeError(redact_sensitive(data.get("message", "Operasi ditolak server.")))
    return data


def api_get(timeout=20):
    """Baca database lewat signed POST. GET legacy hanya jika REQUIRE_HMAC dimatikan sengaja."""
    if AUTH_SIGNING_KEY:
        return _post_json({"action": "read", **actor_payload()}, timeout=timeout)
    if REQUIRE_HMAC:
        raise RuntimeError("Mode aman aktif tetapi AUTH_SIGNING_KEY belum tersedia.")

    if not URL_GSHEET_API:
        raise RuntimeError("URL_GSHEET_API belum diatur di Streamlit Secrets.")
    if not API_SHARED_KEY:
        raise RuntimeError("API_SHARED_KEY belum diatur di Streamlit Secrets.")
    response = requests.get(URL_GSHEET_API, params={"key": API_SHARED_KEY}, timeout=timeout)
    response.raise_for_status()
    try:
        data = response.json()
    except ValueError as exc:
        raise RuntimeError("Respons server bukan JSON yang valid.") from exc
    if isinstance(data, dict) and data.get("ok") is False:
        raise RuntimeError(redact_sensitive(data.get("message", "Server menolak permintaan.")))
    return data


def api_health(timeout=HEALTH_TIMEOUT_SECONDS):
    """Health check ringan untuk auto-sync berdasarkan revision backend."""
    if AUTH_SIGNING_KEY:
        return _post_json({"action": "health", **actor_payload()}, timeout=timeout)
    if REQUIRE_HMAC:
        raise RuntimeError("Mode aman aktif tetapi AUTH_SIGNING_KEY belum tersedia.")
    data = api_get(timeout=timeout)
    return {
        "ok": True,
        "backend_version": data.get("backend_version", ""),
        "data_revision": data.get("data_revision", ""),
        "server_time": data.get("server_time", ""),
    }


def api_post(payload: dict, timeout=60):
    return _post_json(payload, timeout=timeout)


def show_api_error(prefix: str, exc: Exception):
    st.error(f"{prefix}: {api_error_detail(exc)}.")


# ============================================================
# TELEGRAM
# ============================================================
def telegram_response_detail(response) -> str:
    """Ambil pesan error Telegram tanpa menampilkan BOT TOKEN."""
    try:
        data = response.json()
        description = str(data.get("description", "")).strip() if isinstance(data, dict) else ""
    except Exception:
        description = ""

    if description:
        return f"HTTP {response.status_code}: {description}"
    return f"HTTP {response.status_code}: Telegram menolak permintaan."


def telegram_safe_exception(exc: Exception) -> str:
    """Jangan sampai token Telegram / API key ikut muncul di pesan/log error."""
    return redact_sensitive(exc)


def test_telegram_connection():
    """Tes BOT TOKEN, CHAT ID, dan kemampuan bot mengirim pesan."""
    if not TELEGRAM_BOT_TOKEN:
        return False, "TELEGRAM_BOT_TOKEN belum diisi di Streamlit Secrets."
    if not TELEGRAM_CHAT_ID:
        return False, "TELEGRAM_CHAT_ID belum diisi di Streamlit Secrets."

    try:
        # 1) Pastikan token valid dan ambil identitas bot.
        get_me_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe"
        res = requests.get(get_me_url, timeout=15)
        if not res.ok:
            return False, telegram_response_detail(res)

        data = res.json()
        bot_info = data.get("result", {}) if isinstance(data, dict) else {}
        bot_name = bot_info.get("first_name") or bot_info.get("username") or "Telegram Bot"
        bot_username = bot_info.get("username", "")

        # 2) Pastikan CHAT ID bisa menerima pesan dari bot tersebut.
        send_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        test_message = f"✅ Tes koneksi WMS Microcement berhasil\n{waktu_display()}"
        sent = requests.post(
            send_url,
            json={"chat_id": str(TELEGRAM_CHAT_ID), "text": test_message},
            timeout=20,
        )
        if not sent.ok:
            return False, telegram_response_detail(sent)

        identity = f"{bot_name} (@{bot_username})" if bot_username else str(bot_name)
        return True, f"Terhubung ke {identity}. Pesan tes berhasil dikirim ke Chat ID {TELEGRAM_CHAT_ID}."
    except requests.exceptions.Timeout:
        return False, "Koneksi ke Telegram timeout. Coba lagi beberapa saat."
    except requests.exceptions.RequestException as exc:
        return False, f"Gangguan koneksi ke Telegram: {telegram_safe_exception(exc)}"
    except Exception as exc:
        return False, f"Tes Telegram gagal: {telegram_safe_exception(exc)}"


def send_telegram_detailed(message: str, image_bytes=None):
    """Kirim Telegram secara terukur; caller menerima status dan penyebab kegagalan."""
    if not TELEGRAM_BOT_TOKEN:
        return False, "TELEGRAM_BOT_TOKEN belum diisi."
    if not TELEGRAM_CHAT_ID:
        return False, "TELEGRAM_CHAT_ID belum diisi."

    last_error = ""
    for attempt in range(1, TELEGRAM_RETRY_ATTEMPTS + 1):
        try:
            if image_bytes:
                url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
                res = requests.post(
                    url,
                    data={"chat_id": str(TELEGRAM_CHAT_ID), "caption": message},
                    files={"photo": ("bukti.jpg", image_bytes, "image/jpeg")},
                    timeout=20,
                )
            else:
                url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
                res = requests.post(
                    url,
                    json={"chat_id": str(TELEGRAM_CHAT_ID), "text": message, "parse_mode": "Markdown"},
                    timeout=20,
                )
                # Keterangan/nama barang dapat mengandung karakter Markdown.
                # Jika Telegram menolak entity Markdown, kirim ulang sebagai plain text.
                if res.status_code == 400:
                    detail_lower = telegram_response_detail(res).lower()
                    if "parse" in detail_lower or "entity" in detail_lower:
                        res = requests.post(
                            url,
                            json={"chat_id": str(TELEGRAM_CHAT_ID), "text": message},
                            timeout=20,
                        )

            if res.ok:
                return True, "Notifikasi berhasil dikirim ke Telegram."

            last_error = telegram_response_detail(res)
            # 4xx selain rate-limit biasanya tidak akan sembuh dengan retry.
            if 400 <= res.status_code < 500 and res.status_code != 429:
                break
        except requests.exceptions.Timeout:
            last_error = "timeout"
        except requests.exceptions.RequestException as exc:
            last_error = telegram_safe_exception(exc)
        except Exception as exc:
            last_error = telegram_safe_exception(exc)
            break

        if attempt < TELEGRAM_RETRY_ATTEMPTS:
            time.sleep(min(4.0, 0.8 * attempt))

    safe_error = redact_sensitive(last_error or "Telegram menolak notifikasi.")
    print(f"[Telegram error] {safe_error}")
    return False, safe_error


def send_telegram(message: str, image_bytes=None):
    ok, _detail = send_telegram_detailed(message, image_bytes)
    return ok


def record_notification(context: str, ok: bool, detail: str):
    """Simpan hasil pengiriman pada sesi agar kegagalan tidak lagi tersembunyi."""
    rows = list(st.session_state.get("notification_log", []))
    rows.insert(0, {
        "Waktu": waktu_display(),
        "Konteks": context,
        "Status": "TERKIRIM" if ok else "GAGAL",
        "Detail": redact_sensitive(detail),
    })
    st.session_state.notification_log = rows[:NOTIFICATION_LOG_LIMIT]


def deliver_notification(message: str, context: str, image_bytes=None):
    """Notifikasi operasional dijalankan sinkron agar statusnya dapat dilaporkan."""
    ok, detail = send_telegram_detailed(message, image_bytes)
    record_notification(context, ok, detail)
    return ok, detail


def send_telegram_document_detailed(message: str, file_bytes: bytes, file_name: str):
    """Kirim backup dengan retry dan detail error yang sudah disanitasi."""
    if not TELEGRAM_BOT_TOKEN:
        return False, "TELEGRAM_BOT_TOKEN belum diisi."
    if not TELEGRAM_CHAT_ID:
        return False, "TELEGRAM_CHAT_ID belum diisi."

    last_error = ""
    for attempt in range(1, TELEGRAM_RETRY_ATTEMPTS + 1):
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
            res = requests.post(
                url,
                data={"chat_id": str(TELEGRAM_CHAT_ID), "caption": message},
                files={
                    "document": (
                        file_name,
                        file_bytes,
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                },
                timeout=40,
            )
            if res.ok:
                return True, "Backup berhasil dikirim ke Telegram."
            last_error = telegram_response_detail(res)
            if 400 <= res.status_code < 500 and res.status_code != 429:
                break
        except requests.exceptions.Timeout:
            last_error = "Koneksi Telegram timeout saat mengirim backup."
        except requests.exceptions.RequestException as exc:
            last_error = f"Gangguan koneksi Telegram: {telegram_safe_exception(exc)}"
        except Exception as exc:
            last_error = f"Pengiriman backup gagal: {telegram_safe_exception(exc)}"
            break

        if attempt < TELEGRAM_RETRY_ATTEMPTS:
            time.sleep(min(5.0, 1.0 * attempt))

    return False, redact_sensitive(last_error or "Telegram menolak pengiriman backup.")


def send_telegram_document(message: str, file_bytes: bytes, file_name: str):
    ok, _detail = send_telegram_document_detailed(message, file_bytes, file_name)
    return ok


# ============================================================
# DATA NORMALIZATION
# ============================================================
def normalize_stock_rows(raw_rows):
    stock = {}
    master = {}
    rows = raw_rows or []
    if rows and isinstance(rows[0], list):
        rows = rows[1:]

    for row in rows:
        if not isinstance(row, list) or len(row) < 2:
            continue
        nama = str(row[0]).strip()
        if not nama:
            continue
        raw_stock = str(row[1]).strip()
        if not raw_stock or not re.fullmatch(r"-?\d+(?:\.0+)?", raw_stock):
            raise RuntimeError(f"Jumlah stok untuk '{nama}' bukan angka yang valid")
        stock[nama] = safe_int(row[1])
        master[nama] = {
            "status": str(row[2]).strip() if len(row) > 2 and str(row[2]).strip() else "Aktif",
            "min_stok": safe_int(row[3], 5) if len(row) > 3 else 5,
        }

    return stock, master


def normalize_history_rows(raw_rows):
    result = []
    rows = raw_rows or []
    if rows and isinstance(rows[0], list):
        header = [str(x).strip() for x in rows[0]]
        data_rows = rows[1:]
    else:
        header = []
        data_rows = rows

    # Dukungan schema baru dari Code.gs yang disertakan.
    if header and "ID Transaksi" in header:
        for row in data_rows:
            row = list(row) + [""] * max(0, len(header) - len(row))
            item = {header[i]: row[i] for i in range(len(header))}
            item["Jumlah"] = safe_int(item.get("Jumlah"))
            result.append({col: item.get(col, "") for col in RIWAYAT_COLUMNS})
        return result

    # Kompatibilitas dengan schema lama pengguna.
    for row in data_rows:
        if not isinstance(row, list) or len(row) < 4:
            continue
        waktu = str(row[0])
        dt = parse_tx_datetime(waktu)
        result.append(
            {
                "ID Transaksi": "LEGACY-" + hashlib.sha1("|".join(map(str, row[:5])).encode()).hexdigest()[:10].upper(),
                "Waktu": waktu,
                "Tanggal": dt.strftime("%d-%m-%Y") if dt else "",
                "Tipe": str(row[1]),
                "Barang": str(row[2]),
                "Jumlah": safe_int(row[3]),
                "Pembeli / Keterangan": row[4] if len(row) > 4 else "-",
                "Bukti URL": row[5] if len(row) > 5 else "",
                "Status": row[6] if len(row) > 6 and row[6] else "AKTIF",
                "Referensi": row[7] if len(row) > 7 else "",
            }
        )
    return result


def normalize_audit_rows(raw_rows):
    rows = raw_rows or []
    if not rows:
        return []

    if isinstance(rows[0], list):
        header = [str(x).strip() for x in rows[0]]
        data_rows = rows[1:]
    else:
        header = []
        data_rows = rows

    if header and "Aksi" in header:
        result = []
        for row in data_rows:
            row = list(row) + [""] * max(0, len(header) - len(row))
            item = {header[i]: row[i] for i in range(len(header))}
            result.append({col: item.get(col, "") for col in AUDIT_COLUMNS})
        return result

    # Kompatibilitas audit lama: Waktu, Aksi, ID Transaksi, Detail
    result = []
    for row in data_rows:
        if not isinstance(row, list) or len(row) < 1:
            continue
        result.append({
            "Waktu": row[0] if len(row) > 0 else "",
            "User": "",
            "Role": "",
            "Aksi": row[1] if len(row) > 1 else "",
            "ID Transaksi": row[2] if len(row) > 2 else "",
            "Detail": row[3] if len(row) > 3 else "",
        })
    return result


def normalize_server_data(data):
    if not isinstance(data, dict):
        raise RuntimeError("Format data server tidak valid; objek JSON diharapkan.")

    stock, master = normalize_stock_rows(data.get("stok", []))
    history = normalize_history_rows(data.get("riwayat", []))
    audit = normalize_audit_rows(data.get("audit", []))

    # Jangan diam-diam mengubah database kosong menjadi stok dummy.
    # Jika instalasi lama memang membutuhkan perilaku tersebut, aktifkan secret ini secara eksplisit.
    if not stock and SERVER_EMPTY_USE_DEFAULT_STOCK:
        stock = STOK_DEFAULT.copy()
        master = {k: v.copy() for k, v in MASTER_DEFAULT.items()}
    return stock, master, history, audit


@st.cache_data(ttl=DATA_CACHE_TTL_SECONDS, show_spinner=False)
def load_data_cached(api_url: str):
    del api_url  # cache key berubah bila URL deployment berubah
    return api_get()


def refresh_data(force=False, quiet=False):
    try:
        raw = api_get() if force else load_data_cached(URL_GSHEET_API)
        stock, master, history, audit = normalize_server_data(raw)
        st.session_state.stok = stock
        st.session_state.master_info = master
        st.session_state.riwayat = history
        st.session_state.audit = audit
        st.session_state.is_connected = True
        st.session_state.data_source = "server"
        st.session_state.last_server_sync = waktu_display()
        st.session_state.last_server_sync_epoch = time.time()
        revision = str(raw.get("data_revision", "") or "") if isinstance(raw, dict) else ""
        backend_version = str(raw.get("backend_version", "") or "") if isinstance(raw, dict) else ""
        if revision:
            st.session_state.server_revision = revision
        if backend_version:
            st.session_state.backend_version = backend_version
            st.session_state.backend_version_mismatch = backend_version != EXPECTED_BACKEND_VERSION
        st.session_state.health_cache = {
            "ok": True,
            "backend_version": backend_version,
            "data_revision": revision,
        }
        st.session_state.last_health_epoch = time.time()
        st.session_state.last_health_check = waktu_display()
        return True
    except Exception as exc:
        st.session_state.is_connected = False
        if "stok" not in st.session_state:
            if OFFLINE_USE_DEFAULT_STOCK:
                st.session_state.stok = STOK_DEFAULT.copy()
                st.session_state.master_info = {k: v.copy() for k, v in MASTER_DEFAULT.items()}
                st.session_state.data_source = "default_offline"
            else:
                st.session_state.stok = {}
                st.session_state.master_info = {}
                st.session_state.data_source = "offline_empty"
            st.session_state.riwayat = []
            st.session_state.audit = []
        else:
            st.session_state.data_source = "last_known_session"
        if not quiet:
            show_api_error("Gagal mengambil data", exc)
        return False


def clear_and_refresh():
    # Bersihkan hanya cache pembacaan database; cache ekspor pengguna lain tidak ikut terhapus.
    load_data_cached.clear()
    refresh_data(force=True)


def _apply_health_to_session(health: dict):
    """Simpan hasil health check agar rerun Streamlit tidak memanggil Apps Script berulang."""
    health = health or {}
    revision = str(health.get("data_revision", "") or "")
    backend_version = str(health.get("backend_version", "") or "")
    st.session_state.health_cache = dict(health)
    st.session_state.last_health_epoch = time.time()
    st.session_state.last_health_check = waktu_display()
    st.session_state.is_connected = True
    if backend_version:
        st.session_state.backend_version = backend_version
        st.session_state.backend_version_mismatch = backend_version != EXPECTED_BACKEND_VERSION
    return revision


def get_server_health(force=False):
    """Health-check bertingkat: gunakan hasil sesi singkat sebelum meminta Apps Script lagi."""
    now = time.time()
    cached = st.session_state.get("health_cache")
    last = float(st.session_state.get("last_health_epoch", 0) or 0)
    if not force and isinstance(cached, dict) and (now - last) < HEALTH_CACHE_SECONDS:
        return cached
    health = api_health()
    _apply_health_to_session(health)
    return health


def sync_if_changed(force_health=False):
    """Polling ringan; full read hanya saat revision backend berubah."""
    if not AUTO_SYNC_ENABLED and not force_health:
        return False
    try:
        health = get_server_health(force=force_health)
        revision = str(health.get("data_revision", "") or "")
        current_revision = str(st.session_state.get("server_revision", "") or "")
        if not revision or revision != current_revision:
            return refresh_data(force=True, quiet=True)
        return False
    except Exception:
        st.session_state.is_connected = False
        if "stok" in st.session_state:
            st.session_state.data_source = "last_known_session"
        return False


def require_online_operation():
    """Gunakan health terbaru bila masih fresh; server tetap memvalidasi setiap mutation saat submit."""
    if not WRITE_BLOCK_WHEN_OFFLINE:
        return
    try:
        get_server_health(force=False)
    except Exception:
        st.session_state.is_connected = False
        if "stok" in st.session_state:
            st.session_state.data_source = "last_known_session"

    if not st.session_state.get("is_connected"):
        st.error("⛔ Operasi perubahan stok dinonaktifkan karena database sedang offline. Segarkan koneksi terlebih dahulu.")
        st.stop()


def validate_runtime_security():
    """Fail-closed untuk konfigurasi yang seharusnya wajib pada deployment production."""
    missing = []
    if not URL_GSHEET_API:
        missing.append("URL_GSHEET_API")
    if not API_SHARED_KEY:
        missing.append("API_SHARED_KEY")
    if REQUIRE_HMAC and not AUTH_SIGNING_KEY:
        missing.append("AUTH_SIGNING_KEY")
    if missing:
        st.error("⛔ Konfigurasi production belum lengkap: " + ", ".join(missing))
        st.stop()


def account_security_report():
    """Klasifikasikan penyimpanan password tanpa pernah menampilkan password/hash lengkap."""
    report = []
    for username, raw_cfg in get_users_config().items():
        cfg = dict(raw_cfg)
        configured_hash = str(cfg.get("password_hash", "") or "").strip()
        if configured_hash.startswith("pbkdf2_sha256$"):
            status = "PBKDF2"
        elif configured_hash:
            status = "LEGACY_SHA256"
        elif cfg.get("password") is not None:
            status = "PLAIN_PASSWORD"
        else:
            status = "TIDAK_VALID"
        report.append((str(username), status))
    return report


# ============================================================
# LOGIN & ROLE BASED ACCESS CONTROL
# ============================================================
def get_users_config():
    try:
        users = st.secrets.get("USERS", {})
        return dict(users) if users else {}
    except Exception:
        return {}


def normalize_role(role: str) -> str:
    txt = str(role or "").strip().lower()
    mapping = {
        "developer": ROLE_DEVELOPER,
        "boss": ROLE_BOSS,
        "bos": ROLE_BOSS,
        "admin": ROLE_ADMIN,
        "staff": ROLE_STAFF,
    }
    return mapping.get(txt, ROLE_STAFF)


def generate_pbkdf2_hash(password: str, iterations: int = PBKDF2_ITERATIONS) -> str:
    """Format: pbkdf2_sha256$iterations$salt_hex$digest_hex."""
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${digest.hex()}"


def password_matches(input_password: str, configured: dict) -> bool:
    """Mendukung PBKDF2 baru + SHA-256/plain lama agar migrasi tidak memutus login."""
    configured_hash = str(configured.get("password_hash", "") or "").strip()
    if configured_hash:
        if configured_hash.startswith("pbkdf2_sha256$"):
            try:
                _algo, iterations_txt, salt_hex, expected_hex = configured_hash.split("$", 3)
                iterations = int(iterations_txt)
                if iterations < 100_000:
                    return False
                salt = bytes.fromhex(salt_hex)
                digest = hashlib.pbkdf2_hmac(
                    "sha256", input_password.encode("utf-8"), salt, iterations
                ).hex()
                return hmac.compare_digest(digest, expected_hex.lower())
            except (ValueError, TypeError):
                return False

        if not ALLOW_LEGACY_PASSWORDS:
            return False
        supplied_hash = hashlib.sha256(input_password.encode("utf-8")).hexdigest()
        return hmac.compare_digest(supplied_hash, configured_hash.lower())

    if configured.get("password") is not None:
        if not ALLOW_LEGACY_PASSWORDS:
            return False
        return hmac.compare_digest(str(input_password), str(configured["password"]))
    return False


def clear_auth_session():
    for key in ("auth_user", "auth_role", "auth_login_at", "auth_last_activity"):
        st.session_state.pop(key, None)


def login_gate():
    users = get_users_config()
    now = time.time()

    if not users:
        if ALLOW_NO_LOGIN:
            st.session_state.auth_user = "Local Developer"
            st.session_state.auth_role = ROLE_DEVELOPER
            st.session_state.auth_login_at = now
            st.session_state.auth_last_activity = now
            return
        st.error("Konfigurasi USERS belum dibuat di Streamlit Secrets.")
        st.info("Tambahkan akun Developer, Boss, Admin, dan Staff di Streamlit Secrets sebelum aplikasi digunakan.")
        st.stop()

    if st.session_state.get("auth_user"):
        last_activity = float(st.session_state.get("auth_last_activity", now))
        timeout_seconds = SESSION_TIMEOUT_MINUTES * 60
        if now - last_activity > timeout_seconds:
            clear_auth_session()
            st.warning("Sesi login berakhir karena tidak aktif terlalu lama. Silakan masuk kembali.")
        else:
            st.session_state.auth_role = normalize_role(st.session_state.get("auth_role"))
            st.session_state.auth_last_activity = now
            return

    lock_until = float(st.session_state.get("login_lock_until", 0) or 0)
    if lock_until and now >= lock_until:
        st.session_state.login_attempts = 0
        st.session_state.login_lock_until = 0
        lock_until = 0

    st.title("🔐 Login WMS Microcement")
    st.caption("Masuk menggunakan akun yang diberikan sesuai jabatan.")

    if lock_until > now:
        remaining = max(1, int(lock_until - now))
        st.error(f"Terlalu banyak percobaan login gagal. Coba lagi dalam {remaining} detik.")
        st.stop()

    with st.form("login_form"):
        username = st.text_input("Username").strip()
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Masuk", use_container_width=True)

    if submit:
        cfg = users.get(username)
        if cfg and password_matches(password, dict(cfg)):
            st.session_state.auth_user = username
            st.session_state.auth_role = normalize_role(dict(cfg).get("role", ROLE_STAFF))
            st.session_state.auth_login_at = now
            st.session_state.auth_last_activity = now
            st.session_state.login_attempts = 0
            st.session_state.login_lock_until = 0
            st.rerun()

        attempts = int(st.session_state.get("login_attempts", 0)) + 1
        st.session_state.login_attempts = attempts
        remaining_attempts = LOGIN_MAX_ATTEMPTS - attempts
        if attempts >= LOGIN_MAX_ATTEMPTS:
            st.session_state.login_lock_until = now + LOGIN_LOCK_SECONDS
            st.error(f"Login dikunci sementara selama {LOGIN_LOCK_SECONDS} detik karena terlalu banyak percobaan gagal.")
        else:
            st.error(f"Username atau password salah. Sisa percobaan: {remaining_attempts}.")
    st.stop()


def current_role() -> str:
    return normalize_role(st.session_state.get("auth_role", ROLE_STAFF))


def has_permission(permission: str) -> bool:
    return current_role() in PERMISSIONS.get(permission, set())


def actor_payload() -> dict:
    return {
        "actor": str(st.session_state.get("auth_user", "Unknown")),
        "role": current_role(),
        "app_version": APP_VERSION,
    }


def actor_label() -> str:
    return f"{st.session_state.get('auth_user', 'Unknown')} ({current_role()})"


def set_flash(level: str, message: str):
    """Pesan tetap muncul setelah st.rerun, penting untuk hasil transaksi/notifikasi."""
    st.session_state.operation_flash = (level, message)


def render_flash():
    flash = st.session_state.pop("operation_flash", None)
    if not flash:
        return
    level, message = flash
    renderer = {
        "success": st.success,
        "warning": st.warning,
        "error": st.error,
        "info": st.info,
    }.get(level, st.info)
    renderer(message)


def notification_flash(success_message: str, notification_results):
    """Pisahkan sukses database dari status Telegram agar operator tidak terkecoh."""
    failed = [detail for ok, detail in notification_results if not ok]
    if failed:
        set_flash(
            "warning",
            success_message + " Namun notifikasi Telegram gagal: " + "; ".join(failed),
        )
    else:
        suffix = " Notifikasi Telegram berhasil dikirim." if notification_results else ""
        set_flash("success", success_message + suffix)


def require_permission(permission: str):
    if not has_permission(permission):
        st.error("⛔ Anda tidak memiliki izin untuk membuka fitur ini.")
        st.stop()


# ============================================================
# EXPORT
# ============================================================
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


# ============================================================
# SERVER OPERATIONS
# ============================================================
def do_transaction(
    tipe,
    barang,
    jumlah,
    tgl_transaksi,
    keterangan,
    file_uploaded=None,
    image_bytes=None,
    expected_stock_before=None,
):
    payload = {
        "action": "transaction",
        "tx_id": make_tx_id(),
        "tanggal": tgl_transaksi.strftime("%d-%m-%Y"),
        "waktu": combine_manual_date(tgl_transaksi),
        "tipe": tipe,
        "barang": barang,
        "jumlah": int(jumlah),
        "keterangan": clean_note(keterangan, required=(tipe == "KELUAR")),
        **to_image_payload(file_uploaded, image_bytes),
        **actor_payload(),
    }
    if expected_stock_before is not None:
        # Backend baru dapat memakai nilai ini sebagai stale-stock guard;
        # backend 7.1 yang belum mendukung akan mengabaikan field tambahan ini.
        payload["expected_stock_before"] = int(expected_stock_before)
    result = api_post(payload)
    clear_and_refresh()
    return result


def add_master(nama, stok_awal, min_stok):
    result = api_post(
        {
            "action": "master_add",
            "nama": nama,
            "stok_awal": int(stok_awal),
            "min_stok": int(min_stok),
            "status": "Aktif",
            "tx_id": make_tx_id("NEW"),
            "waktu": combine_manual_date(hari_ini_wib()),
            **actor_payload(),
        }
    )
    clear_and_refresh()
    return result


def update_master(old_nama, new_nama, status, min_stok):
    result = api_post(
        {
            "action": "master_update",
            "old_nama": old_nama,
            "new_nama": new_nama,
            "status": status,
            "min_stok": int(min_stok),
            **actor_payload(),
        }
    )
    clear_and_refresh()
    return result


def delete_master(nama):
    result = api_post({"action": "master_delete", "nama": nama, **actor_payload()})
    clear_and_refresh()
    return result


def correct_transaction(old_tx, new_tx):
    result = api_post(
        {
            "action": "transaction_correct",
            "tx_id": old_tx["ID Transaksi"],
            "new_tx_id": make_tx_id("COR"),
            "new_waktu": new_tx["Waktu"],
            "new_tanggal": new_tx["Tanggal"],
            "new_tipe": new_tx["Tipe"],
            "new_barang": new_tx["Barang"],
            "new_jumlah": int(new_tx["Jumlah"]),
            "new_keterangan": clean_note(new_tx["Pembeli / Keterangan"]),
            **actor_payload(),
        }
    )
    clear_and_refresh()
    return result


def void_transaction(tx_id):
    result = api_post({"action": "transaction_void", "tx_id": tx_id, **actor_payload()})
    clear_and_refresh()
    return result


def adjust_stock(barang, stok_baru, alasan, tgl_transaksi, expected_stock_before):
    result = api_post(
        {
            "action": "stock_adjust",
            "tx_id": make_tx_id("ADJ"),
            "barang": barang,
            "stok_baru": int(stok_baru),
            "expected_stock_before": int(expected_stock_before),
            "alasan": clean_note(alasan, required=True),
            "tanggal": tgl_transaksi.strftime("%d-%m-%Y"),
            "waktu": combine_manual_date(tgl_transaksi),
            **actor_payload(),
        }
    )
    clear_and_refresh()
    return result


def reset_database():
    result = api_post({"action": "reset", "confirm": "RESET-DATABASE", **actor_payload()})
    clear_and_refresh()
    return result



# ============================================================
# BACKUP SERVER / AUTO-SYNC UI
# ============================================================
def server_backup_now():
    return api_post({"action": "server_backup", **actor_payload()}, timeout=90)


def install_backup_trigger():
    return api_post({"action": "install_backup_trigger", **actor_payload()}, timeout=60)


def remove_backup_trigger():
    return api_post({"action": "remove_backup_trigger", **actor_payload()}, timeout=60)


def backup_server_status():
    return _post_json({"action": "backup_status", **actor_payload()}, timeout=20)


def backup_server_status_cached(force=False):
    """Status backup tidak perlu dipanggil ulang pada setiap widget rerun."""
    now = time.time()
    cached = st.session_state.get("backup_status_cache")
    last = float(st.session_state.get("backup_status_epoch", 0) or 0)
    if not force and isinstance(cached, dict) and (now - last) < BACKUP_STATUS_TTL_SECONDS:
        return cached
    data = backup_server_status()
    st.session_state.backup_status_cache = dict(data or {})
    st.session_state.backup_status_epoch = now
    return data


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
    cards = [
        ("wms-kpi-blue", "📦", "Barang Aktif", str(active_count)),
        ("wms-kpi-indigo", "▦", "Total Stok", f"{total_stock} pcs"),
        ("wms-kpi-amber", "⚠", "Stok Kritis", str(critical_count)),
        ("wms-kpi-red", "!", "Stok Habis", str(out_count)),
    ]
    card_html = "".join(
        (
            f'<div class="wms-kpi-card {tone}">'
            f'<div class="wms-kpi-top">'
            f'<span class="wms-kpi-label">{html.escape(label)}</span>'
            f'<span class="wms-kpi-icon">{html.escape(icon)}</span>'
            f'</div>'
            f'<div class="wms-kpi-value">{html.escape(value)}</div>'
            f'</div>'
        )
        for tone, icon, label, value in cards
    )
    st.markdown(f'<div class="wms-kpi-grid">{card_html}</div>', unsafe_allow_html=True)


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

    if not st.session_state.get("is_connected"):
        st.error("Database sedang offline. Dashboard menampilkan snapshot terakhir dan tidak boleh dianggap real-time.")

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

    st.divider()
    left, right = st.columns(2)
    with left:
        st.subheader("📊 Status Stok")
        safe_count = len(active_now) - len(critical_now) - len(out_now)
        df_chart = pd.DataFrame(
            {"Status": ["Aman", "Kritis", "Habis"], "Jumlah": [safe_count, len(critical_now), len(out_now)]}
        )
        if int(df_chart["Jumlah"].sum()) > 0:
            fig = px.pie(
                df_chart,
                names="Status",
                values="Jumlah",
                hole=0.52,
                color="Status",
                color_discrete_map={"Aman": "#22c55e", "Kritis": "#f59e0b", "Habis": "#ef4444"},
            )
            fig.update_layout(legend_orientation="h", margin=dict(l=10, r=10, t=20, b=10))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Belum ada data stok aktif untuk ditampilkan.")

    with right:
        st.subheader("🚨 Perlu Perhatian")
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

    st.divider()
    st.subheader("📋 Ringkasan Stok")
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


# ============================================================
# STARTUP
# ============================================================
login_gate()
validate_runtime_security()

if "stok" not in st.session_state:
    refresh_data(force=True)

stock = st.session_state.stok
master = st.session_state.master_info
history = st.session_state.riwayat


# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown("### 📦 WMS Microcement")
    role_now = current_role()
    st.caption(f"👤 {st.session_state.get('auth_user')}")
    st.caption(ROLE_LABEL.get(role_now, role_now))
    st.markdown("---")

    menu_options = [
        "🏠 Dashboard",
        "📋 Lihat Semua Stok",
    ]

    if has_permission("manage_master"):
        menu_options.append("➕ Kelola Master Item")

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
    if st.session_state.get("is_connected"):
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


# ============================================================
# HEADER
# ============================================================
h1, h2 = st.columns([4, 1])
with h1:
    st.title(f"📦 {active_menu}")
    st.caption(f"{waktu_display()} · v{APP_VERSION}")
with h2:
    st.markdown('<span class="wms-refresh-anchor"></span>', unsafe_allow_html=True)
    if st.button("🔄", help="Segarkan data", use_container_width=True, key="main_refresh"):
        clear_and_refresh()
        st.rerun()

st.divider()
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

# Hitung ulang setelah kemungkinan refresh
stock = st.session_state.stok
master = st.session_state.master_info
history = st.session_state.riwayat
active_stock = {k: v for k, v in stock.items() if master.get(k, {}).get("status", "Aktif") == "Aktif"}
critical = [k for k, v in active_stock.items() if 0 < v <= master.get(k, {}).get("min_stok", 5)]
out_of_stock = [k for k, v in active_stock.items() if v <= 0]


# ============================================================
# PAGES
# ============================================================
if active_menu == "Dashboard":
    render_dashboard_live()

elif active_menu == "Lihat Semua Stok":
    render_stock_live()

elif active_menu == "Kelola Master Item":
    require_permission("manage_master")
    sync_if_changed(force_health=True)
    require_online_operation()
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
                        delete_master(selected)
                        notification = deliver_notification(
                            f"🗑️ *ITEM DIHAPUS*\n📦 {selected}\n👤 {actor_label()}",
                            "Hapus item",
                        )
                        notification_flash("Barang berhasil dihapus.", [notification])
                        st.rerun()
                    except Exception as exc:
                        show_api_error("Barang tidak dapat dihapus", exc)


elif active_menu in ("Barang Masuk", "Barang Keluar"):
    require_permission("transaction")
    sync_if_changed(force_health=True)
    require_online_operation()
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
            label_ket = "Supplier / Keterangan" if tipe == "MASUK" else "Nama Pembeli / Proyek"
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
                st.warning("Nama Pembeli / Proyek wajib diisi.")
            else:
                try:
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


elif active_menu == "Penyesuaian Stok":
    require_permission("stock_adjust")
    sync_if_changed(force_health=True)
    require_online_operation()
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


elif active_menu == "Koreksi Transaksi":
    require_permission("correct_transaction")
    sync_if_changed(force_health=True)
    require_online_operation()
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
            ket = st.text_input("Keterangan / Pembeli", value=str(old["Pembeli / Keterangan"]))
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


elif active_menu == "Riwayat Transaksi":
    render_history_live()


elif active_menu == "Laporan Periodik":
    require_permission("view_reports")
    render_reports_live()


elif active_menu == "Audit Log":
    require_permission("view_audit")
    render_audit_live()


elif active_menu == "Backup Data":
    require_permission("backup")
    st.write("Backup berisi stok, riwayat transaksi, audit log, serta manifest URL bukti transaksi.")
    st.caption("Catatan: gambar/nota asli tetap berada di Google Drive; workbook menyimpan daftar URL-nya.")

    backup_is_snapshot = not st.session_state.get("is_connected")
    if backup_is_snapshot:
        st.warning("⚠️ Database offline. File lokal di bawah adalah SNAPSHOT sesi terakhir, bukan backup database real-time.")

    # full_backup_bytes dicache berdasarkan isi data sehingga rerun tombol tidak membuat XLSX berulang-ulang.
    backup = full_backup_bytes(
        st.session_state.get("stok", {}),
        st.session_state.get("master_info", {}),
        st.session_state.get("riwayat", []),
        st.session_state.get("audit", []),
    )
    prefix = "SNAPSHOT_WMS" if backup_is_snapshot else "BACKUP_WMS"
    filename = f"{prefix}_{sekarang_wib().strftime('%Y%m%d_%H%M%S')}.xlsx"
    b1, b2 = st.columns(2)
    b1.download_button("💾 Download Backup", backup, filename, use_container_width=True)
    if b2.button("📤 Kirim Backup ke Telegram", use_container_width=True):
        ok, detail = send_telegram_document_detailed(
            f"💾 BACKUP WMS\n{waktu_display()}",
            backup,
            filename,
        )
        record_notification("Backup manual", ok, detail)
        if ok:
            st.success(detail)
        else:
            st.error(f"Backup gagal dikirim ke Telegram — {detail}")

    st.divider()
    st.subheader("☁️ Backup Database Otomatis")
    st.caption("Backup server membuat salinan Google Spreadsheet langsung ke folder WMS_Backups di Google Drive.")

    backup_flash = st.session_state.pop("backup_flash", None)
    if backup_flash:
        level, message = backup_flash
        if level == "success":
            st.success(message)
        elif level == "warning":
            st.warning(message)
        else:
            st.info(message)

    backup_status = {}
    backup_status_error = None
    if st.session_state.get("is_connected"):
        try:
            backup_status = backup_server_status_cached(force=False)
            st.session_state.backup_last_time = backup_status.get("last_backup_time") or st.session_state.get("backup_last_time", "")
            st.session_state.backup_last_url = backup_status.get("last_backup_url") or st.session_state.get("backup_last_url", "")
            st.session_state.backup_last_name = backup_status.get("last_backup_name") or st.session_state.get("backup_last_name", "")
            st.session_state.backup_trigger_active = bool(backup_status.get("trigger_installed", False))
        except Exception as exc:
            backup_status_error = api_error_detail(exc)
    else:
        backup_status_error = "database sedang offline"

    last_backup = backup_status.get("last_backup_time") or st.session_state.get("backup_last_time") or "Belum ada"
    last_backup_name = backup_status.get("last_backup_name") or st.session_state.get("backup_last_name") or ""
    last_backup_url = backup_status.get("last_backup_url") or st.session_state.get("backup_last_url") or ""
    trigger_active = bool(backup_status.get("trigger_installed", st.session_state.get("backup_trigger_active", False)))

    if backup_status_error:
        st.warning(f"Status backup server belum dapat diperbarui: {backup_status_error}. Status terakhir yang tersimpan tetap ditampilkan.")

    bs1, bs2 = st.columns(2)
    bs1.metric("Backup terakhir", last_backup)
    bs2.metric("Backup harian", "Aktif" if trigger_active else "Belum aktif")
    if last_backup_name:
        st.caption(f"Backup terakhir: {last_backup_name}")
    if last_backup_url:
        st.link_button("📂 Buka Backup Terakhir di Google Drive", last_backup_url, use_container_width=True)

    if st.button("☁️ Buat Backup Server Sekarang", use_container_width=True, disabled=not st.session_state.get("is_connected")):
        try:
            result = server_backup_now()
            backup_time = result.get("backup_time") or waktu_display()
            backup_name = result.get("backup_name") or "WMS backup"
            backup_url = result.get("backup_url") or ""
            st.session_state.backup_last_time = backup_time
            st.session_state.backup_last_name = backup_name
            st.session_state.backup_last_url = backup_url
            st.session_state.backup_status_cache = {
                **st.session_state.get("backup_status_cache", {}),
                "last_backup_time": backup_time,
                "last_backup_name": backup_name,
                "last_backup_url": backup_url,
                "trigger_installed": trigger_active,
            }
            st.session_state.backup_status_epoch = time.time()
            st.session_state.backup_flash = ("success", f"Backup server berhasil: {backup_name}")
            st.rerun()
        except Exception as exc:
            show_api_error("Backup server gagal", exc)

    if current_role() == ROLE_DEVELOPER:
        bt1, bt2 = st.columns(2)
        if bt1.button("🕑 Aktifkan Backup Harian", use_container_width=True, disabled=trigger_active or not st.session_state.get("is_connected")):
            try:
                result = install_backup_trigger()
                st.session_state.backup_trigger_active = bool(result.get("trigger_installed", True)) if isinstance(result, dict) else True
                st.session_state.backup_status_cache = {
                    **st.session_state.get("backup_status_cache", {}),
                    "trigger_installed": st.session_state.backup_trigger_active,
                }
                st.session_state.backup_status_epoch = time.time()
                st.session_state.backup_flash = ("success", "Backup otomatis harian berhasil diaktifkan.")
                st.rerun()
            except Exception as exc:
                show_api_error("Gagal mengaktifkan backup harian", exc)
        if bt2.button("⏹️ Nonaktifkan Backup Harian", use_container_width=True, disabled=(not trigger_active) or not st.session_state.get("is_connected")):
            try:
                result = remove_backup_trigger()
                st.session_state.backup_trigger_active = bool(result.get("trigger_installed", False)) if isinstance(result, dict) else False
                st.session_state.backup_status_cache = {
                    **st.session_state.get("backup_status_cache", {}),
                    "trigger_installed": st.session_state.backup_trigger_active,
                }
                st.session_state.backup_status_epoch = time.time()
                st.session_state.backup_flash = ("success", "Backup otomatis harian dinonaktifkan.")
                st.rerun()
            except Exception as exc:
                show_api_error("Gagal menonaktifkan backup harian", exc)


elif active_menu == "Status Notifikasi":
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
                f"✅ Tes notifikasi WMS Microcement\n{waktu_display()}\n👤 {actor_label()}",
                "Tes manual",
            )
            if ok:
                st.success(detail)
            else:
                st.error(f"Tes Telegram gagal: {detail}")


elif active_menu == "Pengaturan & Reset":
    require_permission("reset")
    sync_if_changed(force_health=True)
    require_online_operation()

    with st.expander("🔐 Generator Password Hash PBKDF2", expanded=False):
        st.caption("Gunakan hasil ini sebagai password_hash di secrets.toml. Password tidak disimpan oleh aplikasi.")
        new_password = st.text_input("Password baru", type="password", key="pbkdf2_password")
        confirm_password = st.text_input("Ulangi password", type="password", key="pbkdf2_password_confirm")
        if st.button("Buat Password Hash", use_container_width=True):
            if len(new_password) < 8:
                st.warning("Gunakan password minimal 8 karakter.")
            elif new_password != confirm_password:
                st.error("Konfirmasi password tidak sama.")
            else:
                generated_hash = generate_pbkdf2_hash(new_password)
                st.code(generated_hash, language=None)
                st.success("Hash berhasil dibuat. Salin ke password_hash pada akun yang sesuai di Streamlit Secrets.")

    with st.expander("🛡️ Status Hardening", expanded=False):
        st.write(f"Cache data: **{DATA_CACHE_TTL_SECONDS} detik**")
        st.write(f"Session timeout: **{SESSION_TIMEOUT_MINUTES} menit**")
        st.write(f"Login lock: **{LOGIN_MAX_ATTEMPTS} percobaan / {LOGIN_LOCK_SECONDS} detik**")
        st.write(f"Auto-sync Dashboard/Stok: **{'Aktif' if AUTO_SYNC_ENABLED else 'Nonaktif'} / {AUTO_SYNC_SECONDS} detik**")
        st.write(f"Auto-sync Riwayat/Laporan/Audit: **{SECONDARY_SYNC_SECONDS} detik**")
        st.write(f"Health cache: **{HEALTH_CACHE_SECONDS} detik**")
        st.write(f"Batas upload bukti: **{MAX_UPLOAD_MB} MB**")
        st.write(f"Revision backend: **{st.session_state.get('server_revision', '-')}**")
        st.write(f"Backend: **{st.session_state.get('backend_version', 'belum diketahui')}**")
        st.write(f"Mode HMAC wajib: **{'Ya' if REQUIRE_HMAC else 'Tidak'}**")
        st.write(f"Password legacy diizinkan: **{'Ya' if ALLOW_LEGACY_PASSWORDS else 'Tidak'}**")
        if AUTH_SIGNING_KEY and REQUIRE_HMAC:
            st.success("AUTH_SIGNING_KEY aktif dan mode fail-closed HMAC aktif.")
        elif AUTH_SIGNING_KEY:
            st.info("AUTH_SIGNING_KEY tersedia, tetapi REQUIRE_HMAC=false.")
        else:
            st.error("AUTH_SIGNING_KEY belum diisi.")

        account_report = account_security_report()
        weak_accounts = [name for name, status in account_report if status != "PBKDF2"]
        if weak_accounts:
            st.warning("Akun belum PBKDF2: " + ", ".join(weak_accounts))
        else:
            st.success("Semua akun menggunakan PBKDF2.")

    st.warning("Reset menghapus data operasional dan mengembalikan master awal. Backup dahulu.")
    backup = full_backup_bytes(
        st.session_state.get("stok", {}),
        st.session_state.get("master_info", {}),
        st.session_state.get("riwayat", []),
        st.session_state.get("audit", []),
    )
    st.download_button("💾 Download Backup Sebelum Reset", backup, f"PRE_RESET_{sekarang_wib().strftime('%Y%m%d_%H%M%S')}.xlsx")
    understood = st.checkbox("Saya memahami bahwa data operasional akan di-reset")
    confirm = st.text_input("Ketik RESET-DATABASE", disabled=not understood)
    if st.button("🚨 Reset Database", disabled=not (understood and confirm == "RESET-DATABASE")):
        try:
            if REQUIRE_SERVER_BACKUP_BEFORE_RESET:
                result_backup = server_backup_now()
                st.info(f"Backup server sebelum reset berhasil: {result_backup.get('backup_name', 'WMS backup')}")
            telegram_ok, telegram_detail = send_telegram_document_detailed(
                "🚨 AUTO BACKUP SEBELUM RESET",
                backup,
                f"PRE_RESET_{sekarang_wib().strftime('%Y%m%d_%H%M%S')}.xlsx",
            )
            record_notification("Backup sebelum reset", telegram_ok, telegram_detail)
            reset_database()
            notification_flash(
                "Database berhasil di-reset setelah prosedur pengamanan.",
                [(telegram_ok, telegram_detail)],
            )
            st.rerun()
        except Exception as exc:
            show_api_error("Reset gagal", exc)


elif active_menu == "Tentang Aplikasi":
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
