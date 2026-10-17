import os
import sqlite3
import tempfile
import unittest

from admin_panel import AdminPanel
from db import Database


class PromoAdminTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "bandit.db")
        self.db = Database(self.db_path)
        self.panel = AdminPanel(self.db, None, {330506446})

    def tearDown(self):
        self.tmp.cleanup()

    def test_numeric_dotted_promo_code_can_be_created(self):
        uid = 330506446
        self.panel.state[uid] = "promo_add"
        handled, message, _ = self.panel.handle(uid, "0.20|Подарок 0.20|20000|100|0")
        self.assertTrue(handled)
        self.assertIn("создан", message.lower())
        with self.db.connect() as conn:
            row = conn.execute(
                "SELECT code,reward_cash,reward_xp,max_uses,used_count,active FROM promo_codes WHERE code=?",
                ("0.20",),
            ).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual((row["reward_cash"], row["reward_xp"], row["max_uses"], row["used_count"], row["active"]),
                         (20000, 100, 0, 0, 1))

    def test_duplicate_promo_does_not_reset_usage(self):
        uid = 330506446
        with self.db.connect() as conn:
            conn.execute(
                "INSERT INTO promo_codes(code,title,reward_cash,reward_xp,max_uses,used_count,active) VALUES(?,?,?,?,?,?,?)",
                ("ZEROSHKA20", "Existing", 1, 1, 10, 4, 1),
            )
        self.panel.state[uid] = "promo_add"
        handled, message, _ = self.panel.handle(uid, "ZEROSHKA20|Replacement|500|50|100")
        self.assertTrue(handled)
        self.assertIn("уже существует", message.lower())
        with self.db.connect() as conn:
            row = conn.execute("SELECT title,used_count FROM promo_codes WHERE code=?", ("ZEROSHKA20",)).fetchone()
        self.assertEqual((row["title"], row["used_count"]), ("Existing", 4))

    def test_old_promo_table_is_migrated_without_dropping_data(self):
        legacy_path = os.path.join(self.tmp.name, "legacy.db")
        with sqlite3.connect(legacy_path) as conn:
            conn.execute(
                "CREATE TABLE promo_codes(code TEXT PRIMARY KEY,title TEXT NOT NULL,"
                "reward_cash INTEGER NOT NULL DEFAULT 0,reward_xp INTEGER NOT NULL DEFAULT 0,"
                "max_uses INTEGER NOT NULL DEFAULT 0,used_count INTEGER NOT NULL DEFAULT 0,"
                "active INTEGER NOT NULL DEFAULT 1)"
            )
            conn.execute(
                "INSERT INTO promo_codes(code,title,reward_cash,reward_xp,max_uses,used_count,active) "
                "VALUES('OLD20','Old promo',500,20,0,2,1)"
            )
        Database(legacy_path)
        with sqlite3.connect(legacy_path) as conn:
            columns = {row[1] for row in conn.execute("PRAGMA table_info(promo_codes)")}
            row = conn.execute("SELECT title,used_count FROM promo_codes WHERE code='OLD20'").fetchone()
        self.assertIn("reward_item", columns)
        self.assertIn("reward_slot", columns)
        self.assertEqual(row, ("Old promo", 2))


if __name__ == "__main__":
    unittest.main()
