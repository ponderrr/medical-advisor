"""
Data loading service - loads JSON files from data/raw/ into SQLite
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Paper, ClinicalTrial, Tweet, RedditPost

logger = logging.getLogger(__name__)

# Project root relative to this file: backend/app/services/ -> ../../.. -> project root
DATA_DIR = Path(__file__).parent.parent.parent.parent / "data" / "raw"


def parse_datetime(value) -> datetime | None:
    """Parse a datetime from ISO string or Unix timestamp. Returns None on failure."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value, tz=timezone.utc).replace(tzinfo=None)
        except (OSError, OverflowError, ValueError):
            return None
    if isinstance(value, str):
        # Strip timezone info for SQLite compatibility
        for fmt in (
            "%Y-%m-%dT%H:%M:%S.%f+00:00",
            "%Y-%m-%dT%H:%M:%S+00:00",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S",
        ):
            try:
                return datetime.strptime(value[:26].rstrip("Z"), fmt.rstrip("+00:00").rstrip(".%f") if "%" not in fmt else fmt)
            except ValueError:
                continue
        # Fallback: let dateutil-style strip
        try:
            clean = value.replace("+00:00", "").replace("Z", "")
            return datetime.fromisoformat(clean)
        except ValueError:
            logger.warning("Could not parse datetime: %s", value)
            return None
    return None


class DataLoader:
    def __init__(self, db: Session, data_dir: Path = None):
        self.db = db
        self.data_dir = data_dir or DATA_DIR
        self.stats = {
            "papers_loaded": 0,
            "trials_loaded": 0,
            "tweets_loaded": 0,
            "reddit_loaded": 0,
            "errors": [],
        }

    def load_all(self):
        """Load all JSON files from data/raw/, dispatching by filename prefix."""
        if not self.data_dir.exists():
            logger.warning("Data directory not found: %s", self.data_dir)
            return self.stats

        json_files = sorted(self.data_dir.glob("*.json"))
        if not json_files:
            logger.info("No JSON files found in %s", self.data_dir)
            return self.stats

        for filepath in json_files:
            name = filepath.name
            logger.info("Processing: %s", name)
            if name.startswith("pubmed_papers"):
                self.load_papers(filepath)
            elif name.startswith("clinical_trials"):
                self.load_trials(filepath)
            elif name.startswith("x_tweets"):
                self.load_tweets(filepath)
            elif name.startswith("reddit_posts"):
                self.load_reddit(filepath)
            else:
                logger.debug("Skipping unrecognised file: %s", name)

        return self.stats

    # ------------------------------------------------------------------ #
    # Papers
    # ------------------------------------------------------------------ #
    def load_papers(self, filepath: Path):
        """Load PubMed papers from JSON file into DB."""
        records = self._read_json(filepath)
        if records is None:
            return

        loaded = 0
        for raw in records:
            try:
                paper = Paper(
                    pmid=raw["pmid"],
                    title=raw.get("title", ""),
                    authors=raw.get("authors", []),
                    journal=raw.get("journal"),
                    publication_date=raw.get("publication_date"),
                    abstract=raw.get("abstract"),
                    keywords=raw.get("keywords"),
                    mesh_terms=raw.get("mesh_terms"),
                    doi=raw.get("doi"),
                    pubmed_url=raw.get("pubmed_url"),
                    scraped_at=parse_datetime(raw.get("scraped_at")),
                )
                self.db.add(paper)
                self.db.flush()
                loaded += 1
            except IntegrityError:
                self.db.rollback()
                logger.debug("Duplicate paper pmid=%s, skipping", raw.get("pmid"))
            except Exception as exc:
                self.db.rollback()
                msg = f"Error loading paper pmid={raw.get('pmid')}: {exc}"
                logger.warning(msg)
                self.stats["errors"].append(msg)

        self.db.commit()
        self.stats["papers_loaded"] += loaded
        logger.info("Loaded %d papers from %s", loaded, filepath.name)

    # ------------------------------------------------------------------ #
    # Clinical Trials
    # ------------------------------------------------------------------ #
    def load_trials(self, filepath: Path):
        """Load clinical trials from JSON file into DB."""
        records = self._read_json(filepath)
        if records is None:
            return

        loaded = 0
        for raw in records:
            try:
                trial = ClinicalTrial(
                    nct_id=raw["nct_id"],
                    brief_title=raw.get("brief_title", ""),
                    official_title=raw.get("official_title"),
                    status=raw.get("status"),
                    sponsor=raw.get("sponsor"),
                    phase=raw.get("phase"),
                    start_date=raw.get("start_date"),
                    completion_date=raw.get("completion_date"),
                    primary_completion_date=raw.get("primary_completion_date"),
                    enrollment=str(raw["enrollment"]) if raw.get("enrollment") is not None else None,
                    brief_summary=raw.get("brief_summary"),
                    detailed_description=raw.get("detailed_description"),
                    conditions=raw.get("conditions"),
                    interventions=raw.get("interventions"),
                    intervention_types=raw.get("intervention_types"),
                    primary_outcomes=raw.get("primary_outcomes"),
                    secondary_outcomes=raw.get("secondary_outcomes"),
                    study_type=raw.get("study_type"),
                    has_results=str(raw["has_results"]) if raw.get("has_results") is not None else None,
                    trial_url=raw.get("trial_url"),
                    scraped_at=parse_datetime(raw.get("scraped_at")),
                )
                self.db.add(trial)
                self.db.flush()
                loaded += 1
            except IntegrityError:
                self.db.rollback()
                logger.debug("Duplicate trial nct_id=%s, skipping", raw.get("nct_id"))
            except Exception as exc:
                self.db.rollback()
                msg = f"Error loading trial nct_id={raw.get('nct_id')}: {exc}"
                logger.warning(msg)
                self.stats["errors"].append(msg)

        self.db.commit()
        self.stats["trials_loaded"] += loaded
        logger.info("Loaded %d trials from %s", loaded, filepath.name)

    # ------------------------------------------------------------------ #
    # Tweets
    # ------------------------------------------------------------------ #
    def load_tweets(self, filepath: Path):
        """Load tweets from JSON file into DB."""
        records = self._read_json(filepath)
        if records is None:
            return

        loaded = 0
        for raw in records:
            try:
                tweet = Tweet(
                    tweet_id=str(raw["id"]),  # JSON field is "id"
                    text=raw.get("text", ""),
                    author_username=raw.get("author_username"),
                    author_followers=raw.get("author_followers"),
                    date=parse_datetime(raw.get("date")),
                    retweet_count=raw.get("retweet_count"),
                    like_count=raw.get("like_count"),
                    url=raw.get("url"),
                    source_query=raw.get("source_query"),
                    scraped_at=parse_datetime(raw.get("scraped_at")),
                )
                self.db.add(tweet)
                self.db.flush()
                loaded += 1
            except IntegrityError:
                self.db.rollback()
                logger.debug("Duplicate tweet id=%s, skipping", raw.get("id"))
            except Exception as exc:
                self.db.rollback()
                msg = f"Error loading tweet id={raw.get('id')}: {exc}"
                logger.warning(msg)
                self.stats["errors"].append(msg)

        self.db.commit()
        self.stats["tweets_loaded"] += loaded
        logger.info("Loaded %d tweets from %s", loaded, filepath.name)

    # ------------------------------------------------------------------ #
    # Reddit
    # ------------------------------------------------------------------ #
    def load_reddit(self, filepath: Path):
        """Load Reddit posts/comments from JSON file into DB."""
        records = self._read_json(filepath)
        if records is None:
            return

        loaded = 0
        for raw in records:
            try:
                post = RedditPost(
                    post_id=str(raw["id"]),          # JSON "id" → DB "post_id"
                    post_type=raw.get("type"),        # JSON "type" → DB "post_type"
                    subreddit=raw.get("subreddit"),
                    author=raw.get("author"),
                    author_karma=None,                # Not in scraper output
                    title=raw.get("title"),
                    text=raw.get("text", ""),
                    score=raw.get("score"),
                    upvote_ratio=raw.get("upvote_ratio"),
                    num_comments=raw.get("num_comments"),
                    created_utc=parse_datetime(raw.get("created_utc")),  # Unix ts → DateTime
                    url=raw.get("url"),
                    parent_post_id=raw.get("parent_post_id"),
                    search_term=raw.get("search_term"),
                    scraped_at=parse_datetime(raw.get("scraped_at")),
                )
                self.db.add(post)
                self.db.flush()
                loaded += 1
            except IntegrityError:
                self.db.rollback()
                logger.debug("Duplicate reddit post id=%s, skipping", raw.get("id"))
            except Exception as exc:
                self.db.rollback()
                msg = f"Error loading reddit post id={raw.get('id')}: {exc}"
                logger.warning(msg)
                self.stats["errors"].append(msg)

        self.db.commit()
        self.stats["reddit_loaded"] += loaded
        logger.info("Loaded %d reddit posts from %s", loaded, filepath.name)

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _read_json(self, filepath: Path):
        """Read and parse a JSON file. Returns list or None on error."""
        try:
            with open(filepath) as f:
                data = json.load(f)
            if not isinstance(data, list):
                logger.error("Expected JSON array in %s", filepath.name)
                return None
            return data
        except (json.JSONDecodeError, OSError) as exc:
            msg = f"Failed to read {filepath.name}: {exc}"
            logger.error(msg)
            self.stats["errors"].append(msg)
            return None
