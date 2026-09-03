"""Client aman untuk Google Apps Script backend."""

import time

import requests
import streamlit as st

from .auth import actor_payload
from .config import (
    API_SHARED_KEY,
    AUTH_SIGNING_KEY,
    DATABASE_READ_TIMEOUT_SECONDS,
    DATABASE_RETRY_ATTEMPTS,
    DATABASE_RETRY_BACKOFF_SECONDS,
    HEALTH_TIMEOUT_SECONDS,
    REQUIRE_HMAC,
    URL_GSHEET_API,
)
from .utils import api_error_detail, make_request_signature, redact_sensitive


def _request_with_retry(method: str, url: str, *, attempts=1, **kwargs):
    """Ulangi gangguan jaringan sementara; mutation tetap memakai satu percobaan."""
    attempts = max(1, int(attempts))
    last_error = None
    for attempt in range(attempts):
        try:
            response = requests.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except (requests.Timeout, requests.ConnectionError, requests.HTTPError) as exc:
            last_error = exc
            if attempt + 1 >= attempts:
                raise
            time.sleep(DATABASE_RETRY_BACKOFF_SECONDS * (2**attempt))
    raise last_error or RuntimeError("Permintaan database gagal.")


def _post_json(payload: dict, timeout=60, retry_attempts=1):
    """POST JSON bertanda tangan. API key berada di body, bukan query URL."""
    if not URL_GSHEET_API:
        raise RuntimeError("URL_GSHEET_API belum diatur di Streamlit Secrets.")
    if not API_SHARED_KEY:
        raise RuntimeError("API_SHARED_KEY belum diatur di Streamlit Secrets.")
    if REQUIRE_HMAC and not AUTH_SIGNING_KEY:
        raise RuntimeError("AUTH_SIGNING_KEY wajib diisi karena REQUIRE_HMAC=true.")

    # Setiap retry wajib memakai nonce/signature baru. Mengirim ulang signature
    # lama akan ditolak backend sebagai replay request.
    retry_attempts = max(1, int(retry_attempts))
    for attempt in range(retry_attempts):
        signed_payload = make_request_signature(payload)
        signed_payload = {**signed_payload, "api_key": API_SHARED_KEY}
        try:
            response = _request_with_retry(
                "post",
                URL_GSHEET_API,
                attempts=1,
                json=signed_payload,
                timeout=timeout,
            )
            break
        except (requests.Timeout, requests.ConnectionError, requests.HTTPError):
            if attempt + 1 >= retry_attempts:
                raise
            time.sleep(DATABASE_RETRY_BACKOFF_SECONDS * (2**attempt))
    try:
        data = response.json()
    except ValueError as exc:
        raise RuntimeError("Respons server bukan JSON yang valid.") from exc
    if not isinstance(data, dict):
        raise RuntimeError("Respons server tidak valid.")
    if data.get("ok") is False:
        raise RuntimeError(
            redact_sensitive(data.get("message", "Operasi ditolak server."))
        )
    return data


def api_get(timeout=DATABASE_READ_TIMEOUT_SECONDS):
    """Baca database lewat signed POST. GET legacy hanya jika REQUIRE_HMAC dimatikan sengaja."""
    if AUTH_SIGNING_KEY:
        return _post_json(
            {"action": "read", **actor_payload()},
            timeout=timeout,
            retry_attempts=DATABASE_RETRY_ATTEMPTS,
        )
    if REQUIRE_HMAC:
        raise RuntimeError("Mode aman aktif tetapi AUTH_SIGNING_KEY belum tersedia.")

    if not URL_GSHEET_API:
        raise RuntimeError("URL_GSHEET_API belum diatur di Streamlit Secrets.")
    if not API_SHARED_KEY:
        raise RuntimeError("API_SHARED_KEY belum diatur di Streamlit Secrets.")
    response = _request_with_retry(
        "get",
        URL_GSHEET_API,
        attempts=DATABASE_RETRY_ATTEMPTS,
        params={"key": API_SHARED_KEY},
        timeout=timeout,
    )
    try:
        data = response.json()
    except ValueError as exc:
        raise RuntimeError("Respons server bukan JSON yang valid.") from exc
    if isinstance(data, dict) and data.get("ok") is False:
        raise RuntimeError(
            redact_sensitive(data.get("message", "Server menolak permintaan."))
        )
    return data


def api_health(timeout=HEALTH_TIMEOUT_SECONDS):
    """Health check ringan untuk auto-sync berdasarkan revision backend."""
    if AUTH_SIGNING_KEY:
        return _post_json(
            {"action": "health", **actor_payload()},
            timeout=timeout,
            retry_attempts=DATABASE_RETRY_ATTEMPTS,
        )
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
