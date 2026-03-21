"""
Email delivery for scan reports using Resend API.
Mobile-optimized HTML with inline styles for Gmail/iPhone.
"""

import requests
from datetime import datetime

from history_db import get_pattern_trends, get_tier_breakdown


def send_report_email(
    to_email: str,
    subject: str,
    body: str,
    resend_api_key: str,
    from_email: str = "YouTube Scanner <scanner@resend.dev>",
    html_body: str = None
) -> bool:
    """
    Send report via Resend API.

    Returns True if successful, False otherwise.
    """
    try:
        payload = {
            "from": from_email,
            "to": [to_email],
            "subject": subject,
        }

        # Prefer HTML if available
        if html_body:
            payload["html"] = html_body
        else:
            payload["text"] = body

        response = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {resend_api_key}",
                "Content-Type": "application/json"
            },
            json=payload
        )

        if response.status_code == 200:
            return True
        else:
            print(f"Resend API error: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        print(f"Failed to send email: {e}")
        return False


def truncate_description(desc: str, max_length: int = 120) -> str:
    """Truncate description to a readable snippet"""
    if not desc:
        return ""
    # Clean up whitespace
    desc = " ".join(desc.split())
    if len(desc) <= max_length:
        return desc
    return desc[:max_length].rsplit(' ', 1)[0] + "..."


def format_email_report(outperformers: list, batch_info: str = "", mid_performers: list = None) -> tuple[str, str, str]:
    """
    Format outperformers into email subject, plain text body, and HTML body.
    Mobile-optimized with inline styles.

    Noise (recaps, live streams, political news) is separated from the main
    analysis since it doesn't provide packaging insights.

    When mid_performers is provided, shows them as a fallback section
    (used when no outperformer insights remain after noise filtering).

    Returns (subject, text_body, html_body)
    """
    now = datetime.now().strftime("%Y-%m-%d")

    # Separate noise (recaps, live streams, political news) from actionable insights
    noise = [op for op in outperformers if getattr(op, 'is_noise', False)]
    insights = [op for op in outperformers if not getattr(op, 'is_noise', False)]

    # Count by classification (only from insights, not noise)
    trend_jackers = [op for op in insights if op.classification == "trend_jacker"]
    authority_builders = [op for op in insights if op.classification == "authority_builder"]
    standard = [op for op in insights if op.classification == "standard"]

    # Subject line (based on insights, not noise)
    total = len(insights)
    if total == 0:
        subject = f"YouTube Scanner [{now}]: No outperformers found"
    else:
        subject = f"YouTube Scanner [{now}]: {total} outperformers found"
        if trend_jackers:
            subject += f" ({len(trend_jackers)} trend-jackers)"

    # ===== HTML Body (Mobile-optimized) =====
    html_parts = []

    html_parts.append("""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YouTube Outperformance Report</title>
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
                            <h1 style="margin: 0 0 8px 0; font-size: 24px; font-weight: 700; color: #1a1a1a; line-height: 1.3;">YouTube Outperformance Report</h1>
                            <p style="margin: 0 0 20px 0; font-size: 16px; color: #666;">{datetime.now().strftime('%B %d, %Y')} {f'• {batch_info}' if batch_info else ''}</p>
""")

    if not insights:
        recap_note = f" ({len(noise)} filtered)" if noise else ""
        html_parts.append(f"""
                            <table role="presentation" cellpadding="0" cellspacing="0" style="width: 100%; background-color: #f8f9fa; border-radius: 12px;">
                                <tr>
                                    <td style="padding: 24px 20px; text-align: center;">
                                        <p style="margin: 0 0 8px 0; font-size: 18px; color: #333;">No outperformers found{recap_note}</p>
                                        <p style="margin: 0; font-size: 15px; color: #666;">This is normal - outperformers are rare signals worth watching.</p>
                                    </td>
                                </tr>
                            </table>
""")
    else:
        # Note about filtered noise
        recap_note = f' <span style="font-size: 13px; color: rgba(255,255,255,0.7);">({len(noise)} filtered)</span>' if noise else ""

        # Summary box
        html_parts.append(f"""
                            <table role="presentation" cellpadding="0" cellspacing="0" style="width: 100%; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 12px; margin-bottom: 24px;">
                                <tr>
                                    <td style="padding: 20px;">
                                        <p style="margin: 0 0 4px 0; font-size: 14px; color: rgba(255,255,255,0.9); text-transform: uppercase; letter-spacing: 0.5px;">Found</p>
                                        <p style="margin: 0; font-size: 36px; font-weight: 700; color: #ffffff;">{total}</p>
                                        <p style="margin: 4px 0 0 0; font-size: 16px; color: rgba(255,255,255,0.9);">outperforming videos{recap_note}</p>
                                    </td>
                                </tr>
                            </table>
""")

        # Breakdown
        html_parts.append(f"""
                            <table role="presentation" cellpadding="0" cellspacing="0" style="width: 100%; margin-bottom: 24px;">
                                <tr>
                                    <td style="padding: 12px 16px; background-color: #fff5f5; border-radius: 8px; margin-bottom: 8px;">
                                        <span style="font-size: 20px;">🔥</span>
                                        <span style="font-size: 16px; font-weight: 600; color: #c53030; margin-left: 8px;">{len(trend_jackers)} Trend-Jackers</span>
                                        <span style="font-size: 14px; color: #666; display: block; margin-top: 4px; margin-left: 36px;">High velocity within 72h</span>
                                    </td>
                                </tr>
                                <tr><td style="height: 8px;"></td></tr>
                                <tr>
                                    <td style="padding: 12px 16px; background-color: #fffbeb; border-radius: 8px;">
                                        <span style="font-size: 20px;">👑</span>
                                        <span style="font-size: 16px; font-weight: 600; color: #b7791f; margin-left: 8px;">{len(authority_builders)} Authority Builders</span>
                                        <span style="font-size: 14px; color: #666; display: block; margin-top: 4px; margin-left: 36px;">Still strong at 7+ days</span>
                                    </td>
                                </tr>
                                <tr><td style="height: 8px;"></td></tr>
                                <tr>
                                    <td style="padding: 12px 16px; background-color: #f0fff4; border-radius: 8px;">
                                        <span style="font-size: 20px;">⬆️</span>
                                        <span style="font-size: 16px; font-weight: 600; color: #276749; margin-left: 8px;">{len(standard)} Standard</span>
                                        <span style="font-size: 14px; color: #666; display: block; margin-top: 4px; margin-left: 36px;">Outperforming videos</span>
                                    </td>
                                </tr>
                            </table>
""")

        # Trend Jackers section
        if trend_jackers:
            html_parts.append("""
                            <p style="margin: 24px 0 16px 0; font-size: 20px; font-weight: 600; color: #c53030;">🔥 Trend-Jackers</p>
""")
            for op in trend_jackers[:25]:
                html_parts.append(format_video_card_html(op, "#ff6b35"))

        # Authority Builders section
        if authority_builders:
            html_parts.append("""
                            <p style="margin: 24px 0 16px 0; font-size: 20px; font-weight: 600; color: #b7791f;">👑 Authority Builders</p>
""")
            for op in authority_builders[:25]:
                html_parts.append(format_video_card_html(op, "#ffd700"))

        # Standard section
        if standard:
            html_parts.append("""
                            <p style="margin: 24px 0 16px 0; font-size: 20px; font-weight: 600; color: #276749;">⬆️ Standard Outperformers</p>
""")
            for op in standard[:25]:
                html_parts.append(format_video_card_html(op, "#4CAF50"))

    # Mid-performer fallback section (shown when no outperformer insights)
    if mid_performers:
        html_parts.append(f"""
                            <table role="presentation" cellpadding="0" cellspacing="0" style="width: 100%; background: linear-gradient(135deg, #4a6fa5 0%, #536b8a 100%); border-radius: 12px; margin: 24px 0 16px 0;">
                                <tr>
                                    <td style="padding: 20px;">
                                        <p style="margin: 0 0 4px 0; font-size: 14px; color: rgba(255,255,255,0.9); text-transform: uppercase; letter-spacing: 0.5px;">Fallback</p>
                                        <p style="margin: 0; font-size: 20px; font-weight: 700; color: #ffffff;">No outperformers this batch</p>
                                        <p style="margin: 4px 0 0 0; font-size: 15px; color: rgba(255,255,255,0.85);">Here are the strongest sports mid-performers (0.5x+)</p>
                                    </td>
                                </tr>
                            </table>
""")
        for op in mid_performers[:10]:
            html_parts.append(format_video_card_html(op, "#4a6fa5"))

    # Trends section (only if we have historical data)
    html_parts.append(_format_trends_html())

    # Tier breakdown section
    html_parts.append(_format_tiers_html())

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

    # ===== Plain text fallback =====
    text_lines = []
    text_lines.append("=" * 50)
    text_lines.append("YOUTUBE OUTPERFORMANCE REPORT")
    text_lines.append("=" * 50)
    text_lines.append(f"Date: {datetime.now()}")
    if batch_info:
        text_lines.append(f"Batch: {batch_info}")
    text_lines.append("")

    if not insights:
        recap_note = f" ({len(noise)} filtered)" if noise else ""
        text_lines.append(f"No outperforming videos found in this batch.{recap_note}")
    else:
        recap_note = f" ({len(noise)} filtered)" if noise else ""
        text_lines.append(f"Found {total} outperforming videos{recap_note}")
        text_lines.append("")

        for i, op in enumerate(insights[:25], 1):
            emoji = {"trend_jacker": "🔥", "authority_builder": "👑", "standard": "⬆️"}.get(op.classification, "")
            text_lines.append(f"{emoji} #{i} — {op.video.title}")
            text_lines.append(f"   Channel: {op.channel.name}")
            text_lines.append(f"   Views: {op.video.views:,} | Ratio: {op.ratio:.1f}x")
            if op.summary:
                text_lines.append(f"   Summary: {op.summary}")
            text_lines.append(f"   Watch: https://youtube.com/watch?v={op.video.video_id}")
            text_lines.append("")

    # Mid-performer fallback for plain text
    if mid_performers:
        text_lines.append("")
        text_lines.append("-" * 50)
        text_lines.append("SPORTS MID-PERFORMERS (0.5x+ fallback)")
        text_lines.append("-" * 50)
        text_lines.append("No outperformers this batch. Best sports mid-performers:")
        text_lines.append("")
        for i, op in enumerate(mid_performers[:10], 1):
            text_lines.append(f"📊 #{i} — {op.video.title}")
            text_lines.append(f"   Channel: {op.channel.name} ({op.channel.category})")
            text_lines.append(f"   Views: {op.video.views:,} | Ratio: {op.ratio:.1f}x")
            text_lines.append(f"   Watch: https://youtube.com/watch?v={op.video.video_id}")
            text_lines.append("")

    text_body = "\n".join(text_lines)

    return subject, text_body, html_body


def format_video_card_html(op, border_color: str) -> str:
    """Format a single video as a mobile-optimized HTML card"""
    video_url = f"https://youtube.com/watch?v={op.video.video_id}"

    # Format age
    if op.age_hours < 24:
        age_str = f"{op.age_hours:.0f}h ago"
    else:
        age_str = f"{op.age_hours/24:.1f}d ago"

    # Show AI summary if available, otherwise fall back to description snippet
    if op.summary:
        desc_html = f"""<p style="margin: 12px 0 0 0; font-size: 14px; color: #333; background: #f0f7ff; padding: 10px; border-radius: 6px; border-left: 3px solid #1a73e8;">{op.summary}</p>"""
    else:
        desc_snippet = truncate_description(op.video.description)
        desc_html = f"""<p style="margin: 12px 0 0 0; font-size: 14px; color: #555; font-style: italic; background: #f8f9fa; padding: 10px; border-radius: 6px;">"{desc_snippet}"</p>""" if desc_snippet else ""

    # Themes as tags
    themes_html = ""
    if op.themes:
        theme_spans = "".join([f'<span style="display: inline-block; background: #e3f2fd; color: #1565c0; padding: 4px 10px; border-radius: 12px; font-size: 13px; margin: 4px 4px 0 0;">{t}</span>' for t in op.themes[:4]])
        themes_html = f'<p style="margin: 10px 0 0 0;">{theme_spans}</p>'

    return f"""
                            <table role="presentation" cellpadding="0" cellspacing="0" style="width: 100%; border-left: 4px solid {border_color}; background-color: #fafafa; border-radius: 0 8px 8px 0; margin-bottom: 12px;">
                                <tr>
                                    <td style="padding: 16px;">
                                        <a href="{video_url}" style="font-size: 17px; font-weight: 600; color: #1a73e8; text-decoration: none; line-height: 1.4; display: block; margin-bottom: 8px;">{op.video.title}</a>
                                        <p style="margin: 0 0 8px 0; font-size: 15px; font-weight: 500; color: #333;">{op.channel.name} <span style="color: #999; font-weight: 400;">({op.channel.category})</span></p>
                                        <p style="margin: 0;">
                                            <span style="display: inline-block; background: #e8e8e8; padding: 4px 10px; border-radius: 4px; font-size: 13px; color: #333; margin-right: 6px;">{op.video.views:,} views</span>
                                            <span style="display: inline-block; background: #e8e8e8; padding: 4px 10px; border-radius: 4px; font-size: 13px; color: #333; margin-right: 6px;">{op.ratio:.1f}x</span>
                                            <span style="display: inline-block; background: #e8e8e8; padding: 4px 10px; border-radius: 4px; font-size: 13px; color: #333;">{age_str}</span>
                                        </p>
                                        {desc_html}
                                        {themes_html}
                                    </td>
                                </tr>
                            </table>
"""


def _format_trends_html() -> str:
    """Build HTML for pattern/theme trend section. Returns empty string if no data."""
    try:
        trends = get_pattern_trends(weeks=4)
    except Exception as e:
        print(f"⚠ Trends section skipped: {e}")
        return ""

    if trends.get('weeks_analyzed', 0) < 2:
        return ""

    # Pick top movers (rising or falling, sorted by absolute % change)
    all_trends = []
    for name, info in trends.get('theme_trends', {}).items():
        if info['direction'] != 'stable':
            all_trends.append((name, 'theme', info))
    for name, info in trends.get('pattern_trends', {}).items():
        if info['direction'] != 'stable':
            all_trends.append((name, 'pattern', info))

    all_trends.sort(key=lambda x: abs(x[2]['pct_change']), reverse=True)
    top_movers = all_trends[:6]

    if not top_movers:
        return ""

    rows_html = ""
    for name, kind, info in top_movers:
        arrow = "📈" if info['direction'] == 'rising' else "📉"
        color = "#276749" if info['direction'] == 'rising' else "#c53030"
        sign = "+" if info['pct_change'] > 0 else ""
        rows_html += f"""
                                <tr>
                                    <td style="padding: 6px 0; font-size: 14px; color: #333;">{arrow} {name}</td>
                                    <td style="padding: 6px 0; font-size: 14px; color: {color}; text-align: right; font-weight: 600;">{sign}{info['pct_change']:.0f}%</td>
                                </tr>"""

    return f"""
                            <table role="presentation" cellpadding="0" cellspacing="0" style="width: 100%; margin-top: 24px;">
                                <tr>
                                    <td colspan="2" style="padding: 0 0 12px 0;">
                                        <p style="margin: 0; font-size: 18px; font-weight: 600; color: #1a1a1a;">📊 Trend Lines</p>
                                        <p style="margin: 4px 0 0 0; font-size: 13px; color: #999;">Based on {trends['weeks_analyzed']} weeks of data ({trends.get('recent_videos', 0)} recent vs {trends.get('prior_videos', 0)} prior videos)</p>
                                    </td>
                                </tr>
                                {rows_html}
                            </table>
"""


def format_weekly_digest_email(digest: dict) -> tuple[str, str, str]:
    """
    Format the weekly intelligence digest into email subject, text, and HTML.
    Mobile-optimized. Focused on actionable sports content intelligence.

    Returns (subject, text_body, html_body)
    """
    now = datetime.now()
    stats = digest.get('summary_stats', {})
    total = stats.get('total_videos', 0)

    subject = f"Weekly Sports Intel [{now.strftime('%b %d')}]: {total} outperformers"

    # ===== Plain text =====
    text_lines = []
    text_lines.append("=" * 55)
    text_lines.append("WEEKLY SPORTS INTELLIGENCE DIGEST")
    text_lines.append("=" * 55)
    text_lines.append(f"Week of {now.strftime('%B %d, %Y')}")
    text_lines.append(f"Total outperformers: {total}")
    text_lines.append("")

    # Winning patterns
    patterns = digest.get('winning_patterns', [])
    if patterns:
        text_lines.append("-" * 55)
        text_lines.append("WHAT'S WORKING (Title Patterns)")
        text_lines.append("-" * 55)
        for p in patterns[:8]:
            text_lines.append(
                f"  {p['pattern']}: {p['count']} videos, "
                f"avg {p['avg_ratio']:.1f}x ratio, {p['avg_velocity']:.1f} velocity"
            )
        text_lines.append("")

    # Title formulas
    formulas = digest.get('title_formulas', [])
    if formulas:
        text_lines.append("-" * 55)
        text_lines.append("TITLE FORMULAS THAT WORKED")
        text_lines.append("-" * 55)
        for f in formulas[:5]:
            text_lines.append(f"  {f['formula']} ({f['count']}x, avg {f['avg_ratio']:.1f}x)")
            for title in f['example_titles'][:2]:
                text_lines.append(f"    e.g. \"{title[:60]}\"")
        text_lines.append("")

    # Emerging creators
    emerging = digest.get('emerging_creators', [])
    if emerging:
        text_lines.append("-" * 55)
        text_lines.append("EMERGING CREATORS TO WATCH (<200K subs)")
        text_lines.append("-" * 55)
        for e in emerging[:5]:
            text_lines.append(
                f"  {e['channel_name']} ({e['subscribers']:,} subs, {e['channel_category']})"
            )
            text_lines.append(f"    \"{e['best_title'][:60]}\" — {e['best_ratio']:.1f}x")
            text_lines.append(f"    {e['url']}")
        text_lines.append("")

    # Top videos
    top = digest.get('top_videos', [])
    if top:
        text_lines.append("-" * 55)
        text_lines.append("TOP 10 THIS WEEK")
        text_lines.append("-" * 55)
        for i, v in enumerate(top[:10], 1):
            text_lines.append(f"  #{i} {v['title'][:55]}")
            text_lines.append(
                f"      {v['channel_name']} | {v['views']:,} views | "
                f"{v['ratio']:.1f}x | {v['url']}"
            )
        text_lines.append("")

    # By sport
    by_sport = digest.get('by_sport', {})
    if by_sport:
        text_lines.append("-" * 55)
        text_lines.append("BY SPORT")
        text_lines.append("-" * 55)
        for sport, data in by_sport.items():
            text_lines.append(f"\n  {sport} ({data['total_videos']} videos)")
            if data['top_patterns']:
                text_lines.append(f"    Top patterns: {', '.join(list(data['top_patterns'].keys())[:3])}")
            for v in data['top_videos'][:3]:
                text_lines.append(f"    - \"{v['title'][:50]}\" ({v['ratio']:.1f}x)")

    text_lines.append("\n" + "=" * 55)
    text_body = "\n".join(text_lines)

    # ===== HTML (mobile-optimized, inline styles) =====
    html_parts = []
    html_parts.append(f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0;padding:0;background:#f5f5f5;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
<table role="presentation" cellpadding="0" cellspacing="0" style="width:100%;background:#f5f5f5;">
<tr><td style="padding:20px 10px;">
<table role="presentation" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.1);">
<tr><td style="padding:24px 20px;">

<h1 style="margin:0 0 8px;font-size:22px;font-weight:700;color:#1a1a1a;">Weekly Sports Intelligence</h1>
<p style="margin:0 0 20px;font-size:15px;color:#666;">{now.strftime('%B %d, %Y')} &bull; {total} outperformers found</p>
""")

    # --- Winning Patterns section ---
    if patterns:
        html_parts.append("""
<table role="presentation" cellpadding="0" cellspacing="0" style="width:100%;background:#f0f7ff;border-radius:12px;margin-bottom:20px;">
<tr><td style="padding:16px 20px;">
<p style="margin:0 0 12px;font-size:17px;font-weight:700;color:#1a1a1a;">What's Working</p>
""")
        for p in patterns[:6]:
            bar_width = min(100, int(p['score'] / max(patterns[0]['score'], 1) * 100))
            html_parts.append(f"""
<p style="margin:0 0 2px;font-size:14px;font-weight:600;color:#333;">{p['pattern'].replace('_', ' ').title()}</p>
<table role="presentation" cellpadding="0" cellspacing="0" style="width:100%;margin-bottom:10px;">
<tr>
<td style="width:{bar_width}%;height:6px;background:#1a73e8;border-radius:3px;"></td>
<td style="height:6px;background:#e8e8e8;border-radius:0 3px 3px 0;"></td>
</tr>
</table>
<p style="margin:-6px 0 10px;font-size:12px;color:#666;">{p['count']} videos &bull; avg {p['avg_ratio']:.1f}x ratio &bull; {p['avg_velocity']:.1f} velocity</p>
""")
        html_parts.append("</td></tr></table>")

    # --- Title Formulas section ---
    if formulas:
        html_parts.append("""
<p style="margin:20px 0 12px;font-size:17px;font-weight:700;color:#1a1a1a;">Title Formulas That Worked</p>
""")
        for f in formulas[:5]:
            examples_html = "".join(
                f'<p style="margin:4px 0 0 12px;font-size:13px;color:#555;font-style:italic;">"{t[:55]}"</p>'
                for t in f['example_titles'][:2]
            )
            html_parts.append(f"""
<table role="presentation" cellpadding="0" cellspacing="0" style="width:100%;border-left:3px solid #ffd700;background:#fffdf0;border-radius:0 8px 8px 0;margin-bottom:10px;">
<tr><td style="padding:12px 16px;">
<p style="margin:0;font-size:15px;font-weight:600;color:#333;">{f['formula'].replace('_', ' ')}</p>
<p style="margin:4px 0 0;font-size:12px;color:#888;">{f['count']} videos &bull; avg {f['avg_ratio']:.1f}x ratio</p>
{examples_html}
</td></tr></table>
""")

    # --- Emerging Creators section ---
    if emerging:
        html_parts.append("""
<p style="margin:20px 0 12px;font-size:17px;font-weight:700;color:#1a1a1a;">Emerging Creators (&lt;200K subs)</p>
<p style="margin:0 0 12px;font-size:13px;color:#888;">Smaller channels punching above their weight this week</p>
""")
        for e in emerging[:5]:
            html_parts.append(f"""
<table role="presentation" cellpadding="0" cellspacing="0" style="width:100%;border-left:3px solid #28a745;background:#f0fff4;border-radius:0 8px 8px 0;margin-bottom:10px;">
<tr><td style="padding:12px 16px;">
<p style="margin:0 0 4px;font-size:15px;font-weight:600;color:#333;">{e['channel_name']}</p>
<p style="margin:0 0 6px;font-size:12px;color:#888;">{e['subscribers']:,} subs &bull; {e['channel_category']}</p>
<a href="{e['url']}" style="font-size:14px;color:#1a73e8;text-decoration:none;">{e['best_title'][:55]}</a>
<p style="margin:4px 0 0;font-size:12px;color:#666;">{e['best_ratio']:.1f}x ratio &bull; Patterns: {', '.join(e['patterns'][:3]) if e['patterns'] else 'none'}</p>
</td></tr></table>
""")

    # --- Top Videos section ---
    if top:
        html_parts.append("""
<p style="margin:20px 0 12px;font-size:17px;font-weight:700;color:#1a1a1a;">Top 10 This Week</p>
""")
        for i, v in enumerate(top[:10], 1):
            class_emoji = {"trend_jacker": "🔥", "authority_builder": "👑"}.get(v['classification'], "⬆️")
            html_parts.append(f"""
<table role="presentation" cellpadding="0" cellspacing="0" style="width:100%;border-bottom:1px solid #eee;margin-bottom:8px;">
<tr><td style="padding:10px 0;">
<p style="margin:0 0 4px;font-size:13px;color:#999;">{class_emoji} #{i} &bull; {v['channel_name']} ({v['channel_category']})</p>
<a href="{v['url']}" style="font-size:15px;font-weight:600;color:#1a73e8;text-decoration:none;line-height:1.4;">{v['title'][:65]}</a>
<p style="margin:4px 0 0;font-size:12px;color:#666;">{v['views']:,} views &bull; {v['ratio']:.1f}x &bull; {v['subscribers']:,} subs</p>
</td></tr></table>
""")

    # --- By Sport section ---
    if by_sport:
        html_parts.append("""
<p style="margin:20px 0 12px;font-size:17px;font-weight:700;color:#1a1a1a;">By Sport</p>
""")
        for sport, data in by_sport.items():
            top_pats = ', '.join(list(data['top_patterns'].keys())[:3]) if data['top_patterns'] else 'none'
            html_parts.append(f"""
<table role="presentation" cellpadding="0" cellspacing="0" style="width:100%;background:#f8f9fa;border-radius:8px;margin-bottom:10px;">
<tr><td style="padding:12px 16px;">
<p style="margin:0 0 4px;font-size:15px;font-weight:600;color:#333;">{sport}</p>
<p style="margin:0 0 6px;font-size:12px;color:#888;">{data['total_videos']} videos &bull; Top patterns: {top_pats}</p>
""")
            for v in data['top_videos'][:3]:
                html_parts.append(f"""<p style="margin:0 0 4px;font-size:13px;color:#555;">• <a href="{v['url']}" style="color:#1a73e8;text-decoration:none;">{v['title'][:50]}</a> ({v['ratio']:.1f}x)</p>""")
            html_parts.append("</td></tr></table>")

    # Footer
    html_parts.append("""
<table role="presentation" cellpadding="0" cellspacing="0" style="width:100%;margin-top:24px;border-top:1px solid #eee;">
<tr><td style="padding-top:12px;">
<p style="margin:0;font-size:12px;color:#999;text-align:center;">YouTube Sports Intelligence &bull; Generated automatically</p>
</td></tr></table>

</td></tr></table>
</td></tr></table>
</body></html>""")

    html_body = "\n".join(html_parts)
    return subject, text_body, html_body


def _format_tiers_html() -> str:
    """Build HTML for subscriber tier breakdown. Returns empty string if no data."""
    try:
        tiers = get_tier_breakdown()
    except Exception as e:
        print(f"⚠ Tiers section skipped: {e}")
        return ""

    # Only show if we have data in at least 2 tiers
    active_tiers = {k: v for k, v in tiers.items() if v['total_videos'] > 0}
    if len(active_tiers) < 2:
        return ""

    rows_html = ""
    tier_labels = {'emerging': '🌱 Emerging', 'mid': '📊 Mid-size', 'large': '🏆 Large'}

    for tier_name, data in active_tiers.items():
        label = tier_labels.get(tier_name, tier_name)
        top_pattern = next(iter(data['top_patterns']), 'none') if data['top_patterns'] else 'none'
        top_theme = next(iter(data['top_themes']), 'none') if data['top_themes'] else 'none'
        rows_html += f"""
                                <tr>
                                    <td style="padding: 8px 0; border-bottom: 1px solid #f0f0f0;">
                                        <p style="margin: 0; font-size: 14px; font-weight: 600; color: #333;">{label} <span style="font-weight: 400; color: #999;">({data['range']})</span></p>
                                        <p style="margin: 4px 0 0 0; font-size: 13px; color: #666;">{data['total_videos']} videos · avg velocity {data['avg_velocity']:.2f} · top: {top_pattern}, {top_theme}</p>
                                    </td>
                                </tr>"""

    return f"""
                            <table role="presentation" cellpadding="0" cellspacing="0" style="width: 100%; margin-top: 24px;">
                                <tr>
                                    <td style="padding: 0 0 12px 0;">
                                        <p style="margin: 0; font-size: 18px; font-weight: 600; color: #1a1a1a;">📏 By Channel Size</p>
                                        <p style="margin: 4px 0 0 0; font-size: 13px; color: #999;">What works at different subscriber tiers</p>
                                    </td>
                                </tr>
                                {rows_html}
                            </table>
"""
