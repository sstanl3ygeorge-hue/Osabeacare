import { useState } from 'react';
import { Badge } from '../ui/badge';
import { 
  FileText, CheckCircle, Clock, AlertTriangle, Upload as UploadIcon,
  Eye, Send, RefreshCw, Shield
} from 'lucide-react';
import RequirementSectionShell from './RequirementSectionShell';
import RequirementActionBar from './RequirementActionBar';
import { formatBackendDate } from '../../lib/dateUtils';

/**
 * UploadRequirementCard - Unified card for upload-based requirements
 * 
 * Used for: Right to Work, DBS, Identity, Proof of Address
 * 
 * Shows:
 * - Evidence row (files) with upload/request actions
 * - Check row (verification) with record/update actions
 * - Request lifecycle status
 * - File previews when expanded
 */
export default function UploadRequirementCard({
  surface,
  isOpen,
  onToggle,
  onOpenDrawer,
  onUpload,
  onRequest,
  onResend,
  onRecordCheck,
  onUpdateCheck,
  onViewHistory,
  isAuditor = false
}) {
  if (!surface) return null;

  const {
    key,
    label,
    activeFiles,
    historicalFiles,
    latestRequest,
    authoritativeCheck,
    summary,
    counters,
    requestState,
    rowStatus,
    rules
  } = surface;

  // Determine blocking status
  const isBlocking = rowStatus === 'missing' || rowStatus === 'rejected' || rowStatus === 'replacement_required';
  const blockingLabel = isBlocking ? 'Blocking' : null;

  // Determine available actions
  const hasFiles = counters.active > 0;
  const hasCheck = !!authoritativeCheck;
  const checkVerified = authoritativeCheck?.status === 'verified';
  const hasPendingRequest = requestState === 'requested' || requestState === 'viewed';

  return (
    <RequirementSectionShell
      title={label}
      summary={summary}
      blockingLabel={blockingLabel}
      isOpen={isOpen}
      onToggle={onToggle}
      testId={`upload-requirement-${key}`}
      actions={
        <RequirementActionBar
          viewLabel="View Files"
          canView={hasFiles}
          onView={onOpenDrawer}
          canUpload={!isAuditor}
          onUpload={onUpload}
          canRequest={!isAuditor && !hasPendingRequest && !hasFiles}
          onRequest={onRequest}
          canResend={!isAuditor && hasPendingRequest}
          onResend={onResend}
          testIdPrefix={`${key}-action`}
        />
      }
    >
      <div className="space-y-4">
        {/* Evidence Section */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-medium text-text-primary flex items-center gap-2">
              <FileText className="h-4 w-4 text-gray-400" />
              Evidence Files
            </h4>
            <div className="flex items-center gap-2">
              {counters.active > 0 && (
                <Badge className="text-[10px] px-1.5 py-0 bg-blue-100 text-blue-700 border border-blue-200">
                  {counters.active} active
                </Badge>
              )}
              {counters.pendingReview > 0 && (
                <Badge className="text-[10px] px-1.5 py-0 bg-amber-100 text-amber-700 border border-amber-200">
                  {counters.pendingReview} pending review
                </Badge>
              )}
              {counters.historical > 0 && (
                <Badge className="text-[10px] px-1.5 py-0 bg-gray-100 text-gray-500 border border-gray-200">
                  {counters.historical} historical
                </Badge>
              )}
            </div>
          </div>

          {/* Active Files Preview */}
          {activeFiles.length > 0 ? (
            <div className="space-y-2">
              {activeFiles.slice(0, 3).map((file) => (
                <div 
                  key={file.file_id || file.id}
                  className="flex items-center justify-between p-3 bg-white border border-gray-200 rounded-lg"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <FileText className="h-4 w-4 text-gray-400 flex-shrink-0" />
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-text-primary truncate">
                        {file.file_name || file.original_filename || 'Document'}
                      </p>
                      <p className="text-xs text-text-muted">
                        {formatBackendDate(file.uploaded_at, { format: 'medium' })}
                        {file.uploaded_by && ` • ${file.uploaded_by}`}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {file.verified ? (
                      <Badge className="text-[10px] px-1.5 py-0 bg-green-100 text-green-700 border border-green-200">
                        <CheckCircle className="h-2.5 w-2.5 mr-0.5" />
                        Verified
                      </Badge>
                    ) : file.extraction_status?.status === 'awaiting_review' ? (
                      <Badge className="text-[10px] px-1.5 py-0 bg-purple-100 text-purple-700 border border-purple-200">
                        <Clock className="h-2.5 w-2.5 mr-0.5" />
                        Extraction pending
                      </Badge>
                    ) : (
                      <Badge className="text-[10px] px-1.5 py-0 bg-amber-100 text-amber-700 border border-amber-200">
                        <Clock className="h-2.5 w-2.5 mr-0.5" />
                        Awaiting review
                      </Badge>
                    )}
                  </div>
                </div>
              ))}
              {activeFiles.length > 3 && (
                <button 
                  onClick={onOpenDrawer}
                  className="text-sm text-blue-600 hover:text-blue-700 font-medium"
                >
                  + {activeFiles.length - 3} more file{activeFiles.length - 3 !== 1 ? 's' : ''}
                </button>
              )}
            </div>
          ) : (
            <div className="p-4 bg-gray-50 border border-gray-200 rounded-lg text-center">
              <UploadIcon className="h-6 w-6 text-gray-300 mx-auto mb-2" />
              <p className="text-sm text-text-muted">No active files</p>
              {rules?.minimumFilesRequired && (
                <p className="text-xs text-text-muted mt-1">
                  {rules.minimumFilesRequired} file{rules.minimumFilesRequired !== 1 ? 's' : ''} required
                </p>
              )}
            </div>
          )}

          {/* Request Status */}
          {latestRequest && (
            <div className={`p-3 rounded-lg border ${
              requestState === 'submitted' ? 'bg-green-50 border-green-200' :
              requestState === 'viewed' ? 'bg-purple-50 border-purple-200' :
              requestState === 'requested' ? 'bg-blue-50 border-blue-200' :
              'bg-gray-50 border-gray-200'
            }`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Send className={`h-4 w-4 ${
                    requestState === 'submitted' ? 'text-green-600' :
                    requestState === 'viewed' ? 'text-purple-600' :
                    requestState === 'requested' ? 'text-blue-600' :
                    'text-gray-500'
                  }`} />
                  <span className="text-sm font-medium">
                    {requestState === 'submitted' ? 'Response submitted' :
                     requestState === 'viewed' ? 'Request viewed' :
                     requestState === 'requested' ? 'Request sent' :
                     requestState === 'replacement_requested' ? 'Replacement requested' :
                     'Request status'}
                  </span>
                </div>
                {latestRequest.sent_at && (
                  <span className="text-xs text-text-muted">
                    {formatBackendDate(latestRequest.sent_at, { format: 'relative' })}
                  </span>
                )}
              </div>
              {latestRequest.viewed_at && requestState !== 'viewed' && (
                <p className="text-xs text-text-muted mt-1 ml-6">
                  Viewed {formatBackendDate(latestRequest.viewed_at, { format: 'relative' })}
                </p>
              )}
              {latestRequest.reminder_count > 0 && (
                <p className="text-xs text-amber-600 mt-1 ml-6">
                  {latestRequest.reminder_count} reminder{latestRequest.reminder_count !== 1 ? 's' : ''} sent
                </p>
              )}
            </div>
          )}
        </div>

        {/* Check/Verification Section */}
        <div className="pt-4 border-t border-gray-200">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-medium text-text-primary flex items-center gap-2">
              <Shield className="h-4 w-4 text-gray-400" />
              Verification Check
            </h4>
            {!isAuditor && (
              <RequirementActionBar
                compact
                canRecordCheck={!hasCheck}
                onRecordCheck={onRecordCheck}
                canUpdate={hasCheck}
                onUpdate={onUpdateCheck}
                testIdPrefix={`${key}-check-action`}
              />
            )}
          </div>

          {authoritativeCheck ? (
            <div className={`mt-3 p-3 rounded-lg border ${
              checkVerified ? 'bg-green-50 border-green-200' : 'bg-amber-50 border-amber-200'
            }`}>
              <div className="flex items-center gap-2">
                {checkVerified ? (
                  <CheckCircle className="h-4 w-4 text-green-600" />
                ) : (
                  <AlertTriangle className="h-4 w-4 text-amber-600" />
                )}
                <span className={`text-sm font-medium ${checkVerified ? 'text-green-700' : 'text-amber-700'}`}>
                  {checkVerified ? 'Verified' : authoritativeCheck.status || 'Pending'}
                </span>
              </div>
              {authoritativeCheck.method && (
                <p className="text-xs text-text-muted mt-1 ml-6">
                  Method: {authoritativeCheck.method}
                </p>
              )}
              {authoritativeCheck.checked_at && (
                <p className="text-xs text-text-muted ml-6">
                  Checked: {formatBackendDate(authoritativeCheck.checked_at, { format: 'medium' })}
                  {authoritativeCheck.checked_by && ` by ${authoritativeCheck.checked_by}`}
                </p>
              )}
              {authoritativeCheck.follow_up_date && (
                <p className="text-xs text-blue-600 ml-6">
                  Follow-up: {formatBackendDate(authoritativeCheck.follow_up_date, { format: 'medium' })}
                </p>
              )}
            </div>
          ) : (
            <div className="mt-3 p-4 bg-gray-50 border border-gray-200 rounded-lg text-center">
              <Shield className="h-6 w-6 text-gray-300 mx-auto mb-2" />
              <p className="text-sm text-text-muted">No check recorded</p>
              <p className="text-xs text-text-muted mt-1">
                Record a verification check to complete this requirement
              </p>
            </div>
          )}
        </div>

        {/* Footer with counters and history */}
        <div className="pt-4 border-t border-gray-100 flex items-center justify-between">
          <div className="flex items-center gap-4 text-xs text-text-muted">
            <span>{counters.active} active</span>
            <span>{counters.pendingReview} pending</span>
            <span>{counters.historical} historical</span>
          </div>
          {onViewHistory && (
            <button
              onClick={() => onViewHistory(key, label)}
              className="text-xs text-text-muted hover:text-text-primary flex items-center gap-1"
              data-testid={`${key}-view-history`}
            >
              View History
            </button>
          )}
        </div>
      </div>
    </RequirementSectionShell>
  );
}
