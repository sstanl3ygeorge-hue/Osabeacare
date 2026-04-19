"""
Care Certificate hybrid worker form schemas.

One short structured form per hybrid induction standard (standards 1, 2, 3, 5, 6, 7).
Each form has:
  - form_id matching care_certificate_config.worker_form_id
  - standard_code mapping back to the care certificate item
  - fields: list of structured question fields with role-aware support
  - max_words per text field (enforced client-side, warned server-side)

Completion type choices, checkboxes, and short-text fields only.
No essay / free-write forms.
"""

from care_certificate_config import get_role_prompt

# ─────────────────────────────────────────────────────
# FIELD TYPES
# text       — short text (max_words enforced)
# textarea   — paragraph (max_words enforced)
# radio      — single choice
# checkboxes — multiple choice
# ─────────────────────────────────────────────────────

CC_WORKER_FORMS = {

    # ── Standard 1: Understand Your Role ─────────────────────────────────────
    "cc_understand_your_role": {
        "form_id": "cc_understand_your_role",
        "standard_code": "understand_your_role",
        "standard_number": 1,
        "title": "Understand Your Role",
        "description": (
            "Answer the questions below to confirm you understand your role, "
            "your responsibilities, and what to do if you have a concern."
        ),
        "fields": [
            {
                "key": "main_responsibilities",
                "label": "Describe your main job responsibilities.",
                "hint": "Include the tasks you will do day-to-day.",
                "type": "textarea",
                "required": True,
                "max_words": 80,
                "role_prompt_key": "understand_your_role",
            },
            {
                "key": "reporting_line",
                "label": "Who do you report to if you have a concern at work?",
                "hint": "Name the role or person you would go to first.",
                "type": "text",
                "required": True,
                "max_words": 30,
            },
            {
                "key": "scope_of_practice",
                "label": "Name one task that is outside your scope of practice and explain why.",
                "hint": "Think about tasks that require a qualified or senior member of staff.",
                "type": "textarea",
                "required": True,
                "max_words": 60,
            },
            {
                "key": "supervision_frequency",
                "label": "How often will you receive supervision?",
                "type": "radio",
                "required": True,
                "options": [
                    {"value": "weekly", "label": "Weekly"},
                    {"value": "fortnightly", "label": "Fortnightly"},
                    {"value": "monthly", "label": "Monthly"},
                    {"value": "other", "label": "Other (describe below)"},
                ],
            },
            {
                "key": "supervision_notes",
                "label": "Any other notes about your supervision arrangement (optional).",
                "type": "text",
                "required": False,
                "max_words": 40,
            },
        ],
    },

    # ── Standard 2: Personal Development ─────────────────────────────────────
    "cc_personal_development": {
        "form_id": "cc_personal_development",
        "standard_code": "personal_development",
        "standard_number": 2,
        "title": "Your Personal Development",
        "description": (
            "Answer the questions below to confirm you understand how your development "
            "will be supported in this role."
        ),
        "fields": [
            {
                "key": "development_plan",
                "label": "Describe how you plan to develop in your role over the next 6 months.",
                "hint": "Include any training, skills, or knowledge you want to improve.",
                "type": "textarea",
                "required": True,
                "max_words": 80,
                "role_prompt_key": "personal_development",
            },
            {
                "key": "appraisal_understood",
                "label": "Do you understand the appraisal process for your role?",
                "type": "radio",
                "required": True,
                "options": [
                    {"value": "yes", "label": "Yes"},
                    {"value": "no", "label": "No — I need more information"},
                    {"value": "partly", "label": "Partly — I have some questions"},
                ],
            },
            {
                "key": "training_agreed",
                "label": "List any training courses you agreed at induction (if any).",
                "hint": "Leave blank if no courses were agreed yet.",
                "type": "text",
                "required": False,
                "max_words": 50,
            },
            {
                "key": "support_needed",
                "label": "Do you have any specific learning support needs your manager should know about?",
                "type": "radio",
                "required": True,
                "options": [
                    {"value": "no", "label": "No"},
                    {"value": "yes", "label": "Yes (describe below)"},
                ],
            },
            {
                "key": "support_details",
                "label": "Describe any support needs (if applicable).",
                "type": "text",
                "required": False,
                "max_words": 60,
            },
        ],
    },

    # ── Standard 3: Duty of Care ──────────────────────────────────────────────
    "cc_duty_of_care": {
        "form_id": "cc_duty_of_care",
        "standard_code": "duty_of_care",
        "standard_number": 3,
        "title": "Duty of Care",
        "description": (
            "Answer the questions below to confirm you understand your duty of care "
            "and how to respond when things go wrong."
        ),
        "fields": [
            {
                "key": "duty_definition",
                "label": "In your own words, explain what 'duty of care' means in your role.",
                "type": "textarea",
                "required": True,
                "max_words": 80,
                "role_prompt_key": "duty_of_care",
            },
            {
                "key": "dilemma_scenario",
                "label": (
                    "Describe a situation where your duty of care might conflict with "
                    "a service user's wishes. What would you do?"
                ),
                "hint": "For example, a service user refusing care or wanting to do something risky.",
                "type": "textarea",
                "required": True,
                "max_words": 100,
            },
            {
                "key": "escalation_steps",
                "label": "What are the first three steps you would take when raising a concern?",
                "hint": "Think about who you tell, what you document, and what happens next.",
                "type": "textarea",
                "required": True,
                "max_words": 80,
            },
            {
                "key": "incident_reporting",
                "label": "Have you been shown how to complete an incident report?",
                "type": "radio",
                "required": True,
                "options": [
                    {"value": "yes", "label": "Yes"},
                    {"value": "no", "label": "No — I need to be shown"},
                ],
            },
        ],
    },

    # ── Standard 5: Work in a Person-Centred Way ──────────────────────────────
    "cc_person_centred_care": {
        "form_id": "cc_person_centred_care",
        "standard_code": "work_person_centred",
        "standard_number": 5,
        "title": "Work in a Person-Centred Way",
        "description": (
            "Answer the questions below to confirm you understand person-centred care "
            "and how to apply it in your role."
        ),
        "fields": [
            {
                "key": "person_centred_definition",
                "label": "What does person-centred care mean to you?",
                "type": "textarea",
                "required": True,
                "max_words": 80,
                "role_prompt_key": "work_person_centred",
            },
            {
                "key": "preference_example",
                "label": "Give one example of how you would find out a service user's preferences.",
                "hint": "For example, reading their care plan, asking them directly, or involving family.",
                "type": "textarea",
                "required": True,
                "max_words": 60,
            },
            {
                "key": "care_plan_familiarity",
                "label": "Have you been shown how to read a care plan?",
                "type": "radio",
                "required": True,
                "options": [
                    {"value": "yes", "label": "Yes"},
                    {"value": "no", "label": "No — I need to be shown"},
                    {"value": "not_applicable", "label": "Not applicable in my role"},
                ],
            },
            {
                "key": "consent_understanding",
                "label": "What would you do if a service user withdrew consent for a care task?",
                "type": "textarea",
                "required": True,
                "max_words": 60,
            },
            {
                "key": "person_centred_approaches",
                "label": "Which of the following have been covered during your induction?",
                "type": "checkboxes",
                "required": True,
                "options": [
                    {"value": "history_preferences", "label": "Recording history and preferences"},
                    {"value": "consent_capacity", "label": "Consent and mental capacity"},
                    {"value": "advocacy", "label": "Advocacy and involving families"},
                    {"value": "care_planning", "label": "Contributing to care planning"},
                    {"value": "risk_enablement", "label": "Positive risk-taking and enablement"},
                ],
            },
        ],
    },

    # ── Standard 6: Communication ─────────────────────────────────────────────
    "cc_communication": {
        "form_id": "cc_communication",
        "standard_code": "communication",
        "standard_number": 6,
        "title": "Communication",
        "description": (
            "Answer the questions below to confirm you can communicate effectively "
            "with service users, families, and your team."
        ),
        "fields": [
            {
                "key": "effective_communication",
                "label": "Describe how you communicate clearly with someone in your care.",
                "hint": "Think about verbal, written, and non-verbal communication.",
                "type": "textarea",
                "required": True,
                "max_words": 80,
                "role_prompt_key": "communication",
            },
            {
                "key": "barrier_example",
                "label": "Give an example of a communication barrier and how you would overcome it.",
                "hint": "For example, language differences, hearing impairment, cognitive impairment.",
                "type": "textarea",
                "required": True,
                "max_words": 80,
            },
            {
                "key": "documentation_understood",
                "label": "Do you understand what you must document after each care interaction?",
                "type": "radio",
                "required": True,
                "options": [
                    {"value": "yes", "label": "Yes — I know what and where to record"},
                    {"value": "mostly", "label": "Mostly — I may need guidance on some records"},
                    {"value": "no", "label": "No — I need to be shown"},
                ],
            },
            {
                "key": "confidentiality",
                "label": "Describe what information about service users is confidential and who you can share it with.",
                "type": "textarea",
                "required": True,
                "max_words": 60,
            },
            {
                "key": "communication_methods_covered",
                "label": "Which communication approaches have been covered during your induction?",
                "type": "checkboxes",
                "required": True,
                "options": [
                    {"value": "verbal", "label": "Verbal and active listening"},
                    {"value": "written_records", "label": "Written records and documentation"},
                    {"value": "non_verbal", "label": "Non-verbal and body language"},
                    {"value": "interpreters", "label": "Using interpreters or communication aids"},
                    {"value": "difficult_conversations", "label": "Difficult or sensitive conversations"},
                ],
            },
        ],
    },

    # ── Standard 7: Privacy and Dignity ───────────────────────────────────────
    "cc_privacy_and_dignity": {
        "form_id": "cc_privacy_and_dignity",
        "standard_code": "privacy_dignity",
        "standard_number": 7,
        "title": "Privacy and Dignity",
        "description": (
            "Answer the questions below to confirm you understand how to protect "
            "the privacy and dignity of the people you support."
        ),
        "fields": [
            {
                "key": "privacy_example",
                "label": "Give a practical example of how you protect a service user's privacy.",
                "hint": "Think about personal care, conversations, or information handling.",
                "type": "textarea",
                "required": True,
                "max_words": 80,
                "role_prompt_key": "privacy_dignity",
            },
            {
                "key": "dignity_in_care",
                "label": "How do you make sure a service user feels respected during personal care?",
                "type": "textarea",
                "required": True,
                "max_words": 80,
            },
            {
                "key": "consent_before_care",
                "label": "What do you do before starting any personal care task?",
                "type": "radio",
                "required": True,
                "options": [
                    {"value": "explain_and_consent", "label": "Explain what I am going to do and get consent"},
                    {"value": "knock_and_enter", "label": "Knock and enter without explaining"},
                    {"value": "follow_care_plan", "label": "Follow the care plan without asking"},
                ],
            },
            {
                "key": "information_privacy",
                "label": "Give an example of how you keep information about a service user private.",
                "hint": "For example, not discussing their care in public areas, locking records.",
                "type": "textarea",
                "required": True,
                "max_words": 60,
            },
            {
                "key": "dignity_topics_covered",
                "label": "Which of the following have been covered during your induction?",
                "type": "checkboxes",
                "required": True,
                "options": [
                    {"value": "personal_care_privacy", "label": "Privacy during personal care"},
                    {"value": "information_handling", "label": "Confidential information handling"},
                    {"value": "individual_choices", "label": "Respecting individual choices and identity"},
                    {"value": "dignity_in_end_of_life", "label": "Dignity at end of life"},
                    {"value": "complaints_concerns", "label": "Raising concerns about dignity"},
                ],
            },
        ],
    },
}


def get_worker_form_schema(form_id: str, role_normalized: str = "") -> dict:
    """
    Return the form schema for a given form_id, with role-aware prompt injected.

    The base field structure stays the same. Fields with a role_prompt_key
    get their label/hint overridden by the matching role variant if available.
    """
    schema = CC_WORKER_FORMS.get(form_id)
    if not schema:
        return {}

    # Deep-copy fields and inject role-aware prompts where applicable
    fields = []
    for field in schema["fields"]:
        f = dict(field)
        if f.get("role_prompt_key") and role_normalized:
            rp = get_role_prompt(f["role_prompt_key"], role_normalized)
            if rp.get("prompt"):
                f["label"] = rp["prompt"]
            if rp.get("examples"):
                f["hint"] = f.get("hint", "") + (
                    f" Examples: {rp['examples']}" if f.get("hint") else rp["examples"]
                )
        fields.append(f)

    return {
        **schema,
        "fields": fields,
    }


def get_all_worker_form_ids() -> list:
    """Return all form_ids available as worker hybrid induction forms."""
    return list(CC_WORKER_FORMS.keys())


def validate_worker_form_submission(form_id: str, data: dict) -> list:
    """
    Validate submitted form data against the schema.
    Returns a list of error strings. Empty list = valid.
    """
    schema = CC_WORKER_FORMS.get(form_id)
    if not schema:
        return [f"Unknown form: {form_id}"]

    errors = []
    for field in schema["fields"]:
        key = field["key"]
        required = field.get("required", False)
        value = data.get(key)

        if required:
            if value is None or (isinstance(value, str) and not value.strip()):
                errors.append(f"Field '{field['label']}' is required.")
            elif isinstance(value, list) and len(value) == 0:
                errors.append(f"Field '{field['label']}' requires at least one selection.")

        if value and isinstance(value, str):
            max_words = field.get("max_words")
            if max_words:
                word_count = len(value.split())
                if word_count > max_words:
                    errors.append(
                        f"Field '{field['label']}' exceeds {max_words} words ({word_count} used)."
                    )

    return errors
