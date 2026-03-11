"""
POST /api/query — natural language query endpoint with rate limiting and query logging
"""
import logging
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from time import time

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

import anthropic

from app.database import get_db
from app.schemas import QueryRequest, QueryResponse
from app.services.query_engine import answer_query

router = APIRouter(tags=["query"])

logger = logging.getLogger(__name__)

# ── Rate limiting ─────────────────────────────────────────────────────────────
_WINDOW = 60  # seconds
_MAX_REQUESTS = 10
_rate_timestamps: dict[str, list[float]] = defaultdict(list)


def _check_rate_limit(ip: str) -> bool:
    """Returns True if request is allowed, False if rate limit exceeded."""
    now = time()
    valid = [t for t in _rate_timestamps[ip] if now - t < _WINDOW]
    _rate_timestamps[ip] = valid
    if len(valid) >= _MAX_REQUESTS:
        return False
    _rate_timestamps[ip].append(now)
    return True


def reset_rate_limit():
    """Clear all rate limit state — used in tests."""
    _rate_timestamps.clear()


# ── Query logging ─────────────────────────────────────────────────────────────

def _log_query(question: str, response: dict) -> None:
    log_dir = Path(__file__).parent.parent.parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d")
    log_path = log_dir / f"queries_{date_str}.log"
    entry = (
        f"[{datetime.now().isoformat()}] Q: {question!r} | "
        f"domains={response.get('domains_covered')} | "
        f"confidence={response.get('confidence')} | "
        f"context_rows={response.get('context_row_count')}\n"
    )
    try:
        with open(log_path, "a") as f:
            f.write(entry)
    except OSError as exc:
        logger.warning("Could not write query log: %s", exc)


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post("/query", response_model=QueryResponse)
async def query_endpoint(
    body: QueryRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Answer a natural language question about Retatrutide using synthesised data.
    Rate limited to 10 requests per IP per minute.
    """
    ip = (request.client.host if request.client else "unknown")

    if not _check_rate_limit(ip):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Maximum 10 requests per minute.",
        )

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured.")
    api_client = anthropic.Anthropic(api_key=api_key)

    try:
        result = await answer_query(
            question=body.question,
            db=db,
            api_client=api_client,
            max_context_rows=body.max_context_rows,
        )
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    _log_query(body.question, result)
    return QueryResponse(**result)
