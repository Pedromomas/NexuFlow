import base64

import pytest

from nexuflow_cloud.config import Settings


@pytest.fixture
def account_environment(monkeypatch):
    for name, value in {
        "FIREBASE_PROJECT_ID": "test-project",
        "FIREBASE_WEB_API_KEY": "public-test-key",
        "PUBLIC_API_BASE": "https://api.example.com",
        "LICENSE_ED25519_PRIVATE_KEY": base64.b64encode(b"k" * 32).decode(),
        "CODE_HASH_PEPPER": base64.b64encode(b"p" * 32).decode(),
    }.items():
        monkeypatch.setenv(name, value)
    for name in ("PUBLIC_APP_RETURN_URL", "MERCADO_PAGO_ACCESS_TOKEN", "MERCADO_PAGO_WEBHOOK_SECRET", "NEXUFLOW_BILLING_ENABLED"):
        monkeypatch.delenv(name, raising=False)


def test_accounts_do_not_require_billing_configuration(account_environment):
    settings = Settings.from_env()
    assert settings.public_app_return_url == ""
    assert settings.mercado_pago_access_token == ""


def test_billing_requires_real_return_url(account_environment, monkeypatch):
    monkeypatch.setenv("NEXUFLOW_BILLING_ENABLED", "true")
    with pytest.raises(RuntimeError, match="PUBLIC_APP_RETURN_URL"):
        Settings.from_env()
