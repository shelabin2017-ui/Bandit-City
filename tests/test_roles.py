import os
import tempfile
import unittest

from db import Database
from roles import Role, RoleManager


class RoleBootstrapTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Database(os.path.join(self.tmp.name, "bandit.db"))
        self.roles = RoleManager(self.db)

    def tearDown(self):
        self.tmp.cleanup()

    def test_bootstrap_owner_demotes_other_owners(self):
        self.roles.bootstrap_owner(330506446)
        self.roles.bootstrap_owner(111111111)
        self.roles.bootstrap_owner(330506446)
        self.assertEqual(self.roles.role(330506446), Role.OWNER)
        self.assertNotEqual(self.roles.role(111111111), Role.OWNER)

    def test_admin_cannot_change_roles(self):
        self.roles.bootstrap_owner(330506446)
        ok, _ = self.roles.set_role(330506446, 222222222, Role.ADMIN)
        self.assertTrue(ok)
        ok, _ = self.roles.set_role(222222222, 333333333, Role.ADMIN)
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
