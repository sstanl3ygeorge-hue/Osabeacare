"""
Rollback script for migration phases.
Rolls back data in reverse order of migration.

Usage:
    python run_rollback.py --phase 6         # Rollback phase 6 only
    python run_rollback.py --from 6 --to 1   # Rollback phases 6 down to 1
    python run_rollback.py --all             # Rollback everything
"""

import asyncio
import argparse
import logging
import sys
import os
from datetime import datetime

sys.path.insert(0, '/app/migration')

import asyncpg
from config.settings import SUPABASE_DB_URL, REPORTS_DIR

# Configure logging
os.makedirs(REPORTS_DIR, exist_ok=True)
log_file = f"{REPORTS_DIR}/rollback_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("migration.rollback")


# Rollback SQL for each phase (in order of execution)
ROLLBACK_SQL = {
    6: """
        -- Phase 6: Rollback checks
        DELETE FROM identity_check_documents;
        DELETE FROM address_check_documents;
        DELETE FROM rtw_checks WHERE mongo_id IS NOT NULL;
        DELETE FROM dbs_checks WHERE mongo_id IS NOT NULL;
        DELETE FROM identity_checks WHERE mongo_id IS NOT NULL;
        DELETE FROM address_checks WHERE mongo_id IS NOT NULL;
        UPDATE migration_state SET status = 'rolled_back', completed_at = NOW() WHERE phase = 'phase_6_checks';
    """,
    5: """
        -- Phase 5: Rollback files (clear storage_path, keep documents)
        UPDATE documents SET 
            storage_path = NULL,
            file_migration_status = 'pending',
            file_migration_error = NULL
        WHERE mongo_id IS NOT NULL;
        UPDATE migration_state SET status = 'rolled_back', completed_at = NOW() WHERE phase = 'phase_5_files';
    """,
    4: """
        -- Phase 4: Rollback documents
        DELETE FROM documents WHERE mongo_id IS NOT NULL;
        DELETE FROM migration_document_map;
        UPDATE migration_state SET status = 'rolled_back', completed_at = NOW() WHERE phase = 'phase_4_documents';
    """,
    3: """
        -- Phase 3: Rollback references and employment data
        DELETE FROM employment_gaps;
        DELETE FROM employment_history;
        DELETE FROM employee_references;
        UPDATE migration_state SET status = 'rolled_back', completed_at = NOW() WHERE phase = 'phase_3_references';
    """,
    2: """
        -- Phase 2: Rollback employees
        DELETE FROM employees WHERE mongo_id IS NOT NULL;
        DELETE FROM migration_employee_map;
        UPDATE migration_state SET status = 'rolled_back', completed_at = NOW() WHERE phase = 'phase_2_employees';
    """,
    1: """
        -- Phase 1: Rollback users/profiles
        DELETE FROM profiles WHERE mongo_id IS NOT NULL;
        DELETE FROM migration_user_map;
        UPDATE migration_state SET status = 'rolled_back', completed_at = NOW() WHERE phase = 'phase_1_users';
    """,
}


async def rollback_phase(conn, phase_num: int) -> bool:
    """Rollback a single phase."""
    if phase_num not in ROLLBACK_SQL:
        logger.error(f"Unknown phase: {phase_num}")
        return False
    
    logger.info(f"Rolling back phase {phase_num}...")
    
    try:
        sql = ROLLBACK_SQL[phase_num]
        await conn.execute(sql)
        logger.info(f"Phase {phase_num} rolled back successfully")
        return True
    except Exception as e:
        logger.error(f"Rollback failed for phase {phase_num}: {e}")
        return False


async def run_rollback(
    from_phase: int = 6,
    to_phase: int = 1,
    confirm: bool = False
):
    """Run rollback from highest phase down to lowest."""
    if not SUPABASE_DB_URL:
        logger.error("No SUPABASE_DB_URL configured")
        return False
    
    logger.info("=" * 60)
    logger.info("ROLLBACK STARTED")
    logger.info(f"Rolling back phases {from_phase} down to {to_phase}")
    logger.info("=" * 60)
    
    if not confirm:
        logger.warning("DRY RUN - Use --confirm to actually execute rollback")
        for phase_num in range(from_phase, to_phase - 1, -1):
            logger.info(f"Would rollback phase {phase_num}")
        return True
    
    conn = await asyncpg.connect(SUPABASE_DB_URL)
    
    try:
        results = {}
        
        # Rollback in reverse order
        for phase_num in range(from_phase, to_phase - 1, -1):
            success = await rollback_phase(conn, phase_num)
            results[phase_num] = success
            
            if not success:
                logger.error(f"Stopping rollback due to error in phase {phase_num}")
                break
        
        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("ROLLBACK SUMMARY")
        logger.info("=" * 60)
        
        for phase_num in sorted(results.keys(), reverse=True):
            status = "SUCCESS" if results[phase_num] else "FAILED"
            logger.info(f"  Phase {phase_num}: {status}")
        
        return all(results.values())
        
    finally:
        await conn.close()


def main():
    parser = argparse.ArgumentParser(description="Rollback migration phases")
    parser.add_argument("--phase", type=int, help="Rollback single phase")
    parser.add_argument("--from", dest="from_phase", type=int, default=6, help="Start rollback from phase")
    parser.add_argument("--to", dest="to_phase", type=int, default=1, help="End rollback at phase")
    parser.add_argument("--all", action="store_true", help="Rollback all phases")
    parser.add_argument("--confirm", action="store_true", help="Actually execute (without this, dry run)")
    
    args = parser.parse_args()
    
    if args.phase:
        from_phase = args.phase
        to_phase = args.phase
    elif args.all:
        from_phase = 6
        to_phase = 1
    else:
        from_phase = args.from_phase
        to_phase = args.to_phase
    
    success = asyncio.run(run_rollback(
        from_phase=from_phase,
        to_phase=to_phase,
        confirm=args.confirm
    ))
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
