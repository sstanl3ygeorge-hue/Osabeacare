# PHASE GATE — Employee Operations Checkpoint

Date: 2026-04-24  
Scope: Care-employer operations platform (post onboarding/recruitment hardening)

## 1) Current Phase Status
- Phase gate status: **Operational Core Established**
- Platform focus: onboarding/governance complete enough for controlled operations expansion.
- Rule for next work: **extend existing systems, do not rebuild parallel engines**.

## 2) Complete
- Recruitment/onboarding readiness and unified blockers/checks.
- Health gate hardening + explicit fit-for-work approval decision.
- References/CV/employment gaps canonical alignment.
- Training matrix + verified/readiness alignment.
- Recurring compliance engine + worker/admin surfacing.
- Shifts/rota MVP: backend core, admin UI, worker read + accept/reject.
- Incidents MVP: worker submit/list + admin management + audit logging.
- Supervisions/spot checks/competency: routes + admin panels + worker visibility.
- Policy acknowledgements and provider certificate register surfaces.
- Staff meetings + employer audits/checklists routes and compliance-centre surfacing.
- PDF/export stack available from backend canonical routes.
- Worker/admin visibility boundaries hardened (active-only access enforced).
- Lifecycle controls and lifecycle event visibility in audit trail.

## 3) Partially Complete
- RIDDOR/reportable incident operational workflow (fields exist; full guided flow not complete).
- Lifecycle controls UX consistency (reason capture and phrasing still uneven across surfaces).
- Audit history normalization for legacy mixed action names.
- Cross-surface operational queue/triage for active workforce obligations.

## 4) Missing
- Full rota domain beyond MVP (availability planner, recurrence/templates, automation).
- Full safeguarding/case-management workflow.
- Deep service-user event linkage beyond optional/minimal links.
- Strongly standardized lifecycle reason dialog patterns everywhere.

## 5) Known Technical Debt
- Large `backend/server.py` legacy overlap with modular routes.
- Legacy and canonical action naming mixed in historical audit rows.
- Some stale planning/export docs can mislead implementation direction.
- Multiple admin action entry points can still feel fragmented.

## 6) Next Safest 10 Tickets
1. RIDDOR/reportable incident decision support on existing incident truth.
2. Standard lifecycle reason dialog component for admin transitions.
3. Audit tab preset/filter for lifecycle transitions and critical governance events.
4. Admin active-workforce “actions due” strip using existing truth sources.
5. Shift transition edge-case hardening + audit metadata consistency checks.
6. Supervision/spot-check due/overdue drilldown UX polish (no new engine).
7. Competency renewal action surfacing using recurring truth.
8. Policy acknowledgement overdue triage surface.
9. Provider certificate expiry operational pass in compliance centre.
10. Route consolidation plan for overlapping legacy vs modular endpoints.

## 7) Explicit Out of Scope (Now)
- Care delivery EMR domain (care plans, MAR, daily notes, clinical charting).
- Full safeguarding case-management platform.
- Payroll/timesheets/payroll integration.
- Notification engine redesign.
- New lifecycle states or replacement readiness engine.
- Full dashboard redesign/replatform.

## 8) Architecture Guardrails (Must Hold)
- Backend remains **source of truth**.
- Frontend remains **display/orchestration only**.
- Do not duplicate readiness/lifecycle/incident/training/compliance engines.
- Audit first before implementation.
- Reuse existing routes/components before building new modules.
- Prefer minimal additive patches over broad refactors.

