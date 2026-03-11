# Data Pipeline Design

## JSON → SQLite Mapping Strategy

### PubMed Papers
All fields match DB columns directly. `scraped_at` is ISO 8601 string → parsed to DateTime.

### Clinical Trials
- `enrollment`: JSON Integer → stored as String (str conversion)
- `has_results`: JSON Boolean → stored as String ("True"/"False")
- All date fields (start_date, completion_date, etc.) are stored as String (no conversion needed)
- `scraped_at`: ISO 8601 string → parsed to DateTime

### X/Twitter
- JSON `id` → DB column `tweet_id`
- `date` and `scraped_at`: ISO 8601 string → parsed to DateTime

### Reddit
- JSON `id` → DB column `post_id`
- JSON `type` → DB column `post_type`
- `created_utc`: Unix timestamp (integer) → converted to DateTime via `datetime.fromtimestamp()`
- `scraped_at`: ISO 8601 string → parsed to DateTime
- `author_karma`: not present in scraper output → stored as None

## Error Handling
- Per-record try/except: bad records are logged and skipped, pipeline continues
- Duplicate detection via unique constraints (pmid, nct_id, tweet_id, post_id) — skip on IntegrityError
- Invalid datetime strings → stored as None with a warning log

## Duplicate Strategy
Skip-on-conflict: if a record with the same unique ID already exists, skip it (idempotent runs).

## Date Parsing
`parse_datetime()` utility handles:
- ISO 8601 with/without timezone (Twitter, PubMed, Reddit scraped_at)
- Unix timestamps (Reddit created_utc)
- Returns None on failure

## File Discovery
Glob `data/raw/*.json` and dispatch based on filename prefix:
- `pubmed_papers_*` → load_papers()
- `clinical_trials_*` → load_trials()
- `x_tweets_*` → load_tweets()
- `reddit_posts_*` → load_reddit()
