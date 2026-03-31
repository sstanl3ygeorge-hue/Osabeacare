import { useState } from 'react';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { 
  Send, Eye, FileText, CheckCircle, Clock, AlertTriangle, 
  XCircle, RefreshCw, Loader2
} from 'lucide-react';
import { formatBackendDate } from '../../lib/dateUtils';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

/**
 * RequestLifecycleInline - Inline request status display for Evidence rows
 * 
 * Shows full lifecycle state: Not Requested → Requested → Viewed → Submitted → Awaiting Review → Verified/Rejected
 * Includes stale request handling, multi-file awareness, and quick actions
 */
export default function RequestLifecycleInline({
  requestLifecycle,
  employeeId,
  employeeEmail,
  requirementKey,
  requirementTitle,
  onRequest,
  onRefresh,
  isMultiFile = false,
  compact = false,
  showQuickActions = true
}) {
  const [isResending, setIsResending] = useState(false);
  const { token } = useAuth();

  if (!requestLifecycle) return null;

  const {
    status,
    current_request,
    last_requested_at,
    last_viewed_at,
    last_submitted_at,
    source,
    is_stale,
    stale_days,
    files_submitted,
    files_needed,
    can_resend,
    can_request_replacement,
    is_replacement_request
  } = requestLifecycle;

  // Status configuration
  const statusConfig = {
    not_requested: {
      label: 'Not Requested',
      icon: null,
      color: 'bg-gray-100 text-gray-500 border-gray-200',
      bgClass: ''
    },
    pending: {
      label: 'Pending',
      icon: Clock,
      color: 'bg-blue-100 text-blue-700 border-blue-200',
      bgClass: ''
    },
    sent: {
      label: 'Requested',
      icon: Send,
      color: 'bg-blue-100 text-blue-700 border-blue-200',
      bgClass: ''
    },
    viewed: {
      label: 'Viewed',
      icon: Eye,
      color: 'bg-purple-100 text-purple-700 border-purple-200',
      bgClass: ''
    },
    submitted: {
      label: 'Submitted',
      icon: FileText,
      color: 'bg-green-100 text-green-700 border-green-200',
      bgClass: ''
    },
    awaiting_review: {
      label: 'Awaiting Review',
      icon: Clock,
      color: 'bg-amber-100 text-amber-700 border-amber-200',
      bgClass: ''
    },
    verified: {
      label: 'Verified',
      icon: CheckCircle,
      color: 'bg-green-100 text-green-700 border-green-200',
      bgClass: ''
    },
    rejected: {
      label: 'Rejected',
      icon: XCircle,
      color: 'bg-red-100 text-red-700 border-red-200',
      bgClass: ''
    },
    replacement_requested: {
      label: 'Replacement Requested',
      icon: RefreshCw,
      color: 'bg-amber-100 text-amber-700 border-amber-200',
      bgClass: ''
    },
    expired: {
      label: 'Request Expired',
      icon: AlertTriangle,
      color: 'bg-gray-100 text-gray-500 border-gray-200',
      bgClass: ''
    }
  };

  // Handle resend request
  const handleResend = async (e) => {
    e.stopPropagation();
    if (!employeeEmail) {
      toast.error('Employee has no email address');
      return;
    }
    
    setIsResending(true);
    try {
      await axios.post(
        `${API}/employees/${employeeId}/requirements/${requirementKey}/resend-request`,
        { message: `Please submit your ${requirementTitle}` },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Request resent successfully');
      if (onRefresh) onRefresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to resend request');
    } finally {
      setIsResending(false);
    }
  };

  // Handle request replacement
  const handleRequestReplacement = async (e) => {
    e.stopPropagation();
    if (!employeeEmail) {
      toast.error('Employee has no email address');
      return;
    }
    
    setIsResending(true);
    try {
      await axios.post(
        `${API}/employees/${employeeId}/requirements/${requirementKey}/request-replacement`,
        { reason: 'Updated document required' },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Replacement requested');
      if (onRefresh) onRefresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to request replacement');
    } finally {
      setIsResending(false);
    }
  };

  // Determine display status
  let displayStatus = status;
  if (is_replacement_request) {
    displayStatus = 'replacement_requested';
  }
  
  const config = statusConfig[displayStatus] || statusConfig.not_requested;
  const Icon = config.icon;

  // Build timeline string
  const buildTimelineText = () => {
    const parts = [];
    
    if (last_requested_at) {
      parts.push(`Requested ${formatBackendDate(last_requested_at, { format: 'relative' })}`);
    }
    if (last_viewed_at) {
      parts.push(`Viewed ${formatBackendDate(last_viewed_at, { format: 'relative' })}`);
    }
    if (last_submitted_at) {
      parts.push(`Submitted ${formatBackendDate(last_submitted_at, { format: 'relative' })}`);
    }
    
    return parts.join(' • ');
  };

  // Build multi-file status text
  const buildMultiFileText = () => {
    if (!isMultiFile) return null;
    
    if (files_submitted > 0 && files_needed > 0) {
      return `${files_submitted} submitted • ${files_needed} still needed`;
    } else if (files_submitted > 0) {
      return `${files_submitted} file${files_submitted !== 1 ? 's' : ''} submitted`;
    } else if (files_needed > 0) {
      return `${files_needed} file${files_needed !== 1 ? 's' : ''} needed`;
    }
    return null;
  };

  // Compact mode - just status badge
  if (compact) {
    if (status === 'not_requested') return null;
    
    return (
      <Badge 
        className={`text-[10px] px-1.5 py-0 border ${config.color}`}
        data-testid={`request-status-compact-${requirementKey}`}
      >
        {Icon && <Icon className="h-2.5 w-2.5 mr-0.5" />}
        {config.label}
      </Badge>
    );
  }

  // Full mode
  return (
    <div 
      className="flex flex-wrap items-center gap-2 text-xs"
      data-testid={`request-lifecycle-${requirementKey}`}
    >
      {/* Status Badge */}
      <Badge 
        className={`text-[10px] px-2 py-0.5 border ${config.color}`}
        data-testid={`request-status-${requirementKey}`}
      >
        {Icon && <Icon className="h-3 w-3 mr-1" />}
        {config.label}
      </Badge>
      
      {/* Timeline info */}
      {status !== 'not_requested' && (
        <span className="text-text-muted">
          {buildTimelineText()}
        </span>
      )}
      
      {/* Source badge (manual/scheduled) */}
      {source === 'scheduled' && status !== 'not_requested' && (
        <Badge className="text-[10px] px-1 py-0 bg-gray-100 text-gray-500 border border-gray-200">
          Auto
        </Badge>
      )}
      
      {/* Stale warning */}
      {is_stale && (
        <Badge className="text-[10px] px-1.5 py-0 bg-amber-100 text-amber-700 border border-amber-200">
          <AlertTriangle className="h-2.5 w-2.5 mr-0.5" />
          Stale ({stale_days}d)
        </Badge>
      )}
      
      {/* Multi-file status */}
      {buildMultiFileText() && (
        <span className="text-text-muted">
          {buildMultiFileText()}
        </span>
      )}
      
      {/* Quick Actions */}
      {showQuickActions && (
        <div className="flex items-center gap-1 ml-auto">
          {/* Request button - for not_requested state */}
          {status === 'not_requested' && employeeEmail && onRequest && (
            <Button
              size="sm"
              variant="ghost"
              onClick={(e) => { e.stopPropagation(); onRequest(requirementKey, requirementTitle); }}
              className="h-6 px-2 text-xs text-blue-600 hover:text-blue-700 hover:bg-blue-50"
              data-testid={`quick-request-${requirementKey}`}
            >
              <Send className="h-3 w-3 mr-1" />
              Request
            </Button>
          )}
          
          {/* Resend button - for stale or sent/viewed states */}
          {can_resend && (is_stale || ['sent', 'viewed'].includes(status)) && employeeEmail && (
            <Button
              size="sm"
              variant="ghost"
              onClick={handleResend}
              disabled={isResending}
              className="h-6 px-2 text-xs text-amber-600 hover:text-amber-700 hover:bg-amber-50"
              data-testid={`quick-resend-${requirementKey}`}
            >
              {isResending ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : (
                <>
                  <RefreshCw className="h-3 w-3 mr-1" />
                  Resend
                </>
              )}
            </Button>
          )}
          
          {/* Request replacement - when files exist but need update */}
          {can_request_replacement && employeeEmail && status !== 'not_requested' && (
            <Button
              size="sm"
              variant="ghost"
              onClick={handleRequestReplacement}
              disabled={isResending}
              className="h-6 px-2 text-xs text-gray-600 hover:text-gray-700 hover:bg-gray-50"
              data-testid={`quick-replacement-${requirementKey}`}
            >
              Request Replacement
            </Button>
          )}
        </div>
      )}
    </div>
  );
}


/**
 * RequestLifecycleSummary - Very compact inline text for row summaries
 */
export function RequestLifecycleSummary({ requestLifecycle, requirementKey }) {
  if (!requestLifecycle || requestLifecycle.status === 'not_requested') {
    return null;
  }

  const { status, last_requested_at, last_viewed_at, last_submitted_at, is_stale, stale_days, source } = requestLifecycle;

  // Build summary text
  let summaryText = '';
  
  if (status === 'submitted' && last_submitted_at) {
    summaryText = `Submitted ${formatBackendDate(last_submitted_at, { format: 'short' })}`;
  } else if (status === 'viewed' && last_viewed_at) {
    summaryText = `Viewed ${formatBackendDate(last_viewed_at, { format: 'short' })}`;
  } else if (['sent', 'pending'].includes(status) && last_requested_at) {
    summaryText = `Requested ${formatBackendDate(last_requested_at, { format: 'short' })}`;
    if (is_stale) {
      summaryText += ` (stale - ${stale_days}d)`;
    }
  }

  if (!summaryText) return null;

  return (
    <span 
      className={`text-xs ${is_stale ? 'text-amber-600' : 'text-text-muted'}`}
      data-testid={`request-summary-${requirementKey}`}
    >
      {summaryText}
      {source === 'scheduled' && ' (auto)'}
    </span>
  );
}
