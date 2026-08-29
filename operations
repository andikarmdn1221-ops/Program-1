"""Pengiriman dan pencatatan status notifikasi Telegram."""

import time

import requests
import streamlit as st

from .config import (
    NOTIFICATION_LOG_LIMIT,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    TELEGRAM_RETRY_ATTEMPTS,
)
from .utils import redact_sensitive, waktu_display

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
