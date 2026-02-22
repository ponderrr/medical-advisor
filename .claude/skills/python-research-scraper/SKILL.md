# Python Research Scraper Skill

Best practices for building production-grade data collection scrapers for research purposes.

## Core Principles

1. **Respectful Scraping**: Always honor rate limits and robots.txt
2. **Error Handling**: Graceful degradation, never crash on single failure
3. **Data Validation**: Verify data quality before export
4. **Logging**: Comprehensive logging for debugging and auditing
5. **Testing**: Full test coverage including edge cases

## Class Structure Pattern
```python
class [Source]Scraper:
    def __init__(self, config_path='config/search_terms.json'):
        """Initialize with configuration"""
        self.config = self._load_config(config_path)
        self.data = {}  # Use dict for auto-deduplication
        self.target_count = N

    def _load_config(self, config_path):
        """Load search terms from config file"""
        with open(config_path, 'r') as f:
            return json.load(f)

    def scrape_all(self):
        """Main scraping logic"""
        # Build queries
        # Execute scraping with error handling
        # Return count

    def export_data(self):
        """Export to JSON with timestamp"""
        # Create output directory
        # Generate timestamped filename
        # Export with proper encoding
        # Generate summary

    def _generate_summary(self, output_file):
        """Log and save summary statistics"""
        # Calculate stats
        # Log to console
        # Save to logs/
```

## Error Handling Pattern
```python
try:
    # Scraping logic
    result = self.fetch_data(item)
    if result:
        self.data[item.id] = result
except Exception as e:
    logger.error(f"Error scraping {item}: {e}")
    # Continue to next item - don't crash
```

## Rate Limiting
```python
import time

# For APIs with rate limits
self.rate_limit_delay = 0.34  # ~3 requests/second
time.sleep(self.rate_limit_delay)
```

## Logging Setup
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Usage
logger.info(f"Scraping query: '{query}'")
logger.warning(f"Only {count} results (target was {target})")
logger.error(f"Failed to fetch: {e}")
```

## Data Export Pattern
```python
from pathlib import Path
from datetime import datetime
import json

def export_data(self):
    # Create output directory
    output_dir = Path('data/raw')
    output_dir.mkdir(parents=True, exist_ok=True)

    # Timestamped filename
    timestamp = datetime.now().strftime('%Y-%m-%d')
    output_file = output_dir / f'source_data_{timestamp}.json'

    # Export with proper encoding
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    logger.info(f"Exported {len(data)} records to {output_file}")
    return output_file
```

## Summary Statistics Pattern
```python
def _generate_summary(self, output_file):
    if not self.data:
        logger.warning("No data to summarize")
        return

    summary = {
        'total_records': len(self.data),
        'date_range': {
            'earliest': min(dates),
            'latest': max(dates)
        },
        'unique_sources': len(set(sources)),
        'output_file': str(output_file)
    }

    # Log summary
    logger.info("=" * 60)
    logger.info("SCRAPE SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total Records: {summary['total_records']}")
    logger.info("=" * 60)

    # Save to logs/
    log_dir = Path('logs')
    log_dir.mkdir(parents=True, exist_ok=True)
    summary_file = log_dir / f'summary_{datetime.now().strftime("%Y-%m-%d")}.json'

    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
```

## Deduplication Pattern
```python
# Use dict with unique ID as key for automatic deduplication
self.data = {}  # Initialize as dict

# When adding items
item_id = item.id  # or item['id'] or generate hash
if item_id not in self.data:
    self.data[item_id] = item_data

# Convert to list for export
data_list = list(self.data.values())
```

## Testing Pattern
```python
import pytest
from scrapers.source_scraper import SourceScraper

def test_load_config():
    scraper = SourceScraper()
    assert scraper.config is not None
    assert 'alternative_names' in scraper.config

def test_scrape_returns_data():
    scraper = SourceScraper()
    count = scraper.scrape_all()
    assert count > 0

def test_export_creates_file():
    scraper = SourceScraper()
    scraper.data = {'test': {'id': 'test'}}
    output_file = scraper.export_data()
    assert output_file.exists()

def test_handles_errors_gracefully():
    scraper = SourceScraper()
    # Should not raise exception
    scraper.scrape_query("invalid_query_that_will_fail")
```

## Main Function Pattern
```python
def main():
    """Main execution function"""
    logger.info("Starting [Source] scraper")

    # Initialize scraper
    scraper = SourceScraper()

    # Scrape data
    total = scraper.scrape_all()

    # Export data
    if total > 0:
        output_file = scraper.export_data()
        logger.info(f"Complete! {total} records saved to {output_file}")
    else:
        logger.warning("No data found!")

    return total

if __name__ == "__main__":
    main()
```

## File Naming Convention

- Scraper files: `[source]_scraper.py` (e.g., `x_scraper.py`, `pubmed_scraper.py`)
- Test files: `test_[source]_scraper.py`
- Output files: `[source]_data_YYYY-MM-DD.json`
- Log files: `[source]_summary_YYYY-MM-DD.json`

## Required Fields in Scraped Data

Every scraped item should include:
- Unique ID
- Source query/search term
- Timestamp when scraped (`scraped_at`)
- Original source URL (when applicable)

## Configuration Integration

Always load from `config/search_terms.json`:
- Use formal names for academic sources (PubMed, Clinical Trials)
- Use slang/common terms for social media (Twitter, Reddit)
- Support multiple search terms and iterate through all

## Critical Reminders

- **Never crash on single item failure** - log and continue
- **Validate before export** - check data quality
- **Always respect rate limits** - add delays between requests
- **Log everything** - debugging requires good logs
- **Test edge cases** - empty results, network errors, malformed data
- **Deduplicate** - use dict with unique IDs as keys
- **Timestamp everything** - both in data and filenames
