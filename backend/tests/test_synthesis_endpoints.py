"""
Tests for synthesis endpoints: /api/synthesis/*
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.models import Conflict, DosingProtocol, Mechanism, SideEffect

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
    app.dependency_overrides[get_db] = override_get_db
    db = TestSession()
    for table in reversed(Base.metadata.sorted_tables):
        db.execute(table.delete())
    db.commit()
    db.close()


@pytest.fixture
def synthesis_data():
    db = TestSession()
    db.add(DosingProtocol(source_type="paper", source_id="P001", dose="4mg",
                          frequency="weekly", route="subcutaneous", confidence="high"))
    db.add(DosingProtocol(source_type="reddit", source_id="R001", dose="8mg",
                          frequency="weekly", route="SC", confidence="medium"))
    db.add(DosingProtocol(source_type="tweet", source_id="T001", dose="2mg",
                          frequency="biweekly", confidence="low"))
    db.add(SideEffect(effect="nausea", severity="mild", frequency=12,
                      sources=["paper:P001", "reddit:R001"]))
    db.add(SideEffect(effect="vomiting", severity="moderate", frequency=5,
                      sources=["tweet:T001"]))
    db.add(SideEffect(effect="pancreatitis", severity="severe", frequency=2,
                      sources=["paper:P002"]))
    db.add(Mechanism(mechanism="GLP-1R", description="Activates GLP-1 receptor",
                     sources=["paper:P001"], confidence="high"))
    db.add(Mechanism(mechanism="GIPR", description="Activates GIP receptor",
                     sources=["paper:P001", "paper:P002"], confidence="medium"))
    db.add(Conflict(topic="dosing", source_a_id="paper:P001", source_b_id="reddit:R001",
                    description="Dosing discrepancy between sources"))
    db.commit()
    db.close()


# ── Dosing endpoints ──────────────────────────────────────────────────────────

def test_dosing_empty_returns_200():
    response = client.get("/api/synthesis/dosing")
    assert response.status_code == 200
    assert response.json() == []


def test_dosing_returns_records(synthesis_data):
    response = client.get("/api/synthesis/dosing")
    assert response.status_code == 200
    assert len(response.json()) == 3


def test_dosing_filter_source_type(synthesis_data):
    response = client.get("/api/synthesis/dosing?source_type=paper")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["source_type"] == "paper"


def test_dosing_filter_min_confidence_high(synthesis_data):
    response = client.get("/api/synthesis/dosing?min_confidence=0.7")
    assert response.status_code == 200
    data = response.json()
    assert all(d["confidence"] == "high" for d in data)


def test_dosing_filter_min_confidence_medium(synthesis_data):
    response = client.get("/api/synthesis/dosing?min_confidence=0.4")
    assert response.status_code == 200
    data = response.json()
    confidences = {d["confidence"] for d in data}
    assert "low" not in confidences
    assert len(data) == 2


# ── Side effects ──────────────────────────────────────────────────────────────

def test_side_effects_empty_returns_200():
    response = client.get("/api/synthesis/side-effects")
    assert response.status_code == 200
    assert response.json() == []


def test_side_effects_filter_severity(synthesis_data):
    response = client.get("/api/synthesis/side-effects?severity=severe")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["effect"] == "pancreatitis"


def test_side_effects_filter_min_frequency(synthesis_data):
    response = client.get("/api/synthesis/side-effects?min_frequency=10")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["effect"] == "nausea"


# ── Mechanisms ────────────────────────────────────────────────────────────────

def test_mechanisms_empty_returns_200():
    response = client.get("/api/synthesis/mechanisms")
    assert response.status_code == 200
    assert response.json() == []


def test_mechanisms_receptor_partial_match(synthesis_data):
    response = client.get("/api/synthesis/mechanisms?receptor=GLP")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["mechanism"] == "GLP-1R"


def test_mechanisms_receptor_matches_multiple(synthesis_data):
    """Partial match 'R' should return both GLP-1R and GIPR."""
    response = client.get("/api/synthesis/mechanisms?receptor=R")
    assert response.status_code == 200
    assert len(response.json()) == 2


# ── Conflicts ─────────────────────────────────────────────────────────────────

def test_conflicts_empty_returns_200():
    response = client.get("/api/synthesis/conflicts")
    assert response.status_code == 200
    assert response.json() == []


def test_conflicts_filter_type(synthesis_data):
    response = client.get("/api/synthesis/conflicts?conflict_type=dosing")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["topic"] == "dosing"


# ── Summary ───────────────────────────────────────────────────────────────────

def test_summary_empty_db_has_all_keys():
    response = client.get("/api/synthesis/summary")
    assert response.status_code == 200
    data = response.json()
    for key in ("total_dosing_protocols", "total_side_effects", "total_mechanisms",
                "total_conflicts", "top_side_effects", "receptor_coverage",
                "conflict_breakdown", "data_freshness"):
        assert key in data, f"Missing key: {key}"
    assert data["total_dosing_protocols"] == 0


def test_summary_with_data(synthesis_data):
    response = client.get("/api/synthesis/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["total_dosing_protocols"] == 3
    assert data["total_side_effects"] == 3
    assert data["total_mechanisms"] == 2
    assert data["total_conflicts"] == 1
    assert len(data["top_side_effects"]) <= 10
    assert data["top_side_effects"][0]["name"] == "nausea"  # highest frequency
