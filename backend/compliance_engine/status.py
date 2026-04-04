# Unified Compliance Status Model
# Single source of truth for employee compliance status

import uuid
from datetime import datetime, timezone, date
from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field


class ComplianceStatus(str, Enum):
    """Standardized compliance statuses for CQC reporting."""
    COMPLIANT = "COMPLIANT"              # Fully verified and valid
    MISSING = "MISSING"                   # No evidence/check recorded
    EXPIRED = "EXPIRED"                   # Was compliant, now expired
    ATTENTION_REQUIRED = "ATTENTION_REQUIRED"  # Partial or needs review
    NOT_APPLICABLE = "NOT_APPLICABLE"     # Requirement doesn't apply to this role


class OverallStatus(str, Enum):
    """Overall employee compliance status."""
    READY_TO_WORK = "READY_TO_WORK"       # All requirements met
    REQUIRES_ATTENTION = "REQUIRES_ATTENTION"  # Some items need attention
    NOT_READY = "NOT_READY"               # Blocking requirements unmet
    EXPIRED = "EXPIRED"                   # Critical requirement expired


class RequirementSummary(BaseModel):
    """Summary for a single compliance requirement."""
    status: ComplianceStatus
    
    # Verification details
    is_verified: bool = False
    verified_at: Optional[datetime] = None
    verified_by: Optional[str] = None
    method: Optional[str] = None
    
    # Expiry tracking
    expiry_date: Optional[date] = None
    days_until_expiry: Optional[int] = None
    is_expired: bool = False
    
    # Evidence tracking
    evidence_count: int = 0
    pending_review_count: int = 0
    
    # Blocking
    blocks_work: bool = True
    
    # Alerts
    alerts: List[str] = Field(default_factory=list)
    
    # Last update
    last_updated: Optional[datetime] = None


class EmployeeComplianceSummary(BaseModel):
    """
    Unified compliance summary for an employee.
    Single source of truth for UI, reporting, and audits.
    """
    id: str = Field(default_factory=lambda: f"summary_{uuid.uuid4().hex[:12]}")
    employee_id: str
    employee_name: str
    
    # Individual requirement statuses
    requirements: Dict[str, RequirementSummary] = Field(default_factory=dict)
    
    # Overall status
    overall_status: OverallStatus = OverallStatus.NOT_READY
    
    # Regulatory mapping
    regulatory_status: str = "NOT_READY"  # Strict CQC-safe status
    
    # Counts
    total_requirements: int = 0
    compliant_count: int = 0
    missing_count: int = 0
    expired_count: int = 0
    attention_count: int = 0
    
    # Blockers (requirements preventing work)
    blockers: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Warnings (approaching expiry, etc.)
    warnings: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Expiry dashboard data
    expiring_soon: List[Dict[str, Any]] = Field(default_factory=list)  # Within 30 days
    
    # Timestamps
    last_calculated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Config:
        use_enum_values = True


class ComplianceStatusService:
    """
    Service for calculating and maintaining unified compliance status.
    """
    
    # Requirements and their blocking status
    REQUIREMENTS = {
        "right_to_work": {"label": "Right to Work", "blocks_work": True},
        "dbs": {"label": "DBS Check", "blocks_work": True},
        "identity": {"label": "Identity Verification", "blocks_work": True},
        "proof_of_address": {"label": "Proof of Address", "blocks_work": True},
        "references": {"label": "References", "blocks_work": True},  # Configurable
        "training": {"label": "Mandatory Training", "blocks_work": True},
        "health": {"label": "Occupational Health", "blocks_work": True},
    }
    
    # Expiry thresholds
    EXPIRY_WARNING_DAYS = 30
    EXPIRY_URGENT_DAYS = 7
    
    def __init__(self, db):
        self.db = db
    
    async def calculate_summary(self, employee_id: str) -> EmployeeComplianceSummary:
        """
        Calculate the complete compliance summary for an employee.
        This is the single source of truth.
        """
        # Get employee
        employee = await self.db.employees.find_one({"id": employee_id})
        if not employee:
            raise ValueError(f"Employee {employee_id} not found")
        
        employee_name = f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip()
        
        # Calculate each requirement
        requirements = {}
        requirements["right_to_work"] = await self._get_rtw_status(employee_id)
        requirements["dbs"] = await self._get_dbs_status(employee_id)
        requirements["identity"] = await self._get_identity_status(employee_id)
        requirements["proof_of_address"] = await self._get_address_status(employee_id)
        requirements["references"] = await self._get_references_status(employee_id)
        requirements["training"] = await self._get_training_status(employee_id)
        requirements["health"] = await self._get_health_status(employee_id)
        
        # Calculate counts
        compliant_count = sum(1 for r in requirements.values() if r.status == ComplianceStatus.COMPLIANT)
        missing_count = sum(1 for r in requirements.values() if r.status == ComplianceStatus.MISSING)
        expired_count = sum(1 for r in requirements.values() if r.status == ComplianceStatus.EXPIRED)
        attention_count = sum(1 for r in requirements.values() if r.status == ComplianceStatus.ATTENTION_REQUIRED)
        
        # Calculate blockers
        blockers = []
        for key, req in requirements.items():
            if req.blocks_work and req.status != ComplianceStatus.COMPLIANT:
                blockers.append({
                    "requirement": key,
                    "label": self.REQUIREMENTS[key]["label"],
                    "status": req.status,
                    "reason": self._get_blocker_reason(key, req)
                })
        
        # Calculate warnings
        warnings = []
        expiring_soon = []
        for key, req in requirements.items():
            if req.days_until_expiry is not None:
                if req.days_until_expiry <= self.EXPIRY_WARNING_DAYS:
                    warning = {
                        "requirement": key,
                        "label": self.REQUIREMENTS[key]["label"],
                        "days_until_expiry": req.days_until_expiry,
                        "expiry_date": req.expiry_date.isoformat() if req.expiry_date else None,
                        "urgent": req.days_until_expiry <= self.EXPIRY_URGENT_DAYS
                    }
                    warnings.append(warning)
                    expiring_soon.append(warning)
            
            # Add alerts as warnings
            for alert in req.alerts:
                warnings.append({
                    "requirement": key,
                    "label": self.REQUIREMENTS[key]["label"],
                    "message": alert
                })
        
        # Calculate overall status
        overall_status = self._calculate_overall_status(requirements, blockers)
        
        # Calculate regulatory status (strict)
        regulatory_status = self._calculate_regulatory_status(requirements)
        
        summary = EmployeeComplianceSummary(
            employee_id=employee_id,
            employee_name=employee_name,
            requirements=requirements,
            overall_status=overall_status,
            regulatory_status=regulatory_status,
            total_requirements=len(requirements),
            compliant_count=compliant_count,
            missing_count=missing_count,
            expired_count=expired_count,
            attention_count=attention_count,
            blockers=blockers,
            warnings=warnings,
            expiring_soon=sorted(expiring_soon, key=lambda x: x.get("days_until_expiry", 999))
        )
        
        # Store in database for caching
        await self._store_summary(summary)
        
        return summary
    
    async def _get_rtw_status(self, employee_id: str) -> RequirementSummary:
        """Get Right to Work status."""
        check = await self.db.rtw_checks.find_one(
            {"employee_id": employee_id, "superseded_at": None},
            sort=[("created_at", -1)]
        )
        
        evidence_count = await self.db.employee_documents.count_documents({
            "employee_id": employee_id,
            "requirement_type": "right_to_work",
            "status": {"$in": ["received", "pending_review", "accepted", "approved", "verified"]}
        })
        
        if not check:
            return RequirementSummary(
                status=ComplianceStatus.MISSING if evidence_count == 0 else ComplianceStatus.ATTENTION_REQUIRED,
                evidence_count=evidence_count,
                blocks_work=True,
                alerts=["No RTW check recorded"] if evidence_count > 0 else []
            )
        
        # Check expiry
        expiry_date = None
        days_until_expiry = None
        is_expired = False
        
        if check.get("permission_end_date") and not check.get("is_indefinite"):
            exp = check["permission_end_date"]
            if isinstance(exp, str):
                expiry_date = date.fromisoformat(exp)
            else:
                expiry_date = exp if isinstance(exp, date) else exp.date()
            
            days_until_expiry = (expiry_date - date.today()).days
            is_expired = days_until_expiry < 0
        
        # Determine status
        if check.get("outcome") != "verified":
            status = ComplianceStatus.ATTENTION_REQUIRED
        elif is_expired:
            status = ComplianceStatus.EXPIRED
        else:
            status = ComplianceStatus.COMPLIANT
        
        alerts = []
        if check.get("restrictions"):
            alerts.append(f"Work restrictions: {check['restrictions']}")
        if check.get("follow_up_required"):
            alerts.append("Follow-up check required")
        
        return RequirementSummary(
            status=status,
            is_verified=check.get("outcome") == "verified",
            verified_at=check.get("created_at"),
            verified_by=check.get("checked_by_name"),
            method=check.get("method"),
            expiry_date=expiry_date,
            days_until_expiry=days_until_expiry,
            is_expired=is_expired,
            evidence_count=evidence_count,
            blocks_work=True,
            alerts=alerts,
            last_updated=check.get("updated_at") or check.get("created_at")
        )
    
    async def _get_dbs_status(self, employee_id: str) -> RequirementSummary:
        """Get DBS status."""
        check = await self.db.dbs_checks.find_one(
            {"employee_id": employee_id},
            sort=[("created_at", -1)]
        )
        
        evidence_count = await self.db.employee_documents.count_documents({
            "employee_id": employee_id,
            "requirement_type": "dbs",
            "status": {"$in": ["received", "pending_review", "accepted", "approved", "verified"]}
        })
        
        if not check:
            return RequirementSummary(
                status=ComplianceStatus.MISSING if evidence_count == 0 else ComplianceStatus.ATTENTION_REQUIRED,
                evidence_count=evidence_count,
                blocks_work=True,
                alerts=["No DBS check recorded"] if evidence_count > 0 else []
            )
        
        # DBS doesn't have statutory expiry, but may have policy-based recheck
        expiry_date = None
        days_until_expiry = None
        is_expired = False
        
        if check.get("next_recheck_date"):
            exp = check["next_recheck_date"]
            if isinstance(exp, str):
                expiry_date = date.fromisoformat(exp)
            else:
                expiry_date = exp if isinstance(exp, date) else exp.date()
            
            days_until_expiry = (expiry_date - date.today()).days
            is_expired = days_until_expiry < 0
        
        # Determine status
        if check.get("outcome") != "verified":
            status = ComplianceStatus.ATTENTION_REQUIRED
        elif is_expired:
            status = ComplianceStatus.EXPIRED
        else:
            status = ComplianceStatus.COMPLIANT
        
        alerts = []
        if check.get("information_present") or check.get("result_status") == "information_present":
            alerts.append("DBS contains disclosed information")
        
        return RequirementSummary(
            status=status,
            is_verified=check.get("outcome") == "verified",
            verified_at=check.get("created_at"),
            verified_by=check.get("checked_by_name"),
            method=check.get("method"),
            expiry_date=expiry_date,
            days_until_expiry=days_until_expiry,
            is_expired=is_expired,
            evidence_count=evidence_count,
            blocks_work=True,
            alerts=alerts,
            last_updated=check.get("updated_at") or check.get("created_at")
        )
    
    async def _get_identity_status(self, employee_id: str) -> RequirementSummary:
        """Get Identity verification status."""
        check = await self.db.identity_checks.find_one(
            {"employee_id": employee_id},
            sort=[("created_at", -1)]
        )
        
        evidence_count = await self.db.employee_documents.count_documents({
            "employee_id": employee_id,
            "requirement_type": "identity",
            "status": {"$in": ["received", "pending_review", "accepted", "approved", "verified"]}
        })
        
        if not check:
            return RequirementSummary(
                status=ComplianceStatus.MISSING if evidence_count == 0 else ComplianceStatus.ATTENTION_REQUIRED,
                evidence_count=evidence_count,
                blocks_work=True,
                alerts=["No identity check recorded"] if evidence_count > 0 else []
            )
        
        # Check document expiry
        expiry_date = None
        days_until_expiry = None
        is_expired = False
        
        if check.get("expiry_date"):
            exp = check["expiry_date"]
            if isinstance(exp, str):
                expiry_date = date.fromisoformat(exp)
            else:
                expiry_date = exp if isinstance(exp, date) else exp.date()
            
            days_until_expiry = (expiry_date - date.today()).days
            is_expired = days_until_expiry < 0
        
        # Determine status
        if check.get("outcome") != "verified":
            status = ComplianceStatus.ATTENTION_REQUIRED
        elif is_expired:
            status = ComplianceStatus.EXPIRED
        else:
            status = ComplianceStatus.COMPLIANT
        
        alerts = []
        if not check.get("name_matches_application"):
            alerts.append("Name mismatch with application")
        if not check.get("dob_matches_application"):
            alerts.append("DOB mismatch with application")
        
        return RequirementSummary(
            status=status,
            is_verified=check.get("outcome") == "verified",
            verified_at=check.get("created_at"),
            verified_by=check.get("checked_by_name"),
            method=check.get("method"),
            expiry_date=expiry_date,
            days_until_expiry=days_until_expiry,
            is_expired=is_expired,
            evidence_count=evidence_count,
            blocks_work=True,
            alerts=alerts,
            last_updated=check.get("updated_at") or check.get("created_at")
        )
    
    async def _get_address_status(self, employee_id: str) -> RequirementSummary:
        """Get Proof of Address status."""
        check = await self.db.address_checks.find_one(
            {"employee_id": employee_id},
            sort=[("created_at", -1)]
        )
        
        evidence_count = await self.db.employee_documents.count_documents({
            "employee_id": employee_id,
            "requirement_type": "proof_of_address",
            "status": {"$in": ["received", "pending_review", "accepted", "approved", "verified"]}
        })
        
        if not check:
            return RequirementSummary(
                status=ComplianceStatus.MISSING if evidence_count == 0 else ComplianceStatus.ATTENTION_REQUIRED,
                evidence_count=evidence_count,
                blocks_work=True,
                alerts=["No address check recorded"] if evidence_count > 0 else []
            )
        
        # Determine status
        docs_received = check.get("documents_received_count", 0)
        docs_required = check.get("documents_required_count", 2)
        all_recent = check.get("all_documents_sufficiently_recent", False)
        
        if check.get("outcome") != "verified":
            status = ComplianceStatus.ATTENTION_REQUIRED
        elif docs_received < docs_required:
            status = ComplianceStatus.ATTENTION_REQUIRED
        elif not all_recent:
            status = ComplianceStatus.ATTENTION_REQUIRED
        else:
            status = ComplianceStatus.COMPLIANT
        
        alerts = []
        if docs_received < docs_required:
            alerts.append(f"Only {docs_received}/{docs_required} documents verified")
        if not all_recent:
            alerts.append("Some documents are outdated")
        
        return RequirementSummary(
            status=status,
            is_verified=check.get("outcome") == "verified",
            verified_at=check.get("created_at"),
            verified_by=check.get("checked_by_name"),
            method=check.get("method"),
            evidence_count=evidence_count,
            blocks_work=True,
            alerts=alerts,
            last_updated=check.get("updated_at") or check.get("created_at")
        )
    
    async def _get_references_status(self, employee_id: str) -> RequirementSummary:
        """Get References status - requires minimum 2 verified references."""
        refs = await self.db.references.find({"employee_id": employee_id}).to_list(100)
        
        verified_count = sum(1 for r in refs if r.get("status") == "verified")
        pending_count = sum(1 for r in refs if r.get("status") in ["pending", "received"])
        
        # Determine status
        if len(refs) == 0:
            status = ComplianceStatus.MISSING
        elif verified_count >= 2:
            status = ComplianceStatus.COMPLIANT
        elif verified_count + pending_count >= 2:
            status = ComplianceStatus.ATTENTION_REQUIRED
        else:
            status = ComplianceStatus.ATTENTION_REQUIRED
        
        alerts = []
        if verified_count < 2:
            alerts.append(f"Only {verified_count}/2 references verified")
        if pending_count > 0:
            alerts.append(f"{pending_count} reference(s) pending")
        
        return RequirementSummary(
            status=status,
            is_verified=verified_count >= 2,
            evidence_count=len(refs),
            pending_review_count=pending_count,
            blocks_work=True,  # Configurable per organization
            alerts=alerts
        )
    
    async def _get_training_status(self, employee_id: str) -> RequirementSummary:
        """Get Training status."""
        # Get employee's role to determine required training
        employee = await self.db.employees.find_one({"id": employee_id})
        
        # Get all training records
        records = await self.db.training_records.find({"employee_id": employee_id}).to_list(100)
        
        # Get mandatory training types
        mandatory_types = await self.db.training_types.find({"category": "mandatory"}).to_list(100)
        
        if not mandatory_types:
            return RequirementSummary(
                status=ComplianceStatus.COMPLIANT,
                is_verified=True,
                blocks_work=True,
                alerts=["No mandatory training defined"]
            )
        
        # Check completion
        completed = 0
        expired = 0
        alerts = []
        
        today = date.today()
        
        for training_type in mandatory_types:
            record = next((r for r in records if r.get("training_type_id") == training_type.get("id")), None)
            
            if not record:
                alerts.append(f"{training_type.get('name')} not completed")
            elif record.get("expiry_date"):
                exp = record["expiry_date"]
                if isinstance(exp, str):
                    exp = date.fromisoformat(exp)
                elif not isinstance(exp, date):
                    exp = exp.date()
                
                if exp < today:
                    expired += 1
                    alerts.append(f"{training_type.get('name')} expired")
                else:
                    completed += 1
            else:
                completed += 1
        
        # Determine status
        if len(alerts) == 0:
            status = ComplianceStatus.COMPLIANT
        elif expired > 0:
            status = ComplianceStatus.EXPIRED
        else:
            status = ComplianceStatus.ATTENTION_REQUIRED
        
        return RequirementSummary(
            status=status,
            is_verified=len(alerts) == 0,
            evidence_count=len(records),
            blocks_work=True,
            alerts=alerts
        )
    
    async def _get_health_status(self, employee_id: str) -> RequirementSummary:
        """Get Occupational Health status."""
        declaration = await self.db.health_declarations.find_one(
            {"employee_id": employee_id},
            sort=[("declaration_date", -1)]
        )
        
        if not declaration:
            return RequirementSummary(
                status=ComplianceStatus.MISSING,
                blocks_work=True,
                alerts=["No health declaration submitted"]
            )
        
        # Determine status based on declaration
        health_status = declaration.get("status", "requires_review")
        
        if health_status == "fit":
            status = ComplianceStatus.COMPLIANT
        elif health_status == "not_fit":
            status = ComplianceStatus.ATTENTION_REQUIRED
        else:
            status = ComplianceStatus.ATTENTION_REQUIRED
        
        alerts = []
        if health_status == "requires_review":
            alerts.append("Health declaration requires review")
        if health_status == "not_fit":
            alerts.append("Declared not fit for work")
        if declaration.get("conditions_disclosed"):
            alerts.append("Health conditions disclosed")
        
        return RequirementSummary(
            status=status,
            is_verified=health_status == "fit",
            verified_at=declaration.get("reviewed_at"),
            verified_by=declaration.get("reviewed_by"),
            blocks_work=True,
            alerts=alerts,
            last_updated=declaration.get("reviewed_at") or declaration.get("declaration_date")
        )
    
    def _calculate_overall_status(
        self, 
        requirements: Dict[str, RequirementSummary], 
        blockers: List[Dict]
    ) -> OverallStatus:
        """Calculate overall status."""
        # Check for expired
        has_expired = any(r.status == ComplianceStatus.EXPIRED and r.blocks_work for r in requirements.values())
        if has_expired:
            return OverallStatus.EXPIRED
        
        # Check for blockers
        if len(blockers) > 0:
            return OverallStatus.NOT_READY
        
        # Check for attention items
        has_attention = any(r.status == ComplianceStatus.ATTENTION_REQUIRED for r in requirements.values())
        if has_attention:
            return OverallStatus.REQUIRES_ATTENTION
        
        return OverallStatus.READY_TO_WORK
    
    def _calculate_regulatory_status(self, requirements: Dict[str, RequirementSummary]) -> str:
        """
        Calculate strict regulatory status for CQC reporting.
        More conservative than operational status.
        """
        statuses = [r.status for r in requirements.values() if r.blocks_work]
        
        if any(s == ComplianceStatus.EXPIRED for s in statuses):
            return "EXPIRED"
        elif any(s == ComplianceStatus.MISSING for s in statuses):
            return "NOT_READY"
        elif any(s == ComplianceStatus.ATTENTION_REQUIRED for s in statuses):
            return "REQUIRES_ATTENTION"
        else:
            return "READY_TO_WORK"
    
    def _get_blocker_reason(self, key: str, req: RequirementSummary) -> str:
        """Get human-readable blocker reason."""
        if req.status == ComplianceStatus.MISSING:
            return f"{self.REQUIREMENTS[key]['label']} not recorded"
        elif req.status == ComplianceStatus.EXPIRED:
            return f"{self.REQUIREMENTS[key]['label']} expired"
        elif req.status == ComplianceStatus.ATTENTION_REQUIRED:
            if req.alerts:
                return req.alerts[0]
            return f"{self.REQUIREMENTS[key]['label']} requires attention"
        return ""
    
    async def _store_summary(self, summary: EmployeeComplianceSummary):
        """Store summary in database for caching."""
        # Convert to dict and ensure all dates are JSON serializable
        summary_dict = summary.dict()
        
        # Convert date objects to ISO strings in requirements
        for key, req in summary_dict.get("requirements", {}).items():
            if isinstance(req, dict):
                if req.get("expiry_date") and isinstance(req["expiry_date"], date):
                    req["expiry_date"] = req["expiry_date"].isoformat()
                if req.get("verified_at") and isinstance(req["verified_at"], datetime):
                    req["verified_at"] = req["verified_at"].isoformat()
                if req.get("last_updated") and isinstance(req["last_updated"], datetime):
                    req["last_updated"] = req["last_updated"].isoformat()
        
        # Convert top-level datetime
        if isinstance(summary_dict.get("last_calculated_at"), datetime):
            summary_dict["last_calculated_at"] = summary_dict["last_calculated_at"].isoformat()
        
        await self.db.employee_compliance_summary.update_one(
            {"employee_id": summary.employee_id},
            {"$set": summary_dict},
            upsert=True
        )
    
    async def get_cached_summary(self, employee_id: str) -> Optional[Dict]:
        """Get cached summary if available."""
        return await self.db.employee_compliance_summary.find_one(
            {"employee_id": employee_id},
            {"_id": 0}
        )


# Service instance
compliance_status_service: Optional[ComplianceStatusService] = None


def init_compliance_status_service(db) -> ComplianceStatusService:
    """Initialize the compliance status service."""
    global compliance_status_service
    compliance_status_service = ComplianceStatusService(db)
    return compliance_status_service


def get_compliance_status_service() -> ComplianceStatusService:
    """Get the compliance status service instance."""
    global compliance_status_service
    if compliance_status_service is None:
        raise RuntimeError("Compliance status service not initialized")
    return compliance_status_service
