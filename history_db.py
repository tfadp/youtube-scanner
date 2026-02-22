"""
Historical database for outperformers.
Stores all outperformers over time to enable pattern analysis and idea testing.
"""

import json
import shutil
from pathlib import Path
from datetime import datetime
from collections import Counter

from config import HISTORY_FILE as HISTORY_FILE_NAME


HISTORY_FILE = Path(__file__).parent / HISTORY_FILE_NAME
BACKUP_FILE = Path(__file__).parent / f"{HISTORY_FILE_NAME}.bak"


def load_history() -> list[dict]:
    """Load historical outperformers, with automatic backup recovery on corruption"""
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print("⚠ history.json corrupted, attempting backup recovery...")
            if restore_from_backup():
                print("✓ Restored from backup")
                with open(HISTORY_FILE, 'r') as f:
                    return json.load(f)
            else:
                print("✗ No backup available, starting fresh")
                return []
    return []


def save_history(history: list[dict]):
    """Save historical outperformers with backup"""
    # Create backup of existing file before overwriting
    if HISTORY_FILE.exists():
        shutil.copy2(HISTORY_FILE, BACKUP_FILE)

    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2, default=str)


def restore_from_backup() -> bool:
    """
    Restore history.json from backup file.
    Returns True if successful, False if no backup exists.
    """
    if not BACKUP_FILE.exists():
        return False

    shutil.copy2(BACKUP_FILE, HISTORY_FILE)
    return True


def add_outperformers(outperformers: list) -> int:
    """
    Add new outperformers to history.
    Deduplicates by video_id.
    Returns number of new entries added.
    """
    history = load_history()
    existing_ids = {entry['video_id'] for entry in history}

    new_count = 0
    for op in outperformers:
        if op.video.video_id not in existing_ids:
            entry = {
                'video_id': op.video.video_id,
                'title': op.video.title,
                'description': op.video.description[:500] if op.video.description else '',
                'channel_name': op.channel.name,
                'channel_category': op.channel.category,
                'views': op.video.views,
                'subscribers': op.channel.subscribers,
                'ratio': op.ratio,
                'velocity_score': op.velocity_score,
                'age_hours': op.age_hours,
                'classification': op.classification,
                'patterns': op.title_patterns,
                'themes': op.themes,
                'tags': op.video.tags[:20] if op.video.tags else [],
                'scanned_at': datetime.now().isoformat(),
                'url': f"https://youtube.com/watch?v={op.video.video_id}"
            }
            history.append(entry)
            existing_ids.add(op.video.video_id)
            new_count += 1

    if new_count > 0:
        save_history(history)

    return new_count


def get_pattern_stats() -> dict:
    """
    Calculate success statistics for each pattern and theme.
    Returns dict with pattern/theme frequencies and avg performance.
    """
    history = load_history()

    if not history:
        return {'patterns': {}, 'themes': {}, 'total_videos': 0}

    pattern_stats = Counter()
    theme_stats = Counter()
    pattern_velocities = {}
    theme_velocities = {}

    for entry in history:
        for pattern in entry.get('patterns', []):
            pattern_stats[pattern] += 1
            if pattern not in pattern_velocities:
                pattern_velocities[pattern] = []
            pattern_velocities[pattern].append(entry.get('velocity_score', 0))

        for theme in entry.get('themes', []):
            theme_stats[theme] += 1
            if theme not in theme_velocities:
                theme_velocities[theme] = []
            theme_velocities[theme].append(entry.get('velocity_score', 0))

    # Calculate average velocity for each pattern/theme
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
        'total_videos': len(history)
    }


def find_similar(patterns: list, themes: list, limit: int = 5) -> list[dict]:
    """
    Find historical videos with similar patterns/themes.
    Returns top matches sorted by velocity score.
    """
    history = load_history()

    if not history:
        return []

    scored = []
    for entry in history:
        entry_patterns = set(entry.get('patterns', []))
        entry_themes = set(entry.get('themes', []))

        # Score based on overlap
        pattern_overlap = len(set(patterns) & entry_patterns)
        theme_overlap = len(set(themes) & entry_themes)
        score = pattern_overlap * 2 + theme_overlap  # Weight patterns more

        if score > 0:
            scored.append((score, entry))

    # Sort by match score, then by velocity
    scored.sort(key=lambda x: (x[0], x[1].get('velocity_score', 0)), reverse=True)

    return [entry for _, entry in scored[:limit]]


def get_history_summary() -> dict:
    """Get summary stats for the history database"""
    history = load_history()

    if not history:
        return {
            'total_videos': 0,
            'trend_jackers': 0,
            'authority_builders': 0,
            'standard': 0,
            'categories': {},
            'date_range': None
        }

    classifications = Counter(e.get('classification', 'standard') for e in history)
    categories = Counter(e.get('channel_category', 'unknown') for e in history)

    dates = [e.get('scanned_at', '') for e in history if e.get('scanned_at')]
    date_range = None
    if dates:
        dates.sort()
        date_range = {'first': dates[0][:10], 'last': dates[-1][:10]}

    return {
        'total_videos': len(history),
        'trend_jackers': classifications.get('trend_jacker', 0),
        'authority_builders': classifications.get('authority_builder', 0),
        'standard': classifications.get('standard', 0),
        'categories': dict(categories.most_common(10)),
        'date_range': date_range
    }
