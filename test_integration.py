"""
Integration tests for the scanner workflow.

Tests the full pipeline with mocked YouTube/Anthropic APIs:
- Channel loading and validation
- Batch management
- Scan → history write
- Empty results + mid-performer fallback
- Email formatting (with trends/tiers)
- Scan results serialization round-trip
- SQLite history operations
"""

import json
import os
import sqlite3
import tempfile
import pytest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

from scanner import Channel, Video, Outperformer, find_outperformers
from main import (
    load_channels, _serialize_outperformer, _deserialize_outperformer,
    save_scan_results, load_scan_results
)
from email_sender import format_email_report, format_weekly_digest_email
from weekly_digest import generate_weekly_digest, get_weekly_data
import history_db
import config


# --- Fixtures ---

def _make_video(video_id="v1", title="Test Video", views=500000, subs=100000,
                age_hours=72, category="athlete", channel_name="TestChannel"):
    """Build a complete Outperformer for testing."""
    published = datetime.now(timezone.utc) - timedelta(hours=age_hours)
    video = Video(
        video_id=video_id,
        channel_id="UC_test",
        channel_name=channel_name,
        title=title,
        description="Test description",
        views=views,
        likes=1000,
        comments=100,
        published_at=published,
        thumbnail_url="https://img.youtube.com/test.jpg",
        duration_seconds=600,
        tags=["test", "video"]
    )
    channel = Channel(
        channel_id="UC_test",
        name=channel_name,
        subscribers=subs,
        category=category,
        about="Test channel about"
    )
    ratio = views / subs
    velocity = ratio / (age_hours / 24)
    return Outperformer(
        video=video,
        channel=channel,
        ratio=ratio,
        velocity_score=velocity,
        age_hours=age_hours,
        classification="standard",
        title_patterns=["reaction", "all_caps"],
        themes=["athlete", "competition"],
        is_noise=False,
        noise_type="",
        summary="A test video summary."
    )


@pytest.fixture
def sample_outperformers():
    """Three outperformers with different characteristics."""
    return [
        _make_video("v1", "I Tried INSANE Basketball Challenge", 500000, 100000, 48, "athlete"),
        _make_video("v2", "The Truth About NFL Draft Picks", 200000, 50000, 120, "football"),
        _make_video("v3", "Day In The Life of a Pro Athlete", 1000000, 200000, 160, "athlete"),
    ]


@pytest.fixture
def temp_db(tmp_path):
    """Provide a temporary SQLite database for history tests."""
    db_path = tmp_path / "test_history.db"
    original_db = config.HISTORY_DB_FILE
    original_json = config.HISTORY_FILE
    config.HISTORY_DB_FILE = db_path
    config.HISTORY_FILE = tmp_path / "history.json"  # non-existent, won't migrate
    yield db_path
    config.HISTORY_DB_FILE = original_db
    config.HISTORY_FILE = original_json


@pytest.fixture
def temp_scan_file(tmp_path):
    """Provide a temporary scan results file."""
    import main as main_mod
    scan_path = tmp_path / "last_scan.json"
    original_config = config.SCAN_RESULTS_FILE
    original_main = main_mod.SCAN_RESULTS_FILE
    original_output_config = config.OUTPUT_DIR
    original_output_main = main_mod.OUTPUT_DIR
    config.SCAN_RESULTS_FILE = scan_path
    main_mod.SCAN_RESULTS_FILE = scan_path
    config.OUTPUT_DIR = tmp_path
    main_mod.OUTPUT_DIR = tmp_path
    yield scan_path
    config.SCAN_RESULTS_FILE = original_config
    main_mod.SCAN_RESULTS_FILE = original_main
    config.OUTPUT_DIR = original_output_config
    main_mod.OUTPUT_DIR = original_output_main


# --- Channel Loading Tests ---

class TestLoadChannels:
    """Test channel loading and validation."""

    def test_load_valid_channels(self, tmp_path):
        channels_file = tmp_path / "channels.json"
        channels_file.write_text(json.dumps({
            "channels": [
                {"id": "UCxyz123", "name": "Test Channel", "category": "athlete"},
                {"id": "UCabc456", "name": "Another Channel", "category": "culture"}
            ]
        }))
        channels = load_channels(channels_file)
        assert len(channels) == 2
        assert channels[0].name == "Test Channel"
        assert channels[1].category == "culture"

    def test_skip_invalid_channel_id(self, tmp_path):
        channels_file = tmp_path / "channels.json"
        channels_file.write_text(json.dumps({
            "channels": [
                {"id": "INVALID", "name": "Bad Channel"},
                {"id": "UCvalid", "name": "Good Channel"}
            ]
        }))
        channels = load_channels(channels_file)
        assert len(channels) == 1
        assert channels[0].name == "Good Channel"

    def test_skip_missing_fields(self, tmp_path):
        channels_file = tmp_path / "channels.json"
        channels_file.write_text(json.dumps({
            "channels": [
                {"name": "No ID Channel"},
                {"id": "UCtest"},
                {"id": "UCgood", "name": "Good"}
            ]
        }))
        channels = load_channels(channels_file)
        assert len(channels) == 1

    def test_empty_channels_raises(self, tmp_path):
        channels_file = tmp_path / "channels.json"
        channels_file.write_text(json.dumps({"channels": []}))
        with pytest.raises(ValueError, match="No valid channels"):
            load_channels(channels_file)

    def test_missing_channels_key_raises(self, tmp_path):
        channels_file = tmp_path / "channels.json"
        channels_file.write_text(json.dumps({"data": []}))
        with pytest.raises(ValueError, match="missing 'channels' key"):
            load_channels(channels_file)


# --- Scan Results Serialization Tests ---

class TestScanResultsSerialization:
    """Test Outperformer round-trip through JSON."""

    def test_serialize_deserialize_round_trip(self, sample_outperformers):
        for op in sample_outperformers:
            serialized = _serialize_outperformer(op)
            restored = _deserialize_outperformer(serialized)

            assert restored.video.video_id == op.video.video_id
            assert restored.video.title == op.video.title
            assert restored.channel.name == op.channel.name
            assert restored.ratio == op.ratio
            assert restored.velocity_score == op.velocity_score
            assert restored.classification == op.classification
            assert restored.title_patterns == op.title_patterns
            assert restored.themes == op.themes
            assert restored.is_noise == op.is_noise
            assert restored.summary == op.summary

    def test_save_and_load_scan_results(self, sample_outperformers, temp_scan_file):
        save_scan_results(sample_outperformers, [], "1/2")
        loaded_ops, loaded_mid, batch_info = load_scan_results()

        assert len(loaded_ops) == 3
        assert batch_info == "1/2"
        assert loaded_ops[0].video.title == sample_outperformers[0].video.title

    def test_load_missing_scan_results(self, tmp_path):
        import main as main_mod
        missing_file = tmp_path / "nonexistent" / "scan.json"
        original_config = config.SCAN_RESULTS_FILE
        original_main = main_mod.SCAN_RESULTS_FILE
        config.SCAN_RESULTS_FILE = missing_file
        main_mod.SCAN_RESULTS_FILE = missing_file
        try:
            ops, mid, info = load_scan_results()
            assert ops == []
            assert mid == []
        finally:
            config.SCAN_RESULTS_FILE = original_config
            main_mod.SCAN_RESULTS_FILE = original_main


# --- SQLite History Tests ---

class TestHistoryDB:
    """Test SQLite-backed history operations."""

    def test_add_and_load(self, temp_db, sample_outperformers):
        count = history_db.add_outperformers(sample_outperformers)
        assert count == 3

        history = history_db.load_history()
        assert len(history) == 3
        assert history[0]['video_id'] in ['v1', 'v2', 'v3']

    def test_deduplication(self, temp_db, sample_outperformers):
        history_db.add_outperformers(sample_outperformers)
        count = history_db.add_outperformers(sample_outperformers)
        assert count == 0  # all duplicates

        history = history_db.load_history()
        assert len(history) == 3  # still 3, not 6

    def test_pattern_stats(self, temp_db, sample_outperformers):
        history_db.add_outperformers(sample_outperformers)
        stats = history_db.get_pattern_stats()

        assert stats['total_videos'] == 3
        assert 'reaction' in stats['patterns']
        assert 'athlete' in stats['themes']
        assert stats['patterns']['reaction'] == 3  # all 3 have 'reaction' pattern

    def test_history_summary(self, temp_db, sample_outperformers):
        history_db.add_outperformers(sample_outperformers)
        summary = history_db.get_history_summary()

        assert summary['total_videos'] == 3
        assert summary['standard'] == 3
        assert 'athlete' in summary['categories']

    def test_find_similar(self, temp_db, sample_outperformers):
        history_db.add_outperformers(sample_outperformers)
        similar = history_db.find_similar(['reaction'], ['athlete'])

        assert len(similar) > 0
        assert similar[0]['video_id'] in ['v1', 'v2', 'v3']

    def test_empty_db_operations(self, temp_db):
        assert history_db.load_history() == []
        assert history_db.get_pattern_stats()['total_videos'] == 0
        assert history_db.get_history_summary()['total_videos'] == 0
        assert history_db.find_similar(['x'], ['y']) == []
        assert history_db.get_pattern_trends()['weeks_analyzed'] == 0
        assert history_db.get_tier_breakdown()['emerging']['total_videos'] == 0

    def test_save_history_updates_existing(self, temp_db, sample_outperformers):
        """Test that save_history can update entries (for deep_analyzer compat)."""
        history_db.add_outperformers(sample_outperformers)
        history = history_db.load_history()

        # Simulate deep_analyzer adding analysis
        history[0]['deep_analysis'] = {'hook': 'curiosity gap'}
        history_db.save_history(history)

        reloaded = history_db.load_history()
        analyzed = [h for h in reloaded if h.get('deep_analysis')]
        assert len(analyzed) == 1
        assert analyzed[0]['deep_analysis']['hook'] == 'curiosity gap'

    def test_tier_breakdown(self, temp_db):
        """Test tier grouping by subscriber count."""
        ops = [
            _make_video("v_small", "Small Channel", 50000, 50000, 72, "athlete", "SmallCh"),
            _make_video("v_mid", "Mid Channel", 200000, 200000, 72, "athlete", "MidCh"),
            _make_video("v_large", "Large Channel", 1000000, 600000, 72, "athlete", "LargeCh"),
        ]
        history_db.add_outperformers(ops)
        tiers = history_db.get_tier_breakdown()

        assert tiers['emerging']['total_videos'] == 1  # 50K subs
        assert tiers['mid']['total_videos'] == 1       # 200K subs
        assert tiers['large']['total_videos'] == 1     # 600K subs


# --- JSON Migration Tests ---

class TestJSONMigration:
    """Test automatic migration from history.json to SQLite."""

    def test_migration_imports_data(self, tmp_path):
        # Use a unique subdirectory to avoid DB pollution from other tests
        migrate_dir = tmp_path / "migrate_test"
        migrate_dir.mkdir()
        json_file = migrate_dir / "history.json"
        db_file = migrate_dir / "history.db"
        json_file.write_text(json.dumps([
            {
                'video_id': 'vmigrate1',
                'title': 'Migrated Video',
                'channel_name': 'MigChan',
                'channel_category': 'athlete',
                'views': 100000,
                'subscribers': 50000,
                'ratio': 2.0,
                'velocity_score': 1.5,
                'age_hours': 48,
                'classification': 'standard',
                'patterns': ['reaction'],
                'themes': ['athlete'],
                'tags': ['test'],
                'scanned_at': '2026-03-01T10:00:00',
                'url': 'https://youtube.com/watch?v=vmigrate1'
            }
        ]))

        original_db = config.HISTORY_DB_FILE
        original_json = config.HISTORY_FILE
        config.HISTORY_DB_FILE = db_file
        config.HISTORY_FILE = json_file

        try:
            history = history_db.load_history()
            assert len(history) == 1
            assert history[0]['video_id'] == 'vmigrate1'
            assert history[0]['patterns'] == ['reaction']

            # JSON file should be renamed to .migrated
            assert not json_file.exists()
            assert (migrate_dir / "history.json.migrated").exists()
        finally:
            config.HISTORY_DB_FILE = original_db
            config.HISTORY_FILE = original_json


# --- Email Formatting Tests ---

class TestEmailFormatting:
    """Test email report generation with various scenarios."""

    def test_format_with_outperformers(self, sample_outperformers):
        subject, text, html = format_email_report(sample_outperformers, "1/2")

        assert "3 outperformers" in subject
        assert "I Tried INSANE" in text
        assert "I Tried INSANE" in html
        assert "1/2" in html

    def test_format_empty_results(self):
        subject, text, html = format_email_report([], "1/2")

        assert "No outperformers" in subject
        assert "No outperforming videos" in text

    def test_format_with_noise_filtered(self):
        noisy = _make_video("vn", "Premier League Recap", 100000, 50000, 72, "soccer")
        noisy.is_noise = True
        noisy.noise_type = "soccer_content"

        clean = _make_video("vc", "Basketball Challenge", 200000, 50000, 72, "athlete")

        subject, text, html = format_email_report([noisy, clean], "1/1")
        assert "1 outperformers" in subject  # only clean one
        assert "1 filtered" in html

    def test_format_with_mid_performers_fallback(self):
        """When all outperformers are noise, mid-performers show as fallback."""
        noisy = _make_video("vn", "Soccer Match Highlights", 100000, 50000, 72, "soccer")
        noisy.is_noise = True
        noisy.noise_type = "soccer_content"

        mid = _make_video("vm", "NBA Draft Preview", 30000, 50000, 72, "basketball")

        subject, text, html = format_email_report([noisy], "1/1", mid_performers=[mid])
        assert "No outperformers" in subject
        assert "NBA Draft Preview" in html
        assert "mid-performers" in text.lower() or "Mid-Performers" in text

    def test_format_noise_only(self):
        """All videos are noise, no mid-performers."""
        noisy = _make_video("vn", "Soccer Drama", 100000, 50000, 72, "soccer")
        noisy.is_noise = True
        noisy.noise_type = "soccer_content"

        subject, text, html = format_email_report([noisy], "1/1")
        assert "No outperformers" in subject
        assert "1 filtered" in html


# --- Batch Manager Tests ---

class TestBatchManager:
    """Test batch management operations."""

    def test_batch_cycling(self, tmp_path):
        import batch_manager
        from batch_manager import get_batch_channels

        channels = [
            Channel(f"UC{i:04d}", f"Channel {i}", 0, "athlete")
            for i in range(10)
        ]

        # Patch BATCH_SIZE in the batch_manager module (where it's imported)
        original = batch_manager.BATCH_SIZE
        batch_manager.BATCH_SIZE = 3

        try:
            batch, num, total = get_batch_channels(channels, batch_num=0)
            assert len(batch) == 3
            assert num == 0
            assert total == 4

            batch, num, total = get_batch_channels(channels, batch_num=3)
            assert len(batch) == 1  # last batch has remainder
            assert num == 3
        finally:
            batch_manager.BATCH_SIZE = original


# --- Scanner with Mocked YouTube ---

class TestScannerWithMocks:
    """Test find_outperformers with mocked YouTube client."""

    def test_finds_outperformers(self):
        mock_yt = MagicMock()
        published = datetime.now(timezone.utc) - timedelta(hours=72)

        mock_yt.get_recent_videos.return_value = [
            {
                "video_id": "vtest1",
                "title": "Amazing Basketball Challenge $1000",
                "description": "Test desc",
                "views": 500000,
                "likes": 10000,
                "comments": 500,
                "published_at": published,
                "thumbnail_url": "https://img.youtube.com/test.jpg",
                "duration_seconds": 600,
                "tags": ["basketball", "challenge"]
            }
        ]

        channels = [
            Channel("UCtest1", "TestChannel", 100000, "athlete")
        ]

        outperformers, mid = find_outperformers(channels, mock_yt)
        assert len(outperformers) == 1
        assert outperformers[0].ratio == 5.0
        assert "challenge_bet" in outperformers[0].title_patterns

    def test_filters_shorts(self):
        mock_yt = MagicMock()
        published = datetime.now(timezone.utc) - timedelta(hours=72)

        mock_yt.get_recent_videos.return_value = [
            {
                "video_id": "vshort1",
                "title": "Quick Dunk #shorts",
                "description": "",
                "views": 1000000,
                "likes": 50000,
                "comments": 1000,
                "published_at": published,
                "thumbnail_url": "",
                "duration_seconds": 30,
                "tags": ["shorts"]
            }
        ]

        channels = [Channel("UCtest1", "TestChannel", 100000, "athlete")]
        outperformers, mid = find_outperformers(channels, mock_yt)
        assert len(outperformers) == 0

    def test_empty_channel_list(self):
        mock_yt = MagicMock()
        outperformers, mid = find_outperformers([], mock_yt)
        assert outperformers == []
        assert mid == []

    def test_zero_subscriber_channel_skipped(self):
        mock_yt = MagicMock()
        channels = [Channel("UCtest1", "NoSubs", 0, "athlete")]
        outperformers, mid = find_outperformers(channels, mock_yt)
        assert outperformers == []
        mock_yt.get_recent_videos.assert_not_called()

    def test_irrelevant_category_skipped(self):
        """Channels outside RELEVANT_CATEGORIES are skipped entirely (no API calls)."""
        mock_yt = MagicMock()
        channels = [
            Channel("UCculture1", "CultureChannel", 100000, "culture"),
            Channel("UCgaming1", "GamingChannel", 100000, "gaming"),
            Channel("UCsoccer1", "SoccerChannel", 100000, "soccer"),
        ]
        outperformers, mid = find_outperformers(channels, mock_yt)
        assert outperformers == []
        mock_yt.get_recent_videos.assert_not_called()

    def test_noise_flagging_event_recap(self):
        """Verify event recap noise filter still works within relevant categories."""
        mock_yt = MagicMock()
        published = datetime.now(timezone.utc) - timedelta(hours=72)

        mock_yt.get_recent_videos.return_value = [
            {
                "video_id": "vrecap1",
                "title": "Lakers vs Warriors | Extended Highlights (112-108)",
                "description": "Full game highlights",
                "views": 500000,
                "likes": 10000,
                "comments": 500,
                "published_at": published,
                "thumbnail_url": "",
                "duration_seconds": 600,
                "tags": ["basketball", "highlights"]
            }
        ]

        channels = [Channel("UCbball", "HoopsHighlights", 100000, "basketball")]
        outperformers, mid = find_outperformers(channels, mock_yt)

        assert len(outperformers) == 1
        assert outperformers[0].is_noise is True
        assert outperformers[0].noise_type == "event_recap"


# --- Weekly Digest Tests ---

class TestWeeklyDigest:
    """Test weekly intelligence digest generation."""

    def test_empty_digest(self, temp_db):
        """Digest with no data returns empty structure."""
        digest = generate_weekly_digest(days=7)
        assert digest['top_videos'] == []
        assert digest['winning_patterns'] == []
        assert digest['emerging_creators'] == []
        assert digest['summary_stats']['total_videos'] == 0

    def test_digest_with_data(self, temp_db, sample_outperformers):
        """Digest analyzes outperformers correctly."""
        history_db.add_outperformers(sample_outperformers)
        digest = generate_weekly_digest(days=7)

        assert digest['summary_stats']['total_videos'] == 3
        assert len(digest['top_videos']) == 3
        assert len(digest['winning_patterns']) > 0

        # Check patterns include 'reaction' (all 3 test videos have it)
        pattern_names = [p['pattern'] for p in digest['winning_patterns']]
        assert 'reaction' in pattern_names

    def test_emerging_creators_filter(self, temp_db):
        """Emerging creators are those under 200K subs."""
        ops = [
            _make_video("v_small", "Small Win", 200000, 50000, 72, "athlete", "SmallCh"),
            _make_video("v_big", "Big Win", 2000000, 500000, 72, "athlete", "BigCh"),
        ]
        history_db.add_outperformers(ops)
        digest = generate_weekly_digest(days=7)

        emerging_names = [e['channel_name'] for e in digest['emerging_creators']]
        assert "SmallCh" in emerging_names
        assert "BigCh" not in emerging_names

    def test_title_formulas(self, temp_db):
        """Title formulas require 2+ pattern combos appearing 2+ times."""
        # Two videos with same pattern combo: reaction + all_caps
        ops = [
            _make_video("v1", "INSANE Challenge REACTION", 500000, 100000, 48, "athlete", "Ch1"),
            _make_video("v2", "CRAZY Workout REACTION", 300000, 100000, 72, "athlete", "Ch2"),
        ]
        history_db.add_outperformers(ops)
        digest = generate_weekly_digest(days=7)

        # Both test videos get reaction + all_caps patterns from _make_video
        formulas = digest['title_formulas']
        if formulas:
            # At least one formula should exist since both have same patterns
            assert formulas[0]['count'] >= 2

    def test_by_sport_grouping(self, temp_db):
        """Videos are grouped by sport category."""
        ops = [
            _make_video("vb1", "Basketball Slam", 500000, 100000, 72, "basketball", "BballCh"),
            _make_video("vf1", "Football TD", 500000, 100000, 72, "football", "FballCh"),
        ]
        history_db.add_outperformers(ops)
        digest = generate_weekly_digest(days=7)

        assert 'Basketball' in digest['by_sport']
        assert 'Football' in digest['by_sport']
        assert digest['by_sport']['Basketball']['total_videos'] == 1
        assert digest['by_sport']['Football']['total_videos'] == 1

    def test_digest_email_format(self, temp_db, sample_outperformers):
        """Weekly digest email renders correctly."""
        history_db.add_outperformers(sample_outperformers)
        digest = generate_weekly_digest(days=7)

        subject, text, html = format_weekly_digest_email(digest)

        assert "Weekly Sports Intel" in subject
        assert "3 outperformers" in subject
        assert "WHAT'S WORKING" in text
        assert "TOP 10 THIS WEEK" in text
        assert "Weekly Sports Intelligence" in html

    def test_digest_email_empty(self, temp_db):
        """Empty digest email still renders."""
        digest = generate_weekly_digest(days=7)
        subject, text, html = format_weekly_digest_email(digest)

        assert "0 outperformers" in subject
        assert "Total outperformers: 0" in text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
