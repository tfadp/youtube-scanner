"""
Email delivery for scan reports using Resend API.
Mobile-optimized HTML with inline styles for Gmail/iPhone.
"""

import requests
from datetime import datetime


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


def format_email_report(outperformers: list, batch_info: str = "") -> tuple[str, str, str]:
    """
    Format outperformers into email subject, plain text body, and HTML body.
    Mobile-optimized with inline styles.

    Returns (subject, text_body, html_body)
    """
    now = datetime.now().strftime("%Y-%m-%d")

    # Count by classification
    trend_jackers = [op for op in outperformers if op.classification == "trend_jacker"]
    authority_builders = [op for op in outperformers if op.classification == "authority_builder"]
    standard = [op for op in outperformers if op.classification == "standard"]

    # Subject line
    total = len(outperformers)
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

    if not outperformers:
        html_parts.append("""
                            <table role="presentation" cellpadding="0" cellspacing="0" style="width: 100%; background-color: #f8f9fa; border-radius: 12px;">
                                <tr>
                                    <td style="padding: 24px 20px; text-align: center;">
                                        <p style="margin: 0 0 8px 0; font-size: 18px; color: #333;">No outperformers found</p>
                                        <p style="margin: 0; font-size: 15px; color: #666;">This is normal - outperformers are rare signals worth watching.</p>
                                    </td>
                                </tr>
                            </table>
""")
    else:
        # Summary box
        html_parts.append(f"""
                            <table role="presentation" cellpadding="0" cellspacing="0" style="width: 100%; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 12px; margin-bottom: 24px;">
                                <tr>
                                    <td style="padding: 20px;">
                                        <p style="margin: 0 0 4px 0; font-size: 14px; color: rgba(255,255,255,0.9); text-transform: uppercase; letter-spacing: 0.5px;">Found</p>
                                        <p style="margin: 0; font-size: 36px; font-weight: 700; color: #ffffff;">{total}</p>
                                        <p style="margin: 4px 0 0 0; font-size: 16px; color: rgba(255,255,255,0.9);">outperforming videos</p>
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

    if not outperformers:
        text_lines.append("No outperforming videos found in this batch.")
    else:
        text_lines.append(f"Found {total} outperforming videos")
        text_lines.append("")

        for i, op in enumerate(outperformers[:25], 1):
            emoji = {"trend_jacker": "🔥", "authority_builder": "👑", "standard": "⬆️"}.get(op.classification, "")
            text_lines.append(f"{emoji} #{i} — {op.video.title}")
            text_lines.append(f"   Channel: {op.channel.name}")
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

    # Get description snippet
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
