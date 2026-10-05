import os
import tempfile
import unittest
from pathlib import Path

from db import Database
from roles import Role, RoleManager


class RoleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(delete=False)
        self.tmp.close()
        self.db = Database(self.tmp.name)
        self.roles = RoleManager(self.db)
        self.owner = 1001
        self.admin = 1002
        self.mod = 1003
        self.player = 1004
        self.roles.bootstrap_owner(self.owner)
        self.roles.set_role(self.owner, self.admin, Role.ADMIN)
        self.roles.set_role(self.owner, self.mod, Role.MODERATOR)

    def tearDown(self):
        os.unlink(self.tmp.name)

    def test_default_player(self):
        self.assertEqual(self.roles.role(self.player), Role.PLAYER)

    def test_hierarchy(self):
        self.assertTrue(self.roles.has(self.owner, "owner.manage"))
        self.assertTrue(self.roles.has(self.admin, "economy.manage"))
        self.assertTrue(self.roles.has(self.mod, "moderation.ban"))
        self.assertFalse(self.roles.has(self.mod, "economy.manage"))
        self.assertFalse(self.roles.has(self.player, "moderation.ban"))

    def test_only_owner_manages_staff(self):
        ok, _ = self.roles.set_role(self.admin, self.player, Role.MODERATOR)
        self.assertFalse(ok)
        ok, _ = self.roles.set_role(self.mod, self.player, Role.ADMIN)
        self.assertFalse(ok)
        ok, _ = self.roles.set_role(self.owner, self.player, Role.MODERATOR)
        self.assertTrue(ok)
        self.assertEqual(self.roles.role(self.player), Role.MODERATOR)

    def test_owner_is_protected(self):
        ok, _ = self.roles.set_role(self.admin, self.owner, Role.PLAYER)
        self.assertFalse(ok)
        ok, _ = self.roles.set_role(self.mod, self.owner, Role.PLAYER)
        self.assertFalse(ok)
        self.assertEqual(self.roles.role(self.owner), Role.OWNER)

    def test_owner_cannot_self_revoke(self):
        ok, _ = self.roles.revoke(self.owner, self.owner)
        self.assertFalse(ok)
        self.assertEqual(self.roles.role(self.owner), Role.OWNER)

    def test_revoke_returns_player(self):
        ok, _ = self.roles.revoke(self.owner, self.admin)
        self.assertTrue(ok)
        self.assertEqual(self.roles.role(self.admin), Role.PLAYER)


    def test_bot_and_panel_are_role_wired(self):
        root = Path(__file__).resolve().parent
        bot = (root / "bot.py").read_text(encoding="utf-8")
        panel = (root / "admin_panel.py").read_text(encoding="utf-8")
        self.assertIn("RoleManager(db)", bot)
        self.assertIn("RoleUI(roles)", bot)
        self.assertIn("roles=roles", bot)
        self.assertIn("def _moderator_allowed", panel)
        self.assertIn("self.roles.set_role", panel)
        self.assertIn("self.roles.revoke", panel)

    def test_staff_listing(self):
        staff = {r.vk_id: r.role for r in self.roles.staff()}
        self.assertEqual(staff[self.owner], Role.OWNER)
        self.assertEqual(staff[self.mod], Role.MODERATOR)
        self.assertNotIn(self.player, staff)


if __name__ == "__main__":
    unittest.main(verbosity=2)
