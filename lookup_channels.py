"""
Utility script to look up YouTube channel IDs by handle using forHandle (1 unit each).
Run: python lookup_channels.py
"""

import json
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from config import YOUTUBE_API_KEY

# Handles to look up (with @ symbol)
CHANNELS = [
    ("@houseofhighlights", "competitor"),
    ("@NBA", "league"),
    ("@NFL", "league"),
    ("@BleacherReport", "competitor"),
    ("@espn", "competitor"),
    ("@Deestroying", "athlete"),
    ("@DudePerfect", "culture"),
    ("@Jesser", "basketball"),
    ("@MrBeast", "culture"),
    ("@UFC", "league"),
    ("@AMP", "culture"),
    ("@KaiCenat", "culture"),
    ("@IShowSpeed", "culture"),
    ("@uninterrupted", "competitor"),
    ("@Complex", "competitor"),
    ("@FlightReacts", "basketball"),
    ("@TristanJass", "basketball"),
    ("@RDCworld1", "culture"),
    ("@CashNasty", "basketball"),
    ("@KOT4Q", "basketball"),
    ("@RustyBuckets", "basketball"),
    ("@TheProfessor", "basketball"),
    ("@ballislife", "basketball"),
    ("@2HYPE", "basketball"),
    ("@GoldenHoops", "basketball"),
    ("@thepatmcafeeshow", "media"),
    ("@jaborickpod", "media"),
    ("@allthesmoke", "media"),
    ("@GilsArenaShow", "media"),
    ("@clubshayshay", "media"),
    ("@fazerug", "culture"),
    ("@nelkboys", "culture"),
    ("@DannyDuncan69", "culture"),
    ("@LoganPaul", "culture"),
    ("@jakepaul", "culture"),
    ("@redbull", "action"),
    ("@GoPro", "action"),
    ("@NitroCircus", "action"),
    ("@baaborslsports", "competitor"),
    ("@NFLFilms", "league"),
    ("@ESPNCFB", "football"),
    ("@TomGrossiComedy", "football"),
    ("@FreeDawkins", "basketball"),
    ("@F2Freestylers", "soccer"),
    ("@Sidemen", "culture"),
    ("@KSI", "culture"),
    ("@BetaSquad", "culture"),
    ("@W2S", "culture"),
    ("@JiDion", "culture"),
    ("@DukeDennis", "basketball"),
    ("@Fanum", "culture"),
    ("@Agent00", "basketball"),
    ("@SLAM", "competitor"),
    ("@overtime", "competitor"),
    ("@WhistleSports", "competitor"),
    ("@ringer", "media"),
    ("@brfootball", "soccer"),
    ("@MikeKorzemba", "basketball"),
    ("@ZackTTG", "basketball"),
    ("@CliveNBAParody", "basketball"),
    ("@AFunkyDiabetic", "basketball"),
    ("@AndyHoops", "basketball"),
    ("@JxmyHighroller", "basketball"),
    ("@ThinkingBasketball", "basketball"),
    ("@SportingLogically", "basketball"),
    ("@NBAonTNT", "media"),
    ("@SportsCenter", "media"),
    ("@KristopherLondon", "basketball"),
    ("@MMG", "basketball"),
    ("@LSK", "basketball"),
    ("@CboysTV", "football"),
    ("@SteveWillDoIt", "culture"),
    ("@MDMotivator", "culture"),
    ("@MoreSidemen", "culture"),
    ("@stephenasmith", "media"),
    ("@OldManAndTheThree", "media"),
    ("@UndisputedOnFS1", "media"),
    ("@FirstTake", "media"),
    ("@GetUpESPN", "media"),
    ("@PardonMyTake", "media"),
    ("@MarshawnLynch", "athlete"),
    ("@YesTheory", "culture"),
    ("@Unspeakable", "culture"),
    ("@PrestonPlayz", "culture"),
    ("@TBJZL", "culture"),
    ("@miniminter", "culture"),
]

def lookup_by_handle(youtube, handle: str) -> dict | None:
    """Look up a channel by its @handle using forHandle parameter (1 quota unit)"""
    # Remove @ if present
    clean_handle = handle.lstrip("@")

    try:
        response = youtube.channels().list(
            part="snippet,statistics",
            forHandle=clean_handle
        ).execute()

        if response.get("items"):
            channel = response["items"][0]
            return {
                "id": channel["id"],
                "name": channel["snippet"]["title"],
                "handle": handle,
                "subscribers": int(channel["statistics"].get("subscriberCount", 0))
            }
        return None
    except HttpError as e:
        print(f"API Error: {e}")
        return None
    except TypeError as e:
        print(f"Parameter Error: {e}")
        print("forHandle may not be supported. Try: pip install --upgrade google-api-python-client")
        return None

def main():
    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

    print("Looking up channel IDs by @handle (forHandle method)...")
    print("Cost: 1 quota unit per channel")
    print("=" * 60)

    results = []
    failed = []

    for i, (handle, category) in enumerate(CHANNELS, 1):
        print(f"[{i}/{len(CHANNELS)}] Looking up {handle}...", end=" ")

        result = lookup_by_handle(youtube, handle)

        if result:
            print(f"✓ {result['name']} ({result['id'][:15]}...) - {result['subscribers']:,} subs")
            result["category"] = category
            results.append(result)
        else:
            print("✗ Not found")
            failed.append(handle)

    print("\n" + "=" * 60)
    print(f"Found: {len(results)} | Failed: {len(failed)}")
    print(f"Quota used: ~{len(CHANNELS)} units (vs ~{len(CHANNELS) * 100} with search method)")

    if failed:
        print(f"\nFailed handles: {', '.join(failed)}")

    # Save to channels_verified.json
    channels_data = {
        "channels": [
            {
                "id": r["id"],
                "name": r["name"],
                "category": r["category"]
            }
            for r in results
        ]
    }

    with open("channels_verified.json", "w") as f:
        json.dump(channels_data, f, indent=2)

    print(f"\nSaved {len(results)} verified channels to channels_verified.json")
    print("To use: cp channels_verified.json channels.json")

if __name__ == "__main__":
    main()
