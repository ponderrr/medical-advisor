"""
CLI script to load data from JSON files into the SQLite database.

Usage:
    cd backend
    python load_data.py
"""
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    from app.database import SessionLocal, init_db
    from app.services.data_loader import DataLoader

    logger.info("Initialising database...")
    init_db()

    db = SessionLocal()
    try:
        loader = DataLoader(db)
        logger.info("Starting data load...")
        stats = loader.load_all()

        logger.info("=" * 60)
        logger.info("DATA LOAD COMPLETE")
        logger.info("=" * 60)
        logger.info("Papers loaded:       %d", stats["papers_loaded"])
        logger.info("Trials loaded:       %d", stats["trials_loaded"])
        logger.info("Tweets loaded:       %d", stats["tweets_loaded"])
        logger.info("Reddit posts loaded: %d", stats["reddit_loaded"])

        if stats["errors"]:
            logger.warning("%d error(s) encountered:", len(stats["errors"]))
            for err in stats["errors"]:
                logger.warning("  - %s", err)
            sys.exit(1)

    finally:
        db.close()


if __name__ == "__main__":
    main()
