# ARCHITECTURE.md — Two-Agent System Design

## Overview

Two parallel workstreams:
- **Agent A (Infrastructure)**: Storage, scaling, monitoring
- **Agent B (Analysis)**: Deep pattern analysis, trend detection, predictions

---

## Data Contract (Shared Interface)

### Core Tables/Collections

```
videos
├── video_id (PK)
├── channel_id (FK)
├── title
├── description (truncated 500 chars)
├── views
├── likes
├── comments
├── duration_seconds
├── published_at
├── scanned_at
├── thumbnail_url
├── tags (JSON array)
├── patterns (JSON array) — ["first_person_action", "question", ...]
├── themes (JSON array) — ["basketball", "money", ...]
├── ratio
├── velocity_score
├── classification — "trend_jacker" | "authority_builder" | "standard"
└── age_hours_at_scan

channels
├── channel_id (PK)
├── name
├── category
├── subscribers (latest)
└── last_scanned_at

pattern_snapshots (for trend analysis)
├── date (daily rollup)
├── pattern
├── count
├── avg_velocity
└── avg_ratio
```

### Required Queries (Analysis Needs)

```python
# 1. Pattern effectiveness over time
get_pattern_trends(pattern: str, days: int = 90) -> list[{date, count, avg_velocity}]

# 2. Pattern + theme correlation
get_pattern_theme_matrix() -> dict[pattern][theme] -> {count, avg_velocity}

# 3. Channel cohort analysis
get_performance_by_subscriber_tier(tiers: list[int]) -> dict[tier] -> {patterns, avg_velocity}

# 4. Decay curves
get_velocity_by_age(pattern: str) -> list[{age_hours, avg_velocity}]

# 5. Emerging topics (multiple channels, same theme, short window)
get_emerging_topics(window_hours: int = 24, min_channels: int = 3) -> list[{theme, channels, velocity}]

# 6. Weekly digest data
get_weekly_comparison(current_week, previous_week) -> {rising_patterns, falling_patterns, new_themes}
```

---

## Agent A: Infrastructure Scope

### Phase 1: SQLite Migration
- [ ] Create `db/` module with SQLite schema
- [ ] Migration script: `history.json` → SQLite
- [ ] Update `history_db.py` to use new storage layer
- [ ] Keep JSON backup for rollback

### Phase 2: Query Layer
- [ ] Implement required queries above
- [ ] Add indexes for common access patterns
- [ ] Daily rollup job for `pattern_snapshots`

### Phase 3: Monitoring
- [ ] Health check endpoint
- [ ] Dead man's snitch integration
- [ ] Error alerting (Sentry or simple email)

### Files to create/modify:
```
db/
├── __init__.py
├── schema.py          # SQLite schema definitions
├── migrations.py      # JSON → SQLite migration
├── queries.py         # Query implementations
└── rollups.py         # Daily aggregation jobs

history_db.py          # Update to use db/ layer
config.py              # Add DB_PATH setting
```

---

## Agent B: Analysis Scope

### Phase 1: Trend Analysis
- [ ] `analytics/trends.py` — pattern effectiveness over time
- [ ] Week-over-week comparison
- [ ] Rising/falling pattern detection

### Phase 2: Correlation Analysis
- [ ] `analytics/correlations.py` — pattern+theme matrix
- [ ] Statistical significance testing
- [ ] Channel cohort breakdowns

### Phase 3: Predictive Signals
- [ ] `analytics/emerging.py` — early topic detection
- [ ] Cross-channel convergence alerts
- [ ] Decay curve modeling

### Files to create:
```
analytics/
├── __init__.py
├── trends.py          # Pattern trends over time
├── correlations.py    # Pattern+theme effectiveness
├── cohorts.py         # Channel size analysis
├── emerging.py        # Early signal detection
└── reports.py         # Weekly digest generation
```

---

## Integration Points

1. **Scanner → Storage**: After each scan, call `db.add_outperformers()`
2. **Storage → Analysis**: Analysis imports from `db.queries`
3. **Analysis → Reports**: Weekly digest uses `analytics.reports`

---

## Next Session Checklist

When resuming:
1. Read this file first
2. Decide: sequential or parallel agents?
3. If parallel: Agent A starts with `db/schema.py`, Agent B starts with `analytics/trends.py`
4. Merge point: After Agent A completes Phase 2 (query layer)

---

## Status

- [x] Contract defined
- [ ] Agent A: Infrastructure (not started)
- [ ] Agent B: Analysis (not started)
