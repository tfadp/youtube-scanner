# File Reference

## Core Files
| File | Purpose |
|------|---------|
| `main.py` | Entry point - orchestrates scan, report, ideas |
| `scanner.py` | Core detection: ratio calc, velocity score, classification |
| `youtube_client.py` | YouTube API wrapper (quota-optimized) |
| `analyzer.py` | Title pattern & theme detection |
| `idea_generator.py` | Claude API integration for content ideas |
| `config.py` | Thresholds, time windows, API keys |

## Data Files
| File | Purpose |
|------|---------|
| `channels.json` | Channel IDs to monitor (86 currently) |
| `lookup_channels.py` | Utility to find channel IDs by @handle |

## Config
| File | Purpose |
|------|---------|
| `.env` | `YOUTUBE_API_KEY`, `ANTHROPIC_API_KEY` |
| `requirements.txt` | Dependencies |

## Output
| Location | Purpose |
|----------|---------|
| `output/report_*.txt` | Timestamped scan reports |

## Key Thresholds (config.py)
| Setting | Value | Purpose |
|---------|-------|---------|
| `MIN_RATIO` | 1.0 | Views must exceed subs |
| `MIN_VIEWS` | 10,000 | Minimum views filter |
| `MIN_VIDEO_AGE_HOURS` | 48 | Avoid subscriber-only early data |
| `MAX_VIDEO_AGE_HOURS` | 168 | 7-day scan window |
| `VELOCITY_TREND_JACKER` | 2.0 | ratio/day threshold for trend-jacker |
| `VELOCITY_AUTHORITY` | 0.5 | ratio/day at 7+ days for authority |
