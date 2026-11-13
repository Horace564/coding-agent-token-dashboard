# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Project overview

**Token Dashboard** — a local dashboard for Claude Code and Codex token usage, prompts, and session history. Claude Code also provides tool, skill, and tips analytics. Codex imports user prompts but not assistant or tool output.

Inspired by [phuryn/claude-usage](https://github.com/phuryn/claude-usage) but diverges in UI (vanilla JS + ECharts, dark theme, hash router, SSE refresh) and scope (expensive-prompt drill-down, skills view, tips engine, streaming-snapshot dedup). See `docs/inspiration.md` for the original's feature set and known limitations.

## Status

Working codebase. Python unit tests run with `python3 -m unittest discover tests`. Seven UI tabs wired up (Overview, Prompts, Sessions, Projects, Skills, Tips, Settings). Runs on macOS, Windows, and Linux.

## Architecture

- `cli.py` → `token_dashboard/scanner.py` and `token_dashboard/codex_scanner.py` → `~/.claude/token-dashboard.db` (SQLite)
- `token_dashboard/server.py` exposes JSON APIs (`/api/*`) + SSE stream (`/api/stream`) + static frontend (`web/`)
- `web/` is vanilla JS, no build step — hash router + ECharts

## Data source

Claude Code writes one JSONL file per session to `~/.claude/projects/<project-slug>/<session-id>.jsonl`. Each line is a message record; usage fields live at `message.usage` and model identifier at `message.model`. The scanner is incremental — it tracks each file's mtime and byte offset in the `files` table and only reads new bytes on subsequent scans.

Codex rollout files are read from `$CODEX_HOME/sessions` (default `~/.codex/sessions`). The Codex adapter prefers per-response `token_usage_record` data and falls back to legacy `event_msg.token_count` snapshots. It imports user prompts from message records, reads session names from the local index or state database, and rescans changed rollout files. Its on-disk format is not a stable public API.

## Conventions

- **Fully local.** No telemetry, no remote calls for user data. Tests run offline.
- **Stdlib only.** No `pip install`. If a new feature needs a third-party library, argue for it first — we're willing to pay ergonomics cost to keep install friction at zero.
- **SQLite parameter binding always.** Any f-string in a SQL statement must interpolate only internal, caller-controlled values (column names, placeholder lists). User-reachable values go through `?`.
- **Small files with clear responsibilities.** If a file grows past ~400 lines or accretes three distinct concerns, split it.
- **Streaming-snapshot dedup.** When adding scanner logic that joins the `messages` table, remember `(session_id, message_id)` is the dedup key, not `uuid`. See `scanner._evict_prior_snapshots` and the migration note in `db._migrate_add_message_id`.

## Customizing

Env vars: `PORT` (default 8080), `HOST` (default 127.0.0.1), `CLAUDE_PROJECTS_DIR`, `CODEX_HOME`, `CODEX_SESSIONS_DIR`, `TOKEN_DASHBOARD_DB`. Claude pricing lives in `pricing.json`. See README.md § Environment variables for details.

## Known limitations

See `docs/KNOWN_LIMITATIONS.md`. Current summary: Skills `tokens_per_call` is populated only for skills installed under the three scanned roots (`~/.claude/skills/`, `~/.claude/scheduled-tasks/`, `~/.claude/plugins/`); project-local skills and subagent-dispatched skills show invocation counts but blank token counts.

## Verifying changes

```bash
python3 -m unittest discover tests        # all tests
python3 cli.py dashboard --no-open        # start the server
curl http://127.0.0.1:8080/api/overview   # sanity-check an endpoint
```
