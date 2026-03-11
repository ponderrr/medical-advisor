"""
Tests for query_engine.py and POST /api/query endpoint — all Claude calls mocked.
"""
import json
import pytest
from unittest.mock import MagicMock, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.models import DosingProtocol, SideEffect, Mechanism
from app.routers.query import reset_rate_limit
from app.services.query_engine import (
    classify_domains,
    build_context,
    answer_query,
    DISCLAIMER,
)

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
def clean_state():
    """Reset DB tables, rate limiter, and re-assert DB override before each test."""
    app.dependency_overrides[get_db] = override_get_db
    reset_rate_limit()
    db = TestSession()
    for table in reversed(Base.metadata.sorted_tables):
        db.execute(table.delete())
    db.commit()
    db.close()


@pytest.fixture
def populated_db():
    db = TestSession()
    db.add(DosingProtocol(source_type="paper", source_id="P001", dose="4mg",
                          frequency="weekly", confidence="high"))
    db.add(SideEffect(effect="nausea", severity="mild", frequency=8,
                      sources=["paper:P001"]))
    db.add(Mechanism(mechanism="GLP-1R", description="cAMP pathway activation",
                     sources=["paper:P001"], confidence="high"))
    db.commit()
    db.close()


def make_mock_client(payload: dict):
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text=json.dumps(payload))]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_msg
    return mock_client


# ── classify_domains ──────────────────────────────────────────────────────────

def test_classify_dosing():
    domains = classify_domains("What is the recommended dose of retatrutide?")
    assert "dosing" in domains


def test_classify_side_effects():
    domains = classify_domains("What are the side effects and adverse events?")
    assert "side_effects" in domains


def test_classify_mechanisms():
    domains = classify_domains("How does retatrutide work at the receptor level?")
    assert "mechanisms" in domains


def test_classify_multi_domain():
    domains = classify_domains("What is the dose and what side effects should I expect?")
    assert "dosing" in domains
    assert "side_effects" in domains


def test_classify_general_fallback():
    domains = classify_domains("Tell me about retatrutide please")
    assert domains == ["general"]


# ── build_context ─────────────────────────────────────────────────────────────

def test_build_context_empty_db():
    db = TestSession()
    try:
        context, count = build_context(db, ["dosing", "side_effects"])
        assert isinstance(context, str)
        assert count == 0
    finally:
        db.close()


def test_build_context_with_data(populated_db):
    db = TestSession()
    try:
        context, count = build_context(db, ["dosing", "side_effects"])
        assert count > 0
        assert "4mg" in context
        assert "nausea" in context
    finally:
        db.close()


def test_build_context_multi_domain(populated_db):
    db = TestSession()
    try:
        context, count = build_context(db, ["dosing", "side_effects", "mechanisms"])
        assert "DOSING PROTOCOLS" in context
        assert "SIDE EFFECTS" in context
        assert "MECHANISMS" in context
    finally:
        db.close()


# ── answer_query ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_answer_query_returns_structured_response(populated_db):
    payload = {
        "answer": "Retatrutide is typically dosed at 4mg weekly.",
        "sources_used": ["clinical trial data", "user reports"],
        "confidence": 0.85,
        "domains_covered": ["dosing"],
        "disclaimer": DISCLAIMER,
    }
    db = TestSession()
    try:
        result = await answer_query("What is the dose?", db, api_client=make_mock_client(payload))
        assert result["answer"] == payload["answer"]
        assert result["confidence"] == 0.85
        assert result["disclaimer"] == DISCLAIMER
        assert "context_row_count" in result
    finally:
        db.close()


@pytest.mark.asyncio
async def test_answer_query_disclaimer_always_present():
    """Disclaimer should be set even if Claude omits it."""
    payload = {
        "answer": "Some answer",
        "sources_used": [],
        "confidence": 0.5,
        "domains_covered": ["general"],
        "disclaimer": None,  # Claude omits it
    }
    db = TestSession()
    try:
        result = await answer_query("Tell me about it", db, api_client=make_mock_client(payload))
        assert result["disclaimer"] == DISCLAIMER
    finally:
        db.close()


@pytest.mark.asyncio
async def test_answer_query_malformed_json_raises():
    """Malformed JSON from Claude should raise ValueError."""
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text="NOT JSON AT ALL")]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_msg

    db = TestSession()
    try:
        with pytest.raises(ValueError, match="Could not parse"):
            await answer_query("What is the dose?", db, api_client=mock_client)
    finally:
        db.close()


# ── POST /api/query endpoint ──────────────────────────────────────────────────

def test_query_too_short_returns_422():
    response = client.post("/api/query", json={"question": "short"})
    assert response.status_code == 422


def test_query_too_long_returns_422():
    response = client.post("/api/query", json={"question": "x" * 501})
    assert response.status_code == 422


def test_rate_limit_allows_10_rejects_11th(monkeypatch):
    """After 10 requests, the 11th should return 429."""
    import os
    import app.services.query_engine as qe

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    payload = {
        "answer": "Test answer",
        "sources_used": [],
        "confidence": 0.7,
        "domains_covered": ["general"],
        "disclaimer": DISCLAIMER,
    }

    async def mock_answer(*args, **kwargs):
        return {
            "question": "test",
            "answer": "Test answer",
            "sources_used": [],
            "confidence": 0.7,
            "domains_covered": ["general"],
            "context_row_count": 0,
            "disclaimer": DISCLAIMER,
        }

    monkeypatch.setattr("app.routers.query.answer_query", mock_answer)

    question = "What are the side effects of retatrutide therapy?"
    for i in range(10):
        response = client.post("/api/query", json={"question": question})
        assert response.status_code != 429, f"Request {i+1} was rejected early"

    response = client.post("/api/query", json={"question": question})
    assert response.status_code == 429
