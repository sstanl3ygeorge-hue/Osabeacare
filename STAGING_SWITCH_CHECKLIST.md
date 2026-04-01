# STAGING VERIFICATION & SWITCH CHECKLIST
## MongoDB → Supabase Read Migration

**Date:** 2026-04-01  
**Status:** EXECUTION PHASE  
**Risk Level:** HIGH (Compliance Data)

---

# PART 1 — PRE-SWITCH VALIDATION

## 1.1 Data Integrity Checks

### A. Record Count Validation

```bash
# Run from /app/migration directory
python3 << 'EOF'
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import asyncpg
import os

async def validate_counts():
    # MongoDB
    mongo = AsyncIOMotorClient(os.environ.get('MONGO_URL', 'mongodb://localhost:27017'))
    mdb = mongo[os.environ.get('DB_NAME', 'test_database')]
    
    # Supabase
    pg = await asyncpg.connect(os.environ.get('SUPABASE_DB_URL'))
    
    checks = [
        ("employees", "employees"),
        ("users", "profiles"),
        ("employee_documents", "documents"),
        ("training_records", "training_records"),
        ("training_catalogue", "training_catalogue"),
        ("rtw_checks", "rtw_checks"),
        ("dbs_checks", "dbs_checks"),
        ("identity_verifications", "identity_checks"),
        ("address_verifications", "address_checks"),
        ("audit_logs", "audit_logs"),
    ]
    
    print("=" * 60)
    print("RECORD COUNT VALIDATION")
    print("=" * 60)
    print(f"{'Collection/Table':<30} {'Mongo':>8} {'Supabase':>8} {'Status':>8}")
    print("-" * 60)
    
    all_pass = True
    for mongo_col, pg_table in checks:
        try:
            mongo_count = await mdb[mongo_col].count_documents({})
        except:
            mongo_count = 0
        
        try:
            pg_count = await pg.fetchval(f"SELECT COUNT(*) FROM {pg_table}")
        except:
            pg_count = 0
        
        status = "PASS" if mongo_count == pg_count else "FAIL"
        if status == "FAIL":
            all_pass = False
        
        print(f"{mongo_col:<30} {mongo_count:>8} {pg_count:>8} {status:>8}")
    
    print("-" * 60)
    print(f"OVERALL: {'PASS' if all_pass else 'FAIL'}")
    
    mongo.close()
    await pg.close()

asyncio.run(validate_counts())
EOF
```

**PASS Criteria:**
- [ ] All counts match within 1% (migration timing variance)
- [ ] No table has 0 records when Mongo has >0

**FAIL Criteria:**
- [ ] Any count mismatch >5%
- [ ] Any critical table (employees, documents, checks) has 0 records

---

### B. Required Fields Validation

```bash
# Check employees required fields
python3 << 'EOF'
import asyncio
import asyncpg
import os

REQUIRED_EMPLOYEE_FIELDS = [
    'id', 'first_name', 'last_name', 'email', 'status', 'created_at'
]

async def check_required_fields():
    pg = await asyncpg.connect(os.environ.get('SUPABASE_DB_URL'))
    
    print("=" * 60)
    print("REQUIRED FIELDS VALIDATION - EMPLOYEES")
    print("=" * 60)
    
    for field in REQUIRED_EMPLOYEE_FIELDS:
        null_count = await pg.fetchval(f"""
            SELECT COUNT(*) FROM employees WHERE {field} IS NULL
        """)
        status = "PASS" if null_count == 0 else f"FAIL ({null_count} nulls)"
        print(f"  {field}: {status}")
    
    await pg.close()

asyncio.run(check_required_fields())
EOF
```

**PASS Criteria:**
- [ ] Zero NULL values in: id, first_name, last_name, email, status
- [ ] created_at populated for all records

---

## 1.2 Relationship Integrity Checks

### A. Employee → Documents

```bash
python3 << 'EOF'
import asyncio
import asyncpg
import os

async def check_employee_documents():
    pg = await asyncpg.connect(os.environ.get('SUPABASE_DB_URL'))
    
    # Orphan documents (no matching employee)
    orphans = await pg.fetchval("""
        SELECT COUNT(*) FROM documents d
        WHERE NOT EXISTS (SELECT 1 FROM employees e WHERE e.id = d.employee_id)
    """)
    
    # Documents per employee (sanity check)
    doc_stats = await pg.fetchrow("""
        SELECT 
            COUNT(DISTINCT employee_id) as employees_with_docs,
            AVG(doc_count) as avg_docs_per_emp
        FROM (
            SELECT employee_id, COUNT(*) as doc_count
            FROM documents
            GROUP BY employee_id
        ) sub
    """)
    
    print("=" * 60)
    print("EMPLOYEE → DOCUMENTS RELATIONSHIP")
    print("=" * 60)
    print(f"  Orphan documents: {orphans} {'PASS' if orphans == 0 else 'FAIL'}")
    print(f"  Employees with docs: {doc_stats['employees_with_docs']}")
    print(f"  Avg docs per employee: {doc_stats['avg_docs_per_emp']:.1f}")
    
    await pg.close()

asyncio.run(check_employee_documents())
EOF
```

### B. Checks → Proof Documents

```bash
python3 << 'EOF'
import asyncio
import asyncpg
import os

async def check_proof_links():
    pg = await asyncpg.connect(os.environ.get('SUPABASE_DB_URL'))
    
    print("=" * 60)
    print("CHECK → PROOF DOCUMENT LINKS")
    print("=" * 60)
    
    checks = [
        ("rtw_checks", "proof_document_id"),
        ("dbs_checks", "proof_document_id"),
        ("identity_checks", "proof_document_id"),
    ]
    
    for table, fk_col in checks:
        # Check for broken links
        broken = await pg.fetchval(f"""
            SELECT COUNT(*) FROM {table} c
            WHERE c.{fk_col} IS NOT NULL
            AND NOT EXISTS (SELECT 1 FROM documents d WHERE d.id = c.{fk_col})
        """)
        
        # Count with proof
        with_proof = await pg.fetchval(f"""
            SELECT COUNT(*) FROM {table} WHERE {fk_col} IS NOT NULL
        """)
        
        total = await pg.fetchval(f"SELECT COUNT(*) FROM {table}")
        
        status = "PASS" if broken == 0 else f"FAIL ({broken} broken)"
        print(f"  {table}: {with_proof}/{total} have proof, broken links: {status}")
    
    await pg.close()

asyncio.run(check_proof_links())
EOF
```

**PASS Criteria:**
- [ ] Zero orphan documents
- [ ] Zero broken proof_document_id links
- [ ] Check tables have expected proof attachment rates

---

## 1.3 Compliance Model Integrity (CRITICAL)

### A. Evidence vs Check Separation

```bash
python3 << 'EOF'
import asyncio
import asyncpg
import os

async def validate_dual_row_model():
    pg = await asyncpg.connect(os.environ.get('SUPABASE_DB_URL'))
    
    print("=" * 60)
    print("DUAL-ROW MODEL VALIDATION (CRITICAL)")
    print("=" * 60)
    
    # 1. Evidence documents should NOT be in verification_proof category
    evidence_categories = ['right_to_work', 'dbs', 'identity', 'proof_of_address', 'training', 'cv']
    
    for cat in evidence_categories:
        count = await pg.fetchval(f"""
            SELECT COUNT(*) FROM documents 
            WHERE category = '{cat}' AND is_current = TRUE
        """)
        print(f"  Evidence [{cat}]: {count} documents")
    
    # 2. Proof documents should be verification_proof
    proof_count = await pg.fetchval("""
        SELECT COUNT(*) FROM documents 
        WHERE category = 'verification_proof' AND is_current = TRUE
    """)
    print(f"  Proof documents [verification_proof]: {proof_count}")
    
    # 3. Check rows exist and are separate from documents
    for check_table in ['rtw_checks', 'dbs_checks', 'identity_checks', 'address_checks']:
        check_count = await pg.fetchval(f"SELECT COUNT(*) FROM {check_table} WHERE is_current = TRUE")
        print(f"  Check records [{check_table}]: {check_count}")
    
    # 4. CRITICAL: Verify no proof documents appear as evidence
    misclassified = await pg.fetchval("""
        SELECT COUNT(*) FROM documents d
        WHERE d.category = 'verification_proof'
        AND d.id IN (
            -- These should NOT be linked as evidence in employee profile
            SELECT id FROM documents WHERE requirement_name IS NOT NULL
        )
    """)
    
    print("-" * 60)
    if misclassified > 0:
        print(f"  CRITICAL FAIL: {misclassified} proof documents misclassified as evidence")
    else:
        print("  PASS: Evidence/Check/Proof separation intact")
    
    await pg.close()

asyncio.run(validate_dual_row_model())
EOF
```

**PASS Criteria:**
- [ ] Evidence documents in correct categories
- [ ] Proof documents in 'verification_proof' category
- [ ] Check tables have records separate from documents
- [ ] Zero proof documents appearing as evidence

**FAIL = STOP MIGRATION:**
- [ ] Any proof documents misclassified as evidence
- [ ] Check records missing when documents exist

---

## 1.4 File Access Validation

```bash
python3 << 'EOF'
import asyncio
import asyncpg
import os
import aiohttp

async def validate_file_access():
    pg = await asyncpg.connect(os.environ.get('SUPABASE_DB_URL'))
    
    print("=" * 60)
    print("FILE ACCESS VALIDATION")
    print("=" * 60)
    
    # Sample 5 documents with file_url
    docs = await pg.fetch("""
        SELECT id, file_url, original_filename, category
        FROM documents
        WHERE file_url IS NOT NULL
        LIMIT 5
    """)
    
    async with aiohttp.ClientSession() as session:
        for doc in docs:
            try:
                async with session.head(doc['file_url'], timeout=5) as resp:
                    status = "PASS" if resp.status == 200 else f"FAIL ({resp.status})"
            except Exception as e:
                status = f"FAIL ({str(e)[:30]})"
            
            print(f"  [{doc['category']}] {doc['original_filename'][:30]}: {status}")
    
    await pg.close()

asyncio.run(validate_file_access())
EOF
```

**PASS Criteria:**
- [ ] All sampled file URLs return 200
- [ ] No broken links in proof documents

---

# PART 2 — STEP-BY-STEP READ SWITCH PLAN

## SWITCH ORDER (MANDATORY)

```
1. Employees List      → Lowest risk, easy to verify
2. Employee Profile    → Single record, more fields
3. Compliance File     → Complex, depends on checks
4. Training            → Catalogue + records
```

---

## Step 1: EMPLOYEES LIST

### Pre-Switch Verification
```bash
# Verify counts match
curl -s "$API_URL/api/employees" -H "Authorization: Bearer $TOKEN" | \
  python3 -c "import sys,json; print(f'Mongo count: {len(json.load(sys.stdin))}')"
```

### Switch Command
```bash
# Edit /app/backend/.env
READ_SOURCE_EMPLOYEES=supabase

# Restart backend
sudo supervisorctl restart backend
```

### Immediate Test
```bash
# Must return same count
curl -s "$API_URL/api/employees" -H "Authorization: Bearer $TOKEN" | \
  python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Supabase count: {len(d)}')"

# Check logs
tail -20 /var/log/supervisor/backend.err.log | grep "\[SOURCE:EMPLOYEES\]"
```

### Expected Log Output
```
[SOURCE:EMPLOYEES] GET /employees -> SUPABASE (records=12, latency=45.2ms)
```

### FAILURE Indicators
- [ ] Record count differs
- [ ] Latency >500ms
- [ ] Log shows `FALLBACK`
- [ ] Any 500 errors

### Rollback
```bash
READ_SOURCE_EMPLOYEES=mongo
sudo supervisorctl restart backend
```

---

## Step 2: EMPLOYEE PROFILE

### Pre-Switch Verification
```bash
EMP_ID="d88335f6-1b18-435a-8086-28af4a583f77"

# Get Mongo response shape
curl -s "$API_URL/api/employees/$EMP_ID" -H "Authorization: Bearer $TOKEN" > /tmp/emp_mongo.json
```

### Switch Command
```bash
# Employees list should already be on Supabase
# Profile shares the same flag
# Already switched in Step 1
```

### Immediate Test
```bash
# Get profile
curl -s "$API_URL/api/employees/$EMP_ID" -H "Authorization: Bearer $TOKEN" > /tmp/emp_supa.json

# Compare key fields
python3 << 'EOF'
import json

with open('/tmp/emp_mongo.json') as f:
    mongo = json.load(f)
with open('/tmp/emp_supa.json') as f:
    supa = json.load(f)

critical_fields = ['id', 'first_name', 'last_name', 'email', 'status', 'role']
print("FIELD COMPARISON:")
for field in critical_fields:
    m_val = mongo.get(field)
    s_val = supa.get(field)
    status = "MATCH" if m_val == s_val else f"DIFFER: {m_val} vs {s_val}"
    print(f"  {field}: {status}")
EOF
```

### Expected Log Output
```
[SOURCE:EMPLOYEES] GET /employees/{id} -> SUPABASE (records=1, emp=d88335f6..., latency=25.3ms)
```

### FAILURE Indicators
- [ ] Profile returns 404
- [ ] Critical fields differ
- [ ] work_readiness_3tier missing
- [ ] person_stage missing

### Rollback
```bash
READ_SOURCE_EMPLOYEES=mongo
sudo supervisorctl restart backend
```

---

## Step 3: COMPLIANCE FILE

### Pre-Switch Verification
```bash
EMP_ID="d88335f6-1b18-435a-8086-28af4a583f77"

# Get Mongo compliance structure
curl -s "$API_URL/api/employees/$EMP_ID/compliance" -H "Authorization: Bearer $TOKEN" > /tmp/comp_mongo.json
```

### Switch Command
```bash
# Edit /app/backend/.env
READ_SOURCE_COMPLIANCE=supabase

# Restart backend
sudo supervisorctl restart backend
```

### Immediate Test
```bash
curl -s "$API_URL/api/employees/$EMP_ID/compliance" -H "Authorization: Bearer $TOKEN" > /tmp/comp_supa.json

# Validate structure
python3 << 'EOF'
import json

with open('/tmp/comp_mongo.json') as f:
    mongo = json.load(f)
with open('/tmp/comp_supa.json') as f:
    supa = json.load(f)

print("COMPLIANCE STRUCTURE VALIDATION:")
print(f"  employee_id match: {mongo.get('employee_id') == supa.get('employee_id')}")
print(f"  work_readiness_3tier present: {'work_readiness_3tier' in supa}")

# Check nested compliance object
m_comp = mongo.get('compliance', {})
s_comp = supa.get('compliance', {})

critical = ['completion_percentage', 'work_readiness_3tier']
for key in critical:
    m_val = m_comp.get(key)
    s_val = s_comp.get(key)
    status = "MATCH" if m_val == s_val else f"DIFFER"
    print(f"  compliance.{key}: {status}")
EOF
```

### Expected Log Output
```
[SOURCE:COMPLIANCE] GET /employees/{id}/compliance -> SUPABASE (records=1, emp=d88335f6..., latency=35.0ms)
```

### FAILURE Indicators (CRITICAL)
- [ ] work_readiness_3tier differs
- [ ] Missing evidence items
- [ ] Incorrect check counts
- [ ] Proof documents appearing in wrong section

### Rollback
```bash
READ_SOURCE_COMPLIANCE=mongo
sudo supervisorctl restart backend
```

---

## Step 4: TRAINING

### Pre-Switch Verification
```bash
EMP_ID="d88335f6-1b18-435a-8086-28af4a583f77"

curl -s "$API_URL/api/employees/$EMP_ID/training" -H "Authorization: Bearer $TOKEN" > /tmp/train_mongo.json
```

### Switch Command
```bash
# Edit /app/backend/.env
READ_SOURCE_TRAINING=supabase

# Restart backend
sudo supervisorctl restart backend
```

### Immediate Test
```bash
curl -s "$API_URL/api/employees/$EMP_ID/training" -H "Authorization: Bearer $TOKEN" > /tmp/train_supa.json

python3 << 'EOF'
import json

with open('/tmp/train_mongo.json') as f:
    mongo = json.load(f)
with open('/tmp/train_supa.json') as f:
    supa = json.load(f)

print("TRAINING STRUCTURE VALIDATION:")
print(f"  overall status match: {mongo.get('overall') == supa.get('overall')}")
print(f"  item count: Mongo={len(mongo.get('items',[]))} Supa={len(supa.get('items',[]))}")
print(f"  blockerCount match: {mongo.get('blockerCount') == supa.get('blockerCount')}")
EOF
```

### Expected Log Output
```
[SOURCE:TRAINING] GET /employees/{id}/training -> SUPABASE (records=6, emp=d88335f6..., latency=15.0ms)
```

### FAILURE Indicators
- [ ] Item count differs
- [ ] blockerCount differs (CRITICAL - affects work readiness)
- [ ] Missing required training items

### Rollback
```bash
READ_SOURCE_TRAINING=mongo
sudo supervisorctl restart backend
```

---

# PART 3 — RESPONSE SHAPE VALIDATION

## Required Response Structures

### Employees List Response
```json
{
  "id": "uuid (REQUIRED)",
  "first_name": "string (REQUIRED)",
  "last_name": "string (REQUIRED)",
  "email": "string (REQUIRED)",
  "status": "string (REQUIRED) - new|screening|interview|compliance_review|onboarding|active|inactive",
  "role": "string",
  "branch": "string",
  "completion_percentage": "number",
  "work_readiness": "object",
  "work_readiness_3tier": "object (REQUIRED)",
  "person_stage": "string (REQUIRED) - applicant|employee",
  "created_at": "ISO timestamp"
}
```

**If Missing → Frontend Breakage:**
- `work_readiness_3tier` → Status badges won't render
- `person_stage` → List filtering breaks
- `status` → Stage routing breaks

### Employee Profile Response
```json
{
  "id": "uuid (REQUIRED)",
  "first_name": "string (REQUIRED)",
  "last_name": "string (REQUIRED)",
  "email": "string (REQUIRED)",
  "status": "string (REQUIRED)",
  "date_of_birth": "string or null",
  "ni_number": "string or null",
  "phone": "string or null",
  "address_line_1": "string or null",
  "city": "string or null",
  "postcode": "string or null",
  "completion_percentage": "number (REQUIRED)",
  "work_readiness_3tier": "object (REQUIRED)",
  "person_stage": "string (REQUIRED)"
}
```

**If Missing → Frontend Breakage:**
- `completion_percentage` → Progress bar breaks
- `work_readiness_3tier` → Profile header breaks

### Compliance Response
```json
{
  "employee_id": "string (REQUIRED)",
  "employee_name": "string (REQUIRED)",
  "role": "string",
  "current_onboarding_status": "string",
  "derived_onboarding_status": "string",
  "compliance": {
    "completion_percentage": "number (REQUIRED)",
    "work_readiness_3tier": "object (REQUIRED)",
    "items": "array (REQUIRED)"
  },
  "work_readiness_3tier": "object (REQUIRED)"
}
```

**If Missing → Frontend Breakage:**
- `compliance.items` → DualRowComplianceSection breaks
- `work_readiness_3tier` → Status calculations break

### Training Response
```json
{
  "overall": "string (REQUIRED) - current|due_soon|overdue|missing",
  "blockerCount": "number (REQUIRED)",
  "warningCount": "number (REQUIRED)",
  "items": [
    {
      "code": "string (REQUIRED)",
      "title": "string (REQUIRED)",
      "status": "string (REQUIRED)",
      "blocker": "boolean (REQUIRED)",
      "expires_at": "string or null"
    }
  ]
}
```

**If Missing → Frontend Breakage:**
- `blockerCount` → Work readiness calculation breaks
- `items[].blocker` → TrainingMatrix breaks

---

# PART 4 — LIVE LOG MONITORING RULES

## Log Patterns to Watch

### Good Patterns
```
[SOURCE:EMPLOYEES] GET /employees -> SUPABASE (records=12, latency=45.2ms)
[SOURCE:EMPLOYEES] GET /employees/{id} -> SUPABASE (records=1, emp=d88335f6..., latency=18.5ms)
[SOURCE:COMPLIANCE] GET /employees/{id}/compliance -> SUPABASE (records=1, latency=32.0ms)
```

### Warning Patterns
```
# High latency (>200ms for list, >100ms for single record)
[SOURCE:EMPLOYEES] GET /employees -> SUPABASE (records=12, latency=350.2ms)

# Fallback triggered
[SOURCE:EMPLOYEES] GET /employees -> MONGO (records=12, latency=30.0ms, FALLBACK)
```

### Error Patterns
```
# Zero records when expecting data
[SOURCE:EMPLOYEES] GET /employees -> SUPABASE (records=0, latency=15.0ms)

# Connection errors in logs
asyncpg.exceptions.ConnectionDoesNotExistError
asyncpg.exceptions.InvalidPasswordError
```

## Latency Thresholds

| Endpoint | Expected | Warning | Failure |
|----------|----------|---------|---------|
| GET /employees | <100ms | >200ms | >500ms |
| GET /employees/{id} | <50ms | >100ms | >200ms |
| GET /compliance | <100ms | >200ms | >500ms |
| GET /training | <50ms | >100ms | >200ms |

## Monitoring Commands

```bash
# Watch for source switching in real-time
tail -f /var/log/supervisor/backend.err.log | grep "\[SOURCE:"

# Count by source
tail -1000 /var/log/supervisor/backend.err.log | grep "\[SOURCE:" | \
  grep -o "-> [A-Z]*" | sort | uniq -c

# Check for fallbacks
tail -1000 /var/log/supervisor/backend.err.log | grep "FALLBACK" | wc -l
```

---

# PART 5 — FAILURE & ROLLBACK RULES

## Immediate Rollback Triggers

| Trigger | Detection | Rollback Action |
|---------|-----------|-----------------|
| Zero records returned | `records=0` in logs | Set flag to `mongo`, restart |
| Repeated fallbacks | >3 fallbacks in 1 min | Set flag to `mongo`, restart |
| 500 errors | HTTP 500 on endpoint | Set flag to `mongo`, restart |
| Data mismatch | Response validation fails | Set flag to `mongo`, restart |
| Work readiness wrong | 3-tier status differs | Set flag to `mongo`, restart |
| Missing compliance items | Empty items array | Set flag to `mongo`, restart |

## Rollback Procedure

### Single Entity Rollback
```bash
# 1. Change flag
echo "READ_SOURCE_EMPLOYEES=mongo" >> /app/backend/.env

# 2. Restart
sudo supervisorctl restart backend

# 3. Verify
tail -10 /var/log/supervisor/backend.err.log | grep "\[SOURCE:EMPLOYEES\]"
# Should show: -> MONGO

# 4. Test endpoint
curl -s "$API_URL/api/employees" -H "Authorization: Bearer $TOKEN" | \
  python3 -c "import sys,json; print(f'Count: {len(json.load(sys.stdin))}')"
```

### Full Rollback (All Entities)
```bash
# 1. Reset all flags
cat > /tmp/rollback_flags.txt << 'EOF'
READ_SOURCE_EMPLOYEES=mongo
READ_SOURCE_COMPLIANCE=mongo
READ_SOURCE_TRAINING=mongo
READ_SOURCE_DOCUMENTS=mongo
EOF

# 2. Apply
grep -v "^READ_SOURCE" /app/backend/.env > /tmp/env_clean
cat /tmp/env_clean /tmp/rollback_flags.txt > /app/backend/.env

# 3. Restart
sudo supervisorctl restart backend

# 4. Verify all on Mongo
curl -s "$API_URL/api/admin/read-source-status" -H "Authorization: Bearer $TOKEN" | \
  python3 -m json.tool
```

## Post-Rollback Verification
```bash
# Run test suite against Mongo
EMP_ID="d88335f6-1b18-435a-8086-28af4a583f77"

curl -s "$API_URL/api/employees" -H "Authorization: Bearer $TOKEN" | \
  python3 -c "import sys,json; print(f'employees: {len(json.load(sys.stdin))}')"

curl -s "$API_URL/api/employees/$EMP_ID" -H "Authorization: Bearer $TOKEN" | \
  python3 -c "import sys,json; print(f'profile: {json.load(sys.stdin).get(\"email\")}')"

curl -s "$API_URL/api/employees/$EMP_ID/compliance" -H "Authorization: Bearer $TOKEN" | \
  python3 -c "import sys,json; print(f'compliance: {json.load(sys.stdin).get(\"work_readiness_3tier\",{}).get(\"status\")}')"

curl -s "$API_URL/api/employees/$EMP_ID/training" -H "Authorization: Bearer $TOKEN" | \
  python3 -c "import sys,json; print(f'training: {json.load(sys.stdin).get(\"overall\")}')"
```

---

# PART 6 — FINAL GO/NO-GO CRITERIA

## Before Enabling All Supabase Reads

### MUST BE TRUE:
- [ ] All record counts match (Part 1.1)
- [ ] Zero orphan documents (Part 1.2)
- [ ] Zero broken FK links (Part 1.2)
- [ ] Dual-row model intact - no evidence/proof mixing (Part 1.3)
- [ ] All file URLs resolve (Part 1.4)
- [ ] Employees list tested for 24 hours with zero fallbacks
- [ ] Employee profile tested for 24 hours
- [ ] Compliance response matches exactly
- [ ] Training response matches exactly
- [ ] Average latency <100ms for all endpoints
- [ ] Zero 500 errors in 24 hours

### GO Criteria:
```
All above checkboxes checked → PROCEED with full Supabase reads
```

### NO-GO Criteria:
```
Any checkbox failed → STOP, investigate, rollback if needed
```

---

## Before Removing Mongo from Read Path

### MUST BE TRUE (in addition to above):
- [ ] All reads on Supabase for 7+ days
- [ ] Zero fallbacks in 7 days
- [ ] Frontend tested by users, no reported issues
- [ ] Work readiness calculations verified correct
- [ ] DBS/RTW check workflows tested end-to-end
- [ ] Document upload/view tested
- [ ] Proof document linking verified
- [ ] All compliance sections render correctly
- [ ] Training matrix displays correctly
- [ ] MongoDB kept as read-only backup for 30 days

### HARD STOP Criteria:
```
Any compliance data incorrectly displayed → DO NOT remove Mongo
Any work readiness calculation wrong → DO NOT remove Mongo
Any CQC-critical field missing → DO NOT remove Mongo
```

---

# QUICK REFERENCE CARD

## Flag Values
```bash
# MongoDB (default/safe)
READ_SOURCE_EMPLOYEES=mongo
READ_SOURCE_COMPLIANCE=mongo
READ_SOURCE_TRAINING=mongo
READ_SOURCE_DOCUMENTS=mongo

# Supabase (gradual switch)
READ_SOURCE_EMPLOYEES=supabase
READ_SOURCE_COMPLIANCE=supabase
READ_SOURCE_TRAINING=supabase
READ_SOURCE_DOCUMENTS=supabase
```

## Status Check
```bash
curl -s "$API_URL/api/admin/read-source-status" -H "Authorization: Bearer $TOKEN"
```

## Log Watch
```bash
tail -f /var/log/supervisor/backend.err.log | grep "\[SOURCE:"
```

## Emergency Rollback
```bash
# Single line rollback
sed -i 's/=supabase/=mongo/g' /app/backend/.env && sudo supervisorctl restart backend
```

---

**Document Version:** 1.0  
**Last Updated:** 2026-04-01  
**Owner:** Backend Engineering
