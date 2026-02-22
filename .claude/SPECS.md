# SPECS.md — Source of Truth (Contracts + Decisions)

## A) Naming Conventions (LOCKED)

### Files
- Python modules: `snake_case.py` (e.g., `email_sender.py`, `youtube_client.py`)
- Config: `config.py` loads from `.env` via `python-dotenv`
- Data files: `channels.json`, `history.json`
- Test files: `test_*.py` prefix

### Variables & Functions
- Functions: `snake_case` (e.g., `find_outperformers`, `get_video_age_hours`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `MIN_RATIO`, `BATCH_SIZE`)
- Classes: `PascalCase` (e.g., `Video`, `Channel`, `Outperformer`)

### Classifications (string literals)
- `"trend_jacker"` — high velocity within 72h
- `"authority_builder"` — still strong at 7+ days
- `"standard"` — meets ratio but neither of above

RULE: Do not change this section unless you follow Change Control in CLAUDE.md.

---

## B) Data Shapes / Schemas (LOCKED)

### Channel (dataclass in scanner.py)
```python
@dataclass
class Channel:
    channel_id: str
    name: str
    subscribers: int
    category: str  # "competitor", "athlete", "culture", "emerging", "media", "gaming"
```

### Video (dataclass in scanner.py)
```python
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
```

### Outperformer (dataclass in scanner.py)
```python
@dataclass
class Outperformer:
    video: Video
    channel: Channel
    ratio: float                    # views / subscribers
    velocity_score: float           # ratio / days_since_posted
    age_hours: float
    classification: str             # "trend_jacker", "authority_builder", "standard"
    title_patterns: list = []
    themes: list = []
```

### History Entry (dict in history.json)
```python
{
    'video_id': str,
    'title': str,
    'description': str,           # truncated to 500 chars
    'channel_name': str,
    'channel_category': str,
    'views': int,
    'subscribers': int,
    'ratio': float,
    'velocity_score': float,
    'age_hours': float,
    'classification': str,
    'patterns': list[str],
    'themes': list[str],
    'tags': list[str],            # max 20
    'scanned_at': str,            # ISO format datetime
    'url': str,
    'deep_analysis': dict | None  # added by deep_analyzer.py
}
```

### channels.json structure
```python
{
    "channels": [
        {"id": str, "name": str, "category": str},
        ...
    ]
}
```

RULE: Any schema change requires before/after + impact + verification command + tests.

---

## C) Invariants (LOCKED)

1. **Shorts Exclusion**: Videos < 180 seconds are ALWAYS excluded (Shorts can be up to 3 min)
2. **Ratio Threshold**: Sports channels use 0.75x, all others use 1.0x
3. **Time Window**: Only videos 48-168 hours old are considered
4. **Deduplication**: history.json dedupes by video_id
5. **Velocity Formula**: `velocity_score = ratio / (age_hours / 24)`
6. **API Quota**: BATCH_SIZE=3000 fits in 10k daily quota
7. **Sports Categories**: `{"athlete", "sports", "basketball", "football", "soccer", "training"}`

RULE: Treat invariants like law.

---

## D) Decisions Log (editable)

- [2026-01-30]: Claude OS installed. Architecture locked to current state.
- [2026-01-30]: Repo initialized with git, commit made, remote set to github.com/tfadp/youtube-scanner
- [Prior]: Category-based ratio thresholds added (0.75 for sports, 1.0 for others)
- [Prior]: Deep analysis module added for Claude-powered strategic insights
- [Prior]: Mobile-optimized HTML emails implemented
- [Prior]: Shorts filtering expanded to 3-layer detection (title hashtags, tags, duration >= 180s)
