import os
import tempfile
import unittest

from db import Database
from diagnostics import REQUIRED_TABLES, run_diagnostics


class DiagnosticsTests(unittest.TestCase):
    def setUp(self):
        handle, self.path = tempfile.mkstemp(suffix=".db")
        os.close(handle)
        self.db = Database(self.path)

    def tearDown(self):
        for suffix in ("", "-wal", "-shm"):
            try:
                os.remove(self.path + suffix)
            except FileNotFoundError:
                pass

    def test_healthy_database_passes(self):
        result = run_diagnostics(self.db)
        self.assertTrue(result["ok"])
        self.assertFalse(result["repaired"])

    def test_missing_core_table_is_repaired_additively(self):
        with self.db.connect() as conn:
            conn.execute("DROP TABLE npc_state")
        result = run_diagnostics(self.db)
        self.assertTrue(result["ok"])
        self.assertTrue(result["repaired"])
        with self.db.connect() as conn:
            tables = {row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()}
        self.assertTrue(REQUIRED_TABLES.issubset(tables))


if __name__ == "__main__":
    unittest.main(verbosity=2)
