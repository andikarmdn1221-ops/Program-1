import base64
import hashlib
import hmac
import io
import re
import threading
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
        /* Desktop/laptop tidak diubah. Aturan berikut hanya aktif <= 768px. */
        @media (max-width: 768px) {
            .block-container {
                padding-top: 0.75rem !important;
                padding-left: 0.8rem !important;
                padding-right: 0.8rem !important;
                padding-bottom: 1.5rem !important;
            }

            /* Kolom ditumpuk agar form, metric, dan header tidak sempit di HP. */
            [data-testid="stHorizontalBlock"] {
                flex-wrap: wrap !important;
                gap: 0.6rem !important;
            }

            [data-testid="column"] {
                flex: 1 1 100% !important;
                width: 100% !important;
                min-width: 100% !important;
            }

            h1 {
                font-size: 1.65rem !important;
                line-height: 1.2 !important;
            }

            h2 {
                font-size: 1.35rem !important;
            }

            h3 {
                font-size: 1.1rem !important;
            }

            /* Tombol lebih besar dan mudah ditekan di layar sentuh. */
            .stButton > button,
            .stDownloadButton > button,
            [data-testid="stFormSubmitButton"] > button {
                width: 100% !important;
                min-height: 2.9rem !important;
                font-size: 0.95rem !important;
            }

            /* Input mobile nyaman dan tidak terlalu kecil. */
            input, textarea, select {
                font-size: 16px !important;
            }

            [data-testid="stMetric"] {
                padding: 0.35rem 0 !important;
            }

            [data-testid="stMetricValue"] {
                font-size: 1.55rem !important;
            }

            /* Grafik mengikuti lebar layar HP. */
            [data-testid="stPlotlyChart"],
            [data-testid="stPlotlyChart"] > div {
                width: 100% !important;
                max-width: 100% !important;
            }

            /* Tabel tetap dapat digeser ke samping tanpa melebarkan halaman. */
            [data-testid="stDataFrame"] {
                max-width: 100vw !important;
                overflow-x: auto !important;
            }

            [data-testid="stCaptionContainer"],
            [data-testid="stAlert"] {
                line-height: 1.35 !important;
            }
        }

        @media (max-width: 420px) {
            .block-container {
                padding-left: 0.55rem !important;
                padding-right: 0.55rem !important;
            }

            h1 {
                font-size: 1.45rem !important;
            }

            [data-testid="stMetricValue"] {
                font-size: 1.35rem !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


inject_responsive_css()

WIB = ZoneInfo("Asia/Jakarta")
APP_VERSION = "6.0"
URL_GSHEET_API = st.secrets.get("URL_GSHEET_API", "")
API_SHARED_KEY = st.secrets.get("API_SHARED_KEY", "")
TELEGRAM_BOT_TOKEN = st.secrets.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = st.secrets.get("TELEGRAM_CHAT_ID", "")
ALLOW_NO_LOGIN = bool(st.secrets.get("ALLOW_NO_LOGIN", False))

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


def compress_image(uploaded_file, max_size=(1000, 1000), quality=78):
    if uploaded_file is None:
        return None
    try:
        uploaded_file.seek(0)
        img = Image.open(uploaded_file)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        output = io.BytesIO()
        img.save(output, format="JPEG", quality=quality, optimize=True)
        return output.getvalue()
    except Exception as exc:
        st.warning(f"Foto tidak dapat dikompres: {exc}")
        try:
            uploaded_file.seek(0)
            return uploaded_file.getvalue()
        except Exception:
            return None


def to_image_payload(uploaded_file):
    if uploaded_file is None:
        return {}
    raw = compress_image(uploaded_file)
    if not raw:
        return {}
    return {
        "image_base64": base64.b64encode(raw).decode("utf-8"),
        "image_name": f"{sekarang_wib().strftime('%Y%m%d_%H%M%S')}_{getattr(uploaded_file, 'name', 'bukti.jpg')}",
        "image_mime": "image/jpeg",
    }


# ============================================================
# API CLIENT
# ============================================================
def api_get(timeout=20):
    if not URL_GSHEET_API:
        raise RuntimeError("URL_GSHEET_API belum diatur di Streamlit Secrets.")
    if not API_SHARED_KEY:
        raise RuntimeError("API_SHARED_KEY belum diatur di Streamlit Secrets.")
    response = requests.get(URL_GSHEET_API, params={"key": API_SHARED_KEY}, timeout=timeout)
    response.raise_for_status()
    data = response.json()
    if isinstance(data, dict) and data.get("ok") is False:
        raise RuntimeError(data.get("message", "Server menolak permintaan."))
    return data


def api_post(payload: dict, timeout=60):
    if not URL_GSHEET_API:
        raise RuntimeError("URL_GSHEET_API belum diatur di Streamlit Secrets.")
    if not API_SHARED_KEY:
        raise RuntimeError("API_SHARED_KEY belum diatur di Streamlit Secrets.")
    payload = {**payload, "api_key": API_SHARED_KEY}
    response = requests.post(URL_GSHEET_API, json=payload, timeout=timeout)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict):
        raise RuntimeError("Respons server tidak valid.")
    if data.get("ok") is False:
        raise RuntimeError(data.get("message", "Operasi ditolak server."))
    return data


def show_api_error(prefix: str, exc: Exception):
    if isinstance(exc, requests.exceptions.Timeout):
        st.error(f"{prefix}: koneksi ke server timeout.")
    elif isinstance(exc, requests.exceptions.RequestException):
        st.error(f"{prefix}: gangguan jaringan/API ({exc}).")
    else:
        st.error(f"{prefix}: {exc}")


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
    """Jangan sampai token Telegram ikut muncul di pesan/log error."""
    text = str(exc)
    if TELEGRAM_BOT_TOKEN:
        text = text.replace(str(TELEGRAM_BOT_TOKEN), "***TOKEN***")
    return text


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


def send_telegram(message: str, image_bytes=None):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False
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
        if not res.ok:
            print(f"[Telegram error] {telegram_response_detail(res)}")
            return False
        return True
    except Exception as exc:
        # Jangan mematikan transaksi hanya karena Telegram gagal.
        print(f"[Telegram error] {telegram_safe_exception(exc)}")
        return False


def send_telegram_document_detailed(message: str, file_bytes: bytes, file_name: str):
    """Versi detail untuk tombol backup agar penyebab gagal terlihat."""
    if not TELEGRAM_BOT_TOKEN:
        return False, "TELEGRAM_BOT_TOKEN belum diisi."
    if not TELEGRAM_CHAT_ID:
        return False, "TELEGRAM_CHAT_ID belum diisi."
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
        if not res.ok:
            return False, telegram_response_detail(res)
        return True, "Backup berhasil dikirim ke Telegram."
    except requests.exceptions.Timeout:
        return False, "Koneksi Telegram timeout saat mengirim backup."
    except requests.exceptions.RequestException as exc:
        return False, f"Gangguan koneksi Telegram: {telegram_safe_exception(exc)}"
    except Exception as exc:
        return False, f"Pengiriman backup gagal: {telegram_safe_exception(exc)}"


def send_telegram_document(message: str, file_bytes: bytes, file_name: str):
    ok, _detail = send_telegram_document_detailed(message, file_bytes, file_name)
    return ok


def telegram_async(message: str, image_bytes=None):
    threading.Thread(target=send_telegram, args=(message, image_bytes), daemon=True).start()


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
        return STOK_DEFAULT.copy(), MASTER_DEFAULT.copy(), [], []

    stock, master = normalize_stock_rows(data.get("stok", []))
    history = normalize_history_rows(data.get("riwayat", []))
    audit = normalize_audit_rows(data.get("audit", []))

    if not stock:
        stock = STOK_DEFAULT.copy()
        master = {k: v.copy() for k, v in MASTER_DEFAULT.items()}
    return stock, master, history, audit


@st.cache_data(ttl=90, show_spinner=False)
def load_data_cached(api_url: str):
    del api_url  # key cache tetap berubah bila URL berubah
    return api_get()


def refresh_data(force=False):
    try:
        raw = api_get() if force else load_data_cached(URL_GSHEET_API)
        stock, master, history, audit = normalize_server_data(raw)
        st.session_state.stok = stock
        st.session_state.master_info = master
        st.session_state.riwayat = history
        st.session_state.audit = audit
        st.session_state.is_connected = True
        return True
    except Exception as exc:
        st.session_state.is_connected = False
        if "stok" not in st.session_state:
            st.session_state.stok = STOK_DEFAULT.copy()
            st.session_state.master_info = {k: v.copy() for k, v in MASTER_DEFAULT.items()}
            st.session_state.riwayat = []
            st.session_state.audit = []
        show_api_error("Gagal mengambil data", exc)
        return False


def clear_and_refresh():
    st.cache_data.clear()
    refresh_data(force=True)


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


def password_matches(input_password: str, configured: dict) -> bool:
    if configured.get("password_hash"):
        supplied_hash = hashlib.sha256(input_password.encode()).hexdigest()
        return hmac.compare_digest(supplied_hash, str(configured["password_hash"]))
    if configured.get("password") is not None:
        return hmac.compare_digest(str(input_password), str(configured["password"]))
    return False


def login_gate():
    users = get_users_config()
    if not users:
        if ALLOW_NO_LOGIN:
            st.session_state.auth_user = "Local Developer"
            st.session_state.auth_role = ROLE_DEVELOPER
            return
        st.error("Konfigurasi USERS belum dibuat di Streamlit Secrets.")
        st.info("Tambahkan akun Developer, Boss, Admin, dan Staff di Streamlit Secrets sebelum aplikasi digunakan.")
        st.stop()

    if st.session_state.get("auth_user"):
        st.session_state.auth_role = normalize_role(st.session_state.get("auth_role"))
        return

    st.title("🔐 Login WMS Microcement")
    st.caption("Masuk menggunakan akun yang diberikan sesuai jabatan.")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Masuk", use_container_width=True)

    if submit:
        cfg = users.get(username)
        if cfg and password_matches(password, dict(cfg)):
            st.session_state.auth_user = username
            st.session_state.auth_role = normalize_role(dict(cfg).get("role", ROLE_STAFF))
            st.rerun()
        st.error("Username atau password salah.")
    st.stop()


def current_role() -> str:
    return normalize_role(st.session_state.get("auth_role", ROLE_STAFF))


def has_permission(permission: str) -> bool:
    return current_role() in PERMISSIONS.get(permission, set())


def actor_payload() -> dict:
    return {
        "actor": str(st.session_state.get("auth_user", "Unknown")),
        "role": current_role(),
    }


def actor_label() -> str:
    return f"{st.session_state.get('auth_user', 'Unknown')} ({current_role()})"


def require_permission(permission: str):
    if not has_permission(permission):
        st.error("⛔ Anda tidak memiliki izin untuk membuka fitur ini.")
        st.stop()


# ============================================================
# EXPORT
# ============================================================
def excel_bytes(df, sheet_name="Data"):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    return output.getvalue()


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
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        pd.DataFrame(stock_rows).to_excel(writer, index=False, sheet_name="Stok Barang")
        pd.DataFrame(history, columns=RIWAYAT_COLUMNS).to_excel(writer, index=False, sheet_name="Riwayat")
        pd.DataFrame(audit).to_excel(writer, index=False, sheet_name="Audit")
    return out.getvalue()


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
def do_transaction(tipe, barang, jumlah, tgl_transaksi, keterangan, file_uploaded=None):
    payload = {
        "action": "transaction",
        "tx_id": make_tx_id(),
        "tanggal": tgl_transaksi.strftime("%d-%m-%Y"),
        "waktu": combine_manual_date(tgl_transaksi),
        "tipe": tipe,
        "barang": barang,
        "jumlah": int(jumlah),
        "keterangan": keterangan.strip() or "-",
        **to_image_payload(file_uploaded),
        **actor_payload(),
    }
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
            "waktu": combine_manual_date(date.today()),
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
            "new_keterangan": new_tx["Pembeli / Keterangan"],
            **actor_payload(),
        }
    )
    clear_and_refresh()
    return result


def void_transaction(tx_id):
    result = api_post({"action": "transaction_void", "tx_id": tx_id, **actor_payload()})
    clear_and_refresh()
    return result


def adjust_stock(barang, stok_baru, alasan, tgl_transaksi):
    result = api_post(
        {
            "action": "stock_adjust",
            "tx_id": make_tx_id("ADJ"),
            "barang": barang,
            "stok_baru": int(stok_baru),
            "alasan": alasan.strip() or "Penyesuaian stok",
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
# STARTUP
# ============================================================
login_gate()

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

    if has_permission("reset"):
        menu_options.append("⚙️ Pengaturan & Reset")

    menu_options.append("ℹ️ Tentang Aplikasi")

    active_raw = st.radio("NAVIGASI", menu_options)
    active_menu = active_raw.split(" ", 1)[1]

    st.markdown("---")
    if st.session_state.get("is_connected"):
        st.success("🟢 Database terhubung")
    else:
        st.error("🔴 Database offline")

    telegram_status = st.session_state.get("telegram_test_status")
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        st.warning("⚪ Telegram belum dikonfigurasi")
    elif telegram_status is True:
        st.success("🟢 Telegram terhubung")
    elif telegram_status is False:
        st.error("🔴 Telegram gagal terhubung")
    else:
        st.info("🟡 Telegram dikonfigurasi · belum diuji")

    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
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
        st.session_state.pop("auth_user", None)
        st.session_state.pop("auth_role", None)
        st.rerun()


# ============================================================
# HEADER
# ============================================================
h1, h2, h3 = st.columns([3, 1.5, 1])
with h1:
    st.title(f"📦 {active_menu}")
with h2:
    st.markdown(
        f"<div style='text-align:right;font-size:12px;color:gray;padding-top:14px'>{waktu_display()}</div>",
        unsafe_allow_html=True,
    )
with h3:
    if st.button("🔄 Segarkan", use_container_width=True):
        clear_and_refresh()
        st.rerun()

st.divider()

if not st.session_state.get("is_connected"):
    st.error("🚨 Database tidak dapat dihubungi. Mode data terakhir/default sedang digunakan.")

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
    if critical or out_of_stock:
        st.warning(f"⚠️ {len(out_of_stock)} item habis dan {len(critical)} item kritis.")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Jenis Barang Aktif", len(active_stock))
    c2.metric("Total Stok", f"{sum(active_stock.values())} pcs")
    c3.metric("Stok Kritis", len(critical))
    c4.metric("Stok Habis", len(out_of_stock))

    st.divider()
    left, right = st.columns(2)
    with left:
        st.subheader("📊 Status Stok")
        safe_count = len(active_stock) - len(critical) - len(out_of_stock)
        df_chart = pd.DataFrame(
            {"Status": ["Aman", "Kritis", "Habis"], "Jumlah": [safe_count, len(critical), len(out_of_stock)]}
        )
        fig = px.pie(df_chart, names="Status", values="Jumlah", hole=0.52)
        st.plotly_chart(fig, use_container_width=True)

    with right:
        st.subheader("🚨 Perlu Perhatian")
        rows = []
        for nama in sorted(set(critical + out_of_stock), key=natural_key):
            qty = active_stock[nama]
            minimum = master.get(nama, {}).get("min_stok", 5)
            rows.append(
                {
                    "Nama Barang": nama,
                    "Stok": qty,
                    "Minimum": minimum,
                    "Status": status_stok(qty, minimum),
                }
            )
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.success("Semua stok aman.")

    st.divider()
    st.subheader("📋 Ringkasan Stok")
    keyword = st.text_input("🔍 Cari barang", placeholder="Contoh: top coat")
    rows = []
    for nama in sorted(stock, key=natural_key):
        if keyword and keyword.lower() not in nama.lower():
            continue
        info = master.get(nama, {})
        rows.append(
            {
                "Nama Barang": nama,
                "Stok": stock[nama],
                "Batas Min": info.get("min_stok", 5),
                "Status Item": info.get("status", "Aktif"),
                "Status Stok": status_stok(stock[nama], info.get("min_stok", 5), info.get("status", "Aktif")),
            }
        )
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


elif active_menu == "Lihat Semua Stok":
    rows = []
    for nama in sorted(stock, key=natural_key):
        info = master.get(nama, {})
        rows.append(
            {
                "Nama Barang": nama,
                "Jumlah Stok": stock[nama],
                "Batas Minimum": info.get("min_stok", 5),
                "Status Item": info.get("status", "Aktif"),
                "Indikator": status_stok(stock[nama], info.get("min_stok", 5), info.get("status", "Aktif")),
            }
        )
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    x1, x2 = st.columns(2)
    x1.download_button(
        "📥 Ekspor Excel",
        excel_bytes(df, "Stok"),
        f"Stok_{sekarang_wib().strftime('%Y%m%d')}.xlsx",
        use_container_width=True,
    )
    pdf = pdf_table(
        "LAPORAN STOK GUDANG",
        ["Nama", "Stok", "Min", "Status Item", "Indikator"],
        [[r["Nama Barang"], r["Jumlah Stok"], r["Batas Minimum"], r["Status Item"], r["Indikator"]] for r in rows],
        [85, 25, 20, 30, 30],
    )
    x2.download_button(
        "📄 Cetak PDF",
        pdf,
        f"Stok_{sekarang_wib().strftime('%Y%m%d')}.pdf",
        use_container_width=True,
    )


elif active_menu == "Kelola Master Item":
    require_permission("manage_master")
    tab_add, tab_edit = st.tabs(["➕ Tambah Barang", "⚙️ Edit / Nonaktifkan"])

    with tab_add:
        with st.form("master_add", clear_on_submit=True):
            nama = st.text_input("Nama Barang")
            a, b = st.columns(2)
            stok_awal = a.number_input("Stok Awal", min_value=0, value=0, step=1)
            minimum = b.number_input("Batas Stok Minimum", min_value=1, value=5, step=1)
            submit = st.form_submit_button("➕ Tambah Barang", use_container_width=True)
        if submit:
            nama = nama.strip()
            if not nama:
                st.warning("Nama barang wajib diisi.")
            elif nama in stock:
                st.error("Nama barang sudah ada.")
            else:
                try:
                    add_master(nama, stok_awal, minimum)
                    telegram_async(f"✨ *ITEM BARU*\n📦 {nama}\nStok awal: {stok_awal} pcs\nMinimum: {minimum} pcs\n👤 {actor_label()}")
                    st.success("Barang berhasil ditambahkan.")
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
                    update_master(selected, new_name.strip(), new_status, new_min)
                    st.success("Master barang diperbarui.")
                    st.rerun()
                except Exception as exc:
                    show_api_error("Gagal memperbarui master", exc)

            with st.expander("🗑️ Hapus permanen (hanya jika belum pernah ditransaksikan)"):
                st.caption("Jika barang sudah memiliki riwayat, server akan menolak penghapusan. Gunakan status Nonaktif.")
                confirm = st.checkbox(f"Saya yakin ingin menghapus {selected}", key="confirm_delete_master")
                if st.button("Hapus Permanen", disabled=not confirm):
                    try:
                        delete_master(selected)
                        st.success("Barang berhasil dihapus.")
                        st.rerun()
                    except Exception as exc:
                        show_api_error("Barang tidak dapat dihapus", exc)


elif active_menu in ("Barang Masuk", "Barang Keluar"):
    require_permission("transaction")

    # Sinkronkan stok terbaru dari server pada setiap rerun halaman transaksi.
    # Ini hanya memperbarui tampilan stok lokal; perhitungan transaksi tetap
    # dilakukan dan divalidasi oleh backend seperti sebelumnya.
    refresh_data(force=True)
    stock = st.session_state.stok
    master = st.session_state.master_info
    history = st.session_state.riwayat

    tipe = "MASUK" if active_menu == "Barang Masuk" else "KELUAR"
    names = sorted(
        [k for k in stock if master.get(k, {}).get("status", "Aktif") == "Aktif"],
        key=natural_key,
    )
    if not names:
        st.warning("Tidak ada barang aktif.")
    else:
        with st.form(f"tx_{tipe.lower()}", clear_on_submit=True):
            barang = st.selectbox("Pilih Barang", names)
            st.info(f"Stok saat ini: **{stock.get(barang, 0)} pcs**")
            jumlah = st.number_input("Jumlah (pcs)", min_value=1, value=1, step=1)
            tgl = st.date_input("Tanggal Transaksi", value=date.today())
            label_ket = "Supplier / Keterangan" if tipe == "MASUK" else "Nama Pembeli / Proyek"
            keterangan = st.text_input(label_ket, "" if tipe == "KELUAR" else "-")
            bukti = st.file_uploader(
                "Upload Bukti / Nota (Opsional)" if tipe == "MASUK" else "Upload Surat Jalan (Opsional)",
                type=["jpg", "jpeg", "png", "jfif", "webp"],
            )
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
                    result = do_transaction(tipe, barang, jumlah, tgl, keterangan, bukti)
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
                    telegram_async(msg, image_bytes)
                    st.success(f"Transaksi berhasil. Stok akhir: {remaining} pcs.")
                    alert = result.get("alert")
                    if alert:
                        telegram_async(alert)
                    st.rerun()
                except Exception as exc:
                    show_api_error("Transaksi gagal", exc)


elif active_menu == "Penyesuaian Stok":
    require_permission("stock_adjust")
    st.info("Gunakan fitur ini saat stok fisik berbeda dari stok sistem. Semua perubahan dicatat di riwayat dan audit log.")
    names = sorted(
        [k for k in stock if master.get(k, {}).get("status", "Aktif") == "Aktif"],
        key=natural_key,
    )
    if not names:
        st.warning("Tidak ada barang aktif.")
    else:
        with st.form("stock_adjustment", clear_on_submit=False):
            barang = st.selectbox("Pilih Barang", names)
            stok_lama = stock.get(barang, 0)
            st.metric("Stok Sistem Saat Ini", f"{stok_lama} pcs")
            stok_baru = st.number_input("Stok Fisik / Stok Baru", min_value=0, value=int(stok_lama), step=1)
            tgl = st.date_input("Tanggal Penyesuaian", value=date.today())
            alasan = st.text_area("Alasan Penyesuaian", placeholder="Contoh: hasil stock opname / selisih pencatatan")
            submit_adjust = st.form_submit_button("🧮 Simpan Penyesuaian Stok", use_container_width=True)

        if submit_adjust:
            if int(stok_baru) == int(stok_lama):
                st.warning("Stok baru sama dengan stok saat ini. Tidak ada perubahan.")
            elif not alasan.strip():
                st.warning("Alasan penyesuaian wajib diisi.")
            else:
                try:
                    result = adjust_stock(barang, stok_baru, alasan, tgl)
                    delta = result.get("selisih", int(stok_baru) - int(stok_lama))
                    telegram_async(
                        f"🧮 *PENYESUAIAN STOK*\n📦 {barang}\n"
                        f"Stok lama: {stok_lama} pcs\nStok baru: {stok_baru} pcs\n"
                        f"Selisih: {delta:+d} pcs\n📝 {alasan.strip()}\n👤 {actor_label()}"
                    )
                    alert = result.get("alert")
                    if alert:
                        telegram_async(alert)
                    st.success("Penyesuaian stok berhasil dan tercatat di audit log.")
                    st.rerun()
                except Exception as exc:
                    show_api_error("Penyesuaian stok gagal", exc)


elif active_menu == "Koreksi Transaksi":
    require_permission("correct_transaction")
    editable = [tx for tx in history if tx.get("Status", "AKTIF") == "AKTIF" and tx.get("Tipe") in ("MASUK", "KELUAR")]
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
                default_date = parsed.date() if parsed else date.today()
            tgl = st.date_input("Tanggal", value=default_date)
            tipe = st.selectbox("Tipe", ["MASUK", "KELUAR"], index=0 if old["Tipe"] == "MASUK" else 1)
            names = sorted([k for k in stock if master.get(k, {}).get("status", "Aktif") == "Aktif"], key=natural_key)
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
                telegram_async(
                    f"✏️ *KOREKSI TRANSAKSI*\nID: {old['ID Transaksi']}\n"
                    f"Lama: {old['Tipe']} {old['Barang']} {old['Jumlah']} pcs\n"
                    f"Baru: {tipe} {barang} {jumlah} pcs\n👤 {actor_label()}"
                )
                st.success(f"Koreksi tersimpan sebagai transaksi baru {result.get('new_tx_id', '')}.")
                st.rerun()
            except Exception as exc:
                show_api_error("Koreksi gagal", exc)

        st.divider()
        st.warning("Void membatalkan transaksi tanpa menghapus jejak audit.")
        confirm_void = st.checkbox("Saya yakin ingin membatalkan transaksi ini")
        if st.button("🚫 Void Transaksi", disabled=not confirm_void):
            try:
                void_transaction(old["ID Transaksi"])
                telegram_async(f"🚫 *VOID TRANSAKSI*\nID: {old['ID Transaksi']}\n{old['Tipe']} {old['Barang']} {old['Jumlah']} pcs\n👤 {actor_label()}")
                st.success("Transaksi dibatalkan dan stok dikembalikan secara aman.")
                st.rerun()
            except Exception as exc:
                show_api_error("Void gagal", exc)


elif active_menu == "Riwayat Transaksi":
    if not history:
        st.info("Belum ada riwayat transaksi.")
    else:
        df = pd.DataFrame(history, columns=RIWAYAT_COLUMNS)
        f1, f2, f3 = st.columns(3)
        tipe_filter = f1.selectbox("Tipe", ["SEMUA", "MASUK", "KELUAR", "PENYESUAIAN", "BARANG BARU"])
        status_filter = f2.selectbox("Status", ["SEMUA", "AKTIF", "VOID", "DIKOREKSI"])
        search = f3.text_input("Cari barang / keterangan")

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
        )
        pdf_rows = [
            [r["Waktu"], r["Tipe"], r["Barang"], r["Jumlah"], r["Pembeli / Keterangan"], r["Status"]]
            for _, r in df.iterrows()
        ]
        pdf = pdf_table("RIWAYAT TRANSAKSI", ["Waktu", "Tipe", "Barang", "Qty", "Keterangan", "Status"], pdf_rows, [40, 25, 65, 20, 95, 30])
        x2.download_button(
            "📄 Cetak Riwayat PDF",
            pdf,
            f"Riwayat_{sekarang_wib().strftime('%Y%m%d')}.pdf",
            use_container_width=True,
        )


elif active_menu == "Laporan Periodik":
    require_permission("view_reports")
    d1, d2 = st.columns(2)
    start = d1.date_input("Tanggal Mulai", value=date.today().replace(day=1))
    end = d2.date_input("Tanggal Selesai", value=date.today())
    if start > end:
        st.error("Tanggal mulai tidak boleh melebihi tanggal selesai.")
    else:
        selected = []
        for tx in history:
            if tx.get("Status", "AKTIF") != "AKTIF":
                continue
            parsed = parse_tx_datetime(tx.get("Waktu", ""))
            if parsed and start <= parsed.date() <= end:
                selected.append(tx)
        if not selected:
            st.info("Tidak ada transaksi aktif pada periode ini.")
        else:
            df = pd.DataFrame(selected, columns=RIWAYAT_COLUMNS)
            masuk = df.loc[df["Tipe"] == "MASUK", "Jumlah"].apply(safe_int).sum()
            keluar = df.loc[df["Tipe"] == "KELUAR", "Jumlah"].apply(safe_int).sum()
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Masuk", f"{masuk} pcs")
            m2.metric("Total Keluar", f"{keluar} pcs")
            m3.metric("Total Transaksi", len(df))
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.download_button(
                "📥 Ekspor Laporan Excel",
                excel_bytes(df, "Laporan Periodik"),
                f"Laporan_{start}_{end}.xlsx",
                use_container_width=True,
            )


elif active_menu == "Audit Log":
    require_permission("view_audit")
    audit_rows = st.session_state.get("audit", [])
    if not audit_rows:
        st.info("Belum ada audit log.")
    else:
        df_audit = pd.DataFrame(audit_rows, columns=AUDIT_COLUMNS)
        a1, a2, a3 = st.columns(3)
        user_filter = a1.selectbox("User", ["SEMUA"] + sorted([x for x in df_audit["User"].dropna().astype(str).unique() if x]))
        role_filter = a2.selectbox("Role", ["SEMUA"] + sorted([x for x in df_audit["Role"].dropna().astype(str).unique() if x]))
        audit_search = a3.text_input("Cari aksi / detail")
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
        )


elif active_menu == "Backup Data":
    require_permission("backup")
    st.write("Backup berisi stok, riwayat transaksi, URL bukti, dan audit log.")
    backup = full_backup_bytes(stock, master, history, st.session_state.get("audit", []))
    filename = f"BACKUP_WMS_{sekarang_wib().strftime('%Y%m%d_%H%M%S')}.xlsx"
    b1, b2 = st.columns(2)
    b1.download_button("💾 Download Backup", backup, filename, use_container_width=True)
    if b2.button("📤 Kirim Backup ke Telegram", use_container_width=True):
        ok, detail = send_telegram_document_detailed(
            f"💾 BACKUP WMS\n{waktu_display()}",
            backup,
            filename,
        )
        if ok:
            st.success(detail)
        else:
            st.error(f"Backup gagal dikirim ke Telegram — {detail}")


elif active_menu == "Pengaturan & Reset":
    require_permission("reset")
    st.warning("Reset menghapus data operasional dan mengembalikan master awal. Backup dahulu.")
    backup = full_backup_bytes(stock, master, history, st.session_state.get("audit", []))
    st.download_button("💾 Download Backup Sebelum Reset", backup, f"PRE_RESET_{sekarang_wib().strftime('%Y%m%d_%H%M%S')}.xlsx")
    understood = st.checkbox("Saya memahami bahwa data operasional akan di-reset")
    confirm = st.text_input("Ketik RESET-DATABASE", disabled=not understood)
    if st.button("🚨 Reset Database", disabled=not (understood and confirm == "RESET-DATABASE")):
        try:
            send_telegram_document("🚨 AUTO BACKUP SEBELUM RESET", backup, f"PRE_RESET_{sekarang_wib().strftime('%Y%m%d_%H%M%S')}.xlsx")
            reset_database()
            st.success("Database berhasil di-reset.")
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
    st.caption("Transaksi, penyesuaian stok, koreksi, void, dan master item diproses server-side dengan LockService agar lebih aman untuk multi-user.")
