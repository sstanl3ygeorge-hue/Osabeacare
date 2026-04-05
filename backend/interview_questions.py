"""
Role-Specific Interview Questions for NHS Adult Care Recruitment

Based on NHS Employment Standards:
- Healthcare Assistant: 10 standard questions (adult care focused)
- Nurse: 16 questions (10 standard + 6 clinical questions)

Note: Osabea Healthcare Solutions provides care for ADULTS ONLY.
No children's services - therefore no safeguarding children questions.
"""

# ============================================================================
# HEALTHCARE ASSISTANT INTERVIEW QUESTIONS (10 Questions - Adult Care)
# ============================================================================

HCA_INTERVIEW_QUESTIONS = [
    {
        "id": "hca_q1",
        "question": "Why do you want to work as a Healthcare Assistant in adult care?",
        "category": "motivation",
        "assessment_criteria": "Motivation, values, understanding of care role",
        "required": True,
        "order": 1
    },
    {
        "id": "hca_q2",
        "question": "Tell me about a time you provided excellent care to an older adult or vulnerable person.",
        "category": "experience",
        "assessment_criteria": "Empathy, compassion, practical experience",
        "required": True,
        "order": 2
    },
    {
        "id": "hca_q3",
        "question": "How do you handle stressful situations in a care environment?",
        "category": "resilience",
        "assessment_criteria": "Resilience, calm under pressure, coping strategies",
        "required": True,
        "order": 3
    },
    {
        "id": "hca_q4",
        "question": "Describe a situation where you worked as part of a care team.",
        "category": "teamwork",
        "assessment_criteria": "Teamwork, communication, collaboration",
        "required": True,
        "order": 4
    },
    {
        "id": "hca_q5",
        "question": "How would you support a resident who is anxious or distressed?",
        "category": "patient_care",
        "assessment_criteria": "Patient-centred care, de-escalation, empathy",
        "required": True,
        "order": 5
    },
    {
        "id": "hca_q6",
        "question": "What does dignity and respect mean to you in adult care?",
        "category": "values",
        "assessment_criteria": "Professional values, person-centred approach",
        "required": True,
        "order": 6
    },
    {
        "id": "hca_q7",
        "question": "How do you maintain patient confidentiality?",
        "category": "compliance",
        "assessment_criteria": "Data protection, GDPR, professional boundaries",
        "required": True,
        "order": 7
    },
    {
        "id": "hca_q8",
        "question": "Tell me about your experience with manual handling.",
        "category": "safety",
        "assessment_criteria": "Safety awareness, practical skills, training",
        "required": True,
        "order": 8
    },
    {
        "id": "hca_q9",
        "question": "Are you flexible with shifts and locations?",
        "category": "availability",
        "assessment_criteria": "Availability, flexibility, commitment",
        "required": True,
        "order": 9
    },
    {
        "id": "hca_q10",
        "question": "Do you have a valid driving licence and access to a vehicle? (for community roles)",
        "category": "practical",
        "assessment_criteria": "Practical requirement for community care roles",
        "required": False,
        "order": 10
    }
]

# ============================================================================
# NURSE ADDITIONAL CLINICAL QUESTIONS (6 Questions - Added to HCA base)
# ============================================================================

NURSE_CLINICAL_QUESTIONS = [
    {
        "id": "nurse_q1",
        "question": "Tell me about your nursing degree and clinical placements in adult care.",
        "category": "qualifications",
        "assessment_criteria": "Education background, clinical experience",
        "required": True,
        "order": 11
    },
    {
        "id": "nurse_q2",
        "question": "Describe a time you made a clinical decision that improved outcomes for an adult patient.",
        "category": "clinical_judgment",
        "assessment_criteria": "Clinical decision-making, patient outcomes",
        "required": True,
        "order": 12
    },
    {
        "id": "nurse_q3",
        "question": "How do you ensure you're working within your NMC Code of Conduct?",
        "category": "professional_standards",
        "assessment_criteria": "NMC standards, professional accountability",
        "required": True,
        "order": 13
    },
    {
        "id": "nurse_q4",
        "question": "Tell me about your experience with medication administration in adult care.",
        "category": "medication",
        "assessment_criteria": "Medication competency, safety protocols",
        "required": True,
        "order": 14
    },
    {
        "id": "nurse_q5",
        "question": "Describe a challenging clinical situation with an adult patient and how you handled it.",
        "category": "clinical_experience",
        "assessment_criteria": "Problem-solving, clinical skills, adaptability",
        "required": True,
        "order": 15
    },
    {
        "id": "nurse_q6",
        "question": "What is your NMC registration number and is it active?",
        "category": "registration",
        "assessment_criteria": "Professional registration verification",
        "required": True,
        "order": 16
    }
]

# ============================================================================
# INTERVIEW SCORING CONFIGURATION
# ============================================================================

INTERVIEW_SCORING = {
    "scale": {
        "min": 1,
        "max": 5,
        "labels": {
            1: "Poor - Does not meet requirements",
            2: "Below Average - Partially meets requirements",
            3: "Average - Meets basic requirements",
            4: "Good - Exceeds requirements",
            5: "Excellent - Significantly exceeds requirements"
        }
    },
    "pass_threshold": 3,  # Minimum average score to pass
    "critical_questions": ["hca_q6", "hca_q7", "nurse_q3", "nurse_q6"],  # Must score 3+ on these
    "overall_pass_score": 60  # Percentage of maximum possible score
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_interview_questions_for_role(role: str) -> list:
    """
    Get the appropriate interview questions for a role.
    
    Args:
        role: Employee role (healthcare_assistant, nurse, etc.)
    
    Returns:
        List of interview questions
    """
    role_lower = role.lower().strip() if role else ""
    
    # Map role variations
    role_mapping = {
        "hca": "healthcare_assistant",
        "healthcare assistant": "healthcare_assistant",
        "health care assistant": "healthcare_assistant",
        "carer": "healthcare_assistant",
        "care assistant": "healthcare_assistant",
        "senior carer": "healthcare_assistant",
        "senior care assistant": "healthcare_assistant",
        "support worker": "healthcare_assistant",
        "registered nurse": "nurse",
        "rn": "nurse",
        "rgn": "nurse",
        "nurse": "nurse"
    }
    
    normalized_role = role_mapping.get(role_lower, "healthcare_assistant")
    
    if normalized_role == "nurse":
        # Nurses get HCA questions + clinical questions
        return HCA_INTERVIEW_QUESTIONS + NURSE_CLINICAL_QUESTIONS
    else:
        # All other roles get HCA questions
        return HCA_INTERVIEW_QUESTIONS


def get_interview_question_count(role: str) -> dict:
    """
    Get the question count for a role.
    
    Returns:
        Dict with total, required, and optional counts
    """
    questions = get_interview_questions_for_role(role)
    
    required = sum(1 for q in questions if q.get("required", True))
    optional = sum(1 for q in questions if not q.get("required", True))
    
    return {
        "total": len(questions),
        "required": required,
        "optional": optional
    }


def get_role_interview_config(role: str) -> dict:
    """
    Get complete interview configuration for a role.
    
    Returns:
        Full config including questions, scoring, and metadata
    """
    questions = get_interview_questions_for_role(role)
    counts = get_interview_question_count(role)
    
    role_lower = role.lower().strip() if role else ""
    is_nurse = "nurse" in role_lower
    
    return {
        "role": role,
        "is_nurse_role": is_nurse,
        "questions": questions,
        "question_counts": counts,
        "scoring": INTERVIEW_SCORING,
        "max_possible_score": counts["total"] * INTERVIEW_SCORING["scale"]["max"],
        "pass_threshold_score": int(counts["total"] * INTERVIEW_SCORING["scale"]["max"] * (INTERVIEW_SCORING["overall_pass_score"] / 100))
    }


# ============================================================================
# ROLE REQUIREMENTS SUMMARY (For Display)
# ============================================================================

ROLE_REQUIREMENTS_SUMMARY = {
    "healthcare_assistant": {
        "display_name": "Healthcare Assistant (HCA)",
        "professional_registration": None,
        "mandatory_training_count": 6,
        "mandatory_training": [
            "Safeguarding Adults",
            "Manual Handling",
            "Fire Safety",
            "Health & Safety",
            "Basic Life Support (BLS)",
            "Infection Prevention & Control"
        ],
        "interview_questions": 10,
        "documents_required": [
            "Passport (photo ID)",
            "Proof of Address (2 documents)",
            "Right to Work (Share Code)",
            "DBS Certificate (Enhanced)"
        ],
        "optional_qualifications": [
            "NVQ/BTEC in Health & Social Care",
            "Care Certificate"
        ],
        "total_gates": 12
    },
    "nurse": {
        "display_name": "Registered Nurse",
        "professional_registration": {
            "body": "NMC",
            "body_name": "Nursing & Midwifery Council",
            "check_url": "https://www.nmc.org.uk/registration/search/"
        },
        "mandatory_training_count": 6,
        "mandatory_training": [
            "Safeguarding Adults",
            "Manual Handling",
            "Fire Safety",
            "Health & Safety",
            "Basic Life Support (BLS)",
            "Infection Prevention & Control"
        ],
        "additional_competencies": [
            "Clinical Competency",
            "Medication Competency"
        ],
        "interview_questions": 16,
        "documents_required": [
            "Passport (photo ID)",
            "Proof of Address (2 documents)",
            "Right to Work (Share Code)",
            "DBS Certificate (Enhanced)",
            "Nursing Degree Certificate",
            "NMC Registration Certificate",
            "Professional Indemnity Insurance"
        ],
        "total_gates": 14
    }
}


def get_role_requirements(role: str) -> dict:
    """Get requirements summary for a role."""
    role_lower = role.lower().strip() if role else ""
    
    if "nurse" in role_lower:
        return ROLE_REQUIREMENTS_SUMMARY["nurse"]
    else:
        return ROLE_REQUIREMENTS_SUMMARY["healthcare_assistant"]
