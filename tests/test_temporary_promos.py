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

    def test_october_promos_are_seeded_with_fixed_expiry_rewards_and_limits(self):
        expected = {
            "BC-OCT-LEGEND": (25_000, 250, 1_000, "🏆 Bandit Legend Outfit"),
            "BC-OCT-NEON": (15_000, 200, 1_500, "🌃 Neon City Background"),
            "BC-OCT-NIGHT": (10_000, 150, 2_000, "🎭 Nightfall Mask"),
        }
        with self.db.connect() as conn:
            rows = conn.execute(
                "SELECT code,expires_at,max_uses,active,reward_item,reward_cash,reward_xp "
                "FROM promo_codes WHERE code LIKE 'BC-OCT-%'"
            ).fetchall()
        self.assertEqual({row["code"] for row in rows}, set(expected))
        for row in rows:
            self.assertEqual(row["active"], 1)
            self.assertEqual(row["expires_at"], 1793491200)  # 2026-11-01 00:00 UTC
            cash, xp, limit, item = expected[row["code"]]
            self.assertEqual(row["max_uses"], limit)
            self.assertEqual(row["reward_cash"], cash)
            self.assertEqual(row["reward_xp"], xp)
            self.assertEqual(row["reward_item"], item)

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
