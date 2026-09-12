import asyncio
from unittest.mock import AsyncMock, MagicMock

from fastapi import HTTPException
from nexuflow_cloud.services import CloudServices


def test_created_account_survives_verification_mail_failure_without_false_success():
    gateway = CloudServices.__new__(CloudServices)
    gateway.auth = MagicMock()
    gateway.db = MagicMock()
    gateway._identity = AsyncMock(side_effect=[
        {'localId': 'test-user', 'idToken': 'test-token'},
        HTTPException(400, 'provider unavailable'),
    ])
    result = asyncio.run(gateway.register('Test User', 'test@example.com', 'test-password-only'))
    assert 'Conta criada' in result['message']
    assert 'não foi possível enviar' in result['message']
    profile = gateway.db.collection.return_value.document.return_value.set.call_args.args[0]
    assert profile['plan'] == 'free'
    assert 'admin' not in profile
    assert 'password' not in profile
    gateway.auth.update_user.assert_called_once_with('test-user', display_name='Test User')
