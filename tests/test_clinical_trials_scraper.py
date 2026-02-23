"""
Tests for the Clinical Trials Scraper.

These tests verify config loading, search term building, parsing logic,
and deduplication without making any actual API calls.
"""

import os
import sys

import pytest

# Ensure the project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.clinical_trials_scraper import ClinicalTrialsScraper


CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "config",
    "search_terms.json",
)


@pytest.fixture
def scraper():
    """Create a scraper instance using the real config file."""
    return ClinicalTrialsScraper(config_path=CONFIG_PATH)


def _make_mock_study(
    nct_id="NCT00000001",
    brief_title="Test Study",
    official_title="Official Test Study Title",
    overall_status="RECRUITING",
    sponsor_name="Eli Lilly and Company",
    phases=None,
    study_type="INTERVENTIONAL",
    enrollment_count=300,
    brief_summary="A brief summary of the study.",
    detailed_description="A detailed description of the study.",
    conditions=None,
    interventions=None,
    primary_outcomes=None,
    secondary_outcomes=None,
    has_results=False,
    start_date="2024-01-15",
    completion_date="2026-12-31",
    primary_completion_date="2026-06-30",
):
    """Build a mock study dict matching the ClinicalTrials.gov v2 API structure."""
    if phases is None:
        phases = ["PHASE3"]
    if conditions is None:
        conditions = ["Obesity", "Type 2 Diabetes"]
    if interventions is None:
        interventions = [
            {
                "type": "DRUG",
                "name": "Retatrutide",
                "description": "GLP-1/GIP/glucagon triple agonist",
            }
        ]
    if primary_outcomes is None:
        primary_outcomes = [
            {
                "measure": "Change in body weight",
                "timeFrame": "48 weeks",
            }
        ]
    if secondary_outcomes is None:
        secondary_outcomes = [
            {
                "measure": "Change in HbA1c",
                "timeFrame": "48 weeks",
            }
        ]

    return {
        "protocolSection": {
            "identificationModule": {
                "nctId": nct_id,
                "briefTitle": brief_title,
                "officialTitle": official_title,
            },
            "statusModule": {
                "overallStatus": overall_status,
                "startDateStruct": {"date": start_date},
                "completionDateStruct": {"date": completion_date},
                "primaryCompletionDateStruct": {"date": primary_completion_date},
            },
            "sponsorCollaboratorsModule": {
                "leadSponsor": {
                    "name": sponsor_name,
                    "class": "INDUSTRY",
                },
            },
            "designModule": {
                "studyType": study_type,
                "phases": phases,
                "enrollmentInfo": {
                    "count": enrollment_count,
                    "type": "ESTIMATED",
                },
            },
            "descriptionModule": {
                "briefSummary": brief_summary,
                "detailedDescription": detailed_description,
            },
            "conditionsModule": {
                "conditions": conditions,
            },
            "armsInterventionsModule": {
                "interventions": interventions,
            },
            "outcomesModule": {
                "primaryOutcomes": primary_outcomes,
                "secondaryOutcomes": secondary_outcomes,
            },
        },
        "hasResults": has_results,
    }


class TestClinicalTrialsScraper:
    """Test suite for ClinicalTrialsScraper."""

    def test_load_config(self, scraper):
        """Verify config loads and has expected keys."""
        config = scraper.config
        assert isinstance(config, dict)
        assert "primary_name" in config
        assert "alternative_names" in config
        assert config["primary_name"] == "Retatrutide"
        assert isinstance(config["alternative_names"], list)
        assert len(config["alternative_names"]) > 0
        # Verify other expected keys exist
        assert "target_accounts" in config
        assert "hashtags" in config
        assert "subreddits" in config

    def test_build_search_terms(self, scraper):
        """Verify returns list with formal names like Retatrutide, LY3437943."""
        terms = scraper.build_search_terms()
        assert isinstance(terms, list)
        assert len(terms) > 0
        # Must contain the primary name
        assert "Retatrutide" in terms
        # Must contain formal drug codes
        assert "LY3437943" in terms
        assert "LY-3437943" in terms
        # Should NOT contain informal short names that would cause false positives
        assert "reta" not in terms
        assert "triple agonist" not in terms

    def test_parse_trial_data(self, scraper):
        """Create a mock v2 API study, call _parse_trial, verify all fields."""
        mock_study = _make_mock_study(
            nct_id="NCT05929066",
            brief_title="A Study of Retatrutide in Participants With Obesity",
            official_title="A Phase 3 Study of Retatrutide (LY3437943) in Participants With Obesity",
            overall_status="RECRUITING",
            sponsor_name="Eli Lilly and Company",
            phases=["PHASE3"],
            study_type="INTERVENTIONAL",
            enrollment_count=1800,
            brief_summary="This study evaluates Retatrutide for obesity treatment.",
            detailed_description="A randomized, double-blind, placebo-controlled study.",
            conditions=["Obesity"],
            interventions=[
                {
                    "type": "DRUG",
                    "name": "Retatrutide",
                    "description": "Triple agonist",
                },
                {
                    "type": "DRUG",
                    "name": "Placebo",
                    "description": "Placebo comparator",
                },
            ],
            primary_outcomes=[
                {"measure": "Percent change in body weight", "timeFrame": "48 weeks"},
            ],
            secondary_outcomes=[
                {"measure": "Proportion achieving >=5% weight loss", "timeFrame": "48 weeks"},
            ],
            has_results=False,
            start_date="2023-09-01",
            completion_date="2026-12-31",
            primary_completion_date="2025-12-31",
        )

        parsed = scraper._parse_trial(mock_study)

        # Verify all expected fields are present and correct
        assert parsed["nct_id"] == "NCT05929066"
        assert parsed["brief_title"] == "A Study of Retatrutide in Participants With Obesity"
        assert "Phase 3" in parsed["official_title"]
        assert parsed["status"] == "RECRUITING"
        assert parsed["sponsor"] == "Eli Lilly and Company"
        assert parsed["phase"] == "PHASE3"
        assert parsed["study_type"] == "INTERVENTIONAL"
        assert parsed["enrollment"] == 1800
        assert "Retatrutide" in parsed["brief_summary"]
        assert "randomized" in parsed["detailed_description"]
        assert "Obesity" in parsed["conditions"]
        assert "Retatrutide" in parsed["interventions"]
        assert "Placebo" in parsed["interventions"]
        assert "DRUG" in parsed["intervention_types"]
        assert len(parsed["primary_outcomes"]) == 1
        assert "body weight" in parsed["primary_outcomes"][0]
        assert len(parsed["secondary_outcomes"]) == 1
        assert "weight loss" in parsed["secondary_outcomes"][0]
        assert parsed["has_results"] is False
        assert parsed["trial_url"] == "https://clinicaltrials.gov/study/NCT05929066"
        assert parsed["start_date"] == "2023-09-01"
        assert parsed["completion_date"] == "2026-12-31"
        assert parsed["primary_completion_date"] == "2025-12-31"
        assert "scraped_at" in parsed

    def test_deduplication(self, scraper):
        """Add same NCT ID twice, verify only one entry remains."""
        study_1 = _make_mock_study(
            nct_id="NCT12345678",
            brief_title="First insertion",
        )
        study_2 = _make_mock_study(
            nct_id="NCT12345678",
            brief_title="Second insertion (duplicate)",
        )

        parsed_1 = scraper._parse_trial(study_1)
        parsed_2 = scraper._parse_trial(study_2)

        # Simulate the deduplication logic used in scrape_all / _search_term
        nct_id_1 = parsed_1["nct_id"]
        if nct_id_1 not in scraper.data:
            scraper.data[nct_id_1] = parsed_1

        nct_id_2 = parsed_2["nct_id"]
        if nct_id_2 not in scraper.data:
            scraper.data[nct_id_2] = parsed_2

        # Should only have one entry
        assert len(scraper.data) == 1
        assert "NCT12345678" in scraper.data
        # The first insertion should win
        assert scraper.data["NCT12345678"]["brief_title"] == "First insertion"
