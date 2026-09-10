from wms import notifications


class SuccessfulResponse:
    ok = True
    status_code = 200


def test_account_request_keyboard_only_offers_staff_admin_and_reject(monkeypatch):
    captured = {}

    def fake_send(message, **kwargs):
        captured["message"] = message
        captured.update(kwargs)
        return True, "terkirim"

    monkeypatch.setattr(notifications, "ACCOUNT_TELEGRAM_BOT_TOKEN", "token-test")
    monkeypatch.setattr(notifications, "ACCOUNT_TELEGRAM_CHAT_ID", "chat-test")
    monkeypatch.setattr(notifications, "send_telegram_detailed", fake_send)
    monkeypatch.setattr(notifications, "record_notification", lambda *_args: None)

    ok, detail = notifications.send_account_request_notification(
        full_name="Nidha Amiroh",
        username="nidha",
        position="admin",
        requested_role="Admin",
        request_id="REQ-001",
    )

    callbacks = [
        button["callback_data"]
        for row in captured["reply_markup"]["inline_keyboard"]
        for button in row
    ]
    assert ok is True
    assert detail == "terkirim"
    assert callbacks == [
        "acc|REQ-001|Staff",
        "acc|REQ-001|Admin",
        "acc|REQ-001|REJECT",
    ]
    assert not any("|Boss" in callback or "|Developer" in callback for callback in callbacks)


def test_operational_notification_has_one_short_attempt(monkeypatch):
    captured = {}

    def fake_send(message, image_bytes=None, **kwargs):
        captured.update(
            {"message": message, "image_bytes": image_bytes, **kwargs}
        )
        return False, "timeout"

    monkeypatch.setattr(notifications, "send_telegram_detailed", fake_send)
    monkeypatch.setattr(notifications, "record_notification", lambda *_args: None)
    monkeypatch.setattr(notifications, "TELEGRAM_OPERATION_TIMEOUT_SECONDS", 8)

    assert notifications.deliver_notification("stok berubah", "Transaksi") == (
        False,
        "timeout",
    )
    assert captured["attempts"] == 1
    assert captured["timeout_seconds"] == 8


def test_telegram_uses_one_plain_text_request_for_user_content(monkeypatch):
    calls = []

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        return SuccessfulResponse()

    monkeypatch.setattr(notifications, "TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setattr(notifications, "TELEGRAM_CHAT_ID", "chat")
    monkeypatch.setattr(notifications.requests, "post", fake_post)

    ok, _detail = notifications.send_telegram_detailed(
        "*BARANG KELUAR* oleh staff_01", attempts=1, timeout_seconds=8
    )

    assert ok is True
    assert len(calls) == 1
    payload = calls[0][1]["json"]
    assert payload["text"] == "BARANG KELUAR oleh staff_01"
    assert "parse_mode" not in payload
