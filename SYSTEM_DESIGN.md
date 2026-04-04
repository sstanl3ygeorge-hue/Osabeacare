# Osabea Healthcare Compliance Platform - System Design Document

## Overview

A CQC audit-ready compliance management system for UK healthcare recruitment agencies. Built with React + FastAPI + MongoDB.

**Live Preview**: https://caretrust-portal.preview.emergentagent.com
**Repository**: github.com/sstanl3ygeorge-hue/Osabeacare

---

## 1. Database Schema (MongoDB)

### Core Collections

#### `users`
```javascript
{
  id: "uuid",
  email: "string",
  password_hash: "string",
  role: "admin" | "manager" | "viewer",
  first_name: "string",
  last_name: "string",
  created_at: "datetime",
  last_login: "datetime"
}
```

#### `employees`
```javascript
{
  id: "uuid",
  first_name: "string",
  last_name: "string",
  email: "string",
  phone: "string",
  date_of_birth: "date",
  address: {
    line1: "string",
    line2: "string",
    city: "string",
    postcode: "string"
  },
  role: "string",  // Job title
  department: "string",
  status: "applicant" | "employee" | "inactive",
  employment_type: "full_time" | "part_time" | "bank",
  start_date: "date",
  
  // Work Readiness (computed)
  work_readiness: "NOT_READY" | "READY_WITH_CONDITIONS" | "READY_TO_WORK",
  compliance_status: "compliant" | "non_compliant" | "pending",
  
  created_at: "datetime",
  updated_at: "datetime"
}
```

### Evidence Collections

#### `employee_documents`
```javascript
{
  id: "uuid",
  employee_id: "uuid",
  requirement_type: "right_to_work" | "dbs" | "identity" | "proof_of_address" | "references" | "training" | "health",
  
  // File info
  file_name: "string",
  original_filename: "string",
  file_url: "string",
  content_type: "string",
  file_size: "number",
  
  // Status
  status: "received" | "pending_review" | "accepted" | "rejected" | "superseded",
  verification_stamp: "original_verified" | "copy_verified" | "online_verified" | null,
  
  // Metadata
  uploaded_by: "uuid",
  uploaded_at: "datetime",
  reviewed_by: "uuid",
  reviewed_at: "datetime",
  notes: "string",
  
  // AI extraction results
  extraction_data: {
    fields: {},
    confidence: "number",
    extracted_at: "datetime"
  }
}
```

### Verification Check Collections

#### `rtw_checks` (Right to Work)
```javascript
{
  id: "uuid",
  employee_id: "uuid",
  
  // Check details
  method: "home_office_online_check" | "manual_passport_uk_irish" | "manual_list_a_check" | "manual_list_b_group_1_check" | "manual_list_b_group_2_check" | "ecs_check" | "idsp_check",
  checked_at: "date",
  checked_by: "uuid",
  checked_by_name: "string",
  outcome: "verified" | "failed" | "needs_more_info",
  
  // Result data
  permission_type: "string",  // e.g., "British Citizen", "Skilled Worker Visa"
  permission_start_date: "date",
  permission_end_date: "date",
  is_indefinite: "boolean",
  share_code: "string",
  reference_number: "string",
  restrictions: "string",
  hours_limit: "number",
  
  // Follow-up
  follow_up_required: "boolean",
  follow_up_due_at: "date",
  
  // Linked evidence
  evidence_document_id: "uuid",
  notes: "string",
  
  created_at: "datetime",
  updated_at: "datetime",
  superseded_at: "datetime"  // null = current
}
```

#### `dbs_checks`
```javascript
{
  id: "uuid",
  employee_id: "uuid",
  
  // Check details
  method: "manual_certificate_review" | "update_service_check",
  checked_at: "date",
  checked_by: "uuid",
  outcome: "verified" | "failed",
  
  // Certificate details
  certificate_number: "string",  // 12 digits
  dbs_level: "basic" | "standard" | "enhanced" | "enhanced_barred",
  certificate_issue_date: "date",
  name_on_certificate: "string",
  workforce: "adult" | "child" | "adult_and_child",
  
  // Result
  result_status: "clear" | "information_present",
  information_present: "boolean",
  result_summary: "string",
  
  // Update Service
  update_service_registered: "boolean",
  update_service_status: "active" | "not_registered" | "expired",
  last_status_check_date: "date",
  update_service_check_result: "no_change" | "changed",
  
  // Policy-based recheck (DBS has no statutory expiry)
  recheck_required: "boolean",
  next_recheck_date: "date",  // Typically 3 years from issue
  
  evidence_document_id: "uuid",
  notes: "string",
  created_at: "datetime"
}
```

#### `identity_checks`
```javascript
{
  id: "uuid",
  employee_id: "uuid",
  
  method: "original_document_seen" | "copy_verified" | "digital_id_verification",
  checked_at: "date",
  checked_by: "uuid",
  outcome: "verified" | "failed",
  
  // Document details
  document_type: "passport" | "driving_licence" | "national_id",
  full_name_on_document: "string",
  date_of_birth: "date",
  document_number: "string",
  issue_date: "date",
  expiry_date: "date",
  nationality: "string",
  
  // Verification checks
  name_matches_application: "boolean",
  dob_matches_application: "boolean",
  photo_match_confirmed: "boolean",
  
  evidence_document_id: "uuid",
  notes: "string",
  created_at: "datetime"
}
```

#### `address_checks`
```javascript
{
  id: "uuid",
  employee_id: "uuid",
  
  method: "original_document_seen" | "uploaded_copy_reviewed",
  checked_at: "date",
  checked_by: "uuid",
  outcome: "verified" | "failed",
  
  // Requirements
  documents_received_count: "number",
  documents_required_count: "number",  // Default: 2
  
  // Verified documents array
  verified_documents: [
    {
      type: "utility_bill" | "bank_statement" | "council_tax" | "hmrc_letter" | "tenancy_agreement",
      issue_date: "date",
      months_old: "number",
      max_age_months: "number",  // 3 for utility/bank, 6 for council tax
      is_valid: "boolean",
      recency_status: "valid" | "expired"
    }
  ],
  
  // Extracted address
  extracted_address_line1: "string",
  extracted_address_line2: "string",
  extracted_city: "string",
  extracted_postcode: "string",
  
  // Validation
  address_matches_application: "boolean",
  all_documents_sufficiently_recent: "boolean",
  
  evidence_document_id: "uuid",
  notes: "string",
  created_at: "datetime"
}
```

#### `references`
```javascript
{
  id: "uuid",
  employee_id: "uuid",
  
  // Referee details
  referee_name: "string",
  referee_email: "string",
  referee_phone: "string",
  referee_job_title: "string",
  referee_organization: "string",
  relationship: "line_manager" | "hr" | "colleague" | "professional",
  
  // Employment being referenced
  employment_start: "date",
  employment_end: "date",
  job_title: "string",
  
  // Request tracking
  request_sent_at: "datetime",
  reminder_sent_at: "datetime",
  
  // Response
  status: "pending" | "received" | "verified" | "discrepancy" | "declined",
  response_received_at: "datetime",
  
  // Verification
  verified_by: "uuid",
  verified_at: "datetime",
  verification_method: "email" | "phone" | "written",
  
  // Reference content
  reference_text: "string",
  would_rehire: "boolean",
  reason_for_leaving: "string",
  
  notes: "string",
  created_at: "datetime"
}
```

### Training Collections

#### `training_records`
```javascript
{
  id: "uuid",
  employee_id: "uuid",
  training_type_id: "uuid",
  
  // Completion
  completed_at: "date",
  expiry_date: "date",
  
  // Certificate
  certificate_document_id: "uuid",
  certificate_number: "string",
  
  // Provider
  provider: "string",
  
  status: "valid" | "expiring_soon" | "expired" | "not_completed",
  created_at: "datetime"
}
```

#### `training_types`
```javascript
{
  id: "uuid",
  name: "string",  // e.g., "Manual Handling", "Safeguarding Adults"
  category: "mandatory" | "role_specific" | "optional",
  validity_months: "number",  // e.g., 12, 24, 36
  required_for_roles: ["string"],  // Job titles that require this
  
  created_at: "datetime"
}
```

---

## 2. Compliance Rules Engine

### Location
`/app/backend/compliance_engine/`

### Structure
```
compliance_engine/
├── __init__.py          # Exports
├── models.py            # Pydantic models (RequirementType, Evidence, Verification, etc.)
├── rule_packs.py        # Requirement-specific rules (RTW, DBS, Identity, POA)
├── engine.py            # ComplianceEngine, StatusEngine, BlockerEngine
├── labels.py            # Human-readable labels for all statuses
└── extraction.py        # Gemini Vision document extraction
```

### Rule Packs

Each requirement type has its own rule pack defining:
- Required fields
- Validation rules
- Status computation logic
- Expiry/follow-up thresholds

```python
class RTWRulePack(BaseRulePack):
    requirement_type = RequirementType.RIGHT_TO_WORK
    blocks_readiness = True
    
    EXPIRY_THRESHOLDS = {
        "green": 180,      # > 180 days: all good
        "amber": 90,       # 90-180 days: approaching
        "red": 30,         # < 30 days: urgent
    }
    
    def compute_status(self, verification_outcome, result_data, evidence_count):
        # Returns: status, status_label, status_color, alerts, is_blocking
```

### Computed States
```python
class ComputedState(Enum):
    MISSING = "missing"
    AWAITING_UPLOAD = "awaiting_upload"
    AWAITING_REVIEW = "awaiting_review"
    VERIFICATION_PENDING = "verification_pending"
    VERIFIED = "verified"
    WARNING = "warning"
    EXPIRED = "expired"
    INCOMPLETE = "incomplete"
```

---

## 3. Worker Status Calculation Logic

### 3-Tier Work Readiness Model

```python
def calculate_work_readiness(employee_id):
    """
    Returns: NOT_READY | READY_WITH_CONDITIONS | READY_TO_WORK
    """
    
    # Get all requirement statuses
    rtw = get_rtw_status(employee_id)      # Must be verified
    dbs = get_dbs_status(employee_id)      # Must be verified
    identity = get_identity_status(employee_id)  # Must be verified
    address = get_address_status(employee_id)    # Must be verified (2 docs)
    references = get_references_status(employee_id)  # 2 required
    training = get_mandatory_training_status(employee_id)
    
    # Blockers = requirements that MUST be complete
    blockers = []
    if not rtw.is_verified:
        blockers.append("Right to Work not verified")
    if not dbs.is_verified:
        blockers.append("DBS check not verified")
    if not identity.is_verified:
        blockers.append("Identity not verified")
    if not address.is_verified:
        blockers.append("Proof of Address incomplete")
    
    # Warnings = approaching expiry or conditions
    warnings = []
    if rtw.days_until_expiry < 90:
        warnings.append(f"RTW expires in {rtw.days_until_expiry} days")
    if dbs.days_until_recheck < 90:
        warnings.append(f"DBS recheck due in {dbs.days_until_recheck} days")
    if rtw.has_restrictions:
        warnings.append(f"Work restrictions: {rtw.restrictions}")
    
    # Calculate readiness
    if len(blockers) > 0:
        return "NOT_READY"
    elif len(warnings) > 0:
        return "READY_WITH_CONDITIONS"
    else:
        return "READY_TO_WORK"
```

### Blocker Priority Order
1. Right to Work (highest priority)
2. DBS Check
3. Identity Verification
4. Proof of Address
5. References
6. Training

---

## 4. API Structure

### Base URL
`/api/`

### Authentication
```
POST /api/auth/login          # Returns JWT token
POST /api/auth/register       # Admin only
GET  /api/auth/me             # Current user
```

### Employees
```
GET    /api/employees                    # List all (paginated)
POST   /api/employees                    # Create new
GET    /api/employees/{id}               # Get single
PUT    /api/employees/{id}               # Update
DELETE /api/employees/{id}               # Delete

GET    /api/employees/{id}/compliance-file    # Full compliance data
GET    /api/employees/{id}/work-readiness     # Status calculation
```

### Document Upload
```
POST   /api/employees/{id}/documents/upload   # Upload evidence
GET    /api/employees/{id}/documents          # List documents
DELETE /api/documents/{doc_id}                # Delete document
```

### Verification Checks
```
# Right to Work
POST   /api/employees/{id}/rtw/check          # Record RTW check
GET    /api/employees/{id}/rtw/current        # Get current check
POST   /api/rtw/extract                       # AI extraction

# DBS
POST   /api/employees/{id}/dbs/check          # Record DBS check
GET    /api/employees/{id}/dbs/current        # Get current check
POST   /api/dbs/extract                       # AI extraction

# Identity
POST   /api/employees/{id}/identity/check     # Record identity check
GET    /api/employees/{id}/identity/current   # Get current check
POST   /api/identity/extract                  # AI extraction

# Address
POST   /api/employees/{id}/address/check      # Record address check
GET    /api/employees/{id}/address/current    # Get current check
POST   /api/address/extract                   # AI extraction
```

### References
```
POST   /api/employees/{id}/references              # Add reference
GET    /api/employees/{id}/references              # List references
PUT    /api/references/{ref_id}                    # Update reference
POST   /api/references/{ref_id}/send-request       # Send request email
POST   /api/references/{ref_id}/verify             # Mark as verified
```

### Training
```
GET    /api/training/types                         # List training types
POST   /api/employees/{id}/training                # Add training record
GET    /api/employees/{id}/training                # List training
GET    /api/employees/{id}/training/matrix         # Training matrix view
```

---

## 5. UI Structure

### Pages (React Router)

```
/login                           # Login page
/portal                          # Dashboard (protected)
/portal/employees                # Employee list
/portal/employees/{id}           # Employee profile (tabbed)
  - Overview tab                 # Summary cards
  - Compliance File tab          # Full compliance checklist
  - Documents tab                # Document library
  - Training tab                 # Training matrix
  - References tab               # Reference management
  - Timeline tab                 # Audit history
/portal/compliance-centre        # Bulk compliance management
/portal/reports                  # Reporting dashboard
```

### Key Components

```
/frontend/src/components/
├── compliance/
│   ├── DualRowComplianceSection.js    # Evidence + Check row pattern
│   ├── UploadRequirementCard.js       # Main requirement card component
│   ├── RecordCheckDialog.js           # Modal for recording verifications
│   ├── surfaceNormalizers.js          # Data transformation helpers
│   └── RequirementSectionShell.js     # Container component
├── ui/                                 # Shadcn components
└── training/
    └── TrainingMatrix.js              # Training requirements grid
```

### Compliance File Structure (per requirement)

```
┌─────────────────────────────────────────────┐
│ [Section Header: Right to Work]             │
├─────────────────────────────────────────────┤
│ EVIDENCE ROW                                │
│ ┌─────────────────────────────────────────┐ │
│ │ 📄 2 files uploaded                     │ │
│ │ [View Files] [Upload More]              │ │
│ └─────────────────────────────────────────┘ │
├─────────────────────────────────────────────┤
│ VERIFICATION ROW                            │
│ ┌─────────────────────────────────────────┐ │
│ │ ✓ Verified - Home Office Online Check   │ │
│ │ Checked: 3 Apr 2026 by Admin            │ │
│ │                                         │ │
│ │ ┌─────────────────────────────────────┐ │ │
│ │ │ RESULT PANEL                        │ │ │
│ │ │ Permission: Skilled Worker Visa     │ │ │
│ │ │ Expires: 10 May 2026 (37 days)      │ │ │
│ │ │ Share Code: ABC123DEF               │ │ │
│ │ │ [⚠ Follow-up required]              │ │ │
│ │ └─────────────────────────────────────┘ │ │
│ │ [Record New Check]                      │ │
│ └─────────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
```

---

## 6. Document Handling Flow

### Upload Flow
```
1. User selects file in UploadRequirementCard
2. Frontend sends to POST /api/employees/{id}/documents/upload
3. Backend:
   a. Validates file type (PDF, PNG, JPG, HEIC)
   b. Generates unique filename
   c. Uploads to cloud storage (or local /uploads)
   d. Creates employee_documents record
   e. Triggers AI extraction (async)
4. Frontend receives document ID and shows in file list
```

### AI Extraction Flow
```
1. POST /api/{type}/extract with file_base64
2. Backend:
   a. Validates image/PDF
   b. Converts PDF first page to image if needed
   c. Calls Gemini 2.5 Flash Vision API
   d. Parses JSON response with JSON Guard
   e. Returns structured fields
3. Frontend pre-fills form fields
4. User reviews/edits fields
5. User submits verification check
```

### Verification Flow
```
1. User clicks "Record Check" in UploadRequirementCard
2. RecordCheckDialog opens with:
   - Pre-filled fields from AI extraction
   - Method selection dropdown
   - Date picker for check date
   - Optional notes field
3. User submits form
4. POST /api/employees/{id}/{type}/check
5. Backend:
   a. Creates check record in {type}_checks collection
   b. Links to evidence document if selected
   c. Updates computed status
   d. Recalculates work readiness
6. Frontend refreshes compliance file
```

---

## 7. AI/OCR Tools

### Current: Google Gemini 2.5 Flash Vision

**Location**: `/app/backend/compliance_engine/extraction.py`

**Configuration**:
```python
# .env
GEMINI_API_KEY=AIzaSy...
```

**Usage**:
```python
from google import genai

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=[
        {
            "role": "user",
            "parts": [
                {"text": EXTRACTION_PROMPT},
                {"inline_data": {"mime_type": "image/png", "data": image_base64}}
            ]
        }
    ]
)
```

**Prompts** (production-grade, UK compliance specific):
- RTW: Extracts permission type, dates, share codes, restrictions
- DBS: Extracts certificate number, level, status, issue date
- Identity: Extracts document type, name, DOB, expiry
- Address: Extracts document type, address, issue date, issuer

**Accuracy**:
| Document Type | Accuracy |
|---------------|----------|
| RTW Share Code | ~97% |
| Passport | ~96% |
| BRP | ~94% |
| DBS Certificate | ~95% |
| Bank Statement | ~93% |
| Utility Bill | ~92% |

### Fallback: Tesseract OCR
```python
import pytesseract
from PIL import Image

text = pytesseract.image_to_string(image)
# Used for text extraction when Gemini unavailable
```

---

## 8. Training Matrix

### Training Types (Configurable)

| Training | Category | Validity | Required For |
|----------|----------|----------|--------------|
| Manual Handling | Mandatory | 12 months | All roles |
| Safeguarding Adults | Mandatory | 36 months | All roles |
| Safeguarding Children | Mandatory | 36 months | Roles with children |
| Fire Safety | Mandatory | 12 months | All roles |
| Basic Life Support | Mandatory | 12 months | Clinical roles |
| Infection Control | Mandatory | 12 months | All roles |
| Food Hygiene | Role-specific | 36 months | Catering roles |
| Medication Administration | Role-specific | 12 months | Senior carers |
| Mental Capacity Act | Role-specific | 36 months | All carers |
| GDPR/Data Protection | Mandatory | 24 months | All roles |

### Training Status Calculation

```python
def get_training_status(employee_id):
    required = get_required_training_for_role(employee.role)
    completed = get_completed_training(employee_id)
    
    matrix = []
    for training_type in required:
        record = completed.get(training_type.id)
        
        if not record:
            status = "not_completed"
        elif record.expiry_date < today:
            status = "expired"
        elif record.expiry_date < today + 30 days:
            status = "expiring_soon"
        else:
            status = "valid"
        
        matrix.append({
            "training": training_type.name,
            "status": status,
            "completed_at": record.completed_at if record else None,
            "expires_at": record.expiry_date if record else None,
            "days_until_expiry": (record.expiry_date - today).days if record else None
        })
    
    return matrix
```

---

## 9. Key Files Reference

### Backend
```
/app/backend/
├── server.py                    # Main FastAPI app (~43k lines)
├── compliance_engine/
│   ├── models.py               # Pydantic models
│   ├── rule_packs.py           # Requirement rules
│   ├── engine.py               # Status computation
│   ├── labels.py               # UI labels
│   └── extraction.py           # Gemini extraction
├── .env                         # Environment variables
└── requirements.txt             # Python dependencies
```

### Frontend
```
/app/frontend/src/
├── App.js                       # Routes
├── pages/
│   └── portal/
│       ├── EmployeeProfilePage.js
│       ├── Dashboard.js
│       └── ComplianceCentre.js
├── components/
│   ├── compliance/
│   │   ├── UploadRequirementCard.js
│   │   ├── RecordCheckDialog.js
│   │   └── DualRowComplianceSection.js
│   └── ui/                      # Shadcn components
└── .env                         # REACT_APP_BACKEND_URL
```

---

## 10. Environment Variables

### Backend (.env)
```
MONGO_URL=mongodb://...
DB_NAME=healthcare_compliance
GEMINI_API_KEY=AIzaSy...
JWT_SECRET=...
```

### Frontend (.env)
```
REACT_APP_BACKEND_URL=https://caretrust-portal.preview.emergentagent.com
```

---

## 11. Pending/Future Work

### In Progress
- [ ] Unified Compliance Rule Engine Phase 2 (Request Flow refactor)
- [ ] Replace remaining LlmChat calls with Gemini (9 remaining)

### Backlog
- [ ] Interview Notes integration
- [ ] Training Matrix PDF export
- [ ] Employee self-service portal
- [ ] Health Questionnaire enforcement
- [ ] Induction & Competency tracking
- [ ] Spot Check templates
- [ ] Split server.py into modular routers
- [ ] Supabase Auth + RLS migration

---

*Document generated: April 4, 2026*
*For: Osabea Healthcare Compliance Platform*
