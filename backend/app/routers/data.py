"""
API endpoints for querying research data
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.models import Paper, ClinicalTrial, Tweet, RedditPost, DosingProtocol, SideEffect
from app.schemas import (
    PaperResponse,
    TrialResponse,
    TweetResponse,
    DosingProtocolResponse,
    SideEffectResponse,
    StatsResponse,
)

router = APIRouter(prefix="/api", tags=["data"])


@router.get("/papers", response_model=List[PaperResponse])
async def get_papers(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Get research papers with pagination."""
    return db.query(Paper).offset(skip).limit(limit).all()


@router.get("/papers/{pmid}", response_model=PaperResponse)
async def get_paper(pmid: str, db: Session = Depends(get_db)):
    """Get a single paper by PMID."""
    from fastapi import HTTPException
    paper = db.query(Paper).filter(Paper.pmid == pmid).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    return paper


@router.get("/trials", response_model=List[TrialResponse])
async def get_trials(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    phase: Optional[str] = Query(None, description="Filter by phase, e.g. 'Phase 3'"),
    status: Optional[str] = Query(None, description="Filter by status, e.g. 'Recruiting'"),
    db: Session = Depends(get_db),
):
    """Get clinical trials with optional filters and pagination."""
    q = db.query(ClinicalTrial)
    if phase:
        q = q.filter(ClinicalTrial.phase.ilike(f"%{phase}%"))
    if status:
        q = q.filter(ClinicalTrial.status.ilike(f"%{status}%"))
    return q.offset(skip).limit(limit).all()


@router.get("/trials/{nct_id}", response_model=TrialResponse)
async def get_trial(nct_id: str, db: Session = Depends(get_db)):
    """Get a single clinical trial by NCT ID."""
    from fastapi import HTTPException
    trial = db.query(ClinicalTrial).filter(ClinicalTrial.nct_id == nct_id).first()
    if not trial:
        raise HTTPException(status_code=404, detail="Trial not found")
    return trial


@router.get("/tweets", response_model=List[TweetResponse])
async def get_tweets(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    author: Optional[str] = Query(None, description="Filter by author username"),
    db: Session = Depends(get_db),
):
    """Get tweets with optional author filter and pagination."""
    q = db.query(Tweet)
    if author:
        q = q.filter(Tweet.author_username.ilike(f"%{author}%"))
    return q.offset(skip).limit(limit).all()


@router.get("/reddit", response_model=List[dict])
async def get_reddit(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    subreddit: Optional[str] = Query(None, description="Filter by subreddit"),
    post_type: Optional[str] = Query(None, description="Filter by type: 'post' or 'comment'"),
    db: Session = Depends(get_db),
):
    """Get Reddit posts/comments with optional filters and pagination."""
    q = db.query(RedditPost)
    if subreddit:
        q = q.filter(RedditPost.subreddit.ilike(f"%{subreddit}%"))
    if post_type:
        q = q.filter(RedditPost.post_type == post_type)
    posts = q.offset(skip).limit(limit).all()
    return [
        {
            "id": p.id,
            "post_id": p.post_id,
            "post_type": p.post_type,
            "subreddit": p.subreddit,
            "author": p.author,
            "title": p.title,
            "text": p.text,
            "score": p.score,
            "url": p.url,
            "created_utc": p.created_utc.isoformat() if p.created_utc else None,
        }
        for p in posts
    ]


@router.get("/dosing", response_model=List[DosingProtocolResponse])
async def get_dosing(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Get dosing protocols."""
    return db.query(DosingProtocol).offset(skip).limit(limit).all()


@router.get("/side-effects", response_model=List[SideEffectResponse])
async def get_side_effects(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Get side effects."""
    return db.query(SideEffect).offset(skip).limit(limit).all()


@router.get("/stats", response_model=StatsResponse)
async def get_stats(db: Session = Depends(get_db)):
    """Get dashboard statistics — counts for all data types."""
    return StatsResponse(
        total_papers=db.query(Paper).count(),
        total_trials=db.query(ClinicalTrial).count(),
        total_tweets=db.query(Tweet).count(),
        total_reddit_posts=db.query(RedditPost).count(),
        total_dosing_protocols=db.query(DosingProtocol).count(),
        total_side_effects=db.query(SideEffect).count(),
    )
