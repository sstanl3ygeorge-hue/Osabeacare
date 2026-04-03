# CareTrust Compliance Portal - PRD

## Original Problem Statement
Build a Requirement-Based Compliance Engine for a Care Recruitment Agency ensuring CQC audit-readiness. Implement a digital application intake flow, strict Applicant vs Employee separation, a single authoritative 3-tier work readiness logic layer, an NHS-level strict Reference/Referee Integrity workflow, CV extraction, and a Supplementary Training module.

## Core Requirements
- 3-tier work readiness: NOT_READY, READY_WITH_CONDITIONS, READY_TO_WORK
- Dual-Row Evidence/Check Model: Clear separation between uploaded evidence and actual employer check/verification outcome
- System Consolidation: Single source of truth per requirement. Consistent UI across all compliance items

## Tech Stack
- Frontend: React + Tailwind + Shadcn/UI
- Backend: FastAPI (Python)
- Database: MongoDB (with Supabase migration in progress)
- Email: Resend
- AI: OpenAI GPT-5.2 Vision for CV/Document extraction
- Auth: JWT-based custom auth

## What's Been Implemented

### Phase 1: Core Architecture (COMPLETED)
- [x] Employee management CRUD
- [x] 3-tier work readiness engine
- [x] Compliance requirements tracking
- [x] Document upload and storage

### Phase 2: Dual-Row Compliance UI (COMPLETED - Apr 2)
- [x] UploadRequirementCard.js rewritten for dual-row model
- [x] DualRowComplianceSection.js created
- [x] Evidence row (employee uploads) vs Verification row (employer checks)
- [x] Right to Work, DBS, Identity, PoA sections with dual-row

### Phase 3: Recruitment Record (COMPLETED - Apr 2)
- [x] Interview Record tracking
- [x] Application Form with hybrid model
- [x] CV/Resume with evidence verification
- [x] Recruitment Compliance Checklist

### Phase 4: Email Automation (COMPLETED - Apr 2)
- [x] Document request email flow
- [x] CORE_REQUIREMENT_NAMES mapping for readable placeholders
- [x] Email template with proper branding
- [x] Click tracking API
- [x] URL parameter handling for direct upload links

### Phase 5: Training Matrix (COMPLETED - Apr 2)
- [x] AuditReadyTrainingMatrix.js with 3 tabs
- [x] Mandatory training requirements
- [x] Additional qualifications (non-mandatory)
- [x] Certificates tracking
- [x] 40+ synonym normalization in backend

### Phase 6: Drawer UI Improvements (COMPLETED - Apr 2)
- [x] ComplianceDrawer.js - Production-ready wrapper
- [x] EvidenceManageDrawer.js - Evidence-only management
- [x] Proper backdrop (semi-transparent, blur)
- [x] Solid white panel with shadow
- [x] ESC/backdrop close support
- [x] Evidence vs Verification complete separation
- [x] Consistent across RTW, DBS, Identity, PoA

## Key Files
- `/app/frontend/src/components/compliance/ComplianceDrawer.js` (NEW)
- `/app/frontend/src/components/compliance/EvidenceManageDrawer.js` (NEW)
- `/app/frontend/src/components/compliance/EvidenceReviewDialog.js` (NEW - Apr 3) - Accept/Reject/Mark in Error for evidence files
- `/app/frontend/src/components/compliance/ApplicationFormViewDrawer.js` (NEW - Apr 3) - Read-only viewer for structured application forms
- `/app/frontend/src/components/compliance/UploadRequirementCard.js`
- `/app/frontend/src/components/compliance/DualRowComplianceSection.js`
- `/app/frontend/src/components/training/AuditReadyTrainingMatrix.js`
- `/app/frontend/src/pages/portal/EmployeeProfilePage.js`
- `/app/backend/server.py`
- `/app/backend/email_automation.py`
- `/app/backend/email_service.py`

## Known Issues
- F811 duplicate function definitions in server.py (technical debt)
- server.py >38k lines - needs modular split

## Recent Fixes (Apr 2-3, 2026)
- [x] Fixed DuplicateKeyError on public application submission - MongoDB unique index on `employee_code` was rejecting multiple `null` values. Now generating unique `APPLICANT-{uuid}` codes for applicants.
- [x] Added clickable blockers in Recruitment Checks - Each blocker item now scrolls to the relevant compliance section with highlight effect
- [x] Added "Next Steps" panel - Shows up to 4 actionable items above Recruitment Approval for quick admin navigation
- [x] Implemented public document upload flow - Email links now use `/upload-document?token=...` route (no login required)
- [x] Fixed email resend flow - `force_resend` param supersedes old requests, returns clear statuses (sent/resent/duplicate_blocked/error)
- [x] Fixed compliance card layout - Removed duplicate actions from header, Evidence row has Upload/Request/Manage, Verification row has Upload Proof/Record Check/View Details
- [x] **Fixed Application Form viewer** - Created `ApplicationFormViewDrawer.js` to render structured application JSON data without requiring a template. The drawer shows all sections: Personal Details, Employment History, References, Declarations, Health Declaration, Criminal Declaration, Right to Work. **Root cause was GET /api/form-submissions/{id} returning 500 due to Pydantic validation error** - removed strict response_model and normalized data/form_data fields.
- [x] **Added Application Form PDF export** - `generate_application_form_pdf()` in server.py creates professional PDF from application form data. Export PDF button now works in ApplicationFormViewDrawer. Fixed `generate_form_pdf` to also read `requirement_id` as fallback for `form_type`.
- [x] **Restored db.references insertion logic** - References submitted via public application now appear in Recruitment Record. Created reference_1_* and reference_2_* fields in employee document + db.references record. Compliance-file endpoint returns status='declared' for new applicants.
- [x] **Changed "Upload Proof" to "Record Check"** - Removed standalone "Upload Proof" button from verification row. Proof upload is now part of the RecordCheckDialog workflow which opens when clicking "Record Check".
- [x] **Implemented System Role Normalization** - Added `system_role` field (HCA/NURSE) for compliance logic. All compliance, training, and readiness logic now uses `system_role` instead of raw string matching. Migration completed for 21 existing employees. Admin endpoints: GET/POST /admin/system-role/status, /migrate, /set-manual.
- [x] **Evidence Review Workflow (Apr 3)** - Created `EvidenceReviewDialog.js` for Accept/Reject/Mark Uploaded in Error actions on evidence files. Added backend endpoints: POST `/api/employee-documents/{doc_id}/reject`, POST `/api/employee-documents/{doc_id}/mark-uploaded-in-error`. Review button visible on pending evidence files in UploadRequirementCard. "Accept & Record Check" button available for document-heavy requirements (RTW, DBS, Identity, PoA).
- [x] **Reference Verification Workflow (Apr 3)** - Added employment history mismatch detection (reference vs application, reference vs normalized, response vs declared dates/employer). Added alternative reference path recording with attempt tracking. New endpoint: POST `/api/references/{employee_id}/{ref_num}/record-alternative-path`. UI shows employment mismatch warnings and alternative path section in ReferenceResponseDrawer.
- [x] **Image Viewer Rotation Controls (Apr 3)** - Added Rotate Left/Right buttons to DocumentPreviewModal for images (JPEG/PNG). Client-side only rotation.
- [x] **ID/Document Verification Stamps (Apr 3)** - New endpoint POST `/api/employee-documents/{doc_id}/verification-stamp`. Four stamp types: Original Seen, Copy Verified, Online Check, Not Verified. Stamp badge displays on evidence files with audit text. VerificationStampDialog created. Stamps appear on ACCEPTED files only.
- [x] **Employment Gap Explanation Enforcement (Apr 3)** - 30-day threshold. Gaps over 30 days flagged for explanation. Full workflow: pending → explained → verified/rejected/needs_more_info. Unexplained/unverified gaps block recruitment approval. EmploymentGapPanel displays in Compliance File with status badges and action buttons.
- [x] **Evidence Workflow State Model Fix (Apr 3)** - Fixed critical bug where accepted/verified files disappeared from main card. Root cause: Frontend only included 'active'/'uploaded' as active statuses, missing 'approved'. Now standardized: ACTIVE_STATUSES = ['active', 'uploaded', 'approved', 'pending_review', 'under_review', 'verified'], EXCLUDED_STATUSES = ['rejected', 'uploaded_in_error', 'superseded', 'misfiled']. Main card and Manage drawer now consistent.
- [x] **Right to Work Compliance Strengthening (Apr 3)** - Share Code as primary method with GOV.UK guidance. BRP warnings about expiry. Dynamic guidance in RecordCheckDialog. Proof upload enforced for online check methods. Public upload page shows Share Code guidance.
- [x] **Right to Work System Overhaul (Apr 3)** - Complete 3-layer data model (Evidence → Verification → Result). New fields: permission_start_date, permission_end_date, reference_number, share_code, restrictions, hours_limit, is_indefinite, follow_up_required, route, document_type. AI auto-extraction endpoint using GPT-5.2 Vision (`/api/rtw/extract`). RTW Result Panel in RecordCheckDialog. Lifecycle state labels on UploadRequirementCard.
- [x] **RTW Workflow Tightening (Apr 3)** - Auto-extract RTW fields when proof file uploaded. Human-friendly method labels (METHOD_LABELS mapping). Resolve checked_by to user name. Enhanced stamp badge with stamper name/date. Edit Stamp button when stamp exists. Fixed stamp document ID lookup.
- [x] **RTW Stamp State Fix (Apr 3)** - Fixed stamp fields not passing through DualRowComplianceSection.transformToUploadSurface. Added Remove Stamp endpoint (DELETE `/api/employee-documents/{doc_id}/verification-stamp`). Evidence summary now says "accepted" instead of "verified". RecordCheckDialog warns if no accepted/stamped evidence before recording check.

## Prioritized Backlog

### P0 (Critical)
- [x] Fix DuplicateKeyError on application submit (DONE - requires production verification)
- [x] **Fix Application Form viewer "Form template not found" error** (DONE - ApplicationFormViewDrawer.js created)
- [x] **Restore db.references insertion logic** (DONE - references now appear in Recruitment Record)
- [x] **Fix fake "Request sent" state on new applicants** (VERIFIED WORKING - frontend correctly shows "not yet requested")
- [x] **Evidence Review Workflow** (DONE Apr 3) - EvidenceReviewDialog allows Accept/Reject/Mark Uploaded in Error actions on evidence files
- [x] **Reference Verification Workflow** (DONE Apr 3) - Employment mismatch detection, alternative reference path recording
- [x] **ID/Document Verification Stamps** (DONE Apr 3) - Original seen, Copy verified, Online check, Not verified stamps
- [x] **Employment Gap Explanation Enforcement** (DONE Apr 3) - 30-day threshold, blocks recruitment approval
- [x] **Right to Work System Overhaul** (DONE Apr 3) - 3-layer data model with AI extraction

### P1 (High)
- [ ] Interview Notes integration
- [ ] Training Matrix PDF export
- [ ] Employee self-service portal
- [ ] Supabase Auth integration and RLS policies

### P2 (Medium)
- [ ] Bulk recurring item creation
- [ ] Split server.py into modular routers
- [ ] Fix F811 linting errors

### P3 (Low/Future)
- [ ] Phase out MongoDB entirely
- [ ] Production deployment optimizations

## Dual-Row Model Specification

### Evidence Row (Candidate/Applicant Files)
- Upload evidence
- View files
- Manage files (via EvidenceManageDrawer)
- Request evidence
- Resend request
- Delete/supersede evidence
- View request history

### Verification Row (Admin/Employer Checks)
- Record check
- Upload proof of check
- Update check
- View proof file
- View verification history

### Managed by EvidenceManageDrawer (NOT verification):
- Active Files section
- Request History section
- Historical Files section
- File actions (verify, reject, supersede, move category)

### Verification stays in main card:
- Method, outcome, checked_by, checked_at
- Proof of check file card
- Upload Proof button
- Record Check / Update Check button

## Test Credentials
- Admin: admin@osabea.care / admin123
- Test Employee: d88335f6-1b18-435a-8086-28af4a583f77

## API Endpoints
- `POST /api/employees/{id}/request-document?requirement_id={id}` - Send document request email
- `POST /api/email-requests/{id}/track-click` - Track email CTA clicks
- `GET /api/employees/{id}/training-matrix` - Get training items and additional items
- `GET /api/employees/{id}/compliance-requirements` - Get all compliance requirements
- `GET /api/employees/{id}/requirements/{key}/files` - Get files for drawer
- `POST /api/employees/{id}/right-to-work/check` - Record RTW check with 3-layer result data
- `GET /api/employees/{id}/right-to-work/check` - Get current RTW check with all fields
- `POST /api/rtw/extract` - AI extraction of RTW document fields using GPT-5.2 Vision

## Last Updated
April 3, 2026 - RTW Stamp State Fix (stamp field passthrough, Remove Stamp, accepted wording, evidence warnings)
