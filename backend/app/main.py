"""
FastAPI application entry point
"""
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import init_db, get_db
from app.routers import data, synthesis, query as query_router

app = FastAPI(
    title="Medical Advisor API",
    description="Research data aggregation and synthesis for medical compounds",
    version="1.0.0"
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(data.router)
app.include_router(synthesis.router, prefix="/api/synthesis", tags=["synthesis"])
app.include_router(query_router.router, prefix="/api", tags=["query"])


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    init_db()


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Medical Advisor API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Simple health check"""
    return {"status": "healthy"}


@app.get("/api/health")
async def api_health(db: Session = Depends(get_db)):
    """Detailed health check with table counts and synthesis readiness."""
    from app.models import (
        ClinicalTrial, Conflict, DosingProtocol, Mechanism,
        Paper, RedditPost, SideEffect, Tweet
    )
    try:
        counts = {
            "papers": db.query(Paper).count(),
            "trials": db.query(ClinicalTrial).count(),
            "tweets": db.query(Tweet).count(),
            "reddit": db.query(RedditPost).count(),
            "dosing": db.query(DosingProtocol).count(),
            "side_effects": db.query(SideEffect).count(),
            "mechanisms": db.query(Mechanism).count(),
            "conflicts": db.query(Conflict).count(),
        }
        db_connected = True
    except Exception:
        counts = {k: 0 for k in ["papers", "trials", "tweets", "reddit",
                                  "dosing", "side_effects", "mechanisms", "conflicts"]}
        db_connected = False

    synthesis_ready = all(
        counts[k] >= 1 for k in ["dosing", "side_effects", "mechanisms", "conflicts"]
    )

    return {
        "status": "ok",
        "db_connected": db_connected,
        "tables": counts,
        "synthesis_ready": synthesis_ready,
    }


@app.get("/api/meta")
async def api_meta(db: Session = Depends(get_db)):
    """Compound metadata and pipeline timestamps."""
    from app.models import (
        ClinicalTrial, Conflict, DosingProtocol, Mechanism,
        Paper, RedditPost, SideEffect, Tweet
    )
    # last_scrape: max created_at across raw tables
    raw_maxes = [
        db.query(func.max(Paper.created_at)).scalar(),
        db.query(func.max(ClinicalTrial.created_at)).scalar(),
        db.query(func.max(Tweet.created_at)).scalar(),
        db.query(func.max(RedditPost.created_at)).scalar(),
    ]
    raw_maxes_filtered = [t for t in raw_maxes if t is not None]
    last_scrape = max(raw_maxes_filtered) if raw_maxes_filtered else None

    # last_synthesis: max extracted_at across synthesis tables
    synth_maxes = [
        db.query(func.max(DosingProtocol.extracted_at)).scalar(),
        db.query(func.max(SideEffect.extracted_at)).scalar(),
        db.query(func.max(Mechanism.extracted_at)).scalar(),
        db.query(func.max(Conflict.extracted_at)).scalar(),
    ]
    synth_maxes_filtered = [t for t in synth_maxes if t is not None]
    last_synthesis = max(synth_maxes_filtered) if synth_maxes_filtered else None

    return {
        "compound": "Retatrutide",
        "aliases": ["GLP-3 RT", "LY3437943"],
        "receptor_targets": ["GLP-1R", "GIPR", "GcgR"],
        "last_scrape": last_scrape,
        "last_synthesis": last_synthesis,
        "version": "0.1.0",
    }
