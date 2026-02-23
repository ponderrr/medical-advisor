# Medical Advisor

Systematic data collection and synthesis pipeline for researching medical compounds.

**Current Focus:** Retatrutide (GLP-3 RT) - Triple agonist peptide

## Status: 🚧 Under Development

## Architecture
```
medical-advisor/
├── scrapers/          # Data collection modules
├── data/
│   ├── raw/          # Scraped JSON
│   └── processed/    # SQLite database
├── logs/             # Execution logs
├── config/           # Configuration
├── tests/            # Test suite
└── experiments/      # Learning tools
```

## Technology Stack

- Python 3.x
- snscrape (Twitter)
- Biopython (PubMed)
- requests
- pytest

## Installation
```bash
# Clone the repository
git clone https://github.com/ponderrr/medical-advisor.git
cd medical-advisor

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment (optional)
cp .env.template .env
# Edit .env with your credentials
```

## Configuration

Edit `config/search_terms.json` to customize:
- Compound names and aliases
- Target social media accounts
- Hashtags to monitor
- Subreddits to search

## Usage

### Run All Scrapers
```bash
python run_scrapers.py
```

This will:
1. Scrape 1000+ tweets from X/Twitter
2. Pull 15-25 research papers from PubMed
3. Get all clinical trials for Retatrutide
4. Optionally scrape Reddit (you'll be asked)

### Run Individual Scrapers
```bash
python scrapers/x_scraper.py
python scrapers/pubmed_scraper.py
python scrapers/clinical_trials_scraper.py
python scrapers/reddit_scraper.py  # Requires Reddit API credentials
```

### Output

All data saved to `data/raw/`:
- `x_tweets_YYYY-MM-DD.json`
- `pubmed_papers_YYYY-MM-DD.json`
- `clinical_trials_YYYY-MM-DD.json`
- `reddit_posts_YYYY-MM-DD.json` (if run)

Logs saved to `logs/`:
- `scrape_run_YYYY-MM-DD_HH-MM-SS.log`
- `run_summary_YYYY-MM-DD_HH-MM-SS.json`
