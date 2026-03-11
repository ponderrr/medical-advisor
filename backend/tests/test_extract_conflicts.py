"""
Tests for extract_conflicts.py — all Claude calls are mocked.
"""
import json
import pytest
from unittest.mock import MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import Conflict, DosingProtocol, SideEffect
from app.services.extract_conflicts import (
    _build_dosing_summary,
    _build_side_effect_summary,
    detect_conflicts,
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


# ------------------------------------------------------------------ #
# Unit tests
# ------------------------------------------------------------------ #

def test_dosing_summary_empty(db):
    summary = _build_dosing_summary(db)
    assert "No dosing data" in summary


def test_dosing_summary_with_data(db):
    db.add(DosingProtocol(source_type="paper", source_id="P001", dose="4mg", frequency="weekly"))
    db.commit()
    summary = _build_dosing_summary(db)
    assert "P001" in summary
    assert "4mg" in summary


def test_side_effect_summary_empty(db):
    summary = _build_side_effect_summary(db)
    assert "No side effect" in summary


def test_side_effect_summary_with_data(db):
    db.add(SideEffect(effect="nausea", severity="mild", frequency=5, sources=["paper:P001"]))
    db.commit()
    summary = _build_side_effect_summary(db)
    assert "nausea" in summary
    assert "mild" in summary


# ------------------------------------------------------------------ #
# Integration tests
# ------------------------------------------------------------------ #

def test_empty_tables_returns_empty_no_crash(db):
    """No data in synthesis tables → no API call, empty stats."""
    client = make_mock_client([])
    stats = detect_conflicts(db, api_client=client)

    assert stats["detected"] == 0
    client.messages.create.assert_not_called()


def test_conflicts_inserted(db):
    db.add(DosingProtocol(source_type="paper", source_id="P001", dose="4mg", frequency="weekly"))
    db.add(SideEffect(effect="nausea", severity="mild", frequency=3, sources=["paper:P001"]))
    db.commit()

    items = [
        {
            "conflict_type": "dosing",
            "description": "Source A says 4mg, source B says 8mg weekly",
            "source_a": "paper:P001",
            "source_b": "reddit:R001",
            "resolution": None,
            "severity": "major",
        }
    ]
    stats = detect_conflicts(db, api_client=make_mock_client(items))

    assert stats["detected"] == 1
    assert db.query(Conflict).count() == 1
    conflict = db.query(Conflict).first()
    assert conflict.topic == "dosing"
    assert conflict.source_a_id == "paper:P001"


def test_duplicate_conflict_skipped(db):
    db.add(DosingProtocol(source_type="paper", source_id="P001", dose="4mg", frequency="weekly"))
    db.add(SideEffect(effect="nausea", severity="mild", frequency=3, sources=["paper:P001"]))
    db.commit()

    items = [
        {"conflict_type": "dosing", "description": "Conflict X",
         "source_a": "paper:P001", "source_b": "reddit:R001",
         "resolution": None, "severity": "minor"},
    ]
    client = make_mock_client(items)
    detect_conflicts(db, api_client=client)
    stats = detect_conflicts(db, api_client=client)  # second run

    assert stats["skipped_duplicates"] == 1
    assert db.query(Conflict).count() == 1


def test_dry_run_no_api(db):
    db.add(DosingProtocol(source_type="paper", source_id="P001", dose="4mg", frequency="weekly"))
    db.add(SideEffect(effect="nausea", severity="mild", frequency=3, sources=["paper:P001"]))
    db.commit()

    client = make_mock_client([{"conflict_type": "dosing", "description": "X",
                                "source_a": "A", "source_b": "B", "resolution": None, "severity": "minor"}])
    stats = detect_conflicts(db, api_client=client, dry_run=True)

    assert stats["api_calls"] == 0
    client.messages.create.assert_not_called()
    assert db.query(Conflict).count() == 0


def test_stats_keys_present(db):
    stats = detect_conflicts(db, api_client=make_mock_client([]))
    for key in ("detected", "skipped_duplicates", "api_calls", "errors"):
        assert key in stats
