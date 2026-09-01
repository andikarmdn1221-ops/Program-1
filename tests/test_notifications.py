from wms import notifications


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
