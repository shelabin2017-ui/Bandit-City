import os
import tempfile
import unittest

from db import Database
from v5.bridge import inventory


class InventoryDisplayTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Database(os.path.join(self.tmp.name, "inventory.db"))
        self.vk_id = 700003
        self.user = self.db.get_or_create_user(self.vk_id)
        with self.db.connect() as c:
            c.executemany(
                "INSERT INTO items(user_id,name,price,bought_at) VALUES(?,?,?,?)",
                [
                    (self.user["id"], "MacBook", 120000, 1),
                    (self.user["id"], "Вода", 3000, 1),
                    (self.user["id"], "Бургер", 12000, 1),
                    (self.user["id"], "Вода", 3000, 2),
                    (self.user["id"], "Подарочный бокс", 200000, 1),
                ],
            )

    def tearDown(self):
        self.tmp.cleanup()

    def test_inventory_groups_categories_counts_duplicates_and_hides_ids(self):
        message, buttons = inventory(self.db, self.vk_id)
        self.assertLess(message.index("🍽️ ЕДА И НАПИТКИ"), message.index("🎁 БОКСЫ"))
        self.assertLess(message.index("🎁 БОКСЫ"), message.index("📦 ПРОЧЕЕ"))
        self.assertIn("Вода ×2", message)
        self.assertNotIn("#", message)
        self.assertIn("🗑 Продать: Вода", str(buttons))
        self.assertIn("🍽 Использовать: Вода", str(buttons))


if __name__ == "__main__":
    unittest.main()
