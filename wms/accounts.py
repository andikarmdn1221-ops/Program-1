"""Pendaftaran, login, dan pengelolaan akun dinamis melalui backend."""

import hashlib
import hmac
import re

from .api import api_post
from .config import AUTH_SIGNING_KEY, PUBLIC_REGISTRATION_ROLES, VALID_ROLES


def normalize_username(value: str) -> str:
    username = str(value or "").strip().lower()
    if not re.fullmatch(r"[a-z0-9._-]{4,32}", username):
        raise ValueError(
            "Username harus 4–32 karakter dan hanya boleh berisi huruf kecil, angka, titik, garis bawah, atau tanda minus."
        )
    return username


def normalize_full_name(value: str) -> str:
    name = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(name) < 3:
        raise ValueError("Nama lengkap minimal 3 karakter.")
    if len(name) > 80:
        raise ValueError("Nama lengkap maksimal 80 karakter.")
    if any(ord(char) < 32 for char in name):
        raise ValueError("Nama mengandung karakter yang tidak valid.")
    return name


def password_verifier(password: str, username: str) -> str:
    """Buat verifier unik per username; password asli tidak dikirim atau disimpan."""
    if not AUTH_SIGNING_KEY:
        raise RuntimeError("AUTH_SIGNING_KEY diperlukan untuk fitur akun dinamis.")
    return hmac.new(
        str(AUTH_SIGNING_KEY).encode("utf-8"),
        f"{normalize_username(username)}\0{password}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def register_account(full_name: str, username: str, password: str, requested_role: str, position: str):
    if len(password) < 8:
        raise ValueError("Password minimal 8 karakter.")
    if requested_role not in PUBLIC_REGISTRATION_ROLES:
        raise ValueError("Pendaftaran publik hanya dapat meminta role Staff atau Admin.")
    clean_username = normalize_username(username)
    return api_post(
        {
            "action": "account_register",
            "actor": "Public Registration",
            "role": "Staff",
            "full_name": normalize_full_name(full_name),
            "username": clean_username,
            "password_verifier": password_verifier(password, clean_username),
            "requested_role": requested_role,
            "position": re.sub(r"\s+", " ", str(position or "")).strip()[:80],
        },
        timeout=30,
    )


def authenticate_account(username: str, password: str):
    try:
        clean_username = normalize_username(username)
    except ValueError:
        return {"authenticated": False, "status": "INVALID"}
    return api_post(
        {
            "action": "account_auth",
            "actor": "Login",
            "role": "Staff",
            "username": clean_username,
            "password_verifier": password_verifier(password, clean_username),
        },
        timeout=20,
    )


def list_accounts():
    from .auth import actor_payload

    return api_post({"action": "account_list", **actor_payload()}, timeout=30).get("accounts", [])


def approve_account(username: str, role: str):
    from .auth import actor_payload

    if role not in VALID_ROLES:
        raise ValueError("Role tidak valid.")
    return api_post(
        {
            "action": "account_approve",
            "username": normalize_username(username),
            "new_role": role,
            **actor_payload(),
        },
        timeout=30,
    )


def reject_account(username: str):
    from .auth import actor_payload

    return api_post(
        {"action": "account_reject", "username": normalize_username(username), **actor_payload()},
        timeout=30,
    )


def update_account(username: str, role: str, status: str):
    from .auth import actor_payload

    if role not in VALID_ROLES:
        raise ValueError("Role tidak valid.")
    if status not in {"ACTIVE", "SUSPENDED"}:
        raise ValueError("Status akun tidak valid.")
    return api_post(
        {
            "action": "account_update",
            "username": normalize_username(username),
            "new_role": role,
            "new_status": status,
            **actor_payload(),
        },
        timeout=30,
    )
