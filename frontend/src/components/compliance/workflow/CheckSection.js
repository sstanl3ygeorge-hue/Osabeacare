import {
  Shield,
  CheckCircle,
  AlertTriangle,
  Clock,
  Plus,
  Edit2,
  Trash2,
} from 'lucide-react';
import { Button } from '../../ui/button';
import { Badge } from '../../ui/badge';
import { formatBackendDate } from '../../../lib/dateUtils';

const METHOD_LABELS = {
  home_office_online_check: 'Home Office Online Check',
  manual_passport_uk_irish: 'Manual – UK/Irish Passport',
  manual_list_a_document: 'Manual – List A Document',
  manual_list_b_group_1: 'Manual – List B Group 1',
  manual_list_b_group_2_ecs: 'Manual – List B Group 2 / ECS',
  idsp_check: 'Digital Verification Service (IDSP)',
  ecs_pvn_check: 'Employer Checking Service (PVN)',
  dbs_certificate_review: 'DBS Certificate Review',
  dbs_update_service_check: 'DBS Update Service Check',
};

const OUTCOME_CONFIG = {
  verified: {
    label: 'Verified',
    className: 'bg-emerald-100 text-emerald-700 border-emerald-200',
  },
  failed: {
    label: 'Rejected / action required',
    className: 'bg-red-100 text-red-700 border-red-200',
  },
  follow_up_required: {
    label: 'Follow-up Required',
    className: 'bg-amber-100 text-amber-700 border-amber-200',
  },
  awaiting_review: {
    label: 'Awaiting admin review',
    className: 'bg-gray-100 text-gray-600 border-gray-200',
  },
  in_progress: {
    label: 'In Progress',
    className: 'bg-blue-100 text-blue-700 border-blue-200',
  },
};

/**
 * CheckSection — Step 3: Record formal check
 *
 * RULES:
 * - Cannot record a check without accepted evidence
 * - Check actions do NOT affect evidence files
 * - "Edit Check" re-records over the existing current check
 * - "Invalidate" prompts re-recording (no direct delete endpoint)
 *
 * Props:
 *  requirementKey   'dbs' | 'right_to_work' | 'identity' | 'proof_of_address'
 *  checkRecord      check_data from compliance-file API (or null)
 *  hasAcceptedEvidence  bool — gates record-check action
 *  isAdminView      bool
 *  onRecordCheck    () => void — opens RecordCheckDialog
 *  onInvalidate     () => void
 */
export function CheckSection({
  requirementKey,
  checkRecord,
  hasAcceptedEvidence,
  isAdminView = true,
  onRecordCheck,
  onInvalidate,
}) {
  const isRTW = requirementKey === 'right_to_work';
  const isDBS = requirementKey === 'dbs';
  const isIdentity = requirementKey === 'identity';
  const isAddress = requirementKey === 'proof_of_address';
  const hasCheck = !!checkRecord;
  const outcome = checkRecord?.outcome;
  const outcomeConfig = OUTCOME_CONFIG[outcome] || OUTCOME_CONFIG.awaiting_review;
  const stepComplete = hasCheck && outcome === 'verified';

  const recheckDate =
    checkRecord?.review_due_at || checkRecord?.next_recheck_date;
  const recheckOverdue = recheckDate
    ? new Date(recheckDate) < new Date()
    : false;

  return (
    <div
      className="p-4 bg-gray-50/40"
      data-testid={`${requirementKey}-check-section`}
    >
      {/* ── Section header ────────────────────────────────────────── */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div
            className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 ${
              stepComplete
                ? 'bg-emerald-100 text-emerald-700'
                : 'bg-primary/10 text-primary'
            }`}
          >
            {stepComplete ? <CheckCircle className="h-3.5 w-3.5" /> : '3'}
          </div>
          <h4 className="text-sm font-semibold text-text-primary">
            {isRTW
              ? 'Right to Work Check'
              : isDBS
                ? 'DBS Status Check'
                : isIdentity
                  ? 'Identity Verification Check'
                  : isAddress
                    ? 'Address Verification Check'
                    : 'Check Record'}
          </h4>
        </div>
        {isAdminView && hasCheck && (
          <Badge
            className={`text-[10px] px-1.5 py-0 border ${outcomeConfig.className}`}
          >
            {outcomeConfig.label}
          </Badge>
        )}
      </div>

      {hasCheck ? (
        <div className="space-y-3">
          {/* ── Check details ─────────────────────────────────────── */}
          <div className="bg-white border border-gray-200 rounded-lg p-3 space-y-3 text-sm">
            {/* Common fields */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <span className="text-xs text-text-muted block mb-0.5">
                  Method
                </span>
                <span className="font-medium text-text-primary text-xs leading-tight">
                  {METHOD_LABELS[checkRecord.method] ||
                    checkRecord.method?.replace(/_/g, ' ') ||
                    '—'}
                </span>
              </div>
              <div>
                <span className="text-xs text-text-muted block mb-0.5">
                  Date Checked
                </span>
                <span className="font-medium text-text-primary text-xs">
                  {checkRecord.checked_at
                    ? formatBackendDate(checkRecord.checked_at, {
                        format: 'medium',
                      })
                    : '—'}
                </span>
              </div>
            </div>

            {/* RTW-specific fields */}
            {isRTW && (
              <>
                {checkRecord.permission_type && (
                  <div>
                    <span className="text-xs text-text-muted block mb-0.5">
                      Permission Type
                    </span>
                    <span className="font-medium text-xs">
                      {checkRecord.permission_type}
                    </span>
                  </div>
                )}
                <div className="grid grid-cols-2 gap-3">
                  {checkRecord.is_indefinite ? (
                    <div>
                      <span className="text-xs text-text-muted block mb-0.5">
                        Duration
                      </span>
                      <Badge className="text-[10px] px-1.5 py-0 bg-blue-100 text-blue-700 border-blue-200">
                        Indefinite / Permanent
                      </Badge>
                    </div>
                  ) : checkRecord.permission_end_date ? (
                    <div>
                      <span className="text-xs text-text-muted block mb-0.5">
                        Permission Expires
                      </span>
                      <span
                        className={`font-medium text-xs ${
                          new Date(checkRecord.permission_end_date) <
                          new Date()
                            ? 'text-red-600'
                            : ''
                        }`}
                      >
                        {formatBackendDate(checkRecord.permission_end_date, {
                          format: 'medium',
                        })}
                      </span>
                    </div>
                  ) : null}
                  {checkRecord.restrictions && (
                    <div>
                      <span className="text-xs text-text-muted block mb-0.5">
                        Restrictions
                      </span>
                      <span className="font-medium text-xs text-amber-700">
                        {checkRecord.restrictions}
                      </span>
                    </div>
                  )}
                </div>
                {checkRecord.follow_up_required && (
                  <div
                    className={`rounded p-2 text-xs border ${
                      checkRecord.follow_up_due_at &&
                      new Date(checkRecord.follow_up_due_at) < new Date()
                        ? 'bg-red-50 border-red-200 text-red-700'
                        : 'bg-amber-50 border-amber-200 text-amber-700'
                    }`}
                  >
                    <AlertTriangle className="h-3 w-3 inline mr-1" />
                    Follow-up required
                    {checkRecord.follow_up_due_at &&
                      ': ' +
                        formatBackendDate(checkRecord.follow_up_due_at, {
                          format: 'medium',
                        })}
                  </div>
                )}
              </>
            )}

            {/* DBS-specific fields */}
            {isDBS && (
              <>
                <div className="grid grid-cols-2 gap-3">
                  {checkRecord.dbs_level && (
                    <div>
                      <span className="text-xs text-text-muted block mb-0.5">
                        DBS Level
                      </span>
                      <span className="font-medium text-xs capitalize">
                        {checkRecord.dbs_level.replace(/_/g, ' ')}
                      </span>
                    </div>
                  )}
                  {checkRecord.result_status && (
                    <div>
                      <span className="text-xs text-text-muted block mb-0.5">
                        Result
                      </span>
                      <Badge
                        className={`text-[10px] px-1.5 py-0 border ${
                          checkRecord.result_status === 'clear'
                            ? 'bg-emerald-100 text-emerald-700 border-emerald-200'
                            : 'bg-amber-100 text-amber-700 border-amber-200'
                        }`}
                      >
                        {checkRecord.result_status === 'clear'
                          ? 'Clear'
                          : 'Information Present'}
                      </Badge>
                    </div>
                  )}
                </div>
                {checkRecord.certificate_number && (
                  <div>
                    <span className="text-xs text-text-muted block mb-0.5">
                      Certificate No.
                    </span>
                    <span className="font-medium font-mono text-xs">
                      {checkRecord.certificate_number}
                    </span>
                  </div>
                )}
                {checkRecord.result_summary && (
                  <div>
                    <span className="text-xs text-text-muted block mb-0.5">
                      Summary
                    </span>
                    <span className="text-xs text-gray-700">
                      {checkRecord.result_summary}
                    </span>
                  </div>
                )}
                {checkRecord.recheck_required && (
                  <div
                    className={`rounded p-2 text-xs border ${
                      recheckOverdue
                        ? 'bg-red-50 border-red-200 text-red-700'
                        : 'bg-amber-50 border-amber-200 text-amber-700'
                    }`}
                  >
                    <Clock className="h-3 w-3 inline mr-1" />
                    Recheck required
                    {recheckDate &&
                      ': ' + formatBackendDate(recheckDate, { format: 'medium' })}
                    {recheckOverdue && ' — OVERDUE'}
                  </div>
                )}
              </>
            )}

            {/* Checked by */}
            {checkRecord.checked_by_name && (
              <div>
                <span className="text-xs text-text-muted block mb-0.5">
                  Checked by
                </span>
                <span className="text-xs text-gray-600">
                  {checkRecord.checked_by_name}
                </span>
              </div>
            )}

            {/* Notes */}
            {checkRecord.notes && (
              <div>
                <span className="text-xs text-text-muted block mb-0.5">
                  Notes
                </span>
                <span className="text-xs text-gray-600">
                  {checkRecord.notes}
                </span>
              </div>
            )}
          </div>

          {/* ── Admin actions ──────────────────────────────────────── */}
          {isAdminView && (
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="outline"
                className="h-7 text-xs"
                onClick={onRecordCheck}
                data-testid={`${requirementKey}-edit-check-btn`}
              >
                <Edit2 className="h-3 w-3 mr-1" />
                Edit Check
              </Button>
              {onInvalidate && (
                <Button
                  size="sm"
                  variant="ghost"
                  className="h-7 text-xs text-red-500 hover:text-red-700 hover:bg-red-50"
                  onClick={onInvalidate}
                  data-testid={`${requirementKey}-invalidate-check-btn`}
                >
                  <Trash2 className="h-3 w-3 mr-1" />
                  Invalidate
                </Button>
              )}
            </div>
          )}
        </div>
      ) : (
        /* ── No check recorded ────────────────────────────────────── */
        <div
          className={`p-3 bg-white border rounded-lg transition-opacity ${
            !hasAcceptedEvidence
              ? 'border-gray-200 opacity-60'
              : 'border-dashed border-amber-300'
          }`}
        >
          <div className="flex items-center justify-between gap-3">
            <div className="min-w-0">
              <div className="flex items-center gap-1.5">
                <Shield className="h-4 w-4 text-gray-400" />
                <p className="text-sm text-text-muted">No check recorded</p>
              </div>
              {!hasAcceptedEvidence && (
                <p className="text-xs text-amber-700 mt-0.5">
                  <AlertTriangle className="h-3 w-3 inline mr-1" />
                  Accept evidence in Step 2 before recording a check
                </p>
              )}
            </div>
            {isAdminView && (
              <Button
                size="sm"
                variant="default"
                className="h-8 text-xs flex-shrink-0"
                onClick={onRecordCheck}
                disabled={!hasAcceptedEvidence}
                data-testid={`${requirementKey}-record-check-btn`}
              >
                <Plus className="h-3.5 w-3.5 mr-1" />
                Record Check
              </Button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
