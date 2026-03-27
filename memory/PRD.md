# Osabea Care Solutions - Care Recruitment Agency Website & Compliance Portal

## Original Problem Statement
Build a modern public-facing care recruitment website plus a secure internal compliance portal for recruitment, onboarding, employee document tracking, and audit visibility. Make the agency look professional externally and highly organised internally, with a system that is easy to show to local council auditors and supports CQC-ready recruitment and onboarding processes.

## Architecture
- **Backend**: FastAPI with MongoDB, Object Storage for documents
- **Frontend**: React with Tailwind CSS, Shadcn/UI components
- **Authentication**: JWT + Emergent Google OAuth
- **Email**: Resend integration (configured but requires API key)

## User Personas
1. **Super Admin**: Full system access, manage users/branches/templates
2. **Admin/Compliance Officer**: Manage employee records, documents, policies
3. **Branch Manager**: View/manage branch-level employees and records
4. **Employee/Applicant**: Upload documents, acknowledge policies, track progress
5. **Auditor**: Read-only access to compliance dashboards

## Core Requirements (Static)
- Public website: Home, About, Services, Recruitment, Compliance, Contact, Apply Now
- Internal portal: Dashboard, Employees, Documents, Policies, Training, Audit View
- Role-based access control
- Document upload and management with object storage
- Policy assignment and acknowledgement tracking
- Training record management
- Audit logging

## What's Been Implemented (March 2026)

### Public Website
- ✅ Homepage with hero, features, services, recruitment process, compliance section
- ✅ About page with values and approach
- ✅ Services page with care service types
- ✅ Recruitment page with benefits and requirements
- ✅ Compliance page explaining safer recruitment
- ✅ Contact page with form
- ✅ Apply Now with multi-step application form

### Internal Portal
- ✅ Login with JWT email/password and Google OAuth
- ✅ Dashboard with compliance metrics
- ✅ Employee list with filters and search
- ✅ Employee profile with 7 tabs (Overview, Checklist, Documents, Policies, Training, Supervision, Audit Log)
- ✅ Document upload functionality
- ✅ Policy creation and assignment
- ✅ Training record management
- ✅ Audit view for read-only compliance overview
- ✅ 41 document types seeded from care worker checklist

### Backend
- ✅ Complete REST API with 19+ endpoints
- ✅ Auto-generated employee codes (OCS-0001 format)
- ✅ Compliance score calculation
- ✅ Document versioning support
- ✅ Audit logging for all actions

## Prioritized Backlog

### P0 - Critical (Core functionality complete)
- [x] Public website pages
- [x] Authentication system
- [x] Employee CRUD
- [x] Document management
- [x] Policy management

### P1 - Important
- [ ] Email notifications for document requests (requires RESEND_API_KEY)
- [ ] Expiry alerts for documents
- [ ] Bulk policy assignment
- [ ] PDF export of employee compliance summary

### P2 - Nice-to-have
- [ ] Automated reminder emails
- [ ] Digital signatures for forms
- [ ] Branch-specific dashboards
- [ ] Candidate pipeline stages
- [ ] Notes and follow-up tasks

## Next Action Items
1. Add RESEND_API_KEY to enable email notifications
2. Implement document expiry alerts
3. Add bulk operations (document requests, policy assignments)
4. Create PDF export for compliance summaries
5. Add more detailed training matrix view
