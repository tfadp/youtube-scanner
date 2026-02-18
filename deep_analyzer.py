"""
Deep Analysis Module

Uses Claude to provide strategic-level insights on WHY videos outperform,
going far beyond surface-level pattern matching.

Analyzes:
- Hook mechanisms (psychological triggers)
- Title architecture (structural breakdown)
- Timing intelligence (trend-riding vs evergreen)
- Replication blueprints (actionable templates)
"""

import json
from anthropic import Anthropic
from history_db import load_history, save_history


def deep_analyze_video(video: dict, api_key: str) -> dict:
    """
    Run deep Claude analysis on a single video.

    Returns structured strategic insights.
    """
    duration_mins = video.get('duration_seconds', 0) / 60 if video.get('duration_seconds') else 0

    prompt = f"""You are a YouTube strategist who reverse-engineers viral content. Analyze this outperforming video with the depth of a professional content consultant.

VIDEO DATA:
- Title: "{video['title']}"
- Channel: {video.get('channel_name', 'Unknown')} ({video.get('channel_category', 'unknown')} category)
- Views: {video.get('views', 0):,}
- Subscribers: {video.get('subscribers', 0):,}
- View/Sub Ratio: {video.get('ratio', 0):.1f}x
- Velocity Score: {video.get('velocity_score', 0):.2f}
- Video Length: {duration_mins:.1f} minutes
- Age: {video.get('age_hours', 0):.0f} hours since posted
- Description: {video.get('description', '')[:500]}
- Tags: {', '.join(video.get('tags', [])[:15])}

Provide analysis in this exact JSON format:
{{
    "hook_mechanism": {{
        "primary_hook": "The main psychological trigger (curiosity gap, controversy, FOMO, social proof, stakes/bet, transformation, conflict, etc.)",
        "why_it_works": "1-2 sentences explaining the psychology - why does this make someone click?",
        "secondary_hooks": ["List any additional hooks at play"]
    }},
    "title_architecture": {{
        "structure": "Break down the title structure (e.g., '[Dollar amount] + [Challenge] + [Stakes]')",
        "power_elements": ["List the specific words/phrases that carry weight"],
        "specificity_score": "low/medium/high - how specific vs vague is the promise?",
        "length_analysis": "Is the length optimal? Why?"
    }},
    "timing_intelligence": {{
        "timing_type": "trend_ride (capitalizing on news/moment) | evergreen (works anytime) | seasonal (specific time of year)",
        "cultural_context": "What cultural moment, trend, or ongoing interest does this tap into? Be specific.",
        "shelf_life": "How long will this title continue to work? Why?"
    }},
    "content_format": {{
        "format_type": "The actual content format (not just 'challenge' - be specific like 'high-stakes skill bet' or 'celebrity drama reaction')",
        "why_format_works": "Why this format resonates with this audience",
        "production_requirements": "What does making this content actually require?"
    }},
    "replication_blueprint": {{
        "template": "A fill-in-the-blank template version of this title structure",
        "key_ingredients": ["The 3-4 must-have elements to make this work"],
        "adaptation_examples": ["2-3 specific title ideas using this template for different topics"],
        "common_mistakes": "What would make a copy of this fall flat?"
    }},
    "strategic_rating": {{
        "virality_factors": "high/medium/low - how many viral mechanics are at play?",
        "replication_difficulty": "easy/medium/hard - how hard to execute well?",
        "saturation_risk": "low/medium/high - is this format overdone?",
        "recommended_for": "What type of creator should use this approach?"
    }},
    "one_line_insight": "The single most important lesson from this video in one sentence"
}}

Be specific and actionable. No generic advice. Respond ONLY with the JSON."""

    client = Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )

    try:
        # Clean up response - sometimes Claude adds markdown
        text = response.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        analysis = json.loads(text)
        return analysis
    except Exception as e:
        return {
            "error": f"Could not parse analysis: {e}",
            "raw_response": response.content[0].text[:500]
        }


def batch_deep_analyze(videos: list, api_key: str, max_videos: int = 5) -> list:
    """
    Run deep analysis on multiple videos.
    Returns list of videos with their analysis.
    """
    results = []

    for i, video in enumerate(videos[:max_videos], 1):
        print(f"  [{i}/{min(len(videos), max_videos)}] Deep analyzing: {video['title'][:40]}...")

        try:
            analysis = deep_analyze_video(video, api_key)
            results.append({
                'video_id': video['video_id'],
                'title': video['title'],
                'channel': video.get('channel_name', ''),
                'velocity_score': video.get('velocity_score', 0),
                'ratio': video.get('ratio', 0),
                'deep_analysis': analysis
            })
        except Exception as e:
            print(f"    Failed: {e}")

    return results


def enrich_history_with_deep_analysis(api_key: str, max_new: int = 3) -> int:
    """
    Add deep analysis to top videos in history that don't have it.
    Focuses on highest velocity videos first.
    Returns count of newly analyzed videos.
    """
    history = load_history()

    # Find videos without deep analysis, sorted by velocity
    unanalyzed = [v for v in history if 'deep_analysis' not in v]
    unanalyzed.sort(key=lambda x: x.get('velocity_score', 0), reverse=True)

    if not unanalyzed:
        return 0

    analyzed_count = 0
    for video in unanalyzed[:max_new]:
        print(f"  Deep analyzing: {video['title'][:40]}...")
        try:
            analysis = deep_analyze_video(video, api_key)
            video['deep_analysis'] = analysis
            analyzed_count += 1
        except Exception as e:
            print(f"    Failed: {e}")

    if analyzed_count > 0:
        save_history(history)

    return analyzed_count


def get_strategic_patterns(history: list = None) -> dict:
    """
    Aggregate insights from deep analysis across all analyzed videos.
    Finds common strategic patterns.
    """
    if history is None:
        history = load_history()

    analyzed = [v for v in history if 'deep_analysis' in v and 'error' not in v.get('deep_analysis', {})]

    if not analyzed:
        return {'message': 'No videos with deep analysis yet'}

    from collections import Counter

    hooks = Counter()
    timing_types = Counter()
    formats = Counter()
    templates = []
    insights = []

    for v in analyzed:
        da = v['deep_analysis']

        # Count hook mechanisms
        if 'hook_mechanism' in da:
            hooks[da['hook_mechanism'].get('primary_hook', 'unknown')] += 1

        # Count timing types
        if 'timing_intelligence' in da:
            timing_types[da['timing_intelligence'].get('timing_type', 'unknown')] += 1

        # Count formats
        if 'content_format' in da:
            formats[da['content_format'].get('format_type', 'unknown')] += 1

        # Collect templates
        if 'replication_blueprint' in da:
            templates.append({
                'template': da['replication_blueprint'].get('template', ''),
                'video': v['title'][:50],
                'velocity': v.get('velocity_score', 0)
            })

        # Collect one-line insights
        if 'one_line_insight' in da:
            insights.append({
                'insight': da['one_line_insight'],
                'video': v['title'][:50],
                'velocity': v.get('velocity_score', 0)
            })

    # Sort by velocity
    templates.sort(key=lambda x: x['velocity'], reverse=True)
    insights.sort(key=lambda x: x['velocity'], reverse=True)

    return {
        'total_analyzed': len(analyzed),
        'top_hooks': dict(hooks.most_common(5)),
        'timing_breakdown': dict(timing_types),
        'top_formats': dict(formats.most_common(5)),
        'best_templates': templates[:5],
        'key_insights': insights[:5]
    }


def format_deep_analysis_report(video_analysis: dict) -> str:
    """Format a single video's deep analysis for display."""
    da = video_analysis.get('deep_analysis', {})

    if 'error' in da:
        return f"Analysis error: {da['error']}"

    lines = []
    lines.append(f"\n{'='*60}")
    lines.append(f"DEEP ANALYSIS: {video_analysis['title'][:50]}...")
    lines.append(f"Channel: {video_analysis['channel']} | Velocity: {video_analysis['velocity_score']:.2f}")
    lines.append('='*60)

    # Hook mechanism
    if 'hook_mechanism' in da:
        hm = da['hook_mechanism']
        lines.append(f"\nHOOK MECHANISM")
        lines.append(f"  Primary: {hm.get('primary_hook', 'N/A')}")
        lines.append(f"  Why it works: {hm.get('why_it_works', 'N/A')}")
        if hm.get('secondary_hooks'):
            lines.append(f"  Secondary: {', '.join(hm['secondary_hooks'])}")

    # Title architecture
    if 'title_architecture' in da:
        ta = da['title_architecture']
        lines.append(f"\nTITLE ARCHITECTURE")
        lines.append(f"  Structure: {ta.get('structure', 'N/A')}")
        lines.append(f"  Power elements: {', '.join(ta.get('power_elements', []))}")
        lines.append(f"  Specificity: {ta.get('specificity_score', 'N/A')}")

    # Timing
    if 'timing_intelligence' in da:
        ti = da['timing_intelligence']
        lines.append(f"\nTIMING")
        lines.append(f"  Type: {ti.get('timing_type', 'N/A')}")
        lines.append(f"  Context: {ti.get('cultural_context', 'N/A')}")
        lines.append(f"  Shelf life: {ti.get('shelf_life', 'N/A')}")

    # Replication blueprint
    if 'replication_blueprint' in da:
        rb = da['replication_blueprint']
        lines.append(f"\nREPLICATION BLUEPRINT")
        lines.append(f"  Template: {rb.get('template', 'N/A')}")
        lines.append(f"  Key ingredients:")
        for ing in rb.get('key_ingredients', []):
            lines.append(f"    - {ing}")
        lines.append(f"  Example adaptations:")
        for ex in rb.get('adaptation_examples', [])[:2]:
            lines.append(f"    - {ex}")
        lines.append(f"  Common mistakes: {rb.get('common_mistakes', 'N/A')}")

    # Strategic rating
    if 'strategic_rating' in da:
        sr = da['strategic_rating']
        lines.append(f"\nSTRATEGIC RATING")
        lines.append(f"  Virality factors: {sr.get('virality_factors', 'N/A')}")
        lines.append(f"  Replication difficulty: {sr.get('replication_difficulty', 'N/A')}")
        lines.append(f"  Saturation risk: {sr.get('saturation_risk', 'N/A')}")
        lines.append(f"  Best for: {sr.get('recommended_for', 'N/A')}")

    # One line insight
    if 'one_line_insight' in da:
        lines.append(f"\nKEY INSIGHT: {da['one_line_insight']}")

    return '\n'.join(lines)


def format_strategic_summary(patterns: dict) -> str:
    """Format the aggregated strategic patterns."""
    if 'message' in patterns:
        return patterns['message']

    lines = []
    lines.append('='*60)
    lines.append('STRATEGIC PATTERNS SUMMARY')
    lines.append('='*60)
    lines.append(f"Based on {patterns['total_analyzed']} deeply analyzed videos\n")

    lines.append('-'*60)
    lines.append('TOP PSYCHOLOGICAL HOOKS')
    lines.append('-'*60)
    for hook, count in patterns['top_hooks'].items():
        pct = count / patterns['total_analyzed'] * 100
        lines.append(f"  {hook}: {count} videos ({pct:.0f}%)")

    lines.append('\n' + '-'*60)
    lines.append('TIMING BREAKDOWN')
    lines.append('-'*60)
    for timing, count in patterns['timing_breakdown'].items():
        pct = count / patterns['total_analyzed'] * 100
        lines.append(f"  {timing}: {count} videos ({pct:.0f}%)")

    lines.append('\n' + '-'*60)
    lines.append('TOP CONTENT FORMATS')
    lines.append('-'*60)
    for fmt, count in patterns['top_formats'].items():
        lines.append(f"  {fmt}: {count} videos")

    lines.append('\n' + '-'*60)
    lines.append('BEST REPLICATION TEMPLATES')
    lines.append('-'*60)
    for i, t in enumerate(patterns['best_templates'], 1):
        lines.append(f"\n{i}. \"{t['template']}\"")
        lines.append(f"   From: {t['video']}...")

    lines.append('\n' + '-'*60)
    lines.append('KEY INSIGHTS (from top performers)')
    lines.append('-'*60)
    for i, ins in enumerate(patterns['key_insights'], 1):
        lines.append(f"\n{i}. {ins['insight']}")
        lines.append(f"   From: \"{ins['video']}...\"")

    lines.append('\n' + '='*60)

    return '\n'.join(lines)


def run_deep_analysis_report(api_key: str, top_n: int = 3) -> str:
    """
    Run deep analysis on top N videos and return formatted report.
    """
    history = load_history()

    if len(history) < 1:
        return "No videos in history to analyze."

    # Get top performers by velocity
    top_videos = sorted(history, key=lambda x: x.get('velocity_score', 0), reverse=True)[:top_n]

    print(f"\nRunning deep analysis on top {len(top_videos)} videos...")

    report_lines = []
    report_lines.append("\n" + "="*60)
    report_lines.append("DEEP ANALYSIS REPORT")
    report_lines.append("="*60)

    for video in top_videos:
        # Check if already analyzed
        if 'deep_analysis' not in video:
            analysis = deep_analyze_video(video, api_key)
            video['deep_analysis'] = analysis

        video_report = {
            'video_id': video['video_id'],
            'title': video['title'],
            'channel': video.get('channel_name', ''),
            'velocity_score': video.get('velocity_score', 0),
            'deep_analysis': video['deep_analysis']
        }

        report_lines.append(format_deep_analysis_report(video_report))

    # Save any new analysis
    save_history(history)

    # Add strategic summary
    patterns = get_strategic_patterns(history)
    if 'message' not in patterns:
        report_lines.append("\n")
        report_lines.append(format_strategic_summary(patterns))

    return '\n'.join(report_lines)


if __name__ == "__main__":
    from config import ANTHROPIC_API_KEY

    if ANTHROPIC_API_KEY:
        print(run_deep_analysis_report(ANTHROPIC_API_KEY, top_n=3))
    else:
        print("Set ANTHROPIC_API_KEY to run deep analysis")
