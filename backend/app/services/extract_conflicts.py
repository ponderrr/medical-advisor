"""
Cross-reference & conflict detector: synthesise DosingProtocol + SideEffect → Conflict rows
"""
import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.orm import Session

import anthropic

from app.models import Conflict, DosingProtocol, SideEffect

load_dotenv(Path(__file__).parent.parent.parent.parent / ".env")

logger = logging.getLogger(__name__)

_SYSTEM = "You are a clinical evidence conflict analyst. Return only JSON."
_PROMPT = """\
Here are dosing claims from multiple sources:
{dosing_summary}

Here are side effect severity reports:
{side_effect_summary}

Identify conflicts — cases where sources directly contradict each other.
Return a JSON array where each item is:
{{"conflict_type": "dosing"|"side_effect"|"mechanism"|"safety",
  "description": str_up_to_300_chars,
  "source_a": str, "source_b": str,
  "resolution": str_or_null,
  "severity": "minor"|"major"|"critical"}}

Return an empty array [] if no conflicts are found."""


def _build_dosing_summary(db: Session) -> str:
    protocols = db.query(DosingProtocol).all()
    if not protocols:
        return "No dosing data available."
    lines = []
    for p in protocols[:50]:  # cap payload size
        lines.append(f"- [{p.source_type}:{p.source_id}] dose={p.dose}, freq={p.frequency}, route={p.route}, confidence={p.confidence}")
    return "\n".join(lines)


def _build_side_effect_summary(db: Session) -> str:
    effects = db.query(SideEffect).all()
    if not effects:
        return "No side effect data available."
    lines = []
    for e in effects[:50]:
        sources_str = ", ".join((e.sources or [])[:3])
        lines.append(f"- {e.effect} | severity={e.severity} | mentions={e.frequency} | sources=[{sources_str}]")
    return "\n".join(lines)


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


def _call_claude(client: anthropic.Anthropic, dosing_summary: str, side_effect_summary: str) -> list[dict]:
    try:
        prompt = _PROMPT.format(
            dosing_summary=dosing_summary,
            side_effect_summary=side_effect_summary,
        )
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2048,
            system=_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        return _parse_array(msg.content[0].text)
    except Exception as exc:
        logger.warning("Claude API error: %s", exc)
        return []


def detect_conflicts(
    db: Session,
    api_client: anthropic.Anthropic | None = None,
    dry_run: bool = False,
) -> dict:
    """
    Query synthesis tables, send consolidated summary to Claude, insert Conflict rows.
    """
    stats = {"detected": 0, "skipped_duplicates": 0, "api_calls": 0, "errors": []}

    if not dry_run and api_client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")
        api_client = anthropic.Anthropic(api_key=api_key)

    dosing_summary = _build_dosing_summary(db)
    side_effect_summary = _build_side_effect_summary(db)

    # Skip API call if no data
    if "No dosing data" in dosing_summary and "No side effect" in side_effect_summary:
        logger.info("No synthesis data to check for conflicts.")
        return stats

    if dry_run:
        return stats

    conflicts = _call_claude(api_client, dosing_summary, side_effect_summary)
    stats["api_calls"] += 1
    logger.info("Claude returned %d potential conflicts", len(conflicts))

    for item in conflicts:
        topic = (item.get("conflict_type") or "unknown").strip()
        source_a = (item.get("source_a") or "").strip()
        source_b = (item.get("source_b") or "").strip()
        description = (item.get("description") or "")[:300]
        resolution = item.get("resolution")

        if not topic or not source_a or not source_b:
            continue

        # Dedup: skip if (topic, source_a, source_b) already exists
        existing = (
            db.query(Conflict)
            .filter(
                Conflict.topic == topic,
                Conflict.source_a_id == source_a,
                Conflict.source_b_id == source_b,
            )
            .first()
        )
        if existing:
            stats["skipped_duplicates"] += 1
            continue

        try:
            record = Conflict(
                topic=topic,
                source_a_id=source_a,
                source_b_id=source_b,
                description=description,
                resolution=resolution,
            )
            db.add(record)
            db.commit()
            stats["detected"] += 1
        except Exception as exc:
            db.rollback()
            msg = f"Insert error ({topic}): {exc}"
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
        result = detect_conflicts(db)
        print(result)
    finally:
        db.close()
