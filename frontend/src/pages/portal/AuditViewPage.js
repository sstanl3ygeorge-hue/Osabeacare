import { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Progress } from '../../components/ui/progress';
import { History, Users, FileCheck, GraduationCap, CheckCircle, AlertTriangle, Loader2 } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function AuditViewPage() {
  const [stats, setStats] = useState(null);
  const [employees, setEmployees] = useState([]);
  const [policies, setPolicies] = useState([]);
  const [training, setTraining] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const { token } = useAuth();

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [statsRes, empsRes, policiesRes, trainingRes, logsRes] = await Promise.all([
          axios.get(`${API}/dashboard/stats`, { headers: { Authorization: `Bearer ${token}` } }),
          axios.get(`${API}/employees`, { headers: { Authorization: `Bearer ${token}` } }),
          axios.get(`${API}/policies`, { headers: { Authorization: `Bearer ${token}` } }),
          axios.get(`${API}/training-records`, { headers: { Authorization: `Bearer ${token}` } }),
          axios.get(`${API}/audit-logs?limit=20`, { headers: { Authorization: `Bearer ${token}` } })
        ]);
        setStats(statsRes.data);
        setEmployees(empsRes.data);
        setPolicies(policiesRes.data);
        setTraining(trainingRes.data);
        setAuditLogs(logsRes.data);
      } catch (error) {
        console.error('Failed to fetch audit data:', error);
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

  const totalEmployees = employees.length;
  const activeEmployees = employees.filter(e => e.status === 'active').length;
  const avgCompletion = totalEmployees > 0 
    ? Math.round(employees.reduce((sum, e) => sum + (e.completion_percentage || 0), 0) / totalEmployees)
    : 0;

  const totalPolicyAssignments = policies.reduce((sum, p) => sum + (p.assigned_count || 0), 0);
  const totalPolicySigned = policies.reduce((sum, p) => sum + (p.signed_count || 0), 0);
  const policyComplianceRate = totalPolicyAssignments > 0 
    ? Math.round((totalPolicySigned / totalPolicyAssignments) * 100)
    : 0;

  const totalTraining = training.length;
  const completedTraining = training.filter(t => t.status === 'completed').length;
  const trainingComplianceRate = totalTraining > 0 
    ? Math.round((completedTraining / totalTraining) * 100)
    : 0;

  return (
    <div className="space-y-6" data-testid="audit-page">
      <div>
        <h1 className="font-heading text-2xl sm:text-3xl font-bold text-text-primary">
          Audit and Compliance Overview
        </h1>
        <p className="text-text-muted mt-1">Read-only view of compliance status across the organisation</p>
      </div>

      {/* Compliance Summary */}
      <div className="grid lg:grid-cols-3 gap-6">
        <Card className="border-[#E4E8EB] shadow-sm">
          <CardHeader>
            <CardTitle className="font-heading text-lg flex items-center gap-2">
              <Users className="h-5 w-5 text-primary" />
              Workforce Summary
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-text-muted">Total Employees</span>
              <span className="font-semibold text-text-primary">{totalEmployees}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-text-muted">Active</span>
              <span className="font-semibold text-success">{activeEmployees}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-text-muted">Onboarding</span>
              <span className="font-semibold text-info">{stats?.onboarding_in_progress || 0}</span>
            </div>
            <div className="pt-4 border-t border-[#E4E8EB]">
              <div className="flex justify-between items-center mb-2">
                <span className="text-text-muted">Avg. File Completion</span>
                <span className="font-semibold text-text-primary">{avgCompletion}%</span>
              </div>
              <Progress value={avgCompletion} className="h-2" />
            </div>
          </CardContent>
        </Card>

        <Card className="border-[#E4E8EB] shadow-sm">
          <CardHeader>
            <CardTitle className="font-heading text-lg flex items-center gap-2">
              <FileCheck className="h-5 w-5 text-primary" />
              Policy Compliance
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-text-muted">Active Policies</span>
              <span className="font-semibold text-text-primary">{policies.length}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-text-muted">Total Assignments</span>
              <span className="font-semibold text-text-primary">{totalPolicyAssignments}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-text-muted">Acknowledged</span>
              <span className="font-semibold text-success">{totalPolicySigned}</span>
            </div>
            <div className="pt-4 border-t border-[#E4E8EB]">
              <div className="flex justify-between items-center mb-2">
                <span className="text-text-muted">Compliance Rate</span>
                <span className="font-semibold text-text-primary">{policyComplianceRate}%</span>
              </div>
              <Progress value={policyComplianceRate} className="h-2" />
            </div>
          </CardContent>
        </Card>

        <Card className="border-[#E4E8EB] shadow-sm">
          <CardHeader>
            <CardTitle className="font-heading text-lg flex items-center gap-2">
              <GraduationCap className="h-5 w-5 text-primary" />
              Training Compliance
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-text-muted">Total Records</span>
              <span className="font-semibold text-text-primary">{totalTraining}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-text-muted">Completed</span>
              <span className="font-semibold text-success">{completedTraining}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-text-muted">Pending/Overdue</span>
              <span className="font-semibold text-warning">{totalTraining - completedTraining}</span>
            </div>
            <div className="pt-4 border-t border-[#E4E8EB]">
              <div className="flex justify-between items-center mb-2">
                <span className="text-text-muted">Compliance Rate</span>
                <span className="font-semibold text-text-primary">{trainingComplianceRate}%</span>
              </div>
              <Progress value={trainingComplianceRate} className="h-2" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Alerts */}
      <Card className="border-[#E4E8EB] shadow-sm">
        <CardHeader>
          <CardTitle className="font-heading text-lg flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-warning" />
            Items Requiring Attention
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="p-4 bg-[#F8FAFA] rounded-xl">
              <p className="text-2xl font-heading font-bold text-warning">{stats?.missing_urgent_documents || 0}</p>
              <p className="text-sm text-text-muted">Missing Documents</p>
            </div>
            <div className="p-4 bg-[#F8FAFA] rounded-xl">
              <p className="text-2xl font-heading font-bold text-warning">{stats?.unsigned_policies || 0}</p>
              <p className="text-sm text-text-muted">Unsigned Policies</p>
            </div>
            <div className="p-4 bg-[#F8FAFA] rounded-xl">
              <p className="text-2xl font-heading font-bold text-error">{stats?.dbs_pending || 0}</p>
              <p className="text-sm text-text-muted">DBS Pending</p>
            </div>
            <div className="p-4 bg-[#F8FAFA] rounded-xl">
              <p className="text-2xl font-heading font-bold text-warning">{stats?.expiring_30_days || 0}</p>
              <p className="text-sm text-text-muted">Expiring (30 days)</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Employee Compliance Table */}
      <Card className="border-[#E4E8EB] shadow-sm">
        <CardHeader>
          <CardTitle className="font-heading text-lg">Employee Compliance Status</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-[#E4E8EB] bg-[#F8FAFA]">
                  <th className="text-left p-4 font-medium text-text-muted text-sm">Employee</th>
                  <th className="text-left p-4 font-medium text-text-muted text-sm">Role</th>
                  <th className="text-left p-4 font-medium text-text-muted text-sm">Branch</th>
                  <th className="text-left p-4 font-medium text-text-muted text-sm">Status</th>
                  <th className="text-left p-4 font-medium text-text-muted text-sm">Completion</th>
                </tr>
              </thead>
              <tbody>
                {employees.slice(0, 20).map((emp) => (
                  <tr key={emp.id} className="border-b border-[#E4E8EB]">
                    <td className="p-4">
                      <p className="font-medium text-text-primary">{emp.first_name} {emp.last_name}</p>
                      <p className="text-sm text-text-muted">{emp.employee_code}</p>
                    </td>
                    <td className="p-4 text-text-primary">{emp.role}</td>
                    <td className="p-4 text-text-muted">{emp.branch}</td>
                    <td className="p-4">
                      <span className={`status-chip ${
                        emp.status === 'active' ? 'status-success' :
                        emp.status === 'onboarding' ? 'status-info' :
                        'status-neutral'
                      }`}>
                        {emp.status?.replace('_', ' ')}
                      </span>
                    </td>
                    <td className="p-4">
                      <div className="flex items-center gap-2">
                        <Progress value={emp.completion_percentage || 0} className="w-20 h-2" />
                        <span className="text-sm text-text-muted">{emp.completion_percentage || 0}%</span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Recent Activity */}
      <Card className="border-[#E4E8EB] shadow-sm">
        <CardHeader>
          <CardTitle className="font-heading text-lg flex items-center gap-2">
            <History className="h-5 w-5 text-primary" />
            Recent Activity
          </CardTitle>
        </CardHeader>
        <CardContent>
          {auditLogs.length === 0 ? (
            <p className="text-center py-8 text-text-muted">No recent activity</p>
          ) : (
            <div className="space-y-3">
              {auditLogs.map((log) => (
                <div key={log.id} className="flex items-center gap-4 p-3 bg-[#F8FAFA] rounded-xl">
                  <div className="w-10 h-10 bg-white rounded-xl flex items-center justify-center border border-[#E4E8EB]">
                    <History className="h-5 w-5 text-primary" />
                  </div>
                  <div className="flex-1">
                    <p className="text-text-primary">
                      <span className="font-medium">{log.user_name || 'System'}</span>
                      {' '}{log.action?.replace('_', ' ')}
                    </p>
                    <p className="text-sm text-text-muted">
                      {new Date(log.created_at).toLocaleString()}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
