import os
import tempfile
import unittest
from unittest.mock import patch

from db import Database
from game import Game


class FixerContractTests(unittest.TestCase):
    def setUp(self):
        handle, self.path = tempfile.mkstemp(suffix=".db")
        os.close(handle)
        self.db = Database(self.path)
        self.user_id = self.db.get_or_create_user(700002)["id"]
        self.game = Game(self.db, set())

    def tearDown(self):
        for suffix in ("", "-wal", "-shm"):
            try:
                os.remove(self.path + suffix)
            except FileNotFoundError:
                pass

    def set_cash(self, amount):
        with self.db.connect() as conn:
            conn.execute("UPDATE users SET balance=? WHERE id=?", (amount, self.user_id))

    def cash(self):
        return int(self.db.user(self.user_id)["balance"])

    def test_fixer_instructions_explain_cash_chance_cooldown_and_no_id(self):
        message = self.game.npc(self.user_id, "fixer")
        self.assertIn("$10 000 наличными", message)
        self.assertIn("50%", message)
        self.assertIn("ID контракта не нужен", message)

    def test_fixer_contract_refuses_insufficient_cash_without_charging(self):
        self.set_cash(9_999)
        message = self.game.npc_action(self.user_id, "fixer")
        self.assertIn("нужно $10 000 наличными", message)
        self.assertEqual(self.cash(), 9_999)

    def test_fixer_contract_success_pays_reward_and_starts_cooldown(self):
        self.set_cash(10_000)
        with patch("game.random.random", return_value=0.1):
            message = self.game.npc_action(self.user_id, "fixer")
        self.assertIn("ЗАКАЗ ВЫПОЛНЕН", message)
        self.assertEqual(self.cash(), 30_000)
        self.assertGreater(self.db.npc_cooldown_remaining(self.user_id, "fixer", "contract"), 0)

    def test_fixer_contract_failure_reports_lost_advance_and_starts_cooldown(self):
        self.set_cash(10_000)
        with patch("game.random.random", return_value=0.9):
            message = self.game.npc_action(self.user_id, "fixer")
        self.assertIn("ЗАКАЗ СОРВАН", message)
        self.assertEqual(self.cash(), 0)
        self.assertGreater(self.db.npc_cooldown_remaining(self.user_id, "fixer", "contract"), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
