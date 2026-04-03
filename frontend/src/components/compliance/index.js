// Compliance Components - Dual-Row Model (Step 11)
// 
// Evidence row = uploaded/supporting files
// Check row = employer/admin verification outcome (authoritative)
// Agreement row = form acknowledgements
// Reference row = referee request/response/verification workflow

// Core Shell Components (STEP 11E+)
export { default as RequirementSectionShell } from './RequirementSectionShell';
export { default as RequirementActionBar } from './RequirementActionBar';
export { default as UploadRequirementCard } from './UploadRequirementCard';
export * from './surfaceNormalizers';

// Row Components
export { default as EvidenceRow } from './EvidenceRow';
export { default as CheckRow } from './CheckRow';
export { default as AgreementRow } from './AgreementRow';
export { default as ReferenceRow } from './ReferenceRow';

// Container Components
export { default as DualRowComplianceSection } from './DualRowComplianceSection';

// Dialogs
export { default as RecordCheckDialog } from './RecordCheckDialog';
export { default as CompleteAgreementDialog } from './CompleteAgreementDialog';
export { default as SendAgreementDialog } from './SendAgreementDialog';

// Phase 4A - High-value cleanup components
export { default as ComplianceActionBar } from './ComplianceActionBar';
export { default as WhatsNeededPanel } from './WhatsNeededPanel';
export { default as TrainingSummaryCard } from './TrainingSummaryCard';

// Phase 4B - Restructured top section components
export { default as ApprovalStatusPanel } from './ApprovalStatusPanel';
export { default as NextActionsPanel } from './NextActionsPanel';

// Phase D2 - File interaction components
export { default as RequirementFilesDrawer } from './RequirementFilesDrawer';
export { default as DocumentActionMenu } from './DocumentActionMenu';

// Phase D3 - Request lifecycle & history components
export { default as RequirementHistoryDrawer } from './RequirementHistoryDrawer';
export { default as RequestStatusBadge, RequestStatusInline } from './RequestStatusBadge';

// Stage Identity Components (Applicant vs Employee)
export { default as StageIdentityBadge, STAGE_CONFIGS } from './StageIdentityBadge';
export { default as ApplicantStageBanner } from './ApplicantStageBanner';

// Simplified Header & Approval Components
export { default as SimplifiedProfileHeader } from './SimplifiedProfileHeader';
export { default as RecruitmentApprovalCard } from './RecruitmentApprovalCard';

// Reference Response Drawer (Ticket E)
export { default as ReferenceResponseDrawer } from './ReferenceResponseDrawer';

// Agreement Form Drawer (Ticket D)
export { default as AgreementFormDrawer } from './AgreementFormDrawer';

// Production-Ready Compliance Drawers
export { default as ComplianceDrawer, DrawerSection, DrawerCard, DrawerEmptyState, DrawerStatusChip } from './ComplianceDrawer';
export { default as EvidenceManageDrawer } from './EvidenceManageDrawer';
