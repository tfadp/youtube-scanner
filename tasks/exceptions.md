# Exceptions Log

## 2026-03-09 — QA Pass

### 1. SPECS.md drift: Channel.about field
- **File:** .claude/SPECS.md (Section B, Channel dataclass)
- **What:** Code had `about: str = ""` on Channel dataclass, but SPECS.md did not list it
- **Resolution:** Added `about: str = ""` to SPECS.md Channel schema

### 2. Silent exception swallowing in email_sender.py
- **File:** email_sender.py, `_format_trends_html()` and `_format_tiers_html()`
- **What:** `except Exception:` with bare `return ""` hid all errors
- **Resolution:** Added `print(f"⚠ ... skipped: {e}")` to both handlers

### 3. Redundant datetime round-trip in history_db.py
- **File:** history_db.py, `add_outperformers()` line 218-223
- **What:** Created `scanned_at = datetime.now().isoformat()` then immediately parsed it back with `datetime.fromisoformat()` to compute `scan_week`
- **Resolution:** Compute `scan_week` directly from `datetime.now()` object

### 4. Unused imports across 3 files
- **File:** batch_manager.py, history_db.py, main.py
- **What:** `from pathlib import Path` (2 files), `BATCH_SIZE` and `load_batch_state` (main.py) were imported but never used
- **Resolution:** Removed all 4 unused imports

## 2026-03-20 — US Sports Focus + Weekly Digest QA Pass

### 5. API quota waste: fetch_subscriber_counts on non-relevant channels
- **File:** main.py, `stage_scan()` line 375
- **What:** `fetch_subscriber_counts` was called on ALL channels (including culture/gaming/soccer) before `find_outperformers` skipped them. Wasted ~60% of API quota.
- **Resolution:** Added RELEVANT_CATEGORIES pre-filter in `stage_scan` before any API calls.

### 6. Stale noise_type docstring after filter removal
- **File:** scanner.py line 54, .claude/SPECS.md line 69
- **What:** Still listed "soccer_content" and "not_relevant" as valid noise types after those filters were removed.
- **Resolution:** Updated both to list only 3 active types: event_recap, live_stream, political_news.

### 7. KeyError in weekly_digest._emerging_creators
- **File:** weekly_digest.py, `_emerging_creators()` line 236
- **What:** Compared `v['velocity_score']` against `channel_best[ch_name]['velocity_score']` but the dict key was `best_velocity`.
- **Resolution:** Changed comparison to use `channel_best[ch_name]['best_velocity']`.

### 8. get_weekly_data crashes on empty DB (no outperformers table)
- **File:** weekly_digest.py, `get_weekly_data()` line 33
- **What:** `sqlite3.OperationalError: no such table: outperformers` when DB exists but table hasn't been created yet.
- **Resolution:** Added table existence check before querying; returns empty list if table missing.
