import pytest

from wms import accounts
from wms.utils import clean_item_name, clean_note, safe_int, status_stok


def test_username_normalization():
    assert accounts.normalize_username("  Andika_01 ") == "andika_01"


@pytest.mark.parametrize("value", ["abc", "nama pakai spasi", "user@contoh", "a" * 33])
def test_invalid_username_is_rejected(value):
    with pytest.raises(ValueError):
        accounts.normalize_username(value)


def test_password_verifier_is_deterministic_and_never_plaintext(monkeypatch):
    monkeypatch.setattr(accounts, "AUTH_SIGNING_KEY", "unit-test-signing-key")
    verifier = accounts.password_verifier("rahasia-ku", "andika_01")
    assert verifier == accounts.password_verifier("rahasia-ku", "andika_01")
    assert "rahasia-ku" not in verifier
    assert len(verifier) == 64


def test_common_input_validation():
    assert clean_item_name("  Top   Coat A ") == "Top Coat A"
    assert clean_note(" catatan\x00aman ") == "catatanaman"
    assert safe_int("12.0") == 12
    assert status_stok(0, 5) == "HABIS"
    assert status_stok(4, 5) == "KRITIS"
    assert status_stok(6, 5) == "AMAN"

