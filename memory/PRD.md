# Osabea Care Compliance Portal - PRD

## Original Problem Statement
Build a Requirement-Based Compliance Engine for a Care Recruitment Agency ensuring CQC audit-readiness. Implement:
- Digital application intake flow
- Strict Applicant vs Employee separation
- Single authoritative 3-tier work readiness logic layer
- NHS-level strict Reference/Referee Integrity workflow
- CV extraction
- Supplementary Training module

## Core Product Requirements
- **3-tier work readiness**: NOT_READY, READY_WITH_CONDITIONS, READY_TO_WORK
- **Dual-Row Evidence/Check Model**: STRICT separation between uploaded evidence (candidate documents) and verification proof (admin check)
- **System Consolidation**: Single source of truth per requirement

## Architecture
```
/app/
├── backend/
│   ├── server.py (Main FastAPI app)
│   ├── stageGates.py (Applicant recruitment logic)
│   ├── supabase_storage.py (Supabase file uploads)
│   └── read_source_switch.py (Feature flags for DB switching)
├── frontend/
│   ├── src/components/compliance/
│   │   ├── UploadRequirementCard.js (Dual-Row UI for RTW/DBS/Identity/PoA)
│   │   ├── DualRowComplianceSection.js (Section container)
│   │   ├── FormRequirementRow.js (Form and evidence rows)
│   │   └── surfaceNormalizers.js (Data transformation)
├── migration/ (Supabase migration scripts)
```

## Key Technical Concepts

### Dual-Row Evidence/Check Model
- **Evidence Row**: Candidate-provided documents stored in `employee_documents` with `category: "evidence"`
- **Verification Row**: Admin verification proof stored separately with `category: "verification_proof"` and linked via `evidence_document_id`

### Storage Model
| Type | Category | Displayed In |
|------|----------|--------------|
| Candidate document | evidence | Evidence row |
| Admin verification proof | verification_proof | Verification row |

## Implemented Features (as of April 2, 2026)

### ✅ Completed
- Public applicant flow with CV upload to Supabase storage
- Admin compliance portal with 3-tier work readiness
- Dual-Row UI for Right to Work, DBS, Identity, Proof of Address
- CV appearing in Recruitment Record with View/Download
- Reference workflow with NHS-level integrity
- Training module with recurring items
- Supabase migration (phases 1-10)
- Railway deployment with Procfile configuration
- Feature flags for read source switching

### UI Components for Dual-Row
Each compliance section (RTW, DBS, Identity, PoA) shows:
- **Row A - Evidence**: Upload/Manage/View/Download files
- **Row B - Verification**: Upload Proof/Record Check/View Proof/Download Proof + check details

## Credentials
- Admin: admin@osabea.care / admin123
- Test Employee: Olakunle Alonge (OCS-0001)

## Pending Tasks

### P1 - High Priority
- [ ] Employee self-service portal
- [ ] Supabase Auth integration with RLS policies
- [ ] Phase out MongoDB entirely

### P2 - Medium Priority
- [ ] Bulk recurring item creation for all employees
- [ ] Fix F811 duplicate function definitions in server.py

### P3 - Low Priority
- [ ] Split server.py (>38k lines) into modular routers

## Deployment
- **Production**: Railway with Supabase (Postgres)
- **Preview**: Emergent with MongoDB

## 3rd Party Integrations
- Resend (Email Notifications) - requires User API Key
- OpenAI GPT-5.2 Vision (CV & Document Extraction) - uses Emergent LLM Key
- Supabase (Database & Storage) - requires User Keys
