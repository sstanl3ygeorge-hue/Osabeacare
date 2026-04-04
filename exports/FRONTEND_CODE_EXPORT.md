# Osabea Healthcare Compliance Portal - Frontend Code Export
# Generated: $(date)

This document contains all relevant frontend code for ChatGPT to restructure.
Files are separated by clear markers.

---

---
## FILE: AuditTrailPanel.js
## Lines: 214
```javascript
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
```
--- END AuditTrailPanel.js ---

---
## FILE: DocumentRequestsPanel.js
## Lines: 222
```javascript
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
```
--- END DocumentRequestsPanel.js ---

---
## FILE: DocumentUploadPage.js
## Lines: 387
```javascript
import { useState, useEffect, useCallback } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { 
  Upload, CheckCircle, XCircle, Loader2, AlertTriangle,
  ArrowLeft, FileText, Home, Clock, Shield, File
} from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

export default function DocumentUploadPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');
  const requestId = searchParams.get('request_id');
  const requirementParam = searchParams.get('requirement');
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [tokenData, setTokenData] = useState(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploaded, setUploaded] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);
  const [dragActive, setDragActive] = useState(false);

  useEffect(() => {
    if (token) {
      validateToken();
    } else {
      setError({ type: 'error', message: 'No upload token provided. Please use the link from your email.' });
      setLoading(false);
    }
  }, [token]);

  const validateToken = async () => {
    try {
      const response = await axios.get(`${API}/api/public/validate-upload-token`, {
        params: { 
          token, 
          request_id: requestId,
          requirement: requirementParam 
        }
      });
      setTokenData(response.data);
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (detail?.includes('expired') || detail?.includes('invalid')) {
        setError({ type: 'expired', message: 'This upload link has expired or is no longer valid. Please contact your recruitment manager for a new link.' });
      } else if (detail?.includes('completed') || detail?.includes('submitted')) {
        setError({ type: 'already_done', message: 'This document has already been uploaded. If you need to upload a replacement, please contact your recruitment manager.' });
      } else {
        setError({ type: 'error', message: detail || 'Failed to validate upload link' });
      }
    } finally {
      setLoading(false);
    }
  };

  const handleDrag = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  }, []);

  const handleFileSelect = (file) => {
    if (!file) return;
    
    // Validate file size (10MB max)
    if (file.size > 10 * 1024 * 1024) {
      toast.error('File is too large. Maximum size is 10MB.');
      return;
    }
    
    // Validate file type
    const allowedExtensions = tokenData?.allowed_extensions || ['.pdf', '.jpg', '.jpeg', '.png', '.webp'];
    const fileExt = '.' + file.name.split('.').pop().toLowerCase();
    if (!allowedExtensions.includes(fileExt)) {
      toast.error(`File type not allowed. Accepted formats: ${allowedExtensions.join(', ')}`);
      return;
    }
    
    setSelectedFile(file);
  };

  const handleUpload = async () => {
    if (!selectedFile || !token) return;
    
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('token', token);
      formData.append('file', selectedFile);
      if (requestId) {
        formData.append('request_id', requestId);
      }
      
      const response = await axios.post(`${API}/api/public/upload-document`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      setUploaded(true);
      setUploadResult(response.data);
      toast.success('Document uploaded successfully!');
    } catch (err) {
      const detail = err.response?.data?.detail;
      toast.error(detail || 'Failed to upload document. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  // Loading state
  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white flex items-center justify-center p-4">
        <Card className="max-w-md w-full">
          <CardContent className="py-12 text-center">
            <Loader2 className="h-12 w-12 animate-spin text-primary mx-auto mb-4" />
            <p className="text-slate-600">Validating your upload link...</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Error states
  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white flex items-center justify-center p-4">
        <Card className="max-w-md w-full">
          <CardContent className="py-12 text-center">
            {error.type === 'expired' ? (
              <Clock className="h-16 w-16 text-amber-500 mx-auto mb-4" />
            ) : error.type === 'already_done' ? (
              <CheckCircle className="h-16 w-16 text-green-500 mx-auto mb-4" />
            ) : (
              <XCircle className="h-16 w-16 text-red-500 mx-auto mb-4" />
            )}
            <h2 className="text-xl font-semibold mb-2">
              {error.type === 'expired' ? 'Link Expired' : 
               error.type === 'already_done' ? 'Already Uploaded' : 'Unable to Load'}
            </h2>
            <p className="text-slate-600 mb-6">{error.message}</p>
            <Link to="/">
              <Button variant="outline" className="gap-2">
                <Home className="h-4 w-4" />
                Return to Homepage
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Success state
  if (uploaded && uploadResult) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white flex items-center justify-center p-4">
        <Card className="max-w-lg w-full border-green-200 bg-green-50/50">
          <CardContent className="py-12 text-center">
            <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
              <CheckCircle className="h-12 w-12 text-green-600" />
            </div>
            <h2 className="text-2xl font-semibold text-green-800 mb-2">Upload Successful!</h2>
            <p className="text-green-700 mb-6">{uploadResult.message}</p>
            
            <div className="bg-white rounded-xl p-6 text-left mb-6 border border-green-200">
              <h3 className="font-medium text-slate-700 mb-3">What happens next?</h3>
              <ul className="space-y-2">
                {uploadResult.next_steps?.map((step, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-sm text-slate-600">
                    <CheckCircle className="h-4 w-4 text-green-500 mt-0.5 flex-shrink-0" />
                    {step}
                  </li>
                ))}
              </ul>
            </div>
            
            <p className="text-sm text-slate-500">
              You can close this page. You'll be contacted if we need anything else.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Upload form
  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white">
      {/* Header */}
      <div className="bg-white border-b border-slate-200 px-4 py-4">
        <div className="max-w-2xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-primary/10 rounded-xl flex items-center justify-center">
              <Shield className="h-5 w-5 text-primary" />
            </div>
            <div>
              <h1 className="font-semibold text-slate-800">Osabea Healthcare</h1>
              <p className="text-xs text-slate-500">Secure Document Upload</p>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-2xl mx-auto px-4 py-8">
        <Card className="shadow-lg border-slate-200">
          <CardHeader className="text-center pb-2">
            <div className="w-16 h-16 bg-primary/10 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <Upload className="h-8 w-8 text-primary" />
            </div>
            <CardTitle className="text-2xl">Upload {tokenData?.requirement_name}</CardTitle>
            <CardDescription className="text-base mt-2">
              Hello <span className="font-medium text-slate-700">{tokenData?.person_name}</span>! 
              Please upload your document below.
            </CardDescription>
          </CardHeader>
          
          <CardContent className="space-y-6">
            {/* RTW-SPECIFIC SHARE CODE GUIDANCE */}
            {(tokenData?.requirement_key === 'right_to_work' || tokenData?.requirement_name?.toLowerCase().includes('right to work')) && (
              <div className="bg-indigo-50 border border-indigo-200 rounded-xl p-4">
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 bg-indigo-100 rounded-lg flex items-center justify-center flex-shrink-0">
                    <Shield className="h-4 w-4 text-indigo-600" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-indigo-800">Recommended: Use Share Code</p>
                    <p className="text-xs text-indigo-700 mt-1">
                      If you have the right to work in the UK, the easiest way to prove this is using a <strong>Share Code</strong> from GOV.UK.
                    </p>
                    <ul className="text-xs text-indigo-700 mt-2 space-y-1 list-disc list-inside">
                      <li>Visit <a href="https://www.gov.uk/prove-right-to-work" target="_blank" rel="noopener noreferrer" className="underline font-medium">gov.uk/prove-right-to-work</a></li>
                      <li>Sign in and get your 9-character Share Code</li>
                      <li>Share this code with your employer</li>
                    </ul>
                    <p className="text-xs text-indigo-600 mt-2 italic">
                      If you're a UK or Irish citizen, uploading your passport is sufficient.
                    </p>
                  </div>
                </div>
              </div>
            )}
            
            {/* Instructions */}
            <div className="bg-blue-50 border border-blue-100 rounded-xl p-4">
              <p className="text-sm text-blue-800">
                <strong>Instructions:</strong> {tokenData?.instructions}
              </p>
              <p className="text-xs text-blue-600 mt-2">
                Maximum file size: {tokenData?.max_file_size_mb || 10}MB
              </p>
            </div>

            {/* Drop Zone */}
            <div
              className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors ${
                dragActive 
                  ? 'border-primary bg-primary/5' 
                  : selectedFile 
                    ? 'border-green-300 bg-green-50' 
                    : 'border-slate-200 hover:border-slate-300'
              }`}
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
            >
              {selectedFile ? (
                <div className="space-y-3">
                  <div className="w-14 h-14 bg-green-100 rounded-xl flex items-center justify-center mx-auto">
                    <File className="h-7 w-7 text-green-600" />
                  </div>
                  <div>
                    <p className="font-medium text-slate-800">{selectedFile.name}</p>
                    <p className="text-sm text-slate-500">{formatFileSize(selectedFile.size)}</p>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setSelectedFile(null)}
                    className="text-slate-600"
                  >
                    Choose Different File
                  </Button>
                </div>
              ) : (
                <div className="space-y-3">
                  <div className="w-14 h-14 bg-slate-100 rounded-xl flex items-center justify-center mx-auto">
                    <Upload className="h-7 w-7 text-slate-400" />
                  </div>
                  <div>
                    <p className="font-medium text-slate-700">
                      Drag and drop your file here
                    </p>
                    <p className="text-sm text-slate-500">or click to browse</p>
                  </div>
                  <input
                    type="file"
                    id="file-upload"
                    className="hidden"
                    accept={tokenData?.allowed_extensions?.join(',')}
                    onChange={(e) => handleFileSelect(e.target.files[0])}
                  />
                  <Button
                    variant="outline"
                    onClick={() => document.getElementById('file-upload').click()}
                    className="gap-2"
                  >
                    <FileText className="h-4 w-4" />
                    Browse Files
                  </Button>
                </div>
              )}
            </div>

            {/* Accepted Formats */}
            <div className="text-center">
              <p className="text-xs text-slate-500">
                Accepted formats: {tokenData?.allowed_extensions?.join(', ')}
              </p>
            </div>

            {/* Submit Button */}
            <Button
              onClick={handleUpload}
              disabled={!selectedFile || uploading}
              className="w-full h-12 text-base gap-2"
              data-testid="upload-document-submit"
            >
              {uploading ? (
                <>
                  <Loader2 className="h-5 w-5 animate-spin" />
                  Uploading...
                </>
              ) : (
                <>
                  <Upload className="h-5 w-5" />
                  Upload Document
                </>
              )}
            </Button>

            {/* Security Note */}
            <div className="flex items-start gap-3 p-4 bg-slate-50 rounded-xl text-sm text-slate-600">
              <Shield className="h-5 w-5 text-slate-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-medium text-slate-700">Secure Upload</p>
                <p>Your document is encrypted and transmitted securely. Only authorised personnel can view uploaded documents.</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Footer */}
        <div className="text-center mt-8 text-sm text-slate-500">
          <p>Need help? Contact us at <a href="mailto:recruitment@osabea.care" className="text-primary hover:underline">recruitment@osabea.care</a></p>
        </div>
      </div>
    </div>
  );
}
```
--- END DocumentUploadPage.js ---

---
## FILE: DualRowComplianceSection.js
## Lines: 935
```javascript
import { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Loader2, AlertTriangle, Shield, ChevronDown, ChevronUp, RefreshCw } from 'lucide-react';
import { toast } from 'sonner';

import EvidenceRow from './EvidenceRow';
import CheckRow from './CheckRow';
import AgreementRow from './AgreementRow';
import ReferenceRow from './ReferenceRow';
import FormRequirementRow from './FormRequirementRow';
import UploadRequirementCard from './UploadRequirementCard';
import EvidenceManageDrawer from './EvidenceManageDrawer';
import RequirementFilesDrawer from './RequirementFilesDrawer';
import RequirementHistoryDrawer from './RequirementHistoryDrawer';
import ReferenceResponseDrawer from './ReferenceResponseDrawer';
import AgreementFormDrawer from './AgreementFormDrawer';
import FormSubmissionDrawer from './FormSubmissionDrawer';
import ApplicationFormViewDrawer from './ApplicationFormViewDrawer';
import RejectFormDialog from './RejectFormDialog';
import { normalizeUploadRequirementSurface } from './surfaceNormalizers';
import { UPLOAD_REQUIREMENT_KEYS } from './complianceRequirementMap';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

/**
 * DualRowComplianceSection - Displays the dual-row compliance file structure
 * 
 * Renders paired evidence/check rows for each compliance area:
 * - Right to Work (Evidence + Check)
 * - DBS (Evidence + Check)
 * - Identity (Evidence + Verification)
 * - Proof of Address (Evidence + Verification)
 * - Agreements (Contract Acceptance, Handbook Acknowledgement)
 * 
 * The backend returns serializer_version: "dual_row_v1" with explicit row_type
 * and allowed_actions per row.
 */
export default function DualRowComplianceSection({
  employeeId,
  employeeEmail,
  employeeName,
  employeeData,  // Full employee data for pre-filling forms
  onUpload,
  onRequest,
  onPreviewFile,
  onExtractReview,
  onRecordCheck,
  isAuditor = false,
  onRefresh
}) {
  const [complianceFile, setComplianceFile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // STEP 11E: Centralized open state for all requirement sections
  const [expandedSections, setExpandedSections] = useState({
    right_to_work: true,
    dbs: true,
    identity: true,
    proof_of_address: true,
    agreements: true,
    references: true,
    training: false,
    recruitment_record: false,
    health_competency: false,
    admin_forms: false
  });
  
  // Form submission drawer state (for new form-type requirements)
  const [formDrawer, setFormDrawer] = useState({
    isOpen: false,
    formKey: null,
    formType: null,
    submissionId: null,
    mode: 'create' // 'create', 'view', 'edit'
  });
  
  // Phase D2: Files drawer state (for legacy rows)
  const [filesDrawer, setFilesDrawer] = useState({
    open: false,
    requirementKey: null,
    requirementTitle: ''
  });
  
  // Ticket C: Shared upload drawer state for RTW, DBS, Identity, PoA
  const [uploadDrawer, setUploadDrawer] = useState({
    isOpen: false,
    requirementKey: null
  });
  
  // Phase D3: History drawer state
  const [historyDrawer, setHistoryDrawer] = useState({
    open: false,
    requirementKey: null,
    requirementTitle: ''
  });
  
  // Ticket E: Reference response drawer state
  const [referenceDrawer, setReferenceDrawer] = useState({
    open: false,
    referenceNum: null
  });
  
  // Ticket D: Agreement form drawer state
  const [agreementDrawer, setAgreementDrawer] = useState({
    isOpen: false,
    templateId: null,
    mode: 'create', // 'create' or 'view'
    submissionId: null,
    agreementKey: null,
    agreementTitle: null
  });
  
  // Application Form viewer drawer state (separate from template-based forms)
  const [applicationFormDrawer, setApplicationFormDrawer] = useState({
    isOpen: false,
    submissionId: null
  });
  
  // Reject form dialog state
  const [rejectDialog, setRejectDialog] = useState({
    isOpen: false,
    submissionId: null,
    formName: '',
    formKey: null
  });
  const [rejectLoading, setRejectLoading] = useState(false);
  
  const { token } = useAuth();
  
  // Open upload drawer for upload-type requirements
  const openUploadDrawer = (requirementKey) => {
    setUploadDrawer({ isOpen: true, requirementKey });
  };
  
  const closeUploadDrawer = () => {
    setUploadDrawer({ isOpen: false, requirementKey: null });
  };
  
  // Open files drawer for a requirement (legacy)
  const handleViewFiles = (requirementKey, requirementTitle) => {
    setFilesDrawer({
      open: true,
      requirementKey,
      requirementTitle
    });
  };
  
  // Open history drawer for a requirement
  const handleViewHistory = (requirementKey, requirementTitle) => {
    setHistoryDrawer({
      open: true,
      requirementKey,
      requirementTitle
    });
  };

  // Fetch compliance file data
  const fetchComplianceFile = async () => {
    if (!employeeId) return;
    
    setLoading(true);
    setError(null);
    try {
      const response = await axios.get(`${API}/employees/${employeeId}/compliance-file`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      // Verify it's the dual-row format
      if (response.data.serializer_version !== 'dual_row_v1') {
        console.warn('Unexpected serializer version:', response.data.serializer_version);
      }
      
      setComplianceFile(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load compliance file');
      toast.error('Failed to load compliance file');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchComplianceFile();
  }, [employeeId, token]);

  // Refresh handler
  const handleRefresh = () => {
    fetchComplianceFile();
    if (onRefresh) onRefresh();
  };

  // Toggle section expansion
  const toggleSection = (sectionKey) => {
    setExpandedSections(prev => ({
      ...prev,
      [sectionKey]: !prev[sectionKey]
    }));
  };

  /**
   * Transform backend evidence/check rows into a normalized surface for UploadRequirementCard
   */
  const transformToUploadSurface = (sectionKey, section) => {
    if (!section || !section.rows) return null;
    
    const evidenceRow = section.rows.find(r => r.row_type === 'evidence');
    const checkRow = section.rows.find(r => r.row_type === 'check');
    
    if (!evidenceRow) return null;
    
    // Transform documents_preview to files array format
    const files = (evidenceRow.documents_preview || []).map(doc => ({
      file_id: doc.id,
      id: doc.id,
      file_name: doc.file_name,
      original_filename: doc.file_name,
      file_url: doc.file_url,
      uploaded_at: doc.uploaded_at,
      uploaded_by: doc.uploaded_by,
      verified: doc.verified || false,
      verified_by: doc.verified_by,
      verified_by_name: doc.verified_by_name,
      verified_at: doc.verified_at,
      status: doc.status || 'active',
      extraction_status: doc.extraction_status,
      // Verification stamp fields - CRITICAL for stamp UI
      verification_stamp: doc.verification_stamp,
      verification_stamp_label: doc.verification_stamp_label,
      verification_stamp_audit_text: doc.verification_stamp_audit_text,
      verification_stamp_badge_color: doc.verification_stamp_badge_color,
      verification_stamp_by_name: doc.verification_stamp_by_name,
      verification_stamp_at: doc.verification_stamp_at,
      // Rejection fields
      rejected_by: doc.rejected_by,
      rejected_by_name: doc.rejected_by_name,
      rejected_at: doc.rejected_at,
      rejection_reason: doc.rejection_reason
    }));
    
    // Add freshness data for PoA files
    if (sectionKey === 'proof_of_address' && checkRow?.freshness?.documents) {
      const freshnessMap = {};
      checkRow.freshness.documents.forEach(fd => {
        freshnessMap[fd.file_id] = fd;
      });
      
      files.forEach(file => {
        const fd = freshnessMap[file.file_id];
        if (fd) {
          file.freshness_status = fd.status;
          file.freshness_is_valid = fd.is_valid;
          file.freshness_reason = fd.reason;
          file.document_date = fd.document_date;
          file.months_old = fd.months_old;
        }
      });
    }
    
    // Add remaining files if has_more_documents indicates there are more
    // The counts tell us how many total active files
    const totalActive = evidenceRow.counts?.active_files || files.length;
    const totalHistorical = (evidenceRow.counts?.superseded || 0) + (evidenceRow.counts?.history || 0) - totalActive;
    
    // Transform request_lifecycle to requests array
    const requests = [];
    if (evidenceRow.request_lifecycle?.current_request) {
      const req = evidenceRow.request_lifecycle.current_request;
      requests.push({
        request_id: req.id,
        status: req.status,
        sent_at: req.sent_at,
        viewed_at: req.viewed_at,
        submitted_at: req.submitted_at,
        reminder_count: req.reminder_count || 0,
        is_replacement: req.is_replacement || false
      });
    }
    
    // Transform check row to checks array
    // Backend returns check_data in check rows, not check_record
    const checks = [];
    if (checkRow && (checkRow.check_data || checkRow.has_check)) {
      const check = checkRow.check_data || {};
      checks.push({
        id: check.id,
        status: check.outcome || (checkRow.is_verified ? 'verified' : 'pending'),
        outcome: check.outcome,
        method: check.method,
        checked_at: check.checked_at,
        checked_by: check.checked_by,
        checked_by_name: check.checked_by_name,
        notes: check.notes,
        follow_up_date: checkRow.follow_up_info?.date || check.follow_up_date,
        updated_at: check.updated_at,
        // COMPLIANCE-CRITICAL: Include verification proof document link
        evidence_document_id: check.evidence_document_id,
        evidence_document: check.evidence_document,
        // IDENTITY-SPECIFIC FIELDS
        document_type: check.document_type,
        full_name_on_document: check.full_name_on_document,
        date_of_birth: check.date_of_birth,
        document_number: check.document_number,
        issue_date: check.issue_date,
        expiry_date: check.expiry_date,
        nationality: check.nationality,
        name_matches_application: check.name_matches_application,
        dob_matches_application: check.dob_matches_application,
        photo_match_confirmed: check.photo_match_confirmed,
        identity_status: check.identity_status,
        // RTW-SPECIFIC FIELDS
        permission_type: check.permission_type,
        permission_start_date: check.permission_start_date,
        permission_end_date: check.permission_end_date,
        is_indefinite: check.is_indefinite,
        share_code: check.share_code,
        reference_number: check.reference_number,
        restrictions: check.restrictions,
        hours_limit: check.hours_limit,
        follow_up_required: check.follow_up_required,
        follow_up_due_at: check.follow_up_due_at,
        route: check.route,
        // DBS-SPECIFIC FIELDS
        dbs_level: check.dbs_level,
        certificate_number: check.certificate_number,
        certificate_issue_date: check.certificate_issue_date,
        name_on_certificate: check.name_on_certificate,
        workforce: check.workforce,
        update_service_registered: check.update_service_registered,
        update_service_status: check.update_service_status,
        last_status_check_date: check.last_status_check_date,
        update_service_check_result: check.update_service_check_result,
        result_status: check.result_status,
        information_present: check.information_present,
        result_summary: check.result_summary,
        recheck_required: check.recheck_required,
        next_recheck_date: check.next_recheck_date,
        dbs_status: check.dbs_status,
        // POA-SPECIFIC FIELDS (from address_verification row)
        documents_received_count: check.documents_received_count,
        documents_required_count: check.documents_required_count,
        verified_documents: check.verified_documents,
        extracted_address_line1: check.extracted_address_line1,
        extracted_address_line2: check.extracted_address_line2,
        extracted_city: check.extracted_city,
        extracted_postcode: check.extracted_postcode,
        address_matches_application: check.address_matches_application,
        all_documents_sufficiently_recent: check.all_documents_sufficiently_recent,
        address_status: check.address_status
      });
    }
    
    // Use the normalizer with transformed data
    return normalizeUploadRequirementSurface({
      requirementKey: sectionKey,
      files,
      requests,
      checks,
      freshness: sectionKey === 'proof_of_address' && checkRow ? checkRow.freshness : null
    });
  };

  /**
   * Render upload-type requirement using UploadRequirementCard
   * DUAL-ROW MODEL: Each card shows Evidence row + Verification row
   */
  const renderUploadSection = (sectionKey, section) => {
    const surface = transformToUploadSurface(sectionKey, section);
    if (!surface) return null;
    
    const isExpanded = expandedSections[sectionKey] !== false;
    
    // Get RTW status for Right to Work section
    const rtwStatus = sectionKey === 'right_to_work' ? section.rtw_status : null;
    
    return (
      <div key={sectionKey} className="mb-6" data-testid={`section-${sectionKey}`}>
        <UploadRequirementCard
          surface={surface}
          isOpen={isExpanded}
          onToggle={() => toggleSection(sectionKey)}
          onOpenDrawer={() => openUploadDrawer(sectionKey)}
          onUpload={() => onUpload && onUpload(`${sectionKey}_evidence`)}
          onRequest={() => onRequest && onRequest(`${sectionKey}_evidence`, section.title)}
          onResend={() => onRequest && onRequest(`${sectionKey}_evidence`, section.title)}
          onRecordCheck={() => onRecordCheck && onRecordCheck(sectionKey)}
          onUpdateCheck={() => onRecordCheck && onRecordCheck(sectionKey)}
          onViewHistory={() => handleViewHistory(sectionKey, section.title)}
          onPreviewFile={onPreviewFile}
          employeeId={employeeId}
          onRefresh={handleRefresh}
          isAuditor={isAuditor}
          rtwStatus={rtwStatus}
        />
      </div>
    );
  };

  // Render a legacy section with paired rows (for agreements and references)
  const renderSection = (sectionKey, section) => {
    if (!section || !section.rows) return null;
    
    const isExpanded = expandedSections[sectionKey] !== false;
    
    // Count blockers in this section
    const blockers = section.rows.filter(r => r.blocker_text);
    
    return (
      <div key={sectionKey} className="mb-6" data-testid={`section-${sectionKey}`}>
        {/* Section Header */}
        <div 
          className="flex items-center justify-between p-3 bg-gray-50 rounded-t-xl cursor-pointer hover:bg-gray-100 transition-colors"
          onClick={() => toggleSection(sectionKey)}
        >
          <div className="flex items-center gap-3">
            <h3 className="font-heading font-semibold text-text-primary">{section.title}</h3>
            {blockers.length > 0 && (
              <Badge className="bg-red-100 text-red-700 text-xs">
                {blockers.length} blocking
              </Badge>
            )}
          </div>
          <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
            {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </Button>
        </div>
        
        {/* Section Content */}
        {isExpanded && (
          <div className="space-y-3 p-3 bg-white border border-t-0 border-gray-200 rounded-b-xl">
            {section.rows.map((row, idx) => {
              // CV row is evidence type but should use FormRequirementRow for file display
              if (row.row_type === 'evidence' && row.key !== 'cv') {
                return (
                  <EvidenceRow
                    key={row.key || idx}
                    row={row}
                    employeeId={employeeId}
                    employeeEmail={employeeEmail}
                    onRefresh={handleRefresh}
                    onUpload={onUpload}
                    onRequest={onRequest}
                    onPreviewFile={onPreviewFile}
                    onExtractReview={onExtractReview}
                    onViewFiles={handleViewFiles}
                    onViewHistory={handleViewHistory}
                    isAuditor={isAuditor}
                  />
                );
              }
              
              if (row.row_type === 'check') {
                return (
                  <CheckRow
                    key={row.key || idx}
                    row={row}
                    employeeId={employeeId}
                    onRefresh={handleRefresh}
                    onRecordCheck={onRecordCheck}
                    onViewHistory={handleViewHistory}
                    onPreviewFile={onPreviewFile}
                    isAuditor={isAuditor}
                  />
                );
              }
              
              if (row.row_type === 'form_acknowledgement') {
                return (
                  <AgreementRow
                    key={row.key || idx}
                    row={row}
                    employeeId={employeeId}
                    employeeEmail={employeeEmail}
                    employeeData={employeeData}
                    onRefresh={handleRefresh}
                    onOpenForm={(agreementKey, title, templateId, mode) => {
                      setAgreementDrawer({
                        isOpen: true,
                        templateId,
                        mode: 'create',
                        submissionId: null,
                        agreementKey,
                        agreementTitle: title
                      });
                    }}
                    onViewSubmission={(agreementKey, title, templateId, submissionId) => {
                      setAgreementDrawer({
                        isOpen: true,
                        templateId,
                        mode: 'view',
                        submissionId,
                        agreementKey,
                        agreementTitle: title
                      });
                    }}
                    onViewHistory={handleViewHistory}
                    isAuditor={isAuditor}
                  />
                );
              }
              
              if (row.row_type === 'reference') {
                return (
                  <ReferenceRow
                    key={row.key || idx}
                    row={row}
                    employeeId={employeeId}
                    onRefresh={handleRefresh}
                    onViewHistory={handleViewHistory}
                    onViewResponse={(refNum) => {
                      // Open reference response drawer
                      setReferenceDrawer({ open: true, referenceNum: refNum });
                    }}
                    onVerify={async (refNum) => {
                      try {
                        // Simple verification - assumes from_cv=true
                        // A more complete implementation would open a dialog asking about CV match
                        await axios.post(
                          `${API}/employees/${employeeId}/verify-reference`,
                          { 
                            reference_num: refNum,
                            from_cv: true
                          },
                          { headers: { Authorization: `Bearer ${token}` } }
                        );
                        toast.success(`Reference ${refNum} verified`);
                        handleRefresh();
                      } catch (err) {
                        toast.error(err.response?.data?.detail || 'Failed to verify reference');
                      }
                    }}
                    onReject={async (refNum) => {
                      try {
                        await axios.post(
                          `${API}/references/${employeeId}/${refNum}/reject`,
                          { rejection_reason: 'Rejected by admin' },
                          { headers: { Authorization: `Bearer ${token}` } }
                        );
                        toast.success(`Reference ${refNum} rejected`);
                        handleRefresh();
                      } catch (err) {
                        toast.error(err.response?.data?.detail || 'Failed to reject reference');
                      }
                    }}
                    isAuditor={isAuditor}
                  />
                );
              }
              
              // Form-type requirement rows
              if (row.row_type === 'form' || row.row_type === 'evidence' && row.key === 'cv') {
                return (
                  <FormRequirementRow
                    key={row.key || idx}
                    row={row}
                    employeeId={employeeId}
                    employeeEmail={employeeEmail}
                    employeeName={employeeName}
                    onRefresh={handleRefresh}
                    onOpenForm={(formKey, formType, submissionId) => {
                      setFormDrawer({
                        isOpen: true,
                        formKey,
                        formType,
                        submissionId,
                        mode: submissionId ? 'edit' : 'create'
                      });
                    }}
                    onViewSubmission={(formKey, formType, submissionId) => {
                      // SPECIAL CASE: Application forms use a dedicated viewer
                      // because they don't have a template in FORM_BASED_REQUIREMENTS
                      if (formKey === 'application_form') {
                        setApplicationFormDrawer({
                          isOpen: true,
                          submissionId
                        });
                      } else {
                        setFormDrawer({
                          isOpen: true,
                          formKey,
                          formType,
                          submissionId,
                          mode: 'view'
                        });
                      }
                    }}
                    onSendForm={async (formKey, empId, empEmail) => {
                      try {
                        await axios.post(
                          `${API}/employees/${empId}/send-form?form_type=${formKey}`,
                          {},
                          { headers: { Authorization: `Bearer ${token}` } }
                        );
                        toast.success(`Form sent to ${empEmail}`);
                        handleRefresh();
                      } catch (err) {
                        toast.error(err.response?.data?.detail || 'Failed to send form');
                      }
                    }}
                    onExportPdf={async (formKey, formType, submissionId) => {
                      try {
                        const response = await axios.get(
                          `${API}/form-submissions/${submissionId}/download-pdf`,
                          { 
                            headers: { Authorization: `Bearer ${token}` },
                            responseType: 'blob'
                          }
                        );
                        const url = window.URL.createObjectURL(new Blob([response.data]));
                        const link = document.createElement('a');
                        link.href = url;
                        link.download = `${formKey}_${submissionId}.pdf`;
                        link.click();
                        window.URL.revokeObjectURL(url);
                      } catch (err) {
                        toast.error('Failed to download PDF');
                      }
                    }}
                    onVerify={async (submissionId) => {
                      try {
                        await axios.post(
                          `${API}/form-submissions/${submissionId}/verify`,
                          {},
                          { headers: { Authorization: `Bearer ${token}` } }
                        );
                        toast.success('Form verified successfully');
                        handleRefresh();
                      } catch (err) {
                        toast.error(err.response?.data?.detail || 'Failed to verify form');
                      }
                    }}
                    onReject={(submissionId, formName) => {
                      setRejectDialog({
                        isOpen: true,
                        submissionId,
                        formName: formName || row.title,
                        formKey: row.key
                      });
                    }}
                    onViewHistory={(reqKey, title) => handleViewHistory(reqKey, title)}
                    onPreviewFile={onPreviewFile}
                    onUpload={(reqKey) => onUpload && onUpload(`${reqKey}_evidence`)}
                    isAuditor={isAuditor}
                  />
                );
              }
              
              return null;
            })}
          </div>
        )}
      </div>
    );
  };

  // Loading state
  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="ml-3 text-text-muted">Loading compliance file...</span>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="text-center py-12">
        <AlertTriangle className="h-12 w-12 mx-auto text-red-400 mb-4" />
        <p className="text-text-muted mb-4">{error}</p>
        <Button variant="outline" onClick={handleRefresh}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Retry
        </Button>
      </div>
    );
  }

  if (!complianceFile) {
    return null;
  }

  const { summary, sections } = complianceFile;

  return (
    <div className="space-y-6" data-testid="dual-row-compliance-section">
      {/* Summary Panel */}
      {summary && summary.blocking_requirements > 0 && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center flex-shrink-0">
              <AlertTriangle className="h-5 w-5 text-red-600" />
            </div>
            <div className="flex-1">
              <h4 className="font-semibold text-red-900">
                {summary.blocking_requirements} Blocking Requirement{summary.blocking_requirements !== 1 ? 's' : ''}
              </h4>
              <p className="text-sm text-red-700 mb-2">
                These items must be resolved before work readiness can be achieved.
              </p>
              {summary.blocking_items && summary.blocking_items.length > 0 && (
                <ul className="space-y-1">
                  {summary.blocking_items.map((item, idx) => (
                    <li key={idx} className="text-sm text-red-800 flex items-center gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-red-400" />
                      {item.message}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Refresh Button */}
      <div className="flex justify-end">
        <Button 
          variant="ghost" 
          size="sm" 
          onClick={handleRefresh}
          className="text-text-muted"
        >
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Compliance Sections */}
      {sections && (
        <>
          {/* Right to Work - Uses unified UploadRequirementCard */}
          {sections.right_to_work && renderUploadSection('right_to_work', sections.right_to_work)}
          
          {/* DBS - Uses unified UploadRequirementCard */}
          {sections.dbs && renderUploadSection('dbs', sections.dbs)}
          
          {/* Identity - Uses unified UploadRequirementCard */}
          {sections.identity && renderUploadSection('identity', sections.identity)}
          
          {/* Proof of Address - Uses unified UploadRequirementCard */}
          {sections.proof_of_address && renderUploadSection('proof_of_address', sections.proof_of_address)}
          
          {/* Agreements - Uses legacy section for now */}
          {sections.agreements && renderSection('agreements', sections.agreements)}
          
          {/* References - Uses legacy section for now */}
          {sections.references && sections.references.rows && renderSection('references', sections.references)}
          
          {/* Training */}
          {sections.training && renderSection('training', sections.training)}
          
          {/* Recruitment Record - Form-type requirements */}
          {sections.recruitment_record && sections.recruitment_record.rows && renderSection('recruitment_record', sections.recruitment_record)}
          
          {/* Health & Competency - Form-type requirements */}
          {sections.health_competency && sections.health_competency.rows && renderSection('health_competency', sections.health_competency)}
          
          {/* Admin Forms - Form-type requirements */}
          {sections.admin_forms && sections.admin_forms.rows && renderSection('admin_forms', sections.admin_forms)}
        </>
      )}
      
      {/* Serializer Version (for debugging) */}
      <div className="text-xs text-text-muted text-right">
        Serializer: {complianceFile.serializer_version}
      </div>
      
      {/* Ticket C: Evidence Management Drawer for RTW, DBS, Identity, PoA */}
      <EvidenceManageDrawer
        isOpen={uploadDrawer.isOpen}
        onClose={closeUploadDrawer}
        employeeId={employeeId}
        requirementKey={uploadDrawer.requirementKey}
        onUploadFile={(key) => onUpload && onUpload(`${key}_evidence`)}
        onSendRequest={(key) => onRequest && onRequest(`${key}_evidence`, UPLOAD_REQUIREMENT_KEYS.includes(key) ? key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()) : key)}
        onPreviewFile={onPreviewFile}
        onExtractReview={onExtractReview}
        onRefresh={handleRefresh}
        isAuditor={isAuditor}
      />
      
      {/* Phase D2: Files Drawer (for legacy rows) */}
      <RequirementFilesDrawer
        open={filesDrawer.open}
        onClose={() => setFilesDrawer({ open: false, requirementKey: null, requirementTitle: '' })}
        employeeId={employeeId}
        requirementKey={filesDrawer.requirementKey}
        requirementTitle={filesDrawer.requirementTitle}
        onRefresh={handleRefresh}
        onUpload={onUpload}
        onRequest={onRequest}
        onPreviewFile={onPreviewFile}
        onExtractReview={onExtractReview}
        isAuditor={isAuditor}
      />
      
      {/* Phase D3: History Drawer */}
      <RequirementHistoryDrawer
        open={historyDrawer.open}
        onClose={() => setHistoryDrawer({ open: false, requirementKey: null, requirementTitle: '' })}
        employeeId={employeeId}
        requirementKey={historyDrawer.requirementKey}
        requirementTitle={historyDrawer.requirementTitle}
      />
      
      {/* Ticket E: Reference Response Drawer */}
      <ReferenceResponseDrawer
        isOpen={referenceDrawer.open}
        onClose={() => setReferenceDrawer({ open: false, referenceNum: null })}
        employeeId={employeeId}
        referenceNum={referenceDrawer.referenceNum}
        onRefresh={handleRefresh}
        isAuditor={isAuditor}
      />
      
      {/* Ticket D: Agreement Form Drawer */}
      <AgreementFormDrawer
        isOpen={agreementDrawer.isOpen}
        onClose={() => setAgreementDrawer({ 
          isOpen: false, templateId: null, mode: 'create', 
          submissionId: null, agreementKey: null, agreementTitle: null 
        })}
        employeeId={employeeId}
        templateId={agreementDrawer.templateId}
        employeeData={employeeData}
        onSubmitSuccess={handleRefresh}
        mode={agreementDrawer.mode}
        existingSubmission={agreementDrawer.submissionId ? { id: agreementDrawer.submissionId } : null}
      />
      
      {/* Form Submission Drawer for form-type requirements */}
      <FormSubmissionDrawer
        isOpen={formDrawer.isOpen}
        onClose={() => setFormDrawer({
          isOpen: false, formKey: null, formType: null,
          submissionId: null, mode: 'create'
        })}
        employeeId={employeeId}
        employeeName={employeeName}
        formKey={formDrawer.formKey}
        formType={formDrawer.formType}
        submissionId={formDrawer.submissionId}
        mode={formDrawer.mode}
        onSubmitSuccess={handleRefresh}
        onVerify={async (submissionId) => {
          try {
            await axios.post(
              `${API}/form-submissions/${submissionId}/verify`,
              {},
              { headers: { Authorization: `Bearer ${token}` } }
            );
            toast.success('Form verified successfully');
            handleRefresh();
            setFormDrawer(prev => ({ ...prev, isOpen: false }));
          } catch (err) {
            toast.error(err.response?.data?.detail || 'Failed to verify form');
          }
        }}
        onReject={(submissionId) => {
          setRejectDialog({
            isOpen: true,
            submissionId,
            formName: formDrawer.formKey?.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
            formKey: formDrawer.formKey
          });
        }}
      />
      
      {/* Application Form View Drawer - Special case for structured application submissions */}
      <ApplicationFormViewDrawer
        isOpen={applicationFormDrawer.isOpen}
        onClose={() => setApplicationFormDrawer({ isOpen: false, submissionId: null })}
        employeeId={employeeId}
        employeeName={employeeName}
        submissionId={applicationFormDrawer.submissionId}
        onVerify={async (submissionId) => {
          try {
            await axios.post(
              `${API}/form-submissions/${submissionId}/verify`,
              {},
              { headers: { Authorization: `Bearer ${token}` } }
            );
            toast.success('Application form verified successfully');
            handleRefresh();
            setApplicationFormDrawer({ isOpen: false, submissionId: null });
          } catch (err) {
            toast.error(err.response?.data?.detail || 'Failed to verify application');
          }
        }}
        onReject={(submissionId) => {
          setRejectDialog({
            isOpen: true,
            submissionId,
            formName: 'Application Form',
            formKey: 'application_form'
          });
          setApplicationFormDrawer({ isOpen: false, submissionId: null });
        }}
        onRefresh={handleRefresh}
      />
      
      {/* Reject Form Dialog */}
      <RejectFormDialog
        isOpen={rejectDialog.isOpen}
        onClose={() => setRejectDialog({ isOpen: false, submissionId: null, formName: '', formKey: null })}
        formName={rejectDialog.formName}
        loading={rejectLoading}
        onConfirm={async (reason) => {
          setRejectLoading(true);
          try {
            await axios.post(
              `${API}/form-submissions/${rejectDialog.submissionId}/reject`,
              { rejection_reason: reason },
              { headers: { Authorization: `Bearer ${token}` } }
            );
            toast.success('Form rejected');
            handleRefresh();
            setRejectDialog({ isOpen: false, submissionId: null, formName: '', formKey: null });
            setFormDrawer(prev => ({ ...prev, isOpen: false }));
          } catch (err) {
            toast.error(err.response?.data?.detail || 'Failed to reject form');
          } finally {
            setRejectLoading(false);
          }
        }}
      />
    </div>
  );
}
```
--- END DualRowComplianceSection.js ---

---
## FILE: EmployeeProfilePage.js
## Lines: 6925
```javascript
import { useState, useEffect, useRef } from 'react';
import { useParams, Link, useNavigate, useSearchParams, useLocation } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs';
import { Progress } from '../../components/ui/progress';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter, DialogDescription } from '../../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from '../../components/ui/dropdown-menu';
import { Label } from '../../components/ui/label';
import { Input } from '../../components/ui/input';
import { Checkbox } from '../../components/ui/checkbox';
import { Textarea } from '../../components/ui/textarea';
import { toast } from 'sonner';
import ComplianceOverview from '../../components/portal/ComplianceOverview';
import DocumentPreviewModal from '../../components/portal/DocumentPreviewModal';
import RecurringComplianceSection from '../../components/portal/RecurringComplianceSection';
import DocumentExtractionReview from '../../components/documents/DocumentExtractionReview';
import TrainingIntakeWizard from '../../components/training/TrainingIntakeWizard';
import TrainingRequestDialog from '../../components/training/TrainingRequestDialog';
import AuditReadyTrainingMatrix from '../../components/training/AuditReadyTrainingMatrix';
import { DualRowComplianceSection, RecordCheckDialog, WhatsNeededPanel, TrainingSummaryCard, ApplicantStageBanner, ReferencesPanel, AuditTrailPanel, DocumentRequestsPanel, InterviewFormPanel } from '../../components/compliance';
import RecruitmentApprovalPanel from '../../components/compliance/RecruitmentApprovalPanel';
import WorkReadinessPanel from '../../components/compliance/WorkReadinessPanel';
import EmploymentGapPanel from '../../components/compliance/EmploymentGapPanel';
import {
  ArrowLeft, Upload, FileText, Mail, Phone, Calendar,
  CheckCircle, Clock, AlertTriangle, XCircle, Loader2, FileCheck,
  GraduationCap, ClipboardList, History, User, FolderUp, Eye, Shield,
  MoreHorizontal, MoreVertical, Edit, Archive, Trash2, RotateCcw, FileDown, Save,
  Download, RefreshCw, FileArchive, FileSpreadsheet, Printer, FileSearch,
  Camera, Replace, FileX, ClipboardCheck, FormInput, ChevronRight,
  Briefcase, UserCheck, FileWarning, CalendarClock, Send
} from 'lucide-react';
import { FileUploaderInline } from '../../components/ui/file-uploader';
import { formatBackendDate, formatBackendDateTime, parseBackendDate } from '../../lib/dateUtils';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Form-based requirements (open modal instead of file upload)
const FORM_BASED_REQUIREMENTS = [
  // 'health_screening' - ARCHIVED: replaced by staff_health_questionnaire
  'induction', 
  'interview_record', 
  'recruitment_checklist', 
  'equal_opportunities',
  'hmrc_starter_checklist',
  'staff_personal_info',
  'staff_health_questionnaire'
];

const statusIcons = {
  not_started: Clock,
  requested: Mail,
  uploaded: Upload,
  under_review: Clock,
  approved: CheckCircle,
  rejected: XCircle,
  expired: AlertTriangle,
  not_applicable: XCircle
};

const statusColors = {
  not_started: 'status-neutral',
  requested: 'status-info',
  uploaded: 'status-info',
  under_review: 'status-warning',
  approved: 'status-success',
  rejected: 'status-error',
  expired: 'status-error',
  not_applicable: 'status-neutral'
};

export default function EmployeeProfilePage() {
  const { employeeId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  
  // Route context detection - determines if viewing from recruitment or employee context
  const isRecruitmentView = location.pathname.startsWith('/portal/recruitment/');
  
  // Initialize active tab from URL for navigation state persistence
  const [activeTab, setActiveTab] = useState(searchParams.get('tab') || 'overview');
  const [employee, setEmployee] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [documentTypes, setDocumentTypes] = useState([]);
  const [policies, setPolicies] = useState([]);
  const [training, setTraining] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [generatedForms, setGeneratedForms] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [compliance, setCompliance] = useState(null);
  const [complianceFile, setComplianceFile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [bulkUploadOpen, setBulkUploadOpen] = useState(false);
  const [generateFormsOpen, setGenerateFormsOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [archiveDialogOpen, setArchiveDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [isRefreshingStatus, setIsRefreshingStatus] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [selectedDocType, setSelectedDocType] = useState('');
  const [uploadFile, setUploadFile] = useState(null);
  const [bulkFiles, setBulkFiles] = useState([]);
  const [bulkDocTypes, setBulkDocTypes] = useState({});
  const [selectedTemplates, setSelectedTemplates] = useState([]);
  const [isUploading, setIsUploading] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [importAppOpen, setImportAppOpen] = useState(false);
  const [importAppFile, setImportAppFile] = useState(null);
  const [importCvFile, setImportCvFile] = useState(null);
  const [isImporting, setIsImporting] = useState(false);
  const [complianceRequirements, setComplianceRequirements] = useState(null);
  const [selectedRequirement, setSelectedRequirement] = useState('');
  const [documentLabel, setDocumentLabel] = useState('');
  // Import document dialog states
  const [importDocOpen, setImportDocOpen] = useState(false);
  const [importDocType, setImportDocType] = useState('');
  const [importDocFile, setImportDocFile] = useState(null);
  const [importDocNotes, setImportDocNotes] = useState('');
  
  // Training completion dialog states
  const [trainingDialogOpen, setTrainingDialogOpen] = useState(false);
  const [selectedTrainingReq, setSelectedTrainingReq] = useState(null);
  const [trainingExpiryDate, setTrainingExpiryDate] = useState('');
  const [isCompletingTraining, setIsCompletingTraining] = useState(false);
  
  // Training certificate upload states
  const [trainingCertDialogOpen, setTrainingCertDialogOpen] = useState(false);
  const [trainingCertFile, setTrainingCertFile] = useState(null);
  const [isUploadingCert, setIsUploadingCert] = useState(false);
  const [isVerifyingTraining, setIsVerifyingTraining] = useState(false);
  
  // Training correction/history dialog states
  const [trainingCorrectionDialogOpen, setTrainingCorrectionDialogOpen] = useState(false);
  const [editingTrainingRecord, setEditingTrainingRecord] = useState(null);
  const [trainingCorrectionField, setTrainingCorrectionField] = useState('expiry_date');
  const [trainingCorrectionValue, setTrainingCorrectionValue] = useState('');
  const [trainingCorrectionReason, setTrainingCorrectionReason] = useState('');
  
  // Recruitment Checks states (Reference Integrity, CV Gaps, Proof of Address)
  const [recruitmentStatus, setRecruitmentStatus] = useState(null);
  const [loadingRecruitment, setLoadingRecruitment] = useState(false);
  const [verifyRefDialogOpen, setVerifyRefDialogOpen] = useState(false);
  const [selectedRefNum, setSelectedRefNum] = useState(null);
  const [refFromCv, setRefFromCv] = useState(true);
  const [refOverrideReason, setRefOverrideReason] = useState('');
  const [isVerifyingRef, setIsVerifyingRef] = useState(false);
  const [explainGapDialogOpen, setExplainGapDialogOpen] = useState(false);
  const [selectedGap, setSelectedGap] = useState(null);
  const [gapExplanation, setGapExplanation] = useState('');
  const [isExplainingGap, setIsExplainingGap] = useState(false);
  const [trainingHistoryDialogOpen, setTrainingHistoryDialogOpen] = useState(false);
  const [trainingHistory, setTrainingHistory] = useState([]);
  
  // Delete training record states
  const [deleteTrainingDialogOpen, setDeleteTrainingDialogOpen] = useState(false);
  const [deletingTrainingRecord, setDeletingTrainingRecord] = useState(null);
  const [deleteTrainingReason, setDeleteTrainingReason] = useState('');
  const [isDeletingTraining, setIsDeletingTraining] = useState(false);
  
  // Training evaluation state (canonical evaluator result)
  const [trainingEvaluation, setTrainingEvaluation] = useState(null);
  const [loadingTrainingEvaluation, setLoadingTrainingEvaluation] = useState(false);
  
  // Acknowledgement states (for Contract/Handbook acknowledgement flow)
  const [acknowledgementDialogOpen, setAcknowledgementDialogOpen] = useState(false);
  const [acknowledgingRequirement, setAcknowledgingRequirement] = useState(null);
  const [isAcknowledging, setIsAcknowledging] = useState(false);
  const [acknowledgementConfirmed, setAcknowledgementConfirmed] = useState(false);
  
  // Profile photo upload state
  const [isUploadingPhoto, setIsUploadingPhoto] = useState(false);
  const [profilePhotoBlob, setProfilePhotoBlob] = useState(null);
  const photoInputRef = useRef(null);
  
  // Evidence edit state
  const [editEvidenceOpen, setEditEvidenceOpen] = useState(false);
  const [editEvidenceData, setEditEvidenceData] = useState(null);
  const [editHistory, setEditHistory] = useState([]);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [isEditingEvidence, setIsEditingEvidence] = useState(false);
  const [editForm, setEditForm] = useState({
    issue_date: '',
    expiry_date: '',
    notes: '',
    file_label: '',
    reason: ''
  });
  
  // File management state
  const [removeDialogOpen, setRemoveDialogOpen] = useState(false);
  const [replaceDialogOpen, setReplaceDialogOpen] = useState(false);
  const [requirementHistoryOpen, setRequirementHistoryOpen] = useState(false);
  const [selectedFileForAction, setSelectedFileForAction] = useState(null);
  const [selectedRequirementForAction, setSelectedRequirementForAction] = useState(null);
  const [removeReason, setRemoveReason] = useState('');
  const [replaceReason, setReplaceReason] = useState('');
  const [replaceFile, setReplaceFile] = useState(null);
  const [isRemoving, setIsRemoving] = useState(false);
  const [isReplacing, setIsReplacing] = useState(false);
  const [requirementHistory, setRequirementHistory] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  
  // Form submission modal state (for structured forms)
  const [formModalOpen, setFormModalOpen] = useState(false);
  const [formTemplate, setFormTemplate] = useState(null);
  const [formData, setFormData] = useState({});
  const [isSubmittingForm, setIsSubmittingForm] = useState(false);
  const [viewFormOpen, setViewFormOpen] = useState(false);
  const [viewFormData, setViewFormData] = useState(null);
  
  // Document request modal state
  const [requestDocDialogOpen, setRequestDocDialogOpen] = useState(false);
  const [requestingRequirement, setRequestingRequirement] = useState(null);
  const [requestDocMessage, setRequestDocMessage] = useState('');
  const [isRequestingDoc, setIsRequestingDoc] = useState(false);
  
  // Send Form state
  const [sendFormDialogOpen, setSendFormDialogOpen] = useState(false);
  const [selectedFormType, setSelectedFormType] = useState('');
  const [sendFormMessage, setSendFormMessage] = useState('');
  const [isSendingForm, setIsSendingForm] = useState(false);
  
  // Reference Request state (NHS-Level Workflow)
  const [referenceStatus, setReferenceStatus] = useState(null);
  const [loadingReferenceStatus, setLoadingReferenceStatus] = useState(false);
  const [requestReferenceDialogOpen, setRequestReferenceDialogOpen] = useState(false);
  const [selectedRefForRequest, setSelectedRefForRequest] = useState(null);
  const [referenceRequestMessage, setReferenceRequestMessage] = useState('');
  const [isRequestingReference, setIsRequestingReference] = useState(false);
  const [reviewReferenceDialogOpen, setReviewReferenceDialogOpen] = useState(false);
  const [selectedRefForReview, setSelectedRefForReview] = useState(null);
  const [reviewMismatchNotes, setReviewMismatchNotes] = useState('');
  const [isReviewingReference, setIsReviewingReference] = useState(false);
  const [isVerifyingReferenceStrict, setIsVerifyingReferenceStrict] = useState(false);
  
  // Profile extraction from application form state
  const [extractionDialogOpen, setExtractionDialogOpen] = useState(false);
  const [extractionResult, setExtractionResult] = useState(null);
  const [extractionFailed, setExtractionFailed] = useState(null); // For graceful failure handling
  const [isExtracting, setIsExtracting] = useState(false);
  const [fieldsToApply, setFieldsToApply] = useState({});
  const [isApplyingExtraction, setIsApplyingExtraction] = useState(false);
  
  // Employment History Mismatch State (CV vs Structured)
  const [employmentMismatch, setEmploymentMismatch] = useState(null);
  const [loadingMismatch, setLoadingMismatch] = useState(false);
  const [mismatchDialogOpen, setMismatchDialogOpen] = useState(false);
  const [mismatchReviewNote, setMismatchReviewNote] = useState('');
  const [isSubmittingMismatchNote, setIsSubmittingMismatchNote] = useState(false);
  const [isReextractingFromCv, setIsReextractingFromCv] = useState(false);
  
  // Document Correction State (Step 8)
  const [docCorrectionDialogOpen, setDocCorrectionDialogOpen] = useState(false);
  const [docCorrectionType, setDocCorrectionType] = useState(null); // 'uploaded_in_error' | 'supersede' | 'move_category' | 'reopen_review'
  const [docCorrectionTarget, setDocCorrectionTarget] = useState(null);
  const [docCorrectionReason, setDocCorrectionReason] = useState('');
  const [docCorrectionNewCategory, setDocCorrectionNewCategory] = useState('');
  const [isSubmittingDocCorrection, setIsSubmittingDocCorrection] = useState(false);
  
  // Document Extraction Review State (Phase 2 - DBS, RTW, ID)
  const [docExtractionReviewOpen, setDocExtractionReviewOpen] = useState(false);
  const [docExtractionDocumentId, setDocExtractionDocumentId] = useState(null);
  const [docExtractionDocumentName, setDocExtractionDocumentName] = useState('');
  const [docExtractionContext, setDocExtractionContext] = useState(null); // Full context for modal header
  
  const { token, isAuditor, isAdmin, user } = useAuth();
  
  // Document preview modal state
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewFile, setPreviewFile] = useState(null);
  const [previewFiles, setPreviewFiles] = useState([]); // For multi-file navigation
  
  // Name Mismatch State (Phase 4 - Cross-Document Intelligence)
  const [nameMismatch, setNameMismatch] = useState(null);
  const [loadingNameMismatch, setLoadingNameMismatch] = useState(false);
  const [nameMismatchExpanded, setNameMismatchExpanded] = useState(false);
  
  // Training Intake Wizard State (Step 10)
  const [trainingIntakeOpen, setTrainingIntakeOpen] = useState(false);
  const [trainingRequestOpen, setTrainingRequestOpen] = useState(false);
  const [proposedTrainingItems, setProposedTrainingItems] = useState([]);
  const [loadingProposedItems, setLoadingProposedItems] = useState(false);
  
  // Dual-Row Compliance Model State (Step 11)
  const [recordCheckDialogOpen, setRecordCheckDialogOpen] = useState(false);
  const [recordCheckType, setRecordCheckType] = useState(null);
  
  // Refs for scrolling to compliance sections
  const complianceSectionRef = useRef(null);
  const trainingSectionRef = useRef(null);
  
  // Helper: Map blocker text to section ID and tab
  const mapBlockerToSection = (blockerText) => {
    const text = blockerText.toLowerCase();
    if (text.includes('right to work') || text.includes('rtw')) {
      return { sectionId: 'section-right_to_work', tab: 'checklist' };
    }
    if (text.includes('dbs') || text.includes('disclosure')) {
      return { sectionId: 'section-dbs', tab: 'checklist' };
    }
    if (text.includes('identity') || text.includes('photo id') || text.includes('passport')) {
      return { sectionId: 'section-identity', tab: 'checklist' };
    }
    if (text.includes('address') || text.includes('proof of address') || text.includes('poa')) {
      return { sectionId: 'section-proof_of_address', tab: 'checklist' };
    }
    if (text.includes('training') || text.includes('certificate') || text.includes('qualification')) {
      return { sectionId: null, tab: 'training' };
    }
    if (text.includes('reference')) {
      return { sectionId: 'section-references', tab: 'checklist' };
    }
    if (text.includes('application') || text.includes('form') || text.includes('interview')) {
      return { sectionId: 'section-recruitment_record', tab: 'checklist' };
    }
    if (text.includes('contract') || text.includes('handbook')) {
      return { sectionId: 'section-agreements', tab: 'checklist' };
    }
    // Default to checklist tab
    return { sectionId: null, tab: 'checklist' };
  };
  
  // Handler: Navigate to blocker section
  const handleBlockerClick = (blockerText) => {
    const { sectionId, tab } = mapBlockerToSection(blockerText);
    
    // Switch to the correct tab first
    if (tab !== activeTab) {
      setActiveTab(tab);
      // Use timeout to allow tab content to render before scrolling
      setTimeout(() => {
        if (sectionId) {
          const element = document.querySelector(`[data-testid="${sectionId}"]`);
          if (element) {
            element.scrollIntoView({ behavior: 'smooth', block: 'start' });
            // Add highlight effect
            element.classList.add('ring-2', 'ring-primary', 'ring-offset-2');
            setTimeout(() => element.classList.remove('ring-2', 'ring-primary', 'ring-offset-2'), 2000);
          }
        } else if (tab === 'training' && trainingSectionRef.current) {
          trainingSectionRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      }, 150);
    } else {
      // Already on correct tab, just scroll
      if (sectionId) {
        const element = document.querySelector(`[data-testid="${sectionId}"]`);
        if (element) {
          element.scrollIntoView({ behavior: 'smooth', block: 'start' });
          element.classList.add('ring-2', 'ring-primary', 'ring-offset-2');
          setTimeout(() => element.classList.remove('ring-2', 'ring-primary', 'ring-offset-2'), 2000);
        }
      }
    }
  };
  
  // Fetch recruitment status (Reference Integrity, CV Gaps, Proof of Address)
  const fetchRecruitmentStatus = async () => {
    if (!employeeId) return;
    setLoadingRecruitment(true);
    try {
      const response = await axios.get(`${API}/employees/${employeeId}/recruitment-status`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setRecruitmentStatus(response.data);
    } catch (err) {
      console.error('Failed to fetch recruitment status:', err);
    } finally {
      setLoadingRecruitment(false);
    }
  };
  
  // Fetch Employment History Mismatch Status (CV vs Structured)
  const fetchEmploymentMismatch = async () => {
    if (!employeeId) return;
    setLoadingMismatch(true);
    try {
      const response = await axios.get(`${API}/employees/${employeeId}/employment-mismatch`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setEmploymentMismatch(response.data);
    } catch (err) {
      console.error('Failed to fetch employment mismatch:', err);
    } finally {
      setLoadingMismatch(false);
    }
  };
  
  // Fetch Name Mismatch Status (Phase 4 - Cross-Document Intelligence)
  const fetchNameMismatch = async () => {
    if (!employeeId) return;
    setLoadingNameMismatch(true);
    try {
      const response = await axios.get(`${API}/employees/${employeeId}/name-mismatches`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setNameMismatch(response.data);
    } catch (err) {
      console.error('Failed to fetch name mismatch:', err);
    } finally {
      setLoadingNameMismatch(false);
    }
  };
  
  // Fetch proposed training items (Step 10)
  const fetchProposedTrainingItems = async () => {
    if (!employeeId) return;
    setLoadingProposedItems(true);
    try {
      const response = await axios.get(`${API}/employees/${employeeId}/training/proposed-items`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setProposedTrainingItems(response.data.proposed_items || []);
    } catch (err) {
      console.error('Failed to fetch proposed training items:', err);
    } finally {
      setLoadingProposedItems(false);
    }
  };
  
  // Re-extract employment history from CV (Admin action)
  const handleReextractFromCv = async () => {
    // Find CV document
    const cvDoc = (compliance?.evidence || []).find(e => 
      e.document_type_name?.toLowerCase().includes('cv') || 
      e.document_type_name?.toLowerCase().includes('resume')
    );
    
    if (!cvDoc?.file_id && !cvDoc?.id) {
      toast.error('No CV document found. Please upload a CV first.');
      return;
    }
    
    setIsReextractingFromCv(true);
    try {
      // Step 1: Extract from CV
      const extractResponse = await axios.post(
        `${API}/cv/extract-employment-history?file_id=${cvDoc.file_id || cvDoc.id}&employee_id=${employeeId}`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      if (extractResponse.data.status !== 'success' || !extractResponse.data.extracted_roles?.length) {
        toast.warning('No employment history could be extracted from CV');
        return;
      }
      
      // Step 2: Compare with structured history
      const compareResponse = await axios.post(
        `${API}/employees/${employeeId}/compare-employment-history`,
        extractResponse.data.extracted_roles,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      toast.success(`CV re-extracted. ${extractResponse.data.extracted_roles.length} roles found.`);
      fetchEmploymentMismatch();
      fetchRecruitmentStatus();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to re-extract from CV');
    } finally {
      setIsReextractingFromCv(false);
    }
  };
  
  // Add mismatch review note
  const handleAddMismatchNote = async () => {
    if (mismatchReviewNote.length < 5) {
      toast.error('Note must be at least 5 characters');
      return;
    }
    
    setIsSubmittingMismatchNote(true);
    try {
      await axios.post(
        `${API}/employees/${employeeId}/employment-mismatch/add-note`,
        { note: mismatchReviewNote },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      toast.success('Review note added');
      setMismatchDialogOpen(false);
      setMismatchReviewNote('');
      fetchEmploymentMismatch();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to add note');
    } finally {
      setIsSubmittingMismatchNote(false);
    }
  };
  
  // Fetch training evaluation (canonical evaluator)
  const fetchTrainingEvaluation = async () => {
    if (!employeeId) return;
    setLoadingTrainingEvaluation(true);
    try {
      const response = await axios.get(`${API}/employees/${employeeId}/training`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setTrainingEvaluation(response.data);
    } catch (err) {
      console.error('Failed to fetch training evaluation:', err);
    } finally {
      setLoadingTrainingEvaluation(false);
    }
  };
  
  // Verify reference with integrity check
  const handleVerifyReference = async () => {
    if (!refFromCv && refOverrideReason.length < 10) {
      toast.error('Override reason must be at least 10 characters');
      return;
    }
    
    setIsVerifyingRef(true);
    try {
      await axios.post(`${API}/employees/${employeeId}/verify-reference`, {
        reference_num: selectedRefNum,
        from_cv: refFromCv,
        override_reason: refFromCv ? null : refOverrideReason
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      toast.success(`Reference ${selectedRefNum} verified successfully`);
      setVerifyRefDialogOpen(false);
      setRefFromCv(true);
      setRefOverrideReason('');
      fetchRecruitmentStatus();
      fetchEmployee();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to verify reference');
    } finally {
      setIsVerifyingRef(false);
    }
  };
  
  // Explain CV gap
  const handleExplainGap = async () => {
    if (gapExplanation.length < 10) {
      toast.error('Explanation must be at least 10 characters');
      return;
    }
    
    setIsExplainingGap(true);
    try {
      await axios.post(`${API}/employees/${employeeId}/explain-cv-gap`, {
        gap_id: selectedGap?.gap_id,
        explanation: gapExplanation
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      toast.success('Gap explanation recorded');
      setExplainGapDialogOpen(false);
      setGapExplanation('');
      setSelectedGap(null);
      fetchRecruitmentStatus();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to record explanation');
    } finally {
      setIsExplainingGap(false);
    }
  };
  
  // Fetch reference status (NHS-Level strict workflow)
  const fetchReferenceStatus = async () => {
    if (!employeeId) return;
    setLoadingReferenceStatus(true);
    try {
      const response = await axios.get(`${API}/employees/${employeeId}/reference-status`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setReferenceStatus(response.data.references || []);
    } catch (err) {
      console.error('Failed to fetch reference status:', err);
    } finally {
      setLoadingReferenceStatus(false);
    }
  };
  
  // Send reference request to referee (NHS-Level Step 1: Request)
  const handleSendReferenceRequest = async () => {
    if (!selectedRefForRequest) return;
    
    setIsRequestingReference(true);
    try {
      const response = await axios.post(
        `${API}/employees/${employeeId}/send-reference-request?reference_num=${selectedRefForRequest.reference_num}${referenceRequestMessage ? `&message=${encodeURIComponent(referenceRequestMessage)}` : ''}`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      if (response.data.status === 'duplicate') {
        toast.info('Reference request already sent and awaiting response');
      } else if (response.data.status === 'success') {
        toast.success(`Reference request sent to ${response.data.referee_email}`);
      } else if (response.data.status === 'email_failed') {
        toast.warning('Request created but email failed to send');
      }
      
      setRequestReferenceDialogOpen(false);
      setReferenceRequestMessage('');
      setSelectedRefForRequest(null);
      fetchReferenceStatus();
      fetchEmployee();
      fetchCompliance();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to send reference request');
    } finally {
      setIsRequestingReference(false);
    }
  };
  
  // Review reference (NHS-Level Step 2: Review with mismatch documentation)
  const handleReviewReference = async () => {
    if (!selectedRefForReview) return;
    
    // If mismatch detected, require notes
    if (selectedRefForReview.mismatch_detected && reviewMismatchNotes.length < 10) {
      toast.error('Mismatch detected - please provide at least 10 characters explaining the mismatch');
      return;
    }
    
    setIsReviewingReference(true);
    try {
      await axios.post(
        `${API}/employees/${employeeId}/review-reference?reference_num=${selectedRefForReview.reference_num}${reviewMismatchNotes ? `&mismatch_notes=${encodeURIComponent(reviewMismatchNotes)}` : ''}`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      toast.success(`Reference ${selectedRefForReview.reference_num} reviewed. Ready for final verification.`);
      setReviewReferenceDialogOpen(false);
      setReviewMismatchNotes('');
      setSelectedRefForReview(null);
      fetchReferenceStatus();
      fetchEmployee();
      fetchCompliance();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to review reference');
    } finally {
      setIsReviewingReference(false);
    }
  };
  
  // Verify reference (NHS-Level Step 3: Final Verification - Admin Only)
  const handleVerifyReferenceStrict = async (refNum) => {
    setIsVerifyingReferenceStrict(true);
    try {
      await axios.post(
        `${API}/employees/${employeeId}/verify-reference-strict?reference_num=${refNum}`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      toast.success(`Reference ${refNum} verified (2-step verification complete)`);
      fetchReferenceStatus();
      fetchEmployee();
      fetchCompliance();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to verify reference');
    } finally {
      setIsVerifyingReferenceStrict(false);
    }
  };
  
  // Sync tab changes to URL
  const handleTabChange = (value) => {
    setActiveTab(value);
    setSearchParams({ tab: value }, { replace: true });
  };
  
  // Open document in preview modal - supports single file or array
  const handlePreviewDocument = (url, name, filename) => {
    setPreviewFile({ url, name, filename });
    setPreviewFiles([]); // Clear multi-file array
    setPreviewOpen(true);
  };
  
  // Open multiple files in preview modal with navigation
  const handlePreviewMultipleFiles = (files, requirementId) => {
    if (!files || files.length === 0) return;
    
    // Build array of file objects for the modal
    const fileArray = files.map(f => ({
      url: `${API}/employees/${employeeId}/requirements/${requirementId}/evidence/${f.file_id}/view`,
      filename: f.file_label || f.original_filename || 'Document',
      content_type: f.content_type,
      file_id: f.file_id
    }));
    
    setPreviewFiles(fileArray);
    setPreviewFile(fileArray[0]); // Set first file as initial
    setPreviewOpen(true);
  };

  const roles = [
    'Care Assistant',
    'Senior Care Assistant',
    'Support Worker',
    'Healthcare Assistant',
    'Nurse',
    'Live-in Carer',
    'Night Carer',
    'Team Leader',
    'Care Coordinator'
  ];

  const statuses = [
    { value: 'new', label: 'New' },
    { value: 'screening', label: 'Screening' },
    { value: 'interview', label: 'Interview' },
    { value: 'compliance_review', label: 'Compliance Review' },
    { value: 'onboarding', label: 'Onboarding' },
    { value: 'active', label: 'Active' },
    { value: 'inactive', label: 'Inactive' }
  ];

  const onboardingStatuses = [
    'New',
    'Recruitment File: Incomplete',
    'Under Review',
    'Ready for Placement',
    'Active',
    'Archived'
  ];

  const isSuperAdmin = () => user?.role === 'super_admin';

  const fetchData = async () => {
    // Use Promise.allSettled to allow partial success
    const results = await Promise.allSettled([
      axios.get(`${API}/employees/${employeeId}`, { headers: { Authorization: `Bearer ${token}` } }),
      axios.get(`${API}/employee-documents?employee_id=${employeeId}`, { headers: { Authorization: `Bearer ${token}` } }),
      axios.get(`${API}/document-types`, { headers: { Authorization: `Bearer ${token}` } }),
      axios.get(`${API}/policy-assignments?employee_id=${employeeId}`, { headers: { Authorization: `Bearer ${token}` } }),
      axios.get(`${API}/training-records?employee_id=${employeeId}`, { headers: { Authorization: `Bearer ${token}` } }),
      axios.get(`${API}/audit-logs?entity_id=${employeeId}&compliance_only=true`, { headers: { Authorization: `Bearer ${token}` } }),
      axios.get(`${API}/generated-forms?employee_id=${employeeId}`, { headers: { Authorization: `Bearer ${token}` } }),
      axios.get(`${API}/templates`, { headers: { Authorization: `Bearer ${token}` } }),
      axios.get(`${API}/employees/${employeeId}/compliance-requirements`, { headers: { Authorization: `Bearer ${token}` } })
    ]);
    
    // Process results - extract data or use defaults
    const [empRes, docsRes, typesRes, policiesRes, trainingRes, logsRes, formsRes, templatesRes, compReqRes] = results;
    
    let hasError = false;
    
    // Employee data is critical - if it fails, show error
    if (empRes.status === 'fulfilled') {
      setEmployee(empRes.value.data);
    } else {
      console.error('Failed to fetch employee:', empRes.reason);
      hasError = true;
    }
    
    // Other data can fail gracefully with defaults
    setDocuments(docsRes.status === 'fulfilled' ? docsRes.value.data : []);
    setDocumentTypes(typesRes.status === 'fulfilled' ? typesRes.value.data : []);
    setPolicies(policiesRes.status === 'fulfilled' ? policiesRes.value.data : []);
    setTraining(trainingRes.status === 'fulfilled' ? trainingRes.value.data : []);
    setAuditLogs(logsRes.status === 'fulfilled' ? logsRes.value.data : []);
    setGeneratedForms(formsRes.status === 'fulfilled' ? formsRes.value.data : []);
    setTemplates(templatesRes.status === 'fulfilled' ? templatesRes.value.data : []);
    setComplianceRequirements(compReqRes.status === 'fulfilled' ? compReqRes.value.data : {});
    
    if (hasError) {
      toast.error('Failed to load employee data');
    }
    
    setLoading(false);
  };

  const fetchCompliance = async () => {
    try {
      const response = await axios.get(`${API}/employees/${employeeId}/compliance`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setCompliance(response.data);
    } catch (error) {
      console.error('Failed to fetch compliance:', error);
    }
  };

  const fetchComplianceFile = async () => {
    try {
      const response = await axios.get(`${API}/employees/${employeeId}/compliance-file`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setComplianceFile(response.data);
    } catch (error) {
      console.error('Failed to fetch compliance file:', error);
    }
  };

  useEffect(() => {
    fetchData();
    fetchCompliance();
    fetchComplianceFile();
    fetchRecruitmentStatus();
    fetchReferenceStatus();
    fetchEmploymentMismatch();
    fetchNameMismatch();
    fetchTrainingEvaluation();
    fetchProposedTrainingItems();
  }, [employeeId, token]);

  // Handle URL parameters from email action links
  useEffect(() => {
    const action = searchParams.get('action');
    const requirement = searchParams.get('requirement');
    const requestId = searchParams.get('request_id');
    const emailToken = searchParams.get('token');
    
    if (action && employee) {
      // Track that user clicked the email link
      if (requestId && emailToken) {
        trackEmailClick(requestId, emailToken);
      }
      
      // Handle different action types
      if (action.includes('upload') || action === 'upload_document') {
        // Set the requirement if provided, then open upload dialog
        if (requirement) {
          setSelectedDocType(requirement);
          setSelectedRequirement(requirement);
        }
        setUploadDialogOpen(true);
        
        // Clear URL params after handling
        setSearchParams(prev => {
          const newParams = new URLSearchParams(prev);
          newParams.delete('action');
          newParams.delete('requirement');
          newParams.delete('request_id');
          newParams.delete('token');
          return newParams;
        });
      }
    }
  }, [searchParams, employee, setSearchParams]);

  // Track email click event
  const trackEmailClick = async (requestId, emailToken) => {
    try {
      await axios.post(
        `${API}/email-requests/${requestId}/track-click`,
        { token: emailToken },
        { headers: { Authorization: `Bearer ${token}` } }
      );
    } catch (error) {
      console.error('Failed to track email click:', error);
    }
  };

  // Fetch profile photo when employee has one
  useEffect(() => {
    const fetchProfilePhoto = async () => {
      if (!employee?.profile_photo_url || !token) {
        setProfilePhotoBlob(null);
        return;
      }
      try {
        const response = await axios.get(
          `${API}/employees/${employeeId}/profile-photo/view`,
          { headers: { Authorization: `Bearer ${token}` }, responseType: 'blob' }
        );
        const blobUrl = URL.createObjectURL(response.data);
        setProfilePhotoBlob(blobUrl);
      } catch (error) {
        console.error('Failed to fetch profile photo:', error);
        setProfilePhotoBlob(null);
      }
    };
    fetchProfilePhoto();
    // Cleanup blob URL on unmount or when employee changes
    return () => {
      if (profilePhotoBlob) {
        URL.revokeObjectURL(profilePhotoBlob);
      }
    };
  }, [employee?.profile_photo_url, employeeId, token]);

  const handleRefreshStatus = async () => {
    setIsRefreshingStatus(true);
    try {
      const response = await axios.post(`${API}/employees/${employeeId}/refresh-status`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (response.data.status_changed) {
        toast.success(`Status updated to: ${response.data.new_status}`);
      } else {
        toast.info('Status is already up to date');
      }
      fetchData();
      fetchCompliance();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to refresh status');
    } finally {
      setIsRefreshingStatus(false);
    }
  };

  const handleExportFile = async () => {
    setIsExporting(true);
    try {
      const response = await axios.get(`${API}/employees/${employeeId}/export-file`, {
        headers: { Authorization: `Bearer ${token}` },
        responseType: 'blob'
      });
      
      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      const filename = response.headers['content-disposition']?.split('filename=')[1]?.replace(/"/g, '') 
        || `${employee?.employee_code}_File.zip`;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      toast.success('Employee file exported successfully');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to export file');
    } finally {
      setIsExporting(false);
    }
  };

  const handleExportComplianceSummary = async () => {
    try {
      const response = await axios.get(`${API}/employees/${employeeId}/export-compliance-summary`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      // Convert JSON to downloadable file
      const blob = new Blob([JSON.stringify(response.data, null, 2)], { type: 'application/json' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${employee?.employee_code}_Compliance_Summary.json`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      toast.success('Compliance summary exported');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to export compliance summary');
    }
  };

  const handleExportCompliancePDF = async () => {
    setIsExporting(true);
    try {
      const response = await axios.get(`${API}/employees/${employeeId}/export-compliance-pdf`, {
        headers: { Authorization: `Bearer ${token}` },
        responseType: 'blob'
      });
      
      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }));
      const link = document.createElement('a');
      link.href = url;
      const filename = response.headers['content-disposition']?.split('filename=')[1]?.replace(/"/g, '') 
        || `${employee?.employee_code}_Compliance_Summary.pdf`;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      toast.success('Compliance PDF exported successfully');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to export PDF');
    } finally {
      setIsExporting(false);
    }
  };

  const handlePrintCompliancePDF = async () => {
    try {
      const response = await axios.get(`${API}/employees/${employeeId}/export-compliance-pdf`, {
        headers: { Authorization: `Bearer ${token}` },
        responseType: 'blob'
      });
      
      // Open in new tab for printing
      const url = window.URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }));
      const printWindow = window.open(url, '_blank');
      if (printWindow) {
        printWindow.onload = () => {
          printWindow.print();
        };
      }
    } catch (error) {
      toast.error('Failed to open PDF for printing');
    }
  };

  // Phase 4A - Unified export handler
  const handleExportComplianceFile = async () => {
    setIsExporting(true);
    try {
      // Default to PDF export
      const response = await axios.get(`${API}/employees/${employeeId}/export-compliance-pdf`, {
        headers: { Authorization: `Bearer ${token}` },
        responseType: 'blob'
      });
      
      const url = window.URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }));
      const link = document.createElement('a');
      link.href = url;
      const filename = response.headers['content-disposition']?.split('filename=')[1]?.replace(/"/g, '') 
        || `${employee?.employee_code}_Compliance_File.pdf`;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      toast.success('Compliance file exported');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to export compliance file');
    } finally {
      setIsExporting(false);
    }
  };

  const handleUploadDocument = async (e) => {
    e.preventDefault();
    if (!selectedRequirement || !uploadFile) {
      toast.error('Please select a requirement and choose a file to upload');
      return;
    }
    
    setIsUploading(true);
    
    try {
      const formData = new FormData();
      formData.append('file', uploadFile);
      if (documentLabel) {
        formData.append('file_label', documentLabel);
      }
      
      // Use the unified evidence upload endpoint
      await axios.post(`${API}/employees/${employeeId}/requirements/${selectedRequirement}/evidence`, formData, {
        headers: { 
          Authorization: `Bearer ${token}`,
          'Content-Type': 'multipart/form-data'
        }
      });
      
      // POST-UPLOAD FEEDBACK - Clear guidance on next step
      toast.success('Document uploaded — please review and approve', {
        duration: 5000,
        description: 'Check the document is clear and correct, then mark as approved.'
      });
      setUploadDialogOpen(false);
      setSelectedRequirement('');
      setSelectedDocType('');
      setDocumentLabel('');
      setUploadFile(null);
      fetchData();
      fetchCompliance();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Upload failed — please try again');
    } finally {
      setIsUploading(false);
    }
  };

  const handleUpdateDocumentStatus = async (docId, status) => {
    try {
      await axios.put(`${API}/employee-documents/${docId}`, { status }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success(`Document ${status}`);
      fetchData();
    } catch (error) {
      toast.error('Failed to update document');
    }
  };

  const handleVerifyDocument = async (docId, fileUrl) => {
    try {
      await axios.post(`${API}/employee-documents/${docId}/verify`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Document approved');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to verify document');
    }
  };

  const handleUnverifyDocument = async (docId) => {
    try {
      await axios.post(`${API}/employee-documents/${docId}/unverify`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Verification removed');
      fetchData();
    } catch (error) {
      toast.error('Failed to remove verification');
    }
  };

  const handleSaveFormAsDocument = async (formId, e) => {
    e.stopPropagation(); // Prevent navigation to form editor
    try {
      toast.loading('Saving form as document...');
      const response = await axios.post(`${API}/generated-forms/${formId}/save-as-document`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.dismiss();
      toast.success(`Saved to ${response.data.folder}`);
      fetchData();
    } catch (error) {
      toast.dismiss();
      toast.error(error.response?.data?.detail || 'Failed to save form as document');
    }
  };

  // Verify all documents under a requirement
  const handleVerifyRequirement = async (requirementId) => {
    try {
      // Get the requirement data
      const req = complianceRequirements?.requirements?.find(r => r.id === requirementId);
      if (!req) {
        toast.error('Requirement not found');
        return;
      }
      
      // Get evidence files
      const evidenceFiles = req.evidence_files || [];
      if (evidenceFiles.length === 0) {
        toast.error('Cannot verify - no evidence file uploaded');
        return;
      }
      
      // Proceed with verification - backend will handle file validation
      await axios.post(`${API}/employees/${employeeId}/requirements/${requirementId}/verify-all`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Requirement approved');
      await fetchData();
      await fetchCompliance();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to verify requirement');
    }
  };

  // Delete a specific document (for multi-file requirements)
  const handleDeleteDocument = async (docId) => {
    try {
      await axios.delete(`${API}/employee-documents/${docId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Document deleted');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete document');
    }
  };

  // Open remove file dialog
  const openRemoveDialog = (file, requirementId) => {
    setSelectedFileForAction(file);
    setSelectedRequirementForAction(requirementId);
    setRemoveReason('');
    setRemoveDialogOpen(true);
  };

  // Handle permanent delete file (removes from active use, keeps audit trail)
  const handleDeleteFile = async () => {
    setIsRemoving(true);
    try {
      await axios.post(
        `${API}/employees/${employeeId}/requirements/${selectedRequirementForAction}/evidence/${selectedFileForAction.file_id}/delete`,
        { reason: removeReason.trim() || null },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('File deleted successfully');
      setRemoveDialogOpen(false);
      setSelectedFileForAction(null);
      setSelectedRequirementForAction(null);
      setRemoveReason('');
      // CRITICAL: await fetchData to ensure UI syncs immediately
      await fetchData();
      await fetchCompliance();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete file');
    } finally {
      setIsRemoving(false);
    }
  };

  // Open replace file dialog
  const openReplaceDialog = (file, requirementId) => {
    setSelectedFileForAction(file);
    setSelectedRequirementForAction(requirementId);
    setReplaceReason('');
    setReplaceFile(null);
    setReplaceDialogOpen(true);
  };

  // Handle replace file
  const handleReplaceFile = async () => {
    if (!replaceReason.trim() || replaceReason.trim().length < 3) {
      toast.error('Please provide a reason (minimum 3 characters)');
      return;
    }
    if (!replaceFile) {
      toast.error('Please select a replacement file');
      return;
    }

    setIsReplacing(true);
    try {
      const formData = new FormData();
      formData.append('file', replaceFile);
      formData.append('reason', replaceReason.trim());
      
      await axios.post(
        `${API}/employees/${employeeId}/requirements/${selectedRequirementForAction}/evidence/${selectedFileForAction.file_id}/replace`,
        formData,
        { 
          headers: { 
            Authorization: `Bearer ${token}`,
            'Content-Type': 'multipart/form-data'
          }
        }
      );
      toast.success('File replaced successfully');
      setReplaceDialogOpen(false);
      setSelectedFileForAction(null);
      setSelectedRequirementForAction(null);
      setReplaceReason('');
      setReplaceFile(null);
      // CRITICAL: await fetchData to ensure UI syncs immediately
      await fetchData();
      await fetchCompliance();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to replace file');
    } finally {
      setIsReplacing(false);
    }
  };

  // Fetch requirement history
  const fetchRequirementHistory = async (requirementId) => {
    setLoadingHistory(true);
    try {
      const response = await axios.get(
        `${API}/employees/${employeeId}/requirements/${requirementId}/history`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setRequirementHistory(response.data.history || []);
    } catch (error) {
      console.error('Failed to fetch history:', error);
      setRequirementHistory([]);
    } finally {
      setLoadingHistory(false);
    }
  };

  // Open requirement history dialog
  const openHistoryDialog = (requirementId) => {
    setSelectedRequirementForAction(requirementId);
    setRequirementHistoryOpen(true);
    fetchRequirementHistory(requirementId);
  };

  // ========================================
  // DOCUMENT CORRECTION ACTIONS (Step 8)
  // ========================================
  
  // Mark document as uploaded in error
  const handleMarkUploadedInError = async (documentId, reason) => {
    if (!reason || reason.trim().length < 10) {
      toast.error('Please provide a reason (minimum 10 characters)');
      return false;
    }
    
    try {
      await axios.post(
        `${API}/documents/${documentId}/mark-uploaded-in-error`,
        { reason: reason.trim() },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Document marked as uploaded in error');
      await fetchData();
      await fetchCompliance();
      return true;
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to mark document');
      return false;
    }
  };

  // Supersede document with newer version
  const handleSupersedeDocument = async (documentId, replacementId, reason) => {
    try {
      await axios.post(
        `${API}/documents/${documentId}/supersede`,
        { 
          replacement_document_id: replacementId || null,
          reason: reason || 'Replaced by newer document'
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Document marked as superseded');
      await fetchData();
      await fetchCompliance();
      return true;
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to supersede document');
      return false;
    }
  };

  // Move document to different requirement category
  const handleMoveDocumentCategory = async (documentId, newRequirementId, reason) => {
    if (!reason || reason.trim().length < 5) {
      toast.error('Please provide a reason (minimum 5 characters)');
      return false;
    }
    
    try {
      await axios.post(
        `${API}/documents/${documentId}/move-category`,
        { 
          new_requirement_id: newRequirementId,
          reason: reason.trim()
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Document moved to new category');
      await fetchData();
      await fetchCompliance();
      return true;
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to move document');
      return false;
    }
  };

  // Reopen document for review (undo verification/rejection)
  const handleReopenDocumentReview = async (documentId, reason) => {
    if (!reason || reason.trim().length < 10) {
      toast.error('Please provide a reason (minimum 10 characters)');
      return false;
    }
    
    try {
      await axios.post(
        `${API}/documents/${documentId}/reopen-review`,
        { reason: reason.trim() },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Document reopened for review');
      await fetchData();
      await fetchCompliance();
      return true;
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to reopen document');
      return false;
    }
  };

  // Open document correction dialog
  const openDocCorrectionDialog = (type, document) => {
    setDocCorrectionType(type);
    setDocCorrectionTarget(document);
    setDocCorrectionReason('');
    setDocCorrectionNewCategory('');
    setDocCorrectionDialogOpen(true);
  };

  // Submit document correction
  const handleSubmitDocCorrection = async () => {
    setIsSubmittingDocCorrection(true);
    try {
      let success = false;
      switch (docCorrectionType) {
        case 'uploaded_in_error':
          success = await handleMarkUploadedInError(docCorrectionTarget.file_id || docCorrectionTarget.id, docCorrectionReason);
          break;
        case 'supersede':
          success = await handleSupersedeDocument(docCorrectionTarget.file_id || docCorrectionTarget.id, null, docCorrectionReason);
          break;
        case 'move_category':
          success = await handleMoveDocumentCategory(docCorrectionTarget.file_id || docCorrectionTarget.id, docCorrectionNewCategory, docCorrectionReason);
          break;
        case 'reopen_review':
          success = await handleReopenDocumentReview(docCorrectionTarget.file_id || docCorrectionTarget.id, docCorrectionReason);
          break;
        default:
          toast.error('Unknown correction type');
      }
      
      if (success) {
        setDocCorrectionDialogOpen(false);
        setDocCorrectionTarget(null);
        setDocCorrectionType(null);
        setDocCorrectionReason('');
        setDocCorrectionNewCategory('');
      }
    } finally {
      setIsSubmittingDocCorrection(false);
    }
  };

  // ========================================
  // DOCUMENT EXTRACTION REVIEW (Phase 2)
  // ========================================
  
  // Requirement IDs that support extraction
  const EXTRACTABLE_REQUIREMENTS = [
    'dbs_certificate', 'dbs_check',
    'right_to_work_documents', 'right_to_work_check',
    'id_document', 'passport', 'driving_licence',
    'proof_of_address', 'proof_of_address_1', 'proof_of_address_2'
  ];
  
  // Check if a requirement supports extraction
  const isExtractableRequirement = (requirementId) => {
    return EXTRACTABLE_REQUIREMENTS.some(r => requirementId?.toLowerCase().includes(r.toLowerCase()));
  };
  
  // Open document extraction review
  // BUGFIX: Must receive actual document_id, not file_id from evidence_files
  const openDocExtraction = (document, requirementName = '') => {
    // Validate we have a proper document ID
    const documentId = document?.id || document?.document_id;
    
    if (!documentId) {
      toast.error('No document selected for extraction. Please select a specific file.');
      console.error('openDocExtraction called without valid document ID:', document);
      return;
    }
    
    // Build context for modal header
    const context = {
      documentId,
      fileName: document.file_label || document.original_filename || document.file_name || 'Document',
      requirementName: requirementName,
      documentType: document.document_type || document.requirement_id || '',
      uploadedAt: document.uploaded_at
    };
    
    setDocExtractionDocumentId(documentId);
    setDocExtractionDocumentName(context.fileName);
    setDocExtractionContext(context);
    setDocExtractionReviewOpen(true);
  };
  
  // Handle extraction review complete
  const handleDocExtractionComplete = () => {
    setDocExtractionReviewOpen(false);
    setDocExtractionDocumentId(null);
    setDocExtractionDocumentName('');
    setDocExtractionContext(null);
    fetchData();
    fetchCompliance();
    toast.success('Document extraction reviewed successfully');
  };

  const handleBulkUpload = async () => {
    if (bulkFiles.length === 0) {
      toast.error('Please select files to upload');
      return;
    }
    
    // Check all files have doc type assigned
    const missingTypes = bulkFiles.filter((_, i) => !bulkDocTypes[i]);
    if (missingTypes.length > 0) {
      toast.error('Please assign document types to all files');
      return;
    }
    
    setIsUploading(true);
    
    try {
      const formData = new FormData();
      bulkFiles.forEach((file) => formData.append('files', file));
      const typeIds = bulkFiles.map((_, i) => bulkDocTypes[i]).join(',');
      
      const response = await axios.post(
        `${API}/employees/${employeeId}/bulk-upload?document_type_ids=${typeIds}`,
        formData,
        { 
          headers: { 
            Authorization: `Bearer ${token}`,
            'Content-Type': 'multipart/form-data'
          }
        }
      );
      
      toast.success(`Uploaded ${response.data.successful} documents`);
      if (response.data.errors?.length > 0) {
        response.data.errors.forEach(err => toast.error(err));
      }
      
      setBulkUploadOpen(false);
      setBulkFiles([]);
      setBulkDocTypes({});
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to upload documents');
    } finally {
      setIsUploading(false);
    }
  };

  const handleGenerateForms = async () => {
    if (selectedTemplates.length === 0) {
      toast.error('Please select at least one template');
      return;
    }
    
    setIsGenerating(true);
    
    try {
      const response = await axios.post(
        `${API}/generated-forms/bulk`,
        null,
        {
          headers: { Authorization: `Bearer ${token}` },
          params: {
            employee_id: employeeId,
            template_ids: selectedTemplates
          },
          paramsSerializer: params => {
            return Object.keys(params).map(key => {
              if (Array.isArray(params[key])) {
                return params[key].map(v => `${key}=${v}`).join('&');
              }
              return `${key}=${params[key]}`;
            }).join('&');
          }
        }
      );
      
      toast.success(`Generated ${response.data.created} forms`);
      if (response.data.errors?.length > 0) {
        response.data.errors.forEach(err => toast.warning(err));
      }
      
      setGenerateFormsOpen(false);
      setSelectedTemplates([]);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to generate forms');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleImportApplication = async () => {
    if (!importAppFile) {
      toast.error('Please select an application form to upload');
      return;
    }
    
    setIsImporting(true);
    
    try {
      const formData = new FormData();
      formData.append('employee_id', employeeId);
      formData.append('application_file', importAppFile);
      if (importCvFile) {
        formData.append('cv_file', importCvFile);
      }
      
      const response = await axios.post(
        `${API}/generated-forms/import-application`,
        formData,
        {
          headers: { 
            Authorization: `Bearer ${token}`,
            'Content-Type': 'multipart/form-data'
          }
        }
      );
      
      toast.success(response.data.message || 'Application imported successfully');
      setImportAppOpen(false);
      setImportAppFile(null);
      setImportCvFile(null);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to import application');
    } finally {
      setIsImporting(false);
    }
  };

  // Import document for Reference, Health Screening, Contract, etc.
  const handleImportDocument = async () => {
    if (!importDocFile || !importDocType) {
      toast.error('Please select document type and file');
      return;
    }
    
    setIsImporting(true);
    
    try {
      const formData = new FormData();
      formData.append('employee_id', employeeId);
      formData.append('form_type', importDocType);
      formData.append('document_file', importDocFile);
      if (importDocNotes) {
        formData.append('notes', importDocNotes);
      }
      
      const response = await axios.post(
        `${API}/generated-forms/import-document`,
        formData,
        {
          headers: { 
            Authorization: `Bearer ${token}`,
            'Content-Type': 'multipart/form-data'
          }
        }
      );
      
      toast.success(response.data.message || 'Document imported successfully');
      setImportDocOpen(false);
      setImportDocType('');
      setImportDocFile(null);
      setImportDocNotes('');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to import document');
    } finally {
      setIsImporting(false);
    }
  };

  // Handle completing a training requirement
  const handleCompleteTraining = async () => {
    if (!selectedTrainingReq) {
      toast.error('No training requirement selected');
      return;
    }
    
    setIsCompletingTraining(true);
    
    try {
      const response = await axios.post(
        `${API}/employees/${employeeId}/complete-training`,
        {
          requirement_id: selectedTrainingReq.id,
          expiry_date: trainingExpiryDate || null
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      toast.success(response.data.message || 'Training marked as complete');
      setTrainingDialogOpen(false);
      setSelectedTrainingReq(null);
      setTrainingExpiryDate('');
      fetchData();
      fetchCompliance();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to complete training');
    } finally {
      setIsCompletingTraining(false);
    }
  };
  
  // Open training completion dialog
  const openTrainingDialog = (requirement) => {
    setSelectedTrainingReq(requirement);
    setTrainingExpiryDate('');
    setTrainingDialogOpen(true);
  };
  
  // Open training certificate upload dialog
  const openTrainingCertDialog = (requirement) => {
    setSelectedTrainingReq(requirement);
    setTrainingExpiryDate('');
    setTrainingCertFile(null);
    setTrainingCertDialogOpen(true);
  };
  
  // Handle uploading training certificate
  const handleUploadTrainingCertificate = async () => {
    if (!selectedTrainingReq || !trainingCertFile) {
      toast.error('Please select a certificate file');
      return;
    }
    
    setIsUploadingCert(true);
    
    try {
      const formData = new FormData();
      formData.append('file', trainingCertFile);
      if (trainingExpiryDate) {
        formData.append('expiry_date', trainingExpiryDate);
      }
      
      const response = await axios.post(
        `${API}/employees/${employeeId}/training/${selectedTrainingReq.id}/upload-certificate`,
        formData,
        { 
          headers: { 
            Authorization: `Bearer ${token}`,
            'Content-Type': 'multipart/form-data'
          } 
        }
      );
      
      toast.success(response.data.message || 'Certificate uploaded successfully');
      setTrainingCertDialogOpen(false);
      setSelectedTrainingReq(null);
      setTrainingCertFile(null);
      setTrainingExpiryDate('');
      fetchData();
      fetchCompliance();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to upload certificate');
    } finally {
      setIsUploadingCert(false);
    }
  };
  
  // Handle verifying training
  const handleVerifyTraining = async (trainingId) => {
    setIsVerifyingTraining(true);
    try {
      await axios.post(
        `${API}/training-records/${trainingId}/verify`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Training verified successfully');
      fetchData();
      fetchCompliance();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to verify training');
    } finally {
      setIsVerifyingTraining(false);
    }
  };
  
  // Handle unverifying training
  const handleUnverifyTraining = async (trainingId) => {
    try {
      await axios.post(
        `${API}/training-records/${trainingId}/unverify`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Training verification removed');
      fetchData();
      fetchCompliance();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to remove verification');
    }
  };
  
  // View training certificate
  const handleViewTrainingCertificate = (trainingId, filename) => {
    if (!trainingId) {
      toast.error('Training record not found');
      return;
    }
    const url = `${API}/training-records/${trainingId}/certificate/file`;
    setPreviewFile({ url, name: filename || 'Certificate', filename: filename || 'Certificate' });
    setPreviewOpen(true);
  };
  
  // Download training certificate
  const handleDownloadTrainingCertificate = async (trainingId, filename) => {
    if (!trainingId) {
      toast.error('Training record not found');
      return;
    }
    try {
      const response = await axios.get(
        `${API}/training-records/${trainingId}/certificate/download`,
        {
          headers: { Authorization: `Bearer ${token}` },
          responseType: 'blob'
        }
      );
      const blob = new Blob([response.data]);
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename || 'training_certificate';
      link.click();
      URL.revokeObjectURL(url);
      toast.success('Certificate downloaded');
    } catch (error) {
      console.error('Download error:', error);
      toast.error(error.response?.status === 404 ? 'Certificate file not found' : 'Failed to download certificate');
    }
  };
  
  // Training correction handler
  const handleTrainingCorrection = async () => {
    if (!trainingCorrectionReason || trainingCorrectionReason.trim().length < 3) {
      toast.error('Please provide a reason for this correction (minimum 3 characters)');
      return;
    }
    
    try {
      await axios.post(
        `${API}/training-records/${editingTrainingRecord.id}/correct`,
        {
          field: trainingCorrectionField,
          old_value: editingTrainingRecord[trainingCorrectionField],
          new_value: trainingCorrectionValue,
          reason: trainingCorrectionReason.trim()
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Training record corrected');
      setTrainingCorrectionDialogOpen(false);
      setEditingTrainingRecord(null);
      await fetchData();
      await fetchCompliance();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to correct training record');
    }
  };

  // Delete training record handler
  const handleDeleteTrainingRecord = async () => {
    setIsDeletingTraining(true);
    try {
      await axios.delete(
        `${API}/training-records/${deletingTrainingRecord.id}`,
        { 
          headers: { Authorization: `Bearer ${token}` },
          params: { reason: deleteTrainingReason.trim() || undefined }
        }
      );
      toast.success('Training record deleted');
      setDeleteTrainingDialogOpen(false);
      setDeletingTrainingRecord(null);
      setDeleteTrainingReason('');
      await fetchData();
      await fetchCompliance();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete training record');
    } finally {
      setIsDeletingTraining(false);
    }
  };

  // Open training correction dialog from What's Needed tab
  // This reuses the same dialog as the Training tab for consistency
  const openTrainingCorrectionFromWhatsNeeded = (requirement) => {
    if (!requirement.training?.id) {
      toast.error('No training record found for this requirement');
      return;
    }
    
    // Build a training record object compatible with the correction dialog
    const trainingRecord = {
      id: requirement.training.id,
      training_name: requirement.name,
      status: requirement.training.status,
      expiry_date: requirement.training.expiry_date,
      completion_date: requirement.training.completed_at,
      verified: requirement.training.verified
    };
    
    setEditingTrainingRecord(trainingRecord);
    setTrainingCorrectionField('expiry_date');
    setTrainingCorrectionValue(trainingRecord.expiry_date?.split('T')[0] || '');
    setTrainingCorrectionReason('');
    setTrainingCorrectionDialogOpen(true);
  };

  // Open delete training dialog from What's Needed tab
  const openDeleteTrainingFromWhatsNeeded = (requirement) => {
    if (!requirement.training?.id) {
      toast.error('No training record found for this requirement');
      return;
    }
    
    // Build a training record object compatible with the delete dialog
    const trainingRecord = {
      id: requirement.training.id,
      training_name: requirement.name,
      status: requirement.training.status,
      verified: requirement.training.verified
    };
    
    setDeletingTrainingRecord(trainingRecord);
    setDeleteTrainingReason('');
    setDeleteTrainingDialogOpen(true);
  };

  // Handle requirement acknowledgement (Contract/Handbook)
  const handleAcknowledgeRequirement = async () => {
    if (!acknowledgingRequirement) return;
    
    setIsAcknowledging(true);
    try {
      await axios.post(
        `${API}/employees/${employeeId}/requirements/${acknowledgingRequirement.id}/acknowledge`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success(`${acknowledgingRequirement.name} acknowledged and completed`);
      setAcknowledgementDialogOpen(false);
      setAcknowledgingRequirement(null);
      setAcknowledgementConfirmed(false);
      await fetchData();
      await fetchCompliance();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to submit acknowledgement');
    } finally {
      setIsAcknowledging(false);
    }
  };

  // Profile photo upload handler
  const handlePhotoUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    // Validate file type
    const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp'];
    if (!allowedTypes.includes(file.type)) {
      toast.error('Only JPG, PNG, and WEBP images are allowed');
      return;
    }
    
    // Validate file size (5MB max)
    if (file.size > 5 * 1024 * 1024) {
      toast.error('Image must be less than 5MB');
      return;
    }
    
    setIsUploadingPhoto(true);
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      await axios.post(
        `${API}/employees/${employeeId}/profile-photo`,
        formData,
        {
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'multipart/form-data'
          }
        }
      );
      toast.success('Profile photo uploaded');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to upload photo');
    } finally {
      setIsUploadingPhoto(false);
      if (photoInputRef.current) photoInputRef.current.value = '';
    }
  };

  // Remove profile photo handler
  const handleRemovePhoto = async () => {
    try {
      await axios.delete(
        `${API}/employees/${employeeId}/profile-photo`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Profile photo removed');
      fetchData();
    } catch (error) {
      toast.error('Failed to remove photo');
    }
  };

  // Open edit evidence modal
  const openEditEvidence = (reqId, fileData) => {
    setEditEvidenceData({ 
      requirementId: reqId, 
      file: fileData 
    });
    setEditForm({
      issue_date: fileData.issue_date || '',
      expiry_date: fileData.expiry_date || '',
      notes: fileData.notes || '',
      file_label: fileData.file_label || fileData.original_filename || '',
      reason: ''
    });
    setEditEvidenceOpen(true);
  };

  // Save evidence edits
  const handleSaveEvidenceEdit = async () => {
    if (!editForm.reason || editForm.reason.trim().length < 3) {
      toast.error('Please provide a reason for this change (min 3 characters)');
      return;
    }
    
    setIsEditingEvidence(true);
    try {
      await axios.put(
        `${API}/employees/${employeeId}/requirements/${editEvidenceData.requirementId}/evidence/${editEvidenceData.file.file_id}`,
        {
          issue_date: editForm.issue_date || null,
          expiry_date: editForm.expiry_date || null,
          notes: editForm.notes || null,
          file_label: editForm.file_label || null,
          reason: editForm.reason
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Document details updated');
      setEditEvidenceOpen(false);
      // Force refresh data immediately after edit to ensure expiry status is recalculated
      await fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update details');
    } finally {
      setIsEditingEvidence(false);
    }
  };

  // Load evidence edit history
  const loadEditHistory = async (reqId, fileId) => {
    try {
      const response = await axios.get(
        `${API}/employees/${employeeId}/requirements/${reqId}/evidence/${fileId}/history`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setEditHistory(response.data);
      setHistoryOpen(true);
    } catch (error) {
      toast.error('Failed to load history');
    }
  };

  const toggleTemplateSelection = (templateId) => {
    setSelectedTemplates(prev => 
      prev.includes(templateId)
        ? prev.filter(id => id !== templateId)
        : [...prev, templateId]
    );
  };

  const openEditDialog = () => {
    setEditForm({
      first_name: employee?.first_name || '',
      last_name: employee?.last_name || '',
      email: employee?.email || '',
      phone: employee?.phone || '',
      role: employee?.role || '',
      status: employee?.status || '',
      onboarding_status: employee?.onboarding_status || 'New',
      start_date: employee?.start_date || '',
      notes: employee?.notes || ''
    });
    setEditDialogOpen(true);
  };

  const handleSaveEmployee = async () => {
    setIsSaving(true);
    try {
      await axios.put(`${API}/employees/${employeeId}`, editForm, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Employee details updated');
      setEditDialogOpen(false);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update employee');
    } finally {
      setIsSaving(false);
    }
  };

  const handleArchiveEmployee = async () => {
    try {
      await axios.post(`${API}/employees/${employeeId}/archive`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Employee archived successfully');
      setArchiveDialogOpen(false);
      navigate(isRecruitmentView ? '/portal/recruitment' : '/portal/employees');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to archive employee');
    }
  };

  const handleRestoreEmployee = async () => {
    try {
      await axios.post(`${API}/employees/${employeeId}/restore`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Employee restored successfully');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to restore employee');
    }
  };

  const handlePermanentDelete = async () => {
    try {
      await axios.delete(`${API}/employees/${employeeId}/permanent`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Employee permanently deleted');
      setDeleteDialogOpen(false);
      navigate(isRecruitmentView ? '/portal/recruitment' : '/portal/employees');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete employee');
    }
  };

  // ========== Document Request Handlers ==========
  
  // Open request document dialog
  const openRequestDocDialog = (requirement, isResend = false) => {
    setRequestingRequirement(requirement);
    setRequestDocMessage('');
    setIsResendMode(isResend);
    setRequestDocDialogOpen(true);
  };
  
  // State for resend mode
  const [isResendMode, setIsResendMode] = useState(false);
  const [duplicateBlockedInfo, setDuplicateBlockedInfo] = useState(null);
  
  // Send document request email
  const handleRequestDocument = async (forceResend = false) => {
    if (!requestingRequirement) return;
    
    setIsRequestingDoc(true);
    setDuplicateBlockedInfo(null);
    
    try {
      const response = await axios.post(
        `${API}/employees/${employeeId}/request-document`,
        null,
        {
          headers: { Authorization: `Bearer ${token}` },
          params: {
            requirement_id: requestingRequirement.id,
            message: requestDocMessage || undefined,
            due_days: 14,
            force_resend: forceResend || isResendMode
          }
        }
      );
      
      const status = response.data.status;
      
      if (status === 'sent') {
        toast.success(response.data.message || 'Request sent successfully');
        setRequestDocDialogOpen(false);
        setRequestingRequirement(null);
        setRequestDocMessage('');
        setIsResendMode(false);
      } else if (status === 'resent') {
        toast.success(response.data.message || 'Request resent successfully');
        setRequestDocDialogOpen(false);
        setRequestingRequirement(null);
        setRequestDocMessage('');
        setIsResendMode(false);
      } else if (status === 'duplicate_blocked') {
        // Show duplicate blocked info and offer resend option
        setDuplicateBlockedInfo({
          message: response.data.message,
          existingRequestId: response.data.existing_request_id
        });
        toast.warning('An active request already exists. Click "Resend" to send a new email.');
      } else {
        toast.info(response.data.message || 'Request processed');
        setRequestDocDialogOpen(false);
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to send request');
    } finally {
      setIsRequestingDoc(false);
    }
  };
  
  // Handle resend action
  const handleResendRequest = () => {
    handleRequestDocument(true);
  };

  // ========== Send Form via Email Handlers ==========
  
  const FORM_OPTIONS = [
    { value: 'staff_health_questionnaire', label: 'Health Questionnaire' },
    { value: 'staff_personal_info', label: 'Personal Details Form' },
    { value: 'hmrc_starter_checklist', label: 'HMRC Starter Checklist' },
    { value: 'interview_record', label: 'Interview Record' }
  ];
  
  const openSendFormDialog = (formType) => {
    setSelectedFormType(formType || '');
    setSendFormMessage('');
    setSendFormDialogOpen(true);
  };
  
  const handleSendForm = async () => {
    if (!selectedFormType) {
      toast.error('Please select a form type');
      return;
    }
    
    setIsSendingForm(true);
    try {
      const response = await axios.post(
        `${API}/employees/${employeeId}/send-form`,
        null,
        {
          headers: { Authorization: `Bearer ${token}` },
          params: {
            form_type: selectedFormType,
            message: sendFormMessage || undefined
          }
        }
      );
      
      if (response.data.status === 'duplicate') {
        toast.info(response.data.message || 'Form request already pending');
      } else {
        toast.success(response.data.message || 'Form request sent');
      }
      
      setSendFormDialogOpen(false);
      setSelectedFormType('');
      setSendFormMessage('');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to send form request');
    } finally {
      setIsSendingForm(false);
    }
  };

  // ========== Application Form Extraction Handlers ==========
  
  // Start extraction from application form
  const handleExtractFromApplication = async () => {
    setIsExtracting(true);
    setExtractionDialogOpen(true);
    setExtractionResult(null);
    setExtractionFailed(null);
    setFieldsToApply({});
    
    try {
      const response = await axios.post(
        `${API}/employees/${employeeId}/extract-from-application`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      // Check if extraction failed gracefully (returns extraction_failed: true)
      if (response.data.extraction_failed) {
        setExtractionFailed(response.data);
        // Don't show error toast - show the options modal instead
      } else {
        setExtractionResult(response.data);
        
        // Initialize fields to apply based on extraction result
        const initialFields = {};
        response.data.fields.forEach(field => {
          // Default: apply if field is empty in profile OR if extracted value differs
          initialFields[field.field_name] = field.apply;
        });
        setFieldsToApply(initialFields);
        
        toast.success(`Extracted ${response.data.fields.length} fields from application form`);
      }
    } catch (error) {
      // Only show toast for actual API errors (not graceful failures)
      const errorDetail = error.response?.data?.detail;
      if (errorDetail && errorDetail.includes('No application form found')) {
        toast.error('No application form found. Please upload an application form first.');
        setExtractionDialogOpen(false);
      } else {
        // For unexpected errors, show failure options
        setExtractionFailed({
          extraction_failed: true,
          message: errorDetail || 'An unexpected error occurred during extraction.',
          options: [
            { action: 'fill_manually', label: 'Fill form manually', description: 'Enter profile data manually' },
            { action: 'retry', label: 'Retry extraction', description: 'Try extracting again' }
          ]
        });
      }
    } finally {
      setIsExtracting(false);
    }
  };
  
  // Handle extraction failure options
  const handleExtractionOption = async (action) => {
    switch (action) {
      case 'fill_manually':
        setExtractionDialogOpen(false);
        setExtractionFailed(null);
        // Switch to forms tab for manual entry
        setActiveTab('forms');
        toast.info('You can manually enter profile data using the forms below.');
        break;
      case 'view_document':
        if (extractionFailed?.file_url) {
          window.open(extractionFailed.file_url, '_blank');
        }
        break;
      case 'retry':
        setExtractionFailed(null);
        await handleExtractFromApplication();
        break;
      default:
        break;
    }
  };
  
  // Toggle a field for applying
  const toggleFieldToApply = (fieldName) => {
    setFieldsToApply(prev => ({
      ...prev,
      [fieldName]: !prev[fieldName]
    }));
  };
  
  // Apply selected extracted fields to profile
  const handleApplyExtraction = async () => {
    if (!extractionResult) return;
    
    const selectedFields = Object.entries(fieldsToApply)
      .filter(([_, apply]) => apply)
      .map(([fieldName]) => fieldName);
    
    if (selectedFields.length === 0) {
      toast.error('Please select at least one field to apply');
      return;
    }
    
    setIsApplyingExtraction(true);
    try {
      const response = await axios.post(
        `${API}/extractions/${extractionResult.extraction_id}/apply`,
        { extraction_id: extractionResult.extraction_id, fields_to_apply: selectedFields },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      const result = response.data;
      
      // Show success with details
      if (result.applied_fields && result.applied_fields.length > 0) {
        toast.success(`Profile updated: ${result.applied_fields.length} field(s) applied`);
      }
      
      // Show warnings for failed fields
      if (result.warnings?.failed_fields?.length > 0) {
        const failedNames = result.warnings.failed_fields.map(f => f.field).join(', ');
        toast.warning(`Some fields could not be applied: ${failedNames}`);
      }
      
      // Show info for unsupported fields
      if (result.unsupported?.fields?.length > 0) {
        const unsupportedNames = result.unsupported.fields.map(f => f.field).join(', ');
        toast.info(`Unsupported fields skipped: ${unsupportedNames}`);
      }
      
      setExtractionDialogOpen(false);
      setExtractionResult(null);
      
      // Refresh employee data
      try {
        await fetchData();
      } catch (refreshError) {
        console.error('Error refreshing data after apply:', refreshError);
        // Don't show error toast - the apply was successful
      }
    } catch (error) {
      const errorDetail = error.response?.data?.detail;
      
      if (typeof errorDetail === 'object') {
        // Structured error response
        const message = errorDetail.message || 'Failed to apply extracted data';
        const failedFields = errorDetail.failed_fields || [];
        const unsupportedFields = errorDetail.unsupported_fields || [];
        
        if (failedFields.length > 0) {
          const failedInfo = failedFields.map(f => `${f.field}: ${f.reason}`).join('\n');
          toast.error(`${message}\n${failedInfo}`);
        } else if (unsupportedFields.length > 0) {
          toast.error(`${message}: ${unsupportedFields.map(f => f.field).join(', ')}`);
        } else {
          toast.error(message);
        }
      } else {
        toast.error(errorDetail || 'Failed to apply extracted data');
      }
    } finally {
      setIsApplyingExtraction(false);
    }
  };
  
  // Discard extraction without applying
  const handleDiscardExtraction = async () => {
    // If there's a failed extraction, just close the dialog
    if (extractionFailed) {
      setExtractionDialogOpen(false);
      setExtractionFailed(null);
      return;
    }
    
    if (!extractionResult) {
      setExtractionDialogOpen(false);
      return;
    }
    
    try {
      await axios.post(
        `${API}/extractions/${extractionResult.extraction_id}/discard`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.info('Extraction discarded');
    } catch (error) {
      // Ignore discard errors
    }
    
    setExtractionDialogOpen(false);
    setExtractionResult(null);
    setExtractionFailed(null);
  };
  
  // Human-readable field name mapping
  const FIELD_LABELS = {
    first_name: 'First Name',
    last_name: 'Last Name',
    email: 'Email Address',
    phone: 'Phone Number',
    address_line_1: 'Address Line 1',
    address_line_2: 'Address Line 2',
    city: 'City',
    county: 'County',
    postcode: 'Postcode',
    country: 'Country',
    ni_number: 'NI Number',
    date_of_birth: 'Date of Birth',
    next_of_kin_name: 'Next of Kin Name',
    next_of_kin_relationship: 'Next of Kin Relationship',
    next_of_kin_phone: 'Next of Kin Phone',
    next_of_kin_address: 'Next of Kin Address',
    emergency_contact_name: 'Emergency Contact Name',
    emergency_contact_phone: 'Emergency Contact Phone',
    emergency_contact_relationship: 'Emergency Contact Relationship',
    reference_1_name: 'Reference 1 Name',
    reference_1_company: 'Reference 1 Company',
    reference_1_phone: 'Reference 1 Phone',
    reference_1_email: 'Reference 1 Email',
    reference_2_name: 'Reference 2 Name',
    reference_2_company: 'Reference 2 Company',
    reference_2_phone: 'Reference 2 Phone',
    reference_2_email: 'Reference 2 Email',
    has_driving_licence: 'Has Driving Licence',
    driving_licence_type: 'Driving Licence Type',
    has_own_vehicle: 'Has Own Vehicle',
    vehicle_registration: 'Vehicle Registration'
  };

  // ========== Form Submission Handlers ==========
  
  // Open form modal for a specific requirement
  const openFormModal = async (requirementId) => {
    try {
      const response = await axios.get(`${API}/form-submissions/template/${requirementId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setFormTemplate(response.data);
      
      // Check if there's an existing submission to pre-fill
      const existingResponse = await axios.get(`${API}/form-submissions?employee_id=${employeeId}&requirement_id=${requirementId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      // Get today's date in YYYY-MM-DD format for auto-fill
      const today = new Date().toISOString().split('T')[0];
      
      if (existingResponse.data && existingResponse.data.length > 0) {
        // Use existing submission data
        setFormData(existingResponse.data[0].data || {});
      } else {
        // Fetch auto-fill data from backend based on employee profile
        try {
          const autoFillResponse = await axios.get(
            `${API}/form-submissions/auto-fill/${requirementId}/${employeeId}`,
            { headers: { Authorization: `Bearer ${token}` } }
          );
          // Add today's date for signature_date if not already set
          const autoFillData = autoFillResponse.data.auto_fill_data || {};
          if (!autoFillData.signature_date) {
            autoFillData.signature_date = today;
          }
          setFormData(autoFillData);
        } catch (autoFillError) {
          // Fallback to basic employee data if auto-fill endpoint fails
          setFormData({
            employee_name: `${employee.first_name} ${employee.last_name}`,
            full_name: `${employee.first_name} ${employee.last_name}`,
            candidate_name: `${employee.first_name} ${employee.last_name}`,
            signature_date: today
          });
        }
      }
      
      setFormModalOpen(true);
    } catch (error) {
      toast.error('Failed to load form template');
    }
  };
  
  // Submit structured form
  const handleFormSubmit = async () => {
    if (!formTemplate) return;
    
    setIsSubmittingForm(true);
    try {
      await axios.post(`${API}/form-submissions`, {
        employee_id: employeeId,
        requirement_id: formTemplate.requirement_id,
        form_type: formTemplate.form_type,
        data: formData
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      toast.success(`${formTemplate.name} submitted successfully`);
      setFormModalOpen(false);
      setFormTemplate(null);
      setFormData({});
      fetchData(); // Refresh all data including compliance requirements
    } catch (error) {
      console.error('Form submission error:', error);
      toast.error(error.response?.data?.detail || 'Failed to submit form');
    } finally {
      setIsSubmittingForm(false);
    }
  };
  
  // View submitted form
  const openViewForm = (requirement) => {
    if (requirement.form_submission) {
      setViewFormData({
        ...requirement.form_submission,
        requirementName: requirement.name
      });
      setViewFormOpen(true);
    }
  };
  
  // Verify form submission
  const handleVerifyFormSubmission = async (submissionId) => {
    try {
      await axios.post(`${API}/form-submissions/${submissionId}/verify`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Form verified successfully');
      setViewFormOpen(false);
      fetchData(); // Refresh all data including compliance requirements
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to verify form');
    }
  };

  // Generate PDF from form submission (Template-Backed Forms Architecture)
  const handleGenerateFormPDF = async (submissionId, formType) => {
    setIsGenerating(true);
    try {
      const response = await axios.post(
        `${API}/form-submissions/${submissionId}/generate-pdf`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      if (response.data.file_url) {
        // Open the generated PDF in a new tab
        window.open(response.data.file_url, '_blank');
        toast.success('PDF generated successfully');
      }
    } catch (error) {
      console.error('PDF generation error:', error);
      toast.error(error.response?.data?.detail || 'Failed to generate PDF');
    } finally {
      setIsGenerating(false);
    }
  };

  // Download existing PDF export or generate new one
  const handleDownloadFormPDF = async (submissionId) => {
    try {
      // Use responseType: 'blob' to receive the actual PDF file bytes
      const response = await axios.get(
        `${API}/form-submissions/${submissionId}/download-pdf`,
        { 
          headers: { Authorization: `Bearer ${token}` },
          responseType: 'blob'
        }
      );
      
      // Extract filename from Content-Disposition header if available
      const contentDisposition = response.headers['content-disposition'];
      let filename = 'form.pdf';
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="?([^";\n]+)"?/);
        if (filenameMatch) {
          filename = filenameMatch[1];
        }
      }
      
      // Create a blob URL and trigger download
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      toast.success('PDF downloaded successfully');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to download PDF');
    }
  };

  // View PDF in a new tab
  const handleViewFormPDF = async (submissionId) => {
    try {
      // Fetch the PDF blob and open in new tab
      const response = await axios.get(
        `${API}/form-submissions/${submissionId}/view-pdf`,
        { 
          headers: { Authorization: `Bearer ${token}` },
          responseType: 'blob'
        }
      );
      
      // Create a blob URL and open in new tab
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      window.open(url, '_blank');
      
      // Note: We don't revoke immediately so the tab can load
      // The blob URL will be garbage collected when the tab closes
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to view PDF');
    }
  };

  const groupedTemplates = templates.reduce((acc, template) => {
    if (!acc[template.category]) acc[template.category] = [];
    acc[template.category].push(template);
    return acc;
  }, {});

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!employee) {
    return (
      <div className="text-center py-12">
        <p className="text-text-muted">{isRecruitmentView ? 'Applicant' : 'Employee'} not found</p>
        <Link to={isRecruitmentView ? '/portal/recruitment' : '/portal/employees'}>
          <Button className="mt-4">{isRecruitmentView ? 'Back to Recruitment Pipeline' : 'Back to Staff'}</Button>
        </Link>
      </div>
    );
  }

  const groupedDocs = documentTypes.reduce((acc, type) => {
    if (!acc[type.category]) acc[type.category] = [];
    const doc = documents.find(d => d.document_type_id === type.id);
    acc[type.category].push({ ...type, document: doc });
    return acc;
  }, {});

  return (
    <div className="space-y-6" data-testid="employee-profile">
      {/* Back Link - Returns to correct section based on route context */}
      <button 
        onClick={() => navigate(isRecruitmentView ? '/portal/recruitment' : '/portal/employees')} 
        className="inline-flex items-center gap-2 text-text-muted hover:text-primary transition-colors"
        data-testid="back-link"
      >
        <ArrowLeft className="h-4 w-4" />
        {isRecruitmentView ? 'Back to Recruitment Pipeline' : 'Back to Staff'}
      </button>

      {/* Recruitment Context Banner - Show when viewing applicant from recruitment */}
      {isRecruitmentView && employee?.person_stage === 'applicant' && (
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
              <User className="h-5 w-5 text-blue-600" />
            </div>
            <div>
              <p className="font-medium text-blue-800">Applicant Profile</p>
              <p className="text-sm text-blue-600">Review this applicant's compliance status before approval</p>
            </div>
          </div>
          <Badge variant="outline" className="bg-blue-100 text-blue-700 border-blue-300">
            Recruitment Review
          </Badge>
        </div>
      )}

      {/* Header Card */}
      <Card className="border-[#E4E8EB] shadow-sm">
        <CardContent className="p-6">
          <div className="flex flex-col lg:flex-row lg:items-start gap-6">
            <div className="flex items-start gap-4 flex-1">
              {/* Profile Photo with Upload */}
              <div className="relative group">
                {profilePhotoBlob ? (
                  <img 
                    src={profilePhotoBlob} 
                    alt={`${employee.first_name} ${employee.last_name}`}
                    className="w-16 h-16 rounded-2xl object-cover border-2 border-[#E4E8EB]"
                    data-testid="profile-photo"
                  />
                ) : (
                  <div className="w-16 h-16 bg-accent rounded-2xl flex items-center justify-center">
                    <span className="text-primary font-heading font-bold text-xl">
                      {employee.first_name?.charAt(0)}{employee.last_name?.charAt(0)}
                    </span>
                  </div>
                )}
                {/* Upload/Edit overlay */}
                {!isAuditor() && (
                  <div className="absolute inset-0 bg-black/50 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                    <label className="cursor-pointer p-2">
                      <input
                        ref={photoInputRef}
                        type="file"
                        accept="image/jpeg,image/jpg,image/png,image/webp"
                        onChange={handlePhotoUpload}
                        className="hidden"
                        disabled={isUploadingPhoto}
                      />
                      {isUploadingPhoto ? (
                        <Loader2 className="h-5 w-5 text-white animate-spin" />
                      ) : (
                        <Camera className="h-5 w-5 text-white" />
                      )}
                    </label>
                    {employee.profile_photo_url && (
                      <button
                        onClick={handleRemovePhoto}
                        className="p-2 hover:bg-white/20 rounded-lg"
                        title="Remove photo"
                      >
                        <XCircle className="h-4 w-4 text-white" />
                      </button>
                    )}
                  </div>
                )}
              </div>
              <div>
                <h1 className="font-heading text-2xl font-bold text-text-primary">
                  {employee.first_name} {employee.last_name}
                </h1>
                <p className="text-text-muted">
                  {employee.employee_code || employee.applicant_reference || 'No ID assigned'} · {employee.role}
                </p>
                <div className="flex items-center gap-2 mt-2 flex-wrap">
                  {/* Person Stage Badge - CLEAR APPLICANT VS STAFF DISTINCTION */}
                  {employee.person_stage === 'applicant' ? (
                    <span className="px-2 py-1 rounded-lg text-xs font-medium bg-blue-100 text-blue-800 border border-blue-200">
                      Applicant
                    </span>
                  ) : (
                    <span className="px-2 py-1 rounded-lg text-xs font-medium bg-green-100 text-green-800 border border-green-200">
                      Staff
                    </span>
                  )}
                  <span className={`status-chip ${
                    employee.status === 'active' ? 'status-success' :
                    employee.status === 'onboarding' ? 'status-info' :
                    employee.status === 'screening' || employee.status === 'interview' || employee.status === 'compliance_review' ? 'status-warning' :
                    'status-neutral'
                  }`}>
                    {employee.status === 'compliance_review' ? 'Awaiting Approval' : employee.status?.replace('_', ' ')}
                  </span>
                  {/* Recruitment Approval Status */}
                  {employee.recruitment_approved ? (
                    <span className="px-2 py-1 rounded-lg text-xs font-medium bg-green-100 text-green-800">
                      Recruitment Approved
                    </span>
                  ) : employee.person_stage === 'applicant' && (
                    <span className="px-2 py-1 rounded-lg text-xs font-medium bg-amber-100 text-amber-800">
                      Awaiting Approval
                    </span>
                  )}
                  {/* 3-Tier Work Readiness Status Badge */}
                  {employee.person_stage === 'employee' && (() => {
                    const workReadiness3tier = complianceRequirements?.work_readiness_3tier || {};
                    const status = workReadiness3tier.status;
                    const statusLabel = workReadiness3tier.label || 'Unknown';
                    const statusColor = workReadiness3tier.color === 'success' ? 'bg-success/10 text-success' : 
                                       workReadiness3tier.color === 'warning' ? 'bg-warning/10 text-warning' : 
                                       'bg-error/10 text-error';
                    const reasons = workReadiness3tier.reasons || [];
                    
                    return (
                      <div className="flex flex-col items-start gap-1">
                        <span className={`px-2.5 py-1 rounded-lg text-xs font-medium flex items-center gap-1.5 ${statusColor}`} data-testid="work-readiness-badge">
                          {status === 'READY_TO_WORK' ? (
                            <Shield className="h-3.5 w-3.5" />
                          ) : (
                            <AlertTriangle className="h-3.5 w-3.5" />
                          )}
                          {statusLabel}
                        </span>
                        {reasons.length > 0 && status !== 'READY_TO_WORK' && (
                          <div className="flex flex-wrap gap-1 max-w-md">
                            {reasons.slice(0, 3).map((reason, idx) => (
                              <span 
                                key={idx} 
                                className={`text-[10px] px-1.5 py-0.5 rounded ${reason.type === 'hard_block' ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'}`}
                              >
                                {reason.message}
                              </span>
                            ))}
                            {reasons.length > 3 && (
                              <span className="text-[10px] text-gray-500">+{reasons.length - 3} more</span>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })()}
                </div>
              </div>
            </div>

            <div className="flex flex-col items-end gap-4">
              <div className="flex items-center gap-3">
                <div className="text-right">
                  <p className="text-sm text-text-muted">Progress</p>
                  {/* Use single source of truth from complianceRequirements */}
                  <p className="text-3xl font-heading font-bold text-text-primary">
                    {complianceRequirements?.statuses?.overall_compliance?.percentage ?? employee.completion_percentage ?? 0}% Complete
                  </p>
                </div>
                {!isAuditor() && (
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="outline" size="sm" className="h-10 w-10 p-0 rounded-xl" data-testid="employee-actions-btn">
                        <MoreHorizontal className="h-5 w-5" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end" className="w-56">
                      <DropdownMenuItem onClick={openEditDialog}>
                        <Edit className="h-4 w-4 mr-2" />
                        Edit Details
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={handleRefreshStatus} disabled={isRefreshingStatus}>
                        <RefreshCw className={`h-4 w-4 mr-2 ${isRefreshingStatus ? 'animate-spin' : ''}`} />
                        Refresh Status
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem onClick={handleExportFile} disabled={isExporting}>
                        <FileArchive className="h-4 w-4 mr-2" />
                        Export Employee File (ZIP)
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={handleExportCompliancePDF} disabled={isExporting} data-testid="download-compliance-pdf-btn">
                        <FileDown className="h-4 w-4 mr-2" />
                        Download Compliance PDF
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={handlePrintCompliancePDF} data-testid="print-compliance-pdf-btn">
                        <Printer className="h-4 w-4 mr-2" />
                        Print Compliance PDF
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                      {employee.status === 'archived' ? (
                        <DropdownMenuItem onClick={handleRestoreEmployee}>
                          <RotateCcw className="h-4 w-4 mr-2" />
                          Restore Employee
                        </DropdownMenuItem>
                      ) : (
                        <DropdownMenuItem 
                          onClick={() => setArchiveDialogOpen(true)}
                          className="text-warning"
                        >
                          <Archive className="h-4 w-4 mr-2" />
                          Archive Employee
                        </DropdownMenuItem>
                      )}
                      {isSuperAdmin() && (
                        <>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem 
                            onClick={() => setDeleteDialogOpen(true)}
                            className="text-error"
                          >
                            <Trash2 className="h-4 w-4 mr-2" />
                            Delete Permanently
                          </DropdownMenuItem>
                        </>
                      )}
                    </DropdownMenuContent>
                  </DropdownMenu>
                )}
              </div>
              <Progress 
                value={complianceRequirements?.statuses?.overall_compliance?.percentage ?? employee.completion_percentage ?? 0} 
                className="w-32 h-2" 
              />
            </div>
          </div>

          {/* AUDIT QUICK VIEW - Key compliance items at a glance */}
          {(() => {
            // Extract key compliance data for audit visibility
            const reqs = complianceRequirements?.requirements || [];
            
            // SAFETY ENGINES - USE COMPUTED DATA FROM API (single source of truth)
            const rtwSummary = complianceRequirements?.rtw_summary || {};
            const dbsSummary = complianceRequirements?.dbs_summary || {};
            const trainingSummary = complianceRequirements?.training_summary || {};
            const safetyStatus = complianceRequirements?.safety_status || {};
            
            // Calculate missing items (no evidence)
            const missingItems = reqs.filter(r => !r.has_evidence && r.requirement_type !== 'conditional').length;
            
            // Calculate pending review (has evidence but not verified)
            const pendingReview = reqs.filter(r => r.has_evidence && !r.verified).length;
            
            // Safety engine blocking status
            const isBlocking = safetyStatus.is_safe_to_deploy === false;
            const blockingReasons = complianceRequirements?.statuses?.safety_blocking_reasons || [];
            
            // DBS info from safety engine
            const dbsExpiry = dbsSummary.review_due_date || dbsSummary.next_dbs_review_due;
            const dbsExpiryDays = dbsSummary.days_remaining;
            const dbsBlocking = dbsSummary.is_blocking;
            
            // RTW info from safety engine
            const rtwExpiry = rtwSummary.expiry_date;
            const rtwExpiryDays = rtwSummary.days_remaining;
            const rtwBlocking = rtwSummary.is_blocking;
            
            // Training info from safety engine
            const trainingBlocking = trainingSummary.is_blocking;
            
            // Category breakdown
            const categoryStats = {};
            reqs.forEach(r => {
              const cat = r.category || 'Other';
              if (!categoryStats[cat]) {
                categoryStats[cat] = { total: 0, complete: 0, verified: 0 };
              }
              categoryStats[cat].total += 1;
              if (r.has_evidence) categoryStats[cat].complete += 1;
              if (r.verified) categoryStats[cat].verified += 1;
            });
            
            // Map categories to display names
            const categoryDisplayNames = {
              '1_Legal_Safety': 'Legal & Safety',
              '2_Core_Training': 'Training',
              '3_Competency_Health': 'Health',
              '4_Recruitment_Record': 'Recruitment',
              '5_Agreements': 'Agreements',
              '6_Admin': 'Admin'
            };
            
            return (
              <div className="mt-6 pt-6 border-t border-[#E4E8EB]">
                {/* Audit Quick View Header */}
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider">Audit Quick View</h3>
                  <p className="text-xs text-text-muted">Key compliance items for checker review</p>
                </div>
                
                {/* Quick Status Cards - 4 cards */}
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-3" data-testid="audit-quick-view">
                  {/* DBS Status with Expiry */}
                  <div className={`p-3 rounded-xl border ${
                    dbsBlocking || dbsSummary.dbs_status_color === 'red' ? 'border-red-200 bg-red-50' :
                    dbsSummary.status_band === 'urgent' || dbsSummary.status_band === 'due_soon' ? 'border-amber-200 bg-amber-50' :
                    dbsSummary.dbs_status_color === 'green' ? 'border-green-200 bg-green-50' : 'border-blue-200 bg-blue-50'
                  }`} data-testid="dbs-status-card">
                    <div className="flex items-center gap-2 mb-1">
                      <Shield className={`h-4 w-4 ${
                        dbsBlocking || dbsSummary.dbs_status_color === 'red' ? 'text-red-600' :
                        dbsSummary.status_band === 'urgent' || dbsSummary.status_band === 'due_soon' ? 'text-amber-600' :
                        dbsSummary.dbs_status_color === 'green' ? 'text-green-600' : 'text-blue-600'
                      }`} />
                      <span className="text-xs font-semibold text-text-primary">DBS</span>
                      {dbsBlocking && <span className="text-xs px-1 py-0.5 bg-red-600 text-white rounded">BLOCKED</span>}
                    </div>
                    <p className={`text-sm font-medium ${
                      dbsBlocking || dbsSummary.dbs_status_color === 'red' ? 'text-red-700' :
                      dbsSummary.status_band === 'urgent' || dbsSummary.status_band === 'due_soon' ? 'text-amber-700' :
                      dbsSummary.dbs_status_color === 'green' ? 'text-green-700' : 'text-blue-700'
                    }`}>
                      {dbsSummary.dbs_status_label || 'Unknown'}
                    </p>
                    {dbsExpiry && (
                      <p className={`text-xs mt-1 ${
                        dbsExpiryDays !== null && dbsExpiryDays < 0 ? 'text-red-600 font-medium' :
                        dbsSummary.status_band === 'urgent' ? 'text-amber-600 font-medium' : 'text-text-muted'
                      }`}>
                        {dbsExpiryDays !== null && dbsExpiryDays < 0 ? 'Overdue: ' : 'Review: '}
                        {formatBackendDate(dbsExpiry)}
                        {dbsExpiryDays !== null && dbsExpiryDays > 0 && dbsExpiryDays <= 60 && (
                          <span className="ml-1">({dbsExpiryDays}d)</span>
                        )}
                      </p>
                    )}
                  </div>
                  
                  {/* RTW Status with Expiry - Dynamic logic based on verification + expiry */}
                  <div className={`p-3 rounded-xl border ${
                    rtwSummary.rtw_status_color === 'red' || rtwSummary.status_band === 'expired' ? 'border-red-200 bg-red-50' :
                    rtwSummary.rtw_status_color === 'amber' || rtwSummary.status_band === 'urgent' || rtwSummary.status_band === 'due_soon' ? 'border-amber-200 bg-amber-50' :
                    rtwSummary.rtw_status_color === 'green' ? 'border-green-200 bg-green-50' : 
                    rtwSummary.rtw_status_color === 'gray' || !rtwSummary.is_verified ? 'border-gray-200 bg-gray-50' : 
                    'border-blue-200 bg-blue-50'
                  }`} data-testid="rtw-status-card">
                    <div className="flex items-center gap-2 mb-1">
                      <FileCheck className={`h-4 w-4 ${
                        rtwSummary.rtw_status_color === 'red' || rtwSummary.status_band === 'expired' ? 'text-red-600' :
                        rtwSummary.rtw_status_color === 'amber' ? 'text-amber-600' :
                        rtwSummary.rtw_status_color === 'green' ? 'text-green-600' : 
                        rtwSummary.rtw_status_color === 'gray' || !rtwSummary.is_verified ? 'text-gray-500' :
                        'text-blue-600'
                      }`} />
                      <span className="text-xs font-semibold text-text-primary">Right to Work</span>
                    </div>
                    
                    {/* Dynamic Status Display - No contradictions */}
                    {!rtwSummary.is_verified ? (
                      // Not verified = MISSING
                      <p className="text-sm font-semibold text-gray-700">MISSING</p>
                    ) : rtwSummary.status_band === 'expired' || rtwSummary.rtw_status_color === 'red' ? (
                      // Expired
                      <p className="text-sm font-semibold text-red-700">
                        EXPIRED • Not valid to work
                      </p>
                    ) : rtwSummary.is_indefinite || rtwSummary.permission_type === 'permanent' ? (
                      // Verified + No expiry
                      <p className="text-sm font-semibold text-green-700">
                        VERIFIED • No Expiry
                      </p>
                    ) : rtwExpiry ? (
                      // Verified + Has expiry
                      <p className={`text-sm font-semibold ${
                        rtwSummary.status_band === 'urgent' ? 'text-amber-700' : 'text-green-700'
                      }`}>
                        VERIFIED • Expires {formatBackendDate(rtwExpiry)}
                      </p>
                    ) : (
                      // Verified but no expiry info
                      <p className="text-sm font-semibold text-green-700">VERIFIED</p>
                    )}
                    
                    {/* Days countdown for expiring */}
                    {rtwSummary.is_verified && rtwExpiry && rtwExpiryDays !== undefined && rtwExpiryDays !== null && (
                      <p className={`text-xs mt-1 font-medium ${
                        rtwExpiryDays < 0 ? 'text-red-600' :
                        rtwExpiryDays <= 30 ? 'text-red-600' :
                        rtwExpiryDays <= 90 ? 'text-amber-600' : 'text-text-muted'
                      }`}>
                        {rtwExpiryDays < 0 ? `${Math.abs(rtwExpiryDays)} days overdue` :
                         rtwExpiryDays === 0 ? 'Expires today' :
                         `${rtwExpiryDays} days remaining`}
                      </p>
                    )}
                  </div>
                  
                  {/* Alerts Card - Show blocking status prominently */}
                  <div className={`p-3 rounded-xl border ${
                    isBlocking ? 'border-red-200 bg-red-50' :
                    (missingItems > 0 || pendingReview > 0) ? 'border-amber-200 bg-amber-50' : 
                    'border-green-200 bg-green-50'
                  }`} data-testid="alerts-card">
                    <div className="flex items-center gap-2 mb-1">
                      <AlertTriangle className={`h-4 w-4 ${
                        isBlocking ? 'text-red-600' :
                        (missingItems > 0 || pendingReview > 0) ? 'text-amber-600' : 'text-green-600'
                      }`} />
                      <span className="text-xs font-semibold text-text-primary">
                        {isBlocking ? 'BLOCKED' : 'Alerts'}
                      </span>
                    </div>
                    {isBlocking ? (
                      <div className="space-y-0.5">
                        <p className="text-xs text-red-700 font-semibold">Not Work Ready</p>
                        {blockingReasons.slice(0, 2).map((reason, idx) => (
                          <p key={idx} className="text-xs text-red-600 line-clamp-1" title={reason}>
                            {reason?.split(' - ')[0] || reason}
                          </p>
                        ))}
                      </div>
                    ) : (missingItems > 0 || pendingReview > 0) ? (
                      <div className="space-y-0.5">
                        {missingItems > 0 && (
                          <p className="text-xs text-amber-700">{missingItems} missing</p>
                        )}
                        {pendingReview > 0 && (
                          <p className="text-xs text-amber-700">{pendingReview} pending</p>
                        )}
                      </div>
                    ) : (
                      <p className="text-sm font-medium text-green-700">Work Ready</p>
                    )}
                  </div>
                  
                  {/* Compliance Breakdown Card */}
                  <div className="p-3 rounded-xl border border-slate-200 bg-slate-50" data-testid="compliance-breakdown-card">
                    <div className="flex items-center gap-2 mb-2">
                      <ClipboardList className="h-4 w-4 text-slate-600" />
                      <span className="text-xs font-semibold text-text-primary">Breakdown</span>
                    </div>
                    <div className="grid grid-cols-2 gap-x-3 gap-y-1">
                      {Object.entries(categoryStats)
                        .sort(([a], [b]) => a.localeCompare(b))
                        .slice(0, 4) // Show top 4 categories
                        .map(([cat, stats]) => {
                          const displayName = categoryDisplayNames[cat] || cat.replace(/^\d+_/, '').replace(/_/g, ' ');
                          const isComplete = stats.complete === stats.total;
                          return (
                            <div key={cat} className="flex items-center justify-between">
                              <span className="text-xs text-text-muted truncate">{displayName}</span>
                              <span className={`text-xs font-medium ${isComplete ? 'text-green-600' : 'text-amber-600'}`}>
                                {stats.complete}/{stats.total}
                              </span>
                            </div>
                          );
                        })}
                    </div>
                  </div>
                </div>
              </div>
            );
          })()}

          {/* Status Strip - Replaces contact row */}
          <div className="flex flex-wrap items-center gap-4 mt-4 pt-4 border-t border-[#E4E8EB]" data-testid="status-strip">
            {/* Employee ID - Always show business-facing code (OCS-XXXX), never internal UUID */}
            <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-100 rounded-lg">
              <User className="h-4 w-4 text-slate-500" />
              <span className="text-sm text-slate-500">Employee ID:</span>
              <span className="text-sm font-semibold text-slate-700">{employee.employee_code || employee.applicant_reference || 'Not assigned'}</span>
            </div>
            
            {/* Missing Items */}
            {(() => {
              const reqs = complianceRequirements?.requirements || [];
              const missing = reqs.filter(r => !r.has_evidence && r.requirement_type !== 'conditional').length;
              if (missing > 0) {
                return (
                  <div className="flex items-center gap-2 px-3 py-1.5 bg-red-100 rounded-lg">
                    <XCircle className="h-4 w-4 text-red-600" />
                    <span className="text-sm font-medium text-red-700">{missing} Missing</span>
                  </div>
                );
              }
              return null;
            })()}
            
            {/* Pending Review */}
            {(() => {
              const reqs = complianceRequirements?.requirements || [];
              const pending = reqs.filter(r => r.has_evidence && !r.verified).length;
              if (pending > 0) {
                return (
                  <div className="flex items-center gap-2 px-3 py-1.5 bg-amber-100 rounded-lg">
                    <Clock className="h-4 w-4 text-amber-600" />
                    <span className="text-sm font-medium text-amber-700">{pending} Pending Review</span>
                  </div>
                );
              }
              return null;
            })()}
            
            {/* Key Expiry - Show most critical */}
            {(() => {
              const dbsSummary = complianceRequirements?.dbs_summary || {};
              const rtwSummary = complianceRequirements?.rtw_summary || {};
              
              // Check RTW expiry first (more critical)
              if (rtwSummary.expiry_date) {
                const days = rtwSummary.days_until_expiry;
                if (days !== undefined && days <= 30) {
                  return (
                    <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg ${
                      days <= 0 ? 'bg-red-100' : 'bg-amber-100'
                    }`}>
                      <Calendar className={`h-4 w-4 ${days <= 0 ? 'text-red-600' : 'text-amber-600'}`} />
                      <span className={`text-sm font-medium ${days <= 0 ? 'text-red-700' : 'text-amber-700'}`}>
                        RTW {days <= 0 ? 'Expired' : `Expires ${days}d`}
                      </span>
                    </div>
                  );
                }
              }
              
              // Check DBS expiry - HARDENING: Use backend-provided days if available
              if (dbsSummary.next_dbs_review_due) {
                // Prefer backend-computed days_until_review, fallback to safe local calc
                const days = dbsSummary.days_until_review ?? Math.ceil((parseBackendDate(dbsSummary.next_dbs_review_due) - new Date()) / (1000 * 60 * 60 * 24));
                if (days <= 30) {
                  return (
                    <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg ${
                      days <= 0 ? 'bg-red-100' : 'bg-amber-100'
                    }`}>
                      <Calendar className={`h-4 w-4 ${days <= 0 ? 'text-red-600' : 'text-amber-600'}`} />
                      <span className={`text-sm font-medium ${days <= 0 ? 'text-red-700' : 'text-amber-700'}`}>
                        DBS {days <= 0 ? 'Overdue' : `Review ${days}d`}
                      </span>
                    </div>
                  );
                }
              }
              
              return null;
            })()}
            
            {/* All Clear badge if no issues */}
            {(() => {
              const reqs = complianceRequirements?.requirements || [];
              const missing = reqs.filter(r => !r.has_evidence && r.requirement_type !== 'conditional').length;
              const pending = reqs.filter(r => r.has_evidence && !r.verified).length;
              
              if (missing === 0 && pending === 0) {
                return (
                  <div className="flex items-center gap-2 px-3 py-1.5 bg-green-100 rounded-lg">
                    <CheckCircle className="h-4 w-4 text-green-600" />
                    <span className="text-sm font-medium text-green-700">All Verified</span>
                  </div>
                );
              }
              return null;
            })()}
          </div>

          {/* Note: Global Upload Document button removed. */}
          {/* All upload actions now live INSIDE each compliance requirement card. */}
          {/* Workflow: See issue → Scroll to section → Upload/Request/Verify there. */}

          {!isAuditor() && (
            <div className="flex flex-wrap gap-3 mt-6">
              {/* Generate Blank Forms Dialog */}
              <Dialog open={generateFormsOpen} onOpenChange={setGenerateFormsOpen}>
                <DialogContent className="max-w-2xl max-h-[80vh] overflow-hidden flex flex-col bg-white">
                  <DialogHeader>
                    <DialogTitle className="font-heading">Generate Compliance Forms</DialogTitle>
                  </DialogHeader>
                  <div className="space-y-4 mt-4 overflow-y-auto flex-1 pr-2">
                    <p className="text-sm text-text-muted">
                      Select templates to generate for <strong>{employee?.first_name} {employee?.last_name}</strong>. 
                      Employee details will be auto-filled.
                    </p>
                    
                    {templates.length === 0 ? (
                      <div className="text-center py-8 text-text-muted">
                        <ClipboardList className="h-10 w-10 mx-auto mb-2 opacity-50" />
                        <p>No templates available. Load templates first.</p>
                      </div>
                    ) : (
                      <div className="space-y-4">
                        {Object.entries(groupedTemplates).map(([category, categoryTemplates]) => (
                          <div key={category} className="space-y-2">
                            <h4 className="font-medium text-text-primary text-sm">{category}</h4>
                            <div className="space-y-2">
                              {categoryTemplates.map((template) => {
                                const existingForm = generatedForms.find(
                                  f => f.template_id === template.id && !['archived', 'signed_off'].includes(f.status)
                                );
                                const isSelected = selectedTemplates.includes(template.id);
                                
                                return (
                                  <div 
                                    key={template.id}
                                    className={`flex items-start gap-3 p-3 rounded-xl border transition-colors ${
                                      existingForm 
                                        ? 'bg-gray-50 border-gray-200 opacity-60' 
                                        : isSelected 
                                          ? 'bg-primary/5 border-primary' 
                                          : 'bg-[#F8FAFA] border-[#E4E8EB] hover:border-primary/30'
                                    }`}
                                  >
                                    <Checkbox
                                      id={template.id}
                                      checked={isSelected}
                                      disabled={!!existingForm}
                                      onCheckedChange={() => toggleTemplateSelection(template.id)}
                                    />
                                    <div className="flex-1 min-w-0">
                                      <label 
                                        htmlFor={template.id}
                                        className={`text-sm font-medium cursor-pointer ${existingForm ? 'text-text-muted' : 'text-text-primary'}`}
                                      >
                                        {template.name}
                                      </label>
                                      {template.description && (
                                        <p className="text-xs text-text-muted mt-0.5 line-clamp-1">{template.description}</p>
                                      )}
                                      {existingForm && (
                                        <div className="flex items-center gap-2 mt-1">
                                          <span className="text-xs text-warning">Form exists ({existingForm.status})</span>
                                          <Button
                                            size="sm"
                                            variant="ghost"
                                            className="h-6 px-2 text-xs"
                                            onClick={() => navigate(`/portal/forms/${existingForm.id}`)}
                                          >
                                            <Eye className="h-3 w-3 mr-1" />
                                            View
                                          </Button>
                                        </div>
                                      )}
                                    </div>
                                    <div className="flex gap-1">
                                      {template.requires_employee_signature && (
                                        <span className="text-xs bg-accent text-primary px-2 py-0.5 rounded">Emp Sign</span>
                                      )}
                                      {template.requires_admin_signature && (
                                        <span className="text-xs bg-secondary/10 text-secondary px-2 py-0.5 rounded">Admin Sign</span>
                                      )}
                                    </div>
                                  </div>
                                );
                              })}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                  
                  <div className="flex justify-between items-center gap-3 pt-4 border-t border-[#E4E8EB] mt-4">
                    <span className="text-sm text-text-muted">
                      {selectedTemplates.length} template{selectedTemplates.length !== 1 ? 's' : ''} selected
                    </span>
                    <div className="flex gap-3">
                      <Button type="button" variant="outline" onClick={() => setGenerateFormsOpen(false)} className="rounded-xl">
                        Cancel
                      </Button>
                      <Button 
                        onClick={handleGenerateForms}
                        disabled={isGenerating || selectedTemplates.length === 0}
                        className="bg-primary hover:bg-primary-hover text-white rounded-xl"
                        data-testid="generate-forms-submit"
                      >
                        {isGenerating ? <Loader2 className="h-4 w-4 animate-spin" /> : `Generate ${selectedTemplates.length} Forms`}
                      </Button>
                    </div>
                  </div>
                </DialogContent>
              </Dialog>

              {/* Import Existing Application Dialog */}
              <Dialog open={importAppOpen} onOpenChange={setImportAppOpen}>
                <DialogContent className="max-w-lg bg-white">
                  <DialogHeader>
                    <DialogTitle className="font-heading">Create from Existing Application</DialogTitle>
                    <DialogDescription>
                      Upload a completed application form and optionally a CV. The form will be stored as uploaded evidence and linked to the employee's compliance checklist.
                    </DialogDescription>
                  </DialogHeader>
                  <div className="space-y-4 mt-4">
                    <div className="space-y-2">
                      <Label className="text-sm font-medium">
                        Application Form <span className="text-red-500">*</span>
                      </Label>
                      <FileUploaderInline
                        onFileSelect={(file) => setImportAppFile(file)}
                        selectedFile={importAppFile}
                        onClear={() => setImportAppFile(null)}
                        acceptedTypes={['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']}
                        placeholder="Drop application form here or click to browse"
                      />
                    </div>

                    <div className="space-y-2">
                      <Label className="text-sm font-medium">
                        CV / Resume <span className="text-text-muted">(optional)</span>
                      </Label>
                      <FileUploaderInline
                        onFileSelect={(file) => setImportCvFile(file)}
                        selectedFile={importCvFile}
                        onClear={() => setImportCvFile(null)}
                        acceptedTypes={['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']}
                        placeholder="Drop CV here or click to browse"
                      />
                    </div>

                    <div className="bg-[#F8FAFA] rounded-xl p-4 space-y-2">
                      <h4 className="text-sm font-medium text-text-primary">What happens next:</h4>
                      <ul className="text-xs text-text-muted space-y-1">
                        <li className="flex items-start gap-2">
                          <CheckCircle className="h-3.5 w-3.5 text-green-500 mt-0.5 shrink-0" />
                          Application Form marked as "Completed (Imported)"
                        </li>
                        <li className="flex items-start gap-2">
                          <CheckCircle className="h-3.5 w-3.5 text-green-500 mt-0.5 shrink-0" />
                          Document stored in employee's A_Application folder
                        </li>
                        <li className="flex items-start gap-2">
                          <CheckCircle className="h-3.5 w-3.5 text-green-500 mt-0.5 shrink-0" />
                          Checklist item evidence uploaded automatically
                        </li>
                        <li className="flex items-start gap-2">
                          <CheckCircle className="h-3.5 w-3.5 text-green-500 mt-0.5 shrink-0" />
                          Form fields locked (read-only) unless manually edited
                        </li>
                      </ul>
                    </div>
                  </div>

                  <div className="flex justify-end gap-3 pt-4 border-t border-[#E4E8EB] mt-4">
                    <Button 
                      variant="outline" 
                      onClick={() => { setImportAppOpen(false); setImportAppFile(null); setImportCvFile(null); }} 
                      className="rounded-xl"
                    >
                      Cancel
                    </Button>
                    <Button 
                      onClick={handleImportApplication}
                      disabled={isImporting || !importAppFile}
                      className="bg-primary hover:bg-primary-hover text-white rounded-xl"
                      data-testid="import-application-submit"
                    >
                      {isImporting ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Import Application'}
                    </Button>
                  </div>
                </DialogContent>
              </Dialog>

              {/* Import Other Document Dialog (Reference, Health Screening, Contract) */}
              <Dialog open={importDocOpen} onOpenChange={setImportDocOpen}>
                <DialogContent className="max-w-lg bg-white">
                  <DialogHeader>
                    <DialogTitle className="font-heading">Import Existing Document</DialogTitle>
                    <DialogDescription>
                      Upload an existing completed document (Reference letter, Health form, Contract, etc.) to add evidence to the corresponding compliance requirement.
                    </DialogDescription>
                  </DialogHeader>
                  <div className="space-y-4 mt-4">
                    <div className="space-y-2">
                      <Label className="text-sm font-medium">
                        Document Type <span className="text-red-500">*</span>
                      </Label>
                      <Select value={importDocType} onValueChange={setImportDocType}>
                        <SelectTrigger className="rounded-xl" data-testid="import-doc-type-select">
                          <SelectValue placeholder="Select document type" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="recruitment_checklist">
                            <div className="flex items-center gap-2">
                              <span className="w-2 h-2 rounded-full bg-primary" />
                              Recruitment Compliance Checklist
                            </div>
                          </SelectItem>
                          <SelectItem value="personal_info">
                            <div className="flex items-center gap-2">
                              <span className="w-2 h-2 rounded-full bg-info" />
                              Personal Information Form
                            </div>
                          </SelectItem>
                          <SelectItem value="interview_record">
                            <div className="flex items-center gap-2">
                              <span className="w-2 h-2 rounded-full bg-primary" />
                              Interview Record Form
                            </div>
                          </SelectItem>
                          <SelectItem value="equal_opportunities">
                            <div className="flex items-center gap-2">
                              <span className="w-2 h-2 rounded-full bg-success" />
                              Equal Opportunities Monitoring
                            </div>
                          </SelectItem>
                          <SelectItem value="reference_1">
                            <div className="flex items-center gap-2">
                              <span className="w-2 h-2 rounded-full bg-warning" />
                              Reference 1
                            </div>
                          </SelectItem>
                          <SelectItem value="reference_2">
                            <div className="flex items-center gap-2">
                              <span className="w-2 h-2 rounded-full bg-warning" />
                              Reference 2
                            </div>
                          </SelectItem>
                          <SelectItem value="health_screening">
                            <div className="flex items-center gap-2">
                              <span className="w-2 h-2 rounded-full bg-info" />
                              Health Screening Questionnaire
                            </div>
                          </SelectItem>
                          <SelectItem value="contract">
                            <div className="flex items-center gap-2">
                              <span className="w-2 h-2 rounded-full bg-success" />
                              Contract / Offer Letter
                            </div>
                          </SelectItem>
                          <SelectItem value="induction">
                            <div className="flex items-center gap-2">
                              <span className="w-2 h-2 rounded-full bg-primary" />
                              Induction & Competency
                            </div>
                          </SelectItem>
                          <SelectItem value="handbook">
                            <div className="flex items-center gap-2">
                              <span className="w-2 h-2 rounded-full bg-gray-400" />
                              Employee Handbook Acknowledgement
                            </div>
                          </SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="space-y-2">
                      <Label className="text-sm font-medium">
                        Document File <span className="text-red-500">*</span>
                      </Label>
                      <FileUploaderInline
                        onFileSelect={(file) => setImportDocFile(file)}
                        selectedFile={importDocFile}
                        onClear={() => setImportDocFile(null)}
                        acceptedTypes={['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'image/jpeg', 'image/jpg', 'image/png']}
                        placeholder="Drop document here or click to browse"
                      />
                    </div>

                    <div className="space-y-2">
                      <Label className="text-sm font-medium">
                        Notes <span className="text-text-muted">(optional)</span>
                      </Label>
                      <Textarea 
                        value={importDocNotes}
                        onChange={(e) => setImportDocNotes(e.target.value)}
                        placeholder="e.g., Reference from John Smith, previous employer at ABC Company"
                        className="rounded-xl resize-none"
                        rows={2}
                      />
                    </div>

                    <div className="bg-[#F8FAFA] rounded-xl p-4 space-y-2">
                      <h4 className="text-sm font-medium text-text-primary">What happens:</h4>
                      <ul className="text-xs text-text-muted space-y-1">
                        <li className="flex items-start gap-2">
                          <CheckCircle className="h-3.5 w-3.5 text-green-500 mt-0.5 shrink-0" />
                          Form marked as "Completed (Imported)"
                        </li>
                        <li className="flex items-start gap-2">
                          <CheckCircle className="h-3.5 w-3.5 text-green-500 mt-0.5 shrink-0" />
                          Document stored in employee's compliance folder
                        </li>
                        <li className="flex items-start gap-2">
                          <CheckCircle className="h-3.5 w-3.5 text-green-500 mt-0.5 shrink-0" />
                          Checklist requirement evidence uploaded
                        </li>
                        <li className="flex items-start gap-2">
                          <CheckCircle className="h-3.5 w-3.5 text-green-500 mt-0.5 shrink-0" />
                          Ready for verification
                        </li>
                      </ul>
                    </div>
                  </div>

                  <div className="flex justify-end gap-3 pt-4 border-t border-[#E4E8EB] mt-4">
                    <Button 
                      variant="outline" 
                      onClick={() => { setImportDocOpen(false); setImportDocType(''); setImportDocFile(null); setImportDocNotes(''); }} 
                      className="rounded-xl"
                    >
                      Cancel
                    </Button>
                    <Button 
                      onClick={handleImportDocument}
                      disabled={isImporting || !importDocFile || !importDocType}
                      className="bg-primary hover:bg-primary-hover text-white rounded-xl"
                      data-testid="import-document-submit"
                    >
                      {isImporting ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Import Document'}
                    </Button>
                  </div>
                </DialogContent>
              </Dialog>
            </div>
          )}
        </CardContent>
      </Card>

      {/* RECRUITMENT APPROVAL PANEL - Show for applicants before tabs */}
      {employee?.person_stage === 'applicant' && !employee?.recruitment_approved && (
        <>
          {/* Next Steps Panel REMOVED - All actions now inside compliance requirement cards */}
          
          <div className="mb-6">
            <RecruitmentApprovalPanel
            employeeId={employee.id}
            employeeName={`${employee.first_name} ${employee.last_name}`}
            role={employee.role}
            stageIdentity={employee.person_stage}
            onApprovalSuccess={(result) => {
              // Refresh employee data
              toast.success(`${employee.first_name} ${employee.last_name} has been approved for recruitment!`);
              // Update local state
              setEmployee(prev => ({
                ...prev,
                recruitment_approved: true,
                status: 'onboarding',
                employee_code: result.employee_code,
                person_stage: 'employee'
              }));
              // Navigate to employee view
              navigate(`/portal/employees/${employee.id}`);
            }}
            onNavigateToRequirement={(requirementKey, section) => {
              // Navigate to compliance tab
              setActiveTab('checklist');
              toast.info(`Navigate to: ${requirementKey.replace(/_/g, ' ').replace(/\\b\\w/g, c => c.toUpperCase())}`);
            }}
          />
          </div>
        </>
      )}

      {/* WORK READINESS PANEL (GATE 2) - Show for approved employees */}
      {employee?.recruitment_approved && (
        <div className="mb-6">
          <WorkReadinessPanel
            employeeId={employee.id}
            employeeName={`${employee.first_name} ${employee.last_name}`}
            role={employee.role}
            stageIdentity={employee.person_stage}
            recruitmentApproved={employee.recruitment_approved}
            onNavigateToRequirement={(requirementKey, section) => {
              // Navigate to compliance or training tab based on section
              if (section === 'training') {
                setActiveTab('training');
              } else {
                setActiveTab('checklist');
              }
              toast.info(`Navigate to: ${requirementKey.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}`);
            }}
          />
        </div>
      )}

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={handleTabChange} className="space-y-6">
        <TabsList className="bg-white border border-[#E4E8EB] p-1 rounded-xl flex-wrap">
          <TabsTrigger value="overview" className="rounded-lg data-[state=active]:bg-primary data-[state=active]:text-white">
            <User className="h-4 w-4 mr-2" />
            Overview
          </TabsTrigger>
          <TabsTrigger value="checklist" className="rounded-lg data-[state=active]:bg-primary data-[state=active]:text-white">
            <CheckCircle className="h-4 w-4 mr-2" />
            Compliance
          </TabsTrigger>
          <TabsTrigger value="references" className="rounded-lg data-[state=active]:bg-primary data-[state=active]:text-white">
            <UserCheck className="h-4 w-4 mr-2" />
            References
          </TabsTrigger>
          <TabsTrigger value="training" className="rounded-lg data-[state=active]:bg-primary data-[state=active]:text-white">
            <GraduationCap className="h-4 w-4 mr-2" />
            Training
          </TabsTrigger>
          <TabsTrigger value="policies" className="rounded-lg data-[state=active]:bg-primary data-[state=active]:text-white">
            <FileCheck className="h-4 w-4 mr-2" />
            Policies
          </TabsTrigger>
          <TabsTrigger value="audit" className="rounded-lg data-[state=active]:bg-primary data-[state=active]:text-white">
            <History className="h-4 w-4 mr-2" />
            Audit
          </TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview">
          <div className="grid lg:grid-cols-2 gap-6">
            <Card className="border-[#E4E8EB] shadow-sm">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="font-heading text-lg">Personal Details</CardTitle>
                  {!isAuditor() && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleExtractFromApplication}
                      disabled={isExtracting}
                      className="text-xs"
                      data-testid="extract-from-app-btn"
                    >
                      {isExtracting ? (
                        <><Loader2 className="h-3 w-3 animate-spin mr-1" /> Extracting...</>
                      ) : (
                        <><FileText className="h-3 w-3 mr-1" /> Extract from App Form</>
                      )}
                    </Button>
                  )}
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-text-muted">Full Name</p>
                    <p className="font-medium text-text-primary">{employee.first_name} {employee.last_name}</p>
                  </div>
                  <div>
                    <p className="text-sm text-text-muted">
                      {employee.person_stage === 'applicant' ? 'Applicant Reference' : 'Employee ID'}
                    </p>
                    <p className="font-medium text-text-primary">
                      {employee.employee_code || employee.applicant_reference || 'Not assigned'}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-text-muted">Role</p>
                    <p className="font-medium text-text-primary">{employee.role}</p>
                  </div>
                  <div>
                    <p className="text-sm text-text-muted">Onboarding Status</p>
                    <p className="font-medium text-text-primary">{employee.onboarding_status || 'New'}</p>
                  </div>
                  <div>
                    <p className="text-sm text-text-muted">Email</p>
                    <p className="font-medium text-text-primary">{employee.email}</p>
                  </div>
                  <div>
                    <p className="text-sm text-text-muted">Phone</p>
                    <p className="font-medium text-text-primary">{employee.phone || 'Not provided'}</p>
                  </div>
                  {employee.ni_number && (
                    <div>
                      <p className="text-sm text-text-muted">NI Number</p>
                      <p className="font-medium text-text-primary">{employee.ni_number}</p>
                    </div>
                  )}
                  {employee.date_of_birth && (
                    <div>
                      <p className="text-sm text-text-muted">Date of Birth</p>
                      <p className="font-medium text-text-primary">{employee.date_of_birth}</p>
                    </div>
                  )}
                </div>
                
                {/* Address Section */}
                {(employee.address_line_1 || employee.city || employee.postcode) && (
                  <div className="pt-3 border-t border-gray-100">
                    <p className="text-sm text-text-muted mb-1">Address</p>
                    <p className="font-medium text-text-primary">
                      {[employee.address_line_1, employee.address_line_2, employee.city, employee.county, employee.postcode, employee.country]
                        .filter(Boolean)
                        .join(', ')}
                    </p>
                  </div>
                )}
                
                {/* Emergency Contact Section */}
                {(employee.next_of_kin_name || employee.emergency_contact_name) && (
                  <div className="pt-3 border-t border-gray-100">
                    <p className="text-sm text-text-muted mb-1">Emergency Contact / Next of Kin</p>
                    {employee.next_of_kin_name && (
                      <p className="font-medium text-text-primary text-sm">
                        {employee.next_of_kin_name} {employee.next_of_kin_relationship && `(${employee.next_of_kin_relationship})`}
                        {employee.next_of_kin_phone && ` - ${employee.next_of_kin_phone}`}
                      </p>
                    )}
                    {employee.emergency_contact_name && !employee.next_of_kin_name && (
                      <p className="font-medium text-text-primary text-sm">
                        {employee.emergency_contact_name} {employee.emergency_contact_relationship && `(${employee.emergency_contact_relationship})`}
                        {employee.emergency_contact_phone && ` - ${employee.emergency_contact_phone}`}
                      </p>
                    )}
                  </div>
                )}
                
                {/* Driving Info */}
                {(employee.has_driving_licence || employee.has_own_vehicle) && (
                  <div className="pt-3 border-t border-gray-100">
                    <p className="text-sm text-text-muted mb-1">Driving / Vehicle</p>
                    <div className="flex gap-3 text-sm">
                      {employee.has_driving_licence && (
                        <span className="px-2 py-0.5 bg-green-100 text-green-700 rounded">
                          {employee.driving_licence_type || 'Driving Licence'}
                        </span>
                      )}
                      {employee.has_own_vehicle && (
                        <span className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded">
                          Own Vehicle {employee.vehicle_registration && `(${employee.vehicle_registration})`}
                        </span>
                      )}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            <Card className="border-[#E4E8EB] shadow-sm">
              <CardHeader>
                <CardTitle className="font-heading text-lg">Care Status</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-4 bg-success/10 border border-success/20 rounded-xl">
                    <p className="text-sm text-success font-medium">Verified & Complete</p>
                    <p className="text-2xl font-heading font-bold text-success">
                      {complianceRequirements?.summary?.verified || 0}/{complianceRequirements?.summary?.total || 0}
                    </p>
                    <p className="text-[10px] text-success/70 mt-1">Checked, approved & current</p>
                  </div>
                  <div className="p-4 bg-info/10 border border-info/20 rounded-xl">
                    <p className="text-sm text-info font-medium">Awaiting Review</p>
                    <p className="text-2xl font-heading font-bold text-info">
                      {(complianceRequirements?.summary?.completed || 0) - (complianceRequirements?.summary?.verified || 0)}
                    </p>
                    <p className="text-[10px] text-info/70 mt-1">Evidence uploaded, needs verification</p>
                  </div>
                  <div className="p-4 bg-error/10 border border-error/20 rounded-xl">
                    <p className="text-sm text-error font-medium">Still Needed</p>
                    <p className="text-2xl font-heading font-bold text-error">
                      {complianceRequirements?.summary?.missing || 0}
                    </p>
                    <p className="text-[10px] text-error/70 mt-1">No evidence uploaded</p>
                  </div>
                  <div className="p-4 bg-[#F8FAFA] rounded-xl">
                    <p className="text-sm text-text-muted">Policies Signed</p>
                    <p className="text-2xl font-heading font-bold text-text-primary">
                      {policies.filter(p => p.status === 'signed').length}/{policies.length}
                    </p>
                    <p className="text-[10px] text-text-muted mt-1">Staff policy acknowledgements</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Document Requests & Interview Records */}
          <div className="grid lg:grid-cols-2 gap-6 mt-6">
            <DocumentRequestsPanel 
              employeeId={employeeId}
              onRefresh={fetchComplianceFile}
            />
            <InterviewFormPanel 
              employeeId={employeeId}
              employeeName={employee ? `${employee.first_name} ${employee.last_name}` : ''}
            />
          </div>

          {/* Training & Compliance Overview */}
          <ComplianceOverview
            employee={employee}
            documents={documents}
            training={training}
            policies={policies}
            generatedForms={generatedForms}
            complianceRequirements={complianceRequirements}
            isAuditor={isAuditor()}
            onCompleteTraining={(item) => {
              // Map the ComplianceOverview item format to requirement format
              // The trainingType corresponds to the requirement_id in MANDATORY_ITEMS
              const trainingReqMapping = {
                'safeguarding': { id: 'safeguarding', name: 'Safeguarding Training', category: 'N_Training' },
                'manual_handling': { id: 'manual_handling', name: 'Manual Handling Training', category: 'N_Training' },
                'infection_control': { id: 'infection_control', name: 'Infection Control Training', category: 'N_Training' },
                'basic_life_support': { id: 'bls', name: 'Basic Life Support (BLS)', category: 'N_Training' },
                'medication': { id: 'medication_competency', name: 'Medication Competency', category: 'N_Training' },
                'induction': { id: 'induction', name: 'Induction & Competency Assessment', category: 'J_Induction_Shadowing_Observations' }
              };
              const reqData = trainingReqMapping[item.trainingType] || {
                id: item.trainingType || item.id,
                name: item.name,
                category: 'N_Training'
              };
              openTrainingDialog(reqData);
            }}
          />
        </TabsContent>

        {/* Compliance File Tab - Primary Requirements & Evidence Management */}
        <TabsContent value="checklist">
          <Card className="border-[#E4E8EB] shadow-sm">
            <CardHeader className="pb-4">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="font-heading text-lg">Compliance File</CardTitle>
                  <p className="text-xs text-text-muted mt-1">
                    Operational workflow for compliance. Upload evidence, verify checks, manage agreements.
                  </p>
                </div>
                {complianceRequirements?.work_readiness_3tier && (
                  <div className={`flex items-center gap-2 text-sm px-4 py-2 rounded-xl font-medium ${
                    complianceRequirements.work_readiness_3tier.status === 'READY_TO_WORK' ? 'bg-green-100 text-green-800' :
                    complianceRequirements.work_readiness_3tier.status === 'READY_WITH_CONDITIONS' ? 'bg-amber-100 text-amber-800' :
                    'bg-red-100 text-red-800'
                  }`}>
                    {complianceRequirements.work_readiness_3tier.status === 'READY_TO_WORK' ? (
                      <Shield className="h-4 w-4" />
                    ) : (
                      <AlertTriangle className="h-4 w-4" />
                    )}
                    {complianceRequirements.work_readiness_3tier.label}
                  </div>
                )}
              </div>
            </CardHeader>
            <CardContent>
              {/* ============================================== */}
              {/* COMPLIANCE FILE - Linear Workflow                */}
              {/* All actions live INSIDE each requirement card    */}
              {/* No global actions - see issue → scroll → fix     */}
              {/* ============================================== */}

              {/* Conditional Items - Keep minimal info about items not required */}
              {complianceRequirements?.conditional_not_required?.length > 0 && (
                <div className="mb-4 p-3 bg-gray-50 border border-gray-200 rounded-lg">
                  <div className="flex items-start gap-2">
                    <CheckCircle className="h-4 w-4 text-green-600 mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="text-sm font-medium text-gray-700">Some items not required for this employee:</p>
                      <ul className="mt-1 space-y-0.5">
                        {complianceRequirements.conditional_not_required.map((item, idx) => (
                          <li key={idx} className="text-xs text-gray-600">
                            {item.name} — {item.reason}
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>
              )}

              {!complianceRequirements ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="h-8 w-8 animate-spin text-primary" />
                </div>
              ) : (
                <div className="space-y-6">
                  {/* ============================================ */}
                  {/* EMPLOYMENT GAP VERIFICATION PANEL */}
                  {/* Shows detected gaps and verification status */}
                  {/* ============================================ */}
                  {complianceFile?.sections?.employment_history?.rows?.[0]?.has_gaps && (
                    <div className="mb-4">
                      <EmploymentGapPanel
                        employeeId={employeeId}
                        employeeName={`${employee?.first_name} ${employee?.last_name}`}
                        initialData={{
                          has_gaps: true,
                          gaps: complianceFile.sections.employment_history.rows[0].gaps,
                          evaluation: complianceFile.sections.employment_history.rows[0].gap_evaluation
                        }}
                        isAdmin={!isAuditor() && (user?.role === 'admin' || user?.role === 'super_admin')}
                        onGapUpdate={() => {
                          fetchCompliance();
                          fetchComplianceFile();
                        }}
                      />
                    </div>
                  )}

                  {/* ============================================ */}
                  {/* DUAL-ROW COMPLIANCE SECTION (Phase 4A) */}
                  {/* Separates evidence from employer checks */}
                  {/* ============================================ */}
                  <div className="mb-6">
                    
                    <DualRowComplianceSection
                      employeeId={employeeId}
                      employeeEmail={employee?.email}
                      employeeName={employee ? `${employee.first_name} ${employee.last_name}` : ''}
                      onUpload={(key) => {
                        // Trigger document upload for the specified requirement
                        setSelectedRequirement(key);
                        setUploadDialogOpen(true);
                      }}
                      onRequest={(key, title) => {
                        // Trigger request document dialog with proper requirement object
                        setRequestingRequirement({ id: key, name: title || key });
                        setRequestDocMessage('');
                        setRequestDocDialogOpen(true);
                      }}
                      onPreviewFile={(fileObj) => {
                        // Handle both old format (doc.file_url) and new format from RequirementFilesDrawer
                        const rawUrl = fileObj?.file_url || fileObj?.url;
                        const name = fileObj?.file_name || fileObj?.name || 'Document';
                        if (rawUrl) {
                          // FIX: Ensure URL is absolute - API already ends with /api
                          let url = rawUrl;
                          if (rawUrl.startsWith('/api/')) {
                            url = `${API}${rawUrl.substring(4)}`; // "/api/foo" -> API + "/foo"
                          }
                          setPreviewFile({ url, name, filename: name });
                          setPreviewFiles([]); // Clear multi-file array
                          setPreviewOpen(true);
                        } else {
                          // No URL available - show error toast
                          console.error('No file URL available for preview', fileObj);
                        }
                      }}
                      onExtractReview={(docId) => {
                        setDocExtractionDocumentId(docId);
                        setDocExtractionReviewOpen(true);
                      }}
                      onRecordCheck={(checkType) => {
                        setRecordCheckType(checkType);
                        setRecordCheckDialogOpen(true);
                      }}
                      employeeData={employee}
                      isAuditor={isAuditor()}
                      onRefresh={() => {
                        fetchData();
                        fetchCompliance();
                      }}
                    />
                  </div>

                  {/* TRAINING SUMMARY CARD - Phase 4A */}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Policies Tab */}

        {/* Policies Tab */}
        <TabsContent value="policies">
          <Card className="border-[#E4E8EB] shadow-sm">
            <CardContent className="p-6">
              {/* Header with stats */}
              <div className="flex items-center justify-between mb-6 pb-4 border-b border-[#E4E8EB]">
                <div>
                  <h3 className="font-heading text-lg font-semibold text-text-primary">Assigned Policies</h3>
                  <p className="text-sm text-text-muted">
                    {policies.filter(p => p.status === 'acknowledged' || p.status === 'signed').length} of {policies.length} acknowledged
                  </p>
                  <p className="text-xs text-text-muted mt-1">
                    Employees must read and acknowledge assigned policies.
                  </p>
                </div>
                {policies.length > 0 && (
                  <div className="flex items-center gap-2 text-sm">
                    <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-gray-100 text-gray-600">
                      <Clock className="w-3 h-3" /> {policies.filter(p => p.status === 'assigned' || p.status === 'viewed').length} Not Read
                    </span>
                    <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-green-100 text-green-700">
                      <CheckCircle className="w-3 h-3" /> {policies.filter(p => p.status === 'acknowledged' || p.status === 'signed').length} Acknowledged
                    </span>
                  </div>
                )}
              </div>

              {policies.length === 0 ? (
                <div className="text-center py-12 text-text-muted">
                  <FileCheck className="h-12 w-12 mx-auto mb-3 opacity-50" />
                  <p>No policies assigned yet</p>
                  <p className="text-sm mt-1">Policies can be assigned from the Compliance Centre</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {policies.map((policy) => (
                    <div key={policy.id} className={`p-4 rounded-xl border ${
                      policy.admin_reviewed ? 'bg-green-50 border-green-200' :
                      (policy.status === 'acknowledged' || policy.status === 'signed') ? 'bg-blue-50 border-blue-200' :
                      policy.status === 'viewed' ? 'bg-amber-50 border-amber-200' :
                      'bg-[#F8FAFA] border-[#E4E8EB]'
                    }`}>
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <p className="font-semibold text-text-primary">{policy.policy_title}</p>
                            <span className="text-xs px-2 py-0.5 bg-gray-200 rounded text-gray-600">
                              v{policy.policy_version || '1.0'}
                            </span>
                          </div>
                          <p className="text-sm text-text-muted mt-1">
                            Assigned: {formatBackendDate(policy.assigned_at)} 
                            {policy.assigned_by_name && ` by ${policy.assigned_by_name}`}
                          </p>
                          
                          {/* Signature Information Display */}
                          {(policy.status === 'acknowledged' || policy.status === 'signed') && (
                            <div className="mt-3 p-3 bg-white/80 rounded-lg border border-green-200">
                              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Employee Acknowledgement</p>
                              <p className="text-sm font-medium text-green-800">
                                {policy.acknowledged_by_employee_name || policy.employee_name || 'Employee'}
                              </p>
                              <p className="text-xs text-green-600">
                                {policy.acknowledged_at ? formatBackendDateTime(policy.acknowledged_at) : 
                                 policy.signed_at ? formatBackendDateTime(policy.signed_at) : ''}
                              </p>
                            </div>
                          )}
                          
                          {policy.admin_reviewed && (
                            <div className="mt-2 p-3 bg-white/80 rounded-lg border border-green-200">
                              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Admin Review</p>
                              <p className="text-sm font-medium text-green-800">
                                {policy.admin_reviewed_by_name || 'Admin'}
                              </p>
                              <p className="text-xs text-green-600">
                                {policy.admin_reviewed_at ? formatBackendDateTime(policy.admin_reviewed_at) : ''}
                              </p>
                            </div>
                          )}
                        </div>
                        
                        <div className="flex flex-col items-end gap-2">
                          {/* Status Badge */}
                          <span className={`status-chip ${
                            policy.admin_reviewed ? 'status-success' :
                            (policy.status === 'acknowledged' || policy.status === 'signed') ? 'bg-green-100 text-green-700 border-green-200' :
                            'bg-gray-100 text-gray-600 border-gray-200'
                          }`}>
                            {policy.admin_reviewed ? 'Reviewed & Approved' :
                             (policy.status === 'acknowledged' || policy.status === 'signed') ? 'Acknowledged' :
                             'Not Read'}
                          </span>
                          
                          {/* Action Buttons */}
                          <div className="flex items-center gap-2 flex-wrap justify-end">
                            {/* View Policy Button */}
                            <Button
                              size="sm"
                              variant="outline"
                              className="rounded-lg text-xs"
                              onClick={async () => {
                                try {
                                  // Mark as viewed if not already
                                  if (policy.status === 'assigned') {
                                    await axios.put(`${API}/policy-assignments/${policy.id}/view`, {}, {
                                      headers: { Authorization: `Bearer ${token}` }
                                    });
                                  }
                                  // Open policy file
                                  const response = await axios.get(`${API}/policies/${policy.policy_id}/file`, {
                                    headers: { Authorization: `Bearer ${token}` },
                                    responseType: 'blob'
                                  });
                                  const url = window.URL.createObjectURL(response.data);
                                  window.open(url, '_blank');
                                  await fetchData();
                                } catch (error) {
                                  if (error.response?.status === 404) {
                                    toast.error('Policy document not found');
                                  } else {
                                    toast.error('Failed to open policy');
                                  }
                                }
                              }}
                              data-testid={`view-policy-${policy.id}`}
                            >
                              <Eye className="w-3 h-3 mr-1" />
                              View Policy
                            </Button>
                            
                            {/* Acknowledge Button - only if not yet acknowledged */}
                            {policy.status !== 'acknowledged' && policy.status !== 'signed' && !isAuditor() && (
                              <Button
                                size="sm"
                                className="rounded-lg text-xs bg-primary hover:bg-primary-hover text-white"
                                onClick={async () => {
                                  try {
                                    await axios.put(`${API}/policy-assignments/${policy.id}/acknowledge`, {}, {
                                      headers: { Authorization: `Bearer ${token}` }
                                    });
                                    toast.success('Policy acknowledged successfully');
                                    await fetchData();
                                  } catch (error) {
                                    toast.error(error.response?.data?.detail || 'Failed to acknowledge policy');
                                  }
                                }}
                                data-testid={`acknowledge-policy-${policy.id}`}
                              >
                                <CheckCircle className="w-3 h-3 mr-1" />
                                Mark as Read & Understood
                              </Button>
                            )}
                            
                            {/* Admin Review Button - only if acknowledged but not reviewed */}
                            {(policy.status === 'acknowledged' || policy.status === 'signed') && !policy.admin_reviewed && isAdmin() && (
                              <Button
                                size="sm"
                                variant="outline"
                                className="rounded-lg text-xs border-green-300 text-green-700 hover:bg-green-50"
                                onClick={async () => {
                                  try {
                                    await axios.put(`${API}/policy-assignments/${policy.id}/admin-review`, {}, {
                                      headers: { Authorization: `Bearer ${token}` }
                                    });
                                    toast.success('Policy reviewed and approved');
                                    await fetchData();
                                  } catch (error) {
                                    toast.error(error.response?.data?.detail || 'Failed to review policy');
                                  }
                                }}
                                data-testid={`admin-review-policy-${policy.id}`}
                              >
                                <Shield className="w-3 h-3 mr-1" />
                                Reviewed and Approved
                              </Button>
                            )}
                            
                            {/* Unassign Button - only for unacknowledged policies (admin/manager only) */}
                            {policy.status !== 'acknowledged' && policy.status !== 'signed' && 
                             policy.status !== 'unassigned' && policy.status !== 'withdrawn' && 
                             isAdmin() && (
                              <Button
                                size="sm"
                                variant="outline"
                                className="rounded-lg text-xs border-amber-300 text-amber-700 hover:bg-amber-50"
                                onClick={async () => {
                                  if (!window.confirm('Remove this policy from the employee\'s active policy list?')) return;
                                  try {
                                    await axios.put(`${API}/policy-assignments/${policy.id}/unassign`, {}, {
                                      headers: { Authorization: `Bearer ${token}` }
                                    });
                                    toast.success('Policy unassigned');
                                    await fetchData();
                                  } catch (error) {
                                    toast.error(error.response?.data?.detail || 'Failed to unassign policy');
                                  }
                                }}
                                data-testid={`unassign-policy-${policy.id}`}
                              >
                                <XCircle className="w-3 h-3 mr-1" />
                                Unassign
                              </Button>
                            )}
                            
                            {/* Withdraw Button - only for acknowledged policies (admin only) */}
                            {(policy.status === 'acknowledged' || policy.status === 'signed') && 
                             policy.status !== 'withdrawn' && isAdmin() && (
                              <Button
                                size="sm"
                                variant="outline"
                                className="rounded-lg text-xs border-red-300 text-red-700 hover:bg-red-50"
                                onClick={async () => {
                                  if (!window.confirm('Withdraw this policy? The acknowledgement history will be preserved for audit purposes.')) return;
                                  try {
                                    await axios.put(`${API}/policy-assignments/${policy.id}/withdraw`, {}, {
                                      headers: { Authorization: `Bearer ${token}` }
                                    });
                                    toast.success('Policy assignment withdrawn');
                                    await fetchData();
                                  } catch (error) {
                                    toast.error(error.response?.data?.detail || 'Failed to withdraw policy');
                                  }
                                }}
                                data-testid={`withdraw-policy-${policy.id}`}
                              >
                                <RotateCcw className="w-3 h-3 mr-1" />
                                Withdraw
                              </Button>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Training Tab */}
        <TabsContent value="training" ref={trainingSectionRef}>
          {/* Audit-Ready Training Matrix - Complete training record with tabs */}
          <AuditReadyTrainingMatrix
            employeeId={employeeId}
            employeeName={`${employee?.first_name} ${employee?.last_name}`}
            role={employee?.role}
            onUploadCertificate={() => {
              // Open the training intake wizard
              setTrainingIntakeOpen(true);
            }}
            onViewCertificate={(documentId) => {
              handleViewTrainingCertificate(documentId, 'training_certificate');
            }}
            onRefresh={() => {
              fetchTraining();
              fetchProposedTrainingItems();
            }}
          />
        </TabsContent>

        {/* Audit Log Tab */}
        <TabsContent value="audit">
          <AuditTrailPanel employeeId={employeeId} />
        </TabsContent>


        {/* References Tab */}
        <TabsContent value="references">
          <ReferencesPanel 
            employeeId={employeeId}
            onRefresh={() => {
              fetchComplianceFile();
              fetchRecruitmentStatus();
            }}
          />
        </TabsContent>
      </Tabs>

      {/* Edit Employee Dialog */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent className="sm:max-w-lg max-h-[90vh] overflow-y-auto bg-white">
          <DialogHeader>
            <DialogTitle className="font-heading flex items-center gap-2 text-gray-900">
              <Edit className="h-5 w-5 text-teal-600" />
              Edit Employee Details
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 mt-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label className="text-gray-700 font-medium">First Name *</Label>
                <Input
                  value={editForm.first_name}
                  onChange={(e) => setEditForm({...editForm, first_name: e.target.value})}
                  className="rounded-xl bg-gray-50 border-gray-300 text-gray-900 placeholder:text-gray-400 focus:ring-2 focus:ring-teal-600 focus:border-teal-600"
                />
              </div>
              <div className="space-y-2">
                <Label className="text-gray-700 font-medium">Last Name *</Label>
                <Input
                  value={editForm.last_name}
                  onChange={(e) => setEditForm({...editForm, last_name: e.target.value})}
                  className="rounded-xl bg-gray-50 border-gray-300 text-gray-900 placeholder:text-gray-400 focus:ring-2 focus:ring-teal-600 focus:border-teal-600"
                />
              </div>
            </div>
            
            <div className="space-y-2">
              <Label className="text-gray-700 font-medium">Email *</Label>
              <Input
                type="email"
                value={editForm.email}
                onChange={(e) => setEditForm({...editForm, email: e.target.value})}
                className="rounded-xl bg-gray-50 border-gray-300 text-gray-900 placeholder:text-gray-400 focus:ring-2 focus:ring-teal-600 focus:border-teal-600"
              />
            </div>
            
            <div className="space-y-2">
              <Label className="text-gray-700 font-medium">Phone</Label>
              <Input
                type="tel"
                value={editForm.phone}
                onChange={(e) => setEditForm({...editForm, phone: e.target.value})}
                className="rounded-xl bg-gray-50 border-gray-300 text-gray-900 placeholder:text-gray-400 focus:ring-2 focus:ring-teal-600 focus:border-teal-600"
              />
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label className="text-gray-700 font-medium">Role *</Label>
                <Select value={editForm.role} onValueChange={(value) => setEditForm({...editForm, role: value})}>
                  <SelectTrigger className="rounded-xl bg-gray-50 border-gray-300 text-gray-900 focus:ring-2 focus:ring-teal-600 focus:border-teal-600">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-white border-gray-200">
                    {roles.map((role) => (
                      <SelectItem key={role} value={role} className="text-gray-900">{role}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label className="text-gray-700 font-medium">Status</Label>
                <Select value={editForm.status} onValueChange={(value) => setEditForm({...editForm, status: value})}>
                  <SelectTrigger className="rounded-xl bg-gray-50 border-gray-300 text-gray-900 focus:ring-2 focus:ring-teal-600 focus:border-teal-600">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-white border-gray-200">
                    {statuses.map((s) => (
                      <SelectItem key={s.value} value={s.value} className="text-gray-900">{s.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label className="text-gray-700 font-medium">Onboarding Status</Label>
                <Select value={editForm.onboarding_status} onValueChange={(value) => setEditForm({...editForm, onboarding_status: value})}>
                  <SelectTrigger className="rounded-xl bg-gray-50 border-gray-300 text-gray-900 focus:ring-2 focus:ring-teal-600 focus:border-teal-600">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-white border-gray-200">
                    {onboardingStatuses.map((s) => (
                      <SelectItem key={s} value={s} className="text-gray-900">{s}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label className="text-gray-700 font-medium">Start Date</Label>
                <Input
                  type="date"
                  value={editForm.start_date}
                  onChange={(e) => setEditForm({...editForm, start_date: e.target.value})}
                  className="rounded-xl bg-gray-50 border-gray-300 text-gray-900 focus:ring-2 focus:ring-teal-600 focus:border-teal-600"
                />
              </div>
            </div>
            
            <div className="space-y-2">
              <Label className="text-gray-700 font-medium">Notes</Label>
              <Textarea
                value={editForm.notes}
                onChange={(e) => setEditForm({...editForm, notes: e.target.value})}
                placeholder="Internal notes about this employee..."
                className="rounded-xl min-h-[80px] bg-gray-50 border-gray-300 text-gray-900 placeholder:text-gray-400 focus:ring-2 focus:ring-teal-600 focus:border-teal-600"
              />
            </div>
          </div>
          <DialogFooter className="mt-6">
            <Button variant="outline" onClick={() => setEditDialogOpen(false)} className="rounded-xl border-gray-300 text-gray-700 hover:bg-gray-50">
              Cancel
            </Button>
            <Button onClick={handleSaveEmployee} disabled={isSaving} className="bg-teal-600 hover:bg-teal-700 text-white rounded-xl">
              {isSaving ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Save className="h-4 w-4 mr-2" />}
              Save Changes
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Archive Confirmation Dialog */}
      <Dialog open={archiveDialogOpen} onOpenChange={setArchiveDialogOpen}>
        <DialogContent className="bg-white">
          <DialogHeader>
            <DialogTitle className="font-heading flex items-center gap-2 text-gray-900">
              <Archive className="h-5 w-5 text-amber-500" />
              Archive Employee
            </DialogTitle>
            <DialogDescription className="text-gray-500">
              Are you sure you want to archive <strong className="text-gray-900">{employee?.first_name} {employee?.last_name}</strong>?
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3 py-4">
            <p className="text-sm text-gray-600">This will:</p>
            <ul className="text-sm text-gray-600 list-disc list-inside space-y-1">
              <li>Hide employee from the active employees list</li>
              <li>Retain all documents, forms, and audit history</li>
              <li>Allow restoration at any time</li>
            </ul>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setArchiveDialogOpen(false)} className="rounded-xl border-gray-300 text-gray-700 hover:bg-gray-50">
              Cancel
            </Button>
            <Button onClick={handleArchiveEmployee} className="bg-amber-500 hover:bg-amber-600 text-white rounded-xl">
              <Archive className="h-4 w-4 mr-2" />
              Archive Employee
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Permanent Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent className="bg-white">
          <DialogHeader>
            <DialogTitle className="font-heading flex items-center gap-2 text-red-600">
              <AlertTriangle className="h-5 w-5" />
              Permanent Deletion
            </DialogTitle>
            <DialogDescription className="text-gray-500">
              Are you sure you want to <strong className="text-gray-900">permanently delete</strong> {employee?.first_name} {employee?.last_name}?
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3 py-4 bg-red-50 p-4 rounded-xl border border-red-200">
            <p className="text-sm font-medium text-red-600">This action cannot be undone!</p>
            <p className="text-sm text-gray-600">All of the following will be permanently deleted:</p>
            <ul className="text-sm text-gray-600 list-disc list-inside space-y-1">
              <li>Employee record</li>
              <li>All uploaded documents</li>
              <li>All compliance forms</li>
              <li>Training records</li>
              <li>Policy assignments</li>
            </ul>
            <p className="text-xs text-gray-500 mt-2">Only use this for duplicate records, test data, or incorrect entries.</p>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDialogOpen(false)} className="rounded-xl border-gray-300 text-gray-700 hover:bg-gray-50">
              Cancel
            </Button>
            <Button onClick={handlePermanentDelete} className="bg-red-600 hover:bg-red-700 text-white rounded-xl">
              <Trash2 className="h-4 w-4 mr-2" />
              Delete Permanently
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Training Completion Dialog */}
      <Dialog open={trainingDialogOpen} onOpenChange={setTrainingDialogOpen}>
        <DialogContent className="sm:max-w-md bg-white">
          <DialogHeader>
            <DialogTitle className="font-heading flex items-center gap-2 text-text-primary">
              <GraduationCap className="h-5 w-5 text-primary" />
              Mark Training Complete
            </DialogTitle>
            <DialogDescription className="text-text-muted">
              Mark this training requirement as completed for the employee.
            </DialogDescription>
          </DialogHeader>
          
          {selectedTrainingReq && (
            <div className="space-y-4 py-4">
              <div className="p-4 bg-[#F8FAFA] rounded-xl">
                <p className="font-medium text-text-primary">{selectedTrainingReq.name}</p>
                <p className="text-sm text-text-muted mt-1">
                  Category: {selectedTrainingReq.category?.replace(/_/g, ' ').replace(/^[A-Z]_/, '')}
                </p>
              </div>
              
              <div className="space-y-2">
                <Label className="text-text-primary">Expiry Date (Optional)</Label>
                <Input
                  type="date"
                  value={trainingExpiryDate}
                  onChange={(e) => setTrainingExpiryDate(e.target.value)}
                  className="rounded-xl"
                  placeholder="Leave empty if no expiry"
                />
                <p className="text-xs text-text-muted">
                  Set an expiry date if this training needs to be renewed
                </p>
              </div>
              
              <div className="bg-info/10 border border-info/20 rounded-xl p-3">
                <p className="text-sm text-info font-medium">What happens:</p>
                <ul className="text-xs text-text-muted mt-1 space-y-1">
                  <li className="flex items-center gap-1">
                    <CheckCircle className="h-3 w-3 text-success" />
                    Training record created or updated
                  </li>
                  <li className="flex items-center gap-1">
                    <CheckCircle className="h-3 w-3 text-success" />
                    Compliance requirement marked complete
                  </li>
                  <li className="flex items-center gap-1">
                    <CheckCircle className="h-3 w-3 text-success" />
                    Compliance score updates immediately
                  </li>
                </ul>
              </div>
            </div>
          )}
          
          <DialogFooter>
            <Button 
              variant="outline" 
              onClick={() => {
                setTrainingDialogOpen(false);
                setSelectedTrainingReq(null);
                setTrainingExpiryDate('');
              }} 
              className="rounded-xl"
            >
              Cancel
            </Button>
            <Button 
              onClick={handleCompleteTraining}
              disabled={isCompletingTraining}
              className="bg-primary hover:bg-primary-hover text-white rounded-xl"
              data-testid="confirm-complete-training"
            >
              {isCompletingTraining ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <>
                  <CheckCircle className="h-4 w-4 mr-2" />
                  Mark Complete
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Training Certificate Upload Dialog */}
      <Dialog open={trainingCertDialogOpen} onOpenChange={setTrainingCertDialogOpen}>
        <DialogContent className="sm:max-w-md bg-white">
          <DialogHeader>
            <DialogTitle className="font-heading flex items-center gap-2 text-text-primary">
              <Upload className="h-5 w-5 text-primary" />
              Upload Training Certificate
            </DialogTitle>
            <DialogDescription className="text-text-muted">
              Upload a certificate as evidence for this training requirement.
            </DialogDescription>
          </DialogHeader>
          
          {selectedTrainingReq && (
            <div className="space-y-4 py-4">
              <div className="p-4 bg-[#F8FAFA] rounded-xl">
                <p className="font-medium text-text-primary">{selectedTrainingReq.name}</p>
                <p className="text-sm text-text-muted mt-1">
                  Category: {selectedTrainingReq.category?.replace(/_/g, ' ').replace(/^[A-Z]_/, '')}
                </p>
              </div>
              
              <div className="space-y-2">
                <Label className="text-text-primary">Certificate File *</Label>
                <FileUploaderInline
                  onFileSelect={(file) => setTrainingCertFile(file)}
                  selectedFile={trainingCertFile}
                  onClear={() => setTrainingCertFile(null)}
                  acceptedTypes={['application/pdf', 'image/jpeg', 'image/jpg', 'image/png', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']}
                  placeholder="Drop certificate here or click to browse"
                  data-testid="training-cert-file-input"
                />
                <p className="text-xs text-text-muted">
                  Accepted formats: PDF, JPG, PNG, DOC, DOCX (max 10MB)
                </p>
              </div>
              
              <div className="space-y-2">
                <Label className="text-text-primary">Certificate Expiry Date (Optional)</Label>
                <Input
                  type="date"
                  value={trainingExpiryDate}
                  onChange={(e) => setTrainingExpiryDate(e.target.value)}
                  className="rounded-xl"
                />
                <p className="text-xs text-text-muted">
                  Set an expiry date if this certificate needs to be renewed
                </p>
              </div>
              
              <div className="bg-success/10 border border-success/20 rounded-xl p-3">
                <p className="text-sm text-success font-medium">Audit-Ready Evidence:</p>
                <ul className="text-xs text-text-muted mt-1 space-y-1">
                  <li className="flex items-center gap-1">
                    <CheckCircle className="h-3 w-3 text-success" />
                    Certificate stored with audit trail
                  </li>
                  <li className="flex items-center gap-1">
                    <CheckCircle className="h-3 w-3 text-success" />
                    Training marked as complete with evidence
                  </li>
                  <li className="flex items-center gap-1">
                    <CheckCircle className="h-3 w-3 text-success" />
                    Certificate can be viewed and downloaded
                  </li>
                  <li className="flex items-center gap-1">
                    <Shield className="h-3 w-3 text-success" />
                    Ready for verification
                  </li>
                </ul>
              </div>
            </div>
          )}
          
          <DialogFooter>
            <Button 
              variant="outline" 
              onClick={() => {
                setTrainingCertDialogOpen(false);
                setSelectedTrainingReq(null);
                setTrainingCertFile(null);
                setTrainingExpiryDate('');
              }} 
              className="rounded-xl"
            >
              Cancel
            </Button>
            <Button 
              onClick={handleUploadTrainingCertificate}
              disabled={isUploadingCert || !trainingCertFile}
              className="bg-primary hover:bg-primary-hover text-white rounded-xl"
              data-testid="confirm-upload-training-cert"
            >
              {isUploadingCert ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <>
                  <Upload className="h-4 w-4 mr-2" />
                  Upload Certificate
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Evidence Details Modal */}
      <Dialog open={editEvidenceOpen} onOpenChange={setEditEvidenceOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="font-heading">Edit Document Details</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 mt-4">
            <p className="text-sm text-text-muted">
              Update document metadata. A reason is required for audit trail purposes.
            </p>
            
            <div className="space-y-2">
              <Label>Document Label</Label>
              <Input
                value={editForm.file_label}
                onChange={(e) => setEditForm(prev => ({ ...prev, file_label: e.target.value }))}
                placeholder="e.g., DBS Certificate 2024"
                className="rounded-xl"
              />
            </div>
            
            {/* DBS Update Service Check - Special labels and auto-calculation */}
            {editEvidenceData?.requirementId === 'dbs_check' ? (
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-2">
                  <Label>Last DBS Check Date</Label>
                  <Input
                    type="date"
                    value={editForm.issue_date}
                    onChange={(e) => {
                      const checkDate = e.target.value;
                      // Auto-calculate Next Review Due = Check Date + 12 months
                      let nextReviewDate = '';
                      if (checkDate) {
                        const date = new Date(checkDate);
                        date.setFullYear(date.getFullYear() + 1);
                        nextReviewDate = date.toISOString().split('T')[0];
                      }
                      setEditForm(prev => ({ 
                        ...prev, 
                        issue_date: checkDate,
                        expiry_date: nextReviewDate
                      }));
                    }}
                    className="rounded-xl"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Next DBS Review Due</Label>
                  <Input
                    type="date"
                    value={editForm.expiry_date}
                    onChange={(e) => setEditForm(prev => ({ ...prev, expiry_date: e.target.value }))}
                    className="rounded-xl bg-gray-50"
                    title="Auto-calculated as 12 months from Last DBS Check Date"
                  />
                  <p className="text-xs text-text-muted">Auto-calculated (+12 months)</p>
                </div>
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-2">
                  <Label>Issue Date</Label>
                  <Input
                    type="date"
                    value={editForm.issue_date}
                    onChange={(e) => setEditForm(prev => ({ ...prev, issue_date: e.target.value }))}
                    className="rounded-xl"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Expiry Date</Label>
                  <Input
                    type="date"
                    value={editForm.expiry_date}
                    onChange={(e) => setEditForm(prev => ({ ...prev, expiry_date: e.target.value }))}
                    className="rounded-xl"
                  />
                </div>
              </div>
            )}
            
            <div className="space-y-2">
              <Label>Notes</Label>
              <Textarea
                value={editForm.notes}
                onChange={(e) => setEditForm(prev => ({ ...prev, notes: e.target.value }))}
                placeholder="Additional notes about this document..."
                className="rounded-xl"
                rows={3}
              />
            </div>
            
            <div className="space-y-2">
              <Label className="text-warning">Reason for Change *</Label>
              <Textarea
                value={editForm.reason}
                onChange={(e) => setEditForm(prev => ({ ...prev, reason: e.target.value }))}
                placeholder="e.g., Wrong expiry year entered, Corrected issue date from certificate..."
                className="rounded-xl border-warning/50 focus:border-warning"
                rows={2}
              />
              <p className="text-xs text-text-muted">
                This will be recorded in the audit trail for CQC compliance.
              </p>
            </div>
          </div>
          <DialogFooter className="mt-4">
            <Button 
              variant="outline" 
              onClick={() => setEditEvidenceOpen(false)}
              className="rounded-xl"
            >
              Cancel
            </Button>
            <Button 
              onClick={handleSaveEvidenceEdit}
              disabled={isEditingEvidence || !editForm.reason}
              className="bg-primary hover:bg-primary-hover text-white rounded-xl"
            >
              {isEditingEvidence ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <>
                  <Save className="h-4 w-4 mr-2" />
                  Save Changes
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit History Modal */}
      <Dialog open={historyOpen} onOpenChange={setHistoryOpen}>
        <DialogContent className="max-w-lg max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="font-heading flex items-center gap-2">
              <History className="h-5 w-5 text-primary" />
              Change History
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-3 mt-4">
            {editHistory.length === 0 ? (
              <div className="text-center py-8">
                <History className="h-10 w-10 mx-auto text-text-muted/50 mb-2" />
                <p className="text-text-muted">No changes recorded</p>
                <p className="text-xs text-text-muted mt-1">
                  Document details have not been modified since upload.
                </p>
              </div>
            ) : (
              editHistory.map((log) => (
                <div 
                  key={log.id} 
                  className="p-3 bg-[#F8FAFA] rounded-xl border border-[#E4E8EB]"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <User className="h-4 w-4 text-primary" />
                      <span className="font-medium text-text-primary text-sm">
                        {log.changed_by_name}
                      </span>
                    </div>
                    <span className="text-xs text-text-muted">
                      {formatBackendDateTime(log.changed_at)}
                    </span>
                  </div>
                  <div className="text-sm space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-text-muted">Field:</span>
                      <span className="font-medium text-text-primary capitalize">
                        {log.field_changed.replace(/_/g, ' ')}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-text-muted">From:</span>
                      <span className="text-error line-through">
                        {log.old_value || '(empty)'}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-text-muted">To:</span>
                      <span className="text-success">
                        {log.new_value || '(empty)'}
                      </span>
                    </div>
                    <div className="flex items-start gap-2 mt-2 pt-2 border-t border-[#E4E8EB]">
                      <span className="text-text-muted">Reason:</span>
                      <span className="text-text-primary italic">
                        "{log.reason}"
                      </span>
                    </div>
                    {log.was_verified_before_edit && (
                      <div className="mt-2 px-2 py-1 bg-warning/10 text-warning text-xs rounded-lg inline-block">
                        Changed after approval
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
          <DialogFooter className="mt-4">
            <Button 
              variant="outline" 
              onClick={() => setHistoryOpen(false)}
              className="rounded-xl"
            >
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete File Dialog */}
      <Dialog open={removeDialogOpen} onOpenChange={setRemoveDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-red-600">
              <Trash2 className="h-5 w-5" />
              Delete File
            </DialogTitle>
            <DialogDescription>
              This will permanently remove the file from active use. The file will no longer count towards compliance. An audit record will be kept.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            {selectedFileForAction && (
              <div className="p-3 bg-red-50 rounded-lg border border-red-200">
                <p className="text-sm font-medium text-red-800">{selectedFileForAction.file_label || selectedFileForAction.original_filename || 'File'}</p>
                {selectedFileForAction.uploaded_at && (
                  <p className="text-xs text-red-600 mt-1">
                    Uploaded: {formatBackendDate(selectedFileForAction.uploaded_at)}
                  </p>
                )}
              </div>
            )}
            <div className="space-y-2">
              <Label htmlFor="delete-reason">Reason for deletion (optional)</Label>
              <Textarea
                id="delete-reason"
                placeholder="Enter an optional reason for deleting this file"
                value={removeReason}
                onChange={(e) => setRemoveReason(e.target.value)}
                className="min-h-[80px] rounded-xl"
              />
              <p className="text-xs text-text-muted">This reason will be recorded in the audit trail if provided.</p>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRemoveDialogOpen(false)} className="rounded-xl">
              Cancel
            </Button>
            <Button 
              variant="destructive" 
              onClick={handleDeleteFile}
              disabled={isRemoving}
              className="rounded-xl"
              data-testid="confirm-delete-file"
            >
              {isRemoving ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Trash2 className="h-4 w-4 mr-2" />}
              Delete File
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Replace File Dialog */}
      <Dialog open={replaceDialogOpen} onOpenChange={setReplaceDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <RefreshCw className="h-5 w-5 text-primary" />
              Replace File
            </DialogTitle>
            <DialogDescription>
              Uploading a new file will replace the existing one. The old file will be kept in history for audit purposes.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            {selectedFileForAction && (
              <div className="p-3 bg-muted rounded-lg">
                <p className="text-sm text-muted-foreground">Replacing:</p>
                <p className="text-sm font-medium">{selectedFileForAction.file_label || selectedFileForAction.original_filename}</p>
              </div>
            )}
            <div className="space-y-2">
              <Label htmlFor="replace-file">New File <span className="text-error">*</span></Label>
              <FileUploaderInline
                onFileSelect={(file) => setReplaceFile(file)}
                selectedFile={replaceFile}
                onClear={() => setReplaceFile(null)}
                acceptedTypes={['application/pdf', 'image/jpeg', 'image/jpg', 'image/png', 'image/webp']}
                placeholder="Drop replacement file here or click to browse"
              />
              <p className="text-xs text-muted-foreground">Upload PDF or photo (JPG, PNG)</p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="replace-reason">Reason for replacement <span className="text-error">*</span></Label>
              <Textarea
                id="replace-reason"
                placeholder="Why is this file being replaced? (e.g. clearer scan, updated document)"
                value={replaceReason}
                onChange={(e) => setReplaceReason(e.target.value)}
                className="min-h-[80px]"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setReplaceDialogOpen(false)}>
              Cancel
            </Button>
            <Button 
              onClick={handleReplaceFile}
              disabled={isReplacing || !replaceReason.trim() || !replaceFile}
              className="bg-primary hover:bg-primary-hover"
            >
              {isReplacing ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <RefreshCw className="h-4 w-4 mr-2" />}
              Replace File
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Document Correction Dialog - Step 8 */}
      <Dialog open={docCorrectionDialogOpen} onOpenChange={setDocCorrectionDialogOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {docCorrectionType === 'uploaded_in_error' && <FileWarning className="h-5 w-5 text-amber-500" />}
              {docCorrectionType === 'supersede' && <FileArchive className="h-5 w-5 text-blue-500" />}
              {docCorrectionType === 'move_category' && <FormInput className="h-5 w-5 text-purple-500" />}
              {docCorrectionType === 'reopen_review' && <RotateCcw className="h-5 w-5 text-green-500" />}
              {docCorrectionType === 'uploaded_in_error' && 'Mark as Uploaded in Error'}
              {docCorrectionType === 'supersede' && 'Mark as Superseded'}
              {docCorrectionType === 'move_category' && 'Move to Different Category'}
              {docCorrectionType === 'reopen_review' && 'Reopen for Review'}
            </DialogTitle>
            <DialogDescription>
              {docCorrectionType === 'uploaded_in_error' && 'This document will be marked as uploaded in error. It will not count toward requirements but is preserved for audit.'}
              {docCorrectionType === 'supersede' && 'Mark this document as superseded by a newer version. The original is preserved for audit trail.'}
              {docCorrectionType === 'move_category' && 'Move this document to a different requirement category if it was filed incorrectly.'}
              {docCorrectionType === 'reopen_review' && 'Reopen this document for review, undoing any previous verification or rejection.'}
            </DialogDescription>
          </DialogHeader>
          
          {docCorrectionTarget && (
            <div className="space-y-4 py-4">
              <div className="p-3 bg-muted rounded-lg">
                <p className="font-medium text-sm">{docCorrectionTarget.file_label || docCorrectionTarget.original_filename || 'Document'}</p>
                {docCorrectionTarget.uploaded_at && (
                  <p className="text-xs text-muted-foreground">
                    Uploaded: {formatBackendDate(docCorrectionTarget.uploaded_at, { format: 'medium' })}
                  </p>
                )}
              </div>

              {docCorrectionType === 'move_category' && (
                <div className="space-y-2">
                  <Label>New Category *</Label>
                  <Select 
                    value={docCorrectionNewCategory} 
                    onValueChange={setDocCorrectionNewCategory}
                  >
                    <SelectTrigger className="rounded-xl">
                      <SelectValue placeholder="Select new category" />
                    </SelectTrigger>
                    <SelectContent>
                      {complianceRequirements?.requirements
                        .filter(r => r.type === 'document' && r.id !== selectedRequirementForAction)
                        .map(r => (
                          <SelectItem key={r.id} value={r.id}>
                            {r.name}
                          </SelectItem>
                        ))}
                    </SelectContent>
                  </Select>
                </div>
              )}

              <div className="space-y-2">
                <Label>
                  Reason for Change *
                  <span className="text-xs text-muted-foreground ml-2">
                    ({docCorrectionType === 'move_category' ? 'min 5' : 'min 10'} characters)
                  </span>
                </Label>
                <Textarea
                  placeholder="Explain why this correction is being made..."
                  value={docCorrectionReason}
                  onChange={(e) => setDocCorrectionReason(e.target.value)}
                  className="min-h-[80px] rounded-xl"
                  data-testid="doc-correction-reason"
                />
                <p className="text-xs text-muted-foreground">
                  This reason will be permanently recorded in the audit trail.
                </p>
              </div>

              {docCorrectionTarget.verified && (
                <div className="p-3 bg-amber-50 rounded-lg border border-amber-200">
                  <p className="text-sm text-amber-700 flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4" />
                    This document is currently verified. This action will be flagged in the audit log.
                  </p>
                </div>
              )}
            </div>
          )}

          <DialogFooter>
            <Button 
              variant="outline" 
              onClick={() => setDocCorrectionDialogOpen(false)}
              className="rounded-xl"
            >
              Cancel
            </Button>
            <Button
              onClick={handleSubmitDocCorrection}
              disabled={
                isSubmittingDocCorrection || 
                !docCorrectionReason.trim() ||
                docCorrectionReason.trim().length < (docCorrectionType === 'move_category' ? 5 : 10) ||
                (docCorrectionType === 'move_category' && !docCorrectionNewCategory)
              }
              className={`rounded-xl ${
                docCorrectionType === 'uploaded_in_error' ? 'bg-amber-600 hover:bg-amber-700' :
                docCorrectionType === 'reopen_review' ? 'bg-green-600 hover:bg-green-700' :
                'bg-primary hover:bg-primary-hover'
              }`}
              data-testid="submit-doc-correction"
            >
              {isSubmittingDocCorrection && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
              Confirm
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Document Extraction Review Modal - Phase 2: DBS, RTW, ID, POA */}
      {docExtractionReviewOpen && docExtractionDocumentId && (
        <DocumentExtractionReview
          documentId={docExtractionDocumentId}
          onClose={() => {
            setDocExtractionReviewOpen(false);
            setDocExtractionDocumentId(null);
            setDocExtractionContext(null);
          }}
          onApproved={handleDocExtractionComplete}
          documentName={docExtractionDocumentName}
          documentContext={docExtractionContext}
        />
      )}

      {/* Training Intake Wizard (Step 10) */}
      <TrainingIntakeWizard
        employeeId={employeeId}
        employeeName={employee ? `${employee.first_name} ${employee.last_name}` : ''}
        open={trainingIntakeOpen}
        onClose={() => setTrainingIntakeOpen(false)}
        onComplete={() => {
          setTrainingIntakeOpen(false);
          fetchData();
          fetchCompliance();
          fetchProposedTrainingItems();
          fetchTrainingEvaluation();
        }}
      />

      {/* Training Request Dialog (Step 10) */}
      <TrainingRequestDialog
        employeeId={employeeId}
        employeeName={employee ? `${employee.first_name} ${employee.last_name}` : ''}
        employeeEmail={employee?.email}
        open={trainingRequestOpen}
        onClose={() => setTrainingRequestOpen(false)}
        onComplete={() => {
          setTrainingRequestOpen(false);
          toast.success('Training certificate request sent');
        }}
      />

      {/* Requirement History Dialog */}
      <Dialog open={requirementHistoryOpen} onOpenChange={setRequirementHistoryOpen}>
        <DialogContent className="sm:max-w-lg max-h-[80vh] overflow-hidden flex flex-col">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <History className="h-5 w-5 text-primary" />
              File History
            </DialogTitle>
            <DialogDescription>
              Complete timeline of all file operations for this requirement.
            </DialogDescription>
          </DialogHeader>
          <div className="flex-1 overflow-y-auto py-4">
            {loadingHistory ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-primary" />
              </div>
            ) : requirementHistory.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <History className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p>No history recorded yet</p>
              </div>
            ) : (
              <div className="space-y-3">
                {requirementHistory.map((entry, idx) => (
                  <div key={entry.id || idx} className="p-3 border rounded-lg">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-2">
                        {entry.action === 'replace_evidence' && <RefreshCw className="h-4 w-4 text-blue-500" />}
                        {entry.action === 'remove_evidence' && <Trash2 className="h-4 w-4 text-red-500" />}
                        {entry.action === 'edit_evidence' && <Edit className="h-4 w-4 text-amber-500" />}
                        {entry.action === 'upload_evidence' && <Upload className="h-4 w-4 text-green-500" />}
                        {entry.action === 'verify_evidence' && <Shield className="h-4 w-4 text-green-600" />}
                        {!['replace_evidence', 'remove_evidence', 'edit_evidence', 'upload_evidence', 'verify_evidence'].includes(entry.action) && (
                          <FileText className="h-4 w-4 text-gray-500" />
                        )}
                        <span className="font-medium text-sm capitalize">
                          {entry.action?.replace(/_/g, ' ')}
                        </span>
                      </div>
                      <span className="text-xs text-muted-foreground">
                        {entry.timestamp ? formatBackendDateTime(entry.timestamp) : 'Unknown'}
                      </span>
                    </div>
                    <p className="text-sm text-muted-foreground mt-1">
                      By: {entry.user_name || 'Unknown'}
                    </p>
                    {entry.reason && (
                      <p className="text-sm mt-2 p-2 bg-muted rounded">
                        <span className="font-medium">Reason:</span> {entry.reason}
                      </p>
                    )}
                    {entry.details && Object.keys(entry.details).length > 0 && (
                      <div className="text-xs text-muted-foreground mt-2 space-y-1">
                        {entry.details.old_filename && (
                          <p>Old file: {entry.details.old_filename}</p>
                        )}
                        {entry.details.new_filename && (
                          <p>New file: {entry.details.new_filename}</p>
                        )}
                        {entry.details.filename && (
                          <p>File: {entry.details.filename}</p>
                        )}
                        {entry.details.field && (
                          <p>Changed: {entry.details.field} from "{entry.details.old_value || 'empty'}" to "{entry.details.new_value}"</p>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRequirementHistoryOpen(false)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Document Preview Modal - supports multi-file navigation */}
      <DocumentPreviewModal
        isOpen={previewOpen}
        onClose={() => { setPreviewOpen(false); setPreviewFiles([]); }}
        fileUrl={previewFile?.url}
        fileName={previewFile?.name || previewFile?.filename}
        token={token}
        files={previewFiles}
        onDownload={previewFile ? async () => {
          try {
            const downloadUrl = previewFile.url.replace('/view', '/download');
            const response = await axios.get(downloadUrl, {
              headers: { Authorization: `Bearer ${token}` },
              responseType: 'blob'
            });
            const blob = new Blob([response.data]);
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = previewFile.filename || 'document';
            link.click();
            URL.revokeObjectURL(url);
            toast.success('Document downloaded');
          } catch (error) {
            toast.error('Failed to download');
          }
        } : undefined}
      />
      
      {/* Training Correction Dialog */}
      <Dialog open={trainingCorrectionDialogOpen} onOpenChange={setTrainingCorrectionDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="font-heading">Edit Training Record</DialogTitle>
            <DialogDescription>
              Make a correction to this training record. All changes require a reason and are logged for audit purposes.
            </DialogDescription>
          </DialogHeader>
          {editingTrainingRecord && (
            <div className="space-y-4 mt-4">
              <div className="p-3 bg-[#F8FAFA] rounded-lg border border-[#E4E8EB]">
                <p className="font-medium text-text-primary">{editingTrainingRecord.training_name}</p>
              </div>
              
              <div className="space-y-2">
                <Label>Field to Edit</Label>
                <Select value={trainingCorrectionField} onValueChange={(value) => {
                  setTrainingCorrectionField(value);
                  setTrainingCorrectionValue(editingTrainingRecord[value]?.split?.('T')?.[0] || editingTrainingRecord[value] || '');
                }}>
                  <SelectTrigger className="rounded-xl">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="expiry_date">Expiry Date</SelectItem>
                    <SelectItem value="completion_date">Completion Date</SelectItem>
                    <SelectItem value="status">Status</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              
              <div className="space-y-2">
                <Label>Current Value</Label>
                <Input 
                  value={editingTrainingRecord[trainingCorrectionField] || '(not set)'} 
                  disabled 
                  className="rounded-xl bg-gray-100"
                />
              </div>
              
              <div className="space-y-2">
                <Label>New Value *</Label>
                {trainingCorrectionField === 'status' ? (
                  <Select value={trainingCorrectionValue} onValueChange={setTrainingCorrectionValue}>
                    <SelectTrigger className="rounded-xl">
                      <SelectValue placeholder="Select new status" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="not_started">Not Started</SelectItem>
                      <SelectItem value="in_progress">In Progress</SelectItem>
                      <SelectItem value="completed">Completed</SelectItem>
                      <SelectItem value="expired">Expired</SelectItem>
                      <SelectItem value="expiring">Expiring</SelectItem>
                    </SelectContent>
                  </Select>
                ) : (
                  <Input 
                    type="date" 
                    value={trainingCorrectionValue?.split?.('T')?.[0] || trainingCorrectionValue || ''} 
                    onChange={(e) => setTrainingCorrectionValue(e.target.value)}
                    className="rounded-xl"
                  />
                )}
              </div>
              
              <div className="space-y-2">
                <Label>Reason for Change *</Label>
                <Textarea 
                  placeholder="Explain why this correction is being made (required for audit trail)"
                  value={trainingCorrectionReason}
                  onChange={(e) => setTrainingCorrectionReason(e.target.value)}
                  className="rounded-xl min-h-[80px]"
                />
              </div>
            </div>
          )}
          <DialogFooter className="mt-6">
            <Button variant="outline" onClick={() => setTrainingCorrectionDialogOpen(false)} className="rounded-xl">
              Cancel
            </Button>
            <Button 
              onClick={handleTrainingCorrection} 
              disabled={!trainingCorrectionReason || !trainingCorrectionValue}
              className="bg-primary hover:bg-primary-hover text-white rounded-xl"
            >
              Save Correction
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      
      {/* Training History Dialog */}
      <Dialog open={trainingHistoryDialogOpen} onOpenChange={setTrainingHistoryDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle className="font-heading">Training Record History</DialogTitle>
          </DialogHeader>
          <div className="space-y-3 max-h-96 overflow-y-auto mt-4">
            {trainingHistory.length === 0 ? (
              <div className="text-center py-8 text-text-muted">
                <History className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p>No correction history</p>
              </div>
            ) : (
              trainingHistory.map((entry, idx) => (
                <div key={entry.id || idx} className="p-3 bg-white rounded-lg border border-[#E4E8EB]">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="font-medium text-text-primary">
                        {entry.action === 'training_correction' ? 'Correction' : entry.action?.replace('_', ' ')}
                      </p>
                      {entry.field_changed && (
                        <p className="text-sm text-text-muted">
                          <span className="font-medium">{entry.field_changed}</span>: {entry.old_value || '(empty)'} → {entry.new_value}
                        </p>
                      )}
                      {entry.reason && (
                        <p className="text-sm text-text-muted mt-1">
                          <span className="font-medium">Reason:</span> {entry.reason}
                        </p>
                      )}
                    </div>
                    <div className="text-right text-xs text-text-muted">
                      <p>{entry.changed_by_name || 'System'}</p>
                      <p>{entry.created_at ? formatBackendDateTime(entry.created_at) : ''}</p>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </DialogContent>
      </Dialog>
      
      {/* Delete Training Record Dialog */}
      <Dialog open={deleteTrainingDialogOpen} onOpenChange={setDeleteTrainingDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-red-600">
              <Trash2 className="h-5 w-5" />
              Delete Training Record
            </DialogTitle>
            <DialogDescription>
              This will permanently remove this training record. An audit trail will be kept.
            </DialogDescription>
          </DialogHeader>
          {deletingTrainingRecord && (
            <div className="space-y-4 py-4">
              <div className="p-3 bg-red-50 rounded-lg border border-red-200">
                <p className="font-medium text-red-800">{deletingTrainingRecord.training_name}</p>
                <p className="text-sm text-red-600 mt-1">
                  Status: {deletingTrainingRecord.status?.replace('_', ' ')}
                </p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="delete-training-reason">Reason for deletion (optional)</Label>
                <Textarea
                  id="delete-training-reason"
                  placeholder="Enter an optional reason for deleting this record"
                  value={deleteTrainingReason}
                  onChange={(e) => setDeleteTrainingReason(e.target.value)}
                  className="min-h-[80px] rounded-xl"
                />
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteTrainingDialogOpen(false)} className="rounded-xl">
              Cancel
            </Button>
            <Button 
              variant="destructive" 
              onClick={handleDeleteTrainingRecord}
              disabled={isDeletingTraining}
              className="rounded-xl"
            >
              {isDeletingTraining ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Trash2 className="h-4 w-4 mr-2" />}
              Delete Record
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      
      {/* Acknowledgement Dialog - For Contract/Handbook acknowledgements */}
      <Dialog open={acknowledgementDialogOpen} onOpenChange={(open) => {
        setAcknowledgementDialogOpen(open);
        if (!open) {
          setAcknowledgementConfirmed(false);
          setAcknowledgingRequirement(null);
        }
      }}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-green-600">
              <CheckCircle className="h-5 w-5" />
              Confirm & Complete
            </DialogTitle>
            <DialogDescription>
              Please confirm that this employee has received and understood the document.
            </DialogDescription>
          </DialogHeader>
          {acknowledgingRequirement && (
            <div className="space-y-4 py-4">
              <div className="p-4 bg-green-50 rounded-lg border border-green-200">
                <p className="font-semibold text-green-800">{acknowledgingRequirement.name}</p>
                <p className="text-sm text-green-600 mt-2">
                  {acknowledgingRequirement.description}
                </p>
              </div>
              
              <div className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg border">
                <Checkbox 
                  id="acknowledgement-confirm"
                  checked={acknowledgementConfirmed}
                  onCheckedChange={setAcknowledgementConfirmed}
                  className="mt-0.5"
                  data-testid="acknowledgement-checkbox"
                />
                <label htmlFor="acknowledgement-confirm" className="text-sm cursor-pointer">
                  {acknowledgingRequirement.acknowledgement_text || 
                    `I confirm that this employee has received, read, and understood the ${acknowledgingRequirement.name.replace(' Acknowledgement', '')}.`}
                </label>
              </div>
              
              <p className="text-xs text-text-muted">
                This acknowledgement will be logged with your name and timestamp for audit purposes.
              </p>
            </div>
          )}
          <DialogFooter>
            <Button 
              variant="outline" 
              onClick={() => setAcknowledgementDialogOpen(false)} 
              className="rounded-xl"
            >
              Cancel
            </Button>
            <Button 
              onClick={handleAcknowledgeRequirement}
              disabled={!acknowledgementConfirmed || isAcknowledging}
              className="rounded-xl bg-green-600 hover:bg-green-700"
              data-testid="submit-acknowledgement-btn"
            >
              {isAcknowledging ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <CheckCircle className="h-4 w-4 mr-2" />
              )}
              Confirm & Complete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Form Submission Modal - Structured forms with sections */}
      <Dialog open={formModalOpen} onOpenChange={(open) => {
        setFormModalOpen(open);
        if (!open) {
          setFormTemplate(null);
          setFormData({});
        }
      }}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          {/* Branded Header for Staff Health Questionnaire */}
          {formTemplate?.branding?.show_logo && (
            <div className="bg-[#2E7D32] text-white p-4 -m-6 mb-4 rounded-t-lg">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 bg-white rounded-full flex items-center justify-center">
                  <span className="text-[#2E7D32] font-bold text-xl">O</span>
                </div>
                <div>
                  <h2 className="text-lg font-bold">{formTemplate?.branding?.company_name || 'Osabea Healthcare Solutions Ltd'}</h2>
                  <p className="text-sm opacity-90">{formTemplate?.name}</p>
                </div>
              </div>
            </div>
          )}
          
          <DialogHeader className={formTemplate?.branding?.show_logo ? 'pt-0' : ''}>
            {!formTemplate?.branding?.show_logo && (
              <DialogTitle className="font-heading flex items-center gap-2">
                <ClipboardCheck className="h-5 w-5 text-primary" />
                {formTemplate?.name || 'Complete Form'}
              </DialogTitle>
            )}
            {formTemplate?.description && (
              <DialogDescription className="text-sm text-text-muted">
                {formTemplate.description}
              </DialogDescription>
            )}
          </DialogHeader>
          
          {formTemplate && (
            <div className="space-y-6 mt-4">
              {/* Optional form notice */}
              {formTemplate.is_optional && (
                <div className="p-3 bg-blue-50 border border-blue-200 rounded-xl">
                  <p className="text-sm text-blue-700 flex items-center gap-2">
                    <span className="px-2 py-0.5 bg-blue-100 text-blue-800 text-xs font-medium rounded">Optional</span>
                    This form does not affect compliance percentage or work readiness status.
                  </p>
                </div>
              )}
              
              {/* Auto-fill notice */}
              {formTemplate.auto_fill_fields?.length > 0 && Object.keys(formData).length > 0 && (
                <div className="p-3 bg-green-50 border border-green-200 rounded-xl">
                  <p className="text-sm text-green-700 flex items-center gap-2">
                    <CheckCircle className="h-4 w-4" />
                    Some fields have been pre-filled from the employee profile. Please review and update as needed.
                  </p>
                </div>
              )}
              
              {/* Profile update notice */}
              {formTemplate.updates_profile && (
                <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl">
                  <p className="text-sm text-amber-700 flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4" />
                    This form can update the employee's profile data when submitted.
                  </p>
                </div>
              )}
              
              {/* Render sections if available, otherwise fallback to flat fields */}
              {formTemplate.sections?.length > 0 ? (
                <div className="space-y-6">
                  {formTemplate.sections.map((section) => {
                    // Skip admin-only sections for non-admins
                    if (section.admin_only && !isAdmin()) return null;
                    
                    // Use green header style if form has branding
                    const sectionHeaderClass = formTemplate?.branding?.header_color 
                      ? 'bg-[#2E7D32] text-white px-4 py-3 border-b border-[#2E7D32]'
                      : 'bg-gray-50 px-4 py-3 border-b border-gray-200';
                    
                    return (
                      <div key={section.id} className="border border-gray-200 rounded-xl overflow-hidden">
                        <div className={sectionHeaderClass}>
                          <h4 className={`font-medium ${formTemplate?.branding?.header_color ? 'text-white' : 'text-text-primary'}`}>
                            {section.title}
                          </h4>
                          {section.description && (
                            <p className={`text-xs mt-0.5 ${formTemplate?.branding?.header_color ? 'text-white/80' : 'text-text-muted'}`}>
                              {section.description}
                            </p>
                          )}
                        </div>
                        <div className="p-4 space-y-4">
                          {section.fields.map((field) => {
                            // Handle conditional fields
                            if (field.conditional_on) {
                              const conditionValue = formData[field.conditional_on];
                              if (conditionValue !== field.conditional_value) {
                                return null;
                              }
                            }
                            
                            return (
                              <div key={field.id} className="space-y-1.5">
                                {field.type === 'info' ? (
                                  <p className="text-sm text-text-muted italic bg-[#F8FAFA] p-3 rounded-lg">
                                    {field.label}
                                  </p>
                                ) : (
                                  <>
                                    <Label className="text-sm font-medium flex items-center gap-2">
                                      {field.label}
                                      {field.required && <span className="text-error">*</span>}
                                      {field.auto_fill && formData[field.id] && (
                                        <span className="text-xs text-green-600 font-normal">(auto-filled)</span>
                                      )}
                                    </Label>
                                    
                                    {field.type === 'text' && (
                                      <Input
                                        value={formData[field.id] || ''}
                                        onChange={(e) => setFormData({...formData, [field.id]: e.target.value})}
                                        placeholder={field.placeholder || ''}
                                        className="rounded-xl"
                                      />
                                    )}
                                    
                                    {field.type === 'number' && (
                                      <Input
                                        type="number"
                                        value={formData[field.id] || ''}
                                        onChange={(e) => setFormData({...formData, [field.id]: e.target.value})}
                                        placeholder={field.placeholder || ''}
                                        className="rounded-xl"
                                      />
                                    )}
                                    
                                    {field.type === 'textarea' && (
                                      <Textarea
                                        value={formData[field.id] || ''}
                                        onChange={(e) => setFormData({...formData, [field.id]: e.target.value})}
                                        placeholder={field.placeholder || ''}
                                        className="rounded-xl"
                                        rows={3}
                                      />
                                    )}
                                    
                                    {field.type === 'date' && (
                                      <Input
                                        type="date"
                                        value={formData[field.id] || ''}
                                        onChange={(e) => setFormData({...formData, [field.id]: e.target.value})}
                                        className="rounded-xl"
                                      />
                                    )}
                                    
                                    {field.type === 'checkbox' && (
                                      <div className="flex items-center gap-2">
                                        <Checkbox
                                          id={field.id}
                                          checked={formData[field.id] || false}
                                          onCheckedChange={(checked) => setFormData({...formData, [field.id]: checked})}
                                        />
                                        <label htmlFor={field.id} className="text-sm cursor-pointer">Yes</label>
                                      </div>
                                    )}
                                    
                                    {field.type === 'select' && (
                                      <Select 
                                        value={formData[field.id] || ''} 
                                        onValueChange={(v) => setFormData({...formData, [field.id]: v})}
                                      >
                                        <SelectTrigger className="rounded-xl">
                                          <SelectValue placeholder="Select..." />
                                        </SelectTrigger>
                                        <SelectContent>
                                          {field.options?.map((opt) => (
                                            <SelectItem key={opt} value={opt}>{opt}</SelectItem>
                                          ))}
                                        </SelectContent>
                                      </Select>
                                    )}
                                    
                                    {field.type === 'multi_select' && (
                                      <div className="flex flex-wrap gap-2">
                                        {field.options?.map((opt) => (
                                          <label key={opt} className="flex items-center gap-1.5 text-sm">
                                            <Checkbox
                                              checked={(formData[field.id] || []).includes(opt)}
                                              onCheckedChange={(checked) => {
                                                const current = formData[field.id] || [];
                                                if (checked) {
                                                  setFormData({...formData, [field.id]: [...current, opt]});
                                                } else {
                                                  setFormData({...formData, [field.id]: current.filter(v => v !== opt)});
                                                }
                                              }}
                                            />
                                            {opt}
                                          </label>
                                        ))}
                                      </div>
                                    )}
                                  </>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                /* Fallback to flat fields for backward compatibility */
                <div className="grid gap-4">
                  {formTemplate.fields?.map((field) => (
                    <div key={field.id} className="space-y-1.5">
                      {field.type === 'info' ? (
                        <p className="text-sm text-text-muted italic bg-[#F8FAFA] p-3 rounded-lg">
                          {field.label}
                        </p>
                      ) : (
                        <>
                          <Label className="text-sm font-medium">
                            {field.label}
                            {field.required && <span className="text-error ml-1">*</span>}
                          </Label>
                          
                          {field.type === 'text' && (
                            <Input
                              value={formData[field.id] || ''}
                              onChange={(e) => setFormData({...formData, [field.id]: e.target.value})}
                              placeholder={field.placeholder || ''}
                              className="rounded-xl"
                            />
                          )}
                          
                          {field.type === 'textarea' && (
                            <Textarea
                              value={formData[field.id] || ''}
                              onChange={(e) => setFormData({...formData, [field.id]: e.target.value})}
                              placeholder={field.placeholder || ''}
                              className="rounded-xl"
                              rows={3}
                            />
                          )}
                          
                          {field.type === 'date' && (
                            <Input
                              type="date"
                              value={formData[field.id] || ''}
                              onChange={(e) => setFormData({...formData, [field.id]: e.target.value})}
                              className="rounded-xl"
                            />
                          )}
                          
                          {field.type === 'checkbox' && (
                            <div className="flex items-center gap-2">
                              <Checkbox
                                id={field.id}
                                checked={formData[field.id] || false}
                                onCheckedChange={(checked) => setFormData({...formData, [field.id]: checked})}
                              />
                              <label htmlFor={field.id} className="text-sm cursor-pointer">Yes</label>
                            </div>
                          )}
                          
                          {field.type === 'select' && (
                            <Select 
                              value={formData[field.id] || ''} 
                              onValueChange={(v) => setFormData({...formData, [field.id]: v})}
                            >
                              <SelectTrigger className="rounded-xl">
                                <SelectValue placeholder="Select..." />
                              </SelectTrigger>
                              <SelectContent>
                                {field.options?.map((opt) => (
                                  <SelectItem key={opt} value={opt}>{opt}</SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          )}
                        </>
                      )}
                    </div>
                  ))}
                </div>
              )}
              
              <DialogFooter className="pt-4">
                <Button 
                  variant="outline" 
                  onClick={() => setFormModalOpen(false)} 
                  className="rounded-xl"
                >
                  Cancel
                </Button>
                <Button 
                  onClick={handleFormSubmit}
                  disabled={isSubmittingForm}
                  className="rounded-xl bg-primary hover:bg-primary/90"
                  data-testid="submit-form-btn"
                >
                  {isSubmittingForm ? (
                    <><Loader2 className="h-4 w-4 animate-spin mr-2" /> Submitting...</>
                  ) : (
                    'Submit Form'
                  )}
                </Button>
              </DialogFooter>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* View Form Modal - Display submitted form data */}
      <Dialog open={viewFormOpen} onOpenChange={setViewFormOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="font-heading flex items-center gap-2">
              <ClipboardCheck className="h-5 w-5 text-primary" />
              {viewFormData?.requirementName || 'Form Submission'}
            </DialogTitle>
          </DialogHeader>
          
          {viewFormData && (
            <div className="space-y-4 mt-4">
              {/* Status badges */}
              <div className="flex items-center gap-3 p-3 bg-[#F8FAFA] rounded-xl">
                <div className="flex items-center gap-2">
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                    viewFormData.verified 
                      ? 'bg-green-100 text-green-700' 
                      : 'bg-blue-100 text-blue-700'
                  }`}>
                    {viewFormData.verified ? 'Verified' : 'Submitted'}
                  </span>
                </div>
                <div className="text-xs text-text-muted">
                  Submitted: {viewFormData.submitted_at ? formatBackendDateTime(viewFormData.submitted_at) : 'Unknown'}
                </div>
                {viewFormData.submitted_by_name && (
                  <div className="text-xs text-text-muted">
                    By: {viewFormData.submitted_by_name}
                  </div>
                )}
              </div>
              
              {/* Form data display */}
              <div className="space-y-3">
                {Object.entries(viewFormData.data || {}).map(([key, value]) => (
                  <div key={key} className="flex items-start gap-3 p-2 border-b border-[#E4E8EB]">
                    <span className="text-sm font-medium text-text-primary min-w-[180px] capitalize">
                      {key.replace(/_/g, ' ')}:
                    </span>
                    <span className="text-sm text-text-muted flex-1">
                      {typeof value === 'boolean' ? (value ? 'Yes' : 'No') : (value || '-')}
                    </span>
                  </div>
                ))}
              </div>
              
              {/* Verification info if verified */}
              {viewFormData.verified && viewFormData.verified_by_name && (
                <div className="p-3 bg-green-50 rounded-xl border border-green-200">
                  <p className="text-sm text-green-700">
                    <CheckCircle className="h-4 w-4 inline mr-2" />
                    Verified by {viewFormData.verified_by_name} on {formatBackendDateTime(viewFormData.verified_at)}
                  </p>
                </div>
              )}
              
              <DialogFooter className="pt-4">
                <Button 
                  variant="outline" 
                  onClick={() => setViewFormOpen(false)} 
                  className="rounded-xl"
                >
                  Close
                </Button>
                {!viewFormData.verified && isAdmin() && (
                  <Button 
                    onClick={() => handleVerifyFormSubmission(viewFormData.id)}
                    className="rounded-xl bg-green-600 hover:bg-green-700"
                    data-testid="verify-form-btn"
                  >
                    <CheckCircle className="h-4 w-4 mr-2" />
                    Verify Form
                  </Button>
                )}
              </DialogFooter>
            </div>
          )}
        </DialogContent>
      </Dialog>
      
      {/* Extraction Review Dialog */}
      <Dialog open={extractionDialogOpen} onOpenChange={(open) => {
        if (!open && !isApplyingExtraction) {
          handleDiscardExtraction();
        }
      }}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="font-heading flex items-center gap-2">
              <FileText className="h-5 w-5 text-primary" />
              {extractionFailed ? 'Extraction Options' : 'Review Extracted Data'}
            </DialogTitle>
            <DialogDescription>
              {extractionFailed ? (
                extractionFailed.message
              ) : (
                <>
                  Review the extracted values below. Select which fields to apply to the employee profile.
                  <span className="block mt-2 text-amber-600 font-medium">
                    Note: This updates profile data only. Compliance evidence requirements remain unchanged.
                  </span>
                </>
              )}
            </DialogDescription>
          </DialogHeader>
          
          {isExtracting ? (
            <div className="flex flex-col items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-primary mb-4" />
              <p className="text-text-muted">Extracting data from application form...</p>
              <p className="text-xs text-text-muted mt-1">This may take a few seconds</p>
            </div>
          ) : extractionFailed ? (
            /* Extraction Failed - Show Options */
            <div className="space-y-4">
              {/* Friendly Message */}
              <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg">
                <div className="flex items-start gap-3">
                  <AlertTriangle className="h-5 w-5 text-amber-600 mt-0.5 flex-shrink-0" />
                  <div className="text-sm text-amber-800">
                    <p className="font-medium mb-1">Don't worry - you can still proceed!</p>
                    <p>Automatic extraction didn't work for this document, but you have options to continue.</p>
                    {extractionFailed.extraction_log && (
                      <p className="text-xs mt-2 text-amber-600">
                        Details: {extractionFailed.extraction_log.file_type} ({Math.round((extractionFailed.extraction_log.file_size_bytes || 0) / 1024)} KB)
                        {extractionFailed.extraction_log.failure_reason && (
                          <span className="block">Reason: {extractionFailed.extraction_log.failure_reason}</span>
                        )}
                      </p>
                    )}
                  </div>
                </div>
              </div>
              
              {/* Options Buttons */}
              <div className="space-y-3">
                {extractionFailed.options?.map((option) => (
                  <button
                    key={option.action}
                    onClick={() => handleExtractionOption(option.action)}
                    className="w-full flex items-center gap-4 p-4 border rounded-lg hover:bg-gray-50 transition-colors text-left"
                    data-testid={`extraction-option-${option.action}`}
                  >
                    <div className="flex-shrink-0">
                      {option.action === 'fill_manually' && (
                        <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center">
                          <Edit className="h-5 w-5 text-blue-600" />
                        </div>
                      )}
                      {option.action === 'view_document' && (
                        <div className="w-10 h-10 rounded-full bg-purple-100 flex items-center justify-center">
                          <Eye className="h-5 w-5 text-purple-600" />
                        </div>
                      )}
                      {option.action === 'retry' && (
                        <div className="w-10 h-10 rounded-full bg-green-100 flex items-center justify-center">
                          <RefreshCw className="h-5 w-5 text-green-600" />
                        </div>
                      )}
                    </div>
                    <div className="flex-1">
                      <p className="font-medium text-text-primary">{option.label}</p>
                      <p className="text-sm text-text-muted">{option.description}</p>
                    </div>
                    <ChevronRight className="h-5 w-5 text-gray-400" />
                  </button>
                ))}
              </div>
              
              <DialogFooter className="pt-4">
                <Button
                  variant="outline"
                  onClick={handleDiscardExtraction}
                  data-testid="close-extraction-dialog"
                >
                  Close
                </Button>
              </DialogFooter>
            </div>
          ) : extractionResult ? (
            <div className="space-y-4">
              {/* Extraction Method & Low Confidence Warning */}
              {extractionResult.low_confidence_fields?.length > 0 && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                  <div className="flex items-start gap-2">
                    <AlertTriangle className="h-4 w-4 text-red-600 mt-0.5 flex-shrink-0" />
                    <div className="text-sm text-red-800">
                      <p className="font-medium">Low Confidence Fields Detected</p>
                      <p>Please review highlighted fields carefully: {extractionResult.low_confidence_fields.map(f => FIELD_LABELS[f] || f).join(', ')}</p>
                    </div>
                  </div>
                </div>
              )}
              
              {/* Extraction Method Badge */}
              {extractionResult.extraction_method && (
                <div className="flex items-center gap-2 text-xs">
                  <span className="text-text-muted">Extraction method:</span>
                  <span className={`px-2 py-0.5 rounded font-medium ${
                    extractionResult.extraction_method === 'ai' ? 'bg-blue-100 text-blue-700' :
                    extractionResult.extraction_method === 'ai+ocr' ? 'bg-purple-100 text-purple-700' :
                    'bg-gray-100 text-gray-700'
                  }`}>
                    {extractionResult.extraction_method === 'ai' ? 'AI Vision' :
                     extractionResult.extraction_method === 'ai+ocr' ? 'AI + OCR' :
                     extractionResult.extraction_method === 'ocr' ? 'OCR' : extractionResult.extraction_method}
                  </span>
                </div>
              )}
              
              {/* Compliance Note */}
              <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
                <div className="flex items-start gap-2">
                  <AlertTriangle className="h-4 w-4 text-amber-600 mt-0.5 flex-shrink-0" />
                  <div className="text-sm text-amber-800">
                    <p className="font-medium">Profile Data Only</p>
                    <p>Extracted values will populate profile fields (e.g., NI Number field). They do NOT complete compliance requirements (e.g., "Proof of NI Number" still needs evidence upload).</p>
                  </div>
                </div>
              </div>
              
              {/* Fields Table */}
              <div className="border rounded-lg overflow-hidden">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="text-left p-3 font-medium">Apply</th>
                      <th className="text-left p-3 font-medium">Field</th>
                      <th className="text-left p-3 font-medium">Extracted Value</th>
                      <th className="text-left p-3 font-medium">Current Value</th>
                      <th className="text-left p-3 font-medium">Confidence</th>
                    </tr>
                  </thead>
                  <tbody>
                    {extractionResult.fields.map((field, idx) => {
                      // Handle both numeric confidence and string confidence_label
                      const confidenceScore = typeof field.confidence === 'number' ? field.confidence : null;
                      const confidenceLabel = field.confidence_label || 
                        (typeof field.confidence === 'string' ? field.confidence : 
                         confidenceScore >= 0.8 ? 'high' : confidenceScore >= 0.5 ? 'medium' : 'low');
                      const isLowConfidence = confidenceLabel === 'low' || (confidenceScore !== null && confidenceScore < 0.5);
                      
                      return (
                        <tr 
                          key={field.field_name} 
                          className={`${idx % 2 === 0 ? 'bg-white' : 'bg-gray-50'} ${isLowConfidence ? 'bg-red-50/50' : ''}`}
                        >
                          <td className="p-3">
                            <input
                              type="checkbox"
                              checked={fieldsToApply[field.field_name] || false}
                              onChange={() => toggleFieldToApply(field.field_name)}
                              className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
                              data-testid={`apply-field-${field.field_name}`}
                            />
                          </td>
                          <td className="p-3 font-medium text-text-primary">
                            {FIELD_LABELS[field.field_name] || field.field_name}
                            {isLowConfidence && (
                              <span className="ml-2 text-red-500" title="Low confidence - please verify">⚠</span>
                            )}
                          </td>
                          <td className="p-3">
                            <span className={`${field.extracted_value ? 'text-text-primary' : 'text-text-muted italic'} ${isLowConfidence ? 'text-red-700' : ''}`}>
                              {field.extracted_value || 'Not found'}
                            </span>
                          </td>
                          <td className="p-3">
                            <span className={`${field.current_value ? 'text-text-primary' : 'text-text-muted italic'}`}>
                              {field.current_value || 'Empty'}
                            </span>
                          </td>
                          <td className="p-3">
                            <div className="flex items-center gap-1">
                              <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                                confidenceLabel === 'high' ? 'bg-green-100 text-green-700' :
                                confidenceLabel === 'medium' ? 'bg-amber-100 text-amber-700' :
                                'bg-red-100 text-red-700'
                              }`}>
                                {confidenceLabel}
                              </span>
                              {confidenceScore !== null && (
                                <span className="text-xs text-text-muted">
                                  {Math.round(confidenceScore * 100)}%
                                </span>
                              )}
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
              
              {/* Quick Actions */}
              <div className="flex gap-2 text-xs">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    const allSelected = {};
                    extractionResult.fields.forEach(f => { allSelected[f.field_name] = true; });
                    setFieldsToApply(allSelected);
                  }}
                >
                  Select All
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    const emptyOnly = {};
                    extractionResult.fields.forEach(f => {
                      emptyOnly[f.field_name] = !f.current_value && !!f.extracted_value;
                    });
                    setFieldsToApply(emptyOnly);
                  }}
                >
                  Select Empty Only
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setFieldsToApply({})}
                >
                  Clear All
                </Button>
              </div>
              
              <DialogFooter className="pt-4">
                <Button
                  variant="outline"
                  onClick={handleDiscardExtraction}
                  disabled={isApplyingExtraction}
                >
                  Discard
                </Button>
                <Button
                  onClick={handleApplyExtraction}
                  disabled={isApplyingExtraction || Object.values(fieldsToApply).filter(Boolean).length === 0}
                  data-testid="apply-extraction-btn"
                >
                  {isApplyingExtraction ? (
                    <><Loader2 className="h-4 w-4 animate-spin mr-2" /> Applying...</>
                  ) : (
                    <>Apply {Object.values(fieldsToApply).filter(Boolean).length} Field(s)</>
                  )}
                </Button>
              </DialogFooter>
            </div>
          ) : (
            <div className="text-center py-8 text-text-muted">
              <p>No extraction data available.</p>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Verify Reference Dialog */}
      <Dialog open={verifyRefDialogOpen} onOpenChange={setVerifyRefDialogOpen}>
        <DialogContent className="sm:max-w-md bg-white">
          <DialogHeader>
            <DialogTitle className="font-heading flex items-center gap-2">
              <Shield className="h-5 w-5 text-primary" />
              Verify Reference {selectedRefNum}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 mt-4">
            <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
              <p className="text-sm text-blue-700">
                <strong>Reference Integrity Rule:</strong> References must match the applicant's CV, 
                or you must document why they differ.
              </p>
            </div>
            
            <div className="space-y-3">
              <label className="block text-sm font-medium">Does this reference match the CV?</label>
              <div className="flex gap-4">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input 
                    type="radio" 
                    name="fromCv" 
                    checked={refFromCv === true}
                    onChange={() => setRefFromCv(true)}
                    className="h-4 w-4 text-primary"
                  />
                  <span>Yes, matches CV</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input 
                    type="radio" 
                    name="fromCv" 
                    checked={refFromCv === false}
                    onChange={() => setRefFromCv(false)}
                    className="h-4 w-4 text-primary"
                  />
                  <span>No, different from CV</span>
                </label>
              </div>
            </div>
            
            {refFromCv === false && (
              <div className="space-y-2">
                <label className="block text-sm font-medium text-red-700">
                  ⚠️ Justification Required
                </label>
                <Textarea
                  value={refOverrideReason}
                  onChange={(e) => setRefOverrideReason(e.target.value)}
                  placeholder="Explain why this reference differs from the CV (min 10 characters)..."
                  className="min-h-[100px] rounded-xl"
                />
                <p className="text-xs text-text-muted">
                  {refOverrideReason.length}/10 characters minimum
                </p>
              </div>
            )}
          </div>
          <DialogFooter className="mt-4">
            <Button variant="outline" onClick={() => setVerifyRefDialogOpen(false)} className="rounded-xl">
              Cancel
            </Button>
            <Button 
              onClick={handleVerifyReference}
              disabled={isVerifyingRef || (!refFromCv && refOverrideReason.length < 10)}
              className="rounded-xl bg-primary hover:bg-primary-hover"
            >
              {isVerifyingRef ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
              Verify Reference
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Explain CV Gap Dialog */}
      <Dialog open={explainGapDialogOpen} onOpenChange={setExplainGapDialogOpen}>
        <DialogContent className="sm:max-w-md bg-white">
          <DialogHeader>
            <DialogTitle className="font-heading flex items-center gap-2">
              <Briefcase className="h-5 w-5 text-purple-600" />
              Explain Employment Gap
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 mt-4">
            {selectedGap && (
              <div className="p-4 bg-amber-50 rounded-lg border border-amber-200">
                <p className="text-sm font-medium text-amber-700">Gap Duration: {selectedGap.gap_duration_days} days</p>
                <p className="text-sm text-amber-600 mt-1">
                  From: {selectedGap.previous_job?.company} ({selectedGap.gap_start})
                </p>
                <p className="text-sm text-amber-600">
                  To: {selectedGap.next_job?.company} ({selectedGap.gap_end})
                </p>
              </div>
            )}
            
            <div className="space-y-2">
              <label className="block text-sm font-medium">
                Explanation for this gap <span className="text-red-500">*</span>
              </label>
              <Textarea
                value={gapExplanation}
                onChange={(e) => setGapExplanation(e.target.value)}
                placeholder="E.g., Career break for family care, further education, travel, etc. (min 10 characters)..."
                className="min-h-[120px] rounded-xl"
              />
              <p className="text-xs text-text-muted">
                {gapExplanation.length}/10 characters minimum
              </p>
            </div>
          </div>
          <DialogFooter className="mt-4">
            <Button variant="outline" onClick={() => setExplainGapDialogOpen(false)} className="rounded-xl">
              Cancel
            </Button>
            <Button 
              onClick={handleExplainGap}
              disabled={isExplainingGap || gapExplanation.length < 10}
              className="rounded-xl bg-purple-600 hover:bg-purple-700"
            >
              {isExplainingGap ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
              Save Explanation
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Document Request Dialog */}
      <Dialog open={requestDocDialogOpen} onOpenChange={(open) => {
        setRequestDocDialogOpen(open);
        if (!open) {
          setDuplicateBlockedInfo(null);
          setIsResendMode(false);
        }
      }}>
        <DialogContent className="sm:max-w-md bg-white">
          <DialogHeader>
            <DialogTitle className="font-heading flex items-center gap-2 text-gray-900">
              <Send className="h-5 w-5 text-blue-600" />
              {isResendMode ? 'Resend Document Request' : 'Request Document'}
            </DialogTitle>
            <DialogDescription>
              Send an email request to {employee?.first_name} for {requestingRequirement?.name}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 mt-4">
            {/* Duplicate blocked warning */}
            {duplicateBlockedInfo && (
              <div className="p-3 bg-amber-50 rounded-lg border border-amber-200">
                <div className="flex items-start gap-2">
                  <AlertTriangle className="h-5 w-5 text-amber-500 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm font-medium text-amber-800">Active Request Exists</p>
                    <p className="text-sm text-amber-700 mt-1">
                      {duplicateBlockedInfo.message}
                    </p>
                    <p className="text-xs text-amber-600 mt-2">
                      Click "Resend" to supersede the previous request and send a new email.
                    </p>
                  </div>
                </div>
              </div>
            )}
            
            {!duplicateBlockedInfo && (
              <div className="p-3 bg-blue-50 rounded-lg border border-blue-100">
                <p className="text-sm text-blue-800">
                  An email will be sent to <strong>{employee?.email}</strong> requesting them to upload this document.
                  {isResendMode && <span className="block mt-1 text-blue-600">This will supersede any previous active request.</span>}
                </p>
              </div>
            )}
            
            <div className="space-y-2">
              <Label className="text-gray-700 font-medium">Additional Message (Optional)</Label>
              <Textarea
                value={requestDocMessage}
                onChange={(e) => setRequestDocMessage(e.target.value)}
                placeholder="Add any specific instructions or notes..."
                rows={3}
                className="bg-white border-[#E4E8EB]"
              />
            </div>
          </div>
          <DialogFooter className="flex gap-2 mt-4">
            <Button 
              variant="outline" 
              onClick={() => {
                setRequestDocDialogOpen(false);
                setDuplicateBlockedInfo(null);
                setIsResendMode(false);
              }}
              className="border-[#E4E8EB]"
            >
              Cancel
            </Button>
            
            {duplicateBlockedInfo ? (
              <Button 
                onClick={handleResendRequest}
                disabled={isRequestingDoc}
                className="bg-amber-600 hover:bg-amber-700 text-white"
                data-testid="resend-request-btn"
              >
                {isRequestingDoc ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <RefreshCw className="h-4 w-4 mr-2" />
                )}
                Resend Request
              </Button>
            ) : (
              <Button 
                onClick={() => handleRequestDocument(isResendMode)}
                disabled={isRequestingDoc}
                className="bg-blue-600 hover:bg-blue-700 text-white"
                data-testid="send-request-btn"
              >
                {isRequestingDoc ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <Send className="h-4 w-4 mr-2" />
                )}
                {isResendMode ? 'Resend Request' : 'Send Request'}
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Send Form Dialog */}
      <Dialog open={sendFormDialogOpen} onOpenChange={setSendFormDialogOpen}>
        <DialogContent className="sm:max-w-md bg-white">
          <DialogHeader>
            <DialogTitle className="font-heading flex items-center gap-2 text-gray-900">
              <FileText className="h-5 w-5 text-primary" />
              Send Form to Employee
            </DialogTitle>
            <DialogDescription>
              Send a form request to {employee?.first_name} via email. They can complete it without logging in.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 mt-4">
            <div className="p-3 bg-blue-50 rounded-lg border border-blue-100">
              <p className="text-sm text-blue-800">
                An email will be sent to <strong>{employee?.email}</strong> with a secure link to complete the form.
              </p>
            </div>
            <div className="space-y-2">
              <Label className="text-gray-700 font-medium">Form Type</Label>
              <Select value={selectedFormType} onValueChange={setSelectedFormType}>
                <SelectTrigger className="bg-white border-[#E4E8EB]">
                  <SelectValue placeholder="Select form to send..." />
                </SelectTrigger>
                <SelectContent>
                  {FORM_OPTIONS.map((form) => (
                    <SelectItem key={form.value} value={form.value}>{form.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label className="text-gray-700 font-medium">Additional Message (Optional)</Label>
              <Textarea
                value={sendFormMessage}
                onChange={(e) => setSendFormMessage(e.target.value)}
                placeholder="Add any specific instructions or context..."
                rows={3}
                className="bg-white border-[#E4E8EB]"
              />
            </div>
          </div>
          <DialogFooter className="flex gap-2 mt-4">
            <Button 
              variant="outline" 
              onClick={() => setSendFormDialogOpen(false)}
              className="border-[#E4E8EB]"
            >
              Cancel
            </Button>
            <Button 
              onClick={handleSendForm}
              disabled={isSendingForm || !selectedFormType}
              className="bg-primary hover:bg-primary-hover text-white"
              data-testid="send-form-btn"
            >
              {isSendingForm ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Send className="h-4 w-4 mr-2" />
              )}
              Send Form
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Reference Request Dialog (NHS-Level Workflow Step 1) */}
      <Dialog open={requestReferenceDialogOpen} onOpenChange={setRequestReferenceDialogOpen}>
        <DialogContent className="sm:max-w-md bg-white">
          <DialogHeader>
            <DialogTitle className="font-heading flex items-center gap-2 text-gray-900">
              <Mail className="h-5 w-5 text-primary" />
              Request Reference from Referee
            </DialogTitle>
            <DialogDescription>
              Send a reference request email directly to the referee. They can complete a secure form without logging in.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 mt-4">
            {selectedRefForRequest && (
              <>
                <div className="p-3 bg-blue-50 rounded-lg border border-blue-100">
                  <p className="text-sm text-blue-800 mb-2">
                    <strong>Referee Details (from application):</strong>
                  </p>
                  <div className="text-sm text-blue-700 space-y-1">
                    <p><strong>Name:</strong> {selectedRefForRequest.declared?.name || 'Not provided'}</p>
                    <p><strong>Email:</strong> {selectedRefForRequest.declared?.email || 'Not provided'}</p>
                    <p><strong>Company:</strong> {selectedRefForRequest.declared?.company || 'Not provided'}</p>
                  </div>
                </div>
                {!selectedRefForRequest.declared?.email && (
                  <div className="p-3 bg-red-50 rounded-lg border border-red-200">
                    <p className="text-sm text-red-800 flex items-center gap-2">
                      <AlertTriangle className="h-4 w-4" />
                      Referee email is required. Please update the employee profile first.
                    </p>
                  </div>
                )}
              </>
            )}
            <div className="space-y-2">
              <Label className="text-gray-700 font-medium">Additional Message (Optional)</Label>
              <Textarea
                value={referenceRequestMessage}
                onChange={(e) => setReferenceRequestMessage(e.target.value)}
                placeholder="Add any specific instructions or context for the referee..."
                rows={3}
                className="bg-white border-[#E4E8EB]"
              />
            </div>
          </div>
          <DialogFooter className="flex gap-2 mt-4">
            <Button 
              variant="outline" 
              onClick={() => setRequestReferenceDialogOpen(false)}
              className="border-[#E4E8EB]"
            >
              Cancel
            </Button>
            <Button 
              onClick={handleSendReferenceRequest}
              disabled={isRequestingReference || !selectedRefForRequest?.declared?.email}
              className="bg-primary hover:bg-primary-hover text-white"
              data-testid="send-reference-request-btn"
            >
              {isRequestingReference ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Send className="h-4 w-4 mr-2" />
              )}
              Send Request
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Review Reference Dialog (NHS-Level Workflow Step 2) */}
      <Dialog open={reviewReferenceDialogOpen} onOpenChange={setReviewReferenceDialogOpen}>
        <DialogContent className="sm:max-w-2xl bg-white max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="font-heading flex items-center gap-2 text-gray-900">
              <ClipboardCheck className="h-5 w-5 text-primary" />
              Review Reference {selectedRefForReview?.reference_num}
            </DialogTitle>
            <DialogDescription>
              Compare declared details with returned response. Document any mismatches before verification.
            </DialogDescription>
          </DialogHeader>
          {selectedRefForReview && (
            <div className="space-y-4 mt-4">
              {/* Mismatch Warning */}
              {selectedRefForReview.mismatch_detected && (
                <div className="p-3 bg-amber-50 rounded-lg border border-amber-200">
                  <p className="text-sm text-amber-800 flex items-center gap-2 font-medium">
                    <AlertTriangle className="h-4 w-4" />
                    Mismatch Detected - Details in returned response differ from application
                  </p>
                </div>
              )}
              
              {/* Side-by-side comparison */}
              <div className="grid grid-cols-2 gap-4">
                {/* Declared (From Application) */}
                <div className="space-y-2">
                  <h4 className="font-medium text-gray-900 text-sm border-b pb-1">Declared (Application)</h4>
                  <div className="text-sm space-y-1.5">
                    <p><span className="text-gray-500">Name:</span> {selectedRefForReview.declared?.name || '-'}</p>
                    <p><span className="text-gray-500">Company:</span> {selectedRefForReview.declared?.company || '-'}</p>
                    <p><span className="text-gray-500">Email:</span> {selectedRefForReview.declared?.email || '-'}</p>
                    <p><span className="text-gray-500">Phone:</span> {selectedRefForReview.declared?.phone || '-'}</p>
                    <p><span className="text-gray-500">Job Title:</span> {selectedRefForReview.declared?.job_title || '-'}</p>
                    <p><span className="text-gray-500">Relationship:</span> {selectedRefForReview.declared?.relationship || '-'}</p>
                  </div>
                </div>
                
                {/* Returned (From Referee) */}
                <div className="space-y-2">
                  <h4 className="font-medium text-gray-900 text-sm border-b pb-1">Returned (Referee Response)</h4>
                  <div className="text-sm space-y-1.5">
                    <p className={selectedRefForReview.mismatch_detected && selectedRefForReview.declared?.name?.toLowerCase() !== selectedRefForReview.returned?.name?.toLowerCase() ? 'text-amber-600 font-medium' : ''}>
                      <span className="text-gray-500">Name:</span> {selectedRefForReview.returned?.name || '-'}
                    </p>
                    <p className={selectedRefForReview.mismatch_detected && selectedRefForReview.declared?.company?.toLowerCase() !== selectedRefForReview.returned?.company?.toLowerCase() ? 'text-amber-600 font-medium' : ''}>
                      <span className="text-gray-500">Company:</span> {selectedRefForReview.returned?.company || '-'}
                    </p>
                    <p><span className="text-gray-500">Email:</span> {selectedRefForReview.returned?.email || '-'}</p>
                    <p><span className="text-gray-500">Phone:</span> {selectedRefForReview.returned?.phone || '-'}</p>
                    <p><span className="text-gray-500">Job Title:</span> {selectedRefForReview.returned?.job_title || '-'}</p>
                    <p><span className="text-gray-500">Relationship:</span> {selectedRefForReview.returned?.relationship || '-'}</p>
                  </div>
                </div>
              </div>
              
              {/* Full Response Summary */}
              {selectedRefForReview.response_data && (
                <div className="space-y-2 mt-4 pt-4 border-t">
                  <h4 className="font-medium text-gray-900 text-sm">Reference Assessment Summary</h4>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <p><span className="text-gray-500">Performance:</span> {selectedRefForReview.response_data.performance_rating || '-'}</p>
                    <p><span className="text-gray-500">Reliability:</span> {selectedRefForReview.response_data.reliability || '-'}</p>
                    <p><span className="text-gray-500">Professionalism:</span> {selectedRefForReview.response_data.professionalism || '-'}</p>
                    <p><span className="text-gray-500">Care Suitable:</span> {selectedRefForReview.response_data.care_vulnerable_suitable || '-'}</p>
                    <p><span className="text-gray-500">Would Re-employ:</span> {selectedRefForReview.response_data.would_re_employ || '-'}</p>
                    <p><span className="text-gray-500">Safeguarding:</span> {selectedRefForReview.response_data.safeguarding_concerns || '-'}</p>
                  </div>
                </div>
              )}
              
              {/* Mismatch Notes (Required if mismatch detected) */}
              {selectedRefForReview.mismatch_detected && (
                <div className="space-y-2 mt-4 pt-4 border-t">
                  <Label className="text-gray-700 font-medium flex items-center gap-1">
                    Mismatch Explanation <span className="text-red-500">*</span>
                  </Label>
                  <p className="text-xs text-gray-500">
                    Document the discrepancy and explain why it is acceptable for verification.
                  </p>
                  <Textarea
                    value={reviewMismatchNotes}
                    onChange={(e) => setReviewMismatchNotes(e.target.value)}
                    placeholder="Explain the mismatch (e.g., 'Name variation is maiden name vs married name, confirmed via phone call with referee on [date]')"
                    rows={3}
                    className="bg-white border-[#E4E8EB]"
                    required
                  />
                </div>
              )}
            </div>
          )}
          <DialogFooter className="flex gap-2 mt-4">
            <Button 
              variant="outline" 
              onClick={() => setReviewReferenceDialogOpen(false)}
              className="border-[#E4E8EB]"
            >
              Cancel
            </Button>
            <Button 
              onClick={handleReviewReference}
              disabled={isReviewingReference || (selectedRefForReview?.mismatch_detected && reviewMismatchNotes.length < 10)}
              className="bg-amber-600 hover:bg-amber-700 text-white"
              data-testid="review-reference-btn"
            >
              {isReviewingReference ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <CheckCircle className="h-4 w-4 mr-2" />
              )}
              Mark as Reviewed
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Employment History Mismatch Details Dialog */}
      <Dialog open={mismatchDialogOpen} onOpenChange={setMismatchDialogOpen}>
        <DialogContent className="sm:max-w-3xl bg-white max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="font-heading flex items-center gap-2 text-gray-900">
              <AlertTriangle className="h-5 w-5 text-amber-600" />
              Employment History vs CV Comparison
            </DialogTitle>
            <DialogDescription>
              Review inconsistencies between structured employment history and CV. Structured history is the source of truth for compliance.
            </DialogDescription>
          </DialogHeader>
          
          {employmentMismatch && (
            <div className="space-y-6 mt-4">
              {/* Summary */}
              <div className="p-3 bg-amber-50 rounded-lg border border-amber-100">
                <p className="text-sm text-amber-800">
                  <strong>{employmentMismatch.mismatch_count}</strong> inconsistencies detected | 
                  <span className="ml-2">Structured roles: {employmentMismatch.structured_history?.length || 0}</span> | 
                  <span className="ml-2">CV roles: {employmentMismatch.cv_extracted_roles?.length || 0}</span>
                </p>
                {employmentMismatch.compared_at && (
                  <p className="text-xs text-amber-600 mt-1">
                    Last compared: {new Date(employmentMismatch.compared_at).toLocaleString()}
                  </p>
                )}
              </div>
              
              {/* Mismatch List */}
              <div className="space-y-3">
                <h4 className="font-medium text-gray-900">Detected Mismatches</h4>
                {employmentMismatch.mismatch_summary?.map((mismatch, idx) => (
                  <div key={idx} className={`p-3 rounded-lg border ${
                    mismatch.severity === 'critical' ? 'bg-red-50 border-red-200' : 'bg-amber-50 border-amber-200'
                  }`}>
                    <p className={`text-sm font-medium ${
                      mismatch.severity === 'critical' ? 'text-red-800' : 'text-amber-800'
                    }`}>
                      {mismatch.type === 'missing_in_structured' && '⚠️ Role in CV not in structured history'}
                      {mismatch.type === 'missing_in_cv' && '⚠️ Role in structured history not in CV'}
                      {mismatch.type === 'date_inconsistency' && '⚠️ Date mismatch'}
                      {mismatch.type === 'overlap_inconsistency' && '⚠️ Overlap inconsistency'}
                    </p>
                    <p className="text-sm text-gray-700 mt-1">{mismatch.description}</p>
                    
                    {/* Show data comparison */}
                    <div className="grid grid-cols-2 gap-4 mt-2 text-xs">
                      {mismatch.structured_data && (
                        <div className="p-2 bg-white rounded border">
                          <p className="font-medium text-gray-600">Structured:</p>
                          <p>{mismatch.structured_data.employer_name || mismatch.structured_data.company}</p>
                          <p className="text-gray-500">{mismatch.structured_data.start_date} - {mismatch.structured_data.end_date || 'Present'}</p>
                        </div>
                      )}
                      {mismatch.cv_data && (
                        <div className="p-2 bg-white rounded border">
                          <p className="font-medium text-gray-600">CV:</p>
                          <p>{mismatch.cv_data.employer}</p>
                          <p className="text-gray-500">{mismatch.cv_data.start_date} - {mismatch.cv_data.end_date || 'Present'}</p>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
              
              {/* Side-by-side View */}
              <div className="grid grid-cols-2 gap-4 pt-4 border-t">
                <div>
                  <h4 className="font-medium text-gray-900 mb-2">Structured Employment History (Source of Truth)</h4>
                  <div className="space-y-2 max-h-60 overflow-y-auto">
                    {employmentMismatch.structured_history?.length > 0 ? (
                      employmentMismatch.structured_history.map((job, idx) => (
                        <div key={idx} className="p-2 bg-green-50 rounded border border-green-200 text-sm">
                          <p className="font-medium">{job.employer_name || job.company}</p>
                          <p className="text-gray-600">{job.job_title || job.role}</p>
                          <p className="text-xs text-gray-500">{job.start_date} - {job.end_date || 'Present'}</p>
                        </div>
                      ))
                    ) : (
                      <p className="text-sm text-gray-500">No structured history recorded</p>
                    )}
                  </div>
                </div>
                <div>
                  <h4 className="font-medium text-gray-900 mb-2">CV Extracted Roles</h4>
                  <div className="space-y-2 max-h-60 overflow-y-auto">
                    {employmentMismatch.cv_extracted_roles?.length > 0 ? (
                      employmentMismatch.cv_extracted_roles.map((role, idx) => (
                        <div key={idx} className="p-2 bg-blue-50 rounded border border-blue-200 text-sm">
                          <p className="font-medium">{role.employer}</p>
                          <p className="text-gray-600">{role.job_title}</p>
                          <p className="text-xs text-gray-500">{role.start_date} - {role.end_date || 'Present'}</p>
                        </div>
                      ))
                    ) : (
                      <p className="text-sm text-gray-500">No roles extracted from CV</p>
                    )}
                  </div>
                </div>
              </div>
              
              {/* Add Review Note */}
              {!isAuditor() && (
                <div className="pt-4 border-t space-y-3">
                  <h4 className="font-medium text-gray-900">Add Review Note</h4>
                  <p className="text-xs text-gray-500">Document your review of this mismatch to proceed with recruitment approval.</p>
                  <Textarea
                    value={mismatchReviewNote}
                    onChange={(e) => setMismatchReviewNote(e.target.value)}
                    placeholder="Explain why this mismatch is acceptable or document actions taken..."
                    rows={3}
                    className="bg-white border-[#E4E8EB]"
                  />
                </div>
              )}
            </div>
          )}
          
          <DialogFooter className="flex gap-2 mt-4">
            <Button 
              variant="outline" 
              onClick={() => setMismatchDialogOpen(false)}
              className="border-[#E4E8EB]"
            >
              Close
            </Button>
            {!isAuditor() && (
              <Button 
                onClick={handleAddMismatchNote}
                disabled={isSubmittingMismatchNote || mismatchReviewNote.length < 5}
                className="bg-amber-600 hover:bg-amber-700 text-white"
                data-testid="add-mismatch-note-btn"
              >
                {isSubmittingMismatchNote ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <CheckCircle className="h-4 w-4 mr-2" />
                )}
                Add Review Note
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
      
      {/* ========== DUAL-ROW COMPLIANCE MODEL DIALOGS (STEP 11) ========== */}
      
      {/* Record Check Dialog */}
      <RecordCheckDialog
        open={recordCheckDialogOpen}
        onClose={() => {
          setRecordCheckDialogOpen(false);
          setRecordCheckType(null);
        }}
        employeeId={employeeId}
        checkType={recordCheckType}
        onComplete={() => {
          fetchData();
          fetchCompliance();
        }}
        // Evidence status props - computed from complianceFile
        hasAcceptedEvidence={(() => {
          if (!complianceFile || !recordCheckType) return false;
          const sectionKey = recordCheckType?.replace('_check', '').replace('_verification', '');
          const section = complianceFile?.requirements?.[sectionKey];
          if (!section?.rows) return false;
          const evidenceRow = section.rows.find(r => r.row_type === 'evidence');
          return (evidenceRow?.counts?.verified || 0) > 0;
        })()}
        hasStampedEvidence={(() => {
          if (!complianceFile || !recordCheckType) return false;
          const sectionKey = recordCheckType?.replace('_check', '').replace('_verification', '');
          const section = complianceFile?.requirements?.[sectionKey];
          if (!section?.rows) return false;
          const evidenceRow = section.rows.find(r => r.row_type === 'evidence');
          const docs = evidenceRow?.documents_preview || [];
          return docs.some(d => d.verification_stamp);
        })()}
        acceptedEvidenceCount={(() => {
          if (!complianceFile || !recordCheckType) return 0;
          const sectionKey = recordCheckType?.replace('_check', '').replace('_verification', '');
          const section = complianceFile?.requirements?.[sectionKey];
          if (!section?.rows) return 0;
          const evidenceRow = section.rows.find(r => r.row_type === 'evidence');
          return evidenceRow?.counts?.verified || 0;
        })()}
      />
    </div>
  );
}
```
--- END EmployeeProfilePage.js ---

---
## FILE: FormCompletionPage.js
## Lines: 372
```javascript
import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Checkbox } from '../../components/ui/checkbox';
import { 
  FileText, CheckCircle, XCircle, Loader2, AlertTriangle,
  ArrowLeft, Send, Home, Clock
} from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

export default function FormCompletionPage() {
  const { token } = useParams();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [formData, setFormData] = useState(null);
  const [formValues, setFormValues] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  useEffect(() => {
    fetchFormData();
  }, [token]);

  const fetchFormData = async () => {
    try {
      const response = await axios.get(`${API}/api/forms/complete/${token}`);
      setFormData(response.data);
      // Pre-fill form with auto-fill data
      setFormValues(response.data.auto_fill_data || {});
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (detail?.includes('expired') || detail?.includes('invalid')) {
        setError({ type: 'expired', message: 'This form link has expired or is no longer valid.' });
      } else {
        setError({ type: 'error', message: detail || 'Failed to load form' });
      }
    } finally {
      setLoading(false);
    }
  };

  const handleFieldChange = (fieldId, value) => {
    setFormValues(prev => ({ ...prev, [fieldId]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Validate required fields
    const template = formData?.form_template;
    const missingFields = [];
    
    template?.sections?.forEach(section => {
      section.fields?.forEach(field => {
        if (field.required && !formValues[field.id]) {
          missingFields.push(field.label || field.id);
        }
      });
    });
    
    if (missingFields.length > 0) {
      toast.error(`Please complete required fields: ${missingFields.slice(0, 3).join(', ')}${missingFields.length > 3 ? '...' : ''}`);
      return;
    }
    
    setSubmitting(true);
    try {
      await axios.post(`${API}/api/forms/complete/${token}`, formValues);
      setSubmitted(true);
      toast.success('Form submitted successfully!');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to submit form');
    } finally {
      setSubmitting(false);
    }
  };

  const renderField = (field, sectionId) => {
    const fieldKey = field.id;
    const value = formValues[fieldKey] || '';
    
    // Handle conditional fields
    if (field.conditional_on) {
      const conditionValue = formValues[field.conditional_on];
      if (conditionValue !== field.conditional_value) {
        return null;
      }
    }
    
    // Skip info fields
    if (field.type === 'info') {
      return (
        <div key={fieldKey} className="p-3 bg-blue-50 rounded-lg border border-blue-100 text-sm text-blue-800">
          {field.label}
        </div>
      );
    }
    
    const isRequired = field.required;
    const isPreFilled = formData?.auto_fill_data?.[fieldKey] !== undefined;
    
    return (
      <div key={fieldKey} className="space-y-2">
        <Label className="text-gray-700 font-medium flex items-center gap-1">
          {field.label}
          {isRequired && <span className="text-red-500">*</span>}
          {isPreFilled && (
            <span className="ml-2 px-2 py-0.5 bg-green-100 text-green-700 text-xs rounded-full">
              Pre-filled
            </span>
          )}
        </Label>
        
        {field.type === 'text' && (
          <Input
            value={value}
            onChange={(e) => handleFieldChange(fieldKey, e.target.value)}
            placeholder={field.placeholder}
            required={isRequired}
            className={`bg-white border-gray-200 ${isPreFilled ? 'border-green-200 bg-green-50/50' : ''}`}
          />
        )}
        
        {field.type === 'textarea' && (
          <Textarea
            value={value}
            onChange={(e) => handleFieldChange(fieldKey, e.target.value)}
            placeholder={field.placeholder}
            required={isRequired}
            rows={3}
            className={`bg-white border-gray-200 ${isPreFilled ? 'border-green-200 bg-green-50/50' : ''}`}
          />
        )}
        
        {field.type === 'date' && (
          <Input
            type="date"
            value={value}
            onChange={(e) => handleFieldChange(fieldKey, e.target.value)}
            required={isRequired}
            className={`bg-white border-gray-200 ${isPreFilled ? 'border-green-200 bg-green-50/50' : ''}`}
          />
        )}
        
        {field.type === 'select' && (
          <Select value={value} onValueChange={(val) => handleFieldChange(fieldKey, val)}>
            <SelectTrigger className="bg-white border-gray-200">
              <SelectValue placeholder={`Select ${field.label}...`} />
            </SelectTrigger>
            <SelectContent>
              {field.options?.map((option) => (
                <SelectItem key={option} value={option}>{option}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
        
        {field.type === 'checkbox' && (
          <div className="flex items-center gap-2">
            <Checkbox
              id={fieldKey}
              checked={!!value}
              onCheckedChange={(checked) => handleFieldChange(fieldKey, checked)}
            />
            <Label htmlFor={fieldKey} className="text-sm text-gray-600 font-normal cursor-pointer">
              {field.label}
            </Label>
          </div>
        )}
        
        {field.type === 'multi_select' && (
          <div className="space-y-2">
            {field.options?.map((option) => (
              <div key={option} className="flex items-center gap-2">
                <Checkbox
                  id={`${fieldKey}-${option}`}
                  checked={(value || []).includes(option)}
                  onCheckedChange={(checked) => {
                    const current = value || [];
                    if (checked) {
                      handleFieldChange(fieldKey, [...current, option]);
                    } else {
                      handleFieldChange(fieldKey, current.filter(v => v !== option));
                    }
                  }}
                />
                <Label htmlFor={`${fieldKey}-${option}`} className="text-sm text-gray-600 font-normal cursor-pointer">
                  {option}
                </Label>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#F8FAFA] flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-12 w-12 animate-spin text-primary mx-auto mb-4" />
          <p className="text-text-muted">Loading form...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-[#F8FAFA] flex items-center justify-center p-4">
        <Card className="max-w-md w-full border-red-200">
          <CardContent className="pt-8 text-center">
            <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
              {error.type === 'expired' ? (
                <Clock className="h-8 w-8 text-red-600" />
              ) : (
                <XCircle className="h-8 w-8 text-red-600" />
              )}
            </div>
            <h2 className="text-xl font-heading font-semibold text-gray-900 mb-2">
              {error.type === 'expired' ? 'Link Expired' : 'Something Went Wrong'}
            </h2>
            <p className="text-gray-600 mb-6">{error.message}</p>
            <p className="text-sm text-gray-500">
              Please contact your recruitment team for a new form link.
            </p>
            <Link to="/">
              <Button variant="outline" className="mt-6">
                <Home className="h-4 w-4 mr-2" />
                Go to Homepage
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (submitted) {
    return (
      <div className="min-h-screen bg-[#F8FAFA] flex items-center justify-center p-4">
        <Card className="max-w-md w-full border-green-200">
          <CardContent className="pt-8 text-center">
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <CheckCircle className="h-8 w-8 text-green-600" />
            </div>
            <h2 className="text-xl font-heading font-semibold text-gray-900 mb-2">
              Form Submitted Successfully
            </h2>
            <p className="text-gray-600 mb-6">
              Thank you, {formData?.employee_name}! Your form has been received and will be reviewed by the team.
            </p>
            <p className="text-sm text-gray-500">
              You can close this page now.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const template = formData?.form_template;
  const preFilledCount = formData?.auto_fill_data ? Object.keys(formData.auto_fill_data).length : 0;

  return (
    <div className="min-h-screen bg-[#F8FAFA]">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-4 py-4">
        <div className="max-w-3xl mx-auto flex items-center gap-3">
          <div className="w-10 h-10 bg-primary/10 rounded-xl flex items-center justify-center">
            <FileText className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h1 className="font-heading font-semibold text-gray-900">
              {template?.name || 'Form Completion'}
            </h1>
            <p className="text-sm text-gray-500">
              For: {formData?.employee_name}
            </p>
          </div>
        </div>
      </header>

      {/* Form Content */}
      <main className="max-w-3xl mx-auto px-4 py-8">
        <form onSubmit={handleSubmit}>
          <div className="space-y-6">
            {/* Pre-fill Notice */}
            {preFilledCount > 0 && (
              <Card className="border-green-200 bg-green-50/50">
                <CardContent className="pt-4 flex items-start gap-3">
                  <CheckCircle className="h-5 w-5 text-green-600 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm font-medium text-green-800">
                      {preFilledCount} field{preFilledCount !== 1 ? 's' : ''} pre-filled from your profile
                    </p>
                    <p className="text-xs text-green-700 mt-1">
                      Fields marked with "Pre-filled" have been automatically populated. Please review and update if needed.
                    </p>
                  </div>
                </CardContent>
              </Card>
            )}
            
            {/* Intro Card */}
            <Card className="border-blue-100 bg-blue-50/50">
              <CardContent className="pt-4">
                <p className="text-sm text-blue-800">
                  Please complete all required fields marked with <span className="text-red-500">*</span>. 
                  Your information will be securely submitted to Osabea Healthcare Solutions.
                </p>
              </CardContent>
            </Card>

            {/* Form Sections */}
            {template?.sections?.map((section) => (
              <Card key={section.id} className="border-gray-200">
                <CardHeader className="pb-2">
                  <CardTitle className="text-lg font-heading">{section.title}</CardTitle>
                  {section.description && (
                    <CardDescription>{section.description}</CardDescription>
                  )}
                </CardHeader>
                <CardContent className="space-y-4">
                  {section.fields?.map((field) => renderField(field, section.id))}
                </CardContent>
              </Card>
            ))}

            {/* Submit Button */}
            <div className="flex justify-end gap-3">
              <Button
                type="submit"
                disabled={submitting}
                className="bg-primary hover:bg-primary-hover text-white px-8"
                data-testid="submit-form-btn"
              >
                {submitting ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Submitting...
                  </>
                ) : (
                  <>
                    <Send className="h-4 w-4 mr-2" />
                    Submit Form
                  </>
                )}
              </Button>
            </div>
          </div>
        </form>
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 px-4 py-4 mt-8">
        <div className="max-w-3xl mx-auto text-center text-sm text-gray-500">
          <p>Osabea Healthcare Solutions - Safer Recruitment</p>
        </div>
      </footer>
    </div>
  );
}
```
--- END FormCompletionPage.js ---

---
## FILE: InterviewFormPanel.js
## Lines: 313
```javascript
import { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { toast } from 'sonner';
import { 
  ClipboardList, Download, CheckCircle, Clock, AlertTriangle,
  Loader2, RefreshCw, User, Calendar, FileText, ChevronDown,
  ChevronRight
} from 'lucide-react';
import { formatBackendDate } from '../../lib/dateUtils';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const DECISION_CONFIG = {
  'Hire': { color: 'bg-green-100 text-green-700', icon: CheckCircle },
  'Strong Hire': { color: 'bg-green-100 text-green-700', icon: CheckCircle },
  'Consider': { color: 'bg-amber-100 text-amber-700', icon: Clock },
  'Maybe': { color: 'bg-amber-100 text-amber-700', icon: Clock },
  'Not Suitable': { color: 'bg-red-100 text-red-700', icon: AlertTriangle },
  'Reject': { color: 'bg-red-100 text-red-700', icon: AlertTriangle }
};

export default function InterviewFormPanel({ employeeId, employeeName }) {
  const [interviews, setInterviews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState(null);
  const [downloading, setDownloading] = useState(null);

  const fetchInterviews = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      
      // Fetch form submissions with requirement_id = interview_record
      const response = await axios.get(`${API}/employees/${employeeId}/forms`, {
        headers: { Authorization: `Bearer ${token}` },
        params: { requirement_id: 'interview_record' }
      });
      
      setInterviews(response.data.forms || response.data || []);
    } catch (error) {
      console.error('Failed to fetch interview records:', error);
      // Try alternative endpoint
      try {
        const token = localStorage.getItem('token');
        const response = await axios.get(`${API}/form-submissions`, {
          headers: { Authorization: `Bearer ${token}` },
          params: { 
            employee_id: employeeId,
            requirement_id: 'interview_record'
          }
        });
        setInterviews(response.data.submissions || response.data || []);
      } catch (err) {
        // Silently fail - interviews are optional
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (employeeId) {
      fetchInterviews();
    }
  }, [employeeId]);

  const handleDownloadPDF = async (submissionId) => {
    try {
      setDownloading(submissionId);
      const token = localStorage.getItem('token');
      
      const response = await axios.get(
        `${API}/form-submissions/${submissionId}/download-pdf`,
        {
          headers: { Authorization: `Bearer ${token}` },
          responseType: 'blob'
        }
      );
      
      // Create download link
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `interview_record_${employeeName?.replace(/\s+/g, '_') || 'employee'}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      toast.success('Interview record downloaded');
    } catch (error) {
      console.error('PDF download failed:', error);
      toast.error('Failed to download interview record');
    } finally {
      setDownloading(null);
    }
  };

  const getDecisionConfig = (decision) => {
    const key = Object.keys(DECISION_CONFIG).find(k => 
      decision?.toLowerCase().includes(k.toLowerCase())
    );
    return key ? DECISION_CONFIG[key] : { color: 'bg-gray-100 text-gray-600', icon: Clock };
  };

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
            <ClipboardList className="h-5 w-5 text-primary" />
            Interview Records
          </span>
          <Button 
            variant="outline" 
            size="sm" 
            onClick={fetchInterviews}
            disabled={loading}
            className="rounded-xl"
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </CardTitle>
        <p className="text-sm text-gray-500 mt-1">
          Completed interview assessments and decisions
        </p>
      </CardHeader>
      <CardContent>
        {interviews.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <ClipboardList className="h-10 w-10 mx-auto mb-3 text-gray-300" />
            <p>No interview records on file</p>
            <p className="text-xs mt-1">Interview records will appear here after completion</p>
          </div>
        ) : (
          <div className="space-y-3">
            {interviews.map((interview, index) => {
              const formData = interview.form_data || {};
              const decision = formData.decision || formData.overall_decision;
              const decisionConfig = getDecisionConfig(decision);
              const DecisionIcon = decisionConfig.icon;
              const isExpanded = expandedId === interview.id;
              
              return (
                <div 
                  key={interview.id || index}
                  className="border rounded-xl overflow-hidden"
                  data-testid={`interview-record-${index}`}
                >
                  {/* Header */}
                  <div 
                    className="flex items-center justify-between p-4 bg-gray-50 cursor-pointer hover:bg-gray-100 transition-colors"
                    onClick={() => setExpandedId(isExpanded ? null : interview.id)}
                  >
                    <div className="flex items-center gap-3">
                      <div className="p-2 rounded-lg bg-primary/10">
                        <ClipboardList className="h-5 w-5 text-primary" />
                      </div>
                      <div>
                        <p className="font-medium text-gray-900">
                          Interview {formData.interview_type || 'Record'}
                        </p>
                        <div className="flex items-center gap-3 text-xs text-gray-500">
                          {formData.interview_date && (
                            <span className="flex items-center gap-1">
                              <Calendar className="h-3 w-3" />
                              {formatBackendDate(formData.interview_date)}
                            </span>
                          )}
                          {formData.interviewer_name && (
                            <span className="flex items-center gap-1">
                              <User className="h-3 w-3" />
                              {formData.interviewer_name}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {decision && (
                        <Badge className={`${decisionConfig.color} flex items-center gap-1`}>
                          <DecisionIcon className="h-3 w-3" />
                          {decision}
                        </Badge>
                      )}
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDownloadPDF(interview.id);
                        }}
                        disabled={downloading === interview.id}
                        className="rounded-lg"
                      >
                        {downloading === interview.id ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Download className="h-4 w-4" />
                        )}
                      </Button>
                      {isExpanded ? (
                        <ChevronDown className="h-4 w-4 text-gray-400" />
                      ) : (
                        <ChevronRight className="h-4 w-4 text-gray-400" />
                      )}
                    </div>
                  </div>

                  {/* Expanded Content */}
                  {isExpanded && (
                    <div className="p-4 border-t bg-white space-y-4">
                      {/* Assessment Summary */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {formData.position_applied && (
                          <div>
                            <p className="text-xs font-medium text-gray-500 mb-1">Position Applied</p>
                            <p className="text-sm text-gray-900">{formData.position_applied}</p>
                          </div>
                        )}
                        {formData.overall_impression && (
                          <div>
                            <p className="text-xs font-medium text-gray-500 mb-1">Overall Impression</p>
                            <p className="text-sm text-gray-900">{formData.overall_impression}</p>
                          </div>
                        )}
                      </div>

                      {/* Strengths */}
                      {formData.strengths && (
                        <div>
                          <p className="text-xs font-medium text-gray-500 mb-1">Strengths</p>
                          <p className="text-sm text-gray-700 bg-green-50 p-3 rounded-lg">
                            {formData.strengths}
                          </p>
                        </div>
                      )}

                      {/* Areas for Development */}
                      {formData.areas_for_development && (
                        <div>
                          <p className="text-xs font-medium text-gray-500 mb-1">Areas for Development</p>
                          <p className="text-sm text-gray-700 bg-amber-50 p-3 rounded-lg">
                            {formData.areas_for_development}
                          </p>
                        </div>
                      )}

                      {/* Notes */}
                      {formData.interviewer_notes && (
                        <div>
                          <p className="text-xs font-medium text-gray-500 mb-1">Interviewer Notes</p>
                          <p className="text-sm text-gray-700 bg-gray-50 p-3 rounded-lg">
                            {formData.interviewer_notes}
                          </p>
                        </div>
                      )}

                      {/* Verification Checks */}
                      <div className="flex flex-wrap gap-2 pt-2 border-t">
                        {formData.right_to_work_verified && (
                          <Badge variant="outline" className="text-xs bg-green-50 text-green-700 border-green-200">
                            <CheckCircle className="h-3 w-3 mr-1" />
                            RTW Verified
                          </Badge>
                        )}
                        {formData.references_discussed && (
                          <Badge variant="outline" className="text-xs bg-blue-50 text-blue-700 border-blue-200">
                            <CheckCircle className="h-3 w-3 mr-1" />
                            References Discussed
                          </Badge>
                        )}
                        {formData.experience_summary && (
                          <Badge variant="outline" className="text-xs bg-purple-50 text-purple-700 border-purple-200">
                            <FileText className="h-3 w-3 mr-1" />
                            Experience Documented
                          </Badge>
                        )}
                      </div>

                      {/* Submission Info */}
                      <div className="text-xs text-gray-400 pt-2 border-t flex items-center gap-4">
                        <span>Submitted: {formatBackendDate(interview.submitted_at || interview.created_at)}</span>
                        {interview.submitted_by_name && (
                          <span>By: {interview.submitted_by_name}</span>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
```
--- END InterviewFormPanel.js ---

---
## FILE: RecordCheckDialog.js
## Lines: 1875
```javascript
import { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '../ui/dialog';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { toast } from 'sonner';
import { Loader2, Shield, Upload, FileText, X, CheckCircle, AlertTriangle, Info, ExternalLink, RefreshCw } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// ==================== AUDIT-READY CHECK METHODS ====================
// These verification methods reflect QA/inspection expectations
// Values are backend enum-compatible, labels are user-friendly
// Organized by requirement type for requirement-aware dropdowns

const CHECK_METHODS = {
  // Right to Work verification methods - UK GOVERNMENT COMPLIANT
  // Values match VALID_RTW_CHECK_METHODS in backend
  right_to_work: [
    { value: 'home_office_online_check', label: 'Home Office Online Check (Share Code)', recommended: true, route: 'home_office_online_check' },
    { value: 'manual_passport_uk_irish', label: 'Manual Check - UK/Irish Passport', route: 'manual_list_a_check' },
    { value: 'manual_list_a_document', label: 'Manual Check - List A Document', route: 'manual_list_a_check' },
    { value: 'manual_list_b_group_1', label: 'Manual Check - List B Group 1 (Time-Limited)', route: 'manual_list_b_group_1_check' },
    { value: 'manual_list_b_group_2_ecs', label: 'Manual Check - List B Group 2 / ECS', route: 'manual_list_b_group_2_check' },
    { value: 'idsp_check', label: 'Digital Verification Service (IDSP)', route: 'digital_verification_service_check' },
    { value: 'ecs_pvn_check', label: 'Employer Checking Service (PVN)', route: 'ecs_pvn_check' }
  ],
  right_to_work_check: [
    { value: 'home_office_online_check', label: 'Home Office Online Check (Share Code)', recommended: true, route: 'home_office_online_check' },
    { value: 'manual_passport_uk_irish', label: 'Manual Check - UK/Irish Passport', route: 'manual_list_a_check' },
    { value: 'manual_list_a_document', label: 'Manual Check - List A Document', route: 'manual_list_a_check' },
    { value: 'manual_list_b_group_1', label: 'Manual Check - List B Group 1 (Time-Limited)', route: 'manual_list_b_group_1_check' },
    { value: 'manual_list_b_group_2_ecs', label: 'Manual Check - List B Group 2 / ECS', route: 'manual_list_b_group_2_check' },
    { value: 'idsp_check', label: 'Digital Verification Service (IDSP)', route: 'digital_verification_service_check' },
    { value: 'ecs_pvn_check', label: 'Employer Checking Service (PVN)', route: 'ecs_pvn_check' }
  ],
  
  // DBS verification methods
  dbs: [
    { value: 'dbs_certificate_review', label: 'DBS Certificate Review' },
    { value: 'dbs_update_service_check', label: 'DBS Update Service Check' },
    { value: 'other', label: 'Other Documented Verification' }
  ],
  dbs_status_check: [
    { value: 'dbs_certificate_review', label: 'DBS Certificate Review' },
    { value: 'dbs_update_service_check', label: 'DBS Update Service Check' },
    { value: 'other', label: 'Other Documented Verification' }
  ],
  
  // Identity verification methods
  identity: [
    { value: 'original_document_seen', label: 'Original Document Seen' },
    { value: 'certified_copy_verified', label: 'Certified Copy Verified' },
    { value: 'digital_id_verification', label: 'Digital ID Verification' },
    { value: 'other', label: 'Other Documented Verification' }
  ],
  identity_verification: [
    { value: 'original_document_seen', label: 'Original Document Seen' },
    { value: 'certified_copy_verified', label: 'Certified Copy Verified' },
    { value: 'digital_id_verification', label: 'Digital ID Verification' },
    { value: 'other', label: 'Other Documented Verification' }
  ],
  
  // Proof of Address verification methods
  proof_of_address: [
    { value: 'original_document_seen', label: 'Original Document Seen' },
    { value: 'uploaded_copy_verified', label: 'Uploaded Copy Verified' },
    { value: 'certified_copy_verified', label: 'Certified Copy Verified' },
    { value: 'other', label: 'Other Documented Verification' }
  ],
  address_verification: [
    { value: 'original_seen', label: 'Original document seen in person' },
    { value: 'uploaded_copy', label: 'Uploaded copy reviewed' },
    { value: 'certified_copy', label: 'Certified copy reviewed' },
    { value: 'other', label: 'Other documented verification' }
  ],
  
  // Reference verification methods
  reference_1: [
    { value: 'email_verified', label: 'Reference verified by email' },
    { value: 'phone_verified', label: 'Reference verified by phone' },
    { value: 'written_reference', label: 'Written reference reviewed' },
    { value: 'employer_portal', label: 'Employer verification portal' },
    { value: 'other', label: 'Other documented verification' }
  ],
  reference_2: [
    { value: 'email_verified', label: 'Reference verified by email' },
    { value: 'phone_verified', label: 'Reference verified by phone' },
    { value: 'written_reference', label: 'Written reference reviewed' },
    { value: 'employer_portal', label: 'Employer verification portal' },
    { value: 'other', label: 'Other documented verification' }
  ],
  
  // Training / Qualifications verification methods
  training: [
    { value: 'certificate_reviewed', label: 'Certificate reviewed' },
    { value: 'provider_portal', label: 'Provider portal checked' },
    { value: 'uploaded_copy', label: 'Uploaded copy reviewed' },
    { value: 'register_checked', label: 'Third-party register checked' },
    { value: 'other', label: 'Other documented verification' }
  ],
  
  // NMC Registration verification (for nurses)
  nmc_registration: [
    { value: 'register_checked', label: 'NMC register checked online' },
    { value: 'pin_verified', label: 'NMC PIN verified' },
    { value: 'certificate_reviewed', label: 'Registration certificate reviewed' },
    { value: 'other', label: 'Other documented verification' }
  ],
  
  // Default fallback for any unrecognized check types
  default: [
    { value: 'original_seen', label: 'Original document seen in person' },
    { value: 'certified_copy', label: 'Certified copy reviewed' },
    { value: 'uploaded_copy', label: 'Uploaded copy reviewed' },
    { value: 'register_checked', label: 'Third-party register checked' },
    { value: 'other', label: 'Other documented verification' }
  ]
};

const CHECK_OUTCOMES = [
  { value: 'verified', label: 'Verified', color: 'text-green-600' },
  { value: 'failed', label: 'Failed', color: 'text-red-600' },
  { value: 'follow_up_required', label: 'Follow-up Required', color: 'text-amber-600' }
];

const SOURCE_STATUS_TYPES = [
  { value: 'share_code', label: 'Share Code Check Result' },
  { value: 'digital_status', label: 'Digital Status (eVisa)' },
  { value: 'settled_status', label: 'Settled Status (EU Settlement Scheme)' },
  { value: 'pre_settled_status', label: 'Pre-Settled Status (EU Settlement Scheme)' },
  { value: 'uk_citizen', label: 'UK Citizen (Passport/Birth Certificate)' },
  { value: 'irish_citizen', label: 'Irish Citizen' },
  { value: 'brp_valid', label: 'BRP - Valid (with online check)' },
  { value: 'brp_expired', label: 'BRP - Expired (online check required)' },
  { value: 'passport_endorsement', label: 'Passport Endorsement' },
  { value: 'work_visa', label: 'Work Visa' },
  { value: 'student_visa', label: 'Student Visa (with work permission)' },
  { value: 'other', label: 'Other' }
];

// RTW-SPECIFIC GUIDANCE based on verification method
const RTW_METHOD_GUIDANCE = {
  home_office_online_check: {
    title: 'Home Office Online Check (Share Code)',
    guidance: 'You MUST verify this online via GOV.UK using the applicant\'s share code.',
    steps: [
      'Ask applicant for their 9-character share code',
      'Visit gov.uk/view-right-to-work',
      'Enter share code and applicant\'s date of birth',
      'Save/screenshot the result as proof'
    ],
    proofRequired: true,
    proofLabel: 'Home Office check result (screenshot/PDF)',
    link: 'https://www.gov.uk/view-right-to-work',
    badgeColor: 'bg-blue-100 text-blue-800 border-blue-200',
    route: 'home_office_online_check'
  },
  manual_passport_uk_irish: {
    title: 'Manual Check - UK/Irish Passport',
    guidance: 'Valid for UK/Irish citizens only. This is a List A document - unlimited right to work.',
    steps: [
      'Check passport is genuine (security features)',
      'Verify photo matches the applicant',
      'Check passport is current or expired (both valid for UK/Irish)',
      'Record passport number and any expiry date',
      'Take a clear copy for records',
      'Apply "Original Document Seen" verification stamp'
    ],
    proofRequired: false,
    stampRequired: true,
    stampType: 'original_seen',
    badgeColor: 'bg-green-100 text-green-800 border-green-200',
    route: 'manual_list_a_check',
    unlimited: true
  },
  manual_list_a_document: {
    title: 'Manual Check - List A Document',
    guidance: 'List A documents prove unlimited right to work in the UK.',
    steps: [
      'Verify document is genuine with security features',
      'Check document relates to the applicant',
      'Acceptable documents: UK/Irish passport (current/expired), Birth certificate + NI proof, Certificate of Registration/Naturalisation + NI proof, Indefinite Leave documents',
      'Take a clear copy for records',
      'Apply appropriate verification stamp'
    ],
    proofRequired: false,
    stampRequired: true,
    stampType: 'original_seen',
    badgeColor: 'bg-green-100 text-green-800 border-green-200',
    route: 'manual_list_a_check',
    unlimited: true
  },
  manual_list_b_group_1: {
    title: 'Manual Check - List B Group 1 (Time-Limited)',
    guidance: 'List B Group 1 documents prove time-limited right to work. FOLLOW-UP REQUIRED before expiry.',
    warning: 'You MUST set a follow-up date before the permission expires. The employee cannot work beyond this date without re-verification.',
    steps: [
      'Check document is genuine with security features',
      'Verify visa/permission is current (not expired)',
      'Record the permission END DATE carefully',
      'Check for any work restrictions',
      'Set follow-up date 28 days BEFORE permission expires',
      'Take a clear copy for records'
    ],
    proofRequired: false,
    stampRequired: true,
    stampType: 'original_seen',
    badgeColor: 'bg-amber-100 text-amber-800 border-amber-200',
    route: 'manual_list_b_group_1_check',
    unlimited: false,
    requiresFollowUp: true
  },
  manual_list_b_group_2_ecs: {
    title: 'Manual Check - List B Group 2 / ECS',
    guidance: 'For applicants with pending immigration applications. Requires Employer Checking Service verification.',
    warning: 'You MUST obtain a Positive Verification Notice (PVN) from the Home Office before employing.',
    steps: [
      'Check Certificate of Application or ARC card',
      'Submit request to Employer Checking Service (ECS)',
      'Wait for Positive Verification Notice (PVN)',
      'Record the PVN reference number',
      'Set 6-month follow-up for repeat ECS check',
      'Do NOT employ without valid PVN'
    ],
    proofRequired: true,
    proofLabel: 'Positive Verification Notice (PVN)',
    link: 'https://www.gov.uk/employee-immigration-employment-status',
    badgeColor: 'bg-purple-100 text-purple-800 border-purple-200',
    route: 'manual_list_b_group_2_check',
    unlimited: false,
    requiresFollowUp: true,
    requiresECS: true
  },
  idsp_check: {
    title: 'Digital Verification Service (IDSP)',
    guidance: 'Use an accredited Identity Service Provider for digital verification of British/Irish passports.',
    steps: [
      'Use an accredited IDSP from the government list',
      'IDSP can only verify British or Irish passports/passport cards',
      'Follow their digital verification process',
      'Retain the IDSP verification certificate',
      'Certificate must confirm document validity'
    ],
    proofRequired: true,
    proofLabel: 'IDSP Verification Certificate',
    badgeColor: 'bg-indigo-100 text-indigo-800 border-indigo-200',
    route: 'digital_verification_service_check',
    unlimited: true
  },
  ecs_pvn_check: {
    title: 'Employer Checking Service (PVN)',
    guidance: 'Use when applicant cannot provide acceptable documents or has pending immigration application.',
    warning: 'You MUST NOT employ someone based solely on their word. A valid PVN is required.',
    steps: [
      'Submit request via gov.uk/employee-immigration-employment-status',
      'Wait for Home Office response (usually within 5 working days)',
      'Receive Positive Verification Notice (PVN)',
      'Record the PVN reference number',
      'Set 6-month follow-up for repeat check',
      'Keep the PVN on file'
    ],
    proofRequired: true,
    proofLabel: 'Positive Verification Notice (PVN)',
    link: 'https://www.gov.uk/employee-immigration-employment-status',
    badgeColor: 'bg-purple-100 text-purple-800 border-purple-200',
    route: 'ecs_pvn_check',
    unlimited: false,
    requiresFollowUp: true
  }
};

// Map check types to requirement IDs for proof file storage
const CHECK_TYPE_TO_REQUIREMENT = {
  right_to_work_check: 'right_to_work_check',
  dbs_status_check: 'dbs_status_check',
  identity_verification: 'identity_verification',
  address_verification: 'address_verification'
};

/**
 * RecordCheckDialog - Dialog for recording employer verification checks
 * 
 * COMPLIANCE-CRITICAL: Requires proof file upload before check can be saved.
 * 
 * Supports:
 * - Right to Work Check
 * - DBS Status Check
 * - Identity Verification
 * - Address Verification
 */
export default function RecordCheckDialog({
  open,
  onClose,
  employeeId,
  checkType,
  onComplete,
  // Evidence status props for validation
  hasAcceptedEvidence = false,
  hasStampedEvidence = false,
  acceptedEvidenceCount = 0
}) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isExtracting, setIsExtracting] = useState(false);
  const [formData, setFormData] = useState({
    method: '',
    checked_at: new Date().toISOString().split('T')[0],
    outcome: 'verified',
    source_status_type: '',
    follow_up_due_at: '',
    review_due_at: '',
    certificate_number: '',
    notes: '',
    // RTW Result Panel fields
    permission_type: '',  // e.g., British Citizen, Skilled Worker, Pre-Settled Status
    permission_start_date: '',
    permission_end_date: '',
    reference_number: '',
    share_code: '',
    restrictions: '',
    hours_limit: '',
    is_indefinite: false,
    follow_up_required: false,
    document_type: '',
    // DBS Result Panel fields
    dbs_level: '',
    certificate_issue_date: '',
    name_on_certificate: '',
    workforce: '',
    update_service_registered: false,
    update_service_status: '',
    last_status_check_date: '',
    update_service_check_result: '',
    recheck_required: true,
    next_recheck_date: '',
    result_status: '',
    information_present: false,
    result_summary: '',
    // Identity Result Panel fields
    id_document_type: '',
    id_full_name_on_document: '',
    id_date_of_birth: '',
    id_document_number: '',
    id_issue_date: '',
    id_expiry_date: '',
    id_nationality: '',
    id_name_matches_application: false,
    id_dob_matches_application: false,
    id_photo_match_confirmed: false,
    // Address Result Panel fields
    address_documents_received_count: 0,
    address_documents_required_count: 2,
    address_verified_documents: [],
    address_extracted_line1: '',
    address_extracted_line2: '',
    address_extracted_city: '',
    address_extracted_postcode: '',
    address_matches_application: false
  });
  
  // Extraction state for RTW and DBS
  const [extractionResult, setExtractionResult] = useState(null);
  const [extractionIssues, setExtractionIssues] = useState([]);
  
  // Proof file state - COMPLIANCE CRITICAL
  const [proofFile, setProofFile] = useState(null);
  const [uploadedProofId, setUploadedProofId] = useState(null);
  const [uploadedProofName, setUploadedProofName] = useState(null);
  const fileInputRef = useRef(null);
  
  const { token } = useAuth();

  // Check if RTW check
  const isRTW = checkType === 'right_to_work_check' || checkType === 'right_to_work';
  
  // Check if DBS check
  const isDBS = checkType === 'dbs_status_check' || checkType === 'dbs';
  
  // Check if Identity check
  const isIdentity = checkType === 'identity_verification' || checkType === 'identity';
  
  // Check if Address check
  const isAddress = checkType === 'address_verification' || checkType === 'proof_of_address';

  // Get methods for this check type with fallback to default
  const methods = CHECK_METHODS[checkType] || CHECK_METHODS.default;
  
  // Get title based on check type
  const getTitle = () => {
    switch (checkType) {
      case 'right_to_work_check': return 'Record Right to Work Check';
      case 'dbs_status_check': return 'Record DBS Status Check';
      case 'identity_verification': return 'Record Identity Verification';
      case 'address_verification': return 'Record Address Verification';
      default: return 'Record Check';
    }
  };

  // Get endpoint based on check type
  const getEndpoint = () => {
    switch (checkType) {
      case 'right_to_work':
      case 'right_to_work_check': 
        return `${API}/employees/${employeeId}/right-to-work/check`;
      case 'dbs':
      case 'dbs_status_check': 
        return `${API}/employees/${employeeId}/dbs/check`;
      case 'identity':
      case 'identity_verification': 
        return `${API}/employees/${employeeId}/identity/check`;
      case 'proof_of_address':
      case 'address_verification': 
        return `${API}/employees/${employeeId}/address/check`;
      default: 
        console.warn(`Unknown check type: ${checkType}`);
        return null;
    }
  };

  // Handle proof file selection - AUTO-EXTRACT for RTW
  const handleFileSelect = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate file type
    const allowedTypes = ['application/pdf', 'image/jpeg', 'image/jpg', 'image/png'];
    if (!allowedTypes.includes(file.type)) {
      toast.error('Invalid file type. Please upload PDF, JPG, or PNG.');
      return;
    }

    // Validate file size (10MB max)
    if (file.size > 10 * 1024 * 1024) {
      toast.error('File too large. Maximum size is 10MB.');
      return;
    }

    setProofFile(file);
    
    // AUTO-EXTRACT: Automatically extract fields when proof file is selected
    if (isRTW) {
      toast.info('Extracting RTW fields from document...', { duration: 2000 });
      await extractRTWFieldsFromFile(file);
    } else if (isDBS) {
      toast.info('Extracting DBS fields from document...', { duration: 2000 });
      await extractDBSFieldsFromFile(file);
    } else if (isIdentity) {
      toast.info('Extracting identity fields from document...', { duration: 2000 });
      await extractIdentityFieldsFromFile(file);
    } else if (isAddress) {
      toast.info('Extracting address fields from document...', { duration: 2000 });
      await extractAddressFieldsFromFile(file);
    }
  };

  // Extract DBS fields from a file using AI Vision
  const extractDBSFieldsFromFile = async (file) => {
    setIsExtracting(true);
    setExtractionResult(null);
    setExtractionIssues([]);

    try {
      // Convert file to base64
      const base64Data = await new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = (e) => resolve(e.target.result.split(',')[1]);
        reader.onerror = () => reject(new Error('Failed to read file'));
        reader.readAsDataURL(file);
      });

      const response = await axios.post(
        `${API}/dbs/extract`,
        {
          file_base64: base64Data,
          file_type: file.type
        },
        {
          headers: { Authorization: `Bearer ${token}` },
          params: { employee_id: employeeId }
        }
      );

      if (response.data?.success && response.data?.extraction) {
        const { fields, issues } = response.data.extraction;
        setExtractionResult(fields);
        setExtractionIssues(issues || []);
        
        // Log extraction results for debugging
        console.log('DBS Extraction result:', { fields, issues });

        // Auto-populate form fields from extraction
        setFormData(prev => ({
          ...prev,
          certificate_number: fields.certificate_number || prev.certificate_number,
          dbs_level: fields.dbs_level || prev.dbs_level,
          certificate_issue_date: fields.issue_date || prev.certificate_issue_date,
          name_on_certificate: fields.name_on_certificate || prev.name_on_certificate,
          workforce: fields.workforce || prev.workforce,
          result_status: fields.result_status || prev.result_status,
          information_present: fields.result_status === 'information_present' || prev.information_present,
          result_summary: fields.result_summary || fields.information_summary || prev.result_summary,
          update_service_status: fields.update_service_status || prev.update_service_status,
          update_service_registered: fields.update_service_status === 'active' || prev.update_service_registered,
          last_status_check_date: fields.last_status_check_date || prev.last_status_check_date,
          update_service_check_result: fields.update_service_check_result || prev.update_service_check_result
        }));

        // Check for blockers
        const blockers = (issues || []).filter(i => i.severity === 'blocker');
        const hasExtractedData = Object.keys(fields).some(k => fields[k] !== null && fields[k] !== undefined);
        
        if (blockers.length > 0) {
          toast.error(`Issue found: ${blockers[0].detail}`);
        } else if (hasExtractedData) {
          toast.success('DBS fields extracted - please review and confirm before saving');
        } else {
          toast.warning('Could not extract DBS data – please fill fields manually', { duration: 5000 });
          setExtractionIssues([...issues, {
            code: 'no_data_extracted',
            detail: 'No DBS fields could be extracted from this document. Please fill in the form manually.',
            severity: 'warning'
          }]);
        }
      } else {
        console.warn('DBS Extraction failed:', response.data);
        toast.warning('Could not extract DBS data – please fill fields manually', { duration: 5000 });
        setExtractionIssues([{
          code: 'extraction_failed',
          detail: response.data?.error || 'Extraction service unavailable. Please fill in the form manually.',
          severity: 'warning'
        }]);
      }
    } catch (err) {
      console.error('DBS Extraction error:', err);
      toast.info('Auto-extraction unavailable. Please fill in fields manually.');
    } finally {
      setIsExtracting(false);
    }
  };

  // Extract Identity fields from a file using AI Vision
  const extractIdentityFieldsFromFile = async (file) => {
    setIsExtracting(true);
    setExtractionResult(null);
    setExtractionIssues([]);

    try {
      const base64Data = await new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = (e) => resolve(e.target.result.split(',')[1]);
        reader.onerror = () => reject(new Error('Failed to read file'));
        reader.readAsDataURL(file);
      });

      const response = await axios.post(
        `${API}/identity/extract`,
        {
          file_base64: base64Data,
          file_type: file.type
        },
        {
          headers: { Authorization: `Bearer ${token}` },
          params: { employee_id: employeeId }
        }
      );

      if (response.data?.success && response.data?.extraction) {
        const { fields, issues } = response.data.extraction;
        setExtractionResult(fields);
        setExtractionIssues(issues || []);
        
        console.log('Identity Extraction result:', { fields, issues });

        setFormData(prev => ({
          ...prev,
          id_document_type: fields.document_type || prev.id_document_type,
          id_full_name_on_document: fields.full_name_on_document || prev.id_full_name_on_document,
          id_date_of_birth: fields.date_of_birth || prev.id_date_of_birth,
          id_document_number: fields.document_number || prev.id_document_number,
          id_issue_date: fields.issue_date || prev.id_issue_date,
          id_expiry_date: fields.expiry_date || prev.id_expiry_date,
          id_nationality: fields.nationality || prev.id_nationality,
          id_name_matches_application: fields.name_matches_application ?? prev.id_name_matches_application,
          id_dob_matches_application: fields.dob_matches_application ?? prev.id_dob_matches_application
        }));

        const blockers = (issues || []).filter(i => i.severity === 'blocker');
        const hasExtractedData = Object.keys(fields).some(k => fields[k] !== null && fields[k] !== undefined);
        
        if (blockers.length > 0) {
          toast.error(`Issue found: ${blockers[0].detail}`);
        } else if (hasExtractedData) {
          toast.success('Identity fields extracted - please review and confirm before saving');
        } else {
          toast.warning('Could not extract identity data – please fill fields manually', { duration: 5000 });
        }
      } else {
        toast.warning('Could not extract identity data – please fill fields manually', { duration: 5000 });
      }
    } catch (err) {
      console.error('Identity Extraction error:', err);
      toast.info('Auto-extraction unavailable. Please fill in fields manually.');
    } finally {
      setIsExtracting(false);
    }
  };

  // Extract Address fields from a file using AI Vision
  const extractAddressFieldsFromFile = async (file) => {
    setIsExtracting(true);
    setExtractionResult(null);
    setExtractionIssues([]);

    try {
      const base64Data = await new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = (e) => resolve(e.target.result.split(',')[1]);
        reader.onerror = () => reject(new Error('Failed to read file'));
        reader.readAsDataURL(file);
      });

      const response = await axios.post(
        `${API}/address/extract`,
        {
          file_base64: base64Data,
          file_type: file.type
        },
        {
          headers: { Authorization: `Bearer ${token}` },
          params: { employee_id: employeeId }
        }
      );

      if (response.data?.success && response.data?.extraction) {
        const { fields, issues } = response.data.extraction;
        setExtractionResult(fields);
        setExtractionIssues(issues || []);
        
        console.log('Address Extraction result:', { fields, issues });

        setFormData(prev => ({
          ...prev,
          address_extracted_line1: fields.address_line1 || prev.address_extracted_line1,
          address_extracted_line2: fields.address_line2 || prev.address_extracted_line2,
          address_extracted_city: fields.city || prev.address_extracted_city,
          address_extracted_postcode: fields.postcode || prev.address_extracted_postcode,
          address_matches_application: fields.address_matches_application ?? prev.address_matches_application
        }));

        const blockers = (issues || []).filter(i => i.severity === 'blocker');
        const hasExtractedData = Object.keys(fields).some(k => fields[k] !== null && fields[k] !== undefined);
        
        if (blockers.length > 0) {
          toast.error(`Issue found: ${blockers[0].detail}`);
        } else if (hasExtractedData) {
          toast.success('Address fields extracted - please review and confirm before saving');
          // Show recency status if available
          if (fields.recency_status?.status === 'outdated') {
            toast.warning(`Document is outdated (${fields.recency_status.days_old} days old)`, { duration: 5000 });
          } else if (fields.recency_status?.status === 'borderline') {
            toast.info(`Document is borderline (${fields.recency_status.days_old} days old)`);
          }
        } else {
          toast.warning('Could not extract address data – please fill fields manually', { duration: 5000 });
        }
      } else {
        toast.warning('Could not extract address data – please fill fields manually', { duration: 5000 });
      }
    } catch (err) {
      console.error('Address Extraction error:', err);
      toast.info('Auto-extraction unavailable. Please fill in fields manually.');
    } finally {
      setIsExtracting(false);
    }
  };

  // Extract RTW fields from a file using AI Vision
  const extractRTWFieldsFromFile = async (file) => {
    setIsExtracting(true);
    setExtractionResult(null);
    setExtractionIssues([]);

    try {
      // Convert file to base64
      const base64Data = await new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = (e) => resolve(e.target.result.split(',')[1]);
        reader.onerror = () => reject(new Error('Failed to read file'));
        reader.readAsDataURL(file);
      });

      const response = await axios.post(
        `${API}/rtw/extract`,
        {
          file_base64: base64Data,
          file_type: file.type
        },
        {
          headers: { Authorization: `Bearer ${token}` },
          params: { employee_id: employeeId }
        }
      );

      if (response.data?.success && response.data?.extraction) {
        const { fields, issues } = response.data.extraction;
        setExtractionResult(fields);
        setExtractionIssues(issues || []);
        
        // Log extraction results for debugging
        console.log('RTW Extraction result:', { fields, issues });

        // Auto-populate form fields from extraction
        setFormData(prev => ({
          ...prev,
          checked_at: fields.check_date || prev.checked_at,
          permission_start_date: fields.permission_start_date || prev.permission_start_date,
          permission_end_date: fields.permission_end_date || prev.permission_end_date,
          reference_number: fields.reference_number || prev.reference_number,
          share_code: fields.share_code || prev.share_code,
          restrictions: fields.restrictions || prev.restrictions,
          hours_limit: fields.hours_limit?.toString() || prev.hours_limit,
          is_indefinite: fields.is_indefinite ?? prev.is_indefinite,
          follow_up_required: fields.requires_followup ?? prev.follow_up_required,
          document_type: fields.document_type || prev.document_type,
          source_status_type: fields.permission_type ? mapPermissionTypeToStatus(fields.permission_type) : prev.source_status_type
        }));

        // Check for blockers
        const blockers = (issues || []).filter(i => i.severity === 'blocker');
        const hasExtractedData = Object.keys(fields).some(k => fields[k] !== null && fields[k] !== undefined);
        
        if (blockers.length > 0) {
          toast.error(`Issue found: ${blockers[0].detail}`);
        } else if (hasExtractedData) {
          toast.success('Fields extracted - please review and confirm before saving');
        } else {
          // No data extracted - show warning
          toast.warning('Could not extract RTW data – please fill fields manually', { duration: 5000 });
          setExtractionIssues([...issues, {
            code: 'no_data_extracted',
            detail: 'No RTW fields could be extracted from this document. Please fill in the form manually.',
            severity: 'warning'
          }]);
        }
      } else {
        // Extraction failed - show clear fallback message
        console.warn('RTW Extraction failed:', response.data);
        toast.warning('Could not extract RTW data – please fill fields manually', { duration: 5000 });
        setExtractionIssues([{
          code: 'extraction_failed',
          detail: response.data?.error || 'Extraction service unavailable. Please fill in the form manually.',
          severity: 'warning'
        }]);
      }
    } catch (err) {
      console.error('Extraction error:', err);
      toast.info('Auto-extraction unavailable. Please fill in fields manually.');
    } finally {
      setIsExtracting(false);
    }
  };

  // Upload proof file to employee_documents
  const uploadProofFile = async () => {
    if (!proofFile) return null;

    setIsUploading(true);
    try {
      const formDataUpload = new FormData();
      formDataUpload.append('file', proofFile);
      formDataUpload.append('requirement_id', CHECK_TYPE_TO_REQUIREMENT[checkType] || checkType);
      formDataUpload.append('document_type', 'verification_proof');
      formDataUpload.append('document_label', `${getTitle()} - Proof`);

      const response = await axios.post(
        `${API}/employees/${employeeId}/upload-document`,
        formDataUpload,
        {
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'multipart/form-data'
          }
        }
      );

      const docId = response.data?.document_id || response.data?.id;
      setUploadedProofId(docId);
      setUploadedProofName(proofFile.name);
      toast.success('Proof file uploaded successfully');
      return docId;
    } catch (err) {
      console.error('Failed to upload proof file:', err);
      toast.error(err.response?.data?.detail || 'Failed to upload proof file');
      return null;
    } finally {
      setIsUploading(false);
    }
  };

  // Remove uploaded proof
  const handleRemoveProof = () => {
    setProofFile(null);
    setUploadedProofId(null);
    setUploadedProofName(null);
    setExtractionResult(null);
    setExtractionIssues([]);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  // Re-extract fields (manual trigger for retry) - works for RTW, DBS, Identity, and Address
  const handleReExtract = async () => {
    if (!proofFile) return;
    if (isRTW) {
      await extractRTWFieldsFromFile(proofFile);
    } else if (isDBS) {
      await extractDBSFieldsFromFile(proofFile);
    } else if (isIdentity) {
      await extractIdentityFieldsFromFile(proofFile);
    } else if (isAddress) {
      await extractAddressFieldsFromFile(proofFile);
    }
  };

  // Map extracted permission type to source_status_type value
  const mapPermissionTypeToStatus = (permissionType) => {
    if (!permissionType) return '';
    const pt = permissionType.toLowerCase();
    if (pt.includes('settled') && !pt.includes('pre')) return 'settled_status';
    if (pt.includes('pre-settled') || pt.includes('presettled')) return 'pre_settled_status';
    if (pt.includes('uk citizen') || pt.includes('british')) return 'uk_citizen';
    if (pt.includes('irish')) return 'irish_citizen';
    if (pt.includes('evisa') || pt.includes('digital')) return 'digital_status';
    if (pt.includes('student')) return 'student_visa';
    if (pt.includes('work visa')) return 'work_visa';
    if (pt.includes('brp')) return 'brp_valid';
    return 'other';
  };

  const handleSubmit = async () => {
    const endpoint = getEndpoint();
    if (!endpoint) {
      toast.error('Invalid check type');
      return;
    }

    // Validation
    if (!formData.method) {
      toast.error('Please select a check method');
      return;
    }

    // RTW-SPECIFIC VALIDATION: Enforce proof upload for online check methods
    const isRTW = checkType === 'right_to_work_check' || checkType === 'right_to_work';
    const onlineCheckMethods = ['home_office_online_check', 'manual_list_b_group_2_ecs', 'ecs_pvn_check', 'idsp_check'];
    const methodGuidance = RTW_METHOD_GUIDANCE[formData.method];
    const requiresProof = isRTW && (onlineCheckMethods.includes(formData.method) || methodGuidance?.proofRequired);
    
    // COMPLIANCE-CRITICAL: Require proof file for online/ECS methods
    if (!proofFile && !uploadedProofId) {
      if (requiresProof) {
        const proofLabel = methodGuidance?.proofLabel || 'verification proof';
        toast.error(`This method requires ${proofLabel}. This is a legal requirement.`);
        return;
      }
      // For manual checks, proof is still required but with different messaging
      toast.error('Upload proof of check before saving. This is required for compliance.');
      return;
    }
    
    // RTW-SPECIFIC: Block expired BRP without online check
    if (isRTW && formData.source_status_type === 'brp_expired') {
      toast.error('Expired BRP is not valid Right to Work evidence. Please use the Home Office Online Check (Share Code) method instead.');
      return;
    }

    setIsSubmitting(true);
    try {
      // Upload proof file first if not already uploaded
      let proofDocId = uploadedProofId;
      if (proofFile && !uploadedProofId) {
        proofDocId = await uploadProofFile();
        if (!proofDocId) {
          setIsSubmitting(false);
          return; // Upload failed, abort
        }
      }

      // Build payload with evidence_document_id linking
      const payload = {
        method: formData.method,
        checked_at: formData.checked_at,
        outcome: formData.outcome,
        notes: formData.notes || null,
        evidence_document_id: proofDocId // CRITICAL: Link check to proof file
      };

      // Add type-specific fields
      if (checkType === 'right_to_work_check' || checkType === 'right_to_work') {
        // Core RTW fields
        payload.source_status_type = formData.source_status_type || null;
        payload.follow_up_due_at = formData.follow_up_due_at || null;
        
        // RTW Result Panel fields (3-layer model)
        payload.permission_type = formData.permission_type || null;  // e.g., British Citizen, Skilled Worker
        payload.permission_start_date = formData.permission_start_date || null;
        payload.permission_end_date = formData.permission_end_date || null;
        payload.reference_number = formData.reference_number || null;
        payload.share_code = formData.share_code || null;
        payload.restrictions = formData.restrictions || null;
        payload.hours_limit = formData.hours_limit ? parseInt(formData.hours_limit) : null;
        payload.is_indefinite = formData.is_indefinite || false;
        payload.follow_up_required = formData.follow_up_required || false;
        payload.document_type = formData.document_type || null;
        
        // Route based on method
        const methodDef = methods.find(m => m.value === formData.method);
        payload.route = methodDef?.route || formData.method;
      }
      
      if (checkType === 'dbs_status_check' || checkType === 'dbs') {
        // DBS Result Panel fields (3-layer model)
        payload.dbs_level = formData.dbs_level || null;
        payload.certificate_number = formData.certificate_number || null;
        payload.certificate_issue_date = formData.certificate_issue_date || null;
        payload.name_on_certificate = formData.name_on_certificate || null;
        payload.workforce = formData.workforce || null;
        
        // Update Service specific
        payload.update_service_registered = formData.update_service_registered || false;
        payload.update_service_status = formData.update_service_status || null;
        payload.last_status_check_date = formData.last_status_check_date || null;
        payload.update_service_check_result = formData.update_service_check_result || null;
        
        // Recheck tracking
        payload.recheck_required = formData.recheck_required !== false; // Default true
        payload.next_recheck_date = formData.next_recheck_date || formData.review_due_at || null;
        payload.review_due_at = formData.review_due_at || formData.next_recheck_date || null;
        
        // Result details
        payload.result_status = formData.result_status || (formData.information_present ? 'information_present' : 'clear');
        payload.information_present = formData.information_present || false;
        payload.result_summary = formData.result_summary || null;
      }
      
      // Identity check payload
      if (checkType === 'identity_verification' || checkType === 'identity') {
        // Identity Result Panel fields (3-layer model)
        payload.document_type = formData.id_document_type || null;
        payload.full_name_on_document = formData.id_full_name_on_document || null;
        payload.date_of_birth = formData.id_date_of_birth || null;
        payload.document_number = formData.id_document_number || null;
        payload.issue_date = formData.id_issue_date || null;
        payload.expiry_date = formData.id_expiry_date || null;
        payload.nationality = formData.id_nationality || null;
        payload.name_matches_application = formData.id_name_matches_application || false;
        payload.dob_matches_application = formData.id_dob_matches_application || false;
        payload.photo_match_confirmed = formData.id_photo_match_confirmed || false;
        payload.proof_document_id = proofDocId;
      }
      
      // Address check payload
      if (checkType === 'address_verification' || checkType === 'proof_of_address') {
        // Address Result Panel fields (3-layer model)
        payload.documents_received_count = formData.address_documents_received_count || 0;
        payload.documents_required_count = formData.address_documents_required_count || 2;
        payload.verified_documents = formData.address_verified_documents || [];
        payload.extracted_address_line1 = formData.address_extracted_line1 || null;
        payload.extracted_address_line2 = formData.address_extracted_line2 || null;
        payload.extracted_city = formData.address_extracted_city || null;
        payload.extracted_postcode = formData.address_extracted_postcode || null;
        payload.address_matches_application = formData.address_matches_application || false;
        payload.proof_document_id = proofDocId;
      }

      await axios.post(endpoint, payload, {
        headers: { Authorization: `Bearer ${token}` }
      });

      toast.success('Verification check recorded with proof');
      if (onComplete) onComplete();
      handleClose();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to record check');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    setFormData({
      method: '',
      checked_at: new Date().toISOString().split('T')[0],
      outcome: 'verified',
      source_status_type: '',
      follow_up_due_at: '',
      review_due_at: '',
      certificate_number: '',
      notes: '',
      // RTW Result Panel fields
      permission_type: '',
      permission_start_date: '',
      permission_end_date: '',
      reference_number: '',
      share_code: '',
      restrictions: '',
      hours_limit: '',
      is_indefinite: false,
      follow_up_required: false,
      document_type: '',
      // DBS Result Panel fields
      dbs_level: '',
      certificate_issue_date: '',
      name_on_certificate: '',
      workforce: '',
      update_service_registered: false,
      update_service_status: '',
      last_status_check_date: '',
      update_service_check_result: '',
      recheck_required: true,
      next_recheck_date: '',
      result_status: '',
      information_present: false,
      result_summary: '',
      // Identity Result Panel fields
      id_document_type: '',
      id_full_name_on_document: '',
      id_date_of_birth: '',
      id_document_number: '',
      id_issue_date: '',
      id_expiry_date: '',
      id_nationality: '',
      id_name_matches_application: false,
      id_dob_matches_application: false,
      id_photo_match_confirmed: false,
      // Address Result Panel fields
      address_documents_received_count: 0,
      address_documents_required_count: 2,
      address_verified_documents: [],
      address_extracted_line1: '',
      address_extracted_line2: '',
      address_extracted_city: '',
      address_extracted_postcode: '',
      address_matches_application: false
    });
    setProofFile(null);
    setUploadedProofId(null);
    setUploadedProofName(null);
    setExtractionResult(null);
    setExtractionIssues([]);
    if (onClose) onClose();
  };

  const hasProof = proofFile || uploadedProofId;

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="bg-white sm:max-w-xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="font-heading flex items-center gap-2">
            <Shield className="h-5 w-5 text-primary" />
            {getTitle()}
          </DialogTitle>
          <DialogDescription>
            Record the employer verification check with proof. Both the check record and proof file are required for compliance.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* EVIDENCE WARNING - Show if no accepted evidence */}
          {!hasAcceptedEvidence && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
              <div className="flex items-start gap-2">
                <AlertTriangle className="h-4 w-4 text-red-600 mt-0.5 flex-shrink-0" />
                <div className="text-sm text-red-800">
                  <p className="font-medium">No accepted evidence</p>
                  <p className="text-xs mt-0.5">You should accept at least one evidence file before recording the verification check.</p>
                </div>
              </div>
            </div>
          )}
          
          {/* STAMP WARNING - Show if evidence accepted but not stamped */}
          {hasAcceptedEvidence && !hasStampedEvidence && (
            <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
              <div className="flex items-start gap-2">
                <Info className="h-4 w-4 text-amber-600 mt-0.5 flex-shrink-0" />
                <div className="text-sm text-amber-800">
                  <p className="font-medium">No stamped evidence</p>
                  <p className="text-xs mt-0.5">Consider applying a verification stamp (Original Seen, Copy Verified, etc.) to accepted evidence files for audit trail.</p>
                </div>
              </div>
            </div>
          )}
          
          {/* COMPLIANCE ALERT */}
          <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
            <div className="flex items-start gap-2">
              <AlertTriangle className="h-4 w-4 text-amber-600 mt-0.5 flex-shrink-0" />
              <div className="text-sm text-amber-800">
                <p className="font-medium">Compliance Requirement</p>
                <p className="text-xs mt-0.5">Upload proof of the check (e.g., Home Office screenshot, DBS Update Service result) before saving.</p>
              </div>
            </div>
          </div>

          {/* PROOF FILE UPLOAD - MANDATORY */}
          <div className="space-y-2">
            <Label className="flex items-center gap-1">
              Proof of Check *
              {hasProof && <CheckCircle className="h-4 w-4 text-green-600" />}
            </Label>
            
            {!hasProof ? (
              <div 
                className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-primary cursor-pointer transition-colors"
                onClick={() => fileInputRef.current?.click()}
              >
                <Upload className="h-8 w-8 mx-auto text-gray-400 mb-2" />
                <p className="text-sm text-gray-600">Click to upload proof file</p>
                <p className="text-xs text-gray-400 mt-1">PDF, JPG, PNG (max 10MB)</p>
                <input
                  ref={fileInputRef}
                  type="file"
                  className="hidden"
                  accept=".pdf,.jpg,.jpeg,.png"
                  onChange={handleFileSelect}
                />
              </div>
            ) : (
              <div className="flex items-center justify-between p-3 bg-green-50 border border-green-200 rounded-lg">
                <div className="flex items-center gap-2">
                  <FileText className="h-5 w-5 text-green-600" />
                  <div>
                    <p className="text-sm font-medium text-green-800">
                      {uploadedProofName || proofFile?.name}
                    </p>
                    <p className="text-xs text-green-600">
                      {uploadedProofId ? 'Uploaded' : 'Ready to upload'}
                    </p>
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleRemoveProof}
                  className="h-8 w-8 p-0 text-red-500 hover:text-red-700 hover:bg-red-50"
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            )}
          </div>

          {/* Extraction Status & Re-extract Option - RTW, DBS, Identity, and Address */}
          {(isRTW || isDBS || isIdentity || isAddress) && hasProof && (
            <div className="space-y-2">
              {/* Extraction in progress */}
              {isExtracting && (
                <div className="flex items-center gap-2 p-3 bg-indigo-50 border border-indigo-200 rounded-lg">
                  <Loader2 className="h-4 w-4 animate-spin text-indigo-600" />
                  <span className="text-sm text-indigo-700">
                    Extracting {isRTW ? 'RTW' : isDBS ? 'DBS' : isIdentity ? 'identity' : 'address'} fields from document...
                  </span>
                </div>
              )}
              
              {/* Extraction complete indicator */}
              {!isExtracting && extractionResult && Object.keys(extractionResult).some(k => extractionResult[k] !== null) && (
                <div className="flex items-center justify-between p-3 bg-green-50 border border-green-200 rounded-lg">
                  <div className="flex items-center gap-2">
                    <CheckCircle className="h-4 w-4 text-green-600" />
                    <span className="text-sm text-green-700">Fields extracted - please review below</span>
                  </div>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={handleReExtract}
                    disabled={isExtracting}
                    className="h-7 px-2 text-xs text-indigo-600 hover:text-indigo-700 hover:bg-indigo-50"
                    data-testid={`${isRTW ? 'rtw' : 'dbs'}-re-extract-btn`}
                  >
                    <RefreshCw className="h-3 w-3 mr-1" />
                    Re-extract
                  </Button>
                </div>
              )}
              
              {/* Manual extract button - only if no extraction yet and not currently extracting */}
              {!isExtracting && !extractionResult && !uploadedProofId && (
                <Button
                  type="button"
                  variant="outline"
                  onClick={handleReExtract}
                  disabled={isExtracting}
                  className="w-full h-9 text-sm bg-indigo-50 border-indigo-200 text-indigo-700 hover:bg-indigo-100"
                  data-testid={`${isRTW ? 'rtw' : 'dbs'}-auto-extract-btn`}
                >
                  <FileText className="h-4 w-4 mr-2" />
                  Extract {isRTW ? 'RTW' : 'DBS'} Fields
                </Button>
              )}
            </div>
          )}

          {/* Extraction Issues Warning */}
          {extractionIssues.length > 0 && (
            <div className="space-y-2">
              {extractionIssues.filter(i => i.severity === 'blocker').map((issue, idx) => (
                <div key={idx} className="p-3 bg-red-50 border border-red-200 rounded-lg">
                  <div className="flex items-start gap-2">
                    <AlertTriangle className="h-4 w-4 text-red-600 mt-0.5 flex-shrink-0" />
                    <div className="text-sm text-red-800">
                      <p className="font-medium">Blocker: {issue.code.replace(/_/g, ' ')}</p>
                      <p className="text-xs mt-0.5">{issue.detail}</p>
                    </div>
                  </div>
                </div>
              ))}
              {extractionIssues.filter(i => i.severity === 'warning').map((issue, idx) => (
                <div key={idx} className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
                  <div className="flex items-start gap-2">
                    <AlertTriangle className="h-4 w-4 text-amber-600 mt-0.5 flex-shrink-0" />
                    <div className="text-sm text-amber-800">
                      <p className="font-medium">Warning: {issue.code.replace(/_/g, ' ')}</p>
                      <p className="text-xs mt-0.5">{issue.detail}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Method */}
          <div className="space-y-2">
            <Label>Check Method *</Label>
            <Select 
              value={formData.method} 
              onValueChange={(v) => setFormData(prev => ({ ...prev, method: v }))}
            >
              <SelectTrigger className="rounded-lg">
                <SelectValue placeholder="Select check method" />
              </SelectTrigger>
              <SelectContent>
                {methods.map(method => (
                  <SelectItem key={method.value} value={method.value}>
                    <span className="flex items-center gap-2">
                      {method.label}
                      {method.recommended && (
                        <span className="text-[10px] bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded">Recommended</span>
                      )}
                    </span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* RTW-SPECIFIC GUIDANCE BOX - Shows method-specific instructions */}
          {(checkType === 'right_to_work_check' || checkType === 'right_to_work') && formData.method && RTW_METHOD_GUIDANCE[formData.method] && (
            <div className={`p-4 rounded-lg border ${RTW_METHOD_GUIDANCE[formData.method].badgeColor || 'bg-blue-50 border-blue-200'}`}>
              <div className="space-y-3">
                <div className="flex items-start gap-2">
                  <Info className="h-4 w-4 mt-0.5 flex-shrink-0" />
                  <div>
                    <p className="font-medium text-sm">{RTW_METHOD_GUIDANCE[formData.method].title}</p>
                    <p className="text-xs mt-1">{RTW_METHOD_GUIDANCE[formData.method].guidance}</p>
                  </div>
                </div>
                
                {/* Warning (e.g., BRP expiry) */}
                {RTW_METHOD_GUIDANCE[formData.method].warning && (
                  <div className="p-2 bg-red-50 border border-red-200 rounded-lg">
                    <div className="flex items-start gap-2">
                      <AlertTriangle className="h-4 w-4 text-red-600 mt-0.5 flex-shrink-0" />
                      <p className="text-xs text-red-700 font-medium">{RTW_METHOD_GUIDANCE[formData.method].warning}</p>
                    </div>
                  </div>
                )}
                
                {/* Steps */}
                {RTW_METHOD_GUIDANCE[formData.method].steps && (
                  <div className="space-y-1">
                    <p className="text-xs font-medium">Steps:</p>
                    <ol className="text-xs space-y-1 list-decimal list-inside">
                      {RTW_METHOD_GUIDANCE[formData.method].steps.map((step, i) => (
                        <li key={i}>{step}</li>
                      ))}
                    </ol>
                  </div>
                )}
                
                {/* GOV.UK Link */}
                {RTW_METHOD_GUIDANCE[formData.method].link && (
                  <a 
                    href={RTW_METHOD_GUIDANCE[formData.method].link} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-xs text-blue-700 hover:text-blue-900 font-medium"
                  >
                    <ExternalLink className="h-3 w-3" />
                    Open GOV.UK verification page
                  </a>
                )}
                
                {/* Proof requirement indicator */}
                {RTW_METHOD_GUIDANCE[formData.method].proofRequired && (
                  <div className="flex items-center gap-2 pt-2 border-t border-current/10">
                    <Upload className="h-3 w-3" />
                    <span className="text-xs font-medium">
                      Required proof: {RTW_METHOD_GUIDANCE[formData.method].proofLabel}
                    </span>
                  </div>
                )}
                
                {/* Stamp requirement indicator */}
                {RTW_METHOD_GUIDANCE[formData.method].stampRequired && (
                  <div className="flex items-center gap-2 pt-2 border-t border-current/10">
                    <CheckCircle className="h-3 w-3" />
                    <span className="text-xs font-medium">
                      Apply verification stamp: "{RTW_METHOD_GUIDANCE[formData.method].stampType === 'original_seen' ? 'Original Document Seen' : 'Copy Verified'}"
                    </span>
                  </div>
                )}
                
                {/* Follow-up requirement indicator */}
                {RTW_METHOD_GUIDANCE[formData.method].requiresFollowUp && (
                  <div className="flex items-center gap-2 pt-2 border-t border-current/10">
                    <AlertTriangle className="h-3 w-3 text-amber-600" />
                    <span className="text-xs font-medium text-amber-700">
                      Time-limited permission - Follow-up date REQUIRED
                    </span>
                  </div>
                )}
                
                {/* Unlimited right indicator */}
                {RTW_METHOD_GUIDANCE[formData.method].unlimited && (
                  <div className="flex items-center gap-2 pt-2 border-t border-current/10">
                    <CheckCircle className="h-3 w-3 text-green-600" />
                    <span className="text-xs font-medium text-green-700">
                      Unlimited right to work - No follow-up required
                    </span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Checked At */}
          <div className="space-y-2">
            <Label>Date Checked *</Label>
            <Input
              type="date"
              value={formData.checked_at}
              onChange={(e) => setFormData(prev => ({ ...prev, checked_at: e.target.value }))}
              className="rounded-lg"
            />
          </div>

          {/* Outcome */}
          <div className="space-y-2">
            <Label>Outcome *</Label>
            <Select 
              value={formData.outcome} 
              onValueChange={(v) => setFormData(prev => ({ ...prev, outcome: v }))}
            >
              <SelectTrigger className="rounded-lg">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {CHECK_OUTCOMES.map(outcome => (
                  <SelectItem key={outcome.value} value={outcome.value}>
                    <span className={outcome.color}>{outcome.label}</span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* RTW-specific: Source Status Type */}
          {checkType === 'right_to_work_check' && (
            <div className="space-y-2">
              <Label>Source Status Type</Label>
              <Select 
                value={formData.source_status_type} 
                onValueChange={(v) => setFormData(prev => ({ ...prev, source_status_type: v }))}
              >
                <SelectTrigger className="rounded-lg">
                  <SelectValue placeholder="Select status type" />
                </SelectTrigger>
                <SelectContent>
                  {SOURCE_STATUS_TYPES.map(type => (
                    <SelectItem key={type.value} value={type.value}>
                      {type.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          {/* RTW-specific: Follow-up Due */}
          {checkType === 'right_to_work_check' && (
            <div className="space-y-2">
              <Label>Follow-up Due Date</Label>
              <Input
                type="date"
                value={formData.follow_up_due_at}
                onChange={(e) => setFormData(prev => ({ ...prev, follow_up_due_at: e.target.value }))}
                className="rounded-lg"
              />
              <p className="text-xs text-text-muted">
                For time-limited permissions, set when the next check is due
              </p>
            </div>
          )}

          {/* ============================================== */}
          {/* RTW RESULT PANEL - Permission Details         */}
          {/* 3-Layer Model: Evidence -> Verification -> Result */}
          {/* ============================================== */}
          {isRTW && (
            <div className="space-y-4 p-4 bg-slate-50 border border-slate-200 rounded-xl">
              <div className="flex items-center gap-2">
                <Shield className="h-4 w-4 text-slate-600" />
                <h4 className="text-sm font-semibold text-slate-800">Right to Work Result</h4>
                {extractionResult && (
                  <span className="text-[10px] px-1.5 py-0.5 bg-indigo-100 text-indigo-700 rounded">
                    AI Extracted
                  </span>
                )}
              </div>
              
              {/* Permission Type - Full width, prominent */}
              <div className="space-y-1">
                <Label className="text-xs font-semibold">Permission Type *</Label>
                <Input
                  value={formData.permission_type}
                  onChange={(e) => setFormData(prev => ({ ...prev, permission_type: e.target.value }))}
                  placeholder="e.g., British Citizen, Skilled Worker, Pre-Settled Status"
                  className="h-9 text-sm rounded-lg"
                  data-testid="rtw-permission-type"
                />
                <p className="text-xs text-text-muted">
                  The immigration status or visa type (e.g., British Citizen, Skilled Worker Visa, Pre-Settled Status)
                </p>
              </div>
              
              <div className="grid grid-cols-2 gap-3">
                {/* Permission Start Date */}
                <div className="space-y-1">
                  <Label className="text-xs">Permission Start</Label>
                  <Input
                    type="date"
                    value={formData.permission_start_date}
                    onChange={(e) => setFormData(prev => ({ ...prev, permission_start_date: e.target.value }))}
                    className="h-8 text-sm rounded-lg"
                    data-testid="rtw-permission-start"
                  />
                </div>
                
                {/* Permission End Date */}
                <div className="space-y-1">
                  <Label className="text-xs">Permission End / Expiry</Label>
                  <Input
                    type="date"
                    value={formData.permission_end_date}
                    onChange={(e) => setFormData(prev => ({ ...prev, permission_end_date: e.target.value }))}
                    className="h-8 text-sm rounded-lg"
                    data-testid="rtw-permission-end"
                  />
                </div>
                
                {/* Reference Number */}
                <div className="space-y-1">
                  <Label className="text-xs">Reference / PVN Number</Label>
                  <Input
                    value={formData.reference_number}
                    onChange={(e) => setFormData(prev => ({ ...prev, reference_number: e.target.value }))}
                    placeholder="e.g., PVN123456"
                    className="h-8 text-sm rounded-lg"
                    data-testid="rtw-reference-number"
                  />
                </div>
                
                {/* Share Code */}
                <div className="space-y-1">
                  <Label className="text-xs">Share Code</Label>
                  <Input
                    value={formData.share_code}
                    onChange={(e) => setFormData(prev => ({ ...prev, share_code: e.target.value.toUpperCase() }))}
                    placeholder="e.g., ABC123DEF"
                    maxLength={9}
                    className="h-8 text-sm rounded-lg font-mono"
                    data-testid="rtw-share-code"
                  />
                </div>
              </div>
              
              {/* Restrictions */}
              <div className="space-y-1">
                <Label className="text-xs">Work Restrictions</Label>
                <Input
                  value={formData.restrictions}
                  onChange={(e) => setFormData(prev => ({ ...prev, restrictions: e.target.value }))}
                  placeholder="e.g., 20 hours per week during term time"
                  className="h-8 text-sm rounded-lg"
                  data-testid="rtw-restrictions"
                />
              </div>
              
              {/* Hours Limit */}
              {formData.restrictions && (
                <div className="space-y-1">
                  <Label className="text-xs">Hours Limit (per week)</Label>
                  <Input
                    type="number"
                    value={formData.hours_limit}
                    onChange={(e) => setFormData(prev => ({ ...prev, hours_limit: e.target.value }))}
                    placeholder="e.g., 20"
                    min={0}
                    max={48}
                    className="h-8 text-sm rounded-lg w-24"
                    data-testid="rtw-hours-limit"
                  />
                </div>
              )}
              
              {/* Checkboxes for status flags */}
              <div className="flex items-center gap-6 pt-2">
                <label className="flex items-center gap-2 text-sm cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.is_indefinite}
                    onChange={(e) => setFormData(prev => ({ ...prev, is_indefinite: e.target.checked }))}
                    className="w-4 h-4 rounded border-gray-300 text-primary focus:ring-primary"
                    data-testid="rtw-is-indefinite"
                  />
                  <span className="text-slate-700">Indefinite right to work</span>
                </label>
                
                <label className="flex items-center gap-2 text-sm cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.follow_up_required}
                    onChange={(e) => setFormData(prev => ({ ...prev, follow_up_required: e.target.checked }))}
                    className="w-4 h-4 rounded border-gray-300 text-amber-500 focus:ring-amber-500"
                    data-testid="rtw-follow-up-required"
                  />
                  <span className="text-slate-700">Follow-up required</span>
                </label>
              </div>
              
              {/* Auto-calculation hint */}
              {formData.permission_end_date && !formData.follow_up_due_at && (
                <div className="p-2 bg-amber-50 border border-amber-200 rounded-lg">
                  <p className="text-xs text-amber-700">
                    <AlertTriangle className="h-3 w-3 inline mr-1" />
                    Permission ends {formData.permission_end_date}. Set a follow-up date 28 days before.
                  </p>
                </div>
              )}
            </div>
          )}

          {/* DBS-specific: Certificate Number */}
          {isDBS && (
            <div className="space-y-2">
              <Label>Certificate Number *</Label>
              <Input
                value={formData.certificate_number}
                onChange={(e) => setFormData(prev => ({ ...prev, certificate_number: e.target.value.replace(/\s/g, '') }))}
                placeholder="12-digit certificate number"
                maxLength={12}
                className="rounded-lg font-mono"
                data-testid="dbs-certificate-number"
              />
              {formData.certificate_number && formData.certificate_number.length !== 12 && (
                <p className="text-xs text-amber-600">Certificate number should be 12 digits</p>
              )}
            </div>
          )}

          {/* DBS-specific: Review Due */}
          {isDBS && (
            <div className="space-y-2">
              <Label>Next Recheck Date</Label>
              <Input
                type="date"
                value={formData.review_due_at || formData.next_recheck_date}
                onChange={(e) => setFormData(prev => ({ ...prev, review_due_at: e.target.value, next_recheck_date: e.target.value }))}
                className="rounded-lg"
                data-testid="dbs-review-due"
              />
              <p className="text-xs text-text-muted">
                Internal policy date for next review (DBS certificates don't have a statutory expiry)
              </p>
            </div>
          )}

          {/* ============================================== */}
          {/* DBS RESULT PANEL - Certificate Details         */}
          {/* 3-Layer Model: Evidence -> Verification -> Result */}
          {/* ============================================== */}
          {isDBS && (
            <div className="space-y-4 p-4 bg-slate-50 border border-slate-200 rounded-xl">
              <div className="flex items-center gap-2">
                <Shield className="h-4 w-4 text-slate-600" />
                <h4 className="text-sm font-semibold text-slate-800">DBS Result</h4>
                {extractionResult && (
                  <span className="text-[10px] px-1.5 py-0.5 bg-indigo-100 text-indigo-700 rounded">
                    AI Extracted
                  </span>
                )}
              </div>
              
              <div className="grid grid-cols-2 gap-3">
                {/* DBS Level */}
                <div className="space-y-1">
                  <Label className="text-xs">DBS Level *</Label>
                  <Select 
                    value={formData.dbs_level} 
                    onValueChange={(v) => setFormData(prev => ({ ...prev, dbs_level: v }))}
                  >
                    <SelectTrigger className="h-8 text-sm rounded-lg" data-testid="dbs-level">
                      <SelectValue placeholder="Select level" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="basic">Basic</SelectItem>
                      <SelectItem value="standard">Standard</SelectItem>
                      <SelectItem value="enhanced">Enhanced</SelectItem>
                      <SelectItem value="enhanced_barred">Enhanced with Barred Lists</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                
                {/* Certificate Issue Date */}
                <div className="space-y-1">
                  <Label className="text-xs">Issue Date</Label>
                  <Input
                    type="date"
                    value={formData.certificate_issue_date}
                    onChange={(e) => setFormData(prev => ({ ...prev, certificate_issue_date: e.target.value }))}
                    className="h-8 text-sm rounded-lg"
                    data-testid="dbs-issue-date"
                  />
                </div>
                
                {/* Name on Certificate */}
                <div className="space-y-1">
                  <Label className="text-xs">Name on Certificate</Label>
                  <Input
                    value={formData.name_on_certificate}
                    onChange={(e) => setFormData(prev => ({ ...prev, name_on_certificate: e.target.value }))}
                    placeholder="As shown on certificate"
                    className="h-8 text-sm rounded-lg"
                    data-testid="dbs-name"
                  />
                </div>
                
                {/* Workforce Type */}
                <div className="space-y-1">
                  <Label className="text-xs">Workforce</Label>
                  <Select 
                    value={formData.workforce} 
                    onValueChange={(v) => setFormData(prev => ({ ...prev, workforce: v }))}
                  >
                    <SelectTrigger className="h-8 text-sm rounded-lg" data-testid="dbs-workforce">
                      <SelectValue placeholder="Select workforce" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="adult">Adult Workforce</SelectItem>
                      <SelectItem value="child">Child Workforce</SelectItem>
                      <SelectItem value="adult_and_child">Adult and Child Workforce</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              
              {/* Update Service Section - only show for dbs_update_service_check method */}
              {formData.method === 'dbs_update_service_check' && (
                <div className="p-3 bg-indigo-50 border border-indigo-200 rounded-lg space-y-3">
                  <div className="flex items-center gap-2">
                    <Shield className="h-3 w-3 text-indigo-600" />
                    <span className="text-xs font-semibold text-indigo-800">Update Service Check</span>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-3">
                    {/* Update Service Status */}
                    <div className="space-y-1">
                      <Label className="text-xs">Update Service Status</Label>
                      <Select 
                        value={formData.update_service_status} 
                        onValueChange={(v) => setFormData(prev => ({ 
                          ...prev, 
                          update_service_status: v,
                          update_service_registered: v === 'active'
                        }))}
                      >
                        <SelectTrigger className="h-8 text-sm rounded-lg" data-testid="dbs-update-status">
                          <SelectValue placeholder="Select status" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="active">Active (Registered)</SelectItem>
                          <SelectItem value="not_registered">Not Registered</SelectItem>
                          <SelectItem value="expired">Expired</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    
                    {/* Last Status Check Date */}
                    <div className="space-y-1">
                      <Label className="text-xs">Check Date</Label>
                      <Input
                        type="date"
                        value={formData.last_status_check_date}
                        onChange={(e) => setFormData(prev => ({ ...prev, last_status_check_date: e.target.value }))}
                        className="h-8 text-sm rounded-lg"
                        data-testid="dbs-last-check-date"
                      />
                    </div>
                  </div>
                  
                  {/* Update Service Check Result */}
                  <div className="space-y-1">
                    <Label className="text-xs">Check Result</Label>
                    <Select 
                      value={formData.update_service_check_result} 
                      onValueChange={(v) => setFormData(prev => ({ ...prev, update_service_check_result: v }))}
                    >
                      <SelectTrigger className="h-8 text-sm rounded-lg" data-testid="dbs-check-result">
                        <SelectValue placeholder="Select result" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="no_change">No change to disclose</SelectItem>
                        <SelectItem value="changed">Changed - New certificate required</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  
                  {/* Warning if changed */}
                  {formData.update_service_check_result === 'changed' && (
                    <div className="p-2 bg-red-50 border border-red-200 rounded-lg">
                      <p className="text-xs text-red-700 font-medium">
                        <AlertTriangle className="h-3 w-3 inline mr-1" />
                        Update Service shows changes. Request a new DBS certificate disclosure.
                      </p>
                    </div>
                  )}
                </div>
              )}
              
              {/* Result Status Section */}
              <div className="space-y-3 pt-3 border-t border-slate-200">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-slate-700">Result Status</span>
                </div>
                
                <div className="grid grid-cols-2 gap-3">
                  {/* Result Status */}
                  <div className="space-y-1">
                    <Label className="text-xs">Clearance Status</Label>
                    <Select 
                      value={formData.result_status || (formData.information_present ? 'information_present' : 'clear')} 
                      onValueChange={(v) => setFormData(prev => ({ 
                        ...prev, 
                        result_status: v,
                        information_present: v === 'information_present'
                      }))}
                    >
                      <SelectTrigger className="h-8 text-sm rounded-lg" data-testid="dbs-result-status">
                        <SelectValue placeholder="Select status" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="clear">Clear - No information</SelectItem>
                        <SelectItem value="information_present">Information Present</SelectItem>
                        <SelectItem value="pending_review">Pending Review</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  
                  {/* Recheck Required checkbox */}
                  <div className="flex items-end">
                    <label className="flex items-center gap-2 text-sm cursor-pointer pb-2">
                      <input
                        type="checkbox"
                        checked={formData.recheck_required !== false}
                        onChange={(e) => setFormData(prev => ({ ...prev, recheck_required: e.target.checked }))}
                        className="w-4 h-4 rounded border-gray-300 text-primary focus:ring-primary"
                        data-testid="dbs-recheck-required"
                      />
                      <span className="text-slate-700 text-xs">Recheck required</span>
                    </label>
                  </div>
                </div>
                
                {/* Information Present Warning */}
                {formData.information_present && (
                  <div className="p-2 bg-amber-50 border border-amber-200 rounded-lg">
                    <p className="text-xs text-amber-700">
                      <AlertTriangle className="h-3 w-3 inline mr-1" />
                      Information/disclosures present on certificate. Include details in notes for risk assessment.
                    </p>
                  </div>
                )}
                
                {/* Result Summary */}
                <div className="space-y-1">
                  <Label className="text-xs">Result Summary</Label>
                  <Input
                    value={formData.result_summary}
                    onChange={(e) => setFormData(prev => ({ ...prev, result_summary: e.target.value }))}
                    placeholder="e.g., Clear - no information disclosed"
                    className="h-8 text-sm rounded-lg"
                    data-testid="dbs-result-summary"
                  />
                </div>
              </div>
              
              {/* Policy reminder */}
              <div className="p-2 bg-blue-50 border border-blue-200 rounded-lg">
                <p className="text-xs text-blue-700">
                  <Info className="h-3 w-3 inline mr-1" />
                  DBS certificates have no statutory expiry. Set a policy-based recheck date (typically 3 years).
                </p>
              </div>
            </div>
          )}

          {/* Notes */}
          <div className="space-y-2">
            <Label>Notes</Label>
            <Textarea
              value={formData.notes}
              onChange={(e) => setFormData(prev => ({ ...prev, notes: e.target.value }))}
              placeholder="Any additional notes about this check..."
              className="rounded-lg min-h-[80px]"
            />
          </div>
        </div>

        <DialogFooter className="gap-2">
          <Button variant="outline" onClick={handleClose} className="rounded-xl">
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={isSubmitting || isUploading || isExtracting || !formData.method || !hasProof}
            className="bg-primary hover:bg-primary-hover text-white rounded-xl"
            data-testid="record-check-submit"
          >
            {isSubmitting || isUploading ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                {isUploading ? 'Uploading...' : 'Saving...'}
              </>
            ) : (
              <>
                <Shield className="h-4 w-4 mr-2" />
                Record Check
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
```
--- END RecordCheckDialog.js ---

---
## FILE: ReferencesPanel.js
## Lines: 381
```javascript
import { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '../ui/dialog';
import { Textarea } from '../ui/textarea';
import { toast } from 'sonner';
import { 
  User, Mail, Phone, Building, Briefcase, Clock, CheckCircle, 
  XCircle, Send, AlertTriangle, Loader2, RefreshCw, Calendar,
  MessageSquare, FileText
} from 'lucide-react';
import { formatBackendDate } from '../../lib/dateUtils';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const STATUS_CONFIG = {
  not_declared: { label: 'Not Declared', color: 'bg-gray-100 text-gray-600', icon: XCircle },
  declared: { label: 'Declared', color: 'bg-blue-100 text-blue-700', icon: Clock },
  sent: { label: 'Request Sent', color: 'bg-amber-100 text-amber-700', icon: Send },
  response_received: { label: 'Response Received', color: 'bg-purple-100 text-purple-700', icon: MessageSquare },
  verified: { label: 'Verified', color: 'bg-green-100 text-green-700', icon: CheckCircle },
  rejected: { label: 'Rejected', color: 'bg-red-100 text-red-700', icon: XCircle }
};

export default function ReferencesPanel({ employeeId, onRefresh }) {
  const [references, setReferences] = useState(null);
  const [loading, setLoading] = useState(true);
  const [sendingRequest, setSendingRequest] = useState(null);
  const [sendDialogOpen, setSendDialogOpen] = useState(false);
  const [selectedRef, setSelectedRef] = useState(null);
  const [customMessage, setCustomMessage] = useState('');

  const fetchReferences = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API}/employees/${employeeId}/references`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setReferences(response.data);
    } catch (error) {
      console.error('Failed to fetch references:', error);
      toast.error('Failed to load references');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (employeeId) {
      fetchReferences();
    }
  }, [employeeId]);

  const handleSendRequest = async (refNum) => {
    try {
      setSendingRequest(refNum);
      const token = localStorage.getItem('token');
      const response = await axios.post(
        `${API}/employees/${employeeId}/send-reference-request?reference_num=${refNum}${customMessage ? `&message=${encodeURIComponent(customMessage)}` : ''}`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      if (response.data.status === 'duplicate') {
        toast.info(response.data.message);
      } else {
        toast.success(`Reference request sent to referee ${refNum}`);
      }
      
      setSendDialogOpen(false);
      setCustomMessage('');
      fetchReferences();
      if (onRefresh) onRefresh();
    } catch (error) {
      const msg = error.response?.data?.detail || 'Failed to send request';
      toast.error(msg);
    } finally {
      setSendingRequest(null);
    }
  };

  const openSendDialog = (refNum) => {
    setSelectedRef(refNum);
    setCustomMessage('');
    setSendDialogOpen(true);
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

  if (!references) {
    return (
      <Card className="border-[#E4E8EB] shadow-sm">
        <CardContent className="py-8 text-center text-gray-500">
          No references data available
        </CardContent>
      </Card>
    );
  }

  return (
    <>
      <Card className="border-[#E4E8EB] shadow-sm">
        <CardHeader>
          <CardTitle className="font-heading text-lg flex items-center justify-between">
            <span className="flex items-center gap-2">
              <User className="h-5 w-5 text-primary" />
              Employment References
            </span>
            <Button 
              variant="outline" 
              size="sm" 
              onClick={fetchReferences}
              disabled={loading}
              className="rounded-xl"
            >
              <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
          </CardTitle>
          <p className="text-sm text-gray-500 mt-1">
            NHS-level reference verification. Minimum 2 verified professional references required.
          </p>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Reference Cards */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {[1, 2].map(refNum => {
              const ref = references.references?.[`reference_${refNum}`];
              const declared = ref?.declared || {};
              const request = ref?.request || {};
              const response = ref?.response || {};
              const verification = ref?.verification || {};
              const status = ref?.status || 'not_declared';
              const config = STATUS_CONFIG[status] || STATUS_CONFIG.not_declared;
              const StatusIcon = config.icon;

              return (
                <div 
                  key={refNum} 
                  className="border rounded-xl overflow-hidden"
                  data-testid={`reference-${refNum}-card`}
                >
                  {/* Header */}
                  <div className="bg-gray-50 px-4 py-3 flex items-center justify-between border-b">
                    <h3 className="font-medium flex items-center gap-2">
                      Reference {refNum}
                    </h3>
                    <Badge className={`${config.color} flex items-center gap-1`}>
                      <StatusIcon className="h-3 w-3" />
                      {config.label}
                    </Badge>
                  </div>

                  {/* Content */}
                  <div className="p-4 space-y-4">
                    {/* Declared Info */}
                    {declared.name ? (
                      <div className="space-y-3">
                        <div className="flex items-start gap-3">
                          <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                            <User className="h-5 w-5 text-primary" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="font-medium text-gray-900">{declared.name}</p>
                            {declared.job_title && (
                              <p className="text-sm text-gray-600 flex items-center gap-1">
                                <Briefcase className="h-3 w-3" />
                                {declared.job_title}
                              </p>
                            )}
                            {declared.organisation && (
                              <p className="text-sm text-gray-600 flex items-center gap-1">
                                <Building className="h-3 w-3" />
                                {declared.organisation}
                              </p>
                            )}
                          </div>
                        </div>

                        {/* Contact Details */}
                        <div className="bg-gray-50 rounded-lg p-3 space-y-1">
                          {declared.email && (
                            <p className="text-sm flex items-center gap-2 text-gray-600">
                              <Mail className="h-3.5 w-3.5 text-gray-400" />
                              <a href={`mailto:${declared.email}`} className="hover:text-primary">
                                {declared.email}
                              </a>
                            </p>
                          )}
                          {declared.phone && (
                            <p className="text-sm flex items-center gap-2 text-gray-600">
                              <Phone className="h-3.5 w-3.5 text-gray-400" />
                              {declared.phone}
                            </p>
                          )}
                          {declared.relationship && (
                            <p className="text-sm text-gray-500">
                              Relationship: {declared.relationship}
                            </p>
                          )}
                          {declared.years_known && (
                            <p className="text-sm text-gray-500">
                              Known for: {declared.years_known} years
                            </p>
                          )}
                          {declared.is_professional !== undefined && (
                            <Badge variant="outline" className="text-xs mt-1">
                              {declared.is_professional ? 'Professional Reference' : 'Personal Reference'}
                            </Badge>
                          )}
                        </div>

                        {/* Request Status */}
                        {request.sent_at && (
                          <div className="bg-amber-50 rounded-lg p-3 border border-amber-200">
                            <p className="text-sm font-medium text-amber-700 flex items-center gap-2">
                              <Send className="h-4 w-4" />
                              Request Sent
                            </p>
                            <p className="text-xs text-amber-600 mt-1">
                              Sent: {formatBackendDate(request.sent_at)}
                            </p>
                            {request.due_at && (
                              <p className="text-xs text-amber-600">
                                Due: {formatBackendDate(request.due_at)}
                              </p>
                            )}
                          </div>
                        )}

                        {/* Response Received */}
                        {response && Object.keys(response).length > 0 && (
                          <div className="bg-purple-50 rounded-lg p-3 border border-purple-200">
                            <p className="text-sm font-medium text-purple-700 flex items-center gap-2">
                              <MessageSquare className="h-4 w-4" />
                              Response Received
                            </p>
                            {response.submitted_at && (
                              <p className="text-xs text-purple-600 mt-1">
                                Received: {formatBackendDate(response.submitted_at)}
                              </p>
                            )}
                          </div>
                        )}

                        {/* Verification Status */}
                        {verification.status === 'verified' && (
                          <div className="bg-green-50 rounded-lg p-3 border border-green-200">
                            <p className="text-sm font-medium text-green-700 flex items-center gap-2">
                              <CheckCircle className="h-4 w-4" />
                              Verified
                            </p>
                            {verification.verified_by && (
                              <p className="text-xs text-green-600 mt-1">
                                By: {verification.verified_by}
                              </p>
                            )}
                            {verification.verified_at && (
                              <p className="text-xs text-green-600">
                                On: {formatBackendDate(verification.verified_at)}
                              </p>
                            )}
                          </div>
                        )}

                        {/* Actions */}
                        {status !== 'verified' && declared.email && (
                          <div className="pt-2 border-t">
                            {status === 'declared' || status === 'sent' ? (
                              <Button
                                size="sm"
                                className="w-full rounded-lg"
                                onClick={() => openSendDialog(refNum)}
                                disabled={sendingRequest === refNum}
                                data-testid={`send-request-btn-${refNum}`}
                              >
                                {sendingRequest === refNum ? (
                                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                ) : (
                                  <Send className="h-4 w-4 mr-2" />
                                )}
                                {status === 'sent' ? 'Resend Request' : 'Send Request'}
                              </Button>
                            ) : status === 'response_received' ? (
                              <Button
                                size="sm"
                                variant="outline"
                                className="w-full rounded-lg"
                                onClick={() => {/* Open verification drawer */}}
                              >
                                <FileText className="h-4 w-4 mr-2" />
                                Review Response
                              </Button>
                            ) : null}
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="text-center py-6 text-gray-500">
                        <AlertTriangle className="h-8 w-8 mx-auto mb-2 text-gray-300" />
                        <p>No referee declared for Reference {refNum}</p>
                        <p className="text-xs mt-1">Referee details should be provided in the application form</p>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Summary */}
          <div className="bg-gray-50 rounded-lg p-4">
            <h4 className="font-medium text-sm mb-2">Reference Requirements</h4>
            <ul className="text-sm text-gray-600 space-y-1">
              <li>- Minimum 2 professional references required</li>
              <li>- References should cover recent employment history</li>
              <li>- At least one must be from the most recent employer</li>
            </ul>
          </div>
        </CardContent>
      </Card>

      {/* Send Request Dialog */}
      <Dialog open={sendDialogOpen} onOpenChange={setSendDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Send Reference Request</DialogTitle>
            <DialogDescription>
              Send an email to the referee requesting them to complete the reference form.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            {selectedRef && references.references?.[`reference_${selectedRef}`]?.declared && (
              <div className="bg-gray-50 rounded-lg p-3">
                <p className="font-medium">{references.references[`reference_${selectedRef}`].declared.name}</p>
                <p className="text-sm text-gray-600">{references.references[`reference_${selectedRef}`].declared.email}</p>
              </div>
            )}
            <div>
              <label className="text-sm font-medium">Custom Message (Optional)</label>
              <Textarea
                value={customMessage}
                onChange={(e) => setCustomMessage(e.target.value)}
                placeholder="Add a personalized message to the referee..."
                className="mt-1"
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setSendDialogOpen(false)}>
              Cancel
            </Button>
            <Button 
              onClick={() => handleSendRequest(selectedRef)}
              disabled={sendingRequest === selectedRef}
            >
              {sendingRequest === selectedRef ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Send className="h-4 w-4 mr-2" />
              )}
              Send Request
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
```
--- END ReferencesPanel.js ---

---
## FILE: RequirementSectionShell.js
## Lines: 79
```javascript
import { ChevronDown, ChevronUp, AlertTriangle } from 'lucide-react';
import { Badge } from '../ui/badge';

/**
 * RequirementSectionShell - Standard shell for all requirement sections
 * 
 * Provides consistent:
 * - Title row with blocking badge
 * - Summary line
 * - Action bar slot
 * - Toggle behavior
 * - Content area when open
 */
export default function RequirementSectionShell({
  title,
  summary,
  blockingLabel = null,
  isOpen,
  onToggle,
  actions,
  children,
  className = '',
  testId
}) {
  return (
    <section 
      className={`rounded-xl border bg-white shadow-sm overflow-hidden ${className}`}
      data-testid={testId || `section-${title.toLowerCase().replace(/\s+/g, '-')}`}
    >
      {/* Header - Always visible */}
      <header 
        className="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-50/50 transition-colors"
        onClick={onToggle}
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="font-semibold text-text-primary">{title}</h3>
            {blockingLabel && (
              <Badge className="text-[10px] px-1.5 py-0.5 bg-red-100 text-red-700 border border-red-200">
                <AlertTriangle className="h-2.5 w-2.5 mr-0.5" />
                {blockingLabel}
              </Badge>
            )}
          </div>
          <p className="text-sm text-text-muted mt-0.5 truncate">{summary}</p>
        </div>

        <div className="flex items-center gap-2 ml-4">
          {/* Action bar slot - stop propagation to prevent toggle */}
          {actions && (
            <div onClick={(e) => e.stopPropagation()}>
              {actions}
            </div>
          )}
          
          {/* Toggle chevron */}
          <button
            className="p-1.5 rounded-lg hover:bg-gray-100 transition-colors"
            aria-expanded={isOpen}
            aria-label={isOpen ? 'Collapse section' : 'Expand section'}
          >
            {isOpen ? (
              <ChevronUp className="h-5 w-5 text-text-muted" />
            ) : (
              <ChevronDown className="h-5 w-5 text-text-muted" />
            )}
          </button>
        </div>
      </header>

      {/* Content - Only when open */}
      {isOpen && (
        <div className="border-t border-gray-100 p-4 bg-gray-50/30">
          {children}
        </div>
      )}
    </section>
  );
}
```
--- END RequirementSectionShell.js ---

---
## FILE: UploadRequirementCard.js
## Lines: 1476
```javascript
import { useState } from 'react';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { toast } from 'sonner';
import { 
  FileText, CheckCircle, Clock, AlertTriangle,
  Eye, Send, RefreshCw, Shield, Download, X, ChevronDown, ChevronUp, Upload as UploadIcon,
  ClipboardCheck, Stamp
} from 'lucide-react';
import RequirementSectionShell from './RequirementSectionShell';
import RequirementActionBar from './RequirementActionBar';
import EvidenceReviewDialog from './EvidenceReviewDialog';
import VerificationStampDialog from './VerificationStampDialog';
import { formatBackendDate } from '../../lib/dateUtils';

// eslint-disable-next-line no-unused-vars
const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Map requirement keys to check types for verification proof storage (used by RecordCheckDialog)
// eslint-disable-next-line no-unused-vars
const REQUIREMENT_TO_CHECK_TYPE = {
  'right_to_work': 'right_to_work_check',
  'dbs': 'dbs_status_check',
  'identity': 'identity_verification',
  'proof_of_address': 'address_verification'
};

/**
 * UploadRequirementCard - Unified DUAL-ROW card for upload-based requirements
 * 
 * Used for: Right to Work, DBS, Identity, Proof of Address
 * 
 * DUAL-ROW MODEL:
 * - Row A: EVIDENCE - Files uploaded by candidate/admin
 *   - Upload, Manage, View files, Download files
 * 
 * - Row B: VERIFICATION - Admin verification proof & check outcome
 *   - Upload verification proof (saved with category: verification_proof)
 *   - Record check (method, outcome, date)
 *   - View proof, Download proof
 *   - Shows: checked_by, checked_at, method, outcome, notes
 */
export default function UploadRequirementCard({
  surface,
  isOpen,
  onToggle,
  onOpenDrawer,
  onUpload,
  onRequest,
  onResend,
  onRecordCheck,
  onUpdateCheck,
  onViewHistory,
  onPreviewFile,
  employeeId,
  onRefresh,
  isAuditor = false,
  // RTW Status - additive, non-breaking prop
  rtwStatus = null
}) {
  // eslint-disable-next-line no-unused-vars
  const { token } = useAuth();
  const [evidenceExpanded, setEvidenceExpanded] = useState(true);
  const [verificationExpanded, setVerificationExpanded] = useState(true);
  
  // Evidence Review Dialog state
  const [reviewDialog, setReviewDialog] = useState({
    isOpen: false,
    file: null
  });
  
  // Verification Stamp Dialog state
  const [stampDialog, setStampDialog] = useState({
    isOpen: false,
    file: null
  });

  if (!surface) return null;

  const {
    key,
    label,
    activeFiles,
    historicalFiles,
    latestRequest,
    authoritativeCheck,
    summary,
    counters,
    requestState,
    rowStatus,
    rules
  } = surface;

  // Determine blocking status
  const isBlocking = rowStatus === 'missing' || rowStatus === 'rejected' || rowStatus === 'replacement_required';
  const blockingLabel = isBlocking ? 'Blocking' : null;

  // Determine available actions
  const hasFiles = counters.active > 0;
  const hasCheck = !!authoritativeCheck;
  const checkVerified = authoritativeCheck?.status === 'verified';
  const hasPendingRequest = requestState === 'requested' || requestState === 'viewed';

  // Get check data details
  const checkData = authoritativeCheck || {};
  const hasVerificationProof = checkData.evidence_document_id && checkData.evidence_document;

  // Handle viewing verification proof
  const handleViewProof = () => {
    if (hasVerificationProof && onPreviewFile) {
      onPreviewFile({
        file_url: `/api/employee-documents/${checkData.evidence_document_id}/file`,
        file_name: checkData.evidence_document.filename || 'Verification Proof'
      });
    }
  };

  // Handle downloading verification proof
  const handleDownloadProof = async () => {
    if (!hasVerificationProof) return;
    
    try {
      const url = `${API}/employee-documents/${checkData.evidence_document_id}/download`;
      const response = await axios.get(url, {
        headers: { Authorization: `Bearer ${token}` },
        responseType: 'blob'
      });
      const blob = new Blob([response.data]);
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = checkData.evidence_document.filename || 'verification_proof';
      link.click();
      URL.revokeObjectURL(link.href);
    } catch (err) {
      toast.error('Download failed');
    }
  };

  // Get method display name
  const getMethodDisplay = (method) => {
    const methods = {
      // RTW Methods
      'home_office_online_check': 'Home Office Online Check',
      'manual_passport_uk_irish': 'Manual Check - UK/Irish Passport',
      'manual_list_a_document': 'Manual Check - List A Document',
      'manual_list_a_check': 'Manual List A Check',
      'manual_list_b_group_1': 'Manual Check - List B Group 1',
      'manual_list_b_group_1_check': 'Manual List B Group 1 Check',
      'manual_list_b_group_2_ecs': 'Manual Check - List B Group 2 / ECS',
      'manual_list_b_group_2_check': 'Manual List B Group 2 Check',
      'idsp_check': 'Digital Verification Service (IDSP)',
      'digital_verification_service_check': 'Digital Verification Service',
      'ecs_pvn_check': 'Employer Checking Service (PVN)',
      'ecs_check': 'Employer Checking Service',
      // DBS Methods
      'update_service_check': 'DBS Update Service Check',
      'manual_certificate_review': 'Manual Certificate Review',
      // Other Methods
      'share_code_online_check': 'Share Code Online Check',
      'manual_passport_check': 'Manual Passport Check',
      'manual_id_verification': 'Manual ID Verification',
      'digital_id_check': 'Digital ID Check',
      'manual_document_check': 'Manual Document Check'
    };
    return methods[method] || method?.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()) || 'Unknown';
  };

  // Get user display name from user ID
  const getUserDisplayName = (userId, fallbackName) => {
    // If we have a name already, use it
    if (fallbackName && !fallbackName.startsWith('user_')) return fallbackName;
    // If it's a user ID, try to format it nicely or return Admin
    if (userId && userId.startsWith('user_')) return 'Admin';
    if (userId) return userId;
    return fallbackName || 'Unknown';
  };

  // Get stamp display info
  const getStampDisplay = (stamp) => {
    const stamps = {
      'original_seen': { label: 'ORIGINAL VERIFIED', className: 'bg-emerald-100 text-emerald-700 border-emerald-200' },
      'copy_verified': { label: 'COPY VERIFIED', className: 'bg-blue-100 text-blue-700 border-blue-200' },
      'online_check': { label: 'ONLINE VERIFIED', className: 'bg-indigo-100 text-indigo-700 border-indigo-200' },
      'not_verified': { label: 'NOT VERIFIED', className: 'bg-red-100 text-red-700 border-red-200' }
    };
    return stamps[stamp] || { label: stamp?.toUpperCase()?.replace(/_/g, ' '), className: 'bg-gray-100 text-gray-600 border-gray-200' };
  };

  // Get outcome display
  const getOutcomeDisplay = (outcome) => {
    const outcomes = {
      'verified': 'Verified',
      'failed': 'Failed',
      'follow_up_required': 'Follow-up Required',
      'awaiting_review': 'Awaiting Review'
    };
    return outcomes[outcome] || outcome?.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()) || 'Unknown';
  };

  return (
    <RequirementSectionShell
      title={label}
      summary={summary}
      blockingLabel={blockingLabel}
      isOpen={isOpen}
      onToggle={onToggle}
      testId={`upload-requirement-${key}`}
      /* REMOVED: Outer card header actions - these are now ONLY in the Evidence row */
      /* Actions were duplicated between header and Evidence row. Each row now has its own actions. */
    >
      <div className="space-y-4">
        {/* ============================================== */}
        {/* ROW A: EVIDENCE SECTION                        */}
        {/* ============================================== */}
        <div 
          className={`border rounded-xl overflow-hidden ${
            hasFiles ? 'border-blue-200 bg-blue-50/20' : 'border-gray-200 bg-gray-50/20'
          }`}
          data-testid={`${key}-evidence-row`}
        >
          {/* Evidence Row Header */}
          <div 
            className="flex items-center justify-between p-3 cursor-pointer hover:bg-white/50 transition-colors"
            onClick={() => setEvidenceExpanded(!evidenceExpanded)}
          >
            <div className="flex items-center gap-3">
              <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                hasFiles ? 'bg-blue-100' : 'bg-gray-100'
              }`}>
                <FileText className={`h-4 w-4 ${hasFiles ? 'text-blue-600' : 'text-gray-400'}`} />
              </div>
              <div>
                <h4 className="text-sm font-semibold text-text-primary">Evidence</h4>
                <p className="text-xs text-text-muted">
                  {/* Computed workflow state based on file status */}
                  {counters.verified > 0 
                    ? `${counters.verified} verified${counters.pendingReview > 0 ? `, ${counters.pendingReview} pending` : ''}`
                    : hasFiles 
                      ? `${counters.active} file${counters.active !== 1 ? 's' : ''} uploaded${counters.pendingReview > 0 ? ' (pending review)' : ''}`
                      : latestRequest && requestState === 'requested'
                        ? 'Request sent - awaiting upload'
                        : 'No files uploaded'
                  }
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {counters.verified > 0 && (
                <Badge className="text-[10px] px-1.5 py-0 bg-green-100 text-green-700 border border-green-200">
                  {counters.verified} verified
                </Badge>
              )}
              {counters.pendingReview > 0 && (
                <Badge className="text-[10px] px-1.5 py-0 bg-amber-100 text-amber-700 border border-amber-200">
                  {counters.pendingReview} pending
                </Badge>
              )}
              {counters.rejected > 0 && (
                <Badge className="text-[10px] px-1.5 py-0 bg-red-100 text-red-700 border border-red-200">
                  {counters.rejected} rejected
                </Badge>
              )}
              <Button variant="ghost" size="sm" className="h-6 w-6 p-0">
                {evidenceExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              </Button>
            </div>
          </div>

          {/* Evidence Row Content */}
          {evidenceExpanded && (
            <div className="p-3 pt-0 space-y-3">
              {/* Evidence Files List */}
              {activeFiles.length > 0 ? (
                <div className="space-y-2">
                  {activeFiles.slice(0, 3).map((file) => (
                    <div 
                      key={file.file_id || file.id}
                      className="flex items-center justify-between p-3 bg-white border border-gray-200 rounded-lg"
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <FileText className="h-4 w-4 text-gray-400 flex-shrink-0" />
                        <div className="min-w-0">
                          <p className="text-sm font-medium text-text-primary truncate">
                            {file.file_name || file.original_filename || 'Document'}
                          </p>
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-xs text-text-muted">
                              {formatBackendDate(file.uploaded_at, { format: 'medium' })}
                              {file.uploaded_by && ` • ${file.uploaded_by}`}
                            </span>
                            {/* Verification Stamp Badge - ENHANCED */}
                            {file.verification_stamp && (() => {
                              const stampInfo = getStampDisplay(file.verification_stamp);
                              return (
                                <div className="flex flex-col">
                                  <Badge 
                                    className={`text-[9px] px-1.5 py-0.5 font-semibold ${stampInfo.className}`}
                                    data-testid={`${key}-stamp-badge-${file.file_id || file.id}`}
                                  >
                                    <Stamp className="h-2.5 w-2.5 mr-1" />
                                    {stampInfo.label}
                                  </Badge>
                                  {(file.verification_stamp_by_name || file.verification_stamp_at) && (
                                    <span className="text-[9px] text-text-muted mt-0.5">
                                      {file.verification_stamp_by_name && `by ${file.verification_stamp_by_name}`}
                                      {file.verification_stamp_at && ` • ${formatBackendDate(file.verification_stamp_at, { format: 'short' })}`}
                                    </span>
                                  )}
                                </div>
                              );
                            })()}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {file.verified ? (
                          <Badge className="text-[10px] px-1.5 py-0 bg-green-100 text-green-700 border border-green-200">
                            <CheckCircle className="h-2.5 w-2.5 mr-0.5" />
                            Accepted
                          </Badge>
                        ) : file.status === 'rejected' ? (
                          <Badge className="text-[10px] px-1.5 py-0 bg-red-100 text-red-700 border border-red-200">
                            <X className="h-2.5 w-2.5 mr-0.5" />
                            Rejected
                          </Badge>
                        ) : file.extraction_status?.status === 'awaiting_review' ? (
                          <Badge className="text-[10px] px-1.5 py-0 bg-purple-100 text-purple-700 border border-purple-200">
                            <Clock className="h-2.5 w-2.5 mr-0.5" />
                            Extraction pending
                          </Badge>
                        ) : (
                          <Badge className="text-[10px] px-1.5 py-0 bg-amber-100 text-amber-700 border border-amber-200">
                            <Clock className="h-2.5 w-2.5 mr-0.5" />
                            Pending Review
                          </Badge>
                        )}
                        
                        {/* Apply Verification Stamp button - show different states */}
                        {!isAuditor && file.verified && (
                          <Button
                            size="sm"
                            variant={file.verification_stamp ? "ghost" : "outline"}
                            className={`h-7 px-2 text-xs ${
                              file.verification_stamp 
                                ? 'text-gray-500 hover:text-gray-700 hover:bg-gray-100' 
                                : 'text-indigo-600 border-indigo-200 hover:bg-indigo-50'
                            }`}
                            onClick={() => setStampDialog({ isOpen: true, file })}
                            title={file.verification_stamp ? "Edit verification stamp" : "Apply verification stamp"}
                            data-testid={`${key}-stamp-btn-${file.file_id || file.id}`}
                          >
                            <Stamp className="h-3 w-3 mr-1" />
                            {file.verification_stamp ? 'Edit Stamp' : 'Stamp'}
                          </Button>
                        )}
                        
                        {/* Review Evidence button - visible for non-verified files */}
                        {!isAuditor && !file.verified && file.status !== 'rejected' && (
                          <Button
                            size="sm"
                            variant="outline"
                            className="h-7 px-2 text-xs text-teal-600 border-teal-200 hover:bg-teal-50"
                            onClick={() => setReviewDialog({ isOpen: true, file })}
                            title="Review evidence"
                            data-testid={`${key}-evidence-review-${file.file_id || file.id}`}
                          >
                            <ClipboardCheck className="h-3 w-3 mr-1" />
                            Review
                          </Button>
                        )}
                        
                        {/* View file button */}
                        {onPreviewFile && (
                          <Button
                            size="sm"
                            variant="ghost"
                            className="h-7 w-7 p-0 text-gray-500 hover:text-blue-600"
                            onClick={() => onPreviewFile({
                              file_url: `/api/employee-documents/${file.file_id || file.id}/file`,
                              file_name: file.file_name || file.original_filename || 'Document'
                            })}
                            title="View file"
                            data-testid={`${key}-evidence-view-${file.file_id || file.id}`}
                          >
                            <Eye className="h-3.5 w-3.5" />
                          </Button>
                        )}
                      </div>
                    </div>
                  ))}
                  {activeFiles.length > 3 && (
                    <button 
                      onClick={onOpenDrawer}
                      className="text-sm text-blue-600 hover:text-blue-700 font-medium"
                    >
                      + {activeFiles.length - 3} more file{activeFiles.length - 3 !== 1 ? 's' : ''}
                    </button>
                  )}
                </div>
              ) : (
                <div className="p-4 bg-white border border-gray-200 rounded-lg text-center">
                  <UploadIcon className="h-6 w-6 text-gray-300 mx-auto mb-2" />
                  <p className="text-sm text-text-muted">No evidence files uploaded</p>
                  {rules?.minimumFilesRequired && (
                    <p className="text-xs text-text-muted mt-1">
                      {rules.minimumFilesRequired} file{rules.minimumFilesRequired !== 1 ? 's' : ''} required
                    </p>
                  )}
                </div>
              )}

              {/* Evidence Upload/Request Actions */}
              {!isAuditor && (
                <div className="flex items-center gap-2 pt-2 border-t border-gray-100">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={onUpload}
                    className="h-8 text-xs rounded-lg"
                    data-testid={`${key}-evidence-upload-btn`}
                  >
                    <UploadIcon className="h-3.5 w-3.5 mr-1" />
                    Upload
                  </Button>
                  {!hasPendingRequest && !hasFiles && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={onRequest}
                      className="h-8 text-xs rounded-lg"
                      data-testid={`${key}-evidence-request-btn`}
                    >
                      <Send className="h-3.5 w-3.5 mr-1" />
                      Request
                    </Button>
                  )}
                  {hasPendingRequest && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={onResend}
                      className="h-8 text-xs rounded-lg text-amber-600 border-amber-200 hover:bg-amber-50"
                      data-testid={`${key}-evidence-resend-btn`}
                    >
                      <RefreshCw className="h-3.5 w-3.5 mr-1" />
                      Resend
                    </Button>
                  )}
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={onOpenDrawer}
                    className="h-8 text-xs rounded-lg"
                    data-testid={`${key}-evidence-manage-btn`}
                  >
                    <Eye className="h-3.5 w-3.5 mr-1" />
                    Manage
                  </Button>
                </div>
              )}

              {/* Request Status - ONLY show if no evidence uploaded yet */}
              {latestRequest && !hasFiles && (
                <div className={`p-3 rounded-lg border ${
                  requestState === 'submitted' ? 'bg-green-50 border-green-200' :
                  requestState === 'viewed' ? 'bg-purple-50 border-purple-200' :
                  requestState === 'requested' ? 'bg-blue-50 border-blue-200' :
                  'bg-gray-50 border-gray-200'
                }`}>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Send className={`h-4 w-4 ${
                        requestState === 'submitted' ? 'text-green-600' :
                        requestState === 'viewed' ? 'text-purple-600' :
                        requestState === 'requested' ? 'text-blue-600' :
                        'text-gray-500'
                      }`} />
                      <span className="text-sm font-medium">
                        {requestState === 'submitted' ? 'Response submitted' :
                         requestState === 'viewed' ? 'Request viewed' :
                         requestState === 'requested' ? 'Request sent' :
                         requestState === 'replacement_requested' ? 'Replacement requested' :
                         'Request status'}
                      </span>
                    </div>
                    {latestRequest.sent_at && (
                      <span className="text-xs text-text-muted">
                        {formatBackendDate(latestRequest.sent_at, { format: 'relative' })}
                      </span>
                    )}
                  </div>
                  {latestRequest.viewed_at && requestState !== 'viewed' && (
                    <p className="text-xs text-text-muted mt-1 ml-6">
                      Viewed {formatBackendDate(latestRequest.viewed_at, { format: 'relative' })}
                    </p>
                  )}
                  {latestRequest.reminder_count > 0 && (
                    <p className="text-xs text-amber-600 mt-1 ml-6">
                      {latestRequest.reminder_count} reminder{latestRequest.reminder_count !== 1 ? 's' : ''} sent
                    </p>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        {/* ============================================== */}
        {/* ROW B: VERIFICATION SECTION                    */}
        {/* ============================================== */}
        <div 
          className={`border rounded-xl overflow-hidden ${
            checkVerified ? 'border-green-200 bg-green-50/20' : 
            hasCheck ? 'border-amber-200 bg-amber-50/20' : 
            'border-red-200 bg-red-50/20'
          }`}
          data-testid={`${key}-verification-row`}
        >
          {/* Verification Row Header */}
          <div 
            className="flex items-center justify-between p-3 cursor-pointer hover:bg-white/50 transition-colors"
            onClick={() => setVerificationExpanded(!verificationExpanded)}
          >
            <div className="flex items-center gap-3">
              <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                checkVerified ? 'bg-green-100' : hasCheck ? 'bg-amber-100' : 'bg-red-100'
              }`}>
                <Shield className={`h-4 w-4 ${
                  checkVerified ? 'text-green-600' : hasCheck ? 'text-amber-600' : 'text-red-600'
                }`} />
              </div>
              <div>
                <h4 className="text-sm font-semibold text-text-primary">Verification</h4>
                <p className="text-xs text-text-muted">
                  {checkVerified 
                    ? 'Check verified'
                    : hasCheck 
                      ? `Check recorded: ${getOutcomeDisplay(checkData.outcome)}`
                      : 'No check recorded'
                  }
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Badge className={`text-[10px] px-1.5 py-0 ${
                checkVerified ? 'bg-green-100 text-green-700 border border-green-200' :
                hasCheck ? 'bg-amber-100 text-amber-700 border border-amber-200' :
                'bg-red-100 text-red-700 border border-red-200'
              }`}>
                {checkVerified ? 'Verified' : hasCheck ? 'Recorded' : 'Required'}
              </Badge>
              <Button variant="ghost" size="sm" className="h-6 w-6 p-0">
                {verificationExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              </Button>
            </div>
          </div>

          {/* Verification Row Content */}
          {verificationExpanded && (
            <div className="p-3 pt-0 space-y-3">
              {/* Verification Check Details */}
              {hasCheck ? (
                <div className="space-y-3">
                  {/* Check Record Details */}
                  <div className={`p-3 rounded-lg border ${
                    checkVerified ? 'bg-green-50 border-green-200' : 'bg-amber-50 border-amber-200'
                  }`}>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                      {/* Method */}
                      <div>
                        <p className="text-xs text-text-muted uppercase tracking-wide">Method</p>
                        <p className="font-medium text-text-primary">{getMethodDisplay(checkData.method)}</p>
                      </div>
                      
                      {/* Outcome */}
                      <div>
                        <p className="text-xs text-text-muted uppercase tracking-wide">Outcome</p>
                        <p className={`font-medium ${
                          checkData.outcome === 'verified' ? 'text-green-600' :
                          checkData.outcome === 'failed' ? 'text-red-600' : 'text-amber-600'
                        }`}>
                          {getOutcomeDisplay(checkData.outcome)}
                        </p>
                      </div>
                      
                      {/* Checked At */}
                      <div>
                        <p className="text-xs text-text-muted uppercase tracking-wide">Checked</p>
                        <p className="font-medium text-text-primary">
                          {formatBackendDate(checkData.checked_at, { format: 'medium' })}
                        </p>
                      </div>
                      
                      {/* Checked By */}
                      <div>
                        <p className="text-xs text-text-muted uppercase tracking-wide">Checked By</p>
                        <p className="font-medium text-text-primary">
                          {getUserDisplayName(checkData.checked_by, checkData.checked_by_name)}
                        </p>
                      </div>
                    </div>
                    
                    {/* Notes */}
                    {checkData.notes && (
                      <div className="mt-3 pt-3 border-t border-gray-200">
                        <p className="text-xs text-text-muted uppercase tracking-wide mb-1">Notes</p>
                        <p className="text-sm text-text-primary">{checkData.notes}</p>
                      </div>
                    )}
                    
                    {/* RTW Result Details - COMPREHENSIVE DISPLAY */}
                    {key === 'right_to_work' && (
                      <div className="mt-3 pt-3 border-t border-gray-200 space-y-3">
                        <div className="flex items-center gap-2">
                          <Shield className="h-4 w-4 text-slate-600" />
                          <p className="text-xs text-text-muted uppercase tracking-wide font-semibold">Right to Work Result</p>
                        </div>
                        
                        <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-sm">
                          {/* Permission Type - NEW */}
                          {(checkData.permission_type || checkData.document_type) && (
                            <div className="col-span-2 md:col-span-3">
                              <p className="text-xs text-text-muted">Permission Type</p>
                              <p className="font-semibold text-text-primary text-base">
                                {checkData.permission_type || checkData.document_type || 'Not specified'}
                              </p>
                            </div>
                          )}
                          
                          {/* Route / Check Type */}
                          {(checkData.route || checkData.method) && (
                            <div>
                              <p className="text-xs text-text-muted">Verification Method</p>
                              <p className="font-medium text-text-primary">{getMethodDisplay(checkData.route || checkData.method)}</p>
                            </div>
                          )}
                          
                          {/* Permission Start */}
                          {checkData.permission_start_date && (
                            <div>
                              <p className="text-xs text-text-muted">Permission Start</p>
                              <p className="font-medium text-text-primary">{formatBackendDate(checkData.permission_start_date, { format: 'medium' })}</p>
                            </div>
                          )}
                          
                          {/* Permission End / Expiry OR No Expiry */}
                          <div>
                            <p className="text-xs text-text-muted">Permission Expiry</p>
                            {checkData.is_indefinite ? (
                              <p className="font-medium text-green-700 flex items-center gap-1">
                                <CheckCircle className="h-3 w-3" />
                                No Expiry (Indefinite)
                              </p>
                            ) : checkData.permission_end_date ? (
                              <p className={`font-medium ${
                                rtwStatus?.status === 'expired' ? 'text-red-700' :
                                rtwStatus?.days_until_expiry <= 30 ? 'text-red-600' :
                                rtwStatus?.days_until_expiry <= 90 ? 'text-amber-600' :
                                'text-text-primary'
                              }`}>
                                {formatBackendDate(checkData.permission_end_date, { format: 'medium' })}
                                {rtwStatus?.days_until_expiry !== null && rtwStatus?.days_until_expiry > 0 && (
                                  <span className="text-xs ml-1">({rtwStatus.days_until_expiry}d)</span>
                                )}
                              </p>
                            ) : (
                              <p className="font-medium text-amber-600">Not specified</p>
                            )}
                          </div>
                          
                          {/* Share Code */}
                          {checkData.share_code && (
                            <div>
                              <p className="text-xs text-text-muted">Share Code</p>
                              <p className="font-medium text-text-primary font-mono text-xs bg-slate-100 px-2 py-1 rounded inline-block">{checkData.share_code}</p>
                            </div>
                          )}
                          
                          {/* Reference Number / PVN */}
                          {checkData.reference_number && (
                            <div>
                              <p className="text-xs text-text-muted">Reference / PVN</p>
                              <p className="font-medium text-text-primary font-mono text-xs bg-slate-100 px-2 py-1 rounded inline-block">{checkData.reference_number}</p>
                            </div>
                          )}
                          
                          {/* Checked Date */}
                          {checkData.checked_at && (
                            <div>
                              <p className="text-xs text-text-muted">Verification Date</p>
                              <p className="font-medium text-text-primary">{formatBackendDate(checkData.checked_at, { format: 'medium' })}</p>
                            </div>
                          )}
                        </div>
                        
                        {/* Follow-up Section - Critical for time-limited permissions */}
                        {(checkData.follow_up_required || checkData.follow_up_due_at) && (
                          <div className={`p-3 rounded-lg border ${
                            rtwStatus?.days_until_followup !== null && rtwStatus?.days_until_followup < 0 ? 'bg-red-50 border-red-200' :
                            rtwStatus?.days_until_followup !== null && rtwStatus?.days_until_followup <= 30 ? 'bg-amber-50 border-amber-200' :
                            'bg-blue-50 border-blue-200'
                          }`}>
                            <div className="flex items-center gap-2 mb-1">
                              <Clock className={`h-4 w-4 ${
                                rtwStatus?.days_until_followup !== null && rtwStatus?.days_until_followup < 0 ? 'text-red-600' :
                                rtwStatus?.days_until_followup !== null && rtwStatus?.days_until_followup <= 30 ? 'text-amber-600' :
                                'text-blue-600'
                              }`} />
                              <span className={`text-xs font-semibold ${
                                rtwStatus?.days_until_followup !== null && rtwStatus?.days_until_followup < 0 ? 'text-red-800' :
                                rtwStatus?.days_until_followup !== null && rtwStatus?.days_until_followup <= 30 ? 'text-amber-800' :
                                'text-blue-800'
                              }`}>
                                {rtwStatus?.days_until_followup !== null && rtwStatus?.days_until_followup < 0 ? 'FOLLOW-UP OVERDUE' : 'Follow-up Required'}
                              </span>
                            </div>
                            <p className={`text-sm font-medium ${
                              rtwStatus?.days_until_followup !== null && rtwStatus?.days_until_followup < 0 ? 'text-red-700' :
                              rtwStatus?.days_until_followup !== null && rtwStatus?.days_until_followup <= 30 ? 'text-amber-700' :
                              'text-blue-700'
                            }`}>
                              {checkData.follow_up_due_at ? (
                                <>
                                  Due: {formatBackendDate(checkData.follow_up_due_at, { format: 'medium' })}
                                  {rtwStatus?.days_until_followup !== null && (
                                    <span className="ml-2">
                                      ({rtwStatus.days_until_followup < 0 ? `${Math.abs(rtwStatus.days_until_followup)} days overdue` : `${rtwStatus.days_until_followup} days`})
                                    </span>
                                  )}
                                </>
                              ) : (
                                'Date not set'
                              )}
                            </p>
                          </div>
                        )}
                        
                        {/* Restrictions - Full width */}
                        {checkData.restrictions && (
                          <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
                            <div className="flex items-center gap-2 mb-1">
                              <AlertTriangle className="h-4 w-4 text-amber-600" />
                              <span className="text-xs font-semibold text-amber-800">Work Restrictions Apply</span>
                            </div>
                            <p className="text-sm text-amber-700">{checkData.restrictions}</p>
                            {checkData.hours_limit && (
                              <p className="text-xs text-amber-600 mt-1 font-medium">Hours limit: {checkData.hours_limit} per week</p>
                            )}
                          </div>
                        )}
                        
                        {/* Status flags */}
                        <div className="flex flex-wrap gap-2">
                          {checkData.is_indefinite && (
                            <div className="flex items-center gap-1 px-2 py-1 bg-green-50 border border-green-200 rounded-lg">
                              <CheckCircle className="h-3 w-3 text-green-600" />
                              <span className="text-xs font-medium text-green-700">Indefinite right to work</span>
                            </div>
                          )}
                          {checkData.outcome === 'verified' && !checkData.is_indefinite && (
                            <div className="flex items-center gap-1 px-2 py-1 bg-blue-50 border border-blue-200 rounded-lg">
                              <Shield className="h-3 w-3 text-blue-600" />
                              <span className="text-xs font-medium text-blue-700">Time-limited permission</span>
                            </div>
                          )}
                        </div>
                        
                        {/* RTW STATUS ALERT PANEL - Non-breaking, read-only display */}
                        {rtwStatus && rtwStatus.status !== 'not_verified' && (
                          <div className={`p-3 rounded-lg border ${
                            rtwStatus.status_color === 'green' ? 'bg-green-50 border-green-200' :
                            rtwStatus.status_color === 'amber' ? 'bg-amber-50 border-amber-200' :
                            rtwStatus.status_color === 'red' ? 'bg-red-50 border-red-200' :
                            'bg-gray-50 border-gray-200'
                          }`}>
                            <div className="flex items-center justify-between mb-2">
                              <div className="flex items-center gap-2">
                                {rtwStatus.status_color === 'green' && <CheckCircle className="h-4 w-4 text-green-600" />}
                                {rtwStatus.status_color === 'amber' && <AlertTriangle className="h-4 w-4 text-amber-600" />}
                                {rtwStatus.status_color === 'red' && <AlertTriangle className="h-4 w-4 text-red-600" />}
                                <span className={`text-sm font-semibold ${
                                  rtwStatus.status_color === 'green' ? 'text-green-800' :
                                  rtwStatus.status_color === 'amber' ? 'text-amber-800' :
                                  rtwStatus.status_color === 'red' ? 'text-red-800' :
                                  'text-gray-800'
                                }`}>
                                  {rtwStatus.status_label}
                                </span>
                              </div>
                              {rtwStatus.days_until_expiry !== null && rtwStatus.days_until_expiry > 0 && (
                                <Badge className={`text-[10px] ${
                                  rtwStatus.days_until_expiry <= 30 ? 'bg-red-100 text-red-700 border-red-200' :
                                  rtwStatus.days_until_expiry <= 90 ? 'bg-amber-100 text-amber-700 border-amber-200' :
                                  'bg-green-100 text-green-700 border-green-200'
                                }`}>
                                  {rtwStatus.days_until_expiry} days
                                </Badge>
                              )}
                            </div>
                            
                            {/* Alerts */}
                            {rtwStatus.alerts && rtwStatus.alerts.length > 0 && (
                              <div className="space-y-1">
                                {rtwStatus.alerts.map((alert, idx) => (
                                  <p key={idx} className={`text-xs ${
                                    alert.level === 'error' || alert.level === 'urgent' ? 'text-red-700' :
                                    alert.level === 'warning' ? 'text-amber-700' :
                                    'text-gray-600'
                                  }`}>
                                    {alert.message}
                                  </p>
                                ))}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )}
                    
                    {/* DBS Result Details - COMPREHENSIVE DISPLAY */}
                    {key === 'dbs' && (
                      <div className="mt-3 pt-3 border-t border-gray-200 space-y-3">
                        <div className="flex items-center gap-2">
                          <Shield className="h-4 w-4 text-slate-600" />
                          <p className="text-xs text-text-muted uppercase tracking-wide font-semibold">DBS Result</p>
                        </div>
                        
                        <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-sm">
                          {/* DBS Level */}
                          {checkData.dbs_level && (
                            <div>
                              <p className="text-xs text-text-muted">DBS Level</p>
                              <p className="font-medium text-text-primary capitalize">{checkData.dbs_level.replace(/_/g, ' ')}</p>
                            </div>
                          )}
                          
                          {/* Certificate Number */}
                          {checkData.certificate_number && (
                            <div>
                              <p className="text-xs text-text-muted">Certificate Number</p>
                              <p className="font-medium text-text-primary font-mono text-xs">{checkData.certificate_number}</p>
                            </div>
                          )}
                          
                          {/* Certificate Issue Date */}
                          {checkData.certificate_issue_date && (
                            <div>
                              <p className="text-xs text-text-muted">Issue Date</p>
                              <p className="font-medium text-text-primary">{formatBackendDate(checkData.certificate_issue_date, { format: 'medium' })}</p>
                            </div>
                          )}
                          
                          {/* Workforce */}
                          {checkData.workforce && (
                            <div>
                              <p className="text-xs text-text-muted">Workforce</p>
                              <p className="font-medium text-text-primary capitalize">{checkData.workforce.replace(/_/g, ' ')}</p>
                            </div>
                          )}
                          
                          {/* Name on Certificate */}
                          {checkData.name_on_certificate && (
                            <div>
                              <p className="text-xs text-text-muted">Name on Certificate</p>
                              <p className="font-medium text-text-primary">{checkData.name_on_certificate}</p>
                            </div>
                          )}
                          
                          {/* Next Recheck Date */}
                          {(checkData.next_recheck_date || checkData.review_due_at) && (
                            <div>
                              <p className="text-xs text-text-muted">Next Recheck</p>
                              <p className="font-medium text-amber-700">{formatBackendDate(checkData.next_recheck_date || checkData.review_due_at, { format: 'medium' })}</p>
                            </div>
                          )}
                        </div>
                        
                        {/* Update Service Section */}
                        {(checkData.update_service_registered || checkData.update_service_status) && (
                          <div className="p-2 bg-indigo-50 border border-indigo-200 rounded-lg">
                            <p className="text-xs text-indigo-800 font-medium mb-1">Update Service</p>
                            <div className="flex flex-wrap gap-2">
                              <span className={`text-xs px-2 py-0.5 rounded ${
                                checkData.update_service_status === 'active' 
                                  ? 'bg-green-100 text-green-700' 
                                  : 'bg-gray-100 text-gray-700'
                              }`}>
                                {checkData.update_service_status === 'active' ? 'Registered' : 'Not Registered'}
                              </span>
                              {checkData.last_status_check_date && (
                                <span className="text-xs text-indigo-600">
                                  Last checked: {formatBackendDate(checkData.last_status_check_date, { format: 'short' })}
                                </span>
                              )}
                              {checkData.update_service_check_result && (
                                <span className={`text-xs px-2 py-0.5 rounded ${
                                  checkData.update_service_check_result === 'no_change' 
                                    ? 'bg-green-100 text-green-700' 
                                    : 'bg-red-100 text-red-700'
                                }`}>
                                  {checkData.update_service_check_result === 'no_change' ? 'No change' : 'Changes detected'}
                                </span>
                              )}
                            </div>
                          </div>
                        )}
                        
                        {/* Result Status */}
                        {checkData.result_status && (
                          <div className={`p-2 rounded-lg ${
                            checkData.result_status === 'clear' ? 'bg-green-50 border border-green-200' :
                            checkData.result_status === 'information_present' ? 'bg-amber-50 border border-amber-200' :
                            'bg-gray-50 border border-gray-200'
                          }`}>
                            <p className={`text-xs font-medium ${
                              checkData.result_status === 'clear' ? 'text-green-800' :
                              checkData.result_status === 'information_present' ? 'text-amber-800' :
                              'text-gray-800'
                            }`}>
                              {checkData.result_status === 'clear' ? 'Clear - No information disclosed' :
                               checkData.result_status === 'information_present' ? 'Information Present - Review Required' :
                               'Pending Review'}
                            </p>
                            {checkData.result_summary && (
                              <p className="text-xs text-gray-600 mt-1">{checkData.result_summary}</p>
                            )}
                          </div>
                        )}
                        
                        {/* Information Present Warning */}
                        {checkData.information_present && (
                          <div className="p-2 bg-amber-50 border border-amber-200 rounded-lg">
                            <div className="flex items-start gap-2">
                              <AlertTriangle className="h-4 w-4 text-amber-600 mt-0.5 flex-shrink-0" />
                              <div>
                                <p className="text-xs text-amber-800 font-medium">Information/disclosures present</p>
                                <p className="text-xs text-amber-700 mt-0.5">Review notes for risk assessment details.</p>
                              </div>
                            </div>
                          </div>
                        )}
                        
                        {/* Status flags */}
                        <div className="flex flex-wrap gap-2">
                          {checkData.recheck_required !== false && (
                            <div className="flex items-center gap-1 px-2 py-1 bg-blue-50 border border-blue-200 rounded-lg">
                              <Clock className="h-3 w-3 text-blue-600" />
                              <span className="text-xs font-medium text-blue-700">Recheck required (policy)</span>
                            </div>
                          )}
                        </div>
                        
                        {/* DBS STATUS ALERT PANEL - Non-breaking, read-only display */}
                        {checkData.dbs_status && checkData.dbs_status.status !== 'not_verified' && (
                          <div className={`p-3 rounded-lg border ${
                            checkData.dbs_status.status_color === 'green' ? 'bg-green-50 border-green-200' :
                            checkData.dbs_status.status_color === 'amber' ? 'bg-amber-50 border-amber-200' :
                            checkData.dbs_status.status_color === 'red' ? 'bg-red-50 border-red-200' :
                            'bg-gray-50 border-gray-200'
                          }`}>
                            <div className="flex items-center justify-between mb-2">
                              <div className="flex items-center gap-2">
                                {checkData.dbs_status.status_color === 'green' && <CheckCircle className="h-4 w-4 text-green-600" />}
                                {checkData.dbs_status.status_color === 'amber' && <AlertTriangle className="h-4 w-4 text-amber-600" />}
                                {checkData.dbs_status.status_color === 'red' && <AlertTriangle className="h-4 w-4 text-red-600" />}
                                <span className={`text-sm font-semibold ${
                                  checkData.dbs_status.status_color === 'green' ? 'text-green-800' :
                                  checkData.dbs_status.status_color === 'amber' ? 'text-amber-800' :
                                  checkData.dbs_status.status_color === 'red' ? 'text-red-800' :
                                  'text-gray-800'
                                }`}>
                                  {checkData.dbs_status.status_label}
                                </span>
                              </div>
                              {checkData.dbs_status.days_until_recheck !== null && checkData.dbs_status.days_until_recheck > 0 && (
                                <Badge className={`text-[10px] ${
                                  checkData.dbs_status.days_until_recheck <= 30 ? 'bg-red-100 text-red-700 border-red-200' :
                                  checkData.dbs_status.days_until_recheck <= 90 ? 'bg-amber-100 text-amber-700 border-amber-200' :
                                  'bg-green-100 text-green-700 border-green-200'
                                }`}>
                                  {checkData.dbs_status.days_until_recheck} days
                                </Badge>
                              )}
                            </div>
                            
                            {/* Alerts */}
                            {checkData.dbs_status.alerts && checkData.dbs_status.alerts.length > 0 && (
                              <div className="space-y-1">
                                {checkData.dbs_status.alerts.map((alert, idx) => (
                                  <p key={idx} className={`text-xs ${
                                    alert.level === 'error' || alert.level === 'urgent' ? 'text-red-700' :
                                    alert.level === 'warning' ? 'text-amber-700' :
                                    'text-gray-600'
                                  }`}>
                                    {alert.message}
                                  </p>
                                ))}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )}
                    
                    {/* Identity Result Details - COMPREHENSIVE DISPLAY */}
                    {key === 'identity' && (
                      <div className="mt-3 pt-3 border-t border-gray-200 space-y-3">
                        <div className="flex items-center gap-2">
                          <Shield className="h-4 w-4 text-slate-600" />
                          <p className="text-xs text-text-muted uppercase tracking-wide font-semibold">Identity Verification Result</p>
                        </div>
                        
                        <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-sm">
                          {/* Document Type */}
                          {checkData.document_type && (
                            <div>
                              <p className="text-xs text-text-muted">Document Type</p>
                              <p className="font-medium text-text-primary capitalize">{checkData.document_type.replace(/_/g, ' ')}</p>
                            </div>
                          )}
                          
                          {/* Full Name on Document */}
                          {checkData.full_name_on_document && (
                            <div className="col-span-2">
                              <p className="text-xs text-text-muted">Name on Document</p>
                              <p className="font-medium text-text-primary">{checkData.full_name_on_document}</p>
                            </div>
                          )}
                          
                          {/* Document Number */}
                          {checkData.document_number && (
                            <div>
                              <p className="text-xs text-text-muted">Document Number</p>
                              <p className="font-medium text-text-primary font-mono text-xs">{checkData.document_number}</p>
                            </div>
                          )}
                          
                          {/* Date of Birth */}
                          {checkData.date_of_birth && (
                            <div>
                              <p className="text-xs text-text-muted">Date of Birth</p>
                              <p className="font-medium text-text-primary">{formatBackendDate(checkData.date_of_birth, { format: 'medium' })}</p>
                            </div>
                          )}
                          
                          {/* Nationality */}
                          {checkData.nationality && (
                            <div>
                              <p className="text-xs text-text-muted">Nationality</p>
                              <p className="font-medium text-text-primary">{checkData.nationality}</p>
                            </div>
                          )}
                          
                          {/* Issue Date */}
                          {checkData.issue_date && (
                            <div>
                              <p className="text-xs text-text-muted">Issue Date</p>
                              <p className="font-medium text-text-primary">{formatBackendDate(checkData.issue_date, { format: 'medium' })}</p>
                            </div>
                          )}
                          
                          {/* Expiry Date */}
                          {checkData.expiry_date && (
                            <div>
                              <p className="text-xs text-text-muted">Expiry Date</p>
                              <p className={`font-medium ${
                                checkData.identity_status?.status === 'expired' ? 'text-red-700' :
                                checkData.identity_status?.days_until_expiry <= 30 ? 'text-amber-600' :
                                'text-text-primary'
                              }`}>
                                {formatBackendDate(checkData.expiry_date, { format: 'medium' })}
                                {checkData.identity_status?.days_until_expiry !== null && checkData.identity_status?.days_until_expiry > 0 && (
                                  <span className="text-xs ml-1">({checkData.identity_status.days_until_expiry}d)</span>
                                )}
                              </p>
                            </div>
                          )}
                        </div>
                        
                        {/* Verification Match Checks */}
                        <div className="p-2 bg-slate-50 border border-slate-200 rounded-lg">
                          <p className="text-xs text-slate-700 font-medium mb-2">Verification Checks</p>
                          <div className="flex flex-wrap gap-3">
                            <div className="flex items-center gap-1">
                              {checkData.name_matches_application ? (
                                <CheckCircle className="h-3.5 w-3.5 text-green-600" />
                              ) : (
                                <AlertTriangle className="h-3.5 w-3.5 text-amber-600" />
                              )}
                              <span className={`text-xs ${checkData.name_matches_application ? 'text-green-700' : 'text-amber-700'}`}>
                                Name {checkData.name_matches_application ? 'matches' : 'mismatch'}
                              </span>
                            </div>
                            <div className="flex items-center gap-1">
                              {checkData.dob_matches_application ? (
                                <CheckCircle className="h-3.5 w-3.5 text-green-600" />
                              ) : (
                                <AlertTriangle className="h-3.5 w-3.5 text-amber-600" />
                              )}
                              <span className={`text-xs ${checkData.dob_matches_application ? 'text-green-700' : 'text-amber-700'}`}>
                                DOB {checkData.dob_matches_application ? 'matches' : 'mismatch'}
                              </span>
                            </div>
                            <div className="flex items-center gap-1">
                              {checkData.photo_match_confirmed ? (
                                <CheckCircle className="h-3.5 w-3.5 text-green-600" />
                              ) : (
                                <AlertTriangle className="h-3.5 w-3.5 text-amber-600" />
                              )}
                              <span className={`text-xs ${checkData.photo_match_confirmed ? 'text-green-700' : 'text-amber-700'}`}>
                                Photo {checkData.photo_match_confirmed ? 'verified' : 'not verified'}
                              </span>
                            </div>
                          </div>
                        </div>
                        
                        {/* Identity Status Alert Panel */}
                        {checkData.identity_status && checkData.identity_status.status !== 'not_verified' && (
                          <div className={`p-3 rounded-lg border ${
                            checkData.identity_status.status_color === 'green' ? 'bg-green-50 border-green-200' :
                            checkData.identity_status.status_color === 'amber' ? 'bg-amber-50 border-amber-200' :
                            checkData.identity_status.status_color === 'red' ? 'bg-red-50 border-red-200' :
                            'bg-gray-50 border-gray-200'
                          }`}>
                            <div className="flex items-center gap-2">
                              {checkData.identity_status.status_color === 'green' && <CheckCircle className="h-4 w-4 text-green-600" />}
                              {checkData.identity_status.status_color === 'amber' && <AlertTriangle className="h-4 w-4 text-amber-600" />}
                              {checkData.identity_status.status_color === 'red' && <AlertTriangle className="h-4 w-4 text-red-600" />}
                              <span className={`text-sm font-semibold ${
                                checkData.identity_status.status_color === 'green' ? 'text-green-800' :
                                checkData.identity_status.status_color === 'amber' ? 'text-amber-800' :
                                checkData.identity_status.status_color === 'red' ? 'text-red-800' :
                                'text-gray-800'
                              }`}>
                                {checkData.identity_status.status_label}
                              </span>
                            </div>
                            
                            {/* Alerts */}
                            {checkData.identity_status.alerts && checkData.identity_status.alerts.length > 0 && (
                              <div className="space-y-1 mt-2">
                                {checkData.identity_status.alerts.map((alert, idx) => (
                                  <p key={idx} className={`text-xs ${
                                    alert.level === 'error' || alert.level === 'urgent' ? 'text-red-700' :
                                    alert.level === 'warning' ? 'text-amber-700' :
                                    'text-gray-600'
                                  }`}>
                                    {alert.message}
                                  </p>
                                ))}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )}
                    
                    {/* Proof of Address Result Details - COMPREHENSIVE DISPLAY */}
                    {key === 'proof_of_address' && (
                      <div className="mt-3 pt-3 border-t border-gray-200 space-y-3">
                        <div className="flex items-center gap-2">
                          <Shield className="h-4 w-4 text-slate-600" />
                          <p className="text-xs text-text-muted uppercase tracking-wide font-semibold">Address Verification Result</p>
                        </div>
                        
                        <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-sm">
                          {/* Document Count */}
                          <div>
                            <p className="text-xs text-text-muted">Documents Verified</p>
                            <p className={`font-semibold ${
                              (checkData.documents_received_count || 0) >= (checkData.documents_required_count || 2) 
                                ? 'text-green-700' 
                                : 'text-amber-700'
                            }`}>
                              {checkData.documents_received_count || 0} / {checkData.documents_required_count || 2}
                            </p>
                          </div>
                          
                          {/* Recency Status */}
                          <div>
                            <p className="text-xs text-text-muted">Document Recency</p>
                            <p className={`font-medium ${
                              checkData.all_documents_sufficiently_recent ? 'text-green-700' : 'text-amber-700'
                            }`}>
                              {checkData.all_documents_sufficiently_recent ? 'All within limits' : 'Contains outdated'}
                            </p>
                          </div>
                          
                          {/* Address Match */}
                          <div>
                            <p className="text-xs text-text-muted">Address Match</p>
                            <p className={`font-medium ${
                              checkData.address_matches_application ? 'text-green-700' : 'text-amber-700'
                            }`}>
                              {checkData.address_matches_application ? 'Matches application' : 'Needs review'}
                            </p>
                          </div>
                        </div>
                        
                        {/* Extracted Address */}
                        {(checkData.extracted_address_line1 || checkData.extracted_postcode) && (
                          <div className="p-2 bg-slate-50 border border-slate-200 rounded-lg">
                            <p className="text-xs text-slate-700 font-medium mb-1">Verified Address</p>
                            <div className="text-sm text-text-primary">
                              {checkData.extracted_address_line1 && <p>{checkData.extracted_address_line1}</p>}
                              {checkData.extracted_address_line2 && <p>{checkData.extracted_address_line2}</p>}
                              {(checkData.extracted_city || checkData.extracted_postcode) && (
                                <p>
                                  {checkData.extracted_city && <span>{checkData.extracted_city}</span>}
                                  {checkData.extracted_city && checkData.extracted_postcode && <span>, </span>}
                                  {checkData.extracted_postcode && <span className="font-mono">{checkData.extracted_postcode}</span>}
                                </p>
                              )}
                            </div>
                          </div>
                        )}
                        
                        {/* Verified Documents List */}
                        {checkData.verified_documents && checkData.verified_documents.length > 0 && (
                          <div className="space-y-2">
                            <p className="text-xs text-text-muted uppercase tracking-wide">Verified Documents</p>
                            {checkData.verified_documents.map((doc, idx) => (
                              <div key={idx} className={`p-2 rounded-lg border ${
                                doc.is_valid || doc.recency_status === 'valid' 
                                  ? 'bg-green-50 border-green-200' 
                                  : 'bg-amber-50 border-amber-200'
                              }`}>
                                <div className="flex items-center justify-between">
                                  <div className="flex items-center gap-2">
                                    <FileText className={`h-3.5 w-3.5 ${
                                      doc.is_valid || doc.recency_status === 'valid' ? 'text-green-600' : 'text-amber-600'
                                    }`} />
                                    <span className="text-sm font-medium capitalize">
                                      {(doc.type || doc.document_type || 'Document').replace(/_/g, ' ')}
                                    </span>
                                  </div>
                                  <Badge className={`text-[10px] ${
                                    doc.is_valid || doc.recency_status === 'valid'
                                      ? 'bg-green-100 text-green-700 border-green-200'
                                      : 'bg-amber-100 text-amber-700 border-amber-200'
                                  }`}>
                                    {doc.is_valid || doc.recency_status === 'valid' ? 'Valid' : doc.recency_status || 'Review needed'}
                                  </Badge>
                                </div>
                                {doc.issue_date && (
                                  <p className="text-xs text-text-muted mt-1 ml-5">
                                    Dated: {formatBackendDate(doc.issue_date, { format: 'medium' })}
                                    {doc.months_old !== undefined && <span className="ml-1">({doc.months_old} months old)</span>}
                                  </p>
                                )}
                              </div>
                            ))}
                          </div>
                        )}
                        
                        {/* Address Status Alert Panel */}
                        {checkData.address_status && checkData.address_status.status !== 'not_verified' && (
                          <div className={`p-3 rounded-lg border ${
                            checkData.address_status.status_color === 'green' ? 'bg-green-50 border-green-200' :
                            checkData.address_status.status_color === 'amber' ? 'bg-amber-50 border-amber-200' :
                            checkData.address_status.status_color === 'red' ? 'bg-red-50 border-red-200' :
                            'bg-gray-50 border-gray-200'
                          }`}>
                            <div className="flex items-center gap-2">
                              {checkData.address_status.status_color === 'green' && <CheckCircle className="h-4 w-4 text-green-600" />}
                              {checkData.address_status.status_color === 'amber' && <AlertTriangle className="h-4 w-4 text-amber-600" />}
                              {checkData.address_status.status_color === 'red' && <AlertTriangle className="h-4 w-4 text-red-600" />}
                              <span className={`text-sm font-semibold ${
                                checkData.address_status.status_color === 'green' ? 'text-green-800' :
                                checkData.address_status.status_color === 'amber' ? 'text-amber-800' :
                                checkData.address_status.status_color === 'red' ? 'text-red-800' :
                                'text-gray-800'
                              }`}>
                                {checkData.address_status.status_label}
                              </span>
                            </div>
                            
                            {/* Alerts */}
                            {checkData.address_status.alerts && checkData.address_status.alerts.length > 0 && (
                              <div className="space-y-1 mt-2">
                                {checkData.address_status.alerts.map((alert, idx) => (
                                  <p key={idx} className={`text-xs ${
                                    alert.level === 'error' || alert.level === 'urgent' ? 'text-red-700' :
                                    alert.level === 'warning' ? 'text-amber-700' :
                                    'text-gray-600'
                                  }`}>
                                    {alert.message}
                                  </p>
                                ))}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  {/* VERIFICATION PROOF FILE SECTION */}
                  <div className="space-y-2">
                    <p className="text-xs text-text-muted uppercase tracking-wide font-medium">
                      Proof of Check
                    </p>
                    
                    {hasVerificationProof ? (
                      <div className="flex items-center justify-between p-3 bg-green-50 border border-green-200 rounded-lg">
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 rounded-lg bg-green-100 flex items-center justify-center">
                            <FileText className="h-5 w-5 text-green-600" />
                          </div>
                          <div>
                            <p className="text-sm font-medium text-green-800">
                              {checkData.evidence_document.filename || 'Verification Proof'}
                            </p>
                            <p className="text-xs text-green-600">
                              Uploaded {formatBackendDate(checkData.evidence_document.uploaded_at, { format: 'medium' })}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-1">
                          {/* View Proof */}
                          <Button
                            size="sm"
                            variant="ghost"
                            className="h-8 w-8 p-0 text-green-600 hover:text-green-700 hover:bg-green-100"
                            onClick={handleViewProof}
                            title="View proof"
                            data-testid={`${key}-verification-view-proof`}
                          >
                            <Eye className="h-4 w-4" />
                          </Button>
                          
                          {/* Download Proof */}
                          <Button
                            size="sm"
                            variant="ghost"
                            className="h-8 w-8 p-0 text-green-600 hover:text-green-700 hover:bg-green-100"
                            onClick={handleDownloadProof}
                            title="Download proof"
                            data-testid={`${key}-verification-download-proof`}
                          >
                            <Download className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                    ) : (
                      <div className="flex items-center gap-2 p-3 bg-amber-50 border border-amber-200 rounded-lg">
                        <AlertTriangle className="h-5 w-5 text-amber-600 flex-shrink-0" />
                        <div className="flex-1">
                          <p className="text-sm font-medium text-amber-800">No proof file attached</p>
                          <p className="text-xs text-amber-600">
                            Upload proof documentation for compliance audit trail.
                          </p>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                /* No Check Recorded State */
                <div className="p-4 bg-white border border-gray-200 rounded-lg text-center">
                  <AlertTriangle className="h-8 w-8 text-red-400 mx-auto mb-2" />
                  <p className="text-sm font-medium text-text-primary mb-1">No check recorded</p>
                  <p className="text-xs text-text-muted mb-3">
                    Record a verification check with proof to complete this requirement.
                  </p>
                </div>
              )}

              {/* Verification Actions */}
              {!isAuditor && (
                <div className="flex items-center gap-2 pt-2 border-t border-gray-100">
                  {/* Record Check / Update Check Button - Primary action that includes proof upload */}
                  {!hasCheck ? (
                    <Button
                      size="sm"
                      variant="default"
                      onClick={() => onRecordCheck && onRecordCheck(key)}
                      className="h-8 text-xs bg-primary hover:bg-primary-hover text-white rounded-lg"
                      data-testid={`${key}-verification-record-check-btn`}
                    >
                      <Shield className="h-3.5 w-3.5 mr-1" />
                      Record Check
                    </Button>
                  ) : (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => onUpdateCheck && onUpdateCheck(key)}
                      className="h-8 text-xs rounded-lg"
                      data-testid={`${key}-verification-update-check-btn`}
                    >
                      <RefreshCw className="h-3.5 w-3.5 mr-1" />
                      Update Check
                    </Button>
                  )}
                  
                  {/* Manage/View Verification - always available */}
                  {hasCheck && (
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={onOpenDrawer}
                      className="h-8 text-xs rounded-lg"
                      data-testid={`${key}-verification-manage-btn`}
                    >
                      <Eye className="h-3.5 w-3.5 mr-1" />
                      View Details
                    </Button>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer with History */}
        <div className="pt-2 flex items-center justify-between text-xs text-text-muted">
          <div className="flex items-center gap-4">
            <span>{counters.active} evidence</span>
            <span>{counters.historical} historical</span>
          </div>
          {onViewHistory && (
            <button
              onClick={() => onViewHistory(key, label)}
              className="text-xs text-text-muted hover:text-text-primary flex items-center gap-1"
              data-testid={`${key}-view-history`}
            >
              View History
            </button>
          )}
        </div>
      </div>
      
      {/* Evidence Review Dialog */}
      <EvidenceReviewDialog
        isOpen={reviewDialog.isOpen}
        onClose={() => setReviewDialog({ isOpen: false, file: null })}
        file={reviewDialog.file}
        employeeId={employeeId}
        requirementKey={key}
        requirementLabel={label}
        onReviewComplete={(decision) => {
          // Refresh parent data after review
          if (onRefresh) {
            onRefresh();
          }
        }}
        onOpenRecordCheck={(file) => {
          // Close review dialog and open record check with file context
          setReviewDialog({ isOpen: false, file: null });
          if (onRecordCheck) {
            onRecordCheck(key, file);
          }
        }}
      />
      
      {/* Verification Stamp Dialog */}
      <VerificationStampDialog
        isOpen={stampDialog.isOpen}
        onClose={() => setStampDialog({ isOpen: false, file: null })}
        file={stampDialog.file}
        employeeId={employeeId}
        requirementKey={key}
        requirementLabel={label}
        onStampApplied={(stampType) => {
          // Refresh parent data after stamp applied
          if (onRefresh) {
            onRefresh();
          }
        }}
      />
    </RequirementSectionShell>
  );
}
```
--- END UploadRequirementCard.js ---

---
## FILE: compliance_index.js
## Lines: 74
```javascript
// Compliance Components - Dual-Row Model (Step 11)
// 
// Evidence row = uploaded/supporting files
// Check row = employer/admin verification outcome (authoritative)
// Agreement row = form acknowledgements
// Reference row = referee request/response/verification workflow

// Core Shell Components (STEP 11E+)
export { default as RequirementSectionShell } from './RequirementSectionShell';
export { default as RequirementActionBar } from './RequirementActionBar';
export { default as UploadRequirementCard } from './UploadRequirementCard';
export * from './surfaceNormalizers';

// Row Components
export { default as EvidenceRow } from './EvidenceRow';
export { default as CheckRow } from './CheckRow';
export { default as AgreementRow } from './AgreementRow';
export { default as ReferenceRow } from './ReferenceRow';

// Container Components
export { default as DualRowComplianceSection } from './DualRowComplianceSection';

// Dialogs
export { default as RecordCheckDialog } from './RecordCheckDialog';
export { default as CompleteAgreementDialog } from './CompleteAgreementDialog';
export { default as SendAgreementDialog } from './SendAgreementDialog';

// Phase 4A - High-value cleanup components
export { default as ComplianceActionBar } from './ComplianceActionBar';
export { default as WhatsNeededPanel } from './WhatsNeededPanel';
export { default as TrainingSummaryCard } from './TrainingSummaryCard';

// Phase 4B - Restructured top section components
export { default as ApprovalStatusPanel } from './ApprovalStatusPanel';
export { default as NextActionsPanel } from './NextActionsPanel';
export { default as BatchRequestModal } from './BatchRequestModal';

// Phase D2 - File interaction components
export { default as RequirementFilesDrawer } from './RequirementFilesDrawer';
export { default as DocumentActionMenu } from './DocumentActionMenu';

// Phase D3 - Request lifecycle & history components
export { default as RequirementHistoryDrawer } from './RequirementHistoryDrawer';
export { default as RequestStatusBadge, RequestStatusInline } from './RequestStatusBadge';

// Stage Identity Components (Applicant vs Employee)
export { default as StageIdentityBadge, STAGE_CONFIGS } from './StageIdentityBadge';
export { default as ApplicantStageBanner } from './ApplicantStageBanner';

// Simplified Header & Approval Components
export { default as SimplifiedProfileHeader } from './SimplifiedProfileHeader';
export { default as RecruitmentApprovalCard } from './RecruitmentApprovalCard';

// Reference Response Drawer (Ticket E)
export { default as ReferenceResponseDrawer } from './ReferenceResponseDrawer';

// Agreement Form Drawer (Ticket D)
export { default as AgreementFormDrawer } from './AgreementFormDrawer';

// Production-Ready Compliance Drawers
export { default as ComplianceDrawer, DrawerSection, DrawerCard, DrawerEmptyState, DrawerStatusChip } from './ComplianceDrawer';
export { default as EvidenceManageDrawer } from './EvidenceManageDrawer';

// References Panel (CQC Gap Fix)
export { default as ReferencesPanel } from './ReferencesPanel';

// Audit Trail Panel (CQC Gap Fix)
export { default as AuditTrailPanel } from './AuditTrailPanel';

// Document Requests Panel (Request visibility)
export { default as DocumentRequestsPanel } from './DocumentRequestsPanel';

// Interview Form Panel (Interview records with PDF download)
export { default as InterviewFormPanel } from './InterviewFormPanel';
```
--- END compliance_index.js ---
