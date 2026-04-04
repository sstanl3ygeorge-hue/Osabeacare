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
- [ ] Role-Based Compliance Configuration using `role_compliance_profiles`
- [ ] Supervision Records tracking UI

### P2 (Medium)
- [ ] server.py modular split (currently 47k+ lines) - CRITICAL for maintainability
- [ ] F811 duplicate function cleanup

### P3 (Future)
- [ ] Supabase Auth integration with RLS policies
- [ ] Phase out MongoDB entirely (PostgreSQL migration)

---

## Test Credentials
- Admin: admin@osabea.care / admin123
- Test Employee: isg1994@outlook.com (Ifedolapo George) - active_employee status

## Database
- Production: Railway MongoDB (`caretrust_production`)
- Connection string in `/app/backend/.env` (MONGO_URL)

---

## Last Updated
December 4, 2025 - Worker Portal complete implementation with save/resume forms, auto-promotion, and email notifications
