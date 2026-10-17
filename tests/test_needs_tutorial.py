import os
import tempfile
import unittest
from unittest.mock import patch

from db import Database
from game import Game


class NeedsAndTutorialTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(delete=False)
        self.tmp.close()
        self.db = Database(self.tmp.name)
        self.user = self.db.get_or_create_user(880001)
        self.uid = self.user["id"]
        self.game = Game(self.db, set())

    def tearDown(self):
        os.unlink(self.tmp.name)

    def test_hunger_ticks_offline_and_energy_regenerates(self):
        now = 2_000_000_000
        with patch("db.time.time", return_value=now):
            self.db.status(self.uid)
        with self.db.connect() as c:
            c.execute(
                "UPDATE player_status SET energy=40,hunger=10,last_update=? WHERE user_id=?",
                (now - 600, self.uid),
            )
        with patch("db.time.time", return_value=now):
            status = self.db.status(self.uid)
        self.assertEqual(status["hunger"], 12)
        self.assertEqual(status["energy"], 90)

    def test_status_reads_do_not_discard_partial_elapsed_time(self):
        now = 2_000_000_000
        with patch("db.time.time", return_value=now):
            self.db.status(self.uid)
        with self.db.connect() as c:
            c.execute(
                "UPDATE player_status SET energy=50,hunger=0,last_update=? WHERE user_id=?",
                (now - 30, self.uid),
            )
        with patch("db.time.time", return_value=now):
            self.db.status(self.uid)
        with patch("db.time.time", return_value=now + 30):
            status = self.db.status(self.uid)
        self.assertEqual(status["energy"], 55)

    def test_food_is_consumed_only_from_owners_inventory(self):
        with self.db.connect() as c:
            c.execute(
                "INSERT INTO items(user_id,name,price,bought_at) VALUES(?,?,?,?)",
                (self.uid, "🍔 Бургер", 12000, 1),
            )
            item_id = c.execute("SELECT last_insert_rowid()").fetchone()[0]
            c.execute(
                "INSERT INTO player_status(user_id,heat,reputation,energy,hunger,last_update) VALUES(?,?,?,?,?,?)",
                (self.uid, 0, 0, 40, 80, 1),
            )
        result = self.game.eat_item(self.uid, item_id)
        self.assertIn("Голод −35", result)
        status = self.db.status(self.uid)
        self.assertEqual(status["hunger"], 45)
        self.assertEqual(status["energy"], 45)
        self.assertIsNone(self.db.consume_inventory_item(self.uid, item_id))

    def test_tutorial_first_job_cannot_be_skipped(self):
        self.db.tutorial_set(self.uid, 1, False)
        result = self.game.tutorial_next(self.uid)
        self.assertIn("нельзя пропустить", result.lower())
        self.assertEqual(int(self.db.tutorial(self.uid)["step"]), 1)
        self.db.sms_task_complete(self.uid, "first_job")
        result = self.game.tutorial_next(self.uid)
        self.assertIn("Деньги", result)
        self.assertEqual(int(self.db.tutorial(self.uid)["step"]), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
