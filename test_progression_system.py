import os
import tempfile
import unittest

from db import Database
from progression_system import Progression, DAILY_TASKS, WEEKLY_TASKS


class ProgressionSystemTests(unittest.TestCase):
    def setUp(self):
        handle, self.path = tempfile.mkstemp(suffix=".db")
        os.close(handle)
        self.db = Database(self.path)
        self.user = self.db.get_or_create_user(998877)["id"]
        self.progress = Progression(self.db)

    def tearDown(self):
        for suffix in ("", "-wal", "-shm"):
            try:
                os.remove(self.path + suffix)
            except FileNotFoundError:
                pass

    def test_daily_contract_claim_is_idempotent(self):
        before = self.db.get_or_create_user(998877)["balance"]
        self.progress.record(self.user, "work", 3)
        first = self.progress.claim(self.user, "work3", "daily")
        after_first = self.db.get_or_create_user(998877)["balance"]
        second = self.progress.claim(self.user, "work3", "daily")
        after_second = self.db.get_or_create_user(998877)["balance"]
        self.assertIn("Контракт выполнен", first)
        self.assertEqual(after_first - before, DAILY_TASKS["work3"]["cash"])
        self.assertIn("уже получена", second)
        self.assertEqual(after_second, after_first)

    def test_incomplete_contract_does_not_pay(self):
        before = self.db.get_or_create_user(998877)["balance"]
        message = self.progress.claim(self.user, "work3", "daily")
        after = self.db.get_or_create_user(998877)["balance"]
        self.assertIn("ещё не выполнен", message)
        self.assertEqual(after, before)

    def test_gang_create_join_and_donate(self):
        second = self.db.get_or_create_user(998878)["id"]
        created = self.progress.gang_command(self.user, "/gang create Night Wolves")
        self.assertIn("создана", created)
        code = created.rsplit(" ", 1)[-1]
        joined = self.progress.gang_command(second, "/gang join " + code)
        self.assertIn("вступил", joined)
        with self.db.connect() as c:
            c.execute("UPDATE users SET balance=5000 WHERE id=?", (second,))
        donated = self.progress.gang_command(second, "/gang donate 1000")
        self.assertIn("Вклад", donated)
        with self.db.connect() as c:
            balance = c.execute("SELECT balance FROM users WHERE id=?", (second,)).fetchone()[0]
            treasury = c.execute("SELECT treasury FROM gangs WHERE code=?", (code,)).fetchone()[0]
        self.assertEqual(balance, 4000)
        self.assertEqual(treasury, 1000)

    def test_gang_donation_cannot_overdraw(self):
        created = self.progress.gang_command(self.user, "/gang create Safe Gang")
        code = created.rsplit(" ", 1)[-1]
        with self.db.connect() as c:
            c.execute("UPDATE users SET balance=10 WHERE id=?", (self.user,))
        result = self.progress.gang_command(self.user, "/gang donate 100")
        self.assertIn("Недостаточно денег", result)
        with self.db.connect() as c:
            self.assertEqual(c.execute("SELECT treasury FROM gangs WHERE code=?", (code,)).fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
