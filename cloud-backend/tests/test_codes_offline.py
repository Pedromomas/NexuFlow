import unittest
from datetime import UTC, datetime, timedelta
from nexuflow_cloud.codes import redemption_updates


class CodeTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 9, 5, tzinfo=UTC)
        self.code = {'durationDays': 7, 'rewards': []}

    def test_seven_days_start_at_server_redemption(self):
        update, consumed, rewards = redemption_updates(self.code, {}, 'user', self.now)
        self.assertEqual(update['codeAccessEndsAt'], self.now + timedelta(days=7))
        self.assertEqual(consumed['usedAt'], self.now)
        self.assertEqual(rewards, [])
        self.assertNotIn('premium:lifetime', update['entitlements'])

    def test_repeat_redemption_and_deleted_account_cannot_reuse(self):
        for consumed in ({'usedBy': 'user'}, {'usedAt': self.now, 'usedBy': None},
                         {'deletedAccountHash': 'opaque'}, {'revoked': True}):
            with self.subTest(consumed=consumed), self.assertRaises(ValueError):
                redemption_updates(self.code | consumed, {}, 'user', self.now)

    def test_expired_code_is_rejected_at_boundary(self):
        with self.assertRaises(ValueError):
            redemption_updates(self.code | {'redeemBefore': self.now}, {}, 'user', self.now)

    def test_distinct_codes_extend_existing_code_access(self):
        current = self.now + timedelta(days=3)
        update, _, _ = redemption_updates(self.code, {'codeAccessEndsAt': current}, 'user', self.now)
        self.assertEqual(update['codeAccessEndsAt'], current + timedelta(days=7))

    def test_invalid_durations_and_multiple_themes_rejected(self):
        for days in (0, -1, 366, True, '7'):
            with self.subTest(days=days), self.assertRaises(ValueError):
                redemption_updates(self.code | {'durationDays': days}, {}, 'user', self.now)
        with self.assertRaises(ValueError):
            redemption_updates({'rewards': ['theme:rio', 'theme:kiwi']}, {}, 'user', self.now)

    def test_theme_does_not_grant_paid_access(self):
        update, _, _ = redemption_updates({'rewards': ['theme:kiwi']}, {}, 'user', self.now)
        self.assertEqual(update['entitlements'], ['theme:kiwi'])
        self.assertNotIn('codeAccessEndsAt', update)
        self.assertNotIn('subscriptionStatus', update)
