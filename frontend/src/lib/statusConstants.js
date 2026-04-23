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
  MISSING: 'missing',
  AWAITING_REVIEW: 'awaiting_review',
  REUPLOAD_REQUIRED: 'reupload_required',
  CHECK_REQUIRED: 'check_required',
  CHECK_IN_PROGRESS: 'check_in_progress',
  PROOF_REQUIRED: 'proof_required',
  VERIFIED: 'verified',
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
  const warningStatuses = [
    'pending', 'expiring', 'expiring_soon', 'needs_renewal', 'supervised_start', 'under_review', 'in_progress',
    'awaiting_review', 'check_required', 'check_in_progress', 'proof_required'
  ];
  const errorStatuses = ['expired', 'missing', 'blocked', 'not_ready', 'rejected', 'overdue', 'reupload_required'];
  
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

/**
 * Canonical status vocabulary — SHARED between admin and worker surfaces.
 *
 * RULE: All status chips, badges, pills, and inline status text across admin
 * and worker UIs must use these seven phrases. Do NOT invent synonyms like
 * "Check complete", "Pending Review", "Work Ready", "Ready to Work",
 * "Completed" — they are mapped here so every surface says the same thing
 * for the same concept.
 *
 * This helper does NOT compute status — it only maps canonical backend
 * values (and a handful of legacy display aliases) to the canonical label.
 */
export const STATUS_VOCABULARY = {
  SUBMITTED: 'Submitted',                       // worker has submitted; pre-review
  VERIFIED: 'Verified',                         // admin has verified
  COMPLETE: 'Complete',                         // system requirement satisfied
  READY_FOR_WORK: 'Ready for Work',             // fit-for-work decision approved
  NOT_READY_FOR_WORK: 'Not ready for work',     // fit-for-work decision blocked/missing
  AWAITING_WORKER: 'Awaiting worker',           // blocker needs worker action
  AWAITING_ADMIN_REVIEW: 'Awaiting admin review', // submitted, waiting on admin
  SYSTEM_ISSUE: 'System issue',                 // render/config failure, not user fault
};

// Maps a backend status string (or a known legacy display phrase) to the
// canonical label. Unknown values return null so callers can fall back to
// their existing label logic — this is additive, not a forced takeover.
const _STATUS_LABEL_MAP = Object.freeze({
  // Submitted
  submitted: STATUS_VOCABULARY.SUBMITTED,
  uploaded: STATUS_VOCABULARY.SUBMITTED,
  // Verified
  verified: STATUS_VOCABULARY.VERIFIED,
  approved: STATUS_VOCABULARY.VERIFIED,
  // Complete
  complete: STATUS_VOCABULARY.COMPLETE,
  completed: STATUS_VOCABULARY.COMPLETE,
  // Awaiting admin review
  pending_review: STATUS_VOCABULARY.AWAITING_ADMIN_REVIEW,
  awaiting_review: STATUS_VOCABULARY.AWAITING_ADMIN_REVIEW,
  under_review: STATUS_VOCABULARY.AWAITING_ADMIN_REVIEW,
  // Awaiting worker
  awaiting_worker: STATUS_VOCABULARY.AWAITING_WORKER,
  requested: STATUS_VOCABULARY.AWAITING_WORKER,
  reupload_required: STATUS_VOCABULARY.AWAITING_WORKER,
  // Ready for work
  work_ready: STATUS_VOCABULARY.READY_FOR_WORK,
  ready: STATUS_VOCABULARY.READY_FOR_WORK,
  ready_to_work: STATUS_VOCABULARY.READY_FOR_WORK,
  // Not ready for work
  not_ready: STATUS_VOCABULARY.NOT_READY_FOR_WORK,
  not_work_ready: STATUS_VOCABULARY.NOT_READY_FOR_WORK,
  // System
  system_issue: STATUS_VOCABULARY.SYSTEM_ISSUE,
});

/**
 * Return the canonical label for a backend status value or a legacy display
 * string. Case-insensitive. Returns null for unknown values so the caller
 * can preserve its existing fallback.
 *
 * @param {string} status
 * @returns {string|null}
 */
export function getStatusLabel(status) {
  if (!status) return null;
  const key = String(status).toLowerCase().replace(/\s+/g, '_');
  return _STATUS_LABEL_MAP[key] || null;
}
