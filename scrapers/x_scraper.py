"""
Twitter/X scraper for medical research project.
Uses snscrape to collect tweets related to Retatrutide and related terms.
"""

import json
import logging
import os
from datetime import datetime, timezone

try:
    import snscrape.modules.twitter as sntwitter
except (ImportError, AttributeError):
    sntwitter = None

# Project root is one level up from scrapers/
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class TwitterScraper:
    """Scrapes Twitter/X for tweets related to configured search terms."""

    def __init__(self, config_path=None):
        """
        Initialize the scraper and load configuration.

        Args:
            config_path: Path to the search_terms.json config file.
                         Defaults to config/search_terms.json relative to project root.
        """
        if config_path is None:
            config_path = os.path.join(PROJECT_ROOT, "config", "search_terms.json")

        self.config_path = config_path
        self.config = self._load_config()
        self.data = {}  # Dict keyed by tweet ID for deduplication
        self.today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        logger.info("TwitterScraper initialized with config from %s", self.config_path)

    def _load_config(self):
        """Load search terms configuration from JSON file."""
        logger.info("Loading config from %s", self.config_path)
        with open(self.config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        logger.info(
            "Config loaded: %d alternative names, %d target accounts, %d hashtags",
            len(config.get("alternative_names", [])),
            len(config.get("target_accounts", [])),
            len(config.get("hashtags", [])),
        )
        return config

    def build_queries(self):
        """
        Build a list of search queries from the config.

        Returns:
            List of (query_string, source_label) tuples.
        """
        queries = []

        # Alternative names as direct search terms
        for name in self.config.get("alternative_names", []):
            queries.append((name, f"search:{name}"))

        # Target accounts with from: syntax
        for account in self.config.get("target_accounts", []):
            queries.append((f"from:{account}", f"account:{account}"))

        # Hashtags with # prefix
        for hashtag in self.config.get("hashtags", []):
            queries.append((f"#{hashtag}", f"hashtag:{hashtag}"))

        logger.info("Built %d queries from config", len(queries))
        return queries

    def _extract_tweet_data(self, tweet, source_query):
        """
        Extract relevant fields from a snscrape Tweet object.

        Args:
            tweet: A snscrape Tweet object.
            source_query: The query string that found this tweet.

        Returns:
            Dictionary of tweet data.
        """
        return {
            "id": tweet.id,
            "text": tweet.rawContent,
            "author_username": tweet.user.username if tweet.user else None,
            "author_followers": tweet.user.followersCount if tweet.user else None,
            "date": tweet.date.isoformat() if tweet.date else None,
            "retweet_count": tweet.retweetCount,
            "like_count": tweet.likeCount,
            "url": tweet.url,
            "source_query": source_query,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        }

    def _scrape_query(self, query, source_label, max_tweets=200):
        """
        Execute a single search query and add results to self.data.

        Args:
            query: The search query string.
            source_label: Label describing the query source.
            max_tweets: Maximum tweets to collect per query.

        Returns:
            Number of new tweets added.
        """
        count = 0
        new_count = 0
        logger.info("Scraping query: '%s' (max %d tweets)", query, max_tweets)

        if sntwitter is None:
            logger.error("snscrape is not available. Cannot scrape Twitter.")
            return 0

        try:
            scraper = sntwitter.TwitterSearchScraper(query)
            for tweet in scraper.get_items():
                if count >= max_tweets:
                    break

                # Skip non-Tweet objects (TweetRef, Tombstone, etc.)
                if not isinstance(tweet, sntwitter.Tweet):
                    continue

                tweet_id = tweet.id

                # Deduplication: only add if not already present
                if tweet_id not in self.data:
                    self.data[tweet_id] = self._extract_tweet_data(tweet, source_label)
                    new_count += 1

                count += 1

        except Exception as e:
            logger.error("Error scraping query '%s': %s", query, str(e))

        logger.info(
            "Query '%s': processed %d tweets, %d new (total: %d)",
            query, count, new_count, len(self.data),
        )
        return new_count

    def scrape_all(self, max_tweets_per_query=200):
        """
        Run all queries and collect tweets.

        Args:
            max_tweets_per_query: Maximum tweets per individual query.
        """
        queries = self.build_queries()
        logger.info("Starting scrape with %d queries", len(queries))

        for query, source_label in queries:
            try:
                self._scrape_query(query, source_label, max_tweets=max_tweets_per_query)
            except Exception as e:
                logger.error(
                    "Failed to scrape query '%s': %s. Continuing with next query.",
                    query, str(e),
                )
                continue

        logger.info("Scrape complete. Total unique tweets: %d", len(self.data))

    def export_data(self, output_dir=None):
        """
        Export collected tweets to a JSON file.

        Args:
            output_dir: Directory for output file. Defaults to data/raw/.

        Returns:
            Path to the exported file.
        """
        if output_dir is None:
            output_dir = os.path.join(PROJECT_ROOT, "data", "raw")

        os.makedirs(output_dir, exist_ok=True)

        filename = f"x_tweets_{self.today}.json"
        filepath = os.path.join(output_dir, filename)

        tweets_list = list(self.data.values())

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(tweets_list, f, indent=2, ensure_ascii=False)

        logger.info("Exported %d tweets to %s", len(tweets_list), filepath)
        return filepath

    def _generate_summary(self, logs_dir=None):
        """
        Generate and save a summary of the scraping session.

        Args:
            logs_dir: Directory for log file. Defaults to logs/.

        Returns:
            Path to the summary file.
        """
        if logs_dir is None:
            logs_dir = os.path.join(PROJECT_ROOT, "logs")

        os.makedirs(logs_dir, exist_ok=True)

        filename = f"x_scrape_summary_{self.today}.json"
        filepath = os.path.join(logs_dir, filename)

        # Compute summary stats
        tweets_list = list(self.data.values())
        total_tweets = len(tweets_list)

        # Count tweets per source query
        source_counts = {}
        for tweet in tweets_list:
            src = tweet.get("source_query", "unknown")
            source_counts[src] = source_counts.get(src, 0) + 1

        # Calculate engagement stats
        total_likes = sum(t.get("like_count", 0) or 0 for t in tweets_list)
        total_retweets = sum(t.get("retweet_count", 0) or 0 for t in tweets_list)

        summary = {
            "scrape_date": self.today,
            "total_unique_tweets": total_tweets,
            "tweets_per_source": source_counts,
            "total_likes": total_likes,
            "total_retweets": total_retweets,
            "avg_likes": round(total_likes / total_tweets, 2) if total_tweets > 0 else 0,
            "avg_retweets": round(total_retweets / total_tweets, 2) if total_tweets > 0 else 0,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        logger.info("Summary saved to %s", filepath)
        logger.info(
            "Summary: %d tweets, %d likes, %d retweets",
            total_tweets, total_likes, total_retweets,
        )
        return filepath

    def run(self, max_tweets_per_query=200):
        """
        Full pipeline: scrape, export, and generate summary.

        Args:
            max_tweets_per_query: Maximum tweets per individual query.
        """
        self.scrape_all(max_tweets_per_query=max_tweets_per_query)
        self.export_data()
        self._generate_summary()


def main():
    """Entry point for the Twitter scraper."""
    scraper = TwitterScraper()
    scraper.run(max_tweets_per_query=200)


if __name__ == "__main__":
    main()
