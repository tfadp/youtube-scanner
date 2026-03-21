# Todo — YouTube Scanner

## Active Tasks
_(none — all clear)_

## Pending Decisions
- Performance bottleneck #1: Batch YouTube API calls (Path A) vs asyncio (Path B) — needs user direction
- Performance bottleneck #2: Centralize `get_weekly_data` into history_db (Path A: add `since_days` param) vs query builder (Path B)
- Performance bottleneck #3: Add LIMIT to load_history (Path A) vs normalize DB schema (Path B)
- Standardize config import pattern across codebase (`from config import X` vs `import config as _config`)
- Install a linter (flake8/ruff) and add to CI
- Set up cron jobs: 3x/week `--scan-only`, 1x/week `--weekly-digest`

## Completed (2026-03-20)
- [x] Add RELEVANT_CATEGORIES to config — US sports only (basketball, football, combat, fitness, athlete, training, highlights)
- [x] Remove soccer from SPORTS_CATEGORIES
- [x] Pre-filter channels in stage_scan before API calls (saves ~60% quota)
- [x] Simplify noise filter chain (removed soccer_content + not_relevant filters)
- [x] Rewrite weekly_digest.py — patterns, title formulas, emerging creators, per-sport breakdowns
- [x] Add format_weekly_digest_email (mobile-optimized HTML)
- [x] Add --weekly-digest CLI flag to main.py
- [x] Add 7 weekly digest tests (99 total)
- [x] Update SPECS.md with new invariants + decisions
- [x] /review — 1 critical (fixed: API quota waste), 3 warnings (2 fixed), 2 suggestions
- [x] /qa — 99/99 tests green, 0 lint errors, 3 bottlenecks identified

## Completed (2026-03-09)
- [x] Fix soccer/Premier League content leaking through noise filters
- [x] Fix political/geopolitical content leaking through noise filters
- [x] Fix "strikes"/"bomb" false positives in geopolitical keywords
- [x] Migrate history from JSON to SQLite (history_db.py)
- [x] Add trend lines — weekly pattern/theme frequency analysis
- [x] Add subscriber tier breakdowns to email reports
- [x] Fix path model — normalize all paths around PROJECT_ROOT in config.py
- [x] Add integration tests (28 tests in test_integration.py)
- [x] Split pipeline into 3 stages: scan -> enrich -> deliver
- [x] /review — 0 critical, 4 warnings, 3 suggestions; all resolved
- [x] /qa — 91/91 tests green, 4 unused imports fixed

---

## Session State
- **Branch:** main
- **Last test result:** 99/99 passed (0.59s)
- **Unpushed commits:** 0 — everything pushed to origin/main
- **Blockers:** None
- **Pending decisions:** See "Pending Decisions" above
