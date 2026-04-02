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
- [x] Right to Work, DBS, Identity sections with dual-row

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

## Key Files
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

## Prioritized Backlog

### P0 (Critical)
- [ ] User verification of email in inbox (pending)
- [ ] GitHub push after verification

### P1 (High)
- [ ] Employee self-service portal
- [ ] Supabase Auth integration and RLS policies

### P2 (Medium)
- [ ] Bulk recurring item creation
- [ ] Split server.py into modular routers
- [ ] Fix F811 linting errors

### P3 (Low/Future)
- [ ] Phase out MongoDB entirely
- [ ] Production deployment optimizations

## Test Credentials
- Admin: admin@osabea.care / admin123
- Test Employee: d88335f6-1b18-435a-8086-28af4a583f77

## API Endpoints
- `POST /api/employees/{id}/request-document?requirement_id={id}` - Send document request email
- `POST /api/email-requests/{id}/track-click` - Track email CTA clicks
- `GET /api/employees/{id}/training-matrix` - Get training items and additional items
- `GET /api/employees/{id}/compliance-requirements` - Get all compliance requirements

## Last Updated
April 2, 2026 - Visual proof screenshots completed, email flow verified via API
