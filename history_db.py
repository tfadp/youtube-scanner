"""
Historical database for outperformers — SQLite backed.

Stores all outperformers over time to enable pattern analysis,
trend tracking, and idea testing. Migrates from history.json
automatically on first run.
"""

import json
import sqlite3
from pathlib import Path
from datetime import datetime
from collections import Counter

import config as _config


def _get_connection() -> sqlite3.Connection:
    """Get a connection to the history database, creating tables if needed."""
    conn = sqlite3.connect(_config.HISTORY_DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")  # safer concurrent access
    _ensure_tables(conn)
    return conn


def _ensure_tables(conn: sqlite3.Connection):
    """Create tables if they don't exist."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS outperformers (
            video_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            summary TEXT DEFAULT '',
            channel_name TEXT NOT NULL,
            channel_category TEXT DEFAULT 'unknown',
            channel_about TEXT DEFAULT '',
            views INTEGER DEFAULT 0,
            subscribers INTEGER DEFAULT 0,
            ratio REAL DEFAULT 0,
            velocity_score REAL DEFAULT 0,
            age_hours REAL DEFAULT 0,
            classification TEXT DEFAULT 'standard',
            patterns TEXT DEFAULT '[]',
            themes TEXT DEFAULT '[]',
            tags TEXT DEFAULT '[]',
            scanned_at TEXT NOT NULL,
            url TEXT DEFAULT '',
            deep_analysis TEXT DEFAULT NULL,
            scan_week TEXT DEFAULT ''
        );

        CREATE INDEX IF NOT EXISTS idx_scanned_at ON outperformers(scanned_at);
        CREATE INDEX IF NOT EXISTS idx_classification ON outperformers(classification);
        CREATE INDEX IF NOT EXISTS idx_scan_week ON outperformers(scan_week);
        CREATE INDEX IF NOT EXISTS idx_channel_category ON outperformers(channel_category);
        CREATE INDEX IF NOT EXISTS idx_subscribers ON outperformers(subscribers);
    """)
    conn.commit()


def _row_to_dict(row: sqlite3.Row) -> dict:
    """Convert a SQLite Row to the legacy dict format."""
    d = dict(row)
    # Deserialize JSON fields
    for field in ('patterns', 'themes', 'tags'):
        if isinstance(d.get(field), str):
            try:
                d[field] = json.loads(d[field])
            except (json.JSONDecodeError, TypeError):
                d[field] = []
    # Deserialize deep_analysis
    if d.get('deep_analysis'):
        try:
            d['deep_analysis'] = json.loads(d['deep_analysis'])
        except (json.JSONDecodeError, TypeError):
            pass
    return d


def _dict_to_row(entry: dict) -> dict:
    """Convert a legacy dict to SQLite row values."""
    scanned_at = entry.get('scanned_at', datetime.now().isoformat())
    # Derive scan_week from scanned_at (YYYY-WNN format)
    try:
        dt = datetime.fromisoformat(scanned_at)
        scan_week = f"{dt.isocalendar()[0]}-W{dt.isocalendar()[1]:02d}"
    except (ValueError, TypeError):
        scan_week = ""

    deep = entry.get('deep_analysis')
    deep_str = json.dumps(deep) if deep else None

    return {
        'video_id': entry['video_id'],
        'title': entry.get('title', ''),
        'description': entry.get('description', ''),
        'summary': entry.get('summary', ''),
        'channel_name': entry.get('channel_name', ''),
        'channel_category': entry.get('channel_category', 'unknown'),
        'channel_about': entry.get('channel_about', ''),
        'views': entry.get('views', 0),
        'subscribers': entry.get('subscribers', 0),
        'ratio': entry.get('ratio', 0),
        'velocity_score': entry.get('velocity_score', 0),
        'age_hours': entry.get('age_hours', 0),
        'classification': entry.get('classification', 'standard'),
        'patterns': json.dumps(entry.get('patterns', [])),
        'themes': json.dumps(entry.get('themes', [])),
        'tags': json.dumps(entry.get('tags', [])),
        'scanned_at': scanned_at,
        'url': entry.get('url', ''),
        'deep_analysis': deep_str,
        'scan_week': scan_week
    }


def _migrate_from_json():
    """One-time migration: import history.json into SQLite."""
    if not _config.HISTORY_FILE.exists():
        return

    print("📦 Migrating history.json → history.db (one-time)...")
    try:
        with open(_config.HISTORY_FILE, 'r') as f:
            history = json.load(f)
    except (json.JSONDecodeError, IOError):
        print("⚠ Could not read history.json for migration, skipping")
        return

    if not history:
        return

    conn = _get_connection()
    inserted = 0
    for entry in history:
        row = _dict_to_row(entry)
        try:
            conn.execute("""
                INSERT OR IGNORE INTO outperformers
                (video_id, title, description, summary, channel_name,
                 channel_category, channel_about, views, subscribers,
                 ratio, velocity_score, age_hours, classification,
                 patterns, themes, tags, scanned_at, url, deep_analysis, scan_week)
                VALUES
                (:video_id, :title, :description, :summary, :channel_name,
                 :channel_category, :channel_about, :views, :subscribers,
                 :ratio, :velocity_score, :age_hours, :classification,
                 :patterns, :themes, :tags, :scanned_at, :url, :deep_analysis, :scan_week)
            """, row)
            inserted += 1
        except sqlite3.Error as e:
            print(f"  ⚠ Skipping entry {entry.get('video_id', '?')}: {e}")

    conn.commit()
    conn.close()

    # Rename old file so migration doesn't re-run
    backup = _config.HISTORY_FILE.with_suffix(".json.migrated")
    _config.HISTORY_FILE.rename(backup)
    print(f"✓ Migrated {inserted} videos. Old file renamed to {backup.name}")


def _ensure_migrated():
    """Run JSON→SQLite migration if history.json exists but history.db doesn't."""
    if _config.HISTORY_FILE.exists() and not _config.HISTORY_DB_FILE.exists():
        _migrate_from_json()


# --- Public API (backward compatible) ---


def load_history() -> list[dict]:
    """Load all historical outperformers as list of dicts."""
    _ensure_migrated()
    conn = _get_connection()
    rows = conn.execute("SELECT * FROM outperformers ORDER BY scanned_at DESC").fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def save_history(history: list[dict]):
    """
    Save historical outperformers (full replace).
    Used by deep_analyzer to update entries with deep_analysis.
    """
    _ensure_migrated()
    conn = _get_connection()
    for entry in history:
        row = _dict_to_row(entry)
        conn.execute("""
            INSERT OR REPLACE INTO outperformers
            (video_id, title, description, summary, channel_name,
             channel_category, channel_about, views, subscribers,
             ratio, velocity_score, age_hours, classification,
             patterns, themes, tags, scanned_at, url, deep_analysis, scan_week)
            VALUES
            (:video_id, :title, :description, :summary, :channel_name,
             :channel_category, :channel_about, :views, :subscribers,
             :ratio, :velocity_score, :age_hours, :classification,
             :patterns, :themes, :tags, :scanned_at, :url, :deep_analysis, :scan_week)
        """, row)
    conn.commit()
    conn.close()


def add_outperformers(outperformers: list) -> int:
    """
    Add new outperformers to history.
    Deduplicates by video_id (PRIMARY KEY handles this).
    Returns number of new entries added.
    """
    _ensure_migrated()
    conn = _get_connection()

    new_count = 0
    for op in outperformers:
        scanned_at = datetime.now().isoformat()
        try:
            dt = datetime.fromisoformat(scanned_at)
            scan_week = f"{dt.isocalendar()[0]}-W{dt.isocalendar()[1]:02d}"
        except (ValueError, TypeError):
            scan_week = ""

        try:
            conn.execute("""
                INSERT OR IGNORE INTO outperformers
                (video_id, title, description, summary, channel_name,
                 channel_category, channel_about, views, subscribers,
                 ratio, velocity_score, age_hours, classification,
                 patterns, themes, tags, scanned_at, url, scan_week)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                op.video.video_id,
                op.video.title,
                op.video.description[:500] if op.video.description else '',
                op.summary if op.summary else '',
                op.channel.name,
                op.channel.category,
                op.channel.about[:500] if op.channel.about else '',
                op.video.views,
                op.channel.subscribers,
                op.ratio,
                op.velocity_score,
                op.age_hours,
                op.classification,
                json.dumps(op.title_patterns),
                json.dumps(op.themes),
                json.dumps(op.video.tags[:20] if op.video.tags else []),
                scanned_at,
                f"https://youtube.com/watch?v={op.video.video_id}",
                scan_week
            ))
            if conn.execute("SELECT changes()").fetchone()[0] > 0:
                new_count += 1
        except sqlite3.Error as e:
            print(f"  ⚠ Could not save {op.video.video_id}: {e}")

    conn.commit()
    conn.close()
    return new_count


def get_pattern_stats() -> dict:
    """
    Calculate success statistics for each pattern and theme.
    Returns dict with pattern/theme frequencies and avg performance.
    """
    _ensure_migrated()
    conn = _get_connection()
    rows = conn.execute("SELECT patterns, themes, velocity_score FROM outperformers").fetchall()
    conn.close()

    if not rows:
        return {'patterns': {}, 'themes': {}, 'total_videos': 0}

    pattern_stats = Counter()
    theme_stats = Counter()
    pattern_velocities = {}
    theme_velocities = {}

    for row in rows:
        patterns = json.loads(row['patterns']) if row['patterns'] else []
        themes = json.loads(row['themes']) if row['themes'] else []
        velocity = row['velocity_score'] or 0

        for pattern in patterns:
            pattern_stats[pattern] += 1
            pattern_velocities.setdefault(pattern, []).append(velocity)

        for theme in themes:
            theme_stats[theme] += 1
            theme_velocities.setdefault(theme, []).append(velocity)

    pattern_avg = {
        p: sum(v) / len(v) for p, v in pattern_velocities.items() if v
    }
    theme_avg = {
        t: sum(v) / len(v) for t, v in theme_velocities.items() if v
    }

    return {
        'patterns': dict(pattern_stats.most_common(20)),
        'themes': dict(theme_stats.most_common(20)),
        'pattern_avg_velocity': pattern_avg,
        'theme_avg_velocity': theme_avg,
        'total_videos': len(rows)
    }


def find_similar(patterns: list, themes: list, limit: int = 5) -> list[dict]:
    """
    Find historical videos with similar patterns/themes.
    Returns top matches sorted by velocity score.
    """
    _ensure_migrated()
    history = load_history()

    if not history:
        return []

    scored = []
    for entry in history:
        entry_patterns = set(entry.get('patterns', []))
        entry_themes = set(entry.get('themes', []))

        pattern_overlap = len(set(patterns) & entry_patterns)
        theme_overlap = len(set(themes) & entry_themes)
        score = pattern_overlap * 2 + theme_overlap

        if score > 0:
            scored.append((score, entry))

    scored.sort(key=lambda x: (x[0], x[1].get('velocity_score', 0)), reverse=True)
    return [entry for _, entry in scored[:limit]]


def get_history_summary() -> dict:
    """Get summary stats for the history database."""
    _ensure_migrated()
    conn = _get_connection()

    total = conn.execute("SELECT COUNT(*) FROM outperformers").fetchone()[0]

    if total == 0:
        conn.close()
        return {
            'total_videos': 0,
            'trend_jackers': 0,
            'authority_builders': 0,
            'standard': 0,
            'categories': {},
            'date_range': None
        }

    # Classification counts
    class_rows = conn.execute(
        "SELECT classification, COUNT(*) as cnt FROM outperformers GROUP BY classification"
    ).fetchall()
    classifications = {r['classification']: r['cnt'] for r in class_rows}

    # Category counts
    cat_rows = conn.execute(
        "SELECT channel_category, COUNT(*) as cnt FROM outperformers "
        "GROUP BY channel_category ORDER BY cnt DESC LIMIT 10"
    ).fetchall()
    categories = {r['channel_category']: r['cnt'] for r in cat_rows}

    # Date range
    date_row = conn.execute(
        "SELECT MIN(scanned_at) as first_date, MAX(scanned_at) as last_date FROM outperformers"
    ).fetchone()
    date_range = None
    if date_row['first_date']:
        date_range = {
            'first': date_row['first_date'][:10],
            'last': date_row['last_date'][:10]
        }

    conn.close()
    return {
        'total_videos': total,
        'trend_jackers': classifications.get('trend_jacker', 0),
        'authority_builders': classifications.get('authority_builder', 0),
        'standard': classifications.get('standard', 0),
        'categories': categories,
        'date_range': date_range
    }


# --- New queries (trends + tiers) ---


def get_pattern_trends(weeks: int = 4) -> dict:
    """
    Compare pattern/theme frequency between recent weeks and prior weeks.

    Returns dict with trend direction and % change for each pattern/theme.
    'rising' = appeared more in recent half, 'falling' = less, 'stable' = similar.
    """
    _ensure_migrated()
    conn = _get_connection()

    # Get all entries with scan_week, ordered
    rows = conn.execute(
        "SELECT patterns, themes, scan_week FROM outperformers "
        "WHERE scan_week != '' ORDER BY scan_week DESC"
    ).fetchall()
    conn.close()

    if not rows:
        return {'pattern_trends': {}, 'theme_trends': {}, 'weeks_analyzed': 0}

    # Collect unique weeks
    all_weeks = sorted(set(r['scan_week'] for r in rows), reverse=True)
    if len(all_weeks) < 2:
        return {'pattern_trends': {}, 'theme_trends': {}, 'weeks_analyzed': len(all_weeks)}

    # Split into recent half and prior half
    num_weeks = min(weeks, len(all_weeks))
    midpoint = num_weeks // 2
    recent_weeks = set(all_weeks[:midpoint]) if midpoint > 0 else set(all_weeks[:1])
    prior_weeks = set(all_weeks[midpoint:num_weeks])

    recent_patterns = Counter()
    prior_patterns = Counter()
    recent_themes = Counter()
    prior_themes = Counter()
    recent_count = 0
    prior_count = 0

    for row in rows:
        week = row['scan_week']
        patterns = json.loads(row['patterns']) if row['patterns'] else []
        themes = json.loads(row['themes']) if row['themes'] else []

        if week in recent_weeks:
            recent_count += 1
            for p in patterns:
                recent_patterns[p] += 1
            for t in themes:
                recent_themes[t] += 1
        elif week in prior_weeks:
            prior_count += 1
            for p in patterns:
                prior_patterns[p] += 1
            for t in themes:
                prior_themes[t] += 1

    def _calc_trend(recent_counter, prior_counter, recent_total, prior_total):
        """Calculate trend direction and % change, normalized by video count."""
        all_keys = set(recent_counter.keys()) | set(prior_counter.keys())
        trends = {}
        for key in all_keys:
            # Normalize to frequency per video
            recent_freq = recent_counter.get(key, 0) / max(recent_total, 1)
            prior_freq = prior_counter.get(key, 0) / max(prior_total, 1)

            if prior_freq == 0:
                pct_change = 100.0 if recent_freq > 0 else 0.0
            else:
                pct_change = ((recent_freq - prior_freq) / prior_freq) * 100

            if pct_change > 15:
                direction = "rising"
            elif pct_change < -15:
                direction = "falling"
            else:
                direction = "stable"

            trends[key] = {
                'recent_count': recent_counter.get(key, 0),
                'prior_count': prior_counter.get(key, 0),
                'pct_change': round(pct_change, 1),
                'direction': direction
            }
        return trends

    return {
        'pattern_trends': _calc_trend(recent_patterns, prior_patterns, recent_count, prior_count),
        'theme_trends': _calc_trend(recent_themes, prior_themes, recent_count, prior_count),
        'weeks_analyzed': num_weeks,
        'recent_videos': recent_count,
        'prior_videos': prior_count
    }


def get_tier_breakdown() -> dict:
    """
    Break down pattern effectiveness by subscriber tier.

    Tiers:
      - emerging: < 100K subscribers
      - mid: 100K - 500K subscribers
      - large: 500K+ subscribers

    Returns dict with per-tier pattern counts and avg velocity.
    """
    _ensure_migrated()
    conn = _get_connection()
    rows = conn.execute(
        "SELECT subscribers, patterns, themes, velocity_score, classification FROM outperformers"
    ).fetchall()
    conn.close()

    tiers = {
        'emerging': {'range': '<100K', 'min': 0, 'max': 100_000},
        'mid': {'range': '100K-500K', 'min': 100_000, 'max': 500_000},
        'large': {'range': '500K+', 'min': 500_000, 'max': float('inf')}
    }

    result = {}
    for tier_name, tier_def in tiers.items():
        tier_rows = [
            r for r in rows
            if tier_def['min'] <= (r['subscribers'] or 0) < tier_def['max']
        ]

        pattern_counts = Counter()
        theme_counts = Counter()
        velocities = []

        for row in tier_rows:
            patterns = json.loads(row['patterns']) if row['patterns'] else []
            themes = json.loads(row['themes']) if row['themes'] else []
            for p in patterns:
                pattern_counts[p] += 1
            for t in themes:
                theme_counts[t] += 1
            if row['velocity_score']:
                velocities.append(row['velocity_score'])

        result[tier_name] = {
            'range': tier_def['range'],
            'total_videos': len(tier_rows),
            'avg_velocity': round(sum(velocities) / len(velocities), 2) if velocities else 0,
            'top_patterns': dict(pattern_counts.most_common(5)),
            'top_themes': dict(theme_counts.most_common(5))
        }

    return result
