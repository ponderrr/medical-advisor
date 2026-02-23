"""
Tests for the Twitter/X scraper.
These tests do NOT make any network calls or use snscrape's actual scraping.
They test config loading, query building, export, and deduplication logic only.
"""

import json
import os
import tempfile

import pytest

from scrapers.x_scraper import TwitterScraper


@pytest.fixture
def scraper(tmp_path):
    """Create a TwitterScraper with a temporary config file."""
    config_data = {
        "primary_name": "Retatrutide",
        "alternative_names": ["reta", "retatrutide", "LY3437943", "LY-3437943", "GLP-3 RT", "triple agonist"],
        "target_accounts": ["BasedBiohacker"],
        "hashtags": ["peptides", "biohacking", "GLP1", "retatrutide"],
        "subreddits": ["Peptides", "PEDs", "Biohacking", "AdvancedFitness"],
    }
    config_path = tmp_path / "search_terms.json"
    config_path.write_text(json.dumps(config_data), encoding="utf-8")
    return TwitterScraper(config_path=str(config_path))


class TestLoadConfig:
    """Tests for config loading."""

    def test_load_config(self, scraper):
        """Verify config loads and has expected keys."""
        assert scraper.config is not None
        assert "primary_name" in scraper.config
        assert "alternative_names" in scraper.config
        assert "target_accounts" in scraper.config
        assert "hashtags" in scraper.config
        assert "subreddits" in scraper.config

    def test_load_config_values(self, scraper):
        """Verify config values are correctly loaded."""
        assert scraper.config["primary_name"] == "Retatrutide"
        assert "reta" in scraper.config["alternative_names"]
        assert "BasedBiohacker" in scraper.config["target_accounts"]
        assert "peptides" in scraper.config["hashtags"]

    def test_load_config_counts(self, scraper):
        """Verify config lists have expected lengths."""
        assert len(scraper.config["alternative_names"]) == 6
        assert len(scraper.config["target_accounts"]) == 1
        assert len(scraper.config["hashtags"]) == 4
        assert len(scraper.config["subreddits"]) == 4


class TestBuildQueries:
    """Tests for query building."""

    def test_build_queries(self, scraper):
        """Verify queries are built from config."""
        queries = scraper.build_queries()
        assert isinstance(queries, list)
        assert len(queries) > 0
        # Each item should be a (query, source_label) tuple
        for query, label in queries:
            assert isinstance(query, str)
            assert isinstance(label, str)

    def test_build_queries_count(self, scraper):
        """Verify the correct number of queries are built."""
        queries = scraper.build_queries()
        # 6 alternative_names + 1 target_account + 4 hashtags = 11
        expected = (
            len(scraper.config["alternative_names"])
            + len(scraper.config["target_accounts"])
            + len(scraper.config["hashtags"])
        )
        assert len(queries) == expected

    def test_build_queries_alternative_names(self, scraper):
        """Verify alternative names are included as search terms."""
        queries = scraper.build_queries()
        query_strings = [q for q, _ in queries]
        for name in scraper.config["alternative_names"]:
            assert name in query_strings

    def test_build_queries_target_accounts(self, scraper):
        """Verify target accounts use 'from:' syntax."""
        queries = scraper.build_queries()
        query_strings = [q for q, _ in queries]
        for account in scraper.config["target_accounts"]:
            assert f"from:{account}" in query_strings

    def test_build_queries_hashtags(self, scraper):
        """Verify hashtags use '#' prefix."""
        queries = scraper.build_queries()
        query_strings = [q for q, _ in queries]
        for hashtag in scraper.config["hashtags"]:
            assert f"#{hashtag}" in query_strings


class TestExport:
    """Tests for data export."""

    def test_export_creates_file(self, scraper, tmp_path):
        """Manually set scraper.data with test data, call export, verify file exists."""
        # Add test data
        scraper.data = {
            123456: {
                "id": 123456,
                "text": "Test tweet about retatrutide",
                "author_username": "testuser",
                "author_followers": 1000,
                "date": "2025-01-15T12:00:00+00:00",
                "retweet_count": 5,
                "like_count": 20,
                "url": "https://twitter.com/testuser/status/123456",
                "source_query": "search:retatrutide",
                "scraped_at": "2025-01-15T13:00:00+00:00",
            },
            789012: {
                "id": 789012,
                "text": "Another tweet about peptides",
                "author_username": "anotheruser",
                "author_followers": 500,
                "date": "2025-01-15T14:00:00+00:00",
                "retweet_count": 2,
                "like_count": 10,
                "url": "https://twitter.com/anotheruser/status/789012",
                "source_query": "hashtag:peptides",
                "scraped_at": "2025-01-15T15:00:00+00:00",
            },
        }

        output_dir = str(tmp_path / "export_output")
        filepath = scraper.export_data(output_dir=output_dir)

        # Verify file was created
        assert os.path.exists(filepath)
        assert filepath.endswith(".json")

        # Verify contents
        with open(filepath, "r", encoding="utf-8") as f:
            exported = json.load(f)
        assert isinstance(exported, list)
        assert len(exported) == 2

    def test_export_empty_data(self, scraper, tmp_path):
        """Verify export works with empty data."""
        output_dir = str(tmp_path / "empty_export")
        filepath = scraper.export_data(output_dir=output_dir)

        assert os.path.exists(filepath)
        with open(filepath, "r", encoding="utf-8") as f:
            exported = json.load(f)
        assert exported == []


class TestDeduplication:
    """Tests for tweet deduplication."""

    def test_deduplication(self, scraper):
        """Add same ID twice, verify only one entry."""
        tweet_id = 111222333

        # Add first entry
        scraper.data[tweet_id] = {
            "id": tweet_id,
            "text": "First version of tweet",
            "author_username": "user1",
            "author_followers": 100,
            "date": "2025-01-15T12:00:00+00:00",
            "retweet_count": 1,
            "like_count": 5,
            "url": f"https://twitter.com/user1/status/{tweet_id}",
            "source_query": "search:reta",
            "scraped_at": "2025-01-15T13:00:00+00:00",
        }

        # Try to add duplicate with same ID (dict naturally deduplicates)
        # This simulates the deduplication check in _scrape_query:
        #   if tweet_id not in self.data: ...
        if tweet_id not in scraper.data:
            scraper.data[tweet_id] = {
                "id": tweet_id,
                "text": "Second version of tweet (should not overwrite)",
                "author_username": "user1",
                "author_followers": 100,
                "date": "2025-01-15T12:00:00+00:00",
                "retweet_count": 1,
                "like_count": 5,
                "url": f"https://twitter.com/user1/status/{tweet_id}",
                "source_query": "search:retatrutide",
                "scraped_at": "2025-01-15T13:00:00+00:00",
            }

        # Verify only one entry exists
        assert len(scraper.data) == 1
        assert scraper.data[tweet_id]["text"] == "First version of tweet"

    def test_deduplication_multiple_ids(self, scraper):
        """Verify different IDs are stored separately."""
        scraper.data[100] = {"id": 100, "text": "Tweet A"}
        scraper.data[200] = {"id": 200, "text": "Tweet B"}
        scraper.data[300] = {"id": 300, "text": "Tweet C"}

        # Try duplicates
        if 100 not in scraper.data:
            scraper.data[100] = {"id": 100, "text": "Duplicate A"}
        if 200 not in scraper.data:
            scraper.data[200] = {"id": 200, "text": "Duplicate B"}

        assert len(scraper.data) == 3
        assert scraper.data[100]["text"] == "Tweet A"
        assert scraper.data[200]["text"] == "Tweet B"


class TestSummary:
    """Tests for summary generation."""

    def test_generate_summary(self, scraper, tmp_path):
        """Verify summary is generated correctly."""
        scraper.data = {
            1: {
                "id": 1,
                "text": "Tweet 1",
                "like_count": 10,
                "retweet_count": 2,
                "source_query": "search:reta",
            },
            2: {
                "id": 2,
                "text": "Tweet 2",
                "like_count": 20,
                "retweet_count": 5,
                "source_query": "search:retatrutide",
            },
        }

        logs_dir = str(tmp_path / "logs_output")
        filepath = scraper._generate_summary(logs_dir=logs_dir)

        assert os.path.exists(filepath)
        with open(filepath, "r", encoding="utf-8") as f:
            summary = json.load(f)

        assert summary["total_unique_tweets"] == 2
        assert summary["total_likes"] == 30
        assert summary["total_retweets"] == 7
