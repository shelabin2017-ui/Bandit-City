import os
import tempfile
import unittest

from db import Database
from duel_system import DuelSystem


class DuelSystemTests(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.db = Database(self.path)
        self.a = self.db.get_or_create_user(998871)
        self.b = self.db.get_or_create_user(998872)
        self.duels = DuelSystem(self.db)

    def tearDown(self):
        for suffix in ("", "-wal", "-shm"):
            try:
                os.remove(self.path + suffix)
            except FileNotFoundError:
                pass

    def test_cannot_challenge_self(self):
        self.assertIn("самого себя", self.duels.challenge(998871, 998871))

    def test_only_target_can_accept_and_stake_is_settled(self):
        challenge = self.duels.challenge(998871, 998872)
        duel_id = int(challenge.split("ID дуэли: ")[1].split(".")[0])
        self.assertIn("только приглашённый", self.duels.accept(998873, duel_id))
        before_a = self.db.get_or_create_user(998871)["balance"]
        before_b = self.db.get_or_create_user(998872)["balance"]
        result = self.duels.accept(998872, duel_id)
        self.assertIn("Дуэль завершена", result)
        after_a = self.db.get_or_create_user(998871)["balance"]
        after_b = self.db.get_or_create_user(998872)["balance"]
        self.assertEqual(after_a + after_b, before_a + before_b)
        with self.db.connect() as c:
            row = c.execute("SELECT status,winner_id,loser_id FROM duels WHERE id=?", (duel_id,)).fetchone()
        self.assertEqual(row["status"], "finished")
        self.assertIn(row["winner_id"], (998871, 998872))
        self.assertIn(row["loser_id"], (998871, 998872))
        # Replaying the same accept request must not transfer another stake.
        replay = self.duels.accept(998872, duel_id)
        self.assertIn("уже завершена", replay)
        self.assertEqual(self.db.get_or_create_user(998871)["balance"], after_a)
        self.assertEqual(self.db.get_or_create_user(998872)["balance"], after_b)

    def test_insufficient_balance_rejects_challenge(self):
        with self.db.connect() as c:
            c.execute("UPDATE users SET balance=0 WHERE vk_id=998872")
        self.assertIn("минимум", self.duels.challenge(998871, 998872))


if __name__ == "__main__":
    unittest.main(verbosity=2)
