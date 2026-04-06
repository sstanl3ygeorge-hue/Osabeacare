import { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '../ui/dialog';
import { Textarea } from '../ui/textarea';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { toast } from 'sonner';
import { 
  User, Mail, Phone, Building, Briefcase, Clock, CheckCircle, 
  XCircle, Send, AlertTriangle, Loader2, RefreshCw, Calendar,
  MessageSquare, FileText, Plus, Edit, Shield, Eye
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

export default function ReferencesPanel({ employeeId, onRefresh, onEditReference }) {
  const [references, setReferences] = useState(null);
  const [loading, setLoading] = useState(true);
  const [sendingRequest, setSendingRequest] = useState(null);
  const [sendDialogOpen, setSendDialogOpen] = useState(false);
  const [selectedRef, setSelectedRef] = useState(null);
  const [customMessage, setCustomMessage] = useState('');
  
  // Add referee dialog state
  const [addDialogOpen, setAddDialogOpen] = useState(false);
  const [addRefNum, setAddRefNum] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [refereeForm, setRefereeForm] = useState({
    name: '',
    email: '',
    phone: '',
    organisation: '',
    position: '',
    relationship: ''
  });
  
  // Review Response modal state
  const [reviewDialogOpen, setReviewDialogOpen] = useState(false);
  const [reviewRefNum, setReviewRefNum] = useState(null);
  
  // Verify/Reject state
  const [verifyDialogOpen, setVerifyDialogOpen] = useState(false);
  const [verifyRefNum, setVerifyRefNum] = useState(null);
  const [verifyAction, setVerifyAction] = useState('verify'); // 'verify' or 'reject'
  const [verifyNotes, setVerifyNotes] = useState('');
  const [mismatchReason, setMismatchReason] = useState('');
  const [verifyLoading, setVerifyLoading] = useState(false);

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
  
  // Open review response modal
  const openReviewDialog = (refNum) => {
    setReviewRefNum(refNum);
    setReviewDialogOpen(true);
  };
  
  // Open verify/reject modal
  const openVerifyDialog = (refNum, action = 'verify') => {
    setVerifyRefNum(refNum);
    setVerifyAction(action);
    setVerifyNotes('');
    setMismatchReason('');
    setVerifyDialogOpen(true);
  };
  
  // Handle verify/reject
  const handleVerifyReference = async () => {
    setVerifyLoading(true);
    try {
      const token = localStorage.getItem('token');
      await axios.post(
        `${API}/employees/${employeeId}/references/${verifyRefNum}/verify`,
        {
          action: verifyAction,
          notes: verifyNotes,
          mismatch_reason: mismatchReason || null
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      toast.success(verifyAction === 'verify' 
        ? 'Reference verified successfully' 
        : 'Reference rejected');
      setVerifyDialogOpen(false);
      fetchReferences();
      if (onRefresh) onRefresh();
    } catch (error) {
      const msg = error.response?.data?.detail || `Failed to ${verifyAction} reference`;
      toast.error(msg);
    } finally {
      setVerifyLoading(false);
    }
  };
  
  const openAddDialog = (refNum) => {
    setAddRefNum(refNum);
    setRefereeForm({
      name: '',
      email: '',
      phone: '',
      organisation: '',
      position: '',
      relationship: ''
    });
    setAddDialogOpen(true);
  };
  
  const handleAddReferee = async () => {
    // Validate
    if (!refereeForm.name.trim() || !refereeForm.email.trim()) {
      toast.error('Name and email are required');
      return;
    }
    
    // Basic email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(refereeForm.email)) {
      toast.error('Please enter a valid email address');
      return;
    }
    
    setIsSubmitting(true);
    try {
      const token = localStorage.getItem('token');
      await axios.post(
        `${API}/employees/${employeeId}/references/${addRefNum}`,
        refereeForm,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      toast.success(`Referee ${addRefNum} details added successfully`);
      setAddDialogOpen(false);
      fetchReferences();
      if (onRefresh) onRefresh();
    } catch (error) {
      const msg = error.response?.data?.detail || 'Failed to add referee';
      toast.error(msg);
    } finally {
      setIsSubmitting(false);
    }
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
                    <div className="flex items-center gap-2">
                      {declared.name && onEditReference && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => onEditReference(refNum, declared)}
                          className="h-7 px-2 text-gray-500 hover:text-primary"
                          data-testid={`edit-reference-btn-${refNum}`}
                        >
                          <Edit className="h-3.5 w-3.5" />
                        </Button>
                      )}
                      <Badge className={`${config.color} flex items-center gap-1`}>
                        <StatusIcon className="h-3 w-3" />
                        {config.label}
                      </Badge>
                    </div>
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
                          <div className="pt-2 border-t space-y-2">
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
                              <>
                                <Button
                                  size="sm"
                                  variant="outline"
                                  className="w-full rounded-lg"
                                  onClick={() => openReviewDialog(refNum)}
                                  data-testid={`review-response-btn-${refNum}`}
                                >
                                  <Eye className="h-4 w-4 mr-2" />
                                  Review Response
                                </Button>
                                <div className="flex gap-2">
                                  <Button
                                    size="sm"
                                    className="flex-1 rounded-lg bg-green-600 hover:bg-green-700"
                                    onClick={() => openVerifyDialog(refNum, 'verify')}
                                    data-testid={`verify-reference-btn-${refNum}`}
                                  >
                                    <CheckCircle className="h-4 w-4 mr-2" />
                                    Verify
                                  </Button>
                                  <Button
                                    size="sm"
                                    variant="destructive"
                                    className="flex-1 rounded-lg"
                                    onClick={() => openVerifyDialog(refNum, 'reject')}
                                    data-testid={`reject-reference-btn-${refNum}`}
                                  >
                                    <XCircle className="h-4 w-4 mr-2" />
                                    Reject
                                  </Button>
                                </div>
                              </>
                            ) : null}
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="text-center py-6">
                        <AlertTriangle className="h-8 w-8 mx-auto mb-2 text-amber-400" />
                        <p className="text-gray-600 font-medium">No referee declared for Reference {refNum}</p>
                        <p className="text-xs text-gray-500 mt-1 mb-4">Add referee details manually or extract from application form</p>
                        <Button
                          size="sm"
                          onClick={() => openAddDialog(refNum)}
                          className="rounded-lg"
                          data-testid={`add-referee-btn-${refNum}`}
                        >
                          <Plus className="h-4 w-4 mr-2" />
                          Add Referee Details
                        </Button>
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
        <DialogContent className="sm:max-w-md bg-white">
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
      
      {/* Add Referee Dialog */}
      <Dialog open={addDialogOpen} onOpenChange={setAddDialogOpen}>
        <DialogContent className="sm:max-w-md bg-white">
          <DialogHeader>
            <DialogTitle>Add Referee Details</DialogTitle>
            <DialogDescription>
              Enter the referee's contact information. You can then send them a reference request.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <Label>Full Name *</Label>
              <Input
                value={refereeForm.name}
                onChange={(e) => setRefereeForm({...refereeForm, name: e.target.value})}
                placeholder="e.g., Jane Smith"
                data-testid="referee-name-input"
              />
            </div>
            
            <div>
              <Label>Email Address *</Label>
              <Input
                type="email"
                value={refereeForm.email}
                onChange={(e) => setRefereeForm({...refereeForm, email: e.target.value})}
                placeholder="e.g., jane.smith@company.com"
                data-testid="referee-email-input"
              />
            </div>
            
            <div>
              <Label>Phone Number</Label>
              <Input
                value={refereeForm.phone}
                onChange={(e) => setRefereeForm({...refereeForm, phone: e.target.value})}
                placeholder="e.g., 01234 567890"
              />
            </div>
            
            <div>
              <Label>Organisation</Label>
              <Input
                value={refereeForm.organisation}
                onChange={(e) => setRefereeForm({...refereeForm, organisation: e.target.value})}
                placeholder="e.g., Previous Care Home Ltd"
              />
            </div>
            
            <div>
              <Label>Job Title / Position</Label>
              <Input
                value={refereeForm.position}
                onChange={(e) => setRefereeForm({...refereeForm, position: e.target.value})}
                placeholder="e.g., Care Manager"
              />
            </div>
            
            <div>
              <Label>Relationship to Applicant</Label>
              <Input
                value={refereeForm.relationship}
                onChange={(e) => setRefereeForm({...refereeForm, relationship: e.target.value})}
                placeholder="e.g., Line Manager"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAddDialogOpen(false)}>
              Cancel
            </Button>
            <Button 
              onClick={handleAddReferee}
              disabled={isSubmitting}
              data-testid="submit-referee-btn"
            >
              {isSubmitting ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Plus className="h-4 w-4 mr-2" />
              )}
              Add Referee
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      
      {/* Review Response Dialog */}
      <Dialog open={reviewDialogOpen} onOpenChange={setReviewDialogOpen}>
        <DialogContent className="sm:max-w-2xl bg-white max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <MessageSquare className="h-5 w-5 text-primary" />
              Reference Response - Referee {reviewRefNum}
            </DialogTitle>
          </DialogHeader>
          {reviewRefNum && references?.references?.[`reference_${reviewRefNum}`]?.response && (
            <div className="space-y-4 py-4">
              {/* Referee Info */}
              <div className="bg-gray-50 rounded-lg p-4">
                <h4 className="font-medium mb-2">Referee Information</h4>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <p><span className="text-gray-500">Name:</span> {references.references[`reference_${reviewRefNum}`].declared?.name}</p>
                  <p><span className="text-gray-500">Organisation:</span> {references.references[`reference_${reviewRefNum}`].declared?.organisation}</p>
                  <p><span className="text-gray-500">Email:</span> {references.references[`reference_${reviewRefNum}`].declared?.email}</p>
                  <p><span className="text-gray-500">Position:</span> {references.references[`reference_${reviewRefNum}`].declared?.job_title}</p>
                </div>
              </div>
              
              {/* Response Answers */}
              <div className="space-y-3">
                <h4 className="font-medium">Reference Answers</h4>
                {Object.entries(references.references[`reference_${reviewRefNum}`].response).map(([key, value]) => {
                  // Skip internal fields
                  if (['submitted_at', 'ip_address', 'user_agent'].includes(key)) return null;
                  
                  return (
                    <div key={key} className="border rounded-lg p-3">
                      <p className="text-sm font-medium text-gray-600 mb-1">
                        {key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                      </p>
                      <p className="text-gray-900">{typeof value === 'boolean' ? (value ? 'Yes' : 'No') : (value || 'N/A')}</p>
                    </div>
                  );
                })}
              </div>
              
              {/* Submission Info */}
              {references.references[`reference_${reviewRefNum}`].response.submitted_at && (
                <p className="text-xs text-gray-500 text-center">
                  Submitted: {formatBackendDate(references.references[`reference_${reviewRefNum}`].response.submitted_at)}
                </p>
              )}
            </div>
          )}
          <DialogFooter className="gap-2">
            <Button variant="outline" onClick={() => setReviewDialogOpen(false)}>
              Close
            </Button>
            <Button
              className="bg-green-600 hover:bg-green-700"
              onClick={() => {
                setReviewDialogOpen(false);
                openVerifyDialog(reviewRefNum, 'verify');
              }}
            >
              <CheckCircle className="h-4 w-4 mr-2" />
              Verify Reference
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      
      {/* Verify/Reject Dialog */}
      <Dialog open={verifyDialogOpen} onOpenChange={setVerifyDialogOpen}>
        <DialogContent className="sm:max-w-md bg-white">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {verifyAction === 'verify' ? (
                <>
                  <Shield className="h-5 w-5 text-green-600" />
                  Verify Reference
                </>
              ) : (
                <>
                  <XCircle className="h-5 w-5 text-red-600" />
                  Reject Reference
                </>
              )}
            </DialogTitle>
            <DialogDescription>
              {verifyAction === 'verify' 
                ? 'Confirm that this reference meets NHS employment standards.'
                : 'Provide a reason for rejecting this reference.'}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            {/* Mismatch Handling */}
            {verifyAction === 'verify' && (
              <div>
                <Label>Organisation Mismatch Reason (if applicable)</Label>
                <Select value={mismatchReason} onValueChange={setMismatchReason}>
                  <SelectTrigger className="mt-1">
                    <SelectValue placeholder="Select if referee not in employment history" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">No mismatch</SelectItem>
                    <SelectItem value="earlier_employment">Referee is from earlier employment</SelectItem>
                    <SelectItem value="personal_reference">Referee is personal/professional reference</SelectItem>
                    <SelectItem value="changed_employers">Applicant changed employers since declaration</SelectItem>
                    <SelectItem value="other">Other (specify in notes)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            )}
            
            <div>
              <Label>{verifyAction === 'verify' ? 'Notes (Optional)' : 'Reason for Rejection *'}</Label>
              <Textarea
                value={verifyNotes}
                onChange={(e) => setVerifyNotes(e.target.value)}
                placeholder={verifyAction === 'verify' 
                  ? 'Any additional notes...'
                  : 'Explain why this reference is being rejected...'}
                className="mt-1"
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setVerifyDialogOpen(false)}>
              Cancel
            </Button>
            <Button 
              onClick={handleVerifyReference}
              disabled={verifyLoading || (verifyAction === 'reject' && !verifyNotes)}
              className={verifyAction === 'verify' ? 'bg-green-600 hover:bg-green-700' : ''}
              variant={verifyAction === 'reject' ? 'destructive' : 'default'}
            >
              {verifyLoading ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : verifyAction === 'verify' ? (
                <CheckCircle className="h-4 w-4 mr-2" />
              ) : (
                <XCircle className="h-4 w-4 mr-2" />
              )}
              {verifyAction === 'verify' ? 'Verify Reference' : 'Reject Reference'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
