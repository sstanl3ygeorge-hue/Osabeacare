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
- Test password configurable via `WORKER_TEST_PASSWORD` env var

### 6. CV Review Flow
- Workers upload CVs (no auto-extraction)
- Admins trigger AI extraction
- Admins can reject with specific reasoning
- Worker notifications for CV status

### 7. Offline PDF Application Form Intake
- Admin uploads scanned/digital PDF application forms
- AI extracts personal details, address, NI number, employment history
- Creates employee record with pre-filled data
- Optional: Sends magic link to worker
- Worker logs in and completes remaining profile via ProfileCompletionWizard

## Architecture

### Backend
- **FastAPI** on port 8001
- **MongoDB** for data storage
- **Supabase Storage** for document hosting
- **APScheduler** for email crons
- **Gemini AI** (via emergentintegrations) for PDF/CV extraction

### Frontend
- **React** with Shadcn/UI components
- **OrgContext** for dynamic organization branding
- **ProfileCompletionWizard** for guided profile completion

### Modular Routes Structure (NEW)
```
/app/backend/routes/
├── __init__.py
├── dependencies.py    - Shared auth utilities (get_current_user, get_db, etc.)
├── auth.py           - 15 endpoints (login, logout, password, magic links)
├── workers.py        - 9 endpoints (worker portal, profile)
├── admin.py          - 6 endpoints (dashboard, system health, audit logs)
├── training.py       - 12 endpoints (training records, certificates)
├── documents.py      - 10 endpoints (document types, categories)
├── recruitment.py    - 10 endpoints (applicants, pipeline)
├── employees.py      - 11 endpoints (employee CRUD)
├── references.py     - 5 endpoints (reference CRUD, status)
└── verification_routes.py - 7 endpoints (document verification)
```

### Key API Endpoints
- `POST /api/worker/request-login` - Magic link request
- `POST /api/worker/verify-login` - Verify magic token
- `GET /api/worker/profile-data` - Get pre-filled profile data
- `GET /api/worker/profile-completion-status` - Check completion status
- `POST /api/admin/employees/extract-from-pdf` - AI PDF extraction
- `POST /api/admin/employees/bulk-import` - Bulk create employees
- `GET /api/references/{employee_id}` - Get employee references
- `GET /api/references/{employee_id}/status` - Get reference status

## What's Been Implemented

### Completed Features (April 2026)
- [x] 5-Step Gated Workflow for RTW/DBS documents
- [x] APScheduler email reminders (30, 14, 7, 1 day before expiry)
- [x] Document Expiry Alerts admin panel
- [x] Dynamic organization branding via OrgContext
- [x] Magic Link primary auth for workers
- [x] Auto account creation on recruitment approval
- [x] CV Review Flow (admin triggers extraction, reject with reason)
- [x] Offline PDF Application Form Intake (BulkImportPanel, AI extraction, ProfileCompletionWizard)

### Server.py Refactoring Progress (April 8, 2026)
- [x] **Phase 1-7**: Extracted 8 route modules (auth, workers, admin, training, documents, recruitment, employees)
- [x] **Phase 8**: Extracted references routes to `routes/references.py` (5 endpoints)
  - Fixed duplicate route collision issue (removed duplicates from references.py)
  - Fixed F821 undefined name errors (EMAIL_FROM -> SENDER_EMAIL)
  - Added missing storage functions (download_file_from_storage, upload_file_to_storage)
- **Current server.py size**: ~58,130 lines (down from ~60,500)
- **Total extracted routes**: ~85 endpoints across 8 modules
- **Testing**: 100% pass rate on iteration_184 (25/25 tests)

## Pending/In Progress

### P1: Continue Server.py Modularization
- [ ] Extract compliance routes (32 endpoints)
- [ ] Extract email/notification routes (28 endpoints)
- [ ] Extract DBS routes (12 endpoints)
- [ ] Extract form/template routes
- [ ] Remove remaining F811 duplicate function definitions

### P3: Future Enhancements
- [ ] Supabase Auth integration with RLS policies
- [ ] MongoDB to PostgreSQL migration
- [ ] MFA (TOTP) for Admin accounts

## Known Issues
- `server.py` still has ~476 routes remaining (needs continued extraction)
- Some lint warnings (E722 bare except, F841 unused variables) - non-critical

## Test Reports
- `/app/test_reports/iteration_183.json` - Mid-refactor regression (100% pass)
- `/app/test_reports/iteration_184.json` - Phase 8 verification (100% pass)

## Test Credentials
- **Admin**: admin@osabea.care / admin123
- **Worker Test Password**: Welcome123! (via WORKER_TEST_PASSWORD env var)

## 3rd Party Integrations
- Supabase (Storage) - User API Key required
- Resend (Email) - User API Key required
- Gemini (AI via emergentintegrations) - Uses Emergent LLM Key
