import os
import tempfile
import time
import unittest

from db import Database


class TemporaryPromoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Database(os.path.join(self.tmp.name, "bandit.db"))

    def tearDown(self):
        self.tmp.cleanup()

    def test_temporary_legendary_promos_are_seeded_with_expiry_and_limit(self):
        with self.db.connect() as conn:
            rows = conn.execute("SELECT code,expires_at,max_uses,active,reward_item FROM promo_codes WHERE code LIKE 'BC-%-72H'").fetchall()
        self.assertEqual(len(rows), 3)
        for row in rows:
            self.assertEqual(row["active"], 1)
            self.assertEqual(row["max_uses"], 100)
            self.assertGreater(row["expires_at"], int(time.time()))
            self.assertTrue(row["reward_item"])

    def test_legacy_promo_codes_are_deactivated_without_deleting_history(self):
        with self.db.connect() as conn:
            conn.execute("INSERT OR IGNORE INTO promo_codes(code,title,reward_cash,reward_xp) VALUES('0.20','Old',20000,100)")
        self.db.seed_promos()
        with self.db.connect() as conn:
            row = conn.execute("SELECT active FROM promo_codes WHERE code='0.20'").fetchone()
        self.assertEqual(row["active"], 0)

    def test_expired_promo_cannot_be_redeemed(self):
        user = self.db.get_or_create_user(330506446)
        with self.db.connect() as conn:
            conn.execute("INSERT INTO promo_codes(code,title,reward_cash,reward_xp,max_uses,used_count,active,expires_at) VALUES('EXPIRED','Истёк',0,0,10,0,1,?)", (int(time.time()) - 1,))
        ok, message = self.db.redeem_promo(user["id"], "EXPIRED")
        self.assertFalse(ok)
        self.assertIn("истёк", message.lower())


if __name__ == "__main__":
    unittest.main()
