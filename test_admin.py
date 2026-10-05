import os
import tempfile
import unittest

from admin_panel import AdminPanel
from db import Database
from game import Game
from role_ui import RoleUI
from roles import Role, RoleManager


class AdminWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(delete=False)
        self.tmp.close()
        self.db = Database(self.tmp.name)
        self.owner = 900001
        self.admin = 900002
        self.player = 900003
        for uid in (self.owner, self.admin, self.player):
            self.db.get_or_create_user(uid)
        self.roles = RoleManager(self.db)
        self.roles.bootstrap_owner(self.owner)
        self.roles.set_role(self.owner, self.admin, Role.ADMIN)
        self.panel = AdminPanel(
            self.db,
            Game(self.db, {self.owner}),
            {self.owner},
            roles=self.roles,
            role_ui=RoleUI(self.roles),
        )

    def tearDown(self):
        os.unlink(self.tmp.name)

    def test_owner_role_controls(self):
        handled, _, _ = self.panel.handle(self.owner, "➕ Выдать роль")
        self.assertTrue(handled)
        handled, message, _ = self.panel.handle(self.owner, f"{self.player} moderator")
        self.assertTrue(handled)
        self.assertIn("MODERATOR", message)

    def test_admin_promo_buttons(self):
        handled, _, _ = self.panel.handle(self.admin, "🎟 Промокоды")
        self.assertTrue(handled)
        handled, _, _ = self.panel.handle(self.admin, "➕ Создать промокод")
        self.assertTrue(handled)
        handled, message, _ = self.panel.handle(self.admin, "WELCOME|Welcome|50000|25|10")
        self.assertTrue(handled)
        self.assertIn("создан", message.lower())

        handled, message, _ = self.panel.handle(self.admin, "📋 Список промокодов")
        self.assertTrue(handled)
        self.assertIn("WELCOME", message)

    def test_admin_appearance_buttons(self):
        handled, _, _ = self.panel.handle(self.admin, "🎨 Внешность")
        self.assertTrue(handled)
        handled, _, _ = self.panel.handle(self.admin, "🔎 Посмотреть внешность")
        self.assertTrue(handled)
        handled, message, _ = self.panel.handle(self.admin, str(self.player))
        self.assertTrue(handled)
        self.assertIn("ВНЕШНОСТЬ", message)

        handled, _, _ = self.panel.handle(self.admin, "✏️ Изменить внешность")
        self.assertTrue(handled)
        handled, message, _ = self.panel.handle(self.admin, f"{self.player} hair Test Hair")
        self.assertTrue(handled)
        self.assertIn("изменена", message.lower())

    def test_broadcast_requires_confirmation(self):
        handled, _, _ = self.panel.handle(self.admin, "📢 Рассылка")
        self.assertTrue(handled)
        handled, _, _ = self.panel.handle(self.admin, "✍️ Создать рассылку")
        self.assertTrue(handled)
        handled, message, _ = self.panel.handle(self.admin, "Тестовая рассылка")
        self.assertTrue(handled)
        self.assertIn("ПРЕДПРОСМОТР", message)
        handled, message, _ = self.panel.handle(self.admin, "✅ Отправить")
        self.assertTrue(handled)
        self.assertTrue(message.startswith("__BROADCAST_EXEC__|"))

    def test_moderator_cannot_open_admin_economy(self):
        self.roles.set_role(self.owner, self.player, Role.MODERATOR)
        handled, _, _ = self.panel.handle(self.player, "💰 Экономика")
        self.assertFalse(handled)


if __name__ == "__main__":
    unittest.main()
