"""
Trend Analysis and Pattern Lifecycle Tracking

Analyzes historical data to identify:
- Emerging patterns (appearing more frequently recently)
- Peaking patterns (high velocity but starting to decline)
- Declining patterns (were popular, now less frequent)
- Week-over-week trend changes
"""

import json
from datetime import datetime, timedelta
from collections import Counter, defaultdict
from pathlib import Path

from history_db import load_history


def get_videos_in_range(history: list, days_back: int, days_end: int = 0) -> list:
    """Get videos scanned within a date range (days ago)"""
    now = datetime.now()
    start_date = now - timedelta(days=days_back)
    end_date = now - timedelta(days=days_end)

    filtered = []
    for entry in history:
        scanned_at = entry.get('scanned_at', '')
        if scanned_at:
            try:
                scan_date = datetime.fromisoformat(scanned_at.replace('Z', '+00:00'))
                # Make naive for comparison
                if scan_date.tzinfo:
                    scan_date = scan_date.replace(tzinfo=None)
                if start_date <= scan_date <= end_date:
                    filtered.append(entry)
            except:
                pass
    return filtered


def analyze_pattern_lifecycle(history: list) -> dict:
    """
    Categorize patterns as emerging, peaking, or declining.

    Compares last 7 days vs previous 7-14 days vs 14-30 days.
    """
    # Get videos from different time periods
    last_week = get_videos_in_range(history, 7, 0)
    prev_week = get_videos_in_range(history, 14, 7)
    month_ago = get_videos_in_range(history, 30, 14)

    # Count patterns in each period
    def count_patterns(videos):
        patterns = Counter()
        themes = Counter()
        for v in videos:
            for p in v.get('patterns', []):
                patterns[p] += 1
            for t in v.get('themes', []):
                themes[t] += 1
        return patterns, themes

    last_patterns, last_themes = count_patterns(last_week)
    prev_patterns, prev_themes = count_patterns(prev_week)
    old_patterns, old_themes = count_patterns(month_ago)

    # Analyze pattern lifecycle
    all_patterns = set(last_patterns.keys()) | set(prev_patterns.keys()) | set(old_patterns.keys())
    all_themes = set(last_themes.keys()) | set(prev_themes.keys()) | set(old_themes.keys())

    def classify_trend(current, previous, old):
        """Classify as emerging, peaking, stable, or declining"""
        if current == 0 and previous == 0:
            return None

        # Emerging: new or significantly increasing
        if current > 0 and previous == 0 and old == 0:
            return "emerging"
        if current > previous * 1.5 and current > old:
            return "emerging"

        # Declining: was popular, now less
        if current < previous * 0.5 and previous > 0:
            return "declining"
        if current == 0 and (previous > 0 or old > 0):
            return "declining"

        # Peaking: high now but showing signs of plateau/decline
        if current >= previous and current >= old and previous > old:
            return "peaking"

        # Stable
        if current > 0:
            return "stable"

        return None

    pattern_lifecycle = {}
    for p in all_patterns:
        status = classify_trend(last_patterns[p], prev_patterns[p], old_patterns[p])
        if status:
            pattern_lifecycle[p] = {
                'status': status,
                'last_week': last_patterns[p],
                'prev_week': prev_patterns[p],
                'month_ago': old_patterns[p]
            }

    theme_lifecycle = {}
    for t in all_themes:
        status = classify_trend(last_themes[t], prev_themes[t], old_themes[t])
        if status:
            theme_lifecycle[t] = {
                'status': status,
                'last_week': last_themes[t],
                'prev_week': prev_themes[t],
                'month_ago': old_themes[t]
            }

    return {
        'patterns': pattern_lifecycle,
        'themes': theme_lifecycle,
        'data_summary': {
            'last_week_videos': len(last_week),
            'prev_week_videos': len(prev_week),
            'month_ago_videos': len(month_ago)
        }
    }


def get_week_over_week_changes(history: list) -> dict:
    """
    Compare this week's patterns to last week.
    Returns what's trending up, down, and new.
    """
    this_week = get_videos_in_range(history, 7, 0)
    last_week = get_videos_in_range(history, 14, 7)

    def get_counts(videos):
        patterns = Counter()
        themes = Counter()
        channels = Counter()
        categories = Counter()
        for v in videos:
            for p in v.get('patterns', []):
                patterns[p] += 1
            for t in v.get('themes', []):
                themes[t] += 1
            channels[v.get('channel_name', 'unknown')] += 1
            categories[v.get('channel_category', 'unknown')] += 1
        return {
            'patterns': patterns,
            'themes': themes,
            'channels': channels,
            'categories': categories,
            'total': len(videos)
        }

    this_data = get_counts(this_week)
    last_data = get_counts(last_week)

    # Calculate changes
    def calc_changes(this_counts, last_counts):
        changes = {'up': [], 'down': [], 'new': [], 'gone': []}

        all_items = set(this_counts.keys()) | set(last_counts.keys())
        for item in all_items:
            this_val = this_counts[item]
            last_val = last_counts[item]

            if this_val > 0 and last_val == 0:
                changes['new'].append((item, this_val))
            elif this_val == 0 and last_val > 0:
                changes['gone'].append((item, last_val))
            elif this_val > last_val:
                changes['up'].append((item, this_val, last_val, this_val - last_val))
            elif this_val < last_val:
                changes['down'].append((item, this_val, last_val, last_val - this_val))

        # Sort by magnitude
        changes['up'].sort(key=lambda x: x[3], reverse=True)
        changes['down'].sort(key=lambda x: x[3], reverse=True)
        changes['new'].sort(key=lambda x: x[1], reverse=True)

        return changes

    return {
        'patterns': calc_changes(this_data['patterns'], last_data['patterns']),
        'themes': calc_changes(this_data['themes'], last_data['themes']),
        'channels': calc_changes(this_data['channels'], last_data['channels']),
        'categories': calc_changes(this_data['categories'], last_data['categories']),
        'total_this_week': this_data['total'],
        'total_last_week': last_data['total']
    }


def get_top_performers_this_week(history: list, limit: int = 10) -> list:
    """Get the highest velocity videos from the past week"""
    this_week = get_videos_in_range(history, 7, 0)
    sorted_videos = sorted(this_week, key=lambda x: x.get('velocity_score', 0), reverse=True)
    return sorted_videos[:limit]


def get_emerging_channels(history: list) -> list:
    """Find channels that are appearing more frequently in outperformers"""
    this_week = get_videos_in_range(history, 7, 0)
    prev_weeks = get_videos_in_range(history, 30, 7)

    this_channels = Counter(v.get('channel_name', '') for v in this_week)
    prev_channels = Counter(v.get('channel_name', '') for v in prev_weeks)

    emerging = []
    for channel, count in this_channels.items():
        prev_count = prev_channels[channel]
        if count >= 2 and count > prev_count:
            emerging.append({
                'channel': channel,
                'this_week': count,
                'previous': prev_count,
                'category': next((v.get('channel_category') for v in this_week if v.get('channel_name') == channel), 'unknown')
            })

    emerging.sort(key=lambda x: x['this_week'], reverse=True)
    return emerging[:10]


def format_trend_report() -> str:
    """Generate a formatted trend analysis report"""
    history = load_history()

    if len(history) < 5:
        return "Not enough historical data yet. Need at least 5 outperformers to analyze trends."

    lifecycle = analyze_pattern_lifecycle(history)
    wow_changes = get_week_over_week_changes(history)
    top_videos = get_top_performers_this_week(history)
    emerging_channels = get_emerging_channels(history)

    lines = []
    lines.append("=" * 60)
    lines.append("TREND ANALYSIS REPORT")
    lines.append("=" * 60)
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"This week: {wow_changes['total_this_week']} outperformers")
    lines.append(f"Last week: {wow_changes['total_last_week']} outperformers")

    # Week over week summary
    lines.append("\n" + "-" * 60)
    lines.append("WEEK OVER WEEK CHANGES")
    lines.append("-" * 60)

    if wow_changes['themes']['up']:
        lines.append("\n📈 Themes TRENDING UP:")
        for item in wow_changes['themes']['up'][:5]:
            lines.append(f"   • {item[0]}: {item[2]} → {item[1]} (+{item[3]})")

    if wow_changes['themes']['down']:
        lines.append("\n📉 Themes TRENDING DOWN:")
        for item in wow_changes['themes']['down'][:5]:
            lines.append(f"   • {item[0]}: {item[2]} → {item[1]} (-{item[3]})")

    if wow_changes['themes']['new']:
        lines.append("\n🆕 NEW Themes This Week:")
        for item in wow_changes['themes']['new'][:5]:
            lines.append(f"   • {item[0]} ({item[1]} videos)")

    # Pattern lifecycle
    lines.append("\n" + "-" * 60)
    lines.append("PATTERN LIFECYCLE")
    lines.append("-" * 60)

    emerging = [p for p, d in lifecycle['patterns'].items() if d['status'] == 'emerging']
    peaking = [p for p, d in lifecycle['patterns'].items() if d['status'] == 'peaking']
    declining = [p for p, d in lifecycle['patterns'].items() if d['status'] == 'declining']

    if emerging:
        lines.append(f"\n🚀 EMERGING PATTERNS (catch these early):")
        for p in emerging[:5]:
            data = lifecycle['patterns'][p]
            lines.append(f"   • {p}: {data['month_ago']} → {data['prev_week']} → {data['last_week']}")

    if peaking:
        lines.append(f"\n🔥 PEAKING PATTERNS (use now, but watch for saturation):")
        for p in peaking[:5]:
            data = lifecycle['patterns'][p]
            lines.append(f"   • {p}: {data['last_week']} this week")

    if declining:
        lines.append(f"\n📉 DECLINING PATTERNS (may be played out):")
        for p in declining[:5]:
            data = lifecycle['patterns'][p]
            lines.append(f"   • {p}: was {data['prev_week']}, now {data['last_week']}")

    # Theme lifecycle
    emerging_themes = [t for t, d in lifecycle['themes'].items() if d['status'] == 'emerging']
    if emerging_themes:
        lines.append(f"\n🚀 EMERGING THEMES:")
        for t in emerging_themes[:5]:
            data = lifecycle['themes'][t]
            lines.append(f"   • {t}: {data['month_ago']} → {data['prev_week']} → {data['last_week']}")

    # Top performers
    if top_videos:
        lines.append("\n" + "-" * 60)
        lines.append("TOP PERFORMERS THIS WEEK")
        lines.append("-" * 60)
        for i, v in enumerate(top_videos[:5], 1):
            lines.append(f"\n#{i} — {v['title'][:50]}...")
            lines.append(f"    Channel: {v['channel_name']}")
            lines.append(f"    Velocity: {v.get('velocity_score', 0):.2f} | Ratio: {v.get('ratio', 0):.1f}x")
            lines.append(f"    URL: {v.get('url', '')}")

    # Emerging channels
    if emerging_channels:
        lines.append("\n" + "-" * 60)
        lines.append("CHANNELS TO WATCH")
        lines.append("-" * 60)
        lines.append("(Multiple outperformers this week)")
        for ch in emerging_channels[:5]:
            lines.append(f"   • {ch['channel']} ({ch['category']}): {ch['this_week']} hits this week")

    lines.append("\n" + "=" * 60)

    return "\n".join(lines)


if __name__ == "__main__":
    print(format_trend_report())
