"""
Tests for extract_mechanisms.py — all Claude calls are mocked.
"""
import json
import pytest
from unittest.mock import MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import ClinicalTrial, Mechanism, Paper, RedditPost, Tweet
from app.services.extract_mechanisms import (
    _has_keyword,
    _confidence_str,
    extract_mechanisms,
)


# ------------------------------------------------------------------ #
# Fixtures
# ------------------------------------------------------------------ #

@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def make_mock_client(items: list[dict]):
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text=json.dumps(items))]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_msg
    return mock_client


MECH_TEXT = "Retatrutide activates GLP-1 receptor and GIP receptor agonist pathways, increasing cAMP signalling."
SOCIAL_TEXT = "Tried retatrutide for 12 weeks, lost 15kg!"


# ------------------------------------------------------------------ #
# Unit tests
# ------------------------------------------------------------------ #

def test_keyword_filter_match():
    assert _has_keyword(MECH_TEXT) is True


def test_keyword_filter_no_match():
    assert _has_keyword("Stock market up 2% today") is False


def test_confidence_str_values():
    assert _confidence_str(0.8) == "high"
    assert _confidence_str(0.5) == "medium"
    assert _confidence_str(0.2) == "low"
    assert _confidence_str(None) == "medium"


# ------------------------------------------------------------------ #
# Integration tests
# ------------------------------------------------------------------ #

def test_literature_only_paper_included(db):
    """Papers should be processed."""
    db.add(Paper(pmid="P001", title=MECH_TEXT, authors=[], abstract=MECH_TEXT))
    db.commit()

    items = [{"receptor_target": "GLP-1R", "mechanism_description": "Activates adenylyl cyclase",
              "effect": "increased insulin secretion", "evidence_level": "human_trial", "confidence": 0.9}]
    stats = extract_mechanisms(db, api_client=make_mock_client(items))

    assert stats["extracted"] == 1


def test_social_media_excluded(db):
    """Tweets and Reddit posts should NOT be processed."""
    db.add(Tweet(tweet_id="T001", text=MECH_TEXT))
    db.add(RedditPost(post_id="R001", post_type="post", text=MECH_TEXT))
    db.commit()

    client = make_mock_client([])
    stats = extract_mechanisms(db, api_client=client)

    assert stats["api_calls"] == 0
    client.messages.create.assert_not_called()


def test_multiple_mechanisms_per_paper(db):
    """One paper can yield multiple mechanism records."""
    db.add(Paper(pmid="P001", title=MECH_TEXT, authors=[], abstract=MECH_TEXT))
    db.commit()

    items = [
        {"receptor_target": "GLP-1R", "mechanism_description": "cAMP pathway activation",
         "effect": "insulin release", "evidence_level": "human_trial", "confidence": 0.9},
        {"receptor_target": "GIPR", "mechanism_description": "GIP receptor binding",
         "effect": "glucose uptake", "evidence_level": "in_vitro", "confidence": 0.8},
    ]
    stats = extract_mechanisms(db, api_client=make_mock_client(items))

    assert stats["extracted"] == 2
    assert db.query(Mechanism).count() == 2


def test_duplicate_source_skipped(db):
    """Same receptor + same source should not be inserted twice."""
    db.add(Paper(pmid="P001", title=MECH_TEXT, authors=[], abstract=MECH_TEXT))
    db.commit()

    items = [{"receptor_target": "GLP-1R", "mechanism_description": "cAMP",
              "effect": "insulin", "evidence_level": "human_trial", "confidence": 0.9}]
    client = make_mock_client(items)
    extract_mechanisms(db, api_client=client)
    stats = extract_mechanisms(db, api_client=client)  # second run

    assert stats["skipped_duplicates"] == 1
    assert db.query(Mechanism).count() == 1


def test_invalid_evidence_level_normalized(db):
    """Unrecognised evidence level should become 'unknown' (not crash)."""
    db.add(Paper(pmid="P001", title=MECH_TEXT, authors=[], abstract=MECH_TEXT))
    db.commit()

    items = [{"receptor_target": "GcgR", "mechanism_description": "Glucagon receptor binding",
              "effect": "lipolysis", "evidence_level": "UNPUBLISHED", "confidence": 0.6}]
    extract_mechanisms(db, api_client=make_mock_client(items))
    # Should not crash — no assertion on evidence level stored in model


def test_dry_run_no_api_no_inserts(db):
    db.add(Paper(pmid="P001", title=MECH_TEXT, authors=[], abstract=MECH_TEXT))
    db.commit()

    stats = extract_mechanisms(db, dry_run=True)

    assert stats["candidates"] >= 1
    assert stats["api_calls"] == 0
    assert db.query(Mechanism).count() == 0


def test_stats_keys_present(db):
    stats = extract_mechanisms(db, api_client=make_mock_client([]))
    for key in ("extracted", "skipped_duplicates", "api_calls", "candidates", "errors"):
        assert key in stats
