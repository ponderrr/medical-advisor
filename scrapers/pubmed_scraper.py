"""
PubMed scraper for medical research papers.

Searches PubMed for papers related to configured search terms,
extracts metadata, deduplicates by PMID, and exports results.
"""

import json
import logging
import os
import re
import time
from datetime import datetime, timedelta

from Bio import Entrez, Medline
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Project root is one level up from scrapers/
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class PubMedScraper:
    """Scraper that searches PubMed for research papers and extracts metadata."""

    # Rate limit: 3 requests per second => 0.34s between requests
    rate_limit_delay = 0.34

    def __init__(self, config_path=None):
        """
        Initialize the scraper by loading config and setting up Entrez.

        Args:
            config_path: Path to search_terms.json. Defaults to config/search_terms.json
                         relative to project root.
        """
        if config_path is None:
            config_path = os.path.join(PROJECT_ROOT, "config", "search_terms.json")

        self.config = self._load_config(config_path)
        self.data = {}  # dict keyed by PMID for deduplication
        self.search_terms = self._extract_formal_names()

        # Set up Entrez email from .env or fallback
        Entrez.email = os.getenv("PUBMED_EMAIL", "researcher@example.com")
        logger.info("Entrez email set to: %s", Entrez.email)

        # Target paper count
        self.min_papers = 15
        self.max_papers = 25

    @staticmethod
    def _load_config(config_path):
        """Load configuration from a JSON file.

        Args:
            config_path: Absolute or relative path to the config JSON file.

        Returns:
            dict: Parsed configuration.
        """
        logger.info("Loading config from: %s", config_path)
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        logger.info("Config loaded successfully. Primary name: %s", config.get("primary_name"))
        return config

    def _extract_formal_names(self):
        """
        Extract formal names from config for PubMed searching.

        Filters alternative_names to include only the primary_name and entries
        that look like formal identifiers (contain uppercase letters, digits,
        or hyphens in identifier patterns like LY3437943 / LY-3437943).

        Returns:
            list: Formal search terms suitable for PubMed queries.
        """
        formal_names = set()

        # Always include primary_name
        primary = self.config.get("primary_name", "")
        if primary:
            formal_names.add(primary)

        # Filter alternative_names for formal identifiers
        alternatives = self.config.get("alternative_names", [])
        for name in alternatives:
            # Match identifiers that contain uppercase + digits (e.g., LY3437943)
            # or uppercase + hyphen + digits (e.g., LY-3437943)
            if re.search(r"[A-Z]+[\-]?\d{3,}", name):
                formal_names.add(name)

        result = sorted(formal_names)
        logger.info("Formal search terms: %s", result)
        return result

    def build_search_query(self):
        """
        Construct a PubMed query string from the formal search terms.

        Returns:
            str: PubMed search query joining terms with OR.
        """
        if not self.search_terms:
            logger.warning("No search terms available to build query.")
            return ""

        # Wrap each term in quotes for exact matching, join with OR
        parts = [f'"{term}"' for term in self.search_terms]
        query = " OR ".join(parts)
        logger.info("Built search query: %s", query)
        return query

    def _search_pubmed(self, query, years_back=5):
        """
        Execute an Entrez esearch for the given query within a date range.

        Args:
            query: PubMed query string.
            years_back: How many years back to search from today.

        Returns:
            list: List of PMID strings returned by the search.
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=years_back * 365)

        mindate = start_date.strftime("%Y/%m/%d")
        maxdate = end_date.strftime("%Y/%m/%d")

        logger.info(
            "Searching PubMed: query=%r, date range=%s to %s",
            query, mindate, maxdate,
        )

        time.sleep(self.rate_limit_delay)
        handle = Entrez.esearch(
            db="pubmed",
            term=query,
            retmax=self.max_papers,
            datetype="pdat",
            mindate=mindate,
            maxdate=maxdate,
        )
        results = Entrez.read(handle)
        handle.close()

        pmids = results.get("IdList", [])
        logger.info("Search returned %d PMIDs.", len(pmids))
        return pmids

    def _fetch_papers(self, pmids):
        """
        Fetch paper details for a list of PMIDs using Entrez efetch + Medline parser.

        Args:
            pmids: List of PMID strings.

        Returns:
            list: List of parsed Medline records (dicts).
        """
        if not pmids:
            return []

        logger.info("Fetching details for %d PMIDs...", len(pmids))
        time.sleep(self.rate_limit_delay)

        handle = Entrez.efetch(
            db="pubmed",
            id=",".join(pmids),
            rettype="medline",
            retmode="text",
        )
        records = list(Medline.parse(handle))
        handle.close()

        logger.info("Fetched %d records.", len(records))
        return records

    def _parse_record(self, record):
        """
        Parse a single Medline record into a standardised dict.

        Args:
            record: A dict-like Medline record.

        Returns:
            dict: Extracted paper metadata, or None on failure.
        """
        try:
            pmid = record.get("PMID", "")
            if not pmid:
                logger.warning("Record missing PMID, skipping.")
                return None

            # Authors: Medline stores as list under "AU"
            authors = record.get("AU", [])
            if isinstance(authors, str):
                authors = [authors]

            # Keywords
            keywords = record.get("OT", [])
            if isinstance(keywords, str):
                keywords = [keywords]

            # MeSH terms
            mesh_terms = record.get("MH", [])
            if isinstance(mesh_terms, str):
                mesh_terms = [mesh_terms]

            # DOI: often in "AID" list as "xxx [doi]"
            doi = ""
            aids = record.get("AID", [])
            if isinstance(aids, str):
                aids = [aids]
            for aid in aids:
                if "[doi]" in aid:
                    doi = aid.replace("[doi]", "").strip()
                    break

            paper = {
                "pmid": pmid,
                "title": record.get("TI", ""),
                "authors": authors,
                "journal": record.get("JT", record.get("TA", "")),
                "publication_date": record.get("DP", ""),
                "abstract": record.get("AB", ""),
                "keywords": keywords,
                "mesh_terms": mesh_terms,
                "doi": doi,
                "pubmed_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                "scraped_at": datetime.now().isoformat(),
            }
            return paper

        except Exception as exc:
            logger.error("Error parsing record: %s", exc, exc_info=True)
            return None

    def scrape_all(self):
        """
        Execute the full scraping pipeline: search, fetch, parse, deduplicate.

        Starts with a 5-year window; if fewer than min_papers are found,
        progressively expands the date range up to 15 years.
        """
        query = self.build_search_query()
        if not query:
            logger.error("Empty query. Cannot scrape.")
            return

        # Try expanding date range if we get too few results
        for years_back in [5, 8, 10, 15]:
            try:
                pmids = self._search_pubmed(query, years_back=years_back)
            except Exception as exc:
                logger.error(
                    "Error during PubMed search (years_back=%d): %s",
                    years_back, exc, exc_info=True,
                )
                continue

            if len(pmids) >= self.min_papers:
                logger.info(
                    "Found %d PMIDs with %d-year window. Proceeding.",
                    len(pmids), years_back,
                )
                break
            else:
                logger.info(
                    "Only %d PMIDs with %d-year window. Expanding range.",
                    len(pmids), years_back,
                )
        else:
            logger.warning(
                "Could not reach %d papers even with expanded range. "
                "Proceeding with %d PMIDs.",
                self.min_papers, len(pmids) if pmids else 0,
            )

        # Fetch and parse
        try:
            records = self._fetch_papers(pmids)
        except Exception as exc:
            logger.error("Error fetching papers: %s", exc, exc_info=True)
            return

        for record in records:
            try:
                paper = self._parse_record(record)
                if paper and paper["pmid"] not in self.data:
                    self.data[paper["pmid"]] = paper
            except Exception as exc:
                logger.error("Error processing a record: %s", exc, exc_info=True)
                continue

        logger.info("Total unique papers collected: %d", len(self.data))

    def export_data(self, output_dir=None):
        """
        Export collected papers to a timestamped JSON file.

        Args:
            output_dir: Directory to write the JSON file. Defaults to data/raw/.

        Returns:
            str: Path to the exported file.
        """
        if output_dir is None:
            output_dir = os.path.join(PROJECT_ROOT, "data", "raw")

        os.makedirs(output_dir, exist_ok=True)

        today = datetime.now().strftime("%Y-%m-%d")
        filename = f"pubmed_papers_{today}.json"
        filepath = os.path.join(output_dir, filename)

        papers_list = list(self.data.values())

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(papers_list, f, indent=2, ensure_ascii=False)

        logger.info("Exported %d papers to %s", len(papers_list), filepath)
        return filepath

    def _generate_summary(self, export_path=None):
        """
        Generate and save a scrape summary to the logs directory.

        Args:
            export_path: The path where data was exported (for reference in summary).

        Returns:
            str: Path to the saved summary JSON file.
        """
        logs_dir = os.path.join(PROJECT_ROOT, "logs")
        os.makedirs(logs_dir, exist_ok=True)

        today = datetime.now().strftime("%Y-%m-%d")
        summary_filename = f"pubmed_scrape_summary_{today}.json"
        summary_path = os.path.join(logs_dir, summary_filename)

        # Collect journals
        journals = {}
        for paper in self.data.values():
            journal = paper.get("journal", "Unknown")
            journals[journal] = journals.get(journal, 0) + 1

        summary = {
            "scrape_date": today,
            "total_papers": len(self.data),
            "search_terms": self.search_terms,
            "journals": journals,
            "export_path": export_path or "",
            "generated_at": datetime.now().isoformat(),
        }

        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        logger.info("Summary saved to %s", summary_path)
        return summary_path


def main():
    """Entry point: instantiate scraper, run pipeline, export, and summarise."""
    logger.info("Starting PubMed scraper...")

    scraper = PubMedScraper()
    scraper.scrape_all()

    export_path = scraper.export_data()
    summary_path = scraper._generate_summary(export_path=export_path)

    logger.info("Scraping complete. Data: %s | Summary: %s", export_path, summary_path)


if __name__ == "__main__":
    main()
