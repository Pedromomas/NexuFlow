import unittest
from datetime import UTC, datetime, timedelta
from nexuflow_cloud.admin import require_admin_claims, make_code_document


class AdminTests(unittest.TestCase):
    def test_role_cannot_be_a_string_or_unverified(self):
        for claims in ({}, {'admin': 'true'}, {'admin': True, 'email_verified': False},
                       {'admin': True, 'email_verified': True, 'auth_time': 1},
                       {'admin': True, 'email_verified': True, 'auth_time': 2000}):
            with self.subTest(claims=claims), self.assertRaises(PermissionError):
                require_admin_claims(claims, 1000)
        require_admin_claims({'admin': True, 'email_verified': True, 'auth_time': 999}, 1000)

    def test_individual_codes_and_separate_redemption_deadline(self):
        now = datetime(2026, 9, 5, tzinfo=UTC)
        kwargs = dict(theme='kiwi', days=7, lifetime=False,
                      redeem_before=now + timedelta(days=2), now=now, admin_uid='admin')
        code, data = make_code_document(**kwargs)
        other, _ = make_code_document(**kwargs)
        self.assertNotEqual(code, other)
        self.assertEqual(len(code), 37)
        self.assertEqual(data['durationDays'], 7)
        self.assertEqual(data['rewards'], ['theme:kiwi'])
        self.assertTrue(data['singleUse'])
        self.assertNotIn('code', data)

    def test_conflicting_lifetime_and_timed_access_rejected(self):
        with self.assertRaises(ValueError):
            make_code_document(theme=None, days=7, lifetime=True, redeem_before=None,
                               now=datetime.now(UTC), admin_uid='admin')
