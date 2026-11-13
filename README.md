# Coding Agent Token Dashboard

[English](README.md) | [简体中文](README.zh-CN.md)

A local dashboard for understanding Claude Code and Codex token usage. It reads session records already on your computer and shows where tokens went across prompts, model calls, sessions, projects, caches, and skills.

The dashboard runs with Python's standard library and a browser. It needs no account, API key, package install, or frontend build.

## Features

- **Overview:** token totals and daily trends, model and project comparisons, and a Claude Code/Codex tool-use table.
- **Prompts:** rank user requests by total processed tokens or recency; inspect model calls and cache reads for each request.
- **Sessions:** browse named conversations, sorted by total tokens by default, and see per-prompt token and tool totals. Expand a prompt to inspect model calls, visible tool activity, results, and Codex compaction events.
- **Skills:** count Claude Code `Skill` calls and infer Codex skill use from reads of `SKILL.md`.

Use the source selector to view Claude Code, Codex, or both.

## Requirements

- Python 3.10 or newer
- A modern browser
- At least one local Claude Code or Codex session

## Quick start

```bash
git clone https://github.com/Horace564/coding-agent-token-dashboard.git
cd coding-agent-token-dashboard
python3 cli.py dashboard
```

On Windows, use `py -3 cli.py dashboard` if `python3` is unavailable.

The command scans local sessions, starts a server at `http://127.0.0.1:8080`, and opens the browser. It checks for new records every 30 seconds. Stop it with `Ctrl+C`.

## Data sources and accounting

| Source | Default session location | Available data |
| --- | --- | --- |
| Claude Code | `~/.claude/projects/` | Prompts, per-response usage, tool calls, and skill calls |
| Codex | `$CODEX_HOME/sessions` or `~/.codex/sessions` | Prompts, per-response usage, visible assistant and tool activity, compactions, and inferred skill use |

Session files are read without modification. The dashboard keeps its own SQLite cache at `~/.claude/token-dashboard.db`. Codex tool arguments and results are stored as bounded previews of up to 12,000 characters each.

**Total tokens** adds usage across model calls, including repeated cache reads. It is a cumulative usage figure, not the size of a single context window. The fresh input, output, cache read, and cache write columns show its components.

The dashboard reports token usage without estimating a dollar cost. Codex skill counts are inferred when a recorded shell command reads a `SKILL.md` file; one skill is counted at most once per user turn. The skill file size estimate is not measured token usage.

Codex's local rollout format can change. Cloud-only sessions and activity on other devices are outside the local scan. See [Known Limitations](docs/KNOWN_LIMITATIONS.md) for details.

## Commands

```bash
python3 cli.py scan       # refresh the SQLite cache, then exit
python3 cli.py today      # today's token totals
python3 cli.py stats      # all-time token totals
python3 cli.py dashboard  # scan and open the dashboard

python3 cli.py dashboard --no-open
python3 cli.py dashboard --no-scan
python3 cli.py dashboard --rebuild-db  # rebuild the cache from current JSONL files
python3 cli.py dashboard --reload    # restart the backend when Python files change
```

`--rebuild-db` creates a fresh SQLite cache and replaces the old one only after both sources have been scanned. Sessions whose JSONL files were deleted or moved out of the configured directories disappear from the dashboard. Original session files are untouched. Stop any other dashboard instance using the same database before rebuilding. This option cannot be combined with `--no-scan`.

On Windows, replace `python3` with `py -3`.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `HOST` | `127.0.0.1` | Server bind address |
| `PORT` | `8080` | Server port |
| `CLAUDE_PROJECTS_DIR` | `~/.claude/projects` | Claude Code session directory |
| `CODEX_HOME` | `~/.codex` | Codex local state directory |
| `CODEX_SESSIONS_DIR` | `$CODEX_HOME/sessions` | Codex session directory override |
| `TOKEN_DASHBOARD_DB` | `~/.claude/token-dashboard.db` | SQLite cache location |

The CLI also accepts `--projects-dir`, `--codex-dir`, and `--db`. For example:

```bash
python3 cli.py dashboard --projects-dir /path/to/claude/projects --codex-dir /path/to/codex/sessions --db /path/to/cache.db
```

Bind to `127.0.0.1` if your session history should remain accessible only from this computer. Press `Ctrl+B` or `Cmd+B` in the dashboard to blur sensitive text for screenshots.

## Development

```bash
python3 -m unittest discover tests
```

The backend uses Python's standard library and SQLite. The frontend is vanilla JavaScript with a bundled ECharts build. [CONTRIBUTING.md](CONTRIBUTING.md) covers development conventions.

Use `python3 cli.py dashboard --reload` during development. It watches Python source files once per second, restarts the backend after an edit, and reloads open dashboard pages after the server reconnects. The regular 30-second JSONL scan continues. If combined with `--rebuild-db`, the cache is rebuilt only on the first start. Stop the watcher with `Ctrl+C`.

## Acknowledgements

This project is a fork of [nateherkai/token-dashboard](https://github.com/nateherkai/token-dashboard) by Nathan Herkelman. The current dashboard adds Codex support and develops the session and usage views for both coding agents.

## License

[MIT](LICENSE).
