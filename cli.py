"""Token Dashboard CLI entrypoint."""
from __future__ import annotations

import argparse
import os
import sqlite3
import tempfile
import webbrowser
from contextlib import closing, contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from token_dashboard.db import init_db, default_db_path, overview_totals
from token_dashboard.scanner import scan_dir
from token_dashboard.codex_scanner import default_codex_sessions_dir, scan_codex_dir


def _db_path(args) -> str:
    return args.db or os.environ.get("TOKEN_DASHBOARD_DB") or str(default_db_path())


def _projects(args) -> str:
    return (
        args.projects_dir
        or os.environ.get("CLAUDE_PROJECTS_DIR")
        or str(Path.home() / ".claude" / "projects")
    )


def _codex_sessions(args) -> str:
    return args.codex_dir or os.environ.get("CODEX_SESSIONS_DIR") or str(default_codex_sessions_dir())


@contextmanager
def _dashboard_lock(db_path: str):
    """Keep two dashboard processes from rebuilding or serving the same DB."""
    lock_path = Path(db_path).expanduser().with_name(Path(db_path).name + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+b") as lock:
        if os.name == "nt":
            import msvcrt

            lock.seek(0, os.SEEK_END)
            if lock.tell() == 0:
                lock.write(b"\0")
                lock.flush()
            lock.seek(0)
            try:
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise RuntimeError(f"Another dashboard is using {db_path}") from exc
        else:
            import fcntl

            try:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise RuntimeError(f"Another dashboard is using {db_path}") from exc
        try:
            yield
        finally:
            if os.name == "nt":
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def _rebuild_db(db_path: str, projects_dir: str, codex_dir: str) -> None:
    """Build a fresh cache beside the old one, then replace it on success."""
    target = Path(db_path).expanduser()
    roots = {"claude": Path(projects_dir).expanduser(), "codex": Path(codex_dir).expanduser()}
    if not any(root.is_dir() for root in roots.values()):
        raise FileNotFoundError("Neither Claude nor Codex session directory exists; cache was left unchanged")
    if target.is_file():
        with closing(sqlite3.connect(target)) as conn:
            columns = {row[1] for row in conn.execute("PRAGMA table_info(messages)")}
            if columns:
                source_column = "source" if "source" in columns else "'claude'"
                cached_sources = {row[0] for row in conn.execute(f"SELECT DISTINCT {source_column} FROM messages")}
                for source, root in roots.items():
                    if source in cached_sources and not root.is_dir():
                        raise FileNotFoundError(
                            f"{source} session directory is missing: {root}; cache was left unchanged"
                        )
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, fresh_name = tempfile.mkstemp(prefix=f".{target.name}.rebuild-", suffix=".db", dir=target.parent)
    os.close(fd)
    fresh = Path(fresh_name)
    try:
        init_db(fresh)
        scan_dir(roots["claude"], fresh)
        scan_codex_dir(roots["codex"], fresh)
        os.replace(fresh, target)
    finally:
        fresh.unlink(missing_ok=True)


def _today_range():
    now = datetime.now(timezone.utc)
    start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc).isoformat()
    end = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    return start, end


def cmd_scan(args):
    db = _db_path(args)
    init_db(db)
    n = scan_dir(_projects(args), db)
    codex = scan_codex_dir(_codex_sessions(args), db)
    print(f"Token Dashboard: Claude scanned {n['files']} files, {n['messages']} messages, {n['tools']} tool calls")
    print(f"Token Dashboard: Codex scanned {codex['files']} files, {codex['messages']} responses, {codex['turns']} turns")


def cmd_today(args):
    db = _db_path(args)
    init_db(db)
    s, e = _today_range()
    t = overview_totals(db, since=s, until=e, source=None if args.source == "all" else args.source)
    print("Token Dashboard — today")
    print(f"  sessions: {t['sessions']}    turns: {t['turns']}")
    print(f"  input:    {t['input_tokens']:>12,}    output: {t['output_tokens']:>12,}")
    print(f"  cache rd: {t['cache_read_tokens']:>12,}    cache cr: {t['cache_create_5m_tokens']+t['cache_create_1h_tokens']:>12,}")


def cmd_stats(args):
    db = _db_path(args)
    init_db(db)
    t = overview_totals(db, source=None if args.source == "all" else args.source)
    print("Token Dashboard — all time")
    print(f"  sessions: {t['sessions']}    turns: {t['turns']}")
    print(f"  input:    {t['input_tokens']:>12,}    output: {t['output_tokens']:>12,}")


def cmd_dashboard(args):
    if args.reload:
        from token_dashboard.dev_reload import run_reloader
        return run_reloader(args, Path(__file__))
    db = _db_path(args)
    projects_dir, codex_dir = _projects(args), _codex_sessions(args)
    with _dashboard_lock(db):
        if args.rebuild_db:
            _rebuild_db(db, projects_dir, codex_dir)
            print(f"Rebuilt SQLite cache: {db}")
        else:
            init_db(db)
            if not args.no_scan:
                scan_dir(projects_dir, db)
                scan_codex_dir(codex_dir, db)
        from token_dashboard.server import run

        host = os.environ.get("HOST", "127.0.0.1")
        port = int(os.environ.get("PORT", "8080"))
        url = f"http://{host}:{port}/"
        if not args.no_open:
            webbrowser.open(url)
        print(f"Token Dashboard listening on {url}")
        run(host, port, db, projects_dir, codex_dir)


def main():
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--db", help="SQLite path (default ~/.claude/token-dashboard.db)")
    common.add_argument("--projects-dir", help="JSONL root (default ~/.claude/projects)")
    common.add_argument("--codex-dir", help="Codex rollout root (default $CODEX_HOME/sessions or ~/.codex/sessions)")
    common.add_argument("--source", choices=("all", "claude", "codex"), default="all", help="Usage source for today/stats")

    p = argparse.ArgumentParser(prog="token-dashboard", description="Local Claude Code and Codex usage dashboard", parents=[common])
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("scan",  parents=[common]).set_defaults(func=cmd_scan)
    sub.add_parser("today", parents=[common]).set_defaults(func=cmd_today)
    sub.add_parser("stats", parents=[common]).set_defaults(func=cmd_stats)
    d = sub.add_parser("dashboard", parents=[common])
    scan_options = d.add_mutually_exclusive_group()
    scan_options.add_argument("--no-scan", action="store_true")
    scan_options.add_argument("--rebuild-db", action="store_true", help="rebuild the SQLite cache from current JSONL files before starting")
    d.add_argument("--no-open", action="store_true")
    d.add_argument("--reload", action="store_true", help="restart the development server when Python files change")
    d.set_defaults(func=cmd_dashboard)
    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
