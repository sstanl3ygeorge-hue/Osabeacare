import { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../../components/ui/dialog';
import { toast } from 'sonner';
import { FileCheck, Plus, Users, CheckCircle, Clock, Loader2 } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function PoliciesPage() {
  const [policies, setPolicies] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading] = useState(true);
  const [createOpen, setCreateOpen] = useState(false);
  const [assignOpen, setAssignOpen] = useState(false);
  const [selectedPolicy, setSelectedPolicy] = useState(null);
  const [selectedEmployees, setSelectedEmployees] = useState([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { token, isAuditor, isAdmin } = useAuth();

  const [newPolicy, setNewPolicy] = useState({
    title: '',
    version: '1.0',
    description: '',
    category: ''
  });

  const fetchData = async () => {
    try {
      const [policiesRes, employeesRes] = await Promise.all([
        axios.get(`${API}/policies`, { headers: { Authorization: `Bearer ${token}` } }),
        axios.get(`${API}/employees`, { headers: { Authorization: `Bearer ${token}` } })
      ]);
      setPolicies(policiesRes.data);
      setEmployees(employeesRes.data);
    } catch (error) {
      console.error('Failed to fetch data:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [token]);

  const handleCreatePolicy = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    
    try {
      await axios.post(`${API}/policies`, newPolicy, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Policy created successfully');
      setCreateOpen(false);
      setNewPolicy({ title: '', version: '1.0', description: '', category: '' });
      fetchData();
    } catch (error) {
      toast.error('Failed to create policy');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleAssignPolicy = async () => {
    if (!selectedPolicy || selectedEmployees.length === 0) {
      toast.error('Please select a policy and at least one employee');
      return;
    }
    
    setIsSubmitting(true);
    
    try {
      await axios.post(`${API}/policies/assign`, {
        policy_id: selectedPolicy.id,
        employee_ids: selectedEmployees
      }, { headers: { Authorization: `Bearer ${token}` } });
      
      toast.success(`Policy assigned to ${selectedEmployees.length} employees`);
      setAssignOpen(false);
      setSelectedPolicy(null);
      setSelectedEmployees([]);
      fetchData();
    } catch (error) {
      toast.error('Failed to assign policy');
    } finally {
      setIsSubmitting(false);
    }
  };

  const toggleEmployee = (empId) => {
    setSelectedEmployees(prev => 
      prev.includes(empId) 
        ? prev.filter(id => id !== empId)
        : [...prev, empId]
    );
  };

  const selectAllEmployees = () => {
    setSelectedEmployees(employees.map(e => e.id));
  };

  const totalAssigned = policies.reduce((sum, p) => sum + (p.assigned_count || 0), 0);
  const totalSigned = policies.reduce((sum, p) => sum + (p.signed_count || 0), 0);

  return (
    <div className="space-y-6" data-testid="policies-page">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="font-heading text-2xl sm:text-3xl font-bold text-text-primary">
            Policy Centre
          </h1>
          <p className="text-text-muted mt-1">Manage and assign policies to employees</p>
        </div>
        
        {isAdmin() && (
          <Dialog open={createOpen} onOpenChange={setCreateOpen}>
            <DialogTrigger asChild>
              <Button className="bg-primary hover:bg-primary-hover text-white rounded-xl" data-testid="create-policy-btn">
                <Plus className="mr-2 h-4 w-4" />
                Create Policy
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle className="font-heading">Create New Policy</DialogTitle>
              </DialogHeader>
              <form onSubmit={handleCreatePolicy} className="space-y-4 mt-4">
                <div className="space-y-2">
                  <Label htmlFor="title">Policy Title *</Label>
                  <Input
                    id="title"
                    value={newPolicy.title}
                    onChange={(e) => setNewPolicy({...newPolicy, title: e.target.value})}
                    required
                    className="rounded-xl"
                    data-testid="policy-title"
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="version">Version</Label>
                    <Input
                      id="version"
                      value={newPolicy.version}
                      onChange={(e) => setNewPolicy({...newPolicy, version: e.target.value})}
                      className="rounded-xl"
                      data-testid="policy-version"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="category">Category</Label>
                    <Input
                      id="category"
                      value={newPolicy.category}
                      onChange={(e) => setNewPolicy({...newPolicy, category: e.target.value})}
                      placeholder="e.g., Health & Safety"
                      className="rounded-xl"
                      data-testid="policy-category"
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="description">Description</Label>
                  <Textarea
                    id="description"
                    value={newPolicy.description}
                    onChange={(e) => setNewPolicy({...newPolicy, description: e.target.value})}
                    rows={3}
                    className="rounded-xl"
                    data-testid="policy-description"
                  />
                </div>
                <div className="flex justify-end gap-3 pt-4">
                  <Button type="button" variant="outline" onClick={() => setCreateOpen(false)} className="rounded-xl">
                    Cancel
                  </Button>
                  <Button type="submit" disabled={isSubmitting} className="bg-primary hover:bg-primary-hover text-white rounded-xl" data-testid="policy-submit">
                    {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Create Policy'}
                  </Button>
                </div>
              </form>
            </DialogContent>
          </Dialog>
        )}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        <Card className="border-[#E4E8EB] shadow-sm">
          <CardContent className="p-4 flex items-center gap-4">
            <div className="w-12 h-12 bg-primary/10 rounded-xl flex items-center justify-center">
              <FileCheck className="h-6 w-6 text-primary" />
            </div>
            <div>
              <p className="text-2xl font-heading font-bold text-text-primary">{policies.length}</p>
              <p className="text-sm text-text-muted">Total Policies</p>
            </div>
          </CardContent>
        </Card>
        <Card className="border-[#E4E8EB] shadow-sm">
          <CardContent className="p-4 flex items-center gap-4">
            <div className="w-12 h-12 bg-info/10 rounded-xl flex items-center justify-center">
              <Users className="h-6 w-6 text-info" />
            </div>
            <div>
              <p className="text-2xl font-heading font-bold text-text-primary">{totalAssigned}</p>
              <p className="text-sm text-text-muted">Assignments</p>
            </div>
          </CardContent>
        </Card>
        <Card className="border-[#E4E8EB] shadow-sm">
          <CardContent className="p-4 flex items-center gap-4">
            <div className="w-12 h-12 bg-success/10 rounded-xl flex items-center justify-center">
              <CheckCircle className="h-6 w-6 text-success" />
            </div>
            <div>
              <p className="text-2xl font-heading font-bold text-text-primary">{totalSigned}</p>
              <p className="text-sm text-text-muted">Acknowledged</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Policies List */}
      <Card className="border-[#E4E8EB] shadow-sm">
        <CardHeader>
          <CardTitle className="font-heading text-lg">Active Policies</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center h-32">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
          ) : policies.length === 0 ? (
            <div className="text-center py-12 text-text-muted">
              <FileCheck className="h-12 w-12 mx-auto mb-3 opacity-50" />
              <p>No policies created yet</p>
            </div>
          ) : (
            <div className="space-y-4">
              {policies.map((policy) => (
                <div key={policy.id} className="flex items-center justify-between p-4 bg-[#F8FAFA] rounded-xl">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 bg-white rounded-xl flex items-center justify-center border border-[#E4E8EB]">
                      <FileCheck className="h-6 w-6 text-primary" />
                    </div>
                    <div>
                      <p className="font-medium text-text-primary">{policy.title}</p>
                      <p className="text-sm text-text-muted">
                        Version {policy.version} · {policy.category || 'General'}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="text-right hidden sm:block">
                      <p className="text-sm font-medium text-text-primary">{policy.signed_count}/{policy.assigned_count}</p>
                      <p className="text-xs text-text-muted">Acknowledged</p>
                    </div>
                    {!isAuditor() && (
                      <Dialog open={assignOpen && selectedPolicy?.id === policy.id} onOpenChange={(open) => {
                        setAssignOpen(open);
                        if (open) setSelectedPolicy(policy);
                        else { setSelectedPolicy(null); setSelectedEmployees([]); }
                      }}>
                        <DialogTrigger asChild>
                          <Button variant="outline" size="sm" className="rounded-lg" data-testid={`assign-policy-${policy.id}`}>
                            Assign
                          </Button>
                        </DialogTrigger>
                        <DialogContent className="max-w-md">
                          <DialogHeader>
                            <DialogTitle className="font-heading">Assign Policy</DialogTitle>
                          </DialogHeader>
                          <div className="mt-4 space-y-4">
                            <div className="p-3 bg-[#F8FAFA] rounded-xl">
                              <p className="font-medium text-text-primary">{policy.title}</p>
                              <p className="text-sm text-text-muted">Version {policy.version}</p>
                            </div>
                            <div className="flex items-center justify-between">
                              <Label>Select Employees</Label>
                              <Button type="button" variant="ghost" size="sm" onClick={selectAllEmployees}>
                                Select All
                              </Button>
                            </div>
                            <div className="max-h-60 overflow-y-auto space-y-2 border border-[#E4E8EB] rounded-xl p-3">
                              {employees.map((emp) => (
                                <label key={emp.id} className="flex items-center gap-3 p-2 hover:bg-[#F8FAFA] rounded-lg cursor-pointer">
                                  <input
                                    type="checkbox"
                                    checked={selectedEmployees.includes(emp.id)}
                                    onChange={() => toggleEmployee(emp.id)}
                                    className="rounded border-[#E4E8EB]"
                                  />
                                  <span className="text-text-primary">{emp.first_name} {emp.last_name}</span>
                                </label>
                              ))}
                            </div>
                            <p className="text-sm text-text-muted">
                              {selectedEmployees.length} employee(s) selected
                            </p>
                            <div className="flex justify-end gap-3 pt-4">
                              <Button type="button" variant="outline" onClick={() => { setAssignOpen(false); setSelectedEmployees([]); }} className="rounded-xl">
                                Cancel
                              </Button>
                              <Button onClick={handleAssignPolicy} disabled={isSubmitting || selectedEmployees.length === 0} className="bg-primary hover:bg-primary-hover text-white rounded-xl" data-testid="assign-submit">
                                {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Assign Policy'}
                              </Button>
                            </div>
                          </div>
                        </DialogContent>
                      </Dialog>
                    )}
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
