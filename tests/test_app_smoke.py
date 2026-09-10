import subprocess
import sys
from pathlib import Path


def test_login_shell_and_all_pages_render_with_production_configuration():
    project_root = Path(__file__).resolve().parents[1]
    script = """
from streamlit.testing.v1 import AppTest
import time
import requests

secrets = {
    "URL_GSHEET_API": "https://script.google.com/macros/s/real-deployment/exec",
    "API_SHARED_KEY": "a" * 32,
    "AUTH_SIGNING_KEY": "b" * 32,
    "PRODUCTION_MODE": True,
    "REQUIRE_HMAC": True,
    "ALLOW_NO_LOGIN": False,
    "ALLOW_LEGACY_PASSWORDS": False,
    "WRITE_BLOCK_WHEN_OFFLINE": True,
    "REQUIRE_SERVER_BACKUP_BEFORE_RESET": True,
    "TELEGRAM_BOT_TOKEN": "123456:abcdefghijklmnopqrstuvwxyz",
    "TELEGRAM_CHAT_ID": "-1001234567890",
    "ACCOUNT_TELEGRAM_BOT_TOKEN": "654321:abcdefghijklmnopqrstuvwxyz",
    "ACCOUNT_TELEGRAM_CHAT_ID": "-1001234567890",
    "USERS": {
        "developer": {
            "display_name": "Developer",
            "role": "Developer",
            "password_hash": "pbkdf2_sha256$310000$" + "a" * 32 + "$" + "b" * 64,
        }
    },
}
at = AppTest.from_file("app.py", default_timeout=10)
at.secrets.update(secrets)
at.run()
assert not list(at.exception), list(at.exception)
assert [tab.label for tab in at.tabs] == ["Masuk", "Daftar Akun Baru"]
assert "Username" in [field.label for field in at.text_input]
assert not list(at.error), [error.value for error in at.error]

capabilities = {
    "hmac_required": True,
    "account_auth_rate_limit": True,
    "idempotent_mutations": True,
    "formula_guard": True,
    "mutation_rollback": True,
    "backup_before_reset": True,
    "drive_folder_configured": True,
    "local_roles_enforced": True,
    "account_approval_configured": True,
}

class FakeResponse:
    ok = True
    status_code = 200

    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        action = self.payload.get("action")
        base = {
            "ok": True,
            "backend_version": "7.6-production",
            "data_revision": "1",
            "server_time": "08-09-2026 12:00:00",
            "capabilities": capabilities,
        }
        if action == "health":
            return base
        return {
            **base,
            "stok": [
                ["Nama Barang", "Jumlah Stok", "Status", "Batas Minimum"],
                ["Primer", 10, "Aktif", 5],
            ],
            "riwayat": [[
                "ID Transaksi", "Waktu", "Tanggal", "Tipe", "Barang",
                "Jumlah", "Pembeli / Keterangan", "Bukti URL", "Status", "Referensi"
            ]],
            "audit": [["Waktu", "User", "Role", "Aksi", "ID Transaksi", "Detail"]],
            "row_counts": {"stok": 1, "riwayat": 0, "audit": 0},
            "account_security": {"pbkdf2": 0, "legacy": 0, "active_legacy": 0},
        }

def fake_request(_method, _url, **kwargs):
    return FakeResponse(kwargs.get("json", {}))

requests.request = fake_request
dashboard = AppTest.from_file("app.py", default_timeout=10)
dashboard.secrets.update(secrets)
now = time.time()
dashboard.session_state["auth_user"] = "developer"
dashboard.session_state["auth_display_name"] = "Developer"
dashboard.session_state["auth_role"] = "Developer"
dashboard.session_state["auth_source"] = "local"
dashboard.session_state["auth_login_at"] = now
dashboard.session_state["auth_last_activity"] = now
dashboard.session_state["auth_last_validation"] = now
dashboard.session_state["_mirai_startup_complete"] = True
dashboard.run()
assert not list(dashboard.exception), list(dashboard.exception)
assert any("Database terhubung" in item.value for item in dashboard.success)
assert len(dashboard.dataframe) >= 1
for page in [
    "📋 Lihat Semua Stok",
    "➕ Kelola Master Item",
    "👥 Kelola Akun",
    "📥 Barang Masuk",
    "📤 Barang Keluar",
    "🧮 Penyesuaian Stok",
    "✏️ Koreksi Transaksi",
    "📊 Riwayat Transaksi",
    "📈 Laporan Periodik",
    "📜 Audit Log",
    "💾 Backup Data",
    "🔔 Status Notifikasi",
    "⚙️ Pengaturan & Reset",
    "ℹ️ Tentang Aplikasi",
]:
    dashboard.sidebar.radio[0].set_value(page).run()
    assert not list(dashboard.exception), (page, list(dashboard.exception))
print("Streamlit login and all-page smoke passed.")
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=project_root,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Streamlit login and all-page smoke passed." in result.stdout
