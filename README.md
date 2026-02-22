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

Coming soon...
