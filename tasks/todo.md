# Todo — YouTube Scanner

## Active Tasks
_(none — all clear)_

## Pending Decisions
- Performance bottleneck #1: Batch YouTube API calls (Path A) vs asyncio (Path B) — needs user direction
- Performance bottleneck #2: Add LIMIT to load_history (Path A) vs normalize DB schema (Path B)
- Performance bottleneck #3: Connection caching (Path A) vs session-scoped context manager (Path B)
- Standardize config import pattern across codebase (`from config import X` vs `import config as _config`)
- Install a linter (flake8/ruff) and add to CI

## Completed (2026-03-09)
- [x] Fix soccer/Premier League content leaking through noise filters
- [x] Fix political/geopolitical content leaking through noise filters
- [x] Fix "strikes"/"bomb" false positives in geopolitical keywords
- [x] Migrate history from JSON to SQLite (history_db.py)
- [x] Add trend lines — weekly pattern/theme frequency analysis
- [x] Add subscriber tier breakdowns to email reports
- [x] Fix path model — normalize all paths around PROJECT_ROOT in config.py
- [x] Add integration tests (28 tests in test_integration.py)
- [x] Split pipeline into 3 stages: scan -> enrich -> deliver (--scan-only, --enrich-only, --deliver-only)
- [x] Update SPECS.md with all new contracts (schemas, invariants, decisions)
- [x] /review — 0 critical, 4 warnings, 3 suggestions; all warnings resolved
- [x] /qa — 91/91 tests green, 4 unused imports fixed, 3 bottlenecks identified

---

## Session State
- **Branch:** main
- **Last test result:** 91/91 passed (0.55s)
- **Unpushed commits:** 1 commit ahead of origin/main + uncommitted review/QA fixes
- **Blockers:** None
- **Pending decisions:** See "Pending Decisions" above
