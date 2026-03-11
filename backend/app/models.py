"""
SQLAlchemy database models
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, JSON, Boolean
from sqlalchemy.sql import func
from app.database import Base


class Paper(Base):
    """Research papers from PubMed"""
    __tablename__ = "papers"

    id = Column(Integer, primary_key=True, index=True)
    pmid = Column(String, unique=True, index=True, nullable=False)
    title = Column(Text, nullable=False)
    authors = Column(JSON)  # List of authors
    journal = Column(String)
    publication_date = Column(String)
    abstract = Column(Text)
    keywords = Column(JSON)  # List of keywords
    mesh_terms = Column(JSON)  # List of MeSH terms
    doi = Column(String)
    pubmed_url = Column(String)
    scraped_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())


class ClinicalTrial(Base):
    """Clinical trials from ClinicalTrials.gov"""
    __tablename__ = "clinical_trials"

    id = Column(Integer, primary_key=True, index=True)
    nct_id = Column(String, unique=True, index=True, nullable=False)
    brief_title = Column(Text, nullable=False)
    official_title = Column(Text)
    status = Column(String, index=True)
    sponsor = Column(String)
    phase = Column(String, index=True)
    start_date = Column(String)
    completion_date = Column(String)
    primary_completion_date = Column(String)
    enrollment = Column(String)
    brief_summary = Column(Text)
    detailed_description = Column(Text)
    conditions = Column(JSON)  # List of conditions
    interventions = Column(JSON)  # List of interventions
    intervention_types = Column(JSON)
    primary_outcomes = Column(JSON)
    secondary_outcomes = Column(JSON)
    study_type = Column(String)
    has_results = Column(String)
    trial_url = Column(String)
    scraped_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())


class Tweet(Base):
    """Tweets from X/Twitter"""
    __tablename__ = "tweets"

    id = Column(Integer, primary_key=True, index=True)
    tweet_id = Column(String, unique=True, index=True, nullable=False)
    text = Column(Text, nullable=False)
    author_username = Column(String, index=True)
    author_followers = Column(Integer)
    date = Column(DateTime, index=True)
    retweet_count = Column(Integer)
    like_count = Column(Integer)
    url = Column(String)
    source_query = Column(String)
    scraped_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())


class RedditPost(Base):
    """Reddit posts and comments"""
    __tablename__ = "reddit_posts"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(String, unique=True, index=True, nullable=False)
    post_type = Column(String)  # 'post' or 'comment'
    subreddit = Column(String, index=True)
    author = Column(String, index=True)
    author_karma = Column(Integer)
    title = Column(Text)  # For posts only
    text = Column(Text, nullable=False)
    score = Column(Integer)
    upvote_ratio = Column(Float)  # For posts only
    num_comments = Column(Integer)  # For posts only
    created_utc = Column(DateTime, index=True)
    url = Column(String)
    parent_post_id = Column(String)  # For comments
    search_term = Column(String)
    scraped_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())


class DosingProtocol(Base):
    """Extracted dosing protocols from all sources"""
    __tablename__ = "dosing_protocols"

    id = Column(Integer, primary_key=True, index=True)
    source_type = Column(String, index=True)  # 'paper', 'trial', 'tweet', 'reddit'
    source_id = Column(String)  # ID in source table
    compound = Column(String, index=True, default="Retatrutide")
    dose = Column(String)  # e.g., "5mg", "2.5-5mg"
    frequency = Column(String)  # e.g., "once weekly", "daily"
    duration = Column(String)  # e.g., "12 weeks", "ongoing"
    route = Column(String)  # e.g., "subcutaneous injection"
    context = Column(Text)  # Additional context
    confidence = Column(String)  # 'high', 'medium', 'low'
    extracted_at = Column(DateTime, server_default=func.now())


class SideEffect(Base):
    """Aggregated side effects from all sources"""
    __tablename__ = "side_effects"

    id = Column(Integer, primary_key=True, index=True)
    effect = Column(String, index=True, nullable=False)
    severity = Column(String, index=True)  # 'mild', 'moderate', 'severe'
    frequency = Column(Integer)  # Number of mentions
    sources = Column(JSON)  # List of source references
    description = Column(Text)
    extracted_at = Column(DateTime, server_default=func.now())


class Mechanism(Base):
    """Mechanisms of action from research papers"""
    __tablename__ = "mechanisms"

    id = Column(Integer, primary_key=True, index=True)
    mechanism = Column(String, index=True, nullable=False)
    description = Column(Text, nullable=False)
    sources = Column(JSON)  # List of paper PMIDs
    confidence = Column(String)  # 'high', 'medium', 'low'
    extracted_at = Column(DateTime, server_default=func.now())


class Conflict(Base):
    """Identified conflicts between sources"""
    __tablename__ = "conflicts"

    id = Column(Integer, primary_key=True, index=True)
    topic = Column(String, index=True, nullable=False)
    source_a_type = Column(String)
    source_a_id = Column(String)
    source_a_claim = Column(Text)
    source_b_type = Column(String)
    source_b_id = Column(String)
    source_b_claim = Column(Text)
    description = Column(Text)
    resolution = Column(Text)  # AI-generated resolution
    extracted_at = Column(DateTime, server_default=func.now())
