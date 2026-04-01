"""
Validation runner for migration phases.
Runs SQL validation queries and reports results.

Usage:
    python run_validation.py              # Run all validations
    python run_validation.py --phase 2    # Run validation for phase 2
"""

import asyncio
import argparse
import logging
import sys
import os

sys.path.insert(0, '/app/migration')

import asyncpg
from config.settings import SUPABASE_DB_URL, REPORTS_DIR, SQL_DIR

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger("migration.validation")


async def run_validation_query(conn, name: str, sql: str):
    """Run a validation query and print results."""
    try:
        rows = await conn.fetch(sql)
        logger.info(f"\n{name}:")
        if rows:
            # Print column headers
            if rows[0]:
                headers = list(rows[0].keys())
                logger.info("  " + " | ".join(str(h) for h in headers))
                logger.info("  " + "-" * 50)
            
            for row in rows[:20]:  # Limit output
                logger.info("  " + " | ".join(str(v) for v in row.values()))
            
            if len(rows) > 20:
                logger.info(f"  ... and {len(rows) - 20} more rows")
        else:
            logger.info("  (no results)")
        return True
    except Exception as e:
        logger.error(f"{name}: ERROR - {e}")
        return False


async def run_validation():
    """Run all validation queries."""
    if not SUPABASE_DB_URL:
        logger.error("No SUPABASE_DB_URL configured")
        return False
    
    conn = await asyncpg.connect(SUPABASE_DB_URL)
    
    try:
        logger.info("=" * 60)
        logger.info("RUNNING VALIDATION QUERIES")
        logger.info("=" * 60)
        
        # Read validation SQL file
        sql_path = f"{SQL_DIR}/validation/all_phases.sql"
        if os.path.exists(sql_path):
            with open(sql_path, 'r') as f:
                sql_content = f.read()
            
            # Split by semicolon and run each query
            queries = [q.strip() for q in sql_content.split(';') if q.strip() and not q.strip().startswith('--')]
            
            for i, sql in enumerate(queries):
                if sql.strip():
                    # Extract name from comment if present
                    lines = sql.strip().split('\n')
                    name = f"Query {i+1}"
                    if lines[0].startswith('--'):
                        name = lines[0].lstrip('-').strip()
                        sql = '\n'.join(lines[1:])
                    
                    await run_validation_query(conn, name, sql)
        else:
            # Run inline validation queries
            queries = [
                ("Profile Count", "SELECT COUNT(*) as count FROM profiles"),
                ("Employee Count", "SELECT COUNT(*) as count FROM employees"),
                ("Document Count", "SELECT COUNT(*) as count FROM documents"),
                ("RTW Check Count", "SELECT COUNT(*) as count FROM rtw_checks"),
                ("DBS Check Count", "SELECT COUNT(*) as count FROM dbs_checks"),
                ("Migration State", "SELECT phase, status, migrated_records, failed_records FROM migration_state ORDER BY phase"),
            ]
            
            for name, sql in queries:
                await run_validation_query(conn, name, sql)
        
        logger.info("\n" + "=" * 60)
        logger.info("VALIDATION COMPLETE")
        logger.info("=" * 60)
        
        return True
        
    finally:
        await conn.close()


def main():
    parser = argparse.ArgumentParser(description="Run migration validation")
    args = parser.parse_args()
    
    success = asyncio.run(run_validation())
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
