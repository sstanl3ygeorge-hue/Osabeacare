# Services module
from .pdf_service import generate_admin_form_pdf, LOGO_URL
from .training_evaluator import (
    set_db as set_training_evaluator_db,
    EXPIRY_WARNING_DAYS,
    TRAINING_VALIDITY_PERIODS,
    TRAINING_BLOCKER_CONFIG,
    get_training_validity_days,
    calculate_training_expiry,
    normalize_date_only,
    compute_training_record_status,
    enrich_training_record_with_computed_status,
    get_training_blocker_config,
    get_canonical_mandatory_training_ids,
    is_mandatory_training_canonical,
    get_required_training_for_employee,
    evaluate_employee_training_status,
)
