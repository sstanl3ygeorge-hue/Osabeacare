import { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Badge } from '../ui/badge';
import { toast } from 'sonner';
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '../ui/sheet';
import { 
  History, Upload, Send, Eye, CheckCircle, XCircle, 
  AlertTriangle, Clock, FileText, ArrowRight, RefreshCw,
  Loader2, Shield, FileCheck, Trash2, Archive
} from 'lucide-react';
import { formatBackendDate } from '../../lib/dateUtils';
import { API_BASE_URL, API_ROOT_URL } from './';

const API = API_BASE_URL;

/**
 * RequirementHistoryDrawer - Shows unified timeline history for a requirement
 * 
 * Timeline includes:
 * - Uploads, requests sent, submissions received
 * - Verification actions, rejections
 * - Superseded files, uploaded in error, moved category
 * - Check updates, agreement completion events
 */
export default function RequirementHistoryDrawer({
  open,
  onClose,
  employeeId,
  requirementKey,
  requirementTitle
}) {
  const [loading, setLoading] = useState(false);
  const [historyData, setHistoryData] = useState(null);
  
  const { token } = useAuth();

  // Fetch history when drawer opens
  useEffect(() => {
    if (open && employeeId && requirementKey) {
      fetchHistory();
    }
  }, [open, employeeId, requirementKey]);

  const fetchHistory = async () => {
    setLoading(true);
    try {
      const response = await axios.get(
        `${API}/employees/${employeeId}/requirements/${requirementKey}/unified-history`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setHistoryData(response.data);
    } catch (err) {
      toast.error('Failed to load history');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  // Get icon for event type
  const getEventIcon = (eventType) => {
    switch (eventType) {
      case 'document_uploaded':
      case 'uploaded':
        return <Upload className="h-4 w-4 text-blue-500" />;
      case 'request_sent':
      case 'document_requested':
        return <Send className="h-4 w-4 text-blue-500" />;
      case 'request_clicked':
      case 'request_viewed':
        return <Eye className="h-4 w-4 text-purple-500" />;
      case 'request_submitted':
      case 'document_submitted':
        return <FileText className="h-4 w-4 text-green-500" />;
      case 'document_verified':
      case 'verified':
        return <CheckCircle className="h-4 w-4 text-green-600" />;
      case 'document_rejected':
      case 'rejected':
        return <XCircle className="h-4 w-4 text-red-500" />;
      case 'check_recorded':
        return <Shield className="h-4 w-4 text-green-600" />;
      case 'agreement_completed':
        return <FileCheck className="h-4 w-4 text-green-600" />;
      case 'document_superseded':
      case 'superseded':
        return <RefreshCw className="h-4 w-4 text-amber-500" />;
      case 'document_marked_uploaded_in_error':
      case 'uploaded_in_error':
        return <Trash2 className="h-4 w-4 text-red-500" />;
      case 'document_moved_category':
      case 'moved':
        return <ArrowRight className="h-4 w-4 text-blue-500" />;
      case 'evidence_edited':
        return <FileText className="h-4 w-4 text-gray-500" />;
      case 'extraction_reviewed':
        return <Eye className="h-4 w-4 text-purple-500" />;
      default:
        return <Clock className="h-4 w-4 text-gray-400" />;
    }
  };

  // Get label for event type
  const getEventLabel = (eventType) => {
    switch (eventType) {
      case 'document_uploaded':
      case 'uploaded':
        return 'File Uploaded';
      case 'request_sent':
      case 'document_requested':
        return 'Request Sent';
      case 'request_clicked':
      case 'request_viewed':
        return 'Request Viewed';
      case 'request_submitted':
      case 'document_submitted':
        return 'Document Submitted';
      case 'document_verified':
      case 'verified':
        return 'Verified';
      case 'document_rejected':
      case 'rejected':
        return 'Rejected';
      case 'check_recorded':
        return 'Check Recorded';
      case 'agreement_completed':
        return 'Agreement Completed';
      case 'document_superseded':
      case 'superseded':
        return 'File Superseded';
      case 'document_marked_uploaded_in_error':
      case 'uploaded_in_error':
        return 'Marked as Error';
      case 'document_moved_category':
      case 'moved':
        return 'Moved Category';
      case 'evidence_edited':
        return 'Evidence Edited';
      case 'extraction_reviewed':
        return 'Extraction Reviewed';
      case 'document_request_resent':
        return 'Request Resent';
      case 'document_replacement_requested':
        return 'Replacement Requested';
      default:
        return eventType?.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()) || 'Event';
    }
  };

  // Get badge color for event type
  const getEventBadgeClass = (eventType) => {
    if (eventType.includes('verified') || eventType.includes('check_recorded') || eventType.includes('agreement_completed')) {
      return 'bg-green-100 text-green-700';
    }
    if (eventType.includes('rejected') || eventType.includes('error')) {
      return 'bg-red-100 text-red-700';
    }
    if (eventType.includes('request') || eventType.includes('sent')) {
      return 'bg-blue-100 text-blue-700';
    }
    if (eventType.includes('superseded') || eventType.includes('moved')) {
      return 'bg-amber-100 text-amber-700';
    }
    if (eventType.includes('uploaded') || eventType.includes('submitted')) {
      return 'bg-green-100 text-green-700';
    }
    return 'bg-gray-100 text-gray-700';
  };

  // Format event details
  const formatDetails = (event) => {
    const details = event.details || {};
    const parts = [];

    if (details.filename) parts.push(`File: ${details.filename}`);
    if (details.file_name) parts.push(`File: ${details.file_name}`);
    if (details.method) parts.push(`Method: ${details.method}`);
    if (details.outcome) parts.push(`Outcome: ${details.outcome}`);
    if (details.reason) parts.push(`Reason: ${details.reason}`);
    if (details.rejection_reason) parts.push(`Reason: ${details.rejection_reason}`);
    if (details.version_acknowledged) parts.push(`Version: ${details.version_acknowledged}`);
    if (details.completion_mode) parts.push(`Mode: ${details.completion_mode}`);
    if (details.valid_until) parts.push(`Valid until: ${formatBackendDate(details.valid_until, { format: 'short' })}`);
    if (details.request_type) parts.push(`Type: ${details.request_type}`);
    if (details.source) parts.push(`Source: ${details.source}`);
    if (details.old_requirement_id && details.new_requirement_id) {
      parts.push(`From: ${details.old_requirement_id} → ${details.new_requirement_id}`);
    }
    if (details.field_changed) {
      parts.push(`${details.field_changed}: ${details.old_value} → ${details.new_value}`);
    }

    return parts;
  };

  return (
    <Sheet open={open} onOpenChange={onClose}>
      <SheetContent side="right" className="w-full sm:max-w-lg overflow-y-auto">
        <SheetHeader className="mb-6">
          <SheetTitle className="font-heading flex items-center gap-2">
            <History className="h-5 w-5 text-gray-600" />
            {requirementTitle || 'Requirement'} History
          </SheetTitle>
          <SheetDescription>
            Complete audit trail for this requirement
          </SheetDescription>
        </SheetHeader>

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        ) : historyData ? (
          <div className="space-y-1">
            {historyData.timeline?.length === 0 ? (
              <div className="p-6 bg-gray-50 rounded-lg text-center">
                <History className="h-8 w-8 text-gray-300 mx-auto mb-2" />
                <p className="text-sm text-text-muted">No history recorded yet</p>
              </div>
            ) : (
              <div className="relative">
                {/* Timeline line */}
                <div className="absolute left-5 top-0 bottom-0 w-px bg-gray-200" />
                
                {/* Timeline events */}
                <div className="space-y-4">
                  {historyData.timeline?.map((event, idx) => (
                    <div 
                      key={idx}
                      className="relative pl-12"
                      data-testid={`history-event-${idx}`}
                    >
                      {/* Event icon */}
                      <div className="absolute left-2.5 w-5 h-5 bg-white rounded-full flex items-center justify-center border border-gray-200">
                        {getEventIcon(event.event_type)}
                      </div>
                      
                      {/* Event content */}
                      <div className="p-3 bg-white border border-gray-200 rounded-lg hover:border-gray-300 transition-colors">
                        <div className="flex items-center justify-between gap-2 flex-wrap">
                          <Badge className={`text-xs ${getEventBadgeClass(event.event_type)}`}>
                            {getEventLabel(event.event_type)}
                          </Badge>
                          <span className="text-xs text-text-muted">
                            {formatBackendDate(event.timestamp, { format: 'medium' })}
                          </span>
                        </div>
                        
                        {/* User who performed action */}
                        {event.user_name && (
                          <p className="text-xs text-text-muted mt-1">
                            by {event.user_name}
                          </p>
                        )}
                        
                        {/* Event details */}
                        {formatDetails(event).length > 0 && (
                          <div className="mt-2 text-xs text-text-muted space-y-0.5">
                            {formatDetails(event).map((detail, i) => (
                              <p key={i}>{detail}</p>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
            
            {/* Total events */}
            <div className="pt-4 text-xs text-text-muted text-center">
              {historyData.total_events || 0} events in history
            </div>
          </div>
        ) : (
          <div className="py-12 text-center text-text-muted">
            Failed to load history
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
}

