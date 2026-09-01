"""Konfigurasi aplikasi, secrets, role, dan schema data."""

from zoneinfo import ZoneInfo

import streamlit as st

try:
    _SECRETS = dict(st.secrets)
except Exception:
    # Modul utilitas dan test harus tetap dapat diimpor di luar runtime Streamlit.
    # validate_runtime_security() tetap menghentikan aplikasi production bila
    # konfigurasi wajib belum tersedia.
    _SECRETS = {}

WIB = ZoneInfo("Asia/Jakarta")
APP_VERSION = "8.3-reliability"
EXPECTED_BACKEND_VERSION = "7.2-accounts"
URL_GSHEET_API = _SECRETS.get("URL_GSHEET_API", "")
API_SHARED_KEY = _SECRETS.get("API_SHARED_KEY", "")
AUTH_SIGNING_KEY = _SECRETS.get("AUTH_SIGNING_KEY", "")
TELEGRAM_BOT_TOKEN = _SECRETS.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = _SECRETS.get("TELEGRAM_CHAT_ID", "")
ACCOUNT_TELEGRAM_BOT_TOKEN = _SECRETS.get("ACCOUNT_TELEGRAM_BOT_TOKEN", "")
ACCOUNT_TELEGRAM_CHAT_ID = _SECRETS.get("ACCOUNT_TELEGRAM_CHAT_ID", "")
ALLOW_NO_LOGIN = bool(_SECRETS.get("ALLOW_NO_LOGIN", False))

# Pengaturan keamanan / reliabilitas. Semua punya default aman dan tetap kompatibel.
DATA_CACHE_TTL_SECONDS = max(15, int(_SECRETS.get("DATA_CACHE_TTL_SECONDS", 30)))
LOGIN_MAX_ATTEMPTS = max(3, int(_SECRETS.get("LOGIN_MAX_ATTEMPTS", 5)))
LOGIN_LOCK_SECONDS = max(30, int(_SECRETS.get("LOGIN_LOCK_SECONDS", 300)))
LOGIN_RATE_WINDOW_SECONDS = max(60, int(_SECRETS.get("LOGIN_RATE_WINDOW_SECONDS", 900)))
SESSION_TIMEOUT_MINUTES = max(5, int(_SECRETS.get("SESSION_TIMEOUT_MINUTES", 60)))
TELEGRAM_RETRY_ATTEMPTS = max(1, min(5, int(_SECRETS.get("TELEGRAM_RETRY_ATTEMPTS", 3))))
OFFLINE_USE_DEFAULT_STOCK = bool(_SECRETS.get("OFFLINE_USE_DEFAULT_STOCK", False))
SERVER_EMPTY_USE_DEFAULT_STOCK = bool(_SECRETS.get("SERVER_EMPTY_USE_DEFAULT_STOCK", False))
PBKDF2_ITERATIONS = max(200_000, int(_SECRETS.get("PBKDF2_ITERATIONS", 310_000)))
AUTO_SYNC_ENABLED = bool(_SECRETS.get("AUTO_SYNC_ENABLED", True))
AUTO_SYNC_SECONDS = max(20, int(_SECRETS.get("AUTO_SYNC_SECONDS", 30)))
HEALTH_TIMEOUT_SECONDS = max(3, min(12, int(_SECRETS.get("HEALTH_TIMEOUT_SECONDS", 5))))
WRITE_BLOCK_WHEN_OFFLINE = bool(_SECRETS.get("WRITE_BLOCK_WHEN_OFFLINE", True))
REQUIRE_HMAC = bool(_SECRETS.get("REQUIRE_HMAC", True))
ALLOW_LEGACY_PASSWORDS = bool(_SECRETS.get("ALLOW_LEGACY_PASSWORDS", False))
REQUIRE_SERVER_BACKUP_BEFORE_RESET = bool(_SECRETS.get("REQUIRE_SERVER_BACKUP_BEFORE_RESET", True))
# Performance mode: health-check berulang pada rerun cepat menggunakan hasil sesi terbaru.
HEALTH_CACHE_SECONDS = max(5, int(_SECRETS.get("HEALTH_CACHE_SECONDS", 20)))
SECONDARY_SYNC_SECONDS = max(AUTO_SYNC_SECONDS, int(_SECRETS.get("SECONDARY_SYNC_SECONDS", 60)))
BACKUP_STATUS_TTL_SECONDS = max(20, int(_SECRETS.get("BACKUP_STATUS_TTL_SECONDS", 60)))
MAX_UPLOAD_MB = max(1, min(15, int(_SECRETS.get("MAX_UPLOAD_MB", 6))))
RESTOCK_TARGET_MULTIPLIER = max(1, min(5, int(_SECRETS.get("RESTOCK_TARGET_MULTIPLIER", 2))))
NOTIFICATION_LOG_LIMIT = max(10, min(100, int(_SECRETS.get("NOTIFICATION_LOG_LIMIT", 30))))

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
PUBLIC_REGISTRATION_ROLES = {ROLE_STAFF, ROLE_ADMIN}

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
    "manage_accounts": {ROLE_DEVELOPER},
}
