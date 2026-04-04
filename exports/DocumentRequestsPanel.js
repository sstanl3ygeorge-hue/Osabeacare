import { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { toast } from 'sonner';
import { 
  Mail, Send, CheckCircle, Clock, AlertTriangle, Eye, 
  Loader2, RefreshCw, FileText, Calendar, XCircle
} from 'lucide-react';
import { formatBackendDate } from '../../lib/dateUtils';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const STATUS_CONFIG = {
  pending_send: { label: 'Pending', color: 'bg-gray-100 text-gray-600', icon: Clock },
  sent: { label: 'Sent', color: 'bg-blue-100 text-blue-700', icon: Send },
  opened: { label: 'Opened', color: 'bg-cyan-100 text-cyan-700', icon: Eye },
  clicked: { label: 'Link Clicked', color: 'bg-indigo-100 text-indigo-700', icon: Eye },
  submitted: { label: 'Submitted', color: 'bg-green-100 text-green-700', icon: CheckCircle },
  completed: { label: 'Completed', color: 'bg-green-100 text-green-700', icon: CheckCircle },
  expired: { label: 'Expired', color: 'bg-red-100 text-red-700', icon: XCircle },
  cancelled: { label: 'Cancelled', color: 'bg-gray-100 text-gray-500', icon: XCircle },
  superseded: { label: 'Superseded', color: 'bg-gray-100 text-gray-500', icon: XCircle },
  overdue: { label: 'Overdue', color: 'bg-amber-100 text-amber-700', icon: AlertTriangle }
};

export default function DocumentRequestsPanel({ employeeId, onRefresh }) {
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchRequests = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API}/employees/${employeeId}/document-requests`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      // Process requests to add overdue status
      const processed = (response.data || []).map(req => {
        let status = req.status;
        if (req.due_at && ['sent', 'opened', 'clicked'].includes(status)) {
          const dueDate = new Date(req.due_at);
          if (dueDate < new Date()) {
            status = 'overdue';
          }
        }
        return { ...req, displayStatus: status };
      });
      
      setRequests(processed);
    } catch (error) {
      console.error('Failed to fetch document requests:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (employeeId) {
      fetchRequests();
    }
  }, [employeeId]);

  const getStatusConfig = (status) => {
    return STATUS_CONFIG[status] || STATUS_CONFIG.pending_send;
  };

  // Group requests by status
  const activeRequests = requests.filter(r => 
    ['pending_send', 'sent', 'opened', 'clicked', 'overdue'].includes(r.displayStatus)
  );
  const completedRequests = requests.filter(r => 
    ['submitted', 'completed'].includes(r.displayStatus)
  );

  if (loading) {
    return (
      <Card className="border-[#E4E8EB] shadow-sm">
        <CardContent className="py-8 flex justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-primary" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-[#E4E8EB] shadow-sm">
      <CardHeader>
        <CardTitle className="font-heading text-lg flex items-center justify-between">
          <span className="flex items-center gap-2">
            <Mail className="h-5 w-5 text-primary" />
            Document Requests
          </span>
          <Button 
            variant="outline" 
            size="sm" 
            onClick={fetchRequests}
            disabled={loading}
            className="rounded-xl"
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </CardTitle>
        <p className="text-sm text-gray-500 mt-1">
          Track document request status - sent, opened, submitted
        </p>
      </CardHeader>
      <CardContent className="space-y-6">
        {requests.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <Mail className="h-10 w-10 mx-auto mb-3 text-gray-300" />
            <p>No document requests sent yet</p>
            <p className="text-xs mt-1">Use the Request buttons in Compliance tab to send requests</p>
          </div>
        ) : (
          <>
            {/* Active Requests */}
            {activeRequests.length > 0 && (
              <div className="space-y-3">
                <h4 className="text-sm font-medium text-gray-700 flex items-center gap-2">
                  <Clock className="h-4 w-4" />
                  Pending Requests ({activeRequests.length})
                </h4>
                <div className="space-y-2">
                  {activeRequests.map((request, index) => {
                    const config = getStatusConfig(request.displayStatus);
                    const StatusIcon = config.icon;
                    
                    return (
                      <div 
                        key={request.id || index}
                        className="flex items-center justify-between p-3 bg-gray-50 rounded-lg border border-gray-100"
                        data-testid={`request-item-${index}`}
                      >
                        <div className="flex items-center gap-3">
                          <div className={`p-2 rounded-lg ${config.color.split(' ')[0]}`}>
                            <FileText className={`h-4 w-4 ${config.color.split(' ')[1]}`} />
                          </div>
                          <div>
                            <p className="font-medium text-gray-900 text-sm">
                              {request.requirement_name || request.requirement_id?.replace(/_/g, ' ')}
                            </p>
                            <div className="flex items-center gap-2 text-xs text-gray-500">
                              {request.sent_at && (
                                <span>Sent: {formatBackendDate(request.sent_at)}</span>
                              )}
                              {request.due_at && (
                                <>
                                  <span>•</span>
                                  <span className={request.displayStatus === 'overdue' ? 'text-amber-600' : ''}>
                                    Due: {formatBackendDate(request.due_at)}
                                  </span>
                                </>
                              )}
                            </div>
                          </div>
                        </div>
                        <Badge className={`${config.color} flex items-center gap-1`}>
                          <StatusIcon className="h-3 w-3" />
                          {config.label}
                        </Badge>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Completed Requests */}
            {completedRequests.length > 0 && (
              <div className="space-y-3">
                <h4 className="text-sm font-medium text-gray-700 flex items-center gap-2">
                  <CheckCircle className="h-4 w-4 text-green-600" />
                  Completed ({completedRequests.length})
                </h4>
                <div className="space-y-2">
                  {completedRequests.slice(0, 5).map((request, index) => {
                    const config = getStatusConfig(request.displayStatus);
                    const StatusIcon = config.icon;
                    
                    return (
                      <div 
                        key={request.id || index}
                        className="flex items-center justify-between p-3 bg-green-50/50 rounded-lg border border-green-100"
                      >
                        <div className="flex items-center gap-3">
                          <div className="p-2 rounded-lg bg-green-100">
                            <FileText className="h-4 w-4 text-green-600" />
                          </div>
                          <div>
                            <p className="font-medium text-gray-900 text-sm">
                              {request.requirement_name || request.requirement_id?.replace(/_/g, ' ')}
                            </p>
                            <p className="text-xs text-gray-500">
                              Submitted: {formatBackendDate(request.submitted_at || request.updated_at)}
                            </p>
                          </div>
                        </div>
                        <Badge className={`${config.color} flex items-center gap-1`}>
                          <StatusIcon className="h-3 w-3" />
                          {config.label}
                        </Badge>
                      </div>
                    );
                  })}
                  {completedRequests.length > 5 && (
                    <p className="text-xs text-gray-500 text-center">
                      +{completedRequests.length - 5} more completed
                    </p>
                  )}
                </div>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
