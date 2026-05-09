from copy import deepcopy
from typing import Any, Dict, List, Optional


def _record(
    destination_section: str,
    title: str,
    *,
    section_type: str,
    section_id: Optional[str] = None,
    accepted_template_types: List[str],
    accepted_document_types: Optional[List[str]] = None,
    match_terms: Optional[List[str]] = None,
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    accepted_document_types = accepted_document_types or list(accepted_template_types)
    match_terms = match_terms or list(
        dict.fromkeys(
            [
                *accepted_template_types,
                *accepted_document_types,
                title.lower(),
                destination_section.replace("_", " "),
            ]
        )
    )
    return {
        "destination_section": destination_section,
        "section_id": section_id or destination_section,
        "title": title,
        "section_type": section_type,
        "accepted_template_types": accepted_template_types,
        "accepted_document_types": accepted_document_types,
        "match_terms": match_terms,
        "notes": notes,
    }


SERVICE_USER_DESTINATION_REGISTER: List[Dict[str, Any]] = [
    _record(
        "1_personal_referral",
        "Personal Info & Referral",
        section_type="tab",
        section_id="1_personal_referral",
        accepted_template_types=["referral_form", "initial_assessment", "personal_details"],
        accepted_document_types=["referral_form", "initial_assessment", "personal_details"],
        match_terms=["personal info", "referral", "intake", "initial assessment", "personal details"],
    ),
    _record(
        "2_consent_contracts",
        "Consent & Contracts",
        section_type="tab",
        section_id="2_consent_contracts",
        accepted_template_types=["service_agreement", "consent_form", "terms_conditions", "confidentiality"],
        accepted_document_types=["service_agreement", "consent_form", "terms_conditions", "confidentiality"],
        match_terms=["consent", "service agreement", "contract", "terms and conditions", "confidentiality"],
    ),
    _record(
        "3_assessments",
        "Assessments",
        section_type="tab",
        section_id="3_assessments",
        accepted_template_types=["needs_assessment", "capacity_assessment", "mental_health_assessment", "nutrition_assessment"],
        accepted_document_types=["needs_assessment", "capacity_assessment", "mental_health_assessment", "nutrition_assessment"],
        match_terms=["assessment", "capacity", "needs assessment", "mental health assessment", "nutrition assessment"],
    ),
    _record(
        "4_care_plans",
        "Care Plans",
        section_type="tab",
        section_id="4_care_plans",
        accepted_template_types=["care_plan", "support_plan", "daily_routine", "activities_plan", "care_plan_activities"],
        accepted_document_types=["care_plan", "support_plan", "daily_routine", "activities_plan", "care_plan_activities"],
        match_terms=["care plan", "support plan", "daily routine", "activities plan", "care plan activities"],
    ),
    _record(
        "5_risk_assessments",
        "Risk Assessments",
        section_type="tab",
        section_id="5_risk_assessments",
        accepted_template_types=["risk_assessment", "falls_risk", "environmental_risk", "infection_control_risk", "medication_risk"],
        accepted_document_types=["risk_assessment", "falls_risk", "environmental_risk", "infection_control_risk", "medication_risk"],
        match_terms=["risk assessment", "risk", "falls risk", "environmental risk", "infection control risk"],
    ),
    _record(
        "6_monitoring",
        "Monitoring",
        section_type="tab",
        section_id="6_monitoring",
        accepted_template_types=["daily_log", "fluid_chart", "food_chart", "repositioning_chart"],
        accepted_document_types=["daily_log", "fluid_chart", "food_chart", "repositioning_chart"],
        match_terms=["monitoring", "daily log", "fluid chart", "food chart", "repositioning chart"],
    ),
    _record(
        "7_medication",
        "Medication",
        section_type="tab",
        section_id="7_medication",
        accepted_template_types=["mar_chart", "prescription", "medication_list", "prn_protocol"],
        accepted_document_types=["mar_chart", "prescription", "medication_list", "prn_protocol"],
        match_terms=["mar", "prescription", "medication list", "prn protocol", "medication record"],
    ),
    _record(
        "8_health_visits",
        "Health Visits",
        section_type="tab",
        section_id="8_health_visits",
        accepted_template_types=["gp_visit", "hospital_letter", "district_nurse_visit", "specialist_report"],
        accepted_document_types=["gp_visit", "hospital_letter", "district_nurse_visit", "specialist_report"],
        match_terms=["health visit", "gp visit", "hospital letter", "district nurse", "specialist report"],
    ),
    _record(
        "9_reviews",
        "Reviews",
        section_type="tab",
        section_id="9_reviews",
        accepted_template_types=["care_review", "quality_check", "family_feedback", "annual_review"],
        accepted_document_types=["care_review", "quality_check", "family_feedback", "annual_review"],
        match_terms=["review", "care review", "quality check", "family feedback", "annual review"],
    ),
    _record(
        "10_correspondence",
        "Letters & Correspondence",
        section_type="tab",
        section_id="10_correspondence",
        accepted_template_types=["letter", "email_correspondence", "other"],
        accepted_document_types=["letter", "email_correspondence", "other"],
        match_terms=["correspondence", "letter", "email", "other correspondence"],
    ),
    _record(
        "11_daily_notes",
        "Daily Notes",
        section_type="tab",
        section_id="11_daily_notes",
        accepted_template_types=["daily_note", "shift_note", "handover", "continuation_sheet"],
        accepted_document_types=["daily_note", "shift_note", "handover", "continuation_sheet"],
        match_terms=["daily note", "shift note", "handover", "continuation sheet", "daily notes"],
    ),
    _record(
        "incidents",
        "Incidents",
        section_type="operational",
        accepted_template_types=["accident_form", "incident_form", "near_miss_form", "incident_log"],
        accepted_document_types=["accident_form", "incident_form", "near_miss_form", "incident_log"],
        match_terms=["incident", "accident", "near miss", "incident form", "accident form"],
    ),
    _record(
        "body_maps",
        "Body Maps",
        section_type="operational",
        accepted_template_types=["body_map", "body_chart", "body_map_for_creams", "skin_integrity"],
        accepted_document_types=["body_map", "body_chart", "body_map_for_creams", "skin_integrity"],
        match_terms=["body map", "body chart", "skin integrity", "body map for creams", "wound map"],
    ),
    _record(
        "behaviour_logs",
        "Behaviour Logs",
        section_type="operational",
        accepted_template_types=["behaviour_log", "abc_log", "behaviour_record", "behaviour_observation"],
        accepted_document_types=["behaviour_log", "abc_log", "behaviour_record", "behaviour_observation"],
        match_terms=["behaviour log", "behavior log", "abc log", "behaviour observation", "behaviour record"],
    ),
    _record(
        "nutrition_charts",
        "Nutrition Charts",
        section_type="operational",
        accepted_template_types=["nutrition_chart", "nutritional_intake_chart", "food_chart", "fluid_chart", "intake_chart"],
        accepted_document_types=["nutrition_chart", "nutritional_intake_chart", "food_chart", "fluid_chart", "intake_chart"],
        match_terms=["nutrition chart", "nutritional intake", "food chart", "fluid chart", "intake chart"],
    ),
    _record(
        "choking_modified_diet",
        "Choking / Modified Diet",
        section_type="operational",
        accepted_template_types=["choking_prevention_plan", "modified_diet_checklist", "swallowing_assessment", "texture_modification_checklist"],
        accepted_document_types=["choking_prevention_plan", "modified_diet_checklist", "swallowing_assessment", "texture_modification_checklist"],
        match_terms=["choking", "modified diet", "swallowing", "texture modification", "choking prevention"],
    ),
    _record(
        "moving_handling",
        "Moving & Handling",
        section_type="operational",
        accepted_template_types=["moving_handling_assessment", "moving_handling_plan", "manual_handling_assessment", "handling_risk_assessment"],
        accepted_document_types=["moving_handling_assessment", "moving_handling_plan", "manual_handling_assessment", "handling_risk_assessment"],
        match_terms=["moving and handling", "moving handling", "manual handling", "handling assessment"],
    ),
    _record(
        "medication_assessment",
        "Medication Assessment",
        section_type="operational",
        accepted_template_types=["medication_assessment", "medication_plan", "medication_risk_assessment", "prn_protocol"],
        accepted_document_types=["medication_assessment", "medication_plan", "medication_risk_assessment", "prn_protocol"],
        match_terms=["medication assessment", "medication plan", "medication risk", "prn protocol", "medication review"],
    ),
    _record(
        "risk_assessments",
        "Risk Assessments",
        section_type="operational",
        accepted_template_types=["generic_risk_assessment", "falls_risk", "environmental_risk", "lone_worker_risk", "coshh_risk"],
        accepted_document_types=["generic_risk_assessment", "falls_risk", "environmental_risk", "lone_worker_risk", "coshh_risk"],
        match_terms=["risk assessment", "falls risk", "environmental risk", "lone worker risk", "coshh"],
    ),
    _record(
        "reviews",
        "Reviews",
        section_type="operational",
        accepted_template_types=["care_review", "annual_review", "multi-disciplinary_review", "review_minutes"],
        accepted_document_types=["care_review", "annual_review", "multi-disciplinary_review", "review_minutes"],
        match_terms=["care review", "annual review", "review minutes", "multi disciplinary review"],
    ),
    _record(
        "daily_notes",
        "Daily Notes",
        section_type="operational",
        accepted_template_types=["daily_notes", "continuation_sheet", "handover_sheet", "shift_summary"],
        accepted_document_types=["daily_notes", "continuation_sheet", "handover_sheet", "shift_summary"],
        match_terms=["daily notes", "continuation sheet", "handover sheet", "shift summary"],
    ),
]


def get_service_user_destination_register() -> List[Dict[str, Any]]:
    return deepcopy(SERVICE_USER_DESTINATION_REGISTER)


def get_service_user_destination_lookup() -> Dict[str, Dict[str, Any]]:
    return {record["destination_section"]: deepcopy(record) for record in SERVICE_USER_DESTINATION_REGISTER}


def find_service_user_destination(destination_section: str) -> Optional[Dict[str, Any]]:
    if not destination_section:
        return None
    for record in SERVICE_USER_DESTINATION_REGISTER:
        if record["destination_section"] == destination_section:
            return deepcopy(record)
    return None


def suggest_service_user_destination_section(
    *,
    filename: str = "",
    text_sample: str = "",
    classification: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    parts = [filename or "", text_sample or ""]
    classification = classification or {}
    for key in (
        "category",
        "document_type",
        "workflow_area",
        "usage_audience",
        "primary_user_role",
        "admin_owner_role",
        "worker_visibility",
        "frequency",
        "review_cycle_months",
        "suggested_title",
    ):
        value = classification.get(key)
        if isinstance(value, dict):
            parts.extend([str(value.get("value") or ""), str(value.get("reasoning") or "")])
        elif value is not None:
            parts.append(str(value))

    haystack = " ".join(parts).lower()
    if not haystack.strip():
        return None

    prioritized_records = [
        *[record for record in SERVICE_USER_DESTINATION_REGISTER if record["section_type"] == "operational"],
        *[record for record in SERVICE_USER_DESTINATION_REGISTER if record["section_type"] == "tab"],
    ]

    for record in prioritized_records:
        matched_terms = [term for term in record["match_terms"] if term and term.lower() in haystack]
        if matched_terms:
            confidence = min(0.99, 0.72 + (0.05 * min(len(matched_terms), 4)))
            return {
                "destination_section": record["destination_section"],
                "title": record["title"],
                "section_type": record["section_type"],
                "confidence": confidence,
                "reasoning": f"Matched: {', '.join(matched_terms[:4])}",
            }

    workflow_area = str((classification.get("workflow_area") or {}).get("value") or "").lower()
    document_type = str((classification.get("document_type") or {}).get("value") or "").lower()
    category = str((classification.get("category") or {}).get("value") or "").lower()

    fallback_map = {
        "body_map": "body_maps",
        "incident_report": "incidents",
        "medication": "medication_assessment",
        "risk_assessment": "risk_assessments",
        "care_plan": "4_care_plans",
        "service_user_record": "3_assessments",
        "complaint": "10_correspondence",
        "audit": "9_reviews",
    }

    fallback_destination = fallback_map.get(workflow_area) or fallback_map.get(document_type) or fallback_map.get(category)
    if fallback_destination:
        record = find_service_user_destination(fallback_destination)
        if record:
            return {
                "destination_section": record["destination_section"],
                "title": record["title"],
                "section_type": record["section_type"],
                "confidence": 0.55,
                "reasoning": f"Fallback from workflow_area={workflow_area or 'n/a'} / document_type={document_type or 'n/a'} / category={category or 'n/a'}",
            }

    return None