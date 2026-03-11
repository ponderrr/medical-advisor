"""
GET endpoints for synthesis tables (dosing, side-effects, mechanisms, conflicts, summary)
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.models import (
    ClinicalTrial, Conflict, DosingProtocol, Mechanism, Paper, SideEffect
)
from app.schemas import (
    ConflictResponse,
    ConflictBreakdown,
    DataFreshness,
    DosingProtocolResponse,
    MechanismResponse,
    ReceptorCoverage,
    SideEffectResponse,
    SynthesisSummaryResponse,
    TopSideEffect,
)

router = APIRouter(tags=["synthesis"])

# Confidence string → float equivalent (for min_confidence filter)
_CONF_RANK = {"low": 0.1, "medium": 0.5, "high": 0.9}


def _confidence_filter(q, min_confidence: float):
    if min_confidence >= 0.7:
        return q.filter(DosingProtocol.confidence == "high")
    if min_confidence >= 0.4:
        return q.filter(DosingProtocol.confidence.in_(["high", "medium"]))
    return q


@router.get("/dosing", response_model=List[DosingProtocolResponse])
async def get_dosing(
    source_type: Optional[str] = Query(None, description="Filter by source: paper, trial, tweet, reddit"),
    min_confidence: float = Query(0.0, ge=0.0, le=1.0, description="Minimum confidence threshold"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Get dosing protocols with optional source_type and confidence filters."""
    q = db.query(DosingProtocol)
    if source_type:
        q = q.filter(DosingProtocol.source_type == source_type)
    q = _confidence_filter(q, min_confidence)
    return q.offset(skip).limit(limit).all()


@router.get("/side-effects", response_model=List[SideEffectResponse])
async def get_side_effects(
    severity: Optional[str] = Query(None, description="Filter by severity: mild, moderate, severe, unknown"),
    min_frequency: Optional[int] = Query(None, ge=1, description="Minimum mention count"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Get side effects with optional severity and frequency filters."""
    q = db.query(SideEffect)
    if severity:
        q = q.filter(SideEffect.severity == severity)
    if min_frequency is not None:
        q = q.filter(SideEffect.frequency >= min_frequency)
    return q.order_by(SideEffect.frequency.desc()).offset(skip).limit(limit).all()


@router.get("/mechanisms", response_model=List[MechanismResponse])
async def get_mechanisms(
    receptor: Optional[str] = Query(None, description="Partial match on receptor name, e.g. GLP"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Get mechanisms with optional receptor partial-match filter."""
    q = db.query(Mechanism)
    if receptor:
        q = q.filter(Mechanism.mechanism.ilike(f"%{receptor}%"))
    return q.offset(skip).limit(limit).all()


@router.get("/conflicts", response_model=List[ConflictResponse])
async def get_conflicts(
    conflict_type: Optional[str] = Query(None, description="Filter by topic/conflict type"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Get conflicts with optional conflict_type filter."""
    q = db.query(Conflict)
    if conflict_type:
        q = q.filter(Conflict.topic.ilike(f"%{conflict_type}%"))
    return q.offset(skip).limit(limit).all()


@router.get("/summary", response_model=SynthesisSummaryResponse)
async def get_summary(db: Session = Depends(get_db)):
    """Aggregated synthesis summary for the dashboard."""
    # Top side effects
    top_effects = (
        db.query(SideEffect)
        .order_by(SideEffect.frequency.desc())
        .limit(10)
        .all()
    )
    top_side_effects = [
        TopSideEffect(name=e.effect, frequency=e.frequency, max_severity=e.severity)
        for e in top_effects
    ]

    # Receptor coverage
    mechanisms = db.query(Mechanism).all()
    receptor_coverage = [
        ReceptorCoverage(receptor=m.mechanism, count=len(m.sources or []))
        for m in mechanisms
    ]

    # Conflict breakdown — we don't have a severity column, so return zeros
    conflict_breakdown = ConflictBreakdown(minor=0, major=0, critical=0)

    # Data freshness from Paper table
    oldest = db.query(func.min(Paper.created_at)).scalar()
    newest = db.query(func.max(Paper.created_at)).scalar()
    scrape_count = db.query(Paper).count()

    data_freshness = DataFreshness(
        oldest_paper=oldest,
        newest_paper=newest,
        scrape_count=scrape_count,
    )

    return SynthesisSummaryResponse(
        total_dosing_protocols=db.query(DosingProtocol).count(),
        total_side_effects=db.query(SideEffect).count(),
        total_mechanisms=db.query(Mechanism).count(),
        total_conflicts=db.query(Conflict).count(),
        top_side_effects=top_side_effects,
        receptor_coverage=receptor_coverage,
        conflict_breakdown=conflict_breakdown,
        data_freshness=data_freshness,
    )
