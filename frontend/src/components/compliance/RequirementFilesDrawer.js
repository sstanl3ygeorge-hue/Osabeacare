import { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { toast } from 'sonner';
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '../ui/sheet';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select';
import { 
  FileText, Upload, Download, Eye, CheckCircle, XCircle, 
  AlertTriangle, Clock, History, Trash2, ArrowRight, 
  RefreshCw, ChevronDown, ChevronRight, Loader2, Send,
  FileSearch, Archive, MoreVertical
} from 'lucide-react';
import { formatBackendDate } from '../../lib/dateUtils';
import DocumentActionMenu from './DocumentActionMenu';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

/**
 * RequirementFilesDrawer - Shows all files for a requirement with full lifecycle data
 * 
 * Features:
 * - Active files with metadata, actions, request linkage
 * - Historical files (superseded, rejected, uploaded_in_error, moved) - collapsed
 * - Per-file actions via DocumentActionMenu
 * - Immediate refresh when file status changes
 */
export default function RequirementFilesDrawer({
  open,
  onClose,
  employeeId,
  requirementKey,
  requirementTitle,
  onRefresh,
  onUpload,
  onRequest,
  onPreviewFile,
  onExtractReview,
  isAuditor = false
}) {
  const [loading, setLoading] = useState(false);
  const [filesData, setFilesData] = useState(null);
  const [historicalExpanded, setHistoricalExpanded] = useState(false);
  const [requestHistoryExpanded, setRequestHistoryExpanded] = useState(false);
  const [actionDialog, setActionDialog] = useState({ open: false, type: null, file: null });
  const [actionReason, setActionReason] = useState('');
  const [newRequirementId, setNewRequirementId] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  const { token } = useAuth();

  // Previewable file types (can be displayed in browser)
  const PREVIEWABLE_TYPES = [
    'application/pdf',
    'image/jpeg',
    'image/png',
    'image/gif',
    'image/webp',
    'image/svg+xml',
    'text/plain',
    'text/html'
  ];

  // Handle file view - opens preview or falls back to download
  const handleViewFile = (file) => {
    if (!file) {
      toast.error('File data not available');
      return;
    }
    
    // Use stamped file URL if available, otherwise use original
    const fileUrl = file.stamped_file_url || file.file_url;
    const isStamped = !!file.stamped_file_url;
    
    if (!fileUrl || !file.file_available) {
      toast.error('File URL not available. The file may have been moved or deleted.');
      return;
    }

    // Check if file type is previewable
    const mimeType = file.mime_type || file.content_type || '';
    const isPreviewable = PREVIEWABLE_TYPES.some(type => mimeType.startsWith(type.split('/')[0]) || mimeType === type);
    
    if (isPreviewable && onPreviewFile) {
      // Use the preview modal - pass full file object for consistency
      onPreviewFile({
        file_url: fileUrl,
        file_name: isStamped ? `[STAMPED] ${file.file_name || file.file_label || 'Document'}` : (file.file_name || file.file_label || 'Document'),
        mime_type: mimeType,
        file_id: file.file_id
      });
    } else {
      // Fallback to download/open in new tab
      try {
        window.open(fileUrl, '_blank');
        if (!isPreviewable) {
          toast.info(`Opening ${file.file_name || 'file'} for download (preview not supported for this file type)`);
        }
      } catch (err) {
        toast.error('Failed to open file. Please try downloading instead.');
        console.error('File open error:', err);
      }
    }
  };

  // Handle file download
  const handleDownloadFile = (file) => {
    if (!file || !file.file_url) {
      toast.error('File URL not available');
      return;
    }
    
    try {
      // Create a temporary link to trigger download
      const link = document.createElement('a');
      link.href = file.file_url;
      link.download = file.file_name || file.file_label || 'document';
      link.target = '_blank';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (err) {
      // Fallback to window.open
      window.open(file.file_url, '_blank');
    }
  };

  // Fetch files data when drawer opens
  useEffect(() => {
    if (open && employeeId && requirementKey) {
      fetchFiles();
    }
  }, [open, employeeId, requirementKey]);

  const fetchFiles = async () => {
    setLoading(true);
    try {
      const response = await axios.get(
        `${API}/employees/${employeeId}/requirements/${requirementKey}/files`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setFilesData(response.data);
    } catch (err) {
      toast.error('Failed to load files');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  // Handle file actions
  const handleMarkUploadedInError = async (fileId) => {
    if (!actionReason.trim()) {
      toast.error('Please provide a reason');
      return;
    }
    setIsSubmitting(true);
    try {
      await axios.post(
        `${API}/documents/${fileId}/mark-uploaded-in-error`,
        { reason: actionReason },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('File marked as uploaded in error');
      setActionDialog({ open: false, type: null, file: null });
      setActionReason('');
      fetchFiles(); // Refresh to move file to historical
      if (onRefresh) onRefresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to mark file');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSupersede = async (fileId) => {
    if (!actionReason.trim()) {
      toast.error('Please provide a reason');
      return;
    }
    setIsSubmitting(true);
    try {
      await axios.post(
        `${API}/documents/${fileId}/supersede`,
        { reason: actionReason },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('File superseded');
      setActionDialog({ open: false, type: null, file: null });
      setActionReason('');
      fetchFiles();
      if (onRefresh) onRefresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to supersede file');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleMoveCategory = async (fileId) => {
    if (!actionReason.trim() || !newRequirementId) {
      toast.error('Please provide a reason and select new category');
      return;
    }
    setIsSubmitting(true);
    try {
      await axios.post(
        `${API}/documents/${fileId}/move-category`,
        { reason: actionReason, new_requirement_id: newRequirementId },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('File moved to new category');
      setActionDialog({ open: false, type: null, file: null });
      setActionReason('');
      setNewRequirementId('');
      fetchFiles();
      if (onRefresh) onRefresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to move file');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleVerify = async (fileId) => {
    setIsSubmitting(true);
    try {
      await axios.post(
        `${API}/documents/${fileId}/verify`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('File verified');
      fetchFiles();
      if (onRefresh) onRefresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to verify file');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReject = async (fileId) => {
    if (!actionReason.trim()) {
      toast.error('Please provide a rejection reason');
      return;
    }
    setIsSubmitting(true);
    try {
      await axios.post(
        `${API}/documents/${fileId}/reject`,
        { reason: actionReason },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('File rejected');
      setActionDialog({ open: false, type: null, file: null });
      setActionReason('');
      fetchFiles();
      if (onRefresh) onRefresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to reject file');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Render file status badge
  const renderStatusBadge = (file) => {
    if (file.verified) {
      return <Badge className="bg-green-100 text-green-700 text-xs">Verified</Badge>;
    }
    if (file.rejected) {
      return <Badge className="bg-red-100 text-red-700 text-xs">Rejected</Badge>;
    }
    if (file.extraction_status?.status === 'awaiting_review') {
      return <Badge className="bg-purple-100 text-purple-700 text-xs">Extraction Review</Badge>;
    }
    if (file.status === 'uploaded') {
      return <Badge className="bg-blue-100 text-blue-700 text-xs">Awaiting Review</Badge>;
    }
    return <Badge className="bg-gray-100 text-gray-600 text-xs">{file.status}</Badge>;
  };

  // Render historical file status badge
  const renderHistoricalBadge = (file) => {
    const status = file.status;
    if (status === 'superseded') {
      return <Badge className="bg-amber-100 text-amber-700 text-xs">Superseded</Badge>;
    }
    if (status === 'uploaded_in_error') {
      return <Badge className="bg-red-100 text-red-700 text-xs">Uploaded in Error</Badge>;
    }
    if (status === 'rejected') {
      return <Badge className="bg-red-100 text-red-700 text-xs">Rejected</Badge>;
    }
    if (status === 'moved') {
      return <Badge className="bg-blue-100 text-blue-700 text-xs">Moved</Badge>;
    }
    return <Badge className="bg-gray-100 text-gray-600 text-xs">{status}</Badge>;
  };

  // Requirement categories for move action
  const requirementCategories = [
    { id: 'right_to_work_documents', label: 'Right to Work Evidence' },
    { id: 'dbs_certificate', label: 'DBS Certificate' },
    { id: 'identity_documents', label: 'Identity Documents' },
    { id: 'proof_of_address', label: 'Proof of Address' },
    { id: 'professional_registration', label: 'Professional Registration' },
    { id: 'training_certificates', label: 'Training Certificates' },
    { id: 'references', label: 'References' },
    { id: 'other', label: 'Other Documents' }
  ].filter(cat => cat.id !== requirementKey);

  return (
    <>
      <Sheet open={open} onOpenChange={onClose}>
        <SheetContent side="right" className="w-full sm:max-w-lg overflow-y-auto">
          <SheetHeader className="mb-6">
            <SheetTitle className="font-heading flex items-center gap-2">
              <FileText className="h-5 w-5 text-gray-600" />
              {requirementTitle || 'Requirement Files'}
            </SheetTitle>
            <SheetDescription>
              View and manage all files for this requirement
            </SheetDescription>
          </SheetHeader>

          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
          ) : filesData ? (
            <div className="space-y-6">
              {/* Summary Stats */}
              <div className="grid grid-cols-3 gap-3">
                <div className="p-3 bg-gray-50 rounded-lg text-center">
                  <p className="text-2xl font-bold text-text-primary">{filesData.active_file_count}</p>
                  <p className="text-xs text-text-muted">Active</p>
                </div>
                <div className="p-3 bg-gray-50 rounded-lg text-center">
                  <p className="text-2xl font-bold text-green-600">{filesData.verified_count}</p>
                  <p className="text-xs text-text-muted">Verified</p>
                </div>
                <div className="p-3 bg-gray-50 rounded-lg text-center">
                  <p className="text-2xl font-bold text-purple-600">{filesData.pending_review_count}</p>
                  <p className="text-xs text-text-muted">Pending</p>
                </div>
              </div>

              {/* Multi-file info */}
              {filesData.multi_file_config?.required_count && (
                <div className={`p-3 rounded-lg border ${
                  filesData.verified_count >= filesData.multi_file_config.required_count
                    ? 'bg-green-50 border-green-200'
                    : 'bg-amber-50 border-amber-200'
                }`}>
                  <p className="text-sm font-medium">
                    {filesData.verified_count >= filesData.multi_file_config.required_count ? (
                      <span className="text-green-700 flex items-center gap-1">
                        <CheckCircle className="h-4 w-4" />
                        {filesData.verified_count}/{filesData.multi_file_config.required_count} required documents verified
                      </span>
                    ) : (
                      <span className="text-amber-700 flex items-center gap-1">
                        <AlertTriangle className="h-4 w-4" />
                        {filesData.verified_count}/{filesData.multi_file_config.required_count} required documents verified
                      </span>
                    )}
                  </p>
                </div>
              )}

              {/* Actions Bar */}
              {!isAuditor && (
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    onClick={() => onUpload && onUpload(requirementKey, requirementTitle)}
                    className="flex-1 bg-primary hover:bg-primary-hover text-white rounded-lg"
                  >
                    <Upload className="h-4 w-4 mr-1" />
                    Upload
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => onRequest && onRequest(requirementKey, requirementTitle)}
                    className="flex-1 rounded-lg"
                  >
                    <Send className="h-4 w-4 mr-1" />
                    Request
                  </Button>
                </div>
              )}

              {/* Active Files */}
              <div>
                <h3 className="text-sm font-semibold text-text-primary mb-3 flex items-center gap-2">
                  <FileText className="h-4 w-4 text-green-600" />
                  Active Files ({filesData.active_file_count})
                </h3>
                
                {filesData.active_files.length === 0 ? (
                  <div className="p-4 bg-gray-50 rounded-lg text-center text-sm text-text-muted">
                    No active files uploaded
                  </div>
                ) : (
                  <div className="space-y-3">
                    {filesData.active_files.map((file) => (
                      <div 
                        key={file.file_id}
                        className="p-4 bg-white border border-gray-200 rounded-xl hover:border-gray-300 transition-colors"
                        data-testid={`active-file-${file.file_id}`}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="flex-1 min-w-0">
                            {/* File Name & Status */}
                            <div className="flex items-center gap-2 flex-wrap">
                              <p className="font-medium text-text-primary truncate">
                                {file.file_name}
                              </p>
                              {renderStatusBadge(file)}
                            </div>
                            
                            {/* Metadata */}
                            <div className="mt-2 space-y-1 text-xs text-text-muted">
                              <p>
                                <span className="font-medium">Uploaded:</span>{' '}
                                {formatBackendDate(file.uploaded_at, { format: 'medium' })}
                                {file.uploaded_by && ` by ${file.uploaded_by}`}
                              </p>
                              {file.source_type && (
                                <p>
                                  <span className="font-medium">Source:</span>{' '}
                                  {file.source_type === 'manual_upload' ? 'Manual Upload' :
                                   file.source_type === 'form_submission' ? 'Form Submission' :
                                   file.source_type === 'request_response' ? 'Request Response' :
                                   file.source_type}
                                </p>
                              )}
                              {file.stamped_file_url && (
                                <p className="text-purple-600 flex items-center gap-1">
                                  <CheckCircle className="h-3 w-3" />
                                  <span className="font-medium">CQC Stamped</span>
                                </p>
                              )}
                              {file.expiry_date && (
                                <p>
                                  <span className="font-medium">Expires:</span>{' '}
                                  {formatBackendDate(file.expiry_date, { format: 'medium' })}
                                </p>
                              )}
                              {file.document_date && (
                                <p>
                                  <span className="font-medium">Document Date:</span>{' '}
                                  {formatBackendDate(file.document_date, { format: 'medium' })}
                                </p>
                              )}
                              {file.verified && file.verified_by && (
                                <p className="text-green-600">
                                  <span className="font-medium">Verified:</span>{' '}
                                  {formatBackendDate(file.verified_at, { format: 'medium' })} by {file.verified_by}
                                </p>
                              )}
                            </div>

                            {/* Extraction Status */}
                            {file.extraction_status && (
                              <div className="mt-2 p-2 bg-purple-50 rounded-lg text-xs">
                                <p className="font-medium text-purple-700">
                                  Extraction: {file.extraction_status.status}
                                </p>
                                {file.extraction_status.reviewed_at && (
                                  <p className="text-purple-600">
                                    Reviewed {formatBackendDate(file.extraction_status.reviewed_at, { format: 'short' })}
                                  </p>
                                )}
                              </div>
                            )}

                            {/* Request Linkage */}
                            {file.request_linkage && (
                              <div className="mt-2 p-2 bg-blue-50 rounded-lg text-xs">
                                <p className="text-blue-700">
                                  <span className="font-medium">From Request:</span>{' '}
                                  {file.request_linkage.request_source === 'scheduled' ? 'Scheduled Request' : 'Manual Request'}
                                </p>
                                {file.request_linkage.submitted_at && (
                                  <p className="text-blue-600">
                                    Submitted {formatBackendDate(file.request_linkage.submitted_at, { format: 'short' })}
                                  </p>
                                )}
                              </div>
                            )}
                          </div>

                          {/* Actions Menu */}
                          <DocumentActionMenu
                            file={file}
                            onView={() => handleViewFile(file)}
                            onDownload={() => handleDownloadFile(file)}
                            onVerify={() => handleVerify(file.file_id)}
                            onReject={() => setActionDialog({ open: true, type: 'reject', file })}
                            onExtractReview={() => onExtractReview && onExtractReview(file.file_id)}
                            onMarkUploadedInError={() => setActionDialog({ open: true, type: 'uploaded_in_error', file })}
                            onSupersede={() => setActionDialog({ open: true, type: 'supersede', file })}
                            onMoveCategory={() => setActionDialog({ open: true, type: 'move_category', file })}
                            isAuditor={isAuditor}
                            isProcessing={isSubmitting}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Historical Files - Collapsed */}
              {filesData.historical_files.length > 0 && (
                <div>
                  <button
                    onClick={() => setHistoricalExpanded(!historicalExpanded)}
                    className="w-full flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors text-sm"
                    data-testid="toggle-historical-files"
                  >
                    <span className="font-medium text-text-muted flex items-center gap-2">
                      <Archive className="h-4 w-4" />
                      Historical Files ({filesData.historical_file_count})
                    </span>
                    {historicalExpanded ? (
                      <ChevronDown className="h-4 w-4 text-text-muted" />
                    ) : (
                      <ChevronRight className="h-4 w-4 text-text-muted" />
                    )}
                  </button>

                  {historicalExpanded && (
                    <div className="mt-3 space-y-2">
                      {filesData.historical_files.map((file) => (
                        <div 
                          key={file.file_id}
                          className="p-3 bg-gray-50 border border-gray-100 rounded-lg opacity-75"
                          data-testid={`historical-file-${file.file_id}`}
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2">
                                <p className="text-sm font-medium text-text-muted truncate">
                                  {file.file_name}
                                </p>
                                {renderHistoricalBadge(file)}
                              </div>
                              <p className="text-xs text-text-muted mt-1">
                                {formatBackendDate(file.uploaded_at, { format: 'medium' })}
                              </p>
                              {file.supersede_reason && (
                                <p className="text-xs text-amber-600 mt-1">
                                  Reason: {file.supersede_reason}
                                </p>
                              )}
                              {file.uploaded_in_error_reason && (
                                <p className="text-xs text-red-600 mt-1">
                                  Reason: {file.uploaded_in_error_reason}
                                </p>
                              )}
                              {file.rejection_reason && (
                                <p className="text-xs text-red-600 mt-1">
                                  Reason: {file.rejection_reason}
                                </p>
                              )}
                              {file.move_reason && (
                                <p className="text-xs text-blue-600 mt-1">
                                  Moved to: {file.moved_to} - {file.move_reason}
                                </p>
                              )}
                            </div>
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => handleViewFile(file)}
                              className="h-8 w-8 p-0"
                              data-testid={`view-historical-file-${file.file_id}`}
                            >
                              <Eye className="h-4 w-4" />
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
              
              {/* Request History - Collapsed */}
              {filesData.requests && filesData.requests.length > 0 && (
                <div>
                  <button
                    onClick={() => setRequestHistoryExpanded(!requestHistoryExpanded)}
                    className="w-full flex items-center justify-between p-3 bg-blue-50 rounded-lg hover:bg-blue-100 transition-colors text-sm"
                    data-testid="toggle-request-history"
                  >
                    <span className="font-medium text-blue-700 flex items-center gap-2">
                      <Send className="h-4 w-4" />
                      Request History ({filesData.request_count})
                    </span>
                    {requestHistoryExpanded ? (
                      <ChevronDown className="h-4 w-4 text-blue-600" />
                    ) : (
                      <ChevronRight className="h-4 w-4 text-blue-600" />
                    )}
                  </button>

                  {requestHistoryExpanded && (
                    <div className="mt-3 space-y-2">
                      {filesData.requests.map((req, idx) => (
                        <div 
                          key={req.request_id || idx}
                          className={`p-3 border rounded-lg ${
                            req.status === 'completed' ? 'bg-green-50 border-green-200' :
                            req.status === 'expired' ? 'bg-gray-50 border-gray-200' :
                            'bg-blue-50 border-blue-200'
                          }`}
                          data-testid={`request-${req.request_id || idx}`}
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex-1">
                              <div className="flex items-center gap-2">
                                <Badge className={`text-[10px] px-1.5 py-0 ${
                                  req.status === 'completed' ? 'bg-green-100 text-green-700' :
                                  req.status === 'sent' ? 'bg-blue-100 text-blue-700' :
                                  req.status === 'clicked' ? 'bg-purple-100 text-purple-700' :
                                  req.status === 'expired' ? 'bg-gray-100 text-gray-500' :
                                  'bg-amber-100 text-amber-700'
                                }`}>
                                  {req.status === 'clicked' ? 'Viewed' : req.status}
                                </Badge>
                                {req.source === 'scheduled' && (
                                  <Badge className="text-[10px] px-1 py-0 bg-gray-100 text-gray-500">
                                    Auto
                                  </Badge>
                                )}
                                {req.is_replacement && (
                                  <Badge className="text-[10px] px-1 py-0 bg-amber-100 text-amber-700">
                                    Replacement
                                  </Badge>
                                )}
                              </div>
                              <div className="text-xs text-text-muted mt-1 space-y-0.5">
                                {req.sent_at && (
                                  <p>Sent: {formatBackendDate(req.sent_at, { format: 'medium' })}</p>
                                )}
                                {req.viewed_at && (
                                  <p>Viewed: {formatBackendDate(req.viewed_at, { format: 'medium' })}</p>
                                )}
                                {req.submitted_at && (
                                  <p>Submitted: {formatBackendDate(req.submitted_at, { format: 'medium' })}</p>
                                )}
                                {req.reminder_count > 0 && (
                                  <p className="text-amber-600">{req.reminder_count} reminder(s) sent</p>
                                )}
                              </div>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          ) : (
            <div className="py-12 text-center text-text-muted">
              Failed to load files
            </div>
          )}
        </SheetContent>
      </Sheet>

      {/* Action Dialogs */}
      <Dialog 
        open={actionDialog.open} 
        onOpenChange={(open) => !open && setActionDialog({ open: false, type: null, file: null })}
      >
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>
              {actionDialog.type === 'uploaded_in_error' && 'Mark as Uploaded in Error'}
              {actionDialog.type === 'supersede' && 'Supersede File'}
              {actionDialog.type === 'move_category' && 'Move to Different Category'}
              {actionDialog.type === 'reject' && 'Reject File'}
            </DialogTitle>
            <DialogDescription>
              {actionDialog.file?.file_name}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            {actionDialog.type === 'move_category' && (
              <div className="space-y-2">
                <Label>New Category *</Label>
                <Select value={newRequirementId} onValueChange={setNewRequirementId}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select category" />
                  </SelectTrigger>
                  <SelectContent>
                    {requirementCategories.map(cat => (
                      <SelectItem key={cat.id} value={cat.id}>
                        {cat.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            <div className="space-y-2">
              <Label>Reason *</Label>
              <Textarea
                value={actionReason}
                onChange={(e) => setActionReason(e.target.value)}
                placeholder={
                  actionDialog.type === 'uploaded_in_error' ? 'Why was this file uploaded in error?' :
                  actionDialog.type === 'supersede' ? 'Why is this file being superseded?' :
                  actionDialog.type === 'move_category' ? 'Why is this file being moved?' :
                  actionDialog.type === 'reject' ? 'Why is this file being rejected?' :
                  'Enter reason...'
                }
                className="min-h-[80px]"
              />
            </div>

            {actionDialog.type === 'uploaded_in_error' && (
              <div className="p-3 bg-amber-50 rounded-lg">
                <p className="text-xs text-amber-700">
                  <AlertTriangle className="h-3 w-3 inline mr-1" />
                  This will remove the file from the active set but preserve it in history for audit purposes.
                </p>
              </div>
            )}

            {actionDialog.type === 'supersede' && (
              <div className="p-3 bg-amber-50 rounded-lg">
                <p className="text-xs text-amber-700">
                  <AlertTriangle className="h-3 w-3 inline mr-1" />
                  This file will be marked as superseded. You can then upload a replacement.
                </p>
              </div>
            )}
          </div>

          <DialogFooter className="gap-2">
            <Button
              variant="outline"
              onClick={() => setActionDialog({ open: false, type: null, file: null })}
            >
              Cancel
            </Button>
            <Button
              onClick={() => {
                if (actionDialog.type === 'uploaded_in_error') {
                  handleMarkUploadedInError(actionDialog.file?.file_id);
                } else if (actionDialog.type === 'supersede') {
                  handleSupersede(actionDialog.file?.file_id);
                } else if (actionDialog.type === 'move_category') {
                  handleMoveCategory(actionDialog.file?.file_id);
                } else if (actionDialog.type === 'reject') {
                  handleReject(actionDialog.file?.file_id);
                }
              }}
              disabled={isSubmitting || !actionReason.trim() || (actionDialog.type === 'move_category' && !newRequirementId)}
              className={
                actionDialog.type === 'reject' || actionDialog.type === 'uploaded_in_error'
                  ? 'bg-red-600 hover:bg-red-700 text-white'
                  : 'bg-primary hover:bg-primary-hover text-white'
              }
            >
              {isSubmitting ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : null}
              {actionDialog.type === 'uploaded_in_error' && 'Mark as Error'}
              {actionDialog.type === 'supersede' && 'Supersede'}
              {actionDialog.type === 'move_category' && 'Move File'}
              {actionDialog.type === 'reject' && 'Reject File'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
