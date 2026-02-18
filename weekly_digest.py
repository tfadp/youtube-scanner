"""
Weekly Digest Generator

Combines trend analysis, success factors, and pattern lifecycle
into a comprehensive weekly report with Claude-powered insights.

Run: python weekly_digest.py [--email]
"""

import argparse
from datetime import datetime
from anthropic import Anthropic

from config import ANTHROPIC_API_KEY, EMAIL_ENABLED, EMAIL_TO, RESEND_API_KEY, EMAIL_FROM
from history_db import load_history
from trend_analyzer import (
    analyze_pattern_lifecycle,
    get_week_over_week_changes,
    get_top_performers_this_week,
    get_emerging_channels
)
from success_analyzer import get_common_success_factors, enrich_history_with_analysis
from deep_analyzer import enrich_history_with_deep_analysis, get_strategic_patterns
from email_sender import send_report_email


def get_claude_weekly_insights(
    wow_changes: dict,
    lifecycle: dict,
    top_videos: list,
    success_factors: dict,
    strategic_patterns: dict,
    api_key: str
) -> str:
    """
    Get Claude's high-level insights on the week's trends.
    """
    # Build context
    emerging_themes = [t for t, d in lifecycle['themes'].items() if d['status'] == 'emerging']
    declining_themes = [t for t, d in lifecycle['themes'].items() if d['status'] == 'declining']
    emerging_patterns = [p for p, d in lifecycle['patterns'].items() if d['status'] == 'emerging']

    top_video_summary = "\n".join([
        f"- \"{v['title'][:50]}\" ({v.get('channel_name', '')}) - {v.get('velocity_score', 0):.2f} velocity"
        for v in top_videos[:5]
    ])

    themes_up = [f"{t[0]} (+{t[3]})" for t in wow_changes['themes'].get('up', [])[:5]]
    themes_down = [f"{t[0]} (-{t[3]})" for t in wow_changes['themes'].get('down', [])[:5]]

    top_emotions = list(success_factors.get('top_emotions', {}).keys())[:3]
    top_formats = list(success_factors.get('top_formats', {}).keys())[:3]

    # Deep analysis insights
    top_hooks = list(strategic_patterns.get('top_hooks', {}).keys())[:3]
    best_templates = strategic_patterns.get('best_templates', [])[:2]
    key_insights = strategic_patterns.get('key_insights', [])[:2]

    templates_text = "\n".join([f"  - \"{t['template']}\"" for t in best_templates]) if best_templates else "not enough data"
    insights_text = "\n".join([f"  - {i['insight']}" for i in key_insights]) if key_insights else "not enough data"

    prompt = f"""You are a YouTube content strategist analyzing this week's outperforming videos.

THIS WEEK'S DATA:
- Total outperformers: {wow_changes['total_this_week']} (vs {wow_changes['total_last_week']} last week)
- Themes trending UP: {', '.join(themes_up) if themes_up else 'none'}
- Themes trending DOWN: {', '.join(themes_down) if themes_down else 'none'}
- Emerging patterns: {', '.join(emerging_patterns) if emerging_patterns else 'none'}
- Declining patterns: {', '.join(declining_themes) if declining_themes else 'none'}

TOP PERFORMERS:
{top_video_summary}

SUCCESS FACTORS (from analyzed videos):
- Top emotions: {', '.join(top_emotions) if top_emotions else 'not enough data'}
- Top formats: {', '.join(top_formats) if top_formats else 'not enough data'}

DEEP ANALYSIS INSIGHTS:
- Top psychological hooks: {', '.join(top_hooks) if top_hooks else 'not enough data'}
- Working title templates:
{templates_text}
- Key strategic insights:
{insights_text}

Based on this data, provide:

1. **THE BIG STORY** (2-3 sentences): What's the main narrative this week? What's working and why?

2. **OPPORTUNITIES** (2-3 bullet points): What should content creators focus on RIGHT NOW based on emerging trends?

3. **WATCH OUT** (1-2 sentences): What trends are declining or oversaturated to avoid?

4. **ONE ACTIONABLE IDEA**: Give ONE specific video concept that capitalizes on this week's trends.

Keep it concise and actionable. No fluff."""

    client = Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}]
    )

    return response.content[0].text


def generate_weekly_digest(include_analysis: bool = True) -> tuple[str, str, str]:
    """
    Generate the weekly digest.
    Returns (subject, text_body, html_body)
    """
    history = load_history()

    if len(history) < 3:
        return (
            "Weekly Digest - Not Enough Data",
            "Need at least 3 outperformers in history to generate insights.",
            None
        )

    # Run analysis
    print("Analyzing trends...")
    lifecycle = analyze_pattern_lifecycle(history)
    wow_changes = get_week_over_week_changes(history)
    top_videos = get_top_performers_this_week(history, limit=10)
    emerging_channels = get_emerging_channels(history)

    # Enrich with success factor analysis
    if include_analysis and ANTHROPIC_API_KEY:
        print("Analyzing success factors...")
        enrich_history_with_analysis(ANTHROPIC_API_KEY, max_new=5)

        print("Running deep analysis on top performers...")
        enrich_history_with_deep_analysis(ANTHROPIC_API_KEY, max_new=3)
        history = load_history()

    success_factors = get_common_success_factors(history)
    strategic_patterns = get_strategic_patterns(history)

    # Get Claude's insights
    claude_insights = ""
    if ANTHROPIC_API_KEY and wow_changes['total_this_week'] > 0:
        print("Getting Claude insights...")
        try:
            claude_insights = get_claude_weekly_insights(
                wow_changes, lifecycle, top_videos,
                success_factors, strategic_patterns, ANTHROPIC_API_KEY
            )
        except Exception as e:
            print(f"⚠ Could not get Claude insights: {e}")

    # Build report
    now = datetime.now()
    subject = f"Weekly YouTube Insights [{now.strftime('%b %d')}]: {wow_changes['total_this_week']} outperformers"

    # ===== Text Body =====
    text_lines = []
    text_lines.append("=" * 60)
    text_lines.append("WEEKLY YOUTUBE DIGEST")
    text_lines.append("=" * 60)
    text_lines.append(f"Week of {now.strftime('%B %d, %Y')}")
    text_lines.append(f"Outperformers: {wow_changes['total_this_week']} this week vs {wow_changes['total_last_week']} last week")

    if claude_insights:
        text_lines.append("\n" + "-" * 60)
        text_lines.append("CLAUDE'S ANALYSIS")
        text_lines.append("-" * 60)
        text_lines.append(claude_insights)

    # Deep Analysis Insights
    if strategic_patterns and 'message' not in strategic_patterns:
        text_lines.append("\n" + "-" * 60)
        text_lines.append("DEEP ANALYSIS: WHAT'S ACTUALLY WORKING")
        text_lines.append("-" * 60)

        if strategic_patterns.get('top_hooks'):
            text_lines.append("\nTop Psychological Hooks:")
            for hook, count in list(strategic_patterns['top_hooks'].items())[:3]:
                text_lines.append(f"  • {hook}")

        if strategic_patterns.get('best_templates'):
            text_lines.append("\nProven Title Templates:")
            for i, t in enumerate(strategic_patterns['best_templates'][:3], 1):
                text_lines.append(f"  {i}. \"{t['template']}\"")
                text_lines.append(f"     From: {t['video'][:40]}...")

        if strategic_patterns.get('key_insights'):
            text_lines.append("\nKey Strategic Insights:")
            for i, ins in enumerate(strategic_patterns['key_insights'][:3], 1):
                text_lines.append(f"  {i}. {ins['insight']}")

    # Trends
    text_lines.append("\n" + "-" * 60)
    text_lines.append("TREND CHANGES")
    text_lines.append("-" * 60)

    if wow_changes['themes']['up']:
        text_lines.append("\nTrending UP:")
        for t in wow_changes['themes']['up'][:5]:
            text_lines.append(f"  • {t[0]}: {t[2]} → {t[1]}")

    if wow_changes['themes']['down']:
        text_lines.append("\nTrending DOWN:")
        for t in wow_changes['themes']['down'][:5]:
            text_lines.append(f"  • {t[0]}: {t[2]} → {t[1]}")

    # Pattern lifecycle
    emerging = [p for p, d in lifecycle['patterns'].items() if d['status'] == 'emerging']
    declining = [p for p, d in lifecycle['patterns'].items() if d['status'] == 'declining']

    if emerging:
        text_lines.append(f"\nEMERGING patterns: {', '.join(emerging[:5])}")
    if declining:
        text_lines.append(f"DECLINING patterns: {', '.join(declining[:5])}")

    # Top videos
    if top_videos:
        text_lines.append("\n" + "-" * 60)
        text_lines.append("TOP 5 THIS WEEK")
        text_lines.append("-" * 60)
        for i, v in enumerate(top_videos[:5], 1):
            text_lines.append(f"\n#{i} — {v['title']}")
            text_lines.append(f"    {v.get('channel_name', '')} | Velocity: {v.get('velocity_score', 0):.2f}")
            text_lines.append(f"    {v.get('url', '')}")

    # Channels to watch
    if emerging_channels:
        text_lines.append("\n" + "-" * 60)
        text_lines.append("CHANNELS TO WATCH")
        text_lines.append("-" * 60)
        for ch in emerging_channels[:5]:
            text_lines.append(f"  • {ch['channel']}: {ch['this_week']} hits")

    text_lines.append("\n" + "=" * 60)
    text_body = "\n".join(text_lines)

    # ===== HTML Body (Mobile-optimized, inline styles for Gmail/iPhone) =====
    html_parts = []
    html_parts.append("""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Weekly YouTube Digest</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f5f5f5; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; -webkit-font-smoothing: antialiased;">
    <table role="presentation" cellpadding="0" cellspacing="0" style="width: 100%; background-color: #f5f5f5;">
        <tr>
            <td style="padding: 20px 10px;">
                <table role="presentation" cellpadding="0" cellspacing="0" style="max-width: 600px; width: 100%; margin: 0 auto; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                    <tr>
                        <td style="padding: 24px 20px;">
""")

    html_parts.append(f"""
                            <h1 style="margin: 0 0 8px 0; font-size: 24px; font-weight: 700; color: #1a1a1a; line-height: 1.3;">Weekly YouTube Digest</h1>
                            <p style="margin: 0 0 20px 0; font-size: 16px; color: #666;">Week of {now.strftime('%B %d, %Y')}</p>
""")

    # Summary box
    change = wow_changes['total_this_week'] - wow_changes['total_last_week']
    change_str = f"+{change}" if change > 0 else str(change)
    change_color = "#28a745" if change > 0 else "#dc3545" if change < 0 else "#666"
    html_parts.append(f"""
                            <table role="presentation" cellpadding="0" cellspacing="0" style="width: 100%; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 12px; margin-bottom: 24px;">
                                <tr>
                                    <td style="padding: 20px;">
                                        <p style="margin: 0 0 4px 0; font-size: 14px; color: rgba(255,255,255,0.9); text-transform: uppercase; letter-spacing: 0.5px;">This Week</p>
                                        <p style="margin: 0; font-size: 36px; font-weight: 700; color: #ffffff;">{wow_changes['total_this_week']}</p>
                                        <p style="margin: 4px 0 0 0; font-size: 16px; color: rgba(255,255,255,0.9);">outperformers <span style="color: {change_color}; background: rgba(255,255,255,0.2); padding: 2px 8px; border-radius: 4px; font-weight: 600;">{change_str}</span></p>
                                    </td>
                                </tr>
                            </table>
""")

    # Claude's insights
    if claude_insights:
        html_parts.append(f"""
                            <table role="presentation" cellpadding="0" cellspacing="0" style="width: 100%; background-color: #f8f9fa; border-left: 4px solid #667eea; border-radius: 0 8px 8px 0; margin-bottom: 24px;">
                                <tr>
                                    <td style="padding: 16px 20px;">
                                        <p style="margin: 0 0 12px 0; font-size: 18px; font-weight: 600; color: #333;">Claude's Analysis</p>
                                        <div style="font-size: 16px; line-height: 1.6; color: #444;">{claude_insights.replace(chr(10), '<br>')}</div>
                                    </td>
                                </tr>
                            </table>
""")

    # Deep Analysis Section
    if strategic_patterns and 'message' not in strategic_patterns:
        html_parts.append("""
                            <table role="presentation" cellpadding="0" cellspacing="0" style="width: 100%; background-color: #1a1a2e; border-radius: 12px; margin-bottom: 24px;">
                                <tr>
                                    <td style="padding: 20px;">
                                        <p style="margin: 0 0 16px 0; font-size: 18px; font-weight: 600; color: #ffd700;">Deep Analysis: What's Actually Working</p>
""")

        if strategic_patterns.get('top_hooks'):
            html_parts.append("""<p style="margin: 0 0 8px 0; font-size: 14px; font-weight: 600; color: #ffffff;">Top Psychological Hooks:</p>""")
            for hook in list(strategic_patterns['top_hooks'].keys())[:3]:
                html_parts.append(f"""<p style="margin: 0 0 6px 0; font-size: 15px; color: #e0e0e0; padding-left: 12px;">• {hook}</p>""")

        if strategic_patterns.get('best_templates'):
            html_parts.append("""<p style="margin: 16px 0 8px 0; font-size: 14px; font-weight: 600; color: #ffffff;">Proven Title Templates:</p>""")
            for t in strategic_patterns['best_templates'][:3]:
                html_parts.append(f"""
                                        <table role="presentation" cellpadding="0" cellspacing="0" style="width: 100%; background-color: rgba(255,255,255,0.1); border-radius: 8px; margin-bottom: 8px;">
                                            <tr>
                                                <td style="padding: 12px;">
                                                    <p style="margin: 0; font-size: 15px; color: #ffd700; font-family: monospace;">{t['template']}</p>
                                                    <p style="margin: 6px 0 0 0; font-size: 13px; color: #aaa;">From: {t['video'][:35]}...</p>
                                                </td>
                                            </tr>
                                        </table>
""")

        if strategic_patterns.get('key_insights'):
            html_parts.append("""<p style="margin: 16px 0 8px 0; font-size: 14px; font-weight: 600; color: #ffffff;">Key Insights:</p>""")
            for i, ins in enumerate(strategic_patterns['key_insights'][:3], 1):
                html_parts.append(f"""<p style="margin: 0 0 8px 0; font-size: 15px; color: #e0e0e0; padding-left: 12px;">{i}. {ins['insight']}</p>""")

        html_parts.append("""
                                    </td>
                                </tr>
                            </table>
""")

    # Trend changes
    html_parts.append("""<p style="margin: 24px 0 12px 0; font-size: 20px; font-weight: 600; color: #333;">Trend Changes</p>""")

    if wow_changes['themes']['up']:
        html_parts.append("""<p style="margin: 0 0 8px 0; font-size: 16px; color: #28a745; font-weight: 600;">📈 Trending UP</p><p style="margin: 0 0 16px 0;">""")
        for t in wow_changes['themes']['up'][:5]:
            html_parts.append(f"""<span style="display: inline-block; background: #e9ecef; padding: 6px 14px; border-radius: 20px; margin: 4px 4px 4px 0; font-size: 14px; color: #333;">{t[0]} ({t[2]}→{t[1]})</span>""")
        html_parts.append("</p>")

    if wow_changes['themes']['down']:
        html_parts.append("""<p style="margin: 0 0 8px 0; font-size: 16px; color: #dc3545; font-weight: 600;">📉 Trending DOWN</p><p style="margin: 0 0 16px 0;">""")
        for t in wow_changes['themes']['down'][:5]:
            html_parts.append(f"""<span style="display: inline-block; background: #e9ecef; padding: 6px 14px; border-radius: 20px; margin: 4px 4px 4px 0; font-size: 14px; color: #333;">{t[0]} ({t[2]}→{t[1]})</span>""")
        html_parts.append("</p>")

    # Pattern lifecycle
    if emerging:
        html_parts.append("""<p style="margin: 0 0 8px 0; font-size: 16px; font-weight: 600;">🚀 Emerging Patterns</p><p style="margin: 0 0 16px 0;">""")
        for p in emerging[:5]:
            html_parts.append(f"""<span style="display: inline-block; background: #d4edda; color: #155724; padding: 6px 14px; border-radius: 20px; margin: 4px 4px 4px 0; font-size: 14px;">{p}</span>""")
        html_parts.append("</p>")

    if declining:
        html_parts.append("""<p style="margin: 0 0 8px 0; font-size: 16px; font-weight: 600;">⚠️ Declining Patterns</p><p style="margin: 0 0 16px 0;">""")
        for p in declining[:5]:
            html_parts.append(f"""<span style="display: inline-block; background: #f8d7da; color: #721c24; padding: 6px 14px; border-radius: 20px; margin: 4px 4px 4px 0; font-size: 14px;">{p}</span>""")
        html_parts.append("</p>")

    # Top videos
    if top_videos:
        html_parts.append("""<p style="margin: 24px 0 16px 0; font-size: 20px; font-weight: 600; color: #333;">Top 5 This Week</p>""")
        for i, v in enumerate(top_videos[:5], 1):
            url = v.get('url', f"https://youtube.com/watch?v={v['video_id']}")
            html_parts.append(f"""
                            <table role="presentation" cellpadding="0" cellspacing="0" style="width: 100%; border-bottom: 1px solid #eee; margin-bottom: 12px;">
                                <tr>
                                    <td style="padding: 12px 0 16px 0;">
                                        <p style="margin: 0 0 6px 0; font-size: 14px; color: #667eea; font-weight: 600;">#{i}</p>
                                        <a href="{url}" style="font-size: 17px; font-weight: 600; color: #1a73e8; text-decoration: none; line-height: 1.4; display: block; margin-bottom: 8px;">{v['title']}</a>
                                        <p style="margin: 0; font-size: 14px; color: #666;">{v.get('channel_name', '')} • Velocity: {v.get('velocity_score', 0):.2f} • {v.get('ratio', 0):.1f}x</p>
                                    </td>
                                </tr>
                            </table>
""")

    # Channels to watch
    if emerging_channels:
        html_parts.append("""<p style="margin: 24px 0 8px 0; font-size: 20px; font-weight: 600; color: #333;">Channels to Watch</p>
                            <p style="margin: 0 0 12px 0; font-size: 15px; color: #666;">Multiple outperformers this week:</p><p style="margin: 0;">""")
        for ch in emerging_channels[:5]:
            html_parts.append(f"""<span style="display: inline-block; background: #fff3cd; padding: 8px 14px; border-radius: 8px; margin: 4px 4px 4px 0; font-size: 14px; color: #856404; font-weight: 500;">{ch['channel']} ({ch['this_week']})</span>""")
        html_parts.append("</p>")

    html_parts.append("""
                            <table role="presentation" cellpadding="0" cellspacing="0" style="width: 100%; margin-top: 32px; border-top: 1px solid #eee;">
                                <tr>
                                    <td style="padding-top: 16px;">
                                        <p style="margin: 0; font-size: 13px; color: #999; text-align: center;">Generated by YouTube Outperformance Scanner</p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>""")

    html_body = "\n".join(html_parts)

    return subject, text_body, html_body


def main():
    parser = argparse.ArgumentParser(description="Generate weekly YouTube digest")
    parser.add_argument("--email", action="store_true", help="Send digest via email")
    parser.add_argument("--no-analysis", action="store_true", help="Skip Claude analysis (faster)")
    args = parser.parse_args()

    print("Generating weekly digest...")
    subject, text_body, html_body = generate_weekly_digest(include_analysis=not args.no_analysis)

    # Print to console
    print("\n" + text_body)

    # Send email if requested
    if args.email:
        if EMAIL_ENABLED and EMAIL_TO and RESEND_API_KEY:
            print("\nSending email...")
            success = send_report_email(
                to_email=EMAIL_TO,
                subject=subject,
                body=text_body,
                resend_api_key=RESEND_API_KEY,
                from_email=EMAIL_FROM,
                html_body=html_body
            )
            if success:
                print(f"✓ Email sent to {EMAIL_TO}")
            else:
                print("⚠ Failed to send email")
        else:
            print("⚠ Email not configured. Set EMAIL_ENABLED=true and configure Resend.")


if __name__ == "__main__":
    main()
