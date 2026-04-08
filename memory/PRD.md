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

### Modular Routes Structure (16 Modules)
```
/app/backend/routes/
├── dependencies.py      - Shared auth utilities
├── auth.py             - 15 endpoints
├── workers.py          - 9 endpoints
├── admin.py            - 6 endpoints
├── training.py         - 12 endpoints
├── documents.py        - 10 endpoints
├── recruitment.py      - 10 endpoints
├── employees.py        - 11 endpoints
├── references.py       - 5 endpoints
├── notifications.py    - 17 endpoints
├── compliance.py       - 27 endpoints
├── templates.py        - 5 endpoints
├── service_users.py    - 10 endpoints
├── forms.py            - 17 endpoints
├── interviews.py       - 6 endpoints
├── contracts.py        - 11 endpoints [NEW]
└── verification_routes.py - 7 endpoints
```

## Server.py Refactoring Progress (April 8, 2026)

### Completed Phases
- Phase 1-7: Extracted auth, workers, admin, training, documents, recruitment, employees
- Phase 8: Extracted references routes (5 endpoints)
- Phase 9: Extracted email/notification routes (17 endpoints)
- Phase 10: Extracted compliance routes (27 endpoints)
- Phase 11: Extracted templates routes (5 endpoints)
- Phase 12: Extracted service_users routes (10 endpoints)
- Phase 13: Extracted forms routes (17 endpoints)
- Phase 14: Removed duplicate form routes (~652 lines)
- Phase 15: Extracted interviews routes (6 endpoints), removed duplicates (~462 lines)
- **Phase 16: Extracted contracts routes (11 endpoints), removed duplicates (~293 lines)** [DONE]

### Current Status
- **server.py**: ~54,535 lines (down from ~60,500 originally - **9.9% reduction**)
- **Route modules**: 16 modules with ~178 endpoints extracted
- **Testing**: 100% pass rate (27/27 tests in Phase 16)

## Pending/In Progress

### P1: Continue Server.py Modularization
- [ ] Extract DBS routes (~5 endpoints - complex dependencies)
- [ ] Extract employee compliance routes (`/employees/{id}/compliance*`)
- [ ] Extract advanced compliance routes (professional registration, etc.)
- [ ] Clean up remaining F811 duplicate function definitions

### P3: Future Enhancements
- [ ] Supabase Auth integration with RLS policies
- [ ] MongoDB to PostgreSQL migration
- [ ] MFA (TOTP) for Admin accounts

## Test Reports
- `/app/test_reports/iteration_190.json` - Phase 14 (form cleanup)
- `/app/test_reports/iteration_191.json` - Phase 15 (interviews extraction)
- `/app/test_reports/iteration_192.json` - Phase 16 (contracts extraction) [NEW]

## Test Credentials
- **Admin**: admin@osabea.care / admin123
- **Worker Test Password**: Welcome123!

## 3rd Party Integrations
- Supabase (Storage) - User API Key required
- Resend (Email) - User API Key required
- Gemini (AI via emergentintegrations) - Uses Emergent LLM Key
