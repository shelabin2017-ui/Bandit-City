import os
import tempfile
import time
import unittest

from business_expansion import BUSINESSES, buy_business, portfolio_text, withdraw_income
from db import Database


class BusinessExpansionTests(unittest.TestCase):
    def setUp(self):
        handle, self.path = tempfile.mkstemp(suffix=".db")
        os.close(handle)
        self.db = Database(self.path)
        self.user_id, _ = self.db.get_or_create_user(10001)

    def tearDown(self):
        for suffix in ("", "-wal", "-shm"):
            try:
                os.remove(self.path + suffix)
            except FileNotFoundError:
                pass

    def test_catalog_has_six_businesses(self):
        self.assertEqual(len(BUSINESSES), 6)

    def test_purchase_deducts_money_and_prevents_duplicate(self):
        self.db.add_money(self.user_id, 1_000_000)
        result = buy_business(self.db, self.user_id, "kiosk")
        self.assertIn("Куплено", result)
        self.assertIn("уже есть", buy_business(self.db, self.user_id, "kiosk"))
        self.assertIn("Продуктовый киоск", portfolio_text(self.db, self.user_id))

    def test_income_is_accrued_and_withdrawn_once(self):
        self.db.add_money(self.user_id, 1_000_000)
        buy_business(self.db, self.user_id, "kiosk")
        with self.db.connect() as c:
            c.execute("UPDATE business_portfolio SET last_tick=? WHERE user_id=?", (int(time.time()) - 180, self.user_id))
        text = portfolio_text(self.db, self.user_id)
        self.assertIn("$1 350", text)
        self.assertIn("$1 350", withdraw_income(self.db, self.user_id))
        self.assertIn("нечего снимать", withdraw_income(self.db, self.user_id).lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
