# Graph Report - coding-agent-token-dashboard  (2026-11-11)

## Corpus Check
- 43 files · ~32,769 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 4 file(s) not represented in the graph (top: (none) 2, .jsonl 1, .css 1)

## Summary
- 1085 nodes · 2969 edges · 64 communities (54 shown, 10 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 168 edges (avg confidence: 0.85)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `53756505`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- echarts.min.js
- n
- rt
- _l
- db.py
- codex_scanner.py
- connect
- init_db
- scanner.py
- ref
- scan_dir
- E
- fi
- fv
- cost_for
- CatalogTests
- Y
- ug
- w_
- z
- vg
- U
- A
- to
- scan_dir
- ed
- D
- mx
- server.py
- test_scanner_rescan.py
- q
- v
- Vr
- kp
- T
- charts.js
- Token Dashboard
- project_name_for
- $
- ServerTests
- k
- Pn
- ms
- scan_codex_dir
- y
- qB
- Inspiration: phuryn/claude-usage
- CLAUDE.md
- G
- CliTests
- qn
- vV
- yb
- Vr
- te
- Li
- Rb
- Contributing
- Known Limitations
- Where the data comes from
- AGENTS.md

## God Nodes (most connected - your core abstractions)
1. `E()` - 125 edges
2. `n()` - 82 edges
3. `Y()` - 60 edges
4. `T()` - 58 edges
5. `U()` - 56 edges
6. `z()` - 45 edges
7. `A()` - 40 edges
8. `init_db()` - 38 edges
9. `connect()` - 38 edges
10. `X()` - 35 edges

## Surprising Connections (you probably didn't know these)
- `Opening a pull request` --references--> `main()`  [INFERRED]
  CONTRIBUTING.md → cli.py
- `Conventions` --references--> `_migrate_add_message_id()`  [INFERRED]
  CLAUDE.md → token_dashboard/db.py
- `Conventions` --references--> `_evict_prior_snapshots()`  [INFERRED]
  CLAUDE.md → token_dashboard/scanner.py
- `cmd_scan()` --calls--> `scan_codex_dir()`  [EXTRACTED]
  cli.py → token_dashboard/codex_scanner.py
- `cmd_scan()` --calls--> `scan_dir()`  [EXTRACTED]
  cli.py → token_dashboard/scanner.py

## Import Cycles
- None detected.

## Communities (64 total, 10 thin omitted)

### Community 0 - "echarts.min.js"
Cohesion: 0.03
Nodes (20): bk(), ct(), da(), ea(), eI(), Ek(), fa(), ga() (+12 more)

### Community 1 - "n"
Cohesion: 0.14
Nodes (15): F(), ir(), Jm(), k(), ki(), mt(), n(), no() (+7 more)

### Community 2 - "rt"
Cohesion: 0.17
Nodes (16): ac(), dc(), Dm(), DO(), ec(), fc(), GC(), ic() (+8 more)

### Community 3 - "_l"
Cohesion: 0.08
Nodes (43): ap(), bl(), Cl(), cp(), dp(), el(), ep(), Fl() (+35 more)

### Community 4 - "db.py"
Cohesion: 0.08
Nodes (13): ProjectNameInQueriesTests, QueryTests, best_project_name(), daily_token_breakdown(), expensive_prompts(), model_breakdown(), project_summary(), _range_clause() (+5 more)

### Community 5 - "codex_scanner.py"
Cohesion: 0.16
Nodes (11): _delta(), _item_turn(), _message_text(), _number(), parse_file(), _preview(), _read_records(), _session_titles() (+3 more)

### Community 6 - "connect"
Cohesion: 0.20
Nodes (15): CacheTipTests, DismissTests, OutlierTests, RepeatTipTests, RightSizeTests, connect(), all_tips(), cache_discipline_tips() (+7 more)

### Community 7 - "init_db"
Cohesion: 0.12
Nodes (16): cmd_dashboard(), cmd_scan(), cmd_stats(), cmd_tips(), cmd_today(), _codex_sessions(), _db_path(), main() (+8 more)

### Community 8 - "scanner.py"
Cohesion: 0.13
Nodes (15): Conventions, _load(), ParseRecordTests, SidechainTests, ToolExtractionTests, _write_jsonl(), _migrate_add_message_id(), _evict_prior_snapshots() (+7 more)

### Community 9 - "ref"
Cohesion: 0.09
Nodes (13): RANGES, SORTS, eventsFor(), renderActivity(), renderEvent(), renderList(), renderPrompt(), renderSession() (+5 more)

### Community 10 - "scan_dir"
Cohesion: 0.17
Nodes (6): _streaming_partial(), StreamingDedupTests, _write_jsonl(), WalkTests, _project_slug(), scan_dir()

### Community 11 - "E"
Cohesion: 0.09
Nodes (28): dd(), df(), E(), ez(), a(), s(), fe(), Gd() (+20 more)

### Community 12 - "fi"
Cohesion: 0.16
Nodes (14): be(), bh(), cw(), di(), Dn(), Fh(), fi(), gh() (+6 more)

### Community 13 - "fv"
Cohesion: 0.15
Nodes (19): cv(), dv(), ev(), fv(), gg(), ha(), hv(), iv() (+11 more)

### Community 14 - "cost_for"
Cohesion: 0.18
Nodes (6): CostTests, PlanFormatTests, cost_for(), format_for_user(), load_pricing(), _tier_from_name()

### Community 15 - "CatalogTests"
Cohesion: 0.19
Nodes (4): CatalogTests, _write(), scan_catalog(), _slugs_for()

### Community 16 - "Y"
Cohesion: 0.13
Nodes (21): af(), c(), ia(), id(), jy(), kn(), Lb(), mi() (+13 more)

### Community 17 - "ug"
Cohesion: 0.15
Nodes (14): ag(), bp(), cg(), dg(), hg(), lg(), ng(), pg() (+6 more)

### Community 18 - "w_"
Cohesion: 0.16
Nodes (16): aA(), ba(), ib(), mA(), A(), nb(), ot(), pW() (+8 more)

### Community 19 - "z"
Cohesion: 0.12
Nodes (17): Jo(), JT(), kz(), lC(), nE(), O(), pk(), Pz() (+9 more)

### Community 20 - "vg"
Cohesion: 0.14
Nodes (15): BG(), Cf(), cs(), fg(), fz(), gz(), Ig(), io() (+7 more)

### Community 21 - "U"
Cohesion: 0.15
Nodes (17): ay(), go(), s(), gp(), hy(), mp(), rd(), m() (+9 more)

### Community 22 - "A"
Cohesion: 0.08
Nodes (32): A(), Al(), at(), B(), bC(), bo(), Cr(), Dl() (+24 more)

### Community 23 - "to"
Cohesion: 0.16
Nodes (14): Ax(), co(), Cx(), dx(), fB(), ho(), Jr(), Ks() (+6 more)

### Community 24 - "scan_dir"
Cohesion: 0.31
Nodes (4): _assistant(), EndToEndTotalsTests, _usage(), _user()

### Community 25 - "ed"
Cohesion: 0.21
Nodes (9): Ad(), ed(), kd(), Kr(), Ld(), nd(), Od(), td() (+1 more)

### Community 26 - "D"
Cohesion: 0.11
Nodes (18): AS(), D(), Eh(), iy(), ls(), mh(), Oh(), oy() (+10 more)

### Community 27 - "mx"
Cohesion: 0.19
Nodes (14): Bx(), Gx(), Hx(), jx(), kg(), mx(), qx(), Ux() (+6 more)

### Community 28 - "server.py"
Cohesion: 0.09
Nodes (16): SkillBreakdownTests, _free_port(), skill_breakdown(), get_plan(), set_plan(), build_handler(), do_GET(), do_HEAD() (+8 more)

### Community 29 - "test_scanner_rescan.py"
Cohesion: 0.31
Nodes (3): _assistant_with_tool_use(), RescanIdempotencyTests, _user_record()

### Community 30 - "q"
Cohesion: 0.12
Nodes (17): ak(), Am(), ao(), Cm(), eo(), Ix(), km(), Lo() (+9 more)

### Community 31 - "v"
Cohesion: 0.19
Nodes (10): Cn(), hc(), oc(), oR(), rR(), Sr(), wr(), m() (+2 more)

### Community 32 - "Vr"
Cohesion: 0.24
Nodes (10): br(), bv(), ce(), er(), n(), he(), mv(), nr() (+2 more)

### Community 33 - "kp"
Cohesion: 0.15
Nodes (13): bm(), Dt(), Ht(), Hu(), JA(), kA(), kp(), kt() (+5 more)

### Community 34 - "T"
Cohesion: 0.11
Nodes (23): aV(), bf(), eb(), ef(), Eg(), ES(), et(), Ff() (+15 more)

### Community 35 - "charts.js"
Cohesion: 0.24
Nodes (11): barChart(), BASE, donutChart(), groupedBarChart(), lineChart(), mount(), PALETTE, stackedBarChart() (+3 more)

### Community 36 - "Token Dashboard"
Cohesion: 0.15
Nodes (13): Accuracy note, CLI reference, Contributing, Further reading, License, Prerequisites, Privacy, Quickstart (+5 more)

### Community 38 - "$"
Cohesion: 0.29
Nodes (11): $$, api(), boot(), buildTopbar(), COMPACT, firstRun(), fmt, render() (+3 more)

### Community 40 - "k"
Cohesion: 0.29
Nodes (6): ab(), Im(), mm(), Ob(), sB(), Tm()

### Community 41 - "Pn"
Cohesion: 0.13
Nodes (16): au(), bu(), cc(), cu(), du(), fu(), i(), mu() (+8 more)

### Community 42 - "ms"
Cohesion: 0.29
Nodes (7): bn(), In(), mn(), ms(), Ss(), vn(), yn()

### Community 43 - "scan_codex_dir"
Cohesion: 0.35
Nodes (5): CodexScannerTests, _line(), _usage(), scan_codex_dir(), overview_totals()

### Community 45 - "qB"
Cohesion: 0.40
Nodes (6): jB(), kb(), mB(), qB(), vB(), zB()

### Community 46 - "Inspiration: phuryn/claude-usage"
Cohesion: 0.22
Nodes (9): CLI commands, Core files, Data shape, Inspiration: phuryn/claude-usage, Limitations worth addressing in our version, Tech stack, What it captures, What it does (+1 more)

### Community 47 - "CLAUDE.md"
Cohesion: 0.25
Nodes (7): Architecture, Customizing, Data source, Known limitations, Project overview, Status, Verifying changes

### Community 48 - "G"
Cohesion: 0.11
Nodes (29): aw(), bi(), ew(), fw(), G(), GR(), gw(), hi() (+21 more)

### Community 50 - "qn"
Cohesion: 0.29
Nodes (10): Fn(), Gn(), Hn(), ii(), jn(), ni(), qn(), ri() (+2 more)

### Community 51 - "vV"
Cohesion: 0.28
Nodes (7): Dy(), ky(), vV(), h(), l(), u(), zV()

### Community 52 - "yb"
Cohesion: 0.09
Nodes (23): An(), Bs(), Bw(), cb(), db(), ds(), gb(), gs() (+15 more)

### Community 53 - "Vr"
Cohesion: 0.11
Nodes (20): je(), s(), Ke(), Lh(), M(), nt(), pb(), b() (+12 more)

### Community 54 - "te"
Cohesion: 0.67
Nodes (4): ee(), le(), te(), ue()

### Community 59 - "Contributing"
Cohesion: 0.25
Nodes (8): Code style, Contributing, Ideas that would genuinely help, License, Opening a pull request, Running the dashboard locally, Running the tests, What we're not looking for

### Community 60 - "Known Limitations"
Cohesion: 0.25
Nodes (8): Codex imports local usage only, Cost for Pro / Max / Max-20x users is shown as API-equivalent, not subscription value, Cowork sessions are invisible, First scan can be slow, Known Limitations, Non-standard model names get tier-fallback pricing, Running two dashboards against the same DB, Skills token counts are partial

### Community 63 - "Where the data comes from"
Cohesion: 0.67
Nodes (3): Codex data and accounting, Environment variables, Where the data comes from

## Knowledge Gaps
- **10 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Conventions` connect `scanner.py` to `CLAUDE.md`?**
  _High betweenness centrality (0.019) - this node is a cross-community bridge._
- **Are the 66 inferred relationships involving `n()` (e.g. with `echarts.min.js` and `Al()`) actually correct?**
  _`n()` has 66 INFERRED edges - model-reasoned connections that need verification._
- **Should `echarts.min.js` be split into smaller, more focused modules?**
  _Cohesion score 0.02762268586541287 - nodes in this community are weakly interconnected._
- **Why does `init_db()` connect `init_db` to `db.py`, `connect`, `scanner.py`, `scan_dir`, `scan_dir`, `server.py`, `test_scanner_rescan.py`?**
  _High betweenness centrality (0.017) - this node is a cross-community bridge._
- **Are the 8 inferred relationships involving `T()` (e.g. with `c()` and `Eg()`) actually correct?**
  _`T()` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Should `n` be split into smaller, more focused modules?**
  _Cohesion score 0.1437908496732026 - nodes in this community are weakly interconnected._
- **Why does `_migrate_add_message_id()` connect `scanner.py` to `db.py`, `init_db`?**
  _High betweenness centrality (0.014) - this node is a cross-community bridge._