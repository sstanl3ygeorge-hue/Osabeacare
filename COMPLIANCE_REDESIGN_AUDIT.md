# Compliance System Redesign Audit
## Evidence-Based Healthcare Compliance Workflow

**Date**: 2026-03-27  
**Purpose**: Align the system with real healthcare compliance workflows  
**Pilot Employee**: OCS-0001 (Olakunle Alonge)

---

## PART 1: CURRENT STATE ANALYSIS

### Current Requirement Structure (MANDATORY_ITEMS)
```
A_Application_Form     → application_form (form)
A_Application_Form     → cv (document, single file)
B_Recruitment_Checklist → recruitment_checklist (form)
C_Personal_Information → personal_info (form)
D_Interview            → interview_record (form)
E_Equal_Opportunities  → equal_opportunities (form)
F_Health_Screening     → health_screening (form)
G_Identity_RTW         → identity_rtw (document, multi-file) ← PROBLEM: Combines employee docs + internal check
H_References           → reference_1 (document, single file)
H_References           → reference_2 (document, single file)
I_DBS                  → dbs (document, single file) ← PROBLEM: Only certificate, no check slot
J_Induction            → induction (form)
L_Contract             → contract (form)
N_Training             → 6 training items (training type)
O_Other                → handbook (form)
```

### Current Problems Identified

| Issue | Current State | Required State |
|-------|--------------|----------------|
| DBS handling | Single "dbs" slot for certificate only | Separate DBS Certificate + DBS Check |
| Right to Work | Combined "identity_rtw" for all | Separate RTW Documents + RTW Verification |
| References | Single file each | Should allow attachments/pages |
| Forms | Separate from documents | Forms should become evidence documents |
| Training | Can mark complete without evidence | Must require certificate upload |
| Verification | Can verify without evidence | Must have viewable file first |
| Multi-file | Only identity_rtw allows multiple | Most requirements need multiple files |

---

## PART 2: PROPOSED REQUIREMENT STRUCTURE

### New Requirement Categories

```
EMPLOYEE-SUBMITTED EVIDENCE (External source - from employee/third party)
├── cv                          → Employee submits CV
├── identity_documents          → Passport, visa, BRP, driving licence
├── dbs_certificate            → DBS certificate from employee
├── reference_1_documents      → Reference from referee (can be multi-page)
├── reference_2_documents      → Reference from referee (can be multi-page)
├── training_certificates      → Safeguarding cert, Manual Handling cert, etc.
├── health_screening_documents → Health questionnaire + any attachments

INTERNAL VERIFICATION EVIDENCE (Internal source - agency staff)
├── right_to_work_check        → Share code verification, RTW check screenshot
├── dbs_check                  → DBS update service check, validation evidence
├── reference_verification     → Notes on reference verification calls

FORM-GENERATED DOCUMENTS (Internal workflow → becomes evidence)
├── application_form           → Completed application → PDF → evidence
├── recruitment_checklist      → Internal checklist → PDF → evidence
├── personal_info_form         → Completed form → PDF → evidence
├── interview_record           → Interview notes → PDF → evidence
├── equal_opportunities        → Monitoring form → PDF → evidence
├── induction_form             → Induction checklist → PDF → evidence
├── contract_acknowledgement   → Signed contract → PDF → evidence
├── handbook_acknowledgement   → Signed handbook → PDF → evidence
```

### Proposed MANDATORY_ITEMS Structure

```python
MANDATORY_ITEMS = {
    "base": [
        # ======== A. Application & CV ========
        {"id": "application_form", "name": "Application Form", "category": "A_Application", 
         "type": "form-generated", "template_name": "Application Form", 
         "allow_multiple_files": False, "auto_create_evidence": True},
        
        {"id": "cv", "name": "CV / Resume", "category": "A_Application", 
         "type": "document", "source": "employee", 
         "allow_multiple_files": True, "description": "CV and supporting documents"},
        
        # ======== B. Recruitment Checklist ========
        {"id": "recruitment_checklist", "name": "Recruitment Compliance Checklist", 
         "category": "B_Recruitment_Checklist", "type": "form-generated", 
         "template_name": "Recruitment Compliance Checklist", 
         "allow_multiple_files": False, "auto_create_evidence": True,
         "source": "internal", "description": "Internal recruitment tracking"},
        
        # ======== C. Personal Information ========
        {"id": "personal_info", "name": "Personal Information Form", 
         "category": "C_Personal_Information", "type": "form-generated", 
         "template_name": "Personal Information Form",
         "allow_multiple_files": True, "auto_create_evidence": True,
         "description": "Personal details form + any supporting docs"},
        
        # ======== D. Interview ========
        {"id": "interview_record", "name": "Interview Record", "category": "D_Interview",
         "type": "form-generated", "template_name": "Interview Record Form",
         "allow_multiple_files": True, "auto_create_evidence": True,
         "source": "internal", "description": "Interview notes and assessment"},
        
        # ======== E. Equal Opportunities ========
        {"id": "equal_opportunities", "name": "Equal Opportunities Monitoring", 
         "category": "E_Equal_Opportunities", "type": "form-generated",
         "template_name": "Equal Opportunities Monitoring Form",
         "allow_multiple_files": False, "auto_create_evidence": True,
         "description": "Diversity monitoring form"},
        
        # ======== F. Health Screening ========
        {"id": "health_screening", "name": "Health Screening Questionnaire", 
         "category": "F_Health_Screening", "type": "form-generated",
         "template_name": "Health Screening Questionnaire",
         "allow_multiple_files": True, "auto_create_evidence": True,
         "description": "Health questionnaire + medical attachments if needed"},
        
        # ======== G. Identity & Right to Work (SPLIT) ========
        {"id": "identity_documents", "name": "Identity Documents", 
         "category": "G_Identity_RTW", "type": "document", "source": "employee",
         "allow_multiple_files": True, "min_files": 1,
         "description": "Passport, driving licence, or other ID"},
        
        {"id": "right_to_work_documents", "name": "Right to Work Documents", 
         "category": "G_Identity_RTW", "type": "document", "source": "employee",
         "allow_multiple_files": True, "min_files": 1,
         "description": "Visa, BRP, share code, settled status proof"},
        
        {"id": "right_to_work_check", "name": "Right to Work Verification", 
         "category": "G_Identity_RTW", "type": "document", "source": "internal",
         "allow_multiple_files": True,
         "description": "Share code check result, employer checking service screenshot"},
        
        # ======== H. References ========
        {"id": "reference_1", "name": "Reference 1", "category": "H_References",
         "type": "document", "source": "employee",
         "allow_multiple_files": True,
         "description": "First reference letter + any attachments"},
        
        {"id": "reference_2", "name": "Reference 2", "category": "H_References",
         "type": "document", "source": "employee",
         "allow_multiple_files": True,
         "description": "Second reference letter + any attachments"},
        
        # ======== I. DBS (SPLIT) ========
        {"id": "dbs_certificate", "name": "DBS Certificate", "category": "I_DBS",
         "type": "document", "source": "employee",
         "allow_multiple_files": True,
         "description": "DBS certificate from employee"},
        
        {"id": "dbs_check", "name": "DBS Update Service Check", "category": "I_DBS",
         "type": "document", "source": "internal",
         "allow_multiple_files": True,
         "description": "DBS update service check result, validation screenshot"},
        
        # ======== J. Induction ========
        {"id": "induction", "name": "Induction & Competency Assessment", 
         "category": "J_Induction", "type": "form-generated",
         "template_name": "Induction & Competency Assessment",
         "allow_multiple_files": True, "auto_create_evidence": True,
         "description": "Induction checklist, shadowing records, competency signs"},
        
        # ======== L. Contract ========
        {"id": "contract", "name": "Contract Acknowledgement", "category": "L_Contract",
         "type": "form-generated", "template_name": "Contract Acknowledgement Form",
         "allow_multiple_files": True, "auto_create_evidence": True,
         "description": "Signed contract/offer letter"},
        
        # ======== O. Handbook ========
        {"id": "handbook", "name": "Employee Handbook Acknowledgement", 
         "category": "O_Handbook", "type": "form-generated",
         "template_name": "Employee Handbook Acknowledgement",
         "allow_multiple_files": False, "auto_create_evidence": True,
         "description": "Signed handbook acknowledgement"},
    ],
    
    "training": [
        # All training items now have certificate upload support
        {"id": "safeguarding", "name": "Safeguarding Training", "category": "N_Training",
         "type": "training", "allow_multiple_files": True,
         "description": "Safeguarding certificate + transcript if available"},
        
        {"id": "manual_handling", "name": "Manual Handling Training", "category": "N_Training",
         "type": "training", "allow_multiple_files": True,
         "description": "Manual handling certificate"},
        
        {"id": "infection_control", "name": "Infection Control Training", "category": "N_Training",
         "type": "training", "allow_multiple_files": True,
         "description": "Infection control certificate"},
        
        {"id": "bls", "name": "Basic Life Support (BLS)", "category": "N_Training",
         "type": "training", "allow_multiple_files": True,
         "description": "BLS certificate, renewal card"},
        
        {"id": "fire_safety", "name": "Fire Safety Training", "category": "N_Training",
         "type": "training", "allow_multiple_files": True,
         "description": "Fire safety certificate"},
        
        {"id": "health_safety", "name": "Health & Safety Training", "category": "N_Training",
         "type": "training", "allow_multiple_files": True,
         "description": "H&S certificate"},
    ],
    
    "nurse_specific": [
        {"id": "nmc_registration", "name": "NMC Registration", "category": "O_Professional",
         "type": "document", "source": "employee",
         "allow_multiple_files": True,
         "description": "NMC PIN card, registration letter"},
        
        {"id": "clinical_competency", "name": "Clinical Competency Evidence", 
         "category": "N_Training", "type": "document", "source": "employee",
         "allow_multiple_files": True,
         "description": "Clinical competency assessments, skill sign-offs"},
        
        {"id": "medication_competency", "name": "Medication Competency", 
         "category": "N_Training", "type": "training",
         "allow_multiple_files": True,
         "description": "Medication administration competency certificate"},
    ]
}
```

---

## PART 3: REQUIREMENT CLASSIFICATION

### By Evidence Source

| Source | Requirement ID | Description |
|--------|---------------|-------------|
| **Employee** | `cv` | CV submitted by candidate |
| **Employee** | `identity_documents` | Passport, driving licence |
| **Employee** | `right_to_work_documents` | Visa, BRP, share code |
| **Employee** | `reference_1`, `reference_2` | References from referees |
| **Employee** | `dbs_certificate` | DBS certificate from employee |
| **Employee** | `nmc_registration` | NMC registration proof |
| **Employee** | `clinical_competency` | Clinical competency evidence |
| **Internal** | `right_to_work_check` | Agency's RTW verification |
| **Internal** | `dbs_check` | Agency's DBS update service check |
| **Internal** | `recruitment_checklist` | Internal tracking form |
| **Internal** | `interview_record` | Interviewer's notes |
| **Form→Doc** | `application_form` | Completed application → PDF evidence |
| **Form→Doc** | `personal_info` | Personal info form → PDF evidence |
| **Form→Doc** | `equal_opportunities` | EO monitoring → PDF evidence |
| **Form→Doc** | `health_screening` | Health form → PDF evidence |
| **Form→Doc** | `induction` | Induction form → PDF evidence |
| **Form→Doc** | `contract` | Signed contract → PDF evidence |
| **Form→Doc** | `handbook` | Signed handbook → PDF evidence |
| **Training** | `safeguarding`, etc. | Training certificate uploads |

### By Multi-File Requirement

| Requirement | Multi-File? | Reason |
|-------------|-------------|--------|
| `cv` | Yes | CV + cover letter + portfolio |
| `identity_documents` | Yes | Passport + licence |
| `right_to_work_documents` | Yes | Visa + BRP + share code |
| `right_to_work_check` | Yes | Screenshot + notes |
| `reference_1`, `reference_2` | Yes | Multiple pages, attachments |
| `dbs_certificate` | Yes | Certificate + cover letter |
| `dbs_check` | Yes | Check result + screenshot |
| `health_screening` | Yes | Form + medical attachments |
| `induction` | Yes | Checklist + shadowing records |
| `contract` | Yes | Contract + appendices |
| All training | Yes | Certificate + transcript |
| `application_form` | No | Single generated PDF |
| `equal_opportunities` | No | Single form |
| `handbook` | No | Single acknowledgement |

---

## PART 4: COMPLETION LOGIC

### Evidence-Based Completion Rules

```
COMPLETION STATUS CALCULATION:

1. For type="document" or type="training":
   - "missing" = No evidence files uploaded
   - "in_progress" = Has files but not marked complete
   - "completed" = Has at least min_files AND marked complete
   - "verified" = Completed AND admin verified
   
2. For type="form-generated":
   - "missing" = Form not generated
   - "draft" = Form generated but not completed
   - "completed" = Form completed AND evidence PDF created
   - "verified" = Completed AND admin verified
   
3. VERIFICATION RULE (CRITICAL):
   - Can only verify if evidence_files.length > 0
   - Verification = "I reviewed the evidence and confirm it"
   
4. COMPLIANCE SCORE:
   score = (completed_requirements + verified_requirements) / total_requirements
   
   Note: verified counts as completed, so max score = 100%
   Verification is optional but recommended for audit-readiness
```

---

## PART 5: UNIFIED DATA MODEL

### employee_requirements Collection (NEW - Single Source of Truth)

```javascript
{
  "id": "uuid",
  "employee_id": "employee-uuid",
  "requirement_id": "dbs_certificate",  // From MANDATORY_ITEMS
  "requirement_name": "DBS Certificate",
  "requirement_type": "document",  // document | form-generated | training
  "category": "I_DBS",
  "source": "employee",  // employee | internal | form
  
  // Evidence files - THE CORE OF THIS REDESIGN
  "evidence_files": [
    {
      "file_id": "file-uuid",
      "file_url": "path/to/file.pdf",
      "original_filename": "john_dbs_cert.pdf",
      "uploaded_at": "2026-03-27T...",
      "uploaded_by": "user-id",
      "file_label": "DBS Certificate",  // User-defined label
      "source_type": "manual_upload"  // manual_upload | form_submission | imported
    }
  ],
  
  // Status tracking
  "status": "completed",  // missing | draft | in_progress | completed
  "completed_at": "2026-03-27T...",
  "completed_by": "user-id",
  
  // Verification (evidence-based)
  "verified": true,
  "verified_at": "2026-03-27T...",
  "verified_by": "admin-id",
  "verified_by_name": "Admin Name",
  
  // Form linkage (for form-generated types)
  "linked_form_id": "generated-form-uuid",  // If created from form
  
  // Training-specific (for type=training)
  "training_completion_date": "2026-03-27",
  "training_expiry_date": "2027-03-27",
  "completion_method": "certificate",  // certificate | manual
  
  // Metadata
  "notes": "Verified against original",
  "created_at": "2026-03-27T...",
  "updated_at": "2026-03-27T..."
}
```

---

## PART 6: ENDPOINTS TO CHANGE/ADD

### Existing Endpoints to Modify

| Endpoint | Change Required |
|----------|-----------------|
| `GET /employees/{id}/compliance-requirements` | Return evidence_files[] array per requirement |
| `POST /employee-documents/upload-document` | Add to evidence_files[], support multi-file |
| `POST /generated-forms/{id}/complete` | Auto-create evidence document from completed form |
| `POST /training-records/{id}/upload-certificate` | Add certificate to evidence_files[] |
| `POST /training-records/{id}/verify` | Require evidence_files.length > 0 |
| `POST /employee-documents/{id}/verify` | Require file exists |

### New Endpoints Needed

| Endpoint | Purpose |
|----------|---------|
| `POST /employees/{id}/requirements/{req_id}/upload` | Add file to requirement's evidence_files |
| `DELETE /employees/{id}/requirements/{req_id}/files/{file_id}` | Remove specific file |
| `PUT /employees/{id}/requirements/{req_id}/files/{file_id}` | Replace/update file |
| `GET /employees/{id}/requirements/{req_id}/files/{file_id}/view` | View specific file |
| `GET /employees/{id}/requirements/{req_id}/files/{file_id}/download` | Download specific file |

---

## PART 7: MIGRATION PLAN

### Phase 1: Add New Requirements (Non-Breaking)
1. Add `dbs_check` requirement to MANDATORY_ITEMS
2. Add `right_to_work_check` requirement to MANDATORY_ITEMS
3. Split `identity_rtw` into `identity_documents` + `right_to_work_documents`
4. Update compliance calculation to handle new requirements

### Phase 2: Enable Multi-File on All Requirements
1. Update `allow_multiple_files: True` for most requirements
2. Modify upload endpoint to append to evidence_files[] instead of replace
3. Add "Add File" button alongside "Replace" in UI

### Phase 3: Form → Evidence Auto-Conversion
1. Modify form completion endpoint to auto-create evidence document
2. Link generated PDF to requirement's evidence_files[]
3. Remove need for manual "Save as Document" action

### Phase 4: OCS-0001 Pilot Data Migration
1. Map existing documents to new requirement structure
2. Create new requirement records for DBS Check, RTW Check
3. Validate all evidence is accessible from employee profile
4. Test compliance score calculation

### Phase 5: UI Updates
1. Checklist tab: Show evidence_files[] per requirement
2. Add Upload/Add File/View/Download/Verify actions per requirement
3. Training section: Same evidence-based UI as documents
4. Remove confusing separate tabs/views

---

## PART 8: SAFE IMPLEMENTATION PLAN FOR OCS-0001

### Step 1: Backend Changes
```
[ ] Add new requirements to MANDATORY_ITEMS:
    - dbs_check (internal verification)
    - right_to_work_check (internal verification)
    - Rename identity_rtw → identity_documents + right_to_work_documents
    
[ ] Update employee_documents schema to support evidence_files array pattern

[ ] Create unified upload endpoint for any requirement

[ ] Modify form completion to auto-create evidence

[ ] Update compliance calculation for new requirements
```

### Step 2: Data Migration for OCS-0001
```
[ ] Audit current data for OCS-0001:
    - List all existing documents
    - List all completed forms
    - List all training records
    
[ ] Map existing data to new requirement structure:
    - DBS document → dbs_certificate requirement
    - Create empty dbs_check requirement (to be uploaded)
    - RTW documents → right_to_work_documents requirement
    - Create empty right_to_work_check requirement
    
[ ] Convert completed forms to evidence documents:
    - interview_record form → interview_record requirement evidence
    - etc.
```

### Step 3: Frontend Changes
```
[ ] Update Checklist tab to show evidence-based requirements

[ ] Add requirement row actions:
    - Upload / Add File (when multi-file)
    - View / Download (when files exist)
    - Verify (when files exist, not verified)
    - Replace (for single file or replacing latest)
    
[ ] Update compliance score display to show:
    - X of Y requirements have evidence
    - X of Y verified
```

### Step 4: Validation
```
[ ] For OCS-0001, verify:
    - Can upload DBS Certificate
    - Can upload DBS Check separately
    - Can upload RTW Documents
    - Can upload RTW Check separately
    - Can add multiple files to requirements
    - Completed forms appear as evidence
    - Can view/download every file
    - Checklist matches actual evidence
    - Compliance score is accurate
```

---

## PART 9: SUCCESS METRICS FOR OCS-0001

| Test | Expected Result |
|------|-----------------|
| Upload DBS Certificate | Creates evidence under `dbs_certificate` requirement |
| Upload DBS Check | Creates evidence under `dbs_check` requirement (separate) |
| Upload multiple RTW docs | All appear under `right_to_work_documents` |
| Upload RTW verification | Appears under `right_to_work_check` (separate) |
| Complete Interview Form | Auto-creates evidence document visible in checklist |
| Try to verify without file | Should be blocked/disabled |
| View file from checklist | Opens preview with download option |
| Compliance score | Shows X/Y based on requirements with evidence |

---

## APPENDIX: CURRENT vs PROPOSED COMPARISON

### Current: OCS-0001 Requirements (20 items)
```
1. application_form (form)
2. cv (document)
3. recruitment_checklist (form)
4. personal_info (form)
5. interview_record (form)
6. equal_opportunities (form)
7. health_screening (form)
8. identity_rtw (document) ← Combined
9. reference_1 (document)
10. reference_2 (document)
11. dbs (document) ← Only certificate
12. induction (form)
13. contract (form)
14. handbook (form)
15-20. 6 training items
```

### Proposed: OCS-0001 Requirements (24 items)
```
1. application_form (form-generated)
2. cv (document)
3. recruitment_checklist (form-generated)
4. personal_info (form-generated)
5. interview_record (form-generated)
6. equal_opportunities (form-generated)
7. health_screening (form-generated)
8. identity_documents (document, employee) ← Split from identity_rtw
9. right_to_work_documents (document, employee) ← Split from identity_rtw
10. right_to_work_check (document, internal) ← NEW
11. reference_1 (document)
12. reference_2 (document)
13. dbs_certificate (document, employee) ← Renamed from dbs
14. dbs_check (document, internal) ← NEW
15. induction (form-generated)
16. contract (form-generated)
17. handbook (form-generated)
18-23. 6 training items
```

**Note**: Total increases from 20 to 24 requirements for comprehensive compliance tracking.

---

## NEXT STEPS

Please confirm this audit aligns with your operational requirements before I proceed with implementation.

Questions to confirm:
1. Is the split of Identity/RTW into 4 slots correct (identity_documents, right_to_work_documents, right_to_work_check)?
2. Should DBS have 2 slots (dbs_certificate + dbs_check) or more?
3. Are there any other requirements that need internal verification slots?
4. Should compliance score include only "evidence-backed" items or also manual completions?
5. For nurse-specific requirements, any additional splits needed?
