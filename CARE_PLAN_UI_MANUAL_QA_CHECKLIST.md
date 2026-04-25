# Care-Plan UI Manual QA Checklist

Scope: Quick manual QA for service-user care-plan UI behavior.

## Preconditions

- Test with `admin` and `manager` users.
- Test with a `worker` user for negative access.
- At least one service user exists.

## Checklist

1. Service-user profile access
- Open a service-user profile from `/portal/service-users`.
- Confirm profile loads without errors.

2. Care-plan tab visibility (admin/manager)
- Confirm Care Plans tab is visible for admin.
- Confirm Care Plans tab is visible for manager.

3. Create draft
- Create a care plan draft.
- Confirm status is `draft`.

4. Edit draft
- Edit and save the draft.
- Confirm updates persist.

5. Activate draft
- Activate the draft.
- Confirm status becomes `active`.

6. Version rollover
- Create a second draft and activate it.
- Confirm new version is `active`.
- Confirm previous active becomes `superseded`.

7. Archive rules
- Archive a `draft` plan (allowed).
- Archive a `superseded` plan (allowed).
- Confirm `active` is not directly editable/archiveable in normal flow.

8. PDF download
- Download care-plan PDF.
- Confirm file opens and includes key fields (title, status, version, goals, needs, support instructions, dates).

9. Audit visibility (if audit UI exists)
- Confirm create/update/activate/archive/download events are visible.

10. Worker access negative check
- Log in as worker.
- Confirm no care-plan admin actions are exposed.

## Test Record (optional)

- Tester:
- Date:
- Environment:
- Result:
- Notes:

## Final Operational Compliance Rehearsal (Go-Live Dry Run)

Purpose: end-to-end rehearsal that proves staffing readiness, shift safety, service-user support workflows, and regulatory evidence continuity.

### A) Create Dummy Entities

1. Dummy HCA
- Create one employee with role equivalent to Healthcare Assistant.
- Set status to `active` only after baseline onboarding/compliance data is present.

2. Dummy Nurse
- Create one employee with role equivalent to Registered Nurse.
- Add nurse-specific credentials (for example NMC data) if your environment requires it.

3. Dummy Service User
- Create one service user with sufficient onboarding/care-profile information for shift linkage and daily notes.

### B) Readiness and Assignment Checks

4. Onboarding readiness works
- Open the service-user onboarding/readiness view for the dummy service user.
- Confirm readiness status resolves deterministically (ready or clearly not ready with reasons).

5. Nurse blockers show
- Intentionally remove one nurse-critical requirement (for example NMC/competency/training) in test data.
- Confirm blocker appears in readiness/compliance surfaces.

6. HCA/nurse shift matching works
- Create one nurse-required shift and one care-assistant-required shift.
- Confirm role mismatch is blocked in assignment UI/API.
- Confirm role-compatible assignment succeeds.

### C) Operational Flow Checks

7. Daily notes work
- For an assigned shift linked to the dummy service user, submit a worker daily note.
- Confirm note is retrievable in shift detail/history.

8. Incident follow-up works
- Create safeguarding/escalation incident for dummy service user.
- Confirm follow-up badge/status appears in incident UI.
- Close incident and confirm linked follow-up is closed/deactivated.

9. Alerts show overdue risks
- Create at least one overdue condition (training/competency/care-plan review/safeguarding follow-up) in dummy data.
- Confirm it appears in Compliance Alerts summary with correct severity and link target.

10. Audit log records key actions
- Verify audit entries for: shift assignment change, incident create/amend/close, and attendance or daily-note actions.

### D) Evidence Capture

- Capture screenshots or exports for each step above.
- Record IDs used (employee IDs, service-user ID, shift IDs, incident ID) for traceability.
- Mark pass/fail per step and log remediation owner for failures.
