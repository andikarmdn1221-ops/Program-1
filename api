"""Client aman untuk Google Apps Script backend."""

import requests
import streamlit as st

from .auth import actor_payload
from .config import (
    API_SHARED_KEY,
    AUTH_SIGNING_KEY,
    HEALTH_TIMEOUT_SECONDS,
    REQUIRE_HMAC,
    URL_GSHEET_API,
)
from .utils import api_error_detail, make_request_signature, redact_sensitive

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
