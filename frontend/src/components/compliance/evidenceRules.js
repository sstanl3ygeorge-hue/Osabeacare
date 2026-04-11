/**
 * Shared evidence rules and state helpers for upload-based compliance requirements.
 *
 * This is the single source of truth used by:
 * - UploadRequirementCard
 * - EvidenceManageDrawer
 * - normalization helpers
 */

export const EVIDENCE_RULES = {
  right_to_work: {
    max_active_files: 2,
    min_required_files: 1,
    multi_file_allowed: true,
    file_recency_required: false,
    recency_months: null,
    admin_verification_required: true,
  },
  dbs: {
    max_active_files: 1,
    min_required_files: 1,
    multi_file_allowed: false,
    file_recency_required: false,
    recency_months: null,
    admin_verification_required: true,
  },
  identity: {
    max_active_files: 2,
    min_required_files: 1,
    multi_file_allowed: true,
    file_recency_required: false,
    recency_months: null,
    admin_verification_required: true,
  },
  proof_of_address: {
    max_active_files: 3,
    min_required_files: 2,
    multi_file_allowed: true,
    file_recency_required: true,
    recency_months: 12,
    admin_verification_required: true,
  },
};

const REQUIREMENT_KEY_ALIASES = {
  right_to_work_evidence: "right_to_work",
  right_to_work_documents: "right_to_work",
  dbs_certificate: "dbs",
  dbs_certificate_evidence: "dbs",
  dbs_evidence: "dbs",
  identity_evidence: "identity",
  identity_documents: "identity",
  proof_of_address_evidence: "proof_of_address",
};

const NON_ACTIVE_STATUSES = new Set([
  "rejected",
  "uploaded_in_error",
  "superseded",
  "misfiled",
  "deleted",
  "removed",
  "archived",
  "moved",
  "invalidated",
  "amendment_requested",
]);

export function getCanonicalRequirementKey(requirementKey) {
  if (!requirementKey) return "";
  return REQUIREMENT_KEY_ALIASES[requirementKey] || requirementKey;
}

export function getEvidenceRules(requirementKey) {
  const canonical = getCanonicalRequirementKey(requirementKey);
  return EVIDENCE_RULES[canonical] || {
    max_active_files: null,
    min_required_files: 1,
    multi_file_allowed: true,
    file_recency_required: false,
    recency_months: null,
    admin_verification_required: true,
  };
}

export function isHistoricalEvidenceFile(file) {
  if (!file) return false;
  const status = (file.status || "").toLowerCase();
  return (
    NON_ACTIVE_STATUSES.has(status) ||
    Boolean(file.superseded_by) ||
    Boolean(file.superseded_at) ||
    Boolean(file.uploaded_in_error_reason) ||
    Boolean(file.moved_to)
  );
}

export function isActiveEvidenceFile(file) {
  if (!file) return false;
  return !isHistoricalEvidenceFile(file);
}

export function hasValidPoADate(file, recencyMonths = 12) {
  if (!file?.document_date && !file?.uploaded_at) return false;

  const docDate = new Date(file.document_date || file.uploaded_at);
  if (Number.isNaN(docDate.getTime())) return false;

  const now = new Date();
  const diffMonths =
    (now.getFullYear() - docDate.getFullYear()) * 12 +
    (now.getMonth() - docDate.getMonth());

  return diffMonths <= recencyMonths;
}
