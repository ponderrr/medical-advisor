"""
Synthesis orchestrator — runs all four extractors in sequence and prints a summary.

Usage:
    cd backend
    python run_synthesis.py           # full run (requires ANTHROPIC_API_KEY)
    python run_synthesis.py --dry-run # count candidates without API calls
"""
import argparse
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

# Ensure backend/ is on sys.path when run directly
sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def setup_log_file() -> logging.FileHandler:
    log_dir = Path(__file__).parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = log_dir / f"synthesis_{ts}.log"
    handler = logging.FileHandler(log_path)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logging.getLogger().addHandler(handler)
    logger.info("Synthesis log: %s", log_path)
    return handler


def main():
    parser = argparse.ArgumentParser(description="AI synthesis pipeline")
    parser.add_argument("--dry-run", action="store_true", help="Count candidates without calling Claude API")
    args = parser.parse_args()

    if not args.dry_run and not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not set. Use --dry-run or set the key.")
        sys.exit(1)

    log_handler = setup_log_file()

    from app.database import SessionLocal, init_db
    from app.services.extract_dosing import extract_dosing_protocols
    from app.services.extract_side_effects import extract_side_effects
    from app.services.extract_mechanisms import extract_mechanisms
    from app.services.extract_conflicts import detect_conflicts

    import anthropic
    api_client = None if args.dry_run else anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    logger.info("Initialising database...")
    init_db()

    db = SessionLocal()
    total_api_calls = 0

    try:
        # ── Step 1: Dosing ────────────────────────────────────────────────
        logger.info("Step 1/4: Extracting dosing protocols...")
        dosing_stats = extract_dosing_protocols(db, api_client=api_client, dry_run=args.dry_run)
        total_api_calls += dosing_stats.get("api_calls", 0)
        logger.info("Dosing: %s", dosing_stats)

        # ── Step 2: Side effects ──────────────────────────────────────────
        logger.info("Step 2/4: Aggregating side effects...")
        se_stats = extract_side_effects(db, api_client=api_client, dry_run=args.dry_run)
        total_api_calls += se_stats.get("api_calls", 0)
        logger.info("Side effects: %s", se_stats)

        # ── Step 3: Mechanisms ────────────────────────────────────────────
        logger.info("Step 3/4: Extracting mechanisms...")
        mech_stats = extract_mechanisms(db, api_client=api_client, dry_run=args.dry_run)
        total_api_calls += mech_stats.get("api_calls", 0)
        logger.info("Mechanisms: %s", mech_stats)

        # ── Step 4: Conflicts ─────────────────────────────────────────────
        logger.info("Step 4/4: Detecting conflicts...")
        conflict_stats = detect_conflicts(db, api_client=api_client, dry_run=args.dry_run)
        total_api_calls += conflict_stats.get("api_calls", 0)
        logger.info("Conflicts: %s", conflict_stats)

    finally:
        db.close()
        logging.getLogger().removeHandler(log_handler)

    # ── Summary ───────────────────────────────────────────────────────────
    mode = "[DRY RUN — no API calls made]" if args.dry_run else ""
    print()
    print("══════════════════════════════════════")
    print(f"  Synthesis Complete {mode}")
    print("══════════════════════════════════════")
    if args.dry_run:
        print(f"  Dosing candidates      : {dosing_stats.get('candidates', 0)}")
        print(f"  Side effect candidates : {se_stats.get('candidates', 0)}")
        print(f"  Mechanism candidates   : {mech_stats.get('candidates', 0)}")
    else:
        print(f"  Dosing protocols extracted : {dosing_stats.get('extracted', 0)}")
        print(f"  Side effects aggregated    : {se_stats.get('extracted', 0)}")
        print(f"  Mechanisms extracted       : {mech_stats.get('extracted', 0)}")
        print(f"  Conflicts detected         : {conflict_stats.get('detected', 0)}")
        print(f"  Total API calls made       : {total_api_calls}")
    print("══════════════════════════════════════")


if __name__ == "__main__":
    main()
