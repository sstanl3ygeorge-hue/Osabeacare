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


class StageGateService:
    """
    Service for generating requirements and validating stage transitions.
    Uses employee_documents as the requirement-slot store.
    """
    
    def __init__(self, db):
        self.db = db
    
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
                missing_requirements=[]
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
                _block(req_key, "Requirement slot not found — documents may not have been linked")
                continue

            defn = get_requirement_definition(req_key)
            needs_verification = defn.get("verification_required", True)

            if needs_verification and not slot.get("verified"):
                _block(req_key, "Not yet verified by admin")
            else:
                _pass(req_key)

        # ------------------------------------------------------------------
        # 2. Proof of Address — quantity rule (≥2 verified files)
        # ------------------------------------------------------------------
        poa_slot = await self._resolve_slot(employee_id, "proof_of_address")
        if poa_slot:
            min_files = policies.get("poa_min_files", 2)
            # Count all docs that resolve to proof_of_address and are verified
            poa_docs = await self.db.employee_documents.count_documents({
                "employee_id": employee_id,
                "$or": [
                    {"requirement_key": "proof_of_address"},
                    {"requirement_id": {"$regex": "proof_of_address", "$options": "i"}},
                    {"requirement_id": {"$regex": "^poa", "$options": "i"}},
                ],
                "verified": True,
                "status": {"$in": ["uploaded", "active", "verified", "approved"]}
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
        # 3. References (handles bool/string duality)
        # ------------------------------------------------------------------
        for ref_num in [1, 2]:
            ref_key = f"reference_{ref_num}"
            ref_slot = await self._resolve_reference_slot(employee_id, ref_num)

            if ref_slot is None:
                _missing(ref_key)
                _block(ref_key, "Reference slot not found")
                continue

            if self._is_reference_verified(employee, ref_num):
                _pass(ref_key)
            else:
                # Check if at least received (warn rather than block if policy allows)
                ref_obj = employee.get(f"ref{ref_num}") or employee.get(f"reference_{ref_num}", {}) or {}
                status = ref_obj.get("verification_status", "")
                if status in (ReferenceStatus.RECEIVED,):
                    _warn(ref_key, "Reference received but not yet verified by admin")
                else:
                    _block(ref_key, "Reference not verified")

        # ------------------------------------------------------------------
        # 4. Interview (check for submission with a decision)
        # ------------------------------------------------------------------
        interview_sub = await self.db.form_submissions.find_one({
            "employee_id": employee_id,
            "form_type": {"$in": ["interview", "interview_questions"]},
            "status": {"$in": ["submitted", "verified", "interview_completed"]},
        })
        if not interview_sub:
            _warn("interview", "No completed interview record found")
        else:
            decision = (interview_sub.get("answers") or {}).get("decision") or interview_sub.get("decision")
            if not decision:
                _warn("interview", "Interview exists but no decision has been recorded")
            else:
                _pass("interview")

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
        # Final verdict
        # ------------------------------------------------------------------
        return GateResult(
            allowed=len(blocking_items) == 0,
            blocking_items=blocking_items,
            warning_items=warning_items,
            passed_items=passed_items,
            missing_requirements=missing_requirements,
        )

