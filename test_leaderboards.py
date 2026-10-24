import os
import tempfile
import unittest

from db import Database


class LeaderboardCategoryTests(unittest.TestCase):
    def setUp(self):
        handle, self.path = tempfile.mkstemp(prefix="bandit-leaderboards-", suffix=".sqlite")
        os.close(handle)
        self.db = Database(self.path)
        self.rich = self.db.get_or_create_user(810001)["id"]
        self.levelled = self.db.get_or_create_user(810002)["id"]
        self.poor = self.db.get_or_create_user(810003)["id"]

        with self.db.connect() as conn:
            conn.execute(
                "UPDATE users SET nickname=?, balance=?, bank=?, level=?, xp=?, referrals=? WHERE id=?",
                ("RichPlayer", 5000, 3000, 4, 250, 3, self.rich),
            )
            conn.execute(
                "UPDATE users SET nickname=?, balance=?, bank=?, level=?, xp=?, referrals=? WHERE id=?",
                ("LevelPlayer", 100, 0, 12, 900, 1, self.levelled),
            )
            conn.execute(
                "UPDATE users SET nickname=?, balance=?, bank=?, level=?, xp=?, referrals=? WHERE id=?",
                ("PoorPlayer", 50, 0, 2, 20, 0, self.poor),
            )
            conn.execute(
                "INSERT INTO cars(user_id,model,category,speed,price,bought_at) VALUES(?,?,?,?,?,?)",
                (self.rich, "Test car", "sedan", 100, 1000, 1),
            )
            conn.execute(
                "INSERT INTO businesses(user_id,type,level,stock,balance,last_tick) VALUES(?,?,?,?,?,?)",
                (self.levelled, "test", 1, 10, 0, 1),
            )
            conn.execute(
                "INSERT INTO achievements(user_id,code,created_at) VALUES(?,?,?)",
                (self.poor, "test-achievement", 1),
            )

    def tearDown(self):
        for suffix in ("", "-wal", "-shm"):
            try:
                os.remove(self.path + suffix)
            except FileNotFoundError:
                pass

    def test_wealth_uses_cash_plus_bank(self):
        result = self.db.top_category("wealth")
        self.assertLess(result.index("RichPlayer"), result.index("LevelPlayer"))
        self.assertIn("$8 000", result)

    def test_level_and_xp_categories_use_their_own_metrics(self):
        self.assertLess(self.db.top_category("level").index("LevelPlayer"),
                        self.db.top_category("level").index("RichPlayer"))
        self.assertLess(self.db.top_category("xp").index("LevelPlayer"),
                        self.db.top_category("xp").index("RichPlayer"))

    def test_car_business_referral_and_achievement_categories(self):
        self.assertLess(self.db.top_category("cars").index("RichPlayer"),
                        self.db.top_category("cars").index("LevelPlayer"))
        self.assertLess(self.db.top_category("business").index("LevelPlayer"),
                        self.db.top_category("business").index("RichPlayer"))
        self.assertLess(self.db.top_category("referrals").index("RichPlayer"),
                        self.db.top_category("referrals").index("LevelPlayer"))
        self.assertLess(self.db.top_category("achievements").index("PoorPlayer"),
                        self.db.top_category("achievements").index("RichPlayer"))

    def test_unknown_category_falls_back_to_wealth(self):
        self.assertEqual(self.db.top_category("not-a-category"),
                         self.db.top_category("wealth"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
