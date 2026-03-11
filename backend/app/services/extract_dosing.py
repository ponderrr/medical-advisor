"""
Dosing protocol extractor: regex pre-filter → Claude API → DosingProtocol rows
"""
import json
import logging
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.orm import Session

import anthropic

from app.models import DosingProtocol, Paper, RedditPost, Tweet

load_dotenv(Path(__file__).parent.parent.parent.parent / ".env")

logger = logging.getLogger(__name__)

DOSE_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*(mg|mcg|µg|ug)", re.IGNORECASE)
FREQ_PATTERN = re.compile(
    r"(once|twice|every\s+\d+\s+days?|weekly|biweekly|QW|Q\d+W)", re.IGNORECASE
)
ROUTE_PATTERN = re.compile(
    r"(subcutaneous|subq\b|SC\b|IM\b|intramuscular|oral|injection)", re.IGNORECASE
)

_SYSTEM = "You are a clinical pharmacology extractor. Return only JSON."
_PROMPT = """\
Extract dosing information from this text. Return JSON:
{{"dose_amount": str_or_null, "dose_unit": str_or_null, "frequency": str_or_null,
  "route": str_or_null, "titration_notes": str_or_null, "confidence": float_or_null,
  "raw_passage": str_or_null}}
If a field cannot be determined, use null.

Text: {text}"""


def _pattern_hits(text: str) -> int:
    return sum([
        bool(DOSE_PATTERN.search(text)),
        bool(FREQ_PATTERN.search(text)),
        bool(ROUTE_PATTERN.search(text)),
    ])


def _parse_claude_json(raw: str) -> dict | None:
    raw = raw.strip()
    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1] if len(parts) > 1 else raw
        if raw.startswith("json"):
            raw = raw[4:]
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.warning("JSON parse error: %s | raw=%r", exc, raw[:200])
        return None


def _confidence_str(value) -> str:
    try:
        f = float(value)
        if f >= 0.7:
            return "high"
        if f >= 0.4:
            return "medium"
        return "low"
    except (TypeError, ValueError):
        return "medium"


def _call_claude(client: anthropic.Anthropic, text: str) -> dict | None:
    try:
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            system=_SYSTEM,
            messages=[{"role": "user", "content": _PROMPT.format(text=text[:2000])}],
        )
        return _parse_claude_json(msg.content[0].text)
    except Exception as exc:
        logger.warning("Claude API error: %s", exc)
        return None


def extract_dosing_protocols(
    db: Session,
    api_client: anthropic.Anthropic | None = None,
    dry_run: bool = False,
) -> dict:
    """
    Scan Paper, Tweet, RedditPost rows for dosing candidates and extract via Claude.
    Returns stats dict.
    """
    stats = {"extracted": 0, "skipped_duplicates": 0, "api_calls": 0, "candidates": 0, "errors": []}

    if not dry_run and api_client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")
        api_client = anthropic.Anthropic(api_key=api_key)

    # Collect candidates: (text, source_type, source_id)
    candidates: list[tuple[str, str, str]] = []

    for paper in db.query(Paper).all():
        text = " ".join(filter(None, [paper.title or "", paper.abstract or ""]))
        if _pattern_hits(text) >= 2:
            candidates.append((text, "paper", str(paper.pmid)))

    for tweet in db.query(Tweet).all():
        text = tweet.text or ""
        if _pattern_hits(text) >= 2:
            candidates.append((text, "tweet", str(tweet.tweet_id)))

    for post in db.query(RedditPost).all():
        text = " ".join(filter(None, [post.title or "", post.text or ""]))
        if _pattern_hits(text) >= 2:
            candidates.append((text, "reddit", str(post.post_id)))

    stats["candidates"] = len(candidates)
    logger.info("Dosing candidates: %d", len(candidates))

    if dry_run:
        return stats

    for text, source_type, source_id in candidates:
        existing = (
            db.query(DosingProtocol)
            .filter(
                DosingProtocol.source_type == source_type,
                DosingProtocol.source_id == source_id,
            )
            .first()
        )
        if existing:
            stats["skipped_duplicates"] += 1
            continue

        parsed = _call_claude(api_client, text)
        stats["api_calls"] += 1

        if not parsed:
            continue

        amount = parsed.get("dose_amount") or ""
        unit = parsed.get("dose_unit") or ""
        dose_str = f"{amount}{unit}".strip() or None

        try:
            record = DosingProtocol(
                source_type=source_type,
                source_id=source_id,
                compound="Retatrutide",
                dose=dose_str,
                frequency=parsed.get("frequency"),
                route=parsed.get("route"),
                context=parsed.get("raw_passage") or text[:500],
                confidence=_confidence_str(parsed.get("confidence")),
            )
            db.add(record)
            db.commit()
            stats["extracted"] += 1
        except Exception as exc:
            db.rollback()
            msg = f"Insert error ({source_type}/{source_id}): {exc}"
            logger.warning(msg)
            stats["errors"].append(msg)

    return stats


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    logging.basicConfig(level=logging.INFO)
    from app.database import SessionLocal, init_db
    init_db()
    db = SessionLocal()
    try:
        result = extract_dosing_protocols(db)
        print(result)
    finally:
        db.close()
