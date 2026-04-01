"""
stage_identity.py - Applicant vs Employee Stage Identity

Determines whether a person is in applicant or employee stage
based on their status and recruitment_approved flag.
"""

# Applicant statuses - person is still in recruitment pipeline
APPLICANT_STATUSES = ["new", "screening", "interview", "compliance_review"]

# Employee statuses - person has been approved and is onboarding/working
EMPLOYEE_STATUSES = ["onboarding", "active", "inactive"]

# All valid statuses
ALL_STATUSES = APPLICANT_STATUSES + EMPLOYEE_STATUSES + ["archived"]


def get_stage_identity(person: dict) -> str:
    """
    Determine the stage identity of a person.
    
    Args:
        person: Employee/applicant document
        
    Returns:
        "applicant" or "employee"
    """
    if not person:
        return "applicant"
    
    # recruitment_approved=true always means employee
    if person.get("recruitment_approved") is True:
        return "employee"
    
    status = person.get("status", "new")
    
    # Check status-based identity
    if status in EMPLOYEE_STATUSES:
        return "employee"
    
    if status in APPLICANT_STATUSES:
        return "applicant"
    
    # Archived - check if they were ever an employee
    if status == "archived":
        # If they have an employee_code, they were an employee
        if person.get("employee_code"):
            return "employee"
        return "applicant"
    
    # Default to applicant
    return "applicant"


def is_applicant(person: dict) -> bool:
    """Check if person is in applicant stage"""
    return get_stage_identity(person) == "applicant"


def is_employee(person: dict) -> bool:
    """Check if person is in employee stage"""
    return get_stage_identity(person) == "employee"


def get_stage_identity_label(person: dict) -> str:
    """Get human-readable label for stage identity"""
    identity = get_stage_identity(person)
    return "Applicant" if identity == "applicant" else "Employee"


def enrich_person_with_stage_identity(person: dict) -> dict:
    """
    Add stage identity fields to a person document.
    
    Adds:
        - stage_identity: "applicant" or "employee"
        - is_applicant: bool
        - is_employee: bool
        
    Returns:
        The same dict with added fields (mutates in place)
    """
    if not person:
        return person
    
    identity = get_stage_identity(person)
    person["stage_identity"] = identity
    person["is_applicant"] = identity == "applicant"
    person["is_employee"] = identity == "employee"
    
    return person


def build_stage_filter(stage_identity: str = None) -> dict:
    """
    Build MongoDB filter for stage identity.
    
    Args:
        stage_identity: "applicant", "employee", or None (all)
        
    Returns:
        MongoDB filter dict
    """
    if not stage_identity or stage_identity == "all":
        return {}
    
    if stage_identity == "applicant":
        return {
            "$and": [
                {"recruitment_approved": {"$ne": True}},
                {"status": {"$in": APPLICANT_STATUSES}}
            ]
        }
    
    if stage_identity == "employee":
        return {
            "$or": [
                {"recruitment_approved": True},
                {"status": {"$in": EMPLOYEE_STATUSES}}
            ]
        }
    
    return {}
