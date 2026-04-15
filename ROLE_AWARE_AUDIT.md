# Role-Aware Requirements Audit
**Date:** Phase 17 — Post Phase 16 Fixes  
**Scope:** All backend surfaces — compliance engine, work readiness, role packs, interview questions, worker dashboard, server.py

---

## 1. System Architecture Overview

There are **two separate compliance calculation paths** running in parallel:

| Path | Function | Used By | Role Awareness |
|---|---|---|---|
| **Server.py** | `calculate_employee_compliance()` → `get_mandatory_items_for_role()` | Most admin endpoints, employee profiles, dashboard | Nurse + Manager + HCA (care cert) |
| **Unified Engine** | `get_unified_employee_status()` from `unified_compliance_engine.py` | Worker dashboard, some admin views (compliance panel) | Nurse only |

These two paths produce **different gate counts** for the same employee — a known architectural divergence.

---

## 2. Role Definitions Across All Surfaces

### 2a. Roles With Full Config (all surfaces aligned):
| Role | work_readiness | role_packs | interview | unified_engine | server.py |
|---|---|---|---|---|---|
| `healthcare_assistant` | ✅ | ✅ HCA pack | ✅ 8Q | ✅ (base, no extras) | ✅ + care_cert |
| `nurse` | ✅ | ✅ Nurse pack | ✅ 14Q | ✅ NMC + indemnity gate | ✅ nurse_specific (6 items) |
| `care_assistant` | → HCA fallback | ✅ pack exists | ✅ 8Q | ✅ (base) | ✅ + care_cert |
| `senior_care_assistant` | → HCA fallback | ✅ pack exists | ✅ 8Q | ✅ (base) | ✅ |
| `support_worker` | ✅ | ✅ pack exists | ✅ 8Q | ✅ (base) | ✅ + care_cert |

### 2b. Roles With Partial Config (fall-through gaps):
| Role | work_readiness | role_packs | interview | Notes |
|---|---|---|---|---|
| `senior_carer` | ✅ in ROLE_WORK_REQUIREMENTS | ❌ NO pack → HCA | ✅ 8Q | Pack fallback is safe (same reqs as HCA) |
| `senior_healthcare_assistant` | ❌ NO entry → HCA fallback | ❌ NO pack → HCA | ✅ 8Q | Falls through silently |
| `live_in_carer` | ❌ NO entry → HCA fallback | ❌ NO pack → HCA | ✅ 8Q | Falls through silently |
| `night_carer` | ❌ NO entry → HCA fallback | ❌ NO pack → HCA | ✅ 8Q | Falls through silently |
| `team_leader` | ❌ NO entry → HCA fallback | ❌ NO pack → HCA | ✅ 8Q (NOT manager) | No leadership-specific checks |
| `care_coordinator` | ❌ NO entry → HCA fallback | ❌ NO pack → HCA | ✅ 8Q (NOT manager) | No coordination-specific checks |

### 2c. Roles With Config Only in server.py (no role_pack, no work_readiness entry):
| Role | server.py | role_packs | work_readiness | interview |
|---|---|---|---|---|
| `manager` / `registered_manager` | ✅ manager_specific (fit_proper_persons) | ❌ NO pack → HCA | ❌ NO entry | ❌ 8Q support worker Qs |
| `director` / `nursing_director` | ✅ manager_specific (fit_proper_persons) | ❌ NO pack → HCA | ❌ NO entry | ❌ 8Q support worker Qs |
| `doctor` | ❌ NO MANDATORY_ITEMS entry | ❌ NO pack → HCA | ❌ NO entry | ❌ 8Q support worker Qs |

---

## 3. Per-Requirement Role Enforcement Matrix

### Core clinical/registration requirements
| Requirement | unified_engine gate | server.py calc | work_readiness | role_packs slot | interview |
|---|---|---|---|---|---|
| NMC registration (nurse) | ✅ blocker | ✅ nurse_specific | ✅ ROLE_WORK_REQUIREMENTS | ✅ nurse pack | ✅ nurse_q6 critical |
| Professional indemnity (nurse) | ✅ blocker | ✅ nurse_specific | ✅ ROLE_WORK_REQUIREMENTS | ❌ **NOT in nurse pack** | — |
| Clinical competency (nurse) | ❌ **not checked** | ✅ nurse_specific | ✅ ROLE_WORK_REQUIREMENTS | ✅ nurse pack | ✅ nurse_q2 |
| Medication competency (nurse) | ❌ **not checked** | ✅ nurse_specific | ❌ **not in ROLE_WORK_REQUIREMENTS** | ❌ **not in any pack** | ✅ nurse_q4 critical |
| Hep B / OHC clearance (nurse) | ❌ **not checked** | ✅ get_work_ready_items (Hep B + OHC) | ❌ not in ROLE_WORK_REQUIREMENTS | ❌ **not in any pack** | — |
| GMC registration (doctor) | ✅ ROLE_SPECIFIC_REQUIREMENTS | ❌ **no doctor MANDATORY_ITEMS entry** | ROLE_REGISTRATION_REQUIREMENTS ✅ | ❌ **no doctor pack** | — |
| fit_proper_persons (manager) | ❌ **not in unified engine** | ✅ manager_specific | ❌ no manager work_readiness | ❌ **no manager pack** | — |
| care_certificate (HCA) | ❌ **not in unified engine** | ✅ care_certificate group | ✅ ROLE_WORK_REQUIREMENTS | — | — |

---

## 4. Proven Bugs (Actionable)

---

### BUG 1 — `professional_indemnity` not in nurse role_pack (MEDIUM)
**Location:** `backend/role_packs.py` — nurse pack definition  
**Evidence:**  
- `MANDATORY_ITEMS["nurse_specific"]` includes `professional_indemnity` (server.py)  
- `unified_compliance_engine.py` line 174: `{"id": "professional_indemnity", ...}` in nurse `ROLE_SPECIFIC_REQUIREMENTS` — it IS a gate  
- `work_readiness_engine.py` `ROLE_WORK_REQUIREMENTS["nurse"]` includes `professional_indemnity` in documents  
- BUT `role_packs.py` nurse pack does NOT include a `professional_indemnity` requirement slot  

**Impact:** Nurse applicants processed through `stageGates.py` at intake never get a `professional_indemnity` slot created. The compliance gate exists but no slot to upload against.

**Fix:** Add `professional_indemnity` to `ROLE_PACK_NURSE` in `role_packs.py`.

---

### BUG 2 — `medication_competency` declared for nurses but never enforced as a gate (MEDIUM)
**Location:** `server.py` `MANDATORY_ITEMS["nurse_specific"]`, `unified_compliance_engine.py`, `work_readiness_engine.py`  
**Evidence:**  
- `server.py` `MANDATORY_ITEMS["nurse_specific"]`: `{"id": "medication_competency", ..., "priority": "supervised_start"}` — it's there  
- `unified_compliance_engine.py`: ZERO mentions of `medication_competency`  
- `work_readiness_engine.py` `ROLE_WORK_REQUIREMENTS["nurse"]["documents"]`: lists `nmc_registration`, `clinical_competency`, `professional_indemnity` — **no** `medication_competency`  
- `role_packs.py` nurse pack: **no** `medication_competency` slot

**Impact:** `medication_competency` shows in admin compliance view (via `calculate_employee_compliance`) as an item, but:
1. Worker dashboard never shows it as a requirement (unified engine ignores it)
2. Work readiness gate is never blocked by it
3. Nurses are never prevented from starting without it

**Fix options:**  
A. Add `medication_competency` to `ROLE_WORK_REQUIREMENTS["nurse"]["documents"]` in `work_readiness_engine.py`  
B. Add `medication_competency` to `ROLE_SPECIFIC_REQUIREMENTS["nurse"]` in `unified_compliance_engine.py`  
C. Both (recommended for full gate coverage)

---

### BUG 3 — `clinical_competency` not enforced by unified compliance engine (MEDIUM)
**Location:** `unified_compliance_engine.py`  
**Evidence:**  
- `server.py` `MANDATORY_ITEMS["nurse_specific"]`: includes `clinical_competency` ✅  
- `work_readiness_engine.py` `ROLE_WORK_REQUIREMENTS["nurse"]["documents"]`: includes `clinical_competency` ✅  
- `role_packs.py` nurse pack: includes `clinical_competency` slot ✅  
- `unified_compliance_engine.py` `ROLE_SPECIFIC_REQUIREMENTS["nurse"]`: only `nmc_registration` and `professional_indemnity` — **no `clinical_competency`**  

**Impact:** Worker-facing compliance (unified engine) never shows clinical competency as a gate. Nurse can be "compliant" per unified engine without clinical competency. Only admin-side `calculate_employee_compliance` catches it.

**Fix:** Add `{"id": "clinical_competency", "name": "Clinical Competency Assessment", "type": "document"}` to `ROLE_SPECIFIC_REQUIREMENTS["nurse"]` in `unified_compliance_engine.py`.

---

### BUG 4 — `fit_proper_persons` not enforced by unified compliance engine for managers (LOW)
**Location:** `unified_compliance_engine.py`  
**Evidence:**  
- `server.py` `MANDATORY_ITEMS["manager_specific"]`: includes `fit_proper_persons` ✅  
- `server.py` `FORM_BASED_REQUIREMENTS["fit_proper_persons"]`: `role_aware: True, roles_required: [...]` ✅  
- `server.py` `get_work_ready_items_for_role()`: adds `fit_proper_persons` for manager roles ✅  
- `unified_compliance_engine.py`: `fit_proper_persons` does NOT appear anywhere  
- `unified_compliance_engine.py` `REQUIRED_FORMS`: only 5 forms — `conflict_of_interest` and `fit_proper_persons` are both absent  

**Impact:** If a registered manager or director also exists as a worker (e.g., working manager), their unified-engine compliance view never surfaces the CQC Regulation 5 requirement. It only appears in admin-side compliance calculations.

**Fix:** Add manager detection + `fit_proper_persons` gate to `unified_compliance_engine.py` (similar to how `is_nurse` is handled).

---

### BUG 5 — No role pack for manager/director roles → `fit_proper_persons` slot never created at intake (MEDIUM)
**Location:** `backend/role_packs.py`  
**Evidence:**  
- `role_packs.py` `ROLE_PACKS` dict has no entry for `"manager"`, `"registered_manager"`, `"director"`, `"nursing_director"`  
- `stageGates.py` `generate_requirements_for_employee()` calls `get_role_pack(normalized_role)` → falls back to `ROLE_PACK_HEALTHCARE_ASSISTANT`  
- HCA pack has no `fit_proper_persons` slot  
- Result: Manager applicant at intake gets HCA requirement slots — no CQC Regulation 5 slot created  

**Fix:** Add `ROLE_PACK_MANAGER` to `role_packs.py` with `fit_proper_persons` requirement, and register it in `ROLE_PACKS` under `"manager"`, `"registered_manager"`, `"director"`, `"nursing_director"`, `"operations_manager"`.

---

### BUG 6 — `doctor` role has a GMC gate in unified engine but no MANDATORY_ITEMS entry and no role pack (LOW)
**Location:** `unified_compliance_engine.py` vs `server.py` vs `role_packs.py`  
**Evidence:**  
- `unified_compliance_engine.py` `ROLE_SPECIFIC_REQUIREMENTS["doctor"]`: `{"id": "gmc_registration", ...}` — gate exists ✅  
- `server.py` `MANDATORY_ITEMS`: no `doctor_specific` equivalent — `calculate_employee_compliance` never adds GMC for doctors  
- `role_packs.py`: no doctor pack — doctors get HCA slots  
- `work_readiness_engine.py` `ROLE_REGISTRATION_REQUIREMENTS`: `"doctor": {"body": "General Medical Council (GMC)", "required": True}` ✅  
- `work_readiness_engine.py` `ROLE_WORK_REQUIREMENTS`: no `"doctor"` key — falls to HCA requirements  

**Impact:** Doctor compliance is partially tracked (unified engine GMC gate) but:
1. Admin-side `calculate_employee_compliance` never adds GMC to the doctor's mandatory items
2. No GMC upload slot is ever created at intake
3. Work readiness requirements use HCA list (no clinical competency requirement for doctor)

**Fix:** Add `doctor_specific` to `MANDATORY_ITEMS`, a doctor pack to `role_packs.py`, and a `"doctor"` key to `ROLE_WORK_REQUIREMENTS`.

---

## 5. Gaps (Structural, Not Immediate Bugs)

### GAP 1 — Two compliance engines give different total gate counts
**Status:** Known architectural issue.  
- Worker sees `unified_compliance_engine` (33 base + 1 for nurse = 34)
- Admin sees `calculate_employee_compliance` (base + training + nurse_specific 6 items + optional others)
- Same employee, different numbers on different views

This is not a crash bug but creates audit inconsistency. Tracked as a future unification task.

### GAP 2 — Hep B and OHC clearance not gate-checked by unified engine
- `get_work_ready_items_for_role()` adds them for nurses ✅  
- `unified_compliance_engine.py` never checks `hepatitis_b_status` or `occupational_health_clearance` for nurses  
- These show in admin list (via mandatory items) but worker sees no gate for them

### GAP 3 — `care_certificate_progress` not tracked by unified engine  
- HCA care certificate only tracked by `calculate_employee_compliance` (admin-facing)  
- Worker dashboard (unified engine) never surfaces care certificate as a pending gate

### GAP 4 — Role normalization patterns differ across surfaces
| Surface | Pattern |
|---|---|
| `unified_compliance_engine.py` | `"nurse" in role` (substring, line 1323) |
| `work_readiness_engine.py` | `normalize_role_for_work()` → explicit dict (Phase 16 fixed) |
| `server.py is_nurse_role()` | `system_role == SystemRole.NURSE` (via `normalize_to_system_role()`) |
| `worker_dashboard.py` line 1144 | `"nurse" in job_role or "midwife" in job_role` (substring) |
| `interview_questions.py` | explicit dict with all variants |

All four patterns cover `"nurse"` substring cases correctly after Phase 16 fixes. However, they are inconsistent in how they handle midwives, doctors (physician/consultant), and HCPC-regulated roles. No immediate bug but fragile.

### GAP 5 — `conflict_of_interest` form never enforced as compliance gate
- Defined in `FORM_BASED_REQUIREMENTS` with `role_aware: False`  
- NOT in `unified_compliance_engine.py` `REQUIRED_FORMS`  
- NOT in `MANDATORY_ITEMS`  
- Exists as a standalone form but not contributing to any compliance count  

---

## 6. Recommended Fix Priority

| Priority | Bug/Gap | File(s) | Risk |
|---|---|---|---|
| HIGH | BUG 1 — `professional_indemnity` missing from nurse role pack | `role_packs.py` | New nurses at intake missing indemnity slot |
| HIGH | BUG 3 — `clinical_competency` not in unified engine nurse gate | `unified_compliance_engine.py` | Workers see wrong compliance picture |
| MEDIUM | BUG 2 — `medication_competency` not enforced as gate | `unified_compliance_engine.py`, `work_readiness_engine.py` | Nurses work without medication competency |
| MEDIUM | BUG 5 — No manager role pack → no `fit_proper_persons` slot at intake | `role_packs.py` | CQC Regulation 5 slot never created |
| LOW | BUG 4 — `fit_proper_persons` not in unified engine for managers | `unified_compliance_engine.py` | Low risk if managers don't use worker portal |
| LOW | BUG 6 — No doctor role pack or MANDATORY_ITEMS entry | `role_packs.py`, `server.py` | Doctors get HCA slots only |
| FUTURE | GAP 1 — Two-engine architecture produces different counts | Architectural | Track separately |
| FUTURE | GAP 2/3 — Hep B, OHC, care_cert missing from unified engine | `unified_compliance_engine.py` | Admin-worker discrepancy |

---

## 7. What IS Consistent (No Action Needed)

- ✅ NMC registration gate — all 4 surfaces enforce it for nurses  
- ✅ Nurse interview questions — 14Q (8 base + 6 clinical) consistently routed  
- ✅ Phase 16 fixes — all nurse role variants now correctly normalize across all 3 normalization paths  
- ✅ `fit_proper_persons` correctly declared as `role_aware: True` with `roles_required` in `FORM_BASED_REQUIREMENTS`  
- ✅ `ROLE_REGISTRATION_REQUIREMENTS` covers all regulated professions (NMC, GMC, HCPC, SWE)  
- ✅ Interview question routing correctly handles all named role variants via explicit dict in `get_interview_questions_for_role()`  
- ✅ `calculate_employee_compliance` manager role check handles `"Registered Manager".lower().replace(" ", "_") = "registered_manager"` correctly  

---

## 8. Fixes Approved in Previous Phases

| Phase | Fix | Status |
|---|---|---|
| Phase 16 | `ApplicationDeclarations` model — added 4 professional registration fields | ✅ Applied |
| Phase 16 | `SYSTEM_ROLE_MAP` — added nurse variants (Nurse (Registered), Senior Nurse, etc.) | ✅ Applied |
| Phase 16 | `normalize_role_for_work()` — added nurse variants | ✅ Applied |
