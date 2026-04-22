"""
Governance plumbing package — Phase 1.

Shared primitives used by every Phase 1 governance domain (supervisions,
competency reassessments, spot checks, incidents + safeguarding, care-plan
reviews).  The provider-profile domain lives on the organisation side and
deliberately does NOT feed worker governance readiness.

This package owns:
    - readiness.compute_worker_governance_readiness() : pure helper
    - audit.new_audit_metadata() / audit.audit_trail_entry() / audit.stamp_update()
    - guards.require_employee_not_applicant : FastAPI dependency

Conventions (see PHASE_1_GOVERNANCE_PLAN.md §0):
    - Due dates are owned by `recurring_compliance`, never by domain tables.
    - Readiness counts only `verification_status == "verified"` records.
    - Every admin governance route MUST depend on
      `require_employee_not_applicant` so no domain leaks into applicant
      context.
    - `governance_readiness` is a SIBLING of `employment_readiness` on the
      worker dashboard payload — it is never merged into employment readiness.
"""

from .readiness import (
    GOVERNANCE_READINESS_STATES,
    compute_worker_governance_readiness,
)
from .audit import (
    new_audit_metadata,
    audit_trail_entry,
    stamp_update,
)
from .guards import require_employee_not_applicant

__all__ = [
    "GOVERNANCE_READINESS_STATES",
    "compute_worker_governance_readiness",
    "new_audit_metadata",
    "audit_trail_entry",
    "stamp_update",
    "require_employee_not_applicant",
]
