# YouTube Outperformance Scanner

Finds YouTube videos that are significantly outperforming their channel's baseline — the signal in the noise. Scans 50+ channels, scores outlier performance, summarizes top videos with AI, and delivers a daily email report.

## What It Does

1. **Scans channels** — Pulls recent videos from 50+ tracked YouTube channels via the YouTube Data API
2. **Detects outliers** — Identifies videos performing well above the channel's historical average (views, engagement)
3. **AI summaries** — Uses Claude to summarize why each outlier is working (topic, format, hook)
4. **Trend analysis** — Groups outliers by emerging patterns (formats, topics, creator types)
5. **Email digest** — Sends a styled daily report with top performers and trend insights
6. **History tracking** — SQLite database prevents duplicate reporting and tracks performance over time

## Key Files

| File | Purpose |
|------|---------|
| `main.py` | Entry point — orchestrates the full pipeline |
| `scanner.py` | YouTube API scanning and outlier detection |
| `analyzer.py` | Channel-level analysis and scoring |
| `video_summarizer.py` | AI-powered video content summaries |
| `trend_analyzer.py` | Cross-channel trend detection |
| `email_sender.py` | HTML email report generation and delivery |
| `history_db.py` | SQLite history for deduplication |
| `channels.json` | Tracked channel list with filters |
| `config.py` | API keys, thresholds, and settings |

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Add your YouTube Data API key and Anthropic API key to .env
python main.py
```

## Filters

- Excludes live streams and political content
- Filters out event recaps and non-original content
- Configurable via `channels.json` and `config.py`
