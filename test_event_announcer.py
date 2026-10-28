import datetime
import os
import tempfile
import unittest
from unittest.mock import patch

from db import Database
from event_announcer import announce_active_events


class FakeMessages:
    def __init__(self):
        self.sent = []

    def isMessagesFromGroupAllowed(self, group_id, user_id):
        return {"is_allowed": 1}

    def send(self, **payload):
        self.sent.append(payload)
        return len(self.sent)


class FakeVK:
    def __init__(self):
        self.messages = FakeMessages()


class EventAnnouncementTests(unittest.TestCase):
    def setUp(self):
        handle, self.path = tempfile.mkstemp(suffix=".db")
        os.close(handle)
        self.db = Database(self.path)
        self.db.get_or_create_user(910001)
        self.vk = FakeVK()

    def tearDown(self):
        for suffix in ("", "-wal", "-shm"):
            try:
                os.remove(self.path + suffix)
            except FileNotFoundError:
                pass

    def test_active_event_is_announced_once_across_rechecks(self):
        events = {
            "test_event": {
                "title": "🌙 ТЕСТОВОЕ СОБЫТИЕ",
                "description": "Проверка автоматического оповещения.",
                "start_at": "2026-10-20T00:00:00Z",
                "end_at": "2026-11-01T00:00:00Z",
                "goal_label": "Выполни тест",
            }
        }
        start_day = datetime.datetime(2026, 10, 20, 0, 0, tzinfo=datetime.timezone.utc)
        with patch("catalog.EVENTS", events):
            first = announce_active_events(self.db, self.vk, 77, now=start_day, delay_seconds=0)
            second = announce_active_events(self.db, self.vk, 77, now=start_day, delay_seconds=0)
        self.assertEqual(len(self.vk.messages.sent), 1)
        self.assertIn("ТЕСТОВОЕ СОБЫТИЕ", self.vk.messages.sent[0]["message"])
        self.assertIn("Выполни тест", self.vk.messages.sent[0]["message"])
        self.assertEqual(first["test_event"]["sent"], 1)
        self.assertTrue(second["test_event"]["already_done"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
