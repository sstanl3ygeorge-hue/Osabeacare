# Care Recruitment Agency Compliance Portal - PRD

## Company
**Osabea Healthcare Solutions**

## Original Problem Statement
Build a comprehensive compliance management portal for a UK care recruitment agency to:
- Manage employee onboarding and compliance documents
- Track training and policy acknowledgements
- Generate and manage compliance forms with digital signatures
- Support CQC audit requirements

## User Personas
1. **Super Admin**: Full system access, manages all employees and compliance
2. **Manager**: Manages team compliance, reviews documents
3. **Auditor**: Read-only access for compliance audits
4. **Employee**: Completes assigned forms (future portal)

## Core Requirements

### Completed Features ✅

#### Phase 1: Foundation (Completed 2026-03-27)
- [x] React + FastAPI + MongoDB full-stack architecture
- [x] JWT + Google OAuth authentication via Emergent Auth
- [x] Employee records management (CRUD)
- [x] Object storage integration for documents
- [x] Document types and compliance tracking
- [x] Policy management with version control
- [x] Training records tracking
- [x] Audit logging for all actions
- [x] Public website with services, about, careers pages
- [x] Responsive design with Shadcn/UI components

#### Phase 2: Template Library & Document Control (Completed 2026-03-27)
- [x] **13 Compliance Templates** (role-aware for HCA vs Nurse):
  - Application Form
  - Interview Record Form
  - Recruitment Compliance Checklist
  - Health Screening Questionnaire (restricted)
  - Induction & Competency Assessment
  - Contract Acknowledgement Form
  - Personal Information Form
  - Equal Opportunities Monitoring Form (confidential)
  - Supervision Record
  - Annual Appraisal Form
  - Reference Request & Verification Form
  - DBS Review & Risk Assessment
  - **Employee Handbook Acknowledgement** (NEW)
- [x] **Form Generation System** with auto-fill, role-based fields, status workflow
- [x] **Digital Signatures** (typed + canvas drawn)
- [x] **Bulk Operations** (bulk upload, bulk form generation)
- [x] **PDF Export** for forms
- [x] **Visibility Controls** (normal/restricted/confidential)
- [x] **Email Templates** for common communications:
  - Document Request
  - Right to Work Request
  - Form Completion Request
  - Onboarding Complete
  - Missing Items Follow-up
  - Expiry Reminder
  - Form Signed Off

#### Phase 2.5: Training & Compliance Overview (Completed 2026-03-27)
- [x] **Compliance Overview Component** on employee profiles
- [x] **9 Key Compliance Items Tracked**:
  - Safeguarding Training
  - Manual Handling
  - Infection Control
  - Basic Life Support (BLS)
  - Medication Training (Nurse-only)
  - DBS Check
  - Right to Work
  - Induction Completed
  - Policies Acknowledgement
- [x] **Status Indicators**: Complete (green), Expiring (amber), Pending (blue), Missing (red), N/A (gray)
- [x] **Expiry Date Display** when applicable
- [x] **Last Updated Date Display**
- [x] **Role-Based Logic**: Medication Training shows N/A for Healthcare Assistants
- [x] **Overall Compliance Progress Bar** with color-coded segments

### Upcoming Features (P0)
- [ ] PDF generation backend (server-side PDF for archival)
- [ ] Email notifications via Resend for form requests
- [ ] Document expiry reminders

### Backlog (P1-P2)
- [ ] Bulk document requests
- [ ] Bulk policy assignment
- [ ] Employee self-service portal
- [ ] Mobile app consideration
- [ ] Advanced reporting dashboard

## Technical Architecture

```
/app/
├── backend/
│   ├── server.py          # FastAPI application
│   ├── templates_data.py  # 12 template definitions
│   ├── requirements.txt   # Python dependencies
│   └── .env              # Environment variables
├── frontend/
│   ├── src/
│   │   ├── App.js        # React Router setup
│   │   ├── context/      # AuthContext
│   │   ├── components/
│   │   │   ├── portal/   # SignaturePad, FormFieldRenderer, PortalLayout
│   │   │   └── ui/       # Shadcn components
│   │   └── pages/
│   │       ├── portal/   # Dashboard, Employees, Templates, FormEditor
│   │       └── public/   # Website pages
│   └── package.json
└── memory/
    └── PRD.md
```

## Key API Endpoints

### Templates
- `GET /api/templates` - List all templates
- `POST /api/seed-templates` - Seed 12 compliance templates
- `GET /api/templates/:id` - Get template details with form fields

### Generated Forms
- `POST /api/generated-forms` - Create form for employee
- `GET /api/generated-forms` - List forms (filter by employee_id)
- `PUT /api/generated-forms/:id` - Update form data/status
- `POST /api/generated-forms/bulk` - Bulk generate forms
- `POST /api/generated-forms/:id/signoff` - Admin sign-off (locks form)
- `POST /api/generated-forms/:id/send` - Send to employee

### Documents
- `POST /api/employees/:id/bulk-upload` - Bulk document upload
- `POST /api/employee-documents/:id/upload` - Single document upload

## Database Collections

### employees
```javascript
{
  id, employee_code, first_name, last_name, email, phone,
  role: "Healthcare Assistant" | "Nurse" | "Care Assistant" | ...,
  assignment: "Unassigned" | "Sunrise Care Home" | "...",  // Current placement
  status: "new" | "screening" | "interview" | "onboarding" | "active" | "inactive",
  completion_percentage, created_at, updated_at
}
```

### templates
```javascript
{
  id, name, description, category, section,
  visibility: "normal" | "restricted" | "confidential",
  role_specific: null | "Nurse" | "Healthcare Assistant",
  form_fields: [...],
  requires_employee_signature, requires_admin_signature,
  active, version, created_at, updated_at
}
```

### generated_forms
```javascript
{
  id, template_id, template_name, template_category,
  employee_id, employee_name, employee_code,
  form_data: {...},
  status: "draft" | "sent" | "in_progress" | "completed" | "reviewed" | "signed_off" | "archived",
  employee_signature, employee_signed_at,
  admin_signature, admin_signed_at, admin_signoff_by,
  locked: boolean,
  version, access_token,
  created_at, updated_at, sent_at, viewed_at, completed_at, signed_off_at
}
```

## Credentials

### Demo Admin
- Email: admin@osabea.care
- Password: admin123
- Role: super_admin

### Test Employees
- Sarah Thompson (OCS-0005) - Nurse - London
- Michael Brown (OCS-0006) - Healthcare Assistant - Manchester

## Last Updated
2026-03-27 - Template Library & Document Control workflow completed
