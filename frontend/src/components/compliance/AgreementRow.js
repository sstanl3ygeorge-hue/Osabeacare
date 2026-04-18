/**
 * AgreementRow.js - Refactored for template-based submissions
 * 
 * Agreements are real template-driven forms, not simple status toggles:
 * - Zero Hour Contract (ZERO_HOUR_CONTRACT_V1)
 * - Employee Handbook Acknowledgement (EMPLOYEE_HANDBOOK_ACKNOWLEDGEMENT_V1)
 * 
 * Real lifecycle states:
 * - not_sent: No action taken
 * - sent: Request sent to employee
 * - in_progress: Employee has viewed but not completed
 * - submitted: Form submitted, awaiting review
 * - verified: Admin verified the submission
 * - rejected: Admin rejected the submission
 * 
 * Completion modes:
 * - self: Employee completed independently
 * - admin_assisted: Admin filled on employee's behalf
 * - phone_assisted: Admin recorded during phone call
 */

import { useState } from 'react';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { toast } from 'sonner';
import { 
  FileSignature, CheckCircle, XCircle, Clock, AlertTriangle, 
  ChevronDown, ChevronUp, Mail, Phone, Edit, History, Eye,
  Download, Send, Loader2, FileText, User, UserCheck, RotateCcw
} from 'lucide-react';
import { formatBackendDate } from '../../lib/dateUtils';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Map agreement keys to template IDs
const AGREEMENT_TEMPLATE_MAP = {
  'contract_acceptance': 'ZERO_HOUR_CONTRACT_V1',
  'handbook_acknowledgement': 'EMPLOYEE_HANDBOOK_ACKNOWLEDGEMENT_V1',
};

export default function AgreementRow({
  row,
  employeeId,
  employeeEmail,
  employeeData,
  onRefresh,
  onOpenForm,      // Opens AgreementFormDrawer in create mode
  onViewSubmission, // Opens AgreementFormDrawer in view mode
  onViewHistory,
  isAuditor = false
}) {
  const [expanded, setExpanded] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const { token } = useAuth();

  const {
    key,
    title,
    status,
    status_summary,
    has_acknowledgement,
    is_verified,
    acknowledgement_data,
    pending_requests = [],
    submission_data,  // New: Real template submission
    counts = {},
    allowed_actions = [],
    blocker_text
  } = row;

  // Get template ID for this agreement
  const templateId = AGREEMENT_TEMPLATE_MAP[key];

  // Determine lifecycle status
  const getLifecycleStatus = () => {
    if (is_verified) return 'verified';
    if (acknowledgement_data?.verification_status === 'rejected') return 'rejected';
    if (has_acknowledgement || submission_data) return 'submitted';
    if (pending_requests.length > 0) return 'sent';
    return 'not_sent';
  };

  const lifecycleStatus = getLifecycleStatus();

  // Status colors and icons
  const getStatusConfig = () => {
    switch (lifecycleStatus) {
      case 'verified':
        return { color: 'green', bgColor: 'bg-green-100', textColor: 'text-green-700', icon: CheckCircle, label: 'Requirement satisfied' };
      case 'rejected':
        return { color: 'red', bgColor: 'bg-red-100', textColor: 'text-red-700', icon: XCircle, label: 'Rejected / action required' };
      case 'submitted':
        return { color: 'amber', bgColor: 'bg-amber-100', textColor: 'text-amber-700', icon: Clock, label: 'Awaiting admin review' };
      case 'sent':
        return { color: 'blue', bgColor: 'bg-blue-100', textColor: 'text-blue-700', icon: Mail, label: 'Evidence requested' };
      case 'in_progress':
        return { color: 'purple', bgColor: 'bg-purple-100', textColor: 'text-purple-700', icon: Edit, label: 'Submitted, not reviewed' };
      default:
        return { color: 'gray', bgColor: 'bg-gray-100', textColor: 'text-gray-700', icon: FileSignature, label: 'Missing' };
    }
  };

  const statusConfig = getStatusConfig();
  const StatusIcon = statusConfig.icon;

  // Completion mode display
  const getCompletionModeDisplay = (mode) => {
    const modes = {
      'self': { label: 'Self-completed', icon: User },
      'self_completed': { label: 'Self-completed', icon: User },
      'admin_assisted': { label: 'Admin-assisted', icon: UserCheck },
      'phone_assisted': { label: 'Phone-assisted', icon: Phone },
    };
    return modes[mode] || { label: mode?.replace(/_/g, ' ') || 'Unknown', icon: User };
  };

  // Handle verify submission
  const handleVerify = async () => {
    const submissionId = submission_data?.id || acknowledgement_data?.submission_id;
    if (!submissionId) {
      // Fallback to legacy verify
      if (acknowledgement_data?.id) {
        setIsProcessing(true);
        try {
          await axios.post(
            `${API}/employees/${employeeId}/agreements/${acknowledgement_data.id}/verify`,
            '"Verified by admin"',
            { headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' } }
          );
          toast.success('Agreement verified');
          if (onRefresh) onRefresh();
        } catch (err) {
          toast.error(err.response?.data?.detail || 'Failed to verify');
        } finally {
          setIsProcessing(false);
        }
      }
      return;
    }
    
    setIsProcessing(true);
    try {
      await axios.post(
        `${API}/agreement-submissions/${submissionId}/verify`,
        { notes: 'Verified by admin' },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Agreement verified');
      if (onRefresh) onRefresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to verify');
    } finally {
      setIsProcessing(false);
    }
  };

  // Handle reject submission
  const handleReject = async () => {
    const reason = prompt('Enter rejection reason (min 10 characters):');
    if (!reason || reason.length < 10) {
      if (reason) toast.error('Rejection reason must be at least 10 characters');
      return;
    }
    
    const submissionId = submission_data?.id || acknowledgement_data?.submission_id;
    if (!submissionId) {
      // Fallback to legacy reject
      if (acknowledgement_data?.id) {
        setIsProcessing(true);
        try {
          await axios.post(
            `${API}/employees/${employeeId}/agreements/${acknowledgement_data.id}/reject`,
            { reason },
            { headers: { Authorization: `Bearer ${token}` } }
          );
          toast.success('Agreement rejected');
          if (onRefresh) onRefresh();
        } catch (err) {
          toast.error(err.response?.data?.detail || 'Failed to reject');
        } finally {
          setIsProcessing(false);
        }
      }
      return;
    }
    
    setIsProcessing(true);
    try {
      await axios.post(
        `${API}/agreement-submissions/${submissionId}/reject`,
        { reason },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Agreement rejected');
      if (onRefresh) onRefresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to reject');
    } finally {
      setIsProcessing(false);
    }
  };

  // Handle unverify submission (for error correction)
  const handleUnverify = async () => {
    const reason = prompt('Enter reason for unverifying (min 3 characters):');
    if (!reason || reason.length < 3) {
      if (reason) toast.error('Reason must be at least 3 characters');
      return;
    }
    
    const submissionId = submission_data?.id || acknowledgement_data?.submission_id;
    if (!submissionId) {
      // Fallback to legacy unverify
      if (acknowledgement_data?.id) {
        setIsProcessing(true);
        try {
          await axios.post(
            `${API}/employees/${employeeId}/agreements/${acknowledgement_data.id}/unverify`,
            { reason },
            { headers: { Authorization: `Bearer ${token}` } }
          );
          toast.success('Agreement unverified - now pending re-review');
          if (onRefresh) onRefresh();
        } catch (err) {
          toast.error(err.response?.data?.detail || 'Failed to unverify');
        } finally {
          setIsProcessing(false);
        }
      }
      return;
    }
    
    setIsProcessing(true);
    try {
      await axios.post(
        `${API}/agreement-submissions/${submissionId}/unverify`,
        { reason },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Agreement unverified - now pending re-review');
      if (onRefresh) onRefresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to unverify');
    } finally {
      setIsProcessing(false);
    }
  };

  // Handle PDF export
  const handleExportPDF = async () => {
    const submissionId = submission_data?.id || acknowledgement_data?.submission_id;
    if (!submissionId) {
      toast.error('No submission to export');
      return;
    }
    
    try {
      const response = await axios.get(
        `${API}/agreement-submissions/${submissionId}/pdf`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      // Open HTML content in new window for printing
      const printWindow = window.open('', '_blank');
      printWindow.document.write(response.data.html_content);
      printWindow.document.close();
      printWindow.print();
    } catch (err) {
      toast.error('Failed to export PDF');
    }
  };

  // Get completion mode data
  const completionMode = submission_data?.completion_mode || acknowledgement_data?.completion_mode;
  const modeConfig = completionMode ? getCompletionModeDisplay(completionMode) : null;
  const ModeIcon = modeConfig?.icon;

  return (
    <div 
      className={`border rounded-xl overflow-hidden ${
        lifecycleStatus === 'verified' ? 'border-green-200 bg-green-50/30' : 
        lifecycleStatus === 'rejected' ? 'border-red-200 bg-red-50/30' :
        lifecycleStatus === 'submitted' ? 'border-amber-200 bg-amber-50/30' : 
        lifecycleStatus === 'sent' ? 'border-blue-200 bg-blue-50/30' : 
        'border-gray-200 bg-gray-50/30'
      }`}
      data-testid={`agreement-row-${key}`}
    >
      {/* Row Header */}
      <div 
        className="flex items-center justify-between p-4 cursor-pointer hover:bg-white/50 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-3 flex-1 min-w-0">
          {/* Icon */}
          <div className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${statusConfig.bgColor}`}>
            <StatusIcon className={`h-5 w-5 ${statusConfig.textColor}`} />
          </div>
          
          {/* Title and Summary */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h4 className="font-medium text-text-primary">{title}</h4>
              <Badge variant="outline" className="text-[10px] px-1.5 py-0 bg-purple-50 text-purple-600 border-purple-200">
                Readiness requirement
              </Badge>
              {blocker_text && (
                <Badge className="bg-red-100 text-red-700 text-[10px]">
                  Blocks Readiness
                </Badge>
              )}
            </div>
            <div className="flex items-center gap-2 mt-0.5">
              <p className="text-sm text-text-muted truncate">{status_summary}</p>
              {modeConfig && (
                <Badge className="text-[9px] bg-gray-100 text-gray-600 border-gray-200">
                  <ModeIcon className="h-2.5 w-2.5 mr-0.5" />
                  {modeConfig.label}
                </Badge>
              )}
            </div>
          </div>
          
          {/* Status Badge */}
          <Badge className={`${statusConfig.bgColor} ${statusConfig.textColor} text-xs`}>
            {statusConfig.label}
          </Badge>
        </div>
        
        {/* Actions */}
        <div className="flex items-center gap-2 ml-4">
          {!isAuditor && (
            <>
              {/* Open Form - for not started or to redo */}
              {lifecycleStatus === 'not_sent' && templateId && (
                <Button
                  size="sm"
                  variant="default"
                  onClick={(e) => { 
                    e.stopPropagation(); 
                    if (onOpenForm) onOpenForm(key, title, templateId, 'create');
                  }}
                  className="h-8 text-xs bg-primary hover:bg-primary-hover text-white rounded-lg"
                  data-testid={`open-form-${key}`}
                >
                  <Edit className="h-3.5 w-3.5 mr-1" />
                  Fill Agreement
                </Button>
              )}
              
              {/* View Submission - for submitted/verified */}
              {(lifecycleStatus === 'submitted' || lifecycleStatus === 'verified' || lifecycleStatus === 'rejected') && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={(e) => { 
                    e.stopPropagation(); 
                    if (onViewSubmission) {
                      const submissionId = submission_data?.id || acknowledgement_data?.submission_id;
                      onViewSubmission(key, title, templateId, submissionId);
                    }
                  }}
                  className="h-8 text-xs rounded-lg"
                  data-testid={`view-submission-${key}`}
                >
                  <Eye className="h-3.5 w-3.5 mr-1" />
                  View
                </Button>
              )}
              
              {/* Verify / Reject for awaiting review */}
              {lifecycleStatus === 'submitted' && (
                <>
                  <Button
                    size="sm"
                    variant="default"
                    onClick={(e) => { e.stopPropagation(); handleVerify(); }}
                    disabled={isProcessing}
                    className="h-8 text-xs bg-green-600 hover:bg-green-700 text-white rounded-lg"
                    data-testid={`verify-${key}`}
                  >
                    {isProcessing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <CheckCircle className="h-3.5 w-3.5 mr-1" />}
                    Verify
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={(e) => { e.stopPropagation(); handleReject(); }}
                    disabled={isProcessing}
                    className="h-8 text-xs text-red-600 border-red-200 hover:bg-red-50 rounded-lg"
                    data-testid={`reject-${key}`}
                  >
                    <XCircle className="h-3.5 w-3.5 mr-1" />
                    Reject
                  </Button>
                </>
              )}
              
              {/* Export PDF for completed */}
              {(lifecycleStatus === 'submitted' || lifecycleStatus === 'verified') && (submission_data?.id || acknowledgement_data?.submission_id) && (
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={(e) => { e.stopPropagation(); handleExportPDF(); }}
                  className="h-8 text-xs rounded-lg"
                  data-testid={`export-pdf-${key}`}
                >
                  <Download className="h-3.5 w-3.5" />
                </Button>
              )}
              
              {/* Unverify button for verified agreements (error correction) */}
              {lifecycleStatus === 'verified' && (
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={(e) => { e.stopPropagation(); handleUnverify(); }}
                  disabled={isProcessing}
                  className="h-8 text-xs text-amber-600 hover:text-amber-700 hover:bg-amber-50 rounded-lg"
                  data-testid={`unverify-${key}`}
                  title="Unverify agreement (for error correction)"
                >
                  {isProcessing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RotateCcw className="h-3.5 w-3.5" />}
                </Button>
              )}
            </>
          )}
          
          {/* History */}
          {onViewHistory && (
            <Button
              size="sm"
              variant="ghost"
              onClick={(e) => { e.stopPropagation(); onViewHistory(key, title); }}
              className="h-8 text-xs rounded-lg"
              data-testid={`history-${key}`}
            >
              <History className="h-3.5 w-3.5" />
            </Button>
          )}
          
          {/* Expand/Collapse */}
          <Button
            size="sm"
            variant="ghost"
            onClick={(e) => { e.stopPropagation(); setExpanded(!expanded); }}
            className="h-8 w-8 p-0"
          >
            {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </Button>
        </div>
      </div>

      {/* Expanded Details */}
      {expanded && (
        <div className="px-4 pb-4 pt-2 border-t border-gray-200/50">
          <div className="grid grid-cols-2 gap-4 text-sm">
            {/* Submission Details */}
            {(submission_data || acknowledgement_data) && (
              <>
                <div>
                  <p className="text-gray-500 text-xs">Completed</p>
                  <p className="text-gray-900">
                    {formatBackendDate(submission_data?.completed_at || acknowledgement_data?.completed_at, { format: 'medium' })}
                  </p>
                </div>
                <div>
                  <p className="text-gray-500 text-xs">Completion Mode</p>
                  <div className="flex items-center gap-1">
                    {modeConfig && <ModeIcon className="h-3.5 w-3.5 text-gray-500" />}
                    <p className="text-gray-900">{modeConfig?.label || 'Unknown'}</p>
                  </div>
                </div>
                {submission_data?.signature_name && (
                  <div>
                    <p className="text-gray-500 text-xs">Signed By</p>
                    <p className="text-gray-900 font-serif italic">{submission_data.signature_name}</p>
                  </div>
                )}
                {submission_data?.admin_note && (
                  <div className="col-span-2">
                    <p className="text-gray-500 text-xs">Admin Note</p>
                    <p className="text-gray-700 text-sm bg-blue-50 p-2 rounded">{submission_data.admin_note}</p>
                  </div>
                )}
              </>
            )}
            
            {/* Verification Details */}
            {lifecycleStatus === 'verified' && (
              <div className="col-span-2 p-3 bg-green-50 rounded-lg border border-green-200">
                <div className="flex items-center gap-2">
                  <CheckCircle className="h-4 w-4 text-green-600" />
                  <span className="font-medium text-green-800">Requirement satisfied</span>
                </div>
                <p className="text-sm text-green-700 mt-1">
                  {formatBackendDate(submission_data?.verified_at || acknowledgement_data?.verified_at, { format: 'medium' })}
                  {(submission_data?.verified_by || acknowledgement_data?.verified_by) && 
                    ` by ${submission_data?.verified_by || acknowledgement_data?.verified_by}`}
                </p>
              </div>
            )}
            
            {/* Rejection Details */}
            {lifecycleStatus === 'rejected' && (
              <div className="col-span-2 p-3 bg-red-50 rounded-lg border border-red-200">
                <div className="flex items-center gap-2">
                  <XCircle className="h-4 w-4 text-red-600" />
                  <span className="font-medium text-red-800">Rejected / action required</span>
                </div>
                <p className="text-sm text-red-700 mt-1">
                  {submission_data?.rejection_reason || acknowledgement_data?.rejection_reason || 'No reason provided'}
                </p>
              </div>
            )}
            
            {/* No submission yet */}
            {lifecycleStatus === 'not_sent' && (
              <div className="col-span-2 p-3 bg-gray-50 rounded-lg border border-gray-200">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 text-gray-500" />
                  <span className="font-medium text-gray-700">Missing</span>
                </div>
                <p className="text-sm text-gray-600 mt-1">
                  The {title} agreement has not been submitted.
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
