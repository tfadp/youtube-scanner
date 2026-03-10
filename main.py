"""
YouTube Outperformance Scanner

Stages:
  scan    — YouTube fetch + scoring → saves output/last_scan.json
  enrich  — Claude summaries + ideas → reads scan, saves enriched result
  deliver — Email + report output → reads enriched result

Run: python main.py [--scan-only] [--enrich-only] [--deliver-only]
     python main.py [--batch N] [--all] [--status] [--reset]
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
    CHANNELS_FILE,
    OUTPUT_DIR,
    SCAN_RESULTS_FILE,
    EMAIL_ENABLED,
    EMAIL_TO,
    RESEND_API_KEY,
    EMAIL_FROM
)
from youtube_client import YouTubeClient
from scanner import find_outperformers, Channel, Video, Outperformer
from analyzer import get_pattern_summary
from idea_generator import generate_ideas
from video_summarizer import generate_summaries
from batch_manager import (
    get_batch_channels,
    advance_batch,
    reset_batch,
    print_batch_status
)
from email_sender import send_report_email, format_email_report
from history_db import add_outperformers


# --- Serialization helpers for intermediate results ---

def _serialize_outperformer(op: Outperformer) -> dict:
    """Convert Outperformer dataclass to JSON-safe dict."""
    return {
        'video': {
            'video_id': op.video.video_id,
            'channel_id': op.video.channel_id,
            'channel_name': op.video.channel_name,
            'title': op.video.title,
            'description': op.video.description,
            'views': op.video.views,
            'likes': op.video.likes,
            'comments': op.video.comments,
            'published_at': op.video.published_at.isoformat(),
            'thumbnail_url': op.video.thumbnail_url,
            'duration_seconds': op.video.duration_seconds,
            'tags': op.video.tags
        },
        'channel': {
            'channel_id': op.channel.channel_id,
            'name': op.channel.name,
            'subscribers': op.channel.subscribers,
            'category': op.channel.category,
            'about': op.channel.about
        },
        'ratio': op.ratio,
        'velocity_score': op.velocity_score,
        'age_hours': op.age_hours,
        'classification': op.classification,
        'title_patterns': op.title_patterns,
        'themes': op.themes,
        'is_noise': op.is_noise,
        'noise_type': op.noise_type,
        'summary': op.summary
    }


def _deserialize_outperformer(d: dict) -> Outperformer:
    """Rebuild Outperformer from JSON dict."""
    v = d['video']
    video = Video(
        video_id=v['video_id'],
        channel_id=v['channel_id'],
        channel_name=v['channel_name'],
        title=v['title'],
        description=v['description'],
        views=v['views'],
        likes=v['likes'],
        comments=v['comments'],
        published_at=datetime.fromisoformat(v['published_at']),
        thumbnail_url=v['thumbnail_url'],
        duration_seconds=v.get('duration_seconds', 0),
        tags=v.get('tags', [])
    )
    c = d['channel']
    channel = Channel(
        channel_id=c['channel_id'],
        name=c['name'],
        subscribers=c['subscribers'],
        category=c['category'],
        about=c.get('about', '')
    )
    return Outperformer(
        video=video,
        channel=channel,
        ratio=d['ratio'],
        velocity_score=d['velocity_score'],
        age_hours=d['age_hours'],
        classification=d['classification'],
        title_patterns=d.get('title_patterns', []),
        themes=d.get('themes', []),
        is_noise=d.get('is_noise', False),
        noise_type=d.get('noise_type', ''),
        summary=d.get('summary', '')
    )


def save_scan_results(outperformers: list, mid_performers: list, batch_info: str):
    """Persist scan results so enrich/deliver can run later without re-scanning."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    data = {
        'scanned_at': datetime.now().isoformat(),
        'batch_info': batch_info,
        'outperformers': [_serialize_outperformer(op) for op in outperformers],
        'mid_performers': [_serialize_outperformer(op) for op in mid_performers]
    }
    with open(SCAN_RESULTS_FILE, 'w') as f:
        json.dump(data, f, indent=2, default=str)
    print(f"💾 Scan results saved to {SCAN_RESULTS_FILE.name}")


def load_scan_results() -> tuple[list, list, str]:
    """Load persisted scan results. Returns (outperformers, mid_performers, batch_info)."""
    if not SCAN_RESULTS_FILE.exists():
        print(f"❌ No scan results found at {SCAN_RESULTS_FILE}")
        print("   Run a scan first: python main.py --scan-only")
        return [], [], ""

    with open(SCAN_RESULTS_FILE, 'r') as f:
        data = json.load(f)

    outperformers = [_deserialize_outperformer(d) for d in data.get('outperformers', [])]
    mid_performers = [_deserialize_outperformer(d) for d in data.get('mid_performers', [])]
    batch_info = data.get('batch_info', '')
    scanned_at = data.get('scanned_at', 'unknown')
    print(f"📂 Loaded scan results from {scanned_at}")
    return outperformers, mid_performers, batch_info


# --- Channel loading ---

def load_channels(filepath=None) -> list[Channel]:
    """Load channel list from JSON file with validation"""
    filepath = filepath or CHANNELS_FILE

    with open(filepath, "r") as f:
        data = json.load(f)

    if "channels" not in data:
        raise ValueError("channels.json missing 'channels' key")

    channels = []
    for i, ch in enumerate(data["channels"]):
        if "id" not in ch:
            print(f"⚠ Skipping channel #{i}: missing 'id' field")
            continue
        if "name" not in ch:
            print(f"⚠ Skipping channel #{i} ({ch['id']}): missing 'name' field")
            continue
        if not ch["id"].startswith("UC"):
            print(f"⚠ Skipping channel '{ch['name']}': invalid ID format (should start with 'UC')")
            continue

        channels.append(Channel(
            channel_id=ch["id"],
            name=ch["name"],
            subscribers=0,
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
            channel.name = info["name"]
            channel.about = info.get("about", "")
            updated.append(channel)
        else:
            print(f"  ⚠ Could not fetch info for {channel.name}")
    return updated


# --- Display helpers ---

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

    print("\nClassifications: 🔥 Trend-Jacker | 👑 Authority Builder | ⬆️ Standard\n")

    trend_jackers = [op for op in outperformers if op.classification == "trend_jacker"]
    authority_builders = [op for op in outperformers if op.classification == "authority_builder"]
    standard = [op for op in outperformers if op.classification == "standard"]

    for label, group, emoji in [
        ("🔥 TREND-JACKERS (high velocity within 72h)", trend_jackers, "🔥"),
        ("👑 AUTHORITY BUILDERS (still strong at 7+ days)", authority_builders, "👑"),
        ("⬆️ STANDARD OUTPERFORMERS", standard, "⬆️"),
    ]:
        if group:
            print("-" * 60)
            print(label)
            print("-" * 60)
            for i, op in enumerate(group, 1):
                print(f"\n#{i} — {op.video.title}")
                print(f"    Channel: {op.channel.name} ({op.channel.category})")
                print(f"    Views: {op.video.views:,} | Subs: {op.channel.subscribers:,}")
                print(f"    Ratio: {op.ratio:.1f}x | Velocity: {op.velocity_score:.2f}/day | Age: {format_age(op.age_hours)}")
                print(f"    Themes: {', '.join(op.themes) if op.themes else 'none'}")
                print(f"    Patterns: {', '.join(op.title_patterns) if op.title_patterns else 'none'}")
                if op.summary:
                    print(f"    Summary: {op.summary}")

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

    print("\n" + "-" * 60)
    print("CLASSIFICATION SUMMARY")
    print("-" * 60)
    print(f"  🔥 Trend-Jackers: {len(trend_jackers)}")
    print(f"  👑 Authority Builders: {len(authority_builders)}")
    print(f"  ⬆️ Standard: {len(standard)}")

    if ideas:
        print("\n" + "=" * 60)
        print("CONTENT IDEAS")
        print("=" * 60)
        print(f"\n{ideas}")


def save_report(outperformers: list, ideas: str = None, batch_info: str = "", output_dir=None):
    """Save report to file"""
    output_dir = output_dir or OUTPUT_DIR
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = os.path.join(output_dir, f"report_{timestamp}.txt")

    with open(filename, "w") as f:
        f.write(f"YouTube Outperformance Report\n")
        f.write(f"Generated: {datetime.now()}\n")
        f.write(f"Time Window: {MIN_VIDEO_AGE_HOURS}-{MAX_VIDEO_AGE_HOURS} hours\n")
        if batch_info:
            f.write(f"Batch: {batch_info}\n")
        f.write("=" * 60 + "\n\n")

        f.write(f"Found {len(outperformers)} outperforming videos\n\n")

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


# --- Pipeline stages ---

def stage_scan(args, batch_info_out: list) -> tuple[list, list, str]:
    """
    Stage 1: YouTube fetch + scoring.
    Saves results to output/last_scan.json so enrichment can run independently.
    """
    if not YOUTUBE_API_KEY:
        print("❌ Error: YOUTUBE_API_KEY not set in .env file")
        return [], [], ""

    all_channels = load_channels()
    total_channels = len(all_channels)

    if args.all:
        channels = all_channels
        batch_info = f"ALL ({total_channels} channels)"
        print(f"\nRunning ALL {total_channels} channels (no batching)")
        print("⚠️  Warning: This may exceed API quota!")
    else:
        batch_channels, current_batch, total_batches = get_batch_channels(
            all_channels, batch_num=args.batch
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

    yt = YouTubeClient(YOUTUBE_API_KEY)

    print("\nFetching subscriber counts...")
    channels = fetch_subscriber_counts(channels, yt)
    print(f"Successfully fetched {len(channels)} channels")

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

    # Persist for later stages
    save_scan_results(outperformers, mid_performers, batch_info)

    # Advance batch for next run
    if not args.all and args.batch is None:
        next_batch, total_batches = advance_batch()
        print(f"\n📊 Next run will scan batch {next_batch + 1}/{total_batches}")

    batch_info_out.append(batch_info)
    return outperformers, mid_performers, batch_info


def stage_enrich(outperformers: list) -> str:
    """
    Stage 2: Claude summaries + ideas.
    Reads from scan results if outperformers not provided.
    Returns ideas string.
    """
    ideas = None

    if ANTHROPIC_API_KEY and len(outperformers) > 0:
        print("\nGenerating video summaries with Claude...")
        try:
            generate_summaries(outperformers[:MAX_RESULTS_IN_REPORT], ANTHROPIC_API_KEY)
            print("✓ Summaries generated")
        except Exception as e:
            print(f"⚠ Could not generate summaries: {e}")

        print("\nGenerating content ideas with Claude...")
        try:
            ideas = generate_ideas(outperformers[:10], ANTHROPIC_API_KEY)
            print("✓ Ideas generated")
        except Exception as e:
            print(f"⚠ Could not generate ideas: {e}")
    elif not ANTHROPIC_API_KEY:
        print("\n⚠ ANTHROPIC_API_KEY not set — skipping enrichment")

    # Re-save with summaries attached
    # (summaries are mutated onto outperformer objects by generate_summaries)

    return ideas


def stage_deliver(outperformers: list, mid_performers: list, batch_info: str, ideas: str = None):
    """
    Stage 3: Console report + file report + email.
    """
    print_report(outperformers[:MAX_RESULTS_IN_REPORT], ideas)
    save_report(outperformers, ideas, batch_info)

    if EMAIL_ENABLED and EMAIL_TO and RESEND_API_KEY:
        print("\nSending email report...")
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


# --- Main entry point ---

def main():
    parser = argparse.ArgumentParser(description="YouTube Outperformance Scanner")
    parser.add_argument("--batch", type=int, help="Run specific batch number (0-indexed)")
    parser.add_argument("--all", action="store_true", help="Run all channels (ignores batching)")
    parser.add_argument("--status", action="store_true", help="Show batch status and exit")
    parser.add_argument("--reset", action="store_true", help="Reset batch counter to 0")
    parser.add_argument("--scan-only", action="store_true", help="Run scan stage only (saves results for later)")
    parser.add_argument("--enrich-only", action="store_true", help="Run enrichment on last scan (no YouTube API)")
    parser.add_argument("--deliver-only", action="store_true", help="Run delivery on last scan (no API calls)")
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

    # Determine which stages to run
    run_scan = not args.enrich_only and not args.deliver_only
    run_enrich = not args.scan_only and not args.deliver_only
    run_deliver = not args.scan_only and not args.enrich_only

    # Stage 1: Scan
    if run_scan:
        batch_info_out = []
        outperformers, mid_performers, batch_info = stage_scan(args, batch_info_out)
    else:
        # Load from persisted scan results
        outperformers, mid_performers, batch_info = load_scan_results()
        if not outperformers and not mid_performers:
            return

    # Stage 2: Enrich
    ideas = None
    if run_enrich:
        ideas = stage_enrich(outperformers)
        # Re-save scan results with summaries if we enriched
        if run_scan or args.enrich_only:
            save_scan_results(outperformers, mid_performers, batch_info)

    # Stage 3: Deliver
    if run_deliver:
        stage_deliver(outperformers, mid_performers, batch_info, ideas)

    print("\n" + "=" * 60)
    print(f"Completed: {datetime.now()}")


if __name__ == "__main__":
    main()
