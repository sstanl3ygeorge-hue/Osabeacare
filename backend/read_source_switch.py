"""
Minimal staging feature flag system for backend source switching.
Env-based read-source flags with MongoDB fallback.

Usage:
    # In .env
    READ_SOURCE_EMPLOYEES=supabase   # or 'mongo' (default)
    READ_SOURCE_COMPLIANCE=supabase
    READ_SOURCE_TRAINING=supabase
    SUPABASE_DB_URL=postgresql://...

    # In code
    from read_source_switch import ReadSource, get_read_source, log_source_served
    
    source = get_read_source("employees")
    if source == ReadSource.SUPABASE:
        data = await read_employees_pg(...)
    else:
        data = await read_employees_mongo(...)
    log_source_served(request, "employees", source, len(data))
"""

import os
import logging
from enum import Enum
from typing import Optional, Any, Dict, List
from datetime import datetime, timezone
from functools import wraps
import asyncpg

logger = logging.getLogger("read_source_switch")
logger.setLevel(logging.INFO)

# Add handler if not present
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    ))
    logger.addHandler(handler)


class ReadSource(str, Enum):
    MONGO = "mongo"
    SUPABASE = "supabase"


# Feature flags - loaded from environment
READ_SOURCE_FLAGS = {
    "employees": os.environ.get("READ_SOURCE_EMPLOYEES", "mongo").lower(),
    "compliance": os.environ.get("READ_SOURCE_COMPLIANCE", "mongo").lower(),
    "training": os.environ.get("READ_SOURCE_TRAINING", "mongo").lower(),
    "documents": os.environ.get("READ_SOURCE_DOCUMENTS", "mongo").lower(),
}


def reload_flags():
    """Reload flags from environment (for hot reload scenarios)."""
    global READ_SOURCE_FLAGS
    READ_SOURCE_FLAGS = {
        "employees": os.environ.get("READ_SOURCE_EMPLOYEES", "mongo").lower(),
        "compliance": os.environ.get("READ_SOURCE_COMPLIANCE", "mongo").lower(),
        "training": os.environ.get("READ_SOURCE_TRAINING", "mongo").lower(),
        "documents": os.environ.get("READ_SOURCE_DOCUMENTS", "mongo").lower(),
    }


def get_read_source(entity: str) -> ReadSource:
    """
    Get the configured read source for an entity type.
    Falls back to MONGO if flag is invalid or not configured.
    """
    flag = READ_SOURCE_FLAGS.get(entity, "mongo")
    if flag == "supabase":
        return ReadSource.SUPABASE
    return ReadSource.MONGO


def is_supabase_enabled(entity: str) -> bool:
    """Check if Supabase is enabled for an entity type."""
    return get_read_source(entity) == ReadSource.SUPABASE


# Supabase connection pool (initialized lazily)
_pg_pool: Optional[asyncpg.Pool] = None


async def get_pg_pool() -> Optional[asyncpg.Pool]:
    """Get or create Postgres connection pool."""
    global _pg_pool
    
    if _pg_pool is not None:
        return _pg_pool
    
    db_url = os.environ.get("SUPABASE_DB_URL")
    if not db_url:
        logger.warning("SUPABASE_DB_URL not configured - Supabase reads will fall back to Mongo")
        return None
    
    try:
        _pg_pool = await asyncpg.create_pool(
            db_url,
            min_size=2,
            max_size=10,
            command_timeout=30
        )
        logger.info("Supabase Postgres pool initialized")
        return _pg_pool
    except Exception as e:
        logger.error(f"Failed to create Postgres pool: {e}")
        return None


async def close_pg_pool():
    """Close the Postgres pool on shutdown."""
    global _pg_pool
    if _pg_pool:
        await _pg_pool.close()
        _pg_pool = None
        logger.info("Supabase Postgres pool closed")


def log_source_served(
    endpoint: str,
    entity: str,
    source: ReadSource,
    record_count: int = 0,
    employee_id: str = None,
    fallback_used: bool = False,
    latency_ms: float = None
):
    """
    Log which backend served the data for observability.
    
    Format: [SOURCE:entity] endpoint -> source (records=N, latency=Xms)
    """
    parts = [
        f"[SOURCE:{entity.upper()}]",
        endpoint,
        "->",
        source.value.upper(),
        f"(records={record_count}"
    ]
    
    if employee_id:
        parts.append(f", emp={employee_id[:8]}...")
    
    if latency_ms:
        parts.append(f", latency={latency_ms:.1f}ms")
    
    if fallback_used:
        parts.append(", FALLBACK")
    
    parts.append(")")
    
    log_msg = " ".join(parts)
    
    if fallback_used:
        logger.warning(log_msg)
    else:
        logger.info(log_msg)


# ============================================================
# SUPABASE READ HELPERS
# ============================================================

async def pg_fetch_one(query: str, *args) -> Optional[Dict[str, Any]]:
    """Execute query and return single row as dict."""
    pool = await get_pg_pool()
    if not pool:
        return None
    
    async with pool.acquire() as conn:
        row = await conn.fetchrow(query, *args)
        return dict(row) if row else None


async def pg_fetch_all(query: str, *args) -> List[Dict[str, Any]]:
    """Execute query and return all rows as list of dicts."""
    pool = await get_pg_pool()
    if not pool:
        return []
    
    async with pool.acquire() as conn:
        rows = await conn.fetch(query, *args)
        return [dict(r) for r in rows]


# ============================================================
# EMPLOYEE READS - SUPABASE IMPLEMENTATION
# ============================================================

async def read_employees_pg(
    status_filter: List[str] = None,
    search: str = None,
    limit: int = 1000
) -> List[Dict[str, Any]]:
    """Read employees from Supabase Postgres."""
    
    conditions = []
    params = []
    param_idx = 1
    
    if status_filter:
        conditions.append(f"status = ANY(${param_idx}::text[])")
        params.append(status_filter)
        param_idx += 1
    
    if search:
        conditions.append(f"""(
            first_name ILIKE ${param_idx} OR 
            last_name ILIKE ${param_idx} OR 
            email ILIKE ${param_idx} OR
            employee_code ILIKE ${param_idx}
        )""")
        params.append(f"%{search}%")
        param_idx += 1
    
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    
    query = f"""
        SELECT 
            id, employee_code, first_name, middle_name, last_name,
            preferred_name, email, phone, role, status, branch,
            start_date, profile_photo_url, created_at, updated_at,
            completion_percentage, compliance_score,
            recruitment_approved, recruitment_approved_at
        FROM employees
        {where_clause}
        ORDER BY created_at DESC
        LIMIT ${param_idx}
    """
    params.append(limit)
    
    return await pg_fetch_all(query, *params)


async def read_employee_by_id_pg(employee_id: str) -> Optional[Dict[str, Any]]:
    """Read single employee from Supabase Postgres."""
    
    query = """
        SELECT *
        FROM employees
        WHERE id = $1
    """
    
    return await pg_fetch_one(query, employee_id)


# ============================================================
# COMPLIANCE READS - SUPABASE IMPLEMENTATION
# ============================================================

async def read_compliance_data_pg(employee_id: str) -> Dict[str, Any]:
    """Read compliance data from Supabase Postgres."""
    
    # Get documents
    docs_query = """
        SELECT id, category, document_type_name, requirement_name,
               status, verified, verified_at, expiry_date,
               file_url, original_filename, created_at
        FROM documents
        WHERE employee_id = $1 AND is_current = TRUE
        ORDER BY category, created_at DESC
    """
    documents = await pg_fetch_all(docs_query, employee_id)
    
    # Get RTW checks
    rtw_query = """
        SELECT id, method, outcome, checked_at, checked_by_name,
               follow_up_due_at, notes, is_current
        FROM rtw_checks
        WHERE employee_id = $1 AND is_current = TRUE
        ORDER BY checked_at DESC
        LIMIT 1
    """
    rtw_check = await pg_fetch_one(rtw_query, employee_id)
    
    # Get DBS checks
    dbs_query = """
        SELECT id, method, outcome, checked_at, checked_by_name,
               certificate_number, review_due_at, notes, is_current
        FROM dbs_checks
        WHERE employee_id = $1 AND is_current = TRUE
        ORDER BY checked_at DESC
        LIMIT 1
    """
    dbs_check = await pg_fetch_one(dbs_query, employee_id)
    
    # Get identity checks
    identity_query = """
        SELECT id, method, outcome, checked_at, checked_by_name, notes
        FROM identity_checks
        WHERE employee_id = $1 AND is_current = TRUE
        ORDER BY checked_at DESC
        LIMIT 1
    """
    identity_check = await pg_fetch_one(identity_query, employee_id)
    
    # Get address checks
    address_query = """
        SELECT id, verified_at, verified_by_name, verified_count,
               meets_requirement, notes
        FROM address_checks
        WHERE employee_id = $1 AND is_current = TRUE
        ORDER BY verified_at DESC
        LIMIT 1
    """
    address_check = await pg_fetch_one(address_query, employee_id)
    
    return {
        "documents": documents,
        "rtw_check": rtw_check,
        "dbs_check": dbs_check,
        "identity_check": identity_check,
        "address_check": address_check,
    }


# ============================================================
# TRAINING READS - SUPABASE IMPLEMENTATION
# ============================================================

async def read_training_records_pg(employee_id: str) -> List[Dict[str, Any]]:
    """Read training records from Supabase Postgres."""
    
    query = """
        SELECT 
            tr.id, tr.training_id, tr.completion_date, tr.expiry_date,
            tr.completion_method, tr.status, tr.verified, tr.verified_at,
            tr.is_current, tr.created_at,
            tc.code, tc.name as training_name, tc.category,
            tc.is_mandatory, tc.is_blocker, tc.validity_months
        FROM training_records tr
        LEFT JOIN training_catalogue tc ON tr.training_id = tc.id
        WHERE tr.employee_id = $1 AND tr.is_current = TRUE
        ORDER BY tc.sort_order, tc.name
    """
    
    return await pg_fetch_all(query, employee_id)


async def read_training_catalogue_pg() -> List[Dict[str, Any]]:
    """Read training catalogue from Supabase Postgres."""
    
    query = """
        SELECT id, code, name, description, category,
               is_mandatory, is_blocker, evidence_required,
               validity_months, applicable_roles, sort_order, active
        FROM training_catalogue
        WHERE active = TRUE
        ORDER BY sort_order, name
    """
    
    return await pg_fetch_all(query)


# ============================================================
# ID MAPPING HELPERS (for transition period)
# ============================================================

async def get_new_employee_id(old_mongo_id: str) -> Optional[str]:
    """Map old MongoDB employee ID to new Postgres UUID."""
    result = await pg_fetch_one(
        "SELECT new_id::text FROM migration_employee_map WHERE old_id = $1",
        old_mongo_id
    )
    return result.get("new_id") if result else None


async def get_old_employee_id(new_pg_id: str) -> Optional[str]:
    """Map new Postgres UUID to old MongoDB ID (for fallback)."""
    result = await pg_fetch_one(
        "SELECT old_id FROM migration_employee_map WHERE new_id = $1",
        new_pg_id
    )
    return result.get("old_id") if result else None


# ============================================================
# SOURCE STATUS ENDPOINT DATA
# ============================================================

def get_source_status() -> Dict[str, Any]:
    """Get current read source configuration status."""
    return {
        "flags": {k: v for k, v in READ_SOURCE_FLAGS.items()},
        "supabase_db_configured": bool(os.environ.get("SUPABASE_DB_URL")),
        "pool_initialized": _pg_pool is not None,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
