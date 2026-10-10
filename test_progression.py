import os
import tempfile
import unittest
from unittest.mock import patch

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


    def test_phone_and_npc_runtime(self):
        target = self.db.get_or_create_user(700003)
        message = self.game.phone_add(self.uid, target["vk_id"])
        self.assertIn("Контакт добавлен", message)
        contacts = self.db.phone_contacts(self.uid)
        self.assertEqual(len(contacts), 1)
        self.assertEqual(contacts[0]["contact_id"], target["vk_id"])
        self.assertEqual(contacts[0]["nickname"], target["nickname"])

        message = self.game.phone_remove(self.uid, target["vk_id"])
        self.assertIn("Контакт удалён", message)
        self.assertEqual(self.db.phone_contacts(self.uid), [])

        self.assertIn("NPC ГОРОДА", self.game.npc_menu(self.uid))
        self.assertIn("Дилер", self.game.npc(self.uid, "dealer"))

    def test_npc_actions_cooldowns_and_car_tuning(self):
        uid = self.db.get_or_create_user(700004)["id"]
        self.db.add_money(uid, 500_000)
        self.assertIn("успеш", self.db.buy_car(uid, "Falcon Compact").lower())

        with patch("game.random.random", return_value=0.1):
            dealer = self.game.npc_action(uid, "dealer")
        self.assertIn("СДЕЛКА УДАЛАСЬ", dealer)
        self.assertIn("Вернись через", self.game.npc_action(uid, "dealer"))

        with patch("game.random.random", return_value=0.1):
            fixer = self.game.npc_action(uid, "fixer")
        self.assertIn("ЗАКАЗ ВЫПОЛНЕН", fixer)

        before = self.db.cars(uid)[0]["speed"]
        tune = self.game.npc_action(uid, "mechanic")
        after = self.db.cars(uid)[0]["speed"]
        self.assertIn("ТЮНИНГ ЗАВЕРШЁН", tune)
        self.assertEqual(after, min(120, before + 5))

        self.db.status_change(uid, heat=20)
        tip = self.game.npc_action(uid, "informant")
        self.assertIn("СЛУХИ ИНФОРМАТОРА", tip)
        self.assertEqual(self.db.status(uid)["heat"], 8)

    def test_auxiliary_schema_exists(self):
        expected = {
            "mission_progress", "sms_task_progress", "sms_messages",
            "story_progress", "tutorial_progress", "player_status",
            "city_events", "casino_stats", "phone_contacts", "npc_state", "npc_cooldowns",
        }
        with self.db.connect() as c:
            tables = {
                r[0] for r in c.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
        self.assertTrue(expected.issubset(tables), expected - tables)


    def test_event_participation_is_unique_and_rewarded(self):
        from catalog import EVENTS, active_events
        from v5 import bridge as v5
        self.assertIn("midnight", active_events())
        first = v5.participate_event(self.db, 700001, "midnight")
        self.assertIn("УЧАСТИЕ ЗАСЧИТАНО", first[0])
        history = self.db.event_history(self.uid)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["event_code"], "midnight")
        second = v5.participate_event(self.db, 700001, "midnight")
        self.assertIn("УЖЕ УЧАСТВОВАЛ", second[0])
        self.assertEqual(len(self.db.event_history(self.uid)), 1)
        with self.db.connect() as c:
            row = c.execute(
                "SELECT 1 FROM v5_wardrobe WHERE user_id=? AND category=? AND name=?",
                (self.uid, "🎪 Ивент • Эксклюзивы", "🌙 Ночная маска"),
            ).fetchone()
        self.assertIsNotNone(row)


if __name__=="__main__":
    unittest.main(verbosity=2)
