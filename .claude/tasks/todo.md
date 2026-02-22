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

## Backlog (Future Features)

- Thumbnail analysis (Claude vision on top performer thumbnails)
- Competitor alerts (immediate notification when specific channels break out)
- Slack/Discord integration (real-time alerts vs email batches)
- Dashboard UI (web interface to browse history)
- Decay curve modeling
- Predictive signals
