# Template definitions for UK Care Compliance Portal
# Aligned with CQC-ready requirements

COMPLIANCE_TEMPLATES = [
    # ==================== 1. APPLICATION FORM (ROLE-AWARE) ====================
    {
        "name": "Application Form",
        "description": "Comprehensive job application form for care staff recruitment. Auto-adapts for Healthcare Assistant or Nurse roles.",
        "category": "Recruitment",
        "section": "Recruitment",
        "visibility": "normal",
        "role_specific": None,  # Both roles, with conditional sections
        "requires_employee_signature": True,
        "requires_admin_signature": True,
        "form_fields": [
            {"name": "section_personal", "type": "section_header", "label": "Section 1: Personal Details"},
            {"name": "full_name", "label": "Full Name", "type": "text", "required": True},
            {"name": "date_of_birth", "label": "Date of Birth", "type": "date", "required": True},
            {"name": "address", "label": "Address", "type": "textarea", "required": True, "rows": 2},
            {"name": "postcode", "label": "Postcode", "type": "text", "required": True},
            {"name": "phone", "label": "Phone Number", "type": "text", "required": True},
            {"name": "email", "label": "Email Address", "type": "email", "required": True},
            {"name": "national_insurance", "label": "National Insurance Number", "type": "text", "required": True},
            {"name": "right_to_work", "label": "Do you have the right to work in the UK?", "type": "select", "options": ["Yes", "No"], "required": True},
            
            {"name": "section_compliance", "type": "section_header", "label": "Section 2: Compliance Documents"},
            {"name": "passport_present", "label": "Do you have a valid Passport or ID?", "type": "select", "options": ["Yes", "No"], "required": True},
            {"name": "proof_of_address", "label": "Can you provide proof of address (utility bill/bank statement)?", "type": "select", "options": ["Yes", "No"], "required": True},
            {"name": "dbs_present", "label": "Do you have an existing DBS certificate?", "type": "select", "options": ["Yes", "No", "Applied"], "required": True},
            {"name": "dbs_number", "label": "DBS Certificate Number (if applicable)", "type": "text", "required": False},
            {"name": "dbs_update_service", "label": "Are you registered with the DBS Update Service?", "type": "select", "options": ["Yes", "No"], "required": False},
            
            # NURSE ONLY SECTION
            {"name": "section_nurse", "type": "section_header", "label": "Section 2a: Nursing Registration (Nurses Only)", "role_restriction": "nurse_only"},
            {"name": "nmc_info", "type": "info_box", "content": "Complete this section only if you are applying for a Nursing role.", "variant": "info", "role_restriction": "nurse_only"},
            {"name": "nmc_pin", "label": "NMC PIN Number", "type": "text", "required": False, "role_restriction": "nurse_only"},
            {"name": "nmc_expiry", "label": "NMC Registration Expiry Date", "type": "date", "required": False, "role_restriction": "nurse_only"},
            {"name": "revalidation_date", "label": "Next Revalidation Date", "type": "date", "required": False, "role_restriction": "nurse_only"},
            {"name": "nmc_under_investigation", "label": "Are you currently under NMC investigation or have any conditions on your practice?", "type": "select", "options": ["No", "Yes"], "required": False, "role_restriction": "nurse_only"},
            {"name": "nmc_investigation_details", "label": "If yes, please provide details", "type": "textarea", "required": False, "role_restriction": "nurse_only"},
            
            {"name": "section_qualifications", "type": "section_header", "label": "Section 3: Qualifications"},
            {"name": "qualifications", "label": "Qualifications (Care Certificate, NVQ, Nursing Degree, etc.)", "type": "textarea", "required": True, "rows": 3, "help_text": "List all relevant qualifications with dates achieved"},
            {"name": "additional_training", "label": "Additional Training/Certifications", "type": "textarea", "required": False, "rows": 2},
            
            {"name": "section_employment", "type": "section_header", "label": "Section 4: Employment History"},
            {"name": "employment_info", "type": "info_box", "content": "Please provide a full employment history for the past 5 years. Any gaps must be explained.", "variant": "warning"},
            {"name": "employment_history", "label": "Employment History", "type": "repeatable", "item_label": "Employer", "required": True, "fields": [
                {"name": "employer", "label": "Employer Name", "type": "text", "required": True},
                {"name": "job_title", "label": "Job Title", "type": "text", "required": True},
                {"name": "dates", "label": "Dates (From - To)", "type": "text", "required": True},
                {"name": "reason_leaving", "label": "Reason for Leaving", "type": "textarea", "required": True, "full_width": True}
            ]},
            {"name": "employment_gaps", "label": "Please explain any gaps in your employment history", "type": "textarea", "required": False, "rows": 2},
            
            {"name": "section_experience", "type": "section_header", "label": "Section 5: Care Experience"},
            {"name": "experience_areas", "label": "Areas of Experience (select all that apply)", "type": "multiselect", "required": True, "options": [
                "Personal Care", "Dementia Care", "Mental Health", "Learning Disabilities", 
                "Physical Disabilities", "Community Care", "End of Life Care", "Palliative Care",
                "Complex Care", "Paediatric Care", "Elderly Care", "Hospital Setting"
            ]},
            
            {"name": "section_skills", "type": "section_header", "label": "Section 6: Skills"},
            {"name": "skills", "label": "Key Skills (select all that apply)", "type": "multiselect", "required": True, "options": [
                "Manual Handling", "Medication Administration", "Safeguarding", "Infection Control",
                "Communication", "Care Planning", "Record Keeping", "First Aid", "Wound Care"
            ]},
            
            {"name": "section_training", "type": "section_header", "label": "Section 7: Mandatory Training"},
            {"name": "training_completed", "label": "Training Completed (select all that apply)", "type": "multiselect", "required": False, "options": [
                "Safeguarding Adults", "Safeguarding Children", "Infection Control", "Moving & Handling",
                "Basic Life Support (BLS)", "Medication Awareness", "Fire Safety", "Food Hygiene",
                "Mental Capacity Act", "GDPR/Data Protection", "Equality & Diversity"
            ]},
            
            {"name": "section_availability", "type": "section_header", "label": "Section 8: Availability"},
            {"name": "availability_days", "label": "Available for Day Shifts?", "type": "select", "options": ["Yes", "No", "Sometimes"], "required": True},
            {"name": "availability_nights", "label": "Available for Night Shifts?", "type": "select", "options": ["Yes", "No", "Sometimes"], "required": True},
            {"name": "availability_weekends", "label": "Available for Weekend Work?", "type": "select", "options": ["Yes", "No", "Sometimes"], "required": True},
            {"name": "hours_preferred", "label": "Preferred Hours per Week", "type": "text", "required": False},
            {"name": "driving_licence", "label": "Do you have a full UK driving licence?", "type": "select", "options": ["Yes", "No", "Provisional"], "required": True},
            {"name": "access_to_car", "label": "Do you have access to a car for work?", "type": "select", "options": ["Yes", "No"], "required": True},
            
            {"name": "section_health", "type": "section_header", "label": "Section 9: Health Declaration"},
            {"name": "health_condition", "label": "Do you have any health conditions that may affect your ability to carry out the role?", "type": "select", "options": ["No", "Yes"], "required": True},
            {"name": "health_details", "label": "If yes, please provide details (this information is confidential)", "type": "textarea", "required": False, "rows": 2},
            
            {"name": "section_references", "type": "section_header", "label": "Section 10: References"},
            {"name": "references_info", "type": "info_box", "content": "Please provide two professional references. One should be your most recent employer.", "variant": "info"},
            {"name": "references", "label": "References", "type": "repeatable", "item_label": "Reference", "required": True, "fields": [
                {"name": "name", "label": "Referee Name", "type": "text", "required": True},
                {"name": "organisation", "label": "Organisation", "type": "text", "required": True},
                {"name": "job_title", "label": "Job Title", "type": "text", "required": True},
                {"name": "email", "label": "Email", "type": "email", "required": True},
                {"name": "phone", "label": "Phone", "type": "text", "required": False},
                {"name": "relationship", "label": "Relationship to You", "type": "text", "required": True}
            ]},
            
            {"name": "section_statement", "type": "section_header", "label": "Section 11: Supporting Statement"},
            {"name": "supporting_statement", "label": "Why do you want to work in care and what makes you suitable for this role?", "type": "textarea", "required": True, "rows": 5},
            
            {"name": "section_declaration", "type": "section_header", "label": "Section 12: Declaration"},
            {"name": "declaration_accurate", "label": "I confirm that all information provided in this application is true and accurate to the best of my knowledge", "type": "checkbox", "required": True},
            {"name": "declaration_dbs", "label": "I understand that this role is subject to an enhanced DBS check and I consent to this being carried out", "type": "checkbox", "required": True},
            {"name": "declaration_references", "label": "I consent to references being obtained from the contacts I have provided", "type": "checkbox", "required": True}
        ]
    },
    
    # ==================== 2. INTERVIEW FORM (ROLE SPLIT) ====================
    {
        "name": "Interview Record Form",
        "description": "Structured interview assessment form with role-specific questions for HCA and Nurse candidates.",
        "category": "Interview",
        "section": "Interview",
        "visibility": "normal",
        "role_specific": None,
        "requires_employee_signature": True,
        "requires_admin_signature": True,
        "form_fields": [
            {"name": "section_details", "type": "section_header", "label": "Interview Details"},
            {"name": "interview_date", "label": "Interview Date", "type": "date", "required": True},
            {"name": "interview_type", "label": "Interview Type", "type": "select", "options": ["Face to Face", "Video Call", "Telephone"], "required": True},
            {"name": "interviewer", "label": "Interviewer Name", "type": "text", "required": True},
            {"name": "second_interviewer", "label": "Second Interviewer (if applicable)", "type": "text", "required": False},
            {"name": "position_applied", "label": "Position Applied For", "type": "text", "required": True},
            
            {"name": "section_common", "type": "section_header", "label": "Common Interview Questions"},
            {"name": "q1_motivation", "label": "Why do you want to work in care?", "type": "textarea", "required": True, "rows": 3},
            {"name": "q2_experience", "label": "Describe your relevant care experience", "type": "textarea", "required": True, "rows": 3},
            {"name": "q3_safeguarding", "label": "How would you handle a safeguarding concern?", "type": "textarea", "required": True, "rows": 3, "help_text": "Assess understanding of reporting procedures and duty of care"},
            {"name": "q4_challenge", "label": "Describe a challenging situation you faced and how you resolved it", "type": "textarea", "required": True, "rows": 3},
            {"name": "q5_teamwork", "label": "Give an example of when you worked effectively in a team", "type": "textarea", "required": True, "rows": 3},
            
            # HCA SPECIFIC QUESTIONS
            {"name": "section_hca", "type": "section_header", "label": "Healthcare Assistant Specific Questions", "role_restriction": "hca_only"},
            {"name": "hca_q1_personal_care", "label": "A service user refuses personal care. How do you handle this?", "type": "textarea", "required": False, "rows": 3, "role_restriction": "hca_only"},
            {"name": "hca_q2_dignity", "label": "How do you maintain dignity and respect when providing intimate care?", "type": "textarea", "required": False, "rows": 3, "role_restriction": "hca_only"},
            {"name": "hca_q3_aggression", "label": "How would you respond to aggressive behaviour from a service user?", "type": "textarea", "required": False, "rows": 3, "role_restriction": "hca_only"},
            {"name": "hca_q4_documentation", "label": "Why is accurate documentation important in care work?", "type": "textarea", "required": False, "rows": 3, "role_restriction": "hca_only"},
            
            # NURSE SPECIFIC QUESTIONS
            {"name": "section_nurse", "type": "section_header", "label": "Nursing Specific Questions", "role_restriction": "nurse_only"},
            {"name": "nurse_q1_emergency", "label": "Describe how you would handle a medical emergency (e.g., cardiac arrest, anaphylaxis)", "type": "textarea", "required": False, "rows": 3, "role_restriction": "nurse_only"},
            {"name": "nurse_q2_prioritisation", "label": "How do you prioritise patient care when managing multiple patients?", "type": "textarea", "required": False, "rows": 3, "role_restriction": "nurse_only"},
            {"name": "nurse_q3_clinical", "label": "Describe a time when you had to make a critical clinical decision", "type": "textarea", "required": False, "rows": 3, "role_restriction": "nurse_only"},
            {"name": "nurse_q4_medication", "label": "How do you ensure safe medication administration and what would you do if you discovered a medication error?", "type": "textarea", "required": False, "rows": 3, "role_restriction": "nurse_only"},
            {"name": "nurse_q5_stress", "label": "How do you manage stress and prevent burnout?", "type": "textarea", "required": False, "rows": 3, "role_restriction": "nurse_only"},
            
            {"name": "section_scoring", "type": "section_header", "label": "Assessment Scoring"},
            {"name": "score_communication", "label": "Communication Skills", "type": "rating", "max": 5, "required": True, "help_text": "1=Poor, 5=Excellent"},
            {"name": "score_experience", "label": "Relevant Experience", "type": "rating", "max": 5, "required": True},
            {"name": "score_values", "label": "Care Values & Empathy", "type": "rating", "max": 5, "required": True},
            {"name": "score_professionalism", "label": "Professionalism", "type": "rating", "max": 5, "required": True},
            {"name": "score_clinical", "label": "Clinical Competence (Nurses only)", "type": "rating", "max": 5, "required": False, "role_restriction": "nurse_only"},
            
            {"name": "section_outcome", "type": "section_header", "label": "Interview Outcome"},
            {"name": "overall_impression", "label": "Overall Assessment Notes", "type": "textarea", "required": True, "rows": 3},
            {"name": "concerns", "label": "Any Concerns or Issues Raised", "type": "textarea", "required": False, "rows": 2},
            {"name": "outcome", "label": "Outcome", "type": "outcome", "options": ["Hire - Proceed to Offer", "Hire with Conditions", "Second Interview Required", "Reserve List", "Reject"], "required": True},
            {"name": "conditions", "label": "Conditions (if applicable)", "type": "textarea", "required": False},
            
            {"name": "candidate_confirmation", "label": "I confirm this is an accurate record of my interview", "type": "checkbox", "required": True}
        ]
    },
    
    # ==================== 3. RECRUITMENT CHECKLIST ====================
    {
        "name": "Recruitment Compliance Checklist",
        "description": "CQC-compliant safer recruitment checklist to verify all pre-employment checks are complete.",
        "category": "Compliance",
        "section": "Compliance",
        "visibility": "normal",
        "role_specific": None,
        "requires_employee_signature": False,
        "requires_admin_signature": True,
        "form_fields": [
            {"name": "section_identity", "type": "section_header", "label": "Identity Verification"},
            {"name": "identity_verified", "label": "Photo ID verified (passport, driving licence, or national ID)", "type": "checkbox", "required": True},
            {"name": "identity_type", "label": "Type of ID Verified", "type": "select", "options": ["UK Passport", "EU Passport", "Driving Licence", "National ID Card", "BRP Card", "Other"], "required": True},
            {"name": "photo_present", "label": "Photograph matches the individual", "type": "checkbox", "required": True},
            {"name": "original_id_seen", "label": "Original document seen", "type": "checkbox", "required": True},
            {"name": "id_copy_filed", "label": "Copy taken and filed", "type": "checkbox", "required": True},
            
            {"name": "section_rtw", "type": "section_header", "label": "Right to Work"},
            {"name": "rtw_checked", "label": "Right to work in UK verified", "type": "checkbox", "required": True},
            {"name": "rtw_method", "label": "RTW Check Method", "type": "select", "options": ["British Passport", "EU Settlement Scheme", "BRP Card", "Share Code Online Check", "Other"], "required": True},
            {"name": "rtw_date", "label": "RTW Check Date", "type": "date", "required": True},
            {"name": "rtw_expiry", "label": "RTW Expiry Date (if applicable)", "type": "date", "required": False},
            
            {"name": "section_dbs", "type": "section_header", "label": "DBS Check"},
            {"name": "dbs_checked", "label": "DBS certificate checked", "type": "checkbox", "required": True},
            {"name": "dbs_type", "label": "DBS Type", "type": "select", "options": ["Enhanced with Barred List", "Enhanced", "Standard", "Basic", "Update Service"], "required": True},
            {"name": "dbs_number", "label": "DBS Certificate Number", "type": "text", "required": True},
            {"name": "dbs_date", "label": "DBS Issue Date", "type": "date", "required": True},
            {"name": "dbs_clear", "label": "DBS is clear (no relevant convictions)", "type": "checkbox", "required": True},
            {"name": "risk_assessment_done", "label": "Risk assessment completed (if convictions present)", "type": "checkbox", "required": False},
            
            {"name": "section_employment", "type": "section_header", "label": "Employment History"},
            {"name": "employment_verified", "label": "Full employment history obtained", "type": "checkbox", "required": True},
            {"name": "gaps_explained", "label": "All gaps in employment explained", "type": "checkbox", "required": True},
            {"name": "gaps_notes", "label": "Notes on employment gaps", "type": "textarea", "required": False},
            
            {"name": "section_references", "type": "section_header", "label": "References"},
            {"name": "ref1_received", "label": "Reference 1 received and satisfactory", "type": "checkbox", "required": True},
            {"name": "ref2_received", "label": "Reference 2 received and satisfactory", "type": "checkbox", "required": True},
            {"name": "references_verified", "label": "References verified as genuine", "type": "checkbox", "required": True},
            
            {"name": "section_qualifications", "type": "section_header", "label": "Qualifications"},
            {"name": "qualifications_verified", "label": "Relevant qualifications verified", "type": "checkbox", "required": True},
            {"name": "nmc_verified", "label": "NMC registration verified (Nurses only)", "type": "checkbox", "required": False, "role_restriction": "nurse_only"},
            
            {"name": "section_health", "type": "section_header", "label": "Health Declaration"},
            {"name": "health_form_completed", "label": "Health screening form completed", "type": "checkbox", "required": True},
            {"name": "fit_for_role", "label": "Declared fit for role", "type": "checkbox", "required": True},
            
            {"name": "section_final", "type": "section_header", "label": "Final Sign-Off"},
            {"name": "all_checks_complete", "label": "All safer recruitment checks completed satisfactorily", "type": "checkbox", "required": True},
            {"name": "file_complete", "label": "Personnel file complete and ready for audit", "type": "checkbox", "required": True},
            {"name": "notes", "label": "Additional Notes", "type": "textarea", "required": False},
            {"name": "completed_by", "label": "Checklist Completed By", "type": "text", "required": True},
            {"name": "completion_date", "label": "Completion Date", "type": "date", "required": True}
        ]
    },
    
    # ==================== 4. HEALTH SCREENING FORM (RESTRICTED) ====================
    {
        "name": "Health Screening Questionnaire",
        "description": "Confidential health declaration and screening form. Restricted access - HR and authorised personnel only.",
        "category": "Health",
        "section": "Health",
        "visibility": "restricted",
        "role_specific": None,
        "requires_employee_signature": True,
        "requires_admin_signature": True,
        "form_fields": [
            {"name": "confidential_notice", "type": "info_box", "content": "CONFIDENTIAL: This form contains sensitive health information and should only be accessed by authorised HR personnel. Information will be used solely for the purpose of ensuring fitness for work and making reasonable adjustments.", "variant": "warning"},
            
            {"name": "section_personal", "type": "section_header", "label": "Personal Details"},
            {"name": "job_title", "label": "Job Title Applied For / Current Role", "type": "text", "required": True},
            {"name": "department", "label": "Department/Branch", "type": "text", "required": True},
            {"name": "gp_name", "label": "GP Name", "type": "text", "required": True},
            {"name": "gp_address", "label": "GP Address", "type": "textarea", "required": True, "rows": 2},
            
            {"name": "section_job_risks", "type": "section_header", "label": "Job Requirements"},
            {"name": "job_risks_info", "type": "info_box", "content": "Please indicate if any of the following job requirements apply to your role:", "variant": "info"},
            {"name": "manual_handling", "label": "Manual handling/lifting required", "type": "checkbox", "required": False},
            {"name": "night_shifts", "label": "Night shift work required", "type": "checkbox", "required": False},
            {"name": "lone_working", "label": "Lone working required", "type": "checkbox", "required": False},
            {"name": "driving_required", "label": "Driving as part of duties", "type": "checkbox", "required": False},
            {"name": "physical_demands", "label": "Other physical demands (bending, kneeling, standing)", "type": "checkbox", "required": False},
            
            {"name": "section_health", "type": "section_header", "label": "Health History"},
            {"name": "health_intro", "type": "info_box", "content": "Please answer the following questions honestly. This information is confidential and will only be used to ensure your wellbeing at work.", "variant": "info"},
            {"name": "back_problems", "label": "Do you have or have you ever had back problems or injuries?", "type": "select", "options": ["No", "Yes - managed", "Yes - ongoing"], "required": True},
            {"name": "joint_problems", "label": "Do you have any joint or musculoskeletal conditions?", "type": "select", "options": ["No", "Yes - managed", "Yes - ongoing"], "required": True},
            {"name": "heart_conditions", "label": "Do you have any heart or circulatory conditions?", "type": "select", "options": ["No", "Yes - managed", "Yes - ongoing"], "required": True},
            {"name": "respiratory", "label": "Do you have any respiratory conditions (e.g., asthma)?", "type": "select", "options": ["No", "Yes - managed", "Yes - ongoing"], "required": True},
            {"name": "diabetes", "label": "Do you have diabetes?", "type": "select", "options": ["No", "Yes - managed", "Yes - ongoing"], "required": True},
            {"name": "epilepsy", "label": "Do you have epilepsy or have you ever had seizures?", "type": "select", "options": ["No", "Yes - managed", "Yes - ongoing"], "required": True},
            {"name": "mental_health", "label": "Have you experienced mental health conditions (e.g., anxiety, depression)?", "type": "select", "options": ["No", "Yes - managed", "Yes - ongoing"], "required": True},
            {"name": "other_conditions", "label": "Any other health conditions not listed above", "type": "textarea", "required": False, "rows": 2},
            
            {"name": "section_medication", "type": "section_header", "label": "Medication"},
            {"name": "takes_medication", "label": "Are you currently taking any regular medication?", "type": "select", "options": ["No", "Yes"], "required": True},
            {"name": "medication_details", "label": "If yes, please list medications and dosages", "type": "textarea", "required": False, "rows": 2},
            {"name": "medication_affects_work", "label": "Could any medication affect your ability to work safely?", "type": "select", "options": ["No", "Yes", "Unsure"], "required": True},
            
            {"name": "section_allergies", "type": "section_header", "label": "Allergies"},
            {"name": "has_allergies", "label": "Do you have any allergies?", "type": "select", "options": ["No", "Yes"], "required": True},
            {"name": "allergy_details", "label": "If yes, please provide details", "type": "textarea", "required": False},
            
            {"name": "section_absence", "type": "section_header", "label": "Absence History"},
            {"name": "absence_days", "label": "Approximate days absent from work due to illness in the last 12 months", "type": "number", "required": True},
            {"name": "absence_reason", "label": "Main reasons for absence (if any)", "type": "textarea", "required": False},
            
            {"name": "section_disability", "type": "section_header", "label": "Disability & Adjustments"},
            {"name": "has_disability", "label": "Do you consider yourself to have a disability under the Equality Act 2010?", "type": "select", "options": ["No", "Yes", "Prefer not to say"], "required": True},
            {"name": "disability_details", "label": "If yes, please provide details", "type": "textarea", "required": False},
            {"name": "adjustments_needed", "label": "Do you require any reasonable adjustments to perform your role?", "type": "select", "options": ["No", "Yes"], "required": True},
            {"name": "adjustments_details", "label": "If yes, please describe adjustments needed", "type": "textarea", "required": False},
            
            {"name": "section_declaration", "type": "section_header", "label": "Declaration"},
            {"name": "declaration_accurate", "label": "I declare that the information I have provided is true and complete to the best of my knowledge", "type": "checkbox", "required": True},
            {"name": "declaration_consent", "label": "I consent to this information being used to assess my fitness for work and for occupational health purposes", "type": "checkbox", "required": True},
            {"name": "declaration_notify", "label": "I agree to notify my employer of any changes to my health that may affect my ability to work safely", "type": "checkbox", "required": True},
            
            {"name": "section_employer", "type": "section_header", "label": "Employer Assessment (HR Use Only)"},
            {"name": "hr_comments", "label": "HR/Occupational Health Comments", "type": "textarea", "required": False},
            {"name": "fit_outcome", "label": "Fitness for Work Outcome", "type": "outcome", "options": ["Fit", "Fit with Adjustments", "OH Referral Required", "Not Fit - Medical Grounds"], "required": True},
            {"name": "adjustments_agreed", "label": "Adjustments Agreed", "type": "textarea", "required": False},
            {"name": "review_date", "label": "Review Date (if applicable)", "type": "date", "required": False}
        ]
    },
    
    # ==================== 5. INDUCTION + SHADOWING + COMPETENCY ====================
    {
        "name": "Induction & Competency Assessment",
        "description": "Comprehensive induction checklist with shadowing record and competency sign-off.",
        "category": "Induction",
        "section": "Induction",
        "visibility": "normal",
        "role_specific": None,
        "requires_employee_signature": True,
        "requires_admin_signature": True,
        "form_fields": [
            {"name": "section_details", "type": "section_header", "label": "Induction Details"},
            {"name": "start_date", "label": "Employment Start Date", "type": "date", "required": True},
            {"name": "induction_date", "label": "Induction Completed Date", "type": "date", "required": True},
            {"name": "supervisor", "label": "Induction Supervisor/Trainer", "type": "text", "required": True},
            {"name": "assignment", "label": "Current Assignment/Placement", "type": "text", "required": True},
            
            {"name": "section_company", "type": "section_header", "label": "Company Induction"},
            {"name": "company_intro", "label": "Company introduction and values", "type": "checkbox", "required": True},
            {"name": "org_structure", "label": "Organisation structure and key contacts", "type": "checkbox", "required": True},
            {"name": "reporting_lines", "label": "Reporting lines and supervision arrangements", "type": "checkbox", "required": True},
            {"name": "handbook_issued", "label": "Employee handbook issued", "type": "checkbox", "required": True},
            {"name": "uniform_issued", "label": "Uniform and PPE issued", "type": "checkbox", "required": True},
            {"name": "id_badge_issued", "label": "ID badge issued", "type": "checkbox", "required": True},
            
            {"name": "section_policies", "type": "section_header", "label": "Key Policies"},
            {"name": "safeguarding_policy", "label": "Safeguarding policy explained", "type": "checkbox", "required": True},
            {"name": "whistleblowing", "label": "Whistleblowing policy explained", "type": "checkbox", "required": True},
            {"name": "confidentiality", "label": "Confidentiality and data protection explained", "type": "checkbox", "required": True},
            {"name": "health_safety", "label": "Health and safety policy explained", "type": "checkbox", "required": True},
            {"name": "lone_working", "label": "Lone working policy explained", "type": "checkbox", "required": True},
            {"name": "equality", "label": "Equality and diversity policy explained", "type": "checkbox", "required": True},
            {"name": "complaints", "label": "Complaints and grievance procedures explained", "type": "checkbox", "required": True},
            
            {"name": "section_mandatory", "type": "section_header", "label": "Mandatory Training"},
            {"name": "safeguarding_training", "label": "Safeguarding training completed", "type": "checkbox", "required": True},
            {"name": "infection_control", "label": "Infection control training completed", "type": "checkbox", "required": True},
            {"name": "manual_handling", "label": "Manual handling training completed", "type": "checkbox", "required": True},
            {"name": "fire_safety", "label": "Fire safety training completed", "type": "checkbox", "required": True},
            {"name": "medication_training", "label": "Medication awareness training completed", "type": "checkbox", "required": True},
            {"name": "first_aid_training", "label": "Basic first aid/BLS training completed", "type": "checkbox", "required": True},
            
            {"name": "section_shadowing", "type": "section_header", "label": "Shadowing Record"},
            {"name": "shadowing_dates", "label": "Shadowing Dates", "type": "text", "required": True, "help_text": "Enter dates of all shadowing shifts"},
            {"name": "shadowing_hours", "label": "Total Shadowing Hours Completed", "type": "number", "required": True},
            {"name": "shadowing_locations", "label": "Locations/Services Shadowed", "type": "textarea", "required": True, "rows": 2},
            {"name": "shadowed_with", "label": "Staff Members Shadowed With", "type": "textarea", "required": True, "rows": 2},
            
            {"name": "section_observed", "type": "section_header", "label": "Activities Observed During Shadowing"},
            {"name": "obs_personal_care", "label": "Personal care delivery", "type": "checkbox", "required": True},
            {"name": "obs_medication", "label": "Medication administration", "type": "checkbox", "required": True},
            {"name": "obs_manual_handling", "label": "Manual handling techniques", "type": "checkbox", "required": True},
            {"name": "obs_documentation", "label": "Care documentation and record keeping", "type": "checkbox", "required": True},
            {"name": "obs_communication", "label": "Communication with service users", "type": "checkbox", "required": True},
            {"name": "obs_emergency", "label": "Emergency procedures", "type": "checkbox", "required": False},
            {"name": "shadowing_notes", "label": "Shadowing Notes/Observations", "type": "textarea", "required": False, "rows": 3},
            
            {"name": "section_competency", "type": "section_header", "label": "Competency Assessment"},
            {"name": "competency_info", "type": "info_box", "content": "Assess the employee's competency in each area based on observed practice during shadowing and induction.", "variant": "info"},
            {"name": "comp_personal_care", "label": "Personal Care Competency", "type": "competency", "required": True},
            {"name": "comp_communication", "label": "Communication Skills", "type": "competency", "required": True},
            {"name": "comp_manual_handling", "label": "Manual Handling Competency", "type": "competency", "required": True},
            {"name": "comp_documentation", "label": "Documentation Competency", "type": "competency", "required": True},
            {"name": "comp_safeguarding", "label": "Safeguarding Awareness", "type": "competency", "required": True},
            {"name": "comp_infection_control", "label": "Infection Control", "type": "competency", "required": True},
            
            {"name": "section_outcome", "type": "section_header", "label": "Final Outcome"},
            {"name": "supervisor_feedback", "label": "Supervisor Feedback & Recommendations", "type": "textarea", "required": True, "rows": 3},
            {"name": "areas_development", "label": "Areas for Development", "type": "textarea", "required": False, "rows": 2},
            {"name": "final_decision", "label": "Final Decision", "type": "outcome", "options": ["Fit to Work Independently", "Requires Extended Supervision", "Further Training Required", "Not Fit for Role"], "required": True},
            {"name": "supervision_period", "label": "Supervision Period (weeks)", "type": "number", "required": False, "help_text": "If extended supervision required"},
            {"name": "next_review_date", "label": "Next Review Date", "type": "date", "required": False},
            
            {"name": "section_declaration", "type": "section_header", "label": "Sign-Off"},
            {"name": "employee_understanding", "label": "I confirm I have completed all induction training and understand my responsibilities", "type": "checkbox", "required": True},
            {"name": "employee_questions", "label": "All my questions have been answered satisfactorily", "type": "checkbox", "required": True}
        ]
    },
    
    # ==================== 6. CONTRACT ACKNOWLEDGEMENT ====================
    {
        "name": "Contract Acknowledgement Form",
        "description": "Confirmation of receipt and understanding of employment contract and terms.",
        "category": "Contract",
        "section": "Contract",
        "visibility": "normal",
        "role_specific": None,
        "requires_employee_signature": True,
        "requires_admin_signature": True,
        "form_fields": [
            {"name": "section_contract", "type": "section_header", "label": "Contract Details"},
            {"name": "contract_date", "label": "Contract Issued Date", "type": "date", "required": True},
            {"name": "job_title", "label": "Job Title", "type": "text", "required": True},
            {"name": "contract_type", "label": "Contract Type", "type": "select", "options": ["Permanent", "Fixed Term", "Bank/Zero Hours", "Temporary"], "required": True},
            {"name": "hours_contracted", "label": "Contracted Hours per Week", "type": "text", "required": True},
            {"name": "hourly_rate", "label": "Hourly Rate", "type": "text", "required": True},
            {"name": "start_date", "label": "Start Date", "type": "date", "required": True},
            {"name": "probation_period", "label": "Probation Period", "type": "text", "required": True, "help_text": "e.g., 3 months, 6 months"},
            {"name": "notice_period", "label": "Notice Period", "type": "text", "required": True},
            
            {"name": "section_acknowledgement", "type": "section_header", "label": "Acknowledgement"},
            {"name": "contract_received", "label": "I confirm I have received a copy of my contract of employment", "type": "checkbox", "required": True},
            {"name": "contract_read", "label": "I confirm I have read and understood the terms of my contract", "type": "checkbox", "required": True},
            {"name": "handbook_received", "label": "I confirm I have received a copy of the Employee Handbook", "type": "checkbox", "required": True},
            {"name": "notice_understood", "label": "I understand the notice period and termination conditions", "type": "checkbox", "required": True},
            {"name": "probation_understood", "label": "I understand the probation period and review process", "type": "checkbox", "required": True},
            {"name": "confidentiality_agreed", "label": "I agree to maintain confidentiality as outlined in my contract", "type": "checkbox", "required": True},
            
            {"name": "section_questions", "type": "section_header", "label": "Questions"},
            {"name": "questions_raised", "label": "Any questions or clarifications required?", "type": "textarea", "required": False, "rows": 3},
            
            {"name": "section_declaration", "type": "section_header", "label": "Declaration"},
            {"name": "acceptance_declaration", "label": "I acknowledge receipt and acceptance of my contract of employment and agree to abide by the terms and conditions set out therein", "type": "checkbox", "required": True}
        ]
    },
    
    # ==================== 7. PERSONAL INFORMATION FORM ====================
    {
        "name": "Personal Information Form",
        "description": "Collection of essential personal information and emergency contacts for HR records.",
        "category": "Personal",
        "section": "Personal",
        "visibility": "normal",
        "role_specific": None,
        "requires_employee_signature": True,
        "requires_admin_signature": False,
        "form_fields": [
            {"name": "section_personal", "type": "section_header", "label": "Personal Details"},
            {"name": "full_name", "label": "Full Legal Name", "type": "text", "required": True},
            {"name": "preferred_name", "label": "Preferred Name (if different)", "type": "text", "required": False},
            {"name": "date_of_birth", "label": "Date of Birth", "type": "date", "required": True},
            {"name": "national_insurance", "label": "National Insurance Number", "type": "text", "required": True},
            
            {"name": "section_address", "type": "section_header", "label": "Address"},
            {"name": "address_line1", "label": "Address Line 1", "type": "text", "required": True},
            {"name": "address_line2", "label": "Address Line 2", "type": "text", "required": False},
            {"name": "city", "label": "City/Town", "type": "text", "required": True},
            {"name": "county", "label": "County", "type": "text", "required": False},
            {"name": "postcode", "label": "Postcode", "type": "text", "required": True},
            
            {"name": "section_contact", "type": "section_header", "label": "Contact Details"},
            {"name": "phone_mobile", "label": "Mobile Number", "type": "text", "required": True},
            {"name": "phone_home", "label": "Home Phone (if different)", "type": "text", "required": False},
            {"name": "email_personal", "label": "Personal Email Address", "type": "email", "required": True},
            
            {"name": "section_emergency", "type": "section_header", "label": "Emergency Contact"},
            {"name": "emergency_name", "label": "Emergency Contact Name", "type": "text", "required": True},
            {"name": "emergency_relationship", "label": "Relationship", "type": "text", "required": True},
            {"name": "emergency_phone", "label": "Emergency Contact Phone", "type": "text", "required": True},
            {"name": "emergency_address", "label": "Emergency Contact Address", "type": "textarea", "required": False, "rows": 2},
            
            {"name": "section_bank", "type": "section_header", "label": "Bank Details (for Salary Payment)"},
            {"name": "bank_name", "label": "Bank Name", "type": "text", "required": True},
            {"name": "account_name", "label": "Account Holder Name", "type": "text", "required": True},
            {"name": "sort_code", "label": "Sort Code", "type": "text", "required": True},
            {"name": "account_number", "label": "Account Number", "type": "text", "required": True},
            
            {"name": "section_driving", "type": "section_header", "label": "Driving Information"},
            {"name": "has_licence", "label": "Do you have a UK driving licence?", "type": "select", "options": ["Yes - Full", "Yes - Provisional", "No"], "required": True},
            {"name": "licence_number", "label": "Driving Licence Number (if applicable)", "type": "text", "required": False},
            {"name": "licence_expiry", "label": "Licence Expiry Date", "type": "date", "required": False},
            {"name": "own_vehicle", "label": "Do you have access to a vehicle for work?", "type": "select", "options": ["Yes", "No"], "required": True},
            
            {"name": "section_declaration", "type": "section_header", "label": "Declaration"},
            {"name": "info_accurate", "label": "I confirm all information provided is accurate", "type": "checkbox", "required": True},
            {"name": "notify_changes", "label": "I agree to notify HR of any changes to my personal details", "type": "checkbox", "required": True}
        ]
    },
    
    # ==================== 8. EQUAL OPPORTUNITIES FORM (CONFIDENTIAL) ====================
    {
        "name": "Equal Opportunities Monitoring Form",
        "description": "Confidential equality monitoring data. Used for statistical purposes only - not used in hiring decisions.",
        "category": "Equal Opportunities",
        "section": "Confidential",
        "visibility": "confidential",
        "role_specific": None,
        "requires_employee_signature": True,
        "requires_admin_signature": False,
        "form_fields": [
            {"name": "confidential_notice", "type": "info_box", "content": "CONFIDENTIAL: This information is collected for equal opportunities monitoring purposes only. It will be kept separately from your application/personnel file and will NOT be used in hiring decisions. All fields are optional.", "variant": "info"},
            
            {"name": "section_equality", "type": "section_header", "label": "Equality Monitoring (All Optional)"},
            {"name": "gender", "label": "Gender", "type": "select", "options": ["Male", "Female", "Non-binary", "Prefer to self-describe", "Prefer not to say"], "required": False},
            {"name": "gender_other", "label": "If you prefer to self-describe, please specify", "type": "text", "required": False},
            
            {"name": "ethnicity", "label": "Ethnic Group", "type": "select", "options": [
                "White - British", "White - Irish", "White - Other", 
                "Mixed - White and Black Caribbean", "Mixed - White and Black African", "Mixed - White and Asian", "Mixed - Other",
                "Asian or Asian British - Indian", "Asian or Asian British - Pakistani", "Asian or Asian British - Bangladeshi", "Asian or Asian British - Chinese", "Asian or Asian British - Other",
                "Black or Black British - Caribbean", "Black or Black British - African", "Black or Black British - Other",
                "Other ethnic group", "Prefer not to say"
            ], "required": False},
            
            {"name": "religion", "label": "Religion or Belief", "type": "select", "options": [
                "No religion", "Christian", "Buddhist", "Hindu", "Jewish", "Muslim", "Sikh", "Other", "Prefer not to say"
            ], "required": False},
            
            {"name": "sexual_orientation", "label": "Sexual Orientation", "type": "select", "options": [
                "Heterosexual/Straight", "Gay/Lesbian", "Bisexual", "Other", "Prefer not to say"
            ], "required": False},
            
            {"name": "disability", "label": "Do you consider yourself to have a disability?", "type": "select", "options": ["No", "Yes", "Prefer not to say"], "required": False},
            
            {"name": "age_group", "label": "Age Group", "type": "select", "options": [
                "16-24", "25-34", "35-44", "45-54", "55-64", "65+", "Prefer not to say"
            ], "required": False},
            
            {"name": "section_declaration", "type": "section_header", "label": "Declaration"},
            {"name": "consent_monitoring", "label": "I understand this information is used for equality monitoring purposes only", "type": "checkbox", "required": True}
        ]
    },
    
    # ==================== 9. SUPERVISION RECORD ====================
    {
        "name": "Supervision Record",
        "description": "One-to-one supervision meeting record for ongoing staff support and development.",
        "category": "Supervision",
        "section": "Supervision",
        "visibility": "normal",
        "role_specific": None,
        "requires_employee_signature": True,
        "requires_admin_signature": True,
        "form_fields": [
            {"name": "section_details", "type": "section_header", "label": "Supervision Details"},
            {"name": "supervision_date", "label": "Supervision Date", "type": "date", "required": True},
            {"name": "supervisor", "label": "Supervisor Name", "type": "text", "required": True},
            {"name": "supervision_type", "label": "Supervision Type", "type": "select", "options": ["Probation Review", "Regular Supervision", "Return to Work", "Performance Review", "Ad-hoc/Unscheduled"], "required": True},
            {"name": "location", "label": "Location", "type": "text", "required": True},
            
            {"name": "section_review", "type": "section_header", "label": "Review"},
            {"name": "previous_actions", "label": "Review of Previous Actions/Objectives", "type": "textarea", "required": True, "rows": 3},
            {"name": "workload_discussion", "label": "Workload and Caseload Discussion", "type": "textarea", "required": True, "rows": 3},
            {"name": "performance_feedback", "label": "Performance Feedback", "type": "textarea", "required": True, "rows": 3},
            
            {"name": "section_wellbeing", "type": "section_header", "label": "Wellbeing"},
            {"name": "wellbeing_check", "label": "Wellbeing Discussion - How are you feeling in your role?", "type": "textarea", "required": True, "rows": 3},
            {"name": "concerns_raised", "label": "Any Concerns Raised", "type": "textarea", "required": False, "rows": 2},
            {"name": "support_needed", "label": "Support Needed", "type": "textarea", "required": False, "rows": 2},
            
            {"name": "section_development", "type": "section_header", "label": "Training & Development"},
            {"name": "training_completed", "label": "Training Completed Since Last Supervision", "type": "textarea", "required": False, "rows": 2},
            {"name": "training_needs", "label": "Training/Development Needs Identified", "type": "textarea", "required": False, "rows": 2},
            
            {"name": "section_objectives", "type": "section_header", "label": "Objectives"},
            {"name": "new_objectives", "label": "Objectives for Next Period", "type": "textarea", "required": True, "rows": 3},
            {"name": "next_supervision", "label": "Next Supervision Date", "type": "date", "required": True},
            
            {"name": "section_sign", "type": "section_header", "label": "Sign-Off"},
            {"name": "employee_comments", "label": "Employee Comments", "type": "textarea", "required": False, "rows": 2},
            {"name": "accurate_record", "label": "I confirm this is an accurate record of our supervision meeting", "type": "checkbox", "required": True}
        ]
    },
    
    # ==================== 10. APPRAISAL FORM ====================
    {
        "name": "Annual Appraisal Form",
        "description": "Annual performance appraisal and development review.",
        "category": "Supervision",
        "section": "Supervision",
        "visibility": "normal",
        "role_specific": None,
        "requires_employee_signature": True,
        "requires_admin_signature": True,
        "form_fields": [
            {"name": "section_details", "type": "section_header", "label": "Appraisal Details"},
            {"name": "appraisal_date", "label": "Appraisal Date", "type": "date", "required": True},
            {"name": "review_period", "label": "Review Period (e.g., Jan 2024 - Dec 2024)", "type": "text", "required": True},
            {"name": "appraiser", "label": "Appraiser Name", "type": "text", "required": True},
            
            {"name": "section_achievements", "type": "section_header", "label": "Review of Period"},
            {"name": "achievements", "label": "Key Achievements This Period", "type": "textarea", "required": True, "rows": 4},
            {"name": "challenges", "label": "Challenges Faced and How Overcome", "type": "textarea", "required": True, "rows": 3},
            {"name": "objectives_achieved", "label": "Previous Objectives - Achievement Status", "type": "textarea", "required": True, "rows": 3},
            
            {"name": "section_performance", "type": "section_header", "label": "Performance Assessment"},
            {"name": "rating_quality", "label": "Quality of Care Delivery", "type": "rating", "max": 5, "required": True},
            {"name": "rating_reliability", "label": "Reliability & Punctuality", "type": "rating", "max": 5, "required": True},
            {"name": "rating_teamwork", "label": "Teamwork & Collaboration", "type": "rating", "max": 5, "required": True},
            {"name": "rating_communication", "label": "Communication Skills", "type": "rating", "max": 5, "required": True},
            {"name": "rating_initiative", "label": "Initiative & Problem Solving", "type": "rating", "max": 5, "required": True},
            {"name": "rating_compliance", "label": "Compliance & Documentation", "type": "rating", "max": 5, "required": True},
            
            {"name": "overall_rating", "label": "Overall Performance Rating", "type": "select", "options": ["Exceptional", "Exceeds Expectations", "Meets Expectations", "Partially Meets Expectations", "Does Not Meet Expectations"], "required": True},
            
            {"name": "section_strengths", "type": "section_header", "label": "Strengths & Development"},
            {"name": "strengths", "label": "Key Strengths Identified", "type": "textarea", "required": True, "rows": 3},
            {"name": "areas_development", "label": "Areas for Development", "type": "textarea", "required": True, "rows": 3},
            {"name": "training_completed", "label": "Training Completed This Period", "type": "textarea", "required": False, "rows": 2},
            {"name": "training_plan", "label": "Training Plan for Next Period", "type": "textarea", "required": False, "rows": 2},
            
            {"name": "section_career", "type": "section_header", "label": "Career Development"},
            {"name": "career_aspirations", "label": "Career Aspirations & Goals", "type": "textarea", "required": False, "rows": 3},
            {"name": "progression_opportunities", "label": "Progression Opportunities Discussed", "type": "textarea", "required": False, "rows": 2},
            
            {"name": "section_objectives", "type": "section_header", "label": "Objectives for Next Period"},
            {"name": "new_objectives", "label": "SMART Objectives for Next Review Period", "type": "textarea", "required": True, "rows": 4},
            {"name": "next_appraisal", "label": "Next Appraisal Date", "type": "date", "required": True},
            
            {"name": "section_sign", "type": "section_header", "label": "Sign-Off"},
            {"name": "employee_comments", "label": "Employee Comments", "type": "textarea", "required": False, "rows": 3},
            {"name": "employee_confirmation", "label": "I confirm this is an accurate record of my appraisal", "type": "checkbox", "required": True}
        ]
    },
    
    # ==================== 11. REFERENCE CHECK FORM ====================
    {
        "name": "Reference Request & Verification Form",
        "description": "Employment reference request form with verification checklist.",
        "category": "References",
        "section": "Recruitment",
        "visibility": "normal",
        "role_specific": None,
        "requires_employee_signature": False,
        "requires_admin_signature": True,
        "form_fields": [
            {"name": "section_ref_details", "type": "section_header", "label": "Reference Details"},
            {"name": "reference_number", "label": "Reference Number", "type": "select", "options": ["Reference 1 (Most Recent Employer)", "Reference 2", "Reference 3", "Character Reference"], "required": True},
            
            {"name": "section_referee", "type": "section_header", "label": "Referee Information"},
            {"name": "referee_name", "label": "Referee Name", "type": "text", "required": True},
            {"name": "referee_job_title", "label": "Referee Job Title", "type": "text", "required": True},
            {"name": "organisation", "label": "Organisation", "type": "text", "required": True},
            {"name": "referee_email", "label": "Referee Email", "type": "email", "required": True},
            {"name": "referee_phone", "label": "Referee Phone", "type": "text", "required": False},
            {"name": "relationship", "label": "Relationship to Candidate", "type": "text", "required": True},
            
            {"name": "section_employment", "type": "section_header", "label": "Employment Details to Verify"},
            {"name": "job_title_claimed", "label": "Job Title Claimed", "type": "text", "required": True},
            {"name": "dates_employed", "label": "Dates of Employment", "type": "text", "required": True},
            
            {"name": "section_request", "type": "section_header", "label": "Reference Request"},
            {"name": "request_sent_date", "label": "Reference Request Sent Date", "type": "date", "required": True},
            {"name": "request_method", "label": "Request Method", "type": "select", "options": ["Email", "Phone", "Post", "Online Form"], "required": True},
            {"name": "reminder_sent", "label": "Reminder Sent?", "type": "select", "options": ["Not needed", "Yes - 1 reminder", "Yes - 2+ reminders"], "required": False},
            
            {"name": "section_response", "type": "section_header", "label": "Reference Response"},
            {"name": "reference_received", "label": "Reference Received", "type": "select", "options": ["Yes", "No - Awaiting", "No - Declined", "No - Unable to contact"], "required": True},
            {"name": "received_date", "label": "Date Received", "type": "date", "required": False},
            
            {"name": "section_verification", "type": "section_header", "label": "Verification Checklist"},
            {"name": "dates_confirmed", "label": "Employment dates confirmed as accurate", "type": "checkbox", "required": False},
            {"name": "role_confirmed", "label": "Job role confirmed as accurate", "type": "checkbox", "required": False},
            {"name": "performance_satisfactory", "label": "Performance was satisfactory", "type": "checkbox", "required": False},
            {"name": "would_reemploy", "label": "Referee would re-employ", "type": "checkbox", "required": False},
            {"name": "no_concerns", "label": "No safeguarding or conduct concerns raised", "type": "checkbox", "required": False},
            
            {"name": "section_outcome", "type": "section_header", "label": "Outcome"},
            {"name": "reference_satisfactory", "label": "Reference Outcome", "type": "select", "options": ["Satisfactory", "Satisfactory with Notes", "Unsatisfactory", "Further Investigation Required"], "required": True},
            {"name": "concerns_identified", "label": "Concerns or Issues Identified", "type": "textarea", "required": False, "rows": 2},
            {"name": "follow_up_needed", "label": "Follow-up Action Required?", "type": "select", "options": ["No", "Yes"], "required": True},
            {"name": "follow_up_notes", "label": "Follow-up Notes", "type": "textarea", "required": False},
            
            {"name": "verified_by", "label": "Verified By", "type": "text", "required": True},
            {"name": "verification_date", "label": "Verification Date", "type": "date", "required": True}
        ]
    },
    
    # ==================== 12. DBS REVIEW FORM ====================
    {
        "name": "DBS Review & Risk Assessment",
        "description": "DBS certificate review form with risk assessment for any disclosed information.",
        "category": "DBS",
        "section": "Compliance",
        "visibility": "normal",
        "role_specific": None,
        "requires_employee_signature": True,
        "requires_admin_signature": True,
        "form_fields": [
            {"name": "section_dbs_details", "type": "section_header", "label": "DBS Certificate Details"},
            {"name": "dbs_type", "label": "DBS Check Type", "type": "select", "options": ["Enhanced with Adults Barred List", "Enhanced with Adults & Children Barred Lists", "Enhanced", "Standard", "Basic"], "required": True},
            {"name": "dbs_number", "label": "DBS Certificate Number", "type": "text", "required": True},
            {"name": "dbs_issue_date", "label": "DBS Issue Date", "type": "date", "required": True},
            {"name": "update_service", "label": "Registered with DBS Update Service?", "type": "select", "options": ["Yes", "No"], "required": True},
            {"name": "update_service_check_date", "label": "Update Service Check Date (if applicable)", "type": "date", "required": False},
            
            {"name": "section_verification", "type": "section_header", "label": "Verification"},
            {"name": "original_seen", "label": "Original certificate seen", "type": "checkbox", "required": True},
            {"name": "copy_taken", "label": "Copy taken and filed", "type": "checkbox", "required": True},
            {"name": "name_matches", "label": "Name matches other ID documents", "type": "checkbox", "required": True},
            {"name": "dob_matches", "label": "Date of birth matches records", "type": "checkbox", "required": True},
            
            {"name": "section_content", "type": "section_header", "label": "DBS Content"},
            {"name": "dbs_clear", "label": "Is the DBS clear (no convictions, cautions, or other information)?", "type": "select", "options": ["Yes - Clear", "No - Contains Information"], "required": True},
            {"name": "barred_list_result", "label": "Barred List Check Result", "type": "select", "options": ["Not barred", "Barred - Adults", "Barred - Children", "N/A - Not Enhanced"], "required": True},
            
            {"name": "section_disclosure", "type": "section_header", "label": "Disclosed Information (if any)"},
            {"name": "disclosure_details", "label": "Details of any convictions, cautions or other information disclosed", "type": "textarea", "required": False, "rows": 4, "help_text": "Leave blank if DBS is clear"},
            
            {"name": "section_risk", "type": "section_header", "label": "Risk Assessment (if applicable)"},
            {"name": "risk_info", "type": "info_box", "content": "Complete this section only if the DBS contains disclosed information. A risk assessment must be conducted before the candidate can start work.", "variant": "warning"},
            {"name": "risk_nature", "label": "Nature and seriousness of the offence(s)", "type": "textarea", "required": False, "rows": 2},
            {"name": "risk_relevance", "label": "Relevance to the role applied for", "type": "textarea", "required": False, "rows": 2},
            {"name": "risk_time_elapsed", "label": "Time elapsed since the offence(s)", "type": "textarea", "required": False, "rows": 2},
            {"name": "risk_circumstances", "label": "Circumstances at the time and any changes since", "type": "textarea", "required": False, "rows": 2},
            {"name": "risk_candidate_explanation", "label": "Candidate's explanation (if discussed)", "type": "textarea", "required": False, "rows": 2},
            {"name": "risk_mitigations", "label": "Proposed risk mitigations (if proceeding)", "type": "textarea", "required": False, "rows": 2},
            
            {"name": "section_outcome", "type": "section_header", "label": "Outcome"},
            {"name": "dbs_outcome", "label": "DBS Check Outcome", "type": "select", "options": ["Approved - Clear DBS", "Approved - Risk Assessment Complete", "Approved with Conditions", "Pending - Awaiting Update Service Check", "Rejected - Unsuitable"], "required": True},
            {"name": "conditions", "label": "Conditions of Approval (if any)", "type": "textarea", "required": False},
            {"name": "renewal_date", "label": "Next DBS Renewal Date", "type": "date", "required": False, "help_text": "Typically 3 years from issue date"},
            
            {"name": "section_sign", "type": "section_header", "label": "Sign-Off"},
            {"name": "employee_declaration", "label": "I declare that I have disclosed all relevant information and this DBS certificate relates to me", "type": "checkbox", "required": True},
            {"name": "reviewed_by", "label": "Reviewed By", "type": "text", "required": True},
            {"name": "review_date", "label": "Review Date", "type": "date", "required": True}
        ]
    },
    
    # ==================== 13. EMPLOYEE HANDBOOK ACKNOWLEDGEMENT ====================
    {
        "name": "Employee Handbook Acknowledgement",
        "description": "Acknowledgement form confirming the employee has read and understood the Employee Handbook and company policies.",
        "category": "Policies",
        "section": "Policies",
        "visibility": "normal",
        "role_specific": None,
        "requires_employee_signature": True,
        "requires_admin_signature": True,
        "form_fields": [
            {"name": "section_welcome", "type": "section_header", "label": "1. Welcome"},
            {"name": "welcome_text", "type": "info_box", "content": "Welcome to Osabea Healthcare Solutions. We are committed to providing safe, compassionate, and high-quality care services. This handbook outlines your responsibilities, expectations, and standards.", "variant": "info"},
            
            {"name": "section_values", "type": "section_header", "label": "2. Company Values"},
            {"name": "values_text", "type": "info_box", "content": "Our core values are: Compassion, Respect, Dignity, Accountability, and Professionalism. These values guide everything we do.", "variant": "info"},
            
            {"name": "section_responsibilities", "type": "section_header", "label": "3. Roles & Responsibilities"},
            {"name": "responsibilities_text", "type": "info_box", "content": "Your responsibilities include: Deliver safe and person-centred care, Follow care plans, Maintain confidentiality, Report incidents promptly.", "variant": "info"},
            
            {"name": "section_conduct", "type": "section_header", "label": "4. Code of Conduct"},
            {"name": "conduct_text", "type": "info_box", "content": "You must: Treat service users with dignity, Maintain professional boundaries, No abuse, neglect, or discrimination is tolerated, Follow all safeguarding policies.", "variant": "warning"},
            
            {"name": "section_safeguarding", "type": "section_header", "label": "5. Safeguarding"},
            {"name": "safeguarding_text", "type": "info_box", "content": "Safeguarding is everyone's responsibility. Report concerns immediately, Follow escalation procedures, Protect vulnerable individuals at all times.", "variant": "warning"},
            
            {"name": "section_health_safety", "type": "section_header", "label": "6. Health & Safety"},
            {"name": "health_safety_text", "type": "info_box", "content": "You must: Follow infection control procedures, Use PPE correctly, Report all hazards immediately.", "variant": "info"},
            
            {"name": "section_medication", "type": "section_header", "label": "7. Medication (Role-Based)"},
            {"name": "medication_hca", "type": "info_box", "content": "Healthcare Assistants: Only assist with medication if you have received appropriate training and competency assessment.", "variant": "info", "role_restriction": "hca_only"},
            {"name": "medication_nurse", "type": "info_box", "content": "Nurses: Administer medication safely following all protocols. Document all administration accurately.", "variant": "info", "role_restriction": "nurse_only"},
            
            {"name": "section_training", "type": "section_header", "label": "8. Training Requirements"},
            {"name": "training_text", "type": "info_box", "content": "All mandatory training must be completed before working with service users. Training must be renewed before expiry dates.", "variant": "info"},
            
            {"name": "section_attendance", "type": "section_header", "label": "9. Attendance & Conduct"},
            {"name": "attendance_text", "type": "info_box", "content": "You must: Be punctual for all shifts, Notify absence as early as possible, Maintain professional conduct at all times.", "variant": "info"},
            
            {"name": "section_confidentiality", "type": "section_header", "label": "10. Confidentiality"},
            {"name": "confidentiality_text", "type": "info_box", "content": "You must protect all personal data. Follow GDPR guidelines. Never share service user information without proper authorisation.", "variant": "warning"},
            
            {"name": "section_complaints", "type": "section_header", "label": "11. Complaints & Whistleblowing"},
            {"name": "complaints_text", "type": "info_box", "content": "Raise concerns safely through proper channels. Whistleblowing is protected - there will be no retaliation for reporting genuine concerns.", "variant": "info"},
            
            {"name": "section_declaration", "type": "section_header", "label": "12. Declaration"},
            {"name": "handbook_read", "label": "I confirm I have read and understood the Employee Handbook", "type": "checkbox", "required": True},
            {"name": "values_understood", "label": "I understand and agree to uphold the company values", "type": "checkbox", "required": True},
            {"name": "code_conduct_understood", "label": "I understand the Code of Conduct and will comply with all policies", "type": "checkbox", "required": True},
            {"name": "safeguarding_understood", "label": "I understand my safeguarding responsibilities and reporting procedures", "type": "checkbox", "required": True},
            {"name": "confidentiality_agreed", "label": "I agree to maintain confidentiality at all times", "type": "checkbox", "required": True},
            {"name": "training_commitment", "label": "I commit to completing all mandatory training requirements", "type": "checkbox", "required": True}
        ]
    }
]

# Email templates for common communications
EMAIL_TEMPLATES = {
    "document_request": {
        "subject": "Documents Required - Osabea Healthcare Solutions",
        "body": """Hi {employee_name},

To complete your onboarding, please upload the following documents:

{document_list}

You can upload these directly via your portal at {portal_url}.

If you need help, please let us know.

Kind regards,
Osabea Healthcare Solutions Team"""
    },
    
    "right_to_work_request": {
        "subject": "Right to Work Evidence Required - Osabea Healthcare Solutions",
        "body": """Hi {employee_name},

Please provide your Right to Work evidence:

If you have a share code, please send it along with your date of birth.

Alternatively, upload a clear copy of your passport.

Kind regards,
Osabea Healthcare Solutions Team"""
    },
    
    "form_completion_request": {
        "subject": "Form to Complete - Osabea Healthcare Solutions",
        "body": """Hi {employee_name},

You have a form to complete in your portal: {form_name}

Please log in at {portal_url} and complete it as soon as possible.

Thank you,
Osabea Healthcare Solutions Team"""
    },
    
    "onboarding_complete": {
        "subject": "Onboarding Complete - Welcome to Osabea Healthcare Solutions",
        "body": """Hi {employee_name},

Your onboarding is now complete!

You are ready for placement. We will contact you regarding available shifts.

Welcome to the team!

Kind regards,
Osabea Healthcare Solutions Team"""
    },
    
    "missing_items_followup": {
        "subject": "Missing Items - Action Required - Osabea Healthcare Solutions",
        "body": """Hi {employee_name},

We are still missing the following items from your records:

{missing_items}

Please upload these as soon as possible to avoid delays in your onboarding.

Thank you,
Osabea Healthcare Solutions Team"""
    },
    
    "expiry_reminder": {
        "subject": "Document Expiring Soon - Osabea Healthcare Solutions",
        "body": """Hi {employee_name},

The following document is expiring soon:

{document_name} - Expires: {expiry_date}

Please ensure you upload a renewed copy before the expiry date.

Kind regards,
Osabea Healthcare Solutions Team"""
    },
    
    "form_signed_off": {
        "subject": "Form Signed Off - Osabea Healthcare Solutions",
        "body": """Hi {employee_name},

The following form has been signed off by admin:

{form_name}

This form is now locked and part of your permanent record.

Kind regards,
Osabea Healthcare Solutions Team"""
    }
}


# Categories for grouping templates
TEMPLATE_CATEGORIES = {
    "Recruitment": ["Application Form", "Interview Record Form", "Reference Request & Verification Form"],
    "Compliance": ["Recruitment Compliance Checklist", "DBS Review & Risk Assessment"],
    "Health": ["Health Screening Questionnaire"],
    "Induction": ["Induction & Competency Assessment"],
    "Contract": ["Contract Acknowledgement Form"],
    "Personal": ["Personal Information Form"],
    "Equal Opportunities": ["Equal Opportunities Monitoring Form"],
    "Supervision": ["Supervision Record", "Annual Appraisal Form"],
    "Policies": ["Employee Handbook Acknowledgement"]
}