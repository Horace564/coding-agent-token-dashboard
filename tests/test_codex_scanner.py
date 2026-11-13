import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from token_dashboard.codex_scanner import scan_codex_dir
from token_dashboard.db import (
    expensive_prompts, init_db, model_breakdown, overview_totals,
    project_summary, recent_sessions, session_turns,
)


def _line(kind, timestamp, payload):
    return json.dumps({"type": kind, "timestamp": timestamp, "payload": payload}) + "\n"


def _usage(input_tokens, cached, output):
    return {
        "input_tokens": input_tokens, "cached_input_tokens": cached,
        "cache_write_input_tokens": 0, "output_tokens": output,
        "reasoning_output_tokens": 2, "total_tokens": input_tokens + output,
    }


class CodexScannerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "sessions"
        self.root.mkdir()
        self.path = self.root / "rollout.jsonl"
        self.db = Path(self.tmp.name) / "usage.db"
        init_db(self.db)

    def _write(self, second=True):
        records = [
            _line("session_meta", "2026-11-01T00:00:00Z", {"id": "session-1", "cwd": "/work/demo"}),
            _line("turn_context", "2026-11-01T00:00:01Z", {"turn_id": "turn-1", "model": "gpt-test", "cwd": "/work/demo"}),
            _line("event_msg", "2026-11-01T00:00:02Z", {"type": "token_count", "info": {
                "last_token_usage": _usage(100, 40, 10), "total_token_usage": _usage(100, 40, 10),
            }}),
            _line("token_usage_record", "2026-11-01T00:00:02Z", {
                "turn_id": "turn-1", "response_id": "response-1", "usage": _usage(100, 40, 10),
            }),
        ]
        if second:
            records.append(_line("token_usage_record", "2026-11-01T00:00:03Z", {
                "turn_id": "turn-1", "response_id": "response-2", "usage": _usage(50, 20, 5),
            }))
        self.path.write_text("".join(records), encoding="utf-8")
        os.utime(self.path, None)

    def test_import_prefers_response_usage_and_normalizes_cache(self):
        self._write()
        result = scan_codex_dir(self.root, self.db)
        self.assertEqual(result, {"files": 1, "messages": 2, "turns": 1})
        totals = overview_totals(self.db, source="codex")
        self.assertEqual(totals["sessions"], 1)
        self.assertEqual(totals["turns"], 1)
        self.assertEqual(totals["input_tokens"], 90)
        self.assertEqual(totals["cache_read_tokens"], 60)
        self.assertEqual(totals["output_tokens"], 15)
        self.assertEqual(totals["reasoning_output_tokens"], 4)
        models = model_breakdown(self.db, source="codex")
        self.assertEqual(models[0]["model"], "gpt-test")
        self.assertEqual(project_summary(self.db, source="claude"), [])

    def test_prompts_are_imported_and_multiple_responses_are_one_prompt(self):
        self._write()
        records = self.path.read_text(encoding="utf-8").splitlines(keepends=True)
        records.insert(1, _line("event_msg", "2026-11-01T00:00:00Z", {
            "type": "task_started", "turn_id": "turn-1",
        }))
        records.insert(2, _line("response_item", "2026-11-01T00:00:01Z", {
            "type": "message", "role": "user", "content": [
                {"type": "input_text", "text": "Please fix the dashboard"},
            ],
        }))
        self.path.write_text("".join(records), encoding="utf-8")
        scan_codex_dir(self.root, self.db)
        prompts = expensive_prompts(self.db, source="codex")
        self.assertEqual(len(prompts), 1)
        self.assertEqual(prompts[0]["prompt_text"], "Please fix the dashboard")
        self.assertEqual(prompts[0]["prompt_chars"], 24)
        self.assertEqual(prompts[0]["billable_tokens"], 105)
        self.assertEqual(prompts[0]["cache_read_tokens"], 60)
        self.assertEqual(prompts[0]["total_tokens"], 165)
        self.assertEqual(prompts[0]["model_calls"], 2)
        turns = session_turns(self.db, "codex:session-1")
        self.assertEqual(turns[0]["prompt_text"], "Please fix the dashboard")

    def test_session_name_updates_without_rollout_rescan(self):
        self._write()
        index = self.root.parent / "session_index.jsonl"
        index.write_text(json.dumps({"id": "session-1", "thread_name": "Original name"}) + "\n", encoding="utf-8")
        scan_codex_dir(self.root, self.db)
        sessions = recent_sessions(self.db, source="codex")
        self.assertEqual(sessions[0]["session_title"], "Original name")
        index.write_text(json.dumps({"id": "session-1", "thread_name": "Renamed session"}) + "\n", encoding="utf-8")
        self.assertEqual(scan_codex_dir(self.root, self.db)["files"], 0)
        self.assertEqual(recent_sessions(self.db, source="codex")[0]["session_title"], "Renamed session")

    def test_session_name_uses_state_database_when_index_is_missing(self):
        self._write()
        state = self.root.parent / "state_5.sqlite"
        conn = sqlite3.connect(state)
        try:
            conn.execute("CREATE TABLE threads (id TEXT, title TEXT, name TEXT)")
            conn.execute("INSERT INTO threads VALUES ('session-1', 'Automatic title', 'Custom name')")
            conn.commit()
        finally:
            conn.close()
        scan_codex_dir(self.root, self.db)
        self.assertEqual(recent_sessions(self.db, source="codex")[0]["session_title"], "Custom name")

    def test_prompt_without_usage_still_appears(self):
        self.path.write_text("".join([
            _line("session_meta", "2026-11-01T00:00:00Z", {"id": "no-usage", "cwd": "/work/demo"}),
            _line("event_msg", "2026-11-01T00:00:01Z", {"type": "task_started", "turn_id": "one"}),
            _line("response_item", "2026-11-01T00:00:02Z", {
                "type": "message", "role": "user",
                "content": [{"type": "input_text", "text": "A question"}],
            }),
        ]), encoding="utf-8")
        scan_codex_dir(self.root, self.db)
        prompts = expensive_prompts(self.db, source="codex")
        self.assertEqual(len(prompts), 1)
        self.assertEqual(prompts[0]["billable_tokens"], 0)
        self.assertEqual(recent_sessions(self.db, source="codex")[0]["session_title"], "A question")

    def test_rescan_is_idempotent_and_rewrite_removes_stale_rows(self):
        self._write()
        scan_codex_dir(self.root, self.db)
        self.assertEqual(scan_codex_dir(self.root, self.db)["files"], 0)
        self._write(second=False)
        scan_codex_dir(self.root, self.db)
        conn = sqlite3.connect(self.db)
        try:
            count = conn.execute("SELECT COUNT(*) FROM messages WHERE source='codex' AND type='assistant'").fetchone()[0]
        finally:
            conn.close()
        self.assertEqual(count, 1)
        self.assertEqual(overview_totals(self.db, source="codex")["input_tokens"], 60)

    def test_old_import_is_rebuilt_for_prompt_support(self):
        self._write()
        scan_codex_dir(self.root, self.db)
        conn = sqlite3.connect(self.db)
        try:
            conn.execute("DELETE FROM scanner_state WHERE source='codex'")
            conn.commit()
        finally:
            conn.close()
        self.assertEqual(scan_codex_dir(self.root, self.db)["files"], 1)

    def test_legacy_cumulative_usage_fallback(self):
        self.path.write_text("".join([
            _line("session_meta", "2026-11-01T00:00:00Z", {"id": "old", "cwd": "/work/old"}),
            _line("turn_context", "2026-11-01T00:00:01Z", {"turn_id": "one", "model": "gpt-old"}),
            _line("event_msg", "2026-11-01T00:00:02Z", {"type": "token_count", "info": {
                "total_token_usage": _usage(100, 40, 10),
            }}),
            _line("event_msg", "2026-11-01T00:00:03Z", {"type": "token_count", "info": {
                "total_token_usage": _usage(150, 60, 15),
            }}),
        ]), encoding="utf-8")
        scan_codex_dir(self.root, self.db)
        totals = overview_totals(self.db, source="codex")
        self.assertEqual(totals["input_tokens"], 90)
        self.assertEqual(totals["cache_read_tokens"], 60)
        self.assertEqual(totals["output_tokens"], 15)

    def test_incomplete_final_line_is_imported_after_completion(self):
        prefix = "".join([
            _line("session_meta", "2026-11-01T00:00:00Z", {"id": "live", "cwd": "/work/live"}),
            _line("turn_context", "2026-11-01T00:00:01Z", {"turn_id": "one", "model": "gpt-live"}),
        ])
        usage_line = _line("token_usage_record", "2026-11-01T00:00:02Z", {
            "turn_id": "one", "response_id": "one", "usage": _usage(100, 40, 10),
        })
        self.path.write_text(prefix + usage_line[:-1], encoding="utf-8")
        self.assertEqual(scan_codex_dir(self.root, self.db)["messages"], 0)
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write("\n")
        self.assertEqual(scan_codex_dir(self.root, self.db)["messages"], 1)
        self.assertEqual(overview_totals(self.db, source="codex")["input_tokens"], 60)

    def test_session_activity_links_tool_result_and_compaction_to_responses(self):
        self.path.write_text("".join([
            _line("session_meta", "2026-11-01T00:00:00Z", {"id": "activity", "cwd": "/work/demo"}),
            _line("event_msg", "2026-11-01T00:00:01Z", {"type": "task_started", "turn_id": "turn-1"}),
            _line("turn_context", "2026-11-01T00:00:02Z", {
                "turn_id": "turn-1", "model": "gpt-test", "effort": "high",
            }),
            _line("response_item", "2026-11-01T00:00:03Z", {
                "type": "message", "role": "user",
                "content": [{"type": "input_text", "text": "Inspect the project"}],
            }),
            _line("response_item", "2026-11-01T00:00:04Z", {
                "type": "message", "role": "assistant", "phase": "commentary",
                "content": [{"type": "output_text", "text": "Checking files"}],
            }),
            _line("response_item", "2026-11-01T00:00:05Z", {
                "type": "custom_tool_call", "call_id": "tool-1", "name": "exec",
                "input": "tools.exec_command({cmd: 'rg --files'})",
            }),
            _line("token_usage_record", "2026-11-01T00:00:06Z", {
                "turn_id": "turn-1", "response_id": "response-1", "usage": _usage(100, 40, 10),
            }),
            _line("response_item", "2026-11-01T00:00:07Z", {
                "type": "custom_tool_call_output", "call_id": "tool-1", "output": "file.py",
            }),
            _line("token_usage_record", "2026-11-01T00:00:08Z", {
                "turn_id": "turn-1", "response_id": "response-2", "usage": _usage(50, 20, 5),
            }),
            _line("compacted", "2026-11-01T00:00:09Z", {
                "compaction_response_id": "response-2", "window_number": 2,
            }),
        ]), encoding="utf-8")

        scan_codex_dir(self.root, self.db)
        calls = [row for row in session_turns(self.db, "codex:activity") if row["type"] == "assistant"]
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0]["reasoning_effort"], "high")
        self.assertEqual(calls[0]["message_id"], "response-1")
        first = json.loads(calls[0]["activity_json"])
        self.assertEqual([event["kind"] for event in first], ["message", "tool"])
        self.assertEqual(first[0]["text"], "Checking files")
        self.assertEqual(first[1]["output"], "file.py")
        self.assertEqual(json.loads(calls[0]["tool_calls_json"])[0]["name"], "exec")
        self.assertEqual(json.loads(calls[1]["activity_json"])[0]["kind"], "compaction")
        self.assertEqual(overview_totals(self.db, source="codex")["cache_read_tokens"], 60)


if __name__ == "__main__":
    unittest.main()
