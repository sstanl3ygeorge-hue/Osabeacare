# ADMIN / RECRUITMENT / VERIFICATION READINESS AUDIT
## Date: 2026-03-30
## Auditor: E1 (Automated System Audit)

---

# PART A — MUST-HAVES STATUS TABLE

## 1. HOSTING / PERSISTENCE ASSUMPTIONS

| Item | Status | Evidence | Risk |
|------|--------|----------|------|
| **App Hosting** | PASS | Emergent Preview Environment | Preview env ≠ production. Data persists but no SLA |
| **Database** | PARTIAL | MongoDB localhost (`mongodb://localhost:27017`, DB: `test_database`) | **CRITICAL**: "test_database" name suggests non-production. No visible backup config |
| **File Storage** | PASS | Emergent Object Storage (`integrations.emergentagent.com/objstore`) | Managed by platform, requires EMERGENT_LLM_KEY |
| **Backups** | FAIL | No backup configuration found | **CRITICAL**: No automated backup strategy visible |
| **Environment Secrets** | PARTIAL | Keys stored in `/app/backend/.env` | Keys present but no vault/secret manager. Resend API key exposed in plaintext |
| **Prod vs Test Separation** | FAIL | DB name is "test_database", single environment | **CRITICAL**: No environment separation |

### Critical Risks:
1. Database named "test_database" - unclear if this is actual production
2. No backup strategy visible in code or config
3. Single environment serves all purposes

---

## 2. ROLE-BASED ACCESS CONTROL

### Current Roles (from `server.py:134-145`):
| Role | Level | Exists |
|------|-------|--------|
| SUPER_ADMIN | Highest | ✅ |
| ADMIN | High | ✅ |
| BRANCH_MANAGER | Medium | ✅ |
| AUDITOR | Read-only | ✅ |
| EMPLOYEE | Lowest | ✅ |

### Sensitive Actions Audit:

| Action | Current Protection | Required | Status |
|--------|-------------------|----------|--------|
| **Delete Employee (soft)** | `require_manager_or_admin` | ADMIN only | PARTIAL |
| **Delete Employee (permanent)** | `SUPER_ADMIN` check | SUPER_ADMIN | ✅ PASS |
| **Archive Employee** | `require_manager_or_admin` | Manager+ | ✅ PASS |
| **Create Employee** | `require_manager_or_admin` | Manager+ | ✅ PASS |
| **Verify Document** | `require_manager_or_admin` | Should be ADMIN only | ⚠️ PARTIAL |
| **Override Onboarding Status** | `SUPER_ADMIN` check | SUPER_ADMIN | ✅ PASS |
| **Delete Policy** | `require_admin` | ADMIN | ✅ PASS |
| **Delete Training Record** | `require_admin` | ADMIN | ✅ PASS |
| **Access Audit Logs** | `require_manager_or_admin` | Manager+ | ✅ PASS |
| **Create Admin User** | Not explicitly protected | Should be SUPER_ADMIN | ⚠️ FAIL |
| **Email Request Creation** | `require_admin` | ADMIN | ✅ PASS |

### Issues Found:
1. **No `require_auditor` function** - Auditor role exists but no backend enforcement
2. **Verification actions allow BRANCH_MANAGER** - May be too permissive for legal documents
3. **Admin creation not gated** - `/api/auth/register` can create any role
4. **No rate limiting** on sensitive endpoints

### Endpoints Too Broadly Accessible:
| Endpoint | Current | Should Be |
|----------|---------|-----------|
| `POST /api/auth/register` | Public | Should gate admin role creation |
| `DELETE /api/employees/{id}` | Admin | Super Admin only |
| `POST /api/compliance-status/{id}/verify` | Manager+ | Admin only |

---

## 3. RECRUITMENT STRICTNESS

| Requirement | Exists | Enforced | Blocks Work? | Location |
|-------------|--------|----------|--------------|----------|
| **Reference Integrity** | ✅ Yes | PARTIAL | No | `server.py:5202` - Verify endpoint exists, `from_cv` field tracked |
| **Reference x2 Required** | ✅ Yes | ⚠️ UI only | No | `REQUIRED_SOON` set, not in `WORK_READY_REQUIREMENTS` |
| **Proof of Address x2** | ✅ Yes | PARTIAL | No | `server.py:287` - `required_count: 2` but not blocking work |
| **CV Gap Explanations** | ✅ Yes | ✅ Yes | No | `server.py:5347` - Gap tracking with explanations |
| **Health Screening** | ✅ Yes | ⚠️ In REQUIRED_SOON | No | `health_screening` in `REQUIRED_SOON`, not blocking |
| **Interview Record** | ✅ Yes | ⚠️ Optional | No | Form exists but not mandatory |
| **Final Recruitment Approval** | ❌ No | N/A | N/A | **MISSING**: No explicit approval gate |

### Blocking Work Readiness (`WORK_READY_REQUIREMENTS`):
```python
# Currently blocking (server.py:198-215):
- right_to_work_documents
- right_to_work_check
- identity_documents
- dbs_certificate
- dbs_check
- safeguarding
- manual_handling
- infection_control
```

### NOT Blocking (But Should Consider):
- References (x2)
- Proof of Address (x2)
- Health Screening
- Interview Record

---

## 4. VERIFICATION INTEGRITY

| Check | Status | Evidence |
|-------|--------|----------|
| **verified/verified_by/verified_at recorded** | ✅ PASS | Consistently tracked across compliance_status, training_records, references |
| **Expiry visible after verification** | ✅ PASS | `expiry_date` separate from `verified` status |
| **Superseded evidence handled** | ✅ PASS | `status: superseded` excluded from queries (`server.py:1729,1764,1788`) |
| **Edit-after-verification surfaced** | ⚠️ PARTIAL | Audit logs track changes but no explicit "verified-then-edited" warning |
| **Broken file references prevented** | ⚠️ PARTIAL | `file_url: {$exists: true}` checks exist but no broken link validation |
| **Form vs Document verification consistent** | ✅ PASS | Both use same `verified/verified_by/verified_at` pattern |

### Gaps:
1. No automated detection of verification followed by edit
2. No periodic file integrity check (are stored files still accessible?)
3. No explicit "requires re-verification" flag after edits

---

## 5. WORK-READINESS GATE

| Check | Status | Evidence |
|-------|--------|----------|
| **Critical expiry overrides readiness** | ✅ PASS | RTW/DBS expiry blocks work readiness (`server.py:2237`) |
| **Mandatory recruitment blockers** | ✅ PASS | `WORK_READY_REQUIREMENTS` enforced in `calculate_employee_compliance()` |
| **List/Profile/Dashboard match** | ✅ PASS | All use same `work_readiness` field from backend |
| **No account before approval** | ⚠️ PARTIAL | Employees can be created without compliance checks |

### How Work Readiness is Calculated (`server.py:1684-1840`):
- Checks `WORK_READY_REQUIREMENTS` items
- Must have evidence (document, form, or training record)
- Must not be expired
- Excludes deleted/superseded records

### Status Mapping:
- `work_ready` = All mandatory items complete + verified + not expired
- `supervised_start` = Core items done, some REQUIRED_SOON pending
- `not_ready` = Missing mandatory items
- `blocked` = Expired critical document

---

## 6. ACTIVATION FLOW

| Check | Status | Evidence |
|-------|--------|----------|
| **When accounts created** | ⚠️ Any time | `POST /api/employees` allows immediate creation |
| **Recruitment approval required** | ❌ FAIL | No approval gate before employee creation |
| **Who can activate** | Manager+ | `derive_onboarding_status()` auto-derives |
| **Manual override** | Super Admin | `server.py:6855` - Override requires SUPER_ADMIN |
| **Audit trail for activation** | ✅ PASS | `log_audit_action()` called on status changes |

### Onboarding Status Flow:
```
NEW → DOCUMENTS_PENDING → UNDER_REVIEW → READY_FOR_PLACEMENT → ACTIVE
                                     ↘ ARCHIVED
```

### Issues:
1. **No approval gate**: Employee can go from NEW to ACTIVE automatically based on compliance
2. **No explicit "recruitment approved" flag** before account creation
3. **Manager can archive but cannot restore** (only change from other statuses)

---

# PART B — CRITICAL RISKS TO FIX BEFORE WIDER ROLLOUT

## 🔴 P0: Must Fix Immediately

### 1. Database Name "test_database"
- **Risk**: Unclear if production data or test data
- **Impact**: Data loss, compliance breach
- **Fix**: Rename to `osabea_production` or confirm this is intentional

### 2. No Backup Strategy
- **Risk**: Data loss without recovery
- **Impact**: Total loss of recruitment/compliance records
- **Fix**: Implement MongoDB backup (Atlas or manual cron)

### 3. Admin Role Creation Ungated
- **Risk**: Anyone can register as admin
- **Impact**: Unauthorized access to all employee data
- **Fix**: Gate admin/super_admin role creation to SUPER_ADMIN only

## 🟠 P1: Fix Before Production

### 4. Verification Actions Too Permissive
- **Risk**: Branch managers can verify legal documents (RTW, DBS)
- **Impact**: Audit non-compliance, legal risk
- **Fix**: Restrict legal document verification to ADMIN+

### 5. No Recruitment Approval Gate
- **Risk**: Employees can become "Active" without human approval
- **Impact**: Unsafe person could appear ready to work
- **Fix**: Add `recruitment_approved_by` field required before ACTIVE status

### 6. References Not Blocking
- **Risk**: Employee can be work-ready without verified references
- **Impact**: CQC non-compliance (references are mandatory)
- **Fix**: Consider adding `reference_1` + `reference_2` to `WORK_READY_REQUIREMENTS`

## 🟡 P2: Fix Soon

### 7. No File Integrity Validation
- **Risk**: Stored files may become inaccessible
- **Impact**: Missing evidence at audit time
- **Fix**: Periodic file accessibility check job

### 8. Edit-After-Verification Not Surfaced
- **Risk**: Verified document could be edited without re-verification
- **Impact**: False compliance status
- **Fix**: Add `requires_reverification` flag when verified document is edited

---

# PART C — SAFE HARDENING PLAN

## Phase 1: Immediate Security (1-2 days)

### 1.1 Gate Admin Creation
```python
# In register endpoint
if user_data.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
    # Require existing super_admin authentication
    raise HTTPException(403, "Admin accounts require super_admin approval")
```

### 1.2 Confirm Database Purpose
- If production: Rename `test_database` → `osabea_care_production`
- Add `.env` variable: `ENVIRONMENT=production`

### 1.3 Restrict Verification Permissions
```python
# Create require_admin_verification dependency
async def require_admin_for_legal_verification(user, requirement_id):
    legal_requirements = ["right_to_work_documents", "right_to_work_check", 
                         "dbs_certificate", "dbs_check", "identity_documents"]
    if requirement_id in legal_requirements and user['role'] == UserRole.BRANCH_MANAGER:
        raise HTTPException(403, "Legal document verification requires Admin")
```

## Phase 2: Recruitment Approval (2-3 days)

### 2.1 Add Recruitment Approval Field
```python
# In Employee model
recruitment_approved: bool = False
recruitment_approved_by: Optional[str] = None
recruitment_approved_at: Optional[str] = None
recruitment_approval_notes: Optional[str] = None
```

### 2.2 Gate ACTIVE Status
```python
# In derive_onboarding_status()
if compliance["complete_count"] == compliance["total_items"]:
    if compliance["verified_count"] == compliance["total_items"]:
        if not employee.get("recruitment_approved"):
            return OnboardingStatus.READY_FOR_PLACEMENT  # Cannot go ACTIVE
        return OnboardingStatus.ACTIVE
```

### 2.3 Add Approval Endpoint
```python
@api_router.post("/employees/{id}/approve-recruitment")
async def approve_recruitment(id: str, notes: str = None, user: dict = Depends(require_admin)):
    # Record approval with audit trail
```

## Phase 3: Work-Readiness Hardening (1-2 days)

### 3.1 Add References to Blocking (Optional - discuss with user)
```python
WORK_READY_REQUIREMENTS = {
    # ... existing ...
    "reference_1",  # CQC requires 2 references
    "reference_2",
}
```

### 3.2 Add Edit-After-Verification Tracking
```python
# When updating verified item
if existing.get("verified") and changes_made:
    updates["requires_reverification"] = True
    updates["reverification_reason"] = "Edited after verification"
    await log_audit_action(user_id, "verified_item_edited", ...)
```

## Phase 4: Monitoring (Ongoing)

### 4.1 File Integrity Check Job
```python
@api_router.post("/admin/check-file-integrity")
async def check_file_integrity():
    # Iterate documents with file_url
    # Verify each file is accessible
    # Flag broken references
```

### 4.2 Database Backup Setup
- Enable MongoDB Atlas backups OR
- Add cron job: `mongodump --db osabea_care_production --out /backups/$(date +%Y%m%d)`

---

# PART D — WHAT IS ALREADY STRONG (DO NOT TOUCH)

## ✅ Strengths to Preserve

### 1. Single Source of Truth Compliance Calculation
- `calculate_employee_compliance()` is the ONLY place compliance is computed
- All views (Dashboard, Profile, Audit, Matrix) use same backend data
- DO NOT add frontend compliance calculations

### 2. Comprehensive Audit Logging
- `log_audit_action()` called on all sensitive operations
- Audit logs include metadata, timestamps, actor ID
- DO NOT reduce audit coverage

### 3. Work-Readiness Blocking Logic
- RTW, DBS, Identity, Core Training properly block work
- Expiry dates properly override status
- DO NOT loosen blocking requirements

### 4. Superseded Record Exclusion
- All queries properly exclude `deleted`, `superseded`, `archived` records
- Consistent across documents, training, forms
- DO NOT change exclusion patterns

### 5. Verification Pattern Consistency
- `verified`, `verified_by`, `verified_at` used everywhere
- Same pattern for documents, training, references
- DO NOT introduce alternative verification fields

### 6. Onboarding Status Derivation
- Status derived from actual compliance, not manual entry
- Manual override requires SUPER_ADMIN
- DO NOT allow managers to directly set ACTIVE

### 7. Email Automation Architecture
- Clean template registry
- Request lifecycle tracking
- Duplicate prevention
- DO NOT scatter Resend calls elsewhere

---

## SUMMARY

| Category | Status | Critical Issues |
|----------|--------|-----------------|
| Hosting/Persistence | ⚠️ PARTIAL | Backup missing, "test_database" name |
| RBAC | ⚠️ PARTIAL | Admin creation ungated, verification too permissive |
| Recruitment Strictness | ⚠️ PARTIAL | No approval gate, references not blocking |
| Verification Integrity | ✅ MOSTLY GOOD | Edit-after-verification not surfaced |
| Work-Readiness Gate | ✅ MOSTLY GOOD | Works correctly |
| Activation Flow | ⚠️ PARTIAL | No recruitment approval required |

**Overall Readiness: 65% - NOT READY FOR PRODUCTION**

**Blocking Items Before Go-Live:**
1. Gate admin role creation
2. Confirm/rename database
3. Add recruitment approval gate
4. Document backup strategy

