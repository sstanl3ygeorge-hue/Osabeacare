# Whistleblowing Policy Rendering MVP Spec

## 1. Goal

Move Whistleblowing Policy from file-upload-only to company-owned rendered policy.

Current state:
- Policy records are created and managed via API/UI.
- Policy file is uploaded as a static document.
- Review date is driven by upload workflow and external document text.

Target state:
- Admin edits policy content in-app.
- System renders branded PDF.
- Policy versioning and review cadence are managed internally.
- Assignment and acknowledgement continue to work as-is.

## 2. Existing Assets To Reuse

Frontend:
- Policy page CRUD/upload/assign flow exists in frontend/src/pages/portal/PoliciesPage.js.

Backend policy endpoints already exist:
- Create/list/upload/assign in backend/routes/policies.py.
- Compliance policy endpoints and review metadata logic in backend/routes/compliance.py.
- Assignment lifecycle in backend/routes/policy_assignments.py.

Template/form rendering pattern already exists:
- Form editor workflow in frontend/src/pages/portal/FormEditorPage.js.
- Generated form pipeline in backend/routes/generated_forms.py.

## 3. MVP Scope (Whistleblowing Only)

In scope:
- One renderable policy template: Whistleblowing.
- Admin can create/edit draft content.
- Admin can publish a version.
- Publish generates a PDF artifact.
- Existing assignment and acknowledgement flows use the published PDF.
- Review date is calculated from policy metadata, not external vendor text.

Out of scope (phase 2+):
- All other policies/templates.
- Rich WYSIWYG editor.
- Multi-language policy packs.

## 4. Data Model (MVP)

Add one collection: policy_templates

Document shape (MVP):
- id: string (uuid)
- policy_key: string (example: whistleblowing)
- company_id: string or null (single-tenant can be null)
- status: draft | published | archived
- version: integer
- title: string
- module: string (example: Safeguarding)
- owner_name: string
- effective_date: ISO date
- review_period_months: integer (default 12)
- next_review_date: ISO date
- content: object
	- purpose
	- principles
	- scope
	- procedure
	- protections
	- exclusions
	- responsibilities
	- references
- render_artifact_url: string or null
- render_artifact_filename: string or null
- published_at: ISO datetime or null
- published_by: string or null
- created_at, created_by, updated_at, updated_by

Optional extension (recommended):
- source_policy_id: existing org policy id for migration linkage

## 5. API Endpoints (New)

Prefix all with /api/policy-templates

1) GET /api/policy-templates
- Filters: policy_key, status
- Returns list summaries.

2) GET /api/policy-templates/{template_id}
- Returns full draft/published content.

3) POST /api/policy-templates
- Creates draft template record.
- Role: admin.

4) PUT /api/policy-templates/{template_id}
- Edits draft content and metadata.
- Role: admin.
- If status == published, require clone workflow or create v+1 draft.

5) POST /api/policy-templates/{template_id}/publish
- Validates required fields.
- Computes next_review_date = effective_date + review_period_months.
- Renders PDF artifact.
- Marks status published.
- Stores render_artifact_url.

6) GET /api/policy-templates/{template_id}/pdf
- Streams rendered PDF inline.

7) POST /api/policy-templates/{template_id}/new-version
- Creates draft from current published version with incremented version.

## 6. API Integration With Existing Policy Records

Keep existing org policy table for compatibility.

Add fields to org_policies:
- source_type: uploaded_file | rendered_template
- source_template_id: nullable
- file_url continues to be used by assignment viewer

Publish behavior:
- When Whistleblowing template is published, sync corresponding org policy row:
	- file_url = render_artifact_url
	- version = v{template.version}
	- review_date = next_review_date
	- status = active
	- notes = published from rendered template

Result:
- Existing assignment/ack/admin-review endpoints continue working unchanged.

## 7. UI Changes (MVP)

Page: frontend/src/pages/portal/PoliciesPage.js

A) Policy card actions
- Keep Upload/Replace for legacy mode.
- Add button: Edit Template (for Whistleblowing card only in MVP).
- Add badge: Rendered or Uploaded.

B) Template editor dialog/page
- Metadata fields:
	- Policy Name
	- Module
	- Owner
	- Effective Date
	- Review period (months)
- Content sections textareas:
	- Statement of purpose
	- Principles
	- Scope
	- Procedure
	- Protections
	- Exclusions
	- Responsibilities
	- References
- Actions:
	- Save Draft
	- Preview PDF
	- Publish Version

C) Viewer
- Existing view policy action should open rendered PDF via current file endpoint path.

## 8. Rendering Strategy

Backend service:
- New helper module: backend/services/policy_render_service.py

Input:
- template metadata + content sections

Output:
- PDF bytes with:
	- company logo/name from org config
	- policy header table (name/module/version)
	- structured sections
	- footer with effective date + review date + version

Storage:
- Reuse existing storage helper used by policy upload or generated forms.

## 9. Validation Rules

On publish, require:
- title, module, owner_name
- effective_date
- review_period_months > 0
- purpose, scope, procedure non-empty

Date rule:
- next_review_date must be computed, not manually typed.

Version rule:
- published version immutable.
- edits require new draft version.

## 10. Audit Trail

Log actions:
- create_policy_template
- update_policy_template
- publish_policy_template
- create_policy_template_version

Include before/after for metadata fields and content hash.

## 11. Migration Plan (Whistleblowing First)

1) Identify existing Whistleblowing policy in org_policies.
2) Extract title/category/version and set first draft content.
3) Admin reviews and publishes v1.
4) System syncs org_policies row to rendered artifact.
5) Existing assignments keep working via existing policy file pathways.

## 12. Rollout Plan

Phase 1 (MVP): Whistleblowing only
- Build template model + endpoints + editor + renderer.

Phase 2: Core policies batch
- Safeguarding Adults
- Safeguarding Children
- Medication
- Infection Prevention & Control
- Incident Reporting
- Lone Working

Phase 3: Full CQC Expert library
- Bulk mapping table from purchased templates to UI placement.
- Convert per policy/form type.

## 13. Acceptance Criteria

1) Admin can edit Whistleblowing policy content in-app.
2) Admin can publish and generate PDF.
3) Published policy appears in current Policy Centre and is viewable.
4) Assignment + acknowledgement flow works without regression.
5) Review date is system-managed from metadata.
6) New version can be created without overwriting previous published artifact.

## 14. Risks And Mitigations

Risk: Breaking current assignment flow.
Mitigation: Keep org_policies + policy_assignments contract unchanged and only sync rendered artifact URL.

Risk: Inconsistent legal wording edits.
Mitigation: enforce publish approval role and keep immutable version history.

Risk: Review dates diverging from policy content.
Mitigation: render footer from system metadata only.

## 15. Next Implementation Task List

1) Create backend/services/policy_render_service.py.
2) Create backend/routes/policy_templates.py with endpoints above.
3) Register new router in backend/server.py.
4) Add source_type/source_template_id support in policy payloads.
5) Add editor UI in frontend/src/pages/portal/PoliciesPage.js (or dedicated page).
6) Add publish action and sync to org_policies.
7) Add tests:
	 - API create/update/publish/version
	 - PDF generation non-empty and metadata fields present
	 - Assignment compatibility regression

