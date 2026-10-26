import unittest

from v5 import bridge


class ShopCategoryTests(unittest.TestCase):
    def test_food_and_drinks_are_separate_categories(self):
        self.assertEqual(bridge.item_category("🍔 Бургер"), "🍔 Еда")
        self.assertEqual(bridge.item_category("🥪 Сэндвич"), "🍔 Еда")
        self.assertEqual(bridge.item_category("💧 Вода"), "🥤 Напитки")
        self.assertEqual(bridge.item_category("⚡ Энергетик"), "🥤 Напитки")
        self.assertNotEqual(bridge.item_category("🍔 Бургер"), bridge.item_category("💧 Вода"))

    def test_medical_tools_equipment_electronics_and_boxes(self):
        expected = {
            "🩹 Аптечка": "💊 Медицина",
            "🧰 Набор отмычек": "🧰 Инструменты",
            "🧰 Инструменты": "🧰 Инструменты",
            "🛡 Бронежилет": "🛡️ Снаряжение",
            "🎭 Маска": "🛡️ Снаряжение",
            "💻 MacBook": "📱 Электроника",
            "📱 Burner Phone": "📱 Электроника",
            "🎁 Подарочный бокс": "🎁 Боксы",
            "🍀 Счастливый жетон": "📦 Прочее",
        }
        for item, category in expected.items():
            with self.subTest(item=item):
                self.assertEqual(bridge.item_category(item), category)

    def test_shop_category_contains_only_matching_items(self):
        text, buttons = bridge.item_shop("🍔 Еда")
        self.assertIn("Бургер", text)
        self.assertIn("Сэндвич", text)
        self.assertNotIn("Энергетик", text)
        self.assertNotIn("Вода", text)
        flattened = [label for row in buttons for label in row]
        self.assertTrue(any(label == "🛒 x1 🍔 Бургер" for label in flattened))

    def test_category_menu_has_separate_food_and_drink_buttons(self):
        text, buttons = bridge.item_shop()
        flattened = [label for row in buttons for label in row]
        self.assertIn("🍔 Еда", flattened)
        self.assertIn("🥤 Напитки", flattened)
        self.assertIn("Выбери категорию", text)


if __name__ == "__main__":
    unittest.main()
