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
- [ ] Role-Based Compliance Configuration using `role_compliance_profiles`
- [ ] Supervision Records tracking UI

### P2 (Medium)
- [ ] server.py modular split (currently 48k+ lines) - CRITICAL for maintainability
- [ ] F811 duplicate function cleanup
- [ ] MFA for admin accounts (RECOMMENDED)

### P3 (Future)
- [ ] Supabase Auth integration with RLS policies
- [ ] Phase out MongoDB entirely (PostgreSQL migration)

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
