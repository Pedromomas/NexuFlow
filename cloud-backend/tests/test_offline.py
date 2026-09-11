"""Local security checks: no cloud credentials, network or payments required."""
import base64
import hashlib
import hmac
import json
import unittest
from unittest.mock import patch

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from nexuflow_cloud.config import Settings
from nexuflow_cloud.security import sign_license, verify_mp_webhook


class OfflineSecurityTests(unittest.TestCase):
    def test_malformed_webhooks_are_rejected(self):
        for header in ('', 'ts=no,v1=abc', 'ts=1700000000', 'v1=' + 'a' * 64):
            with self.subTest(header=header):
                self.assertFalse(verify_mp_webhook(
                    header=header, request_id='request', data_id='123',
                    secret='test-only', now=1700000000))

    def test_webhook_tampering_and_stale_timestamp_are_rejected(self):
        now = 1700000000
        manifest = f'id:123;request-id:request;ts:{now};'
        digest = hmac.new(b'test-only', manifest.encode(), hashlib.sha256).hexdigest()
        values = dict(header=f'ts={now},v1={digest}', request_id='request',
                      data_id='123', secret='test-only', now=now)
        self.assertTrue(verify_mp_webhook(**values))
        for changes in ({'data_id': '999'}, {'request_id': 'other'},
                        {'secret': 'wrong'}, {'now': now + 301}, {'now': now - 301}):
            with self.subTest(changes=changes):
                self.assertFalse(verify_mp_webhook(**(values | changes)))

    def test_license_signature_rejects_changed_expiration(self):
        key = Ed25519PrivateKey.generate()
        payload = {'expiresAt': '2026-09-12T00:00:00Z', 'plan': 'week'}
        document = sign_license(payload, key.private_bytes_raw())
        signature = base64.b64decode(document['signature'])
        def canonical(value):
            return json.dumps(value, ensure_ascii=False, sort_keys=True,
                              separators=(',', ':')).encode()
        key.public_key().verify(signature, canonical(payload))
        with self.assertRaises(InvalidSignature):
            key.public_key().verify(signature, canonical(
                payload | {'expiresAt': '2099-09-12T00:00:00Z'}))

    def test_backend_settings_require_explicit_configuration(self):
        with patch.dict('os.environ', {}, clear=True):
            with self.assertRaises(RuntimeError):
                Settings.from_env()


if __name__ == '__main__':
    unittest.main()
