from wms import config, data


SECURE_CAPABILITIES = {
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


def test_boolean_secret_parser_does_not_treat_false_string_as_true(monkeypatch):
    monkeypatch.setattr(config, "_SECRETS", {"FLAG": "false"})
    assert config._secret_bool("FLAG", True) is False
    monkeypatch.setattr(config, "_SECRETS", {"FLAG": "true"})
    assert config._secret_bool("FLAG", False) is True


def test_backend_contract_requires_exact_version_and_capabilities():
    assert data.backend_contract_issues(
        {
            "backend_version": data.EXPECTED_BACKEND_VERSION,
            "capabilities": SECURE_CAPABILITIES,
        }
    ) == []
    assert data.backend_contract_issues(
        {"backend_version": "old", "capabilities": SECURE_CAPABILITIES}
    )

    insecure = dict(SECURE_CAPABILITIES, idempotent_mutations=False)
    assert "idempotensi transaksi" in data.backend_contract_issues(
        {
            "backend_version": data.EXPECTED_BACKEND_VERSION,
            "capabilities": insecure,
        }
    )


def test_runtime_security_rejects_unsafe_production_flags(monkeypatch):
    from wms import auth

    monkeypatch.setattr(data, "PRODUCTION_MODE", True)
    monkeypatch.setattr(
        data,
        "URL_GSHEET_API",
        "https://script.google.com/macros/s/deployment-value/exec",
    )
    monkeypatch.setattr(data, "API_SHARED_KEY", "a" * 32)
    monkeypatch.setattr(data, "AUTH_SIGNING_KEY", "b" * 32)
    monkeypatch.setattr(data, "REQUIRE_HMAC", True)
    monkeypatch.setattr(data, "ALLOW_NO_LOGIN", False)
    monkeypatch.setattr(data, "ALLOW_LEGACY_PASSWORDS", False)
    monkeypatch.setattr(data, "WRITE_BLOCK_WHEN_OFFLINE", True)
    monkeypatch.setattr(data, "REQUIRE_SERVER_BACKUP_BEFORE_RESET", True)
    monkeypatch.setattr(data, "TELEGRAM_BOT_TOKEN", "123456:abcdefghijklmnopqrstuvwxyz")
    monkeypatch.setattr(data, "TELEGRAM_CHAT_ID", "-1001234567890")
    monkeypatch.setattr(
        data,
        "ACCOUNT_TELEGRAM_BOT_TOKEN",
        "654321:abcdefghijklmnopqrstuvwxyz",
    )
    monkeypatch.setattr(data, "ACCOUNT_TELEGRAM_CHAT_ID", "-1001234567890")
    monkeypatch.setattr(
        auth,
        "get_users_config",
        lambda: {"developer": {"role": "Developer"}},
    )
    monkeypatch.setattr(
        auth, "account_security_report", lambda: [("developer", "PBKDF2")]
    )
    assert data.runtime_security_issues() == []

    monkeypatch.setattr(data, "ALLOW_NO_LOGIN", True)
    monkeypatch.setattr(data, "AUTH_SIGNING_KEY", "a" * 32)
    issues = data.runtime_security_issues()
    assert "ALLOW_NO_LOGIN wajib false" in issues
    assert "API_SHARED_KEY dan AUTH_SIGNING_KEY harus berbeda" in issues
