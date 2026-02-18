"""
YouTube Format & Event Research Tool

Two modes:
1. Format Validation - Test if a format concept has proven demand
2. Event Research - Find successful stunt/challenge events to inspire productions

Usage:
    python research.py format "My House" --keywords "house shopping" "buying mom a house" "I BOUGHT"
    python research.py event --keywords "challenge" "stunt" "competition" --min-views 1000000
    python research.py format "My House" --interactive
"""

import argparse
import json
from datetime import datetime, timezone
from anthropic import Anthropic
from googleapiclient.discovery import build

from config import YOUTUBE_API_KEY, ANTHROPIC_API_KEY


def search_youtube(query: str, max_results: int = 25) -> list[dict]:
    """
    Search YouTube for videos matching query.
    Returns video data with stats.

    Note: This uses 100 quota units per search call.
    """
    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

    # Search for videos
    search_response = youtube.search().list(
        q=query,
        part="snippet",
        type="video",
        maxResults=max_results,
        order="viewCount",  # Get top performing first
        relevanceLanguage="en"
    ).execute()

    if not search_response.get("items"):
        return []

    # Get video IDs
    video_ids = [item["id"]["videoId"] for item in search_response["items"]]

    # Get detailed stats for each video
    videos_response = youtube.videos().list(
        part="snippet,statistics,contentDetails",
        id=",".join(video_ids)
    ).execute()

    results = []
    for video in videos_response.get("items", []):
        stats = video.get("statistics", {})
        snippet = video.get("snippet", {})

        # Parse publish date
        published = snippet.get("publishedAt", "")
        try:
            pub_date = datetime.fromisoformat(published.replace("Z", "+00:00"))
            age_days = (datetime.now(timezone.utc) - pub_date).days
        except:
            age_days = 0

        results.append({
            "video_id": video["id"],
            "title": snippet.get("title", ""),
            "channel": snippet.get("channelTitle", ""),
            "description": snippet.get("description", "")[:500],
            "views": int(stats.get("viewCount", 0)),
            "likes": int(stats.get("likeCount", 0)),
            "comments": int(stats.get("commentCount", 0)),
            "published": published[:10] if published else "",
            "age_days": age_days,
            "url": f"https://youtube.com/watch?v={video['id']}",
            "thumbnail": snippet.get("thumbnails", {}).get("high", {}).get("url", "")
        })

    return results


def analyze_format(format_name: str, keywords: list[str], min_views: int = 100000) -> dict:
    """
    Validate a format concept by searching for similar content.
    """
    print(f"\n🔍 Researching format: {format_name}")
    print(f"   Keywords: {', '.join(keywords)}")
    print(f"   Min views filter: {min_views:,}")

    all_videos = []

    for keyword in keywords:
        print(f"\n   Searching: \"{keyword}\"...")
        videos = search_youtube(keyword, max_results=15)

        # Filter by min views
        filtered = [v for v in videos if v["views"] >= min_views]
        print(f"   Found {len(filtered)} videos with {min_views:,}+ views")

        all_videos.extend(filtered)

    # Deduplicate by video_id
    seen = set()
    unique_videos = []
    for v in all_videos:
        if v["video_id"] not in seen:
            seen.add(v["video_id"])
            unique_videos.append(v)

    # Sort by views
    unique_videos.sort(key=lambda x: x["views"], reverse=True)

    # Calculate stats
    if unique_videos:
        total_views = sum(v["views"] for v in unique_videos)
        avg_views = total_views / len(unique_videos)
        avg_likes = sum(v["likes"] for v in unique_videos) / len(unique_videos)
        avg_age = sum(v["age_days"] for v in unique_videos) / len(unique_videos)
    else:
        total_views = avg_views = avg_likes = avg_age = 0

    return {
        "format_name": format_name,
        "keywords": keywords,
        "min_views": min_views,
        "total_videos": len(unique_videos),
        "total_views": total_views,
        "avg_views": avg_views,
        "avg_likes": avg_likes,
        "avg_age_days": avg_age,
        "top_videos": unique_videos[:20]
    }


def research_events(keywords: list[str], min_views: int = 1000000) -> dict:
    """
    Research successful event/stunt content.
    """
    print(f"\n🎬 Researching event concepts")
    print(f"   Keywords: {', '.join(keywords)}")
    print(f"   Min views filter: {min_views:,}")

    all_videos = []

    for keyword in keywords:
        print(f"\n   Searching: \"{keyword}\"...")
        videos = search_youtube(keyword, max_results=20)

        # Filter by min views
        filtered = [v for v in videos if v["views"] >= min_views]
        print(f"   Found {len(filtered)} videos with {min_views:,}+ views")

        all_videos.extend(filtered)

    # Deduplicate
    seen = set()
    unique_videos = []
    for v in all_videos:
        if v["video_id"] not in seen:
            seen.add(v["video_id"])
            unique_videos.append(v)

    # Sort by views
    unique_videos.sort(key=lambda x: x["views"], reverse=True)

    return {
        "keywords": keywords,
        "min_views": min_views,
        "total_videos": len(unique_videos),
        "total_views": sum(v["views"] for v in unique_videos),
        "top_videos": unique_videos[:25]
    }


def get_claude_format_analysis(data: dict, api_key: str) -> str:
    """Get Claude's analysis of format validation data"""

    videos_summary = "\n".join([
        f"- \"{v['title']}\" by {v['channel']} - {v['views']:,} views"
        for v in data['top_videos'][:15]
    ])

    prompt = f"""You are a YouTube content strategist helping Overtime (a sports media company) validate a format concept.

FORMAT BEING VALIDATED: "{data['format_name']}"
SEARCH KEYWORDS USED: {', '.join(data['keywords'])}

FINDINGS:
- Found {data['total_videos']} videos with {data['min_views']:,}+ views
- Total views across all videos: {data['total_views']:,}
- Average views per video: {data['avg_views']:,.0f}
- Average video age: {data['avg_age_days']:.0f} days

TOP PERFORMING VIDEOS:
{videos_summary}

Based on this data, provide:

1. **DEMAND VALIDATION** (2-3 sentences): Is there proven audience demand for this type of content? What's the evidence?

2. **PATTERN ANALYSIS** (2-3 sentences): What patterns do you see in the top-performing videos? (titles, channels, angles)

3. **OPPORTUNITY GAPS** (2-3 sentences): What angles are working that Overtime could do differently or better?

4. **RECOMMENDATION**: One of [STRONG SIGNAL / MODERATE SIGNAL / WEAK SIGNAL] with one sentence explaining why.

5. **SUGGESTED TEST**: One specific video concept Overtime could produce to test this format.

Be direct and actionable. Focus on what makes this work for a Gen Z sports audience."""

    client = Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}]
    )

    return response.content[0].text


def get_claude_event_analysis(data: dict, api_key: str) -> str:
    """Get Claude's analysis of event research data"""

    videos_summary = "\n".join([
        f"- \"{v['title']}\" by {v['channel']} - {v['views']:,} views"
        for v in data['top_videos'][:15]
    ])

    prompt = f"""You are a YouTube content strategist helping Overtime plan a made-for-YouTube event.

CONTEXT: Overtime wants to produce "eventized" content - must-watch moments like Netflix's climbing special. Budget is ~$200-300K production with $100K+ prize money. Goal is to create something so compelling people would share it.

RESEARCH FINDINGS (videos with {data['min_views']:,}+ views):
- Found {data['total_videos']} viral event/challenge videos
- Total views: {data['total_views']:,}

TOP PERFORMING EVENTS:
{videos_summary}

Based on this data, provide:

1. **WINNING FORMATS** (3-4 sentences): What event formats are crushing it? What makes them shareable?

2. **PRODUCTION PATTERNS** (2-3 sentences): What production elements appear in the biggest hits? (scale, stakes, personalities)

3. **OVERTIME FIT** (2-3 sentences): Which of these formats could Overtime realistically produce at $200-300K? What's the sports angle?

4. **TOP 3 EVENT CONCEPTS**: Specific event ideas Overtime could produce, each with:
   - Event name
   - One-line pitch
   - Why it would work for Overtime's audience
   - Estimated shareability (1-10)

5. **SPONSORSHIP ANGLE**: What brand categories would pay $500K+ to own this type of event?

Be creative but realistic about budget constraints. Focus on community/fan involvement."""

    client = Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )

    return response.content[0].text


def print_format_report(data: dict, analysis: str = None):
    """Print format validation report"""
    print("\n" + "=" * 70)
    print(f"FORMAT VALIDATION: {data['format_name']}")
    print("=" * 70)

    print(f"\nKeywords searched: {', '.join(data['keywords'])}")
    print(f"Minimum views filter: {data['min_views']:,}")

    print("\n" + "-" * 70)
    print("MARKET DATA")
    print("-" * 70)
    print(f"  Videos found: {data['total_videos']}")
    print(f"  Total views: {data['total_views']:,}")
    print(f"  Average views: {data['avg_views']:,.0f}")
    print(f"  Average likes: {data['avg_likes']:,.0f}")
    print(f"  Average age: {data['avg_age_days']:.0f} days")

    print("\n" + "-" * 70)
    print("TOP PERFORMING VIDEOS")
    print("-" * 70)

    for i, v in enumerate(data['top_videos'][:10], 1):
        print(f"\n#{i} — {v['title']}")
        print(f"    Channel: {v['channel']}")
        print(f"    Views: {v['views']:,} | Likes: {v['likes']:,}")
        print(f"    Published: {v['published']} ({v['age_days']} days ago)")
        print(f"    URL: {v['url']}")

    if analysis:
        print("\n" + "-" * 70)
        print("CLAUDE'S ANALYSIS")
        print("-" * 70)
        print(f"\n{analysis}")

    print("\n" + "=" * 70)


def print_event_report(data: dict, analysis: str = None):
    """Print event research report"""
    print("\n" + "=" * 70)
    print("EVENT RESEARCH REPORT")
    print("=" * 70)

    print(f"\nKeywords searched: {', '.join(data['keywords'])}")
    print(f"Minimum views filter: {data['min_views']:,}")
    print(f"Viral events found: {data['total_videos']}")
    print(f"Total views: {data['total_views']:,}")

    print("\n" + "-" * 70)
    print("VIRAL EVENTS")
    print("-" * 70)

    for i, v in enumerate(data['top_videos'][:15], 1):
        print(f"\n#{i} — {v['title']}")
        print(f"    Channel: {v['channel']}")
        print(f"    Views: {v['views']:,}")
        print(f"    URL: {v['url']}")

    if analysis:
        print("\n" + "-" * 70)
        print("CLAUDE'S ANALYSIS")
        print("-" * 70)
        print(f"\n{analysis}")

    print("\n" + "=" * 70)


def save_research(data: dict, filename: str):
    """Save research data to JSON"""
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2, default=str)
    print(f"\n💾 Data saved to: {filename}")


def main():
    parser = argparse.ArgumentParser(description="YouTube Format & Event Research")
    subparsers = parser.add_subparsers(dest="command", help="Research type")

    # Format validation
    format_parser = subparsers.add_parser("format", help="Validate a format concept")
    format_parser.add_argument("name", help="Format name (e.g., 'My House')")
    format_parser.add_argument("--keywords", "-k", nargs="+", required=True,
                               help="Search keywords to test")
    format_parser.add_argument("--min-views", type=int, default=100000,
                               help="Minimum views filter (default: 100000)")
    format_parser.add_argument("--save", help="Save results to JSON file")
    format_parser.add_argument("--no-claude", action="store_true",
                               help="Skip Claude analysis")

    # Event research
    event_parser = subparsers.add_parser("event", help="Research event concepts")
    event_parser.add_argument("--keywords", "-k", nargs="+", required=True,
                              help="Search keywords")
    event_parser.add_argument("--min-views", type=int, default=1000000,
                              help="Minimum views filter (default: 1000000)")
    event_parser.add_argument("--save", help="Save results to JSON file")
    event_parser.add_argument("--no-claude", action="store_true",
                              help="Skip Claude analysis")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        print("\n" + "=" * 70)
        print("EXAMPLES")
        print("=" * 70)
        print('\n# Validate "My House" format:')
        print('python research.py format "My House" -k "house shopping" "buying mom a house" "I BOUGHT house"')
        print('\n# Research viral events:')
        print('python research.py event -k "youtube challenge" "competition event" "stunt challenge" --min-views 5000000')
        print('\n# Save results:')
        print('python research.py format "My House" -k "house tour" --save my_house_research.json')
        return

    if not YOUTUBE_API_KEY:
        print("Error: YOUTUBE_API_KEY not set in .env")
        return

    if args.command == "format":
        # Format validation
        data = analyze_format(args.name, args.keywords, args.min_views)

        # Get Claude analysis
        analysis = None
        if not args.no_claude and ANTHROPIC_API_KEY and data['total_videos'] > 0:
            print("\n🤖 Getting Claude's analysis...")
            try:
                analysis = get_claude_format_analysis(data, ANTHROPIC_API_KEY)
            except Exception as e:
                print(f"⚠ Could not get analysis: {e}")

        print_format_report(data, analysis)

        if args.save:
            data['claude_analysis'] = analysis
            save_research(data, args.save)

    elif args.command == "event":
        # Event research
        data = research_events(args.keywords, args.min_views)

        # Get Claude analysis
        analysis = None
        if not args.no_claude and ANTHROPIC_API_KEY and data['total_videos'] > 0:
            print("\n🤖 Getting Claude's analysis...")
            try:
                analysis = get_claude_event_analysis(data, ANTHROPIC_API_KEY)
            except Exception as e:
                print(f"⚠ Could not get analysis: {e}")

        print_event_report(data, analysis)

        if args.save:
            data['claude_analysis'] = analysis
            save_research(data, args.save)


if __name__ == "__main__":
    main()
