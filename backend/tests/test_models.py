"""
Tests for SQLAlchemy models
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models import Paper, ClinicalTrial, Tweet, RedditPost, DosingProtocol, SideEffect


@pytest.fixture
def db_session():
    """Create test database session"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_create_paper(db_session):
    """Test creating a paper"""
    paper = Paper(
        pmid="12345",
        title="Test Paper",
        authors=["Author 1", "Author 2"],
        journal="Test Journal",
        abstract="Test abstract"
    )
    db_session.add(paper)
    db_session.commit()

    assert paper.id is not None
    assert paper.pmid == "12345"


def test_create_trial(db_session):
    """Test creating a clinical trial"""
    trial = ClinicalTrial(
        nct_id="NCT12345",
        brief_title="Test Trial",
        status="Recruiting",
        phase="Phase 3"
    )
    db_session.add(trial)
    db_session.commit()

    assert trial.id is not None
    assert trial.nct_id == "NCT12345"


def test_create_tweet(db_session):
    """Test creating a tweet"""
    tweet = Tweet(
        tweet_id="123456789",
        text="Test tweet about retatrutide",
        author_username="testuser"
    )
    db_session.add(tweet)
    db_session.commit()

    assert tweet.id is not None
    assert tweet.tweet_id == "123456789"


def test_unique_constraint_pmid(db_session):
    """Test PMID unique constraint"""
    paper1 = Paper(pmid="12345", title="Paper 1", authors=[])
    paper2 = Paper(pmid="12345", title="Paper 2", authors=[])

    db_session.add(paper1)
    db_session.commit()

    db_session.add(paper2)
    with pytest.raises(Exception):  # IntegrityError
        db_session.commit()


def test_create_dosing_protocol(db_session):
    """Test creating dosing protocol"""
    protocol = DosingProtocol(
        source_type="paper",
        source_id="12345",
        dose="5mg",
        frequency="weekly",
        confidence="high"
    )
    db_session.add(protocol)
    db_session.commit()

    assert protocol.id is not None
    assert protocol.dose == "5mg"


def test_create_side_effect(db_session):
    """Test creating side effect"""
    effect = SideEffect(
        effect="Nausea",
        severity="mild",
        frequency=45,
        sources=["tweet_123", "paper_456"]
    )
    db_session.add(effect)
    db_session.commit()

    assert effect.id is not None
    assert effect.frequency == 45
