import { useState, useEffect } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter, DialogDescription } from '../../components/ui/dialog';
import { Label } from '../../components/ui/label';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from '../../components/ui/dropdown-menu';
import { Badge } from '../../components/ui/badge';
import { toast } from 'sonner';
import { Search, UserPlus, Filter, Loader2, MoreHorizontal, Edit, Archive, Trash2, RotateCcw, FileDown, AlertTriangle, Shield, CheckCircle, Clock, Users, Mail, Send, X, CheckSquare, Square } from 'lucide-react';
import { Checkbox } from '../../components/ui/checkbox';
import { Textarea } from '../../components/ui/textarea';
import EmployeeAvatar from '../../components/portal/EmployeeAvatar';
import LifecycleReasonDialog from '../../components/portal/LifecycleReasonDialog';
import { StageIdentityBadge } from '../../components/compliance';
import { isActiveLifecycleStatus, isEmployeeStatus, normalizeLifecycleStatus, TERMINAL_STATUSES } from '../../lib/lifecycle';
import API_BASE from '../../utils/apiBase';

const API = API_BASE;

const getInitialReadinessFilter = (searchParams) => {
  if (searchParams.get('is_work_ready') === 'true') return 'READY_TO_WORK';
  if (searchParams.get('is_work_ready') === 'false') return 'NOT_READY';
  if (searchParams.get('can_promote') === 'true') return 'CAN_PROMOTE';

  const legacy = searchParams.get('work_readiness');
  if (legacy === 'ready_to_work' || legacy === 'READY_TO_WORK') return 'READY_TO_WORK';
  if (legacy === 'not_ready' || legacy === 'NOT_READY') return 'NOT_READY';
  if (legacy === 'supervised_start' || legacy === 'READY_WITH_CONDITIONS') return 'CAN_PROMOTE';
  return '';
};

const matchesReadinessFilter = (employee, filter) => {
  const readiness = employee.canonical_readiness;
  if (!filter) return true;
  if (filter === 'READY_TO_WORK') return readiness?.is_work_ready === true;
  if (filter === 'CAN_PROMOTE') return readiness?.can_promote === true && readiness?.is_work_ready !== true;
  if (filter === 'NOT_READY') return readiness?.is_work_ready !== true && readiness?.can_promote !== true;
  return true;
};

const STAGE_PRESETS = [
  { key: 'ALL', label: 'All' },
  { key: 'ONBOARDING', label: 'Onboarding' },
  { key: 'READY_TO_WORK', label: 'Ready for Work' },
  { key: 'CAN_PROMOTE', label: 'Eligible to Move to Active' },
  { key: 'ACTIVE', label: 'Active' },
  { key: 'INACTIVE', label: 'Inactive' },
];

const statusColors = {
  new: 'status-info',
  screening: 'status-info',
  interview: 'status-info',
  compliance_review: 'status-warning',
  onboarding: 'status-info',
  active: 'status-success',
  inactive: 'status-neutral',
  archived: 'status-neutral',
  withdrawn: 'status-neutral',
  superseded: 'status-neutral'
};

export default function EmployeesPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading] = useState(true);
  const [viewMode, setViewMode] = useState(searchParams.get('view') === 'compliance' ? 'compliance' : 'staff');
  const [complianceStatusFilter, setComplianceStatusFilter] = useState(searchParams.get('compliance_status') || 'all');
  const [complianceRows, setComplianceRows] = useState([]);
  const [complianceLoading, setComplianceLoading] = useState(false);
  
  // Initialize state from URL params for navigation state persistence
  const [search, setSearch] = useState(searchParams.get('q') || '');
  const [statusFilter, setStatusFilter] = useState(searchParams.get('status') || '');
  const [onboardingStatusFilter, setOnboardingStatusFilter] = useState(searchParams.get('onboarding') || '');
  const [workReadinessFilter, setWorkReadinessFilter] = useState(getInitialReadinessFilter(searchParams));
  const [stagePreset, setStagePreset] = useState(searchParams.get('stage_preset') || 'ALL');
  const [requirementFilter, setRequirementFilter] = useState(searchParams.get('requirement') || '');
  const [showArchived, setShowArchived] = useState(searchParams.get('archived') === 'true');
  const [onboardingStatuses, setOnboardingStatuses] = useState([]);
  const [isAddOpen, setIsAddOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [archiveDialogOpen, setArchiveDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [selectedEmployee, setSelectedEmployee] = useState(null);
  
  // Bulk request states
  const [bulkMode, setBulkMode] = useState(false);
  const [selectedEmployees, setSelectedEmployees] = useState([]);
  const [bulkRequestOpen, setBulkRequestOpen] = useState(false);
  const [bulkRequestType, setBulkRequestType] = useState('missing'); // 'missing' or 'specific'
  const [bulkRequirements, setBulkRequirements] = useState([]);
  const [selectedRequirements, setSelectedRequirements] = useState([]);
  const [bulkMessage, setBulkMessage] = useState('');
  const [bulkDueDays, setBulkDueDays] = useState(14);
  const [isBulkRequesting, setIsBulkRequesting] = useState(false);
  const [bulkResult, setBulkResult] = useState(null);
  const [lifecycleReasonDialogOpen, setLifecycleReasonDialogOpen] = useState(false);
  const [lifecycleTargetEmployee, setLifecycleTargetEmployee] = useState(null);
  const [lifecycleNextStatus, setLifecycleNextStatus] = useState('');
  const [lifecycleActionLabel, setLifecycleActionLabel] = useState('');
  const [isLifecycleSaving, setIsLifecycleSaving] = useState(false);
  
  const { token, isAuditor, user } = useAuth();

  // Sync state to URL params for navigation preservation
  useEffect(() => {
    const newParams = new URLSearchParams();
    if (search) newParams.set('q', search);
    if (viewMode === 'compliance') newParams.set('view', 'compliance');
    if (viewMode === 'compliance' && complianceStatusFilter && complianceStatusFilter !== 'all') {
      newParams.set('compliance_status', complianceStatusFilter);
    }
    if (statusFilter) newParams.set('status', statusFilter);
    if (onboardingStatusFilter) newParams.set('onboarding', onboardingStatusFilter);
    if (workReadinessFilter === 'READY_TO_WORK') newParams.set('is_work_ready', 'true');
    if (workReadinessFilter === 'NOT_READY') newParams.set('is_work_ready', 'false');
    if (workReadinessFilter === 'CAN_PROMOTE') newParams.set('can_promote', 'true');
    if (stagePreset && stagePreset !== 'ALL') newParams.set('stage_preset', stagePreset);
    if (requirementFilter) newParams.set('requirement', requirementFilter);
    if (showArchived) newParams.set('archived', 'true');
    
    // Only update URL if params changed (avoid infinite loop)
    const currentString = searchParams.toString();
    const newString = newParams.toString();
    if (currentString !== newString) {
      setSearchParams(newParams, { replace: true });
    }
  }, [
    search,
    viewMode,
    complianceStatusFilter,
    statusFilter,
    onboardingStatusFilter,
    workReadinessFilter,
    stagePreset,
    requirementFilter,
    showArchived,
  ]);

  const [newEmployee, setNewEmployee] = useState({
    first_name: '',
    last_name: '',
    email: '',
    phone: '',
    role: 'Care Assistant',
    onboarding_status: 'New',
    status: 'new'
  });

  const fetchEmployees = async () => {
    try {
      const params = new URLSearchParams();
      if (search) params.append('search', search);
      
      // Use /staff/employees endpoint for staff-only view (excludes applicants)
      // Only fall back to /employees when explicitly viewing archived
      let endpoint = `${API}/staff/employees`;
      
      if (statusFilter === 'archived' || showArchived) {
        // For archived view, use the general employees endpoint
        endpoint = `${API}/employees`;
        params.append('include_archived', 'true');
        if (statusFilter === 'archived') params.append('status', 'archived');
      } else if (statusFilter && statusFilter !== 'all') {
        // Apply status filter within staff
        params.append('status', statusFilter);
      }
      
      if (onboardingStatusFilter) params.append('onboarding_status', onboardingStatusFilter);
      
      const response = await axios.get(`${endpoint}?${params}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      const employeeRows = (response.data || []).filter((employee) => {
        const status = normalizeLifecycleStatus(employee?.status);
        if (isEmployeeStatus(status)) return true;
        if (showArchived && TERMINAL_STATUSES.includes(status)) return true;
        return false;
      });
      const employeeIds = employeeRows.map((employee) => employee.id).filter(Boolean);
      const readinessRes = employeeIds.length > 0
        ? await axios.get(`${API}/employees/unified-progress-summary`, {
            params: { employee_ids: employeeIds.join(',') },
            headers: { Authorization: `Bearer ${token}` }
          }).catch(() => ({ data: [] }))
        : { data: [] };
      const readinessByEmployeeId = new Map(
        (readinessRes.data || []).map((summary) => [summary.employee_id, summary])
      );
      setEmployees(employeeRows.map((employee) => ({
        ...employee,
        canonical_readiness: readinessByEmployeeId.get(employee.id) || null
      })));
    } catch (error) {
      console.error('Failed to fetch employees:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchOnboardingStatuses = async () => {
    try {
      const response = await axios.get(`${API}/onboarding-statuses`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setOnboardingStatuses(response.data);
    } catch (error) {
      console.error('Failed to fetch onboarding statuses:', error);
      // Fallback to default values
      setOnboardingStatuses(['New', 'Documents Pending', 'Under Review', 'Ready for Placement', 'Active', 'Archived']);
    }
  };

  const fetchComplianceDashboard = async () => {
    setComplianceLoading(true);
    try {
      const response = await axios.get(`${API}/staff/compliance-dashboard`, {
        params: {
          status: complianceStatusFilter || 'all',
        },
        headers: { Authorization: `Bearer ${token}` }
      });
      setComplianceRows(response.data?.items || []);
    } catch (error) {
      console.error('Failed to fetch staff compliance dashboard:', error);
      toast.error(error.response?.data?.detail || 'Failed to load compliance dashboard');
      setComplianceRows([]);
    } finally {
      setComplianceLoading(false);
    }
  };

  useEffect(() => {
    if (viewMode === 'staff') {
      fetchEmployees();
      fetchOnboardingStatuses();
    }
  }, [token, search, statusFilter, onboardingStatusFilter, showArchived, viewMode]);

  useEffect(() => {
    if (viewMode === 'compliance') {
      fetchComplianceDashboard();
    }
  }, [token, viewMode, complianceStatusFilter]);

  const handleArchiveEmployee = async () => {
    if (!selectedEmployee) return;
    
    try {
      await axios.post(`${API}/employees/${selectedEmployee.id}/archive`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success(`${selectedEmployee.first_name} ${selectedEmployee.last_name} has been archived`);
      setArchiveDialogOpen(false);
      setSelectedEmployee(null);
      fetchEmployees();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to archive employee');
    }
  };

  const handleRestoreEmployee = async (emp) => {
    try {
      await axios.post(`${API}/employees/${emp.id}/restore`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success(`${emp.first_name} ${emp.last_name} has been restored`);
      fetchEmployees();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to restore employee');
    }
  };

  const handlePermanentDelete = async () => {
    if (!selectedEmployee) return;
    
    try {
      await axios.delete(`${API}/employees/${selectedEmployee.id}/permanent`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success(`${selectedEmployee.first_name} ${selectedEmployee.last_name} has been permanently deleted`);
      setDeleteDialogOpen(false);
      setSelectedEmployee(null);
      fetchEmployees();
    } catch (error) {
      const detail = error.response?.data?.detail;
      if (detail && typeof detail === 'object') {
        toast.error(detail.message || JSON.stringify(detail));
      } else {
        toast.error(detail || 'Failed to delete employee');
      }
    }
  };

  const isSuperAdmin = () => user?.role === 'super_admin';
  const canPromoteEmployee = (emp) => {
    const readiness = emp?.canonical_readiness || {};
    const decision = emp?.latest_work_readiness_decision || null;
    const hasApproval = ['ready', 'ready_with_conditions'].includes(decision?.outcome);
    return !isAuditor() && emp?.status === 'onboarding' && readiness?.can_promote === true && hasApproval;
  };

  const getLifecycleStageLabel = (emp) => {
    const status = normalizeLifecycleStatus(emp?.status);
    if (isActiveLifecycleStatus(status)) return 'Active Workforce';
    if (status === 'inactive') return 'Inactive';
    if (status === 'onboarding') {
      return canPromoteEmployee(emp) ? 'Eligible to move to Active' : 'Onboarding';
    }
    return (status || 'Unknown').replace(/_/g, ' ');
  };

  const applyStagePreset = (preset) => {
    setStagePreset(preset);
    setShowArchived(false);
    setOnboardingStatusFilter('');
    setRequirementFilter('');

    if (preset === 'ALL') {
      setStatusFilter('');
      setWorkReadinessFilter('');
      return;
    }
    if (preset === 'ONBOARDING') {
      setStatusFilter('onboarding');
      setWorkReadinessFilter('');
      return;
    }
    if (preset === 'READY_TO_WORK') {
      setStatusFilter('onboarding');
      setWorkReadinessFilter('READY_TO_WORK');
      return;
    }
    if (preset === 'CAN_PROMOTE') {
      setStatusFilter('onboarding');
      setWorkReadinessFilter('CAN_PROMOTE');
      return;
    }
    if (preset === 'ACTIVE') {
      setStatusFilter('active');
      setWorkReadinessFilter('');
      return;
    }
    if (preset === 'INACTIVE') {
      setStatusFilter('inactive');
      setWorkReadinessFilter('');
    }
  };

  const handlePromoteToActive = async (emp) => {
    try {
      const response = await axios.post(`${API}/employees/${emp.id}/auto-promote`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (response.data?.promoted) {
        toast.success(`${emp.first_name} ${emp.last_name} promoted to active`);
      } else {
        toast.error(response.data?.message || 'Promotion is not currently allowed');
      }
      fetchEmployees();
    } catch (error) {
      const detail = error.response?.data?.detail;
      toast.error(typeof detail === 'string' ? detail : (detail?.message || 'Failed to promote employee'));
    }
  };

  const handleLifecycleStatusChange = async (emp, nextStatus, actionLabel) => {
    setLifecycleTargetEmployee(emp);
    setLifecycleNextStatus(nextStatus);
    setLifecycleActionLabel(actionLabel);
    setLifecycleReasonDialogOpen(true);
  };

  const submitLifecycleStatusChange = async (reason) => {
    if (!lifecycleTargetEmployee || !lifecycleNextStatus) return;
    setIsLifecycleSaving(true);
    try {
      await axios.put(
        `${API}/employees/${lifecycleTargetEmployee.id}`,
        { status: lifecycleNextStatus, status_change_reason: reason },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success(`${lifecycleTargetEmployee.first_name} ${lifecycleTargetEmployee.last_name} updated to ${lifecycleNextStatus}`);
      setLifecycleReasonDialogOpen(false);
      setLifecycleTargetEmployee(null);
      setLifecycleNextStatus('');
      setLifecycleActionLabel('');
      fetchEmployees();
    } catch (error) {
      const detail = error.response?.data?.detail;
      toast.error(typeof detail === 'string' ? detail : 'Failed to update lifecycle status');
    } finally {
      setIsLifecycleSaving(false);
    }
  };

  // Bulk request handlers
  const toggleEmployeeSelection = (empId) => {
    setSelectedEmployees(prev => 
      prev.includes(empId) 
        ? prev.filter(id => id !== empId)
        : [...prev, empId]
    );
  };

  const selectAllEmployees = () => {
    const currentlyFiltered = getFilteredEmployees();
    const allIds = currentlyFiltered.map(e => e.id);
    setSelectedEmployees(allIds);
  };

  const clearSelection = () => {
    setSelectedEmployees([]);
  };

  const fetchDocumentTypes = async () => {
    try {
      const response = await axios.get(`${API}/document-types`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setBulkRequirements(response.data.filter(dt => dt.required));
    } catch (error) {
      console.error('Failed to fetch document types:', error);
    }
  };

  const openBulkRequestDialog = () => {
    if (selectedEmployees.length === 0) {
      toast.error('Please select at least one employee');
      return;
    }
    fetchDocumentTypes();
    setBulkRequestOpen(true);
    setBulkResult(null);
  };

  const handleBulkRequest = async () => {
    setIsBulkRequesting(true);
    try {
      const payload = {
        employee_ids: selectedEmployees,
        requirement_ids: bulkRequestType === 'specific' ? selectedRequirements : null,
        message: bulkMessage || null,
        due_days: bulkDueDays,
        send_immediately: true
      };
      
      const response = await axios.post(`${API}/bulk/document-requests`, payload, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      setBulkResult(response.data);
      
      if (response.data.total_requests_created > 0) {
        toast.success(`Sent ${response.data.total_requests_created} document requests to ${response.data.total_employees} employees`);
      } else if (response.data.total_skipped > 0) {
        toast.info(`No new requests needed - ${response.data.total_skipped} employees already up to date`);
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to send bulk requests');
    } finally {
      setIsBulkRequesting(false);
    }
  };

  const closeBulkDialog = () => {
    setBulkRequestOpen(false);
    setBulkRequestType('missing');
    setSelectedRequirements([]);
    setBulkMessage('');
    setBulkDueDays(14);
    setBulkResult(null);
  };

  const exitBulkMode = () => {
    setBulkMode(false);
    setSelectedEmployees([]);
  };
  
  // Helper to get filtered employees list
  const getFilteredEmployees = () => {
    let filtered = workReadinessFilter 
      ? employees.filter(emp => matchesReadinessFilter(emp, workReadinessFilter))
      : employees;
    
    if (requirementFilter) {
      filtered = filtered.filter(emp => {
        const requirements = emp.compliance_requirements?.statuses?.requirements || [];
        if (requirementFilter === 'dbs') {
          return requirements.some(r => 
            r.name?.toLowerCase().includes('dbs') && 
            (r.status === 'missing' || r.status === 'pending' || r.status === 'expired')
          );
        } else if (requirementFilter === 'rtw') {
          return requirements.some(r => 
            (r.name?.toLowerCase().includes('right to work') || r.name?.toLowerCase().includes('rtw')) && 
            (r.status === 'missing' || r.status === 'pending' || r.status === 'expired')
          );
        } else if (requirementFilter === 'references') {
          return requirements.some(r => 
            r.name?.toLowerCase().includes('reference') && 
            (r.status === 'missing' || r.status === 'pending' || r.status === 'expired')
          );
        }
        return true;
      });
    }
    return filtered;
  };

  const handleAddEmployee = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    
    try {
      await axios.post(`${API}/employees`, newEmployee, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Employee added successfully');
      setIsAddOpen(false);
      setNewEmployee({
        first_name: '',
        last_name: '',
        email: '',
        phone: '',
        role: 'Care Assistant',
        onboarding_status: 'New',
        status: 'new'
      });
      fetchEmployees();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to add employee');
    } finally {
      setIsSubmitting(false);
    }
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

  return (
    <div className="space-y-6" data-testid="employees-page">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="font-heading text-2xl sm:text-3xl font-bold text-text-primary flex items-center gap-3">
            Staff
            <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200 text-xs font-normal">
              Recruited
            </Badge>
          </h1>
          <p className="text-text-muted mt-1">{employees.length} staff members with approved recruitment</p>
          <p className="text-xs text-text-muted/70 mt-0.5">
            Staff appear here after recruitment approval. Applicants are in the Recruitment Pipeline.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <Button
              type="button"
              size="sm"
              variant={viewMode === 'staff' ? 'default' : 'outline'}
              className="rounded-xl"
              onClick={() => setViewMode('staff')}
            >
              Staff List
            </Button>
            <Button
              type="button"
              size="sm"
              variant={viewMode === 'compliance' ? 'default' : 'outline'}
              className="rounded-xl"
              onClick={() => setViewMode('compliance')}
            >
              Compliance Dashboard
            </Button>
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          {/* Bulk Mode Toggle */}
          {!isAuditor() && (
            bulkMode ? (
              <div className="flex items-center gap-2 bg-primary/10 px-3 py-1.5 rounded-xl border border-primary/30">
                <span className="text-sm font-medium text-primary">
                  {selectedEmployees.length} selected
                </span>
                <Button 
                  size="sm" 
                  variant="ghost"
                  onClick={selectAllEmployees}
                  className="h-7 px-2 text-primary hover:bg-primary/20"
                  data-testid="select-all-btn"
                >
                  Select All
                </Button>
                <Button 
                  size="sm"
                  onClick={openBulkRequestDialog}
                  disabled={selectedEmployees.length === 0}
                  className="h-7 bg-primary hover:bg-primary-hover text-white"
                  data-testid="bulk-request-btn"
                >
                  <Mail className="h-3.5 w-3.5 mr-1.5" />
                  Request Documents
                </Button>
                <Button 
                  size="sm" 
                  variant="ghost"
                  onClick={exitBulkMode}
                  className="h-7 px-2 text-gray-500 hover:bg-gray-100"
                  data-testid="exit-bulk-mode-btn"
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            ) : (
              <Button 
                variant="outline" 
                onClick={() => setBulkMode(true)}
                className="rounded-xl"
                data-testid="enter-bulk-mode-btn"
              >
                <Mail className="mr-2 h-4 w-4" />
                Bulk Requests
              </Button>
            )
          )}
          
          {/* Link to Recruitment Pipeline */}
          <Button 
            variant="outline" 
            onClick={() => navigate('/portal/recruitment')}
            data-testid="recruitment-pipeline-btn"
          >
            <Users className="mr-2 h-4 w-4" />
            Recruitment Pipeline
          </Button>
          
          {!isAuditor() && (
          <Dialog open={isAddOpen} onOpenChange={setIsAddOpen}>
            <DialogTrigger asChild>
              <Button className="bg-primary hover:bg-primary-hover text-white rounded-xl" data-testid="add-employee-btn">
                <UserPlus className="mr-2 h-4 w-4" />
                Add Employee
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-lg">
              <DialogHeader>
                <DialogTitle className="font-heading">Add New Employee</DialogTitle>
              </DialogHeader>
              <form onSubmit={handleAddEmployee} className="space-y-4 mt-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="first_name">First name *</Label>
                    <Input
                      id="first_name"
                      value={newEmployee.first_name}
                      onChange={(e) => setNewEmployee({...newEmployee, first_name: e.target.value})}
                      required
                      className="rounded-xl"
                      data-testid="emp-firstname"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="last_name">Last name *</Label>
                    <Input
                      id="last_name"
                      value={newEmployee.last_name}
                      onChange={(e) => setNewEmployee({...newEmployee, last_name: e.target.value})}
                      required
                      className="rounded-xl"
                      data-testid="emp-lastname"
                    />
                  </div>
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="email">Email *</Label>
                  <Input
                    id="email"
                    type="email"
                    value={newEmployee.email}
                    onChange={(e) => setNewEmployee({...newEmployee, email: e.target.value})}
                    required
                    className="rounded-xl"
                    data-testid="emp-email"
                  />
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="phone">Phone</Label>
                  <Input
                    id="phone"
                    type="tel"
                    value={newEmployee.phone}
                    onChange={(e) => setNewEmployee({...newEmployee, phone: e.target.value})}
                    className="rounded-xl"
                    data-testid="emp-phone"
                  />
                </div>
                
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Role *</Label>
                    <Select value={newEmployee.role} onValueChange={(value) => setNewEmployee({...newEmployee, role: value})}>
                      <SelectTrigger className="rounded-xl" data-testid="emp-role">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {roles.map((role) => (
                          <SelectItem key={role} value={role}>{role}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>Onboarding Status</Label>
                    <Select 
                      value={newEmployee.onboarding_status} 
                      onValueChange={(value) => setNewEmployee({...newEmployee, onboarding_status: value})}
                    >
                      <SelectTrigger className="rounded-xl" data-testid="emp-onboarding-status">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {onboardingStatuses.map((status) => (
                          <SelectItem key={status} value={status}>{status}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                
                <div className="flex justify-end gap-3 pt-4">
                  <Button type="button" variant="outline" onClick={() => setIsAddOpen(false)} className="rounded-xl">
                    Cancel
                  </Button>
                  <Button type="submit" disabled={isSubmitting} className="bg-primary hover:bg-primary-hover text-white rounded-xl" data-testid="emp-submit">
                    {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Add Employee'}
                  </Button>
                </div>
              </form>
            </DialogContent>
          </Dialog>
          )}
        </div>
      </div>

      {viewMode === 'staff' ? (
      <>
      {/* Filters */}
      <Card className="border-[#E4E8EB] shadow-sm">
        <CardContent className="p-4">
          {/* Helper text */}
          <p className="text-sm text-text-muted mb-3">
            Filter employees by work status to quickly see who can start work.
          </p>
          <div className="mb-4 flex flex-wrap gap-2">
            {STAGE_PRESETS.map((preset) => (
              <Button
                key={preset.key}
                type="button"
                variant={stagePreset === preset.key ? 'default' : 'outline'}
                className="rounded-xl"
                onClick={() => applyStagePreset(preset.key)}
              >
                {preset.label}
              </Button>
            ))}
          </div>
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-muted" />
              <Input
                placeholder="Search by name, email or ID..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-10 rounded-xl border-[#E4E8EB]"
                data-testid="employees-search"
              />
            </div>
            {/* Work Status Filter - 3-tier model */}
            <Select value={workReadinessFilter || "all"} onValueChange={(v) => setWorkReadinessFilter(v === "all" ? "" : v)}>
              <SelectTrigger className="w-full sm:w-48 rounded-xl" data-testid="work-readiness-filter">
                <Shield className="h-4 w-4 mr-2" />
                <SelectValue placeholder="Work Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Work Status</SelectItem>
                <SelectItem value="READY_TO_WORK">
                  <span className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-success"></span>
                    Ready to Work
                  </span>
                </SelectItem>
                <SelectItem value="CAN_PROMOTE">
                  <span className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-warning"></span>
                    Eligible to Move to Active
                  </span>
                </SelectItem>
                <SelectItem value="NOT_READY">
                  <span className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-error"></span>
                    Not Ready
                  </span>
                </SelectItem>
              </SelectContent>
            </Select>
            <Select value={statusFilter || "all"} onValueChange={(v) => setStatusFilter(v === "all" ? "" : v)}>
              <SelectTrigger className="w-full sm:w-40 rounded-xl" data-testid="status-filter">
                <Filter className="h-4 w-4 mr-2" />
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Active</SelectItem>
                <SelectItem value="new">New</SelectItem>
                <SelectItem value="screening">Screening</SelectItem>
                <SelectItem value="interview">Interview</SelectItem>
                <SelectItem value="onboarding">Onboarding</SelectItem>
                <SelectItem value="active">Active</SelectItem>
                <SelectItem value="inactive">Inactive</SelectItem>
                <SelectItem value="archived">Archived</SelectItem>
              </SelectContent>
            </Select>
            {onboardingStatuses.length > 0 && (
              <Select value={onboardingStatusFilter || "all"} onValueChange={(v) => setOnboardingStatusFilter(v === "all" ? "" : v)}>
                <SelectTrigger className="w-full sm:w-48 rounded-xl" data-testid="onboarding-status-filter">
                  <SelectValue placeholder="Onboarding Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Onboarding</SelectItem>
                  {onboardingStatuses.map((status) => (
                    <SelectItem key={status} value={status}>{status}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Employees List */}
      <Card className="border-[#E4E8EB] shadow-sm">
        <CardContent className="p-0">
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
          ) : employees.length === 0 ? (
            <div className="text-center py-12 text-text-muted">
              <UserPlus className="h-12 w-12 mx-auto mb-3 opacity-50" />
              <p>No employees found</p>
              {search && <p className="text-sm mt-1">Try adjusting your search or filters</p>}
            </div>
          ) : (
            <div className="overflow-x-auto">
              {/* Filter employees by work readiness (3-tier) and requirement */}
              {(() => {
                let filteredEmployees = workReadinessFilter 
                  ? employees.filter(emp => matchesReadinessFilter(emp, workReadinessFilter))
                  : employees;
                
                // Additional filter by requirement type (DBS, RTW, References)
                if (requirementFilter) {
                  filteredEmployees = filteredEmployees.filter(emp => {
                    const requirements = emp.compliance_requirements?.statuses?.requirements || [];
                    if (requirementFilter === 'dbs') {
                      // Find DBS requirement that is not complete
                      return requirements.some(r => 
                        r.name?.toLowerCase().includes('dbs') && 
                        (r.status === 'missing' || r.status === 'pending' || r.status === 'expired')
                      );
                    } else if (requirementFilter === 'rtw') {
                      // Find Right to Work requirement that is not complete
                      return requirements.some(r => 
                        (r.name?.toLowerCase().includes('right to work') || r.name?.toLowerCase().includes('rtw')) && 
                        (r.status === 'missing' || r.status === 'pending' || r.status === 'expired')
                      );
                    } else if (requirementFilter === 'references') {
                      // Find References requirement that is not complete
                      return requirements.some(r => 
                        r.name?.toLowerCase().includes('reference') && 
                        (r.status === 'missing' || r.status === 'pending' || r.status === 'expired')
                      );
                    }
                    return true;
                  });
                }
                
                if (filteredEmployees.length === 0) {
                  return (
                    <div className="text-center py-12 text-text-muted">
                      <Shield className="h-12 w-12 mx-auto mb-3 opacity-50" />
                      <p>No employees match the current filter</p>
                      <p className="text-sm mt-1">Try selecting a different filter</p>
                      {(workReadinessFilter || requirementFilter) && (
                        <Button 
                          variant="outline" 
                          size="sm" 
                          className="mt-3 rounded-xl"
                          onClick={() => {
                            setWorkReadinessFilter('');
                            setRequirementFilter('');
                          }}
                        >
                          Clear Filters
                        </Button>
                      )}
                    </div>
                  );
                }
                
                return (
              <table className="w-full">
                <thead>
                  <tr className="border-b border-[#E4E8EB] bg-[#F8FAFA]">
                    {bulkMode && (
                      <th className="p-4 w-10">
                        <Checkbox
                          checked={selectedEmployees.length === filteredEmployees.length && filteredEmployees.length > 0}
                          onCheckedChange={(checked) => {
                            if (checked) {
                              setSelectedEmployees(filteredEmployees.map(e => e.id));
                            } else {
                              setSelectedEmployees([]);
                            }
                          }}
                          data-testid="select-all-checkbox"
                        />
                      </th>
                    )}
                    <th className="text-left p-4 font-medium text-text-muted text-sm">Employee</th>
                    <th className="text-left p-4 font-medium text-text-muted text-sm hidden md:table-cell">Role</th>
                    <th className="text-left p-4 font-medium text-text-muted text-sm">Work Status</th>
                    <th className="text-left p-4 font-medium text-text-muted text-sm hidden lg:table-cell">File Status</th>
                    <th className="text-left p-4 font-medium text-text-muted text-sm">Progress</th>
                    {!isAuditor() && <th className="text-left p-4 font-medium text-text-muted text-sm w-16">Actions</th>}
                  </tr>
                </thead>
                <tbody>
                  {filteredEmployees.map((emp) => {
                    const readiness = emp.canonical_readiness || {};
                    const status3tier = readiness.is_work_ready === true
                      ? 'READY_TO_WORK'
                      : readiness.can_promote === true
                        ? 'CAN_PROMOTE'
                        : 'NOT_READY';
                    const statusLabel = readiness.is_work_ready === true
                      ? 'Ready for Work'
                      : readiness.can_promote === true
                        ? 'Eligible to Move to Active'
                        : 'Not ready for work';
                    const statusColor = readiness.is_work_ready === true ? 'bg-success/10 text-success' :
                                      readiness.can_promote === true ? 'bg-warning/10 text-warning' :
                                      'bg-error/10 text-error';
                    const firstReason = readiness.blockers?.[0];
                    
                    return (
                    <tr 
                      key={emp.id} 
                      className={`border-b border-[#E4E8EB] hover:bg-[#F8FAFA] transition-colors ${emp.status === 'archived' ? 'opacity-60' : ''} ${selectedEmployees.includes(emp.id) ? 'bg-primary/5' : ''}`}
                    >
                      {bulkMode && (
                        <td className="p-4 w-10">
                          <Checkbox
                            checked={selectedEmployees.includes(emp.id)}
                            onCheckedChange={() => toggleEmployeeSelection(emp.id)}
                            data-testid={`select-emp-${emp.id}`}
                          />
                        </td>
                      )}
                      <td className="p-4">
                        <Link to={`/portal/employees/${emp.id}`} className="flex items-center gap-3" data-testid={`emp-link-${emp.id}`}>
                          <EmployeeAvatar
                            employeeId={emp.id}
                            firstName={emp.first_name}
                            lastName={emp.last_name}
                            hasPhoto={!!emp.profile_photo_url}
                            token={token}
                            size="md"
                            className={emp.status === 'archived' ? 'grayscale opacity-60' : ''}
                          />
                          <div>
                            <div className="flex items-center gap-2">
                              <p className="font-medium text-text-primary">{emp.first_name} {emp.last_name}</p>
                              <StageIdentityBadge 
                                stageIdentity={emp.person_stage || emp.stage_identity || 'employee'} 
                                size="sm" 
                                showIcon={false} 
                              />
                            </div>
                            <p className="text-sm text-text-muted">{emp.employee_code || emp.applicant_reference || '—'}</p>
                          </div>
                        </Link>
                      </td>
                      <td className="p-4 hidden md:table-cell">
                        <div>
                          <span className="text-text-primary">{emp.role}</span>
                          <p className="mt-1 text-xs text-text-muted">{getLifecycleStageLabel(emp)}</p>
                        </div>
                      </td>
                      <td className="p-4">
                        {/* Canonical Work Readiness Badge */}
                        <div 
                          className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${statusColor}`}
                          title={firstReason || statusLabel}
                          data-testid={`work-status-${emp.id}`}
                        >
                          {status3tier === 'READY_TO_WORK' ? (
                            <Shield className="h-3.5 w-3.5" />
                          ) : status3tier === 'CAN_PROMOTE' ? (
                            <AlertTriangle className="h-3.5 w-3.5" />
                          ) : (
                            <AlertTriangle className="h-3.5 w-3.5" />
                          )}
                          {statusLabel}
                        </div>
                        {/* Show first canonical blocker on separate line if not ready */}
                        {firstReason && status3tier !== 'READY_TO_WORK' && (
                          <p className={`text-[10px] mt-0.5 max-w-[150px] truncate ${status3tier === 'NOT_READY' ? 'text-red-600' : 'text-amber-600'}`} title={firstReason}>
                            {firstReason}
                          </p>
                        )}
                      </td>
                      <td className="p-4 hidden lg:table-cell">
                        {/* Recruitment File Status - Same info in condensed form */}
                        <span 
                          className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${statusColor}`}
                          title={firstReason || statusLabel}
                        >
                          {statusLabel}
                        </span>
                      </td>
                      <td className="p-4">
                        <div className="flex items-center gap-2">
                          <div className="w-20 h-2 bg-[#E4E8EB] rounded-full overflow-hidden">
                            <div 
                              className={`h-full rounded-full ${(readiness.overall_percentage ?? 0) >= 80 ? 'bg-success' : (readiness.overall_percentage ?? 0) >= 50 ? 'bg-warning' : 'bg-error'}`}
                              style={{ width: `${readiness.overall_percentage ?? 0}%` }}
                            ></div>
                          </div>
                          <span className="text-sm text-text-muted">{readiness.overall_percentage ?? 0}% Complete</span>
                          {/* Expiry Alert Indicator */}
                          {emp.expiry_alerts?.has_alerts && (
                            <span 
                              className={`ml-1 flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium ${
                                emp.expiry_alerts.expired_count > 0 
                                  ? 'bg-red-100 text-red-700' 
                                  : 'bg-amber-100 text-amber-700'
                              }`}
                              title={`${emp.expiry_alerts.expired_count} expired, ${emp.expiry_alerts.expiring_soon_count} expiring soon`}
                            >
                              <Clock className="h-3 w-3" />
                              {emp.expiry_alerts.expired_count > 0 
                                ? `${emp.expiry_alerts.expired_count} expired` 
                                : `${emp.expiry_alerts.expiring_soon_count} expiring`}
                            </span>
                          )}
                        </div>
                      </td>
                      {!isAuditor() && (
                        <td className="p-4">
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button variant="ghost" size="sm" className="h-8 w-8 p-0" data-testid={`emp-actions-${emp.id}`}>
                                <MoreHorizontal className="h-4 w-4" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end" className="w-48">
                              <DropdownMenuItem onClick={() => navigate(`/portal/employees/${emp.id}`)}>
                                <Edit className="h-4 w-4 mr-2" />
                                Edit Details
                              </DropdownMenuItem>
                              <DropdownMenuItem onClick={() => navigate(`/portal/employees/${emp.id}`)}>
                                <FileDown className="h-4 w-4 mr-2" />
                                Export File
                              </DropdownMenuItem>
                              {canPromoteEmployee(emp) && (
                                <>
                                  <DropdownMenuSeparator />
                                  <DropdownMenuItem onClick={() => handlePromoteToActive(emp)}>
                                    <CheckCircle className="h-4 w-4 mr-2" />
                                    Promote to Active
                                  </DropdownMenuItem>
                                </>
                              )}
                              {emp.status === 'active' && (
                                <DropdownMenuItem
                                  onClick={() => handleLifecycleStatusChange(emp, 'inactive', 'Deactivation')}
                                  className="text-amber-700"
                                >
                                  <Clock className="h-4 w-4 mr-2" />
                                  Set Inactive
                                </DropdownMenuItem>
                              )}
                              {emp.status === 'inactive' && (
                                <DropdownMenuItem
                                  onClick={() => handleLifecycleStatusChange(emp, 'onboarding', 'Reactivation')}
                                  className="text-blue-700"
                                >
                                  <RotateCcw className="h-4 w-4 mr-2" />
                                  Reactivate to Onboarding
                                </DropdownMenuItem>
                              )}
                              <DropdownMenuSeparator />
                              {emp.status === 'archived' ? (
                                <DropdownMenuItem onClick={() => handleRestoreEmployee(emp)}>
                                  <RotateCcw className="h-4 w-4 mr-2" />
                                  Restore Employee
                                </DropdownMenuItem>
                              ) : (
                                <DropdownMenuItem 
                                  onClick={() => {
                                    setSelectedEmployee(emp);
                                    setArchiveDialogOpen(true);
                                  }}
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
                                    onClick={() => {
                                      setSelectedEmployee(emp);
                                      setDeleteDialogOpen(true);
                                    }}
                                    className="text-error"
                                  >
                                    <Trash2 className="h-4 w-4 mr-2" />
                                    Delete Permanently
                                  </DropdownMenuItem>
                                </>
                              )}
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </td>
                      )}
                    </tr>
                    );
                  })}
                </tbody>
              </table>
                );
              })()}
            </div>
          )}
        </CardContent>
      </Card>
      </>
      ) : (
      <>
      <Card className="border-[#E4E8EB] shadow-sm">
        <CardContent className="p-4 flex flex-col sm:flex-row gap-3 sm:items-center sm:justify-between">
          <div>
            <p className="text-sm text-text-muted">
              Read-only compliance view for rapid triage. Use profile links to resolve issues.
            </p>
          </div>
          <Select
            value={complianceStatusFilter}
            onValueChange={(value) => setComplianceStatusFilter(value)}
          >
            <SelectTrigger className="w-full sm:w-48 rounded-xl" data-testid="compliance-status-filter">
              <Shield className="h-4 w-4 mr-2" />
              <SelectValue placeholder="Compliance Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All</SelectItem>
              <SelectItem value="compliant">Compliant</SelectItem>
              <SelectItem value="missing">Missing</SelectItem>
              <SelectItem value="expiring">Expiring Soon</SelectItem>
              <SelectItem value="expired">Expired</SelectItem>
            </SelectContent>
          </Select>
        </CardContent>
      </Card>

      <Card className="border-[#E4E8EB] shadow-sm">
        <CardContent className="p-0">
          {complianceLoading ? (
            <div className="flex items-center justify-center h-64">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
          ) : complianceRows.length === 0 ? (
            <div className="text-center py-12 text-text-muted">
              <Shield className="h-12 w-12 mx-auto mb-3 opacity-50" />
              <p>No staff match the selected compliance filter</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-[#E4E8EB] bg-[#F8FAFA]">
                    <th className="text-left p-4 font-medium text-text-muted text-sm">Employee</th>
                    <th className="text-left p-4 font-medium text-text-muted text-sm hidden md:table-cell">Role</th>
                    <th className="text-left p-4 font-medium text-text-muted text-sm">Status</th>
                    <th className="text-left p-4 font-medium text-text-muted text-sm hidden lg:table-cell">Checklist Summary</th>
                    <th className="text-left p-4 font-medium text-text-muted text-sm w-32">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {complianceRows.map((row) => {
                    const statusClass = row.overall_status === 'compliant'
                      ? 'status-success'
                      : row.overall_status === 'expired'
                        ? 'status-error'
                        : row.overall_status === 'expiring'
                          ? 'status-warning'
                          : 'status-error';
                    const statusLabel = row.overall_status === 'compliant'
                      ? 'Compliant'
                      : row.overall_status === 'expired'
                        ? 'Expired'
                        : row.overall_status === 'expiring'
                          ? 'Expiring soon'
                          : 'Missing items';
                    const summaryChips = [
                      ...(row.expired_items || []).slice(0, 2).map((item) => ({ label: item, tone: 'error' })),
                      ...(row.missing_items || []).slice(0, 2).map((item) => ({ label: item, tone: 'error' })),
                      ...(row.expiring_soon || []).slice(0, 2).map((item) => ({ label: item, tone: 'warning' })),
                    ];

                    return (
                      <tr key={row.employee_id} className="border-b border-[#E4E8EB] hover:bg-[#F8FAFA] transition-colors">
                        <td className="p-4">
                          <Link to={`/portal/employees/${row.employee_id}`} className="font-medium text-text-primary hover:underline">
                            {row.employee_name}
                          </Link>
                        </td>
                        <td className="p-4 hidden md:table-cell text-text-primary">{row.job_title || row.role || '—'}</td>
                        <td className="p-4">
                          <span className={`status-chip ${statusClass}`}>
                            {statusLabel}
                          </span>
                        </td>
                        <td className="p-4 hidden lg:table-cell">
                          <div className="flex flex-wrap gap-1">
                            {summaryChips.length > 0 ? summaryChips.map((chip, index) => (
                              <span
                                key={`${row.employee_id}-chip-${index}`}
                                className={`status-chip ${chip.tone === 'error' ? 'status-error' : 'status-warning'}`}
                              >
                                {chip.label}
                              </span>
                            )) : (
                              <span className="text-xs text-text-muted">No open checklist items</span>
                            )}
                          </div>
                        </td>
                        <td className="p-4">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => navigate(`/portal/employees/${row.employee_id}`)}
                            className="rounded-xl"
                          >
                            Open Profile
                          </Button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
      </>
      )}

      {/* Archive Confirmation Dialog */}
      <Dialog open={archiveDialogOpen} onOpenChange={setArchiveDialogOpen}>
        <DialogContent className="bg-white">
          <DialogHeader>
            <DialogTitle className="font-heading flex items-center gap-2 text-gray-900">
              <Archive className="h-5 w-5 text-amber-500" />
              Archive Employee
            </DialogTitle>
            <DialogDescription className="text-gray-500">
              Are you sure you want to archive <strong className="text-gray-900">{selectedEmployee?.first_name} {selectedEmployee?.last_name}</strong>?
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
              Are you sure you want to <strong className="text-gray-900">permanently delete</strong> {selectedEmployee?.first_name} {selectedEmployee?.last_name}?
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

      {/* Bulk Document Request Dialog */}
      <Dialog open={bulkRequestOpen} onOpenChange={(open) => !open && closeBulkDialog()}>
        <DialogContent className="bg-white sm:max-w-xl">
          <DialogHeader>
            <DialogTitle className="font-heading flex items-center gap-2">
              <Mail className="h-5 w-5 text-primary" />
              Bulk Document Requests
            </DialogTitle>
            <DialogDescription>
              Request documents from {selectedEmployees.length} selected employee{selectedEmployees.length !== 1 ? 's' : ''}.
            </DialogDescription>
          </DialogHeader>
          
          {bulkResult ? (
            // Show results after request is sent
            <div className="space-y-4 py-4">
              <div className="grid grid-cols-3 gap-4 text-center">
                <div className="p-3 bg-green-50 rounded-xl border border-green-200">
                  <p className="text-2xl font-bold text-green-700">{bulkResult.total_emails_sent}</p>
                  <p className="text-xs text-green-600">Emails Sent</p>
                </div>
                <div className="p-3 bg-blue-50 rounded-xl border border-blue-200">
                  <p className="text-2xl font-bold text-blue-700">{bulkResult.total_requests_created}</p>
                  <p className="text-xs text-blue-600">Requests Created</p>
                </div>
                <div className="p-3 bg-gray-50 rounded-xl border border-gray-200">
                  <p className="text-2xl font-bold text-gray-700">{bulkResult.total_skipped}</p>
                  <p className="text-xs text-gray-600">Skipped</p>
                </div>
              </div>
              
              {bulkResult.errors.length > 0 && (
                <div className="p-3 bg-red-50 rounded-xl border border-red-200">
                  <p className="text-sm font-medium text-red-700 mb-1">Errors:</p>
                  <ul className="text-xs text-red-600 list-disc list-inside">
                    {bulkResult.errors.slice(0, 5).map((err, i) => (
                      <li key={i}>{err}</li>
                    ))}
                    {bulkResult.errors.length > 5 && (
                      <li>...and {bulkResult.errors.length - 5} more</li>
                    )}
                  </ul>
                </div>
              )}
              
              <DialogFooter>
                <Button onClick={closeBulkDialog} className="bg-primary hover:bg-primary-hover text-white rounded-xl">
                  Done
                </Button>
              </DialogFooter>
            </div>
          ) : (
            // Show request form
            <div className="space-y-4 py-4">
              {/* Request Type Selection */}
              <div className="space-y-2">
                <Label className="font-medium">What to request</Label>
                <Select value={bulkRequestType} onValueChange={setBulkRequestType}>
                  <SelectTrigger className="rounded-xl" data-testid="bulk-request-type">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="missing">All missing documents (auto-detect)</SelectItem>
                    <SelectItem value="specific">Specific document types</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              
              {/* Specific Requirements Selection */}
              {bulkRequestType === 'specific' && (
                <div className="space-y-2">
                  <Label className="font-medium">Select document types</Label>
                  <div className="max-h-40 overflow-y-auto border rounded-xl p-2 space-y-1">
                    {bulkRequirements.length === 0 ? (
                      <p className="text-sm text-gray-500 p-2">Loading document types...</p>
                    ) : (
                      bulkRequirements.map(req => (
                        <label 
                          key={req.id} 
                          className="flex items-center gap-2 p-2 hover:bg-gray-50 rounded-lg cursor-pointer"
                        >
                          <Checkbox
                            checked={selectedRequirements.includes(req.id)}
                            onCheckedChange={(checked) => {
                              if (checked) {
                                setSelectedRequirements([...selectedRequirements, req.id]);
                              } else {
                                setSelectedRequirements(selectedRequirements.filter(id => id !== req.id));
                              }
                            }}
                          />
                          <span className="text-sm">{req.name}</span>
                        </label>
                      ))
                    )}
                  </div>
                </div>
              )}
              
              {/* Due Days */}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label className="font-medium">Due in (days)</Label>
                  <Select value={String(bulkDueDays)} onValueChange={(v) => setBulkDueDays(Number(v))}>
                    <SelectTrigger className="rounded-xl">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="7">7 days</SelectItem>
                      <SelectItem value="14">14 days</SelectItem>
                      <SelectItem value="21">21 days</SelectItem>
                      <SelectItem value="30">30 days</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              
              {/* Custom Message */}
              <div className="space-y-2">
                <Label className="font-medium">Custom message (optional)</Label>
                <Textarea
                  placeholder="Add a personal note to the request email..."
                  value={bulkMessage}
                  onChange={(e) => setBulkMessage(e.target.value)}
                  className="rounded-xl resize-none"
                  rows={3}
                  data-testid="bulk-message"
                />
              </div>
              
              <DialogFooter className="gap-2">
                <Button variant="outline" onClick={closeBulkDialog} className="rounded-xl">
                  Cancel
                </Button>
                <Button 
                  onClick={handleBulkRequest} 
                  disabled={isBulkRequesting || (bulkRequestType === 'specific' && selectedRequirements.length === 0)}
                  className="bg-primary hover:bg-primary-hover text-white rounded-xl"
                  data-testid="send-bulk-request-btn"
                >
                  {isBulkRequesting ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Sending...
                    </>
                  ) : (
                    <>
                      <Send className="h-4 w-4 mr-2" />
                      Send Requests
                    </>
                  )}
                </Button>
              </DialogFooter>
            </div>
          )}
        </DialogContent>
      </Dialog>

      <LifecycleReasonDialog
        open={lifecycleReasonDialogOpen}
        onOpenChange={(open) => {
          setLifecycleReasonDialogOpen(open);
          if (!open && !isLifecycleSaving) {
            setLifecycleTargetEmployee(null);
            setLifecycleNextStatus('');
            setLifecycleActionLabel('');
          }
        }}
        actionLabel={lifecycleActionLabel || 'Update lifecycle status'}
        subjectLabel={lifecycleTargetEmployee ? `${lifecycleTargetEmployee.first_name} ${lifecycleTargetEmployee.last_name}` : ''}
        minLength={5}
        isSubmitting={isLifecycleSaving}
        onConfirm={submitLifecycleStatusChange}
      />
    </div>
  );
}

