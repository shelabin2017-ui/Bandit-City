import unittest

from keyboard_layout import normalize_rows, paginate_rows


class KeyboardLayoutTests(unittest.TestCase):
    def test_normalizes_long_rows_into_two_button_rows(self):
        result = normalize_rows([["A", "B", "C", "D", "E"]])
        self.assertEqual(result, [["A", "B"], ["C", "D"], ["E"]])

    def test_short_keyboard_is_not_paginated(self):
        rows = [["A", "B"], ["C"], ["🏙️ Главное меню"]]
        self.assertEqual(paginate_rows(rows), [rows])

    def test_long_keyboard_keeps_every_action_and_footer(self):
        rows = [[f"Раздел {i}"] for i in range(1, 25)] + [["🏙️ Главное меню"]]
        pages = paginate_rows(rows)
        self.assertGreater(len(pages), 1)
        self.assertTrue(all(len(page) <= 10 for page in pages))
        self.assertTrue(all(page[-1] == ["🏙️ Главное меню"] for page in pages))
        flattened = [row[0] for page in pages for row in page if row and row[0] not in ("⬅️ Назад меню", "➡️ Далее меню")]
        for i in range(1, 25):
            self.assertEqual(flattened.count(f"Раздел {i}"), 1)

    def test_every_page_has_correct_navigation_direction(self):
        pages = paginate_rows([[str(i)] for i in range(24)] + [["🏙️ Главное меню"]])
        self.assertNotIn("⬅️ Назад меню", [x for row in pages[0] for x in row])
        self.assertIn("➡️ Далее меню", [x for row in pages[0] for x in row])
        self.assertIn("⬅️ Назад меню", [x for row in pages[1] for x in row])
        self.assertNotIn("➡️ Далее меню", [x for row in pages[-1] for x in row])


if __name__ == "__main__":
    unittest.main(verbosity=2)
