from types import SimpleNamespace
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from nexuflow_cloud import main
from nexuflow_cloud.services import CloudServices


def test_unverified_account_cannot_receive_license(monkeypatch):
    monkeypatch.setenv('NEXUFLOW_API_ENABLED', 'true')
    gateway = MagicMock()
    gateway.verify_token.return_value = {'uid': 'unverified', 'email_verified': False}
    gateway.require_verified.side_effect = CloudServices.require_verified.__get__(gateway)
    monkeypatch.setattr(main, 'services', lambda: gateway)
    response = TestClient(main.app).post('/v1/license',
        headers={'Authorization': 'Bearer test-token'},
        json={'installationToken': 'a' * 32})
    assert response.status_code == 403
    gateway.profile.assert_not_called()
    gateway.db.collection.assert_not_called()


def test_unverified_profile_neither_accepts_nor_inherits_duo():
    gateway = CloudServices.__new__(CloudServices)
    gateway.auth = MagicMock()
    gateway.auth.get_user.return_value = SimpleNamespace(email='test@example.com',
        email_verified=False, display_name='Test', custom_claims={})
    gateway.db = MagicMock()
    gateway.db.collection.return_value.document.return_value.get.return_value.to_dict.return_value = {
        'plan': 'free', 'subscriptionStatus': 'free', 'duoOwnerUid': 'owner'}
    gateway._accept_duo_if_available = MagicMock()
    result = gateway.profile('member')
    assert result['subscriptionStatus'] == 'free'
    gateway._accept_duo_if_available.assert_not_called()
    gateway.db.collection.return_value.document.assert_called_once_with('member')
