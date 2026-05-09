"""
Expanded Document Destination Register v2
Master compliance document source supporting Osabea Healthcare Solutions Ltd archive
Supports 5 document categories + folder hierarchy + 400+ templates

Categories:
1. Service-user care plan templates (Assessment, monitoring, care planning)
2. Operational documents (Incidents, body maps, behavior logs, nutrition, moving/handling)
3. HR documents (Recruitment, disciplinary, employment policies)
4. Policies (Safeguarding, whistleblowing, H&S, operations compliance)
5. Compliance/Quality records (Audits, competency, risk assessments)
"""

from copy import deepcopy
from typing import Any, Dict, List, Optional


def _record(
    destination_section: str,
    title: str,
    *,
    section_type: str,
    category: str,
    folder_path: Optional[str] = None,
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
        "category": category,
        "folder_path": folder_path,
        "accepted_template_types": accepted_template_types,
        "accepted_document_types": accepted_document_types,
        "match_terms": match_terms,
        "notes": notes,
    }


EXPANDED_DESTINATION_REGISTER: List[Dict[str, Any]] = [
    # ===== SERVICE-USER CARE PLAN TEMPLATES (Category: service-user-care-plans) =====
    _record(
        "su_personal_referral",
        "Personal Info & Referral",
        section_type="service_user_tab",
        category="service-user-care-plans",
        folder_path="Care Plan Documents",
        accepted_template_types=["referral_form", "initial_assessment", "personal_details", "person_centered_information"],
        match_terms=["referral", "intake", "initial assessment", "personal details", "person centered information"],
        notes="Referral and initial intake documents"
    ),
    _record(
        "su_consent_contracts",
        "Consent & Contracts",
        section_type="service_user_tab",
        category="service-user-care-plans",
        folder_path="Care Plan Documents",
        accepted_template_types=["service_agreement", "consent_form", "terms_conditions", "confidentiality"],
        match_terms=["consent", "service agreement", "contract", "terms", "confidentiality"],
    ),
    _record(
        "su_assessments",
        "Assessments",
        section_type="service_user_tab",
        category="service-user-care-plans",
        folder_path="Care Plan Documents",
        accepted_template_types=[
            "needs_assessment", "capacity_assessment", "mental_health_assessment", "nutrition_assessment",
            "healthcare_assessment", "financial_assessment", "environmental_assessment", "sexuality_assessment"
        ],
        match_terms=["assessment", "capacity", "needs", "mental health", "nutrition", "healthcare", "financial", "environmental"],
    ),
    _record(
        "su_care_plans",
        "Care Plans",
        section_type="service_user_tab",
        category="service-user-care-plans",
        folder_path="Care Plan Documents",
        accepted_template_types=[
            "care_plan", "support_plan", "daily_routine", "activities_plan", "care_plan_activities",
            "end_of_life_care_plan", "diabetes_management_plan", "epilepsy_management_plan"
        ],
        match_terms=["care plan", "support plan", "daily routine", "activities plan", "management plan"],
    ),
    _record(
        "su_risk_assessments",
        "Risk Assessments",
        section_type="service_user_tab",
        category="service-user-care-plans",
        folder_path="Care Plan Documents",
        accepted_template_types=[
            "risk_assessment", "falls_risk", "environmental_risk", "infection_control_risk", "medication_risk", "ligature_risk"
        ],
        match_terms=["risk assessment", "risk", "falls", "environmental", "infection", "medication"],
    ),
    _record(
        "su_monitoring_charts",
        "Monitoring Charts",
        section_type="service_user_tab",
        category="service-user-care-plans",
        folder_path="Care Plan Documents",
        accepted_template_types=[
            "daily_log", "fluid_chart", "food_chart", "repositioning_chart", "blood_pressure_log",
            "blood_sugar_log", "bowel_record_chart", "weight_chart"
        ],
        match_terms=["monitoring", "daily log", "fluid chart", "food chart", "blood pressure", "blood sugar", "bowel", "weight"],
    ),
    _record(
        "su_medication",
        "Medication",
        section_type="service_user_tab",
        category="service-user-care-plans",
        folder_path="Care Plan Documents",
        accepted_template_types=[
            "mar_chart", "prescription", "medication_list", "prn_protocol", "medication_changes_form"
        ],
        match_terms=["medication", "mar", "prescription", "prn", "medication list"],
    ),
    _record(
        "su_health_visits",
        "Health Visits",
        section_type="service_user_tab",
        category="service-user-care-plans",
        folder_path="Care Plan Documents",
        accepted_template_types=[
            "gp_visit", "hospital_letter", "district_nurse_visit", "specialist_report", "healthcare_letter"
        ],
        match_terms=["health visit", "gp visit", "hospital", "district nurse", "specialist"],
    ),
    _record(
        "su_reviews",
        "Reviews",
        section_type="service_user_tab",
        category="service-user-care-plans",
        folder_path="Care Plan Documents",
        accepted_template_types=[
            "care_review", "quality_check", "family_feedback", "annual_review", "care_plan_review"
        ],
        match_terms=["review", "annual review", "quality check", "family feedback"],
    ),
    _record(
        "su_correspondence",
        "Letters & Correspondence",
        section_type="service_user_tab",
        category="service-user-care-plans",
        folder_path="Care Plan Documents",
        accepted_template_types=["letter", "email_correspondence", "handover_form", "staff_handover"],
        match_terms=["correspondence", "letter", "email", "handover"],
    ),
    _record(
        "su_daily_notes",
        "Daily Notes",
        section_type="service_user_tab",
        category="service-user-care-plans",
        folder_path="Care Plan Documents",
        accepted_template_types=[
            "daily_note", "shift_note", "handover", "continuation_sheet", "daily_diary", "daily_visit_record"
        ],
        match_terms=["daily note", "shift note", "handover", "continuation", "daily diary", "visit record"],
    ),

    # ===== OPERATIONAL DOCUMENTS (Category: operational-documents) =====
    _record(
        "incidents",
        "Incidents & Accidents",
        section_type="operational",
        category="operational-documents",
        folder_path="Health and Safety",
        accepted_template_types=[
            "accident_form", "incident_form", "near_miss_form", "incident_log", "incident_continuation_sheet",
            "root_cause_analysis", "ligature_incident_risk_assessment"
        ],
        match_terms=["incident", "accident", "near miss", "root cause", "ligature"],
    ),
    _record(
        "body_maps",
        "Body Maps",
        section_type="operational",
        category="operational-documents",
        folder_path="Health and Safety",
        accepted_template_types=[
            "body_map", "body_chart", "body_map_for_creams", "skin_integrity", "body_map_female", "body_map_male"
        ],
        match_terms=["body map", "body chart", "skin integrity", "wound", "cream"],
    ),
    _record(
        "behaviour_logs",
        "Behaviour Logs",
        section_type="operational",
        category="operational-documents",
        folder_path="Health and Safety",
        accepted_template_types=[
            "behaviour_log", "abc_log", "behaviour_record", "behaviour_observation", "positive_behaviour_daily_routine"
        ],
        match_terms=["behaviour", "behavior", "abc log", "observation", "positive behaviour"],
    ),
    _record(
        "nutrition_operational",
        "Nutrition & Hydration",
        section_type="operational",
        category="operational-documents",
        folder_path="Care Plan Documents + Health and Safety",
        accepted_template_types=[
            "nutrition_chart", "nutritional_intake_chart", "food_chart", "fluid_chart", "intake_chart",
            "choking_prevention_plan", "modified_diet_checklist", "swallowing_assessment", "iddsi_level_form"
        ],
        match_terms=["nutrition", "fluid", "food chart", "intake", "choking", "modified diet", "swallowing", "iddsi"],
    ),
    _record(
        "moving_handling",
        "Moving & Handling",
        section_type="operational",
        category="operational-documents",
        folder_path="Health and Safety",
        accepted_template_types=[
            "moving_handling_assessment", "moving_handling_plan", "manual_handling_assessment",
            "hoist_sling_inspection", "equipment_safety_inspection"
        ],
        match_terms=["moving and handling", "manual handling", "hoist", "sling", "equipment safety"],
    ),
    _record(
        "medication_operational",
        "Medication Management",
        section_type="operational",
        category="operational-documents",
        folder_path="Health and Safety",
        accepted_template_types=[
            "medication_assessment", "medication_plan", "covert_medication_form", "homely_remedies_form",
            "prn_medication_form", "medication_changes_form", "medication_handover_form", "medication_received_form",
            "medication_count_form", "medication_returns_form", "medication_competency_assessment"
        ],
        match_terms=["medication", "medication assessment", "medication plan", "covert", "homely remedies", "prn", "competency"],
    ),
    _record(
        "risk_assessments_operational",
        "Risk Assessments",
        section_type="operational",
        category="operational-documents",
        folder_path="Health and Safety",
        accepted_template_types=[
            "generic_risk_assessment", "falls_risk", "environmental_risk", "lone_worker_risk", "coshh_risk",
            "fire_risk_assessment", "dse_workstation_assessment", "pregnant_staff_risk_assessment"
        ],
        match_terms=["risk assessment", "falls", "environmental", "lone worker", "coshh", "fire", "dse", "pregnant"],
    ),
    _record(
        "equipment_safety",
        "Equipment & Safety Inspections",
        section_type="operational",
        category="operational-documents",
        folder_path="Health and Safety",
        accepted_template_types=[
            "hoist_inspection", "walking_aid_inspection", "electric_bed_inspection", "pat_log", "fire_alarm_check",
            "fire_safety_checklist", "water_temperature_record", "legionella_record", "descaling_record"
        ],
        match_terms=["inspection", "safety check", "equipment", "hoist", "walking aid", "electric bed", "pat", "fire", "temperature"],
    ),
    _record(
        "staffing_operational",
        "Staffing & Rotas",
        section_type="operational",
        category="operational-documents",
        folder_path="Operations",
        accepted_template_types=[
            "care_staff_rota", "staff_weekly_rota", "on_call_log", "on_call_handover", "lone_worker_checklist",
            "staff_signature_record", "staff_file_list", "key_holder_agreement", "key_holder_register"
        ],
        match_terms=["rota", "on call", "lone worker", "signature", "key holder"],
    ),
    _record(
        "financial_operational",
        "Financial Records",
        section_type="operational",
        category="operational-documents",
        folder_path="Operations",
        accepted_template_types=[
            "petty_cash_sheet", "financial_transaction_sheet", "financial_assessment", "mileage_expenses_form",
            "invoice_template", "service_user_bank_details"
        ],
        match_terms=["financial", "petty cash", "expense", "mileage", "invoice", "bank details"],
    ),
    _record(
        "visits_operations",
        "Visit Management",
        section_type="operational",
        category="operational-documents",
        folder_path="Operations",
        accepted_template_types=[
            "daily_visit_records", "daily_hourly_visit_records", "late_visit_record", "missed_visit_record",
            "welfare_check_log", "holiday_plan", "no_reply_visit_form"
        ],
        match_terms=["visit", "visit records", "late visit", "missed visit", "welfare check", "holiday", "no reply"],
    ),

    # ===== HR DOCUMENTS (Category: hr-documents) =====
    _record(
        "recruitment",
        "Recruitment & Selection",
        section_type="hr",
        category="hr-documents",
        folder_path="Document Templates/Recruitment",
        accepted_template_types=[
            "job_advert", "application_form", "applicant_information", "recruitment_checklist",
            "invite_to_interview", "dbs_risk_assessment", "references_risk_assessment",
            "unsuccessful_letter", "successful_letter", "offer_letter", "probation_letter"
        ],
        match_terms=["recruitment", "job advert", "application", "interview", "dbs", "references", "offer", "probation"],
    ),
    _record(
        "onboarding",
        "Onboarding & Induction",
        section_type="hr",
        category="hr-documents",
        folder_path="Document Templates/Recruitment/New Starter Pack",
        accepted_template_types=[
            "induction_checklist_day_one", "induction_checklist_week_one", "induction_checklist_month_one",
            "induction_checklist_months_3_6", "probation_review_report", "successful_completion_letter"
        ],
        match_terms=["induction", "onboarding", "new starter", "probation review", "induction checklist"],
    ),
    _record(
        "disciplinary_hr",
        "Disciplinary & Capability",
        section_type="hr",
        category="hr-documents",
        folder_path="Document Templates/Disciplinary",
        accepted_template_types=[
            "disciplinary_flowchart", "disciplinary_hearing_format", "suspension_letter", "investigation_invite",
            "written_warning_letter", "capability_policy", "dismissal_letter", "no_action_letter"
        ],
        match_terms=["disciplinary", "capability", "suspension", "warning", "dismissal", "investigation"],
    ),
    _record(
        "absence_management",
        "Absence Management",
        section_type="hr",
        category="hr-documents",
        folder_path="Human Resources",
        accepted_template_types=[
            "absence_record_form", "absence_lateness_record", "absence_contact_record", "absence_monthly_contact",
            "absence_concern_meeting", "sickness_reporting_form", "sickness_self_certificate", "return_to_work_interview"
        ],
        match_terms=["absence", "sickness", "lateness", "contact record", "return to work"],
    ),
    _record(
        "performance_management",
        "Performance & Development",
        section_type="hr",
        category="hr-documents",
        folder_path="Human Resources",
        accepted_template_types=[
            "annual_performance_review", "performance_self_assessment", "staff_development_plan",
            "nominated_individual_supervision_review", "registered_manager_supervision_review",
            "senior_staff_observation_sheet", "staff_spot_check_form", "staff_competency_checklist"
        ],
        match_terms=["performance", "review", "development plan", "supervision", "observation", "competency"],
    ),
    _record(
        "employment_contracts",
        "Employment Contracts & Terms",
        section_type="hr",
        category="hr-documents",
        folder_path="Human Resources",
        accepted_template_types=[
            "statement_of_main_terms", "employment_contract_change", "confidentiality_agreement",
            "code_of_conduct", "professional_boundaries_policy"
        ],
        match_terms=["contract", "statement of terms", "confidentiality", "code of conduct", "professional boundaries"],
    ),
    _record(
        "leave_management",
        "Leave & Time Off",
        section_type="hr",
        category="hr-documents",
        folder_path="Human Resources",
        accepted_template_types=[
            "annual_leave_policy", "annual_leave_request_form", "maternity_leave_policy",
            "maternity_confirmation_letter", "adoption_leave_policy", "paternity_leave_policy",
            "flexible_working_policy", "staff_breaks_policy", "overtime_policy"
        ],
        match_terms=["leave", "annual leave", "maternity", "adoption", "paternity", "flexible working", "breaks"],
    ),
    _record(
        "compliance_hr",
        "HR Compliance & Policies",
        section_type="hr",
        category="hr-documents",
        folder_path="Human Resources",
        accepted_template_types=[
            "equal_opportunity_policy", "equality_diversity_inclusion_policy", "anti_harassment_bullying_policy",
            "drug_alcohol_testing_policy", "data_protection_policy", "information_security_policy",
            "social_media_policy", "mobile_phone_policy", "dress_code_policy", "gift_declaration_form"
        ],
        match_terms=["compliance", "equal opportunity", "equality", "harassment", "bullying", "drug", "alcohol", "data protection"],
    ),
    _record(
        "exit_management",
        "Exit & Offboarding",
        section_type="hr",
        category="hr-documents",
        folder_path="Human Resources",
        accepted_template_types=[
            "exit_interview_template", "exit_survey", "termination_letter", "redundancy_policy",
            "medical_report_request_letter", "consent_medical_report"
        ],
        match_terms=["exit", "termination", "offboarding", "redundancy", "medical report"],
    ),

    # ===== POLICIES & COMPLIANCE (Category: policies-compliance) =====
    _record(
        "safeguarding_policies",
        "Safeguarding Policies",
        section_type="policy",
        category="policies-compliance",
        folder_path="Safeguarding",
        accepted_template_types=[
            "safeguarding_adults_policy", "safeguarding_incident_report", "safeguarding_incident_log",
            "whistleblowing_policy", "whistleblowing_flowchart", "modern_slavery_policy",
            "human_trafficking_policy", "self_neglect_hoarding_policy"
        ],
        match_terms=["safeguarding", "whistleblowing", "modern slavery", "human trafficking", "self neglect"],
    ),
    _record(
        "health_safety_policies",
        "Health & Safety Policies",
        section_type="policy",
        category="policies-compliance",
        folder_path="Health and Safety",
        accepted_template_types=[
            "health_safety_policy", "accident_incident_policy", "fire_safety_policy", "first_aid_policy",
            "food_safety_policy", "infection_prevention_policy", "lone_working_policy", "moving_handling_policy",
            "oxygen_therapy_policy", "medical_emergency_policy", "dse_policy", "ppesafety_policy"
        ],
        match_terms=["health and safety", "fire safety", "first aid", "food safety", "infection", "lone working"],
    ),
    _record(
        "operational_policies",
        "Operational Policies",
        section_type="policy",
        category="policies-compliance",
        folder_path="Operations",
        accepted_template_types=[
            "record_keeping_policy", "confidentiality_policy", "consent_to_care_policy",
            "mental_capacity_policy", "best_interests_policy", "complaints_policy",
            "compliments_policy", "late_missed_visits_policy", "missing_persons_policy",
            "death_of_service_user_policy", "end_of_life_policy"
        ],
        match_terms=["operational", "record keeping", "confidentiality", "consent", "mental capacity", "complaints"],
    ),
    _record(
        "governance_policies",
        "Governance & Management",
        section_type="policy",
        category="policies-compliance",
        folder_path="Operations",
        accepted_template_types=[
            "good_governance_policy", "fit_proper_persons_policy", "cqc_notification_log",
            "business_continuity_policy", "risk_management_policy", "finance_policy",
            "person_centered_care_policy", "accessible_information_standard_policy"
        ],
        match_terms=["governance", "fit and proper", "cqc", "business continuity", "finance", "person centered"],
    ),
    _record(
        "medication_policies",
        "Medication Policies",
        section_type="policy",
        category="policies-compliance",
        folder_path="Health and Safety",
        accepted_template_types=[
            "medication_management_policy", "medication_administration_policy", "warfarin_policy",
            "covert_medication_policy", "homely_remedies_policy", "controlled_drugs_policy"
        ],
        match_terms=["medication", "medication management", "administration", "warfarin", "covert", "controlled drugs"],
    ),
    _record(
        "environmental_policies",
        "Environmental & Sustainability",
        section_type="policy",
        category="policies-compliance",
        folder_path="Operations",
        accepted_template_types=[
            "environmental_waste_management_policy", "health_sustainability_policy",
            "environmental_risk_assessment", "legionella_policy", "coshh_policy"
        ],
        match_terms=["environmental", "waste management", "sustainability", "legionella", "coshh"],
    ),

    # ===== QUALITY & COMPLIANCE RECORDS (Category: quality-compliance-records) =====
    _record(
        "audit_records",
        "Audit Records & Tools",
        section_type="audit",
        category="quality-compliance-records",
        folder_path="Quality Assurance/Audits",
        accepted_template_types=[
            "care_plan_audit", "medication_audit", "staff_file_audit", "fire_safety_audit",
            "infection_control_audit", "data_protection_audit", "complaints_audit", "safeguarding_audit",
            "moving_handling_audit", "pressure_area_audit", "accident_incident_audit"
        ],
        match_terms=["audit", "care plan audit", "medication audit", "fire safety audit"],
    ),
    _record(
        "competency_assessments",
        "Competency & Training",
        section_type="audit",
        category="quality-compliance-records",
        folder_path="Quality Assurance/Competency Checklists",
        accepted_template_types=[
            "medication_competency", "infection_prevention_competency", "moving_handling_competency",
            "first_aid_competency", "training_needs_analysis", "competency_tracker",
            "staff_knowledge_understanding_policy"
        ],
        match_terms=["competency", "competency assessment", "training", "knowledge understanding"],
    ),
    _record(
        "quality_assessment_framework",
        "Quality Assessment Framework",
        section_type="audit",
        category="quality-compliance-records",
        folder_path="Quality Assurance/Single Assessment Framework",
        accepted_template_types=[
            "single_assessment_framework", "quality_framework", "quality_check_form"
        ],
        match_terms=["assessment framework", "quality assessment", "quality framework"],
    ),
    _record(
        "digital_audits",
        "Digital Audits & Tracking",
        section_type="audit",
        category="quality-compliance-records",
        folder_path="Quality Assurance/Digital Audits",
        accepted_template_types=[
            "care_notes_audit", "digital_audit", "accessibility_audit", "data_audit"
        ],
        match_terms=["digital audit", "care notes audit", "accessibility audit"],
    ),
    _record(
        "quality_feedback",
        "Quality Feedback & Surveys",
        section_type="audit",
        category="quality-compliance-records",
        folder_path="Quality Assurance",
        accepted_template_types=[
            "family_quality_feedback", "staff_views_survey", "stakeholder_feedback",
            "service_user_advocate_survey", "quality_questionnaire"
        ],
        match_terms=["feedback", "survey", "questionnaire", "quality feedback"],
    ),
    _record(
        "review_records",
        "Review & Planning Records",
        section_type="audit",
        category="quality-compliance-records",
        folder_path="Quality Assurance/Planners",
        accepted_template_types=[
            "person_centered_review", "care_review", "annual_review", "review_minutes",
            "review_of_care_form", "planning_record"
        ],
        match_terms=["review", "care review", "annual review", "planning"],
    ),
]


def get_expanded_destination_register() -> List[Dict[str, Any]]:
    return deepcopy(EXPANDED_DESTINATION_REGISTER)


def get_destinations_by_category(category: str) -> List[Dict[str, Any]]:
    return deepcopy([r for r in EXPANDED_DESTINATION_REGISTER if r["category"] == category])


def get_destinations_by_section_type(section_type: str) -> List[Dict[str, Any]]:
    return deepcopy([r for r in EXPANDED_DESTINATION_REGISTER if r["section_type"] == section_type])


def find_expanded_destination(destination_section: str) -> Optional[Dict[str, Any]]:
    if not destination_section:
        return None
    for record in EXPANDED_DESTINATION_REGISTER:
        if record["destination_section"] == destination_section:
            return deepcopy(record)
    return None


def suggest_expanded_destination(
    *,
    filename: str = "",
    folder_path: str = "",
    text_sample: str = "",
    classification: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Enhanced destination suggestion using folder_path + filename + text + classification."""
    parts = [folder_path or "", filename or "", text_sample or ""]
    classification = classification or {}
    
    for key in (
        "category", "document_type", "workflow_area", "usage_audience",
        "primary_user_role", "admin_owner_role", "worker_visibility",
        "frequency", "review_cycle_months", "suggested_title"
    ):
        value = classification.get(key)
        if isinstance(value, dict):
            parts.extend([str(value.get("value") or ""), str(value.get("reasoning") or "")])
        elif value is not None:
            parts.append(str(value))

    haystack = " ".join(parts).lower()
    if not haystack.strip():
        return None

    # Prioritize by section_type: operational > audit > policy > hr > service_user
    prioritized_records = [
        *[r for r in EXPANDED_DESTINATION_REGISTER if r["section_type"] == "operational"],
        *[r for r in EXPANDED_DESTINATION_REGISTER if r["section_type"] == "audit"],
        *[r for r in EXPANDED_DESTINATION_REGISTER if r["section_type"] == "policy"],
        *[r for r in EXPANDED_DESTINATION_REGISTER if r["section_type"] == "hr"],
        *[r for r in EXPANDED_DESTINATION_REGISTER if r["section_type"] == "service_user_tab"],
    ]

    for record in prioritized_records:
        matched_terms = [term for term in record["match_terms"] if term and term.lower() in haystack]
        if matched_terms:
            confidence = min(0.99, 0.72 + (0.05 * min(len(matched_terms), 4)))
            return {
                "destination_section": record["destination_section"],
                "title": record["title"],
                "section_type": record["section_type"],
                "category": record["category"],
                "confidence": confidence,
                "reasoning": f"Matched: {', '.join(matched_terms[:4])}",
            }

    # Fallback to classification-based mapping
    workflow_area = str((classification.get("workflow_area") or {}).get("value") or "").lower()
    document_type = str((classification.get("document_type") or {}).get("value") or "").lower()
    category = str((classification.get("category") or {}).get("value") or "").lower()

    fallback_map = {
        "body_map": "body_maps",
        "incident_report": "incidents",
        "medication": "medication_operational",
        "risk_assessment": "risk_assessments_operational",
        "care_plan": "su_care_plans",
        "recruitment": "recruitment",
        "audit": "audit_records",
        "safeguarding": "safeguarding_policies",
        "policy": "health_safety_policies",
        "compliance": "audit_records",
    }

    fallback_destination = fallback_map.get(workflow_area) or fallback_map.get(document_type) or fallback_map.get(category)
    if fallback_destination:
        record = find_expanded_destination(fallback_destination)
        if record:
            return {
                "destination_section": record["destination_section"],
                "title": record["title"],
                "section_type": record["section_type"],
                "category": record["category"],
                "confidence": 0.55,
                "reasoning": f"Fallback from workflow/type/category",
            }

    return None
