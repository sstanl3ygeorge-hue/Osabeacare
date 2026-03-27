import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../../components/ui/dialog';
import { Label } from '../../components/ui/label';
import { toast } from 'sonner';
import { Search, UserPlus, Filter, Loader2, ArrowUpDown } from 'lucide-react';

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
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [branchFilter, setBranchFilter] = useState('');
  const [branches, setBranches] = useState([]);
  const [isAddOpen, setIsAddOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { token, isAuditor } = useAuth();

  const [newEmployee, setNewEmployee] = useState({
    first_name: '',
    last_name: '',
    email: '',
    phone: '',
    role: 'Care Assistant',
    branch: '',
    status: 'new'
  });

  const fetchEmployees = async () => {
    try {
      const params = new URLSearchParams();
      if (search) params.append('search', search);
      if (statusFilter) params.append('status', statusFilter);
      if (branchFilter) params.append('branch', branchFilter);
      
      const response = await axios.get(`${API}/employees?${params}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setEmployees(response.data);
    } catch (error) {
      console.error('Failed to fetch employees:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchBranches = async () => {
    try {
      const response = await axios.get(`${API}/branches`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setBranches(response.data);
    } catch (error) {
      console.error('Failed to fetch branches:', error);
    }
  };

  useEffect(() => {
    fetchEmployees();
    fetchBranches();
  }, [token, search, statusFilter, branchFilter]);

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
        branch: '',
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
            Employees
          </h1>
          <p className="text-text-muted mt-1">{employees.length} total employees</p>
        </div>
        
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
                    <Label>Branch *</Label>
                    <Input
                      value={newEmployee.branch}
                      onChange={(e) => setNewEmployee({...newEmployee, branch: e.target.value})}
                      placeholder="e.g., London"
                      required
                      className="rounded-xl"
                      data-testid="emp-branch"
                    />
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

      {/* Filters */}
      <Card className="border-[#E4E8EB] shadow-sm">
        <CardContent className="p-4">
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
            <Select value={statusFilter || "all"} onValueChange={(v) => setStatusFilter(v === "all" ? "" : v)}>
              <SelectTrigger className="w-full sm:w-40 rounded-xl" data-testid="status-filter">
                <Filter className="h-4 w-4 mr-2" />
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="new">New</SelectItem>
                <SelectItem value="screening">Screening</SelectItem>
                <SelectItem value="interview">Interview</SelectItem>
                <SelectItem value="onboarding">Onboarding</SelectItem>
                <SelectItem value="active">Active</SelectItem>
                <SelectItem value="inactive">Inactive</SelectItem>
              </SelectContent>
            </Select>
            {branches.length > 0 && (
              <Select value={branchFilter || "all"} onValueChange={(v) => setBranchFilter(v === "all" ? "" : v)}>
                <SelectTrigger className="w-full sm:w-40 rounded-xl" data-testid="branch-filter">
                  <SelectValue placeholder="Branch" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Branches</SelectItem>
                  {branches.map((branch) => (
                    <SelectItem key={branch} value={branch}>{branch}</SelectItem>
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
              <table className="w-full">
                <thead>
                  <tr className="border-b border-[#E4E8EB] bg-[#F8FAFA]">
                    <th className="text-left p-4 font-medium text-text-muted text-sm">Employee</th>
                    <th className="text-left p-4 font-medium text-text-muted text-sm hidden md:table-cell">Role</th>
                    <th className="text-left p-4 font-medium text-text-muted text-sm hidden lg:table-cell">Branch</th>
                    <th className="text-left p-4 font-medium text-text-muted text-sm">Status</th>
                    <th className="text-left p-4 font-medium text-text-muted text-sm">Compliance</th>
                  </tr>
                </thead>
                <tbody>
                  {employees.map((emp) => (
                    <tr key={emp.id} className="border-b border-[#E4E8EB] hover:bg-[#F8FAFA] transition-colors">
                      <td className="p-4">
                        <Link to={`/portal/employees/${emp.id}`} className="flex items-center gap-3" data-testid={`emp-link-${emp.id}`}>
                          <div className="w-10 h-10 bg-accent rounded-xl flex items-center justify-center">
                            <span className="text-primary font-medium text-sm">
                              {emp.first_name?.charAt(0)}{emp.last_name?.charAt(0)}
                            </span>
                          </div>
                          <div>
                            <p className="font-medium text-text-primary">{emp.first_name} {emp.last_name}</p>
                            <p className="text-sm text-text-muted">{emp.employee_code}</p>
                          </div>
                        </Link>
                      </td>
                      <td className="p-4 hidden md:table-cell">
                        <span className="text-text-primary">{emp.role}</span>
                      </td>
                      <td className="p-4 hidden lg:table-cell">
                        <span className="text-text-muted">{emp.branch}</span>
                      </td>
                      <td className="p-4">
                        <span className={`status-chip ${statusColors[emp.status] || 'status-neutral'}`}>
                          {emp.status?.replace('_', ' ')}
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
                          <span className="text-sm text-text-muted">{emp.completion_percentage}%</span>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
