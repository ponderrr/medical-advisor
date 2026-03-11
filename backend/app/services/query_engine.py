"""
Natural language query engine: classify → fetch context → Claude → structured response
"""
import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.orm import Session

import anthropic

from app.models import Conflict, DosingProtocol, Mechanism, SideEffect

load_dotenv(Path(__file__).parent.parent.parent.parent / ".env")

logger = logging.getLogger(__name__)

DOMAIN_KEYWORDS = {
    "dosing": ["dose", "dosing", "how much", "mg", "frequency", "titrat", "inject"],
    "side_effects": ["side effect", "adverse", "nausea", "risk", "danger", "safe"],
    "mechanisms": ["mechanism", "receptor", "how does", "pathway", "agonist", "work"],
    "conflicts": ["conflict", "contradict", "disagree", "debate", "controversy"],
}

_SYSTEM = """\
You are a harm-reduction medical research assistant synthesizing \
clinical literature and user reports about Retatrutide. \
You NEVER provide personal medical advice. \
Always cite source types (e.g. 'per clinical trial data', 'per user reports'). \
End every response with: 'Consult a qualified physician before use.' \
Return JSON: {"answer": str, "sources_used": list_of_str, \
"confidence": float_0_to_1, "domains_covered": list_of_str, "disclaimer": str}"""

_PROMPT_TEMPLATE = "Question: {question}\n\nContext:\n{context}"

DISCLAIMER = "Consult a qualified physician before use."


def classify_domains(question: str) -> list[str]:
    """Keyword-based domain classification — no API call."""
    low = question.lower()
    matched = []
    for domain, keywords in DOMAIN_KEYWORDS.items():
        if any(kw in low for kw in keywords):
            matched.append(domain)
    return matched if matched else ["general"]


def build_context(db: Session, domains: list[str], max_rows: int = 20) -> tuple[str, int]:
    """
    Fetch rows from relevant synthesis tables and format as compact context string.
    Returns (context_string, total_row_count).
    """
    sections: list[str] = []
    total = 0

    per_domain = max(1, max_rows // max(len(domains), 1))

    if "dosing" in domains or "general" in domains:
        rows = (
            db.query(DosingProtocol)
            .filter(DosingProtocol.dose.isnot(None))
            .limit(per_domain)
            .all()
        )
        if rows:
            lines = ["[DOSING PROTOCOLS]"]
            for r in rows:
                lines.append(
                    f"• {r.dose} {r.route or ''} {r.frequency or ''} "
                    f"(confidence: {r.confidence}) — source: {r.source_type}:{r.source_id}"
                )
            sections.append("\n".join(lines))
            total += len(rows)

    if "side_effects" in domains or "general" in domains:
        rows = (
            db.query(SideEffect)
            .order_by(SideEffect.frequency.desc())
            .limit(per_domain)
            .all()
        )
        if rows:
            lines = ["[SIDE EFFECTS]"]
            for r in rows:
                src = ", ".join((r.sources or [])[:3])
                lines.append(
                    f"• {r.effect} | severity={r.severity} | mentions={r.frequency} | [{src}]"
                )
            sections.append("\n".join(lines))
            total += len(rows)

    if "mechanisms" in domains or "general" in domains:
        rows = db.query(Mechanism).limit(per_domain).all()
        if rows:
            lines = ["[MECHANISMS]"]
            for r in rows:
                lines.append(f"• {r.mechanism}: {r.description} (confidence: {r.confidence})")
            sections.append("\n".join(lines))
            total += len(rows)

    if "conflicts" in domains or "general" in domains:
        rows = db.query(Conflict).limit(per_domain).all()
        if rows:
            lines = ["[CONFLICTS]"]
            for r in rows:
                lines.append(f"• [{r.topic}] {r.description}")
            sections.append("\n".join(lines))
            total += len(rows)

    return "\n\n".join(sections), total


def _parse_response(raw: str) -> dict | None:
    raw = raw.strip()
    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1] if len(parts) > 1 else raw
        if raw.startswith("json"):
            raw = raw[4:]
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


async def answer_query(
    question: str,
    db: Session,
    api_client: anthropic.Anthropic | None = None,
    max_context_rows: int = 20,
) -> dict:
    """
    Classify question → pull context → call Claude → return structured response.
    Raises ValueError on Claude API failure.
    """
    if api_client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")
        api_client = anthropic.Anthropic(api_key=api_key)

    domains = classify_domains(question)
    context, row_count = build_context(db, domains, max_rows=max_context_rows)

    if not context:
        context = "No synthesis data available yet. Synthesis pipeline may not have been run."

    prompt = _PROMPT_TEMPLATE.format(question=question, context=context)

    try:
        msg = api_client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = msg.content[0].text
    except Exception as exc:
        raise ValueError(f"Claude API error: {exc}") from exc

    parsed = _parse_response(raw)
    if not parsed:
        raise ValueError(f"Could not parse Claude response as JSON: {raw[:300]}")

    return {
        "question": question,
        "answer": parsed.get("answer", ""),
        "sources_used": parsed.get("sources_used") or [],
        "confidence": float(parsed.get("confidence") or 0.0),
        "domains_covered": parsed.get("domains_covered") or domains,
        "context_row_count": row_count,
        "disclaimer": parsed.get("disclaimer") or DISCLAIMER,
    }
