"""
Medical Advisor - Master Orchestrator
Runs all scrapers in sequence with logging and error handling.
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).resolve().parent

# Set up logging: console + file
log_dir = PROJECT_ROOT / "logs"
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / f'scrape_run_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.log'

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


class ScraperOrchestrator:
    """Runs all scrapers in sequence, tracking results and handling errors."""

    def __init__(self):
        self.results = {}
        self.start_time = None
        self.end_time = None

    def run_scraper(self, name, scraper_function):
        """Run a single scraper and track results.

        Args:
            name: Human-readable scraper name.
            scraper_function: Callable that returns an int (record count).
        """
        logger.info("=" * 60)
        logger.info("Starting scraper: %s", name)
        logger.info("=" * 60)

        scraper_start = time.time()
        try:
            records = scraper_function()
            duration = round(time.time() - scraper_start, 2)
            self.results[name] = {
                "status": "success",
                "records": records if isinstance(records, int) else 0,
                "duration_seconds": duration,
                "error": None,
            }
            logger.info(
                "%s completed: %s records in %.2fs",
                name,
                self.results[name]["records"],
                duration,
            )
        except Exception as exc:
            duration = round(time.time() - scraper_start, 2)
            self.results[name] = {
                "status": "failed",
                "records": 0,
                "duration_seconds": duration,
                "error": str(exc),
            }
            logger.error("%s FAILED after %.2fs: %s", name, duration, exc)

    def ask_user(self, question):
        """Ask user a yes/no question.

        Returns:
            True if yes, False otherwise.
        """
        answer = input(f"{question} (y/n): ").strip().lower()
        return answer in ("y", "yes")

    def _run_x_scraper(self):
        """Run the X/Twitter scraper and return record count."""
        from scrapers.x_scraper import TwitterScraper

        scraper = TwitterScraper()
        scraper.scrape_all()
        if scraper.data:
            scraper.export_data()
            scraper._generate_summary()
        return len(scraper.data)

    def _run_pubmed_scraper(self):
        """Run the PubMed scraper and return record count."""
        from scrapers.pubmed_scraper import PubMedScraper

        scraper = PubMedScraper()
        scraper.scrape_all()
        if scraper.data:
            export_path = scraper.export_data()
            scraper._generate_summary(export_path=export_path)
        return len(scraper.data)

    def _run_clinical_trials_scraper(self):
        """Run the Clinical Trials scraper and return record count."""
        from scrapers.clinical_trials_scraper import ClinicalTrialsScraper

        scraper = ClinicalTrialsScraper()
        scraper.scrape_all()
        if scraper.data:
            scraper.export_data()
            scraper._generate_summary()
        return len(scraper.data)

    def _run_reddit_scraper(self):
        """Run the Reddit scraper and return record count."""
        from scrapers.reddit_scraper import RedditScraper

        scraper = RedditScraper()
        total = scraper.scrape_all()
        if total > 0:
            scraper.export_data()
            scraper._generate_summary()
        return total

    def run_all(self):
        """Run all scrapers in sequence."""
        self.start_time = time.time()

        logger.info("MEDICAL ADVISOR - DATA COLLECTION PIPELINE")
        logger.info("Started at: %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        # Mandatory scrapers
        self.run_scraper("X/Twitter", self._run_x_scraper)
        self.run_scraper("PubMed", self._run_pubmed_scraper)
        self.run_scraper("Clinical Trials", self._run_clinical_trials_scraper)

        # Reddit is optional - check X results and ask user
        x_result = self.results.get("X/Twitter", {})
        x_records = x_result.get("records", 0)

        if x_records < 500:
            logger.info(
                "X/Twitter returned only %d tweets (< 500). "
                "Reddit scraping is recommended for additional data.",
                x_records,
            )

        run_reddit = self.ask_user("Would you like to run the Reddit scraper?")
        if run_reddit:
            self.run_scraper("Reddit", self._run_reddit_scraper)
        else:
            logger.info("Reddit scraper skipped by user.")
            self.results["Reddit"] = {
                "status": "skipped",
                "records": 0,
                "duration_seconds": 0,
                "error": None,
            }

        self.end_time = time.time()
        self.generate_summary()

    def generate_summary(self):
        """Generate and display final summary, save to JSON."""
        total_duration = round(self.end_time - self.start_time, 2)
        total_records = sum(r.get("records", 0) for r in self.results.values())
        success_count = sum(
            1 for r in self.results.values() if r["status"] == "success"
        )
        failed_count = sum(
            1 for r in self.results.values() if r["status"] == "failed"
        )
        skipped_count = sum(
            1 for r in self.results.values() if r["status"] == "skipped"
        )

        summary = {
            "run_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_duration_seconds": total_duration,
            "total_records": total_records,
            "scrapers_success": success_count,
            "scrapers_failed": failed_count,
            "scrapers_skipped": skipped_count,
            "results": self.results,
        }

        # Log to console
        logger.info("=" * 60)
        logger.info("FINAL SUMMARY")
        logger.info("=" * 60)
        logger.info("Total duration: %.2fs", total_duration)
        logger.info("Total records collected: %d", total_records)
        logger.info(
            "Scrapers: %d success, %d failed, %d skipped",
            success_count,
            failed_count,
            skipped_count,
        )
        for name, result in self.results.items():
            status_icon = (
                "OK" if result["status"] == "success"
                else "FAIL" if result["status"] == "failed"
                else "SKIP"
            )
            logger.info(
                "  [%s] %s: %d records (%.2fs)",
                status_icon,
                name,
                result["records"],
                result["duration_seconds"],
            )
        logger.info("=" * 60)

        # Save summary to JSON
        summary_file = (
            log_dir
            / f'run_summary_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.json'
        )
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        logger.info("Summary saved to %s", summary_file)

        # Next steps
        logger.info("")
        logger.info("NEXT STEPS:")
        logger.info("  1. Review data in data/raw/")
        logger.info("  2. Check logs in logs/")
        logger.info("  3. Run tests: pytest tests/ -v")

        return summary


def main():
    """Main execution."""
    print("=" * 60)
    print("  MEDICAL ADVISOR - DATA COLLECTION")
    print("=" * 60)
    print()
    print("Scrapers: X/Twitter, PubMed, Clinical Trials, Reddit (optional)")
    print()
    input("Press ENTER to begin...")
    print()

    orchestrator = ScraperOrchestrator()
    orchestrator.run_all()


if __name__ == "__main__":
    main()
