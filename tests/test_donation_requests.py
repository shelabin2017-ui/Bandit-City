import os
import tempfile
import unittest

from db import Database
from donation import SERVICES, create_request, get_request, list_requests, set_status


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
        self.assertTrue(set_status(self.db, request_id, "paid", 700001))
        self.assertEqual(get_request(self.db, request_id)["status"], "paid")
        self.assertEqual(len(list_requests(self.db)), 1)

    def test_unknown_service_and_invalid_status_are_rejected(self):
        request_id, message = create_request(self.db, self.user, "unknown")
        self.assertIsNone(request_id)
        self.assertIn("Неизвестная услуга", message)
        self.assertFalse(set_status(self.db, 1, "made_up", 700001))


if __name__ == "__main__":
    unittest.main()
