import { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { toast } from 'sonner';
import { 
  History, Upload, CheckCircle, XCircle, Edit, Eye, FileText,
  Loader2, RefreshCw, Clock, AlertTriangle, ChevronRight
} from 'lucide-react';
import { formatBackendDate } from '../../lib/dateUtils';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const ACTION_CONFIG = {
  document_uploaded: { label: 'Document Uploaded', color: 'bg-blue-100 text-blue-700', icon: Upload },
  document_verified: { label: 'Document Verified', color: 'bg-green-100 text-green-700', icon: CheckCircle },
  document_rejected: { label: 'Document Rejected', color: 'bg-red-100 text-red-700', icon: XCircle },
  check_recorded: { label: 'Check Recorded', color: 'bg-purple-100 text-purple-700', icon: FileText },
  status_changed: { label: 'Status Changed', color: 'bg-amber-100 text-amber-700', icon: Edit },
  reference_requested: { label: 'Reference Requested', color: 'bg-cyan-100 text-cyan-700', icon: FileText },
  reference_received: { label: 'Reference Received', color: 'bg-indigo-100 text-indigo-700', icon: FileText },
  reference_verified: { label: 'Reference Verified', color: 'bg-green-100 text-green-700', icon: CheckCircle },
  health_declaration_submitted: { label: 'Health Declaration', color: 'bg-teal-100 text-teal-700', icon: FileText },
  health_declaration_reviewed: { label: 'Health Review', color: 'bg-emerald-100 text-emerald-700', icon: CheckCircle },
  training_completed: { label: 'Training Completed', color: 'bg-violet-100 text-violet-700', icon: CheckCircle },
  policy_signed: { label: 'Policy Signed', color: 'bg-lime-100 text-lime-700', icon: FileText },
  profile_updated: { label: 'Profile Updated', color: 'bg-gray-100 text-gray-600', icon: Edit },
  viewed: { label: 'Viewed', color: 'bg-slate-100 text-slate-600', icon: Eye }
};

export default function AuditTrailPanel({ employeeId }) {
  const [auditLogs, setAuditLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');
  const [pagination, setPagination] = useState({ limit: 50, skip: 0 });

  const fetchAuditTrail = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      const params = new URLSearchParams({
        limit: pagination.limit.toString(),
        skip: pagination.skip.toString()
      });
      if (filter !== 'all') {
        params.append('action_type', filter);
      }
      
      const response = await axios.get(
        `${API}/employees/${employeeId}/audit-trail?${params}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setAuditLogs(response.data.audit_trail || []);
    } catch (error) {
      console.error('Failed to fetch audit trail:', error);
      // Silently fail - audit is optional
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (employeeId) {
      fetchAuditTrail();
    }
  }, [employeeId, filter]);

  const formatAction = (action) => {
    const config = ACTION_CONFIG[action] || { label: action, color: 'bg-gray-100 text-gray-600', icon: Clock };
    return config;
  };

  if (loading) {
    return (
      <Card className="border-[#E4E8EB] shadow-sm">
        <CardContent className="py-12 flex justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-[#E4E8EB] shadow-sm">
      <CardHeader>
        <CardTitle className="font-heading text-lg flex items-center justify-between">
          <span className="flex items-center gap-2">
            <History className="h-5 w-5 text-primary" />
            Audit Trail
          </span>
          <div className="flex items-center gap-2">
            <Select value={filter} onValueChange={setFilter}>
              <SelectTrigger className="w-40 rounded-lg">
                <SelectValue placeholder="Filter..." />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Actions</SelectItem>
                <SelectItem value="document_uploaded">Uploads</SelectItem>
                <SelectItem value="document_verified">Verifications</SelectItem>
                <SelectItem value="check_recorded">Checks</SelectItem>
                <SelectItem value="status_changed">Status Changes</SelectItem>
              </SelectContent>
            </Select>
            <Button 
              variant="outline" 
              size="sm" 
              onClick={fetchAuditTrail}
              disabled={loading}
              className="rounded-xl"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            </Button>
          </div>
        </CardTitle>
        <p className="text-sm text-gray-500 mt-1">
          Complete CQC-compliant activity log for compliance auditing
        </p>
      </CardHeader>
      <CardContent>
        {auditLogs.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <History className="h-12 w-12 mx-auto mb-3 text-gray-300" />
            <p>No audit events recorded yet</p>
            <p className="text-xs mt-1">Activity will be logged automatically</p>
          </div>
        ) : (
          <div className="space-y-1">
            {auditLogs.map((log, index) => {
              const config = formatAction(log.action);
              const ActionIcon = config.icon;
              
              return (
                <div 
                  key={log.id || index}
                  className="flex items-start gap-3 py-3 border-b border-gray-100 last:border-0 hover:bg-gray-50 transition-colors rounded-lg px-2"
                  data-testid={`audit-log-${index}`}
                >
                  {/* Timeline Indicator */}
                  <div className="flex flex-col items-center pt-1">
                    <div className={`w-8 h-8 rounded-full ${config.color.split(' ')[0]} flex items-center justify-center`}>
                      <ActionIcon className={`h-4 w-4 ${config.color.split(' ')[1]}`} />
                    </div>
                    {index < auditLogs.length - 1 && (
                      <div className="w-0.5 h-full bg-gray-200 mt-1" />
                    )}
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <Badge className={`${config.color} text-xs`}>
                        {config.label}
                      </Badge>
                      {log.entity_type && (
                        <span className="text-xs text-gray-500">
                          {log.entity_type.replace(/_/g, ' ')}
                        </span>
                      )}
                    </div>
                    
                    {log.description && (
                      <p className="text-sm text-gray-700 mt-1">{log.description}</p>
                    )}
                    
                    {/* Metadata */}
                    {log.metadata && Object.keys(log.metadata).length > 0 && (
                      <div className="mt-2 text-xs text-gray-500 bg-gray-50 rounded-lg p-2 space-y-1">
                        {Object.entries(log.metadata).slice(0, 4).map(([key, value]) => (
                          <div key={key} className="flex items-center gap-2">
                            <ChevronRight className="h-3 w-3" />
                            <span className="font-medium">{key.replace(/_/g, ' ')}:</span>
                            <span>{typeof value === 'object' ? JSON.stringify(value) : String(value)}</span>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Footer */}
                    <div className="flex items-center gap-4 mt-2 text-xs text-gray-400">
                      {log.user_name && (
                        <span>By: {log.user_name}</span>
                      )}
                      {log.timestamp && (
                        <span>{formatBackendDate(log.timestamp)}</span>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Load More */}
        {auditLogs.length >= pagination.limit && (
          <div className="text-center pt-4">
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setPagination(prev => ({ ...prev, limit: prev.limit + 50 }));
              }}
              className="rounded-lg"
            >
              Load More
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
