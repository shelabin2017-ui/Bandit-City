import json
import unittest
from unittest.mock import patch

import diagnostics
from diagnostics import _read_current_status, _write_current_status


class FakeDB:
    def __init__(self):
        self.values = {}

    def get_setting(self, key, default=None):
        return self.values.get(key, default)

    def set_setting(self, key, value):
        self.values[key] = value


class DiagnosticsStatusTests(unittest.TestCase):
    def test_current_error_report_is_cleared_by_successful_check(self):
        db = FakeDB()
        _write_current_status(db, {"ok": False, "reason": "database_integrity", "detail": "bad"})
        self.assertFalse(_read_current_status(db)["ok"])

        _write_current_status(db, {"ok": True, "repaired": False})
        current = _read_current_status(db)
        self.assertTrue(current["ok"])
        self.assertEqual(current["reason"], "")
        self.assertEqual(current["detail"], "")

    def test_current_status_is_valid_json(self):
        db = FakeDB()
        _write_current_status(db, {"ok": False, "reason": "test_issue", "detail": "test"})
        status = json.loads(db.values["diagnostics_current_status"])
        self.assertIn("checked_at", status)
        self.assertEqual(status["reason"], "test_issue")

    def test_worker_clears_stale_error_after_recovery(self):
        db = FakeDB()
        failure = {"ok": False, "repaired": False, "reason": "database_integrity", "detail": "old failure"}
        success = {"ok": True, "repaired": False, "tables": 20}
        with patch.object(diagnostics, "run_diagnostics", side_effect=[failure, success]), \
             patch.object(diagnostics.time, "sleep", side_effect=[None, RuntimeError("stop worker")]):
            with self.assertRaisesRegex(RuntimeError, "stop worker"):
                diagnostics.diagnostics_worker(db, interval_seconds=30)

        current = _read_current_status(db)
        self.assertTrue(current["ok"])
        self.assertEqual(current["reason"], "")
        self.assertEqual(current["detail"], "")


if __name__ == "__main__":
    unittest.main()
