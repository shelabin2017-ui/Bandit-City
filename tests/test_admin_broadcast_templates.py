import unittest

from admin_panel import AdminPanel


class FakeDB:
    def __init__(self):
        self.values = {}

    def connect(self):
        raise AssertionError("DB should not be needed for broadcast templates")


class AdminBroadcastTemplateTests(unittest.TestCase):
    def setUp(self):
        self.admin = AdminPanel(FakeDB(), None, admin_ids={123})

    def test_broadcast_menu_has_common_greetings(self):
        handled, message, rows = self.admin.handle(123, "📢 Рассылка")
        self.assertTrue(handled)
        buttons = [button for row in rows for button in row]
        self.assertIn("🌙 Доброй ночи", buttons)
        self.assertIn("🎮 Хорошей игры", buttons)
        self.assertIn("✍️ Свой текст", buttons)

    def test_template_requires_confirmation_before_broadcast(self):
        handled, preview, rows = self.admin.handle(123, "🌙 Доброй ночи")
        self.assertTrue(handled)
        self.assertIn("ДОБРОЙ НОЧИ", preview)
        self.assertIn("Администрация BANDIT CITY", preview)
        self.assertEqual(self.admin.state[123][0], "broadcast_confirm")
        buttons = [button for row in rows for button in row]
        self.assertIn("✅ Отправить", buttons)
        self.assertIn("❌ Отмена", buttons)

    def test_non_admin_cannot_open_broadcast_templates(self):
        handled, _, _ = self.admin.handle(999, "📢 Рассылка")
        self.assertFalse(handled)


if __name__ == "__main__":
    unittest.main()
