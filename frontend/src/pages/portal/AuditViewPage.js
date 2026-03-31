import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Progress } from '../../components/ui/progress';
import { Button } from '../../components/ui/button';
import { 
  AlertTriangle, Users, FileCheck, GraduationCap, CheckCircle, 
  Loader2, Clock, Shield, FileX, CalendarClock, ShieldCheck, AlertCircle, ArrowRight, Download
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function AuditViewPage() {
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [employees, setEmployees] = useState([]);
  const [policies, setPolicies] = useState([]);
  const [expiryAlerts, setExpiryAlerts] = useState(null);
  const [trainingAudit, setTrainingAudit] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(null);
  const { token } = useAuth();

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [statsRes, empsRes, policiesRes, expiryRes, trainingRes] = await Promise.all([
          axios.get(`${API}/dashboard/stats`, { headers: { Authorization: `Bearer ${token}` } }),
          axios.get(`${API}/employees`, { headers: { Authorization: `Bearer ${token}` } }),
          axios.get(`${API}/policies`, { headers: { Authorization: `Bearer ${token}` } }),
          axios.get(`${API}/dashboard/expiry-alerts`, { headers: { Authorization: `Bearer ${token}` } }).catch(() => ({ data: null })),
          axios.get(`${API}/audit/training/summary`, { headers: { Authorization: `Bearer ${token}` } }).catch(() => ({ data: null }))
        ]);
        setStats(statsRes.data);
        setEmployees(empsRes.data);
        setPolicies(policiesRes.data);
        setExpiryAlerts(expiryRes.data);
        setTrainingAudit(trainingRes.data);
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
              {/* Expired Items → Training Matrix filtered to expired */}
              <div 
                onClick={() => expiredItems > 0 && navigate('/portal/training?filter=expired')}
                className={`p-4 rounded-xl transition-all ${expiredItems > 0 ? 'bg-red-100 border border-red-200 cursor-pointer hover:bg-red-150 hover:shadow-md' : 'bg-white border border-gray-200'}`}
                title={expiredItems > 0 ? 'View expired items' : ''}
                data-testid="audit-card-expired"
              >
                <div className="flex items-center gap-3">
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${expiredItems > 0 ? 'bg-red-200' : 'bg-gray-100'}`}>
                    <FileX className={`h-5 w-5 ${expiredItems > 0 ? 'text-red-600' : 'text-gray-400'}`} />
                  </div>
                  <div className="flex-1">
                    <p className={`text-2xl font-heading font-bold ${expiredItems > 0 ? 'text-red-700' : 'text-gray-400'}`}>{expiredItems}</p>
                    <p className={`text-sm ${expiredItems > 0 ? 'text-red-600' : 'text-gray-500'}`}>Expired Items</p>
                  </div>
                  {expiredItems > 0 && <ArrowRight className="h-4 w-4 text-red-400" />}
                </div>
                {expiredItems > 0 && <p className="text-xs text-red-500 mt-2">Review now →</p>}
              </div>
              
              {/* Needs Renewal → Training Matrix filtered to expiring_soon */}
              <div 
                onClick={() => expiringItems > 0 && navigate('/portal/training?filter=expiring_soon')}
                className={`p-4 rounded-xl transition-all ${expiringItems > 0 ? 'bg-amber-100 border border-amber-200 cursor-pointer hover:bg-amber-150 hover:shadow-md' : 'bg-white border border-gray-200'}`}
                title={expiringItems > 0 ? 'View items needing renewal' : ''}
                data-testid="audit-card-expiring"
              >
                <div className="flex items-center gap-3">
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${expiringItems > 0 ? 'bg-amber-200' : 'bg-gray-100'}`}>
                    <CalendarClock className={`h-5 w-5 ${expiringItems > 0 ? 'text-amber-600' : 'text-gray-400'}`} />
                  </div>
                  <div className="flex-1">
                    <p className={`text-2xl font-heading font-bold ${expiringItems > 0 ? 'text-amber-700' : 'text-gray-400'}`}>{expiringItems}</p>
                    <p className={`text-sm ${expiringItems > 0 ? 'text-amber-600' : 'text-gray-500'}`}>Needs Renewal</p>
                  </div>
                  {expiringItems > 0 && <ArrowRight className="h-4 w-4 text-amber-400" />}
                </div>
                {expiringItems > 0 && <p className="text-xs text-amber-600 mt-2">See items →</p>}
              </div>
              
              {/* Staff Not Ready → Employees filtered to not_ready */}
              <div 
                onClick={() => notReady > 0 && navigate('/portal/employees?work_readiness=not_ready')}
                className={`p-4 rounded-xl transition-all ${notReady > 0 ? 'bg-red-100 border border-red-200 cursor-pointer hover:bg-red-150 hover:shadow-md' : 'bg-white border border-gray-200'}`}
                title={notReady > 0 ? 'View affected staff' : ''}
                data-testid="audit-card-not-ready"
              >
                <div className="flex items-center gap-3">
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${notReady > 0 ? 'bg-red-200' : 'bg-gray-100'}`}>
                    <AlertTriangle className={`h-5 w-5 ${notReady > 0 ? 'text-red-600' : 'text-gray-400'}`} />
                  </div>
                  <div className="flex-1">
                    <p className={`text-2xl font-heading font-bold ${notReady > 0 ? 'text-red-700' : 'text-gray-400'}`}>{notReady}</p>
                    <p className={`text-sm ${notReady > 0 ? 'text-red-600' : 'text-gray-500'}`}>Staff Not Ready</p>
                  </div>
                  {notReady > 0 && <ArrowRight className="h-4 w-4 text-red-400" />}
                </div>
                {notReady > 0 && <p className="text-xs text-red-500 mt-2">View staff →</p>}
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
            {/* Total Staff → Employees page (all) */}
            <div 
              onClick={() => totalEmployees > 0 && navigate('/portal/employees')}
              className={`p-4 bg-[#F8FAFA] rounded-xl border border-[#E4E8EB] transition-all ${totalEmployees > 0 ? 'cursor-pointer hover:bg-gray-100 hover:shadow-sm' : ''}`}
              title={totalEmployees > 0 ? 'View all staff' : ''}
              data-testid="audit-card-total-staff"
            >
              <p className="text-3xl font-heading font-bold text-text-primary">{totalEmployees}</p>
              <div className="flex items-center justify-between">
                <p className="text-sm text-text-muted">Total Staff</p>
                {totalEmployees > 0 && <ArrowRight className="h-3 w-3 text-gray-400" />}
              </div>
            </div>
            
            {/* Ready to Work → Employees filtered */}
            <div 
              onClick={() => readyToWork > 0 && navigate('/portal/employees?work_readiness=ready_to_work')}
              className={`p-4 bg-green-50 rounded-xl border border-green-200 transition-all ${readyToWork > 0 ? 'cursor-pointer hover:bg-green-100 hover:shadow-sm' : ''}`}
              title={readyToWork > 0 ? 'View ready staff' : ''}
              data-testid="audit-card-ready"
            >
              <div className="flex items-center gap-2 mb-1">
                <ShieldCheck className="h-4 w-4 text-green-600" />
                <p className="text-sm text-green-600">Ready to Work</p>
              </div>
              <div className="flex items-center justify-between">
                <p className="text-3xl font-heading font-bold text-green-700">{readyToWork}</p>
                {readyToWork > 0 && <ArrowRight className="h-3 w-3 text-green-400" />}
              </div>
            </div>
            
            {/* Supervised Start → Employees filtered */}
            <div 
              onClick={() => supervisedStart > 0 && navigate('/portal/employees?work_readiness=supervised_start')}
              className={`p-4 bg-amber-50 rounded-xl border border-amber-200 transition-all ${supervisedStart > 0 ? 'cursor-pointer hover:bg-amber-100 hover:shadow-sm' : ''}`}
              title={supervisedStart > 0 ? 'View staff on supervised start' : ''}
              data-testid="audit-card-supervised"
            >
              <div className="flex items-center gap-2 mb-1">
                <AlertCircle className="h-4 w-4 text-amber-600" />
                <p className="text-sm text-amber-600">Supervised Start</p>
              </div>
              <div className="flex items-center justify-between">
                <p className="text-3xl font-heading font-bold text-amber-700">{supervisedStart}</p>
                {supervisedStart > 0 && <ArrowRight className="h-3 w-3 text-amber-400" />}
              </div>
            </div>
            
            {/* Not Ready → Employees filtered */}
            <div 
              onClick={() => notReady > 0 && navigate('/portal/employees?work_readiness=not_ready')}
              className={`p-4 bg-red-50 rounded-xl border border-red-200 transition-all ${notReady > 0 ? 'cursor-pointer hover:bg-red-100 hover:shadow-sm' : ''}`}
              title={notReady > 0 ? 'View affected staff' : ''}
              data-testid="audit-card-not-ready-workforce"
            >
              <div className="flex items-center gap-2 mb-1">
                <AlertTriangle className="h-4 w-4 text-red-600" />
                <p className="text-sm text-red-600">Not Ready</p>
              </div>
              <div className="flex items-center justify-between">
                <p className="text-3xl font-heading font-bold text-red-700">{notReady}</p>
                {notReady > 0 && <ArrowRight className="h-3 w-3 text-red-400" />}
              </div>
            </div>
          </div>
          
          {/* Average Employee Compliance */}
          <div className="p-4 bg-[#F8FAFA] rounded-xl border border-[#E4E8EB]">
            <div className="flex justify-between items-center mb-2">
              <span className="text-text-muted">Average Employee Compliance</span>
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
            {/* Active Policies → Compliance Centre */}
            <div 
              onClick={() => policies.length > 0 && navigate('/portal/compliance-centre?tab=policies')}
              className={`p-4 bg-[#F8FAFA] rounded-xl border border-[#E4E8EB] transition-all ${policies.length > 0 ? 'cursor-pointer hover:bg-gray-100 hover:shadow-sm' : ''}`}
              title={policies.length > 0 ? 'View all policies' : ''}
              data-testid="audit-card-policies"
            >
              <p className="text-3xl font-heading font-bold text-text-primary">{policies.length}</p>
              <div className="flex items-center justify-between">
                <p className="text-sm text-text-muted">Active Policies</p>
                {policies.length > 0 && <ArrowRight className="h-3 w-3 text-gray-400" />}
              </div>
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
            <div 
              onClick={() => navigate('/portal/compliance-centre?tab=policies')}
              className="mt-4 p-3 bg-blue-50 rounded-lg border border-blue-200 cursor-pointer hover:bg-blue-100 transition-all"
              title="Review policy acknowledgements"
              data-testid="audit-card-unsigned-policies"
            >
              <div className="flex items-center justify-between">
                <p className="text-sm text-blue-700">
                  <span className="font-medium">{stats.unsigned_policies}</span> policies not yet acknowledged by assigned staff
                </p>
                <ArrowRight className="h-4 w-4 text-blue-400" />
              </div>
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
            {/* Still Needed → Training Matrix */}
            <div 
              onClick={() => (stats?.missing_urgent_documents || 0) > 0 && navigate('/portal/training')}
              className={`p-4 bg-[#F8FAFA] rounded-xl border border-[#E4E8EB] transition-all ${(stats?.missing_urgent_documents || 0) > 0 ? 'cursor-pointer hover:bg-gray-100 hover:shadow-sm' : ''}`}
              title={(stats?.missing_urgent_documents || 0) > 0 ? 'View training records' : ''}
              data-testid="audit-card-still-needed"
            >
              <p className="text-3xl font-heading font-bold text-text-primary">{stats?.missing_urgent_documents || 0}</p>
              <div className="flex items-center justify-between">
                <p className="text-sm text-text-muted">Still Needed</p>
                {(stats?.missing_urgent_documents || 0) > 0 && <ArrowRight className="h-3 w-3 text-gray-400" />}
              </div>
            </div>
            
            {/* DBS Pending → Employees (would filter by DBS requirement) */}
            <div 
              onClick={() => (stats?.dbs_pending || 0) > 0 && navigate('/portal/employees?requirement=dbs')}
              className={`p-4 bg-[#F8FAFA] rounded-xl border border-[#E4E8EB] transition-all ${(stats?.dbs_pending || 0) > 0 ? 'cursor-pointer hover:bg-gray-100 hover:shadow-sm' : ''}`}
              title={(stats?.dbs_pending || 0) > 0 ? 'View staff with DBS awaiting verification' : ''}
              data-testid="audit-card-dbs"
            >
              <p className="text-3xl font-heading font-bold text-text-primary">{stats?.dbs_pending || 0}</p>
              <div className="flex items-center justify-between">
                <p className="text-sm text-text-muted">DBS Awaiting Verification</p>
                {(stats?.dbs_pending || 0) > 0 && <ArrowRight className="h-3 w-3 text-gray-400" />}
              </div>
            </div>
            
            {/* RTW Documents → Employees (would filter by RTW requirement) */}
            <div 
              onClick={() => (stats?.rtw_missing || 0) > 0 && navigate('/portal/employees?requirement=rtw')}
              className={`p-4 bg-[#F8FAFA] rounded-xl border border-[#E4E8EB] transition-all ${(stats?.rtw_missing || 0) > 0 ? 'cursor-pointer hover:bg-gray-100 hover:shadow-sm' : ''}`}
              title={(stats?.rtw_missing || 0) > 0 ? 'View staff with missing Right to Work' : ''}
              data-testid="audit-card-rtw"
            >
              <p className="text-3xl font-heading font-bold text-text-primary">{stats?.rtw_missing || 0}</p>
              <div className="flex items-center justify-between">
                <p className="text-sm text-text-muted">RTW Missing</p>
                {(stats?.rtw_missing || 0) > 0 && <ArrowRight className="h-3 w-3 text-gray-400" />}
              </div>
            </div>
            
            {/* References Outstanding → Employees (would filter by references requirement) */}
            <div 
              onClick={() => (stats?.references_outstanding || 0) > 0 && navigate('/portal/employees?requirement=references')}
              className={`p-4 bg-[#F8FAFA] rounded-xl border border-[#E4E8EB] transition-all ${(stats?.references_outstanding || 0) > 0 ? 'cursor-pointer hover:bg-gray-100 hover:shadow-sm' : ''}`}
              title={(stats?.references_outstanding || 0) > 0 ? 'View staff with outstanding references' : ''}
              data-testid="audit-card-references"
            >
              <p className="text-3xl font-heading font-bold text-text-primary">{stats?.references_outstanding || 0}</p>
              <div className="flex items-center justify-between">
                <p className="text-sm text-text-muted">References Outstanding</p>
                {(stats?.references_outstanding || 0) > 0 && <ArrowRight className="h-3 w-3 text-gray-400" />}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* SECTION 5: Supplementary Training */}
      <Card className="border-[#E4E8EB] shadow-sm">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="font-heading text-lg flex items-center gap-2">
              <GraduationCap className="h-5 w-5 text-primary" />
              Supplementary Training
            </CardTitle>
            <Button
              variant="outline"
              size="sm"
              className="rounded-lg text-xs"
              onClick={async () => {
                try {
                  const response = await axios.get(`${API}/audit/training/export?format=csv`, {
                    headers: { Authorization: `Bearer ${token}` },
                    responseType: 'blob'
                  });
                  const url = window.URL.createObjectURL(new Blob([response.data]));
                  const link = document.createElement('a');
                  link.href = url;
                  link.setAttribute('download', `training_audit_${new Date().toISOString().split('T')[0]}.csv`);
                  document.body.appendChild(link);
                  link.click();
                  link.remove();
                } catch (error) {
                  console.error('Failed to export training data:', error);
                }
              }}
              data-testid="export-training-audit-btn"
            >
              <Download className="h-3.5 w-3.5 mr-1.5" />
              Export CSV
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {trainingAudit ? (
            <>
              <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 mb-6">
                {/* Fully Compliant */}
                <div 
                  className="p-4 bg-green-50 rounded-xl border border-green-200"
                  data-testid="audit-training-compliant"
                >
                  <div className="flex items-center gap-2 mb-1">
                    <CheckCircle className="h-4 w-4 text-green-600" />
                    <p className="text-sm text-green-600">Fully Compliant</p>
                  </div>
                  <p className="text-3xl font-heading font-bold text-green-700">{trainingAudit.fully_compliant}</p>
                </div>
                
                {/* With Warnings */}
                <div 
                  className="p-4 bg-amber-50 rounded-xl border border-amber-200"
                  data-testid="audit-training-warnings"
                >
                  <div className="flex items-center gap-2 mb-1">
                    <AlertCircle className="h-4 w-4 text-amber-600" />
                    <p className="text-sm text-amber-600">With Warnings</p>
                  </div>
                  <p className="text-3xl font-heading font-bold text-amber-700">{trainingAudit.with_warnings}</p>
                </div>
                
                {/* Blocked by Training */}
                <div 
                  className="p-4 bg-red-50 rounded-xl border border-red-200"
                  data-testid="audit-training-blocked"
                >
                  <div className="flex items-center gap-2 mb-1">
                    <AlertTriangle className="h-4 w-4 text-red-600" />
                    <p className="text-sm text-red-600">Blocked by Training</p>
                  </div>
                  <p className="text-3xl font-heading font-bold text-red-700">{trainingAudit.with_blockers}</p>
                </div>
                
                {/* Training Items Summary */}
                <div 
                  className="p-4 bg-[#F8FAFA] rounded-xl border border-[#E4E8EB]"
                  data-testid="audit-training-items"
                >
                  <p className="text-sm text-text-muted mb-2">Training Items</p>
                  <div className="flex items-center gap-4 text-xs">
                    <span className="text-green-600">✓ {trainingAudit.training_items_verified}</span>
                    <span className="text-amber-600">⏳ {trainingAudit.training_items_pending}</span>
                    <span className="text-red-600">✖ {trainingAudit.training_items_missing}</span>
                  </div>
                </div>
              </div>
              
              {/* Blocked Employees Detail */}
              {trainingAudit.blocked_employees && trainingAudit.blocked_employees.length > 0 && (
                <div className="p-4 bg-red-50 rounded-xl border border-red-200">
                  <p className="text-sm font-medium text-red-700 mb-3">Staff Blocked by Training Issues:</p>
                  <div className="space-y-2">
                    {trainingAudit.blocked_employees.slice(0, 5).map((emp, idx) => (
                      <div key={idx} className="flex items-start gap-2 text-sm">
                        <span className="text-red-600 font-medium">{emp.name}</span>
                        <span className="text-red-500">—</span>
                        <span className="text-red-600">
                          {emp.blockers?.map(b => b.title).join(', ') || `${emp.blocker_count} blocking item(s)`}
                        </span>
                      </div>
                    ))}
                    {trainingAudit.blocked_employees.length > 5 && (
                      <p className="text-xs text-red-500 mt-2">
                        + {trainingAudit.blocked_employees.length - 5} more blocked employees
                      </p>
                    )}
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="text-center py-6 text-text-muted">
              <GraduationCap className="h-8 w-8 mx-auto mb-2 opacity-50" />
              <p>Training audit data unavailable</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* SECTION 6: Staff Overview Table */}
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
