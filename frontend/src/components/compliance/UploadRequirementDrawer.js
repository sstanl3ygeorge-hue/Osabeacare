import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { toast } from 'sonner';
import {
  Sheet,
  SheetContent,
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
  AlertTriangle, Clock, Trash2, ArrowRight, Send,
  RefreshCw, ChevronDown, ChevronRight, Loader2, Archive,
  History, X
} from 'lucide-react';
import { formatBackendDate } from '../../lib/dateUtils';
import DocumentActionMenu from './DocumentActionMenu';
import {
  getRequirementConfig,
  getAllowedMoveTargets,
  isPreviewableFile,
  normalizeUploadDrawerData,
  buildDrawerSummary,
} from './complianceRequirementMap';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// =============================================================================
// COMPONENT
// =============================================================================

/**
 * UploadRequirementDrawer - Working drawer for upload requirements
 * 
 * Ticket C spec implementation:
 * - Shows Active Files, Request History, Historical Files
 * - Per-file actions via DocumentActionMenu
 * - PoA 2-file minimum banner (using valid file count)
 * - Shared drawer for RTW, DBS, Identity, PoA
 * - Normalized data model for consistent counts
 */
export default function UploadRequirementDrawer({
  isOpen,
  onClose,
  employeeId,
  requirementKey,
  
  // Action handlers
  onUploadFile,
  onSendRequest,
  onPreviewFile,
  onExtractReview,
  onRefresh,
  
  isAuditor = false
}) {
  const [loading, setLoading] = useState(false);
  const [filesData, setFilesData] = useState(null);
  const [activeFilesExpanded, setActiveFilesExpanded] = useState(true);
  const [requestHistoryExpanded, setRequestHistoryExpanded] = useState(false);
  const [historicalFilesExpanded, setHistoricalFilesExpanded] = useState(false);
  const [actionDialog, setActionDialog] = useState({ open: false, type: null, file: null });
  const [actionReason, setActionReason] = useState('');
  const [newRequirementId, setNewRequirementId] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  const { token } = useAuth();

  // Get requirement configuration from central map
  const requirementConfig = getRequirementConfig(requirementKey);

  // Reset section expansion when drawer opens or requirement changes
  useEffect(() => {
    if (isOpen) {
      setActiveFilesExpanded(true);
      setRequestHistoryExpanded(false);
      setHistoricalFilesExpanded(false);
    }
  }, [isOpen, requirementKey]);

  // Fetch files data when drawer opens
  const fetchFiles = useCallback(async () => {
    if (!employeeId || !requirementKey) return;
    
    setLoading(true);
    try {
      const response = await axios.get(
        `${API}/employees/${employeeId}/requirements/${requirementConfig.evidenceEndpointKey}/files`,
        { headers: { Authorization: `Bearer ${token}` } }
      );

      // Normalize data immediately on fetch
      setFilesData(normalizeUploadDrawerData(response.data, requirementKey));
    } catch (err) {
      toast.error('Failed to load files');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [employeeId, requirementKey, token, requirementConfig.evidenceEndpointKey]);

  useEffect(() => {
    if (isOpen && employeeId && requirementKey) {
      fetchFiles();
    }
  }, [isOpen, employeeId, requirementKey, fetchFiles]);

  // Refresh after mutation
  const refreshAfterMutation = useCallback(async () => {
    await fetchFiles();
    if (onRefresh) onRefresh();
  }, [fetchFiles, onRefresh]);

  // Handle file view - opens preview or falls back to download
  const handleOpenFile = (file) => {
    if (!file) {
      toast.error('File data not available');
      return;
    }
    
    // Priority: openUrl > file_url > downloadUrl > download by ID
    const url = file.openUrl || file.file_url || file.downloadUrl;
    
    if (!url && !file.file_available) {
      toast.error('File URL not available. The file may have been moved or deleted.');
      return;
    }

    const mimeType = file.mime_type || file.content_type || '';

    if (isPreviewableFile(file) && onPreviewFile) {
      onPreviewFile({
        file_url: url,
        file_name: file.file_name || file.file_label || 'Document',
        mime_type: mimeType,
        file_id: file.file_id || file.id
      });
    } else if (url) {
      window.open(url, '_blank', 'noopener,noreferrer');
    } else {
      handleDownloadFile(file);
    }
  };

  // Handle file download
  const handleDownloadFile = (file) => {
    const url = file.downloadUrl || file.file_url;
    
    if (!url) {
      toast.error('Download URL not available');
      return;
    }
    
    try {
      const link = document.createElement('a');
      link.href = url;
      link.download = file.file_name || file.file_label || 'document';
      link.target = '_blank';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (err) {
      window.open(url, '_blank');
    }
  };

  // File actions
  const handleVerify = async (fileId) => {
    setIsSubmitting(true);
    try {
      await axios.post(
        `${API}/documents/${fileId}/verify`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('File verified');
      refreshAfterMutation();
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
      refreshAfterMutation();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to reject file');
    } finally {
      setIsSubmitting(false);
    }
  };

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
      refreshAfterMutation();
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
      refreshAfterMutation();
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
      refreshAfterMutation();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to move file');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Render file status badge - less misleading, separates file state from check state
  const renderFileBadge = (file) => {
    if (file.status === 'uploaded_in_error' || file.uploaded_in_error_reason) {
      return <Badge className="bg-red-100 text-red-700 text-[10px] px-1.5">Uploaded in Error</Badge>;
    }
    if (file.status === 'superseded' || file.superseded_by) {
      return <Badge className="bg-amber-100 text-amber-700 text-[10px] px-1.5">Superseded</Badge>;
    }
    if (file.rejected) {
      return <Badge className="bg-red-100 text-red-700 text-[10px] px-1.5">Rejected</Badge>;
    }
    if (file.extraction_status?.status === 'awaiting_review') {
      return <Badge className="bg-purple-100 text-purple-700 text-[10px] px-1.5">Extraction Review</Badge>;
    }
    if (file.verified) {
      return <Badge className="bg-green-100 text-green-700 text-[10px] px-1.5">Verified</Badge>;
    }
    return <Badge className="bg-amber-100 text-amber-700 text-[10px] px-1.5">Awaiting Review</Badge>;
  };

  // Render historical file badge
  const renderHistoricalBadge = (file) => {
    const status = file.status;
    const badges = {
      superseded: { bg: 'bg-amber-100', text: 'text-amber-700', label: 'Superseded' },
      uploaded_in_error: { bg: 'bg-red-100', text: 'text-red-700', label: 'Uploaded in Error' },
      rejected: { bg: 'bg-red-100', text: 'text-red-700', label: 'Rejected' },
      moved: { bg: 'bg-blue-100', text: 'text-blue-700', label: 'Moved' }
    };
    const badge = badges[status] || { bg: 'bg-gray-100', text: 'text-gray-600', label: status };
    return <Badge className={`${badge.bg} ${badge.text} text-[10px] px-1.5`}>{badge.label}</Badge>;
  };

  // Render request status badge
  const renderRequestBadge = (request) => {
    const statusConfig = {
      completed: { bg: 'bg-green-100', text: 'text-green-700', label: 'Completed' },
      submitted: { bg: 'bg-green-100', text: 'text-green-700', label: 'Submitted' },
      clicked: { bg: 'bg-purple-100', text: 'text-purple-700', label: 'Viewed' },
      viewed: { bg: 'bg-purple-100', text: 'text-purple-700', label: 'Viewed' },
      sent: { bg: 'bg-blue-100', text: 'text-blue-700', label: 'Sent' },
      requested: { bg: 'bg-blue-100', text: 'text-blue-700', label: 'Requested' },
      expired: { bg: 'bg-gray-100', text: 'text-gray-500', label: 'Expired' },
      cancelled: { bg: 'bg-gray-100', text: 'text-gray-500', label: 'Cancelled' }
    };
    const config = statusConfig[request.status] || { bg: 'bg-gray-100', text: 'text-gray-600', label: request.status };
    return <Badge className={`${config.bg} ${config.text} text-[10px] px-1.5`}>{config.label}</Badge>;
  };

  // Restricted move-category options based on requirement type (from central map)
  const requirementCategories = getAllowedMoveTargets(requirementKey);

  // PoA-specific logic using valid file count
  const isPoA = requirementKey === 'proof_of_address';
  const requiredCount = filesData?.multi_file_config?.required_count || (isPoA ? 2 : 1);
  const activeCount = filesData?.counts?.active || 0;
  const verifiedCount = filesData?.counts?.verified || 0;
  const validPoACount = filesData?.counts?.validPoA || 0;
  const needsMoreFiles = isPoA && validPoACount < requiredCount;
  const drawerSummary = buildDrawerSummary(filesData);

  const title = requirementConfig.label;

  return (
    <>
      <Sheet open={isOpen} onOpenChange={onClose}>
        <SheetContent side="right" className="w-full sm:max-w-lg overflow-y-auto p-0">
          {/* Header */}
          <SheetHeader className="sticky top-0 z-10 bg-white border-b border-gray-200 p-4">
            <div className="flex items-center justify-between">
              <SheetTitle className="font-heading flex items-center gap-2 text-lg">
                <FileText className="h-5 w-5 text-primary" />
                {title}
              </SheetTitle>
              <Button variant="ghost" size="sm" onClick={onClose} className="h-8 w-8 p-0">
                <X className="h-4 w-4" />
              </Button>
            </div>
            
            {/* Summary counters from normalized data */}
            {filesData && filesData.counts && (
              <div className="flex items-center gap-3 mt-2 text-sm text-text-muted">
                <span className="flex items-center gap-1">
                  <FileText className="h-3.5 w-3.5" />
                  {filesData.counts.active} active
                </span>
                <span className="flex items-center gap-1 text-green-600">
                  <CheckCircle className="h-3.5 w-3.5" />
                  {filesData.counts.verified} verified
                </span>
                <span className="flex items-center gap-1 text-amber-600">
                  <Clock className="h-3.5 w-3.5" />
                  {filesData.counts.pendingReview} pending
                </span>
              </div>
            )}

            {/* Readable summary */}
            {filesData && drawerSummary && (
              <p className="mt-2 text-xs text-text-muted">
                {drawerSummary}
              </p>
            )}
            
            {/* Action Buttons */}
            {!isAuditor && (
              <div className="flex gap-2 mt-3">
                <Button
                  size="sm"
                  onClick={() => onUploadFile && onUploadFile(requirementKey)}
                  className="flex-1 bg-primary hover:bg-primary-hover text-white rounded-lg"
                  data-testid="drawer-upload-btn"
                >
                  <Upload className="h-4 w-4 mr-1.5" />
                  Upload
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => onSendRequest && onSendRequest(requirementKey)}
                  className="flex-1 rounded-lg"
                  data-testid="drawer-request-btn"
                >
                  <Send className="h-4 w-4 mr-1.5" />
                  Request
                </Button>
              </div>
            )}
          </SheetHeader>

          {/* Content */}
          <div className="p-4 space-y-4">
            {loading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
              </div>
            ) : filesData ? (
              <>
                {/* PoA Banner - uses valid file count, not just active count */}
                {isPoA && (
                  <div className={`p-3 rounded-lg border ${
                    validPoACount >= requiredCount
                      ? 'bg-green-50 border-green-200'
                      : needsMoreFiles
                        ? 'bg-red-50 border-red-200'
                        : 'bg-amber-50 border-amber-200'
                  }`}>
                    <p className="text-sm font-medium flex items-center gap-2">
                      {validPoACount >= requiredCount ? (
                        <>
                          <CheckCircle className="h-4 w-4 text-green-600" />
                          <span className="text-green-700">
                            {validPoACount}/{requiredCount} valid documents
                          </span>
                        </>
                      ) : (
                        <>
                          <AlertTriangle className="h-4 w-4 text-red-600" />
                          <span className="text-red-700">
                            {requiredCount - validPoACount} more valid document{requiredCount - validPoACount !== 1 ? 's' : ''} required
                          </span>
                        </>
                      )}
                    </p>
                    <p className="text-xs text-text-muted mt-1">
                      2 recent documents required for Proof of Address (within 9 months)
                    </p>
                  </div>
                )}

                {/* Active Files Section */}
                <section data-testid="active-files-section">
                  <button
                    onClick={() => setActiveFilesExpanded(!activeFilesExpanded)}
                    className="w-full flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                  >
                    <span className="font-medium text-text-primary flex items-center gap-2">
                      <FileText className="h-4 w-4 text-green-600" />
                      Active Files ({filesData.counts.active})
                    </span>
                    {activeFilesExpanded ? (
                      <ChevronDown className="h-4 w-4 text-text-muted" />
                    ) : (
                      <ChevronRight className="h-4 w-4 text-text-muted" />
                    )}
                  </button>

                  {activeFilesExpanded && (
                    <div className="mt-3 space-y-2">
                      {filesData.active_files?.length === 0 ? (
                        <div className="p-6 bg-gray-50 rounded-lg text-center">
                          <Upload className="h-8 w-8 text-gray-300 mx-auto mb-2" />
                          <p className="text-sm text-text-muted">No active files</p>
                        </div>
                      ) : (
                        filesData.active_files?.map((file) => (
                          <div 
                            key={file.file_id}
                            className="p-3 bg-white border border-gray-200 rounded-lg hover:border-gray-300 transition-colors"
                            data-testid={`active-file-${file.file_id}`}
                          >
                            <div className="flex items-start justify-between gap-3">
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2 flex-wrap">
                                  <p className="font-medium text-text-primary text-sm truncate">
                                    {file.file_name}
                                  </p>
                                  {renderFileBadge(file)}
                                </div>
                                <div className="mt-1.5 text-xs text-text-muted space-y-0.5">
                                  <p>
                                    {formatBackendDate(file.uploaded_at, { format: 'medium' })}
                                    {file.uploaded_by && ` • ${file.uploaded_by}`}
                                  </p>
                                  {file.expiry_date && (
                                    <p>Expires: {formatBackendDate(file.expiry_date, { format: 'medium' })}</p>
                                  )}
                                  {file.extraction_status && (
                                    <p className="text-purple-600">
                                      Extraction: {file.extraction_status.status}
                                    </p>
                                  )}
                                </div>
                              </div>
                              <DocumentActionMenu
                                file={file}
                                onView={() => handleOpenFile(file)}
                                onDownload={() => handleDownloadFile(file)}
                                onVerify={() => handleVerify(file.file_id)}
                                onReject={() => setActionDialog({ open: true, type: 'reject', file })}
                                onExtractReview={() => onExtractReview && onExtractReview(file.file_id)}
                                onMarkUploadedInError={() => setActionDialog({ open: true, type: 'uploaded_in_error', file })}
                                onSupersede={() => setActionDialog({ open: true, type: 'supersede', file })}
                                onMoveCategory={() => setActionDialog({ open: true, type: 'move_category', file })}
                                onViewHistory={null}
                                isAuditor={isAuditor}
                                isProcessing={isSubmitting}
                              />
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  )}
                </section>

                {/* Request History Section */}
                <section data-testid="request-history-section">
                  <button
                    onClick={() => setRequestHistoryExpanded(!requestHistoryExpanded)}
                    className="w-full flex items-center justify-between p-3 bg-blue-50 rounded-lg hover:bg-blue-100 transition-colors"
                  >
                    <span className="font-medium text-blue-700 flex items-center gap-2">
                      <Send className="h-4 w-4" />
                      Request History ({filesData.counts.requests})
                    </span>
                    {requestHistoryExpanded ? (
                      <ChevronDown className="h-4 w-4 text-blue-600" />
                    ) : (
                      <ChevronRight className="h-4 w-4 text-blue-600" />
                    )}
                  </button>

                  {requestHistoryExpanded && (
                    <div className="mt-3 space-y-2">
                      {filesData.requests?.length === 0 ? (
                        <div className="p-6 bg-gray-50 rounded-lg text-center">
                          <Send className="h-8 w-8 text-gray-300 mx-auto mb-2" />
                          <p className="text-sm text-text-muted">No requests</p>
                        </div>
                      ) : (
                        filesData.requests?.map((req, idx) => (
                          <div 
                            key={req.request_id || idx}
                            className="p-3 bg-white border border-gray-200 rounded-lg"
                            data-testid={`request-${req.request_id || idx}`}
                          >
                            <div className="flex items-center gap-2 flex-wrap">
                              {renderRequestBadge(req)}
                              {req.source === 'scheduled' && (
                                <Badge className="bg-gray-100 text-gray-500 text-[10px] px-1">Auto</Badge>
                              )}
                              {req.is_replacement && (
                                <Badge className="bg-amber-100 text-amber-700 text-[10px] px-1">Replacement</Badge>
                              )}
                              {(req.reminder_count > 0 || req.resent_count > 0) && (
                                <Badge className="bg-amber-100 text-amber-700 text-[10px] px-1">
                                  {req.reminder_count || req.resent_count} reminder{(req.reminder_count || req.resent_count) !== 1 ? 's' : ''}
                                </Badge>
                              )}
                            </div>
                            <div className="mt-2 text-xs text-text-muted space-y-0.5">
                              {req.sent_at && <p>Sent: {formatBackendDate(req.sent_at, { format: 'medium' })}</p>}
                              {req.viewed_at && <p>Viewed: {formatBackendDate(req.viewed_at, { format: 'medium' })}</p>}
                              {req.submitted_at && <p>Submitted: {formatBackendDate(req.submitted_at, { format: 'medium' })}</p>}
                              {req.recipient_email && <p>To: {req.recipient_email}</p>}
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  )}
                </section>

                {/* Historical Files Section */}
                <section data-testid="historical-files-section">
                  <button
                    onClick={() => setHistoricalFilesExpanded(!historicalFilesExpanded)}
                    className="w-full flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                  >
                    <span className="font-medium text-text-muted flex items-center gap-2">
                      <Archive className="h-4 w-4" />
                      Historical Files ({filesData.counts.historical})
                    </span>
                    {historicalFilesExpanded ? (
                      <ChevronDown className="h-4 w-4 text-text-muted" />
                    ) : (
                      <ChevronRight className="h-4 w-4 text-text-muted" />
                    )}
                  </button>

                  {historicalFilesExpanded && (
                    <div className="mt-3 space-y-2">
                      {filesData.historical_files?.length === 0 ? (
                        <div className="p-6 bg-gray-50 rounded-lg text-center">
                          <Archive className="h-8 w-8 text-gray-300 mx-auto mb-2" />
                          <p className="text-sm text-text-muted">No historical files</p>
                        </div>
                      ) : (
                        filesData.historical_files?.map((file) => (
                          <div 
                            key={file.file_id}
                            className="p-3 bg-gray-50 border border-gray-100 rounded-lg opacity-80"
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
                                  <p className="text-xs text-amber-600 mt-1">Reason: {file.supersede_reason}</p>
                                )}
                                {file.uploaded_in_error_reason && (
                                  <p className="text-xs text-red-600 mt-1">Reason: {file.uploaded_in_error_reason}</p>
                                )}
                                {file.rejection_reason && (
                                  <p className="text-xs text-red-600 mt-1">Reason: {file.rejection_reason}</p>
                                )}
                                {file.superseded_by && (
                                  <p className="text-xs text-blue-600 mt-1">Replaced by newer file</p>
                                )}
                              </div>
                              <div className="flex gap-1">
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  onClick={() => handleOpenFile(file)}
                                  className="h-7 w-7 p-0"
                                  title="View"
                                >
                                  <Eye className="h-3.5 w-3.5" />
                                </Button>
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  onClick={() => handleDownloadFile(file)}
                                  className="h-7 w-7 p-0"
                                  title="Download"
                                >
                                  <Download className="h-3.5 w-3.5" />
                                </Button>
                              </div>
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  )}
                </section>
              </>
            ) : (
              <div className="py-12 text-center text-text-muted">
                Failed to load files
              </div>
            )}
          </div>
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
                const fileId = actionDialog.file?.file_id;
                if (actionDialog.type === 'uploaded_in_error') handleMarkUploadedInError(fileId);
                else if (actionDialog.type === 'supersede') handleSupersede(fileId);
                else if (actionDialog.type === 'move_category') handleMoveCategory(fileId);
                else if (actionDialog.type === 'reject') handleReject(fileId);
              }}
              disabled={isSubmitting || !actionReason.trim() || (actionDialog.type === 'move_category' && !newRequirementId)}
              className={
                actionDialog.type === 'reject' || actionDialog.type === 'uploaded_in_error'
                  ? 'bg-red-600 hover:bg-red-700 text-white'
                  : 'bg-primary hover:bg-primary-hover text-white'
              }
            >
              {isSubmitting && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
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
