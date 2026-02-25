# lessons.md — What We Learned

## 2026-01-30: Code Review #1

**Lesson: When you add a category in one place, grep for all places it should exist.**

The `SPORTS_CATEGORIES` set in `config.py` includes `"athlete"`, but `analyzer.py` has no `"athlete"` theme in its keyword mappings. This means:
- Channels tagged as "athlete" correctly get the 0.75x ratio threshold
- But their videos get NO theme classification because there's no "athlete" keyword list

**Root cause**: The sports ratio feature was added to `config.py` + `scanner.py` without checking if `analyzer.py` needed updates too.

**Prevention**: Before adding a new category/classification:
1. Grep for existing category lists: `grep -r "category" *.py`
2. Check if it needs to propagate to other modules
3. Add to `.claude/SPECS.md` under Invariants if it's a new contract

---

## 2026-02-18: Feature Planning

**Lesson: "Useful" means analysis depth, not delivery speed.**

When brainstorming features, I initially focused on notifications (Slack, competitor alerts, real-time delivery). The user correctly pushed back: those are *communication* features, not *analysis* features.

What actually matters:
- Pattern effectiveness OVER TIME (not just counts)
- Correlation analysis (which combos actually predict success?)
- Cohort analysis (does it work for 100K channels vs 10M?)
- Trend direction (rising vs falling patterns)

**Prevention**: When planning features, ask: "Does this help me LEARN something new, or just KNOW something faster?"

---

## 2026-02-22: Event Recap Filter

**Lesson: Not all outperformers provide insights.**

When reviewing top-performing videos, we discovered that match highlights/recaps (e.g., "Man United vs Liverpool | Highlights") always outperform because the *event* was popular, not the packaging. They don't teach us anything about content strategy.

**Solution**: Added `is_event_recap()` function that detects:
- Titles with "highlights", "recap", "all goals" + "vs" pattern
- Titles with score patterns like "(2-1)" + "vs" pattern
- Highlights channels posting match content
- Sports terms + recap keywords

These are now flagged with `is_event_recap=True` and filtered from email reports (shown as "X recaps filtered").

**Prevention**: When analyzing performance data, always ask: "Is this success replicable, or just riding an external event?"

---

## 2026-02-23: Expanded Noise Filters

**Lesson: Event recaps aren't the only noise.**

After reviewing another week of outperformers, we identified two more categories that don't provide actionable insights:

1. **Live streams/watch parties** - "USA vs Canada LIVE Stream Reaction" rides the event in real-time
2. **Political news** - "Why The Elites Are Quiet About Epstein" rides news cycles, not content strategy

**Solution**: Added `is_live_stream()` and `is_political_news()` functions. Renamed `is_event_recap` field to `is_noise` with a `noise_type` field for debugging.

**Detection patterns**:
- Live streams: "live stream", "watch party", "play by play"
- Political: political figures + drama keywords, OR culture channels + political figures

**Prevention**: When filtering data, regularly review what's getting through and ask: "Would I actually learn something actionable from this?"

---

## 2026-02-24: AI Video Summaries

**Lesson: Check what the API already returns before adding new calls.**

When adding YouTuber background context, we discovered the YouTube API's `get_channel_info()` call already requested `part="snippet,statistics"` — and `snippet` includes the channel description ("about" text). We were paying the quota cost and throwing away the data. One-line fix to extract it, zero additional API cost.

**Lesson: Batch AI calls for cost efficiency.**

Instead of calling Claude once per video (20-100 calls), we batch all videos into a single prompt with numbered `[1] ... [2] ...` format. Cost: ~$0.004 per batch with Haiku vs ~$0.40-2.00 if called individually with Sonnet.

**Prevention**: Before adding a new API call, always check: "Is this data already being fetched somewhere and just not used?"

---

## 2026-02-25: Deployment Gap & Transient API Errors

**Lesson: SCP failures are silent killers.**

We built and tested the AI summary feature locally, committed and pushed to GitHub, but the SCP deploy to the server failed with "Permission denied". The next day's email had no summaries — the server was still running old code. We didn't catch this until the user reported it.

**Lesson: Transient API errors need retry logic.**

The Anthropic API returned a 500 Internal Server Error during summary generation. Our `try/except` caught it gracefully (email still sent, just without summaries), but we should add retry with exponential backoff — same pattern already used in `youtube_client.py`.

**Prevention**:
1. After any deploy attempt, always verify: "Did the files actually land?" Check with `ssh ... ls -la` or similar
2. Any external API call should have retry logic for transient 5xx errors
3. The `video_summarizer.py` needs the same `retry_on_error` pattern as `youtube_client.py`
