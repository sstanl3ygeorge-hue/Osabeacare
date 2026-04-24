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
