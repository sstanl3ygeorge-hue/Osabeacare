# Care Recruitment Agency Compliance Portal - PRD

## Company
**Osabea Healthcare Solutions**

## Latest Update (2025-12-28)
**Lightweight Acknowledgement Flow & Optional Items - COMPLETE**

### Acknowledgement System (Contract/Handbook)
Implemented lightweight acknowledgement flow for items that don't require file uploads:

**How it works:**
- "Confirm & Complete" button replaces "Upload Document" for acknowledgement-type requirements
- Clicking opens dialog with confirmation checkbox
- User must check: "I confirm I have received, read, and understood..."
- Submitting marks item as **completed AND verified** (auto-verify)
- No file upload required

**Data stored:**
- `acknowledged: true`
- `acknowledged_at: timestamp`
- `acknowledged_by: user_name`
- `requirement_acknowledgements` collection in MongoDB

**Items using acknowledgement flow:**
- Contract Acknowledgement
- Employee Handbook Acknowledgement

**Audit logging:**
- Action: `acknowledgement_completed`
- Includes: employee_name, requirement_name, acknowledged_by, timestamp

### Optional Items (Equal Opportunities)
Equal Opportunities Monitoring is now optional:
- Shows "Optional" badge in UI
- Shows "Does not affect compliance score" text
- Excluded from total requirement count
- Employee can still submit if they choose

**Technical details:**
- `optional: true` flag in MANDATORY_ITEMS
- `optional_count` tracked and subtracted from total in compliance calculation
- Still allows form submission but doesn't affect % progress

### Compliance Impact
- Before acknowledging: 69% (with Contract/Handbook missing)
- After acknowledging: 78% (+9% for completing Contract and Handbook)
- Equal Opportunities no longer blocks 100% completion

## Previous Update (2025-12-28)
**Audit Day UI Visibility Improvements - COMPLETE**

### Audit Quick View Section
Added a compact compliance summary at the top of Employee Profile with 5 status cards:
- **DBS**: Shows Missing/Expired/Pending Review/Verified with expiry date
- **Right to Work**: Shows Missing/Pending Review/Verified
- **Training**: Shows completed/verified count or expired count
- **Documents**: Shows missing/unverified count
- **Progress**: Shows completion percentage

Each card is color-coded: Red (critical), Amber (needs attention), Blue (pending), Green (verified/complete).

### High-Risk Item Badges
DBS and RTW items now have prominent colored badges in What's Needed tab:
- **DBS Badge**: White text on red/amber/green background based on status
- **RTW Badge**: White text on red/amber/green background based on status
- Badges appear next to requirement names for instant visibility

### Documents Tab Improvements
- File rows show expiry status with colored badges (Expired/Expiring Soon/Valid)
- DBS/RTW files tagged with category badges
- Expiry date shown prominently
- Verification status badge improved

### Helper Text/Microcopy Updates
- **What's Needed**: "Upload each required document, then verify it. Only verified documents count towards compliance."
- **Training Tab**: "Track completion status, expiry dates, and renewal status. Verified training counts toward work readiness."
- **Documents Tab**: "Upload and verify documents. Only verified documents count towards compliance."
- **Training Matrix**: "Track staff training, expiry dates, and renewals. Use filters to find risks quickly."

### Technical Notes
- Used existing backend data and calculation logic (no new endpoints)
- No duplicate state introduced
- Progress/count calculations unchanged
- Requirement IDs: `dbs_certificate`, `dbs_check`, `dbs_update_service`, `right_to_work_documents`, `right_to_work_check`

## Previous Update (2025-12-28)
**Unified Training System UI Sync - COMPLETE**

### What's Needed Tab Training Record Integration
Training requirements in What's Needed tab now use the same unified training record system as the Training tab:

**Training Record Info Display:**
- Completion date shown below requirement name
- Expiry date with color-coded status (green=valid, red=expired)
- Verification status badge ("Verified by [user]")
- "No certificate uploaded" warning when evidence missing

**Unified Actions Dropdown:**
For training requirements with existing records:
- **Verify Training** - Uses training-specific endpoint (`/api/training-records/{id}/verify`)
- **Remove Verification** - Uses training-specific endpoint (`/api/training-records/{id}/unverify`)
- **Edit Training Record** - Opens correction dialog with field selector (expiry_date, completion_date, status)
- **Replace Certificate** - Opens certificate upload dialog with superseding logic
- **View History** - Shows training record correction history
- **Delete Training Record** - Soft-deletes with audit trail

**Single Source of Truth:**
- All training state flows through `training_records` collection
- Changes in What's Needed sync instantly to Training tab and Training Matrix
- Documents/evidence are attachments to training records, not independent state
- One active record per employee+requirement (deleted/superseded excluded from calculations)

**Endpoints Used:**
- `POST /api/training-records/{id}/verify` - Verify training
- `POST /api/training-records/{id}/unverify` - Remove verification
- `POST /api/training-records/{id}/correct` - Edit with audit trail
- `DELETE /api/training-records/{id}` - Soft delete
- `GET /api/training-records/{id}/history` - View correction history
- `POST /api/employees/{id}/training/{req_id}/upload-certificate` - Upload/replace certificate

## Previous Update (2026-03-28)
**Simplified File Correction & Clickable Dashboard Cards - COMPLETE**

### Clickable Summary Cards with Drill-Down Navigation
Dashboard and Audit View cards now navigate to filtered pages:
- **Expired** → Training Matrix (?filter=expired)
- **Needs Renewal** → Training Matrix (?filter=expiring_soon)
- **Staff Not Ready** → Employees (?work_readiness=not_ready)
- **Supervised Start** → Employees (?work_readiness=supervised_start)
- **Ready to Work** → Employees (?work_readiness=ready_to_work)
- **Policies Not Acknowledged** → Compliance Centre (?tab=policies)
- **DBS Pending** → Employees (?requirement=dbs)
- **RTW Missing** → Employees (?requirement=rtw)
- **References Outstanding** → Employees (?requirement=references)

Cards show hover states, pointer cursor, arrow icons, and helper text.

### Simplified File Correction System
Every uploaded file now shows 4 actions:
- **View** - Opens file in preview
- **Download** - Downloads to user's device
- **Replace** - Upload new file to replace existing
- **Delete** - Permanently remove from active use

Delete behavior:
- Removes file from active requirement immediately
- Removes from compliance calculation
- Removes from verification flow
- Requirement status updates correctly (Still Needed / Ready for Review)
- Creates audit trail with: filename, requirement, deleted_by, deleted_at, optional reason

Broken file handling:
- Shows "File unavailable" if file cannot be accessed
- View/Download disabled
- Replace/Delete always available

### Training Matrix URL-Based Filters
Added ?filter parameter support:
- ?filter=expired - Shows expired training records
- ?filter=expiring_soon - Shows records needing renewal
- ?filter=valid - Shows valid records
- Filter state syncs with URL for navigation preservation

## Previous Update (2026-03-28)
**CQC-Ready UI Redesigns & Safe Correction System - COMPLETE**

### Action-First Dashboard Redesign
- REDESIGNED: "Needs Attention" section at top with 4 action cards:
  - Expired (documents with past expiry dates)
  - Needs Renewal (items expiring within 30 days)
  - Not Ready to Work (staff missing mandatory requirements)
  - Policies Not Yet Acknowledged
- REDESIGNED: "Workforce Readiness" section with Ready to Work, Supervised Start, Not Ready counts
- REDESIGNED: "Onboarding Progress" with "Progress to Full Compliance" microcopy
- KEPT: Quick Actions and Recent Employees sections

### Inspection-Ready Audit View
- NEW: "Risks & Alerts" section at the TOP (CQC inspector focus)
- NEW: "Last updated: [timestamp]" display
- REDESIGNED: Clear sections - Workforce Status, Policies & Acknowledgement, Training & Certification Status
- REDESIGNED: Staff Overview table with Work Status badges
- READ-ONLY: No action buttons, inspector-friendly view

### Training Matrix Redesign
- NEW: "Expiry Date" column showing actual dates
- NEW: "Renewal Status" column with color badges (Valid/Needs Renewal/Expired) and days count
- NEW: "Verified" column showing verification status
- NEW: Filter buttons: All Records, Expired, Needs Renewal, Valid
- STATS: Completed, Verified, Needs Renewal, Expired counts at top

### Safe Correction System (Audit-Safe)
- NEW: Edit Record modal with field selector (Expiry Date, Completion Date, Status)
- NEW: Mandatory "Reason for Change" field (min 3 characters)
- NEW: Current Value display (read-only) and New Value input
- NEW: Warning for corrections after verification
- NEW: POST /api/training-records/{record_id}/correct endpoint
- NEW: GET /api/training-records/{record_id}/history endpoint
- AUDIT: All corrections logged with old_value, new_value, reason, user, timestamp

### Grouped Audit Log
- REDESIGNED: Audit log now grouped by category (Documents, Training, Policies, Profile Changes)
- NEW: Category icons and counts
- NEW: Enhanced metadata display showing field changes with old→new values
- NEW: Reason display for corrections
- LIMIT: 10 entries per category with "+ N more" indicator

## Previous Update (2026-03-28)
**Policy System Simplification - COMPLETE**
**CQC-Ready Expiry System & Work Readiness Validation - COMPLETE**
- Document expiry tracking per file (issue_date, expiry_date)
- Dynamic expiry status: Valid (>30 days), Expiring Soon (<=30 days), Expired
- Document Status card in employee overview
- Critical expiry override: RTW/DBS expired = Not Ready
- Work readiness microcopy: Clear explanations for each status

**UI Language Standardization - COMPLETE**
- Employee list columns simplified: Employee, Role, Work Status, File Status, Progress, Actions
- Work Status labels standardized: Ready to Work, Supervised Start, Not Ready
- File Status labels standardized: Incomplete, Nearly Complete, Complete
- Progress format standardized: X% Complete
- Employee profile header: "Progress" (was "Compliance Score"), "File Status" badge
- Bulk Upload button removed from employee profile

**Critical Bug Fixes & Policy Reversal System - COMPLETE**
- Fixed document removal sync (await fetchData for immediate UI update)
- Fixed scoring inconsistency (single source of truth for compliance %)
- Added Policy Unassign/Withdraw functionality with audit trail
- Added Organisation Settings with service_type (adults_only/children_only/mixed)

**Policy Acknowledgement & Document Verification System - COMPLETE**
- Two-layer policy system (Org policies + Employee assignments)
- Full acknowledgement workflow: Assigned → Viewed → Acknowledged
- Admin review functionality after employee acknowledgement
- Signature information display with names and timestamps
- Comprehensive audit logging with compliance filter

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

#### Policy Acknowledgement & Document Verification System (Completed 2026-03-28)
- [x] **Two-Layer Policy System**:
  - Compliance Centre: 32 organisation-level policies
  - Policy Assignments: Employee-level policy assignments with acknowledgement tracking
- [x] **Policy Acknowledgement Flow**:
  - "I have read and understood this policy" button
  - Stores: employee_id, policy_id, policy_version, acknowledged_at, acknowledged_by_employee_name
  - Status progression: Assigned → Viewed → Acknowledged
- [x] **Admin Review Flow**:
  - "Reviewed and Approved" button (after employee acknowledges)
  - Stores: admin_id, admin_reviewed_at, admin_reviewed_by_name
- [x] **Policy Unassign/Withdraw** (Completed 2026-03-28):
  - Unassign: For pending policies (before acknowledgement)
  - Withdraw: For acknowledged policies (preserves history)
  - Both actions log to audit trail with reason
  - Status transitions: assigned/viewed → unassigned OR acknowledged → withdrawn
- [x] **Signature Information Display**:
  - Employee Acknowledgement section: Name + Date/Time
  - Admin Review section: Name + Date/Time
- [x] **Document Verification**:
  - "Verified by Admin" action for uploaded documents
  - Stores: admin_id, verified_at, verified_by_name
- [x] **Audit Logging**:
  - policy_assigned, policy_viewed, policy_acknowledged, policy_admin_reviewed
  - policy_unassigned, policy_withdrawn
  - document_verified, document_uploaded, document_replaced
  - compliance_only filter for focused audit trail
- [x] **Policy Assignments Page**:
  - Centralized view of all policies and assignment status
  - Assign to Employee(s) action for active policies
  - Shows: Total Policies, Total Assignments, Acknowledged count
- [x] **Simple, Audit-Safe Design**:
  - Timestamps, identity, clarity, audit trail
  - No drawn signatures or complex PDF editing

#### Document Control & Scoring Fixes (Completed 2026-03-28)
- [x] **Document Removal Sync**:
  - Fixed: await fetchData() after remove/replace actions
  - UI syncs immediately across all tabs
  - No stale data after document operations
- [x] **Scoring Consistency**:
  - Single source of truth: complianceRequirements.statuses.overall_compliance.percentage
  - Top card, What's Needed, Overview all show same percentage
  - Formula: (approved requirements / total requirements) * 100
- [x] **Organisation Settings**:
  - Service type: adults_only, children_only, mixed
  - Endpoint: GET/PUT /api/org-settings
  - Settings logged to audit trail on change

#### Separated Status Model (Completed 2026-03-28)
- [x] **Three Separate Status Types**:
  1. **Start Status**: Not Ready / Supervised Start Only / Ready to Work
     - "Shows whether this employee can safely start work."
  2. **Recruitment File**: Incomplete / Complete
     - "Shows whether the pre-employment record is complete."
  3. **Policies**: No Policies Assigned / Policies Assigned / All Policies Acknowledged
     - "Shows whether assigned policies have been read and acknowledged."
  4. **Overall Compliance**: Percentage as supporting information only
- [x] **Restructured Categories**:
  - 1_Legal_Safety: RTW Documents, RTW Verification, Identity, DBS Certificate, DBS Check, NMC (nurses)
  - 2_Core_Training: Safeguarding, Manual Handling, Infection Control, BLS, Fire Safety, Health & Safety
  - 3_Competency_Health: Health Screening, Induction, Clinical Competency (nurses), Medication Competency
  - 4_Recruitment_Record: Interview Record, Reference 1, Reference 2, Recruitment Checklist, Application Form, CV
  - 5_Agreements: Contract Acknowledgement, Employee Handbook Acknowledgement
  - 6_Admin: Personal Information Form, Equal Opportunities Monitoring
- [x] **Elevated References**: References now in Recruitment Record category, marked as important pre-employment checks
- [x] **Priority Badges Updated**:
  - Red "Required" - start_required items (blocks work)
  - Orange "Health" - supervised_start items
  - Blue "Recruitment" - recruitment file items
  - Gray/none - secondary items
- [x] **Clean Overview**: Shows only Start Status, Recruitment File, Policies, Overall Compliance
- [x] **Start Status Filter**: Dropdown with Ready to Work, Supervised Start Only, Not Ready
- [x] **All Tabs Synchronized**: Overview, What's Needed, Documents all read from complianceRequirements

#### Work Readiness System (Refactored 2026-03-28)
- [x] **Defined Work Readiness Requirements (CQC Standards)**:
  - **MANDATORY (Blocks work)**: Right to Work Documents, RTW Verification, Identity Documents, DBS Certificate, DBS Update Service Check, Safeguarding Training, Manual Handling Training, Infection Control Training
  - **Nurse-specific mandatory**: NMC Registration (only for nurses)
  - **Required Soon**: BLS, Fire Safety, Health & Safety, References 1 & 2, Health Screening
  - **Secondary**: All other compliance items
- [x] **Weighted Compliance Scoring**:
  - Mandatory items = 80% of score
  - Required Soon items = 15% of score
  - Secondary items = 5% of score
- [x] **Work Ready Status Badges** on Employees List:
  - "Work Ready" (green) - All mandatory items verified
  - "Almost Ready" (amber) - Most mandatory items complete
  - "Not Ready" (red) - Missing mandatory items
  - "Fully Compliant" (green) - Everything complete & verified
- [x] **Work Readiness Alert Panel** on What's Needed tab:
  - Shows status with colored background (green/amber/red)
  - Displays weighted compliance score with progress bar
  - Lists missing mandatory items
- [x] **Priority Badges on Requirements**:
  - 🔴 "Required" badge on mandatory items
  - 🟠 "Soon" badge on required_soon items
  - "⚠ Required before employee can start work" hint on mandatory items
- [x] **Sorted Requirements**: Mandatory items always shown first (priority_order)
- [x] **Backend API**: `work_readiness` object returned in compliance-requirements endpoint
- [x] **Work Readiness Filter** on Employees List:
  - Dropdown filter: All Readiness, Work Ready, Almost Ready, Not Ready
  - Client-side filtering by work readiness status
  - Helper text: "Filter employees by work readiness to quickly see who can start work"

#### Expiry Tracking System (Completed 2026-03-28)
- [x] **Expirable Requirements Defined**:
  - Documents: DBS Certificate, Right to Work Documents, NMC Registration
  - Training: Safeguarding, Manual Handling, Infection Control, BLS, Fire Safety, Health & Safety
- [x] **Expiry Status Calculation**:
  - Valid: Expiry date > 30 days away
  - Expiring Soon: Within 30 days of expiry
  - Expired: Past expiry date
- [x] **Expiry Alerts Panel** on Employee Profile:
  - Shows count of expired and expiring items
  - Lists expired items with days overdue
  - Lists expiring items with days until expiry
- [x] **Expiry Status on Requirement Rows**:
  - Badge showing "Expired [date]" / "Expires [date]" / "Valid until [date]"
  - Individual file badges for expiry status
- [x] **Expiry Indicator on Employees List**:
  - Shows "X expired" or "X expiring" badge in Compliance column
  - Red for expired, amber for expiring soon
- [x] **Dashboard Endpoint**: `/api/dashboard/expiry-alerts`
  - Returns all employees with expired/expiring items
  - Grouped by severity (expired first, then expiring)
  - Ready for dashboard UI integration

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
- [x] ~~Phase 2 Migration: Apply evidence-based structure to all employees~~ (DONE)
- [x] ~~Expiry Tracking Enhancements: Dashboard alerts for expiring items~~ (DONE)
- [x] ~~Policy Acknowledgement System with audit trail~~ (DONE 2026-03-28)
- [ ] Email notifications via Resend for document requests and expiries
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
2026-03-28 - CQC Audit Readiness: User Guidance & Microcopy Overhaul

### Checklist Reordering by Audit Priority (Completed 2026-03-28)
- [x] **Reorganized categories by real-world care audit priority**:
  - 1_Legal_Safety: Legal & Safety (RTW, DBS, Identity) - 5 items
  - 2_Core_Training: Core Training (Safeguarding, Manual Handling, etc.) - 6 items
  - 3_Role_Readiness: Role Readiness (Health Screening, Induction, References) - 3 items
  - 4_Employment: Employment (Contract, Application, Interview) - 5 items
  - 5_Agreements: Agreements (Handbook, Policies) - 2 items
  - 6_Admin: Admin / Other - 2 items
- [x] **Backend**: Updated MANDATORY_ITEMS dictionary in server.py with new category prefixes
- [x] **Frontend**: Updated categoryOrder and CATEGORY_DISPLAY in EmployeeProfilePage.js
- [x] **Testing**: All 23 requirements display in correct order, categories verified

### File Preview Reliability Fixes (Completed 2026-03-28)
- [x] **Profile Photo Serving Endpoint**: Added `GET /api/employees/{id}/profile-photo/view` for authenticated photo fetching
- [x] **EmployeeAvatar Component**: New reusable component at `/app/frontend/src/components/portal/EmployeeAvatar.jsx`
  - Fetches photo via authenticated endpoint
  - Falls back gracefully to initials if fetch fails or no photo
  - Supports size variants: sm, md, lg
- [x] **DocumentPreviewModal Improvements**:
  - Enhanced PDF error state with "Preview unavailable" message
  - Added "Open File" and "Download File" fallback buttons when preview fails
  - Better user messaging instead of leaving users in broken error state
- [x] **File Accessibility Check Before Verification**:
  - `handleVerifyRequirement` now checks if evidence file is accessible before allowing approval
  - `handleVerifyDocument` now validates file accessibility before verification
  - Prevents approval of documents that cannot be opened/downloaded
- [x] **Profile Photo Display Fix**:
  - Profile photo now fetched via authenticated endpoint, not raw storage URL
  - Photos display immediately after upload refresh
  - Updated Dashboard, EmployeesPage, and EmployeeProfilePage to use EmployeeAvatar

### Document Control & File Management (Completed 2026-03-28)
- [x] **File Management Actions** - Every requirement with evidence now has:
  - Edit Details (issue date, expiry date, notes, label)
  - Replace File (marks old as superseded, uploads new)
  - Remove File (soft-delete with mandatory reason)
  - View History (full audit trail)
- [x] **Soft-Delete Architecture**:
  - Files are never permanently deleted
  - Remove marks file as `status: "removed"` with removal_reason
  - Replace marks old file as `status: "superseded"` with supersede_reason
  - Only `active` files count for compliance scoring
- [x] **Audit Trail (CQC-compliant)**:
  - Every action logs: user_id, user_name, action_type, timestamp, mandatory reason
  - Stored in `audit_logs` collection
  - View History shows complete timeline per requirement
- [x] **Safety Rules**:
  - Requirements revert to "Still Needed" when all files removed
  - Verification blocked if no active files exist
- [x] **Backend Endpoints**:
  - `POST /api/employees/{id}/requirements/{req_id}/evidence/{file_id}/remove` - Soft delete
  - `POST /api/employees/{id}/requirements/{req_id}/evidence/{file_id}/replace` - Replace with audit
  - `GET /api/employees/{id}/requirements/{req_id}/history` - Full audit trail
- [x] **Frontend UI**:
  - Three-dot dropdown menu on each requirement with evidence
  - Remove dialog with mandatory reason textarea
  - Replace dialog with file upload + reason
  - History dialog with timeline view

### ComplianceOverview Count Fix (Completed 2026-03-28)
- [x] Fixed count discrepancy between Overview and What's Needed tabs
- [x] ComplianceOverview now uses backend `complianceRequirements` data for accurate counts
- [x] Verified: Overview "Care Status" cards match checklist header counts exactly

### Full E2E Onboarding Audit (Completed 2026-03-28)
**Audit Test Employee created and tested through full compliance workflow**

✅ **What Works Perfectly:**
- Employee creation with auto-generated employee code
- All 6 compliance categories displayed (Legal & Safety, Core Training, Role Readiness, Employment, Agreements, Admin/Other)
- Upload Document dialog with categorized dropdown
- View/Download buttons on requirements with evidence
- Three-dot menu with document control options
- Status badges (Checked & Approved, Ready for Review, Still Needed)
- Internal vs Employee document distinction
- Multi-file support with file counts
- Training certificate upload with expiry dates
- Compliance score calculation (0% → 39% after uploads)
- Count consistency between Overview and Checklist tabs

⚠️ **Minor Issues Addressed:**
- Overview Care Status counts now match What's Needed checklist ✓ FIXED

🔴 **Critical Issues:** None

🔁 **Confusing Flows:** None identified

📊 **System Ready for Onboarding Multiple Employees:** YES

### Critical Bug Fix: Approve Button 404 (Fixed 2026-03-28)
- **Issue**: Approve/Verify button returned "Not Found" (404)
- **Root Cause**: The `verify_requirement` function at line 3660 was missing its `@api_router.post` decorator
- **Fix**: Added `@api_router.post("/employees/{employee_id}/requirements/{requirement_id}/verify")` decorator
- **Verified**: Endpoint now works correctly - returns success message or proper error if no evidence

### Data Consistency Fix: Single Source of Truth (Fixed 2026-03-28)
- **Issue**: Overview tab and What's Needed tab showed DIFFERENT data
- **Root Cause**: ComplianceOverview used hardcoded COMPLIANCE_ITEMS (9 items) instead of backend data (23 items)
- **Fix**: Completely rewrote `/app/frontend/src/components/portal/ComplianceOverview.js` to use `complianceRequirements` prop from backend
- **Verified**: Both tabs now show IDENTICAL counts (tested: 11 approved, 10 ready, 2 still needed)

### Upload Reliability Improvements (Fixed 2026-03-28)
- Added comprehensive logging to upload endpoint (start, progress, success/failure)
- Proper error handling with clear error messages
- UI refreshes from backend after every action (no stale state)
- All actions tested: Upload, View, Download, Replace, Remove, Approve - ALL WORKING

### CQC Audit Readiness: User Guidance & Microcopy (Completed 2026-03-28)
**Goal:** Make system impossible to misuse by non-technical care staff

**1. Global Instruction Panel** - Added at top of "What's Needed":
- "Getting an Employee Ready" heading
- Step-by-step instructions: Upload → Check → Mark as Approved
- "You can stop and return at any time — progress is saved automatically"

**2. Next Step Guidance** - Persistent helper panel:
- Shows when items still needed
- "Complete the next item marked 'Still Needed' at the top of the list"
- "Once uploaded, review and approve before moving on"

**3. Standardized Status Labels** - Only these 3 allowed:
- Still Needed (red)
- Ready for Review (amber)
- Checked & Approved (green)

**4. Requirement Microcopy** - Helper text for each requirement:
- Right to Work: "Upload visa, passport, or share code proof"
- ID Documents: "Upload passport or driving licence (photo or scan)"
- DBS: "Upload DBS certificate (front page with reference number)"
- Training: "Upload training certificate or proof of completion"

**5. Clear Button Text**:
- "Upload Document" (not "Add Document")
- "Mark as Approved" (not just "Approve")
- "Add Another File" (for multi-file requirements)

**6. Multi-file Guidance**:
- "You can upload more than one file if needed (e.g. front and back)"

**7. Post-Upload Feedback**:
- "Document uploaded — please review and approve"

**8. Tab Clarity Message**:
- "Use 'What's Needed' to complete compliance. Other tabs show records and history."

**Design Principle:** "Follow the list. Everything gets done."

### Care-Focused Language (Completed 2026-03-28)
- [x] **Renamed all audit terminology to care terminology**:
  - "Audit Summary" → "Care Status"
  - "Verified" → "Checked & Approved"
  - "Evidence Uploaded" → "Ready for Review"  
  - "Missing" → "Still Needed"
  - "Expired" → "Needs Updating"
  - "Checklist" → "What's Needed"
  - "Audit Progress" → "Profile Progress"
  - "Verify" → "Approve"
- [x] **ComplianceOverview sections updated**: Checked & Approved, Ready for Review, Still Needed, Needs Updating
- [x] **Progress bar**: Shows "Profile Progress - X/Y approved"

### Evidence Editing with Audit Trail (Completed 2026-03-28)
- [x] **Edit Details action**: More menu (⋯) on each evidence item with Edit Details and View History
- [x] **Editable fields**: Issue Date, Expiry Date, Notes, Document Label
- [x] **Required reason**: Every edit requires a reason (min 3 characters) for audit trail
- [x] **Full audit trail**: Creates immutable log entry with:
  - employee_id, file_id, requirement_id
  - field_changed, old_value, new_value
  - changed_by, changed_by_name, changed_at
  - reason, was_verified_before_edit
- [x] **View History modal**: Shows complete change history
- [x] **Post-approval flag**: Edits after approval flagged as "edited_after_approval"
- [x] **Expiry tracking**: Updated expiry dates immediately affect dashboard alerts

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

### Phase 2 Migration: Evidence Files Array (Completed 2026-03-28)
- [x] **Data Structure Migration**:
  - Migrated 10 training records from `certificate_url` to `evidence_files` array
  - All employee documents already using `evidence_files` structure (8 docs)
  - Migration script: `/app/backend/migrations/migrate_to_evidence_files.py`
- [x] **Consistent Multi-File Support**:
  - Training records now support multiple evidence files per item
  - Each evidence file has: file_id, file_url, original_filename, file_label, source_type, status
  - Proper labels: "Manual Handling Certificate", "Safeguarding Certificate", etc.
- [x] **Documents Tab Sync Fix** (P0):
  - Fixed JSX syntax error in EmployeeProfilePage.js (lines 3073-3145)
  - Documents tab now uses `evidence_files` array (same as What's Needed tab)
  - Both tabs display identical file counts for all requirements
  - DBS Certificate correctly shows 2 files (Front/Back) in both tabs
- [x] **Verification**:
  - Lawrence Egbeni: 4 training certificates with evidence_files
  - Olakunle Alonge: 5 verified training certificates, 12/23 items verified
  - Certificate preview modal working with page navigation

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
