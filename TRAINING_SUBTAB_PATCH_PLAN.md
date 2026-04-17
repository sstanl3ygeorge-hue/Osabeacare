# TRAINING SUBTAB PATCH PLAN (v2)

**Date:** 2026-04-17 (revised)
**Scope:** 4 confirmed findings from TRAINING_SUBTAB_AUDIT.md + Phase 0 safety stop
**Working rules:** Patch-oriented. No new architecture. No mixed-source subtabs. No worker-side custom truth. No legacy direct-completion path. **Extraction never equals approval.**

---

## Phase 0 — Emergency Safety Stop

### 0.0 Principles

- Certificate upload = evidence. Never completion.
- AI extraction = suggestion. Never approval.
- Only an explicit admin review action (`POST /training/proposed-items/review`) creates a canonical `training_record`.
- No endpoint may write `training_records` as a side-effect of upload or extraction.

### 0.1 Retire `POST /training/bulk-upload` (dead endpoint)

| Property | Value |
|----------|-------|
| **File** | `backend/server.py` L11576–11745 |
| **Function** | `bulk_upload_training_certificates()` |
| **Current behavior** | Reads file → saves to local disk → AI extraction → inserts `training_records` directly with `status: "completed"` → no `employee_documents`, no `proposed_training_items` |
| **Confirmed callers** | `EnhancedTrainingTab.js` — dead code, commented out of all imports |
| **Risk of retirement** | None. No live caller. |

**Exact edit — replace function body:**

```python
@api_router.post("/employees/{employee_id}/training/bulk-upload")
async def bulk_upload_training_certificates(
    employee_id: str,
    file: UploadFile = File(...),
    extract_multiple: str = Form("true"),
    user: dict = Depends(require_manager_or_admin)
):
    """DEPRECATED — this endpoint wrote training_records directly, bypassing review.
    Use POST /employees/{eid}/training/intake/from-upload instead."""
    logger.warning(
        f"DEPRECATED bulk-upload called by {user.get('email')} for {employee_id} — returning 410"
    )
    raise HTTPException(
        status_code=410,
        detail="This endpoint is retired. Use /training/intake/from-upload for certificate uploads."
    )
```

**Before/after:**
| | Before | After |
|--|--------|-------|
| HTTP | 200 + auto-completed training_records | 410 Gone |
| training_records | Written directly | Not touched |
| employee_documents | Not created | Not created |
| Local disk write | Yes | No |

### 0.2 Rewrite `POST /training/bulk-save` (live danger)

| Property | Value |
|----------|-------|
| **File** | `backend/server.py` L12007–12130 |
| **Function** | `bulk_save_training_records()` |
| **Current behavior** | Takes array of `{training_name, completion_date, expiry_date, provider}` → writes `training_records` directly with `record_status: "active"` → no `employee_documents`, no `proposed_training_items` |
| **Live caller** | `TrainingCertificateExtractor.js` L237 — the admin "Save Selected" button |
| **Problem** | Extraction + save = instant completion without review |

**Exact edit — replace function body to create proposed_training_items instead:**

```python
@api_router.post("/employees/{employee_id}/training/bulk-save")
async def bulk_save_training_records(
    employee_id: str,
    trainings: List[dict] = Body(..., embed=True),
    user: dict = Depends(require_manager_or_admin)
):
    """
    Save extracted training items as PROPOSED items awaiting review.
    
    SAFETY: Does NOT create training_records. Creates proposed_training_items
    that must be explicitly approved via /training/proposed-items/review.
    
    Called by TrainingCertificateExtractor after AI extraction + admin selection.
    """
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    if not trainings or len(trainings) == 0:
        raise HTTPException(status_code=400, detail="No training items provided")
    
    now = datetime.now(timezone.utc).isoformat()
    created_items = []
    
    for training in trainings:
        training_name = training.get("training_name", "").strip()
        if not training_name:
            continue
        
        # Generate normalized code
        training_code = training_name.lower().replace(" ", "_").replace("&", "and")[:30]
        training_code = re.sub(r'[^a-z0-9_]', '', training_code)
        
        is_mandatory = is_mandatory_training(training_name)
        
        proposed_item = {
            "id": str(uuid.uuid4()),
            "employee_id": employee_id,
            "source_document_id": training.get("certificate_id"),
            "raw_course_title": training_name,
            "mapped_training_title": training_name,
            "mapped_training_code": training_code,
            "completion_date": training.get("completion_date"),
            "expiry_date": training.get("expiry_date"),
            "provider": training.get("provider", ""),
            "is_mandatory": is_mandatory,
            "ai_extracted": True,
            "status": "proposed",
            "created_at": now,
            "created_by": user.get("email"),
            "source": "admin_extractor",
        }
        
        await db.proposed_training_items.insert_one(proposed_item)
        created_items.append({
            "id": proposed_item["id"],
            "training_name": training_name,
            "is_mandatory": is_mandatory
        })
    
    await log_audit_action(user['user_id'], "training_bulk_save_proposed", "employee", employee_id, {
        "proposed_count": len(created_items),
        "trainings": [r["training_name"] for r in created_items]
    })
    
    return {
        "success": True,
        "saved_count": len(created_items),
        "records": created_items,
        "message": f"Submitted {len(created_items)} training item(s) for review. Go to All Qualifications tab to approve.",
        "requires_review": True
    }
```

**Before/after:**
| | Before | After |
|--|--------|-------|
| HTTP response shape | `{success, saved_count, records, message}` | Same shape + `requires_review: true` |
| `training_records` | Written directly (active) | **Not touched** |
| `proposed_training_items` | Not created | **Created** with `status: "proposed"` |
| Existing record superseding | Yes (dangerous) | No |
| Frontend compatibility | `TrainingCertificateExtractor.js` reads `response.data.saved_count` | **Still works** — same field name |

### 0.3 Frontend toast change in TrainingCertificateExtractor.js

| Property | Value |
|----------|-------|
| **File** | `frontend/src/components/training/TrainingCertificateExtractor.js` L253 |
| **Current** | `` toast.success(`Saved ${response.data.saved_count \|\| itemsToSave.length} training records`); `` |
| **Change to** | `` toast.success(response.data.message \|\| `Submitted ${response.data.saved_count} items for review`); `` |

This is the only frontend change needed for Phase 0. The response shape is preserved (`success`, `saved_count`, `records`), so the rest of the component (including the `onSuccess?.()` and `onClose()` calls) works unchanged.

### 0.4 What Phase 0 does NOT change

- `POST /training/extract-certificate` — read-only preview, untouched
- `POST /training/intake/from-upload` — already correct, untouched
- `POST /worker/upload-document/{requirement_id}` — already creates `employee_documents` + `proposed_training_items`, untouched
- `POST /training/proposed-items/review` — the explicit approval endpoint, untouched (this is the ONLY path that creates `training_records`)
- `POST /training/manual` — manually adds a training record by admin choice (intentional, not extraction-driven), untouched
- Admin inline edit dialog — edits existing `training_records`, not an extraction path, untouched
- `GET /training/matrix` — reads `training_records`, untouched

### 0.5 Phase 0 admin workflow (after patch)

```
1. Admin clicks "Upload Certificate" on Mandatory tab
2. TrainingCertificateExtractor opens
3. Admin uploads PDF → calls POST /training/extract-certificate (preview, no writes)
4. AI returns extracted trainings for review in the dialog
5. Admin selects/edits items → clicks "Save Selected"
6. POST /training/bulk-save creates proposed_training_items (NOT training_records)
7. Toast: "Submitted 5 training items for review. Go to All Qualifications tab to approve."
8. Admin goes to All Qualifications tab → sees "Awaiting Review (5)" section
9. Admin clicks Approve on each item (or bulk-approve)
10. POST /training/proposed-items/review creates canonical training_records
11. Training now appears as completed in Mandatory tab
```

Steps 1–6 are extraction. Step 9–10 are approval. These are separate actions with an explicit review boundary.

### 0.6 Phase 0 summary

| Endpoint | Before Phase 0 | After Phase 0 |
|----------|-----------------|---------------|
| `POST /training/bulk-upload` | Auto-completes training_records, writes local disk | **410 Gone** |
| `POST /training/bulk-save` | Creates training_records directly | Creates **proposed_training_items** only |
| `POST /training/extract-certificate` | Preview only (no writes) | Unchanged |
| `POST /training/intake/from-upload` | Correct (employee_documents + proposed) | Unchanged |
| `POST /training/proposed-items/review` | Creates training_records on explicit approve | Unchanged — **this is now the ONLY completion path** |

---

## Admin Review vs Approval — Strict Definition

### What "auto-approve" meant in the prior plan

The prior plan version said: "admin auto-approve means no UX change — training still appears immediately."

**This is withdrawn.** That approach conflates extraction and approval.

### Strict rule

| Term | Meaning | Acceptable? |
|------|---------|-------------|
| **Auto-approve** (extraction = approval because uploader is admin) | Upload → instant `training_record` creation | **NO** — violates safer recruitment integrity. Extraction accuracy is not guaranteed. CQC expects explicit verification of training evidence. |
| **Explicit review** (admin reviews extracted items, then clicks Approve) | Upload → `proposed_training_items` → admin reviews → clicks Approve → `training_record` created | **YES** — there is a human review boundary between extraction and completion. |
| **Quick approve** (same admin, same session, but separate click) | Admin uploads, reviews the extracted preview, then immediately approves all items | **YES** — the review boundary exists even if the admin acts quickly. The point is that approval is a deliberate action, not a side-effect of upload. |

### Recommended behavior

- **Extraction never equals approval.**
- Admin uploads certificate → AI extracts → items land in `proposed_training_items` with `status: "proposed"`.
- Admin can then approve individual items or bulk-approve from the All Qualifications tab.
- The approve action is `POST /training/proposed-items/review` — this is the only endpoint that creates `training_records`.
- The same admin who uploaded can immediately approve, but through a separate explicit action.

---

## 1 — Patch Plan for the 3 Visible Subtabs

### 1.1 Mandatory Tab

**Current data source:** `GET /api/employees/{eid}/training/matrix` → `response.items`
**Keep as-is.** This tab already uses the canonical evaluator (`evaluate_employee_training_status()`). Status is backend-computed. No frontend status derivation.

**One fix needed:** Remove the hardcoded label.

| What | Detail |
|------|--------|
| File | `frontend/src/components/training/AuditReadyTrainingMatrix.js` |
| Line | 495 |
| Current | `"These 8 mandatory training items are required for work readiness"` |
| Change to | `{summary.totalRequired} mandatory training items required for work readiness` |
| Badge source | `summary.totalRequired` — **keep as-is** (already correct) |
| Endpoint | `GET /employees/{eid}/training/matrix` — **keep as-is** |
| Logic to remove | None |

### 1.2 All Qualifications Tab

**Current data source:** `[...mandatoryTraining, ...additionalTraining]` (mandatory from canonical evaluator, additional from inline date check)

**Fix:** Make the matrix endpoint compute additional-item status through `compute_training_record_status()` instead of the inline date comparison.

| What | Detail |
|------|--------|
| File | `backend/server.py` |
| Lines | 10840–10870 (the `for record in additional_records:` loop) |
| Current logic | Inline `datetime.fromisoformat()` comparison, returns only `current`/`expired`/`expiring_soon` |
| Replace with | Call `compute_training_record_status(record)` → use `computed_status`, map `not_started`→`missing`, `needs_renewal`→`expiring_soon`, keep `expired`, `completed`→`current` |
| Badge source | `summary.additionalQualifications + summary.totalRequired` — **keep as-is** |
| Endpoint | Same endpoint, same response shape |
| Logic to remove | The `from datetime import datetime, timezone` import already exists at top; remove the inline `try/except` expiry block |

**Exact edit in `server.py` L10840–10870:**

```python
# BEFORE (inline date check)
for record in additional_records:
    status = 'current'
    expires_at = record.get('expiry_date') or record.get('expires_at')
    if expires_at:
        from datetime import datetime, timezone
        try:
            ...  # 12 lines of inline parsing
        except:
            pass

# AFTER (canonical function)
for record in additional_records:
    computed = compute_training_record_status(record)
    raw_status = computed.get('computed_status', 'completed')
    status_map = {
        'not_started': 'missing',
        'expired': 'expired',
        'needs_renewal': 'expiring_soon',
        'completed': 'current',
        'valid': 'current',
    }
    status = status_map.get(raw_status, 'current')
    expires_at = record.get('expiry_date') or record.get('expires_at')
```

### 1.3 Certificates Tab

**Current data source:** `GET /api/employee-documents?employee_id={eid}` filtered client-side
**Problem:** Blind to certificates stored only on `training_records.certificate_url`

**Fix:** Create a dedicated backend endpoint that merges both sources into a single certificate list.

| What | Detail |
|------|--------|
| New endpoint | `GET /api/employees/{eid}/training/certificates` |
| File | `backend/server.py` (add after the matrix endpoint, ~L10900) |
| Returns | Unified list combining `employee_documents` (category=training) + synthetic entries for `training_records` that have `certificate_url` but no matching `employee_documents` |
| Frontend file | `AuditReadyTrainingMatrix.js` L160–175 |
| Current fetch | `GET /api/employee-documents?employee_id=${eid}` + client-side filter |
| Replace with | `GET /api/employees/${eid}/training/certificates` (no client-side filter) |
| Badge source | `summary.certificatesUploaded` — change to use length of new certificates endpoint response |

**New endpoint logic:**

```python
@api_router.get("/employees/{employee_id}/training/certificates")
async def get_training_certificates(employee_id: str, user: dict = Depends(get_current_user)):
    # 1. Get employee_documents matching training certificates
    docs = await db.employee_documents.find({
        "employee_id": employee_id,
        "$or": [
            {"document_type": "training_certificate"},
            {"category": "training"},
            {"requirement_id": {"$regex": "training", "$options": "i"}}
        ]
    }, {"_id": 0}).to_list(200)

    doc_ids = {d["id"] for d in docs}

    # 2. Get training_records that have certificate_url but no linked employee_document
    records_with_certs = await db.training_records.find({
        "employee_id": employee_id,
        "certificate_url": {"$ne": None, "$exists": True},
        "record_status": {"$nin": ["superseded", "deleted"]}
    }, {"_id": 0}).to_list(200)

    # 3. Build synthetic employee_document entries for orphaned certificate_urls
    for record in records_with_certs:
        source_doc_id = record.get("source_document_id") or record.get("certificate_document_id")
        if source_doc_id and source_doc_id in doc_ids:
            continue  # already represented

        # Check if any existing doc links to this record
        linked = any(
            d.get("id") == source_doc_id or
            d.get("linked_record_id") == record.get("id")
            for d in docs
        )
        if linked:
            continue

        synthetic = {
            "id": f"synth_{record['id']}",
            "employee_id": employee_id,
            "document_type": "training_certificate",
            "category": "training",
            "original_filename": record.get("original_filename") or record.get("source_file") or "Legacy Certificate",
            "file_url": record.get("certificate_url"),
            "uploaded_at": record.get("uploaded_at") or record.get("created_at"),
            "uploaded_by": record.get("created_by"),
            "source": "training_records_legacy",
            "linked_training_record_id": record.get("id"),
            "linked_training_name": record.get("training_name"),
        }
        docs.append(synthetic)

    return {"certificates": docs, "total": len(docs)}
```

**Frontend fetch change in `fetchTrainingData()` (L160–175):**

```javascript
// BEFORE
const certResponse = await axios.get(
  `${API}/api/employee-documents?employee_id=${employeeId}`, ...
);
const allDocs = certResponse.data.documents || certResponse.data || [];
const trainingCerts = allDocs.filter(doc =>
  doc.document_type === 'training_certificate' || ...
);

// AFTER
const certResponse = await axios.get(
  `${API}/api/employees/${employeeId}/training/certificates`, ...
);
const trainingCerts = certResponse.data.certificates || [];
```

**Badge fix:** Replace `summary.certificatesUploaded` (which comes from the matrix endpoint using stale logic) with a direct count from the certificates response. Add to the `fetchTrainingData` summary build:

```javascript
setSummary(prev => ({
  ...prev,
  certificatesUploaded: trainingCerts.length
}));
```

---

## 2 — Patch Plan for Admin vs Worker Consistency

### 2.1 Same mandatory definitions

**Problem:** Worker hardcodes 8 mandatory + 6 recommended at `worker_dashboard.py` L688–706. Admin uses `MANDATORY_ITEMS["training"]` (14+ items).

**Fix:** Extract the definitions to a shared constant importable by both.

| What | Detail |
|------|--------|
| New file | `backend/training_definitions.py` |
| Contents | Export `MANDATORY_TRAINING_CODES`, `RECOMMENDED_TRAINING_CODES`, and a `get_all_training_definitions()` function |
| Source data | Copy the 8 mandatory IDs and 6 recommended IDs that the worker already uses, plus the mapping to display names. Both admin and worker agree these are the core 8+6 split. The admin evaluator already gets the full list from `MANDATORY_ITEMS["training"]` which includes all 14. |
| Import from | `worker_dashboard.py` replaces hardcoded dicts with `from training_definitions import MANDATORY_TRAINING_IDS, RECOMMENDED_TRAINING_IDS` |
| Admin side | No change needed — admin already uses `MANDATORY_ITEMS["training"]` which is the superset |

```python
# backend/training_definitions.py

# The 8 UCE-blocking mandatory trainings
MANDATORY_TRAINING_IDS = {
    "safeguarding": "Safeguarding",
    "manual_handling": "Moving & Handling",
    "health_safety": "Health & Safety",
    "bls": "First Aid / Basic Life Support",
    "fire_safety": "Fire Safety",
    "infection_control": "Infection Control",
    "information_governance": "Information Governance",
    "prevent": "Prevent",
}

# 6 recommended (tracked but not blocking)
RECOMMENDED_TRAINING_IDS = {
    "induction_training": "Induction",
    "medication": "Medication",
    "food_hygiene": "Food Hygiene",
    "mca_dols": "MCA and DoLs",
    "dementia": "Dementia Awareness",
    "autism": "Autism Awareness",
}

# Fuzzy match patterns (single source for both worker upload matching and dashboard display)
TRAINING_MATCH_PATTERNS = {
    "safeguarding": ["safeguarding", "safeguarding adults", "safeguarding children", "safeguard"],
    "manual_handling": ["manual handling", "moving & handling", "moving and handling", "patient handling"],
    "bls": ["basic life support", "resuscitation", "cpr", "first aid", "bls"],
    "health_safety": ["health, safety and welfare", "health and safety", "h&s"],
    "fire_safety": ["fire safety", "fire awareness", "fire prevention", "fire evacuation"],
    "infection_control": ["infection control", "infection prevention", "ipc"],
    "information_governance": ["information governance", "gdpr", "data protection", "ig training"],
    "prevent": ["prevent", "counter terrorism", "radicalisation", "prevent duty"],
    "induction_training": ["induction"],
    "medication": ["medication"],
    "food_hygiene": ["food hygiene"],
    "mca_dols": ["mca", "dols", "mental capacity"],
    "dementia": ["dementia"],
    "autism": ["autism"],
}
```

**Worker dashboard edit:** Replace L688–706 with:
```python
from training_definitions import MANDATORY_TRAINING_IDS, RECOMMENDED_TRAINING_IDS, TRAINING_MATCH_PATTERNS
mandatory_trainings = MANDATORY_TRAINING_IDS
recommended_trainings_def = RECOMMENDED_TRAINING_IDS
```

**Worker upload endpoint edit:** Replace inline `mandatory_codes` dict at `worker_dashboard.py` L1649–1658 with:
```python
from training_definitions import TRAINING_MATCH_PATTERNS
# Use TRAINING_MATCH_PATTERNS for matching
```

### 2.2 Same training evaluator

**Problem:** Worker builds status inline (L750–810). No `awaiting_review`, no `expiring_soon`, no `verified` distinction.

**Fix:** Extract canonical evaluator to a shared module; have worker endpoint call it.

| What | Detail |
|------|--------|
| New file | `backend/services/training_evaluator.py` |
| Move into it | `compute_training_record_status()`, `evaluate_employee_training_status()`, `get_required_training_for_employee()`, `get_training_blocker_config()`, `get_training_validity_days()`, `TRAINING_VALIDITY_PERIODS`, `TRAINING_BLOCKER_CONFIG`, `EXPIRY_WARNING_DAYS` |
| server.py | Replace definitions with `from services.training_evaluator import ...` |
| worker_dashboard.py | `from services.training_evaluator import evaluate_employee_training_status` |

**Worker endpoint rewrite (replace L688–830 inline training block):**

```python
# REPLACE entire inline training block with:
from services.training_evaluator import evaluate_employee_training_status

role = employee.get('role', '')
training_eval = await evaluate_employee_training_status(employee_id, role)

# Project canonical evaluation into worker-friendly shape
all_mandatory_trainings = []
missing_trainings = []
completed_trainings = []
expired_trainings = []

for item in training_eval.get('items', []):
    code = item.get('code', '')
    # Only include the 8 mandatory for the worker mandatory section
    if code not in MANDATORY_TRAINING_IDS and code not in RECOMMENDED_TRAINING_IDS:
        continue

    is_mandatory = code in MANDATORY_TRAINING_IDS

    # Map canonical status → worker status
    canonical_status = item.get('status', 'missing')
    worker_status_map = {
        'missing': 'missing',
        'expired': 'expired',
        'expiring_soon': 'expiring_soon',
        'due_soon': 'expiring_soon',
        'awaiting_review': 'pending',
        'completed': 'complete',
        'verified': 'complete',
    }
    worker_status = worker_status_map.get(canonical_status, 'missing')

    entry = {
        "id": code,
        "name": MANDATORY_TRAINING_IDS.get(code) or RECOMMENDED_TRAINING_IDS.get(code, code),
        "status": worker_status,
        "completion_date": item.get('completion_date'),
        "expiry_date": item.get('expires_at'),
        "verified": item.get('verified', False),
        "record_id": None,  # evaluator doesn't expose this; add if needed
    }

    if is_mandatory:
        all_mandatory_trainings.append(entry)
    # else: add to recommended list (same logic)

    if worker_status == 'missing':
        missing_trainings.append({"id": code, "name": entry["name"], "action": "upload_certificate"})
    elif worker_status == 'expired':
        expired_trainings.append({"id": code, "name": entry["name"], "expiry_date": entry["expiry_date"], "action": "upload_certificate"})
    elif worker_status in ('complete', 'expiring_soon', 'pending'):
        completed_trainings.append({"id": code, "name": entry["name"], "completion_date": entry["completion_date"], "expiry_date": entry["expiry_date"], "verified": entry["verified"]})
```

**Result:** Worker now sees `expiring_soon` and `pending` (awaiting_review) states. Admin and worker compute from the same evaluator against the same `training_records`. No fuzzy matching on the read path.

### 2.3 Same evidence lifecycle

Covered by Fix 4 below (dual lifecycle patch). After the fix, both admin and worker uploads create `employee_documents` + `proposed_training_items`, and `training_records` are only written on review/approval.

### 2.4 Same certificate visibility

Covered by the new `GET /employees/{eid}/training/certificates` endpoint (§1.3). The worker dashboard does not currently display certificates — if needed in future, it would call the same endpoint.

---

## 3 — Exact Fixes for the 4 Confirmed Issues

### Fix 1: Certificates Tab Blind Spot

| Property | Value |
|----------|-------|
| **Root cause** | Certificates tab reads `employee_documents`; legacy writes `training_records.certificate_url` only |
| **Affected files** | `backend/server.py` (new endpoint ~L10900), `frontend/src/components/training/AuditReadyTrainingMatrix.js` (L160–175, L476 badge) |
| **Functions involved** | `fetchTrainingData()` (frontend L144), needs new `get_training_certificates()` (backend) |
| **Edit** | 1. Add `GET /employees/{eid}/training/certificates` endpoint that merges both sources (see §1.3). 2. Change frontend fetch to call new endpoint. 3. Update badge to use response length. |
| **Risk** | LOW. Additive endpoint. Frontend change is a URL swap + removal of client-side filter. Synthetic entries are clearly marked with `source: "training_records_legacy"`. |
| **Rollout order** | **Phase 1** — deploy backend endpoint first (no frontend consumer yet). Then deploy frontend change. |

### Fix 2: Mandatory List Disagreement

| Property | Value |
|----------|-------|
| **Root cause** | Worker hardcodes 8+6 at `worker_dashboard.py` L688–706 + L1649–1658. Admin uses `MANDATORY_ITEMS["training"]` (14+). |
| **Affected files** | `backend/routes/worker_dashboard.py` (L688–706, L1649–1658), new `backend/training_definitions.py` |
| **Functions involved** | Worker dashboard handler (training block), worker upload handler (mandatory matching) |
| **Edit** | 1. Create `training_definitions.py` with shared constants (see §2.1). 2. Replace hardcoded dicts in `worker_dashboard.py` with imports. 3. Replace inline `mandatory_codes` in upload handler with shared `TRAINING_MATCH_PATTERNS`. |
| **Risk** | LOW. The 8+6 split is preserved — we're just moving the definition to one file. No behavioral change to existing worker views. |
| **Rollout order** | **Phase 2** — deploy after phase 1. Safe to deploy independently. |

### Fix 3: Worker Bypasses Canonical Evaluator

| Property | Value |
|----------|-------|
| **Root cause** | `worker_dashboard.py` L688–830 has inline fuzzy-match + expiry logic instead of calling `evaluate_employee_training_status()` |
| **Affected files** | `backend/server.py` (move functions out), new `backend/services/training_evaluator.py`, `backend/routes/worker_dashboard.py` (L688–830 rewrite) |
| **Functions involved** | `evaluate_employee_training_status()`, `compute_training_record_status()`, `get_required_training_for_employee()`, `get_training_blocker_config()`, `get_training_validity_days()` + constants |
| **Edit** | 1. Create `services/training_evaluator.py` with moved functions. 2. `server.py` imports from new module. 3. Worker endpoint replaces 140 lines of inline logic with canonical evaluator call + status projection (see §2.2). |
| **Risk** | MEDIUM. This changes the worker's status computation. A training that was `complete` on the worker side may now show `pending` or `expiring_soon`. **Mitigation:** Add a `worker_status` projection that maps `awaiting_review`→`pending` and `expiring_soon`→`expiring_soon` — these are new states the worker frontend must handle. |
| **Frontend impact** | `WorkerDashboard.js` status badge rendering needs two new status values: `pending` and `expiring_soon`. Currently handles `complete`, `expired`, `rejected`, `missing`. |
| **Rollout order** | **Phase 3** — deploy after phase 2. Requires coordinated backend + frontend deploy. |

**Worker frontend status badge additions (WorkerDashboard.js):**
```jsx
// Add to the status badge rendering (around L1960-1990):
case 'pending':
  return <Badge className="bg-amber-100 text-amber-700">Pending Review</Badge>;
case 'expiring_soon':
  return <Badge className="bg-orange-100 text-orange-700">Expiring Soon</Badge>;
```

### Fix 4: Dual Document Lifecycle

**Now handled by Phase 0** (see top of this document).

| Property | Value |
|----------|-------|
| **Root cause** | Legacy `bulk-upload` and admin `bulk-save` both write `training_records` directly, bypassing `employee_documents` and `proposed_training_items` |
| **Affected files** | `backend/server.py` (L11576 bulk-upload, L12007 bulk-save), `frontend/src/components/training/TrainingCertificateExtractor.js` (L253 toast) |
| **Resolution** | Phase 0 patches — `bulk-upload` returns 410, `bulk-save` creates `proposed_training_items` instead of `training_records`, frontend toast updated |
| **Risk** | LOW for bulk-upload (dead caller). MEDIUM for bulk-save (live caller, but response shape preserved). |
| **Rollout order** | **Phase 0** — deploy first, before all other fixes. |
| **Post-Phase-0 state** | `POST /training/proposed-items/review` is the ONLY path that creates `training_records`. All upload/extraction paths create evidence + proposals only. |

---

## 4 — Canonical End State

After all phases are applied:

| Collection | Role | Who writes | Who reads |
|------------|------|------------|-----------|
| `training_records` | **Canonical outcome/status** | Only written by: (a) `POST /training/proposed-items/review` (explicit admin approval), (b) `POST /training/manual` (admin manual entry) | `evaluate_employee_training_status()` (canonical evaluator), admin matrix endpoint, worker dashboard (via canonical evaluator) |
| `employee_documents` | **Canonical certificate evidence** | Written by: (a) `POST /training/intake/from-upload` (admin/worker upload), (b) `POST /worker/upload-document/{id}` (worker upload) | `GET /employees/{eid}/training/certificates` (unified endpoint), Certificates tab |
| `proposed_training_items` | **Review queue only — never equals completion** | Written by: (a) AI extraction via IntakeService, (b) `POST /training/bulk-save` (admin extractor save), (c) worker upload extraction | Library tab "Awaiting Review" section, Certificates tab linked items |

**Rules:**
1. **Extraction never equals approval.** No upload or extraction path creates `training_records`.
2. `POST /training/proposed-items/review` is the ONLY automated path from proposal to `training_record`. It requires explicit admin action.
3. `POST /training/manual` is the only other path to create a `training_record`, and it is an intentional admin choice (not extraction-driven).
4. `evaluate_employee_training_status()` is the ONLY function that computes training status — called by both admin and worker endpoints.
5. `training_definitions.py` is the ONLY place mandatory/recommended training IDs and match patterns are defined.
6. Certificate viewing resolves through `GET /employees/{eid}/training/certificates` (merges `employee_documents` + legacy `certificate_url` synthetics).
7. Legacy `POST /training/bulk-upload` is retired (410).
8. `POST /training/bulk-save` writes `proposed_training_items` only, not `training_records`.

---

## 5 — Safe Implementation Sequence (Revised)

```
Phase 0 — Emergency Safety Stop                             [DEPLOY FIRST, blocks unsafe writes]
├─ 0a. Retire POST /training/bulk-upload → 410 (server.py L11576)
├─ 0b. Rewrite POST /training/bulk-save to create proposed_training_items (server.py L12007)
├─ 0c. Update toast in TrainingCertificateExtractor.js L253
├─ 0d. Deploy backend first, then frontend
└─ 0e. Verify: admin upload → extract → save → items appear in "Awaiting Review", NOT in Mandatory tab

Phase 1 — Certificates Tab Fix (Fix 1)                      [SAFE, additive]
├─ 1a. Add GET /employees/{eid}/training/certificates endpoint (backend)
├─ 1b. Deploy backend, verify endpoint returns merged data
├─ 1c. Update AuditReadyTrainingMatrix.js fetchTrainingData() to use new endpoint
├─ 1d. Update certificate badge count source
└─ 1e. Deploy frontend

Phase 2 — Shared Definitions (Fix 2)                        [SAFE, no behavior change]
├─ 2a. Create backend/training_definitions.py
├─ 2b. Replace worker_dashboard.py L688-706 hardcoded dicts with imports
├─ 2c. Replace worker_dashboard.py L1649-1658 upload matching with imports
├─ 2d. Verify worker dashboard returns identical response shape
└─ 2e. Deploy backend

Phase 3 — Canonical Evaluator for Worker (Fix 3)            [MEDIUM risk, coordinated deploy]
├─ 3a. Create backend/services/training_evaluator.py with extracted functions
├─ 3b. Update server.py to import from new module (behavior-preserving refactor)
├─ 3c. Deploy backend, verify admin matrix endpoint unchanged
├─ 3d. Replace worker_dashboard.py L688-830 with canonical evaluator call
├─ 3e. Add 'pending' and 'expiring_soon' status badge handling to WorkerDashboard.js
├─ 3f. Deploy backend + frontend together
└─ 3g. Verify worker dashboard shows correct statuses for edge cases
```

### Dependency graph (revised)

```
Phase 0 ──────────────── MUST GO FIRST (stops unsafe writes)
   │
   ├── Phase 1 (standalone after Phase 0)
   ├── Phase 2 (standalone after Phase 0, can run parallel with Phase 1)
   └── Phase 3 depends on Phase 2 (needs shared definitions)
```

Phase 4 from the prior plan version is **eliminated** — it was the dual-lifecycle fix, which is now fully covered by Phase 0.

### Estimated risk per phase (revised)

| Phase | Risk | Reason |
|-------|------|--------|
| 0 | **LOW-MEDIUM** | `bulk-upload` retirement is zero-risk (dead caller). `bulk-save` rewrite preserves response shape; only behavioral change is items go to review queue instead of instant completion. Admin must now approve explicitly — a minor UX addition, not a loss. |
| 1 | LOW | New additive endpoint + URL swap in frontend |
| 2 | LOW | Moving constants to shared file, zero behavior change |
| 3 | MEDIUM | Worker status values change (new: `pending`, `expiring_soon`). Worker sees more accurate but potentially unfamiliar statuses |

---

## 6 — Knock-On Effects of Phase 0 on Later Phases

### Certificates Tab (Phase 1)
No change. Phase 0 doesn't touch the certificates endpoint or the `employee_documents` read path. Phase 1 proceeds as planned.

### Worker/Admin Consistency (Phases 2–3)
**Minor improvement:** After Phase 0, the admin upload flow creates `proposed_training_items` that are visible in the All Qualifications tab's "Awaiting Review" section. Once Phase 3 deploys the canonical evaluator for the worker, the worker will correctly see training as `pending` (not falsely `complete`) while admin review is pending. Without Phase 0, this accuracy would have been meaningless because `bulk-save` would still be bypassing the review queue.

### Canonical Evaluator (Phase 3)
No change to the evaluator itself. The evaluator reads `training_records`, which after Phase 0 are only written by the review endpoint. This means the evaluator's output is now strictly gated by explicit admin approval.

### Old Compatibility — Existing `training_records` Created by Legacy Path
Phase 0 does NOT retroactively fix or remove `training_records` that were previously created by the old `bulk-save` or `bulk-upload`. These records remain in the database and continue to be read by the canonical evaluator. They will show as valid training completions if they have valid `completion_date` and `expiry_date`.

**This is acceptable:** the existing records represent historical entries that were saved by admins. They were reviewed in the extractor preview step (steps 3-4 of the old workflow). The issue was that "save" equalled "completion" — but the admin did explicitly click save. The risk was extraction errors being auto-committed, not malicious data.

If a retroactive cleanup is needed, it would be a separate data audit task (query `training_records` where `source: "bulk_import"` and verify against actual certificates).
