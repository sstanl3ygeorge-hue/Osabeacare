from __future__ import annotations

from typing import Optional, Tuple


APPLICANT_STATUSES = {"new", "screening", "interview", "compliance_review"}
EMPLOYEE_STATUSES = {"onboarding", "active", "inactive"}
TERMINAL_STATUSES = {"archived", "withdrawn", "superseded", "deleted"}


def guard_cross_gate_status_transition(
    current_status: Optional[str],
    requested_status: Optional[str],
) -> Tuple[bool, Optional[str]]:
    """
    Block non-gate lifecycle crossings on generic update routes.

    Allowed on generic update routes:
    - applicant -> applicant stage changes
    - employee -> employee stage changes
    - terminal flows
    - no-op / missing requested status
    """
    if not requested_status:
        return True, None
    if not current_status:
        return True, None
    if current_status == requested_status:
        return True, None

    if current_status in TERMINAL_STATUSES or requested_status in TERMINAL_STATUSES:
        return True, None

    if current_status in APPLICANT_STATUSES and requested_status in EMPLOYEE_STATUSES:
        return False, "Use recruitment approval gate to move applicant into employee lifecycle"

    if current_status in EMPLOYEE_STATUSES and requested_status in APPLICANT_STATUSES:
        return False, "Cannot move employee lifecycle records back into applicant lifecycle"

    return True, None
