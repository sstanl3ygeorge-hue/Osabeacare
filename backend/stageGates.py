"""
stageGates.py - Stage Gate Validation Service

Validates whether an employee can move to the next stage based on:
- Role pack requirements
- Verified documents/checks
- Submitted forms
- Valid references
"""

from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple
from rolePacks import (
    get_role_pack, 
    get_requirement_type, 
    REQUIREMENT_METADATA,
    STAGE_GATES
)


class StageGateService:
    """
    Service for validating stage transitions and recruitment approval.
    """
    
    def __init__(self, db):
        self.db = db
    
    # =========================================================================
    # CORE VERIFICATION CHECKS
    # =========================================================================
    
    async def is_requirement_verified(self, employee_id: str, requirement_key: str) -> bool:
        """Check if a specific requirement is verified for an employee"""
        req_type = get_requirement_type(requirement_key)
        
        if req_type == "document":
            return await self._is_document_verified(employee_id, requirement_key)
        elif req_type == "reference":
            return await self._is_reference_verified(employee_id, requirement_key)
        elif req_type == "form":
            return await self._is_form_completed(employee_id, requirement_key)
        elif req_type == "registration":
            return await self._is_registration_verified(employee_id, requirement_key)
        else:
            return False
    
    async def _is_document_verified(self, employee_id: str, requirement_key: str) -> bool:
        """Check if document requirement has verified check"""
        # Map requirement to check collection
        check_collections = {
            "right_to_work": "rtw_checks",
            "identity": "identity_verifications",
            "proof_of_address": "address_verifications",
            "dbs": "dbs_checks"
        }
        
        collection_name = check_collections.get(requirement_key)
        if not collection_name:
            return False
        
        collection = self.db[collection_name]
        check = await collection.find_one({
            "employee_id": employee_id,
            "outcome": "verified"
        })
        
        return check is not None
    
    async def _is_reference_verified(self, employee_id: str, requirement_key: str) -> bool:
        """Check if reference is verified"""
        ref_num = 1 if requirement_key == "reference_1" else 2
        
        employee = await self.db.employees.find_one(
            {"id": employee_id},
            {f"reference_{ref_num}_verification_status": 1}
        )
        
        if not employee:
            return False
        
        return employee.get(f"reference_{ref_num}_verification_status") == "verified"
    
    async def _is_form_completed(self, employee_id: str, requirement_key: str) -> bool:
        """Check if form requirement is completed"""
        # Check form_submissions or agreement_acknowledgements
        form_submission = await self.db.form_submissions.find_one({
            "employee_id": employee_id,
            "form_type": requirement_key,
            "status": "completed"
        })
        
        if form_submission:
            return True
        
        # Also check agreement_acknowledgements for agreement forms
        if requirement_key in ["contract_acceptance", "handbook_acknowledgement", "induction"]:
            acknowledgement = await self.db.agreement_acknowledgements.find_one({
                "employee_id": employee_id,
                "agreement_type": requirement_key,
                "verification_status": "verified"
            })
            return acknowledgement is not None
        
        return False
    
    async def _is_registration_verified(self, employee_id: str, requirement_key: str) -> bool:
        """Check if professional registration is verified (e.g., NMC)"""
        if requirement_key == "nmc_registration":
            employee = await self.db.employees.find_one(
                {"id": employee_id},
                {"nmc_pin": 1, "nmc_verified": 1, "nmc_expiry": 1}
            )
            
            if not employee:
                return False
            
            # Must have PIN, be verified, and not expired
            if not employee.get("nmc_pin") or not employee.get("nmc_verified"):
                return False
            
            expiry = employee.get("nmc_expiry")
            if expiry:
                expiry_date = datetime.fromisoformat(expiry.replace("Z", "+00:00")) if isinstance(expiry, str) else expiry
                if expiry_date < datetime.now(timezone.utc):
                    return False
            
            return True
        
        return False
    
    # =========================================================================
    # PROOF OF ADDRESS - SPECIAL VALIDATION
    # =========================================================================
    
    async def is_valid_poa(self, employee_id: str, validity_months: int = 12) -> bool:
        """
        Check if Proof of Address requirement is satisfied.
        Requires 2 valid documents within validity_months.
        """
        # Get active PoA files
        files_cursor = self.db.employee_documents.find({
            "employee_id": employee_id,
            "requirement_id": {"$in": ["proof_of_address", "proof_of_address_evidence"]},
            "status": {"$in": ["active", "uploaded"]},
            "rejected": {"$ne": True}
        })
        
        files = await files_cursor.to_list(length=100)
        
        # Filter to valid files (within validity period)
        now = datetime.now(timezone.utc)
        valid_files = []
        
        for f in files:
            doc_date = f.get("document_date") or f.get("uploaded_at")
            if not doc_date:
                continue
            
            if isinstance(doc_date, str):
                doc_date = datetime.fromisoformat(doc_date.replace("Z", "+00:00"))
            
            months_diff = (now.year - doc_date.year) * 12 + (now.month - doc_date.month)
            
            if months_diff <= validity_months:
                valid_files.append(f)
        
        # Need at least 2 valid files
        return len(valid_files) >= 2
    
    # =========================================================================
    # REFERENCES - SPECIAL VALIDATION
    # =========================================================================
    
    async def has_verified_references(self, employee_id: str, min_references: int = 2) -> bool:
        """Check if employee has required number of verified references"""
        verified_count = 0
        
        for ref_num in [1, 2]:
            if await self._is_reference_verified(employee_id, f"reference_{ref_num}"):
                verified_count += 1
        
        return verified_count >= min_references
    
    # =========================================================================
    # RECRUITMENT APPROVAL GATE
    # =========================================================================
    
    async def can_approve_recruitment(self, employee_id: str) -> Tuple[bool, List[str]]:
        """
        Check if employee can be approved for recruitment.
        Returns (can_approve, list_of_blockers)
        """
        employee = await self.db.employees.find_one({"id": employee_id})
        if not employee:
            return False, ["Employee not found"]
        
        role = employee.get("role", "healthcare_assistant")
        role_pack = get_role_pack(role)
        policies = role_pack.get("policies", {})
        
        blockers = []
        
        # 1. Right to Work verified
        if not await self.is_requirement_verified(employee_id, "right_to_work"):
            blockers.append("Right to Work not verified")
        
        # 2. Identity verified
        if not await self.is_requirement_verified(employee_id, "identity"):
            blockers.append("Identity not verified")
        
        # 3. Proof of Address valid (2 files within 12 months)
        poa_months = policies.get("poa_validity_months", 12)
        if not await self.is_valid_poa(employee_id, poa_months):
            blockers.append(f"Proof of Address requires 2 valid documents (within {poa_months} months)")
        
        # 4. DBS verified (if required)
        if policies.get("dbs_required_before_approval", True):
            if not await self.is_requirement_verified(employee_id, "dbs"):
                blockers.append("DBS not verified")
        
        # 5. References verified
        min_refs = policies.get("min_references", 2)
        if not await self.has_verified_references(employee_id, min_refs):
            blockers.append(f"Requires {min_refs} verified references")
        
        # 6. NMC Registration (nurse only)
        if role == "nurse" and policies.get("nmc_required", False):
            if not await self.is_requirement_verified(employee_id, "nmc_registration"):
                blockers.append("NMC Registration not verified")
        
        can_approve = len(blockers) == 0
        return can_approve, blockers
    
    # =========================================================================
    # STAGE TRANSITION VALIDATION
    # =========================================================================
    
    async def can_transition_stage(
        self, 
        employee_id: str, 
        from_stage: str, 
        to_stage: str
    ) -> Tuple[bool, List[str]]:
        """
        Check if employee can transition from one stage to another.
        Returns (can_transition, list_of_blockers)
        """
        gate_key = f"{from_stage}_to_{to_stage}"
        
        # Special case: recruitment approval
        if to_stage == "recruitment_approval" or (from_stage == "compliance_review" and to_stage == "onboarding"):
            return await self.can_approve_recruitment(employee_id)
        
        gate = STAGE_GATES.get(gate_key)
        if not gate:
            # No gate defined, allow transition
            return True, []
        
        employee = await self.db.employees.find_one({"id": employee_id})
        if not employee:
            return False, ["Employee not found"]
        
        role = employee.get("role", "healthcare_assistant")
        blockers = []
        
        # Check required_verified
        for req_key in gate.get("required_verified", []):
            if not await self.is_requirement_verified(employee_id, req_key):
                metadata = REQUIREMENT_METADATA.get(req_key, {})
                label = metadata.get("label", req_key)
                blockers.append(f"{label} not verified")
        
        # Check role-specific requirements
        role_specific = gate.get("role_specific", {}).get(role, [])
        for req_key in role_specific:
            if not await self.is_requirement_verified(employee_id, req_key):
                metadata = REQUIREMENT_METADATA.get(req_key, {})
                label = metadata.get("label", req_key)
                blockers.append(f"{label} not verified (required for {role})")
        
        can_transition = len(blockers) == 0
        return can_transition, blockers
    
    # =========================================================================
    # REQUIREMENT GENERATION
    # =========================================================================
    
    async def generate_requirements_for_employee(self, employee_id: str, role: str) -> List[dict]:
        """
        Generate requirement slots for an employee based on their role.
        Called when application is submitted or candidate moves to screening.
        """
        role_pack = get_role_pack(role)
        requirements = role_pack.get("requirements", [])
        policies = role_pack.get("policies", {})
        
        created_requirements = []
        now = datetime.now(timezone.utc).isoformat()
        
        for req_key in requirements:
            # Check if requirement already exists
            existing = await self.db.employee_requirements.find_one({
                "employee_id": employee_id,
                "requirement_key": req_key
            })
            
            if existing:
                continue
            
            req_type = get_requirement_type(req_key)
            metadata = REQUIREMENT_METADATA.get(req_key, {})
            
            # Build requirement document
            requirement = {
                "employee_id": employee_id,
                "requirement_key": req_key,
                "type": req_type,
                "status": "not_started",
                "required": metadata.get("required", True),
                "blocking": metadata.get("blocking", False),
                "role": role,
                "created_at": now,
                "updated_at": now,
                "policy": {}
            }
            
            # Add policy-specific fields
            if req_key == "proof_of_address":
                requirement["policy"]["validity_months"] = policies.get("poa_validity_months", 12)
                requirement["policy"]["min_files"] = metadata.get("min_files", 2)
            
            if metadata.get("expiry_tracked"):
                requirement["expiry_tracked"] = True
            
            if metadata.get("extraction_enabled"):
                requirement["extraction_enabled"] = True
            
            if metadata.get("check_required"):
                requirement["check_required"] = True
            
            # Insert
            await self.db.employee_requirements.insert_one(requirement)
            created_requirements.append(requirement)
        
        return created_requirements
    
    # =========================================================================
    # COMPLIANCE SUMMARY
    # =========================================================================
    
    async def get_compliance_summary(self, employee_id: str) -> dict:
        """
        Get a summary of compliance status for an employee.
        """
        employee = await self.db.employees.find_one({"id": employee_id})
        if not employee:
            return {"error": "Employee not found"}
        
        role = employee.get("role", "healthcare_assistant")
        role_pack = get_role_pack(role)
        requirements = role_pack.get("requirements", [])
        
        summary = {
            "employee_id": employee_id,
            "role": role,
            "total_requirements": len(requirements),
            "verified": 0,
            "pending": 0,
            "not_started": 0,
            "blocking": [],
            "can_approve": False,
            "approval_blockers": []
        }
        
        for req_key in requirements:
            metadata = REQUIREMENT_METADATA.get(req_key, {})
            is_verified = await self.is_requirement_verified(employee_id, req_key)
            
            if is_verified:
                summary["verified"] += 1
            else:
                # Check if has any activity
                has_activity = await self._has_requirement_activity(employee_id, req_key)
                if has_activity:
                    summary["pending"] += 1
                else:
                    summary["not_started"] += 1
                
                # Check if blocking
                if metadata.get("blocking", False):
                    summary["blocking"].append({
                        "key": req_key,
                        "label": metadata.get("label", req_key)
                    })
        
        # Check recruitment approval
        can_approve, blockers = await self.can_approve_recruitment(employee_id)
        summary["can_approve"] = can_approve
        summary["approval_blockers"] = blockers
        
        return summary
    
    async def _has_requirement_activity(self, employee_id: str, requirement_key: str) -> bool:
        """Check if a requirement has any activity (files, requests, etc.)"""
        req_type = get_requirement_type(requirement_key)
        
        if req_type == "document":
            # Check for files
            file = await self.db.employee_documents.find_one({
                "employee_id": employee_id,
                "requirement_id": {"$regex": requirement_key}
            })
            return file is not None
        
        if req_type == "reference":
            ref_num = 1 if requirement_key == "reference_1" else 2
            employee = await self.db.employees.find_one(
                {"id": employee_id},
                {f"reference_{ref_num}_request_status": 1}
            )
            if employee:
                status = employee.get(f"reference_{ref_num}_request_status")
                return status and status != "not_started"
        
        if req_type == "form":
            submission = await self.db.form_submissions.find_one({
                "employee_id": employee_id,
                "form_type": requirement_key
            })
            return submission is not None
        
        return False
