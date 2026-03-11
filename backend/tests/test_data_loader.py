"""
Integration tests for the data loading pipeline (JSON → SQLite)
"""
import json
import pytest
from datetime import datetime
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Paper, ClinicalTrial, Tweet, RedditPost
from app.services.data_loader import DataLoader, parse_datetime


# ------------------------------------------------------------------ #
# Fixtures
# ------------------------------------------------------------------ #

@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def sample_papers_file(tmp_path):
    data = [
        {
            "pmid": "11111",
            "title": "Retatrutide Phase 2 Results",
            "authors": ["Smith J", "Doe A"],
            "journal": "NEJM",
            "publication_date": "2023/06/15",
            "abstract": "Significant weight loss observed.",
            "keywords": ["obesity", "GLP-1"],
            "mesh_terms": ["Peptides"],
            "doi": "10.1234/test",
            "pubmed_url": "https://pubmed.ncbi.nlm.nih.gov/11111/",
            "scraped_at": "2026-03-01T10:00:00",
        }
    ]
    p = tmp_path / "pubmed_papers_2026-03-01.json"
    p.write_text(json.dumps(data))
    return p


@pytest.fixture
def sample_trials_file(tmp_path):
    data = [
        {
            "nct_id": "NCT99999",
            "brief_title": "Retatrutide Obesity Trial",
            "official_title": "A Phase 3 Study",
            "status": "Recruiting",
            "sponsor": "Eli Lilly",
            "phase": "Phase 3",
            "start_date": "2023-01-01",
            "completion_date": "2025-12-31",
            "primary_completion_date": "2025-06-30",
            "enrollment": 500,
            "brief_summary": "Testing retatrutide.",
            "detailed_description": None,
            "conditions": ["Obesity"],
            "interventions": ["Retatrutide"],
            "intervention_types": ["Drug"],
            "primary_outcomes": ["Weight loss at 48 weeks"],
            "secondary_outcomes": ["HbA1c reduction"],
            "study_type": "Interventional",
            "has_results": False,
            "trial_url": "https://clinicaltrials.gov/study/NCT99999",
            "scraped_at": "2026-03-01T10:00:00+00:00",
        }
    ]
    p = tmp_path / "clinical_trials_2026-03-01.json"
    p.write_text(json.dumps(data))
    return p


@pytest.fixture
def sample_tweets_file(tmp_path):
    data = [
        {
            "id": "9876543210",
            "text": "Retatrutide is amazing for weight loss!",
            "author_username": "biohacker42",
            "author_followers": 12000,
            "date": "2026-02-15T14:30:00",
            "retweet_count": 5,
            "like_count": 42,
            "url": "https://twitter.com/biohacker42/status/9876543210",
            "source_query": "retatrutide",
            "scraped_at": "2026-03-01T10:00:00+00:00",
        }
    ]
    p = tmp_path / "x_tweets_2026-03-01.json"
    p.write_text(json.dumps(data))
    return p


@pytest.fixture
def sample_reddit_file(tmp_path):
    data = [
        {
            "id": "abc123",
            "type": "post",
            "subreddit": "Peptides",
            "author": "retatrutide_user",
            "title": "My 12-week retatrutide log",
            "text": "Starting at 2.5mg, now at 8mg weekly.",
            "score": 150,
            "upvote_ratio": 0.97,
            "num_comments": 45,
            "created_utc": 1709251200,
            "url": "https://reddit.com/r/Peptides/comments/abc123",
            "search_term": "retatrutide",
            "scraped_at": "2026-03-01T10:00:00+00:00",
        },
        {
            "id": "def456",
            "type": "comment",
            "subreddit": "Peptides",
            "author": "commenter1",
            "title": None,
            "text": "Great results, what vendor?",
            "score": 20,
            "upvote_ratio": None,
            "num_comments": None,
            "created_utc": 1709265600,
            "url": "https://reddit.com/r/Peptides/comments/abc123/comment/def456",
            "parent_post_id": "abc123",
            "search_term": "retatrutide",
            "scraped_at": "2026-03-01T10:00:00+00:00",
        },
    ]
    p = tmp_path / "reddit_posts_2026-03-01.json"
    p.write_text(json.dumps(data))
    return p


# ------------------------------------------------------------------ #
# parse_datetime tests
# ------------------------------------------------------------------ #

def test_parse_datetime_iso():
    dt = parse_datetime("2026-03-01T10:00:00")
    assert isinstance(dt, datetime)
    assert dt.year == 2026


def test_parse_datetime_iso_with_tz():
    dt = parse_datetime("2026-03-01T10:00:00+00:00")
    assert isinstance(dt, datetime)


def test_parse_datetime_unix_timestamp():
    dt = parse_datetime(1709251200)
    assert isinstance(dt, datetime)


def test_parse_datetime_none():
    assert parse_datetime(None) is None


def test_parse_datetime_invalid():
    assert parse_datetime("not-a-date") is None


# ------------------------------------------------------------------ #
# DataLoader tests
# ------------------------------------------------------------------ #

def test_load_papers(test_db, sample_papers_file):
    loader = DataLoader(test_db)
    loader.load_papers(sample_papers_file)

    papers = test_db.query(Paper).all()
    assert len(papers) == 1
    assert papers[0].pmid == "11111"
    assert papers[0].title == "Retatrutide Phase 2 Results"
    assert papers[0].authors == ["Smith J", "Doe A"]
    assert loader.stats["papers_loaded"] == 1
    assert loader.stats["errors"] == []


def test_load_trials(test_db, sample_trials_file):
    loader = DataLoader(test_db)
    loader.load_trials(sample_trials_file)

    trials = test_db.query(ClinicalTrial).all()
    assert len(trials) == 1
    t = trials[0]
    assert t.nct_id == "NCT99999"
    assert t.enrollment == "500"       # Integer converted to String
    assert t.has_results == "False"    # Boolean converted to String
    assert loader.stats["trials_loaded"] == 1


def test_load_tweets(test_db, sample_tweets_file):
    loader = DataLoader(test_db)
    loader.load_tweets(sample_tweets_file)

    tweets = test_db.query(Tweet).all()
    assert len(tweets) == 1
    assert tweets[0].tweet_id == "9876543210"  # JSON "id" → DB "tweet_id"
    assert tweets[0].like_count == 42
    assert loader.stats["tweets_loaded"] == 1


def test_load_reddit(test_db, sample_reddit_file):
    loader = DataLoader(test_db)
    loader.load_reddit(sample_reddit_file)

    posts = test_db.query(RedditPost).all()
    assert len(posts) == 2
    post = next(p for p in posts if p.post_id == "abc123")
    assert post.post_type == "post"      # JSON "type" → DB "post_type"
    assert post.subreddit == "Peptides"
    assert isinstance(post.created_utc, datetime)  # Unix ts converted
    assert loader.stats["reddit_loaded"] == 2


def test_duplicate_skipped(test_db, sample_papers_file):
    loader = DataLoader(test_db)
    loader.load_papers(sample_papers_file)
    loader.load_papers(sample_papers_file)  # Second load should skip duplicates

    papers = test_db.query(Paper).all()
    assert len(papers) == 1  # Still only 1


def test_load_all_dispatches(test_db, tmp_path, sample_papers_file, sample_tweets_file):
    loader = DataLoader(test_db, data_dir=tmp_path)
    stats = loader.load_all()

    assert stats["papers_loaded"] == 1
    assert stats["tweets_loaded"] == 1
    assert stats["trials_loaded"] == 0
    assert stats["reddit_loaded"] == 0


def test_load_all_empty_dir(test_db, tmp_path):
    loader = DataLoader(test_db, data_dir=tmp_path)
    stats = loader.load_all()
    assert stats["papers_loaded"] == 0
    assert stats["errors"] == []


def test_load_invalid_json(test_db, tmp_path):
    bad_file = tmp_path / "pubmed_papers_bad.json"
    bad_file.write_text("not valid json{{{")
    loader = DataLoader(test_db, data_dir=tmp_path)
    loader.load_all()
    assert len(loader.stats["errors"]) == 1


def test_reddit_field_mapping(test_db, sample_reddit_file):
    """Verify all field name discrepancies are handled correctly."""
    loader = DataLoader(test_db)
    loader.load_reddit(sample_reddit_file)

    comment = test_db.query(RedditPost).filter(RedditPost.post_id == "def456").first()
    assert comment is not None
    assert comment.post_type == "comment"
    assert comment.parent_post_id == "abc123"
    assert comment.author_karma is None  # Not in scraper output
