# CareTrust Compliance Portal - PRD

## Original Problem Statement
Build a Requirement-Based Compliance Engine for a Care Recruitment Agency ensuring CQC audit-readiness. Implement a digital application intake flow, strict Applicant vs Employee separation, a single authoritative 2-tier work readiness logic layer, an NHS-level strict Reference/Referee Integrity workflow, CV extraction, and a Supplementary Training module.

## Core Requirements
- 2-tier work readiness: `onboarding` (Conditional Offer) vs `active_employee` (Unconditional Offer)
- Automatic promotion when all NHS compliance checks pass
- Professional Registration tracking (NMC, GMC, HCPC) with role-based blockers
- Single source of truth per requirement
- Complete lockdown of Right to Work, DBS, Identity, Proof of Address with visual PDF document stamping
- Worker Self-Service Portal for tracking compliance, signing contracts, and completing forms with save/resume capability
- Admin Compliance Dashboard top-level views

## Tech Stack
- Frontend: React + Tailwind + Shadcn/UI
- Backend: FastAPI (Python)
- Database: MongoDB (Railway Production)
- Email: Resend
- AI: Google Gemini 2.5 Flash for CV/Document extraction
- Auth: JWT-based custom auth (worker portal) + Admin auth

---

## COMPLETED: Worker Portal Implementation (December 2025)

### Complete Worker Portal Flow
1. **Public Application → Auto-Email with Magic Link**
   - After application submission, applicant receives welcome email with magic link
   - Email includes: Application reference, portal access button, list of required items
   - Magic link valid for 7 days

2. **Worker Login via Magic Link**
   - `/worker/login` - Request magic link by entering email
   - `/worker/verify?token=xxx` - Verify token and create worker session
   - JWT session valid for 7 days

3. **Worker Dashboard**
   - **Onboarding View** (status != active_employee):
     - Progress bar showing compliance percentage
     - Forms to complete (Health Questionnaire, Personal Info, HMRC Starter, Equal Opps, Emergency Contacts)
     - Documents to upload (RTW, DBS, ID, POA x2)
     - Contract signing with digital signature
     - Training certificates needed
   
   - **Active Employee View** (status == active_employee):
     - "Active Employee" green banner
     - Expiry alerts for documents/training
     - Upload renewal documents

4. **Forms with Save/Resume**
   - `GET /api/worker/forms` - List all forms with status
   - `GET /api/worker/forms/{form_id}` - Get form data (saved progress or submitted)
   - `POST /api/worker/forms/{form_id}/save` - Auto-save progress
   - `POST /api/worker/forms/{form_id}/submit` - Final submission
   - Form fields defined in WORKER_FORM_DEFINITIONS constant

5. **Admin Notifications**
   - When worker submits a form, admin receives email notification
   - Email includes: employee name, form type, submission time, review link

6. **Auto-Promotion to Active Employee**
   - Triggered after: form submission, contract signing, document stamp verification
   - Checks ALL requirements: RTW, DBS, Identity, POA (2 docs), References (2), Contract, Induction, Health Declaration, Professional Registration
   - When promoted, worker receives congratulations email

### API Endpoints (Worker Portal)
- `POST /api/worker/request-login` - Send magic link email
- `POST /api/worker/verify-login` - Verify magic link token
- `GET /api/worker/dashboard` - Get worker's compliance dashboard
- `GET /api/worker/forms` - List forms and status
- `GET /api/worker/forms/{form_id}` - Get form data
- `POST /api/worker/forms/{form_id}/save` - Save form progress
- `POST /api/worker/forms/{form_id}/submit` - Submit form
- `POST /api/worker/upload-document/{requirement_id}` - Upload document

### Frontend Routes (Worker Portal)
- `/worker/login` - Magic link request page
- `/worker/verify` - Token verification page
- `/worker/dashboard` - Worker compliance dashboard
- `/worker/forms/:formId` - Form filling page

### Key Files
- `/app/frontend/src/pages/worker/WorkerLoginPage.js`
- `/app/frontend/src/pages/worker/WorkerVerifyPage.js`
- `/app/frontend/src/pages/worker/WorkerDashboard.js`
- `/app/frontend/src/pages/worker/WorkerFormPage.js`
- `/app/backend/server.py` (Worker endpoints: lines 7060-7920)
- `/app/backend/work_readiness_engine.py` (can_promote_to_active function)

---

## Previous Implementations

### NHS Status Flow (COMPLETED Dec 2025)
- `onboarding` = Recruitment Pipeline (Conditional Offer) - cannot work
- `active_employee` = Staff (Unconditional Offer) - cleared to work
- Automatic promotion when ALL checks pass

### Professional Registration (COMPLETED Dec 2025)
- NMC for Nurses
- GMC for Doctors
- HCPC for OT/Physio
- Social Work England for Social Workers
- Not required for HCAs/Care Assistants

### Visual Document Stamps (COMPLETED Dec 2025)
- PDF stamp overlay with verification details
- Image stamp with semi-transparent box
- Stamp types: Original Seen, Copy Verified, Online Check
- CQC-compliant audit trail

### References System (COMPLETED Dec 2025)
- Add Referee details manually
- Send reference request emails
- Public reference form for referees
- Employment history cross-check

---

## Prioritized Backlog

### P0 (Critical) - NONE

### P1 (High)
- [x] Worker Portal complete flow - COMPLETED Dec 2025
- [x] Admin UX Audit - Tab duplicates fixed - COMPLETED Apr 2026
- [x] Admin Internal-Only Forms with PDF - COMPLETED Apr 2026
- [x] Cybersecurity Audit - All P0/P1 fixed - COMPLETED Apr 2026
- [x] Worker Portal End-to-End Experience Enhancements - COMPLETED Apr 2026
- [x] Dashboard & Employee Profile Unified Progress - COMPLETED Apr 2026
- [ ] Role-Based Compliance Configuration using `role_compliance_profiles`
- [ ] Supervision Records tracking UI

### P2 (Medium)
- [x] Remove duplicate sections from Employee Profile - COMPLETED Apr 2026
- [x] Implement 7-section Employee Profile consolidation - COMPLETED Apr 2026
- [ ] server.py modular split (currently 48k+ lines) - CRITICAL for maintainability
- [ ] F811 duplicate function cleanup
- [ ] MFA for admin accounts (RECOMMENDED)

### P3 (Future)
- [ ] Supabase Auth integration with RLS policies
- [ ] Phase out MongoDB entirely (PostgreSQL migration)
- [ ] Auto-delete employee data 3 years after termination (CQC requirement)
- [ ] MFA for admin accounts (TOTP-based)

---

## COMPLETED: Dashboard & Employee Profile Unified Progress (April 2026)

### New Backend Endpoints
1. **GET /api/employees/{id}/unified-progress** - SINGLE SOURCE OF TRUTH
   - Returns: `overall_percentage`, `completed_requirements`, `total_requirements`
   - Category breakdown: documents, forms, training, references, agreements, induction
   - Blockers list with actionable items
   - Role-aware (adds professional registration requirements for clinical roles)
   - Excludes optional items like Equal Opportunities from total

2. **POST /api/workers/{employee_id}/send-reminder**
   - Sends magic link email to worker
   - Includes custom message option
   - Shows outstanding compliance items in email
   - Logs action in audit trail

3. **POST /api/employees/{employee_id}/request-renewal/{type}**
   - Types: dbs, right_to_work, training, professional_registration, identity, proof_of_address
   - Sends renewal request email to worker
   - Includes direct upload link
   - Logs action in audit trail

### New Frontend Components
1. **UnifiedProgressSection** (`/app/frontend/src/components/admin/UnifiedProgressSection.js`)
   - Displays single source of truth progress
   - Shows category breakdown grid
   - Lists blocking items with action buttons
   - Integrated into Employee Profile Overview tab

2. **AdminActionButtons** (`/app/frontend/src/components/admin/AdminActionButtons.js`)
   - SendReminderButton - Opens modal with custom message option
   - RequestRenewalButton - One-click renewal request

3. **useUnifiedProgress Hook** (`/app/frontend/src/hooks/useUnifiedProgress.js`)
   - Reusable hook for fetching unified progress data

4. **Dashboard Empty State** (`/app/frontend/src/pages/portal/DashboardPage.js`)
   - "Get Started" guide when no employees exist
   - Quick setup checklist (Add employee, Upload policies, Configure training)
   - Hidden attention/readiness sections until data exists

### Test Results
- Backend: 100% (24/24 API tests passed)
- Frontend: UnifiedProgressSection integrated and visible
- Test report: `/app/test_reports/iteration_154.json`

---

## COMPLETED: 7-Section Employee Profile Consolidation (April 2026)

### Tab Structure Implemented
| Tab | Content | Purpose |
|-----|---------|---------|
| **Work Readiness** | UnifiedProgressSection + Recruitment/Work Readiness panels + Pre-Employment Gates | Single view of all blockers |
| **Compliance** | DualRowComplianceSection - RTW, DBS, Identity, POA, Contract | Core evidence management |
| **Forms** | Health Questionnaire, Personal Info, HMRC, Emergency Contacts status | Form tracking |
| **Training** | Induction + Competencies + Mandatory Training + Spot Checks | All training in one place |
| **References** | Reference 1 + Reference 2 full workflow | Reference management |
| **Employment** | Employment history + gap verification + declarations | Employment records |
| **Audit** | Full audit trail | Activity history |

### Duplicate Sections Removed
- ✅ Old "Overview" tab content (Personal Details card - moved to Work Readiness Summary)
- ✅ Duplicate ComplianceOverview in overview tab
- ✅ Multiple TabsContent for "checklist" (consolidated to one)
- ✅ Duplicate progress sections (now using UnifiedProgressSection)

### Files Modified
- `/app/frontend/src/pages/portal/EmployeeProfilePage.js` - Restructured to 7 tabs
- Removed ~250 lines of duplicate content

---

## BUGS FIXED (April 2026 - Critical Fixes Session)

### Bug 1: Worker Portal 0% Progress Bug (P0 CRITICAL)
- **Issue**: Worker dashboard showed 0% progress but "9 of 11 requirements completed"
- **Root Cause**: Variable name collision - `progress_percentage` was being overwritten inside form loop
- **Fix**: Renamed inner variable to `form_progress_pct` in `/app/backend/server.py` line 7670
- **Result**: Now correctly shows 82% for 9/11 requirements

### Bug 2: "Loading approval status..." in Recruitment Pipeline (P0)
- **Issue**: Some applicants showed "Loading approval status..." indefinitely
- **Fix**: Added useEffect to automatically fetch approval status for all visible applicants
- **File**: `/app/frontend/src/pages/portal/RecruitmentPage.js`

### Bug 3: Multiple Conflicting Progress Numbers - RESOLVED WITH LABELS
- **Issue**: Different pages showed 2/11, 15%, 50%, 33%, etc.
- **Resolution**: Added clear labels and tooltips to explain each metric:
  - `📋 Recruitment Progress: 4/12` = Documents + references + forms before promotion
  - `✅ Full Compliance: 24%` = All requirements including training + induction
  - `🟢 Work Readiness: 66%` = CQC work readiness calculation

---

## COMPLETED: Labeled Progress Metrics & UI Cleanup (April 2026)

### New Component: LabeledProgressMetrics.js
Location: `/app/frontend/src/components/compliance/LabeledProgressMetrics.js`

**Exported Components:**
1. `LabeledProgressBadge` - Compact badge with label, tooltip, and info icon
2. `LabeledProgressCard` - Full card with progress bar and optional breakdown
3. `ComplianceBreakdownCard` - 6-category breakdown replacing "Care Status"
4. `PROGRESS_METRICS` - Configuration for each metric type

### Changes Implemented

| Task | Status | File |
|------|--------|------|
| Add clear labels to all progress numbers | ✅ DONE | LabeledProgressMetrics.js |
| Add tooltips explaining each metric | ✅ DONE | Uses Tooltip component |
| Remove pipeline stages (New/Screening/Interview) | ✅ DONE | RecruitmentPage.js |
| Replace "Care Status" with category breakdown | ✅ DONE | UnifiedProgressSection.js |

### Visual Changes

**Before (Recruitment Pipeline):**
- New Applications (0), Screening (0), Interview (0), Compliance Review (0)
- "Progress: 4/12"

**After (Recruitment Pipeline):**
- "All Applicants - 24 applicants awaiting review"
- "📋 Recruitment: 4/12 (33%)" with tooltip

**Before (Employee Profile):**
- "Verified & Complete: 8/24", "Still Needed: 12", "Awaiting Review: 4"

**After (Employee Profile):**
- "📊 Compliance Breakdown" with:
  - 📄 Documents: 3/5
  - 📝 Forms: 0/4
  - 🎓 Training: 4/6
  - 👤 References: 0/2
  - ✍️ Agreements: 1/2
  - 📋 Induction: 0/14
- Total: 8/33 (24%)

---

## COMPLETED: Worker Portal End-to-End Experience (April 2026)

### UI Enhancements Implemented
1. **"Cleared to Work" Messaging**
   - Active employees see enhanced green banner with "Cleared to Work" headline
   - Shows "All NHS compliance requirements verified. You are authorised to work."
   - Mini stats showing "All documents current • No renewals due" when no alerts

2. **Pending Verification vs Verified Badges**
   - Documents/trainings show clear "Pending Verification" amber badge when uploaded but not verified
   - Documents/trainings show green "Verified" badge with shield icon when verified
   - Clock icon for pending, Shield icon for verified

3. **View Verified Documents**
   - Verified documents have a "View" button to open the stamped PDF
   - Links to `file_url` (stamped version if available, otherwise original)

4. **Expiry Tracking with Color-Coded Alerts**
   - Red styling for < 30 days (urgent)
   - Amber styling for < 60 days
   - Yellow styling for < 90 days
   - Animated pulse dot indicator
   - Renamed section to "Upcoming Renewals"

5. **Renewal Upload Buttons**
   - Each alert now has an "Upload Renewal" button
   - Urgent alerts (< 30 days) have prominent red styling
   - Direct upload capability from the alerts section

6. **Professional Registration Display**
   - Shows NMC/GMC/HCPC/SWE registration status for applicable roles
   - Displays registration number if submitted
   - Shows "Required" badge if not submitted for clinical roles
   - Color-coded based on status (green=verified, amber=pending, red=required)

### Backend API Updates
- `/api/worker/dashboard` now returns:
  - `file_url` for each completed document (stamped version if verified)
  - `verification_stamp` field for each document
  - `professional_registration` object with type, number, verified, expiry_date, status
  - `training_id` in alerts for training-specific renewal uploads
  - `job_role` in employee object

### Key Files Modified
- `/app/frontend/src/pages/worker/WorkerDashboard.js` - Enhanced UI components
- `/app/backend/server.py` (lines 7409-7760) - Updated worker_dashboard endpoint

### Test Results
- Backend: 13/13 tests passed (100%)
- Frontend: 9/9 UI tests passed (100%)
- Test report: `/app/test_reports/iteration_153.json`

---

## COMPLETED: Cybersecurity Audit (April 2026)

### P0 Critical Fixes
- ✅ CORS restricted to allowed origins only (no wildcard *)
- ✅ Rate limiting: 5 attempts/hour, 15min lockout after 10 failures
- ✅ Magic link single-use verified (already implemented)

### P1 High Fixes
- ✅ Security headers added (CSP, X-Frame-Options, HSTS, etc.)
- ✅ File type validation by content (magic bytes, not extension)
- ✅ Session timeout configured (15min admin, 30min worker)
- ✅ 7 vulnerable packages updated

### Security Module
- `/app/backend/security.py` - Rate limiter, file validation, headers
- `/app/test_reports/cybersecurity_audit.md` - Full audit report

---

## COMPLETED: Admin Internal-Only Forms (April 2026)

### Interview Record Form
- **Location:** Overview tab → Interview Records panel (right side)
- **Features:**
  - "Record Interview" button for admins
  - Create dialog with all fields: date, method, scores (1-5 stars), decision, notes
  - Save as Draft / Submit options
  - Decision options: Approve, On Hold, Reject
  - PDF download with company logo
  - Automatic status update when decision = "Approve"

### Spot Check Record
- **Location:** Training tab → Health & Competency section → Spot Checks sub-tab
- **Features:**
  - "Record Spot Check" button for admins
  - Fields: type, area, outcome (pass/needs improvement/fail), notes, follow-up
  - PDF download with company logo
  - Summary stats (Passed/Needs Work/Failed counts)

### PDF Service
- **File:** `/app/backend/services/pdf_service.py`
- **Features:**
  - Company logo support via `COMPANY_LOGO_URL` environment variable
  - Professional PDF layout with branding
  - Supports: Interview Record, Induction Certificate, Spot Check
  - Footer with timestamp and compliance note

### Key Files
- `/app/backend/services/pdf_service.py` - PDF generation with logo
- `/app/backend/server.py` (lines 46178-46500) - Admin forms API endpoints
- `/app/frontend/src/components/compliance/InterviewFormPanel.js`
- `/app/frontend/src/components/employee/SpotCheckPanel.js`

### Environment Variable
```
COMPANY_LOGO_URL=  # Set to company logo URL when available
```

---

## COMPLETED: Admin UX Audit (April 2026)

### Tab Structure Fixed
1. **Compliance Tab** - Now shows ONLY:
   - Right to Work (documents + verification)
   - DBS Certificate (documents + update service check)
   - Identity (documents)
   - Proof of Address (2 documents required)
   - Agreements (Contract + Handbook)
   - Recruitment Record (forms)
   - Admin Forms

2. **Removed from Compliance Tab** (now in dedicated tabs):
   - References → References Tab
   - Training → Training Tab
   - Health & Competency → Training Tab (as sub-tabs)

3. **References Tab** - Complete workflow:
   - Referee details display
   - Send Request button
   - Status tracking (Not requested → Sent → Received → Verified)
   - View Response button
   - Mark Verified button

4. **Training Tab** - Consolidated view:
   - Induction sub-tab (checklist with mark complete)
   - Competencies sub-tab
   - Spot Checks sub-tab
   - Training Matrix below

### Progress Labels Clarified
- **"Overall Compliance"** - Shows X% Complete with "X of Y requirements" sub-text
- **"Recruitment Readiness"** - Shows X/11 key items verified (for recruitment approval)

### Worker Portal - NHS Standard Improvements
- Document guidance text added for each upload type
- Accepted file formats displayed (PDF, JPG, PNG - max 10MB)
- AI extraction note for training certificates

### Key Files Modified
- `/app/frontend/src/components/compliance/DualRowComplianceSection.js`
- `/app/frontend/src/components/compliance/RecruitmentApprovalPanel.js`
- `/app/frontend/src/pages/portal/EmployeeProfilePage.js`
- `/app/frontend/src/pages/worker/WorkerDashboard.js`

---

## Test Credentials
- Admin: admin@osabea.care / admin123
- Test Employee: isg1994@outlook.com (Ifedolapo George) - ID: b1fdb4e3-cfc9-4579-9ee7-b5b624248de1

## Database
- Production: Railway MongoDB (`caretrust_production`)
- Connection string in `/app/backend/.env` (MONGO_URL)

---

## COMPLETED: AI Multi-Training Extraction (April 2026)

### Problem Solved
Training certificates often contain 40+ training items in a single document (e.g., table format certificates). The previous system assumed 1 certificate = 1 training record, requiring manual entry for each item. This feature enables bulk extraction of ALL trainings from a single certificate upload.

### Implementation Details

#### Backend (`/app/backend/server.py`)
1. **GET /api/employees/{employee_id}/training-records**
   - Returns all training records with `is_mandatory` and `blocks_promotion` flags
   - Categorizes trainings based on role-specific mandatory requirements
   - Mandatory keywords: safeguarding, manual handling, fire safety, health & safety, basic life support, infection control

2. **POST /api/employees/{employee_id}/training/bulk-upload**
   - Accepts single PDF/JPG/PNG certificate
   - Uses Gemini AI to extract ALL training items from certificate
   - Categorizes each training as Mandatory vs Additional based on employee role
   - Creates individual training records for each extracted item
   - Returns summary: total extracted, mandatory count, additional count

#### Service (`/app/backend/services/multi_training_extraction.py`)
- `MANDATORY_TRAINING_BY_ROLE`: Role-specific mandatory training requirements
- `TRAINING_NAME_MAPPING`: Normalizes certificate training names to standard IDs
- `is_mandatory_for_role()`: Determines if training blocks promotion
- `categorize_extracted_trainings()`: Splits trainings into mandatory/additional
- `extract_multiple_trainings_from_certificate()`: Processes AI extraction result

#### Frontend (`/app/frontend/src/components/training/EnhancedTrainingTab.js`)
1. **MandatoryTrainingSection**
   - Displays 6 mandatory training types with icons
   - Shows completion status (Complete/Missing/Expired)
   - "BLOCKS" badge indicating promotion blockers
   - "Upload" button for missing trainings

2. **BulkUploadSection**
   - Drag-and-drop certificate upload
   - "Select Certificate (PDF/JPG)" button
   - Shows extraction result summary after upload

3. **AdditionalTrainingSection**
   - Collapsible section with "BONUS" badge
   - Lists non-mandatory trainings

### Integration
- `EnhancedTrainingTab` added to Training tab in `EmployeeProfilePage.js`
- Appears above existing `HealthCompetencySection` and `AuditReadyTrainingMatrix`

### Test Results
- Backend: 100% (23/23 tests passed)
- Frontend: 100% (10/10 UI elements verified)
- Test report: `/app/test_reports/iteration_155.json`

---

## COMPLETED: Training Expiry Auto-Reminders (April 2026)

### Features Implemented

#### Scheduled Daily Job (8:00 AM)
- Checks all training certificates expiring within 60 days
- Groups expiring trainings by employee
- Only sends reminder if no reminder sent in last 7 days
- Logs all reminder activity in `training_expiry_reminders` collection

#### Email Notifications to Workers
- Professional HTML email template with training list
- Color-coded urgency (red for <14 days, amber for <30 days)
- Direct link to Worker Portal for uploading renewed certificates
- Table showing training name, expiry date, and days remaining

#### Admin Dashboard Integration
- **TrainingExpiryAlerts** component on main dashboard
- Shows summary: Critical (<14 days), Warning (14-30 days), Upcoming (30-60 days)
- "Send Reminders" button for manual trigger
- Clicking items navigates to employee's Training tab
- Green "All Training Current" state when no expiring trainings

#### New API Endpoints
1. **GET /api/admin/training-expiry-alerts?days=60**
   - Returns trainings grouped by urgency level
   - Includes employee name, training name, expiry date, days remaining

2. **POST /api/admin/training-expiry-reminders/send**
   - Manually triggers reminder emails to all affected workers
   - Returns count of employees notified

#### Dashboard Stats Extended
- `training_expiring_critical`: Count of trainings expiring in <14 days
- `training_expiring_warning`: Count expiring in 14-30 days
- `training_expiring_upcoming`: Count expiring in 30-60 days

### Key Files
- `/app/backend/server.py` (lines 42515-42870) - Scheduler job and reminder system
- `/app/frontend/src/components/admin/TrainingExpiryAlerts.js` - Dashboard component
- `/app/frontend/src/pages/portal/DashboardPage.js` - Integration

---

## COMPLETED: CQC Compliance Overhaul Part 1 (April 2026)

### P0 Changes Implemented

#### 1. Remove [Request] Button
- Changed `UploadRequirementCard.js` to show "Send Reminder" instead of separate Request/Resend buttons
- Workers now upload documents themselves; admins only send reminders

#### 2. Employment Gap Explanation Interface
- Added reason dropdown to EmploymentGapPanel: career_break, education, health, travel, unemployed, family, volunteering, self_employed, other
- Added supporting document upload for gap explanations
- Backend: Updated `/api/employees/{id}/employment-gaps/{gap_id}/explain` to accept `reason_type`
- Backend: New `/api/employees/{id}/employment-gaps/{gap_id}/upload-document` endpoint

#### 3. Reference Mismatch Verification
- Added mismatch reason dropdown to ReferenceResponseDrawer: earlier_employment, personal_reference, employer_changed, agency_reference, name_change, other
- Full reason logged with audit trail

#### 4. Audit Trail Enhancement
- Created `AuditReasonDialog` component for logging admin changes
- Backend: New `log_audit_change()` function captures before/after values + reason
- Backend: `POST /api/admin/audit-change` for logging changes
- Backend: `GET /api/admin/audit-trail/{entity_type}/{entity_id}` for retrieving history

### P1 Changes Implemented

#### 1. Admin Dashboard Actionable Tasks
- Created `ActionableTaskQueue.js` showing:
  - PENDING VERIFICATIONS with [Verify] button
  - REFERENCES TO SEND with [Send Request] button
  - REFERENCE RESPONSES TO REVIEW with [Review] button
  - EXPIRING SOON with [Send Reminder] button
  - WORKERS STUCK IN ONBOARDING with [Remind] button
- Enhanced `/api/admin/task-queue` endpoint with detailed actionable items

#### 2. Document Stamp Burning
- Already implemented: `add_verification_stamp_to_pdf()` burns visible stamp into PDFs
- `add_verification_stamp_to_image()` for images
- Stores `stamped_file_url` served for downloads

### Test Results (iteration_156)
- Backend: 100% (20/20 tests passed)
- Frontend: 100% (All UI elements verified)

---

## COMPLETED: Pre-Employment Gates (12 Requirements) (April 2026)

### Gate Requirements
1. Interview Record completed
2. Contract signed  
3. DBS verified + stamped
4. Right to Work verified + stamped
5. Identity verified + stamped
6. Proof of Address (2 documents) verified + stamped
7. Reference 1 verified
8. Reference 2 verified
9. Induction Checklist complete (14 items)
10. Mandatory Training complete + not expired (6 items)
11. Health Questionnaire completed
12. Employment gaps explained

For Nurse role: 13th requirement - NMC registration verified

### Implementation
- `work_readiness_engine.py`: `can_promote_to_active()` enforces all 12 gates
- `server.py`: `GET /api/employees/{id}/pre-employment-gates` returns detailed status
- Promotion button only enabled when ALL gates are ✅

---

## COMPLETED: Employee Profile UI Consolidation (April 5, 2026)

### Problem
Admin users reported that "Blocking Items", "Recruitment Readiness %", and "Full Compliance" sections were appearing 3-4 times on the Employee Profile page. This caused:
- Severe admin confusion
- Duplicate content overlapping with tab navigation layout
- Users had to scroll past duplicate panels to find the tabs

### Solution
Created `ConsolidatedStatusPanel.js` as a single source of truth that renders ONCE above the tabs, containing:
1. **Status Header** - BLOCKED/READY indicator with employee details
2. **Blocker List** - "WHAT'S BLOCKING PROMOTION" with actionable items
3. **Progress Summary** - Category breakdown (Documents, Forms, Training, References, Agreements, Induction)
4. **Quick Actions** - Send Reminder, View Full Compliance, View Training, View References

### Components Removed from EmployeeProfilePage.js
- ❌ `RecruitmentApprovalPanel` (was rendering duplicate status/blockers)
- ❌ `WorkReadinessPanel` (was rendering duplicate status/blockers)
- ❌ `UnifiedProgressSection` (was rendering duplicate progress)

### Current Structure
```
Employee Profile Page
├── ConsolidatedStatusPanel (ONCE - above tabs)
│   ├── Status Header (BLOCKED/READY)
│   ├── Blocker List (10 items)
│   ├── Progress Summary (0/12)
│   └── Quick Actions
├── 7-Tab Navigation
│   ├── Work Readiness (PreEmploymentGatesPanel only)
│   ├── Compliance
│   ├── Forms
│   ├── Training
│   ├── References
│   ├── Employment
│   └── Audit
```

### Test Results
- Frontend: 100% (8/8 UI tests passed)
- Test report: `/app/test_reports/iteration_157.json`

---

## COMPLETED: ConsolidatedStatusPanel Bug Fixes (April 5, 2026)

### Bugs Fixed

1. **Progress Percentage Calculation**
   - **Issue**: Showed "2/12 requirements complete (0%)" when it should be 17%
   - **Fix**: Changed from `progress.percentage` to calculated `gatesPercentage = Math.round((gatesPassed / totalGates) * 100)`
   - **Result**: Now shows correct percentage (e.g., 2/12 = 17%)

2. **Dynamic Total Requirements by Role**
   - **Issue**: Always showed 12 total gates regardless of role
   - **Fix**: Backend already implements this - 12 for HCA, 13 for Nurse (includes NMC)
   - **Verified**: Nurse role correctly shows 13 total gates

3. **Send Reminder to Worker Button**
   - **Status**: Working correctly
   - **Endpoint**: POST `/api/workers/{employee_id}/send-reminder`
   - **Response**: Returns magic link for worker portal access
   - **Note**: `email_sent:false` in preview (Resend API key not configured)

4. **Category Breakdown Grid**
   - **Fix**: Changed variable reference from `breakdown.completed/total` to `catData.completed/total`
   - **Result**: Shows correct category values (Documents, Forms, Training, References, Agreements, Induction)

### Quick Actions vs Tabs
- **Decision**: Kept both Quick Actions and Tabs
- **Rationale**: Quick Actions provide fast shortcuts (Send Reminder, View Full Compliance) without tab navigation

### Test Results
- Backend: 100%
- Frontend: 100%
- Test report: `/app/test_reports/iteration_158.json`

---

## COMPLETED: Universal Editability UI + P1 Features (April 5, 2026)

### P0: Universal Editability [Edit] Buttons - COMPLETE
All edit buttons are now wired up and functional:

1. **Edit Personal Details Button** (`data-testid="edit-personal-btn"`)
   - Location: Work Readiness tab → Employee Summary card
   - Opens: `EditPersonalDetailsDialog` with fields for name, email, phone, DOB, NI number, address, emergency contact
   - Includes: Reason for change (audit trail)

2. **Edit Employment History Button** (`data-testid="edit-employment-btn"`)
   - Location: Employment tab header
   - Opens: `EditEmploymentHistoryDialog` with multi-position support
   - Features: Add/remove positions, current position toggle, responsibilities field
   - Includes: Reason for change (audit trail)

3. **Edit Reference Button** (`data-testid="edit-reference-btn-{n}"`)
   - Location: References tab → next to declared referee info
   - Opens: `EditReferenceDialog` with NHS-required fields:
     - Referee Type (Professional/Character/Personal)
     - Period of Supervision
     - Direct Supervisor checkbox
     - Can Contact Before Offer checkbox
   - Includes: Reason for change (audit trail)

### P1: Color-Coded Blockers - COMPLETE
`ConsolidatedStatusPanel.js` now shows color-coded severity:
- 🔴 **Critical** (Red) = Missing/Unverified documents
- 🟡 **Pending** (Amber) = Uploaded, awaiting verification
- Each blocker item shows severity badge and color-coded styling
- Action buttons styled to match severity

### P1: Gap Explanation UI - ALREADY IMPLEMENTED
`EmploymentGapPanel.js` already had comprehensive gap explanation:
- Reason dropdown: career_break, education, health, travel, unemployed, family, volunteering, self_employed, other
- Explanation text field
- Supporting document upload
- Admin verify/reject workflow
- Color-coded gap status (pending, explained, verified, rejected)

### Key Files Modified
- `/app/frontend/src/pages/portal/EmployeeProfilePage.js` - Wired up edit dialogs and reference handler
- `/app/frontend/src/components/compliance/ConsolidatedStatusPanel.js` - Added color-coded blocker severity
- `/app/frontend/src/components/compliance/ReferencesPanel.js` - Added Edit button for references
- `/app/frontend/src/components/employee/tabs/ReferencesTabContent.js` - Pass onEditReference handler

### Test Results
- Backend: 100%
- Frontend: 100%
- Test report: `/app/test_reports/iteration_159.json`

---

## COMPLETED: P0 Compliance Checklist (April 5, 2026)

### P0 #1: Edit Declarations Dialog - COMPLETE
Created `EditDeclarationsDialog.js` with NHS-required fields:
- **Criminal Convictions** - Checkbox + details text
- **Health Conditions** - Checkbox + details for occupational health
- **DBS Consent** - Consent checkbox + Update Service ID if registered
- **Right to Work Restrictions** - Restrictions details + visa expiry date
- **Driving Licence** - Licence type dropdown + convictions

Backend endpoint: `PUT /api/employees/{id}/declarations` with reason logging

### P0 #2: Induction Checklist - 15 Care Certificate Standards - COMPLETE
Updated `DEFAULT_INDUCTION_ITEMS` in server.py with Care Certificate standards:
1. Understand your role
2. Your personal development
3. Duty of care
4. Equality and diversity
5. Work in a person-centred way
6. Communication
7. Privacy and dignity
8. Fluids and nutrition
9. Awareness of mental health, dementia and learning disabilities
10. Safeguarding adults
11. Basic life support
12. Health and safety
13. Handling information
14. Infection prevention and control
15. Shadow shift completed

Note: Removed "Safeguarding Children" (Adults Only agency)

### P0 #3: Training Tab - Edit/Verify/Unverify Buttons - COMPLETE
Updated `AuditReadyTrainingMatrix.js`:
- Added **[Edit]** button (pencil icon) - Opens edit dialog for training records
- Added **[Verify]** button (green) - Marks training as verified with audit trail
- Added **[Unverify]** button (amber) - Requires reason, reverts to pending status
- Added **Verified By** column - Shows who verified and when

Backend endpoints:
- `POST /api/employees/{id}/training/{record_id}/verify`
- `POST /api/employees/{id}/training/{record_id}/unverify`

### P0 #4: 2 POA Documents - ALREADY IMPLEMENTED
System already enforces 2 Proof of Address documents requirement:
- Backend: `work_readiness_engine.py` checks `poa_stamped_count >= 2`
- Frontend: Shows "Proof of Address (2 documents required)"

### Key Files Modified
- `/app/frontend/src/components/admin/EditDeclarationsDialog.js` (NEW)
- `/app/frontend/src/components/employee/ApplicationDataPanel.js` - Added Edit button
- `/app/frontend/src/components/training/AuditReadyTrainingMatrix.js` - Edit/Verify/Unverify buttons
- `/app/backend/server.py` - Declarations endpoint + training verify/unverify + 15 Care Certificate standards

### Test Results
- Backend: 100%
- Frontend: 100%
- Test report: `/app/test_reports/iteration_160.json`

---

## COMPLETED: P0 UI Audit Fixes (April 5, 2026)

### P0 Issues Fixed:

1. **Employees List Shows 0 Employees** ✅ FIXED
   - Staff page (`/portal/employees`) now correctly shows 4 employees with onboarding status
   - Endpoint `/api/staff/employees` returns employees with status `onboarding` or `active_employee`

2. **Worker Dashboard Progress Shows 0%** ✅ VERIFIED WORKING
   - Progress shows actual percentages (66%, 62%, 50%, 4%)
   - Calculation based on completed vs required items

3. **Category Grid Shows 0/0** ✅ VERIFIED WORKING
   - Grid shows actual numbers: 3/5 Documents, 0/4 Forms, 4/6 Training, 0/2 References, 1/2 Agreements, 0/14 Induction
   - Data from `/api/employees/{id}/unified-progress` endpoint

4. **Employment History Not Flowing from Application** ✅ FIXED
   - Structured application submission now stores `employment_history` on employee document
   - ApplicationDataPanel fetches from `form_submissions` if not on employee record
   - Shows employment history: Current Healthcare Ltd, Care Home B, Care Home A

5. **DBS Consent Not Flowing from Application** ✅ FIXED
   - Declarations section now checks multiple fields: `declarations.dbs_consent_given`, `dbs_update_service_consent`, `has_dbs_declared`
   - Shows "Consent Given for Enhanced DBS Check" instead of "No consent recorded"

6. **[Approve] Button Appears Before Ready** ✅ FIXED
   - Recruitment page now shows "[X] Blockers" button when applicant has blockers
   - "Approve Recruitment" button ONLY shows when `canApprove=true`
   - Clear separation of button states

7. **Edit Buttons on Declarations** ✅ ALREADY DONE
   - EditDeclarationsDialog implemented in previous session

### Key Files Modified:
- `/app/backend/server.py` - Structured application stores employment_history and declarations on employee (line 28590)
- `/app/frontend/src/pages/portal/RecruitmentPage.js` - Approve button conditional logic
- `/app/frontend/src/components/employee/ApplicationDataPanel.js` - Fetch from form_submissions, updated declarations display

### Test Results:
- Backend: 100%
- Frontend: 100%
- Test report: `/app/test_reports/iteration_161.json`

---

## COMPLETED: P1 UI Fixes (April 5, 2026)

### P1 Issues Fixed:

1. **Missing Nurse Role in Application Form** ✅ FIXED
   - Added "Nurse (Registered)" and "Senior Nurse" to role dropdown
   - Full list: Healthcare Assistant, Senior Healthcare Assistant, Nurse (Registered), Senior Nurse, Care Assistant, Senior Care Assistant, Support Worker, Live-in Carer, Night Carer, Team Leader, Care Coordinator

2. **Gap Explanation Field** ✅ ALREADY EXISTS
   - Textarea appears when "I have gaps in my employment history" checkbox is checked
   - Placeholder: "Please explain any gaps in your employment (e.g., education, caring responsibilities, travel, illness)..."

3. **Bulk Upload for Training Certificates** ✅ FIXED
   - Added "Bulk Upload" button in WorkerDashboard.js
   - data-testid: "bulk-upload-training-btn"
   - Allows workers to upload multiple training certificates at once

4. **Required Field Indicators** ✅ ALREADY EXISTS
   - Red asterisks (*) shown for required fields in WorkerFormPage.js
   - Validation error toast shows missing required fields on submit

5. **Send Reminder Button Text** ✅ ALREADY FIXED
   - All buttons say "Send Reminder" (not "Send to Employee")
   - Verified across AdminActionButtons.js, FormRequirementRow.js, UploadRequirementCard.js, ConsolidatedStatusPanel.js

6. **Recruitment Progress Percentage** ✅ ALREADY EXISTS
   - Shows LabeledProgressBadge with format "Recruitment: X/Y (Z%)"
   - Blocker count displayed for applicants with issues

### Test Results:
- Frontend: 100%
- Test report: `/app/test_reports/iteration_162.json`

---

## COMPLETED: P2 Feature - Competency Assessments UI (April 5, 2026)

### Full CQC-Compliant Competency Management Module

**New Component:** `CompetencyAssessmentsPanel.js`

**Features Implemented:**

1. **Competencies Tab** - New tab in Employee Profile (after Audit tab)

2. **Summary Stats Grid:**
   - Competent (green)
   - Training Required (amber)
   - Not Competent (red)
   - Due Soon (orange when > 0)
   - Overdue (red when > 0)

3. **18 Competency Types:**
   - Critical: Medication Administration, Moving & Handling, Safeguarding Adults, Clinical Competency
   - Standard: Dementia Care, Learning Disabilities, Mental Health, End of Life Care, Catheter Care, Stoma Care, PEG Feeding, Wound Care, Diabetes Management, Epilepsy Management, Parkinson's Care, Choking Management, Challenging Behaviour, Staff Supervision

4. **Assessment Status Options:**
   - Competent (green badge)
   - Not Competent (red badge)
   - Training Required (amber badge)

5. **Review Due Date Tracking:**
   - Default: +1 year from assessment date
   - Amber highlight for due within 30 days
   - Red highlight for overdue

6. **Dialogs:**
   - Add Assessment (competency type, status, review date, notes)
   - Edit Assessment (status, review date, notes - type locked)
   - Assessment History (full audit trail with status changes)

7. **Backend Endpoints (Pre-existing):**
   - `GET /api/employees/{id}/competencies`
   - `POST /api/employees/{id}/competencies`
   - `PUT /api/employees/{id}/competencies/{competency_id}`

### Test Results:
- Backend: 100% (10/10 tests)
- Frontend: 100% (all UI features verified)
- Test report: `/app/test_reports/iteration_163.json`

---

## COMPLETED: P2 Feature - Spot Checks UI (April 5, 2026)

### Full CQC-Compliant Spot Check & Observation Module

**New Component:** `SpotChecksPanel.js`

**Features Implemented:**

1. **Spot Checks Tab** - New tab in Employee Profile (after Competencies tab)

2. **Summary Stats Grid:**
   - Pass (green)
   - Needs Improvement (amber)
   - Fail (red)
   - Follow-ups Soon (orange when > 0)
   - Follow-ups Due (red when > 0)

3. **4 Check Types:**
   - Direct Observation
   - Document Review
   - Competency Check
   - Medication Check

4. **7 Observation Areas:**
   - Moving & Handling
   - Medication Administration
   - Record Keeping
   - Communication
   - Infection Control
   - Dignity & Respect
   - Safeguarding

5. **Outcome Options:**
   - Pass (green badge with checkmark)
   - Needs Improvement (amber badge with warning)
   - Fail (red badge with X)

6. **Follow-up Tracking:**
   - Optional follow-up required checkbox
   - Follow-up date field (conditional)
   - Amber highlight for due within 7 days
   - Red highlight for overdue
   - Soon/Due badges on table rows

7. **Dialogs:**
   - Record Spot Check (type, area, outcome, notes required min 5 chars, follow-up)
   - Edit Spot Check (pre-filled data)

8. **Backend Endpoints:**
   - `GET /api/employees/{id}/spot-checks`
   - `POST /api/employees/{id}/spot-checks`
   - `PUT /api/employees/{id}/spot-checks/{id}` (NEW)
   - `GET /api/spot-check-options`

### Test Results:
- Backend: 100% (14/14 tests)
- Frontend: 100% (all UI features verified)
- Test report: `/app/test_reports/iteration_164.json`

---

## COMPLETED: P2 Feature - Bulk PDF Import UI (April 5, 2026)

### AI-Powered PDF Application Import

**New Components:**
- `BulkImportPanel.js` - Full import UI
- `BulkImportPage.js` - Page wrapper
- Sidebar navigation link at `/portal/bulk-import`

**3-Step Workflow:**

1. **Step 1: Upload PDF Applications**
   - Drag & drop or click-to-upload
   - Multiple PDF files supported
   - File list with remove buttons
   - "Extract Data from X PDFs" button with Sparkles icon

2. **Step 2: Review Extracted Data**
   - Table showing: File, Name, Email, Role, Confidence, Status
   - Confidence badges: High (green), Medium (amber), Low (red)
   - Edit button to correct extracted data
   - Delete button to remove records
   - Select/Deselect All functionality

3. **Step 3: Import as Drafts**
   - Creates employees with `send_magic_link=false`
   - Shows import results with applicant reference numbers
   - Link to Recruitment page for manual magic link sending

**AI Extraction (Gemini 2.5 Flash):**
- Personal details (name, email, phone, DOB, address, NI)
- Role applied for
- Employment history
- References
- Declarations (criminal, health, DBS consent)
- Qualifications

**Backend Endpoint:**
- `POST /api/admin/employees/extract-from-pdf`
- Uses emergentintegrations with EMERGENT_LLM_KEY
- Returns structured JSON with confidence score

### Test Results:
- Backend: 100% (8/8 tests)
- Frontend: 100% (all UI features verified)
- Test report: `/app/test_reports/iteration_165.json`

---

## COMPLETED: P0 Contract Signing Lock + Admin Button Fixes (April 5, 2026)

### P0 #1: Contract Signing - Final Step Only

**Backend Implementation:**
- `can_sign_contract(db, employee_id)` function in `work_readiness_engine.py`
- `can_promote_to_active(db, employee_id)` function
- `GET /api/employees/{id}/can-sign-contract` endpoint

**8 Requirements Before Contract:**
1. DBS Certificate verified with stamp
2. Right to Work verified with stamp
3. Identity document verified with stamp
4. 2 Proof of Address documents verified
5. Both references verified
6. Interview record completed
7. Induction checklist complete (15 items)
8. Mandatory training complete (6 items)

**Worker Dashboard Changes:**
- Contract section shows "Contract Locked" when blockers exist
- Locked button with Lock icon
- Lists remaining requirements (max 5 shown)
- Enables "Sign Contract" only when `can_sign=true`

### P0 #2: Admin Button Fixes

| Blocker | Old Button | New Button |
|---------|-----------|------------|
| Interview | (none) | [Complete Interview] |
| Contract | [Send Contract] | [Locked] badge (removed button) |
| DBS/RTW/Identity/POA | [Record Check] | [Verify with Evidence] |
| Reference 1/2 | [Review] | [Review] (unchanged) |
| Induction | [Start] | [Start] (unchanged) |
| Training | [View Training] | [View Training] (unchanged) |

### P0 #3: Category Grid Labels
Already correct: Documents, Forms, Training, References, Agreements, Induction

### Test Results:
- Backend: 89% (16/18 - 2 failures on unrelated endpoint)
- Frontend: 100% (all P0 features verified)
- Test report: `/app/test_reports/iteration_166.json`

---

## Last Updated
April 5, 2026

---

## COMPLETED: P0 Usability Audit Fixes - April 5, 2026

### P0 Issue 1: Fix "Recruitment Approved" Badge Logic (FIXED)
**Problem:** Badge showed "Recruitment Approved" based solely on `employee.recruitment_approved` flag, even if blockers existed.

**Solution:** Updated `EmployeeProfilePage.js` and `RecruitmentPage.js` to:
1. Check `recruitment_approved` AND zero blockers before showing green "Recruitment Approved" badge
2. Show amber "Conditionally Approved" badge when `recruitment_approved=true` but blockers exist
3. Show amber "Awaiting Approval" badge for applicants not yet approved

**Files Modified:**
- `/app/frontend/src/pages/portal/EmployeeProfilePage.js` - Lines 2844-2873
- `/app/frontend/src/pages/portal/RecruitmentPage.js` - Lines 472-485

### P0 Issue 2: Unified Progress Consistency (FIXED)
**Problem:** Worker Dashboard calculated progress differently than Admin view, causing inconsistent percentages.

**Solution:** Created `compute_unified_progress_internal()` helper function in `server.py` and modified Worker Dashboard endpoint to use it, ensuring both Admin and Worker views share identical progress calculation logic.

**Files Modified:**
- `/app/backend/server.py` - Added `compute_unified_progress_internal()` function around line 7461
- `/app/backend/server.py` - Updated `worker_dashboard` endpoint to use unified progress

**API Changes:**
- Worker dashboard response now includes `unified_blockers` array for consistency

### P0 Issue 3: Audit Trail Logging (VERIFIED WORKING)
**Status:** Already implemented and working. Endpoint `GET /api/employees/{id}/audit-trail` returns comprehensive audit events including:
- Document uploads and verifications
- Reference requests and verifications
- Contract signatures
- Status changes

**Evidence:** API test shows events with action, timestamp, entity_type, and metadata fields.

### P0 Issue 4: Remove Duplicate Content from Admin Compliance View (FIXED)
**Problem:** ConsolidatedStatusPanel showed redundant "STATUS: BLOCKED" prefix.

**Solution:** Simplified status text to show clean "Cannot be promoted yet" or "All requirements complete" messages.

**Files Modified:**
- `/app/frontend/src/components/compliance/ConsolidatedStatusPanel.js` - Lines 260-264

### Bug Fix: Pre-Employment Gates 500 Error (FIXED BY TESTING AGENT)
**Problem:** `GET /api/employees/{id}/pre-employment-gates` returned 500 error due to incorrect function argument order.

**Solution:** Changed import to use `can_promote_to_active_legacy` which has the correct signature `(employee_id, db)` matching existing call sites.

**Files Modified:**
- `/app/backend/server.py` - Lines 94-100 and 10399-10406

### Test Results:
- **Backend:** 100% (12/12 tests passed)
- **Frontend:** 100% (all P0 features verified)
- **Test report:** `/app/test_reports/iteration_167.json`

---

## Next Tasks (Priority Order)

### P1 Tasks (Upcoming)
1. **Training Tab Redesign** - Remove duplicates, consolidate into ONE table, add auto-calculated "Recruitment Compliance Checklist"
2. **Pending Verification Badge** - Add badge to Admin view for items awaiting verification
3. **DBS Register Last Check Column** - Populate "Last DBS Check" data in DBS Register page

### P2 Tasks
1. **Admin Dashboard Task Queue** - Actionable task queue UI for admins
2. **Remove Approve Button Until Ready** - Hide [Approve] button in Recruitment Pipeline until requirements complete

### P3 Tasks (Future/Backlog)
1. **server.py Refactoring** - Split 51k+ lines into modular routers (CRITICAL for maintenance)
2. **Supabase Auth Integration** - Implement RLS policies
3. **MongoDB to PostgreSQL Migration** - Phase out MongoDB
4. **MFA for Admin Accounts** - Implement TOTP-based MFA

---

## P0 Fixes Implemented (April 2026)

### Document Verification Modal (CQC Compliant) ✅
- Created `DocumentVerificationModal` component with:
  - Stamp type selection: Original Seen, Copy Verified, Online Check
  - Proof of check upload (required - screenshot/PDF)
  - Outcome selection: Verified, Information Present, Not Verified
  - Reference number (optional)
  - Notes field
- Backend endpoint: `POST /api/employees/{id}/documents/verify`
- Logs all verifications to audit trail

### Action Buttons Replacement ✅
- Replaced all [Dropdown] buttons with specific action buttons:
  - Interview Record → [Complete Interview]
  - Contract Signed → [Locked] (until 100% complete)
  - DBS, RTW, Identity, POA → [Verify with Evidence]
  - References → [Review]
  - Induction Checklist → [Start]
  - Mandatory Training → [View Training]
  - Health Questionnaire → [Send to Worker]
  - NMC Registration → [View]

### Document Viewer Modal ✅
- Worker dashboard [View] button opens proper document viewer
- Shows document preview (PDF/image)
- Displays verification metadata:
  - Verified status badge
  - Stamp type (Original Document Seen, Copy Verified, Online Check)
  - Upload date
  - Verifier name and date
- Actions: Open in New Tab, Download, Close

### Audit Trail Fixed ✅
- Updated `log_audit_action` to include employee_id in all logs
- Fixed `get_employee_audit_trail` query to search:
  - employee_id field (new format)
  - metadata.employee_id (legacy)
  - entity_id when entity_type is employee
- Audit trail now shows 21+ events per employee

### Verification Metadata Display ✅
- Worker dashboard shows "Verified by Admin User on 4 Apr 2026 • Original Document Seen"
- Only shows "Verified" when actual verification with stamp exists
- Backend returns: verification_stamp_label, verified_by_name, verified_at

### Route Fixes ✅
- Added `/portal/login` → `/login` redirect for backwards compatibility

---

## Known Technical Debt
- **F811 Duplicate Functions:** 140+ lint errors in `server.py` including duplicate function definitions
- **server.py Size:** 51,000+ lines needs splitting into modular routers
- **Bare Except Clauses:** Multiple bare `except:` statements should be replaced with specific exception handling

---

## Phase 2 Fixes Implemented (April 2026)

### Task 1: Training Tab Redesign ✅
- Worker dashboard now shows ALL 6 mandatory trainings with status
- Enhanced training matching for CSTF certificate patterns (safeguarding, manual handling, fire safety, health & safety, BLS, infection control)
- Each training shows: Status (Complete/Pending/Expired), Completion date, Expiry date, Verification status
- Bulk upload button for multiple certificates
- Individual upload button for each training

### Task 2: Induction Checklist ✅
- InductionChecklistPanel added to Competencies tab
- Shows all 15 Care Certificate standards:
  1. Understand your role
  2. Your personal development
  3. Duty of care
  4. Equality and diversity
  5. Work in a person-centred way
  6. Communication
  7. Privacy and dignity
  8. Fluids and nutrition
  9. Awareness of mental health, dementia and learning disabilities
  10. Safeguarding adults
  11. Basic life support
  12. Health and safety
  13. Handling information
  14. Infection prevention and control
  15. Shadow shift completed
- Checkboxes for admin to mark each item complete
- Progress tracking (0/15 Induction)

### Task 3: References Workflow ✅
- Status tracking: Not Declared → Declared → Sent → Response Received → Verified/Rejected
- [Add Referee Details] button for manual entry
- [Send Request] button (sends email to referee)
- [Review Response] modal showing all referee answers
- [Verify] and [Reject] buttons with confirmation modal
- Mismatch handling dropdown:
  - Referee is from earlier employment
  - Referee is personal/professional reference
  - Applicant changed employers since declaration
  - Other (specify in notes)
- Backend endpoint: POST /employees/{id}/references/{num}/verify
- Audit logging for all reference actions

