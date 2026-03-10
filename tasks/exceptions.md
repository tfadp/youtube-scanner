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
