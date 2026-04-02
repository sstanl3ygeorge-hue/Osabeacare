# Osabea Care Compliance Portal - PRD

## Original Problem Statement
Build a Requirement-Based Compliance Engine for a Care Recruitment Agency ensuring CQC audit-readiness.

## Core Product Requirements
- **3-tier work readiness**: NOT_READY, READY_WITH_CONDITIONS, READY_TO_WORK
- **Dual-Row Evidence/Check Model**: STRICT separation between uploaded evidence (candidate documents) and verification proof (admin check)

## Current Implementation Status (April 2, 2026)

### ✅ Dual-Row Compliance UI - COMPLETE
For each of: **Right to Work, DBS, Identity, Proof of Address**

**Row A - Evidence** (blue border):
- Upload Evidence button
- Manage button
- View Files / Download
- Shows: file list, upload date, uploaded by, status

**Row B - Verification** (green/amber/red border based on status):
- Upload Verification Proof button
- Record Check button
- View Proof / Download Proof buttons
- Shows: method, checked by, checked at, outcome, notes, proof file

### ✅ CV in Recruitment Record - WORKING
- Shows file with View button when expanded
- Displays upload date and verified status

### ⚠️ Application Form in Recruitment Record
- **Backend fix applied**: Public application now sets `requirement_id: "application_form"` on form_submissions
- **Status recognition**: Backend recognizes `"completed"` status as `awaiting_review`
- **Test limitation**: Current test employee was manually created, not via public application

### Storage Model
| Type | Category | Storage | Display Location |
|------|----------|---------|------------------|
| Candidate document | evidence | employee_documents | Evidence row |
| Admin verification proof | verification_proof | employee_documents | Verification row |
| Form submission | form | form_submissions | Form row |

## Files Changed in This Session
1. `/app/backend/server.py` (Line 21932) - Added `requirement_id: "application_form"` to public application submissions
2. `/app/backend/server.py` (Line 30307) - Updated `is_awaiting_review` to include `"completed"` status
3. `/app/frontend/src/components/compliance/UploadRequirementCard.js` - Dual-Row model implementation
4. `/app/frontend/src/components/compliance/DualRowComplianceSection.js` - Data transformation, CV fix
5. `/app/frontend/src/components/compliance/FormRequirementRow.js` - Evidence file display support
6. `/app/frontend/src/components/compliance/SimplifiedProfileHeader.js` - New clean header
7. `/app/frontend/src/components/compliance/RecruitmentApprovalCard.js` - New approval checklist

## Test Results (Iteration 117)
- ✅ RTW Evidence row with Upload/Manage buttons
- ✅ RTW Verification row with proof file, View/Download buttons
- ✅ DBS Evidence row with 2 files
- ✅ DBS Verification row with DBS Update Service method
- ✅ Identity Evidence/Verification rows
- ✅ Proof of Address Evidence/Verification rows
- ✅ CV row shows file with View button

## Pending Tasks

### P1 - High Priority
- [ ] Integrate SimplifiedProfileHeader into EmployeeProfilePage
- [ ] Integrate RecruitmentApprovalCard into EmployeeProfilePage
- [ ] Employee self-service portal
- [ ] Supabase Auth integration with RLS policies

### P2 - Medium Priority
- [ ] Fix F811 duplicate function definitions in server.py
- [ ] Bulk recurring item creation

### P3 - Low Priority
- [ ] Split server.py into modular routers

## Credentials
- Admin: admin@osabea.care / admin123
- Test Employee: Olakunle Alonge (OCS-0001, d88335f6-1b18-435a-8086-28af4a583f77)
