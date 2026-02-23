"""
Clinical Trials Scraper
Scrapes ClinicalTrials.gov API v2 for studies related to Retatrutide.
"""

import json
import logging
import os
import time
from datetime import datetime, timezone

import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "config", "search_terms.json")
DATA_DIR = os.path.join(BASE_DIR, "data", "raw")
LOGS_DIR = os.path.join(BASE_DIR, "logs")

API_BASE_URL = "https://clinicaltrials.gov/api/v2/studies"
RATE_LIMIT_SECONDS = 0.5


class ClinicalTrialsScraper:
    """Scraper for ClinicalTrials.gov v2 API."""

    def __init__(self, config_path=None):
        """Load configuration from config/search_terms.json."""
        self.config_path = config_path or CONFIG_PATH
        self.config = self._load_config()
        self.data = {}  # dict keyed by NCT ID for deduplication
        logger.info("ClinicalTrialsScraper initialized with config from %s", self.config_path)

    def _load_config(self):
        """Load and return the search terms configuration."""
        with open(self.config_path, "r") as f:
            config = json.load(f)
        logger.info("Loaded config: primary_name=%s", config.get("primary_name"))
        return config

    def build_search_terms(self):
        """Return a list of formal search terms for querying the API.

        Uses primary_name and formal alternative names (excludes informal
        short-hands that would produce too many false positives).
        """
        formal_names = [self.config["primary_name"]]
        # Add formal alternative names (drug codes, formal identifiers)
        formal_alternatives = {"LY3437943", "LY-3437943"}
        for name in self.config.get("alternative_names", []):
            if name in formal_alternatives:
                formal_names.append(name)
        # Deduplicate while preserving order
        seen = set()
        unique = []
        for name in formal_names:
            if name not in seen:
                seen.add(name)
                unique.append(name)
        logger.info("Built %d search terms: %s", len(unique), unique)
        return unique

    def _safe_get(self, data, *keys, default=None):
        """Safely traverse nested dicts/lists by a sequence of keys."""
        current = data
        for key in keys:
            if isinstance(current, dict):
                current = current.get(key)
            elif isinstance(current, list) and isinstance(key, int) and key < len(current):
                current = current[key]
            else:
                return default
            if current is None:
                return default
        return current

    def _parse_trial(self, study):
        """Parse a single study object from the v2 API response into our format.

        The v2 API returns studies with a protocolSection containing nested
        modules (identificationModule, statusModule, sponsorCollaboratorsModule,
        designModule, descriptionModule, conditionsModule, armsInterventionsModule,
        outcomesModule, etc.) and optionally a resultsSection.
        """
        protocol = study.get("protocolSection", {})
        has_results = study.get("hasResults", False)

        # Identification
        id_module = protocol.get("identificationModule", {})
        nct_id = id_module.get("nctId", "")
        brief_title = id_module.get("briefTitle", "")
        official_title = id_module.get("officialTitle", "")

        # Status
        status_module = protocol.get("statusModule", {})
        status = status_module.get("overallStatus", "")
        start_date_struct = status_module.get("startDateStruct", {})
        start_date = start_date_struct.get("date", "")
        completion_date_struct = status_module.get("completionDateStruct", {})
        completion_date = completion_date_struct.get("date", "")
        primary_completion_struct = status_module.get("primaryCompletionDateStruct", {})
        primary_completion_date = primary_completion_struct.get("date", "")

        # Sponsor
        sponsor_module = protocol.get("sponsorCollaboratorsModule", {})
        lead_sponsor = sponsor_module.get("leadSponsor", {})
        sponsor = lead_sponsor.get("name", "")

        # Design
        design_module = protocol.get("designModule", {})
        phases = design_module.get("phases", [])
        phase = ", ".join(phases) if isinstance(phases, list) else str(phases)
        study_type = design_module.get("studyType", "")
        enrollment_info = design_module.get("enrollmentInfo", {})
        enrollment = enrollment_info.get("count", None)

        # Description
        desc_module = protocol.get("descriptionModule", {})
        brief_summary = desc_module.get("briefSummary", "")
        detailed_description = desc_module.get("detailedDescription", "")

        # Conditions
        conditions_module = protocol.get("conditionsModule", {})
        conditions = conditions_module.get("conditions", [])

        # Interventions
        arms_module = protocol.get("armsInterventionsModule", {})
        interventions_raw = arms_module.get("interventions", [])
        interventions = []
        intervention_types = []
        for interv in interventions_raw:
            name = interv.get("name", "")
            itype = interv.get("type", "")
            if name:
                interventions.append(name)
            if itype and itype not in intervention_types:
                intervention_types.append(itype)

        # Outcomes
        outcomes_module = protocol.get("outcomesModule", {})
        primary_outcomes_raw = outcomes_module.get("primaryOutcomes", [])
        primary_outcomes = []
        for outcome in primary_outcomes_raw:
            measure = outcome.get("measure", "")
            if measure:
                primary_outcomes.append(measure)

        secondary_outcomes_raw = outcomes_module.get("secondaryOutcomes", [])
        secondary_outcomes = []
        for outcome in secondary_outcomes_raw:
            measure = outcome.get("measure", "")
            if measure:
                secondary_outcomes.append(measure)

        # Construct trial URL
        trial_url = f"https://clinicaltrials.gov/study/{nct_id}" if nct_id else ""

        return {
            "nct_id": nct_id,
            "brief_title": brief_title,
            "official_title": official_title,
            "status": status,
            "sponsor": sponsor,
            "phase": phase,
            "start_date": start_date,
            "completion_date": completion_date,
            "primary_completion_date": primary_completion_date,
            "enrollment": enrollment,
            "brief_summary": brief_summary,
            "detailed_description": detailed_description,
            "conditions": conditions,
            "interventions": interventions,
            "intervention_types": intervention_types,
            "primary_outcomes": primary_outcomes,
            "secondary_outcomes": secondary_outcomes,
            "study_type": study_type,
            "has_results": has_results,
            "trial_url": trial_url,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        }

    def scrape_all(self):
        """Iterate over search terms, query the API, and parse each trial.

        Deduplicates by NCT ID. Never crashes on a single trial failure.
        """
        search_terms = self.build_search_terms()
        for term in search_terms:
            logger.info("Searching for: %s", term)
            try:
                self._search_term(term)
            except Exception:
                logger.exception("Failed to search for term: %s", term)
            time.sleep(RATE_LIMIT_SECONDS)

        logger.info("Scraping complete. Total unique trials: %d", len(self.data))
        return self.data

    def _search_term(self, term):
        """Query the v2 API for a single search term, handling pagination."""
        next_page_token = None
        while True:
            params = {
                "query.term": term,
                "pageSize": 100,
            }
            if next_page_token:
                params["pageToken"] = next_page_token

            response = requests.get(API_BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            studies = data.get("studies", [])
            for study in studies:
                try:
                    parsed = self._parse_trial(study)
                    nct_id = parsed.get("nct_id")
                    if nct_id and nct_id not in self.data:
                        self.data[nct_id] = parsed
                        logger.debug("Added trial: %s", nct_id)
                    elif nct_id:
                        logger.debug("Duplicate skipped: %s", nct_id)
                except Exception:
                    logger.exception("Failed to parse a study entry")

            next_page_token = data.get("nextPageToken")
            if not next_page_token:
                break
            time.sleep(RATE_LIMIT_SECONDS)

    def export_data(self):
        """Export collected trials to data/raw/clinical_trials_YYYY-MM-DD.json."""
        os.makedirs(DATA_DIR, exist_ok=True)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        filename = f"clinical_trials_{today}.json"
        filepath = os.path.join(DATA_DIR, filename)

        trials_list = list(self.data.values())
        with open(filepath, "w") as f:
            json.dump(trials_list, f, indent=2)

        logger.info("Exported %d trials to %s", len(trials_list), filepath)
        return filepath

    def _generate_summary(self):
        """Generate and save a summary of the scraped data to logs/."""
        os.makedirs(LOGS_DIR, exist_ok=True)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        filename = f"clinical_trials_summary_{today}.json"
        filepath = os.path.join(LOGS_DIR, filename)

        trials_list = list(self.data.values())

        # Compute stats
        status_counts = {}
        phase_counts = {}
        sponsor_counts = {}
        for trial in trials_list:
            s = trial.get("status", "Unknown")
            status_counts[s] = status_counts.get(s, 0) + 1
            p = trial.get("phase", "Unknown")
            phase_counts[p] = phase_counts.get(p, 0) + 1
            sp = trial.get("sponsor", "Unknown")
            sponsor_counts[sp] = sponsor_counts.get(sp, 0) + 1

        summary = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_trials": len(trials_list),
            "status_counts": status_counts,
            "phase_counts": phase_counts,
            "sponsor_counts": sponsor_counts,
            "trials_with_results": sum(1 for t in trials_list if t.get("has_results")),
        }

        with open(filepath, "w") as f:
            json.dump(summary, f, indent=2)

        logger.info("Summary saved to %s", filepath)
        logger.info("Total trials: %d", summary["total_trials"])
        logger.info("Status breakdown: %s", status_counts)
        logger.info("Phase breakdown: %s", phase_counts)
        return summary


def main():
    """Main entry point for the clinical trials scraper."""
    scraper = ClinicalTrialsScraper()
    scraper.scrape_all()
    scraper.export_data()
    scraper._generate_summary()
    logger.info("Clinical trials scraping pipeline complete.")


if __name__ == "__main__":
    main()
