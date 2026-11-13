"""Development-only supervisor for restarting the dashboard on Python edits."""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path


def _child_args(args, first_start: bool) -> list[str]:
    command = ["dashboard"]
    for flag, value in (("--db", args.db), ("--projects-dir", args.projects_dir),
                        ("--codex-dir", args.codex_dir)):
        if value:
            command.extend((flag, value))
    if args.source != "all":
        command.extend(("--source", args.source))
    if args.no_scan:
        command.append("--no-scan")
    elif args.rebuild_db and first_start:
        command.append("--rebuild-db")
    if args.no_open or not first_start:
        command.append("--no-open")
    return command


def _backend_snapshot(root: Path) -> tuple:
    files = [*root.glob("*.py"), *(root / "token_dashboard").rglob("*.py")]
    result = []
    for path in files:
        try:
            stat = path.stat()
        except OSError:
            continue
        result.append((str(path), stat.st_mtime_ns, stat.st_size))
    return tuple(sorted(result))


def _stop(child: subprocess.Popen | None) -> None:
    if child is None or child.poll() is not None:
        return
    child.terminate()
    try:
        child.wait(timeout=5)
    except subprocess.TimeoutExpired:
        child.kill()
        child.wait()


def run_reloader(args, cli_path: Path) -> None:
    root = cli_path.resolve().parent
    command = [sys.executable, str(cli_path.resolve())]
    flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0

    def start(first_start: bool) -> subprocess.Popen:
        return subprocess.Popen(
            [*command, *_child_args(args, first_start)],
            cwd=root, creationflags=flags,
        )

    snapshot = _backend_snapshot(root)
    print("Watching Python backend files; press Ctrl+C to stop.", flush=True)
    child = start(True)
    try:
        while True:
            time.sleep(1)
            current = _backend_snapshot(root)
            if current != snapshot:
                snapshot = current
                print("Backend changed; restarting dashboard...", flush=True)
                _stop(child)
                child = start(False)
            elif child is not None and child.poll() is not None:
                print(f"Dashboard exited ({child.returncode}); waiting for a Python edit to retry.", flush=True)
                child = None
    except KeyboardInterrupt:
        print("Stopping dashboard...", flush=True)
    finally:
        _stop(child)
