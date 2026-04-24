# Route Ownership Matrix

## Purpose

This document is a planning-only ownership sheet for future backend route consolidation.

Constraints:
- No code movement yet
- No route deletion yet
- No endpoint rename yet
- No behavior change yet

## Effective Owner Rules

Current effective owner means the handler most likely reached at runtime today, based on route registration order in backend/server.py.

Observed routing rules from the current app wiring:
- routes.readiness is included early before large inline server.py route blocks, so its exact duplicate paths likely win at runtime.
- routes.generated_forms is included early before routes.forms generated-form routes, so generated_forms likely wins those exact duplicates.
- routes.notifications is included before routes.email_notifications, so notifications likely wins the duplicate notification logs path.
- Most other modular routers are included near the end of backend/server.py, after many inline api_router handlers are already defined, so inline server.py handlers likely win exact server-vs-module duplicates.

## Risk Legend

- High: exact duplicate path, security-sensitive flow, or business-critical compliance lifecycle
- Medium: overlapping namespace or adjacent truth-path risk without confirmed exact collision
- Low: documented ownership is already fairly clear and isolated

## Ownership Matrix

| Domain | Endpoint / route family | Current effective owner | Overlapping file(s) | Target canonical owner | Collision type | Risk level | Required test gate before consolidation | Recommended action | Defer / proceed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Contracts | POST /employees/{employee_id}/contract/sign | backend/server.py line 8757 | backend/routes/contracts.py line 286 | backend/routes/contracts.py | Exact duplicate path | High | Contract sign happy-path, rejected/re-sign path, status endpoint parity, audit log parity, PDF/render regression | Freeze current response shape and auth expectations, then migrate only after parity tests exist | Proceed later |
| Contracts | GET /employees/{employee_id}/contract/status | backend/server.py line 8861 | backend/routes/contracts.py line 232 | backend/routes/contracts.py | Exact duplicate path | High | Status payload parity test across signed, unsigned, rejected, superseded states | Treat status as contract canonical read model and compare payloads before any switch | Proceed later |
| Contracts | POST /employees/{employee_id}/contract/supersede | backend/server.py line 10282 | backend/routes/contracts.py line 404 | backend/routes/contracts.py | Exact duplicate path | High | Supersede regression, existing signed record retention, audit log coverage | Keep frozen until lifecycle parity is documented | Proceed later |
| Readiness approval | POST /employees/{employee_id}/work-readiness/approve | backend/routes/readiness.py line 1031 | backend/server.py line 24139 | backend/routes/readiness.py | Exact duplicate path with include-order winner in module | High | Work-readiness approve regression, blocker gating, approval audit log, downstream employee state transition checks | Treat readiness module as canonical now; do not remove inline path until duplicate coverage exists | Proceed |
| Training proposed-items / intake | GET /employees/{employee_id}/training/proposed-items | backend/server.py line 23109 | backend/routes/training_intake.py line 24 | backend/routes/training_intake.py | Exact duplicate path | High | Proposed-item list parity, extraction review workflow, approve-and-verify path, intake wizard regression | Canonicalize to training_intake after payload diff and intake regression pack | Proceed later |
| Training proposed-items / intake | Intake and request-certificates family under /employees/{employee_id}/training/intake and related review endpoints | backend/server.py for review and approve flows at lines 42121 and 42159 | backend/routes/training_intake.py lines 63 and 107, backend/routes/training.py | backend/routes/training_intake.py for intake, backend/routes/training.py for training_records CRUD | Near-duplicate / split lifecycle ownership | High | End-to-end intake to verified training record test, orphan cleanup test, certificate upload and mapping test | Keep split documented; do not merge until lifecycle boundaries are explicit | Defer partial merge |
| CQC evidence map | GET /compliance/cqc-evidence-map | backend/server.py line 24842 | backend/routes/cqc_evidence.py line 113 | backend/routes/cqc_evidence.py | Exact duplicate path | Medium | Endpoint parity snapshot, inspection dashboard regression consuming same map | Treat modular cqc_evidence as target owner; keep inline until consumers are inventory-checked | Proceed later |
| Generated forms | POST/GET/PUT /generated-forms, GET /generated-forms/{form_id}, POST signoff, POST archive | backend/routes/generated_forms.py lines 197, 261, 282, 353, 450, 695 | backend/routes/forms.py lines 810, 859, 882, 892, 919, 959 | backend/routes/generated_forms.py | Exact duplicate paths across two modular files | High | Generated form CRUD parity, token access flow, send flow, signoff lock behavior, save-as-document regression | Freeze forms.py generated-form block as legacy shadow implementation and consolidate ownership to generated_forms only when safe | Proceed first |
| Notification logs | GET /notifications/logs | backend/routes/notifications.py line 450 | backend/routes/email_notifications.py line 399 | backend/routes/notifications.py | Exact duplicate path across two modular files | Medium | Notification log filters parity, admin auth check, response shape parity | Keep notifications.py as canonical read endpoint; stop adding features to email_notifications copy | Proceed first |
| Employee request-missing-items duplicate | POST /employees/{employee_id}/request-missing-items | backend/server.py line 34373 | backend/server.py line 38877 | Temporary: first backend/server.py definition until a dedicated notification/request owner exists | Exact duplicate path within same file | High | Request dispatch regression, duplicate-send prevention, audit trail, email request linkage, idempotency expectations | Document first definition as effective owner, diff both implementations before any extraction, do not touch until semantics are compared | Defer |
| Employee documents / evidence | Evidence family under /employees/{employee_id}/requirements/{requirement_id}/evidence, /employee-documents/*, upload-document, verification-stamp | backend/server.py lines 15894 through 21790 and line 19584 | backend/routes/documents.py, backend/routes/verifications.py, backend/routes/public_upload.py, backend/routes/verification_sync.py | Split target: backend/server.py remains temporary lifecycle owner; long-term split to documents plus verifications plus public_upload by concern | Near-duplicate lifecycle split, not one exact owner yet | High | Document upload regression, replace/delete/history/download regression, verification and stamp persistence tests, public upload token tests, sync-verification tests | Do not consolidate quickly; first define subdomain boundaries: document types/search, employee evidence lifecycle, verification checks, token upload intake | Defer |
| References | Canonical employee reference lifecycle under /references/* and /employees/{employee_id}/references/* plus integrity/mismatch flows | backend/server.py for lifecycle and integrity endpoints at lines 32572, 32721, 33944 and nearby | backend/routes/references.py, backend/routes/referee_outreach.py | backend/server.py short-term; long-term likely split between referee_outreach and references with one lifecycle owner | Mixed overlap: legacy disabled modular endpoints plus adjacent live modular routes | High | Reference create/change/send/respond/verify/reject/reset regression, mismatch override regression, PDF download regression, drift report coverage | Do not move yet; current domain is too fragmented and business-critical for safe partial extraction without full lifecycle suite | Defer |
| Worker routes | /worker/* dashboard, document upload, worker forms, worker shift/portal self-service | Modular owner already in backend/routes/worker_dashboard.py and backend/routes/shifts.py and backend/routes/auth.py for auth pieces | Adjacent overlap with public token flows and auth worker endpoints | backend/routes/worker_dashboard.py plus backend/routes/shifts.py plus backend/routes/auth.py by concern | Adjacent security-sensitive ownership boundary | High | Worker auth/login regression, worker dashboard payload regression, worker upload permissions, worker shift accept/reject regression | SECURITY-SENSITIVE. Preserve current boundaries; only document ownership, no consolidation until auth and token flows are stable | Defer |
| Auth routes | /auth/* and /worker/request-login, /worker/login, /worker/verify-login, /worker/set-password, /worker/account-status | backend/routes/auth.py | Possible indirect overlap with legacy helper logic in backend/server.py imports, but no current inline duplicate path found | backend/routes/auth.py | Canonical modular owner, security-sensitive | High | Admin login rate-limit regression, magic link login regression, password login regression, session expiry regression, role access regression | SECURITY-SENSITIVE. Do not touch yet beyond documentation and test expansion | Defer |
| Public upload / token routes | /public/validate-upload-token and /public/upload-document | backend/routes/public_upload.py | Overlaps by business flow with backend/routes/form_email.py, backend/routes/generated_forms.py token routes, backend/routes/referee_outreach.py token completion, backend/routes/auth.py worker magic links | backend/routes/public_upload.py for document-upload tokens; keep other token families owned by their existing modules | Adjacent token-surface overlap, not exact duplicate | High | Token validation expiry regression, one-time-use semantics, upload persistence test, request linkage test, unauthorized access test | SECURITY-SENSITIVE. Do not combine token systems yet; keep family boundaries explicit | Defer |
| Public upload / token routes | /forms/access/{access_token} and /forms/access/{access_token}/submit | backend/routes/generated_forms.py | Adjacent overlap with public_upload token handling and worker auth magic links | backend/routes/generated_forms.py | Adjacent token-surface overlap | High | Generated-form token access regression, submit and lock regression, expired token and forbidden edit regression | SECURITY-SENSITIVE. Keep isolated from public document upload flow | Defer |
| References public token routes | /referee/complete/{token} | backend/routes/referee_outreach.py | Adjacent overlap with public_upload and generated form token routes | backend/routes/referee_outreach.py | Adjacent token-surface overlap | High | Referee token validation, response submission, audit and anti-replay regression | SECURITY-SENSITIVE. Keep isolated from other token domains | Defer |
| Employee documents / evidence | Document types, admin document search, pending review, bulk verify | backend/routes/documents.py | backend/server.py employee document lifecycle endpoints | backend/routes/documents.py for admin/document-type functions | Adjacent namespace overlap by concern, not exact duplicate | Medium | Admin document search regression, pending review regression, bulk verify regression | Treat documents.py as canonical owner for document taxonomy and admin search, not employee evidence lifecycle | Proceed |
| Verification checks | Identity, address, RTW, verification sync | backend/routes/verifications.py and backend/routes/verification_sync.py | backend/server.py stamp and employee document verification flows, backend/routes/dbs.py | backend/routes/verifications.py and backend/routes/verification_sync.py by concern | Adjacent lifecycle overlap | Medium | Identity/address/RTW check regression, stamp persistence regression, bulk sync regression | Keep separate from evidence CRUD consolidation for now | Defer |

## Do Not Touch Yet

These route families should be treated as no-touch until broader regression coverage exists:

- Auth and worker authentication flows in backend/routes/auth.py
- Public upload and token-based document intake in backend/routes/public_upload.py
- Generated-form public token access in backend/routes/generated_forms.py
- Referee token completion in backend/routes/referee_outreach.py
- Worker self-service portal routes in backend/routes/worker_dashboard.py
- Employee evidence verification and digital stamping paths split between backend/server.py and backend/routes/verifications.py

## Recommended Initial Consolidation Sequence

1. Resolve modular-vs-modular duplicates first:
   - generated forms
   - notification logs
2. Freeze exact server-vs-module duplicate contracts paths and add parity tests.
3. Freeze training proposed-items parity and choose training_intake as target canonical read owner.
4. Freeze CQC evidence map parity and choose cqc_evidence as target canonical owner.
5. Leave references, employee evidence lifecycle, worker routes, auth, and public token flows deferred until domain regression suites are broader.

## Required Test Gate Catalogue

Before any future consolidation step in a domain, require at least:
- exact status-code parity for happy path and common failure path
- response shape parity snapshot for duplicate endpoints
- audit log parity where mutations exist
- authorization parity for admin, manager, worker, and public-token access as applicable
- one lifecycle regression that crosses domain boundaries where the route updates downstream state
