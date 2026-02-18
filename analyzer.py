"""Title pattern detection and theme classification"""

import re


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
            "soccer", "football", "goal", "messi", "ronaldo", "premier league",
            "world cup", "champions league", "futbol", "mls"
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
