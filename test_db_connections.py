import os
import sqlite3
import tempfile
import unittest

from db import Database


class DatabaseConnectionLifecycleTests(unittest.TestCase):
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

    def test_context_managed_connection_is_closed_after_success(self):
        with self.db.connect() as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS connection_probe(value INTEGER)")
            conn.execute("INSERT INTO connection_probe(value) VALUES(7)")
        with self.assertRaises(sqlite3.ProgrammingError):
            conn.execute("SELECT 1")

        with self.db.connect() as check:
            self.assertEqual(
                check.execute("SELECT value FROM connection_probe").fetchone()[0],
                7,
            )

    def test_context_managed_connection_rolls_back_and_closes_on_error(self):
        with self.assertRaises(RuntimeError):
            with self.db.connect() as conn:
                conn.execute("INSERT INTO settings(key,value) VALUES('probe','bad')")
                raise RuntimeError("intentional rollback test")
        with self.assertRaises(sqlite3.ProgrammingError):
            conn.execute("SELECT 1")

        with self.db.connect() as check:
            self.assertIsNone(
                check.execute("SELECT value FROM settings WHERE key='probe'").fetchone()
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
