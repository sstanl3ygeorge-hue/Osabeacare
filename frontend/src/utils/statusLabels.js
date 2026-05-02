/**
 * Canonical status labels for compliance items (Tier 1 fix #4).
 *
 * Single source of truth used by both the admin profile page and the worker
 * dashboard so the same backend state always shows the same words. Eliminates
 * the "admin says Awaiting review / worker says Submitted" class of bugs.
 *
 * ALWAYS use the helpers below — never hardcode label strings inline.
 */

// Canonical states (string-matched against backend `status` / `lifecycle_status`).
export const STATUS_LABELS = {
  not_started: 'Awaiting your action',
  awaiting_worker: 'Awaiting your action',
  in_progress: 'In progress',
  submitted: 'Submitted — awaiting admin review',
  awaiting_admin_review: 'Submitted — awaiting admin review',
  awaiting_company_countersignature: 'Awaiting company countersignature',
  verified: 'Verified',
  approved: 'Verified',
  signed_off: 'Verified',
  complete: 'Verified',
  completed: 'Verified',
  rejected: 'Rejected — re-do required',
  needs_redo: 'Rejected — re-do required',
  expired: 'Expired — renewal required',
  legacy_template_signed: 'Worker signed previous version — admin must reissue',
  not_required: 'Not required',
  not_applicable: 'Not applicable',
  unavailable: 'Unavailable',
};

// Same canonical key, but viewed from the OTHER party's perspective.
// e.g. when an admin is looking at a row whose state is "submitted", the
// label should still say "Submitted — awaiting admin review" — both parties
// see the same words. Kept as an explicit table to make divergences
// intentional should we ever need them.
const ADMIN_LABEL_OVERRIDES = {
  awaiting_worker: 'Awaiting worker action',
  not_started: 'Awaiting worker action',
};

const WORKER_LABEL_OVERRIDES = {
  awaiting_company_countersignature: "Submitted — awaiting your manager's signature",
};

const TONE_BY_KEY = {
  not_started: 'amber',
  awaiting_worker: 'amber',
  in_progress: 'blue',
  submitted: 'blue',
  awaiting_admin_review: 'blue',
  awaiting_company_countersignature: 'blue',
  verified: 'green',
  approved: 'green',
  signed_off: 'green',
  complete: 'green',
  completed: 'green',
  rejected: 'red',
  needs_redo: 'red',
  expired: 'red',
  legacy_template_signed: 'amber',
  not_required: 'gray',
  not_applicable: 'gray',
  unavailable: 'gray',
};

const _normalise = (input) => String(input || '').toLowerCase().trim().replace(/[\s-]+/g, '_');

/**
 * Get the canonical user-facing label for a status.
 * @param {string} status — backend state string (any case/format).
 * @param {'admin'|'worker'} [audience='admin'] — viewer perspective.
 * @returns {string}
 */
export function getStatusLabel(status, audience = 'admin') {
  const key = _normalise(status);
  if (audience === 'admin' && ADMIN_LABEL_OVERRIDES[key]) return ADMIN_LABEL_OVERRIDES[key];
  if (audience === 'worker' && WORKER_LABEL_OVERRIDES[key]) return WORKER_LABEL_OVERRIDES[key];
  return STATUS_LABELS[key] || _toTitle(status) || 'Unknown';
}

/**
 * Get the colour tone (green/amber/red/blue/gray) for a status.
 * Used by status pills, badges, and tile colours.
 */
export function getStatusTone(status) {
  return TONE_BY_KEY[_normalise(status)] || 'gray';
}

function _toTitle(s) {
  if (!s) return '';
  return String(s)
    .replace(/[_-]+/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}
