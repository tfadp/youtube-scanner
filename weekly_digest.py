"""
Weekly Intelligence Digest for US Sports Content

Analyzes a week's worth of scan data and produces actionable insights
for a US sports channel creator. Focuses on:
- What title patterns and formats are working RIGHT NOW
- What smaller creators are doing that's outperforming
- Sport-by-sport breakdown of winning strategies
- Specific title formulas that produced results

Usage:
  Scans run 3x/week with --scan-only (collects data silently).
  Once/week, run: python main.py --weekly-digest [--email]
"""

import json
import sqlite3
from collections import Counter
from datetime import datetime, timedelta

import config as _config


def get_weekly_data(days: int = 7) -> list[dict]:
    """
    Pull all outperformers from the last N days.
    Returns list of history dicts, newest first by velocity.
    """
    if not _config.HISTORY_DB_FILE.exists():
        return []

    conn = sqlite3.connect(_config.HISTORY_DB_FILE)
    conn.row_factory = sqlite3.Row

    # Check table exists (empty DB from tests may not have it)
    table_check = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='outperformers'"
    ).fetchone()
    if not table_check:
        conn.close()
        return []

    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    rows = conn.execute(
        "SELECT * FROM outperformers WHERE scanned_at >= ? ORDER BY velocity_score DESC",
        (cutoff,)
    ).fetchall()
    conn.close()

    results = []
    for row in rows:
        d = dict(row)
        for field in ('patterns', 'themes', 'tags'):
            if isinstance(d.get(field), str):
                try:
                    d[field] = json.loads(d[field])
                except (json.JSONDecodeError, TypeError):
                    d[field] = []
        results.append(d)
    return results


def generate_weekly_digest(days: int = 7) -> dict:
    """
    Main entry point. Analyzes the week's outperformers and returns
    a structured digest with actionable insights.

    Returns dict with sections:
      - top_videos: best performers this week (by velocity)
      - winning_patterns: title patterns ranked by frequency + avg velocity
      - winning_themes: themes ranked by frequency + avg velocity
      - title_formulas: specific multi-pattern combos that worked
      - emerging_creators: smaller channels (<200K subs) punching above weight
      - by_sport: per-sport breakdown
      - summary_stats: total videos, categories scanned, date range
    """
    videos = get_weekly_data(days)

    if not videos:
        return {
            'top_videos': [],
            'winning_patterns': [],
            'winning_themes': [],
            'title_formulas': [],
            'emerging_creators': [],
            'by_sport': {},
            'summary_stats': {
                'total_videos': 0,
                'date_range': None,
                'categories': {}
            }
        }

    return {
        'top_videos': _top_videos(videos),
        'winning_patterns': _winning_patterns(videos),
        'winning_themes': _winning_themes(videos),
        'title_formulas': _title_formulas(videos),
        'emerging_creators': _emerging_creators(videos),
        'by_sport': _by_sport(videos),
        'summary_stats': _summary_stats(videos)
    }


def _top_videos(videos: list[dict], limit: int = 10) -> list[dict]:
    """Top performers by velocity score (already sorted)."""
    top = []
    for v in videos[:limit]:
        top.append({
            'title': v['title'],
            'channel_name': v['channel_name'],
            'channel_category': v['channel_category'],
            'subscribers': v['subscribers'],
            'views': v['views'],
            'ratio': v['ratio'],
            'velocity_score': v['velocity_score'],
            'age_hours': v['age_hours'],
            'patterns': v['patterns'],
            'themes': v['themes'],
            'url': v['url'],
            'classification': v['classification']
        })
    return top


def _winning_patterns(videos: list[dict]) -> list[dict]:
    """
    Rank title patterns by how often they appear + their avg velocity.
    This tells the creator: "videos using X pattern averaged Y velocity."
    """
    pattern_data = {}
    for v in videos:
        for p in v.get('patterns', []):
            if p not in pattern_data:
                pattern_data[p] = {'count': 0, 'velocities': [], 'ratios': []}
            pattern_data[p]['count'] += 1
            pattern_data[p]['velocities'].append(v.get('velocity_score', 0))
            pattern_data[p]['ratios'].append(v.get('ratio', 0))

    results = []
    for pattern, data in pattern_data.items():
        avg_velocity = sum(data['velocities']) / len(data['velocities'])
        avg_ratio = sum(data['ratios']) / len(data['ratios'])
        results.append({
            'pattern': pattern,
            'count': data['count'],
            'avg_velocity': round(avg_velocity, 2),
            'avg_ratio': round(avg_ratio, 2),
            # Score combines frequency and performance
            'score': round(data['count'] * avg_velocity, 2)
        })

    # Sort by combined score (frequent + high-performing = best signal)
    results.sort(key=lambda x: x['score'], reverse=True)
    return results


def _winning_themes(videos: list[dict]) -> list[dict]:
    """Rank themes by frequency + avg velocity."""
    theme_data = {}
    for v in videos:
        for t in v.get('themes', []):
            if t not in theme_data:
                theme_data[t] = {'count': 0, 'velocities': [], 'ratios': []}
            theme_data[t]['count'] += 1
            theme_data[t]['velocities'].append(v.get('velocity_score', 0))
            theme_data[t]['ratios'].append(v.get('ratio', 0))

    results = []
    for theme, data in theme_data.items():
        avg_velocity = sum(data['velocities']) / len(data['velocities'])
        avg_ratio = sum(data['ratios']) / len(data['ratios'])
        results.append({
            'theme': theme,
            'count': data['count'],
            'avg_velocity': round(avg_velocity, 2),
            'avg_ratio': round(avg_ratio, 2),
            'score': round(data['count'] * avg_velocity, 2)
        })

    results.sort(key=lambda x: x['score'], reverse=True)
    return results


def _title_formulas(videos: list[dict], min_occurrences: int = 2) -> list[dict]:
    """
    Find multi-pattern combos that appeared in multiple winning videos.
    e.g., "challenge_bet + all_caps" appeared 4 times, avg 3.2x ratio.

    These are specific title formulas the creator can replicate.
    """
    combo_data = {}
    for v in videos:
        patterns = sorted(v.get('patterns', []))
        if len(patterns) < 2:
            continue

        # Generate all 2-element combos
        for i in range(len(patterns)):
            for j in range(i + 1, len(patterns)):
                combo = (patterns[i], patterns[j])
                if combo not in combo_data:
                    combo_data[combo] = {
                        'count': 0,
                        'velocities': [],
                        'ratios': [],
                        'example_titles': []
                    }
                combo_data[combo]['count'] += 1
                combo_data[combo]['velocities'].append(v.get('velocity_score', 0))
                combo_data[combo]['ratios'].append(v.get('ratio', 0))
                if len(combo_data[combo]['example_titles']) < 3:
                    combo_data[combo]['example_titles'].append(v['title'])

    results = []
    for combo, data in combo_data.items():
        if data['count'] < min_occurrences:
            continue

        avg_velocity = sum(data['velocities']) / len(data['velocities'])
        avg_ratio = sum(data['ratios']) / len(data['ratios'])
        results.append({
            'formula': f"{combo[0]} + {combo[1]}",
            'count': data['count'],
            'avg_velocity': round(avg_velocity, 2),
            'avg_ratio': round(avg_ratio, 2),
            'example_titles': data['example_titles']
        })

    results.sort(key=lambda x: x['count'] * x['avg_velocity'], reverse=True)
    return results[:10]


def _emerging_creators(videos: list[dict], max_subs: int = 200_000) -> list[dict]:
    """
    Smaller channels (<200K subs) whose videos outperformed.
    These are the signals the user wants — what's working for
    creators at a similar or smaller scale.
    """
    channel_best = {}
    for v in videos:
        subs = v.get('subscribers', 0)
        if subs > max_subs or subs == 0:
            continue

        ch_name = v['channel_name']
        if ch_name not in channel_best or v['velocity_score'] > channel_best[ch_name]['best_velocity']:
            channel_best[ch_name] = {
                'channel_name': ch_name,
                'channel_category': v['channel_category'],
                'subscribers': subs,
                'best_title': v['title'],
                'best_ratio': v['ratio'],
                'best_velocity': v['velocity_score'],
                'patterns': v['patterns'],
                'themes': v['themes'],
                'url': v['url']
            }

    results = list(channel_best.values())
    results.sort(key=lambda x: x['best_velocity'], reverse=True)
    return results[:10]


def _by_sport(videos: list[dict]) -> dict:
    """
    Per-sport breakdown: top videos, winning patterns, and themes.
    Groups by channel_category.
    """
    sport_labels = {
        'basketball': 'Basketball',
        'football': 'Football',
        'combat': 'Combat Sports',
        'athlete': 'Athletes / General Sports',
        'training': 'Training / Fitness',
        'fitness': 'Fitness',
        'highlights': 'Highlights',
        'sports': 'Sports (General)'
    }

    sports = {}
    for v in videos:
        cat = v.get('channel_category', '').lower()
        label = sport_labels.get(cat)
        if not label:
            continue

        if label not in sports:
            sports[label] = {
                'videos': [],
                'patterns': Counter(),
                'themes': Counter(),
                'total_videos': 0
            }

        sports[label]['total_videos'] += 1
        sports[label]['videos'].append(v)
        for p in v.get('patterns', []):
            sports[label]['patterns'][p] += 1
        for t in v.get('themes', []):
            sports[label]['themes'][t] += 1

    result = {}
    for label, data in sports.items():
        data['videos'].sort(key=lambda x: x.get('velocity_score', 0), reverse=True)
        top = data['videos'][:5]

        result[label] = {
            'total_videos': data['total_videos'],
            'top_videos': [
                {
                    'title': v['title'],
                    'channel_name': v['channel_name'],
                    'subscribers': v.get('subscribers', 0),
                    'ratio': v['ratio'],
                    'velocity_score': v['velocity_score'],
                    'url': v['url']
                }
                for v in top
            ],
            'top_patterns': dict(data['patterns'].most_common(5)),
            'top_themes': dict(data['themes'].most_common(5))
        }

    return result


def _summary_stats(videos: list[dict]) -> dict:
    """Overall stats for the digest header."""
    categories = Counter(v.get('channel_category', 'unknown') for v in videos)
    dates = [v.get('scanned_at', '') for v in videos if v.get('scanned_at')]

    return {
        'total_videos': len(videos),
        'categories': dict(categories.most_common()),
        'date_range': {
            'first': min(dates)[:10] if dates else None,
            'last': max(dates)[:10] if dates else None
        }
    }
