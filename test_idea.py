"""
Test a video idea against historical outperformer data.

Usage:
    python test_idea.py --title "Your Video Title" --description "Optional description"
    python test_idea.py --interactive  (prompts for input)
    python test_idea.py --stats  (show database statistics)
"""

import argparse
from anthropic import Anthropic

from config import ANTHROPIC_API_KEY
from analyzer import analyze_title, classify_themes
from history_db import (
    load_history,
    get_pattern_stats,
    find_similar,
    get_history_summary
)


def analyze_idea(title: str, description: str = "", tags: list = None) -> dict:
    """
    Analyze a video idea and return pattern/theme analysis.
    """
    tags = tags or []

    # Use existing analyzers
    patterns = analyze_title(title)
    themes = classify_themes(title, description, tags)

    return {
        'title': title,
        'description': description,
        'patterns': patterns,
        'themes': themes
    }


def calculate_score(patterns: list, themes: list, stats: dict, similar: list) -> dict:
    """
    Calculate a prediction score based on historical data.
    """
    if stats['total_videos'] == 0:
        return {
            'score': 0,
            'confidence': 'low',
            'reason': 'No historical data yet. Run the scanner first to build history.'
        }

    # Pattern scoring
    pattern_score = 0
    pattern_matches = []
    for p in patterns:
        if p in stats['patterns']:
            count = stats['patterns'][p]
            avg_vel = stats['pattern_avg_velocity'].get(p, 0)
            pattern_score += min(count / 10, 1) * 2  # Max 2 points per pattern
            pattern_matches.append({
                'pattern': p,
                'count': count,
                'avg_velocity': round(avg_vel, 2)
            })

    # Theme scoring
    theme_score = 0
    theme_matches = []
    for t in themes:
        if t in stats['themes']:
            count = stats['themes'][t]
            avg_vel = stats['theme_avg_velocity'].get(t, 0)
            theme_score += min(count / 10, 1) * 1.5  # Max 1.5 points per theme
            theme_matches.append({
                'theme': t,
                'count': count,
                'avg_velocity': round(avg_vel, 2)
            })

    # Similar video bonus
    similar_score = len(similar) * 0.5  # 0.5 points per similar winner

    # Calculate final score (0-10)
    raw_score = pattern_score + theme_score + similar_score
    final_score = min(raw_score, 10)

    # Confidence level
    if stats['total_videos'] < 10:
        confidence = 'low'
    elif stats['total_videos'] < 50:
        confidence = 'medium'
    else:
        confidence = 'high'

    return {
        'score': round(final_score, 1),
        'confidence': confidence,
        'pattern_matches': pattern_matches,
        'theme_matches': theme_matches,
        'similar_count': len(similar),
        'data_size': stats['total_videos']
    }


def get_claude_analysis(
    title: str,
    description: str,
    patterns: list,
    themes: list,
    similar: list,
    score: dict,
    api_key: str
) -> str:
    """
    Get Claude's analysis of the idea based on the data.
    """
    # Format similar videos for context
    similar_text = ""
    if similar:
        similar_text = "\n\nSimilar videos that performed well:\n"
        for i, v in enumerate(similar[:5], 1):
            similar_text += f"{i}. \"{v['title']}\" - {v['ratio']:.1f}x ratio, {v['velocity_score']:.2f} velocity\n"

    prompt = f"""You are a YouTube content strategist analyzing a video idea.

PROPOSED VIDEO:
Title: "{title}"
Description: {description or "(none provided)"}

DETECTED PATTERNS: {', '.join(patterns) if patterns else 'none'}
DETECTED THEMES: {', '.join(themes) if themes else 'none'}

HISTORICAL DATA SCORE: {score['score']}/10 ({score['confidence']} confidence based on {score['data_size']} historical outperformers)
{similar_text}

Based on this data, provide a brief analysis (3-4 sentences) of:
1. Why this idea might or might not work
2. One specific suggestion to improve the title/concept
3. Your overall recommendation (go/tweak/rethink)

Be direct and actionable. Focus on the packaging (title, thumbnail potential) not production quality."""

    client = Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )

    return response.content[0].text


def print_analysis(idea: dict, score: dict, similar: list, claude_analysis: str = None):
    """Print formatted analysis results"""
    print("\n" + "=" * 60)
    print("IDEA ANALYSIS")
    print("=" * 60)

    print(f"\nTitle: \"{idea['title']}\"")
    if idea['description']:
        print(f"Description: {idea['description'][:100]}...")

    print(f"\nDetected Patterns: {', '.join(idea['patterns']) if idea['patterns'] else 'none'}")
    print(f"Detected Themes: {', '.join(idea['themes']) if idea['themes'] else 'none'}")

    print("\n" + "-" * 60)
    print("PATTERN ANALYSIS")
    print("-" * 60)

    if score['pattern_matches']:
        for pm in score['pattern_matches']:
            print(f"  ✓ {pm['pattern']}: found in {pm['count']} winners (avg velocity: {pm['avg_velocity']})")
    else:
        print("  No matching patterns found in history")

    if score['theme_matches']:
        for tm in score['theme_matches']:
            print(f"  ✓ {tm['theme']}: found in {tm['count']} winners (avg velocity: {tm['avg_velocity']})")
    else:
        print("  No matching themes found in history")

    print("\n" + "-" * 60)
    print("SIMILAR WINNERS")
    print("-" * 60)

    if similar:
        for i, v in enumerate(similar[:5], 1):
            emoji = {"trend_jacker": "🔥", "authority_builder": "👑", "standard": "⬆️"}.get(v.get('classification'), "⬆️")
            print(f"\n{emoji} #{i} — {v['title']}")
            print(f"    Channel: {v['channel_name']} ({v['channel_category']})")
            print(f"    Ratio: {v['ratio']:.1f}x | Velocity: {v['velocity_score']:.2f}")
            print(f"    URL: {v['url']}")
    else:
        print("  No similar videos found in history")

    print("\n" + "-" * 60)
    print("PREDICTION SCORE")
    print("-" * 60)

    # Score visualization
    filled = int(score['score'])
    empty = 10 - filled
    bar = "█" * filled + "░" * empty
    print(f"\n  [{bar}] {score['score']}/10")
    print(f"  Confidence: {score['confidence']} ({score['data_size']} videos in database)")

    if score['score'] >= 7:
        print("\n  📈 HIGH POTENTIAL - Strong pattern match with historical winners")
    elif score['score'] >= 4:
        print("\n  📊 MODERATE POTENTIAL - Some pattern overlap, could work")
    else:
        print("\n  📉 LOW MATCH - Consider testing different angles")

    if claude_analysis:
        print("\n" + "-" * 60)
        print("CLAUDE'S TAKE")
        print("-" * 60)
        print(f"\n{claude_analysis}")

    print("\n" + "=" * 60)


def print_stats():
    """Print database statistics"""
    summary = get_history_summary()
    stats = get_pattern_stats()

    print("\n" + "=" * 60)
    print("HISTORY DATABASE STATS")
    print("=" * 60)

    print(f"\nTotal videos: {summary['total_videos']}")
    print(f"  🔥 Trend-Jackers: {summary['trend_jackers']}")
    print(f"  👑 Authority Builders: {summary['authority_builders']}")
    print(f"  ⬆️ Standard: {summary['standard']}")

    if summary['date_range']:
        print(f"\nDate range: {summary['date_range']['first']} to {summary['date_range']['last']}")

    if summary['categories']:
        print("\nTop categories:")
        for cat, count in list(summary['categories'].items())[:5]:
            print(f"  • {cat}: {count}")

    if stats['patterns']:
        print("\nTop patterns:")
        for pattern, count in list(stats['patterns'].items())[:10]:
            avg = stats['pattern_avg_velocity'].get(pattern, 0)
            print(f"  • {pattern}: {count} videos (avg velocity: {avg:.2f})")

    if stats['themes']:
        print("\nTop themes:")
        for theme, count in list(stats['themes'].items())[:10]:
            avg = stats['theme_avg_velocity'].get(theme, 0)
            print(f"  • {theme}: {count} videos (avg velocity: {avg:.2f})")

    print("\n" + "=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Test a video idea against historical data")
    parser.add_argument("--title", "-t", help="Video title to test")
    parser.add_argument("--description", "-d", default="", help="Video description")
    parser.add_argument("--tags", nargs="*", help="Video tags")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")
    parser.add_argument("--stats", "-s", action="store_true", help="Show database statistics")
    parser.add_argument("--no-claude", action="store_true", help="Skip Claude analysis")
    args = parser.parse_args()

    # Stats mode
    if args.stats:
        print_stats()
        return

    # Get title
    if args.interactive:
        print("\n📝 Enter your video idea:\n")
        title = input("Title: ").strip()
        description = input("Description (optional): ").strip()
        tags_input = input("Tags (comma-separated, optional): ").strip()
        tags = [t.strip() for t in tags_input.split(",")] if tags_input else []
    elif args.title:
        title = args.title
        description = args.description
        tags = args.tags or []
    else:
        parser.print_help()
        print("\nExample: python test_idea.py --title \"I Bet My Entire Salary on This Shot\"")
        return

    if not title:
        print("Error: Title is required")
        return

    # Analyze the idea
    print("\nAnalyzing idea...")
    idea = analyze_idea(title, description, tags)

    # Get stats and similar videos
    stats = get_pattern_stats()
    similar = find_similar(idea['patterns'], idea['themes'])

    # Calculate score
    score = calculate_score(idea['patterns'], idea['themes'], stats, similar)

    # Get Claude's analysis (if enabled and API key available)
    claude_analysis = None
    if not args.no_claude and ANTHROPIC_API_KEY and stats['total_videos'] > 0:
        print("Getting Claude's analysis...")
        try:
            claude_analysis = get_claude_analysis(
                title, description,
                idea['patterns'], idea['themes'],
                similar, score,
                ANTHROPIC_API_KEY
            )
        except Exception as e:
            print(f"⚠ Could not get Claude analysis: {e}")

    # Print results
    print_analysis(idea, score, similar, claude_analysis)


if __name__ == "__main__":
    main()
