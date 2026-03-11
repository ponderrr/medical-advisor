"""
Mechanism extractor: literature-only sources → Claude API → Mechanism rows
"""
import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.orm import Session

import anthropic

from app.models import ClinicalTrial, Mechanism, Paper

load_dotenv(Path(__file__).parent.parent.parent.parent / ".env")

logger = logging.getLogger(__name__)

MECHANISM_KEYWORDS = [
    "GLP-1", "GIP", "glucagon", "receptor", "agonist",
    "binding", "pathway", "cAMP", "insulin", "adipose",
]

VALID_EVIDENCE = {"in_vitro", "animal", "human_trial", "case_report", "unknown"}

_SYSTEM = "You are a molecular pharmacology extractor. Return only JSON."
_PROMPT = """\
Extract receptor mechanisms described in this text. Return a JSON array where each item is:
{{"receptor_target": str, "mechanism_description": str_up_to_200_chars,
  "effect": str_up_to_100_chars,
  "evidence_level": "in_vitro"|"animal"|"human_trial"|"case_report"|"unknown",
  "confidence": float}}

Text: {text}"""


def _has_keyword(text: str) -> bool:
    return any(kw.lower() in text.lower() for kw in MECHANISM_KEYWORDS)


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


def extract_mechanisms(
    db: Session,
    api_client: anthropic.Anthropic | None = None,
    dry_run: bool = False,
) -> dict:
    """
    Scan Paper and ClinicalTrial rows for mechanism keywords, extract via Claude.
    """
    stats = {"extracted": 0, "skipped_duplicates": 0, "api_calls": 0, "candidates": 0, "errors": []}

    if not dry_run and api_client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")
        api_client = anthropic.Anthropic(api_key=api_key)

    # Literature-only: Paper + ClinicalTrial
    chunks: list[tuple[str, str]] = []

    for paper in db.query(Paper).all():
        text = " ".join(filter(None, [paper.title or "", paper.abstract or ""]))
        if _has_keyword(text):
            chunks.append((text, f"paper:{paper.pmid}"))

    for trial in db.query(ClinicalTrial).all():
        text = " ".join(filter(None, [
            trial.brief_title or "",
            trial.brief_summary or "",
            trial.detailed_description or "",
        ]))
        if _has_keyword(text):
            chunks.append((text, f"trial:{trial.nct_id}"))

    stats["candidates"] = len(chunks)
    logger.info("Mechanism candidates: %d", len(chunks))

    if dry_run:
        return stats

    for text, source_ref in chunks:
        items = _call_claude(api_client, text)
        stats["api_calls"] += 1

        for item in items:
            receptor = (item.get("receptor_target") or "").strip()
            description = (item.get("mechanism_description") or "")[:200]
            evidence = item.get("evidence_level") or "unknown"
            if evidence not in VALID_EVIDENCE:
                evidence = "unknown"

            if not receptor or not description:
                continue

            # Dedup: check if (receptor, source_ref) already in sources of any existing record
            existing = db.query(Mechanism).filter(Mechanism.mechanism == receptor).first()
            if existing:
                current_sources = existing.sources or []
                if source_ref in current_sources:
                    stats["skipped_duplicates"] += 1
                    continue
                existing.sources = current_sources + [source_ref]
                db.commit()
                stats["extracted"] += 1
                continue

            try:
                record = Mechanism(
                    mechanism=receptor,
                    description=description,
                    sources=[source_ref],
                    confidence=_confidence_str(item.get("confidence")),
                )
                db.add(record)
                db.commit()
                stats["extracted"] += 1
            except Exception as exc:
                db.rollback()
                msg = f"Insert error ({receptor}): {exc}"
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
        result = extract_mechanisms(db)
        print(result)
    finally:
        db.close()
