# Lessons Learned

## 2026-03-09 — Infrastructure Upgrade Session

### Lesson 1: `from config import X` captures value at import time
When you do `from config import SCAN_RESULTS_FILE`, Python copies the value into the importing module's namespace. Patching `config.SCAN_RESULTS_FILE` later does NOT affect the copy. Fix: use `import config as _config` and reference `_config.SCAN_RESULTS_FILE` at runtime, OR patch both `config.X` and `module.X` in tests.

### Lesson 2: Geopolitical keyword filters must avoid common English words
Words like "strikes", "bomb", "war" are too broad — they match bowling strikes, slang ("the bomb"), and gaming (Warzone). Use specific compound phrases: "air strikes", "bombing", "war " (with trailing space).

### Lesson 3: Soccer channels bypass `is_not_relevant()` because they're in SPORTS_CATEGORIES
The `is_not_relevant()` filter explicitly returns False for all sports categories. Since "soccer" is in SPORTS_CATEGORIES, soccer content was never filtered. Solution: add a dedicated `is_soccer_content()` check that runs BEFORE `is_not_relevant()` in the noise chain.

### Lesson 4: Test isolation requires unique temp paths per test
When multiple tests share `tmp_path` via config patching, earlier tests can create files that interfere with later tests (e.g., SQLite DB from test A leaking into migration test B). Fix: use unique subdirectories within `tmp_path`.

### Lesson 5: Module-level imports in batch_manager need patching at the module level
`batch_manager.BATCH_SIZE` is set at import time from config. Patching `config.BATCH_SIZE` doesn't change `batch_manager.BATCH_SIZE`. Must patch `batch_manager.BATCH_SIZE` directly in tests.

### Lesson 6: Always update SPECS.md when adding fields to dataclasses
The Channel `about` field existed in code but was missing from SPECS.md. This was caught during /review but should have been updated when the field was first added.
