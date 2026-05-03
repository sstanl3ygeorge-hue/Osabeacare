import { useState } from 'react';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { toast } from 'sonner';
import { 
  User, Building, Mail, Phone, Send, Eye, CheckCircle, XCircle, 
  AlertTriangle, Clock, ChevronDown, ChevronUp, RefreshCw, 
  FileText, History, Loader2, AlertCircle
} from 'lucide-react';
import { formatBackendDate } from '../../lib/dateUtils';
import API_BASE from '../../utils/apiBase';
import AwaitingDaysBadge from './AwaitingDaysBadge';

const API = API_BASE;

/**
 * ReferenceRow - Displays a reference requirement with full lifecycle
 * 
 * States:
 * - not_declared: No referee info entered
 * - not_requested: Referee declared but request not sent
 * - requested/awaiting_response: Request sent, waiting for referee to respond
 * - awaiting_review: Response received, needs admin review
 * - mismatch_detected: Response received but identity mismatch found
 * - reviewed: Admin reviewed, awaiting verification
 * - verified: Reference verified and counts toward readiness
 */
export default function ReferenceRow({
  row,
  employeeId,
  onSendRequest,
  onViewResponse,
  onReview,
  onVerify,
  onReject,
  onViewHistory,
  onRefresh,
  isAuditor = false
}) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const { token } = useAuth();

  const {
    key,
    title,
    reference_num,
    lifecycle_status,
    status,
    status_summary,
    has_declared,
    declared_referee,
    request_status,
    request_sent_at,
    request_lifecycle,
    has_response,
    response_received_at,
    returned_referee,
    response_data_preview,
    mismatch_detected,
    mismatch_notes,
    reviewed,
    reviewed_by,
    reviewed_at,
    verified,
    verified_by,
    verified_at,
    allowed_actions = [],
    blocker_text,
    counts_toward_readiness
  } = row;

  // Status icon and color configuration
  const getStatusConfig = () => {
    switch (lifecycle_status) {
      case 'verified':
        return { icon: CheckCircle, color: 'text-green-600', bgColor: 'bg-green-50', borderColor: 'border-green-200' };
      case 'reviewed':
        return { icon: Clock, color: 'text-blue-600', bgColor: 'bg-blue-50', borderColor: 'border-blue-200' };
      case 'mismatch_detected':
        return { icon: AlertTriangle, color: 'text-amber-600', bgColor: 'bg-amber-50', borderColor: 'border-amber-200' };
      case 'awaiting_review':
        return { icon: FileText, color: 'text-purple-600', bgColor: 'bg-purple-50', borderColor: 'border-purple-200' };
      case 'awaiting_response':
        return { icon: Clock, color: 'text-blue-500', bgColor: 'bg-blue-50', borderColor: 'border-blue-200' };
      case 'requested':
        return { icon: Send, color: 'text-blue-500', bgColor: 'bg-blue-50', borderColor: 'border-blue-200' };
      case 'not_requested':
        return { icon: User, color: 'text-gray-500', bgColor: 'bg-gray-50', borderColor: 'border-gray-200' };
      default:
        return { icon: AlertCircle, color: 'text-gray-400', bgColor: 'bg-gray-50', borderColor: 'border-gray-200' };
    }
  };

  const statusConfig = getStatusConfig();
  const StatusIcon = statusConfig.icon;

  // Handle send/resend reference request
  const handleSendRequest = async (forceResend = false) => {
    if (!declared_referee?.email) {
      toast.error('Referee email not provided. Update employee profile first.');
      return;
    }
    
    setIsSending(true);
    try {
      const response = await axios.post(
        `${API}/employees/${employeeId}/send-reference-request`,
        null,
        { 
          params: { reference_num, force_resend: forceResend },
          headers: { Authorization: `Bearer ${token}` } 
        }
      );
      
      if (response.data.status === 'duplicate') {
        toast.info(response.data.message);
      } else {
        toast.success(`Reference request sent to ${declared_referee.name}`);
        if (onRefresh) onRefresh();
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to send reference request');
    } finally {
      setIsSending(false);
    }
  };

  // Render referee info block
  const renderRefereeInfo = (referee, label) => {
    if (!referee || !referee.name) return null;
    
    return (
      <div className="p-3 bg-gray-50 rounded-lg">
        <p className="text-xs font-medium text-text-muted uppercase tracking-wide mb-2">{label}</p>
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <User className="h-3.5 w-3.5 text-gray-400" />
            <span className="text-sm font-medium">{referee.name}</span>
          </div>
          {referee.company && (
            <div className="flex items-center gap-2">
              <Building className="h-3.5 w-3.5 text-gray-400" />
              <span className="text-sm text-text-muted">{referee.company}</span>
            </div>
          )}
          {referee.job_title && (
            <span className="text-xs text-text-muted ml-5">({referee.job_title})</span>
          )}
          {referee.email && (
            <div className="flex items-center gap-2">
              <Mail className="h-3.5 w-3.5 text-gray-400" />
              <span className="text-sm text-text-muted">{referee.email}</span>
            </div>
          )}
          {referee.phone && (
            <div className="flex items-center gap-2">
              <Phone className="h-3.5 w-3.5 text-gray-400" />
              <span className="text-sm text-text-muted">{referee.phone}</span>
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <div 
      className={`border rounded-lg transition-all ${statusConfig.borderColor} ${isExpanded ? statusConfig.bgColor : 'bg-white hover:bg-gray-50'}`}
      data-testid={`reference-row-${key}`}
    >
      {/* Collapsed Row */}
      <div 
        className="p-4 cursor-pointer"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-4">
          {/* Status Icon */}
          <div className={`p-2 rounded-lg ${statusConfig.bgColor}`}>
            <StatusIcon className={`h-5 w-5 ${statusConfig.color}`} />
          </div>
          
          {/* Title and Summary */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h4 className="font-medium text-text-primary">{title}</h4>
              {verified && (
                <Badge className="text-[10px] px-1.5 py-0 bg-green-100 text-green-700 border border-green-200">
                  Verified
                </Badge>
              )}
              {mismatch_detected && !verified && (
                <Badge className="text-[10px] px-1.5 py-0 bg-amber-100 text-amber-700 border border-amber-200">
                  <AlertTriangle className="h-2.5 w-2.5 mr-0.5" />
                  Mismatch
                </Badge>
              )}
              {request_lifecycle?.is_stale && (
                <Badge className="text-[10px] px-1.5 py-0 bg-amber-100 text-amber-700 border border-amber-200">
                  Stale ({request_lifecycle.stale_days}d)
                </Badge>
              )}
              {/* Awaiting-days chase badge — Tier 3 #5. Counts up from when
                  the reference request was sent, so admins can chase
                  long-pending referees at a glance. Only when truly waiting
                  on the referee (not when verified or response received). */}
              {!verified && !has_response && request_sent_at && (
                <AwaitingDaysBadge
                  sentAt={request_sent_at}
                  testId={`reference-awaiting-${reference_num || key}`}
                />
              )}
            </div>
            <p className="text-sm text-text-muted truncate">{status_summary}</p>
          </div>
          
          {/* Actions */}
          <div className="flex items-center gap-2 ml-4">
            {/* Send/Resend Request */}
            {!isAuditor && allowed_actions.includes('send_request') && declared_referee?.email && (
              <Button
                size="sm"
                variant="default"
                onClick={(e) => { e.stopPropagation(); handleSendRequest(); }}
                disabled={isSending}
                className="h-8 text-xs bg-primary hover:bg-primary-hover text-white rounded-lg"
                data-testid={`send-request-${key}`}
              >
                {isSending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Send className="h-3.5 w-3.5 mr-1" />}
                Request
              </Button>
            )}
            
            {!isAuditor && allowed_actions.includes('resend_request') && (
              <Button
                size="sm"
                variant="outline"
                onClick={(e) => { e.stopPropagation(); handleSendRequest(true); }}
                disabled={isSending}
                className="h-8 text-xs rounded-lg text-amber-600 border-amber-300 hover:bg-amber-50"
                data-testid={`resend-request-${key}`}
              >
                {isSending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5 mr-1" />}
                Resend
              </Button>
            )}
            
            {/* View Response */}
            {has_response && onViewResponse && (
              <Button
                size="sm"
                variant="outline"
                onClick={(e) => { e.stopPropagation(); onViewResponse(reference_num); }}
                className="h-8 text-xs rounded-lg"
                data-testid={`view-response-${key}`}
              >
                <Eye className="h-3.5 w-3.5 mr-1" />
                View Response
              </Button>
            )}
            
            {/* Review/Verify/Reject - shown when response received */}
            {!isAuditor && has_response && !verified && (
              <>
                {allowed_actions.includes('verify') && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={(e) => { e.stopPropagation(); if (onVerify) onVerify(reference_num); }}
                    className="h-8 text-xs rounded-lg text-green-600 border-green-300 hover:bg-green-50"
                    data-testid={`verify-${key}`}
                  >
                    <CheckCircle className="h-3.5 w-3.5 mr-1" />
                    Verify
                  </Button>
                )}
                {allowed_actions.includes('reject') && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={(e) => { e.stopPropagation(); if (onReject) onReject(reference_num); }}
                    className="h-8 text-xs rounded-lg text-red-600 border-red-300 hover:bg-red-50"
                    data-testid={`reject-${key}`}
                  >
                    <XCircle className="h-3.5 w-3.5 mr-1" />
                    Reject
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
                className="h-8 w-8 p-0"
                data-testid={`history-${key}`}
              >
                <History className="h-4 w-4 text-text-muted" />
              </Button>
            )}
            
            {/* Expand/Collapse */}
            <Button
              size="sm"
              variant="ghost"
              className="h-8 w-8 p-0"
              data-testid={`expand-${key}`}
            >
              {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </Button>
          </div>
        </div>
      </div>
      
      {/* Expanded Content */}
      {isExpanded && (
        <div className="px-4 pb-4 border-t border-gray-100">
          <div className="pt-4 space-y-4">
            {/* No Referee Declared */}
            {!has_declared && (
              <div className="p-4 bg-gray-100 rounded-lg text-center">
                <AlertCircle className="h-8 w-8 text-gray-400 mx-auto mb-2" />
                <p className="text-sm text-text-muted">
                  No referee has been declared for this reference.
                </p>
                <p className="text-xs text-text-muted mt-1">
                  Update the employee profile to add referee details.
                </p>
              </div>
            )}
            
            {/* Declared Referee Info */}
            {has_declared && renderRefereeInfo(declared_referee, "Declared Referee")}
            
            {/* Response Info (if received) */}
            {has_response && (
              <div className="space-y-3">
                {/* Returned Referee Info (if different) */}
                {returned_referee && returned_referee.name && (
                  renderRefereeInfo(returned_referee, "From Response")
                )}
                
                {/* Mismatch Warning */}
                {mismatch_detected && (
                  <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
                    <div className="flex items-start gap-2">
                      <AlertTriangle className="h-4 w-4 text-amber-600 mt-0.5" />
                      <div>
                        <p className="text-sm font-medium text-amber-800">Identity Mismatch Detected</p>
                        <p className="text-xs text-amber-700 mt-1">
                          The referee details in the response don't match the declared referee.
                          {mismatch_notes && ` Notes: ${mismatch_notes}`}
                        </p>
                      </div>
                    </div>
                  </div>
                )}
                
                {/* Response Preview */}
                {response_data_preview && (
                  <div className="p-3 bg-purple-50 border border-purple-200 rounded-lg">
                    <p className="text-xs font-medium text-purple-700 uppercase tracking-wide mb-2">Response Summary</p>
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      {response_data_preview.relationship_type && (
                        <div>
                          <span className="text-purple-600">Relationship:</span>{' '}
                          <span className="text-purple-800">{response_data_preview.relationship_type}</span>
                        </div>
                      )}
                      {response_data_preview.employment_dates && response_data_preview.employment_dates !== ' - ' && (
                        <div>
                          <span className="text-purple-600">Employment:</span>{' '}
                          <span className="text-purple-800">{response_data_preview.employment_dates}</span>
                        </div>
                      )}
                      {response_data_preview.would_rehire !== undefined && (
                        <div>
                          <span className="text-purple-600">Would Rehire:</span>{' '}
                          <span className="text-purple-800">{response_data_preview.would_rehire ? 'Yes' : 'No'}</span>
                        </div>
                      )}
                      {response_data_preview.overall_assessment && (
                        <div>
                          <span className="text-purple-600">Assessment:</span>{' '}
                          <span className="text-purple-800">{response_data_preview.overall_assessment}</span>
                        </div>
                      )}
                    </div>
                    <p className="text-xs text-purple-600 mt-2">
                      Received {formatBackendDate(response_received_at, { format: 'medium' })}
                    </p>
                  </div>
                )}
              </div>
            )}
            
            {/* Request Status Timeline */}
            {request_sent_at && !has_response && (
              <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
                <p className="text-xs font-medium text-blue-700 uppercase tracking-wide mb-2">Request Status</p>
                <div className="flex items-center gap-2 text-sm">
                  <Send className="h-4 w-4 text-blue-500" />
                  <span className="text-blue-700">
                    Request sent {formatBackendDate(request_sent_at, { format: 'relative' })}
                  </span>
                </div>
                {request_lifecycle?.is_stale && (
                  <p className="text-xs text-amber-600 mt-2">
                    <AlertTriangle className="h-3 w-3 inline mr-1" />
                    Request is {request_lifecycle.stale_days} days old with no response. Consider resending.
                  </p>
                )}
              </div>
            )}
            
            {/* Verification Status */}
            {verified && (
              <div className="p-3 bg-green-50 border border-green-200 rounded-lg">
                <div className="flex items-center gap-2">
                  <CheckCircle className="h-4 w-4 text-green-600" />
                  <div>
                    <p className="text-sm font-medium text-green-800">Verified</p>
                    <p className="text-xs text-green-600">
                      {formatBackendDate(verified_at, { format: 'medium' })} by {verified_by}
                    </p>
                  </div>
                </div>
              </div>
            )}
            
            {/* Reviewed but not verified */}
            {reviewed && !verified && (
              <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
                <div className="flex items-center gap-2">
                  <Clock className="h-4 w-4 text-blue-600" />
                  <div>
                    <p className="text-sm font-medium text-blue-800">Reviewed - Awaiting Verification</p>
                    <p className="text-xs text-blue-600">
                      {formatBackendDate(reviewed_at, { format: 'medium' })} by {reviewed_by}
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

