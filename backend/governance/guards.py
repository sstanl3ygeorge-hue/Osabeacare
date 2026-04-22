"""
Shared FastAPI guards for Phase 1 governance routes.

The applicant guard is the single reason no governance domain can leak into
applicant context.  EVERY Phase 1 admin governance route must depend on
``require_employee_not_applicant`` (see PHASE_1_GOVERNANCE_PLAN.md §0).

Do not replicate this check inside individual routes — import it from here so
the rule stays in one place.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import HTTPException, Path

# Import lazily-safe: both modules are importable at startup time.
from routes.dependencies import get_db
from routes.employees import PersonStage, get_person_stage


async def _load_employee(employee_id: str, db=None) -> Dict[str, Any]:
    """Fetch the minimal employee projection needed by the guard.

    Split out so tests can exercise the guard without starting FastAPI.
    """
    database = db if db is not None else get_db()
    emp = await database.employees.find_one(
        {"id": employee_id},
        {"_id": 0, "id": 1, "status": 1, "person_stage": 1, "first_name": 1, "last_name": 1, "role": 1},
    )
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    return emp


def _resolve_person_stage(employee: Dict[str, Any]) -> str:
    """Prefer the explicit ``person_stage`` field when present; otherwise
    derive it from ``status`` using the existing canonical mapping.
    """
    explicit = (employee.get("person_stage") or "").strip().lower()
    if explicit in (PersonStage.APPLICANT, PersonStage.EMPLOYEE, PersonStage.ARCHIVED):
        return explicit
    return get_person_stage(employee.get("status") or "")


async def require_employee_not_applicant(
    employee_id: str = Path(..., description="Employee id"),
) -> Dict[str, Any]:
    """FastAPI dependency: load the employee and reject applicant records.

    Returns the employee projection so the route handler does not have to
    fetch it again.  Raises:
        404 if the employee does not exist,
        403 if the person_stage is ``applicant``.

    Archived records are allowed through — historical governance records must
    remain readable for inspection/audit.  Use a stricter guard at the route
    level if a specific endpoint needs an active-only rule.
    """
    return await _guard_employee_not_applicant(employee_id)


async def _guard_employee_not_applicant(
    employee_id: str, db=None
) -> Dict[str, Any]:
    """Pure async implementation — exposed for unit tests.

    Tests call this directly with a fake db so the guard can be validated
    without FastAPI.  The public dependency above is a thin wrapper.
    """
    employee = await _load_employee(employee_id, db=db)
    stage = _resolve_person_stage(employee)
    if stage == PersonStage.APPLICANT:
        raise HTTPException(
            status_code=403,
            detail=(
                "Governance modules are not available for applicants. "
                "Complete onboarding first."
            ),
        )
    return employee
