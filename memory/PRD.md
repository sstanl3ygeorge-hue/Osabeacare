# Care Recruitment Agency Compliance Portal - PRD

## Company
**Osabea Healthcare Solutions**

## Original Problem Statement
Build a comprehensive compliance management portal for a UK care recruitment agency to:
- Manage employee onboarding and compliance documents
- Track training and policy acknowledgements
- Generate and manage compliance forms with digital signatures
- Support CQC audit requirements
- Organisation-level compliance tracking (Compliance Centre)

## User Personas
1. **Super Admin**: Full system access, manages all employees and compliance
2. **Manager**: Manages team compliance, reviews documents
3. **Auditor**: Read-only access for compliance audits
4. **Employee**: Completes assigned forms (future portal)

## Core Requirements

### Completed Features ✅

#### Phase 1: Foundation (Completed 2026-03-27)
- [x] React + FastAPI + MongoDB full-stack architecture
- [x] JWT + Google OAuth authentication via Emergent Auth
- [x] Employee records management (CRUD)
- [x] Object storage integration for documents
- [x] Document types and compliance tracking
- [x] Policy management with version control
- [x] Training records tracking
- [x] Audit logging for all actions
- [x] Public website with services, about, careers pages
- [x] Responsive design with Shadcn/UI components

#### Phase 1.5: Employee Record Management Controls (Completed 2026-03-27)
- [x] **Edit Employee Details** - Full dialog with:
  - Full name, email, phone
  - Role selector (9 roles)
  - Status selector (new, screening, interview, compliance_review, onboarding, active, inactive)
  - Onboarding Status selector
  - Start date
  - Internal notes
- [x] **Actions Menu** on employees list and profile:
  - Edit Details
  - Refresh Status (auto-update onboarding status)
  - Export Employee File (ZIP)
  - Export Compliance Summary
  - Archive Employee
  - Delete Permanently (Super Admin only)
- [x] **Archive Employee (Soft Delete)**:
  - Hides from active employees list
  - Retains all documents, forms, policies, audit history
  - "Archived" filter in status dropdown
  - Restore functionality available
  - Action logged in audit trail
- [x] **Permanent Delete (Super Admin Only)**:
  - Confirmation modal with warning
  - Deletes employee + all related records
  - For duplicate/test/incorrect entries only
  - Action logged in audit trail

#### Phase 4: Smart Compliance System (Completed 2026-03-27)
- [x] **Role-Based Mandatory Items Checklist**:
  - Healthcare Assistant: 18 mandatory items
  - Nurse: 21 mandatory items (HCA items + NMC, Clinical Competency, Medication)
  - Categories: Application, Recruitment, Personal Info, Interview, Equal Opportunities, Health Screening, Identity/RTW, References, DBS, Induction, Contract, Training, Other
- [x] **Auto-Derive Onboarding Status**:
  - New: No meaningful activity
  - Documents Pending: Required items still missing
  - Under Review: Items present but not all verified
  - Ready for Placement: All mandatory items complete and verified
  - Active: Compliant and working
  - Archived: Inactive with records retained
- [x] **Refresh Status Button**: Triggers auto-calculation and updates status
- [x] **Super Admin Override**: Manual status override with audit log
- [x] **Export Employee File (ZIP)**:
  - Organized folder structure (A-O categories)
  - Includes: forms, documents, training records
  - Employee summary JSON
- [x] **Export Compliance Summary**:
  - Employee details
  - Compliance percentage
  - Mandatory items checklist with status
  - Missing items list
  - Training summary
  - Verified documents
- [x] **Audit Readiness Dashboard** (`/api/dashboard/audit-readiness`):
  - Staff compliance breakdown (Ready, Under Review, Documents Pending, New, Active)
  - Critical alerts (missing items, expiring DBS, expiring training)
  - Organisation compliance (policies, insurance)
  - Audit readiness score with status indicator

#### Phase 2: Template Library & Document Control (Completed 2026-03-27)
- [x] **13 Compliance Templates** (role-aware for HCA vs Nurse):
  - Application Form
  - Interview Record Form
  - Recruitment Compliance Checklist
  - Health Screening Questionnaire (restricted)
  - Induction & Competency Assessment
  - Contract Acknowledgement Form
  - Personal Information Form
  - Equal Opportunities Monitoring Form (confidential)
  - Supervision Record
  - Annual Appraisal Form
  - Reference Request & Verification Form
  - DBS Review & Risk Assessment
  - **Employee Handbook Acknowledgement** (NEW)
- [x] **Form Generation System** with auto-fill, role-based fields, status workflow
- [x] **Digital Signatures** (typed + canvas drawn)
- [x] **Bulk Operations** (bulk upload, bulk form generation)
- [x] **PDF Export** for forms
- [x] **Visibility Controls** (normal/restricted/confidential)
- [x] **Email Templates** for common communications:
  - Document Request
  - Right to Work Request
  - Form Completion Request
  - Onboarding Complete
  - Missing Items Follow-up
  - Expiry Reminder
  - Form Signed Off

#### Phase 2.5: Training & Compliance Overview (Completed 2026-03-27)
- [x] **Compliance Overview Component** on employee profiles
- [x] **9 Key Compliance Items Tracked**:
  - Safeguarding Training
  - Manual Handling
  - Infection Control
  - Basic Life Support (BLS)
  - Medication Training (Nurse-only)
  - DBS Check
  - Right to Work
  - Induction Completed
  - Policies Acknowledgement
- [x] **Status Indicators**: Complete (green), Expiring (amber), Pending (blue), Missing (red), N/A (gray)
- [x] **Expiry Date Display** when applicable
- [x] **Last Updated Date Display**
- [x] **Role-Based Logic**: Medication Training shows N/A for Healthcare Assistants
- [x] **Overall Compliance Progress Bar** with color-coded segments

#### Phase 3: Compliance Centre - Organisation Level (Completed 2026-03-27)
- [x] **32 Organisation Policies** categorised into 4 groups:
  - **Core** (8): Safeguarding Adults, Safeguarding Children, Mental Capacity Act & DoLS, Health & Safety, Fire Safety, First Aid, Equality Diversity & Inclusion, Whistleblowing
  - **Clinical** (8): Medication, Infection Prevention & Control, Manual Handling, COSHH, Care Planning, End of Life Care, Nutrition & Hydration, Pressure Ulcer Prevention
  - **Operational** (8): Lone Working, Risk Assessment, Record Keeping, Confidentiality, Complaints, Incident Reporting, Business Continuity, Service User Feedback
  - **Governance** (8): Recruitment & Selection, DBS & Vetting, Induction & Probation, Training & Development, Supervision & Appraisal, Disciplinary & Grievance, Data Protection & GDPR, Code of Conduct
- [x] **6 Insurance & Certificates**:
  - Public Liability Insurance
  - Employer's Liability Insurance
  - Professional Indemnity Insurance
  - CQC Registration Certificate
  - ICO Registration Certificate
  - Company Registration Certificate
- [x] **Auto-seeding on startup** - All policies and insurance seeded as "Missing" placeholders
- [x] **Policy Upload & Versioning** - Admin can upload/replace documents with version numbers and review dates
- [x] **Status Tracking**: Missing (red), Active (green), Expiring (amber)
- [x] **View/Replace functionality** for existing documents
- [x] **Dashboard Summary Cards** - Policy count, Insurance status, Open incidents, Active staff
- [x] **Incident & Outbreak Logs** - Create/track incidents with reference numbers (INC-YYYY-NNNN)
- [x] **Reports Tab** - Staff DBS Dates, Training Report (12 months)

### Upcoming Features (P0)
- [x] **PDF Compliance Summary Export** (Completed 2026-03-27):
  - Download Compliance PDF button in Actions dropdown
  - Print Compliance PDF button (opens in new tab)
  - Professional A4 PDF with employee info, compliance score, checklist, training summary
  - Uses reportlab for server-side PDF generation
- [x] **Navigation State Preservation** (Completed 2026-03-27):
  - URL-based state persistence for filters/tabs using useSearchParams
  - Back button uses navigate(-1) for browser history
  - Employees page preserves search, status, and onboarding filters
  - Employee profile preserves active tab
  - Compliance Centre preserves active tab
  - Templates page preserves search and category filter
- [x] **Policy View Fix** (Completed 2026-03-27):
  - Replaced direct storage URLs with authenticated backend file-serving
  - View button fetches PDF via axios with auth token, opens in new tab
  - Download button downloads with proper Content-Disposition header
  - Works for both policies and insurance/certificates
- [x] **Document Preview Modal** (Completed 2026-03-27):
  - Google Drive/Dropbox style in-app document preview
  - PDF viewer with react-pdf: zoom controls (slider + buttons), page navigation, rotate
  - Image preview with zoom
  - Fullscreen mode toggle
  - Download and Open in New Tab buttons
  - Loading and error states
  - White background, rounded corners, responsive (large on desktop, fullscreen on mobile)
  - Integrated in Compliance Centre (policies, insurance) and Employee Profile (documents)
- [x] **Import Application Form Workflow** (Completed 2026-03-27):
  - "Generate Forms" dropdown with two options: "Generate Blank Forms" and "Create from Existing Application"
  - Import dialog allows uploading completed application form and optional CV
  - Imported forms marked as "Completed (Imported)" with locked fields
  - Application document stored in A_Application folder with "approved" status
  - CV stored in C_Personal Information folder
  - Avoids duplicate data entry for real-world onboarding
- [x] **Document Verification System** (Completed 2026-03-27):
  - Documents have verification status: Pending/Completed/Verified
  - "Mark as Verified" button for approved documents
  - Verification records: verified_by, verified_at, verified_by_name
  - Green "Verified" badge displays in Documents tab
  - Unverify option to remove verification
- [x] **Save Form as Document** (Completed 2026-03-27):
  - "Save as Doc" button appears for completed/imported forms
  - Auto-generates PDF from form data using reportlab
  - Saves to correct employee folder based on form type (A_Application, H_References, etc.)
  - Structured filename: EmployeeName_FormType_Date.pdf
  - Creates employee document record linked to source form
- [x] **1:1 Document-to-Requirement Mapping** (Completed 2026-03-27):
  - One requirement = one document slot (no duplicates)
  - Documents tab shows one row per requirement (not per uploaded file)
  - Upload button for missing requirements, Replace button for existing documents
  - Re-uploading increments version number instead of creating duplicate
  - Added CV / Resume as mandatory requirement
  - Split References into Reference 1 and Reference 2 (separate slots)
  - Requirement-based upload modal with deduplication logic
  - Checklist tab reflects actual uploaded/verified state
  - Compliance score updates correctly based on requirement completion
  - Verification status shows user name (not user ID)
- [x] **Multi-File Document Support** (Completed 2026-03-27):
  - API changed from `req.document` (single) to `req.documents[]` (array)
  - `allow_multiple_files` flag on requirements (Identity/RTW, NMC, Clinical Competency)
  - `min_files` field for minimum evidence required
  - Single-file requirements: "Replace" button, deduplicates to show latest
  - Multi-file requirements: "Add File" button, "Verify All", individual delete icons
  - Upload modal shows "Multi" badge and optional "Document Label" field
  - Checklist shows file count badges (e.g., "3 files")
  - Compliance score based on requirement completion, not file count
  - Delete endpoint blocks deletion for single-file requirements
- [x] **Import Document for All Form Types** (Completed 2026-03-27):
  - New "Import Other Document" option in Generate Forms dropdown
  - Supports: Reference 1, Reference 2, Health Screening, Contract, Induction, Handbook
  - Creates form with status "completed_imported" and links document to requirement
  - Documents stored in correct compliance folder with requirement_id
  - Checklist automatically updates to show requirement as complete
  - Optional notes field for import context
- [x] **CRITICAL: Compliance System Audit & Fix** (Completed 2026-03-27):
  - Fixed: Compliance score now based on REQUIREMENT completion (not document count)
  - Fixed: Forms now have requirement_id linking them to requirements
  - Fixed: Documents now have requirement_id linking them to requirements
  - Fixed: Import endpoint updates existing forms instead of creating duplicates
  - Added: /api/admin/cleanup-duplicates endpoint to remove duplicate forms
  - Cleaned up: 9 duplicate forms removed for employee Olakunle Alonge
  - Result: Employee shows 10/20 requirements complete (55%), 4 verified
  - System now operates as a proper NHS/CQC-ready compliance engine
- [x] **Unified Training Completion Flow** (Completed 2026-03-27):
  - NEW: "Mark Complete" button on training requirements in Checklist tab
  - NEW: "Complete" button in Training & Compliance Overview for missing training
  - NEW: Training completion dialog with optional expiry date
  - NEW: POST /api/employees/{id}/complete-training endpoint
  - NEW: GET /api/employees/{id}/training-requirements endpoint
  - Feature: Prevents duplicates - updates existing records or creates new
  - Feature: Compliance score updates immediately after completion
  - Feature: Works from both Overview and Checklist tabs
  - Fixed: ComplianceOverview matching logic for training record names
  - Result: Single unified flow: Employee → Requirement → Complete → Compliance updates
  - Employee OCS-0001 now at 17/20 (85%) with all 6 training complete
- [x] **Training Evidence & Verification System** (Completed 2026-03-27):
  - CRITICAL: Training now requires evidence for audit compliance
  - NEW: POST /api/employees/{id}/training/{requirement_id}/upload-certificate endpoint
  - NEW: POST /api/training-records/{id}/verify endpoint (REQUIRES certificate)
  - NEW: POST /api/training-records/{id}/unverify endpoint
  - NEW: GET /api/training-records/{id}/certificate/file endpoint (view)
  - NEW: GET /api/training-records/{id}/certificate/download endpoint
  - Feature: Training records now store certificate_url, original_filename, uploaded_at
  - Feature: Training records now store verified, verified_by, verified_at, completion_method
  - Feature: Verification blocked until certificate is uploaded
  - Frontend: "Upload Certificate" button on training without certificates
  - Frontend: "View", "Download", "Verify", "Replace" buttons when certificate exists
  - Frontend: Warning message "No certificate uploaded" for training without evidence
  - Result: Training now follows same pattern as documents: Requirement → Evidence → Verified
- [x] **Evidence-Based Compliance Redesign** (Completed 2026-03-27):
  - MAJOR: Complete redesign to match real healthcare compliance workflows
  - NEW: DBS split into `dbs_certificate` (employee) + `dbs_check` (internal)
  - NEW: RTW split into `identity_documents` + `right_to_work_documents` + `right_to_work_check`
  - NEW: Total requirements increased from 20 to 23 for comprehensive tracking
  - NEW: Unified evidence upload endpoint: POST /api/employees/{id}/requirements/{req_id}/evidence
  - NEW: Evidence view/download endpoints for any requirement
  - NEW: Unified verify/unverify endpoints for any requirement
  - NEW: `evidence_files[]` array replaces single file_url for multi-file support
  - NEW: Source badges (Employee/Internal/Form) on requirement rows
  - Feature: Compliance score now EVIDENCE-BASED ONLY (manual completions don't count)
  - Feature: "completed_no_evidence" status for items without viewable files
  - Feature: Verification blocked unless evidence exists
  - Feature: Can_verify flag indicates when verification is allowed
  - Frontend: Evidence count badge on requirement rows
  - Frontend: Add, View, Download, Verify, Unverify buttons per requirement
  - Frontend: Warning message for items completed without evidence
  - Result: Audit-ready single source of truth for all compliance evidence
  - Pilot: OCS-0001 successfully tested with DBS Certificate + DBS Check separate
- [x] **Audit Validation & Enforcement Pass** (Completed 2026-03-27):
  - VALIDATED: All 23 requirements support evidence upload
  - VALIDATED: All evidence files viewable (HTTP 200)
  - VALIDATED: All evidence files downloadable (HTTP 200)
  - VALIDATED: Verification blocked without evidence
  - FIXED: Legacy requirement ID mapping (dbs→dbs_certificate, identity_rtw→split)
  - FIXED: Upload modal now shows ALL requirements grouped by type
  - FIXED: Unified evidence endpoint handles all requirement types
  - RESULT: OCS-0001 at 100% completion (23/23 with evidence), 5 verified
  - AUDIT STATUS: Evidence-based, traceable, audit-ready
- [x] **Forms → Automatic PDF Evidence** (Completed 2026-03-27):
  - NEW: Forms auto-generate PDF when marked complete
  - NEW: PDF stored as evidence document with proper requirement_id
  - NEW: `POST /generated-forms/{id}/regenerate-pdf` endpoint to force regeneration
  - Feature: Checklist only shows forms as complete if PDF exists
  - Feature: "Generate PDF" button for completed forms without PDF
  - Feature: Clear warning message "No PDF document generated"
  - RESULT: All 8 forms for OCS-0001 now have PDF evidence
  - AUDIT STATUS: Forms = internal workflow, PDFs = audit evidence

### Backlog (P1-P2)
- [ ] Email notifications via Resend for form requests
- [ ] Bulk document requests
- [ ] Bulk policy assignment
- [ ] Employee self-service portal
- [ ] Mobile app consideration

## Technical Architecture

```
/app/
├── backend/
│   ├── server.py          # FastAPI application
│   ├── templates_data.py  # 13 template definitions
│   ├── requirements.txt   # Python dependencies
│   └── .env              # Environment variables
├── frontend/
│   ├── src/
│   │   ├── App.js        # React Router setup
│   │   ├── context/      # AuthContext
│   │   ├── components/
│   │   │   ├── portal/   # SignaturePad, FormFieldRenderer, PortalLayout
│   │   │   └── ui/       # Shadcn components
│   │   └── pages/
│   │       ├── portal/   # Dashboard, Employees, Templates, FormEditor, ComplianceCentre
│   │       └── public/   # Website pages
│   └── package.json
└── memory/
    └── PRD.md
```

## Key API Endpoints

### Templates
- `GET /api/templates` - List all templates
- `POST /api/seed-templates` - Seed 13 compliance templates
- `GET /api/templates/:id` - Get template details with form fields

### Generated Forms
- `POST /api/generated-forms` - Create form for employee
- `GET /api/generated-forms` - List forms (filter by employee_id)
- `PUT /api/generated-forms/:id` - Update form data/status
- `POST /api/generated-forms/bulk` - Bulk generate forms
- `POST /api/generated-forms/:id/signoff` - Admin sign-off (locks form)
- `POST /api/generated-forms/:id/send` - Send to employee

### Documents
- `POST /api/employees/:id/bulk-upload` - Bulk document upload
- `POST /api/employee-documents/:id/upload` - Single document upload

### Compliance Centre
- `GET /api/compliance/policies` - List all 30 organisation policies
- `POST /api/compliance/policies/:id/upload` - Upload policy document
- `GET /api/compliance/insurance` - List all 6 insurance/certificates
- `POST /api/compliance/insurance/:id/upload` - Upload insurance document
- `GET /api/compliance/incidents` - List incident logs
- `POST /api/compliance/incidents` - Create incident report
- `GET /api/compliance/dashboard` - Dashboard summary statistics

## Database Collections

### employees
```javascript
{
  id, employee_code, first_name, last_name, email, phone,
  role: "Healthcare Assistant" | "Nurse" | "Care Assistant" | ...,
  assignment: "Unassigned" | "Sunrise Care Home" | "...",  // Current placement
  status: "new" | "screening" | "interview" | "onboarding" | "active" | "inactive",
  completion_percentage, created_at, updated_at
}
```

### templates
```javascript
{
  id, name, description, category, section,
  visibility: "normal" | "restricted" | "confidential",
  role_specific: null | "Nurse" | "Healthcare Assistant",
  form_fields: [...],
  requires_employee_signature, requires_admin_signature,
  active, version, created_at, updated_at
}
```

### generated_forms
```javascript
{
  id, template_id, template_name, template_category,
  employee_id, employee_name, employee_code,
  form_data: {...},
  status: "draft" | "sent" | "in_progress" | "completed" | "reviewed" | "signed_off" | "archived",
  employee_signature, employee_signed_at,
  admin_signature, admin_signed_at, admin_signoff_by,
  locked: boolean,
  version, access_token,
  created_at, updated_at, sent_at, viewed_at, completed_at, signed_off_at
}
```

### org_policies
```javascript
{
  id, name, category, version, status,
  file_url, original_filename, review_date,
  last_reviewed_at, reviewed_by, notes,
  created_at, updated_at, created_by
}
```

### insurance_docs
```javascript
{
  id, name, insurance_type, status,
  file_url, original_filename, expiry_date,
  policy_number, provider, notes,
  created_at, updated_at
}
```

### incident_logs
```javascript
{
  id, incident_type, reference_number, title, description,
  date_occurred, location, persons_involved,
  immediate_actions, root_cause, corrective_actions, lessons_learned,
  status, reported_by, reported_at, closed_at, closed_by, attachments
}
```

## Credentials

### Demo Admin
- Email: admin@osabea.care
- Password: admin123
- Role: super_admin

### Test Employees
- Sarah Thompson (OCS-0005) - Nurse - London
- Michael Brown (OCS-0006) - Healthcare Assistant - Manchester

## Last Updated
2026-03-28 - Audit-Ready Status Overhaul

### Audit-Ready Status Overhaul (Completed 2026-03-28)
- [x] **Removed "Complete" status entirely** - No "complete" label anywhere in UI
- [x] **Standardized to 4 statuses only**:
  - Verified (green) - Has evidence + admin verified
  - Evidence Uploaded (blue) - Has files but not verified
  - Missing (red) - No evidence
  - Expired (orange) - Evidence exists but past expiry date
- [x] **ComplianceOverview redesigned**:
  - Shows "Audit Summary" with 4 metric cards
  - Groups items by status: Verified, Needs Verification, Missing, Expired
  - Progress bar shows "X/Y verified" instead of "X/Y complete"
- [x] **Summary Card renamed** to "Audit Status":
  - Verified X/Y, Evidence Uploaded X, Missing X, Policies Signed X/Y
- [x] **Category headers** now show "X/Y verified" instead of "X/Y complete"
- [x] **Checklist header** shows: "X verified · Y awaiting verification · Z missing"

### Audit Mode Implementation (Completed 2026-03-28)
- [x] **Hidden Forms System from UI**:
  - Templates removed from sidebar navigation
  - Form Templates removed from Dashboard Quick Actions
  - Internal Forms (Admin) tab hidden from employee profile
  - Generate Forms button hidden from profile header
  - Backend retained for data integrity
- [x] **Employee Profile Simplification**:
  - Tabs: Overview, Checklist, Documents, Policies, Training, Audit Log
  - Clean workflow: Upload → View → Verify → Done
- [x] **Profile Photo Feature**:
  - Upload button on avatar hover (camera icon)
  - Remove photo option
  - Auto-display in employee list and dashboard
  - Non-compliance (doesn't affect checklist/scoring)
- [x] **Dashboard Audit View**:
  - Fully Verified metric
  - Missing Documents
  - Expiring (30 days)
  - DBS/RTW status

### Compliance Centre Datetime Bug Fix (Completed 2026-03-28)
- [x] **Root Cause Identified**: Datetime comparison errors (offset-naive vs offset-aware) causing API failures
- [x] **Fixed Endpoints**:
  - `/api/compliance/dashboard` - was returning 500, now returns correct policy/insurance counts
  - `/api/compliance/policies` - was failing on review date comparison
  - `/api/compliance/insurance` - was failing on expiry date comparison
- [x] **Date Format Handling**: Now properly handles:
  - `datetime` objects (with and without tzinfo)
  - ISO strings with `T` separator
  - Simple `YYYY-MM-DD` format
- [x] **Data Integrity Verified**:
  - 32 policies (3 active: Safeguarding Adults, Medication, Lone Working)
  - 6 insurance documents (1 valid: Public Liability Insurance)
  - All uploaded files remain viewable and downloadable
- [x] **Existing Safeguards Confirmed**:
  - Seed endpoints check by name before inserting (no data overwrite)
  - Initialize Compliance Items does NOT delete existing uploads

### Imported Form Document-First UX (Completed 2026-03-28)
- [x] **Document-First View for Imported Forms**:
  - Imported forms (status=completed_imported) no longer load form editor
  - Shows clean "Uploaded Evidence" view instead
  - Banner: "This document was uploaded as compliance evidence. The original file is available below."
  - Actions: View Document → Download → Verify
  - File info card with filename and upload date
  - Metadata: Employee, Employee ID, Category, Date
- [x] **Removed Error State**:
  - No more "Failed to load form" error for imported forms
  - Template loading is skipped entirely for imported documents
- [x] **Internal Forms Tab Update**:
  - Imported forms show inline View/Download buttons
  - Not clickable cards - actions visible immediately
  - Regular forms still show clickable cards → form editor
- [x] **Single Source of Truth**:
  - Forms = internal admin workflows
  - Documents (PDFs) = audit evidence
  - Everything auditor sees is viewable, downloadable, traceable

### UX & Clarity Pass (Completed 2026-03-27)
- [x] **Fixed FormEditorPage Crash** (P0):
  - Imported forms without templates now load gracefully
  - Shows "Imported Document" info box with evidence explanation
  - Form data displayed in read-only view
- [x] **Forms Tab Renamed** to "Internal Forms (Admin)":
  - Helper text: "Forms are internal workflows. Completed forms generate PDF evidence stored in the checklist."
  - Clear separation between internal forms and compliance evidence
- [x] **Standardized Status Language**:
  - ONLY 3 statuses used: Missing (red), Evidence Uploaded (blue), Verified (green)
  - Removed: "Complete", "In Progress", "Pending", "No Evidence", "Locked"
- [x] **Checklist UI Cleanup**:
  - Linear workflow: Upload → View → Download → Verify
  - Verify button only shown when evidence exists (enforces workflow)
  - Clean action order, no duplicate buttons
  - Source badges only shown for Internal items (not Employee/Form)
  - File count badges (e.g., "1 file", "3 files")
- [x] **Dashboard Trust Fix**:
  - Added "Fully Verified" metric (green) - shows audit-ready employees
  - Replaced "Applicants" with more meaningful metric
- [x] **Removed Clutter**:
  - Hidden "locked" status from user view
  - Simplified evidence file display (max 2 shown, "+N more" indicator)
  - Removed unnecessary status badges
