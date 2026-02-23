"""
Reddit scraper for medical research project.

Searches specified subreddits for posts and comments related to Retatrutide
using the PRAW (Python Reddit API Wrapper) library. Credentials are loaded
from environment variables via python-dotenv.
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import praw
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("reddit_scraper")

# Project root is one level up from the scrapers/ directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Social-media-friendly terms we actually want to search for.
# Identifiers like "LY3437943" or "LY-3437943" are lab codes, not
# casual language used on Reddit.  We keep only the colloquial names.
SOCIAL_MEDIA_TERMS = {"reta", "retatrutide", "triple agonist"}

# Minimum character length for comment bodies to be included.
MIN_COMMENT_LENGTH = 50


class RedditScraper:
    """Scrapes Reddit for posts and comments matching configured search terms."""

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------
    def __init__(self, config_path: str | None = None):
        """Load configuration and initialise the Reddit client.

        Parameters
        ----------
        config_path : str | None
            Path to the JSON config file.  Defaults to
            ``config/search_terms.json`` relative to the project root.
        """
        if config_path is None:
            config_path = str(PROJECT_ROOT / "config" / "search_terms.json")

        self.config = self._load_config(config_path)
        self.data: dict[str, dict] = {}  # keyed by post/comment id
        self.reddit = self._init_reddit()

    # ------------------------------------------------------------------
    # Config helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _load_config(config_path: str) -> dict:
        """Read and return the JSON configuration file."""
        logger.info("Loading config from %s", config_path)
        with open(config_path, "r", encoding="utf-8") as fh:
            return json.load(fh)

    def _init_reddit(self) -> praw.Reddit | None:
        """Create a PRAW Reddit instance using .env credentials.

        Returns ``None`` when credentials are missing so that the rest of the
        class can still be used (e.g. for testing config/search-term logic).
        """
        load_dotenv(PROJECT_ROOT / ".env")

        client_id = os.getenv("REDDIT_CLIENT_ID")
        client_secret = os.getenv("REDDIT_CLIENT_SECRET")
        user_agent = os.getenv("REDDIT_USER_AGENT")

        if not all([client_id, client_secret, user_agent]):
            logger.error(
                "Missing Reddit API credentials. Please set "
                "REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, and "
                "REDDIT_USER_AGENT in your .env file. "
                "The scraper will not be able to fetch data."
            )
            return None

        logger.info("Reddit client initialised successfully.")
        return praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent,
        )

    # ------------------------------------------------------------------
    # Search-term logic
    # ------------------------------------------------------------------
    def get_search_terms(self) -> list[str]:
        """Return social-media-friendly search terms from the config.

        Filters ``alternative_names`` to keep only terms that are commonly
        used in casual online discussion (excludes lab identifiers).
        """
        terms = [
            name
            for name in self.config.get("alternative_names", [])
            if name.lower() in SOCIAL_MEDIA_TERMS
        ]
        return terms

    # ------------------------------------------------------------------
    # Core scraping
    # ------------------------------------------------------------------
    def _extract_post(self, submission, search_term: str) -> dict:
        """Convert a PRAW Submission object into a flat dict."""
        return {
            "id": submission.id,
            "type": "post",
            "subreddit": str(submission.subreddit),
            "author": str(submission.author) if submission.author else "[deleted]",
            "title": submission.title,
            "text": submission.selftext,
            "score": submission.score,
            "upvote_ratio": submission.upvote_ratio,
            "num_comments": submission.num_comments,
            "created_utc": submission.created_utc,
            "url": submission.url,
            "search_term": search_term,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        }

    def _extract_comment(self, comment, search_term: str) -> dict | None:
        """Convert a PRAW Comment object into a flat dict.

        Returns ``None`` if the comment body is shorter than
        ``MIN_COMMENT_LENGTH`` characters.
        """
        body = comment.body if hasattr(comment, "body") else ""
        if len(body) < MIN_COMMENT_LENGTH:
            return None

        return {
            "id": comment.id,
            "type": "comment",
            "subreddit": str(comment.subreddit),
            "author": str(comment.author) if comment.author else "[deleted]",
            "text": body,
            "score": comment.score,
            "created_utc": comment.created_utc,
            "url": f"https://www.reddit.com{comment.permalink}",
            "parent_post_id": comment.submission.id,
            "search_term": search_term,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        }

    def _scrape_subreddit(self, subreddit_name: str, search_term: str) -> int:
        """Search a single subreddit for a single term.

        Returns the number of *new* items added to ``self.data``.
        """
        added = 0
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            # Fetch up to 100 submissions per (subreddit, term) pair.
            for submission in subreddit.search(search_term, limit=100):
                if submission.id not in self.data:
                    self.data[submission.id] = self._extract_post(
                        submission, search_term
                    )
                    added += 1

                # Expand the comment forest and collect qualifying comments.
                try:
                    submission.comments.replace_more(limit=0)
                    for comment in submission.comments.list():
                        if comment.id not in self.data:
                            extracted = self._extract_comment(comment, search_term)
                            if extracted is not None:
                                self.data[comment.id] = extracted
                                added += 1
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "Error expanding comments for post %s: %s",
                        submission.id,
                        exc,
                    )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Error scraping r/%s for '%s': %s",
                subreddit_name,
                search_term,
                exc,
            )
        return added

    def scrape_all(self) -> int:
        """Run the full scrape across all configured subreddits and terms.

        Returns the total number of unique items collected.  Returns ``0``
        immediately if the Reddit client is not available.
        """
        if self.reddit is None:
            logger.error(
                "Cannot scrape: Reddit client is not initialised "
                "(missing credentials)."
            )
            return 0

        search_terms = self.get_search_terms()
        subreddits = self.config.get("subreddits", [])

        logger.info(
            "Starting scrape: %d subreddits x %d terms",
            len(subreddits),
            len(search_terms),
        )

        for subreddit_name in subreddits:
            for term in search_terms:
                new = self._scrape_subreddit(subreddit_name, term)
                logger.info(
                    "r/%s | '%s' -> %d new items (total: %d)",
                    subreddit_name,
                    term,
                    new,
                    len(self.data),
                )

        logger.info("Scrape complete. Total unique items: %d", len(self.data))
        return len(self.data)

    # ------------------------------------------------------------------
    # Export & summary
    # ------------------------------------------------------------------
    def export_data(self) -> str:
        """Export collected data to a timestamped JSON file.

        Returns the path to the written file.
        """
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        output_dir = PROJECT_ROOT / "data" / "raw"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"reddit_posts_{today}.json"

        with open(output_path, "w", encoding="utf-8") as fh:
            json.dump(list(self.data.values()), fh, indent=2, ensure_ascii=False)

        logger.info("Exported %d items to %s", len(self.data), output_path)
        return str(output_path)

    def _generate_summary(self) -> dict:
        """Build a summary dict and persist it to logs/.

        Returns the summary dict.
        """
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        posts = [v for v in self.data.values() if v["type"] == "post"]
        comments = [v for v in self.data.values() if v["type"] == "comment"]

        subreddit_counts: dict[str, int] = {}
        for item in self.data.values():
            sr = item["subreddit"]
            subreddit_counts[sr] = subreddit_counts.get(sr, 0) + 1

        summary = {
            "date": today,
            "total_items": len(self.data),
            "total_posts": len(posts),
            "total_comments": len(comments),
            "subreddit_counts": subreddit_counts,
            "search_terms_used": self.get_search_terms(),
        }

        logs_dir = PROJECT_ROOT / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        summary_path = logs_dir / f"reddit_scrape_summary_{today}.json"

        with open(summary_path, "w", encoding="utf-8") as fh:
            json.dump(summary, fh, indent=2, ensure_ascii=False)

        logger.info("Summary saved to %s", summary_path)
        logger.info(
            "Summary: %d posts, %d comments across %d subreddits",
            len(posts),
            len(comments),
            len(subreddit_counts),
        )
        return summary


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> None:
    """CLI entry point for the Reddit scraper."""
    scraper = RedditScraper()
    total = scraper.scrape_all()

    if total > 0:
        scraper.export_data()
        scraper._generate_summary()
    else:
        logger.warning("No data collected. Skipping export and summary.")


if __name__ == "__main__":
    main()
