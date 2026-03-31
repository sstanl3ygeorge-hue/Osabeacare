import { Button } from '../ui/button';
import { Eye, Upload, Send, RefreshCw, History, Shield, FileText } from 'lucide-react';

/**
 * RequirementActionBar - Standard action bar for all requirement sections
 * 
 * Provides consistent action slots:
 * - View (eye icon) - opens drawer/viewer
 * - Upload - upload new file
 * - Request - send initial request
 * - Resend - resend existing request
 * - Update - update check/record
 * - History - view history
 * 
 * Each action only appears if enabled (canX prop) and has a handler (onX prop)
 */
export default function RequirementActionBar({
  // View action (opens drawer)
  viewLabel = 'View',
  canView = false,
  onView,
  
  // Upload action
  uploadLabel = 'Upload',
  canUpload = false,
  onUpload,
  
  // Request action (send new)
  requestLabel = 'Request',
  canRequest = false,
  onRequest,
  
  // Resend action
  resendLabel = 'Resend',
  canResend = false,
  onResend,
  
  // Update action (update check)
  updateLabel = 'Update',
  canUpdate = false,
  onUpdate,
  
  // Record check action
  recordCheckLabel = 'Record Check',
  canRecordCheck = false,
  onRecordCheck,
  
  // History action
  canHistory = false,
  onHistory,
  
  // Compact mode - icons only
  compact = false,
  
  // Test ID prefix
  testIdPrefix = 'action'
}) {
  const buttonClass = compact 
    ? "h-8 w-8 p-0" 
    : "h-8 text-xs px-3";
  
  return (
    <div className="flex items-center gap-1.5">
      {/* View - Primary action when available */}
      {canView && onView && (
        <Button
          size="sm"
          variant="outline"
          onClick={onView}
          className={`${buttonClass} rounded-lg`}
          data-testid={`${testIdPrefix}-view`}
          title={viewLabel}
        >
          <Eye className={compact ? "h-4 w-4" : "h-3.5 w-3.5 mr-1"} />
          {!compact && viewLabel}
        </Button>
      )}
      
      {/* Upload */}
      {canUpload && onUpload && (
        <Button
          size="sm"
          variant="outline"
          onClick={onUpload}
          className={`${buttonClass} rounded-lg`}
          data-testid={`${testIdPrefix}-upload`}
          title={uploadLabel}
        >
          <Upload className={compact ? "h-4 w-4" : "h-3.5 w-3.5 mr-1"} />
          {!compact && uploadLabel}
        </Button>
      )}
      
      {/* Request (new) */}
      {canRequest && onRequest && (
        <Button
          size="sm"
          variant="outline"
          onClick={onRequest}
          className={`${buttonClass} text-blue-600 border-blue-200 hover:bg-blue-50 rounded-lg`}
          data-testid={`${testIdPrefix}-request`}
          title={requestLabel}
        >
          <Send className={compact ? "h-4 w-4" : "h-3.5 w-3.5 mr-1"} />
          {!compact && requestLabel}
        </Button>
      )}
      
      {/* Resend */}
      {canResend && onResend && (
        <Button
          size="sm"
          variant="outline"
          onClick={onResend}
          className={`${buttonClass} text-amber-600 border-amber-200 hover:bg-amber-50 rounded-lg`}
          data-testid={`${testIdPrefix}-resend`}
          title={resendLabel}
        >
          <RefreshCw className={compact ? "h-4 w-4" : "h-3.5 w-3.5 mr-1"} />
          {!compact && resendLabel}
        </Button>
      )}
      
      {/* Record Check */}
      {canRecordCheck && onRecordCheck && (
        <Button
          size="sm"
          variant="default"
          onClick={onRecordCheck}
          className={`${buttonClass} bg-primary hover:bg-primary-hover text-white rounded-lg`}
          data-testid={`${testIdPrefix}-record-check`}
          title={recordCheckLabel}
        >
          <Shield className={compact ? "h-4 w-4" : "h-3.5 w-3.5 mr-1"} />
          {!compact && recordCheckLabel}
        </Button>
      )}
      
      {/* Update */}
      {canUpdate && onUpdate && (
        <Button
          size="sm"
          variant="outline"
          onClick={onUpdate}
          className={`${buttonClass} rounded-lg`}
          data-testid={`${testIdPrefix}-update`}
          title={updateLabel}
        >
          <RefreshCw className={compact ? "h-4 w-4" : "h-3.5 w-3.5 mr-1"} />
          {!compact && updateLabel}
        </Button>
      )}
      
      {/* History */}
      {canHistory && onHistory && (
        <Button
          size="sm"
          variant="ghost"
          onClick={onHistory}
          className="h-8 w-8 p-0 text-text-muted hover:text-text-primary"
          data-testid={`${testIdPrefix}-history`}
          title="View History"
        >
          <History className="h-4 w-4" />
        </Button>
      )}
    </div>
  );
}
