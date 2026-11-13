import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from argparse import Namespace
from contextlib import closing
from unittest.mock import patch


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import cli
from token_dashboard.dev_reload import _child_args


class CliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.proj = os.path.join(self.tmp, "projects")
        os.makedirs(os.path.join(self.proj, "demo"))
        with open(os.path.join(self.proj, "demo", "s.jsonl"), "w", encoding="utf-8") as f:
            f.write('{"type":"user","uuid":"u1","sessionId":"s1","timestamp":"2026-04-19T00:00:00Z","isSidechain":false,"message":{"role":"user","content":"hi"}}\n')
            f.write('{"type":"assistant","uuid":"a1","parentUuid":"u1","sessionId":"s1","timestamp":"2026-04-19T00:00:01Z","isSidechain":false,"message":{"model":"claude-haiku-4-5","usage":{"input_tokens":1,"output_tokens":1}}}\n')
        self.db = os.path.join(self.tmp, "t.db")
        self.codex = os.path.join(self.tmp, "codex-sessions")
        os.makedirs(self.codex)

    def _run(self, *args):
        env = {**os.environ, "TOKEN_DASHBOARD_DB": self.db, "CODEX_SESSIONS_DIR": self.codex}
        return subprocess.run(
            [sys.executable, "cli.py", *args],
            cwd=ROOT, env=env, capture_output=True, text=True,
        )

    def test_scan_then_today(self):
        r1 = self._run("scan", "--projects-dir", self.proj)
        self.assertEqual(r1.returncode, 0, r1.stderr)
        self.assertIn("scanned", r1.stdout)
        r2 = self._run("today")
        self.assertEqual(r2.returncode, 0, r2.stderr)
        self.assertIn("Token Dashboard", r2.stdout)

    def test_stats(self):
        self._run("scan", "--projects-dir", self.proj)
        r = self._run("stats")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("all time", r.stdout)

    def test_rebuild_removes_deleted_session_from_cache(self):
        self._run("scan", "--projects-dir", self.proj)
        os.remove(os.path.join(self.proj, "demo", "s.jsonl"))
        with patch("token_dashboard.server.run"):
            with patch.object(sys, "argv", [
                "cli.py", "dashboard", "--rebuild-db", "--no-open",
                "--projects-dir", self.proj, "--codex-dir", self.codex, "--db", self.db,
            ]):
                cli.main()
        with closing(sqlite3.connect(self.db)) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM files").fetchone()[0], 0)

    def test_rebuild_failure_preserves_old_cache(self):
        self._run("scan", "--projects-dir", self.proj)
        with patch.object(cli, "scan_codex_dir", side_effect=RuntimeError("scan failed")):
            with self.assertRaisesRegex(RuntimeError, "scan failed"):
                cli._rebuild_db(self.db, self.proj, self.codex)
        with closing(sqlite3.connect(self.db)) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0], 2)
        self.assertFalse(any(".rebuild-" in name for name in os.listdir(self.tmp)))

    def test_rebuild_rejects_missing_directory_with_cached_data(self):
        self._run("scan", "--projects-dir", self.proj)
        os.remove(os.path.join(self.proj, "demo", "s.jsonl"))
        os.rmdir(os.path.join(self.proj, "demo"))
        os.rmdir(self.proj)
        with self.assertRaisesRegex(FileNotFoundError, "claude session directory is missing"):
            cli._rebuild_db(self.db, self.proj, self.codex)
        with closing(sqlite3.connect(self.db)) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0], 2)

    def test_dashboard_lock_rejects_second_process(self):
        with cli._dashboard_lock(self.db):
            with self.assertRaisesRegex(RuntimeError, "Another dashboard"):
                with cli._dashboard_lock(self.db):
                    pass

    def test_rebuild_and_no_scan_are_mutually_exclusive(self):
        r = self._run("dashboard", "--rebuild-db", "--no-scan", "--no-open")
        self.assertEqual(r.returncode, 2)
        self.assertIn("not allowed with argument", r.stderr)

    def test_reload_runs_supervisor_without_starting_server(self):
        with patch("token_dashboard.dev_reload.run_reloader") as reloader:
            with patch.object(sys, "argv", ["cli.py", "dashboard", "--reload", "--no-open"]):
                cli.main()
        reloader.assert_called_once()

    def test_reload_rebuilds_only_once_and_opens_browser_once(self):
        args = Namespace(db=self.db, projects_dir=self.proj, codex_dir=self.codex,
                         source="codex", no_scan=False, rebuild_db=True, no_open=False)
        first = _child_args(args, first_start=True)
        later = _child_args(args, first_start=False)
        self.assertIn("--rebuild-db", first)
        self.assertNotIn("--no-open", first)
        self.assertNotIn("--rebuild-db", later)
        self.assertIn("--no-open", later)
        self.assertEqual(first[:3], ["dashboard", "--db", self.db])

if __name__ == "__main__":
    unittest.main()
