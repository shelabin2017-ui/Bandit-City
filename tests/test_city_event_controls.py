import os
import tempfile
import unittest
import datetime
from unittest.mock import patch

from catalog import EVENTS, active_events as catalog_active_events
from db import Database
from event_announcer import active_events, event_overrides, _announcement


class CityEventControlTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Database(os.path.join(self.tmp.name, "bandit.db"))

    def tearDown(self):
        self.tmp.cleanup()

    def test_admin_override_can_force_future_event_on(self):
        now = datetime.datetime(2026, 10, 28, tzinfo=datetime.timezone.utc)
        self.assertNotIn("prime", catalog_active_events(now))
        self.db.set_setting("city_event:prime", "on")
        self.assertIn("prime", active_events(self.db, now))

    def test_admin_override_can_stop_scheduled_event(self):
        now = datetime.datetime(2026, 10, 28, tzinfo=datetime.timezone.utc)
        self.assertIn("nightfall", catalog_active_events(now))
        self.db.set_setting("city_event:nightfall", "off")
        self.assertNotIn("nightfall", active_events(self.db, now))

    def test_prime_schedule_and_reward_are_not_mixed_with_nightfall(self):
        prime = EVENTS["prime"]
        nightfall = EVENTS["nightfall"]
        self.assertEqual(prime["drops"], ["prime_hair"])
        self.assertEqual(nightfall["drops"], ["nightfall_mask"])
        self.assertEqual(prime["start_at"], "2026-11-10T00:00:00Z")
        self.assertEqual(prime["end_at"], "2026-11-24T00:00:00Z")


    def test_admin_event_alert_retries_after_send_failure(self):
        class FakeMessages:
            def __init__(self, fail):
                self.fail = fail
                self.sent = []

            def send(self, **kwargs):
                self.sent.append(kwargs)
                if self.fail:
                    self.fail = False
                    raise RuntimeError("temporary VK error")
                return 1

        class FakeVK:
            def __init__(self, fail):
                self.messages = FakeMessages(fail)

        event = {"title": "💎 BANDIT PRIME", "start_at": "2026-11-10T00:00:00Z"}
        vk = FakeVK(True)
        with patch("event_announcer.announce_active_events", return_value={}), \
             patch("event_announcer.active_events", return_value={"prime": event}), \
             patch("event_announcer.time.sleep", side_effect=StopIteration):
            with self.assertRaises(StopIteration):
                from event_announcer import event_announcer_worker
                event_announcer_worker(self.db, vk, 1, interval_seconds=60, admin_ids={12345})
        key = "city_event_admin_notified:prime:2026-11-10T00:00:00Z:12345"
        self.assertIsNone(self.db.get_setting(key))
        vk.messages.fail = False
        with patch("event_announcer.announce_active_events", return_value={}), \
             patch("event_announcer.active_events", return_value={"prime": event}), \
             patch("event_announcer.time.sleep", side_effect=StopIteration):
            with self.assertRaises(StopIteration):
                event_announcer_worker(self.db, vk, 1, interval_seconds=60, admin_ids={12345})
        self.assertEqual(self.db.get_setting(key), "1")
        self.assertEqual(len(vk.messages.sent), 2)

    def test_daily_event_copy_changes_by_date(self):
        event = EVENTS["prime"]
        first = datetime.datetime(2026, 11, 11, tzinfo=datetime.timezone.utc)
        second = datetime.datetime(2026, 11, 12, tzinfo=datetime.timezone.utc)
        self.assertNotEqual(
            _announcement("prime", event, "daily", first),
            _announcement("prime", event, "daily", second),
        )


if __name__ == "__main__":
    unittest.main()
