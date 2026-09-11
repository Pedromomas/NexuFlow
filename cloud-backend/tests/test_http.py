import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from nexuflow_cloud import main


@pytest.fixture
def api(monkeypatch):
    monkeypatch.setenv('NEXUFLOW_API_ENABLED', 'true')
    gateway = MagicMock()
    gateway.verify_token.return_value = {'uid': 'admin-1', 'admin': True,
        'email_verified': True, 'auth_time': int(time.time())}
    gateway.auth.get_user.return_value = SimpleNamespace(disabled=False,
        email_verified=True, custom_claims={'admin': True})
    gateway.register = AsyncMock(return_value={'message': 'Confira seu e-mail.'})
    gateway.login = AsyncMock(return_value={'accessToken': 'fake-token', 'profile': {'id': 'test-user'}})
    gateway.reset_password = AsyncMock(return_value={'message': 'Solicitação recebida.'})
    monkeypatch.setattr(main, 'services', lambda: gateway)
    monkeypatch.setattr(main, 'settings', lambda: SimpleNamespace(
        code_hash_pepper=b'p' * 32, mercado_pago_webhook_secret='local-test'))
    return TestClient(main.app), gateway


def test_initial_deployment_is_closed_without_credentials(monkeypatch):
    monkeypatch.delenv('NEXUFLOW_API_ENABLED', raising=False)
    gateway = MagicMock()
    monkeypatch.setattr(main, 'services', gateway)
    client = TestClient(main.app)
    assert client.get('/health').status_code == 200
    for path in ['/v1/auth/login', '/v1/admin/codes', '/v1/license']:
        assert client.post(path, json={}).status_code == 503
    assert client.get('/openapi.json').status_code == 404
    gateway.assert_not_called()


@pytest.mark.parametrize('method,path,body', [
    ('get', '/v1/admin/users?email=test@example.com', None),
    ('post', '/v1/admin/codes', {'days': 7}),
])
def test_admin_rejects_anonymous_and_ordinary_accounts(api, method, path, body):
    client, gateway = api
    args = {'json': body} if body else {}
    assert getattr(client, method)(path, **args).status_code == 401
    gateway.verify_token.return_value = {'uid': 'ordinary', 'email_verified': True, 'auth_time': int(time.time())}
    assert getattr(client, method)(path, headers={'Authorization': 'Bearer token'}, **args).status_code == 403
    gateway.db.collection.assert_not_called()


def test_removed_admin_role_blocks_still_valid_token(api):
    client, gateway = api
    gateway.auth.get_user.return_value.custom_claims = {}
    assert client.post('/v1/admin/codes', json={'days': 7}, headers={'Authorization': 'Bearer token'}).status_code == 403
    gateway.db.collection.assert_not_called()


def test_create_seven_day_code_stores_no_plaintext(api):
    client, gateway = api
    response = client.post('/v1/admin/codes', json={'days': 7, 'theme': 'kiwi'}, headers={'Authorization': 'Bearer token'})
    assert response.status_code == 201
    result = response.json()
    assert result['code'].startswith('NEXU-')
    document = gateway.db.collection.return_value.document.return_value.create.call_args.args[0]
    assert document['durationDays'] == 7
    assert document['rewards'] == ['theme:kiwi']
    assert result['code'] not in repr(document)
    assert len(result['id']) == 64


def test_bad_duration_is_rejected_before_creating_document(api):
    client, gateway = api
    response = client.post('/v1/admin/codes', json={'days': -7}, headers={'Authorization': 'Bearer token'})
    assert response.status_code == 422
    gateway.db.collection.assert_not_called()


def test_register_login_reset_use_service_and_rate_limit(api):
    client, gateway = api
    assert client.post('/v1/auth/register', json={'displayName': 'Local', 'email': 'test@example.com', 'password': 'test-only-password'}).status_code == 201
    assert client.post('/v1/auth/login', json={'email': 'test@example.com', 'password': 'test-only-password'}).status_code == 200
    assert client.post('/v1/auth/password-reset', json={'email': 'test@example.com'}).status_code == 200
    assert gateway.rate_limit.call_count == 3
    gateway.register.assert_awaited_once()
    gateway.login.assert_awaited_once()
    gateway.reset_password.assert_awaited_once()


def test_rate_limit_prevents_login(api):
    client, gateway = api
    gateway.rate_limit.side_effect = HTTPException(status_code=429, detail='Aguarde.')
    assert client.post('/v1/auth/login', json={'email': 'test@example.com', 'password': 'test-only-password'}).status_code == 429
    gateway.login.assert_not_awaited()


def test_malformed_webhook_is_401_not_500(api):
    import os
    from unittest.mock import patch
    client, gateway = api
    with patch.dict(os.environ, {'NEXUFLOW_BILLING_ENABLED': 'true'}):
        response = client.post('/v1/webhooks/mercado-pago?data.id=123',
            headers={'x-signature': 'ts=bad,v1=bad', 'x-request-id': 'local'})
    assert response.status_code == 401
    gateway.payment.assert_not_called()


def test_accounts_can_run_while_billing_is_closed(api, monkeypatch):
    monkeypatch.delenv('NEXUFLOW_BILLING_ENABLED', raising=False)
    client, gateway = api
    assert client.post('/v1/auth/login', json={'email': 'test@example.com', 'password': 'test-only-password'}).status_code == 200
    for path in ['/v1/billing/checkout', '/v1/webhooks/mercado-pago?data.id=123']:
        assert client.post(path, json={}).status_code == 503
    gateway.create_checkout.assert_not_called()
    gateway.payment.assert_not_called()


def test_sandbox_closed_by_default(api):
    client, gateway = api
    assert client.post('/v1/admin/pagbank/checkout', json={'plan': 'week'}).status_code == 503
    assert client.post('/v1/webhooks/pagbank', json={}).status_code == 503


def test_sandbox_requires_admin_and_signed_notifications(api, monkeypatch):
    monkeypatch.setenv('NEXUFLOW_PAGBANK_SANDBOX_ENABLED', 'true')
    client, gateway = api
    assert client.post('/v1/admin/pagbank/checkout', json={'plan': 'week'}).status_code == 401
    assert client.post('/v1/webhooks/pagbank', json={'id': 'ORDE_test'}).status_code == 401
    gateway.db.collection.assert_not_called()


def test_signed_sandbox_notification_reconciles(api, monkeypatch):
    import hashlib
    monkeypatch.setenv('NEXUFLOW_PAGBANK_SANDBOX_ENABLED', 'true')
    monkeypatch.setenv('PAGBANK_ACCESS_TOKEN', 'test-token')
    sandbox = MagicMock()
    sandbox.reconcile = AsyncMock()
    monkeypatch.setattr(main, 'pagbank_sandbox', lambda: sandbox)
    client, _ = api
    body = b'{"id":"ORDE_test"}'
    signature = hashlib.sha256(b'test-token-' + body).hexdigest()
    assert client.post('/v1/webhooks/pagbank', content=body,
        headers={'x-authenticity-token': signature}).status_code == 200
    sandbox.reconcile.assert_awaited_once_with('ORDE_test')


def test_return_does_not_activate_a_subscription(api):
    client, gateway = api
    assert client.get('/billing/return?status=approved').status_code == 200
    gateway.db.collection.assert_not_called()
