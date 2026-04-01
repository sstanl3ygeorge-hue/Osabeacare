"""
stageGates.py - Stage Gate Service

Generates requirement slots and validates stage transitions.
Uses employee_documents collection for requirement slots.
"""

import uuid
from datetime import datetime, timezone
from typing import List, Tuple

from role_packs import get_role_pack, get_role_requirements, get_role_policies
from role_normalization import normalize_role
from requirement_definitions import get_requirement_definition


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
    
    async def can_approve_recruitment(self, employee_id: str) -> Tuple[bool, List[str]]:
        """
        Check if employee can be approved for recruitment.
        Returns (can_approve, list_of_blockers)
        """
        employee = await self.db.employees.find_one({"id": employee_id})
        if not employee:
            return False, ["Employee not found"]
        
        role = employee.get("role", "healthcare_assistant")
        normalized_role = normalize_role(role)
        policies = get_role_policies(normalized_role)
        
        blockers = []
        
        # Check blocking requirements
        blocking_keys = [
            "right_to_work", "identity", "proof_of_address", "dbs",
            "reference_1", "reference_2"
        ]
        
        # Add nurse-specific
        if normalized_role == "nurse":
            blocking_keys.extend(["nmc_registration", "clinical_competency"])
        
        for req_key in blocking_keys:
            slot = await self.db.employee_documents.find_one({
                "employee_id": employee_id,
                "requirement_key": req_key
            })
            
            if not slot:
                blockers.append(f"{req_key} requirement slot not found")
                continue
            
            if not slot.get("verified"):
                defn = get_requirement_definition(req_key)
                label = defn.get("label", req_key)
                blockers.append(f"{label} not verified")
        
        # Check PoA special rule (2 files)
        poa_slot = await self.db.employee_documents.find_one({
            "employee_id": employee_id,
            "requirement_key": "proof_of_address"
        })
        
        if poa_slot:
            # Count verified PoA files
            poa_files = await self.db.employee_documents.count_documents({
                "employee_id": employee_id,
                "requirement_key": {"$regex": "proof_of_address"},
                "status": {"$in": ["uploaded", "active"]},
                "verified": True
            })
            
            min_files = policies.get("poa_min_files", 2)
            if poa_files < min_files:
                blockers.append(f"Proof of Address requires {min_files} verified files (has {poa_files})")
        
        can_approve = len(blockers) == 0
        return can_approve, blockers
