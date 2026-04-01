# Backend Switch Plan: MongoDB to Supabase

**Purpose**: Step-by-step guide to switch `server.py` from MongoDB (Motor) to Supabase (Postgres).  
**Scope**: Code-level changes only. No architecture diagrams.

---

## Phase 1: Prerequisites

### 1.1 Install Dependencies
```bash
pip install supabase asyncpg python-dotenv
```

### 1.2 Add Environment Variables
```bash
# backend/.env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-key  # For admin operations
SUPABASE_DB_URL=postgresql://postgres:password@db.your-project.supabase.co:5432/postgres
```

### 1.3 Run Migration Scripts
```bash
cd /app/migration
python run_migration.py --start 1 --end 10
```

---

## Phase 2: Database Client Setup

### 2.1 Current MongoDB Setup (to remove)
```python
# Current code in server.py
from motor.motor_asyncio import AsyncIOMotorClient
client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]
```

### 2.2 New Supabase Setup (to add)
```python
# Add new imports
from supabase import create_client, Client
import asyncpg
from functools import lru_cache

# Initialize Supabase client (for REST API calls)
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
SUPABASE_DB_URL = os.environ.get("SUPABASE_DB_URL")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
supabase_admin: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Connection pool for direct Postgres queries (better for complex queries)
pg_pool: asyncpg.Pool = None

@app.on_event("startup")
async def startup():
    global pg_pool
    pg_pool = await asyncpg.create_pool(SUPABASE_DB_URL, min_size=5, max_size=20)

@app.on_event("shutdown")
async def shutdown():
    await pg_pool.close()
```

---

## Phase 3: ID Migration Pattern

### 3.1 Problem: MongoDB uses string IDs, Postgres uses UUIDs
```python
# Old MongoDB pattern
employee_id = "abc123-string-id"
result = await db.employees.find_one({"id": employee_id})

# New Postgres pattern - UUIDs
from uuid import UUID
employee_id = UUID("550e8400-e29b-41d4-a716-446655440000")
```

### 3.2 Lookup Helper (during transition)
```python
async def get_new_id(old_id: str, entity_type: str) -> str:
    """Map old MongoDB ID to new Postgres UUID."""
    table_map = {
        "user": "migration_user_map",
        "employee": "migration_employee_map",
        "document": "migration_document_map",
    }
    table = table_map.get(entity_type)
    if not table:
        return old_id
    
    async with pg_pool.acquire() as conn:
        result = await conn.fetchval(
            f"SELECT new_id::text FROM {table} WHERE old_id = $1", old_id
        )
    return result or old_id
```

---

## Phase 4: Query Translation Patterns

### 4.1 Find One
```python
# MongoDB
employee = await db.employees.find_one({"id": emp_id}, {"_id": 0})

# Supabase REST
result = supabase.table("employees").select("*").eq("id", emp_id).single().execute()
employee = result.data

# Supabase asyncpg (recommended for speed)
async with pg_pool.acquire() as conn:
    employee = await conn.fetchrow(
        "SELECT * FROM employees WHERE id = $1", emp_id
    )
    employee = dict(employee) if employee else None
```

### 4.2 Find Many with Filter
```python
# MongoDB
employees = await db.employees.find(
    {"status": "active", "branch": branch},
    {"_id": 0}
).sort("created_at", -1).to_list(100)

# Supabase REST
result = supabase.table("employees") \
    .select("*") \
    .eq("status", "active") \
    .eq("branch", branch) \
    .order("created_at", desc=True) \
    .limit(100) \
    .execute()
employees = result.data

# Supabase asyncpg
async with pg_pool.acquire() as conn:
    rows = await conn.fetch("""
        SELECT * FROM employees 
        WHERE status = $1 AND branch = $2
        ORDER BY created_at DESC
        LIMIT 100
    """, "active", branch)
    employees = [dict(r) for r in rows]
```

### 4.3 Insert One
```python
# MongoDB
result = await db.employees.insert_one(employee_data)
new_id = str(result.inserted_id)

# Supabase REST
result = supabase.table("employees").insert(employee_data).execute()
new_id = result.data[0]["id"]

# Supabase asyncpg
async with pg_pool.acquire() as conn:
    new_id = await conn.fetchval("""
        INSERT INTO employees (first_name, last_name, email, status)
        VALUES ($1, $2, $3, $4)
        RETURNING id
    """, data["first_name"], data["last_name"], data["email"], "new")
```

### 4.4 Update One
```python
# MongoDB
await db.employees.update_one(
    {"id": emp_id},
    {"$set": {"status": "active", "updated_at": datetime.now(timezone.utc)}}
)

# Supabase REST
supabase.table("employees") \
    .update({"status": "active", "updated_at": datetime.now(timezone.utc).isoformat()}) \
    .eq("id", emp_id) \
    .execute()

# Supabase asyncpg
async with pg_pool.acquire() as conn:
    await conn.execute("""
        UPDATE employees SET status = $1, updated_at = $2 WHERE id = $3
    """, "active", datetime.now(timezone.utc), emp_id)
```

### 4.5 Delete One
```python
# MongoDB
await db.employees.delete_one({"id": emp_id})

# Supabase REST
supabase.table("employees").delete().eq("id", emp_id).execute()

# Supabase asyncpg
async with pg_pool.acquire() as conn:
    await conn.execute("DELETE FROM employees WHERE id = $1", emp_id)
```

### 4.6 Aggregation / Count
```python
# MongoDB
count = await db.employees.count_documents({"status": "active"})

# Supabase REST
result = supabase.table("employees").select("id", count="exact").eq("status", "active").execute()
count = result.count

# Supabase asyncpg
async with pg_pool.acquire() as conn:
    count = await conn.fetchval(
        "SELECT COUNT(*) FROM employees WHERE status = $1", "active"
    )
```

---

## Phase 5: Specific Endpoint Migrations

### 5.1 Employee CRUD Example

**Before (MongoDB):**
```python
@app.get("/api/employees/{employee_id}")
async def get_employee(employee_id: str, current_user: dict = Depends(get_current_user)):
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee
```

**After (Supabase):**
```python
@app.get("/api/employees/{employee_id}")
async def get_employee(employee_id: str, current_user: dict = Depends(get_current_user)):
    async with pg_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM employees WHERE id = $1", employee_id
        )
    if not row:
        raise HTTPException(status_code=404, detail="Employee not found")
    return dict(row)
```

### 5.2 Document Upload Example

**Before (MongoDB):**
```python
doc_data = {
    "id": str(uuid4()),
    "employee_id": employee_id,
    "category": category,
    "file_url": file_url,
    "created_at": datetime.now(timezone.utc),
}
await db.employee_documents.insert_one(doc_data)
```

**After (Supabase):**
```python
async with pg_pool.acquire() as conn:
    doc_id = await conn.fetchval("""
        INSERT INTO documents (employee_id, category, file_url, created_at)
        VALUES ($1, $2::document_category, $3, $4)
        RETURNING id
    """, employee_id, category, file_url, datetime.now(timezone.utc))
```

### 5.3 Verification Check Example (Dual-Row Pattern)

**Before (MongoDB):**
```python
# Create RTW check
check_data = {
    "id": str(uuid4()),
    "employee_id": employee_id,
    "method": "share_code_online_check",
    "outcome": "verified",
    "checked_at": datetime.now(timezone.utc),
    "checked_by": current_user["user_id"],
}
await db.rtw_checks.insert_one(check_data)
```

**After (Supabase):**
```python
async with pg_pool.acquire() as conn:
    # Mark old check as superseded
    await conn.execute("""
        UPDATE rtw_checks 
        SET is_current = FALSE, superseded_at = $1
        WHERE employee_id = $2 AND is_current = TRUE
    """, datetime.now(timezone.utc), employee_id)
    
    # Insert new check
    check_id = await conn.fetchval("""
        INSERT INTO rtw_checks (
            employee_id, method, outcome, checked_at, checked_by, 
            proof_document_id, is_current
        )
        VALUES ($1, $2::check_method, $3::verification_outcome, $4, $5, $6, TRUE)
        RETURNING id
    """, employee_id, method, outcome, datetime.now(timezone.utc), 
        current_user_id, proof_doc_id)
```

---

## Phase 6: Authentication Migration

### 6.1 Current JWT Auth (keep for now)
The existing JWT-based auth can remain unchanged initially. Later, you can optionally migrate to Supabase Auth.

### 6.2 User Lookup Change
```python
# Before
user = await db.users.find_one({"email": email}, {"_id": 0})

# After
async with pg_pool.acquire() as conn:
    user = await conn.fetchrow(
        "SELECT * FROM profiles WHERE email = $1", email
    )
    user = dict(user) if user else None
```

---

## Phase 7: File Changes Summary

### Files to Modify
| File | Changes |
|------|---------|
| `backend/server.py` | Replace Motor with Supabase/asyncpg |
| `backend/.env` | Add SUPABASE_* variables |
| `backend/requirements.txt` | Add `supabase`, `asyncpg` |

### Functions to Update (High Priority)
These functions have the most MongoDB calls and should be migrated first:

1. **Employee CRUD**: `get_employee`, `create_employee`, `update_employee`
2. **Documents**: `upload_document`, `get_documents`, `verify_document`
3. **Verification Checks**: `create_rtw_check`, `create_dbs_check`, etc.
4. **Training**: `get_training_records`, `update_training_record`
5. **References**: `get_references`, `submit_reference_response`
6. **Forms**: `submit_form`, `get_form_submissions`
7. **Audit Logging**: `log_action` (update to use Postgres)

---

## Phase 8: Rollback Strategy

### 8.1 Keep MongoDB Running
During migration, keep MongoDB running as read-only backup.

### 8.2 Feature Flag Approach
```python
USE_SUPABASE = os.environ.get("USE_SUPABASE", "false").lower() == "true"

async def get_employee(employee_id: str):
    if USE_SUPABASE:
        return await _get_employee_pg(employee_id)
    else:
        return await _get_employee_mongo(employee_id)
```

### 8.3 Quick Rollback
```bash
# Set env var to switch back to MongoDB
USE_SUPABASE=false
sudo supervisorctl restart backend
```

---

## Phase 9: Testing Checklist

Before going live:
- [ ] Run migration scripts successfully
- [ ] Test all CRUD operations for employees
- [ ] Test document upload/download
- [ ] Test all verification check types (RTW, DBS, Identity, Address)
- [ ] Test reference request/response flow
- [ ] Test training record updates
- [ ] Test form submissions
- [ ] Test audit log capture
- [ ] Test login/authentication
- [ ] Verify data consistency between old and new

---

## Phase 10: Go-Live Steps

1. **Staging Test**
   ```bash
   # Run full migration on staging
   python run_migration.py
   
   # Validate counts
   python run_validation.py
   ```

2. **Production Cutover**
   ```bash
   # Put app in maintenance mode
   # Run migration
   python run_migration.py
   
   # Update .env
   USE_SUPABASE=true
   
   # Restart
   sudo supervisorctl restart backend frontend
   
   # Validate
   python run_validation.py
   ```

3. **Monitor**
   - Check error logs
   - Verify API response times
   - Confirm data consistency

---

## Quick Reference: Collection to Table Mapping

| MongoDB Collection | Postgres Table |
|-------------------|----------------|
| `users` | `profiles` |
| `employees` | `employees` |
| `employee_documents` | `documents` |
| `rtw_checks` | `rtw_checks` |
| `dbs_checks` | `dbs_checks` |
| `identity_checks` | `identity_checks` |
| `address_checks` | `address_checks` |
| `training_catalogue` | `training_catalogue` |
| `training_records` | `training_records` |
| `form_submissions` | `form_submissions` |
| `agreement_acknowledgements` | `agreement_acknowledgements` |
| `org_policies` | `org_policies` |
| `insurance_docs` | `org_certificates` |
| `audit_logs` | `audit_logs` |
