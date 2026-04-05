/**
 * ActionableTaskQueue - Enhanced Admin Dashboard Task Queue
 * 
 * Shows specific actionable items with direct action buttons per user's CQC requirement:
 * - Pending Verifications with [Verify] button
 * - References to Send with [Send Request] button
 * - Reference Responses to Review with [Review] button
 * - Expiring Soon with [Send Reminder] button
 * - Workers Stuck in Onboarding with [Send Reminder] button
 */

import { useState, useEffect } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { 
  Loader2, FileCheck, Mail, MessageSquare, Clock, Users, 
  ChevronRight, RefreshCw, CheckCircle, Send, Eye, AlertTriangle
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

  const totalActionable = pendingVerifications.length + referencesToSend.length + 
    referencesToReview.length + expiringSoon.length + stuckWorkers.length;

  if (totalActionable === 0) {
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

  return (
    <div className="space-y-4" data-testid="actionable-task-queue">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
          <AlertTriangle className="h-5 w-5 text-amber-600" />
          YOUR TASKS TODAY
          <Badge className="bg-amber-100 text-amber-700 ml-2">{totalActionable}</Badge>
        </h2>
        <Button variant="ghost" size="sm" onClick={fetchTasks}>
          <RefreshCw className="h-4 w-4" />
        </Button>
      </div>

      {/* Pending Verifications */}
      {pendingVerifications.length > 0 && (
        <Card className="border border-blue-200 shadow-sm">
          <CardHeader className="py-3 px-4 bg-blue-50/50">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <FileCheck className="h-4 w-4 text-blue-600" />
                PENDING VERIFICATIONS ({tasks.documents_pending_verification})
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
                <div key={idx} className="flex items-center justify-between px-4 py-3 hover:bg-gray-50">
                  <div className="flex-1">
                    <span className="font-medium text-gray-800">{doc.document_type}</span>
                    <span className="mx-2 text-gray-400">•</span>
                    <span className="text-gray-600">{doc.employee_name}</span>
                    {doc.uploaded_at && (
                      <span className="text-xs text-gray-400 ml-2">
                        Uploaded {new Date(doc.uploaded_at).toLocaleDateString()}
                      </span>
                    )}
                  </div>
                  <Button 
                    size="sm" 
                    onClick={() => navigate(`/portal/employees/${doc.employee_id}?tab=compliance`)}
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
      {referencesToSend.length > 0 && (
        <Card className="border border-purple-200 shadow-sm">
          <CardHeader className="py-3 px-4 bg-purple-50/50">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <Mail className="h-4 w-4 text-purple-600" />
                REFERENCES TO SEND ({referencesToSend.length})
              </CardTitle>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            <div className="divide-y divide-gray-100">
              {referencesToSend.map((ref, idx) => (
                <div key={idx} className="flex items-center justify-between px-4 py-3 hover:bg-gray-50">
                  <div className="flex-1">
                    <span className="font-medium text-gray-800">Reference {ref.reference_num}</span>
                    <span className="mx-2 text-gray-400">•</span>
                    <span className="text-gray-600">{ref.employee_name}</span>
                    <span className="text-xs text-gray-400 ml-2">({ref.referee_name})</span>
                  </div>
                  <Button 
                    size="sm"
                    variant="outline"
                    onClick={() => handleSendReferenceRequest(ref.employee_id, ref.reference_num)}
                    disabled={actionLoading === `ref-${ref.employee_id}-${ref.reference_num}`}
                    className="text-purple-600 border-purple-200"
                  >
                    {actionLoading === `ref-${ref.employee_id}-${ref.reference_num}` ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <>
                        <Send className="h-3.5 w-3.5 mr-1" />
                        Send Request
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
      {referencesToReview.length > 0 && (
        <Card className="border border-teal-200 shadow-sm">
          <CardHeader className="py-3 px-4 bg-teal-50/50">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <MessageSquare className="h-4 w-4 text-teal-600" />
                REFERENCE RESPONSES TO REVIEW ({referencesToReview.length})
              </CardTitle>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            <div className="divide-y divide-gray-100">
              {referencesToReview.map((ref, idx) => (
                <div key={idx} className="flex items-center justify-between px-4 py-3 hover:bg-gray-50">
                  <div className="flex-1">
                    <span className="font-medium text-gray-800">Reference {ref.reference_num}</span>
                    <span className="mx-2 text-gray-400">•</span>
                    <span className="text-gray-600">{ref.employee_name}</span>
                  </div>
                  <Button 
                    size="sm"
                    onClick={() => navigate(`/portal/employees/${ref.employee_id}?tab=references`)}
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

      {/* Expiring Soon */}
      {expiringSoon.length > 0 && (
        <Card className="border border-amber-200 shadow-sm">
          <CardHeader className="py-3 px-4 bg-amber-50/50">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <Clock className="h-4 w-4 text-amber-600" />
                EXPIRING SOON ({expiringSoon.length})
              </CardTitle>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            <div className="divide-y divide-gray-100">
              {expiringSoon.map((item, idx) => (
                <div key={idx} className="flex items-center justify-between px-4 py-3 hover:bg-gray-50">
                  <div className="flex-1">
                    <span className="font-medium text-gray-800">{item.item_name}</span>
                    <span className="mx-2 text-gray-400">•</span>
                    <span className="text-gray-600">{item.employee_name}</span>
                    <Badge className={cn(
                      "ml-2 text-xs",
                      item.days_left <= 14 ? "bg-red-100 text-red-700" :
                      item.days_left <= 30 ? "bg-amber-100 text-amber-700" :
                      "bg-blue-100 text-blue-700"
                    )}>
                      {item.days_left} days
                    </Badge>
                  </div>
                  <Button 
                    size="sm"
                    variant="outline"
                    onClick={() => handleSendReminder(item.employee_id, item.type)}
                    disabled={actionLoading === `reminder-${item.employee_id}`}
                    className="text-amber-600 border-amber-200"
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

      {/* Workers Stuck in Onboarding */}
      {stuckWorkers.length > 0 && (
        <Card className="border border-gray-200 shadow-sm">
          <CardHeader className="py-3 px-4 bg-gray-50/50">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <Users className="h-4 w-4 text-gray-600" />
                WORKERS STUCK IN ONBOARDING ({stuckWorkers.length})
              </CardTitle>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            <div className="divide-y divide-gray-100">
              {stuckWorkers.map((worker, idx) => (
                <div key={idx} className="flex items-center justify-between px-4 py-3 hover:bg-gray-50">
                  <div className="flex-1 flex items-center gap-3">
                    <span className="font-medium text-gray-800">{worker.employee_name}</span>
                    <Badge variant="outline" className="text-xs">
                      {worker.progress}% complete
                    </Badge>
                  </div>
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
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
