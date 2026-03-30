/**
 * Status Constants - SINGLE SOURCE OF TRUTH for status values
 * 
 * UI INTEGRITY RULES:
 * 1. Frontend must consume backend-provided status fields
 * 2. These constants are for safe comparison only, NOT for local derivation
 * 3. Status computation happens in backend ONLY
 * 4. Labels must be explicit and unambiguous:
 *    - "Pending" → "Awaiting Review" or "Awaiting Evidence"
 *    - "Completed" → "Completed & Verified" or "Completed (Awaiting Verification)"
 *    - "Valid" → Always include expiry date when available
 */

// Compliance/Document statuses
export const COMPLIANCE_STATUS = {
  VALID: 'valid',
  EXPIRED: 'expired',
  EXPIRING: 'expiring',
  EXPIRING_SOON: 'expiring_soon',
  MISSING: 'missing',
  PENDING: 'pending',  // Backend value - frontend should display as "Awaiting Review"
  PENDING_REVIEW: 'pending_review',
  AWAITING_EVIDENCE: 'awaiting_evidence',
  NEEDS_RENEWAL: 'needs_renewal',
  NOT_STARTED: 'not_started',
  IN_PROGRESS: 'in_progress',
  COMPLETED: 'completed',
  COMPLETED_VERIFIED: 'completed_verified',
  COMPLETED_UNVERIFIED: 'completed_unverified',
  VERIFIED: 'verified',
};

// Work readiness statuses (from backend calculation)
export const WORK_READINESS_STATUS = {
  WORK_READY: 'work_ready',
  SUPERVISED_START: 'supervised_start',
  NOT_READY: 'not_ready',
  BLOCKED: 'blocked',
};

// Document workflow statuses
export const DOCUMENT_STATUS = {
  NOT_STARTED: 'not_started',
  REQUESTED: 'requested',
  UPLOADED: 'uploaded',
  UNDER_REVIEW: 'under_review',
  APPROVED: 'approved',
  REJECTED: 'rejected',
  EXPIRED: 'expired',
};

// Training record statuses (computed from completion_date + expiry_date)
export const TRAINING_STATUS = {
  NOT_STARTED: 'not_started',
  IN_PROGRESS: 'in_progress',
  COMPLETED: 'completed',
  EXPIRING: 'expiring',
  EXPIRED: 'expired',
};

/**
 * Status category helper - determines UI treatment based on status
 * @param {string} status 
 * @returns {'success' | 'warning' | 'error' | 'neutral'}
 */
export function getStatusCategory(status) {
  const normalized = (status || '').toLowerCase();
  
  const successStatuses = ['valid', 'verified', 'completed', 'approved', 'work_ready', 'ready', 'current'];
  const warningStatuses = ['pending', 'expiring', 'expiring_soon', 'needs_renewal', 'supervised_start', 'under_review', 'in_progress'];
  const errorStatuses = ['expired', 'missing', 'blocked', 'not_ready', 'rejected', 'overdue'];
  
  if (successStatuses.includes(normalized)) return 'success';
  if (warningStatuses.includes(normalized)) return 'warning';
  if (errorStatuses.includes(normalized)) return 'error';
  return 'neutral';
}

/**
 * Get CSS classes for status category
 * @param {string} status 
 * @returns {object} { bg, text, border }
 */
export function getStatusColors(status) {
  const category = getStatusCategory(status);
  
  const colorMap = {
    success: { bg: 'bg-green-100', text: 'text-green-700', border: 'border-green-200' },
    warning: { bg: 'bg-amber-100', text: 'text-amber-700', border: 'border-amber-200' },
    error: { bg: 'bg-red-100', text: 'text-red-700', border: 'border-red-200' },
    neutral: { bg: 'bg-gray-100', text: 'text-gray-600', border: 'border-gray-200' },
  };
  
  return colorMap[category];
}

/**
 * Check if status indicates a problem that needs attention
 * @param {string} status 
 * @returns {boolean}
 */
export function isStatusCritical(status) {
  return getStatusCategory(status) === 'error';
}

/**
 * Check if status indicates a warning that may need attention soon
 * @param {string} status 
 * @returns {boolean}
 */
export function isStatusWarning(status) {
  return getStatusCategory(status) === 'warning';
}

export default {
  COMPLIANCE_STATUS,
  WORK_READINESS_STATUS,
  DOCUMENT_STATUS,
  TRAINING_STATUS,
  getStatusCategory,
  getStatusColors,
  isStatusCritical,
  isStatusWarning,
};
