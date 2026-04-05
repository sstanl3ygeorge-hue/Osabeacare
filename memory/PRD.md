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

### Bug 3: Multiple Conflicting Progress Numbers
- **Issue**: Different pages showed 2/11, 15%, 50%, 33%, etc.
- **Clarification**: These are INTENTIONALLY different:
  - `2/11` = 11-item recruitment approval checklist (gates for promotion)
  - `24%` = Unified overall compliance (all requirements)
  - `66%` = Work readiness (subset of critical items)
- **Recommendation**: Add tooltips/labels to clarify which number is which

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

## Last Updated
April 5, 2026 - Admin UX Audit completed - removed duplicate content from tabs, clarified progress labels, added NHS-standard document guidance
