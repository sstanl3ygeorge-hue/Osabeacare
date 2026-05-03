import { useState } from 'react';
import axios from 'axios';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import {
  FileText,
  Send,
  Eye,
  Download,
  CheckCircle,
  XCircle,
  Clock,
  History,
  Edit,
  ChevronDown,
  ChevronUp,
  AlertCircle,
  FileCheck,
  Loader2,
  RotateCcw
} from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '../../lib/utils';
import { 
  getRequirementCapability, 
  DELIVERY_MODES 
} from '../../config/requirementCapabilityMap';
import { useAuth } from '../../context/AuthContext';
import API_BASE from '../../utils/apiBase';
import { getStatusLabel, getStatusTone } from '../../utils/statusLabels';

const API = API_BASE;

/**
 * FormRequirementRow - Displays a single form-type requirement
 * 
 * Handles:
 * - Send (for employee_sendable forms)
 * - Fill Form (admin fills)
 * - View Submission
 * - Export PDF
 * - Verify / Reject / Unverify
 * - History
 */
export default function FormRequirementRow({
  row,
  employeeId,
  employeeEmail,
  employeeName,
  onRefresh,
  onOpenForm,         // Callback to open form drawer in create/edit mode
  onViewSubmission,   // Callback to view existing submission
  onSendForm,         // Callback to send form to employee
  onExportPdf,        // Callback to export PDF
  onVerify,           // Callback to verify submission
  onReject,           // Callback to reject submission (opens dialog)
  onUnverify,         // Callback to unverify submission (error correction)
  onViewHistory,
  onPreviewFile,      // Callback to preview a file (for evidence rows like CV)
  onUpload,           // Callback to upload a file (for evidence rows like CV)
  isAuditor = false
}) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [actionLoading, setActionLoading] = useState(null);
  const { token } = useAuth();
  
  const {
    key,
    title,
    row_type,
    form_type,
    delivery_mode,
    affects_readiness,
    optional,
    blocker_text,
    has_submission,
    submission_data,
    is_verified,
    is_rejected,
    verified_at,
    verified_by,
    rejection_reason,
    status,
    status_summary,
    allowed_actions,
    // Evidence-type fields (for CV row)
    has_files,
    file_count,
    files
  } = row;
  
  // Check if this is an evidence-type row (like CV)
  const isEvidenceRow = row_type === 'evidence' && has_files !== undefined;
  
  // Get capability config for enhanced info
  const capability = getRequirementCapability(key);
  const isSendable = delivery_mode === 'employee_sendable' || delivery_mode === 'hybrid';
  const isAdminOnly = delivery_mode === 'admin_only';
  
  // Status color mapping
  const getStatusColor = () => {
    // For evidence rows, color based on files
    if (isEvidenceRow) {
      if (is_verified) return 'bg-emerald-100 text-emerald-800 border-emerald-200';
      if (has_files && file_count > 0) return 'bg-blue-100 text-blue-800 border-blue-200';
      return 'bg-gray-100 text-gray-600 border-gray-200';
    }
    // For form rows
    switch (status) {
      case 'verified':
        return 'bg-emerald-100 text-emerald-800 border-emerald-200';
      case 'rejected':
        return 'bg-red-100 text-red-800 border-red-200';
      case 'awaiting_review':
        return 'bg-amber-100 text-amber-800 border-amber-200';
      case 'recorded':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'not_completed':
      default:
        return 'bg-gray-100 text-gray-600 border-gray-200';
    }
  };
  
  // Status icon
  const getStatusIcon = () => {
    switch (status) {
      case 'verified':
        return <CheckCircle className="h-4 w-4 text-emerald-600" />;
      case 'rejected':
        return <XCircle className="h-4 w-4 text-red-600" />;
      case 'awaiting_review':
        return <Clock className="h-4 w-4 text-amber-600" />;
      case 'recorded':
        return <FileText className="h-4 w-4 text-blue-600" />;
      case 'not_completed':
      default:
        return <FileText className="h-4 w-4 text-gray-400" />;
    }
  };
  
  // Status text for badge — canonicalised via shared statusLabels helper
  // (Tier 2 fix #4) so admin and worker see the same words for the same
  // backend state. Keep evidence-row file-count fallback intact.
  const getStatusText = () => {
    if (isEvidenceRow) {
      if (is_verified) return getStatusLabel('verified', 'admin');
      if (has_files && file_count > 0) return `${file_count} file${file_count !== 1 ? 's' : ''}`;
      return 'No files';
    }
    // Map row-level status -> canonical key consumed by getStatusLabel.
    const canonicalKey = (status === 'awaiting_review' || status === 'submitted')
      ? 'submitted'
      : (status === 'recorded' ? 'in_progress' : status);
    return getStatusLabel(canonicalKey || 'not_started', 'admin');
  };
  
  // Delivery mode badge
  const getDeliveryBadge = () => {
    // For evidence rows, show "Evidence" badge
    if (isEvidenceRow) {
      return <Badge variant="outline" className="text-xs bg-green-50 text-green-700 border-green-200">Evidence</Badge>;
    }
    if (delivery_mode === 'employee_sendable') {
      return <Badge variant="outline" className="text-xs bg-blue-50 text-blue-700 border-blue-200">Sendable</Badge>;
    }
    if (delivery_mode === 'admin_only') {
      return <Badge variant="outline" className="text-xs bg-slate-50 text-slate-600 border-slate-200">Admin Only</Badge>;
    }
    if (delivery_mode === 'hybrid') {
      return <Badge variant="outline" className="text-xs bg-purple-50 text-purple-700 border-purple-200">Hybrid</Badge>;
    }
    return null;
  };
  
  // Handle actions
  const handleSend = async () => {
    if (!onSendForm) return;
    setActionLoading('send');
    try {
      await onSendForm(key, employeeId, employeeEmail);
      toast.success(`${title} sent to employee`);
      onRefresh && onRefresh();
    } catch (error) {
      toast.error(`Failed to send: ${error.message}`);
    } finally {
      setActionLoading(null);
    }
  };
  
  const handleFillForm = () => {
    if (onOpenForm) {
      onOpenForm(key, form_type, submission_data?.id);
    }
  };
  
  const handleViewSubmission = () => {
    if (onViewSubmission && submission_data?.id) {
      onViewSubmission(key, form_type, submission_data.id);
    }
  };
  
  const handleExportPdf = () => {
    if (onExportPdf && submission_data?.id) {
      onExportPdf(key, form_type, submission_data.id);
    }
  };
  
  const handleViewHistory = () => {
    if (onViewHistory) {
      onViewHistory(key, title);
    }
  };
  
  // Handle unverify (error correction for verified items)
  const handleUnverify = async () => {
    const reason = prompt('Enter reason for unverifying (min 3 characters):');
    if (!reason || reason.trim().length < 3) {
      if (reason !== null) toast.error('Reason must be at least 3 characters');
      return;
    }
    
    setActionLoading('unverify');
    try {
      // For form submissions, use the submission unverify endpoint
      if (submission_data?.id) {
        await axios.post(
          `${API}/form-submissions/${submission_data.id}/unverify`,
          { reason: reason.trim() },
          { headers: { Authorization: `Bearer ${token}` } }
        );
      } else if (isEvidenceRow && files && files.length > 0) {
        // For evidence/document rows (like CV), unverify the document
        const verifiedFile = files.find(f => f.verified);
        if (verifiedFile?.id) {
          await axios.post(
            `${API}/employee-documents/${verifiedFile.id}/unverify`,
            { reason: reason.trim() },
            { headers: { Authorization: `Bearer ${token}` } }
          );
        }
      }
      toast.success(`${title} unverified successfully`);
      onRefresh && onRefresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to unverify');
    } finally {
      setActionLoading(null);
    }
  };
  
  // Determine which actions to show
  const showSend = isSendable && allowed_actions?.includes('send') && !has_submission;
  const showFillForm = allowed_actions?.includes('fill_form') && !has_submission;
  const showEdit = allowed_actions?.includes('edit') && has_submission && !is_verified;
  const showViewSubmission = allowed_actions?.includes('view_submission') && has_submission;
  const showExportPdf = allowed_actions?.includes('export_pdf') && has_submission;
  const showVerify = allowed_actions?.includes('verify') && has_submission && !is_verified && !isAuditor;
  const showReject = allowed_actions?.includes('reject') && has_submission && !is_verified && !isAuditor;
  const showUnverify = is_verified && !isAuditor; // Show unverify for verified items (error correction)
  const showHistory = allowed_actions?.includes('history');
  
  return (
    <div 
      className={cn(
        "border rounded-lg bg-white overflow-hidden transition-all",
        blocker_text ? "border-red-200 bg-red-50/30" : "border-gray-200",
        isExpanded && "shadow-sm"
      )}
      data-testid={`form-row-${key}`}
    >
      {/* Main Row */}
      <div 
        className="flex items-center justify-between p-3 cursor-pointer hover:bg-gray-50"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        {/* Left: Status Icon + Title + Badges */}
        <div className="flex items-center gap-3 flex-1 min-w-0">
          <div className={cn(
            "w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0",
            status === 'verified' ? "bg-emerald-100" :
            status === 'rejected' ? "bg-red-100" :
            status === 'awaiting_review' ? "bg-amber-100" :
            status === 'recorded' ? "bg-blue-100" : "bg-gray-100"
          )}>
            {getStatusIcon()}
          </div>
          
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-medium text-gray-900 truncate">{title}</span>
              {getDeliveryBadge()}
              {optional && (
                <Badge variant="outline" className="text-xs bg-gray-50 text-gray-500">Optional</Badge>
              )}
              {affects_readiness && (
                <Badge variant="outline" className="text-xs bg-orange-50 text-orange-600 border-orange-200">Required</Badge>
              )}
            </div>
            <p className="text-sm text-gray-500 mt-0.5">{status_summary}</p>
          </div>
        </div>
        
        {/* Right: Status Badge + Quick Actions + Expand Icon */}
        <div className="flex items-center gap-2">
          <Badge className={cn("text-xs", getStatusColor())}>
            {getStatusText()}
          </Badge>
          
          {/* Quick Unverify button for verified items (shown in collapsed view) */}
          {is_verified && !isAuditor && (
            <Button
              size="sm"
              variant="ghost"
              className="h-7 w-7 p-0 text-gray-400 hover:text-amber-600 hover:bg-amber-50"
              onClick={(e) => { e.stopPropagation(); handleUnverify(); }}
              disabled={actionLoading === 'unverify'}
              data-testid={`quick-unverify-${key}`}
              title="Unverify (error correction)"
            >
              {actionLoading === 'unverify' ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <RotateCcw className="h-3.5 w-3.5" />
              )}
            </Button>
          )}
          
          {isExpanded ? (
            <ChevronUp className="h-4 w-4 text-gray-400" />
          ) : (
            <ChevronDown className="h-4 w-4 text-gray-400" />
          )}
        </div>
      </div>
      
      {/* Rejection Notice */}
      {status === 'rejected' && rejection_reason && (
        <div className="px-3 pb-2">
          <div className="p-2 bg-red-50 border border-red-200 rounded text-sm">
            <div className="flex items-start gap-2 text-red-700">
              <XCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
              <div>
                <span className="font-medium">Rejected:</span>
                <span className="ml-1">{rejection_reason}</span>
              </div>
            </div>
          </div>
        </div>
      )}
      
      {/* Blocker Warning */}
      {blocker_text && status !== 'rejected' && (
        <div className="px-3 pb-2">
          <div className="flex items-center gap-2 text-red-600 text-sm">
            <AlertCircle className="h-4 w-4" />
            <span>{blocker_text}</span>
          </div>
        </div>
      )}
      
      {/* Expanded Content */}
      {isExpanded && (
        <div className="px-3 pb-3 pt-1 border-t border-gray-100">
          {/* Evidence Files Section (for CV and other evidence rows) */}
          {isEvidenceRow && (
            <div className="mb-3">
              {has_files && files && files.length > 0 ? (
                <div className="space-y-2">
                  <p className="text-xs text-gray-500 uppercase tracking-wide font-medium">Files</p>
                  {files.map((file, idx) => (
                    <div 
                      key={file.id || idx}
                      className="flex items-center justify-between p-2 bg-gray-50 rounded-lg border border-gray-200"
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        <FileText className="h-4 w-4 text-gray-400 flex-shrink-0" />
                        <div className="min-w-0">
                          <p className="text-sm font-medium text-gray-900 truncate">
                            {file.file_name || 'Document'}
                          </p>
                          {file.uploaded_at && (
                            <p className="text-xs text-gray-500">
                              Uploaded {file.uploaded_at?.slice(0, 10)}
                            </p>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-1">
                        {file.verified && (
                          <Badge className="text-[10px] px-1.5 py-0 bg-emerald-100 text-emerald-700">
                            <CheckCircle className="h-2.5 w-2.5 mr-0.5" />
                            Verified
                          </Badge>
                        )}
                        {onPreviewFile && (
                          <Button
                            size="sm"
                            variant="ghost"
                            className="h-7 w-7 p-0 text-gray-500 hover:text-blue-600"
                            onClick={(e) => {
                              e.stopPropagation();
                              onPreviewFile({
                                file_url: file.file_url || `/api/employee-documents/${file.id}/file`,
                                file_name: file.file_name || 'Document'
                              });
                            }}
                            title="View file"
                            data-testid={`view-file-${key}-${file.id}`}
                          >
                            <Eye className="h-3.5 w-3.5" />
                          </Button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="p-3 bg-gray-50 border border-gray-200 rounded-lg text-center">
                  <FileText className="h-5 w-5 text-gray-300 mx-auto mb-1" />
                  <p className="text-sm text-gray-500">No files uploaded</p>
                </div>
              )}
              
              {/* Evidence Upload Button */}
              {!isAuditor && onUpload && (
                <div className="mt-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={(e) => { e.stopPropagation(); onUpload(key); }}
                    data-testid={`upload-file-${key}`}
                  >
                    <FileText className="h-4 w-4 mr-1.5" />
                    Upload
                  </Button>
                </div>
              )}
            </div>
          )}
          
          {/* Submission Details */}
          {has_submission && submission_data && (
            <div className="mb-3 p-2 bg-gray-50 rounded-lg text-sm">
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <span className="text-gray-500">Status:</span>
                  <span className="ml-2 font-medium capitalize">{submission_data.status || 'N/A'}</span>
                </div>
                {submission_data.submitted_at && (
                  <div>
                    <span className="text-gray-500">Submitted:</span>
                    <span className="ml-2">{submission_data.submitted_at?.slice(0, 10)}</span>
                  </div>
                )}
                {is_verified && verified_at && (
                  <div>
                    <span className="text-gray-500">Verified:</span>
                    <span className="ml-2">{verified_at?.slice(0, 10)}</span>
                  </div>
                )}
                {submission_data.has_pdf && (
                  <div className="flex items-center gap-1 text-blue-600">
                    <FileCheck className="h-3.5 w-3.5" />
                    <span>PDF Available</span>
                  </div>
                )}
              </div>
            </div>
          )}
          
          {/* Actions */}
          <div className="flex flex-wrap gap-2">
            {/* Primary Actions */}
            {showSend && (
              <Button
                size="sm"
                variant="default"
                onClick={(e) => { e.stopPropagation(); handleSend(); }}
                disabled={actionLoading === 'send'}
                data-testid={`send-form-${key}`}
              >
                {actionLoading === 'send' ? (
                  <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />
                ) : (
                  <Send className="h-4 w-4 mr-1.5" />
                )}
                Send Reminder
              </Button>
            )}
            
            {showFillForm && (
              <Button
                size="sm"
                variant={showSend ? "outline" : "default"}
                onClick={(e) => { e.stopPropagation(); handleFillForm(); }}
                data-testid={`fill-form-${key}`}
              >
                <Edit className="h-4 w-4 mr-1.5" />
                Fill Form
              </Button>
            )}
            
            {showEdit && (
              <Button
                size="sm"
                variant="outline"
                onClick={(e) => { e.stopPropagation(); handleFillForm(); }}
                data-testid={`edit-form-${key}`}
              >
                <Edit className="h-4 w-4 mr-1.5" />
                Edit
              </Button>
            )}
            
            {showViewSubmission && (
              <Button
                size="sm"
                variant="outline"
                onClick={(e) => { e.stopPropagation(); handleViewSubmission(); }}
                data-testid={`view-submission-${key}`}
              >
                <Eye className="h-4 w-4 mr-1.5" />
                View
              </Button>
            )}
            
            {showExportPdf && (
              <Button
                size="sm"
                variant="outline"
                onClick={(e) => { e.stopPropagation(); handleExportPdf(); }}
                data-testid={`export-pdf-${key}`}
              >
                <Download className="h-4 w-4 mr-1.5" />
                PDF
              </Button>
            )}
            
            {/* Verification Actions */}
            {showVerify && (
              <Button
                size="sm"
                variant="outline"
                className="text-emerald-600 border-emerald-200 hover:bg-emerald-50"
                onClick={(e) => { 
                  e.stopPropagation(); 
                  if (onVerify && submission_data?.id) {
                    onVerify(submission_data.id);
                  }
                }}
                disabled={actionLoading === 'verify'}
                data-testid={`verify-form-${key}`}
              >
                {actionLoading === 'verify' ? (
                  <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />
                ) : (
                  <CheckCircle className="h-4 w-4 mr-1.5" />
                )}
                Verify
              </Button>
            )}
            
            {showReject && (
              <Button
                size="sm"
                variant="outline"
                className="text-red-600 border-red-200 hover:bg-red-50"
                onClick={(e) => { 
                  e.stopPropagation(); 
                  if (onReject && submission_data?.id) {
                    onReject(submission_data.id, title);
                  }
                }}
                data-testid={`reject-form-${key}`}
              >
                <XCircle className="h-4 w-4 mr-1.5" />
                Reject
              </Button>
            )}
            
            {/* Unverify - For error correction on verified items */}
            {showUnverify && (
              <Button
                size="sm"
                variant="ghost"
                className="text-gray-500 hover:text-amber-600 hover:bg-amber-50"
                onClick={(e) => { e.stopPropagation(); handleUnverify(); }}
                disabled={actionLoading === 'unverify'}
                data-testid={`unverify-form-${key}`}
                title="Unverify (for error correction)"
              >
                {actionLoading === 'unverify' ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <RotateCcw className="h-4 w-4" />
                )}
              </Button>
            )}
            
            {/* History */}
            {showHistory && (
              <Button
                size="sm"
                variant="ghost"
                onClick={(e) => { e.stopPropagation(); handleViewHistory(); }}
                data-testid={`history-${key}`}
              >
                <History className="h-4 w-4 mr-1.5" />
                History
              </Button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}


