import os
import sqlite3
import tempfile
import unittest
from token_dashboard.db import init_db, connect


class InitDbTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmp, "test.db")

    def test_init_creates_expected_tables(self):
        init_db(self.db_path)
        with sqlite3.connect(self.db_path) as c:
            tables = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        expected = {"files", "messages", "tool_calls", "codex_skill_uses"}
        self.assertTrue(expected.issubset(tables), f"Missing: {expected - tables}")

    def test_init_is_idempotent(self):
        init_db(self.db_path)
        init_db(self.db_path)

    def test_connect_returns_row_factory(self):
        init_db(self.db_path)
        with connect(self.db_path) as c:
            r = c.execute("SELECT 1 AS one").fetchone()
        self.assertEqual(r["one"], 1)

    def test_existing_claude_rows_get_source_fields(self):
        with sqlite3.connect(self.db_path) as c:
            c.execute("""CREATE TABLE messages (
                uuid TEXT PRIMARY KEY, session_id TEXT, project_slug TEXT,
                timestamp TEXT, model TEXT, type TEXT, message_id TEXT
            )""")
            c.execute("INSERT INTO messages VALUES ('u','s','p','2026-01-01','claude-test','user',NULL)")
        init_db(self.db_path)
        with sqlite3.connect(self.db_path) as c:
            row = c.execute("SELECT source, cache_write_tokens, reasoning_output_tokens FROM messages WHERE uuid='u'").fetchone()
        self.assertEqual(row, ("claude", 0, 0))


if __name__ == "__main__":
    unittest.main()
