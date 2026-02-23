"""Basic unit tests for utility functions"""

import pytest
from youtube_client import parse_duration
from analyzer import (
    analyze_title, classify_themes,
    is_event_recap, is_live_stream, is_political_news
)


class TestParseDuration:
    """Tests for ISO 8601 duration parsing"""

    def test_standard_format(self):
        assert parse_duration("PT1H2M3S") == 3723

    def test_hours_only(self):
        assert parse_duration("PT2H") == 7200

    def test_minutes_only(self):
        assert parse_duration("PT30M") == 1800

    def test_seconds_only(self):
        assert parse_duration("PT45S") == 45

    def test_zero_seconds(self):
        assert parse_duration("PT0S") == 0

    def test_with_days(self):
        assert parse_duration("P1DT12H") == 129600  # 36 hours

    def test_empty_string(self):
        assert parse_duration("") == 0

    def test_none(self):
        assert parse_duration(None) == 0

    def test_invalid_format(self):
        assert parse_duration("invalid") == 0


class TestAnalyzeTitle:
    """Tests for title pattern detection"""

    def test_first_person_action(self):
        patterns = analyze_title("I tried eating only pizza for 30 days")
        assert "first_person_action" in patterns

    def test_challenge(self):
        patterns = analyze_title("$1000 Challenge with my friends")
        assert "challenge_bet" in patterns

    def test_versus(self):
        patterns = analyze_title("iPhone vs Android - Which is better?")
        assert "versus" in patterns

    def test_question(self):
        patterns = analyze_title("Why is this happening?")
        assert "question" in patterns

    def test_listicle(self):
        patterns = analyze_title("Top 10 best plays of the week")
        assert "listicle" in patterns

    def test_expose(self):
        patterns = analyze_title("The REAL reason why he quit")
        assert "expose_truth" in patterns

    def test_no_patterns(self):
        patterns = analyze_title("Hello World")
        assert patterns == []


class TestClassifyThemes:
    """Tests for theme classification"""

    def test_basketball(self):
        themes = classify_themes("NBA highlights", "Best dunks from last night", ["basketball"])
        assert "basketball" in themes

    def test_football_not_soccer(self):
        themes = classify_themes("NFL touchdown compilation", "Super Bowl plays", ["football"])
        assert "football" in themes
        assert "soccer" not in themes

    def test_soccer_not_football(self):
        themes = classify_themes("Messi amazing goal", "Premier League highlights", ["soccer"])
        assert "soccer" in themes
        # football should NOT be in themes anymore after our fix
        assert "football" not in themes

    def test_athlete(self):
        themes = classify_themes("Rookie MVP draft picks", "Pro athlete training", ["athlete"])
        assert "athlete" in themes

    def test_money(self):
        themes = classify_themes("How much money do NBA players make?", "Salary breakdown", [])
        assert "money" in themes

    def test_no_themes(self):
        themes = classify_themes("Random video", "Just a test", [])
        assert themes == []


class TestIsEventRecap:
    """Tests for event recap detection"""

    def test_highlights_with_vs(self):
        # Classic match highlights pattern
        assert is_event_recap("Manchester United vs Liverpool | Highlights") is True

    def test_extended_highlights(self):
        assert is_event_recap("Real Madrid vs Barcelona | Extended Highlights") is True

    def test_all_goals(self):
        assert is_event_recap("Arsenal vs Chelsea | All Goals (3-2)") is True

    def test_score_in_title(self):
        assert is_event_recap("Lakers vs Warriors (112-108) Final") is True

    def test_match_recap(self):
        assert is_event_recap("Match Recap: PSG vs Bayern") is True

    def test_game_highlights_with_sports_term(self):
        assert is_event_recap("NBA Finals Game 7 Highlights") is True

    def test_highlights_channel_with_vs(self):
        # Highlights channel + vs pattern
        assert is_event_recap("Team A vs Team B", channel_category="highlights") is True

    def test_commentary_not_recap(self):
        # Commentary about a match is NOT a recap
        assert is_event_recap("Why This Match Changed Everything") is False

    def test_reaction_not_recap(self):
        # Reaction video is NOT a recap
        assert is_event_recap("My Reaction to the Championship") is False

    def test_analysis_not_recap(self):
        # Analysis video is NOT a recap
        assert is_event_recap("Breaking Down LeBron's Perfect Game") is False

    def test_vs_without_highlights(self):
        # Just "vs" without recap keywords is NOT a recap (could be commentary)
        assert is_event_recap("Lakers vs Warriors - Who's Really Better?") is False

    def test_no_patterns(self):
        # Random title
        assert is_event_recap("How I Became a Pro Gamer") is False


class TestIsLiveStream:
    """Tests for live stream detection"""

    def test_live_stream_keyword(self):
        assert is_live_stream("USA vs Canada LIVE Stream Reaction") is True

    def test_watch_party(self):
        assert is_live_stream("Super Bowl Watch Party with Friends") is True

    def test_play_by_play(self):
        assert is_live_stream("NBA Finals Play by Play Commentary") is True

    def test_livestream_one_word(self):
        assert is_live_stream("Livestream: Championship Game Tonight") is True

    def test_live_reaction(self):
        assert is_live_stream("LIVE Reaction to the Draft Picks") is True

    def test_regular_reaction_not_live(self):
        # Regular reaction video (not live) should NOT be flagged
        assert is_live_stream("My Reaction to the Championship") is False

    def test_analysis_not_live(self):
        assert is_live_stream("Breaking Down the Game") is False

    def test_no_live_keywords(self):
        assert is_live_stream("Top 10 Best Plays of the Week") is False


class TestIsPoliticalNews:
    """Tests for political news detection"""

    def test_epstein_on_culture_channel(self):
        # Tim Dillon Show Clips is categorized as "culture"
        assert is_political_news("Why The Elites Are Quiet About Epstein", channel_category="culture") is True

    def test_political_figure_meltdown(self):
        assert is_political_news("Winter Olympics Leftist Has HILARIOUS MELTDOWN") is True

    def test_trump_scandal(self):
        assert is_political_news("Trump EXPOSED in New Scandal") is True

    def test_culture_channel_with_political(self):
        assert is_political_news("Pam Bondi Has Lost Her Mind", channel_category="culture") is True

    def test_sports_analysis_not_political(self):
        # Sports analysis should NOT be flagged
        assert is_political_news("Why Hockey Outperforms Every Winter Sport") is False

    def test_creator_drama_not_political(self):
        # Creator drama is NOT political news
        assert is_political_news("MrBeast vs PewDiePie Drama Explained") is False

    def test_athlete_news_not_political(self):
        # Athlete news is NOT political
        assert is_political_news("LeBron James Exposed His Workout Routine") is False

    def test_no_political_keywords(self):
        assert is_political_news("I Designed Uppestcase Letters") is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
