# Data Flow

## Main Scan Flow
```mermaid
sequenceDiagram
    participant M as main.py
    participant YT as YouTubeClient
    participant API as YouTube API
    participant S as Scanner
    participant A as Analyzer
    participant C as Claude API

    M->>M: Load channels.json
    M->>YT: fetch_subscriber_counts()
    YT->>API: channels.list (forHandle)
    API-->>YT: subscriber counts

    loop Each Channel
        M->>YT: get_recent_videos()
        YT->>API: playlistItems.list (1 quota unit)
        API-->>YT: video IDs
        YT->>API: videos.list (stats)
        API-->>YT: views, likes, comments
    end

    M->>S: find_outperformers()
    S->>S: Filter by age (48-168h)
    S->>S: Filter by views (>10k)
    S->>S: Calculate ratio (views/subs)
    S->>S: Calculate velocity (ratio/days)
    S->>S: Classify (trend_jacker/authority/standard)
    S->>A: analyze_title(), classify_themes()
    A-->>S: patterns, themes
    S-->>M: List[Outperformer]

    M->>C: generate_ideas(outperformers)
    C-->>M: content ideas
    M->>M: print_report(), save_report()
```

## Velocity Score Formula
```
velocity_score = (views / subscribers) / days_since_posted
```

## Classification Logic
```mermaid
flowchart TD
    A[Outperformer] --> B{age <= 72h AND velocity >= 2.0?}
    B -->|Yes| C[Trend-Jacker]
    B -->|No| D{age >= 168h AND velocity >= 0.5?}
    D -->|Yes| E[Authority Builder]
    D -->|No| F[Standard]
```

## Key Data Structures
```python
@dataclass
class Outperformer:
    video: Video
    channel: Channel
    ratio: float           # views / subscribers
    velocity_score: float  # ratio / days
    age_hours: float
    classification: str    # trend_jacker | authority_builder | standard
    title_patterns: list
    themes: list
```
