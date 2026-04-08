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

### 7. Offline PDF Application Form Intake (NEW - April 8, 2026)
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

### Key API Endpoints
- `POST /api/worker/request-login` - Magic link request
- `POST /api/worker/verify-login` - Verify magic token
- `GET /api/worker/profile-data` - Get pre-filled profile data
- `GET /api/worker/profile-completion-status` - Check completion status
- `POST /api/admin/employees/extract-from-pdf` - AI PDF extraction
- `POST /api/admin/employees/bulk-import` - Bulk create employees

## What's Been Implemented

### Completed Features (April 2026)
- [x] 5-Step Gated Workflow for RTW/DBS documents
- [x] APScheduler email reminders (30, 14, 7, 1 day before expiry)
- [x] Document Expiry Alerts admin panel
- [x] Dynamic organization branding via OrgContext
- [x] Magic Link primary auth for workers
- [x] Auto account creation on recruitment approval
- [x] CV Review Flow (admin triggers extraction, reject with reason)
- [x] **Offline PDF Application Form Intake** (NEW)
  - BulkImportPanel with PDF upload
  - AI extraction using Gemini
  - "Send Welcome Emails" option
  - ProfileCompletionWizard for workers

### Pending/In Progress
- [ ] Refactor `server.py` into modular FastAPI routers (P1 - CRITICAL)
- [ ] Supabase Auth integration with RLS policies (P3)
- [ ] MongoDB to PostgreSQL migration (P3)
- [ ] MFA (TOTP) for Admin accounts (P3)

## Known Issues
- `server.py` is critically bloated (>60,000 lines) - causes token exhaustion

## Test Credentials
- **Admin**: admin@osabea.care / admin123
- **Worker Test Password**: Welcome123! (via WORKER_TEST_PASSWORD env var)

## 3rd Party Integrations
- Supabase (Storage) - User API Key required
- Resend (Email) - User API Key required
- Gemini (AI via emergentintegrations) - Uses Emergent LLM Key
