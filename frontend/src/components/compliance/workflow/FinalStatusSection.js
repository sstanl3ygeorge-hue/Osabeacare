import {
  CheckCircle,
  Clock,
  AlertTriangle,
  XCircle,
  ShieldCheck,
} from 'lucide-react';
import { Badge } from '../../ui/badge';
import { formatBackendDate } from '../../../lib/dateUtils';

const STATUS_DISPLAY = {
  verified: {
    icon: CheckCircle,
    iconClass: 'text-emerald-600',
    badge: 'bg-emerald-100 text-emerald-800 border-emerald-200',
    bg: 'bg-emerald-50 border-emerald-200',
  },
  pending: {
    icon: Clock,
    iconClass: 'text-amber-600',
    badge: 'bg-amber-100 text-amber-800 border-amber-200',
    bg: 'bg-amber-50 border-amber-200',
  },
  incomplete: {
    icon: AlertTriangle,
    iconClass: 'text-orange-600',
    badge: 'bg-orange-100 text-orange-800 border-orange-200',
    bg: 'bg-orange-50 border-orange-200',
  },
  failed: {
    icon: XCircle,
    iconClass: 'text-red-600',
    badge: 'bg-red-100 text-red-800 border-red-200',
    bg: 'bg-red-50 border-red-200',
  },
  overdue: {
    icon: AlertTriangle,
    iconClass: 'text-red-600',
    badge: 'bg-red-100 text-red-800 border-red-200',
    bg: 'bg-red-50 border-red-200',
  },
  expired: {
    icon: AlertTriangle,
    iconClass: 'text-red-600',
    badge: 'bg-red-100 text-red-800 border-red-200',
    bg: 'bg-red-50 border-red-200',
  },
  follow_up_overdue: {
    icon: AlertTriangle,
    iconClass: 'text-amber-600',
    badge: 'bg-amber-100 text-amber-800 border-amber-200',
    bg: 'bg-amber-50 border-amber-200',
  },
};

/**
 * FinalStatusSection — Step 5: System-computed final status
 *
 * CRITICAL: Status shown here is ALWAYS computed from data.
 * It is never manually set or overridden by the UI.
 *
 * Safeguards rendered here:
 * - `noEvidenceButCheckExists` — prevents showing "Verified" with no evidence
 * - `proofMissingButCheckVerified` — warning only; does not downgrade verified check status
 *
 * Props:
 *  workflow         — returned from useComplianceWorkflow
 *  requirementKey   — 'dbs' | 'right_to_work' | 'identity' | 'proof_of_address'
 *  checkRecord      — check_data from compliance-file (or null)
 */
export function FinalStatusSection({ workflow, requirementKey, checkRecord, statusUnavailable = false }) {
  if (statusUnavailable) {
    return (
      <div className="p-4 bg-gray-50/40" data-testid={`${requirementKey}-final-status-section`}>
        <div className="flex items-center gap-2 mb-3">
          <div className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 bg-gray-100 text-gray-500">
            5
          </div>
          <h4 className="text-sm font-semibold text-text-primary">Final Status</h4>
          <span className="text-xs text-text-muted">(system computed)</span>
        </div>
        <div className="flex items-start gap-3 p-3 rounded-lg border bg-gray-50 border-gray-200">
          <AlertTriangle className="h-5 w-5 text-gray-500 mt-0.5" />
          <div className="flex-1 min-w-0">
            <Badge className="text-xs px-2 py-0.5 border font-semibold bg-gray-100 text-gray-700 border-gray-200">
              Unavailable
            </Badge>
            <p className="text-xs text-gray-600 mt-1">
              Compliance status is temporarily unavailable for this section.
            </p>
          </div>
        </div>
      </div>
    );
  }
  const display =
    STATUS_DISPLAY[workflow.finalStatus] || STATUS_DISPLAY.pending;
  const Icon = display.icon;

  const getExplanation = () => {
    switch (workflow.finalStatus) {
      case 'verified':
        return 'All verification steps are complete. This requirement is satisfied.';

      case 'pending':
        if (!workflow.hasEvidence) return 'Awaiting evidence upload.';
        if (!workflow.hasAcceptedEvidence)
          return 'Evidence uploaded but not yet reviewed by an admin.';
        if (!workflow.hasCheck)
          return 'Evidence accepted. A formal check record must be recorded.';
        return 'Check recorded but not yet verified.';

      case 'incomplete':
        return 'Verification is incomplete.';

      case 'failed':
        if (workflow.hasRejectedEvidence && !workflow.hasAcceptedEvidence) {
          return 'Evidence has been rejected or requires replacement. This requirement is not satisfied.';
        }
        return 'The check outcome was "Failed". This requirement is not satisfied.';

      case 'overdue': {
        const dateStr = workflow.reviewDueAt
          ? 'on ' +
            new Date(workflow.reviewDueAt).toLocaleDateString('en-GB')
          : 'in the past';
        return `DBS recheck was due ${dateStr} and is overdue.`;
      }

      case 'expired': {
        const dateStr = workflow.permissionEndDate
          ? 'on ' +
            new Date(workflow.permissionEndDate).toLocaleDateString(
              'en-GB',
            )
          : '';
        return `Right to Work permission expired ${dateStr}. Re-verification is required.`;
      }

      case 'follow_up_overdue': {
        const dateStr = workflow.followUpDueAt
          ? 'on ' +
            new Date(workflow.followUpDueAt).toLocaleDateString('en-GB')
          : '';
        return `A follow-up check was due ${dateStr} and is overdue.`;
      }

      default:
        return workflow.finalStatusLabel;
    }
  };

  return (
    <div
      className="p-4 bg-gray-50/40"
      data-testid={`${requirementKey}-final-status-section`}
    >
      {/* ── Section header ─────────────────────────────────────────── */}
      <div className="flex items-center gap-2 mb-3">
        <div
          className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 ${
            workflow.finalStatus === 'verified'
              ? 'bg-emerald-100 text-emerald-700'
              : 'bg-gray-100 text-gray-500'
          }`}
        >
          {workflow.finalStatus === 'verified' ? (
            <CheckCircle className="h-3.5 w-3.5" />
          ) : (
            '5'
          )}
        </div>
        <h4 className="text-sm font-semibold text-text-primary">
          Final Status
        </h4>
        <span className="text-xs text-text-muted">(system computed)</span>
      </div>

      {/* ── Status display ─────────────────────────────────────────── */}
      <div
        className={`flex items-start gap-3 p-3 rounded-lg border ${display.bg}`}
      >
        <div className="flex-shrink-0 mt-0.5">
          <Icon className={`h-5 w-5 ${display.iconClass}`} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <Badge
              className={`text-xs px-2 py-0.5 border font-semibold ${display.badge}`}
            >
              {workflow.finalStatusLabel}
            </Badge>
            {workflow.finalStatus === 'verified' && (
              <ShieldCheck className="h-4 w-4 text-emerald-600 opacity-70" />
            )}
          </div>
          <p className="text-xs text-gray-600">{getExplanation()}</p>

          {/* Safeguard: check exists but no evidence */}
          {workflow.safeguards.noEvidenceButCheckExists && (
            <div className="mt-2 text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded p-2">
              <AlertTriangle className="h-3 w-3 inline mr-1" />
              A check record exists but no evidence files are present.
              Status remains Pending until evidence is uploaded and
              reviewed.
            </div>
          )}

          {/* Safeguard: check verified but proof missing */}
          {workflow.safeguards.proofMissingButCheckVerified && (
            <div className="mt-2 text-xs text-orange-700 bg-orange-50 border border-orange-200 rounded p-2">
              <AlertTriangle className="h-3 w-3 inline mr-1" />
              The check remains verified, but the proof document is missing.
              Upload proof in Step 4 for audit completeness.
            </div>
          )}
        </div>
      </div>

      {/* ── Last verified timestamp ─────────────────────────────────── */}
      {workflow.finalStatus === 'verified' && checkRecord?.checked_at && (
        <p className="text-[10px] text-text-muted mt-2">
          Last verified:{' '}
          {formatBackendDate(checkRecord.checked_at, { format: 'long' })}
        </p>
      )}
    </div>
  );
}
