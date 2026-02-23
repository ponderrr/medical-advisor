"""
Tests for the data validator (validate_data.py).

These tests verify initialization, JSON loading, field checking,
source-specific validation, and report generation using temporary
test data — no real scraped files are needed.
"""

import json

import pytest

from validate_data import DataValidator


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------
@pytest.fixture
def validator(tmp_path):
    """Create a DataValidator pointing at a temporary data directory."""
    data_dir = tmp_path / "data" / "raw"
    data_dir.mkdir(parents=True)
    return DataValidator(data_dir=str(data_dir))


def _write_json(directory, filename, data):
    """Helper: write a list of dicts as JSON to *directory/filename*."""
    path = directory / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return path


@pytest.fixture
def sample_twitter_data(validator):
    """Create a small X/Twitter JSON file."""
    data = [
        {
            "id": 1,
            "text": "Retatrutide is a promising compound for obesity",
            "author_username": "user1",
            "date": "2024-01-01T12:00:00",
            "retweet_count": 5,
            "like_count": 20,
            "url": "https://twitter.com/user1/status/1",
            "source_query": "search:retatrutide",
            "scraped_at": "2024-01-01T13:00:00",
        },
        {
            "id": 2,
            "text": "Triple agonist data looks great",
            "author_username": "user2",
            "date": "2024-02-15T08:00:00",
            "retweet_count": 2,
            "like_count": 10,
            "url": "https://twitter.com/user2/status/2",
            "source_query": "search:reta",
            "scraped_at": "2024-02-15T09:00:00",
        },
    ]
    return _write_json(validator.data_dir, "x_tweets_2024-01-01.json", data)


@pytest.fixture
def sample_pubmed_data(validator):
    """Create a small PubMed JSON file."""
    data = [
        {
            "pmid": "12345678",
            "title": "A Study of Retatrutide",
            "authors": ["Author A"],
            "journal": "Nature Medicine",
            "publication_date": "2024 Jan",
            "abstract": "This study evaluates the efficacy of retatrutide in obese patients over a 48-week period.",
            "keywords": ["retatrutide"],
            "mesh_terms": ["Humans"],
            "doi": "10.1234/test",
            "pubmed_url": "https://pubmed.ncbi.nlm.nih.gov/12345678/",
            "scraped_at": "2024-01-01T00:00:00",
        },
    ]
    return _write_json(validator.data_dir, "pubmed_papers_2024-01-01.json", data)


@pytest.fixture
def sample_clinical_data(validator):
    """Create a small Clinical Trials JSON file."""
    data = [
        {
            "nct_id": "NCT05929066",
            "brief_title": "A Study of Retatrutide in Obesity",
            "official_title": "Phase 3 Retatrutide Study",
            "status": "RECRUITING",
            "sponsor": "Eli Lilly",
            "phase": "PHASE3",
            "start_date": "2023-09-01",
            "completion_date": "2026-12-31",
            "enrollment": 1800,
            "brief_summary": "Evaluates retatrutide for obesity.",
            "conditions": ["Obesity"],
            "interventions": ["Retatrutide"],
            "study_type": "INTERVENTIONAL",
            "has_results": False,
            "trial_url": "https://clinicaltrials.gov/study/NCT05929066",
            "scraped_at": "2024-01-01T00:00:00",
        },
    ]
    return _write_json(validator.data_dir, "clinical_trials_2024-01-01.json", data)


@pytest.fixture
def sample_reddit_data(validator):
    """Create a small Reddit JSON file."""
    data = [
        {
            "id": "abc123",
            "type": "post",
            "subreddit": "Peptides",
            "author": "testuser",
            "title": "Retatrutide experience",
            "text": "I started retatrutide two weeks ago and already noticing appetite suppression.",
            "score": 42,
            "upvote_ratio": 0.95,
            "num_comments": 15,
            "created_utc": 1700000000,
            "url": "https://reddit.com/r/Peptides/abc123",
            "search_term": "retatrutide",
            "scraped_at": "2024-01-01T00:00:00",
        },
        {
            "id": "def456",
            "type": "comment",
            "subreddit": "Peptides",
            "author": "commenter1",
            "text": "Great write-up, I had a similar experience with the triple agonist compound.",
            "score": 8,
            "created_utc": 1700001000,
            "url": "https://reddit.com/r/Peptides/abc123/def456",
            "parent_post_id": "abc123",
            "search_term": "retatrutide",
            "scraped_at": "2024-01-01T00:00:00",
        },
    ]
    return _write_json(validator.data_dir, "reddit_posts_2024-01-01.json", data)


# ------------------------------------------------------------------
# Tests: Init
# ------------------------------------------------------------------
class TestInit:
    def test_validator_init(self):
        validator = DataValidator()
        assert validator.validation_results == {}
        assert validator.issues == []
        assert validator.recommendations == []

    def test_custom_data_dir(self, tmp_path):
        v = DataValidator(data_dir=str(tmp_path))
        assert v.data_dir == tmp_path


# ------------------------------------------------------------------
# Tests: JSON loading
# ------------------------------------------------------------------
class TestLoadJson:
    def test_load_json_file(self, validator, sample_twitter_data):
        data = validator.load_json_file(sample_twitter_data)
        assert data is not None
        assert len(data) == 2

    def test_load_missing_file(self, validator):
        data = validator.load_json_file(validator.data_dir / "nonexistent.json")
        assert data is None
        assert len(validator.issues) == 1

    def test_load_invalid_json(self, validator):
        bad_file = validator.data_dir / "bad.json"
        bad_file.write_text("not valid json {{{", encoding="utf-8")
        data = validator.load_json_file(bad_file)
        assert data is None
        assert len(validator.issues) == 1


# ------------------------------------------------------------------
# Tests: Required fields
# ------------------------------------------------------------------
class TestRequiredFields:
    def test_check_required_fields_all_present(self, validator):
        data = [
            {"id": 1, "text": "hello"},
            {"id": 2, "text": "world"},
        ]
        missing = validator._check_required_fields(data, ["id", "text"])
        assert missing == {}

    def test_check_required_fields_some_missing(self, validator):
        data = [
            {"id": 1, "text": "hello"},
            {"id": 2, "text": ""},
            {"id": 3},
        ]
        missing = validator._check_required_fields(data, ["id", "text"])
        assert "text" in missing
        assert missing["text"] == 2
        assert "id" not in missing

    def test_check_required_fields_none_values(self, validator):
        data = [
            {"id": 1, "text": None},
            {"id": None, "text": "ok"},
        ]
        missing = validator._check_required_fields(data, ["id", "text"])
        assert missing.get("id") == 1
        assert missing.get("text") == 1


# ------------------------------------------------------------------
# Tests: Source validators
# ------------------------------------------------------------------
class TestTwitterValidation:
    def test_validate_twitter_data(self, validator, sample_twitter_data):
        validator.validate_twitter_data(sample_twitter_data)
        assert "twitter" in validator.validation_results
        result = validator.validation_results["twitter"]
        assert result["total_records"] == 2
        assert result["unique_authors"] == 2

    def test_twitter_below_target(self, validator, sample_twitter_data):
        validator.validate_twitter_data(sample_twitter_data)
        # 2 tweets is below 1000 target
        assert any("Twitter" in r for r in validator.recommendations)


class TestPubMedValidation:
    def test_validate_pubmed_data(self, validator, sample_pubmed_data):
        validator.validate_pubmed_data(sample_pubmed_data)
        assert "pubmed" in validator.validation_results
        result = validator.validation_results["pubmed"]
        assert result["total_records"] == 1
        assert result["complete_abstracts"] == 1
        assert result["unique_journals"] == 1

    def test_pubmed_below_target(self, validator, sample_pubmed_data):
        validator.validate_pubmed_data(sample_pubmed_data)
        assert any("PubMed" in r for r in validator.recommendations)


class TestClinicalTrialsValidation:
    def test_validate_clinical_trials_data(self, validator, sample_clinical_data):
        validator.validate_clinical_trials_data(sample_clinical_data)
        assert "clinical_trials" in validator.validation_results
        result = validator.validation_results["clinical_trials"]
        assert result["total_records"] == 1
        assert "PHASE3" in result["phase_distribution"]
        assert "RECRUITING" in result["status_distribution"]


class TestRedditValidation:
    def test_validate_reddit_data(self, validator, sample_reddit_data):
        validator.validate_reddit_data(sample_reddit_data)
        assert "reddit" in validator.validation_results
        result = validator.validation_results["reddit"]
        assert result["total_records"] == 2
        assert result["posts"] == 1
        assert result["comments"] == 1
        assert "Peptides" in result["subreddit_distribution"]

    def test_reddit_below_target(self, validator, sample_reddit_data):
        validator.validate_reddit_data(sample_reddit_data)
        assert any("Reddit" in r for r in validator.recommendations)


# ------------------------------------------------------------------
# Tests: Full pipeline & report
# ------------------------------------------------------------------
class TestValidateAll:
    def test_validate_all_with_data(
        self, validator, sample_twitter_data, sample_pubmed_data,
        sample_clinical_data, sample_reddit_data,
    ):
        validator.validate_all()
        assert len(validator.validation_results) == 4
        assert "twitter" in validator.validation_results
        assert "pubmed" in validator.validation_results
        assert "clinical_trials" in validator.validation_results
        assert "reddit" in validator.validation_results

    def test_validate_all_empty_dir(self, validator):
        validator.validate_all()
        assert len(validator.validation_results) == 0
        assert any("No data files" in i for i in validator.issues)

    def test_validate_all_missing_dir(self, tmp_path):
        v = DataValidator(data_dir=str(tmp_path / "does_not_exist"))
        v.validate_all()
        assert any("not found" in i for i in v.issues)


class TestGenerateReport:
    def test_generate_report_returns_summary(self, validator):
        validator.validation_results = {
            "twitter": {"total_records": 100, "file": "test.json"},
        }
        summary = validator.generate_report()
        assert summary["total_records"] == 100
        assert summary["sources_validated"] == 1

    def test_generate_report_saves_file(self, validator):
        validator.validation_results = {
            "twitter": {"total_records": 50, "file": "test.json"},
        }
        summary = validator.generate_report()
        assert summary["report_file"].endswith(".txt")

    def test_generate_report_with_issues(self, validator):
        validator.validation_results = {}
        validator.issues = ["Test issue"]
        validator.recommendations = ["Test recommendation"]
        summary = validator.generate_report()
        assert summary["issues"] == 1
        assert summary["recommendations"] == 1
