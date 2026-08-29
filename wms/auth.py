"""Autentikasi, session, role, dan permission."""

import hashlib
import hmac
import secrets
import time

import streamlit as st

from .config import (
    ALLOW_LEGACY_PASSWORDS,
    ALLOW_NO_LOGIN,
    APP_VERSION,
    LOGIN_LOCK_SECONDS,
    LOGIN_MAX_ATTEMPTS,
    PBKDF2_ITERATIONS,
    PERMISSIONS,
    ROLE_ADMIN,
    ROLE_BOSS,
    ROLE_DEVELOPER,
    ROLE_STAFF,
    SESSION_TIMEOUT_MINUTES,
)

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
    for key in ("auth_user", "auth_display_name", "auth_role", "auth_login_at", "auth_last_activity"):
        st.session_state.pop(key, None)


def _complete_login(username: str, role: str, now: float, display_name=""):
    st.session_state.auth_user = username
    st.session_state.auth_display_name = display_name or username
    st.session_state.auth_role = normalize_role(role)
    st.session_state.auth_login_at = now
    st.session_state.auth_last_activity = now
    st.session_state.login_attempts = 0
    st.session_state.login_lock_until = 0
    st.rerun()


def _record_failed_login(now: float):
    attempts = int(st.session_state.get("login_attempts", 0)) + 1
    st.session_state.login_attempts = attempts
    remaining_attempts = LOGIN_MAX_ATTEMPTS - attempts
    if attempts >= LOGIN_MAX_ATTEMPTS:
        st.session_state.login_lock_until = now + LOGIN_LOCK_SECONDS
        st.error(
            f"Login dikunci sementara selama {LOGIN_LOCK_SECONDS} detik karena terlalu banyak percobaan gagal."
        )
    else:
        st.error(f"Username atau password salah. Sisa percobaan: {remaining_attempts}.")


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

    st.title("🔐 WMS Microcement")
    st.caption("Masuk atau ajukan akun baru sesuai jabatan.")

    if lock_until > now:
        remaining = max(1, int(lock_until - now))
        st.error(f"Terlalu banyak percobaan login gagal. Coba lagi dalam {remaining} detik.")
        st.stop()

    login_tab, register_tab = st.tabs(["Masuk", "Daftar Akun Baru"])

    with login_tab:
        with st.form("login_form"):
            username = st.text_input("Username").strip()
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Masuk", use_container_width=True)

        if submit:
            cfg = users.get(username)
            if cfg and password_matches(password, dict(cfg)):
                _complete_login(username, dict(cfg).get("role", ROLE_STAFF), now)

            try:
                from .accounts import authenticate_account

                dynamic = authenticate_account(username, password)
            except Exception:
                dynamic = {"authenticated": False, "status": "ERROR"}

            if dynamic.get("authenticated"):
                _complete_login(
                    str(dynamic.get("username") or username),
                    str(dynamic.get("role") or ROLE_STAFF),
                    now,
                    str(dynamic.get("full_name") or username),
                )

            status = str(dynamic.get("status") or "").upper()
            if status == "PENDING":
                st.warning("Akun masih menunggu persetujuan Developer.")
            elif status == "SUSPENDED":
                st.error("Akun sedang dinonaktifkan. Hubungi Developer.")
            elif status == "REJECTED":
                st.error("Permintaan akun ditolak. Hubungi Developer jika diperlukan.")
            elif status == "ERROR":
                st.error("Layanan akun sedang tidak dapat dihubungi. Coba lagi nanti.")
            else:
                _record_failed_login(now)

    with register_tab:
        st.info("Akun baru belum bisa login sebelum disetujui oleh Developer.")
        role_choices = [ROLE_STAFF, ROLE_ADMIN, ROLE_BOSS, ROLE_DEVELOPER]
        with st.form("registration_form", clear_on_submit=False):
            full_name = st.text_input("Nama lengkap", key="register_full_name")
            new_username = st.text_input(
                "Username baru",
                help="Gunakan huruf kecil, angka, titik, garis bawah, atau tanda minus.",
                key="register_username",
            )
            position = st.text_input("Jabatan", key="register_position")
            requested_role = st.selectbox(
                "Role yang diminta",
                role_choices,
                help="Developer akan menentukan role final saat menyetujui.",
            )
            new_password = st.text_input("Password", type="password", key="register_password")
            confirm_password = st.text_input(
                "Ulangi password", type="password", key="register_password_confirm"
            )
            register_submit = st.form_submit_button(
                "Kirim Permintaan Akun", use_container_width=True
            )

        if register_submit:
            try:
                from .accounts import normalize_username, register_account
                from .notifications import send_account_request_notification

                clean_username = normalize_username(new_username)
                if clean_username in {str(name).lower() for name in users}:
                    raise ValueError("Username sudah digunakan.")
                if not position.strip():
                    raise ValueError("Jabatan wajib diisi.")
                if new_password != confirm_password:
                    raise ValueError("Konfirmasi password tidak sama.")

                result = register_account(
                    full_name,
                    clean_username,
                    new_password,
                    requested_role,
                    position,
                )
                request_id = str(result.get("request_id") or "-")
                telegram_ok, telegram_detail = send_account_request_notification(
                    full_name=full_name,
                    username=clean_username,
                    position=position,
                    requested_role=requested_role,
                    request_id=request_id,
                )
                if telegram_ok:
                    st.success(
                        "Permintaan berhasil dikirim. Tunggu Developer menyetujui akun melalui menu Kelola Akun."
                    )
                else:
                    st.warning(
                        "Permintaan tersimpan dan tetap menunggu persetujuan, tetapi notifikasi Telegram gagal: "
                        + telegram_detail
                    )
            except Exception as exc:
                st.error(str(exc))
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
