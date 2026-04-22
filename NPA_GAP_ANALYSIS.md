# Osabea — Gap Analysis vs Medway-style NPA + UK Regulatory Baseline

> **Source-document note.** The attached `DRAFT Osabea Healthcare NPA.docx` was provided as a binary preview only (first 128 bytes) and is not on the workspace filesystem, so its exact clauses could not be parsed. Rows marked **(assumed-typical)** reflect what a Medway/Kent-style Local Authority Nominated Provider Agreement reliably requires from domiciliary / supported-living providers under HSCA 2008 Regulations and standard LA contract monitoring. Save the `.docx` into the repo and rerun the gap pass to harden any such rows against the actual clauses.

**Baselines applied:**
- **Statutory / regulatory:** Health and Social Care Act 2008 (Regulated Activities) Regs 2014 (esp. Regs 9, 12, 13, 17, 18, 19); Care Act 2014; Mental Capacity Act 2005; Equality Act 2010; Employment Rights Act 1996; RIDDOR 2013; Data Protection Act 2018 / UK-GDPR; Immigration Asylum & Nationality Act 2006 (RTW).
- **Inspection expectation (CQC KLOEs / single-assessment quality statements):** Safe, Effective, Caring, Responsive, Well-led.
- **Local authority QA expectation:** LA placement agreements (Medway, Kent, Essex, London-tri-borough patterns): spot checks, service-user feedback, audits (medication, care plan, recruitment file, infection control, finance-on-behalf), safeguarding reporting, workforce returns, data-sharing/DSPT, business continuity, sub-contracting controls.

**Legend:** ✅ covered · 🟡 partial · ❌ missing · **S** statutory · **I** inspection expectation · **LA** LA QA expectation.

Hard rules applied throughout: no product redesign · single backend truth source per concern · worker-level vs organisation-level governance kept separate · verified-only evidence preserved · role-aware logic maintained with nurse-extensibility in mind.

---

## 1. Gap analysis tables

### A. Onboarding / pre-employment — worker-level

| Requirement | State | Driver | Today: module / route / collection | Gap to close |
| --- | --- | --- | --- | --- |
| Right to Work (share-code + document) | ✅ | S | `routes/pre_employment.py`, `rtw_checks`, `employee_documents` | – |
| Enhanced DBS + Update Service | ✅ | S/I | `routes/dbs.py`, `dbs_checks` | – |
| Identity (Reg 19 Sch 3) | ✅ | S | `routes/verifications.py`, `identity_checks` | – |
| Proof of address | ✅ | S | `routes/verifications.py`, `address_checks` | – |
| References ×2, at least one most-recent employer | ✅ | S (Reg 19) | `routes/references.py`, `reference_matching.py`, `references` | – |
| Full employment history + 10-yr coverage + gap explanations | ✅ | S (Reg 19 Sch 3) | `routes/employment_gaps.py`, `employment_review_engine.py` | – |
| Interview record + scoring + decision | ✅ | I | `routes/interviews.py`, `form_submissions` (`form_type=interview_record`) | – |
| Contract of employment | ✅ | S (ERA 1996) | `routes/agreements.py`, `agreement_acknowledgements` (`contract_acceptance`) | – |
| Employee handbook acknowledgement | ✅ | I | same, `handbook_acknowledgement` | – |
| **Job description / person specification acceptance** (role-aware) | ❌ | I / LA | – | add `job_descriptions` (role-versioned) + `jd_acknowledgements`; tie into `agreement_document_service` so it reuses the same verified-signing pipeline. |
| **Health declaration / Occupational Health clearance** | 🟡 | S (Reg 19 fit and proper, Equality Act 2010) | engine references `follow_up_items` but no first-class form or UI | add `health_declarations` collection + `/worker/health-declaration` form (date, conditions, adjustments, fit-to-work decision, OH provider, expiry). Role-aware so nurses can capture additional NMC revalidation-linked health statements. |
| Professional registration (NMC / HCPC / GPhC) | 🟡 | S (Reg 19) | tagged in `employee_documents`; nurse path ready in UCE | promote to first-class `professional_registrations` collection (pin, expiry, revalidation_due_at, verified_online_at, verification_ref). Keep HCA flag = not required; nurse flag = required. |
| Driving licence + business-use insurance (if community work) | 🟡 | I/LA | `employee_documents` tagged | lift to `vehicle_credentials` with expiry, MOT, class-of-use, policy-no; role-aware (HCA community shift = required). |
| Care Certificate (15 standards) for new-to-care | ✅ | I/LA | `routes/induction.py`, `induction_definitions.py`, `induction_checklists` | – |
| Mandatory training matrix (Skills for Care CSTF) | ✅ | S/I | `routes/training.py`, `training_records`, `training_catalogue` | – |
| Induction record | ✅ | I | `induction_checklists` | – |
| **Uniform / ID badge issue log** | ❌ | LA | – | `equipment_issue` collection (item_type, issued_at, returned_at, condition). Single event-log model reused for PPE, phone, key-fob. |
| **Lone-working policy acknowledgement** (separable from handbook) | 🟡 | I | buried in handbook | extract as its own agreement type (`lone_working_acknowledgement`) in the existing `agreement_acknowledgements` collection — zero new infra. |

### B. Ready to deploy / first shift — worker-level

| Requirement | State | Driver | Today | Gap |
| --- | --- | --- | --- | --- |
| Shadow shifts before unsupervised work | 🟡 | I/LA | mentioned in Care Cert induction items | promote to structured `shadow_shifts` records (date, supervisor, service_user, outcome: competent/needs-more). Feed into a new `deployment_readiness` rollup — see §2. |
| Core competency sign-off (moving & handling, medication, infection control, food hygiene) | ✅ | I/LA | `routes/competency.py`, `competency_records` | – |
| Medication competency (observed + theory) | ✅ | I/LA | `competency_records` (type=medication) | – |
| Moving & handling practical | ✅ | I/LA | `competency_records` + `spot_checks` | – |
| **Emergency contact / NOK** | 🟡 | LA | embedded on `employees`, captured at application time | surface as a required first-shift field with expiry/refresh; no new collection. |
| **"Ready to deploy" gate** (composite truth) | ❌ | I/LA | – | new pure helper `compute_deployment_readiness()` following the pattern of [`compute_employment_readiness()`](backend/routes/worker_dashboard.py); returns `{state, blockers[]}` reusing verified-only rules. |

### C. Post-onboarding workforce oversight — worker-level (ongoing governance of each worker)

| Requirement | State | Driver | Today | Gap |
| --- | --- | --- | --- | --- |
| Supervision (quarterly 1:1) | ✅ | I/LA | `routes/recurring_compliance.py`, `recurring_compliance` (`item_type=supervision`) | keep schedule in recurring engine; add structured `supervisions` record (notes, actions, next_due_at) — see first sprint in §5. |
| Annual appraisal | 🟡 | I/LA | no dedicated module; some overlap in `employment_reviews` | first-class `appraisals` collection, annual cadence via `recurring_compliance`. |
| Spot checks (unannounced observational) | ✅ | I/LA | `routes/spot_checks.py`, `spot_checks` | extend with service-user-facing observation template set (medication admin, moving & handling, communication). |
| Competency reassessment | ✅ | I/LA | `recurring_compliance` + `competency_records` | – |
| Mandatory training renewal tracking | ✅ | S/I | `recurring_compliance` (`training_refresh`) | – |
| DBS renewal / Update Service recheck | ✅ | S | `routes/dbs.py` | – |
| **Disciplinary / capability records** | ❌ | I (Reg 19 fit & proper) | – | `worker_conduct_records` (type: informal / disciplinary / capability / grievance; outcome; linked incident_id). Access-controlled to HR role. |
| **Sickness / absence tracking** | ❌ | LA (workforce returns) | – | `worker_absences` (type: sickness/annual/unpaid, start, end, certificate_doc_id, RTW-interview-done). |
| **Return-to-work interview** | ❌ | LA | – | sub-type of `worker_conduct_records` or its own `return_to_work_interviews` — single place, tied to absence record. |
| **Complaints against a named worker** | 🟡 | I/LA | `routes/feedback_complaints.py`, `service_user_feedback` | add explicit link field `complaint.worker_id` + worker-oversight view that surfaces without exposing complainant PII to that worker. |
| Observation of attitudes/values (Caring KLOE) | 🟡 | I | spot-check template only | extend spot-check template library; no schema change. |

### D. Service governance / provider operations — organisation-level

| Requirement | State | Driver | Today | Gap |
| --- | --- | --- | --- | --- |
| Service user / client records | ✅ | S (Reg 9, 17) | `routes/service_users.py`, `service_users` | – |
| Care plans (person-centred, 10-section structure) | ✅ | S (Reg 9) | `service_users` embedded | – |
| **Scheduled care-plan reviews** (at minimum 6-monthly + on change) | 🟡 | S/I | ad-hoc via `follow_up_items`; no cadence | add `care_plan_reviews` collection with `due_at` tracked by existing `recurring_compliance` engine (new `item_type=care_plan_review`). Reuse truth source. |
| Risk assessments (client, environmental, moving & handling, medication) | ✅ | S | `service_users` embedded risk docs | add scheduled review cadence via `recurring_compliance` (`item_type=risk_assessment_review`). |
| MAR charts / medication administration records | ✅ | S (Reg 12) | `service_users` medication section | add `mar_audits` (monthly) as `recurring_compliance` item. |
| **Daily handover notes** | ❌ | I/LA | referenced only in training content | new `shift_handovers` collection: `{shift_id, service_user_id, worker_id, observations, concerns, follow_up_required}`. Append-only; linked to scheduled visits. |
| **Rota / scheduling** | ❌ | LA (call-monitoring, missed-visit reporting) | – | out of scope for this sprint plan but add `visits` / `rota_entries` collection roadmap item; missed-visit detection drives incident creation. |
| Incidents & accidents | ✅ | S (Reg 12, RIDDOR) | `routes/compliance.py`, `incident_logs` | expose CQC-notifiable filter view + RIDDOR flag. |
| **Safeguarding concerns** (separable from generic incidents) | 🟡 | S (Care Act §42) | `incident_logs` tagged | lift to `safeguarding_concerns` view (or sub-type) with LA-referral fields: alert_raised_to, reference, section_42_enquiry, outcome. |
| Complaints from clients / families | ✅ | S (Reg 16) | `routes/feedback_complaints.py` | – |
| **Compliments / positive feedback** | 🟡 | LA | same collection, not reported | simple type-split in existing UI. |
| **Audits** (medication, care plan, recruitment file, infection control, finance-on-behalf, call-monitoring) | 🟡 | I/LA | `routes/cqc_evidence.py`, some in `incident_logs` audit trails | add `audits` collection: `{type, period, auditor_id, findings[], actions[], status, closed_at}`; medication + recruitment-file audits seeded first. |
| **Quality assurance surveys** (annual service-user / family / staff surveys) | ❌ | I/LA | – | `qa_surveys` + `qa_survey_responses` (anonymised). Reuse form-submission storage if possible. |
| **Provider profile completeness** (CQC reg, RM, NI, insurances, policies) | 🟡 | S/I/LA | `org_settings`, `org_policies`, `insurance_docs` scattered | centralise into `provider_profile` doc with completeness score and per-field verification. See §6. |
| **Policy library + review cycle** | 🟡 | I/LA | `org_policies` exists | add `next_review_due_at` + `policy_review_recurrences` via `recurring_compliance`. |
| **Business continuity / BCP** | ❌ | I/LA | – | document + review cadence (annual) as `recurring_compliance` item. |
| **Data Security and Protection Toolkit (DSPT) status** | ❌ | LA (CQC/NHSD) | – | field on `provider_profile` + annual recurring review. |
| **Whistleblowing policy + raising concerns log** | 🟡 | S (Reg 20) | `org_policies` | add `raised_concerns` log (anonymisable). |
| **Statement of Purpose + Service User Guide** | 🟡 | S (Reg 12, Reg 19 Reg Reg) | present as policies | dedicate fields on `provider_profile`. |

---

## 2. Recommended data model

All new tables are additive. No existing schema changes. Every recurring cadence rides the **existing `recurring_compliance` engine** (single truth source, already trusted by the worker dashboard).

**Worker-level (individual compliance):**

| Collection | Purpose | Key fields |
| --- | --- | --- |
| `supervisions` | 1:1 supervision record | `id, employee_id, supervisor_id, supervision_date, type (clinical/managerial), discussion_points[], actions[], worker_ack: {signed_at, signature_url}, supervisor_ack, next_due_at, verification_status` |
| `appraisals` | annual appraisal | `id, employee_id, period_start, period_end, objectives[], achievements[], development_needs[], rating, completed_at, worker_ack, line_manager_ack` |
| `shadow_shifts` | pre-deployment observation | `id, employee_id, shift_date, supervisor_id, service_user_id, outcome (competent / needs_more / not_ready), notes` |
| `professional_registrations` | NMC / HCPC / GPhC | `id, employee_id, body, pin, registered_since, expiry_date, revalidation_due_at, verified_online_at, verified_by, verification_ref` |
| `health_declarations` | OH clearance | `id, employee_id, declared_at, conditions[], adjustments, fit_to_work, oh_provider, expiry_date` |
| `vehicle_credentials` | driving licence + insurance | `id, employee_id, licence_no, licence_expiry, insurance_policy_no, class_of_use, insurance_expiry, mot_expiry` |
| `jd_acknowledgements` | JD/PS sign-off (reuse `agreement_acknowledgements` if feasible) | versioned JD + worker signature |
| `worker_conduct_records` | disciplinary / capability / grievance | `id, employee_id, type, opened_at, outcome, closed_at, linked_incident_id, access_role=hr` |
| `worker_absences` | sickness / leave | `id, employee_id, type, start, end, certificate_doc_id, rtw_interview_done_at` |
| `equipment_issue` | uniform / ID / PPE | `id, employee_id, item_type, issued_at, returned_at, condition` |

**Organisation-level (service governance):**

| Collection | Purpose | Key fields |
| --- | --- | --- |
| `provider_profile` | single source for CQC/NI/RM/insurance/DSPT | see §6 |
| `care_plan_reviews` | scheduled care-plan reviews | `id, service_user_id, due_at, completed_at, reviewer_id, changes_made, notes` |
| `shift_handovers` | daily handover | `id, shift_id, service_user_id, worker_id, observations, concerns, follow_up_required, signed_off_at` |
| `audits` | governance audits | `id, type (medication / care_plan / recruitment_file / infection_control / finance / call_monitoring), period_start, period_end, auditor_id, findings[], actions[], status, closed_at` |
| `qa_surveys` / `qa_survey_responses` | periodic surveys | template + anonymised responses |
| `safeguarding_concerns` | LA / Section 42 referrals | `id, service_user_id, raised_at, raised_by, la_reference, section_42, outcome, closed_at` |
| `raised_concerns` | whistleblowing | `id, raised_at, anonymous, topic, outcome` |

**Rollups (no new collection):**
- `compute_deployment_readiness(employee_id)` → pure helper in `backend/routes/worker_dashboard.py` (mirror of `compute_employment_readiness`).
- `compute_provider_governance_readiness()` → pure helper reading `provider_profile` + due-audit/policy counts; feeds Admin dashboard.

---

## 3. Recommended dashboard split

> The product already hosts a worker dashboard. Keep it. Add two admin surfaces that consume the same `unified_compliance_engine` truth source but project different slices.

| Dashboard | Audience | Purpose | Primary backend |
| --- | --- | --- | --- |
| **Onboarding Compliance** | Recruitment / onboarding admin | Per-worker % to 36 + employment-readiness state (existing 5-state model). "Are we safe to deploy?" | `get_unified_employee_status` + `compute_employment_readiness` + new `compute_deployment_readiness` |
| **Workforce Oversight** | Registered manager / HR | Ongoing governance of all active staff: supervision due, appraisal due, DBS renewal, training refresh, competency reassessment, spot-check cadence, disciplinary/absence live view | `recurring_compliance` engine (already plural-worker) + new `supervisions`/`appraisals`/`worker_conduct_records`/`worker_absences` |
| **Service Governance** | Registered manager / Nominated Individual | Organisation-level: provider profile, policy review cadence, audits due, safeguarding log, incidents (notifiable filter), complaints, care-plan reviews, QA surveys | new `provider_profile` + `audits` + `care_plan_reviews` + existing `incident_logs`/`service_user_feedback` |

No page rewrites; each is a new admin route that projects existing collections.

---

## 4. Priority order for implementation

| Priority | Theme | Why |
| --- | --- | --- |
| **P0 (immediate, blocks LA contract signature)** | Supervision records · Competency reassessment cadence · Spot-check cadence · Audits (medication + recruitment file) · Safeguarding log · Provider profile completeness | Without these a Medway-style NPA monitoring visit finds immediate non-compliance. |
| **P1 (next-quarter)** | Handover notes · Care-plan review cadence · Appraisals · Complaints-against-worker linkage · Policy review cycle · QA surveys | Inspection / LA QA expectation. |
| **P2 (roadmap)** | Rota / visits / missed-visit detection · Sickness & RTW · Disciplinary/capability · Equipment issue · Vehicle credentials · Business continuity · DSPT · Whistleblowing log | Useful operational depth; lower audit urgency. |
| **P3 (extensibility)** | Nurse-path first-class professional_registration + revalidation; HCPC/GPhC bodies; additional regulated activities (e.g. residential if added later) | Prepare before nurse workforce onboarded. |

---

## 5. Exact first sprint (P0 scope, concrete tickets)

Each ticket follows the same pattern proven by the worker-dashboard fix: pure helper → tests → thin route → thin UI. Single truth source. Verified-only preserved.

### 5.1 Supervision
- **New collection:** `supervisions` (schema above).
- **Backend:** `backend/routes/supervisions.py` — `POST /admin/supervisions`, `GET /admin/supervisions?employee_id=`, `POST /admin/supervisions/{id}/verify`.
- **Recurring engine:** register `item_type=supervision` with `cadence_days` (default 90) keyed by completed_at → next_due_at. Single source of "supervision due".
- **Worker truth:** add `compute_ongoing_oversight_due(employee_id)` pure helper.
- **Tests:** `tests/test_supervisions.py` — creation, verify, overdue calculation, next_due after complete.

### 5.2 Competency assessments (extend, not replace)
- Keep `competency_records`. Add required `assessment_type` enum (`initial`, `reassessment`, `targeted_post_incident`).
- **Recurring engine:** register `item_type=competency_assessment` with per-type cadence (medication 12m, moving & handling 12m).
- **Endpoint:** `GET /admin/competencies/due` — projects from recurring_compliance.
- **Tests:** overdue surfaces for each competency type; reassessment resets clock.

### 5.3 Spot checks (extend)
- Keep `spot_checks`. Add `area` enum with at minimum: `medication_admin`, `moving_handling`, `communication`, `infection_control`, `record_keeping`.
- **Recurring engine:** `item_type=spot_check_cycle` (e.g. 2 per year per worker).
- **Endpoint:** `GET /admin/spot-checks/due`.
- **Tests:** one verified spot-check within window clears the due item; rejected does not.

### 5.4 Complaints
- **Existing** `routes/feedback_complaints.py`, `service_user_feedback`.
- Add fields: `about_worker_id`, `about_service_user_id`, `severity`, `received_via`, `closed_at`, `outcome`, `learning_points`.
- New view `GET /admin/complaints?about_worker_id=` for workforce-oversight linkage.
- **Tests:** worker-linked complaint surfaces on Workforce Oversight; PII-scoped response (worker cannot see complainant identity).

### 5.5 Incidents
- **Existing** `incident_logs`. Add `cqc_notifiable: bool`, `riddor_reportable: bool`, `safeguarding_concern: bool`, `notified_at`, `notification_reference`.
- Add filter view `GET /admin/incidents?notifiable=true`.
- **Tests:** flag enum integrity; notifiable filter correctness; linkage to a `safeguarding_concerns` record when flagged.

### 5.6 Handover
- **New collection:** `shift_handovers` (schema above).
- **Endpoint:** `POST /worker/handovers`, `GET /admin/handovers?service_user_id=&date=`.
- **Tests:** append-only invariant (no edit after signed_off); visible on service-user record.

### 5.7 Audits
- **New collection:** `audits`.
- **Types delivered in sprint 1:** `medication_audit`, `recruitment_file_audit`.
- **Recurring engine:** `item_type=audit_cycle`, per-type cadence (medication monthly, recruitment-file quarterly-sample).
- **Endpoint:** `POST /admin/audits`, `POST /admin/audits/{id}/action`, `GET /admin/audits?due=true`.
- **Tests:** creation, action-close flow, overdue surface, findings & actions link to `follow_up_items`.

### 5.8 Care-plan reviews
- **New collection:** `care_plan_reviews`.
- **Recurring engine:** `item_type=care_plan_review`, default 182-day cadence, plus event-driven trigger when any care-plan section changes.
- **Endpoint:** `POST /admin/service-users/{id}/care-plan-reviews`, `GET /admin/care-plan-reviews?due=true`.
- **Tests:** change to care plan creates a review_due entry; completed review resets clock.

**Definition of done for the sprint:** every new endpoint has import-check green · unit tests pass · recurring_compliance is the one source surfacing due items · worker dashboard unchanged for anything already verified-only.

---

## 6. Provider profile completeness — exact fields

Single new document `provider_profile` (singleton) powering both the Service Governance dashboard and any external reporting (LA returns, CQC updates). A boolean `complete` derives from all required fields being populated **and** verified where a doc is expected.

**Legal entity**
- `legal_name` *
- `trading_name`
- `company_number` * (Companies House) — verified via lookup `verified_at`
- `registered_office_address` *
- `vat_number`
- `ico_registration_number` * + `ico_expiry`

**CQC registration**
- `cqc_provider_id` * (e.g. `1-XXXXXXXXX`)
- `cqc_registered_locations[]` * (per location: `name, id, address, regulated_activities[]`)
- `regulated_activities[]` * (e.g. *Personal care*, *Nursing care*)
- `service_types[]` (DCA, SCA, CH, CHN)
- `registered_at`
- `conditions_of_registration[]`
- `latest_cqc_rating` + `latest_cqc_inspection_date`

**Key persons (Reg 4, 5, 6)**
- `registered_manager` * `{full_name, email, phone, cqc_manager_id, start_date, dbs_expiry, qualification}`
- `nominated_individual` * `{full_name, email, phone, role}`
- `responsible_individual_for_data` * (DPO or equivalent)
- `safeguarding_lead` *
- `infection_prevention_lead`

**Insurance (Reg 15 / LA contract)**
- `employers_liability` * `{policy_no, insurer, indemnity_limit, expiry_date, doc_id}`
- `public_liability` *
- `professional_indemnity` (required if regulated activity includes nursing)
- `cyber_insurance`
- `motor_fleet` (if community work)

**Policies (Reg 17)** — each `{doc_id, version, approved_at, next_review_due_at}`:
- safeguarding adults * · safeguarding children · whistleblowing * · complaints * · medication * · infection prevention & control * · health & safety * · lone working * · data protection / confidentiality * · equality & diversity * · mental capacity & DoLS · end-of-life care · moving & handling · recruitment · disciplinary & grievance · supervision · training · business continuity · DSPT-linked data security

**Governance artefacts**
- `statement_of_purpose` * `{doc_id, version, updated_at}`
- `service_user_guide` *
- `dspt_status` * `{edition, standards_met, published_at, expiry_at}`
- `business_continuity_plan` * `{doc_id, last_tested_at, next_review_due_at}`
- `safeguarding_la_contacts[]` * (LA designated safeguarding contact + out-of-hours)

**Operational capacity**
- `service_coverage_areas[]` * (postcodes or LA boundaries)
- `capacity` * `{hours_per_week, active_clients, active_staff}`
- `recruitment_status` (open / paused / closed-to-new)

**Service details (per-location)**
- `location_id, name, address, phone, email`
- `regulated_activities[]`
- `manager_id` (FK to employees / registered_manager)
- `capacity`
- `opening_date`
- `out_of_hours_contact`

`*` = required for `provider_profile.complete = true`.

Completeness API: `GET /admin/provider-profile/completeness` → `{score, required_missing[], warnings[]}`. The Service Governance dashboard shows the score and the exact missing-field list (same UX pattern already used by the worker dashboard's classified blockers).

---

## 7. How this stays inside the hard rules

- **No redesign.** Every P0/P1 item is an additive collection or a new field on an existing one; no page is rewritten.
- **Single backend truth source.** Every cadence (supervision, competency, spot check, audit, care-plan review, policy review) is registered with the existing `recurring_compliance` engine — the same engine that already drives worker-dashboard alerts. Each domain table stores evidence; `recurring_compliance` stores "due/overdue" truth.
- **Worker vs organisation separation preserved.** Categories A/B/C are worker-level; category D is provider-level. They sit on separate dashboards and cannot conflate percentages.
- **Verified-only evidence preserved.** Every new collection carries a `verification_status` field with the same enum (`pending / verified / rejected`) and is only counted toward readiness when `verified`.
- **Role-aware HCA, nurse-extensible.** `professional_registrations`, `health_declarations`, and competency cadences all carry `applies_to_roles[]` — HCA path unchanged; nurse path can enable NMC revalidation, medication-level-2 competency, clinical competency without branching code.

---

## 8. Next step if you want to lock this to the real NPA clauses

Drop `DRAFT Osabea Healthcare NPA.docx` into the workspace root (same folder as `README.md`) and ask for a "NPA clause map" pass. I will extract each clause, match it against this table, and upgrade any **(assumed-typical)** row to cite the exact paragraph number.
