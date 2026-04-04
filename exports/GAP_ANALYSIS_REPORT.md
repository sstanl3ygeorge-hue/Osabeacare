# Osabea Healthcare - CQC Compliance Gap Analysis Report
## Comparison: Current System vs Medway QA Assessment + UK Healthcare Recruitment Standards

**Report Date**: April 4, 2026  
**Assessment Reference**: Medway Council QA Visit (30.03.2026)  
**Analyst**: CareTrust Compliance System

---

## Executive Summary

| Category | Current Status | Target | Gap Level |
|----------|---------------|--------|-----------|
| **Staff Recruitment** | 75% Complete | 100% | MEDIUM |
| **Reference Verification** | 60% Complete | 100% | HIGH |
| **Training & Competency** | 70% Complete | 100% | MEDIUM |
| **Document Management** | 85% Complete | 100% | LOW |
| **Care Planning** | 0% Complete | 100% | NOT APPLICABLE* |
| **Audit Trail** | 90% Complete | 100% | LOW |

*Care Planning is for service delivery (clients), not recruitment compliance.

---

## PART 1: STAFF RECRUITMENT REQUIREMENTS

### 1.1 Application Form & Employment History

| Requirement (QA Finding) | Current System | Status | Action Needed |
|--------------------------|----------------|--------|---------------|
| Application form fully completed | ✅ Digital application form with all fields | DONE | None |
| Employment history asked | ⚠️ CVs requested but not structured in form | PARTIAL | Add structured employment history section to application form |
| Employment gaps identified | ✅ 30-day gap detection with explanation enforcement | DONE | None |
| Employment gaps explained | ✅ Pending → Explained → Verified workflow | DONE | None |

**QA Finding**: "No employment history asked for on forms but CVs are always asked for"

**System Gap**: Employment history should be a STRUCTURED section in the application form, not just CV upload.

---

### 1.2 Reference Checks (CRITICAL GAP)

| Requirement | Current System | Status | Action Needed |
|-------------|----------------|--------|---------------|
| Two references from last two employers | ✅ Captures 2 references in application | DONE | None |
| References match employment history | ⚠️ Mismatch detection exists but needs UI refinement | PARTIAL | Display employment history alongside reference for comparison |
| References verified | ⚠️ Verification checkbox exists but no formal process | PARTIAL | Add formal verification stamp/signature capture |
| References match application form | ⚠️ System can detect but UI unclear | PARTIAL | Show side-by-side comparison in Reference panel |
| Alternative references recorded | ✅ Alternative path recording implemented | DONE | None |

**QA Finding**: 
- "Two references received, neither appear to match references given in application form"
- "Not verified – advised that this needs to be done"

**System Gap**: 
1. **Visual verification that references match declared employment** - Show employment history next to reference
2. **Clear VERIFIED stamp requirement** - Not just a checkbox, but auditable stamp with date/name

---

### 1.3 Interview Notes

| Requirement | Current System | Status | Action Needed |
|-------------|----------------|--------|---------------|
| Interview notes with date | ✅ InterviewFormPanel captures structured interviews | DONE | None |
| Interview notes on system | ⚠️ Form exists but not enforced pre-employment | PARTIAL | Add interview_completed flag as blocker |
| Interview method recorded | ✅ Phone/Video/In-Person captured | DONE | None |

**QA Finding**: "Notes not on system – advised to add these to record"

**System Gap**: Interview record should be MANDATORY before work readiness approval.

---

### 1.4 DBS Checks

| Requirement | Current System | Status | Action Needed |
|-------------|----------------|--------|---------------|
| DBS within 3 years | ✅ 3-year recheck tracking with alerts | DONE | None |
| DBS enhanced | ✅ dbs_level field with Enhanced/Enhanced with Barred options | DONE | None |
| DBS clear status | ✅ result_status tracks clear/information_present | DONE | None |
| Update Service registered | ✅ update_service_registered tracked | DONE | None |
| Update Service check performed | ✅ Annual check scheduling with last_status_check_date | DONE | None |
| DBS Register visible | ✅ DBS summary in compliance dashboard | DONE | None |

**QA Finding**: "DBS Register on system – all staff showing as having had a DBS check in the last year and are on the update service"

**System Status**: FULLY COMPLIANT ✅

---

### 1.5 ID Checks

| Requirement | Current System | Status | Action Needed |
|-------------|----------------|--------|---------------|
| ID documents uploaded | ✅ Identity evidence with upload/verification | DONE | None |
| ID copies verified | ⚠️ Verification stamp exists but not enforced | PARTIAL | Add "Copy Verified" requirement before work readiness |
| Photo ID confirmed | ✅ photo_match_confirmed field | DONE | None |
| ID matches application | ✅ name_matches_application, dob_matches_application fields | DONE | None |

**QA Finding**: "Nigerian passport, copy not verified – advised this needs to be clearly stated on the system"

**System Gap**: Physical verification stamp ("I have seen the original / verified this copy") must be MANDATORY before work approval.

---

### 1.6 Proof of Address

| Requirement | Current System | Status | Action Needed |
|-------------|----------------|--------|---------------|
| Proof of address uploaded | ✅ POA evidence with multiple document support | DONE | None |
| Address matches application | ✅ address_matches_application field | DONE | None |
| Copy verified | ⚠️ Same as ID - needs enforcement | PARTIAL | Enforce verification stamp |
| Second proof of address | ⚠️ System supports multiple but not enforced | PARTIAL | Add min_documents=2 rule for POA |

**QA Finding**: "UK driving license, matches application form, copy not verified. Second proof of address not yet added to system"

**System Gap**: 
1. VERIFICATION STAMP enforcement (same as ID)
2. MINIMUM 2 documents rule for POA

---

### 1.7 Right to Work

| Requirement | Current System | Status | Action Needed |
|-------------|----------------|--------|---------------|
| RTW document uploaded | ✅ RTW evidence with AI extraction | DONE | None |
| Permission type tracked | ✅ permission_type, visa fields | DONE | None |
| Hours restrictions captured | ✅ hours_limit field | DONE | None |
| Share Code verification | ✅ share_code field with GOV.UK guidance | DONE | None |
| RTW expiry alerts | ✅ Expiry tracking with 30/90/180 day thresholds | DONE | None |
| Home Office follow-up | ✅ follow_up_required, follow_up_date fields | DONE | None |

**QA Finding**: "Home office document in file, valid – part time role only 20 hours (matches application form)"

**System Status**: FULLY COMPLIANT ✅

---

### 1.8 Health Declaration

| Requirement | Current System | Status | Action Needed |
|-------------|----------------|--------|---------------|
| Health questionnaire on file | ✅ HealthDeclarationService with questionnaire | DONE | None |
| Issues flagged | ✅ requires_review flag with admin queue | DONE | None |
| Admin review workflow | ✅ POST /health-declarations/{id}/review | DONE | None |

**QA Finding**: "Health questionnaire on file, no issues raised"

**System Status**: FULLY COMPLIANT ✅

---

### 1.9 Contract of Employment

| Requirement | Current System | Status | Action Needed |
|-------------|----------------|--------|---------------|
| Contract issued | ⚠️ Agreement signature exists but not contract-specific | PARTIAL | Add contract_signed requirement |
| Start date recorded | ✅ start_date field on employee | DONE | None |
| Contract template | ⚠️ Not implemented | MISSING | Add contract PDF generation |

**System Gap**: Formal contract issuance workflow needed.

---

## PART 2: TRAINING & COMPETENCY

### 2.1 Mandatory Training

| Requirement | Current System | Status | Action Needed |
|-------------|----------------|--------|---------------|
| Training matrix | ✅ AuditReadyTrainingMatrix with mandatory tracking | DONE | None |
| Training in date | ✅ Expiry tracking with alerts | DONE | None |
| Training certificates verified | ⚠️ Upload exists but no verification workflow | PARTIAL | Add certificate verification step |
| Care Certificate | ⚠️ Tracked but not enforced as prerequisite | PARTIAL | Add Care Certificate as blocker for HCA role |

**QA Finding**: "Mandatory and Statutory Practical Training Course" list provided

**Current Training Types Covered**:
- ✅ Manual Handling
- ✅ Safeguarding Adults L1 & L2
- ✅ Safeguarding Children L1 & L2
- ✅ Infection Prevention and Control
- ✅ Fire Safety
- ✅ Basic Life Support (Resuscitation)
- ✅ Health Safety and Welfare
- ✅ Equality, Diversity and Human Rights
- ✅ Preventing Radicalisation
- ✅ Information Governance
- ✅ Mental Capacity Act
- ✅ NHS Conflict Resolution

**Missing from System**:
- ⚠️ Medication Administration (role-specific)
- ⚠️ PEG Feeding (specialist)
- ⚠️ Catheter Care (specialist)
- ⚠️ Epilepsy Care (specialist)
- ⚠️ Choking Management (specialist)
- ⚠️ Parkinson's Care (specialist)
- ⚠️ Challenging Behaviour (specialist)

---

### 2.2 Supervision & Competency

| Requirement | Current System | Status | Action Needed |
|-------------|----------------|--------|---------------|
| Induction programme | ⚠️ Template mentioned but not in system | MISSING | Add induction checklist requirement |
| Regular supervision | ⚠️ Not tracked | MISSING | Add supervision record tracking |
| Staff meetings | ⚠️ Not tracked | MISSING | Add meeting attendance tracking |
| Spot checks (twice yearly) | ⚠️ Templates exist, not in system | MISSING | Add spot check scheduling/recording |
| Yearly competency assessments | ⚠️ Not tracked | MISSING | Add competency assessment workflow |
| Medication competency | ⚠️ Not tracked | MISSING | Add medication competency requirement |
| Moving & handling competency | ⚠️ Not tracked | MISSING | Add M&H competency requirement |

**System Gap**: This is the LARGEST gap area. Need:
1. Induction checklist (pre-work)
2. Supervision record (ongoing)
3. Spot check module (ongoing)
4. Competency assessment module (annual)

---

## PART 3: DOCUMENT VERIFICATION WORKFLOW

### Current Workflow
```
Upload → AI Extraction → Admin Review → Accept/Reject → Record Check → Verification Stamp
```

### Required Workflow Enhancement
```
Upload → AI Extraction → Admin Review → PHYSICAL VERIFICATION REQUIRED → Record Check → Verification Stamp → Work Approved
```

**Gap**: The system allows progression without explicit "I have physically seen the original document" confirmation.

**Solution**: Add mandatory "Original Seen" / "Copy Verified with Original" stamp requirement before work readiness.

---

## PART 4: ROLE-BASED COMPLIANCE (PROPOSED ENHANCEMENT)

The QA feedback suggests different requirements for different roles. The proposed `role_compliance_profiles` would solve this:

| Role | DBS Level | References | Specialist Training |
|------|-----------|------------|---------------------|
| Healthcare Assistant | Enhanced Adult | 2 recent employers | Medication (if administering) |
| Senior Carer | Enhanced Adult | 2 recent employers | Medication, Supervision |
| Support Worker (Children) | Enhanced Child | 2 recent employers | Safeguarding Children L3 |
| Nurse | Enhanced Adult | 2 recent employers + NMC check | Clinical competencies |
| Administrator | Basic (or none) | 1 employer | None |

**Recommendation**: Implement the role_compliance_profiles system as discussed.

---

## PART 5: OVERALL COMPLETION PERCENTAGE

### For CQC Registration & Medway QA Compliance

| Area | Weight | Current % | Weighted Score |
|------|--------|-----------|----------------|
| Core Identity Checks (RTW, ID, DBS, POA) | 30% | 90% | 27% |
| Reference Verification | 20% | 60% | 12% |
| Training Matrix | 15% | 80% | 12% |
| Induction & Competency | 20% | 10% | 2% |
| Audit Trail | 10% | 95% | 9.5% |
| Employment History/Gaps | 5% | 90% | 4.5% |

### **TOTAL COMPLETION: 67%**

---

## PART 6: PRIORITY ACTION ITEMS

### 🔴 CRITICAL (Before First Placement)
1. **Reference-Employment Cross-Check UI** - Show employment history alongside references
2. **Mandatory Verification Stamps** - "Original Seen" / "Copy Verified" before work approval
3. **Interview Completed Requirement** - Add as blocker to work readiness
4. **Contract Signed Requirement** - Add as blocker to work readiness
5. **Min 2 POA Documents Rule** - Enforce second proof of address

### 🟠 HIGH (Before CQC Inspection)
6. **Induction Checklist Module** - Digital sign-off before work starts
7. **Care Certificate Tracking** - Blocker for HCA role
8. **Spot Check Module** - Schedule and record spot checks
9. **Competency Assessment Module** - Annual assessments tracking

### 🟡 MEDIUM (Ongoing Improvement)
10. **Supervision Record Tracking** - Monthly supervision log
11. **Staff Meeting Attendance** - Monthly meeting tracking
12. **Role-Based Compliance Profiles** - Configurable requirements per role
13. **Specialist Training Types** - Add PEG, Catheter, Epilepsy, etc.

### 🟢 LOW (Nice to Have)
14. **Contract PDF Generation** - Auto-generate employment contracts
15. **Training Matrix PDF Export** - For external submission
16. **Split server.py** - Technical debt cleanup

---

## PART 7: SIMPLE WORKER READABILITY

### Current System Language
The system uses technical terms that may confuse workers:
- "Evidence Row" → "Your Documents"
- "Verification Row" → "Manager Checks"
- "Compliance File" → "My Work Readiness"
- "Blocking Requirements" → "What I Need to Complete"

### Recommendation
Add a **Worker Self-Service Portal** with simplified language:
- "Upload Your ID"
- "Upload Your DBS"
- "Complete Your Health Questionnaire"
- "Sign Your Contract"
- Progress bar: "You're 75% ready to work!"

---

## CONCLUSION

The CareTrust system is **67% complete** for full CQC/Medway QA compliance. The core document management and AI extraction infrastructure is excellent. The main gaps are:

1. **Reference verification rigour** - Need side-by-side employment check
2. **Physical document verification enforcement** - "Original Seen" stamps
3. **Pre-employment gates** - Interview + Contract signed as blockers
4. **Induction & Competency module** - Currently missing
5. **Worker-friendly interface** - Self-service portal needed

**Estimated Effort to 100%**: 
- Critical items (1-5): 2-3 days
- High items (6-9): 3-5 days  
- Medium items (10-13): 3-5 days

**Total**: ~8-13 development days to full CQC audit readiness

