import {
  normalizeLifecycleStatus,
  isApplicantStatus,
  isEmployeeStatus,
  derivePersonStageFromStatus,
  isActiveLifecycleStatus,
} from './lifecycle';

describe('lifecycle helpers', () => {
  test('normalizes legacy active_employee to active', () => {
    expect(normalizeLifecycleStatus('active_employee')).toBe('active');
  });

  test('maps applicant statuses correctly', () => {
    expect(isApplicantStatus('new')).toBe(true);
    expect(isApplicantStatus('screening')).toBe(true);
    expect(isApplicantStatus('active')).toBe(false);
  });

  test('maps employee statuses correctly', () => {
    expect(isEmployeeStatus('onboarding')).toBe(true);
    expect(isEmployeeStatus('active_employee')).toBe(true);
    expect(isEmployeeStatus('interview')).toBe(false);
  });

  test('derives person stage from status', () => {
    expect(derivePersonStageFromStatus('interview')).toBe('applicant');
    expect(derivePersonStageFromStatus('active_employee')).toBe('employee');
  });

  test('active lifecycle guard uses canonical status', () => {
    expect(isActiveLifecycleStatus('active')).toBe(true);
    expect(isActiveLifecycleStatus('active_employee')).toBe(true);
    expect(isActiveLifecycleStatus('onboarding')).toBe(false);
  });
});

