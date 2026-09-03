import pytest

from wms import accounts
from wms.data import (
    normalize_audit_rows,
    normalize_history_rows,
    normalize_stock_rows,
)
from wms.utils import (
    clean_item_name,
    clean_note,
    safe_int,
    spreadsheet_safe_value,
    status_stok,
)


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


@pytest.mark.parametrize("password", ["pendek", "x" * 129])
def test_password_length_is_bounded(password):
    with pytest.raises(ValueError):
        accounts.validate_password(password)


def test_position_is_normalized_and_validated():
    assert accounts.normalize_position("  Warehouse   Staff ") == "Warehouse Staff"
    with pytest.raises(ValueError):
        accounts.normalize_position(" ")


def test_common_input_validation():
    assert clean_item_name("  Top   Coat A ") == "Top Coat A"
    assert clean_note(" catatan\x00aman ") == "catatanaman"
    assert safe_int("12.0") == 12
    assert status_stok(0, 5) == "HABIS"
    assert status_stok(4, 5) == "KRITIS"
    assert status_stok(6, 5) == "AMAN"


def test_stock_normalization_enforces_inventory_invariants():
    rows = [
        ["Nama Barang", "Jumlah Stok", "Status", "Batas Minimum"],
        ["Top Coat A", "12.0", "AKTIF", "5"],
    ]
    stock, master = normalize_stock_rows(rows)
    assert stock == {"Top Coat A": 12}
    assert master["Top Coat A"] == {"status": "Aktif", "min_stok": 5}


@pytest.mark.parametrize(
    "rows, message",
    [
        (
            [["Top Coat A", 1, "Aktif", 5], ["top coat a", 2, "Aktif", 5]],
            "duplikat",
        ),
        ([["Top Coat A", -1, "Aktif", 5]], "negatif"),
        ([["Top Coat A", 1, "Aktif", 0]], "minimal 1"),
    ],
)
def test_invalid_stock_data_is_rejected(rows, message):
    with pytest.raises(RuntimeError, match=message):
        normalize_stock_rows(rows)


def test_headerless_legacy_rows_do_not_lose_first_record():
    history = normalize_history_rows(
        [["01-09-2026 08:00", "MASUK", "Primer", 2, "Supplier"]]
    )
    audit = normalize_audit_rows(
        [["01-09-2026 08:01", "TRANSACTION", "TRX-1", "Primer +2"]]
    )
    assert len(history) == 1
    assert history[0]["Barang"] == "Primer"
    assert len(audit) == 1
    assert audit[0]["Aksi"] == "TRANSACTION"


@pytest.mark.parametrize("prefix", ["=", "+", "-", "@"])
def test_spreadsheet_formula_prefix_is_neutralized(prefix):
    value = prefix + "SUM(A1:A2)"
    assert spreadsheet_safe_value(value) == "'" + value
