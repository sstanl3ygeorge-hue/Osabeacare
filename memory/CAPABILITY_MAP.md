# Requirement Capability Map

## Overview
This document maps all compliance requirements to their capabilities, types, and supported actions.

## Requirement Types

| Type | Description | Example |
|------|-------------|---------|
| `evidence` | Documents uploaded and verified | Right to Work Documents, DBS Certificate, Proof of Address, CV |
| `form` | Forms filled, saved, and verified | Staff Health Questionnaire, Interview Record, HMRC Starter Checklist |
| `hybrid` | Both form submission AND file attachment | Application Form |
| `reference` | Reference lifecycle workflow | Reference 1, Reference 2 |
| `check` | Internal verification check | Right to Work Check, DBS Update Service Check |
| `agreement` | Agreement acknowledgement workflow | Contract Acceptance, Employee Handbook |
| `training` | Training certificates | Safeguarding, Manual Handling, etc. |

## Delivery Modes

| Mode | Description | Send Button | Fill Form Button |
|------|-------------|-------------|------------------|
| `admin_only` | Only admin can fill | No | Yes |
| `employee_sendable` | Can send to employee to complete | Yes | Yes |
| `internal_only` | Internal admin-only process | No | Yes |
| `hybrid` | Both admin fill and send options | Yes | Yes |

## Requirement Capability Matrix

### 1. Legal & Safety (Evidence Requirements)

| Requirement | Type | Delivery Mode | Actions | Affects Readiness |
|-------------|------|---------------|---------|-------------------|
| Right to Work Documents | evidence | hybrid | request, upload, view, download, verify, reject, history, extract, supersede, resend | YES |
| Right to Work Check | check | admin_only | record_check, update_check, history | YES |
| DBS Certificate | evidence | hybrid | request, upload, view, download, verify, reject, history, extract | YES |
| DBS Update Service Check | check | admin_only | record_check, update_check, history | YES |
| Identity Documents | evidence | hybrid | request, upload, view, download, verify, reject, history, extract | YES |
| Proof of Address | evidence | hybrid | request, upload, view, download, verify, reject, history, extract | YES |

### 2. Recruitment Record (Form & Evidence Requirements)

| Requirement | Type | Delivery Mode | Actions | Affects Readiness |
|-------------|------|---------------|---------|-------------------|
| Interview Record | form | admin_only | fill_form, view_submission, export_pdf, verify, history, edit | NO |
| Application Form | hybrid | hybrid | fill_form, view_submission, export_pdf, upload, view, download, history, extract | NO |
| CV / Resume | evidence | hybrid | request, upload, view, download, history, extract | NO |
| Recruitment Compliance Checklist | form | admin_only | fill_form, view_submission, export_pdf, verify, history, edit | NO |

### 3. Health & Competency (Form Requirements)

| Requirement | Type | Delivery Mode | Actions | Affects Readiness |
|-------------|------|---------------|---------|-------------------|
| Staff Health Questionnaire | form | employee_sendable | send, fill_form, view_submission, export_pdf, verify, reject, history | YES |
| Induction & Competency Assessment | form | admin_only | fill_form, view_submission, export_pdf, verify, history, edit | YES |

### 4. Agreements (Agreement Requirements)

| Requirement | Type | Delivery Mode | Actions | Affects Readiness |
|-------------|------|---------------|---------|-------------------|
| Contract Acceptance | agreement | employee_sendable | send, fill_form, view_submission, export_pdf, verify, reject, history | YES |
| Employee Handbook Acknowledgement | agreement | employee_sendable | send, fill_form, view_submission, export_pdf, verify, reject, history | YES |

### 5. Admin Forms (Form Requirements)

| Requirement | Type | Delivery Mode | Actions | Affects Readiness | Optional |
|-------------|------|---------------|---------|-------------------|----------|
| Staff Personal Information | form | employee_sendable | send, fill_form, view_submission, export_pdf, history, edit | NO | NO |
| HMRC Starter Checklist | form | employee_sendable | send, fill_form, view_submission, export_pdf, verify, history | NO | NO |
| Equal Opportunities Monitoring | form | employee_sendable | send, fill_form, view_submission, export_pdf, history | NO | YES |

### 6. References (Reference Requirements)

| Requirement | Type | Delivery Mode | Actions | Affects Readiness |
|-------------|------|---------------|---------|-------------------|
| Reference 1 | reference | employee_sendable | send_request, resend_request, view_response, verify, reject, override_mismatch, request_replacement, change_referee, reset, history | YES |
| Reference 2 | reference | employee_sendable | send_request, resend_request, view_response, verify, reject, override_mismatch, request_replacement, change_referee, reset, history | YES |

## Action Definitions

### Evidence Actions
- `request` - Send request to employee for document
- `upload` - Admin uploads file directly
- `view` - View file(s)
- `download` - Download file(s)
- `verify` - Verify document as valid
- `reject` - Reject document with reason
- `history` - View document history
- `extract` - AI extraction from document
- `supersede` - Mark as superseded by newer version
- `resend` - Resend request to employee

### Form Actions
- `send` - Send form link to employee
- `fill_form` - Admin fills form
- `view_submission` - View submitted form
- `export_pdf` - Export form as PDF
- `verify` - Verify/sign-off form
- `reject` - Reject form with reason
- `history` - View form history
- `edit` - Edit existing submission
- `reopen` - Reopen for editing

## Backend Endpoints

### Evidence Endpoints
- `POST /api/employees/{id}/requirements/{key}/resend-request` - Request document
- `POST /api/employees/{id}/evidence` - Upload evidence
- `GET /api/employees/{id}/requirements/{key}/files` - Get files
- `GET /api/employees/{id}/requirements/{key}/unified-history` - Get history
- `POST /api/employees/{id}/documents/{docId}/verify` - Verify document
- `POST /api/employees/{id}/documents/{docId}/reject` - Reject document
- `POST /api/documents/{docId}/extract` - Extract from document

### Form Endpoints
- `POST /api/employees/{id}/send-form` - Send form to employee
- `GET /api/form-submissions/template/{requirement_id}` - Get form template
- `GET /api/form-submissions/auto-fill/{requirement_id}/{id}` - Get auto-fill data
- `POST /api/form-submissions` - Submit form
- `GET /api/form-submissions/{submissionId}` - Get submission
- `POST /api/form-submissions/{submissionId}/generate-pdf` - Generate PDF
- `GET /api/form-submissions/{submissionId}/download-pdf` - Download PDF
- `POST /api/form-submissions/{submissionId}/verify` - Verify/sign-off
- `POST /api/form-submissions/{submissionId}/unverify` - Reject

### Agreement Endpoints
- `GET /api/agreement-templates` - List templates
- `GET /api/agreement-templates/{template_id}` - Get template
- `POST /api/employees/{id}/agreement-submissions` - Submit agreement
- `GET /api/agreement-submissions/{submissionId}` - Get submission
- `GET /api/agreement-submissions/{submissionId}/pdf` - Export PDF
- `POST /api/agreement-submissions/{submissionId}/verify` - Verify
- `POST /api/agreement-submissions/{submissionId}/reject` - Reject

### Reference Endpoints
- `POST /api/references/{id}/{num}/send-request` - Send request
- `POST /api/references/{id}/{num}/resend-request` - Resend request
- `GET /api/employees/{id}/references-normalized` - Get normalized references
- `POST /api/employees/{id}/verify-reference` - Verify reference
- `POST /api/references/{id}/{num}/reject` - Reject reference
- `POST /api/references/{id}/{num}/override-mismatch` - Override mismatch
- `POST /api/references/{id}/{num}/request-replacement` - Request replacement
- `POST /api/references/{id}/{num}/change-referee` - Change referee
- `POST /api/references/{id}/{num}/reset` - Reset reference

## Implementation Status

### Fully Functional ✅
- DBS Certificate & Check
- Right to Work Documents & Check
- Identity Documents
- Proof of Address
- Staff Health Questionnaire
- Interview Record
- Induction & Competency Assessment
- Application Form
- Recruitment Compliance Checklist
- CV / Resume
- Staff Personal Information
- HMRC Starter Checklist
- Equal Opportunities Monitoring
- Contract Acceptance
- Employee Handbook Acknowledgement
- Reference 1 & 2

### Backend Endpoints Complete ✅
All form-type requirements have complete backend support for:
- Template retrieval
- Auto-fill data
- Submission
- PDF generation
- Verification/Rejection
- History

## Files Changed
- `/app/frontend/src/config/requirementCapabilityMap.js` - NEW capability map
- `/app/frontend/src/components/compliance/FormRequirementRow.js` - NEW form row component
- `/app/frontend/src/components/compliance/DualRowComplianceSection.js` - Updated to render new sections
- `/app/backend/server.py` - Added build_form_row helper and 3 new sections
