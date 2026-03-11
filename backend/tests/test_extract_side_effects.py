"""
Tests for extract_side_effects.py — all Claude calls are mocked.
"""
import json
import pytest
from unittest.mock import MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import Paper, Tweet, RedditPost, SideEffect, ClinicalTrial
from app.services.extract_side_effects import (
    _has_keyword,
    _normalize_effect,
    _upsert_effect,
    extract_side_effects,
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


SE_TEXT = "Patient reported nausea and vomiting after injection site reaction."
CLEAN_TEXT = "The stock market fell 2% today due to geopolitical tensions."


# ------------------------------------------------------------------ #
# Unit tests
# ------------------------------------------------------------------ #

def test_keyword_filter_matches():
    assert _has_keyword(SE_TEXT) is True


def test_keyword_filter_no_match():
    assert _has_keyword(CLEAN_TEXT) is False


def test_normalize_effect():
    assert _normalize_effect("  Nausea  ") == "nausea"
    assert _normalize_effect("VOMITING") == "vomiting"
    assert _normalize_effect("injection site reaction") == "injection site reaction"


def test_upsert_new_effect(db):
    result = _upsert_effect(db, "Nausea", "mild", "paper:P001", "felt sick")
    assert result is True
    effect = db.query(SideEffect).filter(SideEffect.effect == "nausea").first()
    assert effect is not None
    assert effect.frequency == 1
    assert "paper:P001" in effect.sources


def test_upsert_increments_existing(db):
    _upsert_effect(db, "Nausea", "mild", "paper:P001", "first mention")
    _upsert_effect(db, "Nausea", "moderate", "paper:P002", "second mention")

    effects = db.query(SideEffect).filter(SideEffect.effect == "nausea").all()
    assert len(effects) == 1
    assert effects[0].frequency == 2
    assert effects[0].severity == "moderate"  # upgraded from mild


def test_upsert_skips_duplicate_source(db):
    _upsert_effect(db, "Nausea", "mild", "paper:P001", "first")
    result = _upsert_effect(db, "Nausea", "mild", "paper:P001", "duplicate")
    assert result is False
    assert db.query(SideEffect).first().frequency == 1


def test_severity_validation(db):
    _upsert_effect(db, "Headache", "EXTREME_PAIN", "paper:P001", None)
    effect = db.query(SideEffect).filter(SideEffect.effect == "headache").first()
    assert effect.severity == "unknown"


# ------------------------------------------------------------------ #
# Integration tests
# ------------------------------------------------------------------ #

def test_extract_creates_multiple_effects(db):
    db.add(Paper(pmid="P001", title="Study", authors=[], abstract=SE_TEXT))
    db.commit()

    items = [
        {"effect_name": "Nausea", "severity": "mild", "context_quote": "nausea", "confidence": 0.9},
        {"effect_name": "Vomiting", "severity": "moderate", "context_quote": "vomiting", "confidence": 0.8},
    ]
    stats = extract_side_effects(db, api_client=make_mock_client(items))

    assert stats["extracted"] == 2
    assert db.query(SideEffect).count() == 2


def test_extract_empty_array_no_crash(db):
    db.add(Paper(pmid="P001", title="Study", authors=[], abstract=SE_TEXT))
    db.commit()

    stats = extract_side_effects(db, api_client=make_mock_client([]))

    assert stats["extracted"] == 0
    assert stats["errors"] == []
    assert db.query(SideEffect).count() == 0


def test_keyword_gates_api_calls(db):
    """Text without keywords should not trigger API calls."""
    db.add(Paper(pmid="P001", title="Finance", authors=[], abstract=CLEAN_TEXT))
    db.commit()

    client = make_mock_client([])
    stats = extract_side_effects(db, api_client=client)

    assert stats["api_calls"] == 0
    client.messages.create.assert_not_called()


def test_dry_run_no_api_no_inserts(db):
    db.add(Paper(pmid="P001", title="Study", authors=[], abstract=SE_TEXT))
    db.commit()

    stats = extract_side_effects(db, dry_run=True)

    assert stats["candidates"] >= 1
    assert stats["api_calls"] == 0
    assert db.query(SideEffect).count() == 0


def test_stats_keys_present(db):
    stats = extract_side_effects(db, api_client=make_mock_client([]))
    for key in ("extracted", "skipped", "api_calls", "candidates", "errors"):
        assert key in stats
