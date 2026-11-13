# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Project overview

**Coding Agent Token Dashboard** — a local dashboard for Claude Code and Codex token usage, prompts, session history, visible tool activity, and skills. Codex skill counts are inferred from recorded reads of `SKILL.md`.

The fork attribution is in `README.md` under Acknowledgements. `docs/inspiration.md` records earlier inspiration and design context.

## Status

Working codebase. Python unit tests run with `python3 -m unittest discover tests`. Five UI tabs are wired up (Overview, Prompts, Sessions, Projects, Skills). Runs on macOS, Windows, and Linux.

## Architecture

- `cli.py` → `token_dashboard/scanner.py` and `token_dashboard/codex_scanner.py` → `~/.claude/token-dashboard.db` (SQLite)
- `token_dashboard/server.py` exposes JSON APIs (`/api/*`) + SSE stream (`/api/stream`) + static frontend (`web/`)
- `web/` is vanilla JS, no build step — hash router + ECharts

## Data source

Claude Code writes one JSONL file per session to `~/.claude/projects/<project-slug>/<session-id>.jsonl`. Each line is a message record; usage fields live at `message.usage` and model identifier at `message.model`. The scanner is incremental — it tracks each file's mtime and byte offset in the `files` table and only reads new bytes on subsequent scans.

Codex rollout files are read from `$CODEX_HOME/sessions` (default `~/.codex/sessions`). The Codex adapter prefers per-response `token_usage_record` data and falls back to legacy `event_msg.token_count` snapshots. It imports user prompts and bounded previews of visible assistant and tool activity, reads session names from the local index or state database, and rescans changed rollout files. Its on-disk format is not a stable public API.

## Conventions

- **Fully local.** No telemetry, no remote calls for user data. Tests run offline.
- **Stdlib only.** No `pip install`. If a new feature needs a third-party library, argue for it first — we're willing to pay ergonomics cost to keep install friction at zero.
- **SQLite parameter binding always.** Any f-string in a SQL statement must interpolate only internal, caller-controlled values (column names, placeholder lists). User-reachable values go through `?`.
- **Small files with clear responsibilities.** If a file grows past ~400 lines or accretes three distinct concerns, split it.
- **Streaming-snapshot dedup.** When adding scanner logic that joins the `messages` table, remember `(session_id, message_id)` is the dedup key, not `uuid`. See `scanner._evict_prior_snapshots` and the migration note in `db._migrate_add_message_id`.

## Customizing

Env vars: `PORT` (default 8080), `HOST` (default 127.0.0.1), `CLAUDE_PROJECTS_DIR`, `CODEX_HOME`, `CODEX_SESSIONS_DIR`, `TOKEN_DASHBOARD_DB`. See README.md § Configuration for details.

## Known limitations

See `docs/KNOWN_LIMITATIONS.md`. Skill file token estimates depend on whether the skill is found in the scanned local directories; Codex skill counts are inferred from recorded file reads.

## Verifying changes

```bash
python3 -m unittest discover tests        # all tests
python3 cli.py dashboard --no-open        # start the server
curl http://127.0.0.1:8080/api/overview   # sanity-check an endpoint
```
