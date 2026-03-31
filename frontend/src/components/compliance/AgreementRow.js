import { useState } from 'react';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { toast } from 'sonner';
import { 
  FileSignature, CheckCircle, XCircle, Clock, AlertTriangle, 
  ChevronDown, ChevronUp, Mail, Phone, Edit, History
} from 'lucide-react';
import { formatBackendDate } from '../../lib/dateUtils';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

/**
 * AgreementRow - Renders an agreement acknowledgement row
 * 
 * Agreements are forms, not documents:
 * - Contract Acceptance
 * - Employee Handbook Acknowledgement
 * 
 * Completion modes:
 * - self_completed: Employee filled via secure link
 * - admin_assisted: Admin filled on employee's behalf
 * - phone_assisted: Admin recorded during phone call
 */
export default function AgreementRow({
  row,
  employeeId,
  employeeEmail,
  onRefresh,
  onSendForm,
  onFillInternally,
  onCompleteByPhone,
  onVerify,
  onReject,
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
    counts = {},
    allowed_actions = [],
    blocker_text
  } = row;

  // Status colors
  const getStatusColor = () => {
    if (is_verified) return 'bg-green-100 text-green-700';
    if (has_acknowledgement) return 'bg-amber-100 text-amber-700';
    if (pending_requests.length > 0) return 'bg-blue-100 text-blue-700';
    return 'bg-red-100 text-red-700';
  };

  // Background color for the row
  const getRowBgColor = () => {
    if (is_verified) return 'bg-green-50/30';
    if (has_acknowledgement) return 'bg-amber-50/30';
    if (pending_requests.length > 0) return 'bg-blue-50/30';
    return 'bg-red-50/30';
  };

  // Completion mode display
  const getCompletionModeDisplay = (mode) => {
    const modes = {
      'self_completed': 'Self-completed',
      'admin_assisted': 'Admin-assisted',
      'phone_assisted': 'Phone-assisted'
    };
    return modes[mode] || mode?.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()) || 'Unknown';
  };

  // Verification status display
  const getVerificationStatusDisplay = (status) => {
    const statuses = {
      'awaiting_review': 'Awaiting Review',
      'verified': 'Verified',
      'rejected': 'Rejected'
    };
    return statuses[status] || status?.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()) || 'Unknown';
  };

  // Handle verify
  const handleVerify = async () => {
    if (!acknowledgement_data?.id) return;
    
    setIsProcessing(true);
    try {
      await axios.post(
        `${API}/employees/${employeeId}/agreements/${acknowledgement_data.id}/verify`,
        '"Verified by admin"',
        {
          headers: { 
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        }
      );
      toast.success('Agreement verified');
      if (onRefresh) onRefresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to verify');
    } finally {
      setIsProcessing(false);
    }
  };

  // Handle reject
  const handleReject = async () => {
    const reason = prompt('Enter rejection reason:');
    if (!reason) return;
    
    setIsProcessing(true);
    try {
      await axios.post(
        `${API}/employees/${employeeId}/agreements/${acknowledgement_data.id}/reject`,
        { reason },
        {
          headers: { Authorization: `Bearer ${token}` }
        }
      );
      toast.success('Agreement rejected');
      if (onRefresh) onRefresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to reject');
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div 
      className={`border rounded-xl overflow-hidden ${
        is_verified ? 'border-green-200' : 
        has_acknowledgement ? 'border-amber-200' : 
        pending_requests.length > 0 ? 'border-blue-200' : 'border-red-200'
      } ${getRowBgColor()}`}
      data-testid={`agreement-row-${key}`}
    >
      {/* Row Header */}
      <div 
        className="flex items-center justify-between p-4 cursor-pointer hover:bg-white/50 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-3 flex-1 min-w-0">
          {/* Icon */}
          <div className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${
            is_verified ? 'bg-green-100' : 
            has_acknowledgement ? 'bg-amber-100' : 
            pending_requests.length > 0 ? 'bg-blue-100' : 'bg-red-100'
          }`}>
            {is_verified ? (
              <CheckCircle className="h-5 w-5 text-green-600" />
            ) : has_acknowledgement ? (
              <Clock className="h-5 w-5 text-amber-600" />
            ) : pending_requests.length > 0 ? (
              <Mail className="h-5 w-5 text-blue-600" />
            ) : (
              <FileSignature className="h-5 w-5 text-red-600" />
            )}
          </div>
          
          {/* Title and Summary */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h4 className="font-medium text-text-primary">{title}</h4>
              <Badge variant="outline" className="text-[10px] px-1.5 py-0 bg-purple-50 text-purple-600 border-purple-200">
                Agreement
              </Badge>
              {blocker_text && (
                <Badge className="bg-red-100 text-red-700 text-[10px]">
                  Blocks Readiness
                </Badge>
              )}
            </div>
            <p className="text-sm text-text-muted truncate">{status_summary}</p>
          </div>
          
          {/* Status Badge */}
          <Badge className={`${getStatusColor()} text-xs`}>
            {is_verified ? 'Verified' : 
             has_acknowledgement ? getVerificationStatusDisplay(acknowledgement_data?.verification_status) :
             pending_requests.length > 0 ? 'Sent' : 'Not Completed'}
          </Badge>
        </div>
        
        {/* Actions */}
        <div className="flex items-center gap-2 ml-4">
          {!isAuditor && (
            <>
              {/* Send Form / Fill Internally / Complete by Phone */}
              {!has_acknowledgement && pending_requests.length === 0 && (
                <>
                  {allowed_actions.includes('send_form') && employeeEmail && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={(e) => { e.stopPropagation(); if (onSendForm) onSendForm(key, title); }}
                      className="h-8 text-xs text-blue-600 border-blue-200 hover:bg-blue-50 rounded-lg"
                      data-testid={`send-form-${key}`}
                    >
                      <Mail className="h-3.5 w-3.5 mr-1" />
                      Send
                    </Button>
                  )}
                  
                  {allowed_actions.includes('fill_internally') && (
                    <Button
                      size="sm"
                      variant="default"
                      onClick={(e) => { e.stopPropagation(); if (onFillInternally) onFillInternally(key, title); }}
                      className="h-8 text-xs bg-primary hover:bg-primary-hover text-white rounded-lg"
                      data-testid={`fill-internally-${key}`}
                    >
                      <Edit className="h-3.5 w-3.5 mr-1" />
                      Fill
                    </Button>
                  )}
                  
                  {allowed_actions.includes('complete_by_phone') && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={(e) => { e.stopPropagation(); if (onCompleteByPhone) onCompleteByPhone(key, title); }}
                      className="h-8 text-xs rounded-lg"
                      data-testid={`complete-by-phone-${key}`}
                    >
                      <Phone className="h-3.5 w-3.5 mr-1" />
                      Phone
                    </Button>
                  )}
                </>
              )}
              
              {/* Verify / Reject for awaiting review */}
              {has_acknowledgement && !is_verified && acknowledgement_data?.verification_status === 'awaiting_review' && (
                <>
                  <Button
                    size="sm"
                    variant="default"
                    onClick={(e) => { e.stopPropagation(); handleVerify(); }}
                    disabled={isProcessing}
                    className="h-8 text-xs bg-green-600 hover:bg-green-700 text-white rounded-lg"
                    data-testid={`verify-${key}`}
                  >
                    <CheckCircle className="h-3.5 w-3.5 mr-1" />
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
              
              {/* Fill internally when request is pending */}
              {pending_requests.length > 0 && allowed_actions.includes('fill_internally') && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={(e) => { e.stopPropagation(); if (onFillInternally) onFillInternally(key, title); }}
                  className="h-8 text-xs rounded-lg"
                  data-testid={`fill-internally-pending-${key}`}
                >
                  <Edit className="h-3.5 w-3.5 mr-1" />
                  Complete on Behalf
                </Button>
              )}
            </>
          )}
          
          {/* View History */}
          {counts.history > 0 && (
            <Button
              size="sm"
              variant="ghost"
              onClick={(e) => { e.stopPropagation(); if (onViewHistory) onViewHistory(key); }}
              className="h-8 text-xs"
              data-testid={`history-${key}`}
            >
              <History className="h-3.5 w-3.5 mr-1" />
              {counts.history}
            </Button>
          )}
          
          {/* Expand/Collapse */}
          <Button
            size="sm"
            variant="ghost"
            className="h-8 w-8 p-0"
            onClick={(e) => { e.stopPropagation(); setExpanded(!expanded); }}
          >
            {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </Button>
        </div>
      </div>
      
      {/* Expanded Content - Has Acknowledgement */}
      {expanded && has_acknowledgement && acknowledgement_data && (
        <div className="border-t border-gray-100 p-4 bg-white/50">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            {/* Version */}
            <div>
              <p className="text-xs text-text-muted uppercase tracking-wide">Version</p>
              <p className="font-medium text-text-primary">{acknowledgement_data.version_acknowledged}</p>
            </div>
            
            {/* Completion Mode */}
            <div>
              <p className="text-xs text-text-muted uppercase tracking-wide">Completed Via</p>
              <p className="font-medium text-text-primary">{getCompletionModeDisplay(acknowledgement_data.completion_mode)}</p>
            </div>
            
            {/* Completed At */}
            <div>
              <p className="text-xs text-text-muted uppercase tracking-wide">Completed</p>
              <p className="font-medium text-text-primary">
                {formatBackendDate(acknowledgement_data.completed_at, { format: 'medium' })}
              </p>
            </div>
            
            {/* Verification Status */}
            <div>
              <p className="text-xs text-text-muted uppercase tracking-wide">Status</p>
              <p className={`font-medium ${
                acknowledgement_data.verification_status === 'verified' ? 'text-green-600' :
                acknowledgement_data.verification_status === 'rejected' ? 'text-red-600' : 'text-amber-600'
              }`}>
                {getVerificationStatusDisplay(acknowledgement_data.verification_status)}
              </p>
            </div>
          </div>
          
          {/* Call Note (for phone-assisted) */}
          {acknowledgement_data.call_note && (
            <div className="mt-4 pt-4 border-t border-gray-100">
              <p className="text-xs text-text-muted uppercase tracking-wide mb-1">Call Note</p>
              <p className="text-sm text-text-primary">{acknowledgement_data.call_note}</p>
            </div>
          )}
          
          {/* Verified info */}
          {acknowledgement_data.verified_at && (
            <div className="mt-4 pt-4 border-t border-gray-100 text-sm text-text-muted">
              Verified on {formatBackendDate(acknowledgement_data.verified_at, { format: 'medium' })}
            </div>
          )}
        </div>
      )}
      
      {/* Expanded Content - Pending Request */}
      {expanded && !has_acknowledgement && pending_requests.length > 0 && (
        <div className="border-t border-gray-100 p-4 bg-white/50">
          <h5 className="text-xs font-medium text-text-muted uppercase tracking-wide mb-3">Pending Request</h5>
          {pending_requests.map((req, idx) => (
            <div key={req.id || idx} className="flex items-center gap-3 p-3 bg-blue-50 rounded-lg">
              <Mail className="h-5 w-5 text-blue-600" />
              <div className="flex-1">
                <p className="text-sm font-medium text-blue-900">Form sent to employee</p>
                <p className="text-xs text-blue-700">
                  Sent {formatBackendDate(req.sent_at, { format: 'relative' })} • 
                  Due {formatBackendDate(req.due_at, { format: 'medium' })}
                </p>
              </div>
              <Badge variant="outline" className="text-xs bg-blue-100 text-blue-700 border-blue-200">
                {req.status}
              </Badge>
            </div>
          ))}
        </div>
      )}
      
      {/* Not Completed State */}
      {expanded && !has_acknowledgement && pending_requests.length === 0 && (
        <div className="border-t border-gray-100 p-6 bg-white/50 text-center">
          <FileSignature className="h-10 w-10 mx-auto mb-3 text-red-400" />
          <p className="text-sm text-text-muted mb-2">Agreement not completed yet</p>
          <p className="text-xs text-text-muted mb-4">
            This requirement blocks work readiness until the agreement is completed and verified.
          </p>
          {!isAuditor && (
            <div className="flex items-center justify-center gap-2">
              {allowed_actions.includes('send_form') && employeeEmail && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => onSendForm && onSendForm(key, title)}
                  className="text-blue-600 border-blue-200 hover:bg-blue-50 rounded-lg"
                >
                  <Mail className="h-4 w-4 mr-2" />
                  Send Form
                </Button>
              )}
              {allowed_actions.includes('fill_internally') && (
                <Button
                  size="sm"
                  variant="default"
                  onClick={() => onFillInternally && onFillInternally(key, title)}
                  className="bg-primary hover:bg-primary-hover text-white rounded-lg"
                >
                  <Edit className="h-4 w-4 mr-2" />
                  Fill Internally
                </Button>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
