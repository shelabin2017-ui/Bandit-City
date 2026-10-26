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


class InventoryButtonTests(unittest.TestCase):
    class FakeDB:
        def get_or_create_user(self, vk_id):
            return {"id": 7}

        def items(self, user_id):
            return [
                {"id": 5, "name": "🎁 Подарочный бокс", "price": 200000},
                {"id": 4, "name": "🍔 Бургер", "price": 12000},
                {"id": 3, "name": "🍔 Бургер", "price": 12000},
                {"id": 2, "name": "💧 Вода", "price": 3000},
            ]

    def test_inventory_actions_hide_database_ids_and_deduplicate(self):
        text, buttons = bridge.inventory(self.FakeDB(), 123)
        labels = [label for row in buttons for label in row]
        self.assertTrue(any(label == "🗑 Продать: 🍔 Бургер" for label in labels))
        self.assertIn("🎁 Открыть бокс", labels)
        self.assertIn("🍽 Использовать: 🍔 Бургер", labels)
        self.assertNotIn("🗑 Продать #5", labels)
        self.assertNotIn("🎁 Открыть #5", labels)
        self.assertFalse(any("#" in label for label in labels))
        self.assertEqual(labels.count("🗑 Продать: 🍔 Бургер"), 1)
        self.assertEqual(labels.count("🍽 Использовать: 🍔 Бургер"), 1)


if __name__ == "__main__":
    unittest.main()
