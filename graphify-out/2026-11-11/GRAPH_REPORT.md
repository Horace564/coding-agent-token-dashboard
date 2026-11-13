# Graph Report - coding-agent-token-dashboard  (2026-11-09)

## Corpus Check
- 43 files · ~31,359 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 4 file(s) not represented in the graph (top: (none) 2, .jsonl 1, .css 1)

## Summary
- 1073 nodes · 2934 edges · 66 communities (58 shown, 8 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 166 edges (avg confidence: 0.85)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `53756505`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- echarts.min.js
- n
- ew
- _l
- server.py
- db.py
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
- j
- z
- vg
- U
- A
- T
- scan_dir
- ed
- D
- mx
- server.py
- test_scanner_rescan.py
- q
- vg
- Vr
- kp
- T
- charts.js
- Token Dashboard
- project_name_for
- $
- ServerTests
- k
- Wt
- Ts
- scan_codex_dir
- k
- Cl
- Inspiration: phuryn/claude-usage
- CLAUDE.md
- xw
- CliTests
- qn
- vV
- yb
- je
- Yg
- Li
- Rb
- Contributing
- Known Limitations
- test_pricing.py
- Where the data comes from
- AGENTS.md
- ez

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
- `_codex_sessions()` --calls--> `default_codex_sessions_dir()`  [EXTRACTED]
  cli.py → token_dashboard/codex_scanner.py
- `cmd_scan()` --calls--> `scan_codex_dir()`  [EXTRACTED]
  cli.py → token_dashboard/codex_scanner.py

## Import Cycles
- None detected.

## Communities (66 total, 8 thin omitted)

### Community 0 - "echarts.min.js"
Cohesion: 0.03
Nodes (19): BG(), bk(), ct(), ea(), Ek(), F(), fg(), jf() (+11 more)

### Community 1 - "n"
Cohesion: 0.16
Nodes (15): c(), dc(), Dm(), ir(), ki(), n(), no(), ps() (+7 more)

### Community 2 - "ew"
Cohesion: 0.30
Nodes (12): aw(), bi(), ew(), hi(), mw(), Nw(), qs(), Rw() (+4 more)

### Community 3 - "_l"
Cohesion: 0.12
Nodes (31): ap(), bm(), cp(), dp(), ep(), fp(), hp(), Ht() (+23 more)

### Community 4 - "server.py"
Cohesion: 0.09
Nodes (18): ProjectNameInQueriesTests, QueryTests, SkillBreakdownTests, daily_token_breakdown(), expensive_prompts(), model_breakdown(), project_summary(), _range_clause() (+10 more)

### Community 5 - "db.py"
Cohesion: 0.11
Nodes (8): _delta(), _number(), parse_file(), _read_records(), _session_titles(), _tokens(), _user_text(), _encode_slug()

### Community 6 - "connect"
Cohesion: 0.19
Nodes (15): CacheTipTests, DismissTests, OutlierTests, RepeatTipTests, RightSizeTests, connect(), all_tips(), cache_discipline_tips() (+7 more)

### Community 7 - "init_db"
Cohesion: 0.14
Nodes (14): cmd_dashboard(), cmd_scan(), cmd_stats(), cmd_tips(), cmd_today(), _codex_sessions(), _db_path(), main() (+6 more)

### Community 8 - "scanner.py"
Cohesion: 0.13
Nodes (15): Conventions, _load(), ParseRecordTests, SidechainTests, ToolExtractionTests, _write_jsonl(), _migrate_add_message_id(), _evict_prior_snapshots() (+7 more)

### Community 9 - "ref"
Cohesion: 0.09
Nodes (6): RANGES, SORTS, renderList(), renderSession(), shortSessionId(), RANGES

### Community 10 - "scan_dir"
Cohesion: 0.26
Nodes (3): _streaming_partial(), StreamingDedupTests, _write_jsonl()

### Community 11 - "E"
Cohesion: 0.11
Nodes (22): Cm(), df(), E(), eo(), fe(), hf(), il(), Lo() (+14 more)

### Community 12 - "fi"
Cohesion: 0.12
Nodes (18): be(), bh(), cw(), di(), Dn(), Fh(), fi(), gh() (+10 more)

### Community 13 - "fv"
Cohesion: 0.12
Nodes (23): cv(), dv(), ee(), ev(), fv(), gg(), ha(), hv() (+15 more)

### Community 14 - "cost_for"
Cohesion: 0.35
Nodes (3): CostTests, cost_for(), _tier_from_name()

### Community 15 - "CatalogTests"
Cohesion: 0.19
Nodes (4): CatalogTests, _write(), scan_catalog(), _slugs_for()

### Community 16 - "Y"
Cohesion: 0.12
Nodes (21): af(), eI(), go(), s(), ia(), it(), jy(), kn() (+13 more)

### Community 17 - "ug"
Cohesion: 0.13
Nodes (17): ag(), bp(), cg(), dg(), gp(), hg(), lg(), mp() (+9 more)

### Community 18 - "j"
Cohesion: 0.05
Nodes (51): aA(), ac(), Am(), ba(), br(), Cn(), da(), eb() (+43 more)

### Community 19 - "z"
Cohesion: 0.15
Nodes (15): io(), Jo(), JT(), lC(), nE(), O(), pk(), sy() (+7 more)

### Community 20 - "vg"
Cohesion: 0.25
Nodes (8): Cf(), cs(), fz(), gz(), Ig(), mf(), Pf(), yf()

### Community 21 - "U"
Cohesion: 0.12
Nodes (26): ay(), bv(), hy(), id(), kl(), M(), mv(), nt() (+18 more)

### Community 22 - "A"
Cohesion: 0.10
Nodes (25): A(), Al(), bC(), bo(), Cr(), Dl(), Dr(), fR() (+17 more)

### Community 23 - "T"
Cohesion: 0.43
Nodes (8): bf(), Ff(), nf(), of(), rf(), tf(), wo(), zf()

### Community 24 - "scan_dir"
Cohesion: 0.17
Nodes (7): _assistant(), EndToEndTotalsTests, _usage(), _user(), WalkTests, _project_slug(), scan_dir()

### Community 25 - "ed"
Cohesion: 0.21
Nodes (9): Ad(), ed(), kd(), Kr(), Ld(), nd(), Od(), td() (+1 more)

### Community 26 - "D"
Cohesion: 0.08
Nodes (29): AS(), Ax(), co(), Cx(), D(), dx(), Eh(), ho() (+21 more)

### Community 27 - "mx"
Cohesion: 0.17
Nodes (15): Bx(), fB(), Gx(), Hx(), jx(), kg(), mx(), qx() (+7 more)

### Community 28 - "server.py"
Cohesion: 0.13
Nodes (8): _free_port(), default_codex_sessions_dir(), _clamp_limit(), run(), _scan_loop(), _serve_static(), cached_catalog(), tokens_for()

### Community 29 - "test_scanner_rescan.py"
Cohesion: 0.31
Nodes (3): _assistant_with_tool_use(), RescanIdempotencyTests, _user_record()

### Community 30 - "q"
Cohesion: 0.12
Nodes (15): ak(), ao(), DO(), ef(), Gl(), Ix(), Jm(), km() (+7 more)

### Community 31 - "vg"
Cohesion: 0.40
Nodes (6): cc(), i(), og(), ut(), vg(), h()

### Community 32 - "Vr"
Cohesion: 0.19
Nodes (13): at(), B(), ce(), er(), n(), he(), nr(), pe() (+5 more)

### Community 33 - "kp"
Cohesion: 0.33
Nodes (6): Dt(), Hu(), JA(), kt(), QA(), zt()

### Community 34 - "T"
Cohesion: 0.12
Nodes (13): aV(), Eg(), et(), kV(), mo(), qm(), T(), uw() (+5 more)

### Community 35 - "charts.js"
Cohesion: 0.24
Nodes (11): barChart(), BASE, donutChart(), groupedBarChart(), lineChart(), mount(), PALETTE, stackedBarChart() (+3 more)

### Community 36 - "Token Dashboard"
Cohesion: 0.15
Nodes (13): Accuracy note, CLI reference, Contributing, Further reading, License, Prerequisites, Privacy, Quickstart (+5 more)

### Community 37 - "project_name_for"
Cohesion: 0.21
Nodes (4): ProjectNameTests, best_project_name(), project_name_for(), _walk_to_root()

### Community 38 - "$"
Cohesion: 0.29
Nodes (11): $$, api(), boot(), buildTopbar(), COMPACT, firstRun(), fmt, render() (+3 more)

### Community 40 - "k"
Cohesion: 0.29
Nodes (6): ab(), Im(), mm(), Ob(), sB(), Tm()

### Community 41 - "Wt"
Cohesion: 0.29
Nodes (8): au(), bu(), cu(), du(), fu(), mu(), pu(), xu()

### Community 42 - "Ts"
Cohesion: 0.12
Nodes (18): An(), bn(), Bw(), ds(), Hw(), In(), Is(), jw() (+10 more)

### Community 43 - "scan_codex_dir"
Cohesion: 0.30
Nodes (7): CodexScannerTests, _line(), _usage(), scan_codex_dir(), overview_totals(), recent_sessions(), _title_from_prompt()

### Community 44 - "k"
Cohesion: 0.22
Nodes (9): y(), G(), k(), kc(), kh(), mt(), vi(), d() (+1 more)

### Community 45 - "Cl"
Cohesion: 0.15
Nodes (17): bl(), Cl(), el(), Fl(), jl(), Ll(), nl(), Ol() (+9 more)

### Community 46 - "Inspiration: phuryn/claude-usage"
Cohesion: 0.22
Nodes (9): CLI commands, Core files, Data shape, Inspiration: phuryn/claude-usage, Limitations worth addressing in our version, Tech stack, What it captures, What it does (+1 more)

### Community 47 - "CLAUDE.md"
Cohesion: 0.25
Nodes (7): Architecture, Customizing, Data source, Known limitations, Project overview, Status, Verifying changes

### Community 48 - "xw"
Cohesion: 0.16
Nodes (14): fw(), GR(), gw(), Iw(), Kw(), lw(), ow(), Ur() (+6 more)

### Community 50 - "qn"
Cohesion: 0.22
Nodes (14): Fn(), Gd(), Gn(), Hd(), Hn(), ii(), jn(), ni() (+6 more)

### Community 51 - "vV"
Cohesion: 0.28
Nodes (7): Dy(), ky(), vV(), h(), l(), u(), zV()

### Community 52 - "yb"
Cohesion: 0.10
Nodes (21): Bs(), cb(), db(), gb(), gs(), Gt(), hb(), jB() (+13 more)

### Community 53 - "je"
Cohesion: 0.40
Nodes (5): je(), s(), Ke(), Lh(), qe()

### Community 54 - "Yg"
Cohesion: 0.40
Nodes (5): dd(), pd(), Yg(), r(), u()

### Community 59 - "Contributing"
Cohesion: 0.25
Nodes (8): Code style, Contributing, Ideas that would genuinely help, License, Opening a pull request, Running the dashboard locally, Running the tests, What we're not looking for

### Community 60 - "Known Limitations"
Cohesion: 0.25
Nodes (8): Codex imports local usage only, Cost for Pro / Max / Max-20x users is shown as API-equivalent, not subscription value, Cowork sessions are invisible, First scan can be slow, Known Limitations, Non-standard model names get tier-fallback pricing, Running two dashboards against the same DB, Skills token counts are partial

### Community 61 - "test_pricing.py"
Cohesion: 0.29
Nodes (4): PlanFormatTests, format_for_user(), load_pricing(), set_plan()

### Community 63 - "Where the data comes from"
Cohesion: 0.67
Nodes (3): Codex data and accounting, Environment variables, Where the data comes from

### Community 65 - "ez"
Cohesion: 1.00
Nodes (3): ez(), a(), s()

## Knowledge Gaps
- **8 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `E()` connect `E` to `echarts.min.js`, `n`, `_l`, `fi`, `fv`, `Y`, `ug`, `j`, `z`, `vg`, `U`, `A`, `T`, `ed`, `D`, `mx`, `q`, `vg`, `Vr`, `T`, `k`, `Ts`, `k`, `Cl`, `xw`, `qn`, `vV`, `yb`, `Yg`?**
  _High betweenness centrality (0.018) - this node is a cross-community bridge._
- **Are the 66 inferred relationships involving `n()` (e.g. with `echarts.min.js` and `Al()`) actually correct?**
  _`n()` has 66 INFERRED edges - model-reasoned connections that need verification._
- **Should `echarts.min.js` be split into smaller, more focused modules?**
  _Cohesion score 0.02740138512496236 - nodes in this community are weakly interconnected._
- **Why does `Conventions` connect `scanner.py` to `CLAUDE.md`?**
  _High betweenness centrality (0.017) - this node is a cross-community bridge._
- **Are the 8 inferred relationships involving `T()` (e.g. with `c()` and `Eg()`) actually correct?**
  _`T()` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Should `_l` be split into smaller, more focused modules?**
  _Cohesion score 0.125 - nodes in this community are weakly interconnected._
- **Why does `U()` connect `U` to `echarts.min.js`, `ew`, `_l`, `E`, `fi`, `Y`, `ug`, `j`, `z`, `A`, `T`, `ed`, `D`, `q`, `vg`, `T`, `Wt`, `Ts`, `k`, `Cl`, `xw`, `vV`, `yb`, `Yg`?**
  _High betweenness centrality (0.016) - this node is a cross-community bridge._