"""Title pattern detection and theme classification"""

import re


def is_event_recap(title: str, channel_category: str = "") -> bool:
    """
    Detect if video is an event recap (match highlights, game recaps).

    These are excluded from trend analysis because they don't provide
    packaging insights - they're just popular because the event was popular.

    Returns True if this is likely an event recap.
    """
    title_lower = title.lower()

    # Strong signals: explicit recap keywords + vs pattern
    recap_keywords = [
        "highlights", "extended highlights", "all goals", "match recap",
        "full match", "game recap", "post-game", "postgame", "final score",
        "full highlights", "match highlights", "goals and highlights"
    ]

    has_recap_keyword = any(kw in title_lower for kw in recap_keywords)

    # Check for "Team vs Team" pattern with score like "(2-1)" or "2-1"
    has_score = bool(re.search(r'\(\d+-\d+\)|\b\d+-\d+\b', title_lower))

    # Check for vs pattern
    has_vs = bool(re.search(r'\bvs\.?\b|versus|\bv\b', title_lower))

    # Channel is in highlights category
    is_highlights_channel = channel_category.lower() in ["highlights", "sports highlights"]

    # Decision logic:
    # 1. Has recap keyword + vs = definitely recap
    if has_recap_keyword and has_vs:
        return True

    # 2. Has score in title = likely recap
    if has_score and has_vs:
        return True

    # 3. Highlights channel + vs = likely recap
    if is_highlights_channel and has_vs:
        return True

    # 4. Just "highlights" alone with sports themes
    sports_terms = ["match", "game", "cup", "league", "championship", "final", "semifinal"]
    if has_recap_keyword and any(term in title_lower for term in sports_terms):
        return True

    return False


def is_live_stream(title: str) -> bool:
    """
    Detect if video is a live stream or watch party.

    Live streams ride the event in real-time and don't provide
    replicable packaging insights.

    Returns True if this is likely a live stream.
    """
    title_lower = title.lower()

    live_keywords = [
        "live stream", "livestream", "live reaction",
        "watch party", "watch along", "play by play",
        "live commentary", "live now", "streaming live",
        "live watch", "going live"
    ]

    return any(kw in title_lower for kw in live_keywords)


def is_political_news(title: str, channel_category: str = "") -> bool:
    """
    Detect if video is political news/commentary about non-creator figures.

    Political news rides news cycles and doesn't provide replicable
    content strategy insights for sports/entertainment creators.

    Returns True if this is likely political news noise.
    """
    title_lower = title.lower()

    # Political figures and news topics (not athletes/creators)
    political_figures = [
        "trump", "biden", "obama", "epstein", "bondi",
        "congress", "senator", "governor", "president",
        "democrat", "republican", "leftist", "conservative",
        "maga", "woke"
    ]

    # Political drama keywords
    drama_keywords = [
        "meltdown", "destroyed", "exposed", "scandal",
        "loses mind", "lost her mind", "lost his mind",
        "goes crazy", "freaks out", "backfire"
    ]

    has_political_figure = any(fig in title_lower for fig in political_figures)
    has_drama_keyword = any(kw in title_lower for kw in drama_keywords)

    # Culture channels with political figures = likely political news
    is_culture_channel = channel_category.lower() in ["culture", "news", "politics"]

    # If it mentions political figures + drama keywords = political news
    if has_political_figure and has_drama_keyword:
        return True

    # Culture channel + political figure = likely political news
    if is_culture_channel and has_political_figure:
        return True

    return False


def analyze_title(title: str) -> list[str]:
    """
    Extract patterns from video title.

    Returns list of detected patterns.
    """
    patterns = []
    title_lower = title.lower()

    # First person action: "I tried...", "I spent...", "I went..."
    if re.search(r"\bi\s+(tried|spent|went|made|built|bought|got|did|ate|lived)", title_lower):
        patterns.append("first_person_action")

    # Expose/truth: "The REAL reason...", "...exposed", "The truth about..."
    if re.search(r"(the\s+real\s+reason|exposed|the\s+truth\s+about|what\s+they\s+don'?t|secret|revealed)", title_lower):
        patterns.append("expose_truth")

    # Challenge/bet: "challenge", "$1000", "bet"
    if re.search(r"(challenge|\$\d+|bet\b|wager|competition)", title_lower):
        patterns.append("challenge_bet")

    # Listicle: "Top 5...", "10 best...", "worst"
    if re.search(r"(top\s+\d+|\d+\s+best|\d+\s+worst|ranking|tier\s+list)", title_lower):
        patterns.append("listicle")

    # Versus: "vs", "versus", "1v1"
    if re.search(r"(\bvs\.?\b|versus|\d+v\d+|\bv\b)", title_lower):
        patterns.append("versus")

    # Reaction: "reacts", "reaction", "responding to"
    if re.search(r"(reacts?|reaction|responding\s+to|watching|reacting)", title_lower):
        patterns.append("reaction")

    # Vlog/BTS: "day in the life", "behind the scenes", "vlog"
    if re.search(r"(day\s+in\s+(the\s+)?life|behind\s+the\s+scenes|vlog|bts|24\s+hours)", title_lower):
        patterns.append("vlog_bts")

    # Interview: "interview", "sat down with", "talked to"
    if re.search(r"(interview|sat\s+down\s+with|talked\s+to|speaks\s+on|opens\s+up)", title_lower):
        patterns.append("interview")

    # Highlights: "highlights", "best plays", "mixtape"
    if re.search(r"(highlights?|best\s+plays|mixtape|compilation|moments)", title_lower):
        patterns.append("highlights")

    # Question: ends with "?"
    if title.strip().endswith("?"):
        patterns.append("question")

    # Number start: starts with a number
    if re.match(r"^\d+", title.strip()):
        patterns.append("number_start")

    # All caps: has 2+ ALL CAPS words (at least 2 letters each)
    caps_words = re.findall(r"\b[A-Z]{2,}\b", title)
    if len(caps_words) >= 2:
        patterns.append("all_caps")

    # Emoji: contains emoji
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags
        "\U00002702-\U000027B0"  # dingbats
        "\U000024C2-\U0001F251"
        "]+",
        flags=re.UNICODE
    )
    if emoji_pattern.search(title):
        patterns.append("emoji")

    return patterns


def classify_themes(title: str, description: str, tags: list[str]) -> list[str]:
    """
    Classify video into theme categories.

    Search for keywords in title + description + tags.
    Return all matching themes.
    """
    themes = []

    # Combine all text for searching
    text = f"{title} {description} {' '.join(tags)}".lower()

    # Theme keyword mappings
    theme_keywords = {
        "basketball": [
            "basketball", "nba", "hoops", "dunk", "three pointer", "layup",
            "basketball court", "lebron", "curry", "lakers", "celtics",
            "wnba", "march madness", "ncaa basketball", "hoop"
        ],
        "football": [
            "football", "nfl", "touchdown", "quarterback", "super bowl",
            "gridiron", "end zone", "receiver", "running back", "chiefs",
            "cowboys", "college football"
        ],
        "soccer": [
            "soccer", "goal", "messi", "ronaldo", "premier league",
            "world cup", "champions league", "futbol", "mls", "la liga",
            "bundesliga", "serie a", "striker", "keeper", "penalty kick"
        ],
        "training": [
            "workout", "training", "exercise", "gym", "fitness", "drill",
            "practice", "conditioning", "strength", "lifting"
        ],
        "lifestyle": [
            "lifestyle", "day in the life", "routine", "vlog", "house tour",
            "car collection", "shopping", "travel"
        ],
        "competition": [
            "competition", "challenge", "tournament", "battle", "vs",
            "versus", "1v1", "contest", "showdown", "face off"
        ],
        "reaction": [
            "reaction", "reacts", "watching", "responding", "reacting"
        ],
        "interview": [
            "interview", "podcast", "conversation", "talks", "speaks",
            "sits down", "exclusive", "q&a"
        ],
        "highlights": [
            "highlights", "best plays", "top plays", "mixtape", "compilation",
            "best moments", "career highlights"
        ],
        "drama": [
            "drama", "beef", "fight", "controversy", "exposed", "truth",
            "fired", "arrested", "scandal", "feud"
        ],
        "money": [
            "money", "million", "billion", "$", "expensive", "luxury",
            "rich", "salary", "contract", "net worth", "paid"
        ],
        "celebrity": [
            "celebrity", "famous", "star", "drake", "travis scott", "kanye",
            "kardashian", "influencer", "viral"
        ],
        "athlete": [
            "athlete", "pro athlete", "professional athlete", "player",
            "draft", "rookie", "mvp", "all-star", "pro career", "signed",
            "team", "season", "playoffs", "championship"
        ]
    }

    for theme, keywords in theme_keywords.items():
        for keyword in keywords:
            if keyword in text:
                themes.append(theme)
                break  # Only add each theme once

    return themes


def get_pattern_summary(outperformers: list) -> dict:
    """
    Aggregate pattern and theme counts across all outperformers.

    Returns:
        {
            "patterns": {"pattern_name": count, ...},
            "themes": {"theme_name": count, ...}
        }
    """
    pattern_counts = {}
    theme_counts = {}

    for op in outperformers:
        for pattern in op.title_patterns:
            pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
        for theme in op.themes:
            theme_counts[theme] = theme_counts.get(theme, 0) + 1

    # Sort by count descending
    pattern_counts = dict(sorted(
        pattern_counts.items(),
        key=lambda x: x[1],
        reverse=True
    ))
    theme_counts = dict(sorted(
        theme_counts.items(),
        key=lambda x: x[1],
        reverse=True
    ))

    return {
        "patterns": pattern_counts,
        "themes": theme_counts
    }
