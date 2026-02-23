"""
Tests for the master orchestrator (run_scrapers.py).

These tests verify initialization, result tracking, error handling,
and user input without running any actual scrapers.
"""

import pytest

from run_scrapers import ScraperOrchestrator


class TestOrchestratorInit:
    """Tests for orchestrator initialization."""

    def test_orchestrator_init(self):
        """Test orchestrator initializes correctly."""
        orch = ScraperOrchestrator()
        assert orch.results == {}
        assert orch.start_time is None
        assert orch.end_time is None

    def test_orchestrator_has_required_methods(self):
        """Test orchestrator has all required methods."""
        orch = ScraperOrchestrator()
        assert callable(orch.run_scraper)
        assert callable(orch.ask_user)
        assert callable(orch.run_all)
        assert callable(orch.generate_summary)


class TestAskUser:
    """Tests for user input handling."""

    def test_ask_user_yes(self, monkeypatch):
        """Test user input - yes."""
        orch = ScraperOrchestrator()
        monkeypatch.setattr("builtins.input", lambda _: "y")
        assert orch.ask_user("Test?") is True

    def test_ask_user_yes_full(self, monkeypatch):
        """Test user input - yes (full word)."""
        orch = ScraperOrchestrator()
        monkeypatch.setattr("builtins.input", lambda _: "yes")
        assert orch.ask_user("Test?") is True

    def test_ask_user_no(self, monkeypatch):
        """Test user input - no."""
        orch = ScraperOrchestrator()
        monkeypatch.setattr("builtins.input", lambda _: "n")
        assert orch.ask_user("Test?") is False

    def test_ask_user_empty(self, monkeypatch):
        """Test user input - empty string defaults to no."""
        orch = ScraperOrchestrator()
        monkeypatch.setattr("builtins.input", lambda _: "")
        assert orch.ask_user("Test?") is False

    def test_ask_user_garbage(self, monkeypatch):
        """Test user input - garbage defaults to no."""
        orch = ScraperOrchestrator()
        monkeypatch.setattr("builtins.input", lambda _: "asdf")
        assert orch.ask_user("Test?") is False


class TestRunScraper:
    """Tests for individual scraper execution tracking."""

    def test_run_scraper_tracks_results(self):
        """Test scraper tracking on success."""
        orch = ScraperOrchestrator()

        def mock_scraper():
            return 10

        orch.run_scraper("Test", mock_scraper)
        assert "Test" in orch.results
        assert orch.results["Test"]["status"] == "success"
        assert orch.results["Test"]["records"] == 10
        assert orch.results["Test"]["error"] is None
        assert orch.results["Test"]["duration_seconds"] >= 0

    def test_run_scraper_handles_errors(self):
        """Test error handling - scraper that raises."""
        orch = ScraperOrchestrator()

        def failing_scraper():
            raise Exception("Test error")

        orch.run_scraper("Failing", failing_scraper)
        assert "Failing" in orch.results
        assert orch.results["Failing"]["status"] == "failed"
        assert orch.results["Failing"]["records"] == 0
        assert "Test error" in orch.results["Failing"]["error"]

    def test_run_scraper_zero_records(self):
        """Test scraper returning zero records."""
        orch = ScraperOrchestrator()

        def empty_scraper():
            return 0

        orch.run_scraper("Empty", empty_scraper)
        assert orch.results["Empty"]["status"] == "success"
        assert orch.results["Empty"]["records"] == 0

    def test_run_scraper_non_int_return(self):
        """Test scraper returning non-int value."""
        orch = ScraperOrchestrator()

        def dict_scraper():
            return {"data": [1, 2, 3]}

        orch.run_scraper("DictReturn", dict_scraper)
        assert orch.results["DictReturn"]["status"] == "success"
        assert orch.results["DictReturn"]["records"] == 0

    def test_multiple_scrapers(self):
        """Test running multiple scrapers in sequence."""
        orch = ScraperOrchestrator()

        orch.run_scraper("A", lambda: 5)
        orch.run_scraper("B", lambda: 10)
        orch.run_scraper("C", lambda: 15)

        assert len(orch.results) == 3
        assert orch.results["A"]["records"] == 5
        assert orch.results["B"]["records"] == 10
        assert orch.results["C"]["records"] == 15


class TestGenerateSummary:
    """Tests for summary generation."""

    def test_generate_summary(self):
        """Test summary generation with mixed results."""
        orch = ScraperOrchestrator()
        orch.start_time = 1000.0
        orch.end_time = 1010.0
        orch.results = {
            "A": {"status": "success", "records": 100, "duration_seconds": 5.0, "error": None},
            "B": {"status": "failed", "records": 0, "duration_seconds": 2.0, "error": "timeout"},
            "C": {"status": "skipped", "records": 0, "duration_seconds": 0, "error": None},
        }

        summary = orch.generate_summary()

        assert summary["total_records"] == 100
        assert summary["scrapers_success"] == 1
        assert summary["scrapers_failed"] == 1
        assert summary["scrapers_skipped"] == 1
        assert summary["total_duration_seconds"] == 10.0

    def test_generate_summary_all_success(self):
        """Test summary with all successful scrapers."""
        orch = ScraperOrchestrator()
        orch.start_time = 0.0
        orch.end_time = 5.0
        orch.results = {
            "A": {"status": "success", "records": 50, "duration_seconds": 2.0, "error": None},
            "B": {"status": "success", "records": 25, "duration_seconds": 3.0, "error": None},
        }

        summary = orch.generate_summary()

        assert summary["total_records"] == 75
        assert summary["scrapers_success"] == 2
        assert summary["scrapers_failed"] == 0
