import os
import tempfile
import unittest

from db import Database


class ReminderVariantTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Database(os.path.join(self.tmp.name, "test.sqlite3"))

    def tearDown(self):
        self.tmp.cleanup()

    def test_variants_rotate_and_wrap_per_player(self):
        first = [self.db.next_reminder_variant(101, "city_return", 3) for _ in range(4)]
        self.assertEqual(first[0], first[3])
        self.assertEqual(len(set(first[:3])), 3)

    def test_variant_state_is_independent_per_player_and_reminder(self):
        a = self.db.next_reminder_variant(101, "city_return", 4)
        b = self.db.next_reminder_variant(202, "city_return", 4)
        c = self.db.next_reminder_variant(101, "low_stock", 4)
        self.assertEqual(a, 101 % 4)
        self.assertEqual(b, 202 % 4)
        self.assertEqual(c, 101 % 4)

    def test_variant_state_survives_database_reopen(self):
        first = self.db.next_reminder_variant(101, "business_profit", 5)
        reopened = Database(self.db.path)
        second = reopened.next_reminder_variant(101, "business_profit", 5)
        self.assertEqual(second, (first + 1) % 5)


if __name__ == "__main__":
    unittest.main()
