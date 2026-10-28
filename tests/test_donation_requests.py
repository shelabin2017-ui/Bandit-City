import os
import tempfile
import unittest

from db import Database
from donation import SERVICES, create_request, get_request, list_requests, set_status, set_price


class DonationRequestTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Database(os.path.join(self.tmp.name, "test.db"))
        self.user = self.db.get_or_create_user(700001)

    def tearDown(self):
        self.tmp.cleanup()

    def test_request_is_saved_and_status_changes(self):
        label = "💵 500 000 игровой валюты — 99 ₽ (скидка 23%)"
        request_id, message = create_request(self.db, self.user, label)
        self.assertIsNotNone(request_id)
        self.assertIn("Альфа-Банк", message)
        self.assertIn("проверена вручную", message)
        request = get_request(self.db, request_id)
        self.assertEqual(request["service_code"], SERVICES[label][0])
        self.assertEqual(request["status"], "new")
        self.assertFalse(set_status(self.db, request_id, "paid", 700001))
        self.assertTrue(set_status(self.db, request_id, "awaiting", 700001))
        self.assertTrue(set_status(self.db, request_id, "paid", 700001))
        self.assertTrue(set_status(self.db, request_id, "granted", 700001))
        self.assertTrue(set_status(self.db, request_id, "completed", 700001))
        self.assertEqual(get_request(self.db, request_id)["status"], "completed")
        self.assertEqual(len(list_requests(self.db)), 0)

    def test_unknown_service_and_invalid_status_are_rejected(self):
        request_id, message = create_request(self.db, self.user, "unknown")
        self.assertIsNone(request_id)
        self.assertIn("Неизвестная услуга", message)
        self.assertFalse(set_status(self.db, 1, "made_up", 700001))
        label = "💵 500 000 игровой валюты — 99 ₽ (скидка 23%)"
        request_id, _ = create_request(self.db, self.user, label)
        self.assertTrue(set_status(self.db, request_id, "cancelled", 700001))
        self.assertFalse(set_status(self.db, request_id, "awaiting", 700001))
        self.assertEqual(list_requests(self.db), [])


    def test_custom_order_waits_for_admin_price(self):
        label = "📝 Индивидуальный заказ"
        request_id, message = create_request(self.db, self.user, label, details="Нужен набор для нового игрока")
        self.assertIsNotNone(request_id)
        self.assertIn("не является счётом на оплату", message)
        self.assertNotIn("Альфа-Банк", message)
        request = get_request(self.db, request_id)
        self.assertEqual(request["service_code"], "custom")
        self.assertEqual(request["price_rub"], 0)
        self.assertTrue(set_price(self.db, request_id, 299, 700001))
        self.assertEqual(get_request(self.db, request_id)["price_rub"], 299)
        self.assertEqual(get_request(self.db, request_id)["status"], "quoted")
        self.assertFalse(set_status(self.db, request_id, "awaiting", 700001))
        self.assertTrue(set_status(self.db, request_id, "new", 700001))
        self.assertFalse(set_price(self.db, request_id, 0, 700001))
        self.assertFalse(set_price(self.db, request_id, 100001, 700001))
        self.assertTrue(set_status(self.db, request_id, "awaiting", 700001))
        self.assertTrue(set_status(self.db, request_id, "paid", 700001))
        self.assertTrue(set_status(self.db, request_id, "granted", 700001))
        self.assertTrue(set_status(self.db, request_id, "completed", 700001))
        self.assertFalse(set_price(self.db, request_id, 499, 700001))
        self.assertEqual(list_requests(self.db), [])


if __name__ == "__main__":
    unittest.main()
