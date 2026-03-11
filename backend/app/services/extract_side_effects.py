"""
Side effect aggregator: keyword pre-filter → Claude API → SideEffect rows (upsert by effect name)
"""
import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.orm import Session

import anthropic

from app.models import ClinicalTrial, Paper, RedditPost, SideEffect, Tweet

load_dotenv(Path(__file__).parent.parent.parent.parent / ".env")

logger = logging.getLogger(__name__)

SIDE_EFFECT_KEYWORDS = [
    "nausea", "vomiting", "fatigue", "diarrhea", "constipation",
    "injection site", "headache", "hypoglycemia", "pancreatitis",
    "appetite", "muscle", "sleep", "mood", "heart rate", "bp",
    "gallbladder", "thyroid", "c-cell", "tachycardia",
]

VALID_SEVERITIES = {"mild", "moderate", "severe", "unknown"}

_SYSTEM = "You are a clinical adverse event extractor. Return only JSON."
_PROMPT = """\
Extract side effects from this text. Return a JSON array where each item is:
{{"effect_name": str, "severity": "mild"|"moderate"|"severe"|"unknown",
  "frequency": str_or_null, "context_quote": str_up_to_100_chars, "confidence": float}}

Text: {text}"""


def _has_keyword(text: str) -> bool:
    low = text.lower()
    return any(kw in low for kw in SIDE_EFFECT_KEYWORDS)


def _normalize_effect(name: str) -> str:
    return name.strip().lower()


def _parse_array(raw: str) -> list[dict]:
    raw = raw.strip()
    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1] if len(parts) > 1 else raw
        if raw.startswith("json"):
            raw = raw[4:]
    try:
        result = json.loads(raw)
        return result if isinstance(result, list) else []
    except json.JSONDecodeError as exc:
        logger.warning("JSON parse error: %s | raw=%r", exc, raw[:200])
        return []


def _call_claude(client: anthropic.Anthropic, text: str) -> list[dict]:
    try:
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=_SYSTEM,
            messages=[{"role": "user", "content": _PROMPT.format(text=text[:2000])}],
        )
        return _parse_array(msg.content[0].text)
    except Exception as exc:
        logger.warning("Claude API error: %s", exc)
        return []


def _upsert_effect(db: Session, effect_name: str, severity: str, source_ref: str, quote: str | None) -> bool:
    """Insert new or increment existing SideEffect. Returns True if inserted/updated."""
    normalized = _normalize_effect(effect_name)
    if not normalized:
        return False

    if severity not in VALID_SEVERITIES:
        severity = "unknown"

    existing = db.query(SideEffect).filter(SideEffect.effect == normalized).first()

    if existing:
        # Skip if this source already counted
        current_sources = existing.sources or []
        if source_ref in current_sources:
            return False
        existing.frequency = (existing.frequency or 0) + 1
        existing.sources = current_sources + [source_ref]
        # Update severity if new mention is more severe
        severity_rank = {"unknown": 0, "mild": 1, "moderate": 2, "severe": 3}
        if severity_rank.get(severity, 0) > severity_rank.get(existing.severity or "unknown", 0):
            existing.severity = severity
        db.commit()
        return True
    else:
        record = SideEffect(
            effect=normalized,
            severity=severity,
            frequency=1,
            sources=[source_ref],
            description=quote,
        )
        db.add(record)
        db.commit()
        return True


def extract_side_effects(
    db: Session,
    api_client: anthropic.Anthropic | None = None,
    dry_run: bool = False,
) -> dict:
    """
    Scan all text sources for side effect keywords, extract via Claude, upsert SideEffect rows.
    """
    stats = {"extracted": 0, "skipped": 0, "api_calls": 0, "candidates": 0, "errors": []}

    if not dry_run and api_client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")
        api_client = anthropic.Anthropic(api_key=api_key)

    # Collect (text, source_ref) pairs from all sources
    chunks: list[tuple[str, str]] = []

    for paper in db.query(Paper).all():
        text = " ".join(filter(None, [paper.title or "", paper.abstract or ""]))
        if _has_keyword(text):
            chunks.append((text, f"paper:{paper.pmid}"))

    for trial in db.query(ClinicalTrial).all():
        text = " ".join(filter(None, [trial.brief_summary or "", trial.detailed_description or ""]))
        if _has_keyword(text):
            chunks.append((text, f"trial:{trial.nct_id}"))

    for tweet in db.query(Tweet).all():
        text = tweet.text or ""
        if _has_keyword(text):
            chunks.append((text, f"tweet:{tweet.tweet_id}"))

    for post in db.query(RedditPost).all():
        text = " ".join(filter(None, [post.title or "", post.text or ""]))
        if _has_keyword(text):
            chunks.append((text, f"reddit:{post.post_id}"))

    stats["candidates"] = len(chunks)
    logger.info("Side effect candidates: %d", len(chunks))

    if dry_run:
        return stats

    for text, source_ref in chunks:
        items = _call_claude(api_client, text)
        stats["api_calls"] += 1

        if not items:
            continue

        for item in items:
            effect_name = item.get("effect_name") or ""
            severity = item.get("severity") or "unknown"
            quote = (item.get("context_quote") or "")[:100] or None

            try:
                updated = _upsert_effect(db, effect_name, severity, source_ref, quote)
                if updated:
                    stats["extracted"] += 1
                else:
                    stats["skipped"] += 1
            except Exception as exc:
                db.rollback()
                msg = f"Upsert error ({effect_name}): {exc}"
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
        result = extract_side_effects(db)
        print(result)
    finally:
        db.close()
