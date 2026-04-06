/**
 * ActionableTaskQueue - Enhanced Admin Dashboard Task Queue
 * 
 * Shows specific actionable items with direct action buttons per CQC requirement:
 * - Pending Verifications with [Verify] button
 * - References to Send with [Send Request] button
 * - Reference Responses to Review with [Review] button
 * - Forms Pending Review with [Review] button
 * - Induction Incomplete with [View] button
 * - Expiring Soon with [Send Reminder] button
 * - Workers Stuck in Onboarding with [Send Reminder] button
 */

import { useState, useEffect } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { 
  Loader2, FileCheck, Mail, MessageSquare, Clock, Users, 
  ChevronRight, RefreshCw, CheckCircle, Send, Eye, AlertTriangle,
  ClipboardList, FileText, GraduationCap, UserCheck, Filter
} from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '../../lib/utils';
import { useAuth } from '../../context/AuthContext';

const API = process.env.REACT_APP_BACKEND_URL;

export default function ActionableTaskQueue() {
  const { token } = useAuth();
  const navigate = useNavigate();
  const [tasks, setTasks] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(null);
  const [activeFilter, setActiveFilter] = useState('all');

  const fetchTasks = async () => {
    try {
      const response = await axios.get(`${API}/api/admin/task-queue`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setTasks(response.data);
    } catch (error) {
      console.error('Failed to fetch tasks:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token) {
      fetchTasks();
      const interval = setInterval(fetchTasks, 5 * 60 * 1000);
      return () => clearInterval(interval);
    }
  }, [token]);

  const handleSendReminder = async (employeeId, type) => {
    setActionLoading(`reminder-${employeeId}`);
    try {
      await axios.post(
        `${API}/api/workers/${employeeId}/send-reminder`,
        { reminder_type: type },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Reminder sent successfully');
      fetchTasks();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to send reminder');
    } finally {
      setActionLoading(null);
    }
  };

  const handleSendReferenceRequest = async (employeeId, refNum) => {
    setActionLoading(`ref-${employeeId}-${refNum}`);
    try {
      await axios.post(
        `${API}/api/references/${employeeId}/${refNum}/send-request`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success(`Reference ${refNum} request sent`);
      fetchTasks();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to send reference request');
    } finally {
      setActionLoading(null);
    }
  };

  if (loading) {
    return (
      <Card className="border border-gray-200 shadow-sm">
        <CardContent className="py-8 flex justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-primary" />
        </CardContent>
      </Card>
    );
  }

  const pendingVerifications = tasks?.pending_verifications || [];
  const referencesToSend = tasks?.references_to_send || [];
  const referencesToReview = tasks?.references_to_review || [];
  const expiringSoon = tasks?.expiring_soon || [];
  const stuckWorkers = tasks?.stuck_workers || [];
  
  // Additional counts from API
  const inductionIncomplete = tasks?.induction_incomplete || 0;
  const interviewsPending = tasks?.interviews_pending || 0;
  const spotChecksDue = tasks?.spot_checks_due_this_week || 0;
  const supervisionDue = tasks?.supervision_due_this_week || 0;

  const totalActionable = pendingVerifications.length + referencesToSend.length + 
    referencesToReview.length + expiringSoon.length + stuckWorkers.length;

  // Category counts for tabs
  const categoryCounts = {
    all: totalActionable + inductionIncomplete + interviewsPending,
    verification: pendingVerifications.length,
    references: referencesToSend.length + referencesToReview.length,
    onboarding: stuckWorkers.length + inductionIncomplete + interviewsPending,
    expiring: expiringSoon.length,
    recurring: spotChecksDue + supervisionDue
  };

  if (categoryCounts.all === 0) {
    return (
      <Card className="border border-green-200 bg-green-50/30 shadow-sm">
        <CardContent className="py-8 text-center">
          <CheckCircle className="h-12 w-12 mx-auto mb-3 text-green-500" />
          <p className="font-medium text-green-700">All Tasks Complete</p>
          <p className="text-sm text-green-600 mt-1">No pending actions required. Great work!</p>
        </CardContent>
      </Card>
    );
  }

  // Filter sections based on active tab
  const showSection = (category) => {
    if (activeFilter === 'all') return true;
    return activeFilter === category;
  };

  return (
    <div className="space-y-4" data-testid="actionable-task-queue">
      {/* Header with Tabs */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
          <AlertTriangle className="h-5 w-5 text-amber-600" />
          YOUR TASKS TODAY
          <Badge className="bg-amber-100 text-amber-700 ml-2">{categoryCounts.all}</Badge>
        </h2>
        <div className="flex items-center gap-2">
          <Tabs value={activeFilter} onValueChange={setActiveFilter} className="w-auto">
            <TabsList className="h-8 p-1 bg-gray-100">
              <TabsTrigger value="all" className="text-xs px-2 py-1 h-6">
                All ({categoryCounts.all})
              </TabsTrigger>
              <TabsTrigger value="verification" className="text-xs px-2 py-1 h-6">
                <FileCheck className="h-3 w-3 mr-1" />
                Verify ({categoryCounts.verification})
              </TabsTrigger>
              <TabsTrigger value="references" className="text-xs px-2 py-1 h-6">
                <Mail className="h-3 w-3 mr-1" />
                Refs ({categoryCounts.references})
              </TabsTrigger>
              <TabsTrigger value="onboarding" className="text-xs px-2 py-1 h-6">
                <Users className="h-3 w-3 mr-1" />
                Onboarding ({categoryCounts.onboarding})
              </TabsTrigger>
              {categoryCounts.expiring > 0 && (
                <TabsTrigger value="expiring" className="text-xs px-2 py-1 h-6">
                  <Clock className="h-3 w-3 mr-1" />
                  Expiring ({categoryCounts.expiring})
                </TabsTrigger>
              )}
            </TabsList>
          </Tabs>
          <Button variant="ghost" size="sm" onClick={fetchTasks} className="h-8 w-8 p-0">
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Pending Verifications */}
      {showSection('verification') && pendingVerifications.length > 0 && (
        <Card className="border border-blue-200 shadow-sm overflow-hidden">
          <CardHeader className="py-3 px-4 bg-gradient-to-r from-blue-50 to-blue-100/50">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <FileCheck className="h-4 w-4 text-blue-600" />
                PENDING VERIFICATIONS
                <Badge className="bg-blue-600 text-white ml-1">{tasks.documents_pending_verification}</Badge>
              </CardTitle>
              <Button 
                variant="link" 
                size="sm" 
                className="text-blue-600 p-0 h-auto"
                onClick={() => navigate('/portal/employees')}
              >
                View All <ChevronRight className="h-3 w-3 ml-1" />
              </Button>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            <div className="divide-y divide-gray-100">
              {pendingVerifications.map((doc, idx) => (
                <div key={idx} className="flex items-center justify-between px-4 py-3 hover:bg-blue-50/30 transition-colors">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-gray-800 truncate">{doc.document_type?.replace(/_/g, ' ')}</span>
                      <Badge variant="outline" className="text-xs shrink-0">
                        {doc.employee_name?.split(' ')[0]}
                      </Badge>
                    </div>
                    {doc.uploaded_at && (
                      <span className="text-xs text-gray-400">
                        Uploaded {new Date(doc.uploaded_at).toLocaleDateString()}
                      </span>
                    )}
                  </div>
                  <Button 
                    size="sm" 
                    onClick={() => navigate(`/portal/recruitment/${doc.employee_id}?tab=compliance`)}
                    className="bg-blue-600 hover:bg-blue-700 shrink-0 ml-2"
                  >
                    <Eye className="h-3.5 w-3.5 mr-1" />
                    Verify
                  </Button>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* References to Send */}
      {showSection('references') && referencesToSend.length > 0 && (
        <Card className="border border-purple-200 shadow-sm overflow-hidden">
          <CardHeader className="py-3 px-4 bg-gradient-to-r from-purple-50 to-purple-100/50">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <Mail className="h-4 w-4 text-purple-600" />
                REFERENCES TO SEND
                <Badge className="bg-purple-600 text-white ml-1">{referencesToSend.length}</Badge>
              </CardTitle>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            <div className="divide-y divide-gray-100">
              {referencesToSend.map((ref, idx) => (
                <div key={idx} className="flex items-center justify-between px-4 py-3 hover:bg-purple-50/30 transition-colors">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-gray-800">Reference {ref.reference_num}</span>
                      <span className="text-gray-400">•</span>
                      <span className="text-gray-600 truncate">{ref.employee_name}</span>
                    </div>
                    <span className="text-xs text-gray-400">Referee: {ref.referee_name}</span>
                  </div>
                  <Button 
                    size="sm"
                    variant="outline"
                    onClick={() => handleSendReferenceRequest(ref.employee_id, ref.reference_num)}
                    disabled={actionLoading === `ref-${ref.employee_id}-${ref.reference_num}`}
                    className="text-purple-600 border-purple-200 hover:bg-purple-50 shrink-0 ml-2"
                  >
                    {actionLoading === `ref-${ref.employee_id}-${ref.reference_num}` ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <>
                        <Send className="h-3.5 w-3.5 mr-1" />
                        Send
                      </>
                    )}
                  </Button>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Reference Responses to Review */}
      {showSection('references') && referencesToReview.length > 0 && (
        <Card className="border border-teal-200 shadow-sm overflow-hidden">
          <CardHeader className="py-3 px-4 bg-gradient-to-r from-teal-50 to-teal-100/50">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <MessageSquare className="h-4 w-4 text-teal-600" />
                REFERENCE RESPONSES TO REVIEW
                <Badge className="bg-teal-600 text-white ml-1">{referencesToReview.length}</Badge>
              </CardTitle>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            <div className="divide-y divide-gray-100">
              {referencesToReview.map((ref, idx) => (
                <div key={idx} className="flex items-center justify-between px-4 py-3 hover:bg-teal-50/30 transition-colors">
                  <div className="flex-1">
                    <span className="font-medium text-gray-800">Reference {ref.reference_num}</span>
                    <span className="mx-2 text-gray-400">•</span>
                    <span className="text-gray-600">{ref.employee_name}</span>
                  </div>
                  <Button 
                    size="sm"
                    onClick={() => navigate(`/portal/recruitment/${ref.employee_id}?tab=references`)}
                    className="bg-teal-600 hover:bg-teal-700"
                  >
                    <Eye className="h-3.5 w-3.5 mr-1" />
                    Review
                  </Button>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Induction Checklists Incomplete */}
      {showSection('onboarding') && inductionIncomplete > 0 && (
        <Card className="border border-orange-200 shadow-sm overflow-hidden">
          <CardHeader className="py-3 px-4 bg-gradient-to-r from-orange-50 to-orange-100/50">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <ClipboardList className="h-4 w-4 text-orange-600" />
                INDUCTION CHECKLISTS INCOMPLETE
                <Badge className="bg-orange-600 text-white ml-1">{inductionIncomplete}</Badge>
              </CardTitle>
              <Button 
                variant="link" 
                size="sm" 
                className="text-orange-600 p-0 h-auto"
                onClick={() => navigate('/portal/recruitment')}
              >
                View All <ChevronRight className="h-3 w-3 ml-1" />
              </Button>
            </div>
          </CardHeader>
          <CardContent className="p-3">
            <p className="text-sm text-gray-600">
              {inductionIncomplete} worker{inductionIncomplete !== 1 ? 's' : ''} have incomplete induction checklists.
              Complete these to ensure Care Certificate compliance.
            </p>
          </CardContent>
        </Card>
      )}

      {/* Interviews/Approvals Pending */}
      {showSection('onboarding') && interviewsPending > 0 && (
        <Card className="border border-indigo-200 shadow-sm overflow-hidden">
          <CardHeader className="py-3 px-4 bg-gradient-to-r from-indigo-50 to-indigo-100/50">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <UserCheck className="h-4 w-4 text-indigo-600" />
                INTERVIEWS/APPROVALS PENDING
                <Badge className="bg-indigo-600 text-white ml-1">{interviewsPending}</Badge>
              </CardTitle>
              <Button 
                variant="link" 
                size="sm" 
                className="text-indigo-600 p-0 h-auto"
                onClick={() => navigate('/portal/recruitment')}
              >
                View All <ChevronRight className="h-3 w-3 ml-1" />
              </Button>
            </div>
          </CardHeader>
          <CardContent className="p-3">
            <p className="text-sm text-gray-600">
              {interviewsPending} applicant{interviewsPending !== 1 ? 's' : ''} awaiting interview or recruitment approval.
            </p>
          </CardContent>
        </Card>
      )}

      {/* Expiring Soon */}
      {showSection('expiring') && expiringSoon.length > 0 && (
        <Card className="border border-amber-200 shadow-sm overflow-hidden">
          <CardHeader className="py-3 px-4 bg-gradient-to-r from-amber-50 to-amber-100/50">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <Clock className="h-4 w-4 text-amber-600" />
                EXPIRING SOON
                <Badge className="bg-amber-600 text-white ml-1">{expiringSoon.length}</Badge>
              </CardTitle>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            <div className="divide-y divide-gray-100">
              {expiringSoon.map((item, idx) => (
                <div key={idx} className="flex items-center justify-between px-4 py-3 hover:bg-amber-50/30 transition-colors">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-gray-800 truncate">{item.item_name}</span>
                      <Badge variant="outline" className="text-xs shrink-0">
                        {item.employee_name?.split(' ')[0]}
                      </Badge>
                    </div>
                    <Badge className={cn(
                      "text-xs mt-1",
                      item.days_left <= 14 ? "bg-red-100 text-red-700" :
                      item.days_left <= 30 ? "bg-amber-100 text-amber-700" :
                      "bg-blue-100 text-blue-700"
                    )}>
                      {item.days_left} days left
                    </Badge>
                  </div>
                  <Button 
                    size="sm"
                    variant="outline"
                    onClick={() => handleSendReminder(item.employee_id, item.type)}
                    disabled={actionLoading === `reminder-${item.employee_id}`}
                    className="text-amber-600 border-amber-200 hover:bg-amber-50 shrink-0 ml-2"
                  >
                    {actionLoading === `reminder-${item.employee_id}` ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <>
                        <Send className="h-3.5 w-3.5 mr-1" />
                        Remind
                      </>
                    )}
                  </Button>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Spot Checks & Supervision Due */}
      {showSection('recurring') && (spotChecksDue > 0 || supervisionDue > 0) && (
        <Card className="border border-cyan-200 shadow-sm overflow-hidden">
          <CardHeader className="py-3 px-4 bg-gradient-to-r from-cyan-50 to-cyan-100/50">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <GraduationCap className="h-4 w-4 text-cyan-600" />
                RECURRING COMPLIANCE DUE THIS WEEK
              </CardTitle>
              <Button 
                variant="link" 
                size="sm" 
                className="text-cyan-600 p-0 h-auto"
                onClick={() => navigate('/portal/compliance-centre')}
              >
                View All <ChevronRight className="h-3 w-3 ml-1" />
              </Button>
            </div>
          </CardHeader>
          <CardContent className="p-3">
            <div className="flex gap-4">
              {spotChecksDue > 0 && (
                <div className="flex items-center gap-2 px-3 py-2 bg-white rounded-lg border">
                  <ClipboardList className="h-4 w-4 text-cyan-600" />
                  <span className="text-sm"><strong>{spotChecksDue}</strong> Spot Checks</span>
                </div>
              )}
              {supervisionDue > 0 && (
                <div className="flex items-center gap-2 px-3 py-2 bg-white rounded-lg border">
                  <Users className="h-4 w-4 text-cyan-600" />
                  <span className="text-sm"><strong>{supervisionDue}</strong> Supervisions</span>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Workers Stuck in Onboarding */}
      {showSection('onboarding') && stuckWorkers.length > 0 && (
        <Card className="border border-slate-200 shadow-sm overflow-hidden">
          <CardHeader className="py-3 px-4 bg-gradient-to-r from-slate-50 to-slate-100/50">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <Users className="h-4 w-4 text-slate-600" />
                WORKERS STUCK IN ONBOARDING
                <Badge className="bg-slate-600 text-white ml-1">{stuckWorkers.length}</Badge>
              </CardTitle>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            <div className="divide-y divide-gray-100">
              {stuckWorkers.map((worker, idx) => (
                <div key={idx} className="flex items-center justify-between px-4 py-3 hover:bg-slate-50/30 transition-colors">
                  <div className="flex-1 flex items-center gap-3">
                    <span className="font-medium text-gray-800">{worker.employee_name}</span>
                    <Badge variant="outline" className={cn(
                      "text-xs",
                      worker.progress < 25 ? "border-red-200 text-red-600" :
                      worker.progress < 50 ? "border-amber-200 text-amber-600" :
                      "border-blue-200 text-blue-600"
                    )}>
                      {worker.progress}% complete
                    </Badge>
                  </div>
                  <div className="flex gap-2">
                    <Button 
                      size="sm"
                      variant="outline"
                      onClick={() => navigate(`/portal/recruitment/${worker.employee_id}`)}
                    >
                      <Eye className="h-3.5 w-3.5 mr-1" />
                      View
                    </Button>
                    <Button 
                      size="sm"
                      variant="outline"
                      onClick={() => handleSendReminder(worker.employee_id, 'general')}
                      disabled={actionLoading === `reminder-${worker.employee_id}`}
                    >
                      {actionLoading === `reminder-${worker.employee_id}` ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <>
                          <Send className="h-3.5 w-3.5 mr-1" />
                          Remind
                        </>
                      )}
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
