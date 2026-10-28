import datetime
import json
import unittest

from city_news import NEWS, city_news_feed, daypart_label, city_weather


class FakeDB:
    def __init__(self, values=None):
        self.values = values or {}

    def get_setting(self, key, default=None):
        return self.values.get(key, default)


class CityNewsTests(unittest.TestCase):
    def test_daypart_changes_with_hour(self):
        self.assertEqual(daypart_label(8), "УТРО")
        self.assertEqual(daypart_label(14), "ДЕНЬ")
        self.assertEqual(daypart_label(19), "ВЕЧЕР")
        self.assertEqual(daypart_label(23), "НОЧЬ")

    def test_feed_contains_multiple_headlines_and_bodies(self):
        now = datetime.datetime(2026, 10, 28, 8, tzinfo=datetime.timezone.utc)
        feed = city_news_feed(now, count=3)
        self.assertGreaterEqual(len([line for line in feed if line]), 6)

    def test_feed_changes_by_daypart(self):
        morning = datetime.datetime(2026, 10, 28, 8, tzinfo=datetime.timezone.utc)
        night = datetime.datetime(2026, 10, 28, 23, tzinfo=datetime.timezone.utc)
        self.assertNotEqual(city_news_feed(morning), city_news_feed(night))

    def test_weather_is_stable_for_same_three_hour_block(self):
        first = datetime.datetime(2026, 10, 28, 8, 10, tzinfo=datetime.timezone.utc)
        second = datetime.datetime(2026, 10, 28, 8, 55, tzinfo=datetime.timezone.utc)
        self.assertEqual(city_weather(first), city_weather(second))

    def test_weather_changes_between_blocks_or_seasons(self):
        morning = datetime.datetime(2026, 10, 28, 8, tzinfo=datetime.timezone.utc)
        winter = datetime.datetime(2026, 12, 28, 8, tzinfo=datetime.timezone.utc)
        self.assertNotEqual(city_weather(morning)["period"], city_weather(winter)["period"])
        self.assertTrue(city_weather(morning)["title"])
        self.assertTrue(city_weather(morning)["description"])

    def test_all_dayparts_have_varied_stories(self):
        self.assertTrue(all(len(stories) >= 4 for stories in NEWS.values()))

    def test_custom_admin_news_is_included(self):
        now = datetime.datetime(2026, 10, 28, 8, tzinfo=datetime.timezone.utc)
        db = FakeDB({"city_news_custom:morning": json.dumps([{"title": "CUSTOM ALERT", "body": "A custom city report."}])})
        feed = city_news_feed(now, count=10, db=db)
        self.assertIn("CUSTOM ALERT", feed)
        self.assertIn("A custom city report.", feed)


if __name__ == "__main__":
    unittest.main()
