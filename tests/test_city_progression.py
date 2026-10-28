import os
import tempfile
import unittest

from db import Database
from progression_system import Progression


class CityProgressionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Database(os.path.join(self.tmp.name, "bandit.db"))
        self.player = self.db.get_or_create_user(123456789)
        self.uid = int(self.player["id"])
        self.progression = Progression(self.db)

    def tearDown(self):
        self.tmp.cleanup()

    def test_city_help_counts_toward_daily_and_weekly_contracts(self):
        self.progression.record(self.uid, "city_help", now=1793188800)
        daily = self.progression.view(self.uid, "daily", now=1793188800)
        weekly = self.progression.view(self.uid, "weekly", now=1793188800)
        self.assertIn("Помоги городу в 2 происшествиях", daily)
        self.assertIn("1/2", daily)
        self.assertIn("Помоги городу в 10 происшествиях", weekly)
        self.assertIn("1/10", weekly)

    def test_city_help_does_not_advance_work_tasks(self):
        self.progression.record(self.uid, "city_help", now=1793188800)
        daily = self.progression.view(self.uid, "daily", now=1793188800)
        self.assertIn("Выполни 3 рабочие смены", daily)
        self.assertIn("0/3", daily)


if __name__ == "__main__":
    unittest.main()
