"""
Role-Specific Interview Questions for NHS Adult Care Recruitment
Osabea Healthcare Solutions - CQC Compliant Interview Template

Based on:
- Osabea Interview Questions Support Workers template
- NHS Employment Check Standards
- CQC Fundamental Standards

Scoring Scale (0-3):
- 0: Does not meet criteria
- 1: Part meets criteria  
- 2: Meets criteria
- 3: Exceeds criteria

Minimum Score Required: 11 points out of 24 (46%)

Note: Osabea Healthcare Solutions provides care for ADULTS ONLY.
"""

# ============================================================================
# OSABEA SUPPORT WORKER INTERVIEW QUESTIONS (8 Questions - 0-3 Scale)
# Based on official Osabea Interview Questions Support Workers template
# ============================================================================

SUPPORT_WORKER_INTERVIEW_QUESTIONS = [
    {
        "id": "sw_q1",
        "question": "What interested you in applying for the position of Care Worker?",
        "category": "understanding_role_motivation",
        "skills_assessed": "Motivation, values, understanding of care role",
        "scoring_criteria": {
            "0": "No clear interest or generic answer",
            "1": "Mentions general interest in caring roles or helping people without specific connection to the position",
            "2": "Demonstrates an understanding of what a Care Worker does and expresses a genuine desire to help others, aligning with the role's purpose",
            "3": "Articulates a personal connection or passion for care work, referencing specific values or experiences that draw them to this particular role. Shows understanding of impact of care work."
        },
        "expected_answer_notes": "Look for passion, empathy, and genuine desire to make a difference. Candidates should show awareness of the organization or type of support provided. Answers should be specific to Care Worker role.",
        "required": True,
        "order": 1,
        "max_score": 3
    },
    {
        "id": "sw_q2",
        "question": "How will you ensure that the person is supported to lead the life that they choose?",
        "category": "person_centred_support",
        "skills_assessed": "Communication, understanding, person-centred approach, working with individuals/families/staff",
        "scoring_criteria": {
            "0": "No understanding of person-centred planning or individual choice",
            "1": "Mentions listening to the individual but lacks concrete strategies",
            "2": "Describes actively listening to preferences, involving them in decision-making, working with them to identify goals. Mentions communication with families and staff.",
            "3": "Articulates comprehensive approach to person-centred support. Demonstrates deep understanding of empowering individuals - proactive communication, collaborative goal-setting, respecting autonomy, advocating for choices."
        },
        "expected_answer_notes": "Emphasis on 'choice' and 'leading the life they choose'. Active listening, understanding individual needs. Involving individual in their own care planning. Communication with families and staff.",
        "required": True,
        "order": 2,
        "max_score": 3
    },
    {
        "id": "sw_q3",
        "question": "Tell us about a time when you worked as part of a team to achieve a successful goal?",
        "category": "teamwork_collaboration",
        "skills_assessed": "Team ethic, motivation, responsibility, relationships, taking direction",
        "scoring_criteria": {
            "0": "Cannot provide an example or example lacks team involvement",
            "1": "Provides basic example of working with others but doesn't clearly demonstrate teamwork or shared goal",
            "2": "Describes situation where they contributed to team effort, highlighting their role, listening to others, working towards common objective",
            "3": "Provides detailed compelling example showcasing strong teamwork skills - actively contributing, supporting colleagues, communicating effectively, taking responsibility, demonstrating how actions helped achieve specific successful outcome"
        },
        "expected_answer_notes": "STAR method (Situation, Task, Action, Result) is good framework. Focus on collaboration, communication, shared responsibility. Evidence of working towards common goal.",
        "required": True,
        "order": 3,
        "max_score": 3
    },
    {
        "id": "sw_q4",
        "question": "What is it about your personality that makes you successful at building relationships and networks?",
        "category": "relationship_building",
        "skills_assessed": "Building bridges for person supported, linking to people/organisations, self-awareness",
        "scoring_criteria": {
            "0": "No understanding of how personality traits contribute to relationship building",
            "1": "Mentions general positive traits like being friendly, but doesn't connect to practical application",
            "2": "Identifies specific traits (empathetic, good listener, patient, approachable) and explains how these help connect with individuals. Shows awareness of linking to networks.",
            "3": "Articulates strong understanding of how personality fosters trust and rapport. Provides concrete examples of building genuine connections with individuals, families, friends, colleagues, and community resources. Demonstrates self-awareness."
        },
        "expected_answer_notes": "Keywords: empathy, active listening, patience, trustworthiness, reliability, openness. Understanding of individual's existing network and building new connections.",
        "required": True,
        "order": 4,
        "max_score": 3
    },
    {
        "id": "sw_q5",
        "question": "Some of the individuals we support may become anxious and challenge. What do you feel you would need to know about an individual to help them? Can you give an example of challenging behaviour you have dealt with?",
        "category": "challenging_behaviour",
        "skills_assessed": "Understanding challenging behaviour, consistent support, safety protocols, knowing triggers, de-escalation, forward planning",
        "scoring_criteria": {
            "0": "No understanding of challenging behaviour or how to manage it",
            "1": "Provides very basic understanding, mentions needing information but lacks detail on what or how to act",
            "2": "Demonstrates good understanding of challenging behaviour as communication. Identifies key info needed (triggers, communication methods, history, preferences). Describes situation with reasonable response showing de-escalation.",
            "3": "Exhibits thorough understanding recognizing it as symptom of unmet needs. Articulates detailed list of essential info (history, communication styles, sensory needs, coping mechanisms, triggers, de-escalation strategies). Provides clear effective example with calm professional person-centred approach."
        },
        "expected_answer_notes": "Challenging behaviour as communication. Key info: triggers, communication preferences, personal history, what calms/escalates them. Importance of consistency. Adherence to care plans and risk assessments.",
        "required": True,
        "order": 5,
        "max_score": 3
    },
    {
        "id": "sw_q6",
        "question": "How would you know if you were doing a good job for them?",
        "category": "performance_evaluation",
        "skills_assessed": "Individual's demeanour, progress, feedback from individual/family/team/managers/professionals",
        "scoring_criteria": {
            "0": "No understanding of how to assess their own performance in a care role",
            "1": "Mentions general job satisfaction without specific indicators",
            "2": "Identifies key indicators such as individual's happiness or progress, mentions seeking feedback from others",
            "3": "Articulates comprehensive understanding of performance evaluation - observing individual's demeanour and progress, actively seeking and valuing feedback from individual, family, colleagues, other professionals. Understands 'doing a good job' is multi-faceted and client-focused."
        },
        "expected_answer_notes": "Focus on individual's well-being and outcomes. Observation of mood, engagement, progress towards goals. Seeking feedback from individual themselves, family, other staff, external professionals.",
        "required": True,
        "order": 6,
        "max_score": 3
    },
    {
        "id": "sw_q7",
        "question": "What do you see as the benefits and challenges of supporting in the community?",
        "category": "community_support",
        "skills_assessed": "Following guidance, crisis management, risk understanding, confidence in community work",
        "scoring_criteria": {
            "0": "No understanding of community-based support",
            "1": "Mentions one benefit or challenge without detail",
            "2": "Identifies several benefits (integration, independence, variety) and challenges (public perception, safety, accessibility). Shows awareness of following guidance and managing risks.",
            "3": "Provides well-rounded perspective - clear benefits (promoting independence, social inclusion, real-life experiences) and thoughtful challenges (navigating public attitudes, safety concerns, logistical issues). Demonstrates strong understanding of guidance and risk assessment, and confident management of potential issues."
        },
        "expected_answer_notes": "Benefits: increased independence, social inclusion, greater variety, living life as citizen. Challenges: public perception, safety concerns, navigating unfamiliar environments, accessibility. Following guidance and risk assessments.",
        "required": True,
        "order": 7,
        "max_score": 3
    },
    {
        "id": "sw_q8",
        "question": "We need people that will be committed to the people they support and the team. How have you demonstrated commitment in a work setting before?",
        "category": "commitment_values",
        "skills_assessed": "Values, trust-building, teamwork, flexibility",
        "scoring_criteria": {
            "0": "Cannot provide an example of commitment",
            "1": "Provides vague example without specific actions or outcomes",
            "2": "Describes situation showing dedication to task, person, or team - mentioning reliability and willingness to go extra mile. Touches on teamwork or relationship building.",
            "3": "Provides strong specific example clearly illustrating dedication to individuals and/or team. Demonstrates reliability, going above and beyond, genuine understanding of importance of building trusting relationships and working effectively as team. Shows flexibility and proactive attitude."
        },
        "expected_answer_notes": "Examples of going above and beyond. Reliability and dependability. Consistency in support. Willingness to adapt and be flexible. Contributing positively to team morale. Building trust through actions.",
        "required": True,
        "order": 8,
        "max_score": 3
    }
]

# Alias for backward compatibility
HCA_INTERVIEW_QUESTIONS = SUPPORT_WORKER_INTERVIEW_QUESTIONS

# ============================================================================
# NURSE ADDITIONAL CLINICAL QUESTIONS (6 Questions - Added to Support Worker base)
# For Registered Nurses: Use Support Worker questions + these clinical questions
# ============================================================================

NURSE_CLINICAL_QUESTIONS = [
    {
        "id": "nurse_q1",
        "question": "Tell me about your nursing degree and clinical placements in adult care.",
        "category": "qualifications",
        "skills_assessed": "Education background, clinical experience",
        "scoring_criteria": {
            "0": "No relevant nursing qualification or unable to describe placements",
            "1": "Has nursing qualification but limited experience in adult care settings",
            "2": "Has nursing qualification with relevant adult care placement experience",
            "3": "Has nursing qualification with extensive adult care experience across multiple settings"
        },
        "expected_answer_notes": "Look for relevant adult care placements, understanding of adult health conditions, practical nursing skills.",
        "required": True,
        "order": 9,
        "max_score": 3
    },
    {
        "id": "nurse_q2",
        "question": "Describe a time you made a clinical decision that improved outcomes for an adult patient.",
        "category": "clinical_judgment",
        "skills_assessed": "Clinical decision-making, patient outcomes, evidence-based practice",
        "scoring_criteria": {
            "0": "Cannot provide relevant example",
            "1": "Provides basic example but lacks clear clinical reasoning",
            "2": "Provides good example with clear clinical reasoning and positive outcome",
            "3": "Provides excellent example demonstrating advanced clinical judgment, evidence-based approach, and measurable positive outcome"
        },
        "expected_answer_notes": "Look for clinical reasoning process, assessment skills, consideration of patient safety, measurable outcomes.",
        "required": True,
        "order": 10,
        "max_score": 3
    },
    {
        "id": "nurse_q3",
        "question": "How do you ensure you're working within your NMC Code of Conduct?",
        "category": "professional_standards",
        "skills_assessed": "NMC standards, professional accountability, revalidation",
        "scoring_criteria": {
            "0": "No understanding of NMC Code",
            "1": "Basic awareness of NMC Code but limited application",
            "2": "Good understanding of NMC Code with practical examples of application",
            "3": "Comprehensive understanding with clear commitment to professional standards, revalidation process, and continuous development"
        },
        "expected_answer_notes": "Understanding of NMC Code pillars: prioritise people, practise effectively, preserve safety, promote professionalism and trust.",
        "required": True,
        "order": 11,
        "max_score": 3,
        "is_critical": True
    },
    {
        "id": "nurse_q4",
        "question": "Tell me about your experience with medication administration in adult care.",
        "category": "medication",
        "skills_assessed": "Medication competency, safety protocols, controlled drugs",
        "scoring_criteria": {
            "0": "No relevant medication experience",
            "1": "Basic medication administration experience",
            "2": "Good experience with medication administration including controlled drugs and safety checks",
            "3": "Extensive experience including complex medications, controlled drugs, medication reconciliation, and incident management"
        },
        "expected_answer_notes": "Look for knowledge of 5 rights, controlled drugs procedures, documentation, error prevention.",
        "required": True,
        "order": 12,
        "max_score": 3,
        "is_critical": True
    },
    {
        "id": "nurse_q5",
        "question": "Describe a challenging clinical situation with an adult patient and how you handled it.",
        "category": "clinical_experience",
        "skills_assessed": "Problem-solving, clinical skills, adaptability, escalation",
        "scoring_criteria": {
            "0": "Cannot provide relevant example",
            "1": "Provides basic example but limited problem-solving demonstrated",
            "2": "Provides good example with clear problem-solving and appropriate escalation",
            "3": "Provides excellent example demonstrating advanced clinical skills, critical thinking, appropriate escalation, and reflection on learning"
        },
        "expected_answer_notes": "Look for clinical assessment, prioritisation, escalation when appropriate, reflection on learning.",
        "required": True,
        "order": 13,
        "max_score": 3
    },
    {
        "id": "nurse_q6",
        "question": "What is your NMC registration number and is it active?",
        "category": "registration",
        "skills_assessed": "Professional registration verification, PIN check",
        "scoring_criteria": {
            "0": "No active NMC registration",
            "1": "Registration pending or issues identified",
            "2": "Active NMC registration provided",
            "3": "Active NMC registration with no restrictions and clear revalidation record"
        },
        "expected_answer_notes": "Must provide NMC PIN for verification on NMC register. Check for any restrictions or conditions.",
        "required": True,
        "order": 14,
        "max_score": 3,
        "is_critical": True
    }
]

# ============================================================================
# OSABEA INTERVIEW SCORING CONFIGURATION (0-3 Scale)
# Based on Osabea Interview Questions template
# ============================================================================

INTERVIEW_SCORING = {
    "scale": {
        "min": 0,
        "max": 3,
        "labels": {
            0: "Does not meet criteria",
            1: "Part meets criteria",
            2: "Meets criteria",
            3: "Exceeds criteria"
        }
    },
    "pass_threshold": 2,  # Minimum average score to pass individual question
    "minimum_total_score": 11,  # Out of 24 for Support Worker (8 questions x 3)
    "overall_pass_percentage": 46,  # 11/24 = 46%
    "critical_questions": ["nurse_q3", "nurse_q4", "nurse_q6"],  # Must score 2+ on these for nurses
}

# Part 2 - General Administrative Questions (Yes/No or Free text)
ADMINISTRATIVE_QUESTIONS = [
    {"id": "admin_q1", "question": "Do you require a Work Permit?", "type": "yes_no"},
    {"id": "admin_q2", "question": "What proof of candidate's eligibility to work in the UK was taken?", "type": "text"},
    {"id": "admin_q3", "question": "How many hours do you want to work?", "type": "text"},
    {"id": "admin_q4", "question": "Are you able to participate in flexible working?", "type": "yes_no"},
    {"id": "admin_q5", "question": "Do you have a full and valid driver's licence?", "type": "yes_no"},
    {"id": "admin_q6", "question": "Have you any annual leave booked?", "type": "text"},
    {"id": "admin_q7", "question": "If successful, what notice period would you need to give to your current employer?", "type": "text"},
    {"id": "admin_q8", "question": "When would you be able to start?", "type": "date"},
]

# Pre-Employment Checks to discuss at interview
PRE_EMPLOYMENT_CHECKS_NOTES = [
    "Explore sickness information on application form",
    "Check employee references cover past 2 years and all gaps accounted for",
    "Check completion of Rehabilitation Offenders Act section and confirm understanding",
    "Inform candidate of outcome notification timing",
    "Take copy of applicant's proof of eligibility to work in UK",
    "Inform of DBS Check requirement before employment confirmed"
]

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_interview_questions_for_role(role: str) -> list:
    """
    Get the appropriate interview questions for a role.
    
    Args:
        role: Employee role (support_worker, nurse, etc.)
    
    Returns:
        List of interview questions (8 for Support Workers, 14 for Nurses)
    """
    role_lower = role.lower().strip() if role else ""
    
    # Map role variations
    role_mapping = {
        "hca": "support_worker",
        "healthcare assistant": "support_worker",
        "health care assistant": "support_worker",
        "carer": "support_worker",
        "care assistant": "support_worker",
        "senior carer": "support_worker",
        "senior care assistant": "support_worker",
        "support worker": "support_worker",
        "care worker": "support_worker",
        "live-in carer": "support_worker",
        "night carer": "support_worker",
        "team leader": "support_worker",
        "care coordinator": "support_worker",
        "registered nurse": "nurse",
        "nurse (registered)": "nurse",
        "senior nurse": "nurse",
        "rn": "nurse",
        "rgn": "nurse",
        "nurse": "nurse"
    }
    
    normalized_role = role_mapping.get(role_lower, "support_worker")
    
    if normalized_role == "nurse":
        # Nurses get Support Worker questions + clinical questions (14 total)
        return SUPPORT_WORKER_INTERVIEW_QUESTIONS + NURSE_CLINICAL_QUESTIONS
    else:
        # All other roles get Support Worker questions (8 total)
        return SUPPORT_WORKER_INTERVIEW_QUESTIONS


def get_administrative_questions() -> list:
    """Get Part 2 administrative questions."""
    return ADMINISTRATIVE_QUESTIONS


def get_pre_employment_check_notes() -> list:
    """Get pre-employment checks to discuss at interview."""
    return PRE_EMPLOYMENT_CHECKS_NOTES


def get_interview_question_count(role: str) -> dict:
    """
    Get the question count for a role.
    
    Returns:
        Dict with total, required, optional, and max_score
    """
    questions = get_interview_questions_for_role(role)
    
    required = sum(1 for q in questions if q.get("required", True))
    optional = sum(1 for q in questions if not q.get("required", True))
    max_score = sum(q.get("max_score", 3) for q in questions)
    
    return {
        "total": len(questions),
        "required": required,
        "optional": optional,
        "max_score": max_score,
        "pass_score": INTERVIEW_SCORING["minimum_total_score"] if "nurse" not in role.lower() else int(max_score * 0.46)
    }


def calculate_interview_result(scores: dict, role: str) -> dict:
    """
    Calculate interview result based on scores.
    
    Args:
        scores: Dict mapping question_id to score (0-3)
        role: Employee role
        
    Returns:
        Dict with total_score, max_score, percentage, passed, critical_passed
    """
    questions = get_interview_questions_for_role(role)
    
    total_score = 0
    max_score = 0
    critical_passed = True
    
    for q in questions:
        q_id = q["id"]
        score = scores.get(q_id, 0)
        max_q_score = q.get("max_score", 3)
        
        total_score += min(score, max_q_score)  # Cap at max
        max_score += max_q_score
        
        # Check critical questions (must score 2+)
        if q.get("is_critical") and score < 2:
            critical_passed = False
    
    percentage = round((total_score / max_score) * 100) if max_score > 0 else 0
    pass_score = INTERVIEW_SCORING["minimum_total_score"]
    
    return {
        "total_score": total_score,
        "max_score": max_score,
        "percentage": percentage,
        "passed": total_score >= pass_score and critical_passed,
        "critical_passed": critical_passed,
        "pass_threshold": pass_score,
        "recommendation": "Proceed to Offer" if total_score >= pass_score and critical_passed else "Further Review Required"
    }


def get_role_interview_config(role: str) -> dict:
    """
    Get complete interview configuration for a role.
    
    Returns:
        Full config including questions, scoring, admin questions, and metadata
    """
    questions = get_interview_questions_for_role(role)
    counts = get_interview_question_count(role)
    
    role_lower = role.lower().strip() if role else ""
    is_nurse = "nurse" in role_lower
    
    return {
        "role": role,
        "is_nurse_role": is_nurse,
        "questions": questions,
        "administrative_questions": ADMINISTRATIVE_QUESTIONS,
        "pre_employment_checks": PRE_EMPLOYMENT_CHECKS_NOTES,
        "question_counts": counts,
        "scoring": INTERVIEW_SCORING,
        "max_possible_score": counts["max_score"],
        "pass_threshold_score": counts["pass_score"],
        "question_count": 8 if not is_nurse else 14,
        "scale_description": "0 = Does not meet, 1 = Part meets, 2 = Meets, 3 = Exceeds"
    }


# ============================================================================
# ROLE REQUIREMENTS SUMMARY (For Display)
# ============================================================================

ROLE_REQUIREMENTS_SUMMARY = {
    "support_worker": {
        "display_name": "Support Worker / Care Worker",
        "professional_registration": None,
        "mandatory_training_count": 8,
        "mandatory_training": [
            "Safeguarding Adults",
            "Manual Handling / Moving & Handling",
            "Fire Safety",
            "Health & Safety",
            "Basic Life Support (BLS)",
            "Infection Prevention & Control",
            "Information Governance / GDPR",
            "Prevent Training"
        ],
        "interview_questions": 8,
        "interview_pass_score": 11,
        "interview_max_score": 24,
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
    "healthcare_assistant": {
        "display_name": "Healthcare Assistant (HCA)",
        "professional_registration": None,
        "mandatory_training_count": 8,
        "mandatory_training": [
            "Safeguarding Adults",
            "Manual Handling / Moving & Handling",
            "Fire Safety",
            "Health & Safety",
            "Basic Life Support (BLS)",
            "Infection Prevention & Control",
            "Information Governance / GDPR",
            "Prevent Training"
        ],
        "interview_questions": 8,
        "interview_pass_score": 11,
        "interview_max_score": 24,
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
        "mandatory_training_count": 8,
        "mandatory_training": [
            "Safeguarding Adults",
            "Manual Handling / Moving & Handling",
            "Fire Safety",
            "Health & Safety",
            "Basic Life Support (BLS)",
            "Infection Prevention & Control",
            "Information Governance / GDPR",
            "Prevent Training"
        ],
        "additional_competencies": [
            "Clinical Competency",
            "Medication Competency"
        ],
        "interview_questions": 14,
        "interview_pass_score": 19,
        "interview_max_score": 42,
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
    elif "support" in role_lower or "care worker" in role_lower:
        return ROLE_REQUIREMENTS_SUMMARY["support_worker"]
    else:
        return ROLE_REQUIREMENTS_SUMMARY["healthcare_assistant"]


# Export all for use in server.py
__all__ = [
    "SUPPORT_WORKER_INTERVIEW_QUESTIONS",
    "HCA_INTERVIEW_QUESTIONS",
    "NURSE_CLINICAL_QUESTIONS",
    "INTERVIEW_SCORING",
    "ADMINISTRATIVE_QUESTIONS",
    "PRE_EMPLOYMENT_CHECKS_NOTES",
    "ROLE_REQUIREMENTS_SUMMARY",
    "get_interview_questions_for_role",
    "get_administrative_questions",
    "get_pre_employment_check_notes",
    "get_interview_question_count",
    "calculate_interview_result",
    "get_role_interview_config",
    "get_role_requirements",
]
