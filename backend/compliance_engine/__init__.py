# Unified Compliance Rule Engine
# All requirements use the same backbone with requirement-specific rule packs

from .models import (
    RequirementType,
    EvidenceStatus,
    StampType,
    VerificationStatus,
    VerificationOutcome,
    ComputedState,
    VisibilityBucket,
    Evidence,
    Verification,
    StructuredResult,
    RequirementSummary,
    ComplianceSummary,
    DocumentRequestItem,
    ConsolidatedRequest
)

from .engine import (
    ComplianceEngine,
    EvidenceService,
    VerificationService,
    ResultService,
    BlockerEngine,
    StatusEngine
)

from .rule_packs import (
    BaseRulePack,
    RTWRulePack,
    DBSRulePack,
    IdentityRulePack,
    POARulePack,
    get_rule_pack,
    RULE_PACKS
)

from .labels import (
    EVIDENCE_STATUS_LABELS,
    STAMP_TYPE_LABELS,
    VERIFICATION_STATUS_LABELS,
    OUTCOME_LABELS,
    COMPUTED_STATE_LABELS,
    METHOD_LABELS,
    RTW_METHOD_LABELS,
    DBS_METHOD_LABELS,
    IDENTITY_METHOD_LABELS,
    ADDRESS_METHOD_LABELS,
    STATUS_COLORS,
    REQUIREMENT_TYPE_LABELS,
    BLOCKER_MESSAGES,
    get_label,
    get_status_color
)

from .extraction import (
    DocumentExtractor,
    resize_image_for_extraction,
    pdf_first_page_to_image,
    extract_rtw_fields,
    extract_dbs_fields,
    extract_identity_fields,
    extract_address_fields,
    RTW_EXTRACTION_PROMPT,
    DBS_EXTRACTION_PROMPT,
    IDENTITY_EXTRACTION_PROMPT,
    ADDRESS_EXTRACTION_PROMPT
)

__all__ = [
    # Models
    'RequirementType', 'EvidenceStatus', 'StampType', 
    'VerificationStatus', 'VerificationOutcome', 'ComputedState', 'VisibilityBucket',
    'Evidence', 'Verification', 'StructuredResult', 'RequirementSummary',
    'ComplianceSummary', 'DocumentRequestItem', 'ConsolidatedRequest',
    # Engine
    'ComplianceEngine', 'EvidenceService', 'VerificationService',
    'ResultService', 'BlockerEngine', 'StatusEngine',
    # Rule Packs
    'BaseRulePack', 'RTWRulePack', 'DBSRulePack', 'IdentityRulePack', 'POARulePack', 
    'get_rule_pack', 'RULE_PACKS',
    # Labels
    'EVIDENCE_STATUS_LABELS', 'STAMP_TYPE_LABELS', 'VERIFICATION_STATUS_LABELS',
    'OUTCOME_LABELS', 'COMPUTED_STATE_LABELS', 'METHOD_LABELS',
    'RTW_METHOD_LABELS', 'DBS_METHOD_LABELS', 'IDENTITY_METHOD_LABELS', 'ADDRESS_METHOD_LABELS',
    'STATUS_COLORS', 'REQUIREMENT_TYPE_LABELS', 'BLOCKER_MESSAGES',
    'get_label', 'get_status_color',
    # Extraction
    'DocumentExtractor', 'resize_image_for_extraction', 'pdf_first_page_to_image',
    'extract_rtw_fields', 'extract_dbs_fields', 'extract_identity_fields', 'extract_address_fields',
    'RTW_EXTRACTION_PROMPT', 'DBS_EXTRACTION_PROMPT', 'IDENTITY_EXTRACTION_PROMPT', 'ADDRESS_EXTRACTION_PROMPT'
]
