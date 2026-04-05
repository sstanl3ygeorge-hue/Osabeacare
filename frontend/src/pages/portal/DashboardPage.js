import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Progress } from '../../components/ui/progress';
import EmployeeAvatar from '../../components/portal/EmployeeAvatar';
import AdminTaskQueue from '../../components/admin/AdminTaskQueue';
import ActionableTaskQueue from '../../components/admin/ActionableTaskQueue';
import TrainingExpiryAlerts from '../../components/admin/TrainingExpiryAlerts';
import {
  Users, UserPlus, AlertTriangle, FileX, Shield, ShieldCheck,
  FileCheck, CalendarClock, ArrowRight, Loader2, Upload, FileText,
  Clock, AlertCircle, CheckCircle, ExternalLink, ClipboardList, GraduationCap
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function DashboardPage() {
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [employees, setEmployees] = useState([]);
  const [expiryAlerts, setExpiryAlerts] = useState(null);
  const [recurringCompliance, setRecurringCompliance] = useState(null);
  const [trainingSummary, setTrainingSummary] = useState(null);
  const { token } = useAuth();

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [statsRes, employeesRes, expiryRes, recurringRes, trainingRes] = await Promise.all([
          axios.get(`${API}/dashboard/stats`, { headers: { Authorization: `Bearer ${token}` } }),
          // Use staff/employees endpoint for employee-only data (excludes applicants)
          axios.get(`${API}/staff/employees`, { headers: { Authorization: `Bearer ${token}` } }),
          axios.get(`${API}/dashboard/expiry-alerts`, { headers: { Authorization: `Bearer ${token}` } }).catch(() => ({ data: null })),
          axios.get(`${API}/recurring-compliance/dashboard-summary`, { headers: { Authorization: `Bearer ${token}` } }).catch(() => ({ data: null })),
          axios.get(`${API}/dashboard/training-summary`, { headers: { Authorization: `Bearer ${token}` } }).catch(() => ({ data: null }))
        ]);
        setStats(statsRes.data);
        // Ensure we only have employee-status records (staff, not applicants)
        const staffOnly = (employeesRes.data?.employees || employeesRes.data || [])
          .filter(e => ['onboarding', 'active', 'inactive'].includes(e.status));
        setEmployees(staffOnly);
        setExpiryAlerts(expiryRes.data);
        setRecurringCompliance(recurringRes.data);
        setTrainingSummary(trainingRes.data);
      } catch (error) {
        console.error('Failed to fetch dashboard data:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [token]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  // ========== EMPTY STATE: Get Started Guide ==========
  if (employees.length === 0) {
    return (
      <div className="space-y-8" data-testid="dashboard-page-empty">
        {/* Header */}
        <div>
          <h1 className="font-heading text-2xl sm:text-3xl font-bold text-text-primary">
            Welcome to Osabea Healthcare Compliance Portal
          </h1>
          <p className="text-text-muted mt-1">
            Get started by adding your first employee or inviting applicants.
          </p>
        </div>

        {/* Get Started Card */}
        <Card className="border-2 border-primary/20 bg-gradient-to-br from-primary/5 to-white shadow-lg">
          <CardContent className="pt-8 pb-8">
            <div className="text-center max-w-md mx-auto">
              <div className="w-20 h-20 bg-primary/10 rounded-2xl flex items-center justify-center mx-auto mb-6">
                <Users className="h-10 w-10 text-primary" />
              </div>
              
              <h2 className="text-xl font-heading font-bold text-text-primary mb-2">
                No Employees Yet
              </h2>
              <p className="text-text-muted mb-8">
                Add your first employee to start tracking compliance, or share your public application link to invite new applicants.
              </p>

              <div className="space-y-4">
                <Link to="/portal/employees" className="block">
                  <Button className="w-full bg-primary hover:bg-primary-hover text-white rounded-xl py-6 text-lg" data-testid="get-started-add-employee">
                    <UserPlus className="mr-2 h-5 w-5" />
                    Add New Employee
                  </Button>
                </Link>

                <div className="relative">
                  <div className="absolute inset-0 flex items-center">
                    <div className="w-full border-t border-gray-200"></div>
                  </div>
                  <div className="relative flex justify-center text-xs uppercase">
                    <span className="bg-white px-2 text-text-muted">or</span>
                  </div>
                </div>

                <Link to="/portal/applications" className="block">
                  <Button variant="outline" className="w-full rounded-xl py-5" data-testid="get-started-applications">
                    <ExternalLink className="mr-2 h-4 w-4" />
                    Share Application Link
                  </Button>
                </Link>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Quick Setup Checklist */}
        <Card className="border-[#E4E8EB] shadow-sm">
          <CardHeader>
            <CardTitle className="font-heading text-lg">Quick Setup Checklist</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center">
                  <span className="text-blue-600 font-bold text-sm">1</span>
                </div>
                <div className="flex-1">
                  <p className="font-medium text-text-primary">Add your first employee</p>
                  <p className="text-sm text-text-muted">Enter their details and upload compliance documents</p>
                </div>
                <Link to="/portal/employees">
                  <Button size="sm" variant="outline">Start</Button>
                </Link>
              </div>
              
              <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center">
                  <span className="text-blue-600 font-bold text-sm">2</span>
                </div>
                <div className="flex-1">
                  <p className="font-medium text-text-primary">Upload company policies</p>
                  <p className="text-sm text-text-muted">Add policies for employees to acknowledge</p>
                </div>
                <Link to="/portal/compliance-centre?tab=policies">
                  <Button size="sm" variant="outline">Setup</Button>
                </Link>
              </div>
              
              <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center">
                  <span className="text-blue-600 font-bold text-sm">3</span>
                </div>
                <div className="flex-1">
                  <p className="font-medium text-text-primary">Configure training requirements</p>
                  <p className="text-sm text-text-muted">Set up mandatory training for your staff</p>
                </div>
                <Link to="/portal/training">
                  <Button size="sm" variant="outline">Configure</Button>
                </Link>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // ========== NORMAL DASHBOARD (employees exist) ==========
  
  // Calculate workforce readiness counts using 3-tier system (authoritative)
  const readyToWork = employees.filter(e => 
    e.work_readiness_3tier?.status === 'READY_TO_WORK'
  ).length;
  const supervisedStart = employees.filter(e => 
    e.work_readiness_3tier?.status === 'READY_WITH_CONDITIONS'
  ).length;
  const notReady = employees.filter(e => 
    e.work_readiness_3tier?.status === 'NOT_READY' ||
    !e.work_readiness_3tier
  ).length;

  // Calculate onboarding stats
  const onboarding = employees.filter(e => e.status === 'onboarding').length;
  const avgCompletion = employees.length > 0 
    ? Math.round(employees.reduce((sum, e) => sum + (e.completion_percentage || 0), 0) / employees.length)
    : 0;

  // Calculate attention items from expiry alerts API
  const expiredDocs = expiryAlerts?.expired?.total_items || 0;
  const expiringSoon = expiryAlerts?.expiring_soon?.total_items || stats?.expiring_30_days || 0;
  const policiesNotAcknowledged = stats?.unsigned_policies || 0;
  
  // Calculate staff not ready to work
  const staffNotReady = notReady;
  
  const needsAttentionTotal = expiredDocs + expiringSoon + policiesNotAcknowledged + staffNotReady;

  return (
    <div className="space-y-8" data-testid="dashboard-page">
      {/* Header with microcopy */}
      <div>
        <h1 className="font-heading text-2xl sm:text-3xl font-bold text-text-primary">
          Compliance Dashboard
        </h1>
        <p className="text-text-muted mt-1">
          This dashboard highlights what needs attention today. Start with expired items and required checks.
        </p>
      </div>

      {/* ACTIONABLE TASK QUEUE - New CQC-compliant task list */}
      <ActionableTaskQueue />

      {/* Admin Task Queue (Summary counts) */}
      <div className="mt-4">
        <AdminTaskQueue />
      </div>

      {/* PRIMARY: Needs Attention */}
      <Card className={`border-2 ${needsAttentionTotal > 0 ? 'border-red-200 bg-red-50' : 'border-green-200 bg-green-50'} shadow-sm`}>
        <CardHeader className="pb-3">
          <CardTitle className="font-heading text-lg flex items-center gap-2">
            {needsAttentionTotal > 0 ? (
              <>
                <AlertTriangle className="h-5 w-5 text-red-600" />
                <span className="text-red-700">Needs Attention</span>
              </>
            ) : (
              <>
                <CheckCircle className="h-5 w-5 text-green-600" />
                <span className="text-green-700">All Clear</span>
              </>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {needsAttentionTotal > 0 ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* Expired Documents - Critical → Training Matrix filtered to expired */}
              <div 
                onClick={() => expiredDocs > 0 && navigate('/portal/training?filter=expired')}
                className={`p-4 rounded-xl transition-all ${expiredDocs > 0 ? 'bg-red-100 border border-red-200 cursor-pointer hover:bg-red-150 hover:shadow-md' : 'bg-white border border-gray-200'}`}
                title={expiredDocs > 0 ? 'View expired items' : ''}
                data-testid="card-expired"
              >
                <div className="flex items-center gap-3">
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${expiredDocs > 0 ? 'bg-red-200' : 'bg-gray-100'}`}>
                    <FileX className={`h-5 w-5 ${expiredDocs > 0 ? 'text-red-600' : 'text-gray-400'}`} />
                  </div>
                  <div className="flex-1">
                    <p className={`text-2xl font-heading font-bold ${expiredDocs > 0 ? 'text-red-700' : 'text-gray-400'}`}>{expiredDocs}</p>
                    <p className={`text-sm ${expiredDocs > 0 ? 'text-red-600' : 'text-gray-500'}`}>Expired</p>
                  </div>
                  {expiredDocs > 0 && <ArrowRight className="h-4 w-4 text-red-400" />}
                </div>
                {expiredDocs > 0 && <p className="text-xs text-red-500 mt-2">Review now →</p>}
              </div>
              
              {/* Expiring Soon → Training Matrix filtered to expiring_soon */}
              <div 
                onClick={() => expiringSoon > 0 && navigate('/portal/training?filter=expiring_soon')}
                className={`p-4 rounded-xl transition-all ${expiringSoon > 0 ? 'bg-amber-100 border border-amber-200 cursor-pointer hover:bg-amber-150 hover:shadow-md' : 'bg-white border border-gray-200'}`}
                title={expiringSoon > 0 ? 'View items needing renewal' : ''}
                data-testid="card-expiring"
              >
                <div className="flex items-center gap-3">
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${expiringSoon > 0 ? 'bg-amber-200' : 'bg-gray-100'}`}>
                    <CalendarClock className={`h-5 w-5 ${expiringSoon > 0 ? 'text-amber-600' : 'text-gray-400'}`} />
                  </div>
                  <div className="flex-1">
                    <p className={`text-2xl font-heading font-bold ${expiringSoon > 0 ? 'text-amber-700' : 'text-gray-400'}`}>{expiringSoon}</p>
                    <p className={`text-sm ${expiringSoon > 0 ? 'text-amber-600' : 'text-gray-500'}`}>Needs Renewal</p>
                  </div>
                  {expiringSoon > 0 && <ArrowRight className="h-4 w-4 text-amber-400" />}
                </div>
                {expiringSoon > 0 && <p className="text-xs text-amber-600 mt-2">See items →</p>}
              </div>
              
              {/* Staff Not Ready → Employees filtered to not_ready */}
              <div 
                onClick={() => staffNotReady > 0 && navigate('/portal/employees?work_readiness=not_ready')}
                className={`p-4 rounded-xl transition-all ${staffNotReady > 0 ? 'bg-red-100 border border-red-200 cursor-pointer hover:bg-red-150 hover:shadow-md' : 'bg-white border border-gray-200'}`}
                title={staffNotReady > 0 ? 'View affected staff' : ''}
                data-testid="card-not-ready"
              >
                <div className="flex items-center gap-3">
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${staffNotReady > 0 ? 'bg-red-200' : 'bg-gray-100'}`}>
                    <AlertTriangle className={`h-5 w-5 ${staffNotReady > 0 ? 'text-red-600' : 'text-gray-400'}`} />
                  </div>
                  <div className="flex-1">
                    <p className={`text-2xl font-heading font-bold ${staffNotReady > 0 ? 'text-red-700' : 'text-gray-400'}`}>{staffNotReady}</p>
                    <p className={`text-sm ${staffNotReady > 0 ? 'text-red-600' : 'text-gray-500'}`}>Not Ready to Work</p>
                  </div>
                  {staffNotReady > 0 && <ArrowRight className="h-4 w-4 text-red-400" />}
                </div>
                {staffNotReady > 0 && <p className="text-xs text-red-500 mt-2">View staff →</p>}
              </div>
              
              {/* Policies Not Acknowledged → Compliance Centre policies tab */}
              <div 
                onClick={() => policiesNotAcknowledged > 0 && navigate('/portal/compliance-centre?tab=policies')}
                className={`p-4 rounded-xl transition-all ${policiesNotAcknowledged > 0 ? 'bg-blue-100 border border-blue-200 cursor-pointer hover:bg-blue-150 hover:shadow-md' : 'bg-white border border-gray-200'}`}
                title={policiesNotAcknowledged > 0 ? 'Review policy acknowledgements' : ''}
                data-testid="card-policies"
              >
                <div className="flex items-center gap-3">
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${policiesNotAcknowledged > 0 ? 'bg-blue-200' : 'bg-gray-100'}`}>
                    <FileCheck className={`h-5 w-5 ${policiesNotAcknowledged > 0 ? 'text-blue-600' : 'text-gray-400'}`} />
                  </div>
                  <div className="flex-1">
                    <p className={`text-2xl font-heading font-bold ${policiesNotAcknowledged > 0 ? 'text-blue-700' : 'text-gray-400'}`}>{policiesNotAcknowledged}</p>
                    <p className={`text-sm ${policiesNotAcknowledged > 0 ? 'text-blue-600' : 'text-gray-500'}`}>Policies Not Yet Acknowledged</p>
                  </div>
                  {policiesNotAcknowledged > 0 && <ArrowRight className="h-4 w-4 text-blue-400" />}
                </div>
                {policiesNotAcknowledged > 0 && <p className="text-xs text-blue-500 mt-2">Open list →</p>}
              </div>
            </div>
          ) : (
            <p className="text-green-700">No expired documents, no items expiring soon, all staff ready, and all policies acknowledged. Great work!</p>
          )}
        </CardContent>
      </Card>

      {/* TRAINING EXPIRY ALERTS */}
      <TrainingExpiryAlerts />

      {/* SECONDARY: Workforce Readiness + Onboarding Progress */}
      <div className="grid lg:grid-cols-2 gap-6">
        {/* Workforce Readiness */}
        <Card className="border-[#E4E8EB] shadow-sm">
          <CardHeader>
            <CardTitle className="font-heading text-lg flex items-center gap-2">
              <Shield className="h-5 w-5 text-primary" />
              Workforce Readiness
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {/* Ready to Work → Employees filtered to ready_to_work */}
              <div 
                onClick={() => readyToWork > 0 && navigate('/portal/employees?work_readiness=ready_to_work')}
                className={`flex items-center justify-between p-3 bg-green-50 rounded-xl border border-green-200 transition-all ${readyToWork > 0 ? 'cursor-pointer hover:bg-green-100 hover:shadow-sm' : ''}`}
                title={readyToWork > 0 ? 'View ready staff' : ''}
                data-testid="card-ready-to-work"
              >
                <div className="flex items-center gap-3">
                  <ShieldCheck className="h-5 w-5 text-green-600" />
                  <span className="font-medium text-green-700">Ready to Work</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-2xl font-heading font-bold text-green-700">{readyToWork}</span>
                  {readyToWork > 0 && <ArrowRight className="h-4 w-4 text-green-400" />}
                </div>
              </div>
              
              {/* Supervised Start → Employees filtered to supervised_start */}
              <div 
                onClick={() => supervisedStart > 0 && navigate('/portal/employees?work_readiness=supervised_start')}
                className={`flex items-center justify-between p-3 bg-amber-50 rounded-xl border border-amber-200 transition-all ${supervisedStart > 0 ? 'cursor-pointer hover:bg-amber-100 hover:shadow-sm' : ''}`}
                title={supervisedStart > 0 ? 'View staff on supervised start' : ''}
                data-testid="card-supervised-start"
              >
                <div className="flex items-center gap-3">
                  <AlertCircle className="h-5 w-5 text-amber-600" />
                  <span className="font-medium text-amber-700">Supervised Start</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-2xl font-heading font-bold text-amber-700">{supervisedStart}</span>
                  {supervisedStart > 0 && <ArrowRight className="h-4 w-4 text-amber-400" />}
                </div>
              </div>
              
              {/* Not Ready → Employees filtered to not_ready */}
              <div 
                onClick={() => notReady > 0 && navigate('/portal/employees?work_readiness=not_ready')}
                className={`flex items-center justify-between p-3 bg-red-50 rounded-xl border border-red-200 transition-all ${notReady > 0 ? 'cursor-pointer hover:bg-red-100 hover:shadow-sm' : ''}`}
                title={notReady > 0 ? 'View affected staff' : ''}
                data-testid="card-not-ready-workforce"
              >
                <div className="flex items-center gap-3">
                  <AlertTriangle className="h-5 w-5 text-red-600" />
                  <span className="font-medium text-red-700">Not Ready</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-2xl font-heading font-bold text-red-700">{notReady}</span>
                  {notReady > 0 && <ArrowRight className="h-4 w-4 text-red-400" />}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Onboarding Progress */}
        <Card className="border-[#E4E8EB] shadow-sm">
          <CardHeader>
            <CardTitle className="font-heading text-lg flex items-center gap-2">
              <Clock className="h-5 w-5 text-primary" />
              Onboarding Progress
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center justify-between p-3 bg-blue-50 rounded-xl border border-blue-200">
                <div className="flex items-center gap-3">
                  <Users className="h-5 w-5 text-blue-600" />
                  <span className="font-medium text-blue-700">In Progress</span>
                </div>
                <span className="text-2xl font-heading font-bold text-blue-700">{onboarding}</span>
              </div>
              <div className="p-4 bg-[#F8FAFA] rounded-xl border border-[#E4E8EB]">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-text-muted">Average Employee Compliance</span>
                  <span className="font-semibold text-text-primary">{avgCompletion}%</span>
                </div>
                <Progress value={avgCompletion} className="h-3" />
              </div>
              <div className="flex justify-between items-center p-3 bg-[#F8FAFA] rounded-xl border border-[#E4E8EB]">
                <span className="text-text-muted">Total Employees</span>
                <span className="text-xl font-heading font-bold text-text-primary">{employees.length}</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recurring Compliance Summary */}
      {recurringCompliance && (recurringCompliance.summary?.overdue > 0 || recurringCompliance.summary?.due > 0 || recurringCompliance.summary?.upcoming > 0) && (
        <Card className="border-[#E4E8EB] shadow-sm">
          <CardHeader>
            <CardTitle className="font-heading text-lg flex items-center gap-2">
              <ClipboardList className="h-5 w-5 text-primary" />
              Recurring Compliance
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-4">
              {/* Overdue */}
              <div className={`p-4 rounded-xl border ${recurringCompliance.summary?.overdue > 0 ? 'bg-red-50 border-red-200' : 'bg-white border-[#E4E8EB]'}`}>
                <div className="flex items-center justify-between">
                  <span className={`text-sm font-medium ${recurringCompliance.summary?.overdue > 0 ? 'text-red-700' : 'text-gray-500'}`}>Overdue</span>
                  <AlertTriangle className={`h-4 w-4 ${recurringCompliance.summary?.overdue > 0 ? 'text-red-600' : 'text-gray-400'}`} />
                </div>
                <p className={`text-2xl font-heading font-bold mt-1 ${recurringCompliance.summary?.overdue > 0 ? 'text-red-700' : 'text-gray-400'}`}>
                  {recurringCompliance.summary?.overdue || 0}
                </p>
              </div>
              
              {/* Due */}
              <div className={`p-4 rounded-xl border ${recurringCompliance.summary?.due > 0 ? 'bg-amber-50 border-amber-200' : 'bg-white border-[#E4E8EB]'}`}>
                <div className="flex items-center justify-between">
                  <span className={`text-sm font-medium ${recurringCompliance.summary?.due > 0 ? 'text-amber-700' : 'text-gray-500'}`}>Due Now</span>
                  <Clock className={`h-4 w-4 ${recurringCompliance.summary?.due > 0 ? 'text-amber-600' : 'text-gray-400'}`} />
                </div>
                <p className={`text-2xl font-heading font-bold mt-1 ${recurringCompliance.summary?.due > 0 ? 'text-amber-700' : 'text-gray-400'}`}>
                  {recurringCompliance.summary?.due || 0}
                </p>
              </div>
              
              {/* Upcoming */}
              <div className="p-4 rounded-xl border bg-white border-[#E4E8EB]">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-blue-700">Upcoming</span>
                  <CalendarClock className="h-4 w-4 text-blue-600" />
                </div>
                <p className="text-2xl font-heading font-bold mt-1 text-blue-700">
                  {recurringCompliance.summary?.upcoming || 0}
                </p>
              </div>
            </div>

            {/* Urgent Items List */}
            {(recurringCompliance.overdue_items?.length > 0 || recurringCompliance.due_items?.length > 0) && (
              <div className="space-y-2">
                <p className="text-sm font-medium text-text-muted">Action Required:</p>
                {recurringCompliance.overdue_items?.slice(0, 3).map((item, idx) => (
                  <Link 
                    key={`overdue-${idx}`}
                    to={`/portal/employees/${item.employee_id}?tab=recurring`}
                    className="flex items-center justify-between p-2 rounded-lg bg-red-50 hover:bg-red-100 transition-colors"
                    data-testid={`recurring-overdue-${idx}`}
                  >
                    <div className="flex items-center gap-2">
                      <AlertTriangle className="h-4 w-4 text-red-600" />
                      <span className="text-sm text-red-800">{item.item_name}</span>
                      <span className="text-xs text-red-600">({item.employee_name})</span>
                    </div>
                    <span className="text-xs text-red-600">{Math.abs(item.days_value || 0)}d overdue</span>
                  </Link>
                ))}
                {recurringCompliance.due_items?.slice(0, 2).map((item, idx) => (
                  <Link 
                    key={`due-${idx}`}
                    to={`/portal/employees/${item.employee_id}?tab=recurring`}
                    className="flex items-center justify-between p-2 rounded-lg bg-amber-50 hover:bg-amber-100 transition-colors"
                    data-testid={`recurring-due-${idx}`}
                  >
                    <div className="flex items-center gap-2">
                      <Clock className="h-4 w-4 text-amber-600" />
                      <span className="text-sm text-amber-800">{item.item_name}</span>
                      <span className="text-xs text-amber-600">({item.employee_name})</span>
                    </div>
                    <span className="text-xs text-amber-600">Due in {item.days_value || 0}d</span>
                  </Link>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Training Summary */}
      {trainingSummary && (trainingSummary.training_overdue_count > 0 || trainingSummary.training_due_soon_count > 0 || trainingSummary.employees_blocked_by_training > 0) && (
        <Card className="border-[#E4E8EB] shadow-sm">
          <CardHeader>
            <CardTitle className="font-heading text-lg flex items-center gap-2">
              <GraduationCap className="h-5 w-5 text-primary" />
              Training Status
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-4">
              {/* Blocked by Training */}
              <div className={`p-4 rounded-xl border ${trainingSummary.employees_blocked_by_training > 0 ? 'bg-red-50 border-red-200' : 'bg-white border-[#E4E8EB]'}`}>
                <div className="flex items-center justify-between">
                  <span className={`text-sm font-medium ${trainingSummary.employees_blocked_by_training > 0 ? 'text-red-700' : 'text-gray-500'}`}>Blocked</span>
                  <AlertTriangle className={`h-4 w-4 ${trainingSummary.employees_blocked_by_training > 0 ? 'text-red-600' : 'text-gray-400'}`} />
                </div>
                <p className={`text-2xl font-heading font-bold mt-1 ${trainingSummary.employees_blocked_by_training > 0 ? 'text-red-700' : 'text-gray-400'}`}>
                  {trainingSummary.employees_blocked_by_training || 0}
                </p>
              </div>
              
              {/* Overdue */}
              <div className={`p-4 rounded-xl border ${trainingSummary.training_overdue_count > 0 ? 'bg-amber-50 border-amber-200' : 'bg-white border-[#E4E8EB]'}`}>
                <div className="flex items-center justify-between">
                  <span className={`text-sm font-medium ${trainingSummary.training_overdue_count > 0 ? 'text-amber-700' : 'text-gray-500'}`}>Overdue</span>
                  <Clock className={`h-4 w-4 ${trainingSummary.training_overdue_count > 0 ? 'text-amber-600' : 'text-gray-400'}`} />
                </div>
                <p className={`text-2xl font-heading font-bold mt-1 ${trainingSummary.training_overdue_count > 0 ? 'text-amber-700' : 'text-gray-400'}`}>
                  {trainingSummary.training_overdue_count || 0}
                </p>
              </div>
              
              {/* Due Soon */}
              <div className={`p-4 rounded-xl border ${trainingSummary.training_due_soon_count > 0 ? 'bg-blue-50 border-blue-200' : 'bg-white border-[#E4E8EB]'}`}>
                <div className="flex items-center justify-between">
                  <span className={`text-sm font-medium ${trainingSummary.training_due_soon_count > 0 ? 'text-blue-700' : 'text-gray-500'}`}>Due Soon</span>
                  <CalendarClock className={`h-4 w-4 ${trainingSummary.training_due_soon_count > 0 ? 'text-blue-600' : 'text-gray-400'}`} />
                </div>
                <p className={`text-2xl font-heading font-bold mt-1 ${trainingSummary.training_due_soon_count > 0 ? 'text-blue-700' : 'text-gray-400'}`}>
                  {trainingSummary.training_due_soon_count || 0}
                </p>
              </div>
            </div>

            {/* Blocked Employees List */}
            {trainingSummary.blocked_employees?.length > 0 && (
              <div className="space-y-2">
                <p className="text-sm font-medium text-text-muted">Staff Blocked by Training:</p>
                {trainingSummary.blocked_employees.slice(0, 3).map((emp, idx) => (
                  <Link 
                    key={`blocked-${idx}`}
                    to={`/portal/employees/${emp.id}?tab=training`}
                    className="flex items-center justify-between p-2 rounded-lg bg-red-50 hover:bg-red-100 transition-colors"
                    data-testid={`training-blocked-${idx}`}
                  >
                    <div className="flex items-center gap-2">
                      <GraduationCap className="h-4 w-4 text-red-600" />
                      <span className="text-sm text-red-800">{emp.name}</span>
                    </div>
                    <span className="text-xs text-red-600">
                      {emp.blockers?.length || 0} training item(s) required
                    </span>
                  </Link>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Quick Actions & Recent Employees */}
      <div className="grid lg:grid-cols-3 gap-6">
        {/* Quick Actions */}
        <Card className="border-[#E4E8EB] shadow-sm">
          <CardHeader>
            <CardTitle className="font-heading text-lg">Quick Actions</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Link to="/portal/employees" className="block">
              <Button variant="outline" className="w-full justify-start rounded-xl border-[#E4E8EB]" data-testid="quick-add-employee">
                <UserPlus className="mr-2 h-4 w-4" />
                Add New Employee
              </Button>
            </Link>
            <Link to="/portal/compliance-centre?tab=policies" className="block">
              <Button variant="outline" className="w-full justify-start rounded-xl border-[#E4E8EB]" data-testid="quick-upload-policy">
                <Upload className="mr-2 h-4 w-4" />
                Upload Policy
              </Button>
            </Link>
            <Link to="/portal/employees" className="block">
              <Button variant="outline" className="w-full justify-start rounded-xl border-[#E4E8EB]" data-testid="quick-upload-document">
                <FileText className="mr-2 h-4 w-4" />
                Upload Document
              </Button>
            </Link>
          </CardContent>
        </Card>

        {/* Recent Employees */}
        <Card className="lg:col-span-2 border-[#E4E8EB] shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="font-heading text-lg">Recent Employees</CardTitle>
            <Link to="/portal/employees">
              <Button variant="ghost" size="sm" className="text-primary" data-testid="view-all-employees">
                View all
                <ArrowRight className="ml-1 h-4 w-4" />
              </Button>
            </Link>
          </CardHeader>
          <CardContent>
            {employees.length === 0 ? (
              <div className="text-center py-8 text-text-muted">
                <Users className="h-12 w-12 mx-auto mb-3 opacity-50" />
                <p>No employees yet</p>
                <Link to="/portal/employees">
                  <Button className="mt-4 bg-primary hover:bg-primary-hover text-white rounded-xl">
                    Add your first employee
                  </Button>
                </Link>
              </div>
            ) : (
              <div className="space-y-3">
                {employees.slice(0, 5).map((emp) => {
                  const isReady = emp.work_readiness?.status === 'work_ready' || emp.work_readiness?.status === 'fully_compliant';
                  const isSupervisedStart = emp.work_readiness?.status === 'almost_ready' || emp.work_readiness?.status === 'supervised_start';
                  const notReadyReason = emp.work_readiness?.reason;
                  
                  return (
                    <Link
                      key={emp.id}
                      to={`/portal/employees/${emp.id}`}
                      className="flex items-center justify-between p-3 rounded-xl hover:bg-[#F8FAFA] transition-colors"
                      data-testid={`employee-row-${emp.id}`}
                    >
                      <div className="flex items-center gap-3">
                        <EmployeeAvatar
                          employeeId={emp.id}
                          firstName={emp.first_name}
                          lastName={emp.last_name}
                          hasPhoto={!!emp.profile_photo_url}
                          token={token}
                          size="md"
                        />
                        <div>
                          <p className="font-medium text-text-primary">{emp.first_name} {emp.last_name}</p>
                          <p className="text-sm text-text-muted">{emp.role}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <div className="text-right hidden sm:block">
                          <p className="text-sm font-medium text-text-primary">{emp.completion_percentage}%</p>
                          <p className="text-xs text-text-muted">Compliance</p>
                        </div>
                        <div className="text-right">
                          <span 
                            className={`px-2 py-1 rounded-lg text-xs font-medium ${
                              isReady ? 'bg-green-100 text-green-700' :
                              isSupervisedStart ? 'bg-amber-100 text-amber-700' :
                              'bg-red-100 text-red-700'
                            }`}
                            title={notReadyReason || (isReady ? 'All mandatory requirements verified' : 'Some requirements missing')}
                          >
                            {isReady ? 'Ready to Work' : isSupervisedStart ? 'Supervised Start' : 'Not Ready'}
                          </span>
                          {/* UI INTEGRITY: Show WHY someone is Not Ready */}
                          {!isReady && !isSupervisedStart && notReadyReason && (
                            <p className="text-[10px] text-red-600 mt-0.5 max-w-[120px] truncate" title={notReadyReason}>
                              {notReadyReason}
                            </p>
                          )}
                        </div>
                      </div>
                    </Link>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
