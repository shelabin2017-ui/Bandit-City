import unittest

from memorial import MEMORIAL_MESSAGE, MEMORIAL_RELEASE_ID


class MemorialTests(unittest.TestCase):
    def test_memorial_message_has_confirmed_details_and_minute_of_silence(self):
        self.assertEqual(MEMORIAL_RELEASE_ID, "memorial-stas-2026-10-28")
        self.assertIn("Стаса", MEMORIAL_MESSAGE)
        self.assertIn("23 февраля 2003 года", MEMORIAL_MESSAGE)
        self.assertIn("18 октября", MEMORIAL_MESSAGE)
        self.assertIn("минуту", MEMORIAL_MESSAGE.lower())
        self.assertIn("официально подтверждена гибель", MEMORIAL_MESSAGE.lower())


if __name__ == "__main__":
    unittest.main()
