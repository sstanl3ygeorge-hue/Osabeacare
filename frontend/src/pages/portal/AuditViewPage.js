import { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Progress } from '../../components/ui/progress';
import { 
  AlertTriangle, Users, FileCheck, GraduationCap, CheckCircle, 
  Loader2, Clock, Shield, FileX, CalendarClock, ShieldCheck, AlertCircle
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function AuditViewPage() {
  const [stats, setStats] = useState(null);
  const [employees, setEmployees] = useState([]);
  const [policies, setPolicies] = useState([]);
  const [expiryAlerts, setExpiryAlerts] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(null);
  const { token } = useAuth();

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [statsRes, empsRes, policiesRes, expiryRes] = await Promise.all([
          axios.get(`${API}/dashboard/stats`, { headers: { Authorization: `Bearer ${token}` } }),
          axios.get(`${API}/employees`, { headers: { Authorization: `Bearer ${token}` } }),
          axios.get(`${API}/policies`, { headers: { Authorization: `Bearer ${token}` } }),
          axios.get(`${API}/dashboard/expiry-alerts`, { headers: { Authorization: `Bearer ${token}` } }).catch(() => ({ data: null }))
        ]);
        setStats(statsRes.data);
        setEmployees(empsRes.data);
        setPolicies(policiesRes.data);
        setExpiryAlerts(expiryRes.data);
        setLastUpdated(new Date());
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

  // Calculate workforce readiness
  const readyToWork = employees.filter(e => 
    e.work_readiness?.status === 'work_ready' || e.work_readiness?.status === 'fully_compliant'
  ).length;
  const supervisedStart = employees.filter(e => 
    e.work_readiness?.status === 'almost_ready' || e.work_readiness?.status === 'supervised_start'
  ).length;
  const notReady = employees.filter(e => 
    !e.work_readiness || 
    (e.work_readiness?.status !== 'work_ready' && 
     e.work_readiness?.status !== 'fully_compliant' && 
     e.work_readiness?.status !== 'almost_ready' &&
     e.work_readiness?.status !== 'supervised_start')
  ).length;

  const totalEmployees = employees.length;
  const avgCompletion = totalEmployees > 0 
    ? Math.round(employees.reduce((sum, e) => sum + (e.completion_percentage || 0), 0) / totalEmployees)
    : 0;

  // Policy compliance calculations
  const totalPolicyAssignments = policies.reduce((sum, p) => sum + (p.assigned_count || 0), 0);
  const totalPoliciesAcknowledged = policies.reduce((sum, p) => sum + (p.signed_count || 0), 0);
  const policyComplianceRate = totalPolicyAssignments > 0 
    ? Math.round((totalPoliciesAcknowledged / totalPolicyAssignments) * 100)
    : 0;

  // Expiry alerts data
  const expiredItems = expiryAlerts?.expired?.total_items || 0;
  const expiringItems = expiryAlerts?.expiring_soon?.total_items || 0;

  return (
    <div className="space-y-6" data-testid="audit-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="font-heading text-2xl sm:text-3xl font-bold text-text-primary">
            Inspection View
          </h1>
          <p className="text-text-muted mt-1">
            Read-only compliance overview for CQC inspection
          </p>
        </div>
        {lastUpdated && (
          <div className="flex items-center gap-2 text-sm text-text-muted bg-[#F8FAFA] px-3 py-2 rounded-lg border border-[#E4E8EB]">
            <Clock className="h-4 w-4" />
            Last updated: {lastUpdated.toLocaleString()}
          </div>
        )}
      </div>

      {/* SECTION 1: Compliance Risks & Alerts (Top Priority) */}
      <Card className={`border-2 ${(expiredItems > 0 || notReady > 0) ? 'border-red-200 bg-red-50' : expiringItems > 0 ? 'border-amber-200 bg-amber-50' : 'border-green-200 bg-green-50'} shadow-sm`}>
        <CardHeader className="pb-3">
          <CardTitle className="font-heading text-lg flex items-center gap-2">
            {(expiredItems > 0 || notReady > 0) ? (
              <>
                <AlertTriangle className="h-5 w-5 text-red-600" />
                <span className="text-red-700">Risks & Alerts</span>
              </>
            ) : expiringItems > 0 ? (
              <>
                <AlertCircle className="h-5 w-5 text-amber-600" />
                <span className="text-amber-700">Items Requiring Attention</span>
              </>
            ) : (
              <>
                <CheckCircle className="h-5 w-5 text-green-600" />
                <span className="text-green-700">No Outstanding Risks</span>
              </>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {(expiredItems > 0 || expiringItems > 0 || notReady > 0) ? (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className={`p-4 rounded-xl ${expiredItems > 0 ? 'bg-red-100 border border-red-200' : 'bg-white border border-gray-200'}`}>
                <div className="flex items-center gap-3">
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${expiredItems > 0 ? 'bg-red-200' : 'bg-gray-100'}`}>
                    <FileX className={`h-5 w-5 ${expiredItems > 0 ? 'text-red-600' : 'text-gray-400'}`} />
                  </div>
                  <div>
                    <p className={`text-2xl font-heading font-bold ${expiredItems > 0 ? 'text-red-700' : 'text-gray-400'}`}>{expiredItems}</p>
                    <p className={`text-sm ${expiredItems > 0 ? 'text-red-600' : 'text-gray-500'}`}>Expired Items</p>
                  </div>
                </div>
              </div>
              <div className={`p-4 rounded-xl ${expiringItems > 0 ? 'bg-amber-100 border border-amber-200' : 'bg-white border border-gray-200'}`}>
                <div className="flex items-center gap-3">
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${expiringItems > 0 ? 'bg-amber-200' : 'bg-gray-100'}`}>
                    <CalendarClock className={`h-5 w-5 ${expiringItems > 0 ? 'text-amber-600' : 'text-gray-400'}`} />
                  </div>
                  <div>
                    <p className={`text-2xl font-heading font-bold ${expiringItems > 0 ? 'text-amber-700' : 'text-gray-400'}`}>{expiringItems}</p>
                    <p className={`text-sm ${expiringItems > 0 ? 'text-amber-600' : 'text-gray-500'}`}>Needs Renewal</p>
                  </div>
                </div>
              </div>
              <div className={`p-4 rounded-xl ${notReady > 0 ? 'bg-red-100 border border-red-200' : 'bg-white border border-gray-200'}`}>
                <div className="flex items-center gap-3">
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${notReady > 0 ? 'bg-red-200' : 'bg-gray-100'}`}>
                    <AlertTriangle className={`h-5 w-5 ${notReady > 0 ? 'text-red-600' : 'text-gray-400'}`} />
                  </div>
                  <div>
                    <p className={`text-2xl font-heading font-bold ${notReady > 0 ? 'text-red-700' : 'text-gray-400'}`}>{notReady}</p>
                    <p className={`text-sm ${notReady > 0 ? 'text-red-600' : 'text-gray-500'}`}>Staff Not Ready</p>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <p className="text-green-700">All documents current, all staff ready to work. No compliance risks identified.</p>
          )}
        </CardContent>
      </Card>

      {/* SECTION 2: Workforce Status */}
      <Card className="border-[#E4E8EB] shadow-sm">
        <CardHeader>
          <CardTitle className="font-heading text-lg flex items-center gap-2">
            <Shield className="h-5 w-5 text-primary" />
            Workforce Status
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 mb-6">
            <div className="p-4 bg-[#F8FAFA] rounded-xl border border-[#E4E8EB]">
              <p className="text-3xl font-heading font-bold text-text-primary">{totalEmployees}</p>
              <p className="text-sm text-text-muted">Total Staff</p>
            </div>
            <div className="p-4 bg-green-50 rounded-xl border border-green-200">
              <div className="flex items-center gap-2 mb-1">
                <ShieldCheck className="h-4 w-4 text-green-600" />
                <p className="text-sm text-green-600">Ready to Work</p>
              </div>
              <p className="text-3xl font-heading font-bold text-green-700">{readyToWork}</p>
            </div>
            <div className="p-4 bg-amber-50 rounded-xl border border-amber-200">
              <div className="flex items-center gap-2 mb-1">
                <AlertCircle className="h-4 w-4 text-amber-600" />
                <p className="text-sm text-amber-600">Supervised Start</p>
              </div>
              <p className="text-3xl font-heading font-bold text-amber-700">{supervisedStart}</p>
            </div>
            <div className="p-4 bg-red-50 rounded-xl border border-red-200">
              <div className="flex items-center gap-2 mb-1">
                <AlertTriangle className="h-4 w-4 text-red-600" />
                <p className="text-sm text-red-600">Not Ready</p>
              </div>
              <p className="text-3xl font-heading font-bold text-red-700">{notReady}</p>
            </div>
          </div>
          
          {/* Progress to Full Compliance */}
          <div className="p-4 bg-[#F8FAFA] rounded-xl border border-[#E4E8EB]">
            <div className="flex justify-between items-center mb-2">
              <span className="text-text-muted">Progress to Full Compliance</span>
              <span className="font-semibold text-text-primary">{avgCompletion}%</span>
            </div>
            <Progress value={avgCompletion} className="h-3" />
          </div>
        </CardContent>
      </Card>

      {/* SECTION 3: Policy Compliance */}
      <Card className="border-[#E4E8EB] shadow-sm">
        <CardHeader>
          <CardTitle className="font-heading text-lg flex items-center gap-2">
            <FileCheck className="h-5 w-5 text-primary" />
            Policies & Acknowledgement
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
            <div className="p-4 bg-[#F8FAFA] rounded-xl border border-[#E4E8EB]">
              <p className="text-3xl font-heading font-bold text-text-primary">{policies.length}</p>
              <p className="text-sm text-text-muted">Active Policies</p>
            </div>
            <div className="p-4 bg-[#F8FAFA] rounded-xl border border-[#E4E8EB]">
              <p className="text-3xl font-heading font-bold text-text-primary">{totalPolicyAssignments}</p>
              <p className="text-sm text-text-muted">Total Assignments</p>
            </div>
            <div className="p-4 bg-green-50 rounded-xl border border-green-200">
              <p className="text-3xl font-heading font-bold text-green-700">{totalPoliciesAcknowledged}</p>
              <p className="text-sm text-green-600">Acknowledged</p>
            </div>
          </div>
          
          {/* Policy Compliance Rate */}
          <div className="p-4 bg-[#F8FAFA] rounded-xl border border-[#E4E8EB]">
            <div className="flex justify-between items-center mb-2">
              <span className="text-text-muted">Policy Acknowledgement Rate</span>
              <span className="font-semibold text-text-primary">{policyComplianceRate}%</span>
            </div>
            <Progress value={policyComplianceRate} className="h-3" />
          </div>
          
          {stats?.unsigned_policies > 0 && (
            <div className="mt-4 p-3 bg-blue-50 rounded-lg border border-blue-200">
              <p className="text-sm text-blue-700">
                <span className="font-medium">{stats.unsigned_policies}</span> policies not yet acknowledged by assigned staff
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* SECTION 4: Training & Certification Status */}
      <Card className="border-[#E4E8EB] shadow-sm">
        <CardHeader>
          <CardTitle className="font-heading text-lg flex items-center gap-2">
            <GraduationCap className="h-5 w-5 text-primary" />
            Training & Certification Status
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
            <div className="p-4 bg-[#F8FAFA] rounded-xl border border-[#E4E8EB]">
              <p className="text-3xl font-heading font-bold text-text-primary">{stats?.missing_urgent_documents || 0}</p>
              <p className="text-sm text-text-muted">Still Needed</p>
            </div>
            <div className="p-4 bg-[#F8FAFA] rounded-xl border border-[#E4E8EB]">
              <p className="text-3xl font-heading font-bold text-text-primary">{stats?.dbs_pending || 0}</p>
              <p className="text-sm text-text-muted">DBS Pending</p>
            </div>
            <div className="p-4 bg-[#F8FAFA] rounded-xl border border-[#E4E8EB]">
              <p className="text-3xl font-heading font-bold text-text-primary">{stats?.rtw_missing || 0}</p>
              <p className="text-sm text-text-muted">RTW Documents</p>
            </div>
            <div className="p-4 bg-[#F8FAFA] rounded-xl border border-[#E4E8EB]">
              <p className="text-3xl font-heading font-bold text-text-primary">{stats?.references_outstanding || 0}</p>
              <p className="text-sm text-text-muted">References Outstanding</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* SECTION 5: Staff Overview Table */}
      <Card className="border-[#E4E8EB] shadow-sm">
        <CardHeader>
          <CardTitle className="font-heading text-lg">Staff Overview</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-[#E4E8EB] bg-[#F8FAFA]">
                  <th className="text-left p-4 font-medium text-text-muted text-sm">Employee</th>
                  <th className="text-left p-4 font-medium text-text-muted text-sm">Role</th>
                  <th className="text-left p-4 font-medium text-text-muted text-sm">Work Status</th>
                  <th className="text-left p-4 font-medium text-text-muted text-sm">Progress</th>
                </tr>
              </thead>
              <tbody>
                {employees.slice(0, 20).map((emp) => {
                  const isReady = emp.work_readiness?.status === 'work_ready' || emp.work_readiness?.status === 'fully_compliant';
                  const isSupervisedStart = emp.work_readiness?.status === 'almost_ready' || emp.work_readiness?.status === 'supervised_start';
                  
                  return (
                    <tr key={emp.id} className="border-b border-[#E4E8EB]" data-testid={`audit-employee-row-${emp.id}`}>
                      <td className="p-4">
                        <p className="font-medium text-text-primary">{emp.first_name} {emp.last_name}</p>
                        <p className="text-sm text-text-muted">{emp.employee_code}</p>
                      </td>
                      <td className="p-4 text-text-primary">{emp.role}</td>
                      <td className="p-4">
                        <span className={`px-2 py-1 rounded-lg text-xs font-medium ${
                          isReady ? 'bg-green-100 text-green-700' :
                          isSupervisedStart ? 'bg-amber-100 text-amber-700' :
                          'bg-red-100 text-red-700'
                        }`}>
                          {isReady ? 'Ready to Work' : isSupervisedStart ? 'Supervised Start' : 'Not Ready'}
                        </span>
                      </td>
                      <td className="p-4">
                        <div className="flex items-center gap-2">
                          <Progress value={emp.completion_percentage || 0} className="w-20 h-2" />
                          <span className="text-sm text-text-muted">{emp.completion_percentage || 0}%</span>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          {employees.length > 20 && (
            <div className="p-4 text-center text-text-muted text-sm border-t border-[#E4E8EB]">
              Showing 20 of {employees.length} employees
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
