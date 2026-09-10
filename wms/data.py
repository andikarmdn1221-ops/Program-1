"""Normalisasi data, cache, health check, dan sinkronisasi sesi."""

import hashlib
import re
import time
from urllib.parse import urlparse

import streamlit as st

from .api import api_get, api_health, show_api_error
from .config import (
    ACCOUNT_TELEGRAM_BOT_TOKEN,
    ACCOUNT_TELEGRAM_CHAT_ID,
    ALLOW_LEGACY_PASSWORDS,
    ALLOW_NO_LOGIN,
    API_SHARED_KEY,
    AUDIT_COLUMNS,
    AUTH_SIGNING_KEY,
    AUTO_SYNC_ENABLED,
    CONNECTION_FAILURE_THRESHOLD,
    DATA_CACHE_TTL_SECONDS,
    EXPECTED_BACKEND_VERSION,
    HEALTH_CACHE_SECONDS,
    MASTER_DEFAULT,
    MIN_SECRET_LENGTH,
    OFFLINE_USE_DEFAULT_STOCK,
    PRODUCTION_MODE,
    REQUIRE_HMAC,
    REQUIRE_SERVER_BACKUP_BEFORE_RESET,
    RIWAYAT_COLUMNS,
    SERVER_EMPTY_USE_DEFAULT_STOCK,
    STOK_DEFAULT,
    SYNC_ROW_WARNING_THRESHOLD,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    URL_GSHEET_API,
    WRITE_BLOCK_WHEN_OFFLINE,
)
from .utils import clean_item_name, parse_tx_datetime, safe_int, waktu_display


def _has_header(row, required_labels) -> bool:
    labels = {str(value or "").strip().casefold() for value in (row or [])}
    return all(str(label).casefold() in labels for label in required_labels)


def normalize_item_status(value) -> str:
    normalized = str(value or "Aktif").strip().casefold()
    if normalized == "aktif":
        return "Aktif"
    if normalized in {"nonaktif", "non-aktif", "inactive"}:
        return "Nonaktif"
    raise RuntimeError(f"Status master barang tidak valid: {value!s}")


def _cache_scope() -> tuple[str, str]:
    """Pisahkan cache per identitas agar hasil Developer tidak dipakai sesi lain."""
    return (
        str(st.session_state.get("auth_user", "Unknown")).strip().casefold(),
        str(st.session_state.get("auth_role", "Staff")).strip().casefold(),
    )


def normalize_stock_rows(raw_rows):
    stock = {}
    master = {}
    rows = raw_rows or []
    if (
        rows
        and isinstance(rows[0], list)
        and _has_header(rows[0], {"Nama Barang", "Jumlah Stok"})
    ):
        rows = rows[1:]

    seen_names = set()
    for row in rows:
        if not isinstance(row, list) or len(row) < 2:
            continue
        nama = clean_item_name(row[0])
        if not nama:
            continue
        normalized_name = nama.casefold()
        if normalized_name in seen_names:
            raise RuntimeError(f"Nama barang duplikat terdeteksi: '{nama}'")
        seen_names.add(normalized_name)
        raw_stock = str(row[1]).strip()
        if not raw_stock or not re.fullmatch(r"-?\d+(?:\.0+)?", raw_stock):
            raise RuntimeError(f"Jumlah stok untuk '{nama}' bukan angka yang valid")
        quantity = safe_int(row[1])
        if quantity < 0:
            raise RuntimeError(f"Jumlah stok untuk '{nama}' tidak boleh negatif")

        raw_minimum = str(row[3]).strip() if len(row) > 3 else "5"
        if not raw_minimum:
            raw_minimum = "5"
        if not re.fullmatch(r"\d+(?:\.0+)?", raw_minimum):
            raise RuntimeError(f"Batas minimum untuk '{nama}' bukan angka yang valid")
        minimum = safe_int(raw_minimum, 5)
        if minimum < 1:
            raise RuntimeError(f"Batas minimum untuk '{nama}' minimal 1")

        stock[nama] = quantity
        master[nama] = {
            "status": normalize_item_status(row[2] if len(row) > 2 else "Aktif"),
            "min_stok": minimum,
        }

    return stock, master


def normalize_history_rows(raw_rows):
    result = []
    rows = raw_rows or []
    if (
        rows
        and isinstance(rows[0], list)
        and _has_header(rows[0], {"ID Transaksi", "Waktu"})
    ):
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
                "ID Transaksi": "LEGACY-"
                + hashlib.sha1("|".join(map(str, row[:5])).encode())
                .hexdigest()[:10]
                .upper(),
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

    if isinstance(rows[0], list) and _has_header(rows[0], {"Waktu", "Aksi"}):
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
        result.append(
            {
                "Waktu": row[0] if len(row) > 0 else "",
                "User": "",
                "Role": "",
                "Aksi": row[1] if len(row) > 1 else "",
                "ID Transaksi": row[2] if len(row) > 2 else "",
                "Detail": row[3] if len(row) > 3 else "",
            }
        )
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
def load_data_cached(api_url: str, actor: str, role: str):
    del api_url, actor, role  # seluruh nilai tetap menjadi bagian dari cache key
    return api_get()


def refresh_data(force=False, quiet=False):
    try:
        raw = api_get() if force else load_data_cached(URL_GSHEET_API, *_cache_scope())
        stock, master, history, audit = normalize_server_data(raw)
        st.session_state.stok = stock
        st.session_state.master_info = master
        st.session_state.riwayat = history
        st.session_state.audit = audit
        st.session_state.is_connected = True
        st.session_state.connection_status = "online"
        st.session_state.connection_failure_count = 0
        st.session_state.data_source = "server"
        st.session_state.last_server_sync = waktu_display()
        st.session_state.last_server_sync_epoch = time.time()
        st.session_state.last_health_success_epoch = time.time()
        revision = (
            str(raw.get("data_revision", "") or "") if isinstance(raw, dict) else ""
        )
        backend_version = (
            str(raw.get("backend_version", "") or "") if isinstance(raw, dict) else ""
        )
        server_duration_ms = (
            safe_int(raw.get("server_duration_ms", 0)) if isinstance(raw, dict) else 0
        )
        if revision:
            st.session_state.server_revision = revision
        if backend_version:
            st.session_state.backend_version = backend_version
            st.session_state.backend_version_mismatch = (
                backend_version != EXPECTED_BACKEND_VERSION
            )
        if server_duration_ms > 0:
            st.session_state.last_server_duration_ms = server_duration_ms
        raw_counts = raw.get("row_counts", {}) if isinstance(raw, dict) else {}
        row_counts = {
            name: max(0, safe_int(raw_counts.get(name, 0)))
            for name in ("stok", "riwayat", "audit")
        }
        st.session_state.server_row_counts = row_counts
        st.session_state.sync_scale_warning = any(
            row_counts[name] >= SYNC_ROW_WARNING_THRESHOLD
            for name in ("riwayat", "audit")
        )
        raw_account_security = (
            raw.get("account_security", {}) if isinstance(raw, dict) else {}
        )
        if not isinstance(raw_account_security, dict):
            raw_account_security = {}
        st.session_state.dynamic_account_security = {
            name: max(0, safe_int(raw_account_security.get(name, 0)))
            for name in ("pbkdf2", "legacy", "active_legacy")
        }
        st.session_state.health_cache = {
            "ok": True,
            "backend_version": backend_version,
            "data_revision": revision,
            "capabilities": (
                dict(raw.get("capabilities", {}))
                if isinstance(raw, dict)
                and isinstance(raw.get("capabilities"), dict)
                else {}
            ),
        }
        st.session_state.last_health_epoch = time.time()
        st.session_state.last_health_check = waktu_display()
        return True
    except Exception as exc:
        failures = int(st.session_state.get("connection_failure_count", 0) or 0) + 1
        st.session_state.connection_failure_count = failures
        has_snapshot = "stok" in st.session_state

        if not has_snapshot:
            st.session_state.is_connected = False
            st.session_state.connection_status = "offline"
            if OFFLINE_USE_DEFAULT_STOCK:
                st.session_state.stok = STOK_DEFAULT.copy()
                st.session_state.master_info = {
                    k: v.copy() for k, v in MASTER_DEFAULT.items()
                }
                st.session_state.data_source = "default_offline"
            else:
                st.session_state.stok = {}
                st.session_state.master_info = {}
                st.session_state.data_source = "offline_empty"
            st.session_state.riwayat = []
            st.session_state.audit = []
        else:
            st.session_state.data_source = "last_known_session"
            if failures < CONNECTION_FAILURE_THRESHOLD:
                # Gangguan singkat tidak langsung mengubah seluruh UI menjadi offline.
                st.session_state.is_connected = True
                st.session_state.connection_status = "recovering"
            else:
                st.session_state.is_connected = False
                st.session_state.connection_status = "offline"

        if not quiet:
            show_api_error("Gagal mengambil data", exc)
        return False


def clear_and_refresh():
    # Bersihkan entri identitas aktif saja; sesi pengguna lain tidak ikut kehilangan cache.
    load_data_cached.clear(URL_GSHEET_API, *_cache_scope())
    refresh_data(force=True)


def _apply_health_to_session(health: dict):
    """Simpan hasil health check agar rerun Streamlit tidak memanggil Apps Script berulang."""
    health = health or {}
    revision = str(health.get("data_revision", "") or "")
    backend_version = str(health.get("backend_version", "") or "")
    st.session_state.health_cache = dict(health)
    st.session_state.last_health_epoch = time.time()
    st.session_state.last_health_check = waktu_display()
    st.session_state.last_health_success_epoch = time.time()
    st.session_state.is_connected = True
    st.session_state.connection_status = "online"
    st.session_state.connection_failure_count = 0
    if backend_version:
        st.session_state.backend_version = backend_version
        st.session_state.backend_version_mismatch = (
            backend_version != EXPECTED_BACKEND_VERSION
        )
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
        # Health endpoint dapat terlambat saat Apps Script cold start.
        # Coba full read sebelum menyatakan koneksi gagal.
        return refresh_data(force=True, quiet=True)


def require_online_operation():
    """Verifikasi server terbaru sebelum mutation; snapshot tidak pernah dianggap cukup untuk menulis."""
    verified = False
    health = {}
    try:
        health = get_server_health(force=True)
        verified = True
    except Exception:
        # Health ringan gagal: full read menjadi verifikasi cadangan.
        verified = refresh_data(force=True, quiet=True)
        health = st.session_state.get("health_cache", {})

    if WRITE_BLOCK_WHEN_OFFLINE and not verified:
        st.error(
            "⛔ Server belum dapat diverifikasi. Sistem mempertahankan data terakhir, "
            "tetapi perubahan stok ditahan agar tidak terjadi data ganda atau kehilangan data."
        )
        st.stop()

    contract_issues = backend_contract_issues(health)
    if contract_issues:
        st.error(
            "⛔ Perubahan ditahan karena backend belum memenuhi kontrak produksi: "
            + "; ".join(contract_issues)
            + ". Deploy Code_Accounts.gs yang sesuai terlebih dahulu."
        )
        st.stop()


def backend_contract_issues(health: dict) -> list[str]:
    """Return safe, human-readable reasons why mutations must stay blocked."""
    health = health if isinstance(health, dict) else {}
    version = str(health.get("backend_version", "") or "").strip()
    if version != EXPECTED_BACKEND_VERSION:
        return [
            f"versi backend {version or 'tidak diketahui'} (wajib {EXPECTED_BACKEND_VERSION})"
        ]

    capabilities = health.get("capabilities")
    if not isinstance(capabilities, dict):
        return ["capability keamanan backend tidak tersedia"]

    required_capabilities = {
        "hmac_required": "HMAC wajib",
        "account_auth_rate_limit": "rate-limit autentikasi akun",
        "idempotent_mutations": "idempotensi transaksi",
        "formula_guard": "proteksi formula spreadsheet",
        "mutation_rollback": "rollback mutasi",
        "backup_before_reset": "backup wajib sebelum reset",
        "drive_folder_configured": "folder Drive khusus",
        "local_roles_enforced": "pemetaan role akun lokal",
        "account_approval_configured": "persetujuan akun Telegram",
    }
    return [
        label
        for key, label in required_capabilities.items()
        if capabilities.get(key) is not True
    ]


def _looks_placeholder(value: str) -> bool:
    normalized = str(value or "").strip().casefold()
    markers = (
        "ganti-dengan",
        "deployment_id",
        "changeme",
        "change-me",
        "your-",
        "example",
    )
    return not normalized or any(marker in normalized for marker in markers)


def _valid_telegram_token(value: str) -> bool:
    return bool(re.fullmatch(r"\d{5,}:[A-Za-z0-9_-]{20,}", str(value or "").strip()))


def _valid_telegram_chat(value: str, *, numeric_only=False) -> bool:
    text = str(value or "").strip()
    if re.fullmatch(r"-?\d+", text):
        return True
    return not numeric_only and bool(re.fullmatch(r"@[A-Za-z0-9_]{5,32}", text))


def runtime_security_issues() -> list[str]:
    """Audit konfigurasi frontend tanpa mengungkapkan nilai secret."""
    issues = []
    parsed_url = urlparse(str(URL_GSHEET_API or "").strip())
    if not URL_GSHEET_API:
        issues.append("URL_GSHEET_API belum diisi")
    elif (
        parsed_url.scheme != "https"
        or parsed_url.netloc != "script.google.com"
        or not parsed_url.path.endswith("/exec")
        or _looks_placeholder(URL_GSHEET_API)
    ):
        issues.append("URL_GSHEET_API harus URL HTTPS Apps Script berakhiran /exec")

    for name, value in (
        ("API_SHARED_KEY", API_SHARED_KEY),
        ("AUTH_SIGNING_KEY", AUTH_SIGNING_KEY),
    ):
        if _looks_placeholder(value) or len(str(value or "")) < MIN_SECRET_LENGTH:
            issues.append(f"{name} harus acak dan minimal {MIN_SECRET_LENGTH} karakter")
    if API_SHARED_KEY and AUTH_SIGNING_KEY and API_SHARED_KEY == AUTH_SIGNING_KEY:
        issues.append("API_SHARED_KEY dan AUTH_SIGNING_KEY harus berbeda")

    if not REQUIRE_HMAC:
        issues.append("REQUIRE_HMAC wajib true")
    if ALLOW_NO_LOGIN:
        issues.append("ALLOW_NO_LOGIN wajib false")
    if ALLOW_LEGACY_PASSWORDS:
        issues.append("ALLOW_LEGACY_PASSWORDS wajib false")
    if not WRITE_BLOCK_WHEN_OFFLINE:
        issues.append("WRITE_BLOCK_WHEN_OFFLINE wajib true")
    if not REQUIRE_SERVER_BACKUP_BEFORE_RESET:
        issues.append("REQUIRE_SERVER_BACKUP_BEFORE_RESET wajib true")
    if not AUTO_SYNC_ENABLED:
        issues.append("AUTO_SYNC_ENABLED wajib true")

    if PRODUCTION_MODE:
        for name, value in (
            ("TELEGRAM_BOT_TOKEN", TELEGRAM_BOT_TOKEN),
            ("ACCOUNT_TELEGRAM_BOT_TOKEN", ACCOUNT_TELEGRAM_BOT_TOKEN),
        ):
            if not _valid_telegram_token(value):
                issues.append(f"{name} tidak valid")
        if not _valid_telegram_chat(TELEGRAM_CHAT_ID):
            issues.append("TELEGRAM_CHAT_ID tidak valid")
        if not _valid_telegram_chat(
            ACCOUNT_TELEGRAM_CHAT_ID, numeric_only=True
        ):
            issues.append("ACCOUNT_TELEGRAM_CHAT_ID harus ID chat numerik")

        from .auth import account_security_report, get_users_config

        users = get_users_config()
        if not users:
            issues.append("minimal satu akun lokal USERS wajib tersedia")
        seen_usernames = set()
        has_developer = False
        for username, raw_config in users.items():
            normalized_username = str(username or "").strip().casefold()
            if not re.fullmatch(r"[a-z0-9._-]{1,32}", normalized_username):
                issues.append(f"username akun lokal {username} tidak valid")
            if normalized_username in seen_usernames:
                issues.append("username akun lokal duplikat case-insensitive")
            seen_usernames.add(normalized_username)
            try:
                configured_role = str(dict(raw_config).get("role", "")).casefold()
            except (TypeError, ValueError):
                configured_role = ""
            if configured_role not in {"developer", "boss", "admin", "staff"}:
                issues.append(f"role akun lokal {username} tidak valid")
            has_developer = has_developer or configured_role == "developer"
        if users and not has_developer:
            issues.append("minimal satu akun lokal Developer wajib tersedia")
        for username, status in account_security_report():
            if status != "PBKDF2":
                issues.append(f"akun lokal {username} belum memakai PBKDF2")
    return issues


def validate_runtime_security():
    """Fail-closed untuk konfigurasi yang seharusnya wajib pada deployment production."""
    issues = runtime_security_issues()
    if issues:
        st.error("⛔ Konfigurasi production belum aman: " + "; ".join(issues))
        st.stop()
