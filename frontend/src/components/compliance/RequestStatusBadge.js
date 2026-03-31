import { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Badge } from '../ui/badge';
import { 
  Send, Eye, FileText, CheckCircle, Clock, AlertTriangle, XCircle
} from 'lucide-react';
import { formatBackendDate } from '../../lib/dateUtils';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

/**
 * RequestStatusBadge - Inline request lifecycle status for requirement rows
 * 
 * Shows: Not Requested → Sent → Viewed → Submitted → Verified/Rejected
 * Also shows: last_requested_at, last_submitted_at, request_source
 */
export default function RequestStatusBadge({
  employeeId,
  requirementKey,
  compact = false,
  showDetails = true
}) {
  const [loading, setLoading] = useState(true);
  const [requestData, setRequestData] = useState(null);
  
  const { token } = useAuth();

  useEffect(() => {
    if (employeeId && requirementKey) {
      fetchRequestStatus();
    }
  }, [employeeId, requirementKey]);

  const fetchRequestStatus = async () => {
    try {
      const response = await axios.get(
        `${API}/employees/${employeeId}/requirements/${requirementKey}/requests`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setRequestData(response.data);
    } catch (err) {
      // Silently fail - request status is supplementary info
      console.error('Failed to load request status:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading || !requestData) {
    return null; // Don't show anything while loading
  }

  const { overall_status, current_request, last_requested_at, last_submitted_at } = requestData;

  // Status configuration
  const statusConfig = {
    not_requested: {
      label: 'Not Requested',
      icon: null,
      color: 'bg-gray-100 text-gray-500',
      showDate: false
    },
    sent: {
      label: 'Requested',
      icon: Send,
      color: 'bg-blue-100 text-blue-700',
      date: current_request?.sent_at || last_requested_at,
      dateLabel: 'Sent'
    },
    viewed: {
      label: 'Viewed',
      icon: Eye,
      color: 'bg-purple-100 text-purple-700',
      date: current_request?.viewed_at,
      dateLabel: 'Viewed'
    },
    submitted: {
      label: 'Submitted',
      icon: FileText,
      color: 'bg-green-100 text-green-700',
      date: current_request?.submitted_at || last_submitted_at,
      dateLabel: 'Submitted'
    },
    completed: {
      label: 'Completed',
      icon: CheckCircle,
      color: 'bg-green-100 text-green-700',
      showDate: false
    },
    expired_or_cancelled: {
      label: 'Expired',
      icon: AlertTriangle,
      color: 'bg-amber-100 text-amber-700',
      showDate: false
    },
    pending: {
      label: 'Pending',
      icon: Clock,
      color: 'bg-blue-100 text-blue-700',
      showDate: false
    }
  };

  const config = statusConfig[overall_status] || statusConfig.not_requested;
  const Icon = config.icon;

  // Don't show badge for "not_requested" if compact mode
  if (overall_status === 'not_requested' && compact) {
    return null;
  }

  // Compact mode - just the badge
  if (compact) {
    return (
      <Badge className={`text-[10px] px-1.5 py-0 ${config.color}`}>
        {Icon && <Icon className="h-2.5 w-2.5 mr-0.5" />}
        {config.label}
      </Badge>
    );
  }

  // Full mode - badge with date
  return (
    <div className="flex items-center gap-2 text-xs" data-testid={`request-status-${requirementKey}`}>
      <Badge className={`text-[10px] px-1.5 py-0 ${config.color}`}>
        {Icon && <Icon className="h-2.5 w-2.5 mr-0.5" />}
        {config.label}
      </Badge>
      
      {showDetails && config.date && (
        <span className="text-text-muted">
          {config.dateLabel} {formatBackendDate(config.date, { format: 'relative' })}
        </span>
      )}
      
      {showDetails && current_request?.source === 'scheduled' && (
        <Badge className="text-[10px] px-1 py-0 bg-gray-100 text-gray-500">
          Auto
        </Badge>
      )}
    </div>
  );
}


/**
 * RequestStatusInline - Simple inline text for row summaries
 * Shows: "Last requested 31 Mar" or "Submitted 02 Apr"
 */
export function RequestStatusInline({
  employeeId,
  requirementKey
}) {
  const [requestData, setRequestData] = useState(null);
  const { token } = useAuth();

  useEffect(() => {
    if (employeeId && requirementKey) {
      fetchRequestStatus();
    }
  }, [employeeId, requirementKey]);

  const fetchRequestStatus = async () => {
    try {
      const response = await axios.get(
        `${API}/employees/${employeeId}/requirements/${requirementKey}/requests`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setRequestData(response.data);
    } catch (err) {
      // Silently fail
    }
  };

  if (!requestData || requestData.overall_status === 'not_requested') {
    return null;
  }

  const { overall_status, current_request, last_requested_at, last_submitted_at } = requestData;

  // Build status text
  let statusText = '';
  
  if (overall_status === 'submitted' && (current_request?.submitted_at || last_submitted_at)) {
    const date = current_request?.submitted_at || last_submitted_at;
    statusText = `Submitted ${formatBackendDate(date, { format: 'short' })}`;
  } else if (overall_status === 'viewed' && current_request?.viewed_at) {
    statusText = `Viewed ${formatBackendDate(current_request.viewed_at, { format: 'short' })}`;
  } else if (overall_status === 'sent' && (current_request?.sent_at || last_requested_at)) {
    const date = current_request?.sent_at || last_requested_at;
    statusText = `Requested ${formatBackendDate(date, { format: 'short' })}`;
  } else if (overall_status === 'completed') {
    statusText = 'Request completed';
  }

  if (!statusText) return null;

  return (
    <span className="text-xs text-text-muted" data-testid={`request-inline-${requirementKey}`}>
      {statusText}
      {current_request?.source === 'scheduled' && ' (auto)'}
    </span>
  );
}
