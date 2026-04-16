"""
Enhanced Training Certificate Extraction Service

This service handles extraction of MULTIPLE training items from a single certificate.
It also categorizes trainings as MANDATORY (blocks promotion) vs ADDITIONAL (bonus).

Certificate Types Handled:
1. Table format (Lawrence's) - Multiple rows with individual dates
2. Single certificate (Olufisayo's) - One training with "Frequency: Every X Years"
3. Bundle certificate (Ramon's) - Multiple modules with shared completion date and "Valid for X year"
"""

import os
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)

# =====================================================
# MANDATORY TRAINING BY ROLE
# These are required for promotion and block work readiness if missing/expired
# =====================================================

MANDATORY_TRAINING_BY_ROLE = {
    "healthcare_assistant": [
        "safeguarding",  # Matches: Safeguarding Adults, Safeguarding Children, etc.
        "manual_handling",  # Matches: Manual Handling, Moving & Handling
        "fire_safety",  # Matches: Fire Safety
        "health_safety",  # Matches: Health & Safety
        "basic_life_support",  # Matches: BLS, Basic Life Support, Resuscitation
        "infection_control",  # Matches: Infection Control, Infection Prevention
        "information_governance",  # Matches: Information Governance, GDPR, Data Protection
        "prevent",  # Matches: Prevent, Counter-Terrorism Awareness
    ],
    "nurse": [
        "safeguarding",
        "manual_handling",
        "fire_safety", 
        "health_safety",
        "basic_life_support",
        "infection_control",
        "information_governance",
        "prevent",
        # NMC registration is tracked separately, not as training
    ],
    "senior_carer": [
        "safeguarding",
        "manual_handling",
        "fire_safety",
        "health_safety",
        "basic_life_support",
        "infection_control",
        "information_governance",
        "prevent",
        "medication",  # Medication Administration required for senior carers
    ],
    "support_worker": [
        "safeguarding",
        "manual_handling",
        "fire_safety",
        "health_safety",
        "basic_life_support",
        "infection_control",
        "information_governance",
        "prevent",
    ],
    "default": [  # Fallback for unknown roles
        "safeguarding",
        "manual_handling",
        "fire_safety",
        "health_safety",
        "basic_life_support",
        "infection_control",
        "information_governance",
        "prevent",
    ]
}

# =====================================================
# TRAINING NAME NORMALIZATION MAPPING
# Maps various certificate names to our standard IDs
# =====================================================

TRAINING_NAME_MAPPING = {
    # Safeguarding
    "safeguarding adults": "safeguarding_adults",
    "cstf. safeguarding adults": "safeguarding_adults",
    "cstf safeguarding adults": "safeguarding_adults",
    "safeguarding adults level": "safeguarding_adults",
    "safeguarding children": "safeguarding_children",
    "cstf. safeguarding children": "safeguarding_children",
    "cstf safeguarding children": "safeguarding_children",
    "safeguarding children level": "safeguarding_children",
    
    # Manual Handling
    "manual handling": "manual_handling",
    "moving & handling": "manual_handling",
    "moving and handling": "manual_handling",
    "cstf - manual handling": "manual_handling",
    "cstf manual handling": "manual_handling",
    "cstf moving & handling": "manual_handling",
    
    # Fire Safety
    "fire safety": "fire_safety",
    "cstf - fire safety": "fire_safety",
    "cstf fire safety": "fire_safety",
    
    # Health & Safety
    "health & safety": "health_safety",
    "health and safety": "health_safety",
    "cstf - health & safety": "health_safety",
    "cstf health, safety and welfare": "health_safety",
    "health, safety and welfare": "health_safety",
    
    # Basic Life Support / Resuscitation
    "basic life support": "basic_life_support",
    "bls": "basic_life_support",
    "adult basic life support": "basic_life_support",
    "cstf - adult basic life support": "basic_life_support",
    "resuscitation": "basic_life_support",
    "cstf resuscitation adults": "basic_life_support",
    "immediate life support": "immediate_life_support",
    "ils": "immediate_life_support",
    "cstf - adult immediate life support": "immediate_life_support",
    
    # Infection Control
    "infection control": "infection_control",
    "infection prevention": "infection_control",
    "infection prevention and control": "infection_control",
    "cstf - infection prevention and control": "infection_control",
    "cstf infection prevention & control": "infection_control",
    
    # Medication
    "medication": "medication",
    "medication administration": "medication",
    "safe handling & administration of medication": "medication",
    "the safe handling & administration of medication": "medication",
    
    # Additional trainings (not mandatory but tracked)
    "food hygiene": "food_hygiene",
    "food hygiene & safety": "food_hygiene",
    "dementia": "dementia_awareness",
    "dementia awareness": "dementia_awareness",
    "awareness of mental health, dementia": "dementia_awareness",
    "mental capacity act": "mental_capacity_act",
    "epilepsy": "epilepsy_awareness",
    "seizures & epilepsy": "epilepsy_awareness",
    "catheter": "catheter_care",
    "catheters & catheter care": "catheter_care",
    "peg feeding": "peg_feeding",
    "peg feeding online module": "peg_feeding",
    "buccal midazolam": "buccal_midazolam",
    "dysphagia": "dysphagia_awareness",
    "dysphagia awareness": "dysphagia_awareness",
    "sepsis": "sepsis_awareness",
    "sepsis awareness": "sepsis_awareness",
    "pressure sores": "pressure_sores",
    "skin integrity": "pressure_sores",
    "suicide awareness": "suicide_awareness",
    "autism": "autism_awareness",
    "adhd": "adhd_awareness",
    "understanding and supporting adhd and autism": "autism_awareness",
    "conflict resolution": "conflict_resolution",
    "cstf nhs conflict resolution": "conflict_resolution",
    "prevent": "prevent_radicalisation",
    "preventing radicalisation": "prevent_radicalisation",
    "cstf - preventing radicalisation": "prevent_radicalisation",
    "equality": "equality_diversity",
    "diversity": "equality_diversity",
    "cstf - equality & diversity": "equality_diversity",
    "cstf equality, diversity and human rights": "equality_diversity",
    "information governance": "information_governance",
    "cstf - information governance": "information_governance",
    "gdpr": "information_governance",
    "data security": "information_governance",
    "lone worker": "lone_worker",
    "covid": "covid_awareness",
    "covid awareness": "covid_awareness",
    "anaphylaxis": "anaphylaxis_awareness",
    "anaphylaxis awareness": "anaphylaxis_awareness",
}

# =====================================================
# VALIDITY PERIOD PATTERNS
# =====================================================

VALIDITY_PATTERNS = [
    (r"valid\s+for\s+(\d+)\s+year", "years"),
    (r"frequency:\s+every\s+(\d+)\s+year", "years"),
    (r"every\s+(\d+)\s+year", "years"),
    (r"renewal:\s+(\d+)\s+year", "years"),
    (r"valid\s+for\s+(\d+)\s+month", "months"),
    (r"(\d+)\s+year\s+validity", "years"),
]

DEFAULT_VALIDITY_YEARS = {
    "safeguarding_adults": 1,
    "safeguarding_children": 1,
    "manual_handling": 1,
    "fire_safety": 2,  # Often 2 years
    "health_safety": 1,
    "basic_life_support": 1,
    "infection_control": 1,
    "medication": 1,
    "food_hygiene": 3,
    "first_aid": 3,
    "default": 1
}


def normalize_training_name(name: str) -> tuple:
    """
    Normalize a training name from certificate to our standard ID.
    Returns (standard_id, display_name, is_mandatory_type)
    """
    if not name:
        return (None, None, False)
    
    name_lower = name.lower().strip()
    
    # Direct mapping
    for pattern, standard_id in TRAINING_NAME_MAPPING.items():
        if pattern in name_lower:
            # Check if this is a mandatory training type
            is_mandatory = any(
                standard_id.startswith(m) 
                for m in ["safeguarding", "manual_handling", "fire_safety", 
                          "health_safety", "basic_life_support", "infection_control"]
            )
            return (standard_id, name.strip(), is_mandatory)
    
    # No match - return as additional training
    # Create a slug from the name
    slug = re.sub(r'[^a-z0-9]+', '_', name_lower).strip('_')
    return (slug, name.strip(), False)


def extract_validity_period(text: str) -> Optional[int]:
    """
    Extract validity period in days from certificate text.
    Looks for patterns like "Valid for 1 YEAR", "Frequency: Every 2 Years"
    """
    if not text:
        return None
    
    text_lower = text.lower()
    
    for pattern, unit in VALIDITY_PATTERNS:
        match = re.search(pattern, text_lower)
        if match:
            value = int(match.group(1))
            if unit == "years":
                return value * 365
            elif unit == "months":
                return value * 30
    
    return None


def parse_date(date_str: str) -> Optional[datetime]:
    """Parse various date formats from certificates."""
    if not date_str:
        return None
    
    date_str = date_str.strip()
    
    formats = [
        "%d/%m/%Y",
        "%d-%m-%Y", 
        "%Y-%m-%d",
        "%d %B %Y",
        "%d %b %Y",
        "%B %d, %Y",
        "%b %d, %Y",
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    return None


def calculate_expiry_date(
    completion_date: datetime, 
    explicit_expiry: Optional[datetime],
    validity_days: Optional[int],
    training_id: str
) -> datetime:
    """
    Calculate expiry date using the following priority:
    1. Explicit expiry date from certificate
    2. Completion date + validity period from certificate
    3. Completion date + default validity for training type
    """
    if explicit_expiry:
        return explicit_expiry
    
    if validity_days:
        return completion_date + timedelta(days=validity_days)
    
    # Use default validity for training type
    default_years = DEFAULT_VALIDITY_YEARS.get(training_id, DEFAULT_VALIDITY_YEARS["default"])
    return completion_date + timedelta(days=default_years * 365)


def is_mandatory_for_role(training_id: str, role: str) -> bool:
    """
    Check if a training is mandatory for the given role.
    """
    role_lower = role.lower().replace(" ", "_") if role else "default"
    
    mandatory_list = MANDATORY_TRAINING_BY_ROLE.get(
        role_lower, 
        MANDATORY_TRAINING_BY_ROLE["default"]
    )
    
    # Check if training_id matches any mandatory training type
    for mandatory_type in mandatory_list:
        if training_id.startswith(mandatory_type) or mandatory_type in training_id:
            return True
    
    return False


def categorize_extracted_trainings(
    trainings: List[Dict], 
    employee_role: str
) -> Dict[str, List[Dict]]:
    """
    Categorize extracted trainings into mandatory and additional.
    
    Returns:
    {
        "mandatory": [... trainings that block promotion ...],
        "additional": [... bonus trainings ...],
        "summary": {
            "mandatory_count": X,
            "mandatory_complete": Y,
            "additional_count": Z
        }
    }
    """
    mandatory = []
    additional = []
    
    for training in trainings:
        training_id = training.get("training_id") or training.get("id")
        
        if is_mandatory_for_role(training_id, employee_role):
            training["is_mandatory"] = True
            training["blocks_promotion"] = True
            mandatory.append(training)
        else:
            training["is_mandatory"] = False
            training["blocks_promotion"] = False
            additional.append(training)
    
    return {
        "mandatory": mandatory,
        "additional": additional,
        "summary": {
            "mandatory_count": len(mandatory),
            "mandatory_complete": len([t for t in mandatory if t.get("status") == "complete"]),
            "additional_count": len(additional)
        }
    }


async def extract_multiple_trainings_from_certificate(
    file_content: bytes,
    file_name: str,
    employee_id: str,
    employee_role: str,
    ai_extraction_result: Dict
) -> Dict:
    """
    Process AI extraction result to create multiple training records from one certificate.
    
    The AI extraction should return:
    {
        "trainings": [
            {"name": "...", "completed": "...", "expires": "...", "cert_number": "..."},
            ...
        ],
        "validity_period": "1 year" or "Every 2 years",
        "person_name": "...",
        "provider": "..."
    }
    
    Returns:
    {
        "trainings": [...],  # All extracted training records
        "mandatory": [...],  # Mandatory trainings only
        "additional": [...],  # Additional trainings only
        "summary": {...},
        "file_name": "...",
        "employee_id": "..."
    }
    """
    extracted_trainings = ai_extraction_result.get("trainings", [])
    global_validity = extract_validity_period(
        ai_extraction_result.get("validity_period", "") or 
        ai_extraction_result.get("raw_text", "")
    )
    global_completion_date = parse_date(ai_extraction_result.get("completion_date", ""))
    
    processed_trainings = []
    
    for training in extracted_trainings:
        name = training.get("name") or training.get("training_name")
        if not name:
            continue
        
        # Normalize the training name
        training_id, display_name, is_mandatory_type = normalize_training_name(name)
        if not training_id:
            continue
        
        # Parse dates
        completion_str = training.get("completed") or training.get("completion_date")
        expiry_str = training.get("expires") or training.get("expiry_date")
        
        completion_date = parse_date(completion_str) or global_completion_date or datetime.now()
        explicit_expiry = parse_date(expiry_str)
        
        # Get validity for this specific training
        training_validity = extract_validity_period(training.get("validity", "")) or global_validity
        
        # Calculate expiry
        expiry_date = calculate_expiry_date(
            completion_date,
            explicit_expiry,
            training_validity,
            training_id
        )
        
        # Determine if mandatory for this role
        is_mandatory = is_mandatory_for_role(training_id, employee_role)
        
        processed_training = {
            "training_id": training_id,
            "training_name": display_name,
            "completion_date": completion_date.isoformat(),
            "expiry_date": expiry_date.isoformat(),
            "certificate_number": training.get("cert_number") or training.get("certificate_number"),
            "provider": ai_extraction_result.get("provider"),
            "is_mandatory": is_mandatory,
            "blocks_promotion": is_mandatory,
            "status": "complete",
            "source_file": file_name,
            "employee_id": employee_id,
            "extracted_at": datetime.now().isoformat()
        }
        
        processed_trainings.append(processed_training)
    
    # Categorize
    categorized = categorize_extracted_trainings(processed_trainings, employee_role)
    
    return {
        "trainings": processed_trainings,
        "mandatory": categorized["mandatory"],
        "additional": categorized["additional"],
        "summary": categorized["summary"],
        "file_name": file_name,
        "employee_id": employee_id,
        "total_extracted": len(processed_trainings)
    }


# =====================================================
# GEMINI EXTRACTION PROMPT
# =====================================================

MULTI_TRAINING_EXTRACTION_PROMPT = """
You are analyzing a training certificate. Extract ALL training courses/modules listed.

CRITICAL: One certificate may contain MULTIPLE trainings (40+ in some cases).
Extract EVERY training item as a separate entry.

For EACH training found, extract:
1. Training Name (exact name as shown)
2. Completion Date (format: DD/MM/YYYY)
3. Expiry Date (format: DD/MM/YYYY) - if shown explicitly
4. Certificate Number - if shown

Also look for:
- "Valid for X year(s)" or "Frequency: Every X years" - this is the validity period
- Provider/Issuer name
- Person name on certificate

Return JSON format:
{
  "person_name": "Name on certificate",
  "provider": "Training provider name",
  "validity_period": "1 year" or "Every 2 years" (if shown on certificate),
  "completion_date": "DD/MM/YYYY" (if a single date applies to all),
  "trainings": [
    {
      "name": "Training Name 1",
      "completed": "DD/MM/YYYY",
      "expires": "DD/MM/YYYY",
      "cert_number": "12345"
    },
    {
      "name": "Training Name 2",
      "completed": "DD/MM/YYYY", 
      "expires": "DD/MM/YYYY",
      "cert_number": "12346"
    }
    // ... continue for ALL trainings found
  ]
}

IMPORTANT:
- If certificate shows a table with many rows, extract EVERY row
- If no individual dates shown but one completion date + "Valid for X year", use that for all
- If expiry is not shown but validity period is (e.g., "Every 2 Years"), calculate expiry from completion date
- Extract even partial information - better to have name only than miss a training
"""
