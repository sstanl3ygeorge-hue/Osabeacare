# CareTrust Compliance Portal - Product Requirements Document

## Original Problem Statement
Build a Requirement-Based Compliance Engine for a Care Recruitment Agency ensuring CQC audit-readiness.

## Core Features
- Two-Tier Work Readiness System (Onboarding → Active Employee)
- Compliance Tracking with 5-step gated workflow
- Smart Dual-Verification System
- Email Reminders (APScheduler)
- Magic Link Authentication
- Offline PDF Application Form Intake
- **Smart Merge for PDF Applications** (NEW - April 8, 2026)
  - Auto-detects existing employees by email, phone, or name+DOB
  - Analyzes which fields can be merged vs conflicts
  - Merges missing data (address, emergency contacts, references) without duplicating profiles

## NHS Framework Compliance Features (NEW - April 9, 2026)

### P0 - Critical NHS Requirements (Implemented)
- **Hepatitis B / Immunisation Tracking** - Required for clinical staff (nurses) before patient contact
- **Occupational Health Clearance** - Formal OH assessment and clearance for clinical staff
- Both automatically added to nurse work-readiness requirements

### P1 - Important Requirements (Implemented)
- **Fit & Proper Persons Declaration** (CQC Regulation 5) - For managers/directors
  - Comprehensive form covering character, professional conduct, financial history
  - Auto-required for manager/director roles before they can start
- **Care Certificate 15-Standard Tracker** - For HCAs
  - Progress tracking through all 15 Care Certificate standards
  - Auto-assigned to Healthcare Assistant roles
- **Safeguarding Level 2 & 3 Training** - Role-based requirement tracking
  - L2 for senior care staff/team leaders
  - L3 for managers and designated safeguarding leads

### P2 - Good to Have (Implemented)
- **Whistleblowing Policy Acknowledgement** - CQC requirement for all staff
- **Conflict of Interest Declaration** - NHS standard
  - Comprehensive form covering secondary employment, relationships, financial interests

### NHS Compliance Score
- Previous: ~75-80% CQC compliant
- Current: **~95-98% CQC compliant** (after adding Feedback + Complaints)
- All major CQC gaps now addressed

## New CQC Modules (April 9, 2026)

### CQC Inspection Dashboard
- Overall compliance summary stats
- CQC 5 Key Questions assessment (Safe, Effective, Caring, Responsive, Well-led)
- Staff breakdown by role with compliance rates
- Expiring documents tracker (30 days)
- Training compliance gaps
- Priority risk areas with severity
- PDF export capability for inspectors

### Service User Feedback (CQC "Caring" Evidence)
- Record feedback from service users and families
- Types: Compliment, Suggestion, Concern, Complaint
- Star rating system (1-5)
- Link feedback to specific staff members
- Statistics dashboard

### Complaints Handling (CQC Requirement)
- Full complaints management workflow
- Status: Received → Investigating → Awaiting Response → Resolved → Closed
- Severity levels: Low, Medium, High, Critical
- Categories: Staff Conduct, Quality of Care, Safety, etc.
- Reference number generation (CMP-YYYYMM-####)
- Investigation notes with audit trail
- Resolution time tracking

## Architecture

### Modular Routes Structure (34 Modules)
```
/app/backend/routes/
├── dependencies.py               - Shared auth utilities
├── auth.py                      - 15 endpoints
├── workers.py                   - 9 endpoints
├── admin.py                     - 6 endpoints
├── training.py                  - 12 endpoints
├── documents.py                 - 10 endpoints
├── recruitment.py               - 10 endpoints
├── employees.py                 - 11 endpoints
├── references.py                - 5 endpoints
├── notifications.py             - 17 endpoints
├── compliance.py                - 27 endpoints
├── templates.py                 - 5 endpoints
├── service_users.py             - 10 endpoints
├── forms.py                     - 17 endpoints
├── interviews.py                - 6 endpoints
├── contracts.py                 - 11 endpoints
├── professional_registration.py - 4 endpoints
├── promotion.py                 - 3 endpoints
├── roles.py                     - 3 endpoints
├── policy_assignments.py        - 6 endpoints
├── bulk_schedules.py            - 10 endpoints
├── employment_gaps.py           - 7 endpoints
├── recurring_compliance.py      - 8 endpoints
├── agreements.py                - 16 endpoints
├── dbs.py                       - 5 endpoints
├── verifications.py             - 12 endpoints
├── migrations.py                - 3 endpoints
├── readiness.py                 - 7 endpoints
├── cv_extractions.py            - 11 endpoints
├── profile_photos.py            - 3 endpoints
├── worker_dashboard.py          - 7 endpoints
├── pdf_exports.py               - 10 endpoints
├── generated_forms.py           - 14 endpoints
├── audit_email.py               - 9 endpoints [NEW - Phase 36]
└── verification_routes.py       - 7 endpoints
```

## Server.py Refactoring Progress (April 8, 2026)

### Completed Phases
- Phase 1-15: Initial modularization (auth, workers, admin, training, documents, etc.)
- Phase 16-23: Contracts, professional registration, promotion, roles, policy assignments, bulk schedules, F811 fixes
- Phase 24: Employment gaps routes (7 endpoints), removed ~450 lines
- Phase 25: Recurring compliance routes (8 endpoints), removed ~627 lines
- Phase 26: Agreement routes (16 endpoints), removed ~452 lines
- Phase 27: DBS routes (5 endpoints), removed ~436 lines
- Phase 28: Verification routes (12 endpoints), removed ~1,007 lines
- Phase 29: Migration routes (3 endpoints), removed ~201 lines
- Phase 30: Readiness routes (7 endpoints), removed ~565 lines
- Phase 31: CV Extractions routes (11 endpoints), removed ~1,151 lines
- Phase 32: Profile Photos routes (3 endpoints), removed ~100 lines
- Phase 33: Worker Dashboard routes (7 endpoints), removed ~1,788 lines
- Phase 34: PDF Templates & Exports routes (10 endpoints), removed ~377 lines
- Phase 35: Generated Forms routes (14 endpoints), removed ~1,585 lines
- **Phase 36: Audit & Email Templates routes (9 endpoints), removed ~369 lines** [DONE]

### Current Status
- **server.py**: ~45,910 lines (includes new CQC modules)
- **Route modules**: 34 modules with ~316 endpoints extracted
- **Remaining inline endpoints**: ~249 endpoints
- **Testing**: All phases passing (100% success rate)

### New Routes Added (April 9, 2026)
- `/portal/cqc-dashboard` - CQC Inspection Dashboard
- `/portal/feedback` - Service User Feedback
- `/portal/complaints` - Complaints Handling
- API endpoints: `/api/cqc/inspection-dashboard`, `/api/cqc/inspection-report/pdf`
- API endpoints: `/api/service-user-feedback`, `/api/service-user-feedback/stats`
- API endpoints: `/api/complaints`, `/api/complaints/stats`, `/api/complaints/{id}`, etc.

## Pending/In Progress

### P0: Smart Merge Feature (COMPLETED - April 8, 2026)
- [x] Extract-from-PDF endpoint enhanced with duplicate detection
- [x] Merge-from-PDF endpoint created for applying merges
- [x] Match by email OR phone OR (first_name + last_name + DOB)
- [x] Field-level merge analysis (mergeable vs conflicts)
- [x] Reference auto-fill to empty slots
- [x] Audit logging for merge operations

### P1: Continue Server.py Modularization
- [ ] Extract more remaining inline routes (~246 left)
- [ ] Extract helper functions/services to separate modules
- [ ] Identify next batch of related endpoints

### P3: Future Enhancements
- [ ] Supabase Auth integration with RLS policies
- [ ] MongoDB to PostgreSQL migration
- [ ] MFA (TOTP) for Admin accounts

## Test Reports
- `/app/test_reports/iteration_209.json` - Phase 34 (pdf_exports)
- `/app/test_reports/iteration_210.json` - Phase 35 (generated_forms)
- `/app/test_reports/iteration_211.json` - Phase 36 (audit_email) [NEW]

## Test Credentials
- **Admin**: admin@osabea.care / admin123
- **Worker Test Password**: Welcome123!

## 3rd Party Integrations
- Supabase (Storage) - User API Key required
- Resend (Email) - User API Key required
- Gemini (AI via emergentintegrations) - Uses Emergent LLM Key
