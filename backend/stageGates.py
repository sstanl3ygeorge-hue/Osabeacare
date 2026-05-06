"""
stageGates.py - Stage Gate Service

Generates requirement slots and validates stage transitions.
Uses employee_documents collection for requirement slots.
"""

import uuid
from datetime import datetime, timezone
from typing import List, Tuple, TypedDict

from role_packs import get_role_pack, get_role_requirements, get_role_policies
from role_normalization import normalize_role
from requirement_definitions import (
    get_requirement_definition,
    resolve_requirement_key,
    REQUIREMENT_DEFINITIONS,
    REQUIREMENT_ID_ALIASES,
)
from reference_matching import (
    match_employers,
    identify_most_recent_employer,
    normalize_employer,
    compliance_status_for_match,
    MATCH_REASON_LABELS,
)


# ---------------------------------------------------------------------------
# Shared reference-status enum
# ---------------------------------------------------------------------------
class ReferenceStatus:
    PENDING  = "pending"
    REQUESTED = "requested"
    RECEIVED = "received"
    VERIFIED = "verified"
    REJECTED = "rejected"


# ---------------------------------------------------------------------------
# Gate result type
# ---------------------------------------------------------------------------
class GateResult(TypedDict):
    allowed: bool
    blocking_items: list   # Each: {key, label, reason}
    warning_items: list    # Non-blocking but worth surfacing
    passed_items: list     # {key, label}
    missing_requirements: list  # requirement_key slots that were never created
    interview: dict  # Canonical interview assessment summary


class StageGateService:
    """
    Service for generating requirements and validating stage transitions.
    Uses employee_documents as the requirement-slot store.
    """
    
    def __init__(self, db):
        self.db = db

    async def get_canonical_interview_status(self, employee_id: str) -> dict:
        """
        Resolve the latest canonical interview assessment from interview_record submissions.
        """
        record = await self.db.form_submissions.find_one(
            {
                "employee_id": employee_id,
                "requirement_id": "interview_record",
            },
            {"_id": 0},
            sort=[("submitted_at", -1), ("updated_at", -1), ("created_at", -1)],
        )

        if not record:
            return {
                "exists": False,
                "completed": False,
                "passed": None,
                "score": None,
                "pass_mark": None,
                "reviewed_at": None,
                "source_record_id": None,
            }

        form_data = record.get("form_data") or record.get("data") or {}
        status = str(record.get("status") or "").lower()
        completed = status not in {"", "draft", "not_started", "in_progress"}

        decision = form_data.get("decision") or form_data.get("overall_decision")
        score = form_data.get("total_score")
        pass_mark = form_data.get("pass_score") or form_data.get("pass_mark")
        passed = form_data.get("passed")

        if isinstance(decision, str):
            decision_lc = decision.strip().lower()
            if decision_lc in {"reject", "not suitable", "fail", "failed"}:
                passed = False
            elif decision_lc in {"approve", "approved", "hire", "strong hire", "pass", "passed"}:
                passed = True

        if passed is None and score is not None:
            try:
                numeric_score = float(score)
                numeric_pass = float(pass_mark) if pass_mark is not None else 11.0
                passed = numeric_score >= numeric_pass
            except (TypeError, ValueError):
                passed = None

        return {
            "exists": True,
            "completed": bool(completed),
            "passed": passed,
            "score": score,
            "pass_mark": pass_mark,
            "reviewed_at": (
                record.get("reviewed_at")
                or record.get("verified_at")
                or record.get("signed_off_at")
                or record.get("submitted_at")
                or record.get("updated_at")
                or record.get("created_at")
            ),
            "source_record_id": record.get("id"),
        }
    
    # =========================================================================
    # REQUIREMENT GENERATION
    # =========================================================================
    
    async def generate_requirements_for_employee(
        self, 
        employee_id: str, 
        role: str,
        reference_metadata: dict = None
    ) -> List[dict]:
        """
        Generate requirement slots for an employee based on their role.
        
        Args:
            employee_id: The employee/applicant ID
            role: The role (will be normalized)
            reference_metadata: Optional dict with ref1/ref2 details from form
            
        Returns:
            List of created requirement slot documents
        """
        # Normalize role
        normalized_role = normalize_role(role)
        
        # Get role pack
        role_pack = get_role_pack(normalized_role)
        requirements = role_pack.get("requirements", [])
        policies = role_pack.get("policies", {})
        
        now = datetime.now(timezone.utc).isoformat()
        created_slots = []
        
        for req_key in requirements:
            # Skip cv, application_form, equal_opportunities - these are seeded separately
            if req_key in ["cv", "application_form", "equal_opportunities"]:
                continue
            
            # Check if slot already exists (by requirement_key)
            existing = await self.db.employee_documents.find_one({
                "employee_id": employee_id,
                "requirement_key": req_key
            })
            
            if existing:
                continue
            
            # Get requirement definition
            defn = get_requirement_definition(req_key)
            
            # Build requirement slot document
            slot = {
                "id": str(uuid.uuid4()),
                "employee_id": employee_id,
                
                # Requirement metadata
                "requirement_key": req_key,
                "requirement_type": defn.get("type", "document"),
                "document_type_name": defn.get("label", req_key),
                "category": defn.get("category", "Other"),
                
                # Role context
                "role_scope": normalized_role,
                
                # Behavior flags
                "blocking": defn.get("blocking", False),
                "supports_files": defn.get("supports_files", True),
                "supports_requests": defn.get("supports_requests", True),
                
                # Status
                "status": "not_started",
                "verified": False,
                
                # Policy (merged from definition + role policies)
                "policy": self._build_policy(req_key, defn, policies),
                
                # Metadata (for references, etc.)
                "metadata": self._build_metadata(req_key, reference_metadata),
                
                # Notes
                "notes": self._build_notes(req_key, defn),
                
                # Timestamps
                "created_at": now,
                "updated_at": now
            }
            
            await self.db.employee_documents.insert_one(slot)
            created_slots.append(slot)
        
        return created_slots
    
    def _build_policy(self, req_key: str, defn: dict, role_policies: dict) -> dict:
        """Build policy dict for a requirement"""
        policy = defn.get("policy", {}).copy()
        
        # Merge role-specific policies
        if req_key == "proof_of_address":
            policy["min_files"] = role_policies.get("poa_min_files", 2)
            policy["validity_months"] = role_policies.get("poa_validity_months", 12)
        
        if req_key == "dbs":
            policy["required_before_approval"] = role_policies.get("dbs_required_before_approval", True)
        
        return policy
    
    def _build_metadata(self, req_key: str, reference_metadata: dict) -> dict:
        """Build metadata dict for a requirement"""
        if not reference_metadata:
            return {}
        
        if req_key == "reference_1" and "ref1" in reference_metadata:
            return reference_metadata["ref1"]
        
        if req_key == "reference_2" and "ref2" in reference_metadata:
            return reference_metadata["ref2"]
        
        return {}
    
    def _build_notes(self, req_key: str, defn: dict) -> str:
        """Build initial notes for a requirement"""
        req_type = defn.get("type", "document")
        label = defn.get("label", req_key)
        
        if req_type == "reference":
            return f"{label} verification required"
        elif req_type == "document":
            return f"{label} evidence required"
        elif req_type == "form":
            return f"{label} completion required"
        elif req_type == "registration":
            return f"{label} verification required"
        else:
            return f"{label} required"
    
    # =========================================================================
    # APPLICATION COMPLETION SEEDING
    # =========================================================================
    
    async def seed_application_completion(
        self,
        employee_id: str,
        cv_file_id: str = None,
        form_submission_id: str = None
    ):
        """
        Seed the application-stage requirements as completed.
        
        Args:
            employee_id: The employee/applicant ID
            cv_file_id: The CV file ID if uploaded
            form_submission_id: The form submission ID
        """
        now = datetime.now(timezone.utc).isoformat()
        
        # CV - mark as completed if uploaded
        if cv_file_id:
            # Update the existing CV document
            await self.db.employee_documents.update_one(
                {"id": cv_file_id},
                {"$set": {
                    "employee_id": employee_id,
                    "requirement_key": "cv",
                    "requirement_id": "cv",  # Also set requirement_id for compliance file query
                    "requirement_type": "system",
                    "status": "uploaded",
                    "verified": False,
                    "updated_at": now
                }}
            )
        
        # Application form - create completed slot
        existing_app = await self.db.employee_documents.find_one({
            "employee_id": employee_id,
            "requirement_key": "application_form"
        })
        
        if not existing_app:
            defn = get_requirement_definition("application_form")
            await self.db.employee_documents.insert_one({
                "id": str(uuid.uuid4()),
                "employee_id": employee_id,
                "requirement_key": "application_form",
                "requirement_id": "application_form",  # Also set requirement_id for compliance file query
                "requirement_type": "form",
                "document_type_name": defn.get("label"),
                "category": defn.get("category"),
                "blocking": defn.get("blocking", True),
                "supports_files": False,
                "supports_requests": False,
                "status": "completed",
                "verified": False,
                "form_submission_id": form_submission_id,
                "policy": {},
                "metadata": {},
                "notes": "Application form submitted",
                "created_at": now,
                "updated_at": now
            })
        
        # Equal opportunities - create completed slot (data is in form_submissions)
        existing_eo = await self.db.employee_documents.find_one({
            "employee_id": employee_id,
            "requirement_key": "equal_opportunities"
        })
        
        if not existing_eo:
            defn = get_requirement_definition("equal_opportunities")
            await self.db.employee_documents.insert_one({
                "id": str(uuid.uuid4()),
                "employee_id": employee_id,
                "requirement_key": "equal_opportunities",
                "requirement_id": "equal_opportunities",  # Also set requirement_id for compliance file query
                "requirement_type": "form",
                "document_type_name": defn.get("label"),
                "category": defn.get("category"),
                "blocking": defn.get("blocking", False),
                "supports_files": False,
                "supports_requests": False,
                "status": "completed",
                "verified": False,
                "form_submission_id": form_submission_id,
                "policy": {},
                "metadata": {},
                "notes": "Equal opportunities data submitted with application",
                "created_at": now,
                "updated_at": now
            })
    
    # =========================================================================
    # FOLLOW-UP ITEMS BUILDER
    # =========================================================================
    
    def build_follow_up_items(self, role: str, created_slots: list) -> list:
        """
        Build the follow-up items list for the application response.
        
        Args:
            role: The normalized role
            created_slots: List of created requirement slots
            
        Returns:
            List of follow-up item dicts
        """
        items = []
        
        for slot in created_slots:
            req_key = slot.get("requirement_key")
            req_type = slot.get("requirement_type")
            label = slot.get("document_type_name", req_key)
            
            if req_type == "reference":
                items.append({
                    "type": "reference",
                    "requirement_key": req_key,
                    "description": f"{label} verification required",
                    "status": "pending"
                })
            elif req_type == "document":
                items.append({
                    "type": req_key,
                    "requirement_key": req_key,
                    "description": f"{label} evidence required",
                    "status": "required"
                })
            elif req_type == "registration":
                items.append({
                    "type": "professional_registration",
                    "requirement_key": req_key,
                    "description": f"{label} verification required",
                    "status": "verification_required"
                })
            elif req_type == "form":
                items.append({
                    "type": "form",
                    "requirement_key": req_key,
                    "description": f"{label} completion required",
                    "status": "required"
                })
        
        return items
    
    # =========================================================================
    # VALIDATION (kept simple for now)
    # =========================================================================

    # -------------------------------------------------------------------------
    # Internal: collect employment history (mirrors reference_comparison.py)
    # -------------------------------------------------------------------------
    async def _get_employment_history(self, employee_id: str, employee: dict) -> list[dict]:
        """
        Collect de-duplicated employment history from three sources,
        most authoritative first:
          1. employee.employment_history  (direct profile field)
          2. form_submissions             (application form data)
          3. employee.cv_extraction       (CV parser output)
        """
        history: list[dict] = []

        def _add(employer_name, position, start_date, end_date, is_current, source):
            if not employer_name:
                return
            norm = normalize_employer(employer_name)
            if not norm:
                return
            if any(normalize_employer(e["employer_name"]) == norm for e in history):
                return  # deduplicate
            history.append({
                "employer_name": employer_name,
                "position": position or "",
                "start_date": start_date or "",
                "end_date": end_date or "",
                "is_current": bool(is_current),
                "source": source,
            })

        # Source 1 — direct profile field
        for emp in (employee.get("employment_history") or []):
            if isinstance(emp, dict):
                _add(
                    emp.get("employer_name") or emp.get("employer") or emp.get("company") or emp.get("organisation") or "",
                    emp.get("position") or emp.get("job_title") or emp.get("role") or "",
                    emp.get("start_date") or emp.get("from") or "",
                    emp.get("end_date") or emp.get("to") or "",
                    emp.get("is_current") or emp.get("current") or False,
                    "profile",
                )

        # Source 2 — application form submission
        application = await self.db.form_submissions.find_one(
            {
                "employee_id": employee_id,
                "form_type": {"$in": ["application_form", "application", "public_application"]},
            },
            {"_id": 0, "data": 1, "form_data": 1},
        )
        if application:
            app_data = application.get("data") or application.get("form_data") or {}
            for emp in (app_data.get("employment_history") or app_data.get("employmentHistory") or []):
                if isinstance(emp, dict):
                    _add(
                        emp.get("employer_name") or emp.get("employer") or emp.get("company") or emp.get("organisation") or "",
                        emp.get("position") or emp.get("job_title") or emp.get("role") or "",
                        emp.get("start_date") or emp.get("from") or "",
                        emp.get("end_date") or emp.get("to") or "",
                        emp.get("is_current") or emp.get("current") or False,
                        "application",
                    )

        # Source 3 — CV extraction
        cv_data = employee.get("cv_extraction") or employee.get("extracted_cv_data") or {}
        for emp in (cv_data.get("employment_history") or cv_data.get("work_experience") or []):
            if isinstance(emp, dict):
                _add(
                    emp.get("employer") or emp.get("company") or emp.get("organisation") or "",
                    emp.get("position") or emp.get("title") or emp.get("role") or "",
                    emp.get("start_date") or "",
                    emp.get("end_date") or "",
                    emp.get("is_current") or False,
                    "cv",
                )

        return history

    # -------------------------------------------------------------------------
    # Internal: canonical slot resolution
    # -------------------------------------------------------------------------
    async def _resolve_slot(self, employee_id: str, req_key: str):
        """
        Find the employee_document slot for *req_key*, trying:
          1. Direct match on requirement_key (preferred — slots created by
             generate_requirements_for_employee carry this field).
          2. Fallback match on requirement_id for legacy / worker-portal docs
             that were uploaded before slot generation was wired up.
        Returns the slot dict or None.
        """
        # Primary lookup
        slot = await self.db.employee_documents.find_one({
            "employee_id": employee_id,
            "requirement_key": req_key
        })
        if slot:
            return slot

        # Fallback: any doc where requirement_id resolves to req_key
        # Pull a reasonable batch and filter in Python (avoids full collection scan)
        cursor = self.db.employee_documents.find(
            {"employee_id": employee_id},
            {"_id": 0, "id": 1, "requirement_id": 1, "requirement_key": 1,
             "verified": 1, "status": 1}
        )
        async for doc in cursor:
            resolved = resolve_requirement_key(doc.get("requirement_id", ""))
            if resolved == req_key:
                return doc
        return None

    # -------------------------------------------------------------------------
    # Internal: reference verification check (handles bool/string duality)
    # -------------------------------------------------------------------------
    def _is_reference_verified(self, employee: dict, ref_num: int) -> bool:
        """
        A reference is considered verified when:
          - employee.reference_{N}_verified is True (bool)  OR
          - the slot in employee_documents has verified=True
          - OR employee.ref{N}.verification_status == ReferenceStatus.VERIFIED
        The field can also be stored as the string 'accepted' (legacy BUG-W9).
        """
        prefix = f"reference_{ref_num}_"
        # Primary flat field (bool)
        val = employee.get(f"{prefix}verified")
        if val is True:
            return True
        # Legacy: some code wrote the string 'accepted' (bool/string mix)
        if isinstance(val, str) and val.lower() in ("true", "accepted", "verified"):
            return True
        # Nested reference object
        ref_obj = employee.get(f"ref{ref_num}") or employee.get(f"reference_{ref_num}")
        if isinstance(ref_obj, dict):
            vs = ref_obj.get("verification_status", "")
            if vs in (ReferenceStatus.VERIFIED, "accepted", "true"):
                return True
        return False

    async def _resolve_reference_slot(self, employee_id: str, ref_num: int):
        """Look up reference slot, trying both key styles."""
        return await self._resolve_slot(employee_id, f"reference_{ref_num}")

    # -------------------------------------------------------------------------
    # Internal: multi-source verification check for requirement gate
    # -------------------------------------------------------------------------
    async def _is_requirement_verified(self, employee_id: str, req_key: str) -> tuple:
        """
        Check whether a requirement is admin-verified by inspecting ALL matching
        employee_documents rows, not just the slot.

        Sources (in order of authority):
          1. Any doc with requirement_key == req_key that is verified
          2. Any doc with requirement_id in the alias list that is verified
          3. Employee-level verification flags (identity_verified,
             rtw_fully_verified, dbs_fully_verified) as a safety-net for
             documents stamped before requirement-slot generation was wired.

        A document is deemed verified when ANY of the following is true:
          - doc.verified is True
          - doc.status in ("verified", "approved")
          - doc.review_status in ("verified", "approved")
          - doc.verification_stamp is a non-empty dict with verified_by_name

        Deleted/rejected docs are excluded.

        Returns:
            (is_verified: bool, diagnostic: str)
            diagnostic values:
              "no_docs"              – no docs at all for this requirement
              "slot_unverified"      – slot exists, none verified
              "uploaded_unverified"  – worker upload exists, not yet verified
              "verified_flag"        – verified by doc.verified == True
              "verified_status"      – verified by status/review_status field
              "verified_stamp"       – verified by verification_stamp dict
              "verified_employee"    – verified by top-level employee flag
        """
        # Build alias list for this req_key
        aliases = [k for k, v in REQUIREMENT_ID_ALIASES.items() if v == req_key]

        _dead = frozenset((
            "rejected", "amendment_requested", "invalidated",
            "deleted", "superseded", "uploaded_in_error",
        ))

        # Pull all matching docs (slot + uploads)
        or_clauses = [{"requirement_key": req_key}]
        if aliases:
            or_clauses.append({"requirement_id": {"$in": aliases}})

        docs = await self.db.employee_documents.find(
            {"employee_id": employee_id, "$or": or_clauses},
            {"_id": 0, "id": 1, "requirement_key": 1, "requirement_id": 1,
             "verified": 1, "status": 1, "review_status": 1,
             "verification_stamp": 1, "verified_by_name": 1},
        ).to_list(50)

        if not docs:
            # Nothing found — check employee-level flags before giving up
            employee = await self.db.employees.find_one(
                {"id": employee_id},
                {"_id": 0, "identity_verified": 1, "rtw_fully_verified": 1,
                 "dbs_fully_verified": 1},
            )
            if employee:
                emp_flag = {
                    "identity": employee.get("identity_verified"),
                    "right_to_work": employee.get("rtw_fully_verified"),
                    "dbs": employee.get("dbs_fully_verified"),
                }.get(req_key)
                if emp_flag:
                    return True, "verified_employee"
            return False, "no_docs"

        for doc in docs:
            if (doc.get("status") or "").lower() in _dead:
                continue
            if (doc.get("review_status") or "").lower() in _dead:
                continue

            if doc.get("verified") is True:
                return True, "verified_flag"

            s = (doc.get("status") or "").lower()
            r = (doc.get("review_status") or "").lower()
            if s in ("verified", "approved") or r in ("verified", "approved"):
                return True, "verified_status"

            stamp = doc.get("verification_stamp")
            if isinstance(stamp, dict) and stamp.get("verified_by_name"):
                return True, "verified_stamp"
            if isinstance(stamp, str) and stamp.lower() in (
                "original_seen", "copy_verified", "certified_copy",
                "online_check", "verified",
            ):
                return True, "verified_stamp"

        # Docs exist but none verified — generate contextual diagnostic
        has_slot = any(d.get("requirement_key") == req_key for d in docs)
        diag = "slot_unverified" if has_slot else "uploaded_unverified"

        # Safety-net: employee-level flags
        employee = await self.db.employees.find_one(
            {"id": employee_id},
            {"_id": 0, "identity_verified": 1, "rtw_fully_verified": 1,
             "dbs_fully_verified": 1},
        )
        if employee:
            emp_flag = {
                "identity": employee.get("identity_verified"),
                "right_to_work": employee.get("rtw_fully_verified"),
                "dbs": employee.get("dbs_fully_verified"),
            }.get(req_key)
            if emp_flag:
                return True, "verified_employee"

        return False, diag

    # =========================================================================
    # RECRUITMENT GATE (single source of truth)
    # =========================================================================

    async def can_approve_recruitment(self, employee_id: str) -> Tuple[bool, List[str]]:
        """
        Backward-compat wrapper. Calls evaluate_recruitment_gate and returns
        (allowed, list_of_blocker_strings) for callers that haven't been
        updated yet.
        """
        result = await self.evaluate_recruitment_gate(employee_id)
        blocker_strings = [
            f"{b['label']}: {b['reason']}" for b in result["blocking_items"]
        ]
        return result["allowed"], blocker_strings

    async def evaluate_recruitment_gate(self, employee_id: str) -> GateResult:
        """
        Canonical recruitment approval gate.

        Returns a structured GateResult:
          allowed            – True only when blocking_items is empty
          blocking_items     – list of {key, label, reason}
          warning_items      – non-blocking issues worth surfacing
          passed_items       – list of {key, label}
          missing_requirements – requirement keys whose slot was never created
        """
        employee = await self.db.employees.find_one({"id": employee_id})
        if not employee:
            return GateResult(
                allowed=False,
                blocking_items=[{"key": "employee", "label": "Employee", "reason": "Employee record not found"}],
                warning_items=[],
                passed_items=[],
                missing_requirements=[],
                interview={
                    "exists": False,
                    "completed": False,
                    "passed": None,
                    "score": None,
                    "pass_mark": None,
                    "reviewed_at": None,
                    "source_record_id": None,
                },
            )

        role = employee.get("role", "healthcare_assistant")
        normalized_role = normalize_role(role)
        policies = get_role_policies(normalized_role)

        blocking_items = []
        warning_items = []
        passed_items = []
        missing_requirements = []

        # ------------------------------------------------------------------
        # Helper closures
        # ------------------------------------------------------------------
        def _block(key: str, reason: str):
            defn = get_requirement_definition(key)
            blocking_items.append({"key": key, "label": defn.get("label", key), "reason": reason})

        def _warn(key: str, reason: str):
            defn = get_requirement_definition(key)
            warning_items.append({"key": key, "label": defn.get("label", key), "reason": reason})

        def _pass(key: str):
            defn = get_requirement_definition(key)
            passed_items.append({"key": key, "label": defn.get("label", key)})

        def _missing(key: str):
            missing_requirements.append(key)

        # ------------------------------------------------------------------
        # 1. Document-backed requirements (RTW, Identity, PoA, DBS)
        # ------------------------------------------------------------------
        doc_keys = ["right_to_work", "identity", "proof_of_address", "dbs"]

        # Nurse adds professional registration
        if normalized_role == "nurse":
            doc_keys.extend(["nmc_registration", "clinical_competency"])

        for req_key in doc_keys:
            slot = await self._resolve_slot(employee_id, req_key)

            if slot is None:
                _missing(req_key)
                _block(req_key, "Requirement slot not found — documents may not have been linked to this applicant")
                continue

            defn = get_requirement_definition(req_key)
            needs_verification = defn.get("verification_required", True)

            if needs_verification:
                is_verified, diag = await self._is_requirement_verified(employee_id, req_key)
                if not is_verified:
                    # Surface a contextual reason rather than a generic string so
                    # admins can diagnose quickly without digging in the DB.
                    _diag_reasons = {
                        "no_docs":            "No document found — file upload required",
                        "slot_unverified":    "Document slot exists but not yet verified by admin — open the compliance panel and complete verification",
                        "uploaded_unverified":"Document uploaded but not yet reviewed and verified by admin",
                    }
                    reason = _diag_reasons.get(diag, "Not yet verified by admin")
                    _block(req_key, reason)
                else:
                    _pass(req_key)
            else:
                _pass(req_key)

        # ------------------------------------------------------------------
        # 2. Proof of Address — quantity rule (≥2 verified files)
        # ------------------------------------------------------------------
        poa_slot = await self._resolve_slot(employee_id, "proof_of_address")
        if poa_slot:
            min_files = policies.get("poa_min_files", 2)
            # Count all docs that resolve to proof_of_address and are verified.
            # Accept verified=True OR status/review_status "verified"/"approved"
            # so the count matches the compliance-file's is_document_verified_with_stamp().
            poa_docs = await self.db.employee_documents.count_documents({
                "employee_id": employee_id,
                "$and": [
                    {
                        "$or": [
                            {"requirement_key": "proof_of_address"},
                            {"requirement_id": {"$regex": "proof_of_address", "$options": "i"}},
                            {"requirement_id": {"$regex": "^poa", "$options": "i"}},
                        ]
                    },
                    {
                        "status": {"$nin": [
                            "rejected", "amendment_requested", "invalidated",
                            "deleted", "superseded", "uploaded_in_error",
                        ]}
                    },
                    {
                        "$or": [
                            {"verified": True},
                            {"status": {"$in": ["verified", "approved"]}},
                            {"review_status": {"$in": ["verified", "approved"]}},
                            {"verification_stamp": {
                                "$nin": [None, "", "not_verified"],
                                "$not": {"$type": "null"}
                            }},
                        ]
                    },
                ]
            })
            if poa_docs < min_files:
                # Re-use existing block or add a separate warning
                already_blocked = any(b["key"] == "proof_of_address" for b in blocking_items)
                if not already_blocked:
                    _block(
                        "proof_of_address",
                        f"Requires {min_files} verified Proof of Address documents (found {poa_docs})"
                    )
                    # Remove the _pass we may have added above
                    passed_items[:] = [p for p in passed_items if p["key"] != "proof_of_address"]

        # ------------------------------------------------------------------
        # 3. References
        #    Layer A — Verification: has admin reviewed the actual reference?
        #    Layer B — Employment cross-check: does the referee's employer
        #              appear in the declared employment history?
        #              (uses shared reference_matching helpers — same logic as
        #               the /reference-employment-comparison API endpoint)
        # ------------------------------------------------------------------
        employment_history = await self._get_employment_history(employee_id, employee)
        most_recent_norm = identify_most_recent_employer(employment_history)

        # CQC-aligned rule (replaces "both refs must match"):
        #   * At least ONE referee must match the worker's most-recent employer.
        #   * The other referee may match an earlier employer OR be a
        #     character/personal referee, PROVIDED an override_reason is
        #     recorded explaining why the referee does not match the
        #     declared employment history.
        #   * If NEITHER referee matches the most-recent employer, the gate
        #     blocks once at the references level until a matching referee is
        #     supplied — silent overrides are not enough on their own.
        any_matched_most_recent = False
        any_admin_accepted_recent_exception = False
        ref_summary: list[dict] = []

        for ref_num in [1, 2]:
            ref_key = f"reference_{ref_num}"
            ref_slot = await self._resolve_reference_slot(employee_id, ref_num)

            if ref_slot is None:
                _missing(ref_key)
                _block(ref_key, "Reference slot not found")
                continue

            # --- Layer A: verification status ---
            verified = self._is_reference_verified(employee, ref_num)
            if not verified:
                ref_obj = employee.get(f"ref{ref_num}") or employee.get(f"reference_{ref_num}", {}) or {}
                status = ref_obj.get("verification_status", "")
                if status in (ReferenceStatus.RECEIVED,):
                    _warn(ref_key, "Reference received but not yet verified by admin")
                else:
                    _block(ref_key, "Reference not verified — response evidence required before approval")
                # Don't bail: still run cross-check so the full picture is visible

            # --- Layer B: employment cross-check ---
            ref_company = (
                employee.get(f"reference_{ref_num}_company") or
                (ref_slot.get("metadata") or {}).get("organisation") or
                ""
            )
            override_reason = employee.get(f"reference_{ref_num}_override_reason") or None

            ref_state = {
                "key": ref_key,
                "ref_num": ref_num,
                "company": ref_company,
                "matched": False,
                "is_most_recent": False,
                "has_override_reason": bool(override_reason),
                "recent_mismatch_exception_accepted": False,
            }

            if ref_company:
                matched, matching_employer, match_reason = match_employers(ref_company, employment_history)

                is_most_recent = False
                if matched and matching_employer and most_recent_norm:
                    emp_norm = normalize_employer(matching_employer.get("employer_name") or "")
                    is_most_recent = (emp_norm == most_recent_norm)

                ref_state["matched"] = matched
                ref_state["is_most_recent"] = is_most_recent

                mismatch_obj = (ref_slot.get("mismatch") or {}) if isinstance(ref_slot, dict) else {}
                recent_exception_accepted = bool(
                    mismatch_obj.get("resolved")
                    or str(mismatch_obj.get("admin_decision") or "").lower() == "accepted"
                    or str(employee.get(f"reference_{ref_num}_mismatch_admin_decision") or "").lower() == "accepted"
                    or employee.get(f"reference_{ref_num}_mismatch_override_reason")
                )
                ref_state["recent_mismatch_exception_accepted"] = recent_exception_accepted

                if is_most_recent:
                    any_matched_most_recent = True
                elif matched and verified and recent_exception_accepted:
                    # Explicit admin acceptance for a non-most-recent employer match:
                    # this is a documented exception path (CQC/NHS audit-traceable)
                    # and should satisfy the aggregate most-recent rule.
                    any_admin_accepted_recent_exception = True

                reason_label = MATCH_REASON_LABELS.get(match_reason, match_reason)

                if not matched and not override_reason:
                    # NHS/CQC dynamic rule:
                    # - If at least one referee matches the most-recent employer,
                    #   an additional unmatched referee is a documentation warning.
                    # - Hard block is applied once at the aggregate level below
                    #   ONLY when none of the referees match the most-recent employer.
                    _warn(
                        ref_key,
                        f"Reference employer '{ref_company}' not found in declared employment history — "
                        "record explanation or replace referee per NHS guidance"
                    )
                elif matched and not is_most_recent:
                    matched_name = (matching_employer or {}).get("employer_name", "")
                    _warn(
                        ref_key,
                        f"Reference employer '{ref_company}' matches an earlier employer "
                        f"('{matched_name}', {reason_label}), not the most-recent — "
                        "verify and record explanation per NHS guidance"
                    )
                elif not matched and override_reason:
                    _warn(
                        ref_key,
                        f"Reference employer '{ref_company}' has no employment-history match, "
                        f"but an explanation has been recorded: {override_reason}"
                    )
                else:
                    # matched AND is_most_recent — pass if Layer A also passed
                    if verified and not any(b["key"] == ref_key for b in blocking_items):
                        _pass(ref_key)
            else:
                # No company declared — can't run cross-check; if verified, accept it
                if verified and not any(b["key"] == ref_key for b in blocking_items):
                    _pass(ref_key)

            ref_summary.append(ref_state)

        # CQC cross-reference rule: if at least one referee was declared but
        # NONE matched the most-recent declared employer, block at the
        # references level. We only enforce this when employment history is
        # known and at least one referee has a company declared, so an
        # empty-state employee doesn't get a confusing message.
        any_company_declared = any(r["company"] for r in ref_summary)
        if (
            employment_history
            and most_recent_norm
            and any_company_declared
            and not any_matched_most_recent
            and not any_admin_accepted_recent_exception
            and not any(b["key"] == "references_most_recent_employer" for b in blocking_items)
        ):
            _block(
                "references_most_recent_employer",
                "At least one reference must come from the most-recent declared "
                "employer (NHS Employment Check Standards). Replace one of the "
                "referees or document why no referee from that employer can be "
                "obtained before approval."
            )

        # ------------------------------------------------------------------
        # 4. Interview (canonical interview_record source)
        # ------------------------------------------------------------------
        interview = await self.get_canonical_interview_status(employee_id)
        if not interview.get("exists"):
            _block("interview_record", "No interview assessment record found")
        elif not interview.get("completed"):
            _block("interview_record", "Interview record exists but is still draft/incomplete")
        elif interview.get("passed") is False:
            _block("interview_record", "Interview outcome is failed")
        elif interview.get("passed") is None:
            _warn("interview_record", "Interview completed but no pass/fail outcome is recorded")
        else:
            _pass("interview_record")

        # ------------------------------------------------------------------
        # 5. Employment history / 10-year gap review
        # ------------------------------------------------------------------
        emp_history = employee.get("employment_history", [])
        if not emp_history:
            _warn("employment_history", "No employment history entries recorded")
        else:
            unexplained = [
                e for e in emp_history
                if e.get("is_gap") and e.get("verification_status") not in ("explained", "verified")
            ]
            if unexplained:
                _warn("employment_history", f"{len(unexplained)} unexplained employment gap(s)")
            else:
                _pass("employment_history")

        # ------------------------------------------------------------------
        # 6. Application form (basic check — must be submitted)
        # ------------------------------------------------------------------
        app_form_slot = await self._resolve_slot(employee_id, "application_form")
        if not app_form_slot or app_form_slot.get("status") not in ("completed", "submitted", "verified"):
            _warn("application_form", "Application form not marked as completed")
        else:
            _pass("application_form")

        # ------------------------------------------------------------------
        # 7. CV / Resume (soft-mandatory supporting evidence)
        #    Required for interview + hiring progression. CV must NOT
        #    populate employment history — that comes from the application
        #    form + gap review. Truth source mirrors the
        #    /api/worker/cv-extraction-status endpoint.
        # ------------------------------------------------------------------
        cv_document_id = employee.get("cv_document_id")
        cv_status_value = (employee.get("cv_status") or "").lower()
        cv_replacement_required = cv_status_value in {
            "rejected", "replacement_requested", "missing", "replacement_required"
        }
        cv_present = False
        if cv_document_id and not cv_replacement_required:
            cv_doc = await self.db.employee_documents.find_one({"id": cv_document_id})
            if cv_doc:
                doc_status = (cv_doc.get("status") or "").lower()
                cv_present = (
                    bool(cv_doc.get("file_url"))
                    and doc_status not in {"superseded", "archived", "deleted", "rejected", "invalidated"}
                    and cv_doc.get("is_active") is not False
                )
        if not cv_present:
            if cv_replacement_required:
                cv_reason = "CV was rejected — applicant must upload a replacement before progressing"
            elif cv_document_id:
                cv_reason = "CV is no longer on file — applicant must re-upload before progressing"
            else:
                cv_reason = "CV / Resume not uploaded — required before interview or hiring approval"
            _block("cv", cv_reason)
        else:
            _pass("cv")

        # ------------------------------------------------------------------
        # Final verdict
        # ------------------------------------------------------------------
        return GateResult(
            allowed=len(blocking_items) == 0,
            blocking_items=blocking_items,
            warning_items=warning_items,
            passed_items=passed_items,
            missing_requirements=missing_requirements,
            interview=interview,
        )

