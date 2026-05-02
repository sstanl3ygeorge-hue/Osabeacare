import { Briefcase, UserCheck, AlertCircle, Archive } from 'lucide-react';

/**
 * Small status pill that makes the employee's lifecycle stage explicit
 * (Tier 1 fix #2). Without this, admins and workers couldn't tell at a
 * glance whether they were viewing an "applicant in onboarding" or an
 * "active employee" — and the meaning of every counter on the page shifts
 * between those stages.
 *
 * Usage:
 *   <LifecycleStagePill status={employee.status} stage={employee.person_stage} />
 */
export default function LifecycleStagePill({ status, stage, className = '' }) {
  const config = resolveConfig(status, stage);
  const Icon = config.icon;
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${config.classes} ${className}`}
      data-testid="lifecycle-stage-pill"
      title={config.tooltip}
    >
      <Icon className="h-3.5 w-3.5" />
      {config.label}
    </span>
  );
}

function resolveConfig(status, stage) {
  const s = String(status || '').toLowerCase();
  const st = String(stage || '').toLowerCase();

  if (s === 'active' || st === 'employee') {
    return {
      label: 'Active employee',
      icon: UserCheck,
      classes: 'bg-green-100 text-green-800',
      tooltip: 'On payroll and working — ongoing compliance only.',
    };
  }
  if (s === 'archived' || s === 'inactive' || s === 'terminated') {
    return {
      label: 'Archived',
      icon: Archive,
      classes: 'bg-gray-200 text-gray-700',
      tooltip: 'No longer employed. Records retained for audit.',
    };
  }
  if (s === 'onboarding') {
    return {
      label: 'Onboarding',
      icon: Briefcase,
      classes: 'bg-blue-100 text-blue-800',
      tooltip: 'Approved for recruitment — completing pre-employment setup.',
    };
  }
  // Default: applicant / unknown
  return {
    label: 'Applicant',
    icon: AlertCircle,
    classes: 'bg-amber-100 text-amber-800',
    tooltip: 'Pre-recruitment. Awaiting full compliance pack and approval.',
  };
}
