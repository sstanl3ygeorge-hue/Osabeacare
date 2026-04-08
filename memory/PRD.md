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
- **server.py**: ~44,486 lines (down from ~60,500 originally - **26.5% reduction**)
- **Route modules**: 34 modules with ~316 endpoints extracted
- **Remaining inline endpoints**: ~246 endpoints
- **Testing**: All phases passing (100% success rate)

## Pending/In Progress

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
