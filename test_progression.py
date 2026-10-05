import os
import tempfile
import unittest

from db import Database
from game import Game


class ProgressionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.NamedTemporaryFile(delete=False)
        self.tmp.close()
        self.db=Database(self.tmp.name)
        self.uid=self.db.get_or_create_user(700001)["id"]
        self.game=Game(self.db,set())

    def tearDown(self):
        os.unlink(self.tmp.name)

    def test_work_updates_mission_and_sms(self):
        message=self.game.work(self.uid,"taxi")
        self.assertIn("Таксист",message)
        row=self.db.mission_rows(self.uid,["work_3"])["work_3"]
        self.assertEqual(row["progress"],1)
        task=self.db.sms_task_rows(self.uid,["first_job"])["first_job"]
        self.assertEqual(task["completed"],1)
        self.assertTrue(self.db.sms_list(self.uid))

    def test_sms_reward_is_claimed_once(self):
        self.db.sms_task_complete(self.uid,"first_job")
        first=self.game.complete_sms_task(self.uid,"first_job")
        second=self.game.complete_sms_task(self.uid,"first_job")
        self.assertIn("ЗАДАНИЕ ВЫПОЛНЕНО",first)
        self.assertIn("Награда уже получена",second)

    def test_tutorial_completion_opens_city(self):
        for _ in range(len(self.game.TUTORIAL)):
            self.game.tutorial_next(self.uid)
        self.assertTrue(self.db.tutorial(self.uid)["completed"])
        self.assertFalse(self.db.needs_onboarding(self.uid))

    def test_casino_stats_and_missions(self):
        self.db.add_money(self.uid,1_000_000)
        self.game.casino(self.uid,"🎲 Кости")
        stats=self.db.casino_stats(self.uid)
        self.assertEqual(stats["plays"],1)
        self.assertEqual(stats["wagered"],10_000)
        self.assertEqual(self.db.mission_rows(self.uid,["casino_3"])["casino_3"]["progress"],1)


if __name__=="__main__":
    unittest.main(verbosity=2)
