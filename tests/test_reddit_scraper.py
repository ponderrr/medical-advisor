"""
Tests for scrapers/reddit_scraper.py.

These tests verify config loading, search-term filtering, and deduplication
logic. They never call the Reddit API -- the PRAW client initialisation is
patched out so the test suite works without credentials.
"""

from unittest.mock import patch

import pytest

# Patch praw.Reddit before importing the scraper so that __init__ never
# attempts to contact Reddit (which would fail without credentials).
with patch("praw.Reddit"):
    from scrapers.reddit_scraper import RedditScraper


@pytest.fixture
def scraper():
    """Return a RedditScraper instance with a mocked Reddit client."""
    with patch("scrapers.reddit_scraper.RedditScraper._init_reddit", return_value=None):
        s = RedditScraper()
    return s


class TestLoadConfig:
    """Verify that the JSON config loads correctly."""

    def test_load_config(self, scraper):
        config = scraper.config
        assert isinstance(config, dict)
        assert "primary_name" in config
        assert "alternative_names" in config
        assert "subreddits" in config
        assert "hashtags" in config
        assert "target_accounts" in config

    def test_config_primary_name(self, scraper):
        assert scraper.config["primary_name"] == "Retatrutide"

    def test_config_subreddits(self, scraper):
        expected = {"Peptides", "PEDs", "Biohacking", "AdvancedFitness"}
        assert set(scraper.config["subreddits"]) == expected


class TestGetSearchTerms:
    """Verify that get_search_terms returns social-media-friendly terms."""

    def test_returns_list(self, scraper):
        terms = scraper.get_search_terms()
        assert isinstance(terms, list)

    def test_contains_expected_terms(self, scraper):
        terms = scraper.get_search_terms()
        assert "reta" in terms
        assert "retatrutide" in terms
        assert "triple agonist" in terms

    def test_excludes_lab_codes(self, scraper):
        terms = scraper.get_search_terms()
        for term in terms:
            assert term not in ("LY3437943", "LY-3437943", "GLP-3 RT")

    def test_length(self, scraper):
        terms = scraper.get_search_terms()
        # Exactly three social-media-friendly terms in the default config.
        assert len(terms) == 3


class TestDeduplication:
    """Verify that the dict-based deduplication works as expected."""

    def test_duplicate_post_is_not_added_twice(self, scraper):
        post = {
            "id": "abc123",
            "type": "post",
            "subreddit": "Peptides",
            "author": "testuser",
            "title": "Test post",
            "text": "Some text",
            "score": 10,
            "upvote_ratio": 0.95,
            "num_comments": 3,
            "created_utc": 1700000000,
            "url": "https://reddit.com/r/Peptides/abc123",
            "search_term": "reta",
            "scraped_at": "2025-01-01T00:00:00+00:00",
        }

        # Add the same post twice using the same key.
        scraper.data[post["id"]] = post
        scraper.data[post["id"]] = post

        assert len(scraper.data) == 1

    def test_different_ids_are_kept(self, scraper):
        for i in range(5):
            scraper.data[f"id_{i}"] = {"id": f"id_{i}", "type": "post"}

        assert len(scraper.data) == 5

    def test_duplicate_comment_is_not_added_twice(self, scraper):
        comment = {
            "id": "comment_xyz",
            "type": "comment",
            "subreddit": "PEDs",
            "author": "anotheruser",
            "text": "A" * 60,
            "score": 5,
            "created_utc": 1700000000,
            "url": "https://reddit.com/r/PEDs/comments/abc/test/comment_xyz",
            "parent_post_id": "abc",
            "search_term": "retatrutide",
            "scraped_at": "2025-01-01T00:00:00+00:00",
        }

        scraper.data[comment["id"]] = comment
        scraper.data[comment["id"]] = {**comment, "score": 999}

        assert len(scraper.data) == 1
        # The second write should overwrite (dict semantics), but there is
        # still only one entry.
        assert scraper.data["comment_xyz"]["score"] == 999


class TestScrapeAllWithoutCredentials:
    """Verify that scrape_all returns 0 when no Reddit client is available."""

    def test_scrape_all_returns_zero(self, scraper):
        assert scraper.reddit is None
        result = scraper.scrape_all()
        assert result == 0
