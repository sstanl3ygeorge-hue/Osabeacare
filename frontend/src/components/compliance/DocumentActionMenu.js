import { Button } from '../ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '../ui/dropdown-menu';
import { 
  MoreVertical, Eye, Download, CheckCircle, XCircle, 
  FileSearch, Trash2, ArrowRight, RefreshCw, History, Stamp
} from 'lucide-react';

/**
 * DocumentActionMenu - Per-file action dropdown menu
 * 
 * Actions shown based on backend-allowed actions and file state:
 * - View / Download (always)
 * - Review Extraction (if extraction pending)
 * - Verify / Reject (if awaiting verification)
 * - Remove Stamp (if stamped)
 * - Mark Uploaded in Error
 * - Supersede / Replace
 * - Move Category
 * - View File History
 */
export default function DocumentActionMenu({
  file,
  onView,
  onDownload,
  onVerify,
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
  // Determine what actions to show based on file state
  const hasExtraction = file.extraction_status?.status === 'awaiting_review';
  const canVerify = !file.verified && !file.rejected && file.status !== 'superseded';
  const canReject = !file.verified && !file.rejected && file.status !== 'superseded';
  const canRemoveStamp = !!file.verification_stamp || !!file.stamped_file_url;
  const canMarkError = file.status !== 'uploaded_in_error' && file.status !== 'superseded';
  const canSupersede = file.status !== 'superseded' && file.status !== 'uploaded_in_error';
  const canMove = file.status !== 'superseded' && file.status !== 'uploaded_in_error' && file.status !== 'rejected';

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
      <DropdownMenuContent align="end" className="w-48">
        {/* View & Download - Always available */}
        {onView && (
          <DropdownMenuItem onClick={onView} data-testid="action-view">
            <Eye className="h-4 w-4 mr-2" />
            View
          </DropdownMenuItem>
        )}
        {onDownload && (
          <DropdownMenuItem onClick={onDownload} data-testid="action-download">
            <Download className="h-4 w-4 mr-2" />
            Download
          </DropdownMenuItem>
        )}

        {/* Extraction Review - If extraction pending */}
        {hasExtraction && onExtractReview && !isAuditor && (
          <>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={onExtractReview} data-testid="action-extract-review">
              <FileSearch className="h-4 w-4 mr-2 text-purple-600" />
              <span className="text-purple-600">Review Extraction</span>
            </DropdownMenuItem>
          </>
        )}

        {/* Verification Actions - If not auditor */}
        {!isAuditor && (canVerify || canReject) && (
          <>
            <DropdownMenuSeparator />
            {canVerify && onVerify && (
              <DropdownMenuItem onClick={onVerify} data-testid="action-verify">
                <CheckCircle className="h-4 w-4 mr-2 text-green-600" />
                <span className="text-green-600">Verify</span>
              </DropdownMenuItem>
            )}
            {canReject && onReject && (
              <DropdownMenuItem onClick={onReject} data-testid="action-reject">
                <XCircle className="h-4 w-4 mr-2 text-red-600" />
                <span className="text-red-600">Reject</span>
              </DropdownMenuItem>
            )}
          </>
        )}

        {/* Remove Stamp - If file has a stamp */}
        {!isAuditor && canRemoveStamp && onRemoveStamp && (
          <>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={onRemoveStamp} data-testid="action-remove-stamp">
              <Stamp className="h-4 w-4 mr-2 text-amber-600" />
              <span className="text-amber-600">Remove Stamp</span>
            </DropdownMenuItem>
          </>
        )}

        {/* File Management Actions - If not auditor */}
        {!isAuditor && (canMarkError || canSupersede || canMove) && (
          <>
            <DropdownMenuSeparator />
            {canSupersede && onSupersede && (
              <DropdownMenuItem onClick={onSupersede} data-testid="action-supersede">
                <RefreshCw className="h-4 w-4 mr-2" />
                Supersede / Replace
              </DropdownMenuItem>
            )}
            {canMove && onMoveCategory && (
              <DropdownMenuItem onClick={onMoveCategory} data-testid="action-move">
                <ArrowRight className="h-4 w-4 mr-2" />
                Move Category
              </DropdownMenuItem>
            )}
            {canMarkError && onMarkUploadedInError && (
              <DropdownMenuItem onClick={onMarkUploadedInError} data-testid="action-mark-error" className="text-red-600">
                <Trash2 className="h-4 w-4 mr-2" />
                Mark Uploaded in Error
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
              View File History
            </DropdownMenuItem>
          </>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
