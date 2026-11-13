# Known Limitations

## Codex imports local usage only

The Codex importer reads local rollout JSONL under `$CODEX_HOME/sessions`. Cloud sessions or other devices are not included. Codex's rollout format is not a stable public API. The dashboard imports token counts, model, project, session names, prompts, and visible tool activity. Codex Skills counts are inferred from shell commands that read `SKILL.md`, so preloaded or externally provided skills and reads through other tools may be missed. The general tools breakdown remains unavailable for Codex. Changed Codex files are reparsed in full so per-response and cumulative records cannot be counted twice.

None of these are blockers — the dashboard still gives you useful information. They're the rough edges you'll notice if you look hard.

## Skills token counts are partial

The Skills route shows Claude Code Skill calls and inferred Codex skill reads, their counts, sessions, and last use. Codex counts each skill at most once per user turn. The **tokens-per-call** column estimates the size of `SKILL.md` for skills found under Claude or Codex user/plugin directories, `~/.agents/skills/`, or the current project's `.codex/skills/`. Skills registered elsewhere (such as another project's local skills) show invocation counts but leave this column blank.

This column is an approximate file size, not the actual tokens consumed by a skill invocation.

## Cowork sessions are invisible

If you use Claude's Cowork mode (server-side sessions, not local `claude` CLI), those sessions don't write JSONL to `~/.claude/projects/` and the dashboard can't see them.

## First scan can be slow

The first `python3 cli.py scan` on a heavy user's machine can read tens of MB across hundreds of JSONLs. Claude scans then use byte offsets; Codex scans skip unchanged files and reparse changed files in full.

## Running two dashboards against the same DB

Both will fight over the SQLite file and you'll see inconsistent numbers and occasional `database is locked` errors. Only run one at a time. If you want to view the dashboard from a second device, use `HOST=0.0.0.0` on the one running machine and point the second device's browser at it.
