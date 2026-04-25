"""
Care Certificate Configuration Layer.

Single source of truth for all 15 Care Certificate standard definitions:
- completion_type: automatic | hybrid | manual
- worker_input_required: whether a worker form must be submitted
- admin_signoff_required: whether admin must explicitly sign off
- auto_complete_allowed: whether evidence alone can complete without admin
- role_variants: role-aware prompt/example overrides (wording only; standards are the same)
- worker_form_id: ID of the worker induction form (hybrid items only)
- evidence_sources: what satisfies this item
- status_rules: ordered conditions that determine status
"""

from typing import Optional

# ─────────────────────────────────────────────────────
# ROLE VARIANT PROMPTS
# Wording overrides per role — standard list does NOT change.
# ─────────────────────────────────────────────────────
_ROLE_PROMPTS = {
    "understand_your_role": {
        "healthcare_assistant": {
            "prompt": "Describe your responsibilities as a Healthcare Assistant and who you report to.",
            "examples": "Assisting with personal care, supporting nursing staff, escalating to senior nurse.",
        },
        "support_worker": {
            "prompt": "Describe your responsibilities as a Support Worker and who you report to.",
            "examples": "Daily living support, community activities, escalating to team leader.",
        },
        "care_assistant": {
            "prompt": "Describe your responsibilities as a Care Assistant and who you supervise you.",
            "examples": "Personal care, meal assistance, reporting changes in wellbeing to senior carer.",
        },
        "_default": {
            "prompt": "Describe your main job responsibilities and who you report to if you have a concern.",
            "examples": "What tasks you will do day-to-day and which manager or senior you escalate to.",
        },
    },
    "personal_development": {
        "_default": {
            "prompt": "Describe how you plan to develop in your role and what support you expect.",
            "examples": "Supervision schedule, training you hope to complete, development goals you discussed at induction.",
        },
    },
    "duty_of_care": {
        "nurse": {
            "prompt": "Explain what duty of care means for a registered nurse in your setting.",
            "examples": "Patient safety, acting within your scope of practice, escalating concerns to the responsible clinician.",
        },
        "_default": {
            "prompt": "Explain what duty of care means in your role and describe a situation where you would need to raise a concern.",
            "examples": "A service user refusing care, a colleague acting unsafely, a near-miss incident you would report.",
        },
    },
    "equality_diversity": {
        "_default": {
            "prompt": "Describe how you will promote equality, diversity, dignity, and inclusion in your day-to-day work.",
            "examples": "Respecting protected characteristics, challenging exclusion, making reasonable adjustments, and reporting discriminatory behaviour.",
        },
    },
    "work_person_centred": {
        "_default": {
            "prompt": "Describe how you would support someone in a way that respects their individual preferences and choices.",
            "examples": "Asking before providing care, checking care plan preferences, supporting decision-making.",
        },
    },
    "communication": {
        "nurse": {
            "prompt": "Describe how you communicate effectively with patients, families, and the wider clinical team.",
            "examples": "Handover, escalation to doctor, documenting observations, breaking difficult news.",
        },
        "_default": {
            "prompt": "Describe how you communicate clearly with service users, families, and your team.",
            "examples": "Speaking clearly, listening actively, written notes/records, using interpreters.",
        },
    },
    "privacy_dignity": {
        "_default": {
            "prompt": "Give an example of how you would protect a service user's privacy and dignity during personal care.",
            "examples": "Closing doors, using screens, knocking before entering, explaining what you are doing.",
        },
    },
}

def get_role_prompt(item_code: str, role_normalized: str) -> dict:
    """Return role-aware prompt/examples for a hybrid induction item."""
    item_variants = _ROLE_PROMPTS.get(item_code, {})
    return item_variants.get(role_normalized) or item_variants.get("_default") or {}


# ─────────────────────────────────────────────────────
# CARE CERTIFICATE CONFIGURATION (15 STANDARDS)
# ─────────────────────────────────────────────────────
HYBRID_LEARNING_CONTENT = {
    "understand_your_role": {
        "overview": "This standard confirms you understand your role, your limits, and who to ask for help.",
        "expected_to_know": [
            "Your day-to-day responsibilities.",
            "What is outside your role or training.",
            "Who you report concerns to.",
        ],
        "guidance": [
            "Work within your job description, training, and local policies.",
            "Ask a senior member of staff before doing tasks you have not been trained for.",
            "Record and escalate concerns promptly.",
        ],
        "dos": ["Do ask for supervision when unsure.", "Do report unsafe practice."],
        "donts": ["Do not perform clinical tasks outside your competence.", "Do not ignore concerns."],
    },
    "equality_diversity": {
        "overview": "This standard confirms you understand equality, diversity, inclusion, human rights, and respectful care in your role.",
        "expected_to_know": [
            "What discrimination, harassment, and exclusion can look like in care settings.",
            "How to respect protected characteristics, beliefs, identity, and individual preferences.",
            "How to challenge poor practice and escalate concerns appropriately.",
        ],
        "guidance": [
            "Treat each person as an individual and avoid assumptions about their needs or choices.",
            "Make reasonable adjustments and use communication support where needed.",
            "Raise concerns promptly if you witness discriminatory language, behaviour, or decisions.",
        ],
        "dos": ["Do respect identity, culture, faith, and personal choices.", "Do report discriminatory behaviour or barriers to inclusion."],
        "donts": ["Do not make assumptions based on age, disability, ethnicity, gender, religion, or sexuality.", "Do not ignore exclusionary or degrading behaviour."],
    },
    "personal_development": {
        "overview": "This standard confirms you understand supervision, learning, and development in your role.",
        "expected_to_know": [
            "How supervision and appraisal work.",
            "What training you need for your role.",
            "How to ask for support with learning needs.",
        ],
        "guidance": [
            "Use supervision to discuss confidence, training, and support needs.",
            "Keep your training current and tell your manager if a certificate is due to expire.",
            "Reflect on feedback and agree practical development goals.",
        ],
        "dos": ["Do keep evidence of completed training.", "Do raise learning support needs early."],
        "donts": ["Do not wait until training expires before asking for help.", "Do not work beyond your competence."],
    },
    "duty_of_care": {
        "overview": "This standard confirms you understand your duty to act safely and in the person's best interests.",
        "expected_to_know": [
            "What duty of care means in practice.",
            "How to handle dilemmas and refusals of care.",
            "How to report incidents, near misses, and concerns.",
        ],
        "guidance": [
            "Balance choice with safety and follow care plans, risk assessments, and escalation routes.",
            "If someone refuses care, stay calm, respect their rights, and report concerns according to policy.",
            "Document facts clearly and promptly.",
        ],
        "dos": ["Do escalate risks or safeguarding concerns.", "Do record what happened factually."],
        "donts": ["Do not force care unless there is a lawful emergency reason.", "Do not hide mistakes or near misses."],
    },
    "work_person_centred": {
        "overview": "This standard confirms you can support people in a way that respects their choices and needs.",
        "expected_to_know": [
            "How to find out a person's preferences.",
            "How consent and choice affect daily care.",
            "How to use care plans to support individual needs.",
        ],
        "guidance": [
            "Read the care plan and ask the person how they prefer to be supported.",
            "Offer choices wherever possible and involve family or advocates when appropriate.",
            "Report changes in needs or preferences so records stay accurate.",
        ],
        "dos": ["Do ask before providing support.", "Do respect preferences and routines."],
        "donts": ["Do not assume everyone wants care delivered the same way.", "Do not ignore changes in needs."],
    },
    "communication": {
        "overview": "This standard confirms you can communicate clearly, respectfully, and safely.",
        "expected_to_know": [
            "How to communicate with people you support, families, and colleagues.",
            "How to document care and concerns.",
            "How to protect confidential information.",
        ],
        "guidance": [
            "Use clear language, active listening, and communication aids where needed.",
            "Share information only with people who need it for care or safeguarding.",
            "Write records that are factual, timely, and respectful.",
        ],
        "dos": ["Do check understanding.", "Do record important information promptly."],
        "donts": ["Do not discuss private information in public areas.", "Do not leave unclear handovers."],
    },
    "privacy_dignity": {
        "overview": "This standard confirms you understand how to protect privacy, dignity, and respect.",
        "expected_to_know": [
            "How to maintain dignity during personal care.",
            "How consent applies before care tasks.",
            "How to protect private information and personal space.",
        ],
        "guidance": [
            "Knock, explain what you are doing, and ask for consent before care.",
            "Use curtains, doors, towels, or screens to protect privacy.",
            "Speak respectfully and avoid exposing or embarrassing the person.",
        ],
        "dos": ["Do explain care before starting.", "Do protect privacy during personal care."],
        "donts": ["Do not rush intimate care without consent.", "Do not talk over the person."],
    },
    "fluids_nutrition": {
        "overview": "This standard confirms you understand nutrition, hydration, and safe support with food and fluids.",
        "expected_to_know": [
            "Why hydration and nutrition matter for health and wellbeing.",
            "How to follow care plans, diet guidance, and swallowing-risk instructions.",
            "When to report concerns about eating, drinking, or weight changes.",
        ],
        "guidance": [
            "Offer food and drinks in line with the person's care plan, preferences, and risk assessment.",
            "Record intake where required and report poor appetite, choking concerns, dehydration, or sudden change.",
            "Follow food hygiene practice and ask for guidance if specialist diets or swallowing risks apply.",
        ],
        "dos": ["Do follow care plans and diet instructions.", "Do report poor intake or choking concerns promptly."],
        "donts": ["Do not ignore swallowing-risk instructions.", "Do not force food or fluids."],
    },
    "awareness_mental_health": {
        "overview": "This standard confirms you understand basic awareness of mental health, dementia, and learning disabilities.",
        "expected_to_know": [
            "How mental health, dementia, and learning disabilities may affect communication and support needs.",
            "Why person-centred support and reasonable adjustments matter.",
            "When to report changes, distress, or safeguarding concerns.",
        ],
        "guidance": [
            "Treat each person as an individual and use their care plan, communication needs, and preferences.",
            "Look for changes in mood, confusion, distress, or behaviour and report concerns.",
            "Support dignity, inclusion, and choice without making assumptions.",
        ],
        "dos": ["Do use person-centred support.", "Do report changes or distress."],
        "donts": ["Do not dismiss behaviour as difficult without looking for causes.", "Do not make assumptions about capacity or ability."],
    },
}


def get_learning_content_for_item(code: str) -> dict:
    """Return worker-facing teaching content for a hybrid induction item."""
    return HYBRID_LEARNING_CONTENT.get(code, {})


CARE_CERTIFICATE_CONFIG = [
    {
        "code": "understand_your_role",
        "standard_number": 1,
        "title": "Understand Your Role",
        "completion_type": "hybrid",
        "worker_input_required": True,
        "admin_signoff_required": True,
        "auto_complete_allowed": False,
        "worker_form_id": "cc_understand_your_role",
        "evidence_sources": ["worker_submission", "manager_signoff"],
        "status_rules": [
            {"condition": "admin_signed_off", "status": "completed"},
            {"condition": "worker_submitted", "status": "awaiting_signoff"},
            {"condition": "worker_returned", "status": "returned"},
            {"condition": "worker_draft", "status": "in_progress"},
            {"condition": "none", "status": "awaiting_worker"},
        ],
        "description": (
            "The worker understands their duties, working boundaries, supervision route, "
            "and what to do when something goes wrong."
        ),
    },
    {
        "code": "personal_development",
        "standard_number": 2,
        "title": "Your Personal Development",
        "completion_type": "hybrid",
        "worker_input_required": True,
        "admin_signoff_required": True,
        "auto_complete_allowed": False,
        "worker_form_id": "cc_personal_development",
        "evidence_sources": ["worker_submission", "manager_signoff"],
        "status_rules": [
            {"condition": "admin_signed_off", "status": "completed"},
            {"condition": "worker_submitted", "status": "awaiting_signoff"},
            {"condition": "worker_returned", "status": "returned"},
            {"condition": "worker_draft", "status": "in_progress"},
            {"condition": "none", "status": "awaiting_worker"},
        ],
        "description": (
            "The worker understands supervision, appraisal, CPD expectations, "
            "and how to plan their own development."
        ),
    },
    {
        "code": "duty_of_care",
        "standard_number": 3,
        "title": "Duty of Care",
        "completion_type": "hybrid",
        "worker_input_required": True,
        "admin_signoff_required": True,
        "auto_complete_allowed": False,
        "worker_form_id": "cc_duty_of_care",
        "evidence_sources": ["worker_submission", "manager_signoff"],
        "status_rules": [
            {"condition": "admin_signed_off", "status": "completed"},
            {"condition": "worker_submitted", "status": "awaiting_signoff"},
            {"condition": "worker_returned", "status": "returned"},
            {"condition": "worker_draft", "status": "in_progress"},
            {"condition": "none", "status": "awaiting_worker"},
        ],
        "description": (
            "The worker understands their duty of care, what dilemmas may arise, "
            "and how to raise concerns and escalate."
        ),
    },
    {
        "code": "equality_diversity",
        "standard_number": 4,
        "title": "Equality and Diversity",
        "completion_type": "hybrid",
        "worker_input_required": True,
        "admin_signoff_required": True,
        "auto_complete_allowed": False,
        "worker_form_id": "cc_equality_diversity",
        "evidence_sources": ["worker_submission", "manager_signoff"],
        "status_rules": [
            {"condition": "admin_signed_off", "status": "completed"},
            {"condition": "worker_submitted", "status": "awaiting_signoff"},
            {"condition": "worker_returned", "status": "returned"},
            {"condition": "worker_draft", "status": "in_progress"},
            {"condition": "none", "status": "awaiting_worker"},
        ],
        "description": (
            "The worker confirms their understanding of equality, diversity, inclusion, and human rights, "
            "then a manager reviews and signs off the standard."
        ),
    },
    {
        "code": "work_person_centred",
        "standard_number": 5,
        "title": "Work in a Person-Centred Way",
        "completion_type": "hybrid",
        "worker_input_required": True,
        "admin_signoff_required": True,
        "auto_complete_allowed": False,
        "worker_form_id": "cc_person_centred_care",
        "evidence_sources": ["worker_submission", "manager_signoff"],
        "status_rules": [
            {"condition": "admin_signed_off", "status": "completed"},
            {"condition": "worker_submitted", "status": "awaiting_signoff"},
            {"condition": "worker_returned", "status": "returned"},
            {"condition": "worker_draft", "status": "in_progress"},
            {"condition": "none", "status": "awaiting_worker"},
        ],
        "description": (
            "The worker understands person-centred care, individual preferences, consent, "
            "and working in partnership with service users."
        ),
    },
    {
        "code": "communication",
        "standard_number": 6,
        "title": "Communication",
        "completion_type": "hybrid",
        "worker_input_required": True,
        "admin_signoff_required": True,
        "auto_complete_allowed": False,
        "worker_form_id": "cc_communication",
        "evidence_sources": ["worker_submission", "manager_signoff"],
        "status_rules": [
            {"condition": "admin_signed_off", "status": "completed"},
            {"condition": "worker_submitted", "status": "awaiting_signoff"},
            {"condition": "worker_returned", "status": "returned"},
            {"condition": "worker_draft", "status": "in_progress"},
            {"condition": "none", "status": "awaiting_worker"},
        ],
        "description": (
            "The worker communicates effectively with service users, families, and the team "
            "including in writing, verbally, and in difficult situations."
        ),
    },
    {
        "code": "privacy_dignity",
        "standard_number": 7,
        "title": "Privacy and Dignity",
        "completion_type": "hybrid",
        "worker_input_required": True,
        "admin_signoff_required": True,
        "auto_complete_allowed": False,
        "worker_form_id": "cc_privacy_and_dignity",
        "evidence_sources": ["worker_submission", "manager_signoff"],
        "status_rules": [
            {"condition": "admin_signed_off", "status": "completed"},
            {"condition": "worker_submitted", "status": "awaiting_signoff"},
            {"condition": "worker_returned", "status": "returned"},
            {"condition": "worker_draft", "status": "in_progress"},
            {"condition": "none", "status": "awaiting_worker"},
        ],
        "description": (
            "The worker understands privacy, dignity, consent, and respect in all interactions."
        ),
    },
    {
        "code": "fluids_nutrition",
        "standard_number": 8,
        "title": "Fluids and Nutrition",
        "completion_type": "hybrid",
        "worker_input_required": True,
        "admin_signoff_required": True,
        "auto_complete_allowed": False,
        "worker_form_id": "cc_fluids_nutrition",
        "evidence_sources": ["verified_training_record", "worker_submission", "manager_signoff"],
        "status_rules": [
            {"condition": "has_verified_training", "status": "completed"},
            {"condition": "admin_signed_off", "status": "completed"},
            {"condition": "worker_submitted", "status": "awaiting_signoff"},
            {"condition": "worker_returned", "status": "returned"},
            {"condition": "worker_draft", "status": "in_progress"},
            {"condition": "none", "status": "awaiting_worker"},
        ],
        "description": (
            "Verified food hygiene or nutrition training auto-completes this standard. "
            "Where no training evidence exists, worker submission and manager sign-off are required."
        ),
    },
    {
        "code": "awareness_mental_health",
        "standard_number": 9,
        "title": "Awareness of Mental Health, Dementia and Learning Disabilities",
        "completion_type": "hybrid",
        "worker_input_required": True,
        "admin_signoff_required": True,
        "auto_complete_allowed": False,
        "worker_form_id": "cc_awareness_mental_health",
        "evidence_sources": ["verified_training_record", "worker_submission", "manager_signoff"],
        "status_rules": [
            {"condition": "has_verified_training", "status": "completed"},
            {"condition": "admin_signed_off", "status": "completed"},
            {"condition": "worker_submitted", "status": "awaiting_signoff"},
            {"condition": "worker_returned", "status": "returned"},
            {"condition": "worker_draft", "status": "in_progress"},
            {"condition": "none", "status": "awaiting_worker"},
        ],
        "description": (
            "Verified mental health, dementia, or learning disability training auto-completes this standard. "
            "Where no training evidence exists, worker submission and manager sign-off are required."
        ),
    },
    {
        "code": "safeguarding_adults",
        "standard_number": 10,
        "title": "Safeguarding Adults",
        "completion_type": "automatic",
        "worker_input_required": False,
        "admin_signoff_required": False,
        "auto_complete_allowed": True,
        "worker_form_id": None,
        "evidence_sources": ["verified_training_record"],
        "status_rules": [
            {"condition": "has_verified_training", "status": "completed"},
            {"condition": "none", "status": "pending_evidence"},
        ],
        "description": (
            "Verified safeguarding adults training confirms this standard."
        ),
    },
    {
        "code": "basic_life_support",
        "standard_number": 11,
        "title": "Basic Life Support",
        "completion_type": "automatic",
        "worker_input_required": False,
        "admin_signoff_required": False,
        "auto_complete_allowed": True,
        "worker_form_id": None,
        "evidence_sources": ["verified_training_record"],
        "status_rules": [
            {"condition": "has_verified_training", "status": "completed"},
            {"condition": "none", "status": "pending_evidence"},
        ],
        "description": (
            "Verified basic life support or resuscitation training confirms this standard."
        ),
    },
    {
        "code": "health_safety",
        "standard_number": 12,
        "title": "Health and Safety",
        "completion_type": "automatic",
        "worker_input_required": False,
        "admin_signoff_required": False,
        "auto_complete_allowed": True,
        "worker_form_id": None,
        "evidence_sources": ["verified_training_record"],
        "status_rules": [
            {"condition": "has_verified_training", "status": "completed"},
            {"condition": "none", "status": "pending_evidence"},
        ],
        "description": (
            "Verified health and safety training confirms this standard."
        ),
    },
    {
        "code": "handling_information",
        "standard_number": 13,
        "title": "Handling Information",
        "completion_type": "automatic",
        "worker_input_required": False,
        "admin_signoff_required": False,
        "auto_complete_allowed": True,
        "worker_form_id": None,
        "evidence_sources": ["verified_training_record"],
        "status_rules": [
            {"condition": "has_verified_training", "status": "completed"},
            {"condition": "none", "status": "pending_evidence"},
        ],
        "description": (
            "Verified information governance, GDPR, or data protection training confirms this standard."
        ),
    },
    {
        "code": "infection_control",
        "standard_number": 14,
        "title": "Infection Prevention and Control",
        "completion_type": "automatic",
        "worker_input_required": False,
        "admin_signoff_required": False,
        "auto_complete_allowed": True,
        "worker_form_id": None,
        "evidence_sources": ["verified_training_record"],
        "status_rules": [
            {"condition": "has_verified_training", "status": "completed"},
            {"condition": "none", "status": "pending_evidence"},
        ],
        "description": (
            "Verified infection prevention and control training confirms this standard."
        ),
    },
    {
        "code": "shadow_shift",
        "standard_number": 15,
        "title": "Shadow Shift Completed",
        "completion_type": "manual",
        "worker_input_required": False,
        "admin_signoff_required": True,
        "auto_complete_allowed": False,
        "worker_form_id": None,
        "evidence_sources": ["manager_signoff", "witness_note"],
        "status_rules": [
            {"condition": "admin_signed_off", "status": "completed"},
            {"condition": "none", "status": "awaiting_manager"},
        ],
        "description": (
            "A supervisor or witness note confirming supervised shadowing was completed "
            "before unsupervised work commenced."
        ),
    },
]

# ─────────────────────────────────────────────────────
# LOOKUP HELPERS
# ─────────────────────────────────────────────────────
_CONFIG_BY_CODE = {c["code"]: c for c in CARE_CERTIFICATE_CONFIG}
_CONFIG_BY_STANDARD_NUM = {c["standard_number"]: c for c in CARE_CERTIFICATE_CONFIG}

HYBRID_FORM_IDS = {
    c["worker_form_id"]
    for c in CARE_CERTIFICATE_CONFIG
    if c["worker_form_id"] is not None
}

HYBRID_ITEM_CODES = {
    c["code"]
    for c in CARE_CERTIFICATE_CONFIG
    if c["completion_type"] == "hybrid"
}

AUTOMATIC_ITEM_CODES = {
    c["code"]
    for c in CARE_CERTIFICATE_CONFIG
    if c["completion_type"] == "automatic"
}

MANUAL_ITEM_CODES = {
    c["code"]
    for c in CARE_CERTIFICATE_CONFIG
    if c["completion_type"] == "manual"
}

def get_config_for_item(code: str) -> Optional[dict]:
    return _CONFIG_BY_CODE.get(code)

def get_config_for_standard(standard_number: int) -> Optional[dict]:
    return _CONFIG_BY_STANDARD_NUM.get(standard_number)

def get_all_hybrid_forms() -> list:
    """Return list of {form_id, code, title} for all hybrid items that need worker forms."""
    return [
        {
            "form_id": c["worker_form_id"],
            "code": c["code"],
            "standard_number": c["standard_number"],
            "title": c["title"],
        }
        for c in CARE_CERTIFICATE_CONFIG
        if c["worker_form_id"] is not None
    ]


def resolve_item_status(
    code: str,
    admin_signed_off: bool,
    worker_submitted: bool,
    worker_returned: bool,
    worker_has_draft: bool,
    has_verified_training: bool,
) -> str:
    """
    Evaluate status for a single induction item based on the config's status_rules.

    Returns one of:
        completed | awaiting_signoff | returned | in_progress |
        awaiting_worker | pending_evidence | awaiting_manager
    """
    cfg = _CONFIG_BY_CODE.get(code, {})
    for rule in cfg.get("status_rules", []):
        condition = rule["condition"]
        if condition == "admin_signed_off" and admin_signed_off:
            return rule["status"]
        if condition == "has_verified_training" and has_verified_training:
            return rule["status"]
        if condition == "worker_submitted" and worker_submitted and not worker_returned:
            return rule["status"]
        if condition == "worker_returned" and worker_returned:
            return rule["status"]
        if condition == "worker_draft" and worker_has_draft:
            return rule["status"]
        if condition == "none":
            return rule["status"]
    return "pending"
