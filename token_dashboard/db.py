"""SQLite schema, connection, and shared query helpers."""
from __future__ import annotations

import json
import os
import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, Union

SCHEMA = """
CREATE TABLE IF NOT EXISTS files (
  path        TEXT PRIMARY KEY,
  mtime       REAL    NOT NULL,
  bytes_read  INTEGER NOT NULL,
  scanned_at  REAL    NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
  uuid                    TEXT PRIMARY KEY,
  source                  TEXT NOT NULL DEFAULT 'claude',
  source_file             TEXT,
  parent_uuid             TEXT,
  session_id              TEXT NOT NULL,
  project_slug            TEXT NOT NULL,
  cwd                     TEXT,
  git_branch              TEXT,
  cc_version              TEXT,
  entrypoint              TEXT,
  type                    TEXT NOT NULL,
  is_sidechain            INTEGER NOT NULL DEFAULT 0,
  agent_id                TEXT,
  timestamp               TEXT NOT NULL,
  model                   TEXT,
  reasoning_effort        TEXT,
  stop_reason             TEXT,
  prompt_id               TEXT,
  message_id              TEXT,
  input_tokens            INTEGER NOT NULL DEFAULT 0,
  output_tokens           INTEGER NOT NULL DEFAULT 0,
  cache_read_tokens       INTEGER NOT NULL DEFAULT 0,
  cache_create_5m_tokens  INTEGER NOT NULL DEFAULT 0,
  cache_create_1h_tokens  INTEGER NOT NULL DEFAULT 0,
  cache_write_tokens      INTEGER NOT NULL DEFAULT 0,
  reasoning_output_tokens INTEGER NOT NULL DEFAULT 0,
  prompt_text             TEXT,
  prompt_chars            INTEGER,
  tool_calls_json         TEXT,
  activity_json           TEXT
);
CREATE INDEX IF NOT EXISTS idx_messages_session   ON messages(session_id);
CREATE INDEX IF NOT EXISTS idx_messages_project   ON messages(project_slug);
CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp);
CREATE INDEX IF NOT EXISTS idx_messages_model     ON messages(model);
CREATE INDEX IF NOT EXISTS idx_messages_msgid     ON messages(session_id, message_id);

CREATE TABLE IF NOT EXISTS session_titles (
  session_id TEXT PRIMARY KEY,
  title      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scanner_state (
  source  TEXT PRIMARY KEY,
  version INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS tool_calls (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  message_uuid  TEXT    NOT NULL,
  session_id    TEXT    NOT NULL,
  project_slug  TEXT    NOT NULL,
  tool_name     TEXT    NOT NULL,
  target        TEXT,
  result_tokens INTEGER,
  is_error      INTEGER NOT NULL DEFAULT 0,
  timestamp     TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tools_session ON tool_calls(session_id);
CREATE INDEX IF NOT EXISTS idx_tools_name    ON tool_calls(tool_name);
CREATE INDEX IF NOT EXISTS idx_tools_target  ON tool_calls(target);

CREATE TABLE IF NOT EXISTS codex_skill_uses (
  source_file  TEXT NOT NULL,
  turn_uuid    TEXT NOT NULL,
  session_id   TEXT NOT NULL,
  project_slug TEXT NOT NULL,
  skill        TEXT NOT NULL,
  timestamp    TEXT NOT NULL,
  PRIMARY KEY (source_file, turn_uuid, skill)
);
CREATE INDEX IF NOT EXISTS idx_codex_skills_timestamp ON codex_skill_uses(timestamp);

"""


def default_db_path() -> Path:
    return Path.home() / ".claude" / "token-dashboard.db"


def init_db(path: Union[str, Path]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(path)
    try:
        _migrate_add_message_id(c)
        c.executescript(SCHEMA)
        _migrate_sources(c)
    finally:
        c.close()


def _migrate_sources(conn) -> None:
    """Add provider-neutral fields without discarding existing Claude data."""
    cols = {row[1] for row in conn.execute("PRAGMA table_info(messages)")}
    additions = {
        "source": "TEXT NOT NULL DEFAULT 'claude'",
        "source_file": "TEXT",
        "cache_write_tokens": "INTEGER NOT NULL DEFAULT 0",
        "reasoning_output_tokens": "INTEGER NOT NULL DEFAULT 0",
        "activity_json": "TEXT",
        "reasoning_effort": "TEXT",
    }
    for name, definition in additions.items():
        if name not in cols:
            conn.execute(f"ALTER TABLE messages ADD COLUMN {name} {definition}")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_source ON messages(source)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_source_file ON messages(source_file)")
    conn.commit()


def _migrate_add_message_id(conn) -> None:
    """Add messages.message_id for streaming-snapshot dedup.

    Why: pre-migration rows were summed from all streaming snapshots (over-count).
    How to apply: if the old table exists without the column, add it and clear
    messages/tool_calls/files so the next scan replays JSONLs cleanly. Source
    of truth is on disk; rescanning is cheap.
    """
    has_table = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='messages'"
    ).fetchone()
    if not has_table:
        return
    cols = {row[1] for row in conn.execute("PRAGMA table_info(messages)")}
    if "message_id" in cols:
        return
    conn.execute("ALTER TABLE messages ADD COLUMN message_id TEXT")
    conn.execute("DELETE FROM messages")
    conn.execute("DELETE FROM tool_calls")
    conn.execute("DELETE FROM files")
    conn.commit()


@contextmanager
def connect(path: Union[str, Path]):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()


def _range_clause(since, until, col: str = "timestamp", source=None):
    where, args = [], []
    if since:
        where.append(f"{col} >= ?"); args.append(since)
    if until:
        where.append(f"{col} < ?"); args.append(until)
    if source:
        where.append("source = ?"); args.append(source)
    return ((" AND " + " AND ".join(where)) if where else "", args)


def _encode_slug(path: str) -> str:
    """Claude Code's project-slug encoding: each of `:`, `\\`, `/`, space → one `-`."""
    return re.sub(r"[:\\/ ]", "-", path)


def _walk_to_root(cwd: str, slug: str) -> Optional[str]:
    """If any ancestor of cwd encodes to slug, return that ancestor's basename."""
    if not cwd or not slug:
        return None
    trimmed = cwd.rstrip("/\\")
    sep = "\\" if "\\" in trimmed else "/"
    parts = trimmed.split(sep)
    for i in range(len(parts), 0, -1):
        if _encode_slug(sep.join(parts[:i])) == slug:
            name = parts[i - 1]
            if name:
                return name
    return None


def project_name_for(cwd: Optional[str], fallback_slug: str) -> str:
    """Pretty project name from a single cwd + slug (best-effort).

    For the multi-cwd case, prefer `best_project_name`.
    """
    name = _walk_to_root(cwd or "", fallback_slug or "")
    if name:
        return name
    if cwd:
        trimmed = cwd.rstrip("/\\")
        sep = "\\" if "\\" in trimmed else "/"
        tail = trimmed.split(sep)[-1]
        if tail:
            return tail
    if fallback_slug:
        parts = [p for p in re.split(r"-+", fallback_slug) if p]
        if parts:
            return parts[-1]
    return fallback_slug or ""


def best_project_name(cwds, slug: str) -> str:
    """Pick a pretty name from a list of cwds.

    Prefer a cwd whose walk-up matches `slug` (a true descendant of the project
    root). If none match, fall back to `project_name_for` on the first cwd,
    then to the slug's last segment.
    """
    cwds = [c for c in (cwds or []) if c]
    for cwd in cwds:
        name = _walk_to_root(cwd, slug)
        if name:
            return name
    return project_name_for(cwds[0] if cwds else None, slug)


def overview_totals(db_path, since=None, until=None, source=None) -> dict:
    rng, args = _range_clause(since, until, source=source)
    sql = f"""
      SELECT COUNT(DISTINCT session_id) AS sessions,
             SUM(CASE WHEN type='user' THEN 1 ELSE 0 END) AS turns,
             COALESCE(SUM(input_tokens),0)            AS input_tokens,
             COALESCE(SUM(output_tokens),0)           AS output_tokens,
             COALESCE(SUM(cache_read_tokens),0)       AS cache_read_tokens,
             COALESCE(SUM(cache_create_5m_tokens),0)  AS cache_create_5m_tokens,
             COALESCE(SUM(cache_create_1h_tokens),0)  AS cache_create_1h_tokens,
             COALESCE(SUM(cache_write_tokens),0) AS cache_write_tokens,
             COALESCE(SUM(reasoning_output_tokens),0) AS reasoning_output_tokens
        FROM messages WHERE 1=1 {rng}
    """
    with connect(db_path) as c:
        return dict(c.execute(sql, args).fetchone())


def expensive_prompts(db_path, limit: int = 50, sort: str = "tokens", source=None) -> list:
    """User prompt with all response usage attributed to that turn.

    sort="tokens" (default) → largest total processed first.
    sort="recent"           → newest first.
    """
    order = "u.timestamp DESC" if sort == "recent" else "total_tokens DESC"
    sql = f"""
      SELECT u.uuid AS user_uuid, u.session_id, u.project_slug, u.source, u.timestamp,
             u.prompt_text, u.prompt_chars,
             MAX(a.uuid) AS assistant_uuid, MAX(a.model) AS model,
             COUNT(a.uuid) AS model_calls,
             COALESCE(SUM(a.input_tokens+a.output_tokens+a.cache_write_tokens
               +a.cache_create_5m_tokens+a.cache_create_1h_tokens),0) AS billable_tokens,
             COALESCE(SUM(a.cache_read_tokens),0) AS cache_read_tokens,
             COALESCE(SUM(a.input_tokens+a.output_tokens+a.cache_read_tokens
               +a.cache_write_tokens+a.cache_create_5m_tokens+a.cache_create_1h_tokens),0) AS total_tokens,
             st.title AS session_title
        FROM messages u
        LEFT JOIN messages a ON a.parent_uuid = u.uuid AND a.type='assistant'
        LEFT JOIN session_titles st ON st.session_id = u.session_id
       WHERE u.type='user' AND u.prompt_text IS NOT NULL AND TRIM(u.prompt_text) != ''
         AND (? IS NULL OR u.source = ?)
       GROUP BY u.uuid
       ORDER BY {order}
       LIMIT ?
    """
    with connect(db_path) as c:
        rows = [dict(r) for r in c.execute(sql, (source, source, limit))]
        if not rows:
            return rows
        by_uuid = {row["user_uuid"]: row for row in rows}
        for row in rows:
            row["tool_count"] = 0
            row["compaction_count"] = 0
        placeholders = ",".join("?" * len(rows))
        activity_sql = f"""SELECT parent_uuid, activity_json, tool_calls_json
                             FROM messages
                            WHERE type='assistant' AND parent_uuid IN ({placeholders})"""
        for assistant in c.execute(activity_sql, tuple(by_uuid)):
            prompt = by_uuid[assistant["parent_uuid"]]
            events = []
            for raw in (assistant["activity_json"], assistant["tool_calls_json"]):
                try:
                    parsed = json.loads(raw or "[]")
                except (TypeError, ValueError):
                    continue
                if isinstance(parsed, list) and parsed:
                    events = parsed
                    break
            prompt["tool_count"] += sum(
                isinstance(event, dict) and event.get("kind", "tool") == "tool"
                for event in events
            )
            prompt["compaction_count"] += sum(
                isinstance(event, dict) and event.get("kind") == "compaction"
                for event in events
            )
        return rows


def project_summary(db_path, since=None, until=None, source=None) -> list:
    rng, args = _range_clause(since, until, source=source)
    sql = f"""
      SELECT project_slug, source,
             COUNT(DISTINCT session_id) AS sessions,
             SUM(CASE WHEN type='user' THEN 1 ELSE 0 END) AS turns,
             COALESCE(SUM(input_tokens), 0)  AS input_tokens,
             COALESCE(SUM(output_tokens), 0) AS output_tokens,
             SUM(input_tokens)+SUM(output_tokens)
               +SUM(cache_create_5m_tokens)+SUM(cache_create_1h_tokens)
               +SUM(cache_write_tokens) AS billable_tokens,
             SUM(cache_read_tokens) AS cache_read_tokens
        FROM messages m
       WHERE 1=1 {rng}
       GROUP BY project_slug, source
       ORDER BY billable_tokens DESC
    """
    with connect(db_path) as c:
        rows = [dict(r) for r in c.execute(sql, args)]
        for r in rows:
            cwds = [row["cwd"] for row in c.execute(
                "SELECT DISTINCT cwd FROM messages WHERE project_slug=? AND source=? AND cwd IS NOT NULL",
                (r["project_slug"], r["source"]),
            )]
            r["project_name"] = best_project_name(cwds, r["project_slug"])
    return rows


_NESTED_TOOL_CALL = re.compile(r"(?<![.\w$])tools\.([A-Za-z_]\w*)\s*\(")
_KNOWN_NESTED_TOOLS = {
    "exec_command", "apply_patch", "write_stdin", "view_image", "web__run",
    "image_gen__imagegen", "clock__curr_time", "list_mcp_resources",
    "list_mcp_resource_templates", "read_mcp_resource", "get_goal",
    "create_goal", "update_goal",
}


def _exec_tool_name(event: dict) -> str:
    """Classify one exec wrapper by tool calls visible in its JavaScript input."""
    if event.get("input_truncated") or not isinstance(event.get("input"), str):
        return "exec → unknown"
    source = event["input"]
    code = []
    i = 0
    while i < len(source):
        char = source[i]
        if char in ('"', "'", "`"):
            quote = char
            code.append(" ")
            i += 1
            while i < len(source):
                if source[i] == "\\":
                    i += 2
                elif source[i] == quote:
                    i += 1
                    break
                else:
                    i += 1
        elif source.startswith("//", i):
            code.append(" ")
            end = source.find("\n", i + 2)
            i = len(source) if end < 0 else end
        elif source.startswith("/*", i):
            code.append(" ")
            end = source.find("*/", i + 2)
            i = len(source) if end < 0 else end + 2
        else:
            code.append(char)
            i += 1
    names = {
        match.group(1) for match in _NESTED_TOOL_CALL.finditer("".join(code))
        if match.group(1) in _KNOWN_NESTED_TOOLS or match.group(1).startswith("mcp__")
    }
    if len(names) > 1:
        return "exec → mixed"
    if not names:
        return "exec → unknown"
    name = names.pop()
    return "exec → exec_command (shell)" if name == "exec_command" else f"exec → {name}"


def tool_use_breakdown(db_path, since=None, until=None, source=None) -> list:
    """Count recorded outer tool calls, classifying Codex exec wrappers by nested tool."""
    result = []
    with connect(db_path) as c:
        if source != "codex":
            rng, args = _range_clause(since, until)
            sql = f"""
              SELECT 'claude' AS source, tool_name, COUNT(*) AS calls,
                     COUNT(DISTINCT session_id) AS sessions
                FROM tool_calls
               WHERE tool_name != '_tool_result' {rng}
               GROUP BY tool_name
            """
            result.extend(dict(row) for row in c.execute(sql, args))
        if source != "claude":
            rng, args = _range_clause(since, until)
            sql = f"""
              SELECT session_id, activity_json
                FROM messages
               WHERE source='codex' AND type='assistant'
                 AND activity_json IS NOT NULL {rng}
            """
            codex_tools = {}
            for row in c.execute(sql, args):
                try:
                    events = json.loads(row["activity_json"])
                except (TypeError, ValueError):
                    continue
                if not isinstance(events, list):
                    continue
                for event in events:
                    if not isinstance(event, dict) or event.get("kind") != "tool":
                        continue
                    name = event.get("name") or "tool"
                    if name == "exec":
                        name = _exec_tool_name(event)
                    stats = codex_tools.setdefault(name, {"calls": 0, "sessions": set()})
                    stats["calls"] += 1
                    stats["sessions"].add(row["session_id"])
            result.extend({
                "source": "codex", "tool_name": name,
                "calls": stats["calls"], "sessions": len(stats["sessions"]),
            } for name, stats in codex_tools.items())
    return sorted(result, key=lambda row: (-row["calls"], row["source"], row["tool_name"]))


def recent_sessions(db_path, limit: int = 20, since=None, until=None, source=None,
                    sort: str = "recent") -> list:
    rng, args = _range_clause(since, until, source=source)
    if sort not in ("recent", "tokens"):
        raise ValueError(f"invalid session sort: {sort}")
    order_by = "tokens DESC, ended DESC, m.session_id" if sort == "tokens" else "ended DESC, m.session_id"
    sql = f"""
      SELECT m.session_id, project_slug, source, st.title AS session_title,
             MIN(timestamp) AS started, MAX(timestamp) AS ended,
             SUM(CASE WHEN type='user' THEN 1 ELSE 0 END) AS turns,
             SUM(input_tokens)+SUM(cache_read_tokens)+SUM(cache_write_tokens)
               +SUM(cache_create_5m_tokens)+SUM(cache_create_1h_tokens)
               +SUM(output_tokens) AS tokens
        FROM messages m
        LEFT JOIN session_titles st ON st.session_id = m.session_id
       WHERE 1=1 {rng}
       GROUP BY m.session_id, m.source
       ORDER BY {order_by}
       LIMIT ?
    """
    with connect(db_path) as c:
        rows = [dict(r) for r in c.execute(sql, (*args, limit))]
        for row in rows:
            row["compaction_count"] = 0
        if rows:
            by_id = {row["session_id"]: row for row in rows}
            placeholders = ",".join("?" * len(by_id))
            activity_rng, activity_args = _range_clause(
                since, until, col="m.timestamp", source=source,
            )
            activity_sql = f"""SELECT m.session_id, m.activity_json
                                 FROM messages m
                                WHERE m.type='assistant'
                                  AND m.session_id IN ({placeholders})
                                  AND m.activity_json LIKE '%compaction%'
                                  {activity_rng}"""
            for message in c.execute(activity_sql, (*by_id, *activity_args)):
                try:
                    events = json.loads(message["activity_json"] or "[]")
                except (TypeError, ValueError):
                    continue
                if isinstance(events, list):
                    by_id[message["session_id"]]["compaction_count"] += sum(
                        isinstance(event, dict) and event.get("kind") == "compaction"
                        for event in events
                    )
        # Cache per-slug name lookups so we don't query once per session.
        slug_cache = {}
        for r in rows:
            slug = (r["project_slug"], r["source"])
            if slug not in slug_cache:
                cwds = [row["cwd"] for row in c.execute(
                    "SELECT DISTINCT cwd FROM messages WHERE project_slug=? AND source=? AND cwd IS NOT NULL",
                    slug,
                )]
                slug_cache[slug] = best_project_name(cwds, r["project_slug"])
            r["project_name"] = slug_cache[slug]
            if not r["session_title"]:
                prompt = c.execute(
                    """SELECT prompt_text FROM messages
                       WHERE session_id=? AND type='user' AND prompt_text IS NOT NULL
                         AND TRIM(prompt_text) != ''
                       ORDER BY timestamp, uuid LIMIT 1""",
                    (r["session_id"],),
                ).fetchone()
                r["session_title"] = _title_from_prompt(prompt[0]) if prompt else None
    return rows


def session_turns(db_path, session_id: str) -> list:
    sql = """
      SELECT uuid, parent_uuid, type, timestamp, model, reasoning_effort,
             is_sidechain, agent_id, source,
             input_tokens, output_tokens, cache_read_tokens,
             cache_create_5m_tokens, cache_create_1h_tokens, cache_write_tokens,
             reasoning_output_tokens,
             prompt_text, prompt_chars, tool_calls_json, activity_json,
             message_id, source_file, project_slug, cwd,
             st.title AS session_title
        FROM messages m
        LEFT JOIN session_titles st ON st.session_id = m.session_id
       WHERE m.session_id = ?
       ORDER BY timestamp ASC
    """
    with connect(db_path) as c:
        return [dict(r) for r in c.execute(sql, (session_id,))]


def _title_from_prompt(prompt: str) -> str | None:
    first = next((line.strip() for line in prompt.splitlines() if line.strip()), None)
    if not first:
        return None
    return first[:97] + "..." if len(first) > 100 else first


def daily_token_breakdown(db_path, since=None, until=None, source=None) -> list:
    """One row per day: stacked bar data for input/output/cache_read/cache_create."""
    rng, args = _range_clause(since, until, source=source)
    sql = f"""
      SELECT substr(timestamp, 1, 10) AS day,
             COALESCE(SUM(input_tokens),0)      AS input_tokens,
             COALESCE(SUM(output_tokens),0)     AS output_tokens,
             COALESCE(SUM(cache_read_tokens),0) AS cache_read_tokens,
             COALESCE(SUM(cache_create_5m_tokens),0)
               + COALESCE(SUM(cache_create_1h_tokens),0)
               + COALESCE(SUM(cache_write_tokens),0) AS cache_create_tokens
        FROM messages
       WHERE timestamp IS NOT NULL {rng}
       GROUP BY day
       ORDER BY day ASC
    """
    with connect(db_path) as c:
        return [dict(r) for r in c.execute(sql, args)]


def skill_breakdown(db_path, since=None, until=None, source=None) -> list:
    """Claude Skill calls and inferred Codex SKILL.md reads.

    Token attribution per skill is not included: in Claude Code, a Skill's
    content is loaded via a system-reminder on the next turn, not as the
    tool_result body — so `result_tokens` on _tool_result rows reflects the
    activation ack (tiny), not the skill definition (which is what actually
    fills context). A future schema change (storing tool_use_id on the
    invocation row) could enable precise attribution; for now we only expose
    the reliable counts.
    """
    rng, args = _range_clause(since, until, source=source)
    sql = f"""
      SELECT source, skill,
             COUNT(*) AS invocations,
             COUNT(DISTINCT session_id) AS sessions,
             MAX(timestamp) AS last_used
        FROM (
          SELECT 'claude' AS source, target AS skill, session_id, timestamp
            FROM tool_calls
           WHERE tool_name = 'Skill' AND target IS NOT NULL AND target != ''
          UNION ALL
          SELECT 'codex' AS source, skill, session_id, timestamp
            FROM codex_skill_uses
        ) AS uses
       WHERE 1=1 {rng}
       GROUP BY source, skill
       ORDER BY invocations DESC, skill
    """
    with connect(db_path) as c:
        return [dict(r) for r in c.execute(sql, args)]


def model_breakdown(db_path, since=None, until=None, source=None) -> list:
    """Per-model token totals + turn count."""
    rng, args = _range_clause(since, until, source=source)
    sql = f"""
      SELECT source, COALESCE(model, 'unknown') AS model,
             COUNT(DISTINCT COALESCE(parent_uuid, uuid)) AS turns,
             COALESCE(SUM(input_tokens),0)            AS input_tokens,
             COALESCE(SUM(output_tokens),0)           AS output_tokens,
             COALESCE(SUM(cache_read_tokens),0)       AS cache_read_tokens,
             COALESCE(SUM(cache_create_5m_tokens),0)  AS cache_create_5m_tokens,
             COALESCE(SUM(cache_create_1h_tokens),0)  AS cache_create_1h_tokens,
             COALESCE(SUM(cache_write_tokens),0) AS cache_write_tokens,
             COALESCE(SUM(reasoning_output_tokens),0) AS reasoning_output_tokens
        FROM messages
       WHERE type = 'assistant' {rng}
       GROUP BY source, model
       ORDER BY (input_tokens + output_tokens + cache_read_tokens
                 + cache_create_5m_tokens + cache_create_1h_tokens
                 + cache_write_tokens) DESC
    """
    with connect(db_path) as c:
        return [dict(r) for r in c.execute(sql, args)]
