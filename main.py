"""
YouTube Outperformance Scanner
Run: python main.py [--batch N] [--all] [--status]
"""

import argparse
import json
import os
from datetime import datetime

from config import (
    YOUTUBE_API_KEY,
    ANTHROPIC_API_KEY,
    MAX_RESULTS_IN_REPORT,
    MIN_VIDEO_AGE_HOURS,
    MAX_VIDEO_AGE_HOURS,
    BATCH_SIZE,
    CHANNELS_FILE,
    EMAIL_ENABLED,
    EMAIL_TO,
    RESEND_API_KEY,
    EMAIL_FROM
)
from youtube_client import YouTubeClient
from scanner import find_outperformers, Channel
from analyzer import get_pattern_summary
from idea_generator import generate_ideas
from video_summarizer import generate_summaries
from batch_manager import (
    get_batch_channels,
    advance_batch,
    reset_batch,
    print_batch_status,
    load_batch_state
)
from email_sender import send_report_email, format_email_report
from history_db import add_outperformers


def load_channels(filepath: str = None) -> list[Channel]:
    """Load channel list from JSON file with validation"""
    filepath = filepath or CHANNELS_FILE

    with open(filepath, "r") as f:
        data = json.load(f)

    if "channels" not in data:
        raise ValueError("channels.json missing 'channels' key")

    channels = []
    for i, ch in enumerate(data["channels"]):
        # Validate required fields
        if "id" not in ch:
            print(f"⚠ Skipping channel #{i}: missing 'id' field")
            continue
        if "name" not in ch:
            print(f"⚠ Skipping channel #{i} ({ch['id']}): missing 'name' field")
            continue
        # Validate channel ID format (should start with UC)
        if not ch["id"].startswith("UC"):
            print(f"⚠ Skipping channel '{ch['name']}': invalid ID format (should start with 'UC')")
            continue

        channels.append(Channel(
            channel_id=ch["id"],
            name=ch["name"],
            subscribers=0,  # Will be fetched from API
            category=ch.get("category", "unknown")
        ))

    if not channels:
        raise ValueError("No valid channels found in channels.json")

    return channels


def fetch_subscriber_counts(channels: list[Channel], yt: YouTubeClient) -> list[Channel]:
    """Fetch current subscriber counts for all channels"""
    updated = []
    for channel in channels:
        info = yt.get_channel_info(channel.channel_id)
        if info:
            channel.subscribers = info["subscribers"]
            channel.name = info["name"]  # Use official name from API
            channel.about = info.get("about", "")
            updated.append(channel)
        else:
            print(f"  ⚠ Could not fetch info for {channel.name}")
    return updated


def format_age(hours: float) -> str:
    """Format age in hours to readable string"""
    if hours < 24:
        return f"{hours:.0f}h"
    days = hours / 24
    return f"{days:.1f}d"


def print_report(outperformers: list, ideas: str = None):
    """Print formatted report to console"""
    print("\n" + "=" * 60)
    print("OUTPERFORMERS (sorted by velocity score)")
    print("=" * 60)

    if not outperformers:
        print("\nNo outperforming videos found in the time window.")
        print(f"Looking at videos {MIN_VIDEO_AGE_HOURS}-{MAX_VIDEO_AGE_HOURS} hours old.")
        print("Try adjusting time windows or lowering MIN_RATIO in config.py")
        return

    # Classification legend
    print("\nClassifications: 🔥 Trend-Jacker | 👑 Authority Builder | ⬆️ Standard\n")

    # Group by classification
    trend_jackers = [op for op in outperformers if op.classification == "trend_jacker"]
    authority_builders = [op for op in outperformers if op.classification == "authority_builder"]
    standard = [op for op in outperformers if op.classification == "standard"]

    if trend_jackers:
        print("-" * 60)
        print("🔥 TREND-JACKERS (high velocity within 72h)")
        print("-" * 60)
        for i, op in enumerate(trend_jackers, 1):
            print(f"\n#{i} — {op.video.title}")
            print(f"    Channel: {op.channel.name} ({op.channel.category})")
            print(f"    Views: {op.video.views:,} | Subs: {op.channel.subscribers:,}")
            print(f"    Ratio: {op.ratio:.1f}x | Velocity: {op.velocity_score:.2f}/day | Age: {format_age(op.age_hours)}")
            print(f"    Themes: {', '.join(op.themes) if op.themes else 'none'}")
            print(f"    Patterns: {', '.join(op.title_patterns) if op.title_patterns else 'none'}")
            if op.summary:
                print(f"    Summary: {op.summary}")

    if authority_builders:
        print("\n" + "-" * 60)
        print("👑 AUTHORITY BUILDERS (still strong at 7+ days)")
        print("-" * 60)
        for i, op in enumerate(authority_builders, 1):
            print(f"\n#{i} — {op.video.title}")
            print(f"    Channel: {op.channel.name} ({op.channel.category})")
            print(f"    Views: {op.video.views:,} | Subs: {op.channel.subscribers:,}")
            print(f"    Ratio: {op.ratio:.1f}x | Velocity: {op.velocity_score:.2f}/day | Age: {format_age(op.age_hours)}")
            print(f"    Themes: {', '.join(op.themes) if op.themes else 'none'}")
            print(f"    Patterns: {', '.join(op.title_patterns) if op.title_patterns else 'none'}")
            if op.summary:
                print(f"    Summary: {op.summary}")

    if standard:
        print("\n" + "-" * 60)
        print("⬆️ STANDARD OUTPERFORMERS")
        print("-" * 60)
        for i, op in enumerate(standard, 1):
            print(f"\n#{i} — {op.video.title}")
            print(f"    Channel: {op.channel.name} ({op.channel.category})")
            print(f"    Views: {op.video.views:,} | Subs: {op.channel.subscribers:,}")
            print(f"    Ratio: {op.ratio:.1f}x | Velocity: {op.velocity_score:.2f}/day | Age: {format_age(op.age_hours)}")
            print(f"    Themes: {', '.join(op.themes) if op.themes else 'none'}")
            print(f"    Patterns: {', '.join(op.title_patterns) if op.title_patterns else 'none'}")
            if op.summary:
                print(f"    Summary: {op.summary}")

    # Pattern summary
    summary = get_pattern_summary(outperformers)

    print("\n" + "-" * 60)
    print("PATTERN SUMMARY")
    print("-" * 60)

    print("\nThemes:")
    for theme, count in summary["themes"].items():
        print(f"  • {theme}: {count} video{'s' if count > 1 else ''}")

    print("\nTitle Patterns:")
    for pattern, count in summary["patterns"].items():
        print(f"  • {pattern}: {count} video{'s' if count > 1 else ''}")

    # Classification summary
    print("\n" + "-" * 60)
    print("CLASSIFICATION SUMMARY")
    print("-" * 60)
    print(f"  🔥 Trend-Jackers: {len(trend_jackers)}")
    print(f"  👑 Authority Builders: {len(authority_builders)}")
    print(f"  ⬆️ Standard: {len(standard)}")

    # Ideas
    if ideas:
        print("\n" + "=" * 60)
        print("CONTENT IDEAS")
        print("=" * 60)
        print(f"\n{ideas}")


def save_report(outperformers: list, ideas: str = None, batch_info: str = "", output_dir: str = "output"):
    """Save report to file"""
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"{output_dir}/report_{timestamp}.txt"

    with open(filename, "w") as f:
        f.write(f"YouTube Outperformance Report\n")
        f.write(f"Generated: {datetime.now()}\n")
        f.write(f"Time Window: {MIN_VIDEO_AGE_HOURS}-{MAX_VIDEO_AGE_HOURS} hours\n")
        if batch_info:
            f.write(f"Batch: {batch_info}\n")
        f.write("=" * 60 + "\n\n")

        f.write(f"Found {len(outperformers)} outperforming videos\n\n")

        # Group by classification
        trend_jackers = [op for op in outperformers if op.classification == "trend_jacker"]
        authority_builders = [op for op in outperformers if op.classification == "authority_builder"]
        standard = [op for op in outperformers if op.classification == "standard"]

        f.write(f"Classification Summary:\n")
        f.write(f"  Trend-Jackers: {len(trend_jackers)}\n")
        f.write(f"  Authority Builders: {len(authority_builders)}\n")
        f.write(f"  Standard: {len(standard)}\n\n")

        for i, op in enumerate(outperformers, 1):
            class_label = {
                "trend_jacker": "[TREND-JACKER]",
                "authority_builder": "[AUTHORITY]",
                "standard": "[STANDARD]"
            }.get(op.classification, "")

            f.write(f"#{i} {class_label} — {op.video.title}\n")
            f.write(f"    Channel: {op.channel.name} ({op.channel.category})\n")
            f.write(f"    Views: {op.video.views:,} | Subs: {op.channel.subscribers:,}\n")
            f.write(f"    Ratio: {op.ratio:.1f}x | Velocity: {op.velocity_score:.2f}/day | Age: {format_age(op.age_hours)}\n")
            f.write(f"    URL: https://youtube.com/watch?v={op.video.video_id}\n")
            f.write(f"    Themes: {', '.join(op.themes) if op.themes else 'none'}\n")
            f.write(f"    Patterns: {', '.join(op.title_patterns) if op.title_patterns else 'none'}\n")
            if op.summary:
                f.write(f"    Summary: {op.summary}\n")
            f.write("\n")

        if ideas:
            f.write("\n" + "=" * 60 + "\n")
            f.write("CONTENT IDEAS\n")
            f.write("=" * 60 + "\n\n")
            f.write(ideas)

    print(f"\n📄 Report saved to: {filename}")
    return filename


def main():
    parser = argparse.ArgumentParser(description="YouTube Outperformance Scanner")
    parser.add_argument("--batch", type=int, help="Run specific batch number (0-indexed)")
    parser.add_argument("--all", action="store_true", help="Run all channels (ignores batching)")
    parser.add_argument("--status", action="store_true", help="Show batch status and exit")
    parser.add_argument("--reset", action="store_true", help="Reset batch counter to 0")
    args = parser.parse_args()

    # Handle status/reset commands
    if args.status:
        print_batch_status()
        return

    if args.reset:
        reset_batch()
        print("Batch counter reset to 0")
        return

    print("YouTube Outperformance Scanner")
    print(f"Started: {datetime.now()}")
    print("=" * 60)

    # Validate API keys
    if not YOUTUBE_API_KEY:
        print("❌ Error: YOUTUBE_API_KEY not set in .env file")
        return

    # Load all channels
    all_channels = load_channels()
    total_channels = len(all_channels)

    # Apply batching unless --all flag is used
    if args.all:
        channels = all_channels
        batch_info = f"ALL ({total_channels} channels)"
        print(f"\nRunning ALL {total_channels} channels (no batching)")
        print("⚠️  Warning: This may exceed API quota!")
    else:
        batch_channels, current_batch, total_batches = get_batch_channels(
            all_channels,
            batch_num=args.batch
        )
        channels = [
            Channel(
                channel_id=ch.channel_id,
                name=ch.name,
                subscribers=0,
                category=ch.category
            )
            for ch in batch_channels
        ]
        batch_info = f"{current_batch + 1}/{total_batches}"
        print(f"\nBatch {current_batch + 1} of {total_batches}")
        print(f"Scanning {len(channels)} of {total_channels} total channels")

    print(f"Time window: {MIN_VIDEO_AGE_HOURS}-{MAX_VIDEO_AGE_HOURS} hours ({MIN_VIDEO_AGE_HOURS/24:.1f}-{MAX_VIDEO_AGE_HOURS/24:.1f} days)")

    # Initialize YouTube client
    yt = YouTubeClient(YOUTUBE_API_KEY)

    # Fetch subscriber counts
    print("\nFetching subscriber counts...")
    channels = fetch_subscriber_counts(channels, yt)
    print(f"Successfully fetched {len(channels)} channels")

    # Find outperformers
    print("\nScanning for outperformers...")
    outperformers, mid_performers = find_outperformers(channels, yt)
    print(f"\n✓ Found {len(outperformers)} videos exceeding subscriber count")
    if mid_performers:
        print(f"📊 Found {len(mid_performers)} sports mid-performers (0.5x-0.75x fallback)")

    # Save to history database
    if outperformers:
        new_count = add_outperformers(outperformers)
        if new_count > 0:
            print(f"📚 Added {new_count} new videos to history database")

    # Generate video summaries (requires Anthropic key)
    if ANTHROPIC_API_KEY and len(outperformers) > 0:
        print("\nGenerating video summaries with Claude...")
        try:
            generate_summaries(outperformers[:MAX_RESULTS_IN_REPORT], ANTHROPIC_API_KEY)
            print("✓ Summaries generated")
        except Exception as e:
            print(f"⚠ Could not generate summaries: {e}")

    # Generate ideas (optional - requires Anthropic key)
    ideas = None
    if ANTHROPIC_API_KEY and len(outperformers) > 0:
        print("\nGenerating content ideas with Claude...")
        try:
            ideas = generate_ideas(outperformers[:10], ANTHROPIC_API_KEY)
            print("✓ Ideas generated")
        except Exception as e:
            print(f"⚠ Could not generate ideas: {e}")

    # Output
    print_report(outperformers[:MAX_RESULTS_IN_REPORT], ideas)
    save_report(outperformers, ideas, batch_info)

    # Send email report
    if EMAIL_ENABLED and EMAIL_TO and RESEND_API_KEY:
        print("\nSending email report...")
        # Use mid-performer fallback if no actionable insights after noise filtering
        insights = [op for op in outperformers if not op.is_noise]
        fallback = mid_performers if len(insights) == 0 and mid_performers else None
        if fallback:
            print("  ↳ No outperformer insights — including mid-performer fallback")
        subject, body, html_body = format_email_report(outperformers, batch_info, mid_performers=fallback)
        success = send_report_email(
            to_email=EMAIL_TO,
            subject=subject,
            body=body,
            resend_api_key=RESEND_API_KEY,
            from_email=EMAIL_FROM,
            html_body=html_body
        )
        if success:
            print(f"✓ Email sent to {EMAIL_TO}")
        else:
            print("⚠ Failed to send email")

    # Advance batch for next run (unless specific batch was requested or --all was used)
    if not args.all and args.batch is None:
        next_batch, total_batches = advance_batch()
        print(f"\n📊 Next run will scan batch {next_batch + 1}/{total_batches}")

    print("\n" + "=" * 60)
    print(f"Completed: {datetime.now()}")


if __name__ == "__main__":
    main()
