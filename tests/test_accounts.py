from types import SimpleNamespace

import pytest

from wms import accounts, auth


class AttrDict(dict):
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError as exc:
            raise AttributeError(key) from exc

    def __setattr__(self, key, value):
        self[key] = value


def test_delete_account_requires_exact_username():
    with pytest.raises(ValueError, match="Konfirmasi"):
        accounts.delete_account("andika_01", "akun-lain")


def test_delete_account_sends_permanent_delete_contract(monkeypatch):
    captured = {}

    def fake_post(payload, timeout):
        captured.update(payload)
        captured["timeout"] = timeout
        return {"deleted": True}

    monkeypatch.setattr(accounts, "api_post", fake_post)
    monkeypatch.setattr(
        auth,
        "actor_payload",
        lambda: {
            "actor": "developer",
            "role": "Developer",
            "auth_source": "local",
        },
    )

    result = accounts.delete_account("Andika_01", "andika_01")

    assert result["deleted"] is True
    assert captured["action"] == "account_delete"
    assert captured["username"] == "andika_01"
    assert captured["confirm"] == "DELETE:andika_01"
    assert captured["timeout"] == 30


def test_dynamic_session_revalidation_refreshes_role(monkeypatch):
    state = AttrDict(
        auth_user="staff_01",
        auth_display_name="Nama Lama",
        auth_role="Staff",
        auth_source="dynamic",
        auth_last_validation=0,
    )
    fake_streamlit = SimpleNamespace(
        session_state=state,
        error=lambda _message: None,
    )
    monkeypatch.setattr(auth, "st", fake_streamlit)
    monkeypatch.setattr(auth, "SESSION_REVALIDATE_SECONDS", 30)
    monkeypatch.setattr(
        accounts,
        "validate_account_session",
        lambda _username: {
            "active": True,
            "status": "ACTIVE",
            "role": "Admin",
            "full_name": "Andika",
        },
    )

    assert auth._revalidate_active_session({}, now=100) is True
    assert state.auth_role == "Admin"
    assert state.auth_display_name == "Andika"
    assert state.auth_last_validation == 100


def test_suspended_dynamic_account_loses_session(monkeypatch):
    state = AttrDict(
        auth_user="staff_01",
        auth_display_name="Staff",
        auth_role="Staff",
        auth_source="dynamic",
        auth_last_validation=0,
    )
    errors = []
    fake_streamlit = SimpleNamespace(
        session_state=state,
        error=errors.append,
    )
    monkeypatch.setattr(auth, "st", fake_streamlit)
    monkeypatch.setattr(auth, "SESSION_REVALIDATE_SECONDS", 30)
    monkeypatch.setattr(
        accounts,
        "validate_account_session",
        lambda _username: {
            "active": False,
            "status": "SUSPENDED",
        },
    )

    assert auth._revalidate_active_session({}, now=100) is False
    assert "auth_user" not in state
    assert errors
