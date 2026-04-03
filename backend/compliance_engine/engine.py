# Unified Compliance Engine
# Core services for managing compliance requirements

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import uuid

from .models import (
    RequirementType,
    EvidenceStatus,
    VerificationStatus,
    VerificationOutcome,
    ComputedState,
    VisibilityBucket,
    Evidence,
    Verification,
    StructuredResult,
    RequirementSummary,
    ComplianceSummary
)
from .rule_packs import get_rule_pack
from .labels import get_label


# =============================================================================
# EVIDENCE SERVICE
# =============================================================================

class EvidenceService:
    """
    Service for managing evidence files across all requirement types.
    
    Evidence is per-file, stamps are per-evidence.
    """
    
    # Status transitions that are allowed
    ALLOWED_TRANSITIONS = {
        EvidenceStatus.RECEIVED: [EvidenceStatus.PENDING_REVIEW, EvidenceStatus.ACCEPTED, EvidenceStatus.REJECTED],
        EvidenceStatus.PENDING_REVIEW: [EvidenceStatus.ACCEPTED, EvidenceStatus.REJECTED],
        EvidenceStatus.ACCEPTED: [EvidenceStatus.SUPERSEDED, EvidenceStatus.UPLOADED_IN_ERROR],
        EvidenceStatus.REJECTED: [],
        EvidenceStatus.UPLOADED_IN_ERROR: [],
        EvidenceStatus.SUPERSEDED: [],
    }
    
    # Statuses that are considered "active" (visible on main card)
    ACTIVE_STATUSES = [
        EvidenceStatus.RECEIVED,
        EvidenceStatus.PENDING_REVIEW,
        EvidenceStatus.ACCEPTED,
        # Legacy
        "active", "uploaded", "approved", "under_review", "verified"
    ]
    
    # Statuses that are hidden from main card
    HIDDEN_STATUSES = [
        EvidenceStatus.REJECTED,
        EvidenceStatus.UPLOADED_IN_ERROR,
        EvidenceStatus.SUPERSEDED,
        EvidenceStatus.HISTORICAL
    ]
    
    @classmethod
    def create_evidence(
        cls,
        requirement_type: RequirementType,
        employee_id: str,
        file_name: str,
        file_url: Optional[str] = None,
        file_type: Optional[str] = None,
        uploaded_by: str = "system",
        source: str = "applicant_upload"
    ) -> Evidence:
        """Create a new evidence record."""
        return Evidence(
            evidence_id=str(uuid.uuid4()),
            requirement_type=requirement_type,
            employee_id=employee_id,
            file_name=file_name,
            file_url=file_url,
            file_type=file_type,
            uploaded_by=uploaded_by,
            uploaded_at=datetime.now(timezone.utc),
            source=source,
            review_status=EvidenceStatus.RECEIVED,
            visibility_bucket=VisibilityBucket.ACTIVE
        )
    
    @classmethod
    def can_transition(cls, current_status: EvidenceStatus, new_status: EvidenceStatus) -> bool:
        """Check if a status transition is allowed."""
        allowed = cls.ALLOWED_TRANSITIONS.get(current_status, [])
        return new_status in allowed
    
    @classmethod
    def is_active(cls, status: str) -> bool:
        """Check if a status is considered active."""
        if isinstance(status, EvidenceStatus):
            return status in cls.ACTIVE_STATUSES
        return status in [s.value if hasattr(s, 'value') else s for s in cls.ACTIVE_STATUSES]
    
    @classmethod
    def get_visibility_bucket(cls, status: str) -> VisibilityBucket:
        """Get the visibility bucket for a status."""
        if cls.is_active(status):
            return VisibilityBucket.ACTIVE
        elif status in [s.value if hasattr(s, 'value') else s for s in cls.HIDDEN_STATUSES]:
            return VisibilityBucket.HIDDEN
        else:
            return VisibilityBucket.HISTORICAL
    
    @classmethod
    def compute_evidence_counts(cls, evidence_list: List[Dict]) -> Dict[str, int]:
        """
        Compute evidence counts from a list of evidence records.
        
        Returns:
            Dict with counts for active, pending, verified, rejected, etc.
        """
        counts = {
            "total": len(evidence_list),
            "active": 0,
            "pending_review": 0,
            "accepted": 0,
            "rejected": 0,
            "historical": 0,
            "with_stamp": 0
        }
        
        for ev in evidence_list:
            status = ev.get("status") or ev.get("review_status", "")
            
            if cls.is_active(status):
                counts["active"] += 1
                if status in ["pending_review", "under_review", "uploaded", "received"]:
                    counts["pending_review"] += 1
                elif status in ["accepted", "approved", "verified"]:
                    counts["accepted"] += 1
            else:
                counts["historical"] += 1
                if status == "rejected":
                    counts["rejected"] += 1
            
            if ev.get("verification_stamp") or ev.get("stamp_type"):
                counts["with_stamp"] += 1
        
        return counts


# =============================================================================
# VERIFICATION SERVICE
# =============================================================================

class VerificationService:
    """
    Service for managing verification checks across all requirement types.
    
    Verification is requirement-level (one per requirement per employee at a time).
    """
    
    @classmethod
    def create_verification(
        cls,
        requirement_type: RequirementType,
        employee_id: str,
        method: str,
        outcome: VerificationOutcome,
        checked_at: str,
        checked_by: str,
        proof_document_id: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Verification:
        """Create a new verification record."""
        rule_pack = get_rule_pack(requirement_type)
        
        return Verification(
            verification_id=str(uuid.uuid4()),
            requirement_type=requirement_type,
            employee_id=employee_id,
            method=method,
            outcome=outcome,
            checked_at=checked_at,
            checked_by=checked_by,
            proof_document_id=proof_document_id,
            notes=notes,
            status=VerificationStatus.COMPLETED,
            method_label=rule_pack.get_method_label(method),
            outcome_label=get_label("outcome", outcome.value if hasattr(outcome, 'value') else outcome),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
    
    @classmethod
    def is_verified(cls, verification: Optional[Dict]) -> bool:
        """Check if a verification is successful."""
        if not verification:
            return False
        outcome = verification.get("outcome", "")
        return outcome == "verified" or outcome == VerificationOutcome.VERIFIED.value


# =============================================================================
# RESULT SERVICE
# =============================================================================

class ResultService:
    """
    Service for managing structured results across all requirement types.
    
    Results contain requirement-specific data validated by rule packs.
    """
    
    @classmethod
    def create_result(
        cls,
        verification_id: str,
        requirement_type: RequirementType,
        data: Dict[str, Any]
    ) -> StructuredResult:
        """Create a new structured result."""
        rule_pack = get_rule_pack(requirement_type)
        
        # Validate the data
        validation = rule_pack.validate_result(data)
        
        return StructuredResult(
            result_id=str(uuid.uuid4()),
            verification_id=verification_id,
            requirement_type=requirement_type,
            data=data,
            is_complete=validation["is_valid"],
            missing_fields=validation["missing_fields"]
        )
    
    @classmethod
    def compute_state(
        cls,
        requirement_type: RequirementType,
        verification_outcome: Optional[str],
        result_data: Dict[str, Any],
        evidence_count: int = 0
    ) -> Dict[str, Any]:
        """
        Compute the state for a requirement using its rule pack.
        
        Returns:
            Dict with status, label, color, alerts, blocking info
        """
        rule_pack = get_rule_pack(requirement_type)
        return rule_pack.compute_status(verification_outcome, result_data, evidence_count)


# =============================================================================
# STATUS ENGINE
# =============================================================================

class StatusEngine:
    """
    Central engine for computing status across all requirements.
    """
    
    @classmethod
    def compute_requirement_summary(
        cls,
        requirement_type: RequirementType,
        requirement_key: str,
        evidence_list: List[Dict],
        verification: Optional[Dict],
        result_data: Dict[str, Any] = None
    ) -> RequirementSummary:
        """
        Compute a complete summary for a requirement.
        
        This is the single source of truth for requirement status.
        """
        rule_pack = get_rule_pack(requirement_type)
        
        # Compute evidence counts
        evidence_counts = EvidenceService.compute_evidence_counts(evidence_list)
        
        # Get verification outcome
        verification_outcome = None
        if verification:
            verification_outcome = verification.get("outcome")
        
        # Compute status using rule pack
        status_result = rule_pack.compute_status(
            verification_outcome,
            result_data or {},
            evidence_counts["active"]
        )
        
        # Build summary
        summary = RequirementSummary(
            requirement_type=requirement_type,
            requirement_key=requirement_key,
            status=ComputedState(status_result["status"]) if status_result["status"] in [s.value for s in ComputedState] else ComputedState.INCOMPLETE,
            status_label=status_result["status_label"],
            status_color=status_result["status_color"],
            blocking=status_result.get("is_blocking", True),
            evidence_count=evidence_counts["total"],
            active_evidence_count=evidence_counts["active"],
            accepted_evidence_count=evidence_counts["accepted"],
            pending_review_count=evidence_counts["pending_review"],
            historical_evidence_count=evidence_counts["historical"],
            has_verification=verification is not None,
            verification_outcome=verification_outcome,
            summary_badges=[]
        )
        
        # Add blocker text if blocking
        if summary.blocking:
            summary.blocker_text = get_label("blocker", requirement_key, f"{requirement_key.replace('_', ' ').title()} not verified")
        
        # Compute summary label
        if summary.has_verification and verification_outcome == "verified":
            summary.summary_label = "Verified"
        elif summary.has_verification:
            summary.summary_label = f"Check recorded: {get_label('outcome', verification_outcome)}"
        elif evidence_counts["active"] > 0:
            summary.summary_label = f"{evidence_counts['active']} file(s) uploaded"
        else:
            summary.summary_label = "Not started"
        
        # Add badges
        if evidence_counts["pending_review"] > 0:
            summary.summary_badges.append(f"{evidence_counts['pending_review']} pending review")
        
        if status_result.get("alerts"):
            for alert in status_result["alerts"]:
                if alert.get("level") in ["error", "urgent"]:
                    summary.summary_badges.append(alert.get("message", "Alert"))
        
        # Contributions
        summary.contributes_blocker = summary.blocking
        summary.contributes_warning = not summary.blocking and len(status_result.get("alerts", [])) > 0
        summary.contributes_pending_review = evidence_counts["pending_review"]
        
        return summary


# =============================================================================
# BLOCKER ENGINE
# =============================================================================

class BlockerEngine:
    """
    Central engine for computing blockers across all requirements.
    
    Single source of truth for what's blocking work readiness.
    """
    
    # Requirements that block work readiness
    BLOCKING_REQUIREMENTS = [
        RequirementType.RIGHT_TO_WORK,
        RequirementType.DBS,
        RequirementType.IDENTITY,
        RequirementType.PROOF_OF_ADDRESS
    ]
    
    @classmethod
    def compute_blockers(
        cls,
        requirement_summaries: Dict[str, RequirementSummary]
    ) -> List[Dict[str, Any]]:
        """
        Compute all blockers from requirement summaries.
        
        Returns:
            List of blocker dicts with key, message, priority
        """
        blockers = []
        
        for key, summary in requirement_summaries.items():
            if summary.blocking and summary.requirement_type in cls.BLOCKING_REQUIREMENTS:
                blockers.append({
                    "key": key,
                    "requirement_type": summary.requirement_type.value if hasattr(summary.requirement_type, 'value') else summary.requirement_type,
                    "message": summary.blocker_text or f"{key.replace('_', ' ').title()} not verified",
                    "status": summary.status.value if hasattr(summary.status, 'value') else summary.status,
                    "priority": cls._get_blocker_priority(summary)
                })
        
        # Sort by priority
        blockers.sort(key=lambda b: b["priority"])
        
        return blockers
    
    @classmethod
    def _get_blocker_priority(cls, summary: RequirementSummary) -> int:
        """Get the priority for a blocker (lower = higher priority)."""
        # Priority order: RTW > DBS > Identity > PoA
        priority_map = {
            RequirementType.RIGHT_TO_WORK: 1,
            RequirementType.DBS: 2,
            RequirementType.IDENTITY: 3,
            RequirementType.PROOF_OF_ADDRESS: 4
        }
        return priority_map.get(summary.requirement_type, 99)
    
    @classmethod
    def is_ready_to_work(cls, blockers: List[Dict]) -> bool:
        """Check if an employee is ready to work (no blockers)."""
        return len(blockers) == 0


# =============================================================================
# COMPLIANCE ENGINE (MAIN)
# =============================================================================

class ComplianceEngine:
    """
    Main compliance engine that orchestrates all services.
    
    Use this class to:
    - Get a complete compliance summary for an employee
    - Compute work readiness
    - Get blockers and warnings
    """
    
    def __init__(self, db=None):
        """Initialize with optional database connection."""
        self.db = db
    
    async def get_compliance_summary(
        self,
        employee_id: str,
        evidence_by_type: Dict[str, List[Dict]],
        verifications: Dict[str, Optional[Dict]],
        result_data: Dict[str, Dict[str, Any]] = None
    ) -> ComplianceSummary:
        """
        Get a complete compliance summary for an employee.
        
        Args:
            employee_id: The employee ID
            evidence_by_type: Dict mapping requirement keys to evidence lists
            verifications: Dict mapping requirement keys to verification dicts
            result_data: Dict mapping requirement keys to result data dicts
        
        Returns:
            ComplianceSummary with all counts, blockers, and requirement summaries
        """
        result_data = result_data or {}
        
        # Map string keys to RequirementType
        key_to_type = {
            "right_to_work": RequirementType.RIGHT_TO_WORK,
            "dbs": RequirementType.DBS,
            "identity": RequirementType.IDENTITY,
            "proof_of_address": RequirementType.PROOF_OF_ADDRESS
        }
        
        # Compute summaries for each requirement
        requirement_summaries = {}
        for key, req_type in key_to_type.items():
            evidence = evidence_by_type.get(key, [])
            verification = verifications.get(key)
            data = result_data.get(key, {})
            
            # Merge verification data into result_data if available
            if verification:
                merged_data = {**data, **verification}
            else:
                merged_data = data
            
            summary = StatusEngine.compute_requirement_summary(
                requirement_type=req_type,
                requirement_key=key,
                evidence_list=evidence,
                verification=verification,
                result_data=merged_data
            )
            requirement_summaries[key] = summary
        
        # Compute blockers
        blockers = BlockerEngine.compute_blockers(requirement_summaries)
        
        # Compute aggregate counts
        total_requirements = len(requirement_summaries)
        completed_count = sum(1 for s in requirement_summaries.values() if not s.blocking)
        blocking_count = sum(1 for s in requirement_summaries.values() if s.blocking)
        warning_count = sum(1 for s in requirement_summaries.values() if s.contributes_warning)
        pending_review_count = sum(s.contributes_pending_review for s in requirement_summaries.values())
        missing_count = sum(1 for s in requirement_summaries.values() if s.status == ComputedState.MISSING)
        
        # Build summary
        return ComplianceSummary(
            employee_id=employee_id,
            total_requirements=total_requirements,
            completed_count=completed_count,
            blocking_count=blocking_count,
            warning_count=warning_count,
            pending_review_count=pending_review_count,
            missing_count=missing_count,
            completion_percentage=(completed_count / total_requirements * 100) if total_requirements > 0 else 0,
            is_ready_to_work=BlockerEngine.is_ready_to_work(blockers),
            can_approve=BlockerEngine.is_ready_to_work(blockers),
            blockers=blockers,
            warnings=[],  # TODO: Compute warnings
            pending_items=[],  # TODO: Compute pending items
            requirements=requirement_summaries
        )
