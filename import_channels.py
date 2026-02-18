"""
Import channels from CSV files into channels.json
Run: python import_channels.py
"""

import csv
import json
import re
from pathlib import Path

# Map AI-assigned categories to our simplified categories
CATEGORY_MAP = {
    "basketball": "basketball",
    "football": "football",
    "soccer": "soccer",
    "combat sports": "combat",
    "mma": "combat",
    "boxing": "combat",
    "sports highlights": "highlights",
    "sports news": "media",
    "sports commentary": "media",
    "gaming": "gaming",
    "comedy": "culture",
    "pranks": "culture",
    "challenges": "culture",
    "entertainment": "culture",
    "music": "music",
    "hip hop": "music",
    "rap": "music",
    "fitness": "fitness",
    "lifestyle": "lifestyle",
    "vlogs": "lifestyle",
}

def extract_category(ai_categories: str) -> str:
    """Extract simplified category from AI-assigned categories string"""
    if not ai_categories:
        return "other"

    ai_lower = ai_categories.lower()

    # Check for sports first (most relevant for this scanner)
    if "basketball" in ai_lower:
        return "basketball"
    if "football" in ai_lower and "soccer" not in ai_lower:
        return "football"
    if "soccer" in ai_lower or "football" in ai_lower:
        return "soccer"
    if "combat" in ai_lower or "mma" in ai_lower or "boxing" in ai_lower or "wrestling" in ai_lower:
        return "combat"
    if "sports highlight" in ai_lower:
        return "highlights"
    if "sports news" in ai_lower or "sports commentary" in ai_lower:
        return "media"

    # Then other categories
    if "gaming" in ai_lower:
        return "gaming"
    if "comedy" in ai_lower or "prank" in ai_lower or "challenge" in ai_lower:
        return "culture"
    if "music" in ai_lower or "hip hop" in ai_lower or "rap" in ai_lower:
        return "music"
    if "fitness" in ai_lower or "workout" in ai_lower:
        return "fitness"
    if "vlog" in ai_lower or "lifestyle" in ai_lower:
        return "lifestyle"

    return "other"


def parse_csv(filepath: str) -> dict:
    """Parse CSV and return dict of channel_id -> channel_info"""
    channels = {}

    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            channel_id = row.get('Channel ID', '').strip()
            if not channel_id or not channel_id.startswith('UC'):
                continue

            name = row.get('Name', '').strip()
            if not name:
                continue

            # Get subscriber count for filtering
            subs_str = row.get('Subscribers', '0').strip()
            try:
                subs = int(subs_str) if subs_str else 0
            except ValueError:
                subs = 0

            ai_categories = row.get('Categories & niches (AI assigned)', '')
            category = extract_category(ai_categories)

            channels[channel_id] = {
                "id": channel_id,
                "name": name,
                "category": category,
                "subscribers": subs
            }

    return channels


def main():
    csv_dir = Path(__file__).parent.parent

    csv_files = [
        csv_dir / "36ce4587-e824-4788-869f-867783333313.csv",
        csv_dir / "816762ec-52aa-44ac-8c6c-3b0987b2e758.csv"
    ]

    all_channels = {}

    for csv_file in csv_files:
        if csv_file.exists():
            print(f"Processing {csv_file.name}...")
            channels = parse_csv(str(csv_file))
            print(f"  Found {len(channels)} channels")
            all_channels.update(channels)
        else:
            print(f"  File not found: {csv_file}")

    print(f"\nTotal unique channels: {len(all_channels)}")

    # Filter to channels with reasonable subscriber counts (10K - 50M)
    # This removes tiny channels and potential bot accounts
    filtered = {
        cid: ch for cid, ch in all_channels.items()
        if 10000 <= ch['subscribers'] <= 50000000
    }
    print(f"After filtering (10K-50M subs): {len(filtered)}")

    # Show category breakdown
    categories = {}
    for ch in filtered.values():
        cat = ch['category']
        categories[cat] = categories.get(cat, 0) + 1

    print("\nCategory breakdown:")
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")

    # Convert to list format for channels.json (without subscribers field)
    channel_list = [
        {"id": ch["id"], "name": ch["name"], "category": ch["category"]}
        for ch in filtered.values()
    ]

    # Save to channels_full.json
    output_file = Path(__file__).parent / "channels_full.json"
    with open(output_file, 'w') as f:
        json.dump({"channels": channel_list}, f, indent=2)

    print(f"\nSaved {len(channel_list)} channels to channels_full.json")
    print("To use: cp channels_full.json channels.json")


if __name__ == "__main__":
    main()
