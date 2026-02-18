"""
Success Factor Analysis

Uses Claude to analyze WHY specific videos outperformed,
extracting actionable lessons for content creation.
"""

from anthropic import Anthropic
from history_db import load_history, save_history


def analyze_success_factors(video: dict, api_key: str) -> dict:
    """
    Use Claude to analyze why a video succeeded.

    Returns structured analysis of success factors.
    """
    # Build context for analysis
    duration_mins = video.get('duration_seconds', 0) / 60 if video.get('duration_seconds') else 0

    prompt = f"""Analyze why this YouTube video outperformed (got more views than the channel's subscriber count).

VIDEO DATA:
- Title: "{video['title']}"
- Channel: {video.get('channel_name', 'Unknown')} ({video.get('channel_category', 'unknown')} category)
- Views: {video.get('views', 0):,}
- Subscribers: {video.get('subscribers', 0):,}
- Ratio: {video.get('ratio', 0):.1f}x (views/subs)
- Velocity: {video.get('velocity_score', 0):.2f} (ratio/day)
- Video Length: {duration_mins:.1f} minutes
- Age: {video.get('age_hours', 0):.0f} hours old
- Description: {video.get('description', '')[:300]}...
- Tags: {', '.join(video.get('tags', [])[:10])}

Provide a brief analysis in this exact JSON format:
{{
    "title_hook": "What makes the title click-worthy (1 sentence)",
    "topic_timing": "Why this topic worked NOW - trending event, evergreen, or seasonal (1 sentence)",
    "emotion_trigger": "Primary emotion the title/topic triggers - curiosity, FOMO, nostalgia, controversy, etc.",
    "format_type": "Content format type - challenge, listicle, reaction, tutorial, story, compilation, etc.",
    "key_lesson": "One actionable lesson to apply to your own content (1 sentence)",
    "replication_difficulty": "easy/medium/hard - how hard to make similar content",
    "confidence": "high/medium/low - confidence in this analysis"
}}

Only respond with the JSON, no other text."""

    client = Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )

    # Parse JSON response
    try:
        import json
        analysis = json.loads(response.content[0].text)
        return analysis
    except:
        return {
            "title_hook": "Could not analyze",
            "topic_timing": "Unknown",
            "emotion_trigger": "Unknown",
            "format_type": "Unknown",
            "key_lesson": "Unable to extract",
            "replication_difficulty": "unknown",
            "confidence": "low"
        }


def batch_analyze_videos(videos: list, api_key: str, max_videos: int = 10) -> list:
    """
    Analyze multiple videos and return their success factors.
    Limits to max_videos to control API costs.
    """
    results = []
    for video in videos[:max_videos]:
        print(f"  Analyzing: {video['title'][:40]}...")
        analysis = analyze_success_factors(video, api_key)
        results.append({
            'video_id': video['video_id'],
            'title': video['title'],
            'channel': video.get('channel_name', ''),
            'analysis': analysis
        })
    return results


def enrich_history_with_analysis(api_key: str, max_new: int = 5) -> int:
    """
    Add success factor analysis to videos in history that don't have it yet.
    Returns number of videos analyzed.
    """
    history = load_history()

    # Find videos without analysis
    unanalyzed = [v for v in history if 'success_analysis' not in v]

    if not unanalyzed:
        return 0

    # Sort by velocity to analyze the best performers first
    unanalyzed.sort(key=lambda x: x.get('velocity_score', 0), reverse=True)

    analyzed_count = 0
    for video in unanalyzed[:max_new]:
        print(f"  Analyzing: {video['title'][:40]}...")
        try:
            analysis = analyze_success_factors(video, api_key)
            video['success_analysis'] = analysis
            analyzed_count += 1
        except Exception as e:
            print(f"    ⚠ Failed: {e}")

    if analyzed_count > 0:
        save_history(history)

    return analyzed_count


def get_common_success_factors(history: list = None) -> dict:
    """
    Aggregate success factors across all analyzed videos
    to find common patterns.
    """
    if history is None:
        history = load_history()

    analyzed = [v for v in history if 'success_analysis' in v]

    if not analyzed:
        return {'message': 'No analyzed videos yet'}

    from collections import Counter

    emotions = Counter()
    formats = Counter()
    difficulties = Counter()
    lessons = []

    for v in analyzed:
        analysis = v['success_analysis']
        emotions[analysis.get('emotion_trigger', 'unknown')] += 1
        formats[analysis.get('format_type', 'unknown')] += 1
        difficulties[analysis.get('replication_difficulty', 'unknown')] += 1
        if analysis.get('key_lesson'):
            lessons.append({
                'lesson': analysis['key_lesson'],
                'video': v['title'][:50],
                'velocity': v.get('velocity_score', 0)
            })

    # Sort lessons by velocity (best performing videos first)
    lessons.sort(key=lambda x: x['velocity'], reverse=True)

    return {
        'total_analyzed': len(analyzed),
        'top_emotions': dict(emotions.most_common(5)),
        'top_formats': dict(formats.most_common(5)),
        'difficulty_distribution': dict(difficulties),
        'top_lessons': lessons[:10]
    }


def format_success_report(api_key: str = None) -> str:
    """Generate a formatted success factors report"""
    history = load_history()

    # Optionally enrich with new analysis
    if api_key:
        new_count = enrich_history_with_analysis(api_key, max_new=3)
        if new_count > 0:
            print(f"✓ Analyzed {new_count} new videos")
            history = load_history()  # Reload

    factors = get_common_success_factors(history)

    if 'message' in factors:
        return factors['message']

    lines = []
    lines.append("=" * 60)
    lines.append("SUCCESS FACTORS ANALYSIS")
    lines.append("=" * 60)
    lines.append(f"Based on {factors['total_analyzed']} analyzed outperformers\n")

    lines.append("-" * 60)
    lines.append("TOP EMOTION TRIGGERS")
    lines.append("-" * 60)
    for emotion, count in factors['top_emotions'].items():
        pct = count / factors['total_analyzed'] * 100
        lines.append(f"  • {emotion}: {count} videos ({pct:.0f}%)")

    lines.append("\n" + "-" * 60)
    lines.append("TOP CONTENT FORMATS")
    lines.append("-" * 60)
    for fmt, count in factors['top_formats'].items():
        pct = count / factors['total_analyzed'] * 100
        lines.append(f"  • {fmt}: {count} videos ({pct:.0f}%)")

    lines.append("\n" + "-" * 60)
    lines.append("REPLICATION DIFFICULTY")
    lines.append("-" * 60)
    for diff, count in factors['difficulty_distribution'].items():
        lines.append(f"  • {diff}: {count} videos")

    lines.append("\n" + "-" * 60)
    lines.append("KEY LESSONS (from top performers)")
    lines.append("-" * 60)
    for i, lesson in enumerate(factors['top_lessons'][:5], 1):
        lines.append(f"\n{i}. {lesson['lesson']}")
        lines.append(f"   From: \"{lesson['video']}...\"")

    lines.append("\n" + "=" * 60)

    return "\n".join(lines)


if __name__ == "__main__":
    from config import ANTHROPIC_API_KEY

    if ANTHROPIC_API_KEY:
        print(format_success_report(ANTHROPIC_API_KEY))
    else:
        print("Set ANTHROPIC_API_KEY to run analysis")
