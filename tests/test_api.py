from types import SimpleNamespace

import requests

from wms import api


def test_api_get_uses_bounded_read_budget(monkeypatch):
    captured = {}

    def fake_post(payload, timeout, retry_attempts):
        captured["payload"] = payload
        captured["timeout"] = timeout
        captured["retry_attempts"] = retry_attempts
        return {"ok": True}

    monkeypatch.setattr(api, "AUTH_SIGNING_KEY", "test-signing-key")
    monkeypatch.setattr(api, "_post_json", fake_post)

    assert api.api_get() == {"ok": True}
    assert captured["payload"]["action"] == "read"
    assert captured["timeout"] == api.DATABASE_READ_TIMEOUT_SECONDS
    assert captured["retry_attempts"] <= 2


def test_signed_retry_generates_fresh_signature(monkeypatch):
    nonces = []

    def fake_signature(payload):
        nonce = f"nonce-{len(nonces) + 1}"
        nonces.append(nonce)
        return {**payload, "auth_nonce": nonce}

    # Gunakan nama terpisah agar parameter `attempts` tidak menimpa list uji.
    attempt_counts = []

    def fake_request_once(method, url, *, attempts: int, **kwargs):
        del method, url, kwargs
        attempt_counts.append(attempts)
        if len(attempt_counts) == 1:
            raise requests.Timeout("simulasi timeout")
        return SimpleNamespace(json=lambda: {"ok": True})

    monkeypatch.setattr(api, "URL_GSHEET_API", "https://example.test/exec")
    monkeypatch.setattr(api, "API_SHARED_KEY", "test-api-key")
    monkeypatch.setattr(api, "AUTH_SIGNING_KEY", "test-signing-key")
    monkeypatch.setattr(api, "REQUIRE_HMAC", True)
    monkeypatch.setattr(api, "make_request_signature", fake_signature)
    monkeypatch.setattr(api, "_request_with_retry", fake_request_once)
    monkeypatch.setattr(api.time, "sleep", lambda _seconds: None)

    assert api._post_json({"action": "read"}, timeout=1, retry_attempts=2) == {
        "ok": True
    }
    assert nonces == ["nonce-1", "nonce-2"]
    assert attempt_counts == [1, 1]
