export const APPLICANT_STATUSES = ['new', 'screening', 'interview', 'compliance_review'];
export const EMPLOYEE_STATUSES = ['onboarding', 'active', 'inactive'];
export const TERMINAL_STATUSES = ['archived', 'withdrawn', 'superseded'];

const LEGACY_STATUS_MAP = {
  active_employee: 'active',
};

export function normalizeLifecycleStatus(status) {
  const value = String(status || '').trim().toLowerCase();
  return LEGACY_STATUS_MAP[value] || value;
}

export function isApplicantStatus(status) {
  return APPLICANT_STATUSES.includes(normalizeLifecycleStatus(status));
}

export function isEmployeeStatus(status) {
  return EMPLOYEE_STATUSES.includes(normalizeLifecycleStatus(status));
}

export function derivePersonStageFromStatus(status) {
  const normalized = normalizeLifecycleStatus(status);
  if (isApplicantStatus(normalized)) return 'applicant';
  if (isEmployeeStatus(normalized)) return 'employee';
  if (TERMINAL_STATUSES.includes(normalized)) return 'employee';
  return 'applicant';
}

export function getCanonicalPersonStage(person) {
  const statusStage = derivePersonStageFromStatus(person?.status);
  const rawStage = String(person?.person_stage || '').toLowerCase();
  return rawStage === 'employee' || rawStage === 'applicant' ? rawStage : statusStage;
}

export function isActiveLifecycleStatus(status) {
  return normalizeLifecycleStatus(status) === 'active';
}

