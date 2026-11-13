"""Read local Codex session rollouts into the shared usage database.

Codex's on-disk rollout format is not a public API. Keep this adapter isolated
from the Claude parser; retain bounded previews of visible assistant and tool
activity for the session timeline.
"""
from __future__ import annotations

import json
import hashlib
import os
import re
import sqlite3
import time
from contextlib import closing
from pathlib import Path
from typing import Union

from .db import _encode_slug, connect


INSERT = """
INSERT INTO messages (
  uuid, source, source_file, parent_uuid, session_id, project_slug, cwd,
  type, is_sidechain, timestamp, model, reasoning_effort, message_id, input_tokens,
  output_tokens, cache_read_tokens, cache_write_tokens, reasoning_output_tokens,
  prompt_text, prompt_chars, tool_calls_json, activity_json
) VALUES (
  :uuid, 'codex', :source_file, :parent_uuid, :session_id, :project_slug, :cwd,
  :type, :is_sidechain, :timestamp, :model, :reasoning_effort, :message_id, :input_tokens,
  :output_tokens, :cache_read_tokens, :cache_write_tokens, :reasoning_output_tokens,
  :prompt_text, :prompt_chars, :tool_calls_json, :activity_json
)
"""


def default_codex_sessions_dir() -> Path:
    return Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex").expanduser() / "sessions"


def _number(value) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _tokens(usage: dict) -> dict:
    """Normalize Codex's inclusive input total into disjoint categories."""
    gross = _number(usage.get("input_tokens"))
    cached = min(_number(usage.get("cached_input_tokens")), gross)
    written = min(_number(usage.get("cache_write_input_tokens")), gross - cached)
    output = _number(usage.get("output_tokens"))
    return {
        "input_tokens": gross - cached - written,
        "cache_read_tokens": cached,
        "cache_write_tokens": written,
        "output_tokens": output,
        "reasoning_output_tokens": min(_number(usage.get("reasoning_output_tokens")), output),
    }


def _delta(total: dict, previous: dict) -> dict:
    return {k: max(0, _number(total.get(k)) - _number(previous.get(k))) for k in (
        "input_tokens", "cached_input_tokens", "cache_write_input_tokens",
        "output_tokens", "reasoning_output_tokens",
    )}


def _read_records(path: Path):
    """Yield complete JSONL records; a writer's unfinished final line is retried."""
    with path.open("rb") as stream:
        for line_no, raw in enumerate(stream, 1):
            if not raw.endswith(b"\n"):
                break
            try:
                rec = json.loads(raw)
            except (UnicodeError, json.JSONDecodeError):
                continue
            if isinstance(rec, dict):
                yield line_no, rec


def _user_text(payload: dict) -> str | None:
    content = payload.get("content")
    if not isinstance(content, list):
        return None
    parts = [item.get("text") for item in content
             if isinstance(item, dict) and item.get("type") in ("input_text", "text")
             and isinstance(item.get("text"), str)]
    return "\n\n".join(part for part in parts if part) or None


def _message_text(payload: dict) -> str | None:
    content = payload.get("content")
    if not isinstance(content, list):
        return None
    parts = [item.get("text") for item in content
             if isinstance(item, dict) and item.get("type") in ("output_text", "text")
             and isinstance(item.get("text"), str)]
    return "\n\n".join(part for part in parts if part) or None


def _preview(value, limit=12000) -> tuple[str | None, bool]:
    if value is None:
        return None, False
    value = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    return value[:limit], len(value) > limit


def _item_turn(payload: dict, current_turn: str | None) -> str | None:
    metadata = payload.get("internal_chat_message_metadata_passthrough") or {}
    return metadata.get("turn_id", current_turn) if isinstance(metadata, dict) else current_turn


_COMMAND_RE = re.compile(
    r"""(?:\bcmd|["']cmd["'])\s*:\s*(?:"(?P<double>(?:\\.|[^"\\])*)"|'(?P<single>(?:\\.|[^'\\])*)')"""
)
_READ_COMMAND_RE = re.compile(
    r"(?:^|[;&|{]\s*)\s*(?:Get-Content|cat|sed|head|tail|more|less)\b", re.I,
)
_SKILL_PATH_RE = re.compile(r"([A-Za-z0-9_.-]+)[\\/]+SKILL\.md\b", re.I)


def _skill_reads(tool_input) -> set[str]:
    """Infer activation only when a shell command reads a SKILL.md file."""
    if isinstance(tool_input, dict):
        commands = [tool_input.get("cmd")]
    elif isinstance(tool_input, str):
        commands = [m.group("double") or m.group("single") for m in _COMMAND_RE.finditer(tool_input)]
        if not commands:
            commands = [tool_input]
    else:
        return set()
    return {
        match.group(1)
        for command in commands if isinstance(command, str) and _READ_COMMAND_RE.search(command)
        for match in _SKILL_PATH_RE.finditer(command)
    }


def _session_titles(codex_home: Path) -> dict[str, str]:
    """Use Codex's local thread names, with the state database as a fallback."""
    titles = {}
    state = codex_home / "state_5.sqlite"
    if state.is_file():
        try:
            with closing(sqlite3.connect(f"file:{state}?mode=ro", uri=True)) as conn:
                for sid, title in conn.execute("SELECT id, COALESCE(NULLIF(name, ''), title) FROM threads"):
                    if sid and isinstance(title, str) and title.strip():
                        titles[f"codex:{sid}"] = title.strip()
        except (OSError, sqlite3.DatabaseError):
            pass
    index = codex_home / "session_index.jsonl"
    if index.is_file():
        try:
            for _, rec in _read_records(index):
                sid, title = rec.get("id"), rec.get("thread_name")
                if sid and isinstance(title, str) and title.strip():
                    titles[f"codex:{sid}"] = title.strip()
        except OSError:
            pass
    return titles


def parse_file(path: Path) -> list:
    """Return rows for one rollout, preferring per-response usage records.

    Older rollouts expose ``event_msg.token_count`` instead. Those records can
    contain both a last-response delta and a cumulative session snapshot.
    Never ingest both formats from the same file.
    """
    session_id = path.stem
    session_cwd = None
    project_root = None
    current_turn = None
    current_model = None
    current_effort = None
    current_cwd = None
    turn_context = {}
    response_rows = {}
    legacy_rows = []
    previous_total = {}
    prompts = {}
    legacy_prompts = {}
    pending_activity = {}
    tools_by_call_id = {}

    for line_no, rec in _read_records(path):
        kind = rec.get("type")
        payload = rec.get("payload") or {}
        if not isinstance(payload, dict):
            continue
        if kind == "session_meta":
            session_id = payload.get("id") or payload.get("session_id") or session_id
            session_cwd = payload.get("cwd") or session_cwd
            roots = payload.get("runtime_workspace_roots") or []
            if isinstance(roots, list) and roots and isinstance(roots[0], str):
                project_root = roots[0]
        elif kind == "turn_context":
            current_turn = payload.get("turn_id") or current_turn
            current_model = payload.get("model") or current_model
            current_effort = payload.get("effort") or current_effort
            current_cwd = payload.get("cwd") or current_cwd
            roots = payload.get("workspace_roots") or []
            if isinstance(roots, list) and roots and isinstance(roots[0], str):
                project_root = roots[0]
            if current_turn:
                turn_context[current_turn] = (
                    current_model, current_cwd, payload.get("root_turn_id"), current_effort,
                )
        elif kind == "response_item":
            item_type = payload.get("type")
            turn = _item_turn(payload, current_turn)
            if item_type == "message" and payload.get("role") == "user":
                prompt = _user_text(payload)
                if turn and prompt:
                    prompts.setdefault(turn, []).append((rec.get("timestamp"), prompt))
            elif item_type == "message" and payload.get("role") == "assistant":
                message = _message_text(payload)
                if message:
                    value, truncated = _preview(message)
                    pending_activity.setdefault(turn, []).append({
                        "kind": "message", "timestamp": rec.get("timestamp"),
                        "phase": payload.get("phase"), "text": value,
                        "truncated": truncated,
                    })
            elif item_type == "reasoning":
                summary = payload.get("summary") or []
                if isinstance(summary, list):
                    text = "\n".join(item.get("text", "") for item in summary
                                     if isinstance(item, dict) and isinstance(item.get("text"), str))
                    if text:
                        value, truncated = _preview(text)
                        pending_activity.setdefault(turn, []).append({
                            "kind": "reasoning_summary", "timestamp": rec.get("timestamp"),
                            "text": value, "truncated": truncated,
                        })
            elif item_type in ("custom_tool_call", "function_call"):
                value, truncated = _preview(payload.get("input", payload.get("arguments")))
                event = {
                    "kind": "tool", "timestamp": rec.get("timestamp"),
                    "name": payload.get("name") or "tool", "call_id": payload.get("call_id"),
                    "input": value, "input_truncated": truncated,
                    "output": None, "output_truncated": False,
                }
                pending_activity.setdefault(turn, []).append(event)
                if payload.get("call_id"):
                    tools_by_call_id[payload["call_id"]] = event
            elif item_type in ("custom_tool_call_output", "function_call_output"):
                value, truncated = _preview(payload.get("output"))
                event = tools_by_call_id.get(payload.get("call_id"))
                if event is not None:
                    event["output"] = value
                    event["output_truncated"] = truncated
                    event["completed_at"] = rec.get("timestamp")
                else:
                    pending_activity.setdefault(turn, []).append({
                        "kind": "tool_output", "timestamp": rec.get("timestamp"),
                        "call_id": payload.get("call_id"), "output": value,
                        "output_truncated": truncated,
                    })
        elif kind == "event_msg" and payload.get("type") == "task_started":
            current_turn = payload.get("turn_id") or current_turn
        elif kind == "event_msg" and payload.get("type") == "user_message":
            prompt = payload.get("message")
            if current_turn and isinstance(prompt, str) and prompt:
                legacy_prompts.setdefault(current_turn, []).append((rec.get("timestamp"), prompt))
        elif kind == "token_usage_record":
            usage = payload.get("usage")
            if not isinstance(usage, dict):
                continue
            turn = payload.get("turn_id") or current_turn
            model, cwd, root_turn, effort = turn_context.get(
                turn, (current_model, current_cwd, None, current_effort),
            )
            key = payload.get("response_id") or f"line-{line_no}"
            activity = pending_activity.pop(turn, [])
            response_rows[str(key)] = (
                line_no, rec.get("timestamp"), turn, root_turn, model, cwd,
                project_root, usage, str(key), activity, effort,
            )
        elif kind == "event_msg" and payload.get("type") == "token_count":
            info = payload.get("info") or {}
            if not isinstance(info, dict):
                continue
            total = info.get("total_token_usage")
            last = info.get("last_token_usage")
            if isinstance(last, dict):
                usage = last
            elif isinstance(total, dict):
                usage = _delta(total, previous_total)
            else:
                continue
            if isinstance(total, dict):
                previous_total = total
            turn = payload.get("turn_id") or current_turn
            model, cwd, root_turn, effort = turn_context.get(
                turn, (current_model, current_cwd, None, current_effort),
            )
            legacy_rows.append((
                line_no, rec.get("timestamp"), turn, root_turn, model, cwd,
                project_root, usage, f"line-{line_no}", pending_activity.pop(turn, []), effort,
            ))
        elif kind == "compacted":
            key = payload.get("compaction_response_id")
            record = response_rows.get(str(key)) if key else None
            if record is None and legacy_rows:
                record = legacy_rows[-1]
            if record is not None:
                record[-2].append({
                    "kind": "compaction", "timestamp": rec.get("timestamp"),
                    "window_number": payload.get("window_number"),
                })

    selected = list(response_rows.values()) if response_rows else legacy_rows
    selected.sort(key=lambda row: row[0])
    namespaced_session = f"codex:{session_id}"
    file_key = hashlib.sha1(str(path).encode("utf-8")).hexdigest()[:12]
    rows = []
    user_rows = {}
    for line_no, timestamp, turn, root_turn, model, cwd, row_root, usage, response_id, activity, effort in selected:
        if not timestamp:
            continue
        cwd = cwd or session_cwd
        project_path = row_root or session_cwd or cwd
        slug = _encode_slug(project_path) if project_path else "unknown"
        parent_uuid = None
        if turn:
            parent_uuid = f"{namespaced_session}:{file_key}:turn:{turn}"
            if turn not in user_rows:
                user_rows[turn] = {
                    "uuid": parent_uuid, "source_file": str(path), "parent_uuid": None,
                    "session_id": namespaced_session, "project_slug": slug, "cwd": cwd,
                    "type": "user", "is_sidechain": int(bool(root_turn and root_turn != turn)),
                    "timestamp": timestamp, "model": None, "reasoning_effort": None,
                    "message_id": None,
                    "prompt_text": None, "prompt_chars": None,
                    "tool_calls_json": None, "activity_json": None,
                    **_tokens({}),
                }
        row_id = f"{namespaced_session}:{file_key}:response:{response_id}"
        rows.append({
            "uuid": row_id, "source_file": str(path), "parent_uuid": parent_uuid,
            "session_id": namespaced_session, "project_slug": slug, "cwd": cwd,
            "type": "assistant", "is_sidechain": int(bool(root_turn and root_turn != turn)),
            "timestamp": timestamp, "model": model, "reasoning_effort": effort,
            "message_id": response_id,
            "prompt_text": None, "prompt_chars": None,
            "tool_calls_json": json.dumps(
                [event for event in activity if event["kind"] == "tool"], ensure_ascii=False,
            ) if any(event["kind"] == "tool" for event in activity) else None,
            "activity_json": json.dumps(activity, ensure_ascii=False) if activity else None,
            **_tokens(usage),
        })
    for turn, messages in (prompts | {k: v for k, v in legacy_prompts.items() if k not in prompts}).items():
        text = "\n\n".join(message for _, message in messages)
        if turn not in user_rows:
            model, cwd, root_turn, effort = turn_context.get(
                turn, (current_model, current_cwd, None, current_effort),
            )
            project_path = project_root or session_cwd or cwd
            user_rows[turn] = {
                "uuid": f"{namespaced_session}:{file_key}:turn:{turn}",
                "source_file": str(path), "parent_uuid": None,
                "session_id": namespaced_session,
                "project_slug": _encode_slug(project_path) if project_path else "unknown",
                "cwd": cwd or session_cwd, "type": "user",
                "is_sidechain": int(bool(root_turn and root_turn != turn)),
                "timestamp": messages[0][0] or "", "model": None,
                "reasoning_effort": None, "message_id": None,
                "prompt_text": None, "prompt_chars": None,
                "tool_calls_json": None, "activity_json": None, **_tokens({}),
            }
        user_rows[turn]["prompt_text"] = text
        user_rows[turn]["prompt_chars"] = len(text)
        user_rows[turn]["timestamp"] = messages[0][0] or user_rows[turn]["timestamp"]
    rows.extend(row for row in user_rows.values() if row["timestamp"])
    rows.sort(key=lambda row: row["timestamp"])
    return rows


def scan_codex_dir(sessions_root: Union[str, Path], db_path: Union[str, Path]) -> dict:
    root = Path(sessions_root).expanduser().resolve()
    totals = {"files": 0, "messages": 0, "turns": 0}
    if not root.is_dir():
        return totals
    titles = _session_titles(root.parent)
    with connect(db_path) as conn:
        version = conn.execute("SELECT version FROM scanner_state WHERE source='codex'").fetchone()
        rebuild = version is None or version[0] != 4
        for sid, title in titles.items():
            conn.execute("INSERT OR REPLACE INTO session_titles (session_id, title) VALUES (?, ?)", (sid, title))
        for path in root.rglob("*.jsonl"):
            try:
                stat = path.stat()
            except OSError:
                continue
            prior = conn.execute("SELECT mtime, bytes_read FROM files WHERE path=?", (str(path),)).fetchone()
            if not rebuild and prior and prior["mtime"] == stat.st_mtime and prior["bytes_read"] == stat.st_size:
                continue
            rows = parse_file(path)
            conn.execute("DELETE FROM messages WHERE source='codex' AND source_file=?", (str(path),))
            conn.execute("DELETE FROM codex_skill_uses WHERE source_file=?", (str(path),))
            for row in rows:
                conn.execute(INSERT, row)
                if row["type"] != "assistant" or not row["activity_json"]:
                    continue
                for event in json.loads(row["activity_json"]):
                    if event.get("kind") != "tool":
                        continue
                    for skill in _skill_reads(event.get("input")):
                        conn.execute("""
                            INSERT OR IGNORE INTO codex_skill_uses
                              (source_file, turn_uuid, session_id, project_slug, skill, timestamp)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            str(path), row["parent_uuid"] or row["uuid"], row["session_id"],
                            row["project_slug"], skill, event.get("timestamp") or row["timestamp"],
                        ))
            conn.execute(
                "INSERT OR REPLACE INTO files (path, mtime, bytes_read, scanned_at) VALUES (?, ?, ?, ?)",
                (str(path), stat.st_mtime, stat.st_size, time.time()),
            )
            totals["files"] += 1
            totals["messages"] += sum(row["type"] == "assistant" for row in rows)
            totals["turns"] += sum(row["type"] == "user" for row in rows)
        conn.execute("INSERT OR REPLACE INTO scanner_state (source, version) VALUES ('codex', 4)")
        conn.commit()
    return totals
