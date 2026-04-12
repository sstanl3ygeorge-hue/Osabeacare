# Identity & Proof of Address Minimal Hardening Patch

## Summary
Tightens the existing Identity and PoA admin review flow by:
1. Adding a lightweight review checklist requirement before verification
2. Requiring file_viewed confirmation before Verify & Stamp actions
3. Storing minimal metadata (reviewed_by, reviewed_at, checklist)
4. Leveraging existing admin UI/endpoints

**Changes:** backend/server.py and frontend/src/components/compliance/QuickVerifyStampDialog.js  
**New endpoints:** 1 lightweight endpoint  
**New models:** 1 Pydantic model  
**No new routers, dialogs, or hooks**

---

## Exact Changes

### CHANGE 1: Add Request Model (before endpoint definition)

**Location:** backend/server.py, line ~19120 (before `start_document_review` endpoint)

```python
class DocumentReviewChecklistRequest(BaseModel):
    """Lightweight review checklist for Identity/PoA documents before verification."""
    file_viewed: bool = Field(..., description="Admin has opened and viewed the file")
    name_matches: bool = Field(..., description="Name/details on document match profile")
    document_acceptable: bool = Field(..., description="Document type is acceptable")
    legible: bool = Field(..., description="Document is legible and clear")
    front_present: Optional[bool] = Field(None, description="Front side present (Identity only)")
    back_present: Optional[bool] = Field(None, description="Back side present (Identity only)")
    address_valid: Optional[bool] = Field(None, description="Address valid (PoA only)")
    date_valid: Optional[bool] = Field(None, description="Document within acceptable date range (PoA only)")
```

---

### CHANGE 2: Add New Lightweight Review Endpoint

**Location:** backend/server.py, after the model above

```python
@api_router.post("/employee-documents/{doc_id}/start-review")
async def start_document_review(
    doc_id: str, 
    payload: DocumentReviewChecklistRequest,
    user: dict = Depends(require_manager_or_admin)
):
    """
    Record that admin has opened a document and confirms review checklist items.
    This enables the verify action for Identity and Proof of Address documents.
    
    For minimal compliance hardening only - stores file_viewed and checklist.
    """
    doc = await db.employee_documents.find_one({"id": doc_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    requirement_id = doc.get("requirement_id", "").lower()
    is_identity_poa = any(x in requirement_id for x in ["identity", "proof_of_address"])
    
    if not is_identity_poa:
        raise HTTPException(status_code=400, detail="Review checklist only for Identity and Proof of Address documents")
    
    # Validate checklist - at least file_viewed + one other must be true
    checklist_items = [
        payload.file_viewed,
        payload.name_matches,
        payload.document_acceptable,
        payload.legible
    ]
    if sum(checklist_items) < 2:
        raise HTTPException(status_code=400, detail="At least 2 checklist items required (file_viewed must be true)")
    
    if not payload.file_viewed:
        raise HTTPException(status_code=400, detail="file_viewed must be true before verification")
    
    now = datetime.now(timezone.utc).isoformat()
    reviewer = await db.users.find_one({"user_id": user['user_id']}, {"_id": 0, "name": 1})
    reviewer_name = reviewer.get('name') if reviewer else user.get('email', 'Admin')
    
    review_checklist = {
        "file_viewed": payload.file_viewed,
        "name_matches": payload.name_matches,
        "document_acceptable": payload.document_acceptable,
        "legible": payload.legible,
    }
    
    # Add type-specific fields
    if "identity" in requirement_id:
        review_checklist["front_present"] = payload.front_present or False
        review_checklist["back_present"] = payload.back_present or False
    elif "address" in requirement_id:
        review_checklist["address_valid"] = payload.address_valid or False
        review_checklist["date_valid"] = payload.date_valid or False
    
    update_data = {
        "file_viewed": True,
        "file_viewed_at": now,
        "file_viewed_by": user['user_id'],
        "file_viewed_by_name": reviewer_name,
        "review_checklist": review_checklist,
        "last_reviewed_at": now,
        "last_reviewed_by": user['user_id'],
        "last_reviewed_by_name": reviewer_name
    }
    
    await db.employee_documents.update_one({"id": doc_id}, {"$set": update_data})
    
    # Log to audit trail
    await log_audit_action(user['user_id'], "start_document_review", "employee_document", doc_id, {
        "checklist": review_checklist,
        "requirement_id": requirement_id,
        "employee_id": doc.get("employee_id")
    })
    
    return {"success": True, "message": "Review checklist recorded. Verification enabled."}
```

---

### CHANGE 3: Add Guard to `/employee-documents/{doc_id}/verify` Endpoint

**Location:** backend/server.py, in existing `verify_employee_document` function

**Before:**
```python
@api_router.post("/employee-documents/{doc_id}/verify")
async def verify_employee_document(doc_id: str, user: dict = Depends(require_manager_or_admin)):
    """
    Mark a document as verified.
    
    LEGAL DOCUMENT RESTRICTION:
    - Sensitive/legal documents require ADMIN+ to verify
    """
    doc = await db.employee_documents.find_one({"id": doc_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # LEGAL DOCUMENT RESTRICTION
    LEGAL_SENSITIVE_REQUIREMENTS = [
        "right_to_work_documents",
        "right_to_work_check",
        "dbs_certificate",
        "dbs_check",
        "identity_documents",
        "proof_of_address"
    ]
    
    requirement_id = doc.get("requirement_id", "")
    if requirement_id in LEGAL_SENSITIVE_REQUIREMENTS:
        if user.get('role') == UserRole.BRANCH_MANAGER:
            raise HTTPException(
                status_code=403,
                detail=f"Legal/sensitive documents ({requirement_id}) require Admin verification."
            )
    
    # Ensure document is approved before verification
    if doc.get('status') not in ['approved', 'uploaded']:
        raise HTTPException(status_code=400, detail="Document must be approved before verification")
```

**After:**
```python
@api_router.post("/employee-documents/{doc_id}/verify")
async def verify_employee_document(doc_id: str, user: dict = Depends(require_manager_or_admin)):
    """
    Mark a document as verified.
    
    LEGAL DOCUMENT RESTRICTION:
    - Sensitive/legal documents require ADMIN+ to verify
    
    IDENTITY/POA HARDENING:
    - Requires review checklist completion before verification
    """
    doc = await db.employee_documents.find_one({"id": doc_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # LEGAL DOCUMENT RESTRICTION
    LEGAL_SENSITIVE_REQUIREMENTS = [
        "right_to_work_documents",
        "right_to_work_check",
        "dbs_certificate",
        "dbs_check",
        "identity_documents",
        "proof_of_address"
    ]
    
    requirement_id = doc.get("requirement_id", "")
    if requirement_id in LEGAL_SENSITIVE_REQUIREMENTS:
        if user.get('role') == UserRole.BRANCH_MANAGER:
            raise HTTPException(
                status_code=403,
                detail=f"Legal/sensitive documents ({requirement_id}) require Admin verification."
            )
    
    # HARDENING: For Identity/PoA, require review checklist before verification
    is_identity_poa = any(x in requirement_id.lower() for x in ["identity", "proof_of_address"])
    if is_identity_poa and not doc.get("file_viewed"):
        raise HTTPException(
            status_code=400,
            detail="Must complete review checklist before verification. Call /start-review endpoint first."
        )
    
    # Ensure document is approved before verification
    if doc.get('status') not in ['approved', 'uploaded']:
        raise HTTPException(status_code=400, detail="Document must be approved before verification")
```

---

### CHANGE 4: Add Guard to `/employee-documents/{doc_id}/verify-with-digital-stamp` Endpoint

**Location:** backend/server.py, in existing `verify_document_with_digital_stamp` function

**Before:**
```python
@api_router.post("/employee-documents/{doc_id}/verify-with-digital-stamp")
async def verify_document_with_digital_stamp(
    doc_id: str,
    payload: DocumentVerificationStampRequest,
    user: dict = Depends(require_manager_or_admin)
):
    """
    Verify a document and add a VISIBLE digital stamp to the file.
    
    The stamp is permanently embedded into the PDF/image and cannot be removed.
    This creates a new stamped version while preserving the original.
    
    CQC/Medway Requirement: Visible proof of document verification.
    
    Supported formats: PDF, JPG, JPEG, PNG
    """
    from io import BytesIO
    
    # Validate stamp type
    if payload.stamp_type not in VERIFICATION_STAMP_TYPES:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid stamp type. Valid options: {list(VERIFICATION_STAMP_TYPES.keys())}"
        )
    
    doc = await db.employee_documents.find_one({"id": doc_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Get employee info for stamp
```

**After:**
```python
@api_router.post("/employee-documents/{doc_id}/verify-with-digital-stamp")
async def verify_document_with_digital_stamp(
    doc_id: str,
    payload: DocumentVerificationStampRequest,
    user: dict = Depends(require_manager_or_admin)
):
    """
    Verify a document and add a VISIBLE digital stamp to the file.
    
    The stamp is permanently embedded into the PDF/image and cannot be removed.
    This creates a new stamped version while preserving the original.
    
    CQC/Medway Requirement: Visible proof of document verification.
    
    Supported formats: PDF, JPG, JPEG, PNG
    
    IDENTITY/POA HARDENING:
    - Requires review checklist completion before stamping
    """
    from io import BytesIO
    
    # Validate stamp type
    if payload.stamp_type not in VERIFICATION_STAMP_TYPES:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid stamp type. Valid options: {list(VERIFICATION_STAMP_TYPES.keys())}"
        )
    
    doc = await db.employee_documents.find_one({"id": doc_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # HARDENING: For Identity/PoA, require review checklist before stamping
    requirement_id = doc.get("requirement_id", "").lower()
    is_identity_poa = any(x in requirement_id for x in ["identity", "proof_of_address"])
    if is_identity_poa and not doc.get("file_viewed"):
        raise HTTPException(
            status_code=400,
            detail="Must complete review checklist before stamping. Call /start-review endpoint first."
        )
    
    # Get employee info for stamp
```

---

## Database Fields Added

New fields written to `employee_documents` collection:

```
file_viewed: boolean                    # Admin has opened the file
file_viewed_at: ISO timestamp          # When file was marked as viewed
file_viewed_by: string (user_id)       # Who marked it viewed
file_viewed_by_name: string            # Name of reviewer
review_checklist: object {
  file_viewed: boolean,
  name_matches: boolean,
  document_acceptable: boolean,
  legible: boolean,
  front_present: boolean (Identity),
  back_present: boolean (Identity),
  address_valid: boolean (PoA),
  date_valid: boolean (PoA)
}
last_reviewed_at: ISO timestamp        # Last review action time
last_reviewed_by: string (user_id)     # Who last reviewed
last_reviewed_by_name: string          # Name
```

---

## API Flows

### Admin Reviews Identity/PoA Document

1. **Open/View File:** Admin opens document in admin UI (existing action, records nothing)

2. **Start Review:** Admin submits review checklist
   ```
   POST /employee-documents/{doc_id}/start-review
   {
     "file_viewed": true,
     "name_matches": true,
     "document_acceptable": true,
     "legible": true,
     "front_present": true,      // Identity only
     "address_valid": true       // PoA only
   }
   ```
   
   → Stores: `file_viewed=true`, `file_viewed_at`, `file_viewed_by`, `review_checklist`  
   → Enables verify action in admin UI

3. **Verify or Stamp:** Admin clicks Verify or Verify & Stamp
   ```
   POST /employee-documents/{doc_id}/verify
   or
   POST /employee-documents/{doc_id}/verify-with-digital-stamp
   ```
   
   → Endpoint checks: `if file_viewed != true: error`  
   → Proceeds with verification as normal

---

## Worker State Impact

No changes. Worker dashboard already:
- Filters by `_is_live_document(doc)` which checks `status` and `review_status`
- Won't show rejected/amendment_requested docs
- Shows correct Identity/PoA state based on approved documents

---

## Audit Trail

Each review action logged:

**Action:** `start_document_review`
```json
{
  "user_id": "admin_id",
  "action": "start_document_review",
  "resource_type": "employee_document",
  "resource_id": "doc_id",
  "metadata": {
    "checklist": {...},
    "requirement_id": "identity",
    "employee_id": "emp_id"
  }
}
```

---

## Existing Actions (Unchanged)

These continue to work exactly as before:

- **View** - Opens file (no change)
- **Verify** - Now **requires** file_viewed + checklist (changed)
- **Verify & Stamp** - Now **requires** file_viewed + checklist (changed)
- **Amend/Amendment Request** - Unchanged
- **Uploaded in Error** - Unchanged  
- **Reject** - Unchanged (already requires reason)

---

## Deployment Checklist

- [x] No new router or file required
- [x] No breaking changes to existing endpoints
- [x] Guards only prevent action without proper checklist
- [x] RTW/DBS completely untouched
- [x] Worker dashboard compatible (no changes needed)
- [x] Audit trail captures all decisions
- [x] Clean error messages guide admin action

---

## Lines Changed

Total: **~120 lines** added to backend/server.py

- Model definition: ~10 lines
- New endpoint: ~70 lines
- Guard in verify: ~7 lines
- Guard in verify-with-stamp: ~7 lines
- Endpoint docstring updates: ~2 lines

**Files modified:** 3 (backend/server.py, frontend/src/components/compliance/QuickVerifyStampDialog.js, IDENTITY_POA_MINIMAL_PATCH.md)  
**Frontend integration:** Existing verification dialog now enforces checklist step before verification actions.

