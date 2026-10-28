import os
import tempfile
import time
import unittest

from db import Database


class CarPromotionTest(unittest.TestCase):
    def setUp(self):
        self.path = tempfile.mktemp(suffix=".db")
        self.db = Database(self.path)

    def tearDown(self):
        for suffix in ("", "-wal", "-shm"):
            try:
                os.remove(self.path + suffix)
            except FileNotFoundError:
                pass

    def test_promotion_starts_once_and_survives_restarts(self):
        start = 1_800_000_000
        state = self.db.ensure_car_promo_started(now=start)
        self.assertTrue(state["active"])
        self.assertEqual(state["start_at"], start)
        self.assertEqual(state["end_at"], start + 72 * 60 * 60)
        later = self.db.ensure_car_promo_started(now=start + 120)
        self.assertEqual(later["start_at"], start)
        self.assertEqual(later["end_at"], start + 72 * 60 * 60)

    def test_discount_is_exactly_20_percent_for_every_catalog_price(self):
        start = int(time.time()) - 10
        self.db.set_setting(self.db.CAR_PROMO_START_KEY, str(start))
        for base_price in (18_000, 35_000, 1_000_000, 50_000_000):
            self.assertEqual(self.db.car_purchase_price(base_price), base_price * 80 // 100)

    def test_promotion_expires_at_72_hours_without_restarting(self):
        start = 1_800_000_000
        self.db.set_setting(self.db.CAR_PROMO_START_KEY, str(start))
        before_end = self.db.car_promo_status(now=start + 72 * 60 * 60 - 1)
        at_end = self.db.car_promo_status(now=start + 72 * 60 * 60)
        self.assertTrue(before_end["active"])
        self.assertFalse(at_end["active"])
        self.assertEqual(self.db.car_purchase_price(100_000, now=start + 72 * 60 * 60), 100_000)

    def test_purchase_charges_discounted_price_and_records_actual_cost(self):
        user = self.db.get_or_create_user(880001)
        with self.db.connect() as conn:
            conn.execute("UPDATE users SET balance=100000 WHERE id=?", (user["id"],))
        self.db.set_setting(self.db.CAR_PROMO_START_KEY, str(int(time.time()) - 1))
        result = self.db.buy_car(user["id"], "Falcon Compact")
        self.assertIn("куплен за $14 400", result)
        self.assertIn("скидка 20%", result)
        with self.db.connect() as conn:
            balance = conn.execute("SELECT balance FROM users WHERE id=?", (user["id"],)).fetchone()["balance"]
            car = conn.execute("SELECT price FROM cars WHERE user_id=? AND model='Falcon Compact'", (user["id"],)).fetchone()
        self.assertEqual(balance, 85_600)
        self.assertEqual(car["price"], 14_400)

    def test_purchase_after_expiry_uses_regular_price(self):
        user = self.db.get_or_create_user(880002)
        with self.db.connect() as conn:
            conn.execute("UPDATE users SET balance=100000 WHERE id=?", (user["id"],))
        self.db.set_setting(self.db.CAR_PROMO_START_KEY, str(int(time.time()) - 72 * 60 * 60 - 5))
        result = self.db.buy_car(user["id"], "Falcon Compact")
        self.assertIn("куплен за $18 000", result)
        with self.db.connect() as conn:
            balance = conn.execute("SELECT balance FROM users WHERE id=?", (user["id"],)).fetchone()["balance"]
        self.assertEqual(balance, 82_000)


if __name__ == "__main__":
    unittest.main(verbosity=2)
