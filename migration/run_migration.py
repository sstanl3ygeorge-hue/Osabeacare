"""
Main migration orchestrator.
Runs phases in sequence with validation between each.

Usage:
    python run_migration.py                    # Run all phases
    python run_migration.py --phase 2          # Run specific phase
    python run_migration.py --start 3 --end 5  # Run phases 3-5
    python run_migration.py --dry-run          # Dry run (no writes)
    python run_migration.py --validate-only    # Just run validation
"""

import asyncio
import argparse
import logging
import sys
import os
from datetime import datetime

sys.path.insert(0, '/app/migration')

from scripts import (
    phase_1_users,
    phase_2_employees,
    phase_3_references,
    phase_4_documents,
    phase_5_files,
    phase_6_checks,
)
from config.settings import REPORTS_DIR

# Configure logging
os.makedirs(REPORTS_DIR, exist_ok=True)
log_file = f"{REPORTS_DIR}/migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("migration.orchestrator")


PHASES = {
    1: ("phase_1_users", phase_1_users),
    2: ("phase_2_employees", phase_2_employees),
    3: ("phase_3_references", phase_3_references),
    4: ("phase_4_documents", phase_4_documents),
    5: ("phase_5_files", phase_5_files),
    6: ("phase_6_checks", phase_6_checks),
}


async def run_phase(phase_num: int, dry_run: bool = False) -> bool:
    """Run a single migration phase."""
    if phase_num not in PHASES:
        logger.error(f"Unknown phase: {phase_num}")
        return False
    
    phase_name, phase_module = PHASES[phase_num]
    logger.info(f"{'=' * 60}")
    logger.info(f"STARTING PHASE {phase_num}: {phase_name}")
    logger.info(f"{'=' * 60}")
    
    try:
        result = await phase_module.run(dry_run=dry_run)
        
        if result.status.value == "completed":
            logger.info(f"PHASE {phase_num} COMPLETED: {result.migrated_records}/{result.total_records} migrated")
            return True
        else:
            logger.error(f"PHASE {phase_num} FAILED: {result.status.value}")
            logger.error(f"Errors: {len(result.errors)}")
            for err in result.errors[:5]:
                logger.error(f"  - {err}")
            return False
            
    except Exception as e:
        logger.error(f"PHASE {phase_num} EXCEPTION: {e}", exc_info=True)
        return False


async def run_migration(
    start_phase: int = 1,
    end_phase: int = 6,
    dry_run: bool = False,
    stop_on_error: bool = True
):
    """Run migration phases in sequence."""
    logger.info("=" * 60)
    logger.info("MIGRATION STARTED")
    logger.info(f"Phases: {start_phase} to {end_phase}")
    logger.info(f"Dry run: {dry_run}")
    logger.info(f"Log file: {log_file}")
    logger.info("=" * 60)
    
    results = {}
    
    for phase_num in range(start_phase, end_phase + 1):
        success = await run_phase(phase_num, dry_run)
        results[phase_num] = success
        
        if not success and stop_on_error:
            logger.error(f"Stopping migration due to error in phase {phase_num}")
            break
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("MIGRATION SUMMARY")
    logger.info("=" * 60)
    
    for phase_num, success in results.items():
        status = "SUCCESS" if success else "FAILED"
        phase_name = PHASES[phase_num][0]
        logger.info(f"  Phase {phase_num} ({phase_name}): {status}")
    
    all_success = all(results.values())
    logger.info(f"\nOverall: {'SUCCESS' if all_success else 'FAILED'}")
    logger.info(f"Log file: {log_file}")
    
    return all_success


def main():
    parser = argparse.ArgumentParser(description="Run Supabase migration")
    parser.add_argument("--phase", type=int, help="Run single phase (1-6)")
    parser.add_argument("--start", type=int, default=1, help="Start phase")
    parser.add_argument("--end", type=int, default=6, help="End phase")
    parser.add_argument("--dry-run", action="store_true", help="Dry run (no writes)")
    parser.add_argument("--continue-on-error", action="store_true", help="Continue on error")
    
    args = parser.parse_args()
    
    if args.phase:
        start_phase = args.phase
        end_phase = args.phase
    else:
        start_phase = args.start
        end_phase = args.end
    
    success = asyncio.run(run_migration(
        start_phase=start_phase,
        end_phase=end_phase,
        dry_run=args.dry_run,
        stop_on_error=not args.continue_on_error
    ))
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
