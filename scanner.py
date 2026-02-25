"""Core outperformance detection logic"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from config import (
    MIN_RATIO, MIN_RATIO_SPORTS, MIN_RATIO_MID, MIN_VIEWS, VIDEOS_PER_CHANNEL,
    MIN_VIDEO_AGE_HOURS, MAX_VIDEO_AGE_HOURS,
    SIGNAL_WINDOW_HOURS, VELOCITY_TREND_JACKER, VELOCITY_AUTHORITY,
    MIN_VIDEO_DURATION, SPORTS_CATEGORIES
)

if TYPE_CHECKING:
    from youtube_client import YouTubeClient


@dataclass
class Video:
    video_id: str
    channel_id: str
    channel_name: str
    title: str
    description: str
    views: int
    likes: int
    comments: int
    published_at: datetime
    thumbnail_url: str
    duration_seconds: int = 0
    tags: list = field(default_factory=list)


@dataclass
class Channel:
    channel_id: str
    name: str
    subscribers: int
    category: str  # competitor, athlete, culture, emerging, media
    about: str = ""  # Channel description from YouTube "About" page


@dataclass
class Outperformer:
    video: Video
    channel: Channel
    ratio: float                    # views / subscribers
    velocity_score: float           # ratio / days_since_posted
    age_hours: float                # hours since posted
    classification: str             # "trend_jacker", "authority_builder", or "standard"
    title_patterns: list = field(default_factory=list)
    themes: list = field(default_factory=list)
    is_noise: bool = False          # True if this should be excluded from insights
    noise_type: str = ""            # Why excluded: "event_recap", "live_stream", "political_news"
    summary: str = ""               # AI-generated summary of video content + channel context


def get_video_age_hours(published_at: datetime) -> float:
    """Get the age of a video in hours"""
    now = datetime.now(timezone.utc)

    # Ensure published_at is timezone-aware
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=timezone.utc)

    return (now - published_at).total_seconds() / 3600


def is_within_time_window(age_hours: float, min_hours: int, max_hours: int) -> bool:
    """Check if video age is within the acceptable window"""
    return min_hours <= age_hours <= max_hours


def calculate_velocity_score(ratio: float, age_hours: float) -> float:
    """
    Calculate Growth Velocity Score.

    Formula: (views/subscribers) / (days_since_posted)

    This normalizes the ratio by time, allowing fair comparison
    between a 3-day-old video and a 14-day-old video.
    """
    days = age_hours / 24
    if days <= 0:
        return 0
    return ratio / days


def classify_outperformer(ratio: float, velocity_score: float, age_hours: float) -> str:
    """
    Classify an outperformer based on their performance pattern.

    - trend_jacker: High velocity within 72 hours (great at reacting to trends)
    - authority_builder: Still performing well at 7+ days (evergreen content)
    - standard: Meets criteria but doesn't fit either category
    """
    # Trend-Jacker: High velocity within the signal window (72 hours)
    if age_hours <= SIGNAL_WINDOW_HOURS and velocity_score >= VELOCITY_TREND_JACKER:
        return "trend_jacker"

    # Authority Builder: Still strong at 7+ days
    if age_hours >= 168 and velocity_score >= VELOCITY_AUTHORITY:
        return "authority_builder"

    return "standard"


def find_outperformers(
    channels: list[Channel],
    youtube_client: "YouTubeClient"
) -> tuple[list[Outperformer], list[Outperformer]]:
    """
    Main scanner function with velocity scoring.

    For each channel:
    1. Get recent videos (within time window)
    2. Filter by age (48-168 hours to get clean data)
    3. Calculate ratio = views / subscribers
    4. Calculate velocity score = ratio / days
    5. Classify as trend_jacker, authority_builder, or standard
    6. Analyze title patterns and themes

    Returns (outperformers, mid_performers) both sorted by velocity score.
    Mid performers = sports videos between 0.5x and 0.75x ratio (fallback for empty reports).
    """
    # Import here to avoid circular imports
    from analyzer import (
        analyze_title, classify_themes,
        is_event_recap, is_live_stream, is_political_news, is_not_relevant
    )

    outperformers = []
    mid_performers = []
    total_channels = len(channels)

    for i, channel in enumerate(channels, 1):
        print(f"  Scanning [{i}/{total_channels}]: {channel.name}")

        # Skip channels with hidden/zero subscribers
        if channel.subscribers == 0:
            print(f"    ⚠ Skipping (no subscriber count)")
            continue

        # Get recent videos
        videos = youtube_client.get_recent_videos(
            channel.channel_id,
            max_results=VIDEOS_PER_CHANNEL
        )

        for video_data in videos:
            # Calculate age
            age_hours = get_video_age_hours(video_data["published_at"])

            # Check time window (48-168 hours by default)
            if not is_within_time_window(age_hours, MIN_VIDEO_AGE_HOURS, MAX_VIDEO_AGE_HOURS):
                continue

            # Skip Shorts - multiple detection methods
            # 1. Check for #shorts hashtag in title (most reliable)
            title_lower = video_data["title"].lower()
            if "#shorts" in title_lower or "#short" in title_lower or "#ytshorts" in title_lower:
                continue

            # 2. Check for "shorts" in tags
            video_tags = [t.lower() for t in video_data.get("tags", [])]
            if "shorts" in video_tags or "short" in video_tags or "ytshorts" in video_tags:
                continue

            # 3. Check duration - Shorts can be up to 3 min (180s)
            #    Skip if under 180s OR if duration is unknown (0)
            duration = video_data.get("duration_seconds", 0)
            if duration == 0 or duration < MIN_VIDEO_DURATION:
                continue

            # Check minimum views
            if video_data["views"] < MIN_VIEWS:
                continue

            # Calculate ratio
            ratio = video_data["views"] / channel.subscribers

            # Use lower threshold for sports channels
            min_ratio = MIN_RATIO_SPORTS if channel.category.lower() in SPORTS_CATEGORIES else MIN_RATIO

            # Check if outperforming
            if ratio >= min_ratio:
                # Calculate velocity score
                velocity = calculate_velocity_score(ratio, age_hours)

                # Classify the outperformer
                classification = classify_outperformer(ratio, velocity, age_hours)

                # Create Video object
                video = Video(
                    video_id=video_data["video_id"],
                    channel_id=channel.channel_id,
                    channel_name=channel.name,
                    title=video_data["title"],
                    description=video_data["description"],
                    views=video_data["views"],
                    likes=video_data["likes"],
                    comments=video_data["comments"],
                    published_at=video_data["published_at"],
                    thumbnail_url=video_data["thumbnail_url"],
                    duration_seconds=video_data.get("duration_seconds", 0),
                    tags=video_data.get("tags", [])
                )

                # Analyze patterns and themes
                patterns = analyze_title(video.title)
                themes = classify_themes(
                    video.title,
                    video.description,
                    video.tags
                )

                # Check noise filters (content that doesn't provide insights)
                noise_type = ""
                if is_event_recap(video.title, channel.category):
                    noise_type = "event_recap"
                elif is_live_stream(video.title):
                    noise_type = "live_stream"
                elif is_political_news(video.title, channel.category):
                    noise_type = "political_news"
                elif is_not_relevant(channel.category, patterns, themes):
                    noise_type = "not_relevant"

                outperformer = Outperformer(
                    video=video,
                    channel=channel,
                    ratio=ratio,
                    velocity_score=velocity,
                    age_hours=age_hours,
                    classification=classification,
                    title_patterns=patterns,
                    themes=themes,
                    is_noise=bool(noise_type),
                    noise_type=noise_type
                )
                outperformers.append(outperformer)

                # Show classification emoji
                class_emoji = {
                    "trend_jacker": "🔥",
                    "authority_builder": "👑",
                    "standard": "⬆️"
                }
                emoji = class_emoji.get(classification, "⬆️")
                noise_flag = f" [{noise_type.upper()}]" if noise_type else ""

                print(f"    ✓ Found: {video.title[:45]}... ({ratio:.1f}x, {age_hours:.0f}h) {emoji}{noise_flag}")

            # Mid performer fallback: sports videos between 0.5x and 0.75x
            elif channel.category.lower() in SPORTS_CATEGORIES and ratio >= MIN_RATIO_MID:
                velocity = calculate_velocity_score(ratio, age_hours)
                video = Video(
                    video_id=video_data["video_id"],
                    channel_id=channel.channel_id,
                    channel_name=channel.name,
                    title=video_data["title"],
                    description=video_data["description"],
                    views=video_data["views"],
                    likes=video_data["likes"],
                    comments=video_data["comments"],
                    published_at=video_data["published_at"],
                    thumbnail_url=video_data["thumbnail_url"],
                    duration_seconds=video_data.get("duration_seconds", 0),
                    tags=video_data.get("tags", [])
                )
                patterns = analyze_title(video.title)
                themes = classify_themes(video.title, video.description, video.tags)
                mid_performers.append(Outperformer(
                    video=video,
                    channel=channel,
                    ratio=ratio,
                    velocity_score=velocity,
                    age_hours=age_hours,
                    classification="standard",
                    title_patterns=patterns,
                    themes=themes
                ))

    # Sort by velocity score descending (normalizes for time)
    outperformers.sort(key=lambda x: x.velocity_score, reverse=True)
    mid_performers.sort(key=lambda x: x.ratio, reverse=True)

    return outperformers, mid_performers
