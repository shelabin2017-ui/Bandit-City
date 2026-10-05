import os
import tempfile
import unittest

from db import Database
from game import Game


class StatusTests(unittest.TestCase):
    def setUp(self):
        self.f=tempfile.NamedTemporaryFile(delete=False)
        self.f.close()
        self.db=Database(self.f.name)
        self.uid=self.db.get_or_create_user(700002)["id"]
        self.game=Game(self.db,set())

    def tearDown(self):
        os.unlink(self.f.name)

    def test_status_defaults_and_energy(self):
        r=self.db.status(self.uid)
        self.assertEqual(r["energy"],100)
        self.assertEqual(r["heat"],0)
        self.db.status_change(self.uid,heat=20,reputation=5,energy=-10)
        r=self.db.status(self.uid)
        self.assertEqual(r["heat"],20)
        self.assertEqual(r["reputation"],5)
        self.assertEqual(r["energy"],90)

    def test_work_consumes_energy(self):
        before=self.db.status(self.uid)["energy"]
        self.game.work(self.uid,"taxi")
        after=self.db.status(self.uid)["energy"]
        self.assertEqual(after,before-10)


if __name__=="__main__":
    unittest.main(verbosity=2)
