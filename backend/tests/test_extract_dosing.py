"""
Tests for extract_dosing.py — all Claude calls are mocked.
"""
import json
import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import DosingProtocol, Paper, Tweet, RedditPost
from app.services.extract_dosing import (
    _pattern_hits,
    _parse_claude_json,
    _confidence_str,
    extract_dosing_protocols,
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


def make_mock_client(payload: dict | None):
    """Return a mock anthropic.Anthropic that returns payload as JSON."""
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text=json.dumps(payload) if payload else "not-json{{{")]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_msg
    return mock_client


DOSING_TEXT = "Retatrutide 4 mg subcutaneous injection once weekly for 24 weeks"
NON_DOSING_TEXT = "Patient reported feeling better after the visit to the doctor."


# ------------------------------------------------------------------ #
# Unit tests
# ------------------------------------------------------------------ #

def test_pattern_hits_strong():
    """Text with dose + freq + route hits all 3 patterns."""
    assert _pattern_hits(DOSING_TEXT) == 3


def test_pattern_hits_weak():
    """Non-dosing text hits 0 patterns."""
    assert _pattern_hits(NON_DOSING_TEXT) == 0


def test_pattern_hits_partial():
    """Text with only dose hits 1 pattern."""
    assert _pattern_hits("Administered 5mg to the patient") == 1


def test_parse_claude_json_valid():
    payload = {"dose_amount": "4", "dose_unit": "mg", "frequency": "weekly"}
    assert _parse_claude_json(json.dumps(payload)) == payload


def test_parse_claude_json_with_fences():
    payload = {"dose_amount": "5", "dose_unit": "mg"}
    raw = f"```json\n{json.dumps(payload)}\n```"
    assert _parse_claude_json(raw) == payload


def test_parse_claude_json_invalid():
    assert _parse_claude_json("not valid json") is None


def test_confidence_str():
    assert _confidence_str(0.9) == "high"
    assert _confidence_str(0.5) == "medium"
    assert _confidence_str(0.1) == "low"
    assert _confidence_str(None) == "medium"
    assert _confidence_str("bad") == "medium"


# ------------------------------------------------------------------ #
# Integration tests (with mocked Claude)
# ------------------------------------------------------------------ #

def test_extract_inserts_record(db):
    db.add(Paper(pmid="P001", title=DOSING_TEXT, authors=[], abstract=DOSING_TEXT))
    db.commit()

    payload = {"dose_amount": "4", "dose_unit": "mg", "frequency": "once weekly",
               "route": "subcutaneous", "titration_notes": None, "confidence": 0.9, "raw_passage": DOSING_TEXT}
    stats = extract_dosing_protocols(db, api_client=make_mock_client(payload))

    assert stats["extracted"] == 1
    assert stats["api_calls"] == 1
    protocol = db.query(DosingProtocol).first()
    assert protocol is not None
    assert protocol.dose == "4mg"
    assert protocol.source_type == "paper"


def test_extract_skips_duplicate(db):
    db.add(Paper(pmid="P001", title=DOSING_TEXT, authors=[], abstract=DOSING_TEXT))
    db.commit()

    payload = {"dose_amount": "4", "dose_unit": "mg", "frequency": "weekly",
               "route": "SC", "titration_notes": None, "confidence": 0.8, "raw_passage": ""}
    client = make_mock_client(payload)
    extract_dosing_protocols(db, api_client=client)
    stats = extract_dosing_protocols(db, api_client=client)  # second run

    assert stats["skipped_duplicates"] == 1
    assert db.query(DosingProtocol).count() == 1


def test_extract_handles_malformed_json(db):
    db.add(Paper(pmid="P002", title=DOSING_TEXT, authors=[], abstract=DOSING_TEXT))
    db.commit()

    client = make_mock_client(None)  # returns invalid JSON
    stats = extract_dosing_protocols(db, api_client=client)

    assert stats["extracted"] == 0
    assert stats["api_calls"] == 1
    assert db.query(DosingProtocol).count() == 0


def test_extract_null_fields_no_crash(db):
    """Claude returning all nulls should insert a record without crashing."""
    db.add(Paper(pmid="P003", title=DOSING_TEXT, authors=[], abstract=DOSING_TEXT))
    db.commit()

    payload = {"dose_amount": None, "dose_unit": None, "frequency": None,
               "route": None, "titration_notes": None, "confidence": None, "raw_passage": None}
    stats = extract_dosing_protocols(db, api_client=make_mock_client(payload))

    assert stats["extracted"] == 1
    protocol = db.query(DosingProtocol).first()
    assert protocol.dose is None
    assert protocol.frequency is None


def test_dry_run_no_inserts(db):
    db.add(Paper(pmid="P004", title=DOSING_TEXT, authors=[], abstract=DOSING_TEXT))
    db.commit()

    stats = extract_dosing_protocols(db, dry_run=True)

    assert stats["candidates"] >= 1
    assert stats["api_calls"] == 0
    assert db.query(DosingProtocol).count() == 0


def test_stats_keys_present(db):
    stats = extract_dosing_protocols(db, api_client=make_mock_client({}))
    for key in ("extracted", "skipped_duplicates", "api_calls", "candidates", "errors"):
        assert key in stats


def test_tweet_candidate_extracted(db):
    db.add(Tweet(tweet_id="T001", text=DOSING_TEXT))
    db.commit()

    payload = {"dose_amount": "4", "dose_unit": "mg", "frequency": "weekly",
               "route": "SC", "titration_notes": None, "confidence": 0.7, "raw_passage": ""}
    stats = extract_dosing_protocols(db, api_client=make_mock_client(payload))

    assert stats["extracted"] == 1
    assert db.query(DosingProtocol).first().source_type == "tweet"
