import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { toast } from 'sonner';
import DocumentPreviewModal from '../../components/portal/DocumentPreviewModal';
import {
  Shield, FileText, AlertTriangle, CheckCircle, Clock, Upload,
  Loader2, Building, Users, ClipboardList, AlertCircle, Calendar,
  RefreshCw, Download, Plus, Search, Filter, Eye, XCircle, UserPlus
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function ComplianceCentrePage() {
  const { token, isAdmin } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  
  // Initialize tab from URL for navigation state persistence
  const [activeTab, setActiveTab] = useState(searchParams.get('tab') || 'policies');
  const [loading, setLoading] = useState(true);
  const [dashboard, setDashboard] = useState(null);
  const [policies, setPolicies] = useState([]);
  const [insurance, setInsurance] = useState([]);
  const [incidents, setIncidents] = useState([]);
  const [dbsReport, setDbsReport] = useState(null);
  const [trainingReport, setTrainingReport] = useState(null);
  
  // Document preview modal state
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewFile, setPreviewFile] = useState(null);
  
  // Sync tab changes to URL
  const handleTabChange = (value) => {
    setActiveTab(value);
    setSearchParams({ tab: value }, { replace: true });
  };
  
  // Open document in preview modal
  const handleViewDocument = (type, id, title, filename) => {
    const endpoint = type === 'policy' 
      ? `${API}/compliance/policies/${id}/file`
      : `${API}/compliance/insurance/${id}/file`;
    
    setPreviewFile({
      url: endpoint,
      name: title || filename || 'Document',
      filename: filename
    });
    setPreviewOpen(true);
  };
  
  // Download document with authentication
  const handleDownloadDocument = async (type, id, filename) => {
    try {
      toast.loading('Downloading...');
      
      const endpoint = type === 'policy' 
        ? `${API}/compliance/policies/${id}/download`
        : `${API}/compliance/insurance/${id}/download`;
      
      const response = await axios.get(endpoint, {
        headers: { Authorization: `Bearer ${token}` },
        responseType: 'blob'
      });
      
      const blob = new Blob([response.data]);
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename || 'document.pdf';
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      
      toast.dismiss();
      toast.success('Document downloaded');
    } catch (error) {
      console.error('Failed to download document:', error);
      toast.dismiss();
      toast.error('Failed to download document');
    }
  };
  
  // Upload states
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [selectedPolicy, setSelectedPolicy] = useState(null);
  const [selectedInsurance, setSelectedInsurance] = useState(null);
  const [uploadFile, setUploadFile] = useState(null);
  const [uploadVersion, setUploadVersion] = useState('');
  const [uploadReviewDate, setUploadReviewDate] = useState('');
  const [uploadExpiryDate, setUploadExpiryDate] = useState('');
  const [uploadPolicyNumber, setUploadPolicyNumber] = useState('');
  const [uploadProvider, setUploadProvider] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  
  // Incident form
  const [incidentDialogOpen, setIncidentDialogOpen] = useState(false);
  const [newIncident, setNewIncident] = useState({
    incident_type: 'incident',
    title: '',
    description: '',
    date_occurred: new Date().toISOString().split('T')[0],
    location: '',
    persons_involved: '',
    immediate_actions: '',
    root_cause: '',
    corrective_actions: ''
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Employee Assignment state
  const [assignDialogOpen, setAssignDialogOpen] = useState(false);
  const [policyToAssign, setPolicyToAssign] = useState(null);
  const [employees, setEmployees] = useState([]);
  const [policyAssignments, setPolicyAssignments] = useState([]);
  const [selectedEmployees, setSelectedEmployees] = useState([]);
  const [isAssigning, setIsAssigning] = useState(false);

  useEffect(() => {
    fetchData();
  }, [token]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [dashRes, policiesRes, insuranceRes, incidentsRes, employeesRes, assignmentsRes] = await Promise.all([
        axios.get(`${API}/compliance/dashboard`, { headers: { Authorization: `Bearer ${token}` } }),
        axios.get(`${API}/compliance/policies`, { headers: { Authorization: `Bearer ${token}` } }),
        axios.get(`${API}/compliance/insurance`, { headers: { Authorization: `Bearer ${token}` } }),
        axios.get(`${API}/compliance/incidents`, { headers: { Authorization: `Bearer ${token}` } }),
        axios.get(`${API}/employees`, { headers: { Authorization: `Bearer ${token}` } }),
        axios.get(`${API}/policy-assignments?include_inactive=true`, { headers: { Authorization: `Bearer ${token}` } })
      ]);
      
      setDashboard(dashRes.data);
      setPolicies(policiesRes.data);
      setInsurance(insuranceRes.data);
      setIncidents(incidentsRes.data);
      setEmployees(employeesRes.data.filter(e => e.status !== 'archived'));
      setPolicyAssignments(assignmentsRes.data);
    } catch (error) {
      console.error('Failed to fetch compliance data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSeedPolicies = async () => {
    try {
      await axios.post(`${API}/compliance/seed-policies`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      await axios.post(`${API}/compliance/seed-insurance`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Compliance items created');
      fetchData();
    } catch (error) {
      toast.error('Failed to seed compliance items');
    }
  };

  // Handle assigning policy to employees
  const handleAssignPolicy = async () => {
    if (!policyToAssign || selectedEmployees.length === 0) {
      toast.error('Please select at least one employee');
      return;
    }
    
    setIsAssigning(true);
    try {
      // Create assignments for each selected employee using the policy assignments API
      // Note: We use the policy-assignments endpoint which expects policy_id from employee policies collection
      // But the Compliance Centre uses org_policy_id - need to create linking
      const response = await axios.post(`${API}/policies/assign`, {
        policy_id: policyToAssign.id,
        employee_ids: selectedEmployees
      }, { headers: { Authorization: `Bearer ${token}` } });
      
      toast.success(response.data.message || `Policy assigned to ${selectedEmployees.length} employees`);
      setAssignDialogOpen(false);
      setPolicyToAssign(null);
      setSelectedEmployees([]);
      await fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to assign policy');
    } finally {
      setIsAssigning(false);
    }
  };

  // Toggle employee selection
  const toggleEmployeeSelection = (empId) => {
    setSelectedEmployees(prev => 
      prev.includes(empId) 
        ? prev.filter(id => id !== empId)
        : [...prev, empId]
    );
  };

  // Select all unassigned employees
  const selectAllUnassigned = () => {
    if (!policyToAssign) return;
    const alreadyAssigned = policyAssignments
      .filter(a => a.policy_id === policyToAssign.id && !['unassigned', 'withdrawn'].includes(a.status))
      .map(a => a.employee_id);
    const unassigned = employees.filter(e => !alreadyAssigned.includes(e.id)).map(e => e.id);
    setSelectedEmployees(unassigned);
  };

  // Get assignment count for a policy
  const getAssignmentStats = (policyId) => {
    const assignments = policyAssignments.filter(a => a.policy_id === policyId && !['unassigned', 'withdrawn'].includes(a.status));
    const total = assignments.length;
    const acknowledged = assignments.filter(a => a.status === 'acknowledged' || a.status === 'signed').length;
    return { total, acknowledged };
  };

  const handleUploadPolicy = async (e) => {
    e.preventDefault();
    if (!uploadFile || !selectedPolicy) return;
    
    setIsUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', uploadFile);
      
      let url = `${API}/compliance/policies/${selectedPolicy.id}/upload`;
      const params = new URLSearchParams();
      if (uploadVersion) params.append('version', uploadVersion);
      if (uploadReviewDate) params.append('review_date', uploadReviewDate);
      if (params.toString()) url += `?${params.toString()}`;
      
      await axios.post(url, formData, {
        headers: { 
          Authorization: `Bearer ${token}`,
          'Content-Type': 'multipart/form-data'
        }
      });
      
      toast.success('Policy document uploaded');
      setUploadDialogOpen(false);
      resetUploadForm();
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to upload policy');
    } finally {
      setIsUploading(false);
    }
  };

  const handleUploadInsurance = async (e) => {
    e.preventDefault();
    if (!uploadFile || !selectedInsurance || !uploadExpiryDate) return;
    
    setIsUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', uploadFile);
      
      let url = `${API}/compliance/insurance/${selectedInsurance.id}/upload?expiry_date=${uploadExpiryDate}`;
      if (uploadPolicyNumber) url += `&policy_number=${encodeURIComponent(uploadPolicyNumber)}`;
      if (uploadProvider) url += `&provider=${encodeURIComponent(uploadProvider)}`;
      
      await axios.post(url, formData, {
        headers: { 
          Authorization: `Bearer ${token}`,
          'Content-Type': 'multipart/form-data'
        }
      });
      
      toast.success('Insurance document uploaded');
      setUploadDialogOpen(false);
      resetUploadForm();
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to upload insurance');
    } finally {
      setIsUploading(false);
    }
  };

  const handleCreateIncident = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    
    try {
      await axios.post(`${API}/compliance/incidents`, newIncident, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      toast.success('Incident report created');
      setIncidentDialogOpen(false);
      setNewIncident({
        incident_type: 'incident',
        title: '',
        description: '',
        date_occurred: new Date().toISOString().split('T')[0],
        location: '',
        persons_involved: '',
        immediate_actions: '',
        root_cause: '',
        corrective_actions: ''
      });
      fetchData();
    } catch (error) {
      toast.error('Failed to create incident report');
    } finally {
      setIsSubmitting(false);
    }
  };

  const fetchReports = async (type) => {
    try {
      if (type === 'dbs' && !dbsReport) {
        const res = await axios.get(`${API}/compliance/reports/staff-dbs`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        setDbsReport(res.data);
      }
      if (type === 'training' && !trainingReport) {
        const res = await axios.get(`${API}/compliance/reports/training?months=12`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        setTrainingReport(res.data);
      }
    } catch (error) {
      toast.error('Failed to generate report');
    }
  };

  const resetUploadForm = () => {
    setSelectedPolicy(null);
    setSelectedInsurance(null);
    setUploadFile(null);
    setUploadVersion('');
    setUploadReviewDate('');
    setUploadExpiryDate('');
    setUploadPolicyNumber('');
    setUploadProvider('');
  };

  const getStatusBadge = (status) => {
    const config = {
      active: { bg: 'bg-success/10', text: 'text-success', icon: CheckCircle },
      valid: { bg: 'bg-success/10', text: 'text-success', icon: CheckCircle },
      missing: { bg: 'bg-error/10', text: 'text-error', icon: XCircle },
      expired: { bg: 'bg-error/10', text: 'text-error', icon: AlertTriangle },
      expiring_soon: { bg: 'bg-warning/10', text: 'text-warning', icon: Clock },
      under_review: { bg: 'bg-info/10', text: 'text-info', icon: Clock },
      open: { bg: 'bg-error/10', text: 'text-error', icon: AlertCircle },
      investigating: { bg: 'bg-warning/10', text: 'text-warning', icon: Search },
      resolved: { bg: 'bg-info/10', text: 'text-info', icon: CheckCircle },
      closed: { bg: 'bg-success/10', text: 'text-success', icon: CheckCircle }
    };
    const c = config[status] || config.missing;
    const Icon = c.icon;
    
    return (
      <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${c.bg} ${c.text}`}>
        <Icon className="h-3 w-3" />
        {status.replace('_', ' ')}
      </span>
    );
  };

  const groupedPolicies = policies.reduce((acc, policy) => {
    if (!acc[policy.category]) acc[policy.category] = [];
    acc[policy.category].push(policy);
    return acc;
  }, {});

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="compliance-centre">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="font-heading text-2xl font-bold text-text-primary">Compliance Centre</h1>
          <p className="text-text-muted">Organisation-level compliance management for CQC readiness</p>
        </div>
        
        {isAdmin() && policies.length === 0 && (
          <Button onClick={handleSeedPolicies} className="bg-primary hover:bg-primary-hover text-white rounded-xl">
            <Plus className="h-4 w-4 mr-2" />
            Initialize Compliance Items
          </Button>
        )}
      </div>

      {/* Dashboard Summary */}
      {dashboard && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card className="border-[#E4E8EB] shadow-sm">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className={`p-2 rounded-lg ${dashboard.policies.missing > 0 ? 'bg-error/10' : 'bg-success/10'}`}>
                  <FileText className={`h-5 w-5 ${dashboard.policies.missing > 0 ? 'text-error' : 'text-success'}`} />
                </div>
                <div>
                  <p className="text-2xl font-bold text-text-primary">
                    {dashboard.policies.active}/{dashboard.policies.total}
                  </p>
                  <p className="text-xs text-text-muted">Policies Active</p>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card className="border-[#E4E8EB] shadow-sm">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className={`p-2 rounded-lg ${dashboard.insurance.missing > 0 || dashboard.insurance.expired > 0 ? 'bg-error/10' : 'bg-success/10'}`}>
                  <Shield className={`h-5 w-5 ${dashboard.insurance.missing > 0 || dashboard.insurance.expired > 0 ? 'text-error' : 'text-success'}`} />
                </div>
                <div>
                  <p className="text-2xl font-bold text-text-primary">
                    {dashboard.insurance.valid}/{dashboard.insurance.total}
                  </p>
                  <p className="text-xs text-text-muted">Insurance Valid</p>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card className="border-[#E4E8EB] shadow-sm">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className={`p-2 rounded-lg ${dashboard.incidents.open > 0 ? 'bg-warning/10' : 'bg-success/10'}`}>
                  <AlertCircle className={`h-5 w-5 ${dashboard.incidents.open > 0 ? 'text-warning' : 'text-success'}`} />
                </div>
                <div>
                  <p className="text-2xl font-bold text-text-primary">{dashboard.incidents.open}</p>
                  <p className="text-xs text-text-muted">Open Incidents</p>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card className="border-[#E4E8EB] shadow-sm">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-primary/10">
                  <Users className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-text-primary">{dashboard.staff.active}</p>
                  <p className="text-xs text-text-muted">Active Staff</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={handleTabChange} className="space-y-6">
        <TabsList className="bg-white border border-[#E4E8EB] p-1 rounded-xl flex-wrap">
          <TabsTrigger value="policies" className="rounded-lg data-[state=active]:bg-primary data-[state=active]:text-white" data-testid="tab-policies">
            <FileText className="h-4 w-4 mr-2" />
            Policies
          </TabsTrigger>
          <TabsTrigger value="insurance" className="rounded-lg data-[state=active]:bg-primary data-[state=active]:text-white" data-testid="tab-insurance">
            <Shield className="h-4 w-4 mr-2" />
            Insurance & Certificates
          </TabsTrigger>
          <TabsTrigger value="incidents" className="rounded-lg data-[state=active]:bg-primary data-[state=active]:text-white" data-testid="tab-incidents">
            <AlertCircle className="h-4 w-4 mr-2" />
            Incidents
          </TabsTrigger>
          <TabsTrigger 
            value="reports" 
            className="rounded-lg data-[state=active]:bg-primary data-[state=active]:text-white"
            onClick={() => fetchReports('dbs')}
            data-testid="tab-reports"
          >
            <ClipboardList className="h-4 w-4 mr-2" />
            Reports
          </TabsTrigger>
        </TabsList>

        {/* Policies Tab */}
        <TabsContent value="policies">
          <Card className="border-[#E4E8EB] shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="font-heading text-lg">Organisation Policies</CardTitle>
                <p className="text-sm text-text-muted mt-1">
                  Upload and manage your organisation's policies here. Assign them to employees once uploaded.
                </p>
                <p className="text-xs text-text-muted mt-1">
                  {policies.filter(p => p.status === 'active').length} of {policies.length} policies uploaded
                </p>
              </div>
              {isAdmin() && policies.length > 0 && policies.some(p => p.status === 'missing') && (
                <div className="flex items-center gap-2 text-sm text-warning bg-warning/10 px-3 py-1.5 rounded-lg">
                  <AlertTriangle className="h-4 w-4" />
                  {policies.filter(p => p.status === 'missing').length} policies missing
                </div>
              )}
            </CardHeader>
            <CardContent>
              {policies.length === 0 ? (
                <div className="text-center py-12">
                  <FileText className="h-12 w-12 mx-auto text-text-muted/50 mb-3" />
                  <p className="text-text-muted">No policies configured</p>
                  {isAdmin() && (
                    <Button onClick={handleSeedPolicies} className="mt-4 rounded-xl">
                      Initialize Core Policies
                    </Button>
                  )}
                </div>
              ) : (
                <div className="space-y-8">
                  {['Core', 'Clinical', 'Operational', 'Governance'].map((category) => {
                    const categoryPolicies = groupedPolicies[category] || [];
                    if (categoryPolicies.length === 0) return null;
                    
                    const activeCount = categoryPolicies.filter(p => p.status === 'active').length;
                    const missingCount = categoryPolicies.filter(p => p.status === 'missing').length;
                    const expiringCount = categoryPolicies.filter(p => p.status === 'expired' || p.status === 'under_review').length;
                    
                    const categoryColors = {
                      'Core': 'bg-primary',
                      'Clinical': 'bg-info',
                      'Operational': 'bg-warning',
                      'Governance': 'bg-success'
                    };
                    
                    return (
                      <div key={category} data-testid={`policy-category-${category.toLowerCase()}`}>
                        <div className="flex items-center justify-between mb-4">
                          <div className="flex items-center gap-3">
                            <div className={`w-1 h-8 rounded-full ${categoryColors[category]}`}></div>
                            <div>
                              <h3 className="font-semibold text-text-primary">{category}</h3>
                              <p className="text-xs text-text-muted">
                                {activeCount}/{categoryPolicies.length} uploaded
                                {missingCount > 0 && <span className="text-error ml-2">• {missingCount} missing</span>}
                                {expiringCount > 0 && <span className="text-warning ml-2">• {expiringCount} expiring</span>}
                              </p>
                            </div>
                          </div>
                        </div>
                        <div className="space-y-2 ml-4">
                          {categoryPolicies.map((policy) => (
                            <div 
                              key={policy.id}
                              className="flex items-center justify-between p-4 bg-[#F8FAFA] rounded-xl border border-[#E4E8EB] hover:border-primary/30 transition-colors"
                              data-testid={`policy-${policy.id}`}
                            >
                              <div className="flex items-center gap-4">
                                <div className={`p-2 rounded-lg ${policy.status === 'active' ? 'bg-success/10' : 'bg-error/10'}`}>
                                  <FileText className={`h-5 w-5 ${policy.status === 'active' ? 'text-success' : 'text-error'}`} />
                                </div>
                                <div>
                                  <p className="font-medium text-text-primary">{policy.name}</p>
                                  <div className="flex items-center gap-3 text-xs text-text-muted mt-1">
                                    <span>Version: {policy.version}</span>
                                    {policy.review_date && (
                                      <span className="flex items-center gap-1">
                                        <Calendar className="h-3 w-3" />
                                        Review: {new Date(policy.review_date).toLocaleDateString()}
                                      </span>
                                    )}
                                    {policy.last_reviewed_at && (
                                      <span className="flex items-center gap-1">
                                        <CheckCircle className="h-3 w-3 text-success" />
                                        Last reviewed: {new Date(policy.last_reviewed_at).toLocaleDateString()}
                                      </span>
                                    )}
                                  </div>
                                </div>
                              </div>
                              
                              <div className="flex items-center gap-3">
                                {getStatusBadge(policy.status)}
                                
                                {policy.file_url ? (
                                  <div className="flex items-center gap-2">
                                    <Button 
                                      variant="outline" 
                                      size="sm"
                                      className="rounded-lg"
                                      onClick={() => handleViewDocument('policy', policy.id, policy.name, policy.original_filename)}
                                      data-testid={`view-policy-${policy.id}`}
                                    >
                                      <Eye className="h-4 w-4 mr-1" />
                                      View
                                    </Button>
                                    <Button 
                                      variant="outline" 
                                      size="sm"
                                      className="rounded-lg"
                                      onClick={() => handleDownloadDocument('policy', policy.id, policy.original_filename || `${policy.name}.pdf`)}
                                      data-testid={`download-policy-${policy.id}`}
                                    >
                                      <Download className="h-4 w-4 mr-1" />
                                      Download
                                    </Button>
                                    {isAdmin() && (
                                      <>
                                        <Button 
                                          size="sm"
                                          variant="outline"
                                          className="rounded-lg"
                                          onClick={() => {
                                            setSelectedPolicy(policy);
                                            setSelectedInsurance(null);
                                            setUploadDialogOpen(true);
                                          }}
                                        >
                                          <RefreshCw className="h-4 w-4 mr-1" />
                                          Replace
                                        </Button>
                                        {/* Assign to Employees Button */}
                                        <Button 
                                          size="sm"
                                          className="bg-primary hover:bg-primary-hover text-white rounded-lg"
                                          onClick={() => {
                                            setPolicyToAssign(policy);
                                            setSelectedEmployees([]);
                                            setAssignDialogOpen(true);
                                          }}
                                          data-testid={`assign-policy-${policy.id}`}
                                        >
                                          <UserPlus className="h-4 w-4 mr-1" />
                                          Assign to Employees
                                          {(() => {
                                            const stats = getAssignmentStats(policy.id);
                                            return stats.total > 0 ? (
                                              <span className="ml-1 text-xs bg-white/20 px-1.5 py-0.5 rounded">
                                                {stats.acknowledged}/{stats.total}
                                              </span>
                                            ) : null;
                                          })()}
                                        </Button>
                                      </>
                                    )}
                                  </div>
                                ) : isAdmin() && (
                                  <div className="flex items-center gap-2">
                                    <Button 
                                      size="sm"
                                      className="bg-primary hover:bg-primary-hover text-white rounded-lg"
                                      onClick={() => {
                                        setSelectedPolicy(policy);
                                        setSelectedInsurance(null);
                                        setUploadDialogOpen(true);
                                      }}
                                    >
                                      <Upload className="h-4 w-4 mr-1" />
                                      Upload
                                    </Button>
                                    {/* Disabled Assign Button - no document yet */}
                                    <Button 
                                      size="sm"
                                      variant="outline"
                                      className="rounded-lg text-text-muted"
                                      disabled
                                      title="Upload policy document before assigning to employees"
                                    >
                                      <UserPlus className="h-4 w-4 mr-1" />
                                      Assign
                                    </Button>
                                  </div>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Insurance Tab */}
        <TabsContent value="insurance">
          <Card className="border-[#E4E8EB] shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="font-heading text-lg">Insurance & Certificates</CardTitle>
                <p className="text-sm text-text-muted mt-1">
                  {insurance.filter(i => i.status === 'valid').length} of {insurance.length} documents valid
                </p>
              </div>
              {insurance.some(i => i.status === 'missing' || i.status === 'expired') && (
                <div className="flex items-center gap-2 text-sm text-error bg-error/10 px-3 py-1.5 rounded-lg">
                  <AlertTriangle className="h-4 w-4" />
                  {insurance.filter(i => i.status === 'missing' || i.status === 'expired').length} require attention
                </div>
              )}
            </CardHeader>
            <CardContent>
              {insurance.length === 0 ? (
                <div className="text-center py-12">
                  <Shield className="h-12 w-12 mx-auto text-text-muted/50 mb-3" />
                  <p className="text-text-muted">No insurance documents configured</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {insurance.map((ins) => (
                    <div 
                      key={ins.id}
                      className="flex items-center justify-between p-4 bg-[#F8FAFA] rounded-xl border border-[#E4E8EB] hover:border-primary/30 transition-colors"
                      data-testid={`insurance-${ins.id}`}
                    >
                      <div className="flex items-center gap-4">
                        <div className={`p-2 rounded-lg ${ins.status === 'valid' ? 'bg-success/10' : ins.status === 'expiring_soon' ? 'bg-warning/10' : 'bg-error/10'}`}>
                          <Shield className={`h-5 w-5 ${ins.status === 'valid' ? 'text-success' : ins.status === 'expiring_soon' ? 'text-warning' : 'text-error'}`} />
                        </div>
                        <div>
                          <p className="font-medium text-text-primary">{ins.name}</p>
                          <div className="flex items-center gap-3 text-xs text-text-muted mt-1">
                            {ins.provider && <span>Provider: {ins.provider}</span>}
                            {ins.policy_number && <span>Policy #: {ins.policy_number}</span>}
                            {ins.expiry_date && (
                              <span className="flex items-center gap-1">
                                <Calendar className="h-3 w-3" />
                                Expires: {new Date(ins.expiry_date).toLocaleDateString()}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-3">
                        {getStatusBadge(ins.status)}
                        
                        {ins.file_url ? (
                          <div className="flex items-center gap-2">
                            <Button 
                              variant="outline" 
                              size="sm"
                              className="rounded-lg"
                              onClick={() => handleViewDocument('insurance', ins.id, ins.name, ins.original_filename)}
                              data-testid={`view-insurance-${ins.id}`}
                            >
                              <Eye className="h-4 w-4 mr-1" />
                              View
                            </Button>
                            <Button 
                              variant="outline" 
                              size="sm"
                              className="rounded-lg"
                              onClick={() => handleDownloadDocument('insurance', ins.id, ins.original_filename || `${ins.name}.pdf`)}
                              data-testid={`download-insurance-${ins.id}`}
                            >
                              <Download className="h-4 w-4 mr-1" />
                              Download
                            </Button>
                            {isAdmin() && (
                              <Button 
                                size="sm"
                                variant="outline"
                                className="rounded-lg"
                                onClick={() => {
                                  setSelectedInsurance(ins);
                                  setSelectedPolicy(null);
                                  setUploadDialogOpen(true);
                                }}
                              >
                                <RefreshCw className="h-4 w-4 mr-1" />
                                Replace
                              </Button>
                            )}
                          </div>
                        ) : isAdmin() && (
                          <Button 
                            size="sm"
                            className="bg-primary hover:bg-primary-hover text-white rounded-lg"
                            onClick={() => {
                              setSelectedInsurance(ins);
                              setSelectedPolicy(null);
                              setUploadDialogOpen(true);
                            }}
                          >
                            <Upload className="h-4 w-4 mr-1" />
                            Upload
                          </Button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Incidents Tab */}
        <TabsContent value="incidents">
          <Card className="border-[#E4E8EB] shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="font-heading text-lg">Incident & Outbreak Logs</CardTitle>
              <Dialog open={incidentDialogOpen} onOpenChange={setIncidentDialogOpen}>
                <DialogTrigger asChild>
                  <Button className="bg-primary hover:bg-primary-hover text-white rounded-xl">
                    <Plus className="h-4 w-4 mr-2" />
                    Report Incident
                  </Button>
                </DialogTrigger>
                <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
                  <DialogHeader>
                    <DialogTitle className="font-heading">Report Incident/Outbreak</DialogTitle>
                  </DialogHeader>
                  <form onSubmit={handleCreateIncident} className="space-y-4 mt-4">
                    <div className="grid sm:grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label>Incident Type *</Label>
                        <Select 
                          value={newIncident.incident_type} 
                          onValueChange={(v) => setNewIncident({...newIncident, incident_type: v})}
                        >
                          <SelectTrigger className="rounded-xl">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="incident">Incident</SelectItem>
                            <SelectItem value="outbreak">Outbreak</SelectItem>
                            <SelectItem value="near_miss">Near Miss</SelectItem>
                            <SelectItem value="complaint">Complaint</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="space-y-2">
                        <Label>Date Occurred *</Label>
                        <Input
                          type="date"
                          value={newIncident.date_occurred}
                          onChange={(e) => setNewIncident({...newIncident, date_occurred: e.target.value})}
                          required
                          className="rounded-xl"
                        />
                      </div>
                    </div>
                    
                    <div className="space-y-2">
                      <Label>Title *</Label>
                      <Input
                        value={newIncident.title}
                        onChange={(e) => setNewIncident({...newIncident, title: e.target.value})}
                        placeholder="Brief title for the incident"
                        required
                        className="rounded-xl"
                      />
                    </div>
                    
                    <div className="space-y-2">
                      <Label>Description *</Label>
                      <Textarea
                        value={newIncident.description}
                        onChange={(e) => setNewIncident({...newIncident, description: e.target.value})}
                        placeholder="Detailed description of what happened"
                        required
                        className="rounded-xl"
                        rows={3}
                      />
                    </div>
                    
                    <div className="grid sm:grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label>Location</Label>
                        <Input
                          value={newIncident.location}
                          onChange={(e) => setNewIncident({...newIncident, location: e.target.value})}
                          placeholder="Where did it occur?"
                          className="rounded-xl"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>Persons Involved</Label>
                        <Input
                          value={newIncident.persons_involved}
                          onChange={(e) => setNewIncident({...newIncident, persons_involved: e.target.value})}
                          placeholder="Names/roles of people involved"
                          className="rounded-xl"
                        />
                      </div>
                    </div>
                    
                    <div className="space-y-2">
                      <Label>Immediate Actions Taken</Label>
                      <Textarea
                        value={newIncident.immediate_actions}
                        onChange={(e) => setNewIncident({...newIncident, immediate_actions: e.target.value})}
                        placeholder="What actions were taken immediately?"
                        className="rounded-xl"
                        rows={2}
                      />
                    </div>
                    
                    <div className="space-y-2">
                      <Label>Root Cause Analysis</Label>
                      <Textarea
                        value={newIncident.root_cause}
                        onChange={(e) => setNewIncident({...newIncident, root_cause: e.target.value})}
                        placeholder="What was the underlying cause?"
                        className="rounded-xl"
                        rows={2}
                      />
                    </div>
                    
                    <div className="space-y-2">
                      <Label>Corrective Actions</Label>
                      <Textarea
                        value={newIncident.corrective_actions}
                        onChange={(e) => setNewIncident({...newIncident, corrective_actions: e.target.value})}
                        placeholder="What steps will be taken to prevent recurrence?"
                        className="rounded-xl"
                        rows={2}
                      />
                    </div>
                    
                    <div className="flex justify-end gap-3 pt-4">
                      <Button type="button" variant="outline" onClick={() => setIncidentDialogOpen(false)} className="rounded-xl">
                        Cancel
                      </Button>
                      <Button type="submit" disabled={isSubmitting} className="bg-primary hover:bg-primary-hover text-white rounded-xl">
                        {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Submit Report'}
                      </Button>
                    </div>
                  </form>
                </DialogContent>
              </Dialog>
            </CardHeader>
            <CardContent>
              {incidents.length === 0 ? (
                <div className="text-center py-12">
                  <AlertCircle className="h-12 w-12 mx-auto text-text-muted/50 mb-3" />
                  <p className="text-text-muted">No incidents recorded</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {incidents.map((incident) => (
                    <div 
                      key={incident.id}
                      className="p-4 bg-[#F8FAFA] rounded-xl border border-[#E4E8EB]"
                    >
                      <div className="flex items-start justify-between">
                        <div>
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-xs font-mono text-text-muted">{incident.reference_number}</span>
                            {getStatusBadge(incident.status)}
                            <span className={`text-xs px-2 py-0.5 rounded ${
                              incident.incident_type === 'outbreak' ? 'bg-error/10 text-error' :
                              incident.incident_type === 'complaint' ? 'bg-warning/10 text-warning' :
                              'bg-info/10 text-info'
                            }`}>
                              {incident.incident_type}
                            </span>
                          </div>
                          <p className="font-medium text-text-primary">{incident.title}</p>
                          <p className="text-sm text-text-muted mt-1 line-clamp-2">{incident.description}</p>
                          <div className="flex items-center gap-3 text-xs text-text-muted mt-2">
                            <span>Date: {new Date(incident.date_occurred).toLocaleDateString()}</span>
                            {incident.location && <span>Location: {incident.location}</span>}
                          </div>
                        </div>
                      </div>
                      {incident.root_cause && (
                        <div className="mt-3 pt-3 border-t border-[#E4E8EB]">
                          <p className="text-xs text-text-muted">Root Cause:</p>
                          <p className="text-sm text-text-primary">{incident.root_cause}</p>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Reports Tab */}
        <TabsContent value="reports">
          <div className="grid md:grid-cols-2 gap-6">
            {/* Staff DBS Report */}
            <Card className="border-[#E4E8EB] shadow-sm">
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="font-heading text-lg">Staff DBS Dates</CardTitle>
                <Button 
                  variant="outline" 
                  size="sm" 
                  className="rounded-lg"
                  onClick={() => fetchReports('dbs')}
                >
                  <RefreshCw className="h-4 w-4 mr-1" />
                  Refresh
                </Button>
              </CardHeader>
              <CardContent>
                {dbsReport ? (
                  <div className="space-y-2 max-h-96 overflow-y-auto">
                    {dbsReport.report.map((staff) => (
                      <div key={staff.employee_id} className="flex items-center justify-between p-3 bg-[#F8FAFA] rounded-lg">
                        <div>
                          <p className="font-medium text-text-primary text-sm">{staff.name}</p>
                          <p className="text-xs text-text-muted">{staff.role} • {staff.assignment}</p>
                        </div>
                        <div className="text-right">
                          {getStatusBadge(staff.dbs_status)}
                          {staff.dbs_expiry && (
                            <p className="text-xs text-text-muted mt-1">
                              Exp: {new Date(staff.dbs_expiry).toLocaleDateString()}
                            </p>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <Loader2 className="h-6 w-6 animate-spin mx-auto text-text-muted" />
                    <p className="text-sm text-text-muted mt-2">Loading report...</p>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Training Report */}
            <Card className="border-[#E4E8EB] shadow-sm">
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="font-heading text-lg">Training Report (12 months)</CardTitle>
                <Button 
                  variant="outline" 
                  size="sm" 
                  className="rounded-lg"
                  onClick={() => fetchReports('training')}
                >
                  <RefreshCw className="h-4 w-4 mr-1" />
                  Refresh
                </Button>
              </CardHeader>
              <CardContent>
                {trainingReport ? (
                  <div className="space-y-2 max-h-96 overflow-y-auto">
                    {trainingReport.report.map((staff) => (
                      <div key={staff.employee_id} className="flex items-center justify-between p-3 bg-[#F8FAFA] rounded-lg">
                        <div>
                          <p className="font-medium text-text-primary text-sm">{staff.name}</p>
                          <p className="text-xs text-text-muted">{staff.role}</p>
                        </div>
                        <div className="text-right">
                          <span className="text-sm font-medium text-success">{staff.completed_count} completed</span>
                          {staff.pending_count > 0 && (
                            <span className="text-sm text-warning ml-2">{staff.pending_count} pending</span>
                          )}
                          {staff.expiring_soon?.length > 0 && (
                            <p className="text-xs text-error mt-1">{staff.expiring_soon.length} expiring</p>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <Button onClick={() => fetchReports('training')} variant="outline" className="rounded-xl">
                      Generate Report
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>

      {/* Upload Dialog */}
      <Dialog open={uploadDialogOpen} onOpenChange={(open) => { setUploadDialogOpen(open); if (!open) resetUploadForm(); }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="font-heading">
              {selectedPolicy ? `Upload ${selectedPolicy.name}` : selectedInsurance ? `Upload ${selectedInsurance.name}` : 'Upload Document'}
            </DialogTitle>
          </DialogHeader>
          
          <form onSubmit={selectedPolicy ? handleUploadPolicy : handleUploadInsurance} className="space-y-4 mt-4">
            <div className="space-y-2">
              <Label>Document File *</Label>
              <Input
                type="file"
                onChange={(e) => setUploadFile(e.target.files[0])}
                required
                className="rounded-xl"
              />
            </div>
            
            {selectedPolicy && (
              <>
                <div className="space-y-2">
                  <Label>Version</Label>
                  <Input
                    value={uploadVersion}
                    onChange={(e) => setUploadVersion(e.target.value)}
                    placeholder="e.g., v2.0"
                    className="rounded-xl"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Next Review Date</Label>
                  <Input
                    type="date"
                    value={uploadReviewDate}
                    onChange={(e) => setUploadReviewDate(e.target.value)}
                    className="rounded-xl"
                  />
                </div>
              </>
            )}
            
            {selectedInsurance && (
              <>
                <div className="space-y-2">
                  <Label>Expiry Date *</Label>
                  <Input
                    type="date"
                    value={uploadExpiryDate}
                    onChange={(e) => setUploadExpiryDate(e.target.value)}
                    required
                    className="rounded-xl"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Policy Number</Label>
                  <Input
                    value={uploadPolicyNumber}
                    onChange={(e) => setUploadPolicyNumber(e.target.value)}
                    placeholder="Insurance policy number"
                    className="rounded-xl"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Insurance Provider</Label>
                  <Input
                    value={uploadProvider}
                    onChange={(e) => setUploadProvider(e.target.value)}
                    placeholder="e.g., Aviva, AXA"
                    className="rounded-xl"
                  />
                </div>
              </>
            )}
            
            <div className="flex justify-end gap-3 pt-4">
              <Button type="button" variant="outline" onClick={() => { setUploadDialogOpen(false); resetUploadForm(); }} className="rounded-xl">
                Cancel
              </Button>
              <Button type="submit" disabled={isUploading} className="bg-primary hover:bg-primary-hover text-white rounded-xl">
                {isUploading ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Upload'}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      {/* Document Preview Modal */}
      <DocumentPreviewModal
        isOpen={previewOpen}
        onClose={() => setPreviewOpen(false)}
        fileUrl={previewFile?.url}
        fileName={previewFile?.name}
        token={token}
        onDownload={previewFile ? () => {
          // Determine type from URL
          const isPolicy = previewFile.url?.includes('/policies/');
          const id = previewFile.url?.split('/').slice(-2, -1)[0];
          if (id) {
            handleDownloadDocument(isPolicy ? 'policy' : 'insurance', id, previewFile.filename);
          }
        } : undefined}
      />

      {/* Policy Assignment Modal */}
      <Dialog open={assignDialogOpen} onOpenChange={(open) => {
        setAssignDialogOpen(open);
        if (!open) {
          setPolicyToAssign(null);
          setSelectedEmployees([]);
        }
      }}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="font-heading">Assign Policy to Employees</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 mt-4">
            {policyToAssign && (
              <div className="p-3 bg-[#F8FAFA] rounded-xl border border-[#E4E8EB]">
                <p className="font-medium text-text-primary">{policyToAssign.name}</p>
                <p className="text-sm text-text-muted">Version {policyToAssign.version}</p>
              </div>
            )}
            
            <div className="flex items-center justify-between">
              <Label className="text-sm font-medium">Select Employees</Label>
              <Button 
                type="button" 
                variant="ghost" 
                size="sm"
                onClick={selectAllUnassigned}
                className="text-primary"
              >
                Select All Unassigned
              </Button>
            </div>
            
            <div className="max-h-60 overflow-y-auto space-y-2 border border-[#E4E8EB] rounded-xl p-3">
              {employees.length === 0 ? (
                <p className="text-sm text-text-muted text-center py-4">No employees found</p>
              ) : (
                employees.map((emp) => {
                  const isAlreadyAssigned = policyAssignments.some(
                    a => a.policy_id === policyToAssign?.id && 
                         a.employee_id === emp.id && 
                         !['unassigned', 'withdrawn'].includes(a.status)
                  );
                  const assignment = policyAssignments.find(
                    a => a.policy_id === policyToAssign?.id && 
                         a.employee_id === emp.id && 
                         !['unassigned', 'withdrawn'].includes(a.status)
                  );
                  
                  return (
                    <label 
                      key={emp.id} 
                      className={`flex items-center gap-3 p-2 rounded-lg cursor-pointer ${
                        isAlreadyAssigned ? 'bg-gray-100 opacity-60' : 'hover:bg-[#F8FAFA]'
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={selectedEmployees.includes(emp.id)}
                        onChange={() => !isAlreadyAssigned && toggleEmployeeSelection(emp.id)}
                        disabled={isAlreadyAssigned}
                        className="rounded border-[#E4E8EB]"
                      />
                      <span className="text-text-primary flex-1">
                        {emp.first_name} {emp.last_name}
                      </span>
                      {isAlreadyAssigned && (
                        <span className={`text-xs px-2 py-0.5 rounded ${
                          assignment?.status === 'acknowledged' || assignment?.status === 'signed' 
                            ? 'bg-green-100 text-green-700' 
                            : 'bg-blue-100 text-blue-700'
                        }`}>
                          {assignment?.status === 'acknowledged' || assignment?.status === 'signed' 
                            ? 'Acknowledged' 
                            : 'Assigned'}
                        </span>
                      )}
                    </label>
                  );
                })
              )}
            </div>
            
            <p className="text-sm text-text-muted">
              {selectedEmployees.length} employee(s) selected
            </p>
            
            <div className="flex justify-end gap-3 pt-4">
              <Button 
                type="button" 
                variant="outline" 
                onClick={() => { setAssignDialogOpen(false); setSelectedEmployees([]); }} 
                className="rounded-xl"
              >
                Cancel
              </Button>
              <Button 
                onClick={handleAssignPolicy}
                disabled={isAssigning || selectedEmployees.length === 0} 
                className="bg-primary hover:bg-primary-hover text-white rounded-xl"
                data-testid="assign-policy-submit"
              >
                {isAssigning ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Assign Policy'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
