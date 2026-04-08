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
- Manual "Send All Reminders" trigger in admin dashboard

### 5. Magic Link Authentication
- Primary auth method for workers
- Password login as optional secondary method

### 6. Offline PDF Application Form Intake
- Admin uploads scanned/digital PDF application forms
- AI extracts personal details, address, NI number, employment history
- Creates employee record with pre-filled data
- Optional: Sends magic link to worker

## Architecture

### Backend
- **FastAPI** on port 8001
- **MongoDB** for data storage
- **Supabase Storage** for document hosting
- **APScheduler** for email crons
- **Gemini AI** (via emergentintegrations) for PDF/CV extraction

### Modular Routes Structure
```
/app/backend/routes/
├── __init__.py
├── dependencies.py     - Shared auth utilities
├── auth.py            - 15 endpoints (login, logout, password, magic links)
├── workers.py         - 9 endpoints (worker portal, profile)
├── admin.py           - 6 endpoints (dashboard, system health, audit logs)
├── training.py        - 12 endpoints (training records, certificates)
├── documents.py       - 10 endpoints (document types, categories)
├── recruitment.py     - 10 endpoints (applicants, pipeline)
├── employees.py       - 11 endpoints (employee CRUD)
├── references.py      - 5 endpoints (reference CRUD, status)
├── notifications.py   - 17 endpoints (email service, email requests)
├── compliance.py      - 27 endpoints (policies, insurance, incidents, reports) [NEW]
└── verification_routes.py - 7 endpoints (document verification)
```

## What's Been Implemented

### Server.py Refactoring Progress (April 8, 2026)
- [x] **Phase 1-7**: Extracted auth, workers, admin, training, documents, recruitment, employees
- [x] **Phase 8**: Extracted references routes (5 endpoints)
- [x] **Phase 9**: Extracted email/notification routes (17 endpoints)
- [x] **Phase 10**: Extracted compliance routes (27 endpoints) [NEW]
  - Policies management (CRUD, upload, review tracking, audit trail)
  - Insurance/certificates management (CRUD, upload, expiry tracking)
  - Incident logs management (CRUD, audit trail)
  - Compliance reports (staff-dbs, training)

**Current Status:**
- `server.py`: ~56,485 lines (down from ~60,500 originally)
- Route modules: 10 modules with ~129 endpoints extracted
- Testing: 100% pass rate (iteration_186: 29/29 tests)

### Routes Still in server.py (Not Duplicated)
- `/compliance/dashboard` - Compliance overview dashboard
- `/compliance/centre-summary` - Centre compliance summary
- `/compliance/cqc-evidence-map` - CQC evidence mapping
- `/compliance/name-mismatches` - Name mismatch detection

## Pending/In Progress

### P1: Continue Server.py Modularization
- [ ] Extract DBS routes (~12 endpoints)
- [ ] Extract employee compliance routes (`/employees/{id}/compliance*`)
- [ ] Extract service user routes
- [ ] Clean up remaining F811 duplicate function definitions

### P3: Future Enhancements
- [ ] Supabase Auth integration with RLS policies
- [ ] MongoDB to PostgreSQL migration
- [ ] MFA (TOTP) for Admin accounts

## Test Reports
- `/app/test_reports/iteration_185.json` - Phase 9 verification (100% pass)
- `/app/test_reports/iteration_186.json` - Phase 10 verification (100% pass)

## Test Credentials
- **Admin**: admin@osabea.care / admin123
- **Worker Test Password**: Welcome123! (via WORKER_TEST_PASSWORD env var)

## 3rd Party Integrations
- Supabase (Storage) - User API Key required
- Resend (Email) - User API Key required
- Gemini (AI via emergentintegrations) - Uses Emergent LLM Key
