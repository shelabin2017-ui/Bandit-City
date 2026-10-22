import os
import tempfile
import unittest

from db import Database
from game import Game


class GuidedTutorialTests(unittest.TestCase):
    def setUp(self):
        handle, self.path = tempfile.mkstemp(suffix=".db")
        os.close(handle)
        self.db = Database(self.path)
        self.user_id = self.db.get_or_create_user(700001)["id"]
        self.game = Game(self.db, set())

    def tearDown(self):
        for suffix in ("", "-wal", "-shm"):
            try:
                os.remove(self.path + suffix)
            except FileNotFoundError:
                pass

    def test_tour_covers_menu_categories_and_creator(self):
        self.assertGreaterEqual(len(self.game.TUTORIAL), 14)
        for button in (
            "👤 Профиль", "📊 Мой статус", "💼 Работа", "🏢 Бизнес",
            "🚗 Авто", "🛒 Магазин", "🏦 Банк", "🎰 Казино",
            "👥 Игроки", "📱 Телефон", "🎯 Миссии", "🌆 События города",
            "🎒 Инвентарь", "🍔 Потребности", "📩 СМС", "🏆 Рейтинг",
            "🏆 Достижения", "🎁 Бонус", "📚 Ещё", "📖 Сюжет",
            "🎟 Промокод", "⚙️ Настройки", "❓ Помощь", "👑 О создателе",
        ):
            self.assertIn(button, self.game.TUTORIAL_VIEWS)
            self.assertTrue(self.game.tutorial_view(self.user_id, button).strip())

    def test_first_job_step_cannot_be_skipped(self):
        self.db.tutorial_set(self.user_id, 1, False)
        message = self.game.tutorial_next(self.user_id)
        self.assertIn("первую рабочую смену", message)
        self.assertEqual(int(self.db.tutorial(self.user_id)["step"]), 1)
        self.assertTrue(self.db.needs_onboarding(self.user_id))

    def test_first_job_unlocks_tour_and_completion_finishes_onboarding(self):
        self.db.tutorial_set(self.user_id, 1, False)
        self.db.sms_task_complete(self.user_id, "first_job")
        message = self.game.tutorial_next(self.user_id)
        self.assertIn("Деньги, профиль и статус", message)
        self.assertEqual(int(self.db.tutorial(self.user_id)["step"]), 2)
        self.db.tutorial_set(self.user_id, len(self.game.TUTORIAL) - 1, False)
        final = self.game.tutorial_next(self.user_id)
        self.assertIn("ОБУЧЕНИЕ ЗАВЕРШЕНО", final)
        self.assertFalse(self.db.needs_onboarding(self.user_id))
        self.assertTrue(self.db.tutorial(self.user_id)["completed"])

    def test_viewing_a_section_does_not_change_tutorial_progress(self):
        self.db.tutorial_set(self.user_id, 4, False)
        before = int(self.db.tutorial(self.user_id)["step"])
        view = self.game.tutorial_view(self.user_id, "🚗 Авто")
        self.assertIn("гараж и автосалон", view)
        self.assertEqual(int(self.db.tutorial(self.user_id)["step"]), before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
