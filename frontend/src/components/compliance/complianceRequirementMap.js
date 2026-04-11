/**
 * complianceRequirementMap.js
 * 
 * Single source of truth for all compliance requirement key mappings.
 * Use this everywhere to avoid key drift between UI, backend endpoints,
 * and move-category targets.
 */

import {
  getEvidenceRules,
  isActiveEvidenceFile,
  isHistoricalEvidenceFile,
  hasValidPoADate as sharedHasValidPoADate,
} from './evidenceRules';

export const REQUIREMENT_MAP = {
  right_to_work: {
    uiKey: 'right_to_work',
    evidenceEndpointKey: 'right_to_work_evidence',
    moveCategoryKey: 'right_to_work_documents',
    checkEndpointKey: 'right_to_work',
    label: 'Right to Work',
    shortLabel: 'RTW',
    allowedMoveTargets: ['identity_documents', 'proof_of_address', 'other'],
    requiredCount: 1,
    multiFile: true,
  },
  dbs: {
    uiKey: 'dbs',
    evidenceEndpointKey: 'dbs_evidence',
    moveCategoryKey: 'dbs_certificate',
    checkEndpointKey: 'dbs',
    label: 'DBS Certificate',
    shortLabel: 'DBS',
    allowedMoveTargets: ['identity_documents', 'other'],
    requiredCount: 1,
    multiFile: false,
  },
  identity: {
    uiKey: 'identity',
    evidenceEndpointKey: 'identity_evidence',
    moveCategoryKey: 'identity_documents',
    checkEndpointKey: 'identity',
    label: 'Identity',
    shortLabel: 'ID',
    allowedMoveTargets: ['right_to_work_documents', 'proof_of_address', 'other'],
    requiredCount: 1,
    multiFile: true,
  },
  proof_of_address: {
    uiKey: 'proof_of_address',
    evidenceEndpointKey: 'proof_of_address_evidence',
    moveCategoryKey: 'proof_of_address',
    checkEndpointKey: 'proof_of_address',
    label: 'Proof of Address',
    shortLabel: 'PoA',
    allowedMoveTargets: ['identity_documents', 'other'],
    requiredCount: 2,
    multiFile: true,
    validityMonths: 12, // Updated from 9 to 12 per role pack policy
  },
};

export const CATEGORY_OPTIONS = [
  { id: 'right_to_work_documents', label: 'Right to Work' },
  { id: 'dbs_certificate', label: 'DBS Certificate' },
  { id: 'identity_documents', label: 'Identity' },
  { id: 'proof_of_address', label: 'Proof of Address' },
  { id: 'professional_registration', label: 'Professional Registration' },
  { id: 'training_certificates', label: 'Training Certificates' },
  { id: 'other', label: 'Other Documents' },
];

// List of upload-type requirement keys
export const UPLOAD_REQUIREMENT_KEYS = ['right_to_work', 'dbs', 'identity', 'proof_of_address'];

/**
 * Get requirement configuration by UI key
 */
export function getRequirementConfig(requirementKey) {
  const rules = getEvidenceRules(requirementKey);
  if (!requirementKey) {
    return {
      uiKey: '',
      evidenceEndpointKey: '',
      moveCategoryKey: '',
      checkEndpointKey: '',
      label: '',
      shortLabel: '',
      allowedMoveTargets: ['other'],
      requiredCount: 1,
      multiFile: true,
      evidenceRules: rules,
    };
  }
  const baseConfig = REQUIREMENT_MAP[requirementKey] || {
    uiKey: requirementKey,
    evidenceEndpointKey: `${requirementKey}_evidence`,
    moveCategoryKey: requirementKey,
    checkEndpointKey: requirementKey,
    label: requirementKey,
    shortLabel: requirementKey.substring(0, 3).toUpperCase(),
    allowedMoveTargets: ['other'],
    requiredCount: 1,
    multiFile: true,
  };

  return {
    ...baseConfig,
    requiredCount: rules.min_required_files || baseConfig.requiredCount,
    multiFile: rules.multi_file_allowed,
    evidenceRules: rules,
  };
}

/**
 * Get label for a requirement key
 */
export function getRequirementLabel(requirementKey) {
  return getRequirementConfig(requirementKey).label;
}

/**
 * Get evidence endpoint key for API calls
 */
export function getEvidenceEndpointKey(requirementKey) {
  return getRequirementConfig(requirementKey).evidenceEndpointKey;
}

/**
 * Get move-category target key
 */
export function getMoveCategoryKey(requirementKey) {
  return getRequirementConfig(requirementKey).moveCategoryKey;
}

/**
 * Get allowed move targets for a requirement
 */
export function getAllowedMoveTargets(requirementKey) {
  const config = getRequirementConfig(requirementKey);
  return CATEGORY_OPTIONS.filter((cat) =>
    config.allowedMoveTargets.includes(cat.id)
  );
}

/**
 * Check if a file is previewable based on mime type or extension
 */
export function isPreviewableFile(file) {
  const mime = (file?.mime_type || file?.content_type || '').toLowerCase();
  const name = (file?.file_name || '').toLowerCase();

  return (
    mime === 'application/pdf' ||
    mime.startsWith('image/') ||
    mime.startsWith('text/') ||
    name.endsWith('.pdf') ||
    name.endsWith('.jpg') ||
    name.endsWith('.jpeg') ||
    name.endsWith('.png') ||
    name.endsWith('.gif') ||
    name.endsWith('.webp') ||
    name.endsWith('.txt')
  );
}

/**
 * Check if file is historical (superseded, rejected, etc.)
 */
export function isHistoricalFile(file) {
  return isHistoricalEvidenceFile(file);
}

/**
 * Check if a PoA file has a valid date (within 12 months)
 */
export function hasValidPoADate(file) {
  return sharedHasValidPoADate(file, 12);
}

/**
 * Normalize API data for upload requirement drawer
 */
export function normalizeUploadDrawerData(raw, requirementKey) {
  const rules = getEvidenceRules(requirementKey);
  const activeFiles = Array.isArray(raw?.active_files) ? raw.active_files : [];
  const historicalFiles = Array.isArray(raw?.historical_files) ? raw.historical_files : [];
  const requests = Array.isArray(raw?.requests) ? [...raw.requests] : [];

  const activeByRule = activeFiles.filter(isActiveEvidenceFile);
  const historicalByRule = [
    ...historicalFiles,
    ...activeFiles.filter(isHistoricalEvidenceFile)
  ];

  // Sort requests by most recent first
  requests.sort(
    (a, b) =>
      new Date(b.sent_at || b.created_at || 0).getTime() -
      new Date(a.sent_at || a.created_at || 0).getTime()
  );

  // A file is pending review only if NOT verified by any indicator
  const pendingReviewFiles = activeByRule.filter(
    (file) =>
      !file?.verified &&
      file?.status !== 'verified' &&
      !file?.verification_stamp &&
      !file?.rejected &&
      !file?.uploaded_in_error_reason &&
      file?.status !== 'uploaded_in_error'
  );

  // A file is verified if ANY verification indicator is true
  const verifiedFiles = activeByRule.filter((file) => 
    !!file?.verified || file?.status === 'verified' || !!file?.verification_stamp
  );

  // For PoA, calculate valid files (within 9 months)
  const validPoAFiles =
    requirementKey === 'proof_of_address'
      ? activeByRule.filter(
          (file) =>
            !file?.rejected &&
            !file?.uploaded_in_error_reason &&
            file?.status !== 'uploaded_in_error' &&
            sharedHasValidPoADate(file, rules.recency_months || 12)
        )
      : [];

  return {
    ...raw,
    active_files: activeByRule,
    historical_files: historicalByRule,
    requests,
    evidence_rules: rules,
    counts: {
      active: activeByRule.length,
      historical: historicalByRule.length,
      pendingReview: pendingReviewFiles.length,
      verified: verifiedFiles.length,
      requests: requests.length,
      validPoA: validPoAFiles.length,
    },
  };
}

/**
 * Build readable summary string for drawer header
 */
export function buildDrawerSummary(data) {
  if (!data || !data.counts) return '';

  const parts = [];
  parts.push(`${data.counts.active} active`);

  if (data.counts.historical > 0) {
    parts.push(`${data.counts.historical} historical`);
  }

  if (data.counts.requests === 0) {
    parts.push('no requests');
  } else {
    const latest = data.requests[0];
    if (latest?.submitted_at) parts.push('submitted');
    else if (latest?.viewed_at) parts.push('viewed');
    else if (latest?.sent_at) parts.push('request sent');
    else parts.push(latest?.status || 'requested');
  }

  if (data.counts.pendingReview > 0) {
    parts.push(`${data.counts.pendingReview} pending review`);
  }

  return parts.join(' • ');
}
