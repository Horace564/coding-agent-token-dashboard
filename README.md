# Token Dashboard

A local dashboard for Claude Code and Codex token usage. It reads Claude Code transcripts from `~/.claude/projects/` and local Codex session rollouts from `$CODEX_HOME/sessions` (normally `~/.codex/sessions`), then shows prompts, sessions, projects, models, cache usage, and token totals. Claude Code also has tool, skill, and tips views.

**Everything runs locally.** No data leaves your machine — no telemetry, no API calls for your data, no login.

![Overview tab — totals and daily charts](docs/images/dashboard-overview-top.jpg)

![Overview tab — per-project, per-model, top tools, recent sessions](docs/images/dashboard-overview-bottom.jpg)

## What this is useful for

- Seeing which of your prompts are expensive (surprise: they usually involve large tool results).
- Comparing token usage across projects you've worked on.
- Spotting wasteful patterns — the same file read twenty times in a session, a tool call returning 80k tokens.
- Understanding what a "cache hit" actually saves you.
- If you're on Pro or Max, confirming you're getting your money's worth in API-equivalent dollars.

## Prerequisites

- **Python 3.8 or newer** — already installed on macOS and most Linux. On Windows: `winget install Python.Python.3.12` or download from python.org.
- **Claude Code or Codex** with at least one local session. The dashboard can scan either source independently.
- **A web browser.** Any modern one.

No `pip install`. No Node.js. No build step.

## Quickstart

```bash
git clone https://github.com/nateherkai/token-dashboard.git
cd token-dashboard
python3 cli.py dashboard
```

> On Windows, if `python3` isn't on your PATH, substitute `py -3` for `python3` in every command below.

The command:
1. Scans `~/.claude/projects/` and `$CODEX_HOME/sessions` for local usage records.
2. Starts a local server at http://127.0.0.1:8080.
3. Opens your default browser to that URL.

Leave it running; it re-scans every 30 seconds and pushes updates live. Stop with `Ctrl+C`.

## Where the data comes from

Claude Code writes one JSONL file per session here:

| OS | Path |
|---|---|
| macOS / Linux | `~/.claude/projects/<project-slug>/<session-id>.jsonl` |
| Windows | `C:\Users\<you>\.claude\projects\<project-slug>\<session-id>.jsonl` |

The dashboard never modifies those files — it only reads them and keeps a local SQLite cache at `~/.claude/token-dashboard.db`.

To point at a different location:

```bash
python3 cli.py dashboard --projects-dir /path/to/projects --codex-dir /path/to/codex/sessions --db /path/to/cache.db
```

### Codex data and accounting

Codex sessions are scanned read-only from `$CODEX_HOME/sessions` or `~/.codex/sessions`. The importer stores timestamps, model names, project paths, user prompts, and token counts; it does not copy Codex assistant or tool output into the dashboard database. Session names come from Codex's local session index or state database when available. Select **All sources**, **Claude Code**, or **Codex** in the top bar. Tool, skill, and suggestion views currently use Claude Code records only.

Codex rollout files can contain both per-response usage and cumulative token snapshots. The importer uses per-response records when present and falls back to snapshot deltas for older files. Codex's on-disk rollout format is not a documented stable API, so new versions may need a parser update. `codex exec --json` is an officially documented source for future scripted runs, but does not backfill existing interactive sessions.

The dollar estimate in the dashboard covers Claude Code only. Codex token counts are displayed without a dollar figure because ChatGPT subscription usage is not an API bill. The SQLite cache remains at `~/.claude/token-dashboard.db` to preserve existing data.

### Environment variables

| Var | Default | Purpose |
|---|---|---|
| `PORT` | `8080` | Port the local web server listens on |
| `HOST` | `127.0.0.1` | Bind address. Keep the default. Setting `0.0.0.0` exposes your entire prompt history to anyone on your local network — don't do this on any network you don't fully control (no coffee-shop Wi-Fi, no coworking spaces). |
| `CLAUDE_PROJECTS_DIR` | `~/.claude/projects` | Where to scan for session JSONL files |
| `CODEX_HOME` | `~/.codex` | Codex's local state root |
| `CODEX_SESSIONS_DIR` | `$CODEX_HOME/sessions` | Override the Codex session directory directly |
| `TOKEN_DASHBOARD_DB` | `~/.claude/token-dashboard.db` | SQLite cache location |

Pricing lives in [`pricing.json`](pricing.json). Edit it directly if model prices change or to add a new plan.

## CLI reference

```bash
python3 cli.py scan          # populate / refresh the local DB, then exit
python3 cli.py today         # today's totals (terminal)
python3 cli.py stats         # all-time totals (terminal)
python3 cli.py tips          # active suggestions (terminal)
python3 cli.py dashboard     # scan + serve the UI at http://localhost:8080

# dashboard flags
python3 cli.py dashboard --no-open   # don't auto-open the browser
python3 cli.py dashboard --no-scan   # skip the initial scan (use cached DB only)
```

Change the port: `PORT=9000 python3 cli.py dashboard`.

## The 7 tabs

Overview, Sessions, and Projects include Codex data. Prompts, tools, skills, and tips currently describe Claude Code only. The source selector in the top bar filters usage views.

The dashboard is a single page with a hash-router tab bar across the top. Each tab is backed by its own JSON API under `/api/`:

- **Overview** — input/output/cache tokens, sessions, turns, Claude API-equivalent cost, daily charts, project/model comparisons, Claude tools, and recent sessions. This is the landing tab.
- **Prompts** — user prompts ranked by total processed tokens or recency. Each row shows model calls, cache reads, and total tokens across the turn. Click a row to see the full prompt.
- **Sessions** — named conversations with a turn-by-turn view of prompts and token usage; Claude Code also shows tool calls.
- **Projects** — per-project comparison: tokens, session counts, and which files were touched most.
- **Skills** — which skills you invoke most often, and (where we can measure them) their token cost. See [limitations](docs/KNOWN_LIMITATIONS.md#skills-token-counts-are-partial).
- **Tips** — rule-based suggestions for reducing token usage (repeated file reads, oversized tool results, low cache-hit rate, etc.).
- **Settings** — select the Claude pricing display plan. Codex usage remains token-only.

The Overview tab also has a built-in "What do these numbers mean?" panel that explains input/output/cache tokens in plain English.

## Troubleshooting

**"No data" or empty charts.** Run `python3 cli.py scan` once to populate the DB, then reload.

**Port 8080 already in use.** `PORT=9000 python3 cli.py dashboard`.

**Numbers look wrong / stuck.** The DB lives at `~/.claude/token-dashboard.db`. Delete it and re-run `python3 cli.py scan` to rebuild from scratch.

**Running the dashboard twice at the same time.** Don't — both processes will fight over the SQLite DB. Stop all instances before starting a new one.

## Accuracy note

Claude Code writes each assistant response 2–3 times to disk while it streams (the same API message gets snapshotted as output grows). The dashboard dedupes these by `message.id` so the final tally matches what the API actually billed. If you compare against another tool that sums every JSONL row, expect this dashboard's numbers to be lower — and closer to reality.

## Privacy

Nothing leaves your machine. No telemetry. No remote calls for your data. The browser fetches its JSON from `127.0.0.1`, and all JS/CSS/fonts are served from that same local server — ECharts is vendored into `web/`, and the UI falls back to system fonts rather than pulling from a font CDN. If you want to verify: `grep -r "https://" token_dashboard/ web/` — you'll find nothing.

## Tech stack

Python 3 (stdlib only) for the CLI, scanner, and HTTP server. SQLite for the local cache. Vanilla JS + ECharts for the UI, no build step. Dark theme, hash-based router, server-sent events for live refresh.

Data flow: `cli.py` calls the Claude and Codex scanners, which write to SQLite; `token_dashboard/server.py` exposes `/api/*` routes and serves `web/`.

## Further reading

- [`CLAUDE.md`](CLAUDE.md) — conventions and architecture overview (also picked up automatically by Claude Code)
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — how to develop and test
- [`docs/KNOWN_LIMITATIONS.md`](docs/KNOWN_LIMITATIONS.md) — rough edges
- [`docs/inspiration.md`](docs/inspiration.md) — prior art and how this project diverges

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). Short version: fork, `python3 -m unittest discover tests` before opening a PR, keep it stdlib-only.

## License

[MIT](LICENSE).
