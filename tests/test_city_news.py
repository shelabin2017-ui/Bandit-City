import datetime
import unittest

from city_news import NEWS, city_news_feed, daypart_label


class CityNewsTests(unittest.TestCase):
    def test_daypart_changes_with_hour(self):
        self.assertEqual(daypart_label(8), "УТРО")
        self.assertEqual(daypart_label(14), "ДЕНЬ")
        self.assertEqual(daypart_label(19), "ВЕЧЕР")
        self.assertEqual(daypart_label(23), "НОЧЬ")

    def test_feed_contains_multiple_headlines_and_bodies(self):
        now = datetime.datetime(2026, 10, 28, 8, tzinfo=datetime.timezone.utc)
        feed = city_news_feed(now, count=3)
        self.assertGreaterEqual(sum(1 for line in feed if line.startswith(("🐈", "🚧", "☕", "🧳", "🐕"))), 1)
        self.assertGreaterEqual(len([line for line in feed if line]), 6)

    def test_feed_changes_by_daypart(self):
        morning = datetime.datetime(2026, 10, 28, 8, tzinfo=datetime.timezone.utc)
        night = datetime.datetime(2026, 10, 28, 23, tzinfo=datetime.timezone.utc)
        self.assertNotEqual(city_news_feed(morning), city_news_feed(night))

    def test_all_dayparts_have_varied_stories(self):
        self.assertTrue(all(len(stories) >= 4 for stories in NEWS.values()))


if __name__ == "__main__":
    unittest.main()
