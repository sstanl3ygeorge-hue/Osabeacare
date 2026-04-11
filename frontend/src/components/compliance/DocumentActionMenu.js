import { Button } from '../ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '../ui/dropdown-menu';
import { 
  MoreVertical, Eye, Download, CheckCircle, RotateCcw, 
  FileSearch, Trash2, ArrowRight, RefreshCw, History, Stamp, X
} from 'lucide-react';

/**
 * DocumentActionMenu - Per-file action dropdown menu
 * 
 * Simplified UX following 5 E's of Usability:
 * - Primary actions: View, Download (always visible)
 * - Verification: Verify OR Request Replacement (mutually exclusive states)
 * - Admin Actions: Grouped under "More Actions" to reduce clutter
 */
export default function DocumentActionMenu({
  file,
  onView,
  onDownload,
  onVerify,
  onRequestReplacement,
  onRejectEvidence,
  onReject,
  onExtractReview,
  onRemoveStamp,
  onMarkUploadedInError,
  onSupersede,
  onMoveCategory,
  onViewHistory,
  isAuditor = false,
  isProcessing = false
}) {
  // Simplified state checks
  // IMPORTANT: Exclude "not_verified" which is a placeholder value, not an actual stamp
  const hasValidStamp = file.verification_stamp && 
    file.verification_stamp !== 'not_verified' && 
    file.verification_stamp !== '';
  const isVerified = file.verified || hasValidStamp || file.stamped_file_url;
  const hasExtraction = file.extraction_status?.status === 'awaiting_review';
  const isActiveFile = !['superseded', 'uploaded_in_error', 'rejected', 'deleted'].includes(file.status);
  
  // Determine primary action based on file state
  const showVerifyAction = !isVerified && isActiveFile && !isAuditor;
  const showRemoveStamp = isVerified && !isAuditor;
  const canRequestReplacement = !isAuditor && isActiveFile && !!(onRequestReplacement || onReject);
  const canRejectEvidence = !isAuditor && isActiveFile && !!(onRejectEvidence || onReject);

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button 
          variant="ghost" 
          size="sm" 
          className="h-8 w-8 p-0"
          disabled={isProcessing}
          data-testid={`file-action-menu-${file.file_id}`}
        >
          <MoreVertical className="h-4 w-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-52">
        {/* Primary Actions - Always visible */}
        {onView && (
          <DropdownMenuItem onClick={onView} data-testid="action-view">
            <Eye className="h-4 w-4 mr-2" />
            View File
          </DropdownMenuItem>
        )}
        {onDownload && (
          <DropdownMenuItem onClick={onDownload} data-testid="action-download">
            <Download className="h-4 w-4 mr-2" />
            Download
          </DropdownMenuItem>
        )}

        {/* Extraction Review - High priority if pending */}
        {hasExtraction && onExtractReview && !isAuditor && (
          <>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={onExtractReview} data-testid="action-extract-review">
              <FileSearch className="h-4 w-4 mr-2 text-purple-600" />
              <span className="text-purple-600 font-medium">Review Extraction</span>
            </DropdownMenuItem>
          </>
        )}

        {/* Verification Section */}
        {!isAuditor && (showVerifyAction || showRemoveStamp) && (
          <>
            <DropdownMenuSeparator />
            {showVerifyAction && onVerify && (
              <DropdownMenuItem onClick={onVerify} data-testid="action-verify">
                <CheckCircle className="h-4 w-4 mr-2 text-green-600" />
                <span className="text-green-600 font-medium">Verify & Stamp</span>
              </DropdownMenuItem>
            )}
            {showRemoveStamp && onRemoveStamp && (
              <DropdownMenuItem onClick={onRemoveStamp} data-testid="action-remove-stamp">
                <Stamp className="h-4 w-4 mr-2 text-amber-600" />
                <span className="text-amber-600">Remove Stamp</span>
              </DropdownMenuItem>
            )}
          </>
        )}

        {/* Document Management - Only for active files, non-auditors */}
        {!isAuditor && isActiveFile && (
          <>
            <DropdownMenuSeparator />
            {/* Amendment path: keep audit reason and ask worker to re-upload */}
            {canRequestReplacement && (
              <DropdownMenuItem
                onClick={onRequestReplacement || onReject}
                data-testid="action-request-replacement"
              >
                <RotateCcw className="h-4 w-4 mr-2 text-amber-600" />
                <span className="text-amber-600">Request Replacement (Amendment)</span>
              </DropdownMenuItem>
            )}
            {/* Hard reject path: explicit evidence rejection */}
            {canRejectEvidence && (
              <DropdownMenuItem
                onClick={onRejectEvidence || onReject}
                data-testid="action-reject-evidence"
              >
                <X className="h-4 w-4 mr-2 text-red-600" />
                <span className="text-red-600">Reject Evidence</span>
              </DropdownMenuItem>
            )}
            {/* Mark as error - when file shouldn't be here */}
            {onMarkUploadedInError && (
              <DropdownMenuItem onClick={onMarkUploadedInError} data-testid="action-mark-error" className="text-red-600">
                <Trash2 className="h-4 w-4 mr-2" />
                Remove (Uploaded in Error - Admin Cleanup)
              </DropdownMenuItem>
            )}
          </>
        )}

        {/* Advanced Actions - Hidden in submenu or shown sparingly */}
        {!isAuditor && isActiveFile && (onSupersede || onMoveCategory) && (
          <>
            <DropdownMenuSeparator />
            {onMoveCategory && (
              <DropdownMenuItem onClick={onMoveCategory} data-testid="action-move" className="text-gray-600">
                <ArrowRight className="h-4 w-4 mr-2" />
                Move to Category
              </DropdownMenuItem>
            )}
            {onSupersede && (
              <DropdownMenuItem onClick={onSupersede} data-testid="action-supersede" className="text-gray-600">
                <RefreshCw className="h-4 w-4 mr-2" />
                Archive & Replace
              </DropdownMenuItem>
            )}
          </>
        )}

        {/* History - Always available */}
        {onViewHistory && (
          <>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={onViewHistory} data-testid="action-history">
              <History className="h-4 w-4 mr-2" />
              File History
            </DropdownMenuItem>
          </>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
