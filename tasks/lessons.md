# Lessons Learned

## 2026-03-20 — US Sports Focus + Weekly Digest

### Lesson 7: Pre-filter channels BEFORE API calls, not just in the scanner
The category filter in `find_outperformers` skipped irrelevant channels, but `fetch_subscriber_counts` still made API calls for ALL channels first. The filter must be applied at the earliest possible point — before any API interaction — to save quota.

### Lesson 8: When rewriting a module, check for existing bugs in the code you're replacing
The old `weekly_digest.py` had complex dependencies (trend_analyzer, success_analyzer, deep_analyzer). The rewrite replaced it with a self-contained data-driven module, but the `_emerging_creators` function had a dict key mismatch (`velocity_score` vs `best_velocity`). Always test new code against edge cases even when it looks straightforward.

### Lesson 9: New DB queries need table-existence guards
`get_weekly_data` opened its own SQLite connection and immediately queried `outperformers`. On a fresh DB (or in tests with `temp_db`), the table doesn't exist yet. Always check for table existence when bypassing the standard `history_db` API.

### Lesson 10: When removing a filter, update ALL references to it
Removing `soccer_content` and `not_relevant` noise filters from the scanner also requires updating: the Outperformer dataclass docstring, SPECS.md noise_type list, and any test that relied on those filter types.

## 2026-03-09 — Infrastructure Upgrade Session

### Lesson 1: `from config import X` captures value at import time
When you do `from config import SCAN_RESULTS_FILE`, Python copies the value into the importing module's namespace. Patching `config.SCAN_RESULTS_FILE` later does NOT affect the copy. Fix: use `import config as _config` and reference `_config.SCAN_RESULTS_FILE` at runtime, OR patch both `config.X` and `module.X` in tests.

### Lesson 2: Geopolitical keyword filters must avoid common English words
Words like "strikes", "bomb", "war" are too broad — they match bowling strikes, slang ("the bomb"), and gaming (Warzone). Use specific compound phrases: "air strikes", "bombing", "war " (with trailing space).

### Lesson 3: Soccer channels bypass `is_not_relevant()` because they're in SPORTS_CATEGORIES
The `is_not_relevant()` filter explicitly returns False for all sports categories. Since "soccer" is in SPORTS_CATEGORIES, soccer content was never filtered. Resolved in 2026-03-20 by removing soccer from SPORTS_CATEGORIES entirely and filtering at the category level.

### Lesson 4: Test isolation requires unique temp paths per test
When multiple tests share `tmp_path` via config patching, earlier tests can create files that interfere with later tests (e.g., SQLite DB from test A leaking into migration test B). Fix: use unique subdirectories within `tmp_path`.

### Lesson 5: Module-level imports in batch_manager need patching at the module level
`batch_manager.BATCH_SIZE` is set at import time from config. Patching `config.BATCH_SIZE` doesn't change `batch_manager.BATCH_SIZE`. Must patch `batch_manager.BATCH_SIZE` directly in tests.

### Lesson 6: Always update SPECS.md when adding fields to dataclasses
The Channel `about` field existed in code but was missing from SPECS.md. This was caught during /review but should have been updated when the field was first added.
