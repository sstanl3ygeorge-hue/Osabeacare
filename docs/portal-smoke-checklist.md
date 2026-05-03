# Portal Smoke Checklist (Pre-Audit)

Use this after each deploy to confirm core recruitment/compliance flows are healthy.

## 1. Navigation and Access
- Admin login succeeds.
- Sidebar shows only current items (no legacy placeholder tabs).
- `Compliance Hub` opens successfully.
- `Audit & Inspection` opens successfully.
- Legacy URLs still redirect safely:
  - `/portal/bulk-import` -> recruitment
  - `/portal/cqc-dashboard` -> compliance hub insights
  - `/portal/compliance-alerts` -> compliance hub insights
  - `/portal/complaints` -> compliance hub complaints
  - `/portal/incidents` -> compliance hub incidents
  - `/portal/global-audit` -> audit
  - `/portal/scheduled-requests` -> compliance hub

## 2. Applicant Core Journey
- Public application can be submitted.
- Applicant appears in recruitment pipeline.
- Admin can open applicant profile.
- Documents upload and preview work.
- Verify-and-stamp works for key IDs (RTW, DBS, ID, address).
- Form submissions appear and status transitions are correct.
- References appear, can be reviewed, and mismatch workflow behaves correctly.

## 3. Agreements and Contract Gate
- Handbook row reflects truthful state:
  - awaiting worker, awaiting admin review, or verified.
- Contract row lock state is consistent across:
  - admin compliance file
  - worker dashboard
  - next-action card
- If contract is locked, blockers/reason are visible.
- If all blockers are satisfied, contract becomes signable.
- After worker signs, admin can verify/reject and status syncs on both sides.

## 4. Worker Dashboard Integrity
- Progress counters are consistent with visible rows.
- "Next action" never says "all caught up" when contract or handbook still needs action.
- Agreements card actions work:
  - view PDF
  - download PDF
  - sign/acknowledge when allowed

## 5. Compliance/Audit Readiness
- Compliance Hub tabs load: policies, incidents, complaints, insights.
- Audit & Inspection loads without critical errors.
- Expiry/renewal badges render with sensible day values.
- Readiness summary and blockers are coherent with underlying rows.

## 6. Security and Reliability Basics
- Unauthorized user cannot access admin pages.
- Worker cannot access another worker's data.
- API errors show safe user messaging (no stack traces in UI).
- Critical pages render even if one non-critical API call fails.

## 7. Spot Data Integrity Checks (Sample 3 Applicants)
- For each sample applicant, compare:
  - Admin agreement row status
  - Worker agreement status
  - Next-action state
  - Contract lock/unlock reason
- Expected: all 4 surfaces agree.
