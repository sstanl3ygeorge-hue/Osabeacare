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
import { Search, UserPlus, Filter, Loader2, MoreHorizontal, Edit, Archive, Trash2, RotateCcw, FileDown, AlertTriangle, Shield, CheckCircle, Clock, Users } from 'lucide-react';
import EmployeeAvatar from '../../components/portal/EmployeeAvatar';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const statusColors = {
  new: 'status-info',
  screening: 'status-info',
  interview: 'status-info',
  compliance_review: 'status-warning',
  onboarding: 'status-info',
  active: 'status-success',
  inactive: 'status-neutral',
  archived: 'status-neutral'
};

export default function EmployeesPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // Initialize state from URL params for navigation state persistence
  const [search, setSearch] = useState(searchParams.get('q') || '');
  const [statusFilter, setStatusFilter] = useState(searchParams.get('status') || '');
  const [onboardingStatusFilter, setOnboardingStatusFilter] = useState(searchParams.get('onboarding') || '');
  const [workReadinessFilter, setWorkReadinessFilter] = useState(searchParams.get('work_readiness') || '');
  const [requirementFilter, setRequirementFilter] = useState(searchParams.get('requirement') || '');
  const [showArchived, setShowArchived] = useState(searchParams.get('archived') === 'true');
  const [onboardingStatuses, setOnboardingStatuses] = useState([]);
  const [isAddOpen, setIsAddOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [archiveDialogOpen, setArchiveDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [selectedEmployee, setSelectedEmployee] = useState(null);
  const { token, isAuditor, user } = useAuth();

  // Sync state to URL params for navigation preservation
  useEffect(() => {
    const newParams = new URLSearchParams();
    if (search) newParams.set('q', search);
    if (statusFilter) newParams.set('status', statusFilter);
    if (onboardingStatusFilter) newParams.set('onboarding', onboardingStatusFilter);
    if (workReadinessFilter) newParams.set('work_readiness', workReadinessFilter);
    if (requirementFilter) newParams.set('requirement', requirementFilter);
    if (showArchived) newParams.set('archived', 'true');
    
    // Only update URL if params changed (avoid infinite loop)
    const currentString = searchParams.toString();
    const newString = newParams.toString();
    if (currentString !== newString) {
      setSearchParams(newParams, { replace: true });
    }
  }, [search, statusFilter, onboardingStatusFilter, workReadinessFilter, requirementFilter, showArchived]);

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
      setEmployees(response.data);
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

  useEffect(() => {
    fetchEmployees();
    fetchOnboardingStatuses();
  }, [token, search, statusFilter, onboardingStatusFilter, showArchived]);

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
      toast.error(error.response?.data?.detail || 'Failed to delete employee');
    }
  };

  const isSuperAdmin = () => user?.role === 'super_admin';

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
          <h1 className="font-heading text-2xl sm:text-3xl font-bold text-text-primary">
            Staff
          </h1>
          <p className="text-text-muted mt-1">{employees.length} employees (recruited staff only)</p>
        </div>
        
        <div className="flex items-center gap-2">
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

      {/* Filters */}
      <Card className="border-[#E4E8EB] shadow-sm">
        <CardContent className="p-4">
          {/* Helper text */}
          <p className="text-sm text-text-muted mb-3">
            Filter employees by work status to quickly see who can start work.
          </p>
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
            {/* Work Status Filter */}
            <Select value={workReadinessFilter || "all"} onValueChange={(v) => setWorkReadinessFilter(v === "all" ? "" : v)}>
              <SelectTrigger className="w-full sm:w-48 rounded-xl" data-testid="work-readiness-filter">
                <Shield className="h-4 w-4 mr-2" />
                <SelectValue placeholder="Work Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Work Status</SelectItem>
                <SelectItem value="ready_to_work">
                  <span className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-success"></span>
                    Ready to Work
                  </span>
                </SelectItem>
                <SelectItem value="supervised_start">
                  <span className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-warning"></span>
                    Supervised Start
                  </span>
                </SelectItem>
                <SelectItem value="not_ready">
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
              {/* Filter employees by work readiness and requirement */}
              {(() => {
                let filteredEmployees = workReadinessFilter 
                  ? employees.filter(emp => {
                      const status = emp.work_readiness?.status;
                      if (workReadinessFilter === 'ready_to_work') {
                        return status === 'work_ready' || status === 'fully_compliant';
                      } else if (workReadinessFilter === 'supervised_start') {
                        return status === 'supervised_start' || status === 'almost_ready';
                      } else if (workReadinessFilter === 'not_ready') {
                        return status === 'not_started' || status === 'in_progress' || !status;
                      }
                      return true;
                    })
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
                    // Use work_readiness from API (single source of truth)
                    const workReadiness = emp.work_readiness || {};
                    // UI INTEGRITY: Show reason when Not Ready (never hide risk)
                    const workStatusLabel = workReadiness.reason 
                      ? `${workReadiness.label}: ${workReadiness.reason.replace('Missing: ', '')}`
                      : workReadiness.label || 'Unknown';
                    const workStatusColor = workReadiness.color === 'success' ? 'bg-success/10 text-success' :
                                           workReadiness.color === 'warning' ? 'bg-warning/10 text-warning' :
                                           'bg-error/10 text-error';
                    
                    return (
                    <tr key={emp.id} className={`border-b border-[#E4E8EB] hover:bg-[#F8FAFA] transition-colors ${emp.status === 'archived' ? 'opacity-60' : ''}`}>
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
                            <p className="font-medium text-text-primary">{emp.first_name} {emp.last_name}</p>
                            <p className="text-sm text-text-muted">{emp.employee_code}</p>
                          </div>
                        </Link>
                      </td>
                      <td className="p-4 hidden md:table-cell">
                        <span className="text-text-primary">{emp.role}</span>
                      </td>
                      <td className="p-4">
                        {/* Work Status Badge - Uses API work_readiness (single source of truth) */}
                        {/* UI INTEGRITY: Shows WHY someone is Not Ready */}
                        <div 
                          className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${workStatusColor}`}
                          title={workReadiness.reason || workReadiness.label}
                        >
                          {workReadiness.status === 'work_ready' || workReadiness.status === 'fully_compliant' ? (
                            <Shield className="h-3.5 w-3.5" />
                          ) : (
                            <AlertTriangle className="h-3.5 w-3.5" />
                          )}
                          {/* Show condensed label in table, full reason in tooltip */}
                          {workReadiness.label || 'Unknown'}
                        </div>
                        {/* Show reason on separate line if Not Ready */}
                        {workReadiness.reason && workReadiness.color === 'error' && (
                          <p className="text-[10px] text-red-600 mt-0.5 max-w-[150px] truncate" title={workReadiness.reason}>
                            {workReadiness.reason}
                          </p>
                        )}
                      </td>
                      <td className="p-4 hidden lg:table-cell">
                        {/* Recruitment File Status - Same info in condensed form */}
                        <span 
                          className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${workStatusColor}`}
                          title={workReadiness.reason || workReadiness.label}
                        >
                          {workReadiness.label || 'Unknown'}
                        </span>
                      </td>
                      <td className="p-4">
                        <div className="flex items-center gap-2">
                          <div className="w-20 h-2 bg-[#E4E8EB] rounded-full overflow-hidden">
                            <div 
                              className={`h-full rounded-full ${emp.completion_percentage >= 80 ? 'bg-success' : emp.completion_percentage >= 50 ? 'bg-warning' : 'bg-error'}`}
                              style={{ width: `${emp.completion_percentage}%` }}
                            ></div>
                          </div>
                          <span className="text-sm text-text-muted">{emp.completion_percentage}% Complete</span>
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
    </div>
  );
}
