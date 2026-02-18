# Deployment

## Local Setup
```bash
cd "/Users/danporter/Desktop/Beast You Tube/youtube-scanner"
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Environment Variables
| Key | Purpose | Get it from |
|-----|---------|-------------|
| `YOUTUBE_API_KEY` | YouTube Data API v3 | console.cloud.google.com |
| `ANTHROPIC_API_KEY` | Claude for idea generation | console.anthropic.com |

## Run Scanner
```bash
source venv/bin/activate
python main.py
```

## Add New Channels
```bash
# Edit lookup_channels.py CHANNELS list, then:
python lookup_channels.py
cp channels_verified.json channels.json
```

## API Quota (YouTube)
- Free tier: 10,000 units/day
- playlistItems.list: 1 unit (we use this)
- search.list: 100 units (avoid)
- Current usage: ~5 units per channel scanned

## Output
Reports saved to: `output/report_YYYY-MM-DD_HH-MM-SS.txt`

## Scheduled Runs (future)
```bash
# Add to crontab for daily 9am scan:
0 9 * * * cd /path/to/youtube-scanner && source venv/bin/activate && python main.py
```
