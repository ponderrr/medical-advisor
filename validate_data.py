"""
Medical Advisor - Data Validator
Checks quality and completeness of scraped data from all sources.
"""

import json
import logging
import random
from datetime import datetime
from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).resolve().parent

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Targets per source
TARGETS = {
    "twitter": 1000,
    "pubmed": 15,
    "clinical_trials": 1,
    "reddit": 100,
}


class DataValidator:
    """Validates quality and completeness of scraped research data."""

    def __init__(self, data_dir=None):
        self.data_dir = Path(data_dir) if data_dir else PROJECT_ROOT / "data" / "raw"
        self.validation_results = {}
        self.issues = []
        self.recommendations = []

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def load_json_file(self, filepath):
        """Load and parse a JSON file safely.

        Returns:
            list or None on failure.
        """
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.info("Loaded %d records from %s", len(data), filepath.name)
            return data
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("Failed to load %s: %s", filepath, exc)
            self.issues.append(f"Could not load {filepath.name}: {exc}")
            return None

    def _check_required_fields(self, data, required_fields):
        """Check how many records are missing each required field.

        Returns:
            dict mapping field name -> count of records missing it.
        """
        missing = {}
        for field in required_fields:
            count = sum(
                1
                for item in data
                if field not in item or item[field] in [None, "", "N/A"]
            )
            if count > 0:
                missing[field] = count
        return missing

    def _sample_records(self, data, n=10):
        """Return up to *n* random samples from the data."""
        if len(data) <= n:
            return list(data)
        return random.sample(data, n)

    # ------------------------------------------------------------------
    # Source validators
    # ------------------------------------------------------------------
    def validate_twitter_data(self, filepath):
        """Validate X/Twitter scraped data."""
        data = self.load_json_file(filepath)
        if data is None:
            return

        required = ["id", "text", "author_username", "date", "url"]
        missing = self._check_required_fields(data, required)

        # Stats
        total = len(data)
        unique_authors = len({r.get("author_username") for r in data if r.get("author_username")})
        texts = [r.get("text", "") for r in data]
        avg_length = round(sum(len(t) for t in texts) / max(total, 1), 1)
        dates = [r.get("date", "") for r in data if r.get("date")]
        date_range = (min(dates), max(dates)) if dates else ("N/A", "N/A")

        samples = self._sample_records(data)

        result = {
            "file": filepath.name,
            "total_records": total,
            "unique_authors": unique_authors,
            "avg_text_length": avg_length,
            "date_range": date_range,
            "missing_fields": missing,
            "samples": samples[:5],
        }
        self.validation_results["twitter"] = result

        # Issues / recommendations
        if missing:
            self.issues.append(f"Twitter: missing fields {missing}")
        if total < TARGETS["twitter"]:
            self.recommendations.append(
                f"Twitter: only {total} tweets collected (target was {TARGETS['twitter']}+). "
                "Consider broadening search terms or increasing per-query limits."
            )

        logger.info(
            "Twitter: %d records, %d unique authors, avg length %.1f chars",
            total, unique_authors, avg_length,
        )

    def validate_pubmed_data(self, filepath):
        """Validate PubMed scraped data."""
        data = self.load_json_file(filepath)
        if data is None:
            return

        required = ["pmid", "title", "abstract"]
        missing = self._check_required_fields(data, required)

        total = len(data)
        complete_abstracts = sum(
            1 for r in data if r.get("abstract") and len(r["abstract"]) > 50
        )
        journals = {r.get("journal", "Unknown") for r in data}
        unique_journals = len(journals - {""})

        samples = self._sample_records(data)

        result = {
            "file": filepath.name,
            "total_records": total,
            "complete_abstracts": complete_abstracts,
            "unique_journals": unique_journals,
            "journals": sorted(journals - {""}),
            "missing_fields": missing,
            "samples": samples[:5],
        }
        self.validation_results["pubmed"] = result

        if missing:
            self.issues.append(f"PubMed: missing fields {missing}")
        if total < TARGETS["pubmed"]:
            self.recommendations.append(
                f"PubMed: only {total} papers found (target was {TARGETS['pubmed']}-25). "
                "The compound may have limited published research."
            )

        logger.info(
            "PubMed: %d records, %d with abstracts, %d journals",
            total, complete_abstracts, unique_journals,
        )

    def validate_clinical_trials_data(self, filepath):
        """Validate Clinical Trials scraped data."""
        data = self.load_json_file(filepath)
        if data is None:
            return

        required = ["nct_id", "brief_title", "status"]
        missing = self._check_required_fields(data, required)

        total = len(data)

        # Phase distribution
        phase_dist = {}
        for trial in data:
            phase = trial.get("phase", "Unknown") or "Unknown"
            phase_dist[phase] = phase_dist.get(phase, 0) + 1

        # Status distribution
        status_dist = {}
        for trial in data:
            status = trial.get("status", "Unknown") or "Unknown"
            status_dist[status] = status_dist.get(status, 0) + 1

        result = {
            "file": filepath.name,
            "total_records": total,
            "phase_distribution": phase_dist,
            "status_distribution": status_dist,
            "missing_fields": missing,
            "trials": data,  # show all — usually a small number
        }
        self.validation_results["clinical_trials"] = result

        if missing:
            self.issues.append(f"Clinical Trials: missing fields {missing}")
        if total < TARGETS["clinical_trials"]:
            self.recommendations.append(
                "Clinical Trials: no trials found. Verify search terms."
            )

        logger.info(
            "Clinical Trials: %d records. Phases: %s. Statuses: %s",
            total, phase_dist, status_dist,
        )

    def validate_reddit_data(self, filepath):
        """Validate Reddit scraped data."""
        data = self.load_json_file(filepath)
        if data is None:
            return

        required = ["id", "text", "subreddit", "author"]
        missing = self._check_required_fields(data, required)

        total = len(data)
        posts = [r for r in data if r.get("type") == "post"]
        comments = [r for r in data if r.get("type") == "comment"]
        substantial = sum(1 for r in data if len(r.get("text", "")) > 50)

        # Subreddit distribution
        sub_dist = {}
        for item in data:
            sub = item.get("subreddit", "Unknown")
            sub_dist[sub] = sub_dist.get(sub, 0) + 1

        samples = self._sample_records(data)

        result = {
            "file": filepath.name,
            "total_records": total,
            "posts": len(posts),
            "comments": len(comments),
            "substantial_content": substantial,
            "subreddit_distribution": sub_dist,
            "missing_fields": missing,
            "samples": samples[:5],
        }
        self.validation_results["reddit"] = result

        if missing:
            self.issues.append(f"Reddit: missing fields {missing}")
        if total < TARGETS["reddit"]:
            self.recommendations.append(
                f"Reddit: only {total} items collected (target was {TARGETS['reddit']}+). "
                "Consider adding more subreddits or search terms."
            )

        logger.info(
            "Reddit: %d records (%d posts, %d comments), %d substantial",
            total, len(posts), len(comments), substantial,
        )

    # ------------------------------------------------------------------
    # Orchestration
    # ------------------------------------------------------------------
    def validate_all(self):
        """Find all JSON files in data/raw/ and validate each."""
        if not self.data_dir.exists():
            logger.warning("Data directory %s does not exist.", self.data_dir)
            self.issues.append(f"Data directory {self.data_dir} not found.")
            self.generate_report()
            return

        json_files = sorted(self.data_dir.glob("*.json"))
        if not json_files:
            logger.warning("No JSON files found in %s", self.data_dir)
            self.issues.append("No data files found. Run scrapers first.")
            self.generate_report()
            return

        logger.info("Found %d JSON files in %s", len(json_files), self.data_dir)

        for filepath in json_files:
            name = filepath.name.lower()
            if "x_tweets" in name or "twitter" in name:
                self.validate_twitter_data(filepath)
            elif "pubmed" in name:
                self.validate_pubmed_data(filepath)
            elif "clinical_trials" in name:
                self.validate_clinical_trials_data(filepath)
            elif "reddit" in name:
                self.validate_reddit_data(filepath)
            else:
                logger.info("Skipping unrecognised file: %s", filepath.name)

        self.generate_report()

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------
    def generate_report(self):
        """Generate and display the final validation report."""
        now = datetime.now()
        timestamp = now.strftime("%Y-%m-%d_%H-%M-%S")

        lines = []
        lines.append("=" * 60)
        lines.append("DATA VALIDATION REPORT")
        lines.append(f"Generated: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 60)
        lines.append("")

        # Per-source summaries
        total_records = 0
        for source, result in self.validation_results.items():
            count = result.get("total_records", 0)
            total_records += count
            lines.append(f"--- {source.upper()} ---")
            lines.append(f"  File: {result.get('file', 'N/A')}")
            lines.append(f"  Records: {count}")

            if result.get("missing_fields"):
                lines.append(f"  Missing fields: {result['missing_fields']}")

            # Source-specific details
            if source == "twitter":
                lines.append(f"  Unique authors: {result.get('unique_authors', 0)}")
                lines.append(f"  Avg text length: {result.get('avg_text_length', 0)}")
                lines.append(f"  Date range: {result.get('date_range', ('N/A', 'N/A'))}")
            elif source == "pubmed":
                lines.append(f"  Complete abstracts: {result.get('complete_abstracts', 0)}")
                lines.append(f"  Unique journals: {result.get('unique_journals', 0)}")
            elif source == "clinical_trials":
                lines.append(f"  Phase distribution: {result.get('phase_distribution', {})}")
                lines.append(f"  Status distribution: {result.get('status_distribution', {})}")
            elif source == "reddit":
                lines.append(f"  Posts: {result.get('posts', 0)}")
                lines.append(f"  Comments: {result.get('comments', 0)}")
                lines.append(f"  Substantial (>50 chars): {result.get('substantial_content', 0)}")
                lines.append(f"  Subreddits: {result.get('subreddit_distribution', {})}")

            # Samples
            samples = result.get("samples", [])
            if samples:
                lines.append(f"  Sample records ({min(len(samples), 5)} shown):")
                for i, sample in enumerate(samples[:5]):
                    preview = str(sample.get("text", sample.get("title", sample.get("brief_title", ""))))[:80]
                    lines.append(f"    [{i+1}] {preview}...")

            lines.append("")

        # Totals
        lines.append("=" * 60)
        lines.append(f"TOTAL RECORDS: {total_records}")
        lines.append(f"SOURCES VALIDATED: {len(self.validation_results)}")
        lines.append("")

        # Issues
        if self.issues:
            lines.append("ISSUES FOUND:")
            for issue in self.issues:
                lines.append(f"  - {issue}")
            lines.append("")

        # Recommendations
        if self.recommendations:
            lines.append("RECOMMENDATIONS:")
            for rec in self.recommendations:
                lines.append(f"  - {rec}")
            lines.append("")

        # Manual review checklist
        lines.append("MANUAL REVIEW CHECKLIST:")
        lines.append("  [ ] Spot-check sample tweets for relevance")
        lines.append("  [ ] Verify PubMed papers are about Retatrutide")
        lines.append("  [ ] Confirm clinical trial phases match expectations")
        lines.append("  [ ] Check Reddit posts for quality content")
        lines.append("  [ ] Review date ranges for currency")
        lines.append("")

        # Next steps
        lines.append("NEXT STEPS:")
        lines.append("  1. Address any issues listed above")
        lines.append("  2. Re-run failing scrapers if needed")
        lines.append("  3. Proceed to data processing pipeline")
        lines.append("=" * 60)

        report_text = "\n".join(lines)

        # Print to console
        print(report_text)

        # Save to file
        log_dir = PROJECT_ROOT / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        report_file = log_dir / f"validation_report_{timestamp}.txt"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report_text)

        logger.info("Validation report saved to %s", report_file)

        return {
            "total_records": total_records,
            "sources_validated": len(self.validation_results),
            "issues": len(self.issues),
            "recommendations": len(self.recommendations),
            "report_file": str(report_file),
        }


def main():
    """Main execution."""
    print("=" * 60)
    print("  MEDICAL ADVISOR - DATA VALIDATION")
    print("=" * 60)
    print()

    validator = DataValidator()
    validator.validate_all()


if __name__ == "__main__":
    main()
