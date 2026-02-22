"""YouTube API wrapper with quota-optimized methods"""

import re
import time
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2  # Base delay, doubles each retry


def sanitize_error(error: HttpError) -> str:
    """Remove API key from error messages to prevent leaks"""
    error_str = str(error)
    # Remove any query string parameters that might contain the key
    error_str = re.sub(r'key=[^&\s]+', 'key=***', error_str)
    return error_str


def retry_on_error(func):
    """Decorator to retry API calls on transient failures"""
    def wrapper(*args, **kwargs):
        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                return func(*args, **kwargs)
            except HttpError as e:
                last_error = e
                # Don't retry on quota exceeded (403) or not found (404)
                if e.resp.status in (403, 404):
                    print(f"API error (not retrying): {sanitize_error(e)}")
                    return None if 'get_channel_info' in func.__name__ else []
                # Retry on rate limit (429) or server errors (5xx)
                if e.resp.status in (429, 500, 502, 503, 504):
                    delay = RETRY_DELAY_SECONDS * (2 ** attempt)
                    print(f"API error, retrying in {delay}s... ({sanitize_error(e)})")
                    time.sleep(delay)
                else:
                    print(f"API error: {sanitize_error(e)}")
                    return None if 'get_channel_info' in func.__name__ else []
        # All retries exhausted
        print(f"API error after {MAX_RETRIES} retries: {sanitize_error(last_error)}")
        return None if 'get_channel_info' in func.__name__ else []
    return wrapper


def parse_duration(iso_duration: str) -> int:
    """
    Parse ISO 8601 duration (PT1H2M3S or P1DT1H2M3S) to seconds.
    Returns 0 if parsing fails.

    Examples:
        PT1H2M3S -> 3723 seconds
        PT30M -> 1800 seconds
        P1DT12H -> 129600 seconds (36 hours)
    """
    if not iso_duration:
        return 0

    # Match days, hours, minutes, seconds
    # Format: P[nD]T[nH][nM][nS]
    pattern = r'P(?:(\d+)D)?T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
    match = re.match(pattern, iso_duration)

    if not match:
        return 0

    days = int(match.group(1) or 0)
    hours = int(match.group(2) or 0)
    minutes = int(match.group(3) or 0)
    seconds = int(match.group(4) or 0)

    return days * 86400 + hours * 3600 + minutes * 60 + seconds


class YouTubeClient:
    def __init__(self, api_key: str):
        """Initialize the YouTube API client"""
        self.youtube = build("youtube", "v3", developerKey=api_key)

    @retry_on_error
    def get_channel_info(self, channel_id: str) -> dict | None:
        """
        Get channel metadata including subscriber count.

        Returns:
            {
                "channel_id": str,
                "name": str,
                "subscribers": int
            }
        """
        response = self.youtube.channels().list(
            part="snippet,statistics",
            id=channel_id
        ).execute()

        if not response.get("items"):
            return None

        channel = response["items"][0]
        return {
            "channel_id": channel_id,
            "name": channel["snippet"]["title"],
            "subscribers": int(channel["statistics"].get("subscriberCount", 0))
        }

    @retry_on_error
    def get_recent_videos(self, channel_id: str, max_results: int = 5) -> list[dict]:
        """
        Get recent videos from a channel using the uploads playlist.

        Uses playlistItems endpoint (1 quota unit) instead of search (100 units).
        The uploads playlist ID = channel_id with "UC" replaced by "UU"

        Returns list of video metadata with stats.
        """
        # Convert channel ID to uploads playlist ID
        # UC... -> UU...
        if channel_id.startswith("UC"):
            uploads_playlist_id = "UU" + channel_id[2:]
        else:
            print(f"Unexpected channel ID format: {channel_id}")
            return []

        # Get playlist items (video IDs and basic info)
        playlist_response = self.youtube.playlistItems().list(
            part="snippet,contentDetails",
            playlistId=uploads_playlist_id,
            maxResults=max_results
        ).execute()

        if not playlist_response.get("items"):
            return []

        # Extract video IDs for batch details request
        video_ids = [
            item["contentDetails"]["videoId"]
            for item in playlist_response["items"]
        ]

        # Get detailed stats for all videos in one request
        return self.get_video_details(video_ids)

    def get_video_details(self, video_ids: list[str]) -> list[dict]:
        """
        Get detailed stats for multiple videos (batch up to 50).

        Returns list of:
            {
                "video_id": str,
                "title": str,
                "description": str,
                "published_at": datetime,
                "thumbnail_url": str,
                "views": int,
                "likes": int,
                "comments": int,
                "tags": list[str]
            }
        """
        if not video_ids:
            return []

        # Batch in groups of 50 (API limit)
        results = []
        for i in range(0, len(video_ids), 50):
            batch = video_ids[i:i + 50]
            batch_results = self._fetch_video_batch(batch)
            results.extend(batch_results)

        return results

    @retry_on_error
    def _fetch_video_batch(self, video_ids: list[str]) -> list[dict]:
        """Fetch a single batch of video details (max 50)"""
        response = self.youtube.videos().list(
            part="snippet,statistics,contentDetails",
            id=",".join(video_ids)
        ).execute()

        results = []
        for item in response.get("items", []):
            snippet = item["snippet"]
            stats = item["statistics"]
            content_details = item.get("contentDetails", {})

            # Parse published date
            published_str = snippet["publishedAt"]
            published_at = datetime.fromisoformat(
                published_str.replace("Z", "+00:00")
            )

            # Parse duration (ISO 8601 -> seconds)
            duration_iso = content_details.get("duration", "")
            duration_seconds = parse_duration(duration_iso)

            # Get best thumbnail available
            thumbnails = snippet.get("thumbnails", {})
            thumbnail_url = (
                thumbnails.get("maxres", {}).get("url") or
                thumbnails.get("high", {}).get("url") or
                thumbnails.get("medium", {}).get("url") or
                thumbnails.get("default", {}).get("url", "")
            )

            results.append({
                "video_id": item["id"],
                "title": snippet["title"],
                "description": snippet.get("description", ""),
                "published_at": published_at,
                "thumbnail_url": thumbnail_url,
                "views": int(stats.get("viewCount", 0)),
                "likes": int(stats.get("likeCount", 0)),
                "comments": int(stats.get("commentCount", 0)),
                "tags": snippet.get("tags", []),
                "channel_id": snippet["channelId"],
                "channel_name": snippet["channelTitle"],
                "duration_seconds": duration_seconds
            })

        return results
