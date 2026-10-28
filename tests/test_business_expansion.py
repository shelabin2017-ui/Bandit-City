import os
import tempfile
import unittest

from db import Database
from business_expansion import buy_business, ensure_schema


class BusinessPortfolioLimitTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Database(os.path.join(self.tmp.name, "test.db"))
        self.user = self.db.get_or_create_user(700002)
        with self.db.connect() as c:
            c.execute("UPDATE users SET balance=100000000, level=2 WHERE id=?", (self.user["id"],))
        ensure_schema(self.db)

    def tearDown(self):
        self.tmp.cleanup()

    def test_level_sets_portfolio_limit(self):
        uid = self.user["id"]
        self.assertIn("Куплено", buy_business(self.db, uid, "kiosk"))
        self.assertIn("Куплено", buy_business(self.db, uid, "car_wash"))
        message = buy_business(self.db, uid, "cafe")
        self.assertIn("Лимит бизнеса", message)
        with self.db.connect() as c:
            self.assertEqual(c.execute(
                "SELECT COUNT(*) FROM business_portfolio WHERE user_id=?", (uid,)
            ).fetchone()[0], 2)

    def test_legacy_business_counts_toward_limit(self):
        uid = self.user["id"]
        with self.db.connect() as c:
            c.execute(
                "INSERT INTO businesses(user_id,type,last_tick) VALUES(?,?,?)",
                (uid, "airport", 1),
            )
        self.assertIn("Куплено", buy_business(self.db, uid, "kiosk"))
        self.assertIn("Лимит бизнеса", buy_business(self.db, uid, "car_wash"))


if __name__ == "__main__":
    unittest.main()
