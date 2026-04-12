import { useState } from 'react';
import {
  FileText,
  Upload,
  Eye,
  Download,
  CheckCircle,
  XCircle,
  MoreHorizontal,
  AlertTriangle,
  RefreshCw,
  Send,
  Clock,
} from 'lucide-react';
import { Button } from '../../ui/button';
import { Badge } from '../../ui/badge';
import { Textarea } from '../../ui/textarea';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '../../ui/dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '../../ui/dropdown-menu';
import { formatBackendDate } from '../../../lib/dateUtils';

/**
 * EvidenceSection — Steps 1 (upload) and 2 (review)
 *
 * RULES (enforced in this component):
 * - NO "Verify" action on evidence rows — verification is the whole workflow
 * - Evidence actions (accept/reject/remove/request-replacement) do NOT
 *   touch check records or proof documents
 * - "Remove" = mark-uploaded-in-error (soft delete, not a hard delete)
 * - Admin sees full action menu; worker sees simplified upload-only view
 */
export function EvidenceSection({
  requirementKey,
  files = [],
  pendingRequests = [],
  counts = {},
  isAdminView = true,
  onAccept,
  onReject,
  onRemove,
  onRequestReplacement,
  onReviewFile,
  onPreviewFile,
  onUpload,
  workflow,
}) {
  const [removeDialog, setRemoveDialog] = useState({ open: false, docId: null, fileName: '' });
  const [removeReason, setRemoveReason] = useState('Uploaded in error');
  const hasFiles = files.length > 0;
  const latestRequest = pendingRequests[0] || null;

  // Step completion bubble
  const stepComplete = workflow.hasAcceptedEvidence;

  const getFileStatusBadge = (file) => {
    const isAccepted =
      file.verified ||
      file.status === 'verified' ||
      file.status === 'accepted' ||
      file.status === 'approved';
    const isRejected = file.status === 'rejected';

    if (isAccepted) {
      return (
        <Badge className="text-[10px] px-1.5 py-0 bg-emerald-100 text-emerald-700 border border-emerald-200">
          <CheckCircle className="h-2.5 w-2.5 mr-0.5" />
          Accepted
        </Badge>
      );
    }
    if (isRejected) {
      return (
        <Badge className="text-[10px] px-1.5 py-0 bg-red-100 text-red-700 border border-red-200">
          <XCircle className="h-2.5 w-2.5 mr-0.5" />
          Rejected
        </Badge>
      );
    }
    return (
      <Badge className="text-[10px] px-1.5 py-0 bg-amber-100 text-amber-700 border border-amber-200">
        <Clock className="h-2.5 w-2.5 mr-0.5" />
        Pending Review
      </Badge>
    );
  };

  const handleRemoveWithConfirm = (docId, fileName) => {
    setRemoveDialog({ open: true, docId, fileName });
    setRemoveReason('Uploaded in error');
  };

  const handleConfirmRemove = () => {
    if (!removeDialog.docId) return;
    onRemove(removeDialog.docId, removeReason.trim() || 'Uploaded in error');
    setRemoveDialog({ open: false, docId: null, fileName: '' });
    setRemoveReason('Uploaded in error');
  };

  return (
    <div
      className="p-4"
      data-testid={`${requirementKey}-evidence-section`}
    >
      {/* ── Section header ─────────────────────────────────────────── */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div
            className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 ${
              stepComplete
                ? 'bg-emerald-100 text-emerald-700'
                : 'bg-primary/10 text-primary'
            }`}
          >
            {stepComplete ? (
              <CheckCircle className="h-3.5 w-3.5" />
            ) : (
              '1–2'
            )}
          </div>
          <h4 className="text-sm font-semibold text-text-primary">
            Evidence
          </h4>
          {counts.active > 0 && (
            <span className="text-xs text-text-muted">
              ({counts.active} file
              {counts.active !== 1 ? 's' : ''})
            </span>
          )}
        </div>
        {isAdminView && hasFiles && !workflow.hasAcceptedEvidence && (
          <Badge className="text-[10px] px-1.5 py-0 bg-amber-100 text-amber-700 border-amber-200">
            Review required
          </Badge>
        )}
      </div>

      {/* ── File list ──────────────────────────────────────────────── */}
      {hasFiles ? (
        <div className="space-y-2 mb-3">
          {files.map((file) => {
            const docId = file.id || file.file_id;
            const fileName =
              file.file_name || file.original_filename || 'Document';
            const isAccepted =
              file.verified ||
              file.status === 'verified' ||
              file.status === 'accepted' ||
              file.status === 'approved';
            const isRejected = file.status === 'rejected';

            return (
              <div
                key={docId}
                className="flex items-center justify-between p-3 bg-white border border-gray-200 rounded-lg hover:border-gray-300 transition-colors"
                data-testid={`evidence-file-${docId}`}
              >
                <div className="flex items-center gap-3 min-w-0 flex-1">
                  <FileText className="h-4 w-4 text-gray-400 flex-shrink-0" />
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-text-primary truncate">
                      {fileName}
                    </p>
                    <div className="flex items-center gap-2 flex-wrap mt-0.5">
                      <span className="text-xs text-text-muted">
                        Uploaded{' '}
                        {formatBackendDate(file.uploaded_at, {
                          format: 'medium',
                        })}
                        {file.uploaded_by_name &&
                          ` by ${file.uploaded_by_name}`}
                      </span>
                      {file.rejection_reason && (
                        <span className="text-xs text-red-600 font-medium">
                          Reason: {file.rejection_reason}
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2 flex-shrink-0">
                  {getFileStatusBadge(file)}

                  {/* View */}
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-7 w-7 p-0 text-gray-400 hover:text-blue-600"
                    onClick={() =>
                      onPreviewFile?.({
                        file_url:
                          file.file_url ||
                          `/api/employee-documents/${docId}/file`,
                        file_name: fileName,
                      })
                    }
                    data-testid={`evidence-view-${docId}`}
                    title="View file"
                  >
                    <Eye className="h-3.5 w-3.5" />
                  </Button>

                  {/* Download */}
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-7 w-7 p-0 text-gray-400 hover:text-green-600"
                    onClick={() =>
                      window.open(
                        file.file_url ||
                          `/api/employee-documents/${docId}/file`,
                        '_blank',
                      )
                    }
                    data-testid={`evidence-download-${docId}`}
                    title="Download original file"
                  >
                    <Download className="h-3.5 w-3.5" />
                  </Button>

                  {/* Admin action menu — evidence actions ONLY */}
                  {isAdminView && (
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button
                          size="sm"
                          variant="ghost"
                          className="h-7 w-7 p-0 text-gray-400 hover:text-gray-600"
                          data-testid={`evidence-menu-${docId}`}
                        >
                          <MoreHorizontal className="h-3.5 w-3.5" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end" className="w-52">
                        {/* Accept/Reject only when not yet reviewed */}
                        {!isAccepted && !isRejected && (
                          <>
                            <DropdownMenuItem
                              className="text-emerald-700 focus:bg-emerald-50 focus:text-emerald-800"
                              onClick={() => onAccept(docId)}
                              data-testid={`evidence-accept-${docId}`}
                            >
                              <CheckCircle className="h-3.5 w-3.5 mr-2" />
                              Accept Evidence
                            </DropdownMenuItem>
                            <DropdownMenuItem
                              className="text-red-600 focus:bg-red-50 focus:text-red-700"
                              onClick={() => onReviewFile(file)}
                              data-testid={`evidence-reject-${docId}`}
                            >
                              <XCircle className="h-3.5 w-3.5 mr-2" />
                              Reject Evidence
                            </DropdownMenuItem>
                            <DropdownMenuSeparator />
                          </>
                        )}
                        <DropdownMenuItem
                          onClick={() => onRequestReplacement(docId)}
                          data-testid={`evidence-request-replacement-${docId}`}
                        >
                          <RefreshCw className="h-3.5 w-3.5 mr-2" />
                          Request Replacement
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem
                          className="text-gray-500 focus:bg-gray-50"
                          onClick={() =>
                            handleRemoveWithConfirm(docId, fileName)
                          }
                          data-testid={`evidence-remove-${docId}`}
                        >
                          <AlertTriangle className="h-3.5 w-3.5 mr-2" />
                          Remove (Uploaded in Error)
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        /* Empty state */
        <div className="p-4 bg-gray-50 border border-dashed border-gray-200 rounded-lg text-center mb-3">
          <FileText className="h-6 w-6 text-gray-300 mx-auto mb-1" />
          <p className="text-sm text-text-muted">No evidence uploaded</p>
          {isAdminView && latestRequest && (
            <p className="text-xs text-blue-600 mt-1">
              <Send className="h-3 w-3 inline mr-1" />
              Request sent — awaiting upload
            </p>
          )}
        </div>
      )}

      {/* ── Upload action ───────────────────────────────────────────── */}
      {/* Admin can always upload; worker only when no files */}
      {(isAdminView || !hasFiles) && (
        <Button
          size="sm"
          variant="outline"
          className="h-8 text-xs"
          onClick={onUpload}
          data-testid={`${requirementKey}-upload-evidence-btn`}
        >
          <Upload className="h-3.5 w-3.5 mr-1" />
          Upload Evidence
        </Button>
      )}

      {/* ── Worker simplified view ──────────────────────────────────── */}
      {!isAdminView && hasFiles && (
        <p className="text-xs text-text-muted mt-2">
          {workflow.hasAcceptedEvidence
            ? 'Evidence accepted by admin.'
            : 'Evidence is being reviewed by admin. No action needed.'}
        </p>
      )}

      <Dialog
        open={removeDialog.open}
        onOpenChange={(open) => {
          if (!open) {
            setRemoveDialog({ open: false, docId: null, fileName: '' });
            setRemoveReason('Uploaded in error');
          }
        }}
      >
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Remove Evidence</DialogTitle>
          </DialogHeader>
          <div className="space-y-3 py-2">
            <p className="text-sm text-text-muted">
              Remove "{removeDialog.fileName}" from active records. This keeps audit history.
            </p>
            <Textarea
              value={removeReason}
              onChange={(e) => setRemoveReason(e.target.value)}
              placeholder="Reason for removal"
              className="min-h-[90px]"
            />
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setRemoveDialog({ open: false, docId: null, fileName: '' });
                setRemoveReason('Uploaded in error');
              }}
            >
              Cancel
            </Button>
            <Button
              className="bg-red-600 hover:bg-red-700 text-white"
              onClick={handleConfirmRemove}
            >
              Remove
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
