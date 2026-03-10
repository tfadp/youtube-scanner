"""Configuration and thresholds for YouTube Outperformance Scanner"""

import os
from pathlib import Path
from dotenv import load_dotenv

# All paths resolve from this root, regardless of where the script is invoked
PROJECT_ROOT = Path(__file__).parent

load_dotenv(PROJECT_ROOT / ".env")

# API Keys
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Scanner thresholds
MIN_RATIO = 1.0              # Views must exceed subscriber count (default)
MIN_RATIO_SPORTS = 0.75      # Lower bar for sports channels (large sub counts rarely hit 1x)
MIN_RATIO_MID = 0.5          # Floor for mid-performer fallback (shown when no outperformers found)
MIN_VIEWS = 10000            # Minimum views to consider

# Sports categories (use lower ratio threshold)
SPORTS_CATEGORIES = {"athlete", "sports", "basketball", "football", "soccer", "training"}
VIDEOS_PER_CHANNEL = 5       # How many recent videos to check per channel
MIN_VIDEO_DURATION = 180     # Minimum duration in seconds (excludes Shorts, which can be up to 3 min)

# Time windows (in hours)
MIN_VIDEO_AGE_HOURS = 48     # Ignore videos newer than this (avoids subscriber-only data)
MAX_VIDEO_AGE_HOURS = 168    # Max age to consider (7 days)

# Sweet spots for analysis
SIGNAL_WINDOW_HOURS = 72     # Primary "signal" window (packaging worked)
VALIDATION_WINDOW_HOURS = 336  # 14 days - validation window (retention worked)

# Velocity thresholds
VELOCITY_TREND_JACKER = 2.0   # ratio/days for "Trend-Jacker" classification
VELOCITY_AUTHORITY = 0.5      # ratio/days at 14 days for "Authority Builder"

# Output
MAX_RESULTS_IN_REPORT = 25   # Top N outperformers to show

# Batching (for large channel lists)
BATCH_SIZE = 3000            # Channels per batch (fits in 10k quota)

# File paths (resolved from PROJECT_ROOT)
CHANNELS_FILE = PROJECT_ROOT / "channels.json"
HISTORY_FILE = PROJECT_ROOT / "history.json"
HISTORY_DB_FILE = PROJECT_ROOT / "history.db"
BATCH_STATE_FILE = PROJECT_ROOT / "batch_state.json"
OUTPUT_DIR = PROJECT_ROOT / "output"
SCAN_RESULTS_FILE = PROJECT_ROOT / "output" / "last_scan.json"

# Email settings (Resend)
EMAIL_ENABLED = os.getenv("EMAIL_ENABLED", "false").lower() == "true"
EMAIL_TO = os.getenv("EMAIL_TO", "")
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "YouTube Scanner <scanner@resend.dev>")
