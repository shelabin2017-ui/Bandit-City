import os
import tempfile
import unittest

from db import Database
from release import announce_release


class FakeMessages:
    def __init__(self, denied=None, fail_once=None):
        self.sent = []
        self.denied = set(denied or ())
        self.fail_once = set(fail_once or ())

    def isMessagesFromGroupAllowed(self, group_id, user_id):
        return {"is_allowed": 0 if user_id in self.denied else 1}

    def send(self, **payload):
        uid = payload["user_id"]
        if uid in self.fail_once:
            self.fail_once.remove(uid)
            raise RuntimeError("temporary failure")
        self.sent.append(payload)
        return len(self.sent)


class FakeVK:
    def __init__(self, **kwargs):
        self.messages = FakeMessages(**kwargs)


class ReleaseBroadcastTests(unittest.TestCase):
    def setUp(self):
        handle, self.path = tempfile.mkstemp(suffix=".db")
        os.close(handle)
        self.db = Database(self.path)
        for vk_id in (101, 102, 103):
            self.db.get_or_create_user(vk_id)
        self.vk = FakeVK(denied={102})

    def tearDown(self):
        for suffix in ("", "-wal", "-shm"):
            try:
                os.remove(self.path + suffix)
            except FileNotFoundError:
                pass

    def test_release_sent_once_and_denied_player_skipped(self):
        first = announce_release(self.db, self.vk, 77, "2026-10-10", "Тестовое обновление", 0)
        self.assertEqual(first["sent"], 2)
        self.assertEqual(first["skipped"], 1)
        self.assertEqual(len(self.vk.messages.sent), 2)

        second = announce_release(self.db, self.vk, 77, "2026-10-10", "Тестовое обновление", 0)
        self.assertTrue(second["already_done"])
        self.assertEqual(len(self.vk.messages.sent), 2)

    def test_failed_recipient_resumes_without_resending_successes(self):
        self.vk = FakeVK(fail_once={101})
        first = announce_release(self.db, self.vk, 77, "2026-10-11", "Тестовое обновление", 0)
        self.assertEqual(first["failed"], 1)
        self.assertEqual(len(self.vk.messages.sent), 2)

        second = announce_release(self.db, self.vk, 77, "2026-10-11", "Тестовое обновление", 0)
        self.assertEqual(len(self.vk.messages.sent), 3)
        self.assertTrue(second["already_done"] is False)
        self.assertEqual(second["failed"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
