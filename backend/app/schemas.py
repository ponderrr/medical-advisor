"""
Pydantic schemas for API request/response validation
"""
from pydantic import BaseModel, ConfigDict, Field
from typing import Any, List, Optional
from datetime import datetime


# ── Raw data responses ────────────────────────────────────────────────────────

class PaperBase(BaseModel):
    pmid: str
    title: str
    authors: List[str]
    journal: Optional[str] = None
    publication_date: Optional[str] = None
    abstract: Optional[str] = None
    keywords: Optional[List[str]] = None
    mesh_terms: Optional[List[str]] = None
    doi: Optional[str] = None
    pubmed_url: Optional[str] = None


class PaperResponse(PaperBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class TrialBase(BaseModel):
    nct_id: str
    brief_title: str
    status: Optional[str] = None
    phase: Optional[str] = None
    sponsor: Optional[str] = None


class TrialResponse(TrialBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class TweetBase(BaseModel):
    tweet_id: str
    text: str
    author_username: Optional[str] = None
    date: Optional[datetime] = None


class TweetResponse(TweetBase):
    id: int
    like_count: Optional[int] = None
    retweet_count: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)


# ── Synthesis responses ───────────────────────────────────────────────────────

class DosingProtocolResponse(BaseModel):
    id: int
    source_type: str
    source_id: Optional[str] = None
    compound: Optional[str] = None
    dose: Optional[str] = None
    frequency: Optional[str] = None
    duration: Optional[str] = None
    route: Optional[str] = None
    context: Optional[str] = None
    confidence: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class SideEffectResponse(BaseModel):
    id: int
    effect: str
    severity: Optional[str] = None
    frequency: int
    sources: Optional[List[str]] = None
    description: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class MechanismResponse(BaseModel):
    id: int
    mechanism: str
    description: str
    sources: Optional[List[str]] = None
    confidence: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class ConflictResponse(BaseModel):
    id: int
    topic: str
    source_a_type: Optional[str] = None
    source_a_id: Optional[str] = None
    source_a_claim: Optional[str] = None
    source_b_type: Optional[str] = None
    source_b_id: Optional[str] = None
    source_b_claim: Optional[str] = None
    description: Optional[str] = None
    resolution: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


# ── Summary / dashboard ───────────────────────────────────────────────────────

class StatsResponse(BaseModel):
    total_papers: int
    total_trials: int
    total_tweets: int
    total_reddit_posts: int
    total_dosing_protocols: int
    total_side_effects: int


class TopSideEffect(BaseModel):
    name: str
    frequency: int
    max_severity: Optional[str] = None


class ReceptorCoverage(BaseModel):
    receptor: str
    count: int


class ConflictBreakdown(BaseModel):
    minor: int
    major: int
    critical: int


class DataFreshness(BaseModel):
    oldest_paper: Optional[datetime] = None
    newest_paper: Optional[datetime] = None
    scrape_count: int


class SynthesisSummaryResponse(BaseModel):
    total_dosing_protocols: int
    total_side_effects: int
    total_mechanisms: int
    total_conflicts: int
    top_side_effects: List[TopSideEffect]
    receptor_coverage: List[ReceptorCoverage]
    conflict_breakdown: ConflictBreakdown
    data_freshness: DataFreshness


# ── Query ─────────────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    question: str = Field(..., min_length=10, max_length=500)
    max_context_rows: int = Field(default=20, ge=1, le=100)


class QueryResponse(BaseModel):
    question: str
    answer: str
    sources_used: List[str]
    confidence: float
    domains_covered: List[str]
    context_row_count: int
    disclaimer: str


# ── Health / Meta ─────────────────────────────────────────────────────────────

class TableCounts(BaseModel):
    papers: int
    trials: int
    tweets: int
    reddit: int
    dosing: int
    side_effects: int
    mechanisms: int
    conflicts: int


class HealthResponse(BaseModel):
    status: str
    db_connected: bool
    tables: TableCounts
    synthesis_ready: bool


class MetaResponse(BaseModel):
    compound: str
    aliases: List[str]
    receptor_targets: List[str]
    last_scrape: Optional[datetime]
    last_synthesis: Optional[datetime]
    version: str
