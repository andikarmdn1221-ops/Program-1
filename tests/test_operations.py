from datetime import date

import pytest

from wms import operations


def test_transaction_requires_stale_stock_guard():
    with pytest.raises(ValueError, match="Stok sebelumnya"):
        operations.do_transaction(
            "MASUK",
            "Primer",
            1,
            date(2026, 9, 8),
            "Supplier",
            expected_stock_before=None,
        )


def test_transaction_reuses_one_business_id_for_api_call(monkeypatch):
    captured = {}
    monkeypatch.setattr(operations, "make_tx_id", lambda: "TRX-STABLE")
    monkeypatch.setattr(operations, "actor_payload", lambda: {"actor": "staff"})
    monkeypatch.setattr(operations, "clear_and_refresh", lambda: None)
    monkeypatch.setattr(
        operations,
        "api_post",
        lambda payload: captured.update(payload) or {"ok": True},
    )

    operations.do_transaction(
        "KELUAR",
        "Primer",
        2,
        date(2026, 9, 8),
        "Proyek A",
        expected_stock_before=10,
    )

    assert captured["tx_id"] == "TRX-STABLE"
    assert captured["expected_stock_before"] == 10
