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
