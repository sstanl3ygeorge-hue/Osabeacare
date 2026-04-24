# Phase 1 Governance — Implementation-ready plan (worker + org only)

**Scope lock.** Worker-level governance on the existing Employee surface (not the applicant view). Organisation-level provider profile on Admin Settings. Zero applicant-page changes. Zero product redesign.

**Repo facts this plan is anchored to** (verified before writing):
- Cadence engine already exists: [`backend/routes/recurring_compliance.py`](backend/routes/recurring_compliance.py) with `item_type ∈ {supervision, competency_assessment, spot_check, training_refresh, report_followup}`, frequencies `monthly|bi_monthly|quarterly|six_monthly|annual|ad_hoc` ↔ `frequency_days`, statuses `scheduled|upcoming|due|overdue|completed`, reminders `[14,7,0]`, escalation `escalation_threshold_days=7`. **This is the single truth source for "when is X next due."**
- Competency already exists: collection `competency_records`, fields include `review_due_date`, `status ∈ {competent, not_competent, training_required, scheduled}`, role requirements in `DEFAULT_COMPETENCY_REQUIREMENTS`.
- Spot-check route file does **not** exist; only the cadence rows. This plan adds the evidence collection.
- Incidents already exist: `incident_logs` with `incident_type ∈ {incident, outbreak, near_miss, complaint}`, statuses `open|investigating|resolved|closed`, reference `CMP-YYYYMM-0001`. Complaints exist in [`backend/routes/feedback_complaints.py`](backend/routes/feedback_complaints.py) with `employee_id` link.
- Service users embed care-plan docs under `sections["4_care_plans"]` and reviews under `sections["9_reviews"]`. No scheduled-review tracking.
- `org_settings` singleton id=`"default"` is branding/contact only — provider profile is additive, not a rename.
- Employee profile tabs today: `employment, forms, references, checklist, training, work_readiness, competencies, spot_checks, audit` in [`frontend/src/pages/portal/EmployeeProfilePage.js`](frontend/src/pages/portal/EmployeeProfilePage.js). Applicant = same component routed via `/portal/recruitment/:id`; Phase 1 UI must be guarded by the existing `isRecruitmentView` flag so it never appears in applicant context.

---

## 0. Cross-cutting conventions (apply to every domain)

Every new collection in §A–§F ships with these fields, same names, same semantics — this is what lets us keep one truth source per domain:

| Field | Type | Meaning |
| --- | --- | --- |
| `id` | uuid v4 | primary key |
| `created_at`, `updated_at` | ISO-8601 UTC | write-time stamps |
| `created_by`, `updated_by` | user_id | actor audit |
| `verification_status` | `pending \| verified \| rejected` | evidence gate — same enum as existing verified-only rule |
| `verified_at`, `verified_by`, `verified_by_name` | – | admin verification |
| `audit_trail` | array of `{at, by, by_name, action, from, to, reason?}` | append-only history |
| `recurring_compliance_id` | uuid | **FK to the single cadence row** that owns "next due" for this instance |
| `role_scope` | `[healthcare_assistant, senior_carer, nurse, any]` | role-awareness |

Rules:
- **Due dates live in `recurring_compliance`**. Domain tables never own cadence; they own evidence.
- **Readiness only counts `verification_status == "verified"`**. Same rule that protects the worker dashboard.
- **Applicant guard** on every admin route: `if employee.person_stage == "applicant": 403`. Enforced in a shared dependency so no domain can leak into applicant context.

**Shared backend helper** — [`backend/governance/readiness.py`](backend/governance/readiness.py) (new module):
```python
def compute_worker_governance_readiness(employee_id, db) -> dict:
    """Returns {state, blockers[], alerts[]} mirroring the 5-state model already
    used by compute_employment_readiness(). Blockers classify per-actor:
    worker_action | admin_action | manager_action | system_issue.
    Pure function over already-fetched rows; no side effects."""
```

**Blocker vs alert** (non-negotiable):
- **Blocker** = prevents `worker_governance_readiness == ready_for_work` (e.g. overdue supervision).
- **Alert** = visible nudge but does not flip state (e.g. supervision due in <14 days).

---

## A. Supervisions

**Collection:** `supervisions` (new; no name clash).

**Schema / example document:**
```json
{
  "id": "5a1c...",
  "employee_id": "9355cb2a-...",
  "supervisor_id": "u-123",
  "supervisor_name": "J. Manager",
  "supervision_type": "managerial | clinical | safeguarding | post_incident | probation",
  "scheduled_at": "2026-05-12T10:00:00Z",
  "completed_at": "2026-05-12T10:42:00Z",
  "location": "office | remote | on_site",
  "agenda": ["caseload", "training", "wellbeing"],
  "discussion_notes": "…",
  "outcome": "satisfactory | concerns_raised | action_required | not_completed",
  "actions": [{"id":"a-1","description":"complete MH refresher","due_at":"2026-06-01","owner_id":"emp-…","status":"open"}],
  "evidence_document_id": "doc-123",
  "worker_ack": {"signed_at":"…","signature_url":"…"},
  "supervisor_ack": {"signed_at":"…","signature_url":"…"},
  "next_due_at": "2026-08-12T00:00:00Z",
  "status": "scheduled | completed | overdue | cancelled",
  "cancelled_reason": null,
  "recurring_compliance_id": "rc-uuid",
  "role_scope": ["any"],
  "verification_status": "verified",
  "audit_trail": [{"at":"…","by":"u-123","action":"create"}],
  "created_at":"…","updated_at":"…","created_by":"u-123"
}
```

**Status model (derivation; never both stored and computed):**
- Stored: `status ∈ {scheduled, completed, cancelled}`.
- Derived view `effective_status`: `overdue` iff status=`scheduled` AND `scheduled_at < now()` AND no completion.

**Due-date logic:**
- On `POST /admin/employees/{id}/supervisions/{sid}/complete`: set `completed_at`, `next_due_at = completed_at + frequency_days_for_role(role, type)` (HCA managerial = 91 days; clinical = 182 days; probation = 42 days), then upsert/update the linked `recurring_compliance` row so the cadence engine takes over.

**Recurring cadence integration:** one `recurring_compliance` row per `(employee_id, item_type="supervision", item_name=supervision_type)`. Completion calls `POST /recurring-compliance/{id}/complete` with the supervision as `evidence_url` AND writes a `supervisions` row. The cadence row owns `next_due_date` and reminders `[14,7,0]`.

**API routes** (all under `/api`, all behind `require_admin_or_manager` + applicant guard):

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/admin/employees/{employee_id}/supervisions` | list (most-recent first) |
| POST | `/admin/employees/{employee_id}/supervisions` | schedule a supervision (creates both supervisions row `status=scheduled` and recurring_compliance row if absent) |
| GET | `/admin/supervisions/{id}` | fetch one |
| PATCH | `/admin/supervisions/{id}` | edit pre-completion |
| POST | `/admin/supervisions/{id}/complete` | mark completed; writes back to recurring_compliance |
| POST | `/admin/supervisions/{id}/cancel` | with reason; never silently deletes |
| POST | `/admin/supervisions/{id}/verify` | admin verification flip; required before counted toward readiness |
| GET | `/worker/supervisions` | worker self-view (read-only summary + action items assigned to them) |

**Truth helpers:**
- `get_supervision_summary(employee_id)` → `{last_completed_at, next_due_at, overdue, open_actions_count}`.
- Feeds `compute_worker_governance_readiness` — overdue=blocker, `next_due_at - now < 14d`=alert.

**UI placement:**
- **Employee profile** — new tab `supervisions`, placed between `spot_checks` and `audit`. Hidden when `isRecruitmentView==true`.
- **Admin dashboard** — "Supervision due this week" card (already feasible off recurring_compliance).
- **Worker page** (self-service) — read-only "Last supervision / Next due / Open actions for you" card on existing worker dashboard; no new nav.

**Summary card content (worker page):**
- Primary: `Last supervision: {date}` or `No supervision on record`.
- Secondary: `Next due: {date}` with badge `Overdue | Due soon | Scheduled`.
- Tertiary: `{n} action(s) assigned to you` linked to a modal.

**Blockers vs alerts:**
- Blocker: effective_status=`overdue` beyond `escalation_threshold_days`.
- Blocker: any `actions[].status=="open"` with `due_at < now()` assigned to the worker.
- Alert: `next_due_at - now < 14d`.

**Tests** — `tests/test_supervisions.py`:
- schedule → cadence row created with correct `frequency_days`
- complete → `next_due_at` = completed + cadence, `recurring_compliance` updated
- overdue: past scheduled_at with no completion flips effective status
- verify-gate: unverified supervision does not clear blocker
- applicant-guard: 403 when employee is applicant
- role cadence: HCA vs probation vs clinical distinct
- cancel preserves audit_trail
- worker endpoint returns only own data

---

## B. Competency reassessments

**Collection:** extend existing `competency_records`. No new table. Add:

| New field | Type | Values |
| --- | --- | --- |
| `assessment_type` | enum | `initial \| reassessment \| targeted_post_incident \| probationary` |
| `role_scope` | array | default from `DEFAULT_COMPETENCY_REQUIREMENTS` |
| `recurring_compliance_id` | uuid | FK to cadence |
| `verification_status` + audit fields | – | per §0 |
| `linked_incident_id` | uuid? | for `targeted_post_incident` |

Existing `competency_type` enum already covers HCA values (`medication, manual_handling, infection_control, safeguarding, …`). **Nurse extensibility:** values `clinical_competency, medication_competency, catheter_care, peg_feeding, wound_care` already present — no schema change required when the nurse path opens.

**Status model (kept):** `competent | not_competent | training_required | scheduled` + a derived `expired` (when `review_due_date < now()` AND status was last `competent`).

**Due-date logic:**
- On record-result: if status=`competent` → `review_due_date = assessed_at + cadence(competency_type, role)`. Default 365d; medication/manual-handling = 365d; clinical_competency = 365d; safeguarding = 365d (aligned with Skills for Care CSTF). Override via `DEFAULT_COMPETENCY_REQUIREMENTS`.
- If status=`not_competent` → immediate `status=training_required`, `review_due_date = now() + 30d`, linked action in supervisions on next 1:1.

**Recurring cadence integration:** one `recurring_compliance` row per `(employee_id, item_type="competency_assessment", item_name=competency_type)`. Competency completion calls `/recurring-compliance/{id}/complete`.

**API routes (additions only — existing endpoints stay):**

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/employees/{id}/competencies/matrix` | merged view: required-by-role × status × review_due_date × effective_status |
| POST | `/employees/{id}/competencies/{cid}/reassess` | new assessment row referencing previous via `assessment_history` |
| POST | `/employees/{id}/competencies/{cid}/verify` | verification flip |
| GET | `/admin/competencies/due?window_days=30` | all workers' due/overdue competencies |

**Truth helpers:**
- `get_competency_matrix(employee_id, role)` → list of required types with `{last_status, review_due_date, effective_status, recurring_compliance_id}`.
- `compute_worker_governance_readiness` reads this and raises a blocker per **critical** type (medication, manual_handling, safeguarding, clinical_competency) that is `expired` or missing.

**UI placement:**
- Employee profile → existing `competencies` tab; add a "Reassessment due" section sourced from the matrix. No new tab.
- Worker dashboard → extend existing competencies card with `Next reassessment due` badge.

**Summary card:**
- `{n_competent}/{n_required} competent · {n_due_in_30d} due soon · {n_overdue} overdue`.

**Blockers vs alerts:**
- Blocker: any **critical** competency `expired` or `training_required`.
- Blocker: any required competency with no record at all (`missing`).
- Alert: non-critical `due soon` (< 30d).

**Tests** — `tests/test_competency_matrix.py`:
- matrix for HCA returns exactly the HCA required set
- matrix for nurse returns HCA set + clinical extensions (extensibility test)
- reassessment resets `review_due_date` via cadence
- `not_competent` raises a training_required entry with 30-day re-review
- `targeted_post_incident` links back to `incident_logs`
- expired critical = blocker; expired non-critical = alert
- verify-gate enforced

---

## C. Spot checks

**Collection:** `spot_checks` (new — today only the cadence rows exist).

**Schema / example:**
```json
{
  "id":"sc-…",
  "employee_id":"…",
  "reviewer_id":"u-…","reviewer_name":"…",
  "check_type":"medication_admin | moving_handling | infection_control | communication | record_keeping | call_punctuality | ppe_use",
  "service_user_id":"su-…",            // optional, if observed during a visit
  "observed_at":"…",
  "announced":false,
  "location":"home_visit | office | community",
  "score":4,                           // 1–5
  "outcome":"pass | pass_with_actions | fail",
  "findings":[{"area":"hand_hygiene","observation":"…","severity":"minor|major|critical"}],
  "actions":[{"description":"…","due_at":"…","owner_id":"…","status":"open"}],
  "follow_up_due_at":"…",
  "next_due_at":"…",
  "status":"scheduled | completed | action_required | overdue",
  "evidence_document_id":"doc-…",
  "worker_feedback":"…",
  "worker_ack":{"signed_at":"…"},
  "recurring_compliance_id":"rc-…",
  "role_scope":["any"],
  "verification_status":"verified",
  "audit_trail":[…],
  "created_at":"…","updated_at":"…"
}
```

**Status model:** stored `{scheduled, completed, action_required, cancelled}`; derived `overdue` when past `next_due_at` OR `follow_up_due_at` with no completion.

**Due-date logic:**
- Baseline cadence: 2 checks per worker per year → `frequency="six_monthly"` in recurring_compliance.
- On `outcome=fail` or `outcome=pass_with_actions`: create a targeted follow-up spot-check cadence with `frequency="ad_hoc"`, `next_due_date=now+30d`.
- `action_required` → blocker until closed.

**Recurring cadence integration:** one `recurring_compliance` row per `(employee_id, item_type="spot_check")` for the periodic cycle. Ad-hoc follow-ups create a separate `item_type="spot_check"` row with `linked_report_id=spot_check.id`. Completion writes back.

**API routes:**

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/admin/employees/{id}/spot-checks` | list |
| POST | `/admin/employees/{id}/spot-checks` | schedule |
| POST | `/admin/spot-checks/{id}/complete` | record observation + outcome, attaches findings/actions |
| PATCH | `/admin/spot-checks/{id}` | edit pre-completion |
| POST | `/admin/spot-checks/{id}/verify` | admin verify |
| POST | `/admin/spot-checks/{id}/actions/{aid}/close` | close action |
| GET | `/worker/spot-checks` | worker self-view |
| GET | `/admin/spot-checks/due?window_days=30` | org-wide due list |

**Truth helpers:**
- `get_spot_check_summary(employee_id)` → `{last_outcome, last_observed_at, next_due_at, open_actions, overdue_followups}`.

**UI placement:**
- Employee profile → **existing** `spot_checks` tab. Plumb the new collection behind it; keep tab name. Hidden in recruitment view.
- Worker dashboard → card showing `Last spot check: {outcome} ({date}) · Actions to complete: {n}`.
- Admin — no new nav; sits inside employee record and in existing Compliance Centre listing.

**Summary card:**
- Primary: `Last spot check: {outcome} · {date}` with colour pass=green / with_actions=amber / fail=red.
- Secondary: `Follow-up due: {date}` or `No follow-up required`.

**Blockers vs alerts:**
- Blocker: `outcome=fail` unclosed beyond `escalation_threshold_days`.
- Blocker: any critical-severity finding open.
- Alert: next periodic due in <30d, follow-up due in <7d.

**Tests** — `tests/test_spot_checks.py`:
- schedule creates cadence row
- fail outcome creates ad-hoc follow-up cadence
- closing all actions clears action_required
- worker self-view is PII-scoped (no reviewer private notes)
- critical finding = blocker; minor = alert
- verify-gate

---

## D. Incidents + safeguarding concerns

**Decision:** extend the existing `incident_logs` rather than introduce a parallel collection. Reason: one truth source, already CQC-aligned, already has reference numbering, and complaints/incident UI already reads it.

**Collection:** `incident_logs` with these **added** fields (migration-safe — all optional):

| New field | Values |
| --- | --- |
| `concern_type` | `incident \| near_miss \| safeguarding_concern \| medication_error \| fall \| complaint_linked \| accident \| rc_notifiable_death` (supersedes the narrower `incident_type`; old records keep `incident_type` and are mapped on read via `concern_type = concern_type or incident_type`) |
| `severity` | `low \| moderate \| high \| critical` |
| `employee_ids` | array of involved employee ids (primary + witnesses) |
| `service_user_id` | optional link |
| `linked_competency_id`, `linked_medication_record_id`, `linked_complaint_id` | optional FKs |
| `external_escalation` | `{la_safeguarding_ref, cqc_notification_ref, riddor_ref, notified_at, notified_by}` |
| `investigation` | `{investigator_id, started_at, completed_at, findings, root_cause, lessons_learned}` |
| `is_cqc_notifiable`, `is_riddor_reportable`, `is_safeguarding` | booleans |
| `recurring_compliance_id` | if a report_followup cadence is opened |
| plus `verification_status`, `audit_trail` per §0 |

**Status model (augmented):** `open | under_review | escalated | closed` — alias existing `investigating` → `under_review`, `resolved` → `closed` on read only (no destructive migration).

**Due-date logic:**
- On create with `severity ∈ {high, critical}`: auto-open a `recurring_compliance` row `item_type="report_followup"` with `next_due_date = now + 7d` for investigation sign-off.
- On `concern_type=safeguarding_concern`: also require `external_escalation.la_safeguarding_ref` before status can move to `closed`.

**Recurring cadence integration:** only when an incident triggers a follow-up (report_followup exists already in the cadence engine enum).

**API routes (additions — existing stay):**

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/compliance/incidents?employee_id=&concern_type=&severity=&status=` | filters, including per-worker view |
| POST | `/compliance/incidents/{id}/escalate` | captures external_escalation fields; status→escalated |
| POST | `/compliance/incidents/{id}/investigation/start` \| `/complete` | structured investigation |
| POST | `/compliance/incidents/{id}/close` | requires investigation.completed_at if severity≥high |
| GET | `/worker/incidents` | incidents where worker is in `employee_ids` — PII-scoped (no complainant identity, no other workers' notes) |

**Truth helpers:**
- `get_worker_incident_summary(employee_id)` → `{open_count, open_high_or_critical_count, overdue_investigations}`.

**UI placement:**
- Employee profile → new tab `incidents` (concerns + incidents + safeguarding combined). Placed after `spot_checks`, before `audit`. Hidden in recruitment view.
- Admin — existing Compliance Centre continues to own the org-wide list; add filter chips for new `concern_type` values.
- Worker page — "Open incidents involving you" card (counts only, with a "view details" deep-link to the PII-scoped endpoint).

**Summary card (worker page):**
- `{open_count} open · {open_high_or_critical_count} high/critical · {overdue_investigations} investigation(s) overdue`.

**Blockers vs alerts:**
- Blocker: severity=critical and status in `{open, under_review}` past 7d.
- Blocker: safeguarding_concern without `la_safeguarding_ref` and older than 24h.
- Alert: any open high-severity item involving the worker.

**Tests** — `tests/test_incidents_and_safeguarding.py`:
- concern_type back-compat mapping from legacy `incident_type`
- high/critical auto-opens follow-up cadence
- close-blocked until safeguarding ref captured
- worker view scrubs complainant identity
- escalation writes to audit_trail
- verify-gate on close

---

## E. Care-plan reviews

**Collection:** `care_plan_reviews` (new). Primarily service-user-level but carries worker links so it surfaces on the worker page.

**Schema / example:**
```json
{
  "id":"cpr-…",
  "service_user_id":"su-…",
  "review_type":"scheduled | change_triggered | post_incident | annual",
  "scheduled_at":"…",
  "completed_at":"…",
  "assigned_reviewer_employee_id":"emp-…",
  "participants_employee_ids":["emp-a","emp-b"],
  "changes_made":[{"section":"7_medication","summary":"…","document_id":"doc-…"}],
  "attendees":["service_user","family","gp","social_worker"],
  "outcome":"no_change | plan_updated | escalated_to_safeguarding | paused",
  "linked_incident_id":null,
  "next_due_at":"…",
  "status":"scheduled | completed | overdue | cancelled",
  "recurring_compliance_id":"rc-…",
  "verification_status":"verified",
  "audit_trail":[…],
  "created_at":"…","updated_at":"…"
}
```

**Status model:** stored `{scheduled, completed, cancelled}`; derived `overdue` past `scheduled_at` with no completion.

**Due-date logic:**
- Default cadence: monthly (`frequency="monthly"`, `frequency_days=30`) per service user — tightenable to weekly via service_user override.
- Any edit to `service_users.sections["4_care_plans"]` documents triggers an event-driven `change_triggered` review due within 14d (hook inside the service_users PATCH route — single place).
- Any incident with `service_user_id` and severity≥high triggers `post_incident` review due within 7d.

**Recurring cadence integration:** one row per `(service_user_id, item_type="report_followup", item_name="care_plan_review")` — reuses the existing enum. `assigned_reviewer_employee_id` is copied to cadence `assigned_to`, which means the cadence engine's existing reminder/escalation pipeline drives the reviewer notification for free.

**API routes:**

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/service-users/{suid}/care-plan-reviews` | list |
| POST | `/service-users/{suid}/care-plan-reviews` | schedule |
| POST | `/care-plan-reviews/{id}/complete` | complete with outcome + changes_made |
| POST | `/care-plan-reviews/{id}/verify` | verify |
| GET | `/admin/care-plan-reviews/due?window_days=14` | org-wide |
| GET | `/worker/care-plan-reviews?as=reviewer\|participant` | worker-scoped (participation summary) |

**Truth helpers:**
- `get_worker_care_plan_review_summary(employee_id)` → `{assigned_as_reviewer, overdue_as_reviewer, upcoming_participation}`.

**UI placement:**
- Worker page — **summary only** tab or section: `Care plan reviews assigned to you`. **No care-plan editor on the worker page**. Clicking a row deep-links to the existing `ServiceUserProfilePage` with section 4/9 focus.
- Admin / service-user profile — owns the full editor (ServiceUserProfilePage §4 and §9 continue to hold documents; the new `care_plan_reviews` collection holds the structured cadence/outcome).

**Summary card (worker page):**
- `{assigned_as_reviewer} assigned to you · {overdue_as_reviewer} overdue · {upcoming_participation} upcoming where you participate`.

**Blockers vs alerts:**
- Blocker: any review `assigned_reviewer_employee_id==worker` with effective status `overdue`.
- Alert: assigned and due in <7d.

**Tests** — `tests/test_care_plan_reviews.py`:
- monthly cadence opens on service_user creation
- care-plan edit triggers change_triggered review
- overdue assignment blocks worker governance readiness
- worker participant view does not permit editing the plan itself
- high-severity incident auto-creates post_incident review
- verify-gate

---

## F. Provider profile completeness (organisation-level only)

**Collection:** `provider_profile` (singleton, id=`"default"`). Do **not** rename `org_settings` — it stays as brand/contact. `provider_profile` is additive and sits next to it.

**Schema — Phase 1 minimum fields (expandable later):**
```json
{
  "id":"default",

  // Service details (required for 'complete')
  "service_name": "Osabea Healthcare",
  "service_address": {"line_1":"","line_2":"","city":"","county":"","postcode":""},
  "telephone": "",
  "email": "",
  "website": "",

  // Registration / governance
  "registered_manager": {"employee_id":"","full_name":"","email":"","start_date":"","cqc_manager_id":""},
  "named_proprietor":  {"full_name":"","role":"","email":""},
  "nominated_individual": {"full_name":"","role":"","email":""},
  "cqc_provider_id":"",
  "cqc_registered_locations":[{"id":"","name":"","address":{...},"regulated_activities":[]}],
  "regulated_activities":[],                       // e.g. "personal_care"
  "ico_registration_number":"",
  "ico_expiry":"",
  "dspt_status": {"edition":"","standards_met":false,"published_at":"","expiry_at":""},

  // Operational
  "specialism_services": ["adults_65_plus","learning_disability"],
  "client_capacity": {"max_clients":0, "active_clients":0},
  "service_coverage_areas":[],

  // QA / report metadata
  "last_internal_audit_at": "",
  "latest_cqc_rating": "",
  "latest_cqc_inspection_date": "",
  "business_continuity_plan_reviewed_at": "",

  // Meta
  "status": "incomplete | partially_complete | complete | needs_review",
  "completeness_score": 0,                         // 0..100
  "required_missing": [],                          // list of required field ids
  "warnings": [],                                  // non-blocking
  "updated_at":"…","updated_by":"…",
  "audit_trail":[…]
}
```

**Required-field set (for `complete`):** `service_name, service_address.*, telephone, email, registered_manager.{employee_id|full_name, email}, named_proprietor.full_name, cqc_provider_id, regulated_activities[≥1], ico_registration_number, specialism_services[≥1], client_capacity.max_clients, dspt_status.standards_met==true`.

**Status model:**
- `incomplete` — <50% required present.
- `partially_complete` — 50–99% required present.
- `complete` — 100% required present AND `dspt_status.standards_met==true` AND `ico_expiry >= now()`.
- `needs_review` — was complete but any of: ico_expiry<now(), `business_continuity_plan_reviewed_at` older than 365d, registered_manager.employee_id no longer active.

**Due-date logic:** annual review — one `recurring_compliance` row `item_type="report_followup", item_name="provider_profile_review"`, `frequency="annual"`.

**API routes:**

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/admin/provider-profile` | full doc |
| PUT | `/admin/provider-profile` | upsert (admin only) |
| GET | `/admin/provider-profile/completeness` | `{status, completeness_score, required_missing, warnings}` |
| POST | `/admin/provider-profile/review` | record annual review; resets cadence |

**Truth helper:** `compute_provider_profile_completeness(doc) -> {...}` (pure; same pattern as worker-readiness helper; unit-testable with zero DB).

**UI placement:**
- **Not on worker page. Not on applicant page.**
- Admin sidebar → under existing `Settings` add a sub-entry `Provider Profile` (new route `/portal/settings/provider-profile`). Also surface a single completeness card on `/portal/dashboard` (admin only).

**Summary card (admin dashboard only):**
- `Provider profile: {status} · {completeness_score}% · {len(required_missing)} required field(s) missing`.

**Blockers vs alerts:**
- **Organisation blocker** (displayed on admin dashboard only): `status in {incomplete, needs_review}`. Does **not** affect any worker's readiness state. Worker governance stays strictly worker-level.
- Alert: completeness_score 50–99%.

**Tests** — `tests/test_provider_profile.py`:
- pure helper: 12 branches (missing service_name, missing DBS, expired ICO, stale BCP, etc.)
- needs_review triggered on ICO expiry
- annual review resets cadence
- writes to audit_trail
- no endpoint leaks into `/worker/*` or applicant paths

---

## 1. Recommended navigation split

| Surface | What lives here | New Phase 1 entry points |
| --- | --- | --- |
| **Applicant** (`/portal/recruitment/:id` — same component as Employee, flag-gated) | pre-employment truth only (existing tabs) | **none.** (Optional read-only note at the top of the employment tab when `isRecruitmentView && person_stage=="applicant"`: *"Post-hire governance becomes available after activation."*) |
| **Employee / Worker** (`/portal/employees/:id`, `/worker/dashboard`) | post-onboarding ops governance | new tabs: `supervisions`, `incidents` · existing tabs gain content: `competencies` (reassessment matrix), `spot_checks` (new detail collection) · new summary section on worker dashboard showing governance readiness |
| **Organisation / Admin** (`/portal/*`) | org-level oversight | `Settings → Provider Profile` (new); admin dashboard card for provider profile; `Compliance Centre` gains `concern_type` filter chips |

Explicit: **nothing Phase-1 appears on the applicant view.**

---

## 2. First implementation order (within the sprint)

Order is chosen so each step ships runnable value and unlocks the next. One PR per step.

1. **Cross-cutting plumbing** — `backend/governance/__init__.py`, `readiness.py` helper stub, shared applicant-guard dependency, shared audit-trail helper. No routes yet. Tests for the guard.
2. **Supervisions** (§A) — most-requested, cleanest standalone, exercises the cadence integration pattern every other domain reuses.
3. **Competency reassessments** (§B) — extends existing `competency_records`; proves the matrix helper pattern.
4. **Spot checks** (§C) — builds the first new evidence collection on top of an already-existing cadence item_type.
5. **Incidents + safeguarding** (§D) — extends `incident_logs` in place; wires worker-scoped view.
6. **Care-plan reviews** (§E) — consumes worker links from §A–§D, touches service_users read paths only.
7. **Provider profile** (§F) — pure org-level; independent of 1–6 but slotted last so admin UI is added once everything else is visible to link to.
8. **Worker dashboard governance summary** — wire `compute_worker_governance_readiness` into the existing dashboard response as a new `governance_readiness` block (parallels the existing `employment_readiness`). Zero UI redesign — same banner component renders it.

---

## 3. Integration points with existing routes

| Existing | Phase-1 integration |
| --- | --- |
| [`backend/routes/worker_dashboard.py`](backend/routes/worker_dashboard.py) | Extend response with a sibling block `governance_readiness = compute_worker_governance_readiness(employee_id, db)`. Do **not** merge with `employment_readiness` (onboarding vs post-onboarding stay separate per hard rule). |
| [`backend/routes/recurring_compliance.py`](backend/routes/recurring_compliance.py) | Every new domain creates/updates rows here for its cadence. No schema change. `item_type` enum already covers all Phase-1 needs. |
| [`backend/routes/service_users.py`](backend/routes/service_users.py) | On PATCH to `sections["4_care_plans"]`, emit a `change_triggered` care-plan review (hook in the existing PATCH handler, one call site). |
| [`backend/routes/competency.py`](backend/routes/competency.py) | Add `assessment_type`, verification fields, `recurring_compliance_id`. Back-fill: null on existing rows, treated as `reassessment`. |
| [`backend/routes/spot_checks.py`](backend/routes/spot_checks.py) (new file) | First time a dedicated spot-check evidence collection exists. Cadence already flows through recurring_compliance. |
| [`backend/routes/compliance.py`](backend/routes/compliance.py) — incidents | Add optional fields; do not rename; map legacy reads. Add worker-scoped endpoint. |
| [`backend/routes/feedback_complaints.py`](backend/routes/feedback_complaints.py) | When a complaint with `employee_id` escalates to investigation, auto-create an `incident_logs` row with `concern_type="complaint_linked"` and mirror `linked_complaint_id`. Single create path, idempotent. |
| `org_settings` | Untouched. `provider_profile` is a new sibling singleton. |

---

## 4. Naming / schema conflicts to avoid

- `incident_type` already exists on `incident_logs` — **do not** drop it. Add `concern_type` alongside, map on read.
- `spot_checks` will be a **new** collection; the string `"spot_check"` is already used as `recurring_compliance.item_type`. Keep the cadence item_type string unchanged; collection name is different namespace.
- `competency_records.status ∈ {competent, not_competent, training_required, scheduled}` is authoritative. Do not introduce `expired` as a stored value — it is derived from `review_due_date`.
- `supervisions.status` values must not collide with cadence `recurring_compliance.status`. They mean different things (domain vs cadence). Keep domain statuses in `supervisions`; ask the cadence engine for "due/overdue".
- `provider_profile.status` values (`incomplete|partially_complete|complete|needs_review`) are organisation-level — do not reuse the worker 5-state model tokens on this doc. Separate namespaces prevent dashboard cross-pollination.
- Route prefixes: all worker-scoped paths under `/api/worker/...` and auth-gated to the authenticated worker's own employee_id; all admin paths under `/api/admin/...`; existing `/api/employees/{id}/...` paths kept for back-compat.
- Applicant guard is **centralised**: one FastAPI dependency `require_employee_not_applicant(employee_id)` used by every Phase-1 admin route. No domain re-implements it.

---

## 5. Regulatory alignment map (what each domain satisfies)

| Domain | Regulation 18 (staffing / supervision / competence) | Regulation 17 (governance / records / audits) | Medway-style LA QA |
| --- | --- | --- | --- |
| A. Supervisions | ✔ scheduled documented supervision | ✔ audit_trail, evidence, sign-off | ✔ quarterly evidence of 1:1 |
| B. Competency reassessments | ✔ competence maintained | ✔ matrix as an auditable record | ✔ annual competence evidence |
| C. Spot checks | ✔ observed competence | ✔ findings/action trail | ✔ unannounced observations |
| D. Incidents + safeguarding | ✔ staff performance follow-up via targeted reassessment | ✔ investigation + lessons learned | ✔ §42 referrals, CQC/RIDDOR flags |
| E. Care plan reviews | – | ✔ review cadence, change control | ✔ periodic review evidence |
| F. Provider profile | – | ✔ provider fit-and-proper, registered manager, DSPT | ✔ service details, named roles, capacity |

---

## 6. Definition of done for the sprint

For each domain:
- new/extended collection with all §0 conventions present
- exactly the routes listed above, behind applicant-guard + role check
- cadence wiring via `recurring_compliance` (no parallel cadence tracking)
- pure truth helper unit-tested before any UI
- worker dashboard summary card wired (except §F which is admin-only)
- blockers vs alerts wired through `compute_worker_governance_readiness`
- verified-only rule honoured end-to-end
- applicant surface visually unchanged (manual verification + one test per domain asserting 403 for applicant routes)
- backend import check green; frontend `get_errors` clean; new tests all pass; `unified_compliance_engine` untouched (onboarding truth preserved)

---

## 7. Care Employer Legal and Operational Obligations Addendum (audit and plan only)

This addendum is planning-only and does not authorize implementation in this pass.

### 7.1 Updated backlog table (current truth audit)

| Obligation area | Current status | Current truth path | Visibility now | Minimal next ticket (no new parallel truth) | Delivery phase |
| --- | --- | --- | --- | --- | --- |
| Supervision cadence and records | Partially exists | backend/routes/supervisions.py + backend/routes/recurring_compliance.py + frontend/src/components/compliance/SupervisionsPanel.js | Admin and manager primary, worker summary visible | Add explicit appraisal subtype guidance and completion SLAs to supervision policy and UI labels | Workforce now |
| Formal appraisal cycle | Missing | No dedicated appraisal domain beyond supervision types | Admin-only by workaround | Add appraisal profile on existing supervisions truth (type, annual due window, outcome template) | Workforce now |
| Spot checks and follow-up actions | Exists | backend/routes/spot_checks.py + frontend/src/components/compliance/SpotChecksPanel.js + worker dashboard summary | Admin and manager primary, worker summary visible | Add stricter closure rule for critical follow-up actions and recurring escalation copy | Workforce now |
| Competency assessment and reassessment | Exists | backend/routes/competency.py + frontend/src/components/compliance/CompetencyAssessmentsPanel.js + worker dashboard summary | Admin and manager primary, worker summary visible | Add required-by-role matrix endpoint consumption in existing UI and explicit overdue chip | Workforce now |
| Training refresh cadence | Partially exists | backend/routes/recurring_compliance.py supports training_refresh item_type | Mostly admin; worker visibility not explicit per item type | Add worker-safe training refresh card sourced from recurring_compliance without new collection | Workforce now |
| Incidents and concern follow-up | Exists | backend/routes/compliance.py incident_logs + recurring report_followup support + Compliance Centre incidents tab | Admin full, worker incident views exist with scoping | Add mandatory follow-up due date workflow for unresolved high severity incidents | Workforce now |
| RIDDOR and reportable external flags | Partially exists | Incident model has type and status; no explicit RIDDOR capture standard in current admin flow | Admin-only | Add explicit reportable flags and external reference fields on existing incident records | Workforce now |
| Employer insurance and H and S certificate register | Exists | backend/routes/compliance.py insurance endpoints + seed types + Compliance Centre certificates tab | Admin-only | Add alert tiers by certificate category and renewal window to existing certificate truth | Workforce now |
| Employer internal audit tracker | Partially exists | Audit artifacts exist in markdown and generic audit logs; no dedicated structured tracker route | Admin-only | Add lightweight internal-audit schedule and outcomes using recurring_compliance report_followup and evidence links | Workforce now |
| Staff meetings and minutes | Missing | No staff meeting domain routes or UI | None | Add staff_meetings domain with minutes, actions, attendance, and follow-up via recurring_compliance | Workforce now |
| Policy acknowledgements evidence | Exists | backend/routes/policy_assignments.py + employee policy tab + Compliance Centre assignment modal | Worker and admin visible | Add policy review cycle reminder on existing assignment truth, not a new policy system | Workforce now |
| Shift change and cancellation audit trail | Exists | backend/routes/shifts.py + portal Shifts page + worker dashboard shift visibility | Worker and admin visible | Add immutable timeline panel in existing shift detail modal (created, edited, cancelled, reason) | Workforce now |

### 7.2 Already covered (use as-is)

- Spot checks with outcomes and follow-up fields.
- Competency records, scheduling, reassessment result capture.
- Incident logging and admin incident operations.
- Employer certificate register with upload, replace, history, expiry status.
- Policy acknowledgement lifecycle with signer capture and PDF evidence export.
- Shift cancellation reason capture and worker-safe cancellation visibility.

### 7.3 Partially covered (extend existing truth only)

- Supervision exists but appraisal semantics are not yet explicit as a managed cycle.
- Training refresh exists in recurring cadence but worker-facing clarity is limited.
- RIDDOR and external-reporting flags are not explicit and standardized in incident workflows.
- Internal audit tracking is present as artifacts/audits but not as a single structured operational tracker.

### 7.4 Missing (new capabilities, but still on existing architecture patterns)

- Dedicated formal appraisal profile using current supervision truth.
- Staff meetings and minutes tracking with action follow-up.
- Structured employer internal-audit schedule/outcomes register.

### 7.5 Next 5 safest tickets (ordered)

1. Incident reportable flags hardening on existing incident_logs (RIDDOR and external refs, no new collection).
2. Training refresh worker visibility card from recurring_compliance training_refresh items.
3. Supervision to appraisal profile extension (new supervision_type conventions, annual appraisal status chips).
4. Internal audit tracker minimal slice using recurring_compliance report_followup + linked evidence.
5. Shift timeline panel on existing shift truth and audit metadata (read-only timeline).

### 7.6 Later or out of scope now (care-delivery phase or lower safety return)

- Care-plan review orchestration tied to service-user clinical pathways (later care-delivery phase).
- Multi-agency safeguarding workflow automation beyond incident flagging (later care-delivery phase).
- Deep service-user outcome analytics in governance dashboard (later care-delivery phase).

### 7.7 Guardrails for future tickets

- No new parallel cadence engine; all due dates remain in recurring_compliance.
- No duplicate incident system; extend compliance incident_logs only.
- No duplicate policy store; continue policy_assignments lifecycle.
- Keep worker visibility worker-safe; sensitive investigation details stay admin/manager only.
