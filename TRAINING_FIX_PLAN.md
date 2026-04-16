# Training System — Strict Fix Plan

**Date:** 2026-04-17  
**Status:** PLAN ONLY — no implementation until approved  
**Prerequisite:** TRAINING_SYSTEM_AUDIT.md (all findings verified at code level)

---

## 1. Phase-by-Phase Rollout

### Phase 0 — EMERGENCY STOP: Disable uncontrolled training writes

**Objective:** Stop `bulk-upload` from creating completed `training_records`. Fix certificate storage so uploaded files are viewable.

**Files touched:**
| File | Change |
|---|---|
| `backend/server.py` L11576–11745 | Rewrite `bulk_upload_training_certificates()` to stop inserting `training_records` |
| `backend/server.py` L11623–11633 | Replace local disk write with `put_object()` (Supabase) |

**Expected impact:**
- `bulk-upload` stops producing unreviewed completed training outcomes
- Uploaded certificates become viewable immediately (Supabase path matches viewer)
- Admin will see extraction results as a preview, not as committed records
- No change to the safe alternative paths (`/training/intake/from-upload`, `/training/manual`)

**Risk:** LOW — the endpoint is already producing wrong data; making it safe cannot make things worse.

**Rollback:** Revert the single function. No schema migration involved.

---

### Phase 1 — GATE: Certificate upload stops auto-completing training

**Objective:** All 4 certificate upload paths stop setting `completion_date = now`. Uploading evidence does not equal completion.

**Files touched:**
| File | Change |
|---|---|
| `backend/server.py` L22131 (`upload_training_certificate`) | Remove `"completion_date": now` from update_data |
| `backend/server.py` L22252 (`upload_training_certificate_for_requirement`) | Remove `"completion_date": now` from both update and insert branches |
| `backend/server.py` ~L15150 (unified evidence upload, training branch) | Remove `"completion_date": now` |
| `backend/server.py` L22176 | Remove `"completion_method": "certificate"` auto-set |

**Expected impact:**
- Certificate upload adds evidence to `evidence_files[]` / `certificate_url` only
- Training stays `not_started` until admin explicitly completes or verifies
- Existing completed records with certificates already set are unaffected
- Worker dashboard and admin views show "Evidence uploaded — awaiting review" instead of "Completed"

**Risk:** MEDIUM — admin workflow must now include an explicit "mark complete" step after viewing evidence. If no UI affordance exists, training stays in limbo.

**Mitigation:** Phase 1 must ship with a clear admin action button to mark complete after reviewing evidence. The manual training record endpoint (`/training/manual`, L40046) already exists and sets `status: "completed"`.

**Rollback:** Restore `completion_date: now` lines.

---

### Phase 2 — UNIFY: Single status evaluator

**Objective:** Every runtime surface calls `compute_training_record_status()` / `evaluate_employee_training_status()`. All independent evaluators removed or redirected.

**Files touched:**
| File | Current evaluator | Change |
|---|---|---|
| `backend/unified_compliance_engine.py` L483 (`is_training_valid()`) | Checks `verified` OR stored `status=="verified"` independently | Rewrite: call `compute_training_record_status()` from server.py, then check `verified` flag |
| `backend/work_readiness_engine.py` L310–365 | Inline verified + expiry check | Replace: import and call `compute_training_record_status()`, then check `verified` |
| `backend/routes/worker_dashboard.py` L688–830 | Inline expiry parsing + status derivation | Replace: import and call `evaluate_employee_training_status()` for mandatories |
| `backend/compliance_engine/status.py` L489–530 (`_get_training_status()`) | Queries `training_types` collection, no status filter | Rewrite: call canonical evaluator. Remove `training_types` dependency. Add `record_status` filter. |
| `frontend/src/components/training/EnhancedTrainingTab.js` L61–68 | Local `isExpired()` / `getDaysUntilExpiry()` JS functions | Remove: use `computed_status` and `days_until_expiry` from API response |

**Expected impact:**
- Same training shows same status on every surface
- UCE compliance gate, worker dashboard, work readiness, admin views, and frontend all agree
- Status disagreement bugs eliminated

**Risk:** MEDIUM — if a downstream consumer expects a different field name (e.g. `status` vs `computed_status`), that surface may break.

**Mitigation:** Enrichment function `enrich_training_record_with_computed_status()` already exists at server.py ~L6740 and copies computed values onto the record. All API responses should use this enrichment.

**Rollback:** Each evaluator change is independent. Can revert individual files.

---

### Phase 3 — UNIFY: Single mandatory training definition

**Objective:** One canonical list of mandatory trainings with one set of IDs.

**Files touched:**
| File | Current definition | Change |
|---|---|---|
| NEW: `backend/training_definitions.py` | — | Create: single canonical definition file |
| `backend/unified_compliance_engine.py` L52 (`MANDATORY_TRAINING_HCA`) | 8 items, uses `safeguarding_adults`, `basic_life_support` | Import from `training_definitions.py` |
| `backend/server.py` L11297 (`MANDATORY_TRAININGS`) | **6 items — missing IG and Prevent** | Delete. Import from `training_definitions.py` |
| `backend/server.py` L11313 (`is_mandatory_training()`) | Substring match against 6-item list | Rewrite: import canonical list |
| `backend/work_readiness_engine.py` L310 (`mandatory_training`) | 8-item inline list | Import from `training_definitions.py` |
| `backend/routes/worker_dashboard.py` L688 (`mandatory_trainings`) | 8-item inline dict | Import from `training_definitions.py` |
| `backend/services/multi_training_extraction.py` L26 (`MANDATORY_TRAINING_BY_ROLE`) | 8 per role, uses `safeguarding`, `basic_life_support` | Import core list from `training_definitions.py`, keep role-specific extensions local |

**ID reconciliation:**

| Training | Canonical ID | Current variants to reconcile |
|---|---|---|
| Safeguarding | `safeguarding` | `safeguarding_adults` (UCE) |
| Manual Handling | `manual_handling` | — |
| Fire Safety | `fire_safety` | — |
| Health & Safety | `health_safety` | — |
| Basic Life Support | `bls` | `basic_life_support` (UCE, extraction) |
| Infection Control | `infection_control` | — |
| Information Governance | `information_governance` | MISSING from server.py L11297 |
| Prevent | `prevent` | MISSING from server.py L11297 |

Canonical evaluator (`evaluate_employee_training_status()`, server.py L6862) already uses fuzzy name matching to locate records. After Phase 3, all definition sites use the same IDs, so fuzzy matching becomes a safety net rather than the primary mechanism.

**Risk:** LOW — definition consolidation only. Record-matching logic is fuzzy and tolerant.

**Rollback:** Revert imports to inline constants.

---

### Phase 4 — CLEAN: Schema enforcement

**Objective:** Every `training_records` insert goes through a validated model. Duplicate fields eliminated.

**Files touched:**
| File | Change |
|---|---|
| NEW: `backend/models/training_record.py` | Create `TrainingRecordCreate` Pydantic model |
| All write paths (W1–W41 from audit) | Use model for inserts/updates |

**Canonical field set (after cleanup):**
```
id: str (UUID)
employee_id: str
training_name: str
requirement_id: str
mandatory: bool
completion_date: Optional[str]  # ISO datetime — only set by explicit admin action
expiry_date: Optional[str]      # ISO datetime
certificate_url: Optional[str]  # Supabase path
evidence_files: list[dict]      # { file_id, file_url, original_filename, uploaded_at, status }
verified: bool                  # Only set by /verify endpoint
verified_by: Optional[str]      # user_id
verified_at: Optional[str]      # ISO datetime
record_status: str              # "active" | "superseded" | "deleted"
completion_method: Optional[str] # "manual" | "certificate" | "intake_review"
created_at: str
updated_at: str
```

**Fields to remove/stop writing:**
- `status` (stored) → always derive via `compute_training_record_status()`
- `is_mandatory` → use `mandatory` only
- `provider_name` → use `provider` only
- `training_code` → use `requirement_id` only
- `needs_manual_review` → always false after Phase 0 (proposals go to separate collection)
- `extracted_by_ai` → move to audit trail metadata, not on canonical record

**Risk:** MEDIUM — existing records with old field names must still be readable.

**Mitigation:** Read-side code must fall back: `record.get("mandatory") or record.get("is_mandatory", False)`. Schema enforcement is write-side only. No migration of existing docs required.

**Rollback:** Remove Pydantic model usage; revert to raw dicts.

---

### Phase 5 — CLEAN: Certificates tab data source

**Objective:** Certificates tab reads `training_records` with evidence, not `employee_documents`.

**Files touched:**
| File | Change |
|---|---|
| `frontend/src/components/training/AuditReadyTrainingMatrix.js` L152 | Replace `GET /employee-documents?employee_id=${id}` with `GET /employees/${id}/training-records?has_certificate=true` |
| `backend/server.py` or `backend/routes/training.py` | Add filter parameter to training records list endpoint: `has_certificate=true` returns only records with `certificate_url` or non-empty `evidence_files` |

**Expected impact:**
- Certificates tab shows actual uploaded certificates from training records
- No more empty tab when certificates were uploaded via bulk-upload or direct upload

**Risk:** LOW — read-path change only. No data mutation.

**Rollback:** Revert frontend fetch URL.

---

### Phase 6 — CLEAN: Dead code and duplicate removal

**Objective:** Remove code no longer needed after canonical flows are in place.

**Covered in section 7 below.**

---

## 2. Exact Phase 0 Safety Patch

### Target: `bulk_upload_training_certificates()` at server.py L11576

**Current behavior:**
1. Upload file → save to local disk (`Path("/app/uploads/training")`)
2. AI extraction → returns list of trainings
3. For-loop at L11671 → `db.training_records.insert_one()` for EACH extracted item
4. Each record has `status: "completed"`, `verified: False`
5. Return full list of inserted records

**New behavior:**
1. Upload file → save to **Supabase** via `put_object()`
2. AI extraction → returns list of trainings (unchanged)
3. **NO `training_records` inserts.** Store results in `proposed_training_items` collection.
4. Return extraction preview with `proposed_training_items` IDs
5. Admin reviews via existing `POST /employees/{eid}/training/proposed-items/review`

### Exact changes to `bulk_upload_training_certificates()`:

**Replace** (L11623–11633, local file save):
```python
# BEFORE:
upload_dir = Path("/app/uploads/training") / employee_id
upload_dir.mkdir(parents=True, exist_ok=True)
safe_filename = f"{uuid.uuid4().hex[:8]}_{file.filename}"
file_path = upload_dir / safe_filename
with open(file_path, "wb") as f:
    f.write(contents)
file_url = f"/uploads/training/{employee_id}/{safe_filename}"
```
```python
# AFTER:
file_ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "pdf"
storage_path = f"{APP_NAME}/training/{employee_id}/{uuid.uuid4().hex[:8]}_{file.filename}"
content_type = file.content_type or "application/pdf"
if file_ext in ("png", "jpg", "jpeg", "webp"):
    content_type = f"image/{file_ext.replace('jpg', 'jpeg')}"
upload_result = put_object(storage_path, contents, content_type)
file_url = upload_result.get("path") or storage_path
```

**Replace** (L11671–11720, the insert loop):
```python
# BEFORE: for training in extraction_result.get("trainings", []):
#   ... training_record = { "status": "completed", ... }
#   ... await db.training_records.insert_one(training_record)

# AFTER:
now = datetime.now(timezone.utc).isoformat()
proposed_items = []

for training in extraction_result.get("trainings", []):
    training_name = training.get("training_name") or training.get("name", "Unknown Training")

    proposed_item = {
        "id": str(uuid.uuid4()),
        "employee_id": employee_id,
        "source_document_url": file_url,
        "source_document_name": file.filename,
        "training_name": training_name,
        "course_name": training.get("course_name", training_name),
        "provider": training.get("provider"),
        "completion_date": training.get("completion_date"),
        "expiry_date": training.get("expiry_date"),
        "certificate_number": training.get("certificate_number"),
        "mapped_training_code": training.get("training_id"),
        "is_mandatory": training.get("is_mandatory", False),
        "blocks_promotion": training.get("blocks_promotion", False),
        "ai_extracted": True,
        "status": "proposed",        # NOT "completed"
        "created_at": now,
        "uploaded_by": user.get("user_id"),
    }
    proposed_items.append(proposed_item)

if proposed_items:
    await db.proposed_training_items.insert_many(proposed_items)
```

**Replace** return value:
```python
# AFTER:
mandatory = [p for p in proposed_items if p.get("is_mandatory")]
additional = [p for p in proposed_items if not p.get("is_mandatory")]

await log_audit_action(user['user_id'], "training_bulk_upload", "employee", employee_id, {
    "file_uploaded": file.filename,
    "trainings_extracted": len(proposed_items),
    "mandatory_count": len(mandatory),
    "additional_count": len(additional),
    "status": "proposed_for_review",  # not "completed"
})

return {
    "success": True,
    "file_uploaded": file.filename,
    "file_url": file_url,
    "proposed_items": [
        {
            "id": p["id"],
            "training_name": p["training_name"],
            "completion_date": p.get("completion_date"),
            "expiry_date": p.get("expiry_date"),
            "is_mandatory": p.get("is_mandatory", False),
            "status": "proposed",
        }
        for p in proposed_items
    ],
    "total_extracted": len(proposed_items),
    "requires_review": True,
    "message": f"Extracted {len(proposed_items)} training(s). Admin review required before records are created."
}
```

### Frontend impact of Phase 0

The frontend component that calls `bulk-upload` (likely `TrainingCertificateExtractor.js` or similar) currently expects `response.data.trainings` as committed records. After Phase 0:

- Response shape changes: `trainings` → `proposed_items`, each has `status: "proposed"`
- Frontend should show "Extraction complete — X items pending admin review" instead of "X trainings added"
- Frontend should redirect admin to the proposed items review UI (already exists)

### What Phase 0 does NOT change
- `POST /training/extract-certificate` — preview only, no writes (safe, unchanged)
- `POST /training/re-extract` — preview only (safe, unchanged)
- `POST /training/intake/from-upload` — already uses Supabase + proposed items (safe, unchanged)
- `POST /training/proposed-items/review` — already creates canonical records from proposals (safe, unchanged)
- `POST /training/manual` — admin manual entry (intentional, unchanged)

---

## 3. Canonical Write Model

After Phase 0 + Phase 1, these are the ONLY allowed write paths to `training_records`:

### A. Direct writes to `training_records` (allowed, gated)

| Path | Trigger | Who | Sets `completion_date`? | Sets `verified`? |
|---|---|---|---|---|
| `POST /{eid}/training/proposed-items/review` (approve) | Admin approves proposed items from extraction | Admin only | YES — from proposed item's `completion_date` | NO — `verified: False` |
| `POST /{eid}/training/manual` | Admin manually creates record | Admin only | YES — from admin input | NO — `verified: False` |
| `POST /{eid}/training/record` | Admin creates record | Admin only | YES — from admin input | NO — `verified: False` |
| `POST /{eid}/training/{id}/verify` | Admin verifies a completed record | Admin only | NO (already set) | YES — `verified: True` |
| `POST /{eid}/training/{id}/reject` | Admin rejects a record | Admin only | NO | Sets `verification_status: "rejected"` |
| `POST /{eid}/training/{id}/unverify` | Admin revokes verification | Admin only | NO | `verified: False` |
| `get_or_create_training_record()` | Ensures blank record exists for a requirement | System | NO — creates with `completion_date: None` | NO |
| `supersede_training_record()` | Marks old record as superseded | System | NO | NO |

### B. Evidence-only writes (no completion, no status mutation)

| Path | Writes to | What it does |
|---|---|---|
| `POST /training-records/{id}/upload-certificate` | `training_records.certificate_url`, `training_records.evidence_files[]` | Adds file evidence. Does NOT set `completion_date`. |
| `POST /{eid}/training/{req}/upload-certificate` | `training_records.certificate_url`, `training_records.evidence_files[]` | Adds file evidence. Does NOT set `completion_date`. |
| Unified evidence upload (training branch, L15150) | `training_records.evidence_files[]` | Adds file evidence. Does NOT set `completion_date`. |
| Worker dashboard upload (`/worker/upload-document/training_*`) | `proposed_training_items` + `employee_documents` | Creates proposed items for admin review. Does NOT touch `training_records`. |

### C. Suggestion-only writes (proposals, NOT training_records)

| Path | Writes to | What it does |
|---|---|---|
| `POST /{eid}/training/bulk-upload` (after Phase 0) | `proposed_training_items` | AI extraction → proposed items. NO `training_records` writes. |
| `POST /{eid}/training/intake/from-upload` | `proposed_training_items` via `employee_documents` | Upload + extraction → proposed items. |
| `POST /training/respond/{token}/upload` | `employee_documents` | Worker public upload → proposed items. |

### D. Must NEVER auto-complete training

| Action | Rule |
|---|---|
| Certificate file upload | Evidence only. No `completion_date`. |
| AI extraction | Proposals only. No `training_records` inserts. |
| Document verification (verification_sync) | Must NOT auto-set `verified: True` on training records based on document verification. Training verification is a separate admin action. |
| Induction auto-sync | May mark induction items complete from verified training. Must NOT create or complete training records. |

---

## 4. Canonical Read Model

### After Phase 2, every read surface works as follows:

| Surface | Endpoint | Reads From | Evaluator | Duplicated evaluator to remove |
|---|---|---|---|---|
| **Admin — Training Matrix** | `GET /{eid}/training/matrix` | `training_records` | `evaluate_employee_training_status()` → calls `compute_training_record_status()` per record | None — already correct |
| **Admin — Training Tab** | `GET /{eid}/training` or `GET /{eid}/training-records` | `training_records` | `enrich_training_record_with_computed_status()` per record | None — already correct |
| **Admin — Certificates Tab** | Phase 5: `GET /{eid}/training-records?has_certificate=true` | `training_records` (filtered to records with `certificate_url` or `evidence_files`) | N/A — data display only | Remove: `GET /employee-documents` query from `AuditReadyTrainingMatrix.js` L152 |
| **Worker Dashboard — Training Section** | `GET /worker/dashboard` | `training_records` via `evaluate_employee_training_status()` | Must call canonical evaluator | Remove: inline evaluator at `worker_dashboard.py` L688–830 |
| **UCE — Compliance Gate** | `get_unified_employee_status()` | `training_records` | Must call `compute_training_record_status()` then check `verified` | Remove: independent `is_training_valid()` at `unified_compliance_engine.py` L483 |
| **Work Readiness Engine** | `compute_work_readiness()` | `training_records` | Must call `compute_training_record_status()` then check `verified` | Remove: inline evaluator at `work_readiness_engine.py` L310–365 |
| **Compliance Engine (legacy)** | `_get_training_status()` | `training_records` | Must call canonical evaluator | Remove: `training_types` collection dependency, add `record_status` filter. `compliance_engine/status.py` L489–530 |
| **Frontend — EnhancedTrainingTab** | `GET /{eid}/training-records` | `training_records` enriched by backend | Use `computed_status`, `days_until_expiry`, `status_color` from API response | Remove: `isExpired()` and `getDaysUntilExpiry()` at `EnhancedTrainingTab.js` L61–68 |
| **Frontend — TrainingMatrix** | `GET /{eid}/training/matrix` | Backend-computed | Use backend-computed status | None — already correct |
| **Dashboard Summaries** | `GET /dashboard/training-summary` | `training_records` | `evaluate_employee_training_status()` | None — already correct |
| **Induction auto-sync** | `get_employee_induction_status()` | `training_records` + `employee_documents` | `_build_verified_training_set()` | Remove: `employee_documents` regex query from `induction_definitions.py` L290. Read `training_records` only. |
| **Expiry alerts** | `calculate_expiry_alerts_quick()` | `training_records` + `employee_documents` | Various date parsing | Remove: `employee_documents` training reads. Read `training_records` only. |

### Canonical evaluator chain:

```
compute_training_record_status(record) → per-record status
    ↓ used by
evaluate_employee_training_status(employee_id, db) → per-employee summary
    ↓ used by
GET /{eid}/training/matrix, GET /worker/dashboard, UCE, work readiness, etc.
```

All surfaces must funnel through this chain. No independent date parsing, no stored `status` field reads, no `training_types` collection queries.

---

## 5. Certificate Storage / Viewing Fix

### Root cause (confirmed)

| Operation | Storage | Path stored on record |
|---|---|---|
| `bulk-upload` (L11623) | **Local disk**: `Path("/app/uploads/training")` | `/uploads/training/{eid}/{filename}` |
| `upload_training_certificate` (L22158) | **Supabase**: `put_object()` | `{APP_NAME}/certificates/{eid}/{filename}` |
| `upload_training_certificate_for_requirement` (L22291) | **Supabase**: `put_object()` | `{APP_NAME}/certificates/{eid}/{filename}` |
| `intake/from-upload` (L39972) | **Supabase**: `put_object()` | `{APP_NAME}/training/{eid}/{uuid}.{ext}` |
| Certificate viewer (L22198) | Reads via `get_object()` | Expects **Supabase** path |

The viewer ALWAYS calls `get_object()` which hits Supabase storage. Files saved locally are unreachable.

### Short-term fix (Phase 0 — ship immediately)

Change `bulk-upload` to use `put_object()` instead of local disk write. This is already included in the Phase 0 patch above.

**No local-disk fallback.** Local disk storage is not viable on Railway (ephemeral filesystem). Files saved there are lost on every deploy.

### Long-term fix (already achieved by Phase 0)

After Phase 0, ALL training certificate uploads go through `put_object()`. The viewer's `get_object()` call works for all paths. No further migration needed for NEW files.

### Existing broken files

Files uploaded via the old `bulk-upload` are on local disk and already lost (Railway ephemeral FS). They are not recoverable.

**Impact:** Any `training_records` with `certificate_url` starting with `/uploads/training/` have broken certificate links. These records exist but their certificates are gone.

**Remediation options:**
1. **Flag affected records.** Query `training_records` where `certificate_url` starts with `/uploads/training/`. Mark as `certificate_status: "lost"`. Notify admin to re-upload.
2. **Bulk re-upload.** Admin re-uploads certificates for affected records. New upload uses Supabase path.

**Migration script (one-time):**
```python
broken = await db.training_records.find({
    "certificate_url": {"$regex": "^/uploads/training/"}
}).to_list(None)
for r in broken:
    await db.training_records.update_one(
        {"id": r["id"]},
        {"$set": {"certificate_url_broken": True, "certificate_url_original": r["certificate_url"]}}
    )
print(f"Flagged {len(broken)} records with lost certificates")
```

---

## 6. Mandatory Training Definition Cleanup

### Canonical source: NEW `backend/training_definitions.py`

```python
# backend/training_definitions.py
# SINGLE SOURCE OF TRUTH for mandatory training requirements.

MANDATORY_TRAINING = [
    {"id": "safeguarding",           "name": "Safeguarding Adults",                     "expiry_months": 12, "blocker": True},
    {"id": "manual_handling",        "name": "Manual Handling / Moving & Handling",      "expiry_months": 12, "blocker": True},
    {"id": "fire_safety",            "name": "Fire Safety",                              "expiry_months": 12, "blocker": True},
    {"id": "health_safety",          "name": "Health & Safety",                          "expiry_months": 12, "blocker": True},
    {"id": "bls",                    "name": "Basic Life Support (BLS)",                 "expiry_months": 12, "blocker": True},
    {"id": "infection_control",      "name": "Infection Prevention & Control",           "expiry_months": 12, "blocker": True},
    {"id": "information_governance", "name": "Information Governance / GDPR",            "expiry_months": 12, "blocker": True},
    {"id": "prevent",                "name": "Prevent (Counter-Terrorism Awareness)",    "expiry_months": 36, "blocker": True},
]

MANDATORY_TRAINING_IDS = frozenset(t["id"] for t in MANDATORY_TRAINING)

# Aliases: map any variant ID seen in the wild to the canonical ID above.
# Evaluators use this to find records regardless of which ID was written.
TRAINING_ID_ALIASES = {
    "safeguarding_adults": "safeguarding",
    "safeguarding_children": "safeguarding",
    "safeguard": "safeguarding",
    "basic_life_support": "bls",
    "resuscitation": "bls",
    "cpr": "bls",
    "first_aid": "bls",
    "moving_and_handling": "manual_handling",
    "moving_handling": "manual_handling",
    "patient_handling": "manual_handling",
    "health_and_safety": "health_safety",
    "fire_awareness": "fire_safety",
    "infection_prevention": "infection_control",
    "ipc": "infection_control",
    "gdpr": "information_governance",
    "data_protection": "information_governance",
    "ig_training": "information_governance",
    "counter_terrorism": "prevent",
    "radicalisation": "prevent",
    "prevent_duty": "prevent",
}
```

### Duplicate definitions to remove or redirect

| Location | Current | Action |
|---|---|---|
| `unified_compliance_engine.py` L52 (`MANDATORY_TRAINING_HCA`) | 8 items, uses `safeguarding_adults`, `basic_life_support` | Replace with: `from training_definitions import MANDATORY_TRAINING` + alias map |
| `server.py` L11297 (`MANDATORY_TRAININGS`) | **6 items — MISSING IG and Prevent** | DELETE entirely. Replace `is_mandatory_training()` with import from `training_definitions.py` |
| `work_readiness_engine.py` L310 | 8-item inline list | Replace with: `from training_definitions import MANDATORY_TRAINING_IDS` |
| `routes/worker_dashboard.py` L688 | 8-item inline dict | Replace with: `from training_definitions import MANDATORY_TRAINING` (derive dict from it) |
| `services/multi_training_extraction.py` L26 (`MANDATORY_TRAINING_BY_ROLE`) | Per-role lists | Keep role-specific extensions. Import base 8 from `training_definitions.py`. |

### ID reconciliation rules

1. **Canonical IDs** are the `id` values in `MANDATORY_TRAINING` above: `safeguarding`, `bls`, etc.
2. **Alias map** resolves old IDs: `safeguarding_adults` → `safeguarding`, `basic_life_support` → `bls`.
3. **Record matching** continues to use fuzzy name matching (canonical evaluator at L6862) as a safety net.
4. **New writes** must use canonical IDs only. The `TrainingRecordCreate` model (Phase 4) validates `requirement_id` against `MANDATORY_TRAINING_IDS`.
5. **Existing records** with old IDs (`safeguarding_adults`, `basic_life_support`) are NOT migrated. The alias map resolves them at read time.

---

## 7. Dead Code / Duplicated Logic Removal Plan

### Status evaluators to remove after Phase 2

| Code | File | Line | Reason |
|---|---|---|---|
| `is_training_valid()` | `unified_compliance_engine.py` | L483 | Replaced by canonical evaluator call |
| Inline training status derivation | `routes/worker_dashboard.py` | L688–830 | Replaced by canonical evaluator call |
| Inline training verified+expiry check | `work_readiness_engine.py` | L310–365 | Replaced by canonical evaluator call |
| `_get_training_status()` | `compliance_engine/status.py` | L489–530 | Replaced by canonical evaluator call. Also removes `training_types` collection dependency. |
| `isExpired()` / `getDaysUntilExpiry()` | `EnhancedTrainingTab.js` | L61–68 | Replaced by backend `computed_status` / `days_until_expiry` |
| `isExpired` (inline) | `EnhancedTrainingTab.js` | L267 | Same — use backend values |

### Upload flows to retire after Phase 0

| Code | File | Line | Reason |
|---|---|---|---|
| Local disk file save in `bulk-upload` | `server.py` | L11623–11633 | Replaced by `put_object()` |
| Direct `training_records.insert_one()` loop in `bulk-upload` | `server.py` | L11671–11720 | Replaced by `proposed_training_items.insert_many()` |

### Constants to delete after Phase 3

| Constant | File | Line | Reason |
|---|---|---|---|
| `MANDATORY_TRAININGS` (6-item list) | `server.py` | L11297 | Replaced by `training_definitions.MANDATORY_TRAINING` |
| `is_mandatory_training()` | `server.py` | L11311 | Replaced by import from `training_definitions` |
| `mandatory_trainings` (inline dict) | `routes/worker_dashboard.py` | L688 | Replaced by import from `training_definitions` |
| `mandatory_training` (inline list) | `work_readiness_engine.py` | L310 | Replaced by import from `training_definitions` |

### Mixed-source reads to fix after Phase 2

| Read path | File | Line | Current sources | Target source |
|---|---|---|---|---|
| `_build_verified_training_set()` | `induction_definitions.py` | L290 | `training_records` + `employee_documents` | `training_records` only |
| `calculate_expiry_alerts_quick()` | `server.py` | L2679 | `training_records` + `employee_documents` | `training_records` only |
| Certificates tab fetch | `AuditReadyTrainingMatrix.js` | L152 | `employee_documents` | `training_records` with evidence filter |
| Training section of compliance requirements | `server.py` L795 | `training_records` + `employee_documents` + `generated_forms` | `training_records` only for training status |

### Verification sync to gate after Phase 1

| Code | File | Line | Change |
|---|---|---|---|
| Auto-verify training from document verification | `routes/verification_sync.py` | L160–178 | Remove or gate: verifying a source document must NOT auto-set `verified: True` on training records. Training verification is a separate admin action. |

---

## Phase Dependency Graph

```
Phase 0 (EMERGENCY)
  │  Stop bulk-upload auto-writes
  │  Fix certificate storage to Supabase
  │
  ├── Phase 1 (GATE)
  │     Stop all certificate uploads from auto-completing
  │     │
  │     └── Phase 2 (UNIFY EVALUATORS)
  │           Single status evaluator everywhere
  │           │
  │           ├── Phase 4 (SCHEMA)
  │           │     Pydantic model enforcement
  │           │
  │           └── Phase 6 (DEAD CODE)
  │                 Remove retired evaluators and constants
  │
  ├── Phase 3 (UNIFY DEFINITIONS)
  │     Single training_definitions.py
  │     (independent of Phase 2)
  │
  └── Phase 5 (CERTIFICATES TAB)
        Fix data source to training_records
        (independent of Phase 2)
```

Phase 0 ships first. Phases 1, 3, 5 can run in parallel after Phase 0. Phase 2 follows Phase 1. Phases 4 and 6 follow Phase 2.
