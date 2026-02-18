"""
Test email sending without using YouTube API quota.
Usage: python test_email.py
"""

from config import EMAIL_TO, RESEND_API_KEY, EMAIL_FROM
from email_sender import send_report_email

def main():
    if not RESEND_API_KEY:
        print("Error: RESEND_API_KEY not set in .env")
        return

    if not EMAIL_TO:
        print("Error: EMAIL_TO not set in .env")
        return

    print(f"Testing email to: {EMAIL_TO}")
    print(f"From: {EMAIL_FROM}")
    print(f"API Key: {RESEND_API_KEY[:10]}...")

    subject = "YouTube Scanner - Test Email"

    # Plain text fallback
    text_body = """This is a test email from your YouTube Outperformance Scanner.

If you're seeing this, your email configuration is working correctly.

The scanner will send you reports automatically on Mon/Wed/Fri at 9am UTC.
"""

    # HTML version
    html_body = """
    <html>
    <head>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.5; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }
            h1 { color: #1a1a1a; }
            .box { background: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0; }
            .video-card { border: 1px solid #ddd; border-radius: 8px; padding: 15px; margin: 15px 0; background: #fafafa; border-left: 4px solid #ff6b35; }
            .video-title a { color: #1a73e8; text-decoration: none; font-weight: bold; }
            .stats { display: inline-block; background: #e8e8e8; padding: 2px 8px; border-radius: 4px; margin-right: 8px; font-size: 13px; }
            .theme-tag { display: inline-block; background: #e3f2fd; color: #1565c0; padding: 2px 8px; border-radius: 12px; font-size: 12px; margin-right: 5px; }
        </style>
    </head>
    <body>
        <h1>YouTube Scanner - Test Email</h1>

        <div class="box">
            <p><strong>Your email is configured correctly!</strong></p>
            <p>The scanner will send you HTML-formatted reports that look like this:</p>
        </div>

        <h2>Example Video Card</h2>

        <div class="video-card">
            <div class="video-title">
                <a href="https://youtube.com/watch?v=dQw4w9WgXcQ" target="_blank">Example Outperformer Video Title Here</a>
            </div>
            <div style="color: #666; margin: 8px 0;">
                <strong>Example Channel</strong> (sports)
            </div>
            <div style="margin: 8px 0;">
                <span class="stats">1,234,567 views</span>
                <span class="stats">15.2x ratio</span>
                <span class="stats">5.4/day velocity</span>
                <span class="stats">2.1 days ago</span>
            </div>
            <div style="color: #555; font-style: italic; margin-top: 10px; padding: 10px; background: #fff; border-radius: 4px;">
                "This is where the video description snippet would appear, giving you context about what the video is about..."
            </div>
            <div style="margin-top: 8px;">
                <span class="theme-tag">basketball</span>
                <span class="theme-tag">highlights</span>
                <span class="theme-tag">viral</span>
            </div>
        </div>

        <hr style="margin-top: 40px; border: none; border-top: 1px solid #ddd;">
        <p style="color: #999; font-size: 12px;">Reports run Mon/Wed/Fri at 9am UTC</p>
    </body>
    </html>
    """

    success = send_report_email(
        to_email=EMAIL_TO,
        subject=subject,
        body=text_body,
        resend_api_key=RESEND_API_KEY,
        from_email=EMAIL_FROM,
        html_body=html_body
    )

    if success:
        print(f"\n✓ Test email sent successfully to {EMAIL_TO}")
        print("  Check your inbox for the HTML formatted email!")
    else:
        print("\n✗ Failed to send test email")


if __name__ == "__main__":
    main()
