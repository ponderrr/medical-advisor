"""
Tests for the PubMed scraper.

These tests verify config loading, query building, data export, and rate limit
configuration WITHOUT making any real network calls to the PubMed API.
"""

import json
import os
import tempfile

import pytest

from scrapers.pubmed_scraper import PubMedScraper


# Path to the real config file used by the project
CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "config",
    "search_terms.json",
)


@pytest.fixture
def scraper():
    """Create a PubMedScraper instance using the project config."""
    return PubMedScraper(config_path=CONFIG_PATH)


class TestLoadConfig:
    """Tests for configuration loading."""

    def test_load_config(self, scraper):
        """Verify config loads and contains expected top-level keys."""
        config = scraper.config
        assert isinstance(config, dict)
        assert "primary_name" in config
        assert "alternative_names" in config
        assert "target_accounts" in config
        assert "hashtags" in config
        assert "subreddits" in config

    def test_load_config_primary_name(self, scraper):
        """Verify the primary_name matches the expected value."""
        assert scraper.config["primary_name"] == "Retatrutide"

    def test_load_config_alternative_names_is_list(self, scraper):
        """Verify alternative_names is a list with entries."""
        alt = scraper.config["alternative_names"]
        assert isinstance(alt, list)
        assert len(alt) > 0

    def test_formal_names_extracted(self, scraper):
        """Verify that formal names are correctly filtered from config."""
        # Should include primary_name and formal identifiers
        assert "Retatrutide" in scraper.search_terms
        assert "LY3437943" in scraper.search_terms
        assert "LY-3437943" in scraper.search_terms

        # Should NOT include informal/slang terms
        assert "reta" not in scraper.search_terms
        assert "triple agonist" not in scraper.search_terms
        assert "GLP-3 RT" not in scraper.search_terms


class TestBuildSearchQuery:
    """Tests for query string construction."""

    def test_build_search_query_contains_formal_names(self, scraper):
        """Verify the query string contains each formal search term."""
        query = scraper.build_search_query()
        assert "Retatrutide" in query
        assert "LY3437943" in query
        assert "LY-3437943" in query

    def test_build_search_query_uses_or_operator(self, scraper):
        """Verify terms are joined with OR."""
        query = scraper.build_search_query()
        assert " OR " in query

    def test_build_search_query_terms_quoted(self, scraper):
        """Verify each term is wrapped in double quotes for exact match."""
        query = scraper.build_search_query()
        for term in scraper.search_terms:
            assert f'"{term}"' in query

    def test_build_search_query_no_informal_terms(self, scraper):
        """Verify informal terms do not appear in the query."""
        query = scraper.build_search_query()
        assert '"reta"' not in query
        assert '"triple agonist"' not in query


class TestExportCreatesFile:
    """Tests for the export_data method."""

    def test_export_creates_file(self, scraper):
        """Manually set scraper.data with test data, call export, verify file exists."""
        # Populate with fake data
        scraper.data = {
            "12345678": {
                "pmid": "12345678",
                "title": "Test Paper on Retatrutide",
                "authors": ["Author A", "Author B"],
                "journal": "Test Journal",
                "publication_date": "2025 Jan",
                "abstract": "This is a test abstract.",
                "keywords": ["retatrutide", "GLP-1"],
                "mesh_terms": ["Humans"],
                "doi": "10.1234/test.2025.001",
                "pubmed_url": "https://pubmed.ncbi.nlm.nih.gov/12345678/",
                "scraped_at": "2025-01-01T00:00:00",
            },
            "87654321": {
                "pmid": "87654321",
                "title": "Another Paper",
                "authors": ["Author C"],
                "journal": "Another Journal",
                "publication_date": "2024 Jun",
                "abstract": "Another abstract.",
                "keywords": [],
                "mesh_terms": [],
                "doi": "",
                "pubmed_url": "https://pubmed.ncbi.nlm.nih.gov/87654321/",
                "scraped_at": "2025-01-01T00:00:00",
            },
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = scraper.export_data(output_dir=tmpdir)

            # File should exist
            assert os.path.isfile(filepath)

            # File should be valid JSON with 2 entries
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            assert isinstance(data, list)
            assert len(data) == 2

    def test_export_empty_data(self, scraper):
        """Exporting with no data should still create a valid JSON file."""
        scraper.data = {}

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = scraper.export_data(output_dir=tmpdir)
            assert os.path.isfile(filepath)

            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            assert data == []


class TestRateLimiting:
    """Tests for rate limit configuration."""

    def test_rate_limiting(self, scraper):
        """Verify the scraper has rate_limit_delay set to 0.34 seconds."""
        assert hasattr(scraper, "rate_limit_delay")
        assert scraper.rate_limit_delay == 0.34

    def test_rate_limit_is_class_attribute(self):
        """Verify rate_limit_delay is defined at the class level."""
        assert hasattr(PubMedScraper, "rate_limit_delay")
        assert PubMedScraper.rate_limit_delay == 0.34
