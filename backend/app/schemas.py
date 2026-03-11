"""
Pydantic schemas for API request/response validation
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


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

    class Config:
        from_attributes = True


class TrialBase(BaseModel):
    nct_id: str
    brief_title: str
    status: Optional[str] = None
    phase: Optional[str] = None
    sponsor: Optional[str] = None


class TrialResponse(TrialBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class TweetBase(BaseModel):
    tweet_id: str
    text: str
    author_username: Optional[str] = None
    date: Optional[datetime] = None


class TweetResponse(TweetBase):
    id: int
    like_count: Optional[int] = None
    retweet_count: Optional[int] = None

    class Config:
        from_attributes = True


class DosingProtocolResponse(BaseModel):
    id: int
    source_type: str
    dose: Optional[str] = None
    frequency: Optional[str] = None
    duration: Optional[str] = None
    route: Optional[str] = None
    confidence: Optional[str] = None

    class Config:
        from_attributes = True


class SideEffectResponse(BaseModel):
    id: int
    effect: str
    severity: Optional[str] = None
    frequency: int
    description: Optional[str] = None

    class Config:
        from_attributes = True


class StatsResponse(BaseModel):
    total_papers: int
    total_trials: int
    total_tweets: int
    total_reddit_posts: int
    total_dosing_protocols: int
    total_side_effects: int
