# CareTrust Compliance Portal - Product Requirements Document

## Original Problem Statement
Build a Requirement-Based Compliance Engine for a Care Recruitment Agency ensuring CQC audit-readiness.

## Core Features

### 1. Two-Tier Work Readiness System
- **Onboarding Tier**: New workers completing compliance requirements
- **Active Employee Tier**: Fully compliant workers cleared to work
- Automatic promotion when all NHS compliance checks pass

### 2. Compliance Tracking
- Professional Registration tracking (NMC) with role-based blockers
- Document management with 5-step gated workflow for RTW/DBS
- CQC-compliant visual stamping on PDFs
- Training certificate tracking with expiry alerts

### 3. Smart Dual-Verification System
- Workers upload evidence documents
- Admins review, fill verification checklists, and digitally stamp

### 4. Email Reminders (APScheduler)
- Automated reminders at 30, 14, 7, 1 days before document/training expiry

### 5. Magic Link Authentication
- Primary auth method for workers
- Password login as optional secondary method

## Architecture

### Modular Routes Structure (13 Modules)
```
/app/backend/routes/
├── __init__.py
├── dependencies.py      - Shared auth utilities
├── auth.py             - 15 endpoints (login, logout, password, magic links)
├── workers.py          - 9 endpoints (worker portal, profile)
├── admin.py            - 6 endpoints (dashboard, system health, audit logs)
├── training.py         - 12 endpoints (training records, certificates)
├── documents.py        - 10 endpoints (document types, categories)
├── recruitment.py      - 10 endpoints (applicants, pipeline)
├── employees.py        - 11 endpoints (employee CRUD)
├── references.py       - 5 endpoints (reference CRUD, status)
├── notifications.py    - 17 endpoints (email service, email requests)
├── compliance.py       - 27 endpoints (policies, insurance, incidents, reports)
├── templates.py        - 5 endpoints (template CRUD)
├── service_users.py    - 10 endpoints (CQC care records, documents)
├── forms.py            - 17 endpoints (form templates, submissions, generated forms) [NEW]
└── verification_routes.py - 7 endpoints (document verification)
```

## Server.py Refactoring Progress (April 8, 2026)

### Completed Phases
- [x] Phase 1-7: Extracted auth, workers, admin, training, documents, recruitment, employees
- [x] Phase 8: Extracted references routes (5 endpoints)
- [x] Phase 9: Extracted email/notification routes (17 endpoints)
- [x] Phase 10: Extracted compliance routes (27 endpoints)
- [x] Phase 11: Extracted templates routes (5 endpoints)
- [x] Phase 12: Extracted service_users routes (10 endpoints)
- [x] Phase 13: Extracted forms routes (17 endpoints) [NEW]

### Current Status
- **server.py**: ~55,942 lines (down from ~60,500 originally - **7.5% reduction**)
- **Route modules**: 13 modules with ~161 endpoints extracted
- **Testing**: 100% pass rate across all phases (27/27 tests in Phase 13)

### Architecture Note
Forms.py routes coexist with server.py routes. Complex routes remain in server.py:
- `/generated-forms/{form_id}/send` - Email form to worker
- `/generated-forms/token/{token}` - Public access
- `/generated-forms/{form_id}/sign` - Employee signature
- `/generated-forms/import-document` - Document import

## Pending/In Progress

### P1: Continue Server.py Modularization
- [ ] Extract DBS routes (~5 endpoints - complex dependencies)
- [ ] Extract employee compliance routes (`/employees/{id}/compliance*`)
- [ ] Remove duplicate routes from server.py after forms extraction
- [ ] Clean up remaining F811 duplicate function definitions

### P3: Future Enhancements
- [ ] Supabase Auth integration with RLS policies
- [ ] MongoDB to PostgreSQL migration
- [ ] MFA (TOTP) for Admin accounts

## Test Reports
- `/app/test_reports/iteration_188.json` - Phase 12 (service_users) verification
- `/app/test_reports/iteration_189.json` - Phase 13 (forms) verification

## Test Credentials
- **Admin**: admin@osabea.care / admin123
- **Worker Test Password**: Welcome123! (via WORKER_TEST_PASSWORD env var)

## 3rd Party Integrations
- Supabase (Storage) - User API Key required
- Resend (Email) - User API Key required
- Gemini (AI via emergentintegrations) - Uses Emergent LLM Key
