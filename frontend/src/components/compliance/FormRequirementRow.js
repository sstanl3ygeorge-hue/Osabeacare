import { useState } from 'react';
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
  Loader2
} from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '../../lib/utils';
import { 
  getRequirementCapability, 
  DELIVERY_MODES 
} from '../../config/requirementCapabilityMap';

/**
 * FormRequirementRow - Displays a single form-type requirement
 * 
 * Handles:
 * - Send (for employee_sendable forms)
 * - Fill Form (admin fills)
 * - View Submission
 * - Export PDF
 * - Verify / Reject
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
  onViewHistory,
  isAuditor = false
}) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [actionLoading, setActionLoading] = useState(null);
  
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
    verified_at,
    verified_by,
    status,
    status_summary,
    allowed_actions
  } = row;
  
  // Get capability config for enhanced info
  const capability = getRequirementCapability(key);
  const isSendable = delivery_mode === 'employee_sendable' || delivery_mode === 'hybrid';
  const isAdminOnly = delivery_mode === 'admin_only';
  
  // Status color mapping
  const getStatusColor = () => {
    switch (status) {
      case 'verified':
        return 'bg-emerald-100 text-emerald-800 border-emerald-200';
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
      case 'awaiting_review':
        return <Clock className="h-4 w-4 text-amber-600" />;
      case 'recorded':
        return <FileText className="h-4 w-4 text-blue-600" />;
      case 'not_completed':
      default:
        return <FileText className="h-4 w-4 text-gray-400" />;
    }
  };
  
  // Delivery mode badge
  const getDeliveryBadge = () => {
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
  
  // Determine which actions to show
  const showSend = isSendable && allowed_actions?.includes('send') && !has_submission;
  const showFillForm = allowed_actions?.includes('fill_form') && !has_submission;
  const showEdit = allowed_actions?.includes('edit') && has_submission && !is_verified;
  const showViewSubmission = allowed_actions?.includes('view_submission') && has_submission;
  const showExportPdf = allowed_actions?.includes('export_pdf') && has_submission;
  const showVerify = allowed_actions?.includes('verify') && has_submission && !is_verified && !isAuditor;
  const showReject = allowed_actions?.includes('reject') && has_submission && !is_verified && !isAuditor;
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
        
        {/* Right: Status Badge + Expand Icon */}
        <div className="flex items-center gap-2">
          <Badge className={cn("text-xs", getStatusColor())}>
            {status === 'verified' ? 'Verified' :
             status === 'awaiting_review' ? 'Awaiting Review' :
             status === 'recorded' ? 'Draft' : 'Not Started'}
          </Badge>
          {isExpanded ? (
            <ChevronUp className="h-4 w-4 text-gray-400" />
          ) : (
            <ChevronDown className="h-4 w-4 text-gray-400" />
          )}
        </div>
      </div>
      
      {/* Blocker Warning */}
      {blocker_text && (
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
                Send to Employee
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
                onClick={(e) => { e.stopPropagation(); /* TODO: Implement verify */ }}
                data-testid={`verify-form-${key}`}
              >
                <CheckCircle className="h-4 w-4 mr-1.5" />
                Verify
              </Button>
            )}
            
            {showReject && (
              <Button
                size="sm"
                variant="outline"
                className="text-red-600 border-red-200 hover:bg-red-50"
                onClick={(e) => { e.stopPropagation(); /* TODO: Implement reject */ }}
                data-testid={`reject-form-${key}`}
              >
                <XCircle className="h-4 w-4 mr-1.5" />
                Reject
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
