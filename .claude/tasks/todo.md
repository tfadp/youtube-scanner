# todo.md — Roadmap

## Next 3 Steps (from Code Review)

1) ~~**Fix .env.example**~~ ✅ — Added EMAIL_ENABLED, EMAIL_TO, RESEND_API_KEY, EMAIL_FROM with setup instructions.

2) ~~**Fix football/soccer keyword overlap**~~ ✅ — Removed "football" from soccer theme, added more soccer-specific keywords.

3) ~~**Add "athlete" theme to analyzer.py**~~ ✅ — Added athlete theme with keywords: athlete, player, draft, rookie, mvp, playoffs, etc.

## Code Review Findings (to address later)

### HIGH
- [x] No backup/recovery for history.json
- [x] .env.example missing email vars
- [x] Football/soccer keyword conflict
- [x] SPORTS_CATEGORIES vs theme mismatch

### MEDIUM
- [x] No retry logic on YouTube API failures
- [x] No validation on channels.json entries
- [x] API key could leak in error messages

### LOW
- [x] Hardcoded file paths (history.json, batch_state.json)
- [x] No automated tests
- [x] Duration regex edge cases

## NEXT: Two-Agent Architecture (see ARCHITECTURE.md)

### Agent A: Infrastructure
- [ ] SQLite migration (replace history.json)
- [ ] Query layer for analysis
- [ ] Daily rollup jobs
- [ ] Monitoring/health checks

### Agent B: Analysis
- [ ] Pattern trends over time (rising/falling)
- [ ] Pattern+theme correlation matrix
- [ ] Channel cohort analysis (by subscriber tier)
- [ ] Emerging topic detection
- [ ] Weekly digest with trend comparisons

## Active Tasks

(none)

## Completed (2026-02-27)

- [x] Fixed deploy path mismatch: files were SCP'd to `/root/youtube-scanner/` but cron runs from `/opt/youtube-scanner/`
- [x] Verified server has: video_summarizer.py, noise filters, retry logic, anthropic package

## Completed (2026-02-25)

- [x] Add retry logic to `video_summarizer.py` for Anthropic API 500 errors
- [x] Deploy all uncommitted changes to server (mid-performer fallback, not-relevant filter, retry logic)

- [x] Deployed AI summary files to server via SCP
- [x] Mid-performer fallback — sports videos 0.5x-0.75x shown when no outperformers found
- [x] `is_not_relevant()` filter — non-sports videos without transferable patterns/themes marked as noise
- [x] `MIN_RATIO_MID = 0.5` added to config.py

## Completed (2026-02-24)

- [x] Deleted SOUL.md, migrated to lean three-layer CLAUDE.md system
- [x] AI video summaries — Claude Haiku generates 1-3 sentence summaries per outperformer
- [x] Channel "about" extraction — captures YouTuber context from existing API call (zero extra quota)
- [x] Summaries shown in email (HTML + plain text), console, and saved reports
- [x] Summaries stored in history.json for future analysis
- [x] New module: `video_summarizer.py`

## Backlog (Future Features)

- Thumbnail analysis (Claude vision on top performer thumbnails)
- Competitor alerts (immediate notification when specific channels break out)
- Slack/Discord integration (real-time alerts vs email batches)
- Dashboard UI (web interface to browse history)
- Decay curve modeling
- Predictive signals
