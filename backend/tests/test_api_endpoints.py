"""
Tests for API data endpoints
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.models import Paper, ClinicalTrial, Tweet, RedditPost, DosingProtocol, SideEffect

# ------------------------------------------------------------------ #
# StaticPool forces all connections to share a single SQLite connection
# so create_all tables are visible to every Session.
# ------------------------------------------------------------------ #

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Base.metadata.create_all(bind=engine)
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_db():
    """Truncate all tables before each test."""
    db = TestSession()
    for table in reversed(Base.metadata.sorted_tables):
        db.execute(table.delete())
    db.commit()
    db.close()


@pytest.fixture
def db_with_data():
    db = TestSession()
    db.add(Paper(pmid="P001", title="Paper One", authors=["A"], journal="J1"))
    db.add(Paper(pmid="P002", title="Paper Two", authors=["B"], journal="J2"))
    db.add(ClinicalTrial(nct_id="NCT001", brief_title="Trial One", status="Recruiting", phase="Phase 3"))
    db.add(ClinicalTrial(nct_id="NCT002", brief_title="Trial Two", status="Completed", phase="Phase 2"))
    db.add(Tweet(tweet_id="T001", text="Tweet one", author_username="user1", like_count=10))
    db.add(Tweet(tweet_id="T002", text="Tweet two", author_username="user2", like_count=5))
    db.add(RedditPost(post_id="R001", post_type="post", subreddit="Peptides", text="Reddit post", author="ruser"))
    db.add(DosingProtocol(source_type="paper", source_id="P001", dose="5mg", frequency="weekly"))
    db.add(SideEffect(effect="Nausea", severity="mild", frequency=10))
    db.commit()
    db.close()


# ------------------------------------------------------------------ #
# /api/papers
# ------------------------------------------------------------------ #

def test_get_papers_empty():
    response = client.get("/api/papers")
    assert response.status_code == 200
    assert response.json() == []


def test_get_papers(db_with_data):
    response = client.get("/api/papers")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["pmid"] == "P001"


def test_get_papers_pagination(db_with_data):
    response = client.get("/api/papers?limit=1&skip=1")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_paper_by_pmid(db_with_data):
    response = client.get("/api/papers/P001")
    assert response.status_code == 200
    assert response.json()["pmid"] == "P001"


def test_get_paper_not_found():
    response = client.get("/api/papers/NOPE")
    assert response.status_code == 404


# ------------------------------------------------------------------ #
# /api/trials
# ------------------------------------------------------------------ #

def test_get_trials(db_with_data):
    response = client.get("/api/trials")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_get_trials_filter_phase(db_with_data):
    response = client.get("/api/trials?phase=Phase+3")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["nct_id"] == "NCT001"


def test_get_trials_filter_status(db_with_data):
    response = client.get("/api/trials?status=Completed")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["nct_id"] == "NCT002"


def test_get_trial_by_nct_id(db_with_data):
    response = client.get("/api/trials/NCT001")
    assert response.status_code == 200
    assert response.json()["nct_id"] == "NCT001"


def test_get_trial_not_found():
    response = client.get("/api/trials/NCTNOPE")
    assert response.status_code == 404


# ------------------------------------------------------------------ #
# /api/tweets
# ------------------------------------------------------------------ #

def test_get_tweets(db_with_data):
    response = client.get("/api/tweets")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_get_tweets_filter_author(db_with_data):
    response = client.get("/api/tweets?author=user1")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["tweet_id"] == "T001"


# ------------------------------------------------------------------ #
# /api/reddit
# ------------------------------------------------------------------ #

def test_get_reddit(db_with_data):
    response = client.get("/api/reddit")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["post_id"] == "R001"


def test_get_reddit_filter_subreddit(db_with_data):
    response = client.get("/api/reddit?subreddit=Peptides")
    assert response.status_code == 200
    assert len(response.json()) == 1


# ------------------------------------------------------------------ #
# /api/stats
# ------------------------------------------------------------------ #

def test_get_stats_empty():
    response = client.get("/api/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["total_papers"] == 0
    assert data["total_trials"] == 0
    assert data["total_tweets"] == 0
    assert data["total_reddit_posts"] == 0
    assert data["total_dosing_protocols"] == 0
    assert data["total_side_effects"] == 0


def test_get_stats_with_data(db_with_data):
    response = client.get("/api/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["total_papers"] == 2
    assert data["total_trials"] == 2
    assert data["total_tweets"] == 2
    assert data["total_reddit_posts"] == 1
    assert data["total_dosing_protocols"] == 1
    assert data["total_side_effects"] == 1


# ------------------------------------------------------------------ #
# /api/dosing and /api/side-effects
# ------------------------------------------------------------------ #

def test_get_dosing(db_with_data):
    response = client.get("/api/dosing")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["dose"] == "5mg"


def test_get_side_effects(db_with_data):
    response = client.get("/api/side-effects")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["effect"] == "Nausea"
