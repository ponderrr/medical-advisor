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

### Validate Data Quality

After running scrapers, validate the collected data:
```bash
python validate_data.py
```

This will:
- Check data quality and completeness
- Verify required fields are present
- Calculate summary statistics
- Show sample data for manual review
- Identify any issues or gaps
- Generate validation report in `logs/`

The validator checks:
- **X/Twitter**: 1000+ tweets, valid fields, date ranges
- **PubMed**: 15-25 papers, complete abstracts, journal diversity
- **Clinical Trials**: All trials found, phase/status distribution
- **Reddit**: 100+ items, substantial content, subreddit coverage

## Backend API

The backend is a FastAPI application with SQLAlchemy ORM.

### Setup
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your Anthropic API key
```

### Run Development Server
```bash
cd backend
uvicorn app.main:app --reload
```

API will be available at: http://localhost:8000
API docs: http://localhost:8000/docs

### Database

SQLite database located at: `data/processed/medical_advisor.db`
Tables: papers, clinical_trials, tweets, reddit_posts, dosing_protocols, side_effects, mechanisms, conflicts

## Data Pipeline

### Load Data into Database

After running scrapers, load JSON data into SQLite:
```bash
cd backend
python load_data.py
```

This will:
- Read all JSON files from `data/raw/`
- Parse and validate data
- Load into SQLite database
- Print summary statistics

### Query Data via API
```bash
# Get statistics
curl http://localhost:8000/api/stats

# Get papers
curl http://localhost:8000/api/papers?limit=10

# Get clinical trials (filter by phase)
curl "http://localhost:8000/api/trials?phase=Phase%203"

# Get tweets (filter by author)
curl http://localhost:8000/api/tweets?author=BasedBiohacker
```
