import json
import os
import tempfile
import unittest

from token_dashboard.db import (
    init_db, connect,
    overview_totals, expensive_prompts, project_summary,
    tool_use_breakdown, recent_sessions, session_turns,
    daily_token_breakdown, model_breakdown, project_name_for,
    skill_breakdown,
)


class QueryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.db = os.path.join(self.tmp, "q.db")
        init_db(self.db)
        with connect(self.db) as c:
            c.executescript("""
            INSERT INTO messages (uuid, parent_uuid, session_id, project_slug, type, timestamp, model,
              input_tokens, output_tokens, cache_read_tokens, cache_create_5m_tokens, cache_create_1h_tokens,
              prompt_text, prompt_chars)
            VALUES
              ('u1',NULL,'s1','projA','user','2026-04-10T00:00:00Z',NULL,0,0,0,0,0,'big prompt',10),
              ('a1','u1','s1','projA','assistant','2026-04-10T00:00:01Z','claude-opus-4-7',100,200,300,0,0,NULL,NULL),
              ('u2',NULL,'s2','projB','user','2026-04-11T00:00:00Z',NULL,0,0,0,0,0,'small',5),
              ('a2','u2','s2','projB','assistant','2026-04-11T00:00:01Z','claude-sonnet-4-6',5,5,0,0,0,NULL,NULL);
            INSERT INTO tool_calls (message_uuid, session_id, project_slug, tool_name, target, timestamp, is_error)
            VALUES ('a1','s1','projA','Read','foo.py','2026-04-10T00:00:01Z',0),
                   ('a1','s1','projA','Bash','npm test','2026-04-10T00:00:01Z',0);
            """)
            c.commit()

    def test_overview_totals(self):
        t = overview_totals(self.db, since=None, until=None)
        self.assertEqual(t["sessions"], 2)
        self.assertEqual(t["turns"], 2)
        self.assertEqual(t["input_tokens"], 105)
        self.assertEqual(t["output_tokens"], 205)

    def test_expensive_prompts_orders_by_tokens(self):
        rows = expensive_prompts(self.db, limit=10)
        self.assertGreaterEqual(len(rows), 2)
        self.assertEqual(rows[0]["prompt_text"], "big prompt")
        self.assertEqual(rows[0]["total_tokens"], 600)
        self.assertEqual(rows[0]["billable_tokens"], 300)
        self.assertEqual(rows[0]["model_calls"], 1)

    def test_expensive_prompts_sort_recent(self):
        rows = expensive_prompts(self.db, limit=10, sort="recent")
        self.assertEqual(rows[0]["prompt_text"], "small")
        self.assertEqual(rows[1]["prompt_text"], "big prompt")

    def test_expensive_prompts_includes_activity_counts(self):
        with connect(self.db) as c:
            c.execute("UPDATE messages SET tool_calls_json=? WHERE uuid='a1'", (
                '[{"name":"Read"},{"name":"Bash"}]',
            ))
            c.execute("""INSERT INTO messages
                (uuid, parent_uuid, session_id, project_slug, type, timestamp,
                 source, activity_json, input_tokens, output_tokens)
                VALUES ('a3', 'u2', 's2', 'projB', 'assistant',
                        '2026-04-11T00:00:02Z', 'codex', ?, 1, 1)""", (
                '[{"kind":"tool","name":"exec"},{"kind":"compaction"}]',
            ))
            c.commit()
        rows = {row["user_uuid"]: row for row in expensive_prompts(self.db, limit=10)}
        self.assertEqual((rows["u1"]["tool_count"], rows["u1"]["compaction_count"]), (2, 0))
        self.assertEqual((rows["u2"]["tool_count"], rows["u2"]["compaction_count"]), (1, 1))

    def test_project_summary_groups(self):
        rows = project_summary(self.db)
        slugs = {r["project_slug"]: r for r in rows}
        self.assertIn("projA", slugs)
        self.assertEqual(slugs["projA"]["turns"], 1)

    def test_tool_breakdown(self):
        rows = tool_use_breakdown(self.db)
        names = {r["tool_name"]: r for r in rows}
        self.assertIn("Read", names)
        self.assertIn("Bash", names)
        self.assertEqual((names["Read"]["source"], names["Read"]["calls"], names["Read"]["sessions"]),
                         ("claude", 1, 1))

    def test_tool_use_includes_codex_and_respects_filters(self):
        with connect(self.db) as c:
            c.execute("""INSERT INTO messages
                (uuid, source, session_id, project_slug, type, timestamp, activity_json)
                VALUES ('codex-tool', 'codex', 'codex:s', 'projC', 'assistant',
                        '2026-04-11T00:00:02Z', ?)""", (
                '[{"kind":"tool","name":"exec_command"},'
                '{"kind":"tool","name":"exec_command"},'
                '{"kind":"message","text":"done"}]',
            ))
            c.commit()
        rows = tool_use_breakdown(self.db)
        self.assertEqual([r["source"] for r in rows], ["codex", "claude", "claude"])
        self.assertEqual(rows[0]["tool_name"], "exec_command")
        self.assertEqual((rows[0]["calls"], rows[0]["sessions"]), (2, 1))
        self.assertEqual([r["source"] for r in tool_use_breakdown(self.db, source="codex")], ["codex"])
        self.assertEqual(len(tool_use_breakdown(self.db, source="claude")), 2)
        self.assertEqual(len(tool_use_breakdown(self.db, since="2026-04-11T00:00:00Z")), 1)

    def test_tool_use_classifies_exec_without_double_counting(self):
        events = [
            {"kind": "tool", "name": "exec", "input": "await tools.exec_command({cmd: 'ls'})"},
            {"kind": "tool", "name": "exec", "input": "await tools.apply_patch('patch')"},
            {"kind": "tool", "name": "exec", "input":
             "await tools.exec_command({}); await tools.apply_patch('patch')"},
            {"kind": "tool", "name": "exec", "input":
             "const example = 'tools.exec_command('; await tools.apply_patch('patch')"},
            {"kind": "tool", "name": "exec", "input":
             "await tools.exec_command({})", "input_truncated": True},
        ]
        with connect(self.db) as c:
            c.execute("""INSERT INTO messages
                (uuid, source, session_id, project_slug, type, timestamp, activity_json)
                VALUES ('exec-wrapper', 'codex', 'codex:split', 'projC', 'assistant',
                        '2026-04-11T00:00:02Z', ?)""", (json.dumps(events),))
            c.commit()
        rows = tool_use_breakdown(self.db, source="codex")
        counts = {row["tool_name"]: row["calls"] for row in rows}
        self.assertEqual(counts, {
            "exec → exec_command (shell)": 1,
            "exec → apply_patch": 2,
            "exec → mixed": 1,
            "exec → unknown": 1,
        })
        self.assertEqual(sum(row["calls"] for row in rows), len(events))
        self.assertTrue(all(row["sessions"] == 1 for row in rows))

    def test_recent_sessions(self):
        rows = recent_sessions(self.db, limit=5)
        self.assertEqual(rows[0]["session_id"], "s2")

    def test_recent_sessions_orders_by_total_tokens_before_limit(self):
        rows = recent_sessions(self.db, limit=1, sort="tokens")
        self.assertEqual([row["session_id"] for row in rows], ["s1"])
        self.assertEqual(rows[0]["tokens"], 600)

    def test_recent_sessions_counts_compactions(self):
        with connect(self.db) as c:
            c.execute("UPDATE messages SET activity_json=? WHERE uuid='a1'", (
                '[{"kind":"compaction"},{"kind":"tool"},{"kind":"compaction"}]',
            ))
            c.execute("""INSERT INTO messages
                (uuid, parent_uuid, session_id, project_slug, type, timestamp, activity_json)
                VALUES ('a3', 'u1', 's1', 'projA', 'assistant',
                        '2026-04-10T00:00:02Z', ?)""", (
                '[{"kind":"compaction"}]',
            ))
            c.commit()
        rows = {row["session_id"]: row for row in recent_sessions(self.db, limit=5)}
        self.assertEqual(rows["s1"]["compaction_count"], 3)
        self.assertEqual(rows["s2"]["compaction_count"], 0)
        filtered = {row["session_id"]: row for row in recent_sessions(
            self.db, limit=5, since="2026-04-10T00:00:02Z",
        )}
        self.assertEqual(filtered["s1"]["compaction_count"], 1)

    def test_session_turns(self):
        rows = session_turns(self.db, "s1")
        self.assertEqual(len(rows), 2)

    def test_daily_token_breakdown_groups_by_day(self):
        rows = daily_token_breakdown(self.db)
        days = {r["day"]: r for r in rows}
        self.assertIn("2026-04-10", days)
        self.assertIn("2026-04-11", days)
        self.assertEqual(days["2026-04-10"]["input_tokens"], 100)
        self.assertEqual(days["2026-04-10"]["output_tokens"], 200)
        self.assertEqual(days["2026-04-10"]["cache_read_tokens"], 300)

    def test_daily_token_breakdown_respects_since(self):
        rows = daily_token_breakdown(self.db, since="2026-04-11T00:00:00Z")
        days = [r["day"] for r in rows]
        self.assertEqual(days, ["2026-04-11"])

    def test_model_breakdown_respects_since_and_groups(self):
        rows = model_breakdown(self.db)
        models = {r["model"]: r for r in rows}
        self.assertIn("claude-opus-4-7", models)
        self.assertIn("claude-sonnet-4-6", models)
        self.assertEqual(models["claude-opus-4-7"]["input_tokens"], 100)

        filtered = model_breakdown(self.db, since="2026-04-11T00:00:00Z")
        names = [r["model"] for r in filtered]
        self.assertEqual(names, ["claude-sonnet-4-6"])


class SkillBreakdownTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.db = os.path.join(self.tmp, "s.db")
        init_db(self.db)
        with connect(self.db) as c:
            c.executescript("""
            INSERT INTO messages (uuid, session_id, project_slug, type, timestamp)
            VALUES
              ('u1','s1','pA','user','2026-04-10T00:00:00Z'),
              ('a1','s1','pA','assistant','2026-04-10T00:00:01Z'),
              ('u2','s2','pA','user','2026-04-11T00:00:00Z'),
              ('a2','s2','pA','assistant','2026-04-11T00:00:01Z');

            INSERT INTO tool_calls (message_uuid, session_id, project_slug, tool_name, target, result_tokens, timestamp, is_error)
            VALUES
              ('a1','s1','pA','Skill','brainstorming',NULL,'2026-04-10T00:00:01Z',0),
              ('u1','s1','pA','_tool_result','use-123',500,'2026-04-10T00:00:05Z',0),
              ('a1','s1','pA','Skill','brainstorming',NULL,'2026-04-10T00:00:30Z',0),
              ('u1','s1','pA','_tool_result','use-124',800,'2026-04-10T00:00:32Z',0),
              ('a2','s2','pA','Skill','create-skill',NULL,'2026-04-11T00:00:01Z',0),
              ('u2','s2','pA','_tool_result','use-125',1200,'2026-04-11T00:00:02Z',0);
            """)
            c.commit()

    def test_groups_by_skill(self):
        rows = skill_breakdown(self.db)
        by_name = {r["skill"]: r for r in rows}
        self.assertEqual(by_name["brainstorming"]["invocations"], 2)
        self.assertEqual(by_name["brainstorming"]["sessions"], 1)
        self.assertEqual(by_name["create-skill"]["invocations"], 1)

    def test_orders_by_invocations(self):
        rows = skill_breakdown(self.db)
        self.assertEqual(rows[0]["skill"], "brainstorming")

    def test_respects_since(self):
        rows = skill_breakdown(self.db, since="2026-04-11T00:00:00Z")
        names = [r["skill"] for r in rows]
        self.assertEqual(names, ["create-skill"])


class ProjectNameTests(unittest.TestCase):
    def test_basename_of_posix_cwd(self):
        self.assertEqual(project_name_for("/Users/x/foo", "slug"), "foo")

    def test_basename_of_windows_cwd(self):
        self.assertEqual(
            project_name_for(r"C:\Users\alice\projects\Token Dashboard", "anything"),
            "Token Dashboard",
        )

    def test_trailing_slash_stripped(self):
        self.assertEqual(project_name_for("/a/b/c/", "slug"), "c")

    def test_fallback_uses_last_dash_segment(self):
        self.assertEqual(
            project_name_for(None, "C--Users-x-Foo-Bar"),
            "Bar",
        )

    def test_fallback_single_segment(self):
        self.assertEqual(project_name_for(None, "projA"), "projA")

    def test_empty(self):
        self.assertEqual(project_name_for(None, ""), "")

    def test_walks_up_cwd_to_project_root(self):
        # cwd is a subfolder; slug matches the parent → return the parent's basename
        self.assertEqual(
            project_name_for(
                r"C:\Users\alice\projects\MyProject\subdir",
                "C--Users-alice-projects-MyProject",
            ),
            "MyProject",
        )

    def test_walks_up_preserves_spaces(self):
        self.assertEqual(
            project_name_for(
                r"C:\Users\alice\projects\Token Dashboard\src\subdir",
                "C--Users-alice-projects-Token-Dashboard",
            ),
            "Token Dashboard",
        )


class ProjectNameInQueriesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.db = os.path.join(self.tmp, "n.db")
        init_db(self.db)
        with connect(self.db) as c:
            c.executescript("""
            INSERT INTO messages (uuid, session_id, project_slug, cwd, type, timestamp,
              input_tokens, output_tokens, cache_read_tokens, cache_create_5m_tokens, cache_create_1h_tokens)
            VALUES
              ('u1','s1','C--Users-x-My-Repo','/Users/x/My Repo','user','2026-04-10T00:00:00Z',0,0,0,0,0),
              ('a1','s1','C--Users-x-My-Repo','/Users/x/My Repo','assistant','2026-04-10T00:00:01Z',10,20,0,0,0),
              ('u2','s2','slugOnly',NULL,'user','2026-04-11T00:00:00Z',0,0,0,0,0),
              ('a2','s2','slugOnly',NULL,'assistant','2026-04-11T00:00:01Z',5,5,0,0,0);
            """)
            c.commit()

    def test_project_summary_uses_cwd_basename(self):
        rows = project_summary(self.db)
        names = {r["project_slug"]: r["project_name"] for r in rows}
        self.assertEqual(names["C--Users-x-My-Repo"], "My Repo")
        self.assertEqual(names["slugOnly"], "slugOnly")

    def test_recent_sessions_has_project_name(self):
        rows = recent_sessions(self.db)
        by_sid = {r["session_id"]: r for r in rows}
        self.assertEqual(by_sid["s1"]["project_name"], "My Repo")
        self.assertEqual(by_sid["s2"]["project_name"], "slugOnly")


if __name__ == "__main__":
    unittest.main()
