# Digital Care Agency OS - Template Library Migration Strategy

**Archive:** Osabea Healthcare Solutions Ltd (2)  
**Generated:** 2026-05-09  
**Total Templates to Import:** 705 (58 CRITICAL/HIGH priority)

---

## Migration Overview

### Archive Statistics
- **Total Templates:** 705
- **Total Size:** 81.6 MB
- **Exact Duplicates Found:** 0 ✅
- **Near-Duplicates (Intentional Variants):** 6 ✅
  - Body Map variants (Female, Male, Cream-specific)
  - Medication MAR variants (Weekly, Monthly, Controlled)
  - Risk Assessment variants (context-specific)

### Priority Distribution
| Priority | Count | Effort | Timeline |
|----------|-------|--------|----------|
| CRITICAL | 57 | 2-3 days | Week 1 |
| HIGH | 43 | 3-4 days | Week 2 |
| MEDIUM | 103 | 4-5 days | Week 3-4 |
| LOW | 502 | Ongoing | Weeks 5+ |
| **TOTAL** | **705** | **10-15 days** | **3-4 weeks** |

**Fast-Track Path:** Import 57 CRITICAL + 43 HIGH (100 templates) in 5 days for immediate system value

---

## Phase 1: Critical Path (57 CRITICAL Templates)
**Timeline:** Days 1-2 | **Effort:** 24-32 hours | **Output:** Service user care plans + operational core

### 1.1 Service-User Care Plans (17 templates)

**Destination:** `su_*` tabs in ServiceUserProfilePage  
**Endpoint:** `POST /document-templates/care-plan/{template-id}/import`  
**Collections:** `service_user_documents` (versioned cache)

| Template | Folder | Destination | Action |
|----------|--------|-------------|--------|
| Osabea Care Plan.docx | Care Plan Documents | su_care_plans | IMPORT |
| Osabea Care Plan Initial Assessment.docx | Care Plan Documents | su_assessments | IMPORT |
| Osabea Care Plan Top Sheets.docx | Care Plan Documents | su_care_plans | IMPORT |
| Osabea Care Plan Review Record Sheet.docx | Care Plan Documents | su_reviews | IMPORT |
| Osabea One Page Profile.docx | Care Plan Documents | su_personal_referral | IMPORT |
| Osabea Person Centred Information File.docx | Care Plan Documents | su_assessments | IMPORT |
| Osabea Healthcare Assessment & Plan.docx | Care Plan Documents | su_assessments | IMPORT |
| Osabea Medication Assessment & Plan.docx | Care Plan Documents | su_medication | IMPORT |
| Osabea Nutrition & Hydration Assessment & Plan.docx | Care Plan Documents | su_assessments | IMPORT |
| Osabea Moving & Handling Assessment & Plan.docx | Care Plan Documents | su_risk_assessments | IMPORT |
| Osabea Diabetes Plan & Assessment.docx | Care Plan Documents | su_assessments | IMPORT |
| Osabea End of Life Care Plan.docx | Care Plan Documents | su_care_plans | IMPORT |
| Osabea Epilepsy Management Plan.docx | Care Plan Documents | su_care_plans | IMPORT |
| Osabea Environmental Assessment & Plan.docx | Care Plan Documents | su_assessments | IMPORT |
| Osabea Positive Behaviour Support Plan Template.docx | Care Plan Documents | su_care_plans | IMPORT |
| Osabea Personal Care Assessment & Plan.docx | Care Plan Documents | su_assessments | IMPORT |
| Osabea Sexuality and Relationship Plan Assessment.docx | Care Plan Documents | su_assessments | IMPORT |

**Implementation:**
1. Create care plan import batch endpoint: `POST /document-templates/batch-import`
2. Parse DOCX → extract text + preserve formatting
3. Inject template fields: {SERVICE_USER_NAME}, {DATE}, {CARE_PLAN_ID}
4. Store in `service_user_documents` collection
5. Create PDF renderers for each template type
6. Build ServiceUserProfilePage UI for template selection

**Success Criteria:**
- ✅ All 17 templates importable without errors
- ✅ PDF rendering preserves Osabea branding
- ✅ Service user context injection working
- ✅ Tab-level destination assignment correct
- ✅ Audit log records each template action

**Estimated Effort:** 8-10 hours

---

### 1.2 Operational Core: Incidents + Body Maps (12 templates)

**Destinations:** `incidents`, `body_maps`  
**Endpoints:** 
- `POST /incidents/create-from-template`
- `POST /body-maps/create-from-template`

| Template | Folder | Destination | Action |
|----------|--------|-------------|--------|
| Osabea Accident & Incident Report Form.docx | Health & Safety | incidents | IMPORT |
| Osabea Accident and Incident Continuation Sheet.docx | Health & Safety | incidents | IMPORT |
| Osabea Accident, Incident & Investigation Policy.docx | Health & Safety | incidents | IMPORT |
| Osabea Incident Log.docx | Health & Safety | incidents | IMPORT |
| Osabea Body Map Template.docx | Health & Safety | body_maps | IMPORT |
| Osabea Body Map_Female Template.docx | Health & Safety | body_maps | IMPORT |
| Osabea Body Map_Male Template.docx | Health & Safety | body_maps | IMPORT |
| Osabea Body Map for Creams Template.docx | Health & Safety | body_maps | IMPORT |
| Osabea Body Map for Creams_Female Template.docx | Health & Safety | body_maps | IMPORT |
| Osabea Body Map for Creams_Male Template.docx | Health & Safety | body_maps | IMPORT |
| Osabea Root Cause Analysis Policy Procedure.docx | Health & Safety | incidents | IMPORT |
| Osabea Root Cause Analysis Toolkit.docx | Health & Safety | incidents | IMPORT |

**Implementation:**
1. Incident form → template-driven form creation
2. Body map templates → image annotation + overlay system
3. RCA toolkit → incident investigation workflow
4. Continuation sheets → multi-part form handling

**Success Criteria:**
- ✅ Incident creation via template functional
- ✅ Body maps render with gender variants
- ✅ RCA workflow integrated with incident
- ✅ Continuation sheets linked to parent incident

**Estimated Effort:** 6-8 hours

---

### 1.3 Medication Management (20 templates + charts)

**Destination:** `medication_operational`  
**Endpoints:**
- `POST /service-users/{id}/medication-templates`
- `GET /medication-templates/mar-chart`

| Template Subset | Count | Action |
|---|---|---|
| MAR Chart variants (Weekly, Monthly, Controlled, PRN) | 4 | IMPORT |
| Medication forms (Authorization, Handover, Received, Returns, Count, Changes) | 6 | IMPORT |
| Medication protocols (Covert, Homely Remedies, PRN) | 3 | IMPORT |
| Medication audit templates | 7 | IMPORT (Phase 3) |

**Implementation:**
1. MAR chart templates → CSV-exportable forms
2. Medication forms → service user context injection
3. Dynamic field generation (staff names, medication lists)
4. PDF generation for MAR charts with branding

**Success Criteria:**
- ✅ MAR charts functional for all 4 variants
- ✅ Medication forms pre-populate staff names
- ✅ Medication tracking audit-ready
- ✅ Export to CSV for records

**Estimated Effort:** 4-6 hours

---

### 1.4 Risk Assessments + Policies (8 templates)

**Destinations:** `risk_assessments_operational`, `safeguarding_policies`

**High-Value Templates:**
1. Osabea Risk Assessment Template.docx (generic foundation)
2. Osabea Fire Safety Risk Assessment_Service User Home.docx
3. Osabea Risk Assessment Template - Risk of falls.docx
4. Osabea Risk Assessment Template - Hoist usage.docx
5. Osabea Lone Working Policy.docx
6. Osabea Safeguarding Adults at Risk Policy.docx
7. Osabea Whistleblowing Policy & Flowchart.docx
8. Osabea Modern Slavery Policy.docx

**Implementation:**
1. Risk assessment templates → form generation
2. Hoist/equipment risk → context-specific fields
3. Lone working → staff assignment tracking
4. Safeguarding/whistleblowing → policy distribution + acknowledgment tracking

**Success Criteria:**
- ✅ Risk assessment forms auto-populate context
- ✅ Safeguarding policies published + tracked
- ✅ Whistleblowing flowchart accessible
- ✅ Policy sign-off functionality

**Estimated Effort:** 6-8 hours

---

## Phase 2: High Priority (43 HIGH Templates)
**Timeline:** Days 3-4 | **Effort:** 16-20 hours | **Output:** Full operational system + audit foundation

### 2.1 Audit & Competency Foundation (23 templates)

**Destinations:** `audit_records`, `competency_assessments`

**High-Value Templates:**
1. Osabea Care Plan Audit Tool.docx
2. Osabea Medication Administration Audit.docx
3. Osabea Fire Safety Audit.docx
4. Osabea Staff File Audit.docx
5. Osabea Medication Competency Assessment.docx
6-8. [3 more competency modules for medication, moving/handling, first aid]

**Implementation:**
1. Audit templates → spreadsheet generation
2. Digital audit tracking → auto-scoring
3. Competency assessment forms → staff tracking
4. Audit schedule → calendar integration

**Success Criteria:**
- ✅ Audit templates downloadable + trackable
- ✅ Competency assessments mapped to staff
- ✅ Digital audit scoring functional
- ✅ Compliance dashboard

**Estimated Effort:** 8-10 hours

---

### 2.2 Recruitment & HR Core (10 templates)

**Destinations:** `recruitment`, `onboarding`, `disciplinary_hr`

**Templates:**
1. Osabea Job Advert.docx
2. Osabea Application Request Form.docx
3. Osabea Invite to Interview.docx
4. Osabea Offer of Employment Letter.docx
5. Osabea Induction Checklist.docx
6. Osabea Probation Review Report Form.docx
7. Osabea Disciplinary Flowchart.docx
8. Osabea Written Warning Letter.docx
9. Osabea Absence Record Form.docx
10. Osabea Exit Interview Template.docx

**Implementation:**
1. Recruitment workflow → template-driven process
2. Induction templates → checklist tracking
3. Disciplinary process → flowchart + letters
4. Absence tracking → automated reporting

**Success Criteria:**
- ✅ Recruitment workflow functional
- ✅ Induction tracked + auditable
- ✅ Disciplinary process documented
- ✅ Absence analytics available

**Estimated Effort:** 6-8 hours

---

### 2.3 Specialized Operational (10 templates)

**Destinations:** `moving_handling`, `equipment_safety`, `staffing_operational`

**Templates:**
1. Osabea Moving and Handling Policy.docx
2. Osabea Moving and Handling Procedure.docx
3. Osabea Hoist_Sling Safety Inspection Record.docx
4. Osabea Electric Bed Safety Inspection Record.docx
5. Osabea Walking Aid Safety Inspection Record.docx
6. Osabea Care Staff Rota.docx (28/30/31 day variants)
7. Osabea Staff Weekly Rota detailed.docx
8. Osabea Key Holder Register.docx
9. Osabea Key Safe Log.docx
10. Osabea On Call Log Sheet.docx

**Implementation:**
1. Safety inspection templates → scheduled maintenance
2. Rota templates → staff scheduling UI
3. Key management → access control tracking
4. On-call log → shift coordination

**Success Criteria:**
- ✅ Safety inspections scheduled + tracked
- ✅ Rotas generated from template
- ✅ Key management auditable
- ✅ On-call coordination functional

**Estimated Effort:** 6-8 hours

---

## Phase 3: Medium Priority (103 MEDIUM Templates)
**Timeline:** Days 5-7 | **Effort:** 20-24 hours | **Output:** Full compliance library + analytics

### 3.1 Comprehensive Audit Framework (40 audit templates)

**Coverage:**
- Care plan audits
- Medication audits (8 variants: consent, controlled drugs, covert, errors, homely, ordering, chart individual, chart overall)
- Fire safety audits
- Data protection audits
- Infection control audits
- Moving & handling audits
- And 30+ more

**Implementation:**
1. Digital audit spreadsheets → Excel template library
2. Audit schedule → automated reminders
3. Compliance tracking dashboard
4. Audit findings → corrective action workflow
5. Trend analysis → reporting

**Success Criteria:**
- ✅ All 40 audit templates available
- ✅ Digital audit scoring automated
- ✅ Compliance dashboard real-time
- ✅ Audit trends analyzed

**Estimated Effort:** 10-12 hours

---

### 3.2 Competency Framework (88 competency modules)

**Coverage:**
- Medication administration
- Infection prevention
- Dementia care
- Sensory loss support
- Disability awareness
- Mobility & moving/handling
- Personal care & hygiene
- Healthcare procedures
- Pain management
- End of life care
- And 78+ more

**Implementation:**
1. Competency modules → digital assessment system
2. Staff skill mapping
3. Development planning → competency-linked training
4. Competency tracker (Excel) → staff tracking dashboard
5. Skill gap analysis

**Success Criteria:**
- ✅ 88 competency modules mapped
- ✅ Staff competency tracking live
- ✅ Development plans linked to gaps
- ✅ Training recommendations generated

**Estimated Effort:** 8-10 hours

---

### 3.3 Quality Feedback & Assessment (35 templates)

**Coverage:**
- Family quality assurance feedback forms
- Staff views surveys
- Service user-advocate surveys
- Quality questionnaire analysis
- Quality assurance policy
- Review of care forms
- Stakeholder feedback

**Implementation:**
1. Survey templates → digital form collection
2. Feedback analysis → automated reporting
3. Quality metrics dashboard
4. Continuous improvement tracking
5. Family/staff engagement metrics

**Success Criteria:**
- ✅ Survey templates digital + mobile-friendly
- ✅ Feedback collection automated
- ✅ Quality metrics real-time
- ✅ Improvement actions tracked

**Estimated Effort:** 6-8 hours

---

### 3.4 Operations & Compliance (28 templates)

**Coverage:**
- Rota variants + scheduling
- Financial management (petty cash, expenses, invoice)
- Complaint handling
- Consent forms
- Service user guides
- Policies (health & safety, operational, environmental)

**Implementation:**
1. Rota scheduling integration
2. Petty cash tracker
3. Complaint management workflow
4. Consent tracking + audit trail
5. Policy distribution + sign-off

**Success Criteria:**
- ✅ Rota scheduling optimized
- ✅ Financial tracking automated
- ✅ Complaint workflow end-to-end
- ✅ Consent management compliant
- ✅ Policies tracked + acknowledged

**Estimated Effort:** 6-8 hours

---

## Phase 4: Low Priority Templates (502 templates)
**Timeline:** Weeks 4+ | **Effort:** 30-40 hours | **Output:** Complete compliance archive

### 4.1 HR Compliance Library (86 templates)
- Full HR policy set
- Employment contracts (variants by role)
- Leave management
- Absence management variants
- Recruitment workflows
- Exit/offboarding procedures

### 4.2 Specialized Policies (40+ templates)
- Health & safety variants by context
- Environmental policies
- Data protection compliance
- Social media policy
- Mobile phone policy
- Dress code policy
- And more

### 4.3 COVID-19 & Seasonal (20 templates)
- COVID-19 policies (lower priority but archived)
- Winter toolkit (seasonal)
- Influenza program checklists
- Temperature tracking
- Staff risk assessments

### 4.4 Unclassified & Resources (101 templates)
- PDF guides and resources
- Support documents
- Handbook materials
- Policy templates (masters)
- Archived/legacy documents

**Implementation Strategy:**
- Batch import by category
- Gradual rollout (don't overwhelm system)
- Archive less-frequently-used documents
- Create policy archive section in UI
- Maintain searchability across full library

---

## Implementation Timeline

### Week 1: Critical Path (57 templates)
```
Day 1 (8 hours):
  - Setup batch import endpoint
  - Import 17 care plan templates
  - Build service user context injection
  - Test PDF rendering

Day 2 (8 hours):
  - Import 12 incident/body map templates
  - Create body map image system
  - Import 20 medication templates
  - Build MAR chart rendering

Day 3 (8 hours):
  - Import 8 risk/policy templates
  - Safeguarding policy distribution
  - Create policy sign-off tracking
  - End-to-end testing
```

### Week 2: High Priority (43 templates)
```
Day 4 (8 hours):
  - Import 23 audit/competency templates
  - Build audit scoring system
  - Competency tracking dashboard

Day 5 (8 hours):
  - Import 10 recruitment/HR templates
  - Recruitment workflow creation
  - Induction tracking setup

Day 6 (8 hours):
  - Import 10 specialized operational templates
  - Safety inspection scheduling
  - Rota system integration
  - Performance validation
```

### Week 3-4: Medium Priority (103 templates)
```
Days 7-10:
  - Comprehensive audit framework (40 templates)
  - Competency modules mapping (88 templates)
  - Quality feedback system (35 templates)
  - Operations compliance (28 templates)
  - Testing + UAT
```

### Week 5+: Low Priority (502 templates)
```
  - Batch imports by category
  - Policy archive
  - Legacy document preservation
  - Ongoing maintenance
```

---

## Technical Architecture

### Folder Hierarchy Support

**New Data Model:**
```python
class DocumentTemplate:
    id: str
    archive_folder_path: str              # "Care Plan Documents"
    archive_subfolder: Optional[str]      # "Risk Assessment Templates"
    filename: str                         # Original archive filename
    destination_section: str              # su_care_plans, incidents, etc.
    template_type: str                    # care_plan, incident, medication, etc.
    category: str                         # service-user-care-plans, operational, etc.
    content: bytes                        # DOCX binary
    extracted_text: str                   # For classification
    metadata: Dict[str, Any]              # folder_path, creation_date, etc.
    version: int
    created_at: datetime
    updated_at: datetime
    created_by: str
    status: str                           # draft, approved, published, archived
```

**New Collections:**
```javascript
// document_templates collection (enhanced)
{
  archive: {
    source: "osabea_healthcare_2024",
    folder_path: "Care Plan Documents",
    subfolder: null,
    original_filename: "Osabea Care Plan.docx",
    import_date: ISODate("2026-05-09"),
    import_batch: "phase_1_critical",
  },
  destination: {
    section: "su_care_plans",
    section_type: "service_user_tab",
    category: "service-user-care-plans",
  },
  classification: {
    document_type: { value: "care_plan_template", confidence: 0.95 },
    category: { value: "service-user-care-plans", confidence: 0.98 },
    // ... 8 other dimensions
  },
  content: {
    text_extracted: "...first 5000 chars...",
    has_placeholders: true,
    placeholder_fields: ["{SERVICE_USER_NAME}", "{DATE}", ...],
  },
  audit: {
    import_count: 0,
    last_used: null,
    total_uses: 0,
    created_by: "admin@system",
  }
}
```

---

## API Design for Template Import

### Batch Import Endpoint
```
POST /document-templates/batch-import
Content-Type: application/json

{
  "source": "osabea_healthcare_2024",
  "folder_path": "Care Plan Documents",
  "templates": [
    {
      "filename": "Osabea Care Plan.docx",
      "destination_section": "su_care_plans",
      "content_base64": "...",
      "metadata": {
        "priority": "CRITICAL",
        "approval_required": false
      }
    },
    // ... more templates
  ],
  "parallel": true,  // Process in parallel
  "auto_approve": true  // Skip review for low-risk
}

Response:
{
  "batch_id": "batch_20260509_phase1_001",
  "total": 17,
  "imported": 16,
  "errors": 1,
  "errors_detail": [
    {
      "filename": "...",
      "error": "...",
      "action": "RETRY | SKIP | MANUAL_REVIEW"
    }
  ],
  "import_progress": {
    "in_progress": 0,
    "completed": 16,
    "failed": 1
  }
}
```

### Template Classification + Destination Suggestion
```
POST /document-templates/classify-and-suggest

{
  "filename": "Osabea Care Plan.docx",
  "folder_path": "Care Plan Documents",
  "text_sample": "...first 3000 chars of extracted text...",
  "archive_source": "osabea_healthcare_2024"
}

Response:
{
  "classification": {
    "category": {
      "value": "service-user-care-plans",
      "confidence": 0.98,
      "reasoning": "Folder 'Care Plan Documents' + text contains 'care plan' + 'assessment'"
    },
    "document_type": {
      "value": "care_plan_template",
      "confidence": 0.95,
      "reasoning": "Matched care plan keywords in filename + text"
    },
    // ... 8 more dimensions
  },
  "destination_suggestion": {
    "destination_section": "su_care_plans",
    "title": "Care Plans",
    "section_type": "service_user_tab",
    "confidence": 0.95,
    "reasoning": "Matched: care plan, assessment, service user context"
  },
  "recommended_action": "AUTO_IMPORT | REVIEW | MANUAL_DESTINATION"
}
```

---

## Validation & Testing Strategy

### Pre-Import Validation (Phase 1)
- ✅ DOCX structure integrity
- ✅ File size limits (max 50MB)
- ✅ Encoding validation
- ✅ Archive folder structure parsing
- ✅ Filename normalization
- ✅ Duplicate detection (hash-based)
- ✅ Classification confidence >0.7

### Post-Import Testing (Phase 1)
- ✅ Document retrieval by destination
- ✅ PDF rendering without errors
- ✅ Service user context injection
- ✅ Audit trail logging
- ✅ Search functionality
- ✅ Access control (role-based)
- ✅ Folder hierarchy preserved
- ✅ Metadata indexed
- ✅ Version control functional

### UAT Checklist (Phase 2)
- ✅ Care plan workflow end-to-end
- ✅ Incident creation from template
- ✅ Body map system operational
- ✅ Medication tracking functional
- ✅ Risk assessment automation
- ✅ Safeguarding policy distribution
- ✅ Audit system baseline
- ✅ Performance (import 50 templates <1 sec)
- ✅ Backup/recovery working

---

## Success Metrics

| Metric | Target | Timeline |
|--------|--------|----------|
| CRITICAL templates imported | 57/57 (100%) | Day 2 |
| HIGH templates imported | 43/43 (100%) | Day 4 |
| MEDIUM templates imported | 103/103 (100%) | Day 7 |
| Import error rate | <1% | Day 7 |
| PDF rendering success | 100% | Day 2 |
| Search performance | <200ms | Day 7 |
| Audit trail completeness | 100% | Day 2 |
| Duplicate detection | 100% accuracy | Day 1 |
| Folder hierarchy support | Functional | Day 7 |
| User satisfaction (staff pilot) | >4.5/5 | Week 2 |

---

## Rollout Strategy

### Staff Pilot (Day 1-2)
- Select 5 power users per module
- Care plan management
- Incident tracking
- Medication management
- Feedback collection

### Phased Rollout (Day 3-7)
- **Day 3:** Service User Care Plans → ServiceUserProfilePage (all staff)
- **Day 4:** Operational Records → Incidents, Body Maps (care staff)
- **Day 5:** Medication → MAR Charts (medication staff)
- **Day 6:** Risk Assessments & Policies (managers)
- **Day 7:** Audit Framework (auditors + managers)

### Training Plan
- 30-min video walkthrough per module
- in-app tutorial overlays
- Help documentation + examples
- Dedicated support channel (Slack)
- Weekly office hours Q&A

---

## Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|---|---|---|
| Import failures (corrupted DOCX) | Medium | Low | Pre-validate DOCX integrity, skip on error, manual review |
| Misclassification | Medium | Medium | Confidence threshold >0.7, manual review for <0.7, retraining |
| Duplicate content | Low | Medium | Hash-based detection, near-duplicate flagging |
| Performance degradation | Low | High | Batch import limits, async processing, indexing strategy |
| User adoption | Medium | Medium | Training, pilot feedback, iterative improvement |
| Data loss | Low | Critical | Backup before import, transaction rollback on error |

---

## Success Criteria for Go-Live

✅ **Functional:**
- All 100 CRITICAL/HIGH templates imported + testable
- 0 critical bugs in core workflows
- PDF rendering 100% success rate
- Audit trails complete for all actions

✅ **Performance:**
- Import batch <1 sec for 50 templates
- Search <200ms for 700+ templates
- PDF generation <5 sec
- UI responsiveness >60fps

✅ **Adoption:**
- >80% staff completion of training
- >4.0/5 satisfaction rating
- 0 escalated production issues
- <1 hour rollback time if needed

✅ **Compliance:**
- 100% duplicate detection
- Archive source metadata preserved
- Folder hierarchy captured
- Normalization documented

---

**Next Step:** Approve Phase 1 critical path. Ready to begin import on command.

