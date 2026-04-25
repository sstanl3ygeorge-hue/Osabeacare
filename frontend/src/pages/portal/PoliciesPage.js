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
import { FileUploaderInline } from '../../components/ui/file-uploader';
import { 
  FileCheck, Plus, Users, CheckCircle, Clock, Loader2, 
  Upload, Eye, Shield, AlertTriangle, FileText
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function PoliciesPage() {
  const [policies, setPolicies] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [policyAssignments, setPolicyAssignments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [createOpen, setCreateOpen] = useState(false);
  const [assignOpen, setAssignOpen] = useState(false);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [selectedPolicy, setSelectedPolicy] = useState(null);
  const [selectedEmployees, setSelectedEmployees] = useState([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [uploadFile, setUploadFile] = useState(null);
  const { token, isAuditor, isAdmin } = useAuth();

  const [newPolicy, setNewPolicy] = useState({
    title: '',
    version: '1.0',
    description: '',
    category: ''
  });

  const fetchData = async () => {
    try {
      const [policiesRes, employeesRes, assignmentsRes] = await Promise.all([
        axios.get(`${API}/policies`, { headers: { Authorization: `Bearer ${token}` } }),
        axios.get(`${API}/staff/employees`, { headers: { Authorization: `Bearer ${token}` } }),
        axios.get(`${API}/policy-assignments`, { headers: { Authorization: `Bearer ${token}` } })
      ]);
      setPolicies(policiesRes.data);
      setEmployees(employeesRes.data.filter(e => e.status !== 'archived'));
      setPolicyAssignments(assignmentsRes.data);
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
      await fetchData();
    } catch (error) {
      toast.error('Failed to create policy');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleUploadPolicyFile = async (e) => {
    e.preventDefault();
    if (!selectedPolicy || !uploadFile) {
      toast.error('Please select a file');
      return;
    }
    
    setIsSubmitting(true);
    const formData = new FormData();
    formData.append('file', uploadFile);
    
    try {
      await axios.post(`${API}/policies/${selectedPolicy.id}/upload`, formData, {
        headers: { 
          Authorization: `Bearer ${token}`,
          'Content-Type': 'multipart/form-data'
        }
      });
      toast.success('Policy document uploaded successfully');
      setUploadOpen(false);
      setSelectedPolicy(null);
      setUploadFile(null);
      await fetchData();
    } catch (error) {
      toast.error('Failed to upload policy document');
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
      const response = await axios.post(`${API}/policies/assign`, {
        policy_id: selectedPolicy.id,
        employee_ids: selectedEmployees
      }, { headers: { Authorization: `Bearer ${token}` } });
      
      toast.success(response.data.message || `Policy assigned to ${selectedEmployees.length} employees`);
      setAssignOpen(false);
      setSelectedPolicy(null);
      setSelectedEmployees([]);
      await fetchData();
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
    // Only select employees not already assigned this policy
    const alreadyAssigned = policyAssignments
      .filter(a => a.policy_id === selectedPolicy?.id)
      .map(a => a.employee_id);
    const unassigned = employees.filter(e => !alreadyAssigned.includes(e.id)).map(e => e.id);
    setSelectedEmployees(unassigned);
  };

  const getAssignmentStats = (policyId) => {
    const assignments = policyAssignments.filter(a => a.policy_id === policyId);
    const total = assignments.length;
    const acknowledged = assignments.filter(a => a.status === 'acknowledged' || a.status === 'signed').length;
    const reviewed = assignments.filter(a => a.admin_reviewed).length;
    return { total, acknowledged, reviewed };
  };

  // Calculate totals
  const totalAssigned = policies.reduce((sum, p) => sum + (p.assigned_count || 0), 0);
  const totalAcknowledged = policies.reduce((sum, p) => sum + (p.signed_count || 0), 0);

  return (
    <div className="space-y-6" data-testid="policies-page">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="font-heading text-2xl sm:text-3xl font-bold text-text-primary">
            Policy Centre
          </h1>
          <p className="text-text-muted mt-1">Manage organisation policies and track employee acknowledgements</p>
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
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
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
            <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center">
              <Users className="h-6 w-6 text-blue-600" />
            </div>
            <div>
              <p className="text-2xl font-heading font-bold text-text-primary">{totalAssigned}</p>
              <p className="text-sm text-text-muted">Total Assignments</p>
            </div>
          </CardContent>
        </Card>
        <Card className="border-[#E4E8EB] shadow-sm">
          <CardContent className="p-4 flex items-center gap-4">
            <div className="w-12 h-12 bg-green-100 rounded-xl flex items-center justify-center">
              <CheckCircle className="h-6 w-6 text-green-600" />
            </div>
            <div>
              <p className="text-2xl font-heading font-bold text-text-primary">{totalAcknowledged}</p>
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
              {isAdmin() && <p className="text-sm mt-1">Click "Create Policy" to add your first policy</p>}
            </div>
          ) : (
            <div className="space-y-4">
              {policies.map((policy) => {
                const stats = getAssignmentStats(policy.id);
                const hasFile = !!policy.file_url;
                
                return (
                  <div key={policy.id} className={`p-4 rounded-xl border ${hasFile ? 'bg-[#F8FAFA] border-[#E4E8EB]' : 'bg-amber-50 border-amber-200'}`}>
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex items-start gap-4 flex-1">
                        <div className={`w-12 h-12 rounded-xl flex items-center justify-center border ${hasFile ? 'bg-white border-[#E4E8EB]' : 'bg-amber-100 border-amber-200'}`}>
                          {hasFile ? (
                            <FileCheck className="h-6 w-6 text-primary" />
                          ) : (
                            <AlertTriangle className="h-6 w-6 text-amber-600" />
                          )}
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <p className="font-semibold text-text-primary">{policy.title}</p>
                            <span className="text-xs px-2 py-0.5 bg-gray-200 rounded text-gray-600">
                              v{policy.version}
                            </span>
                            <span className="text-xs px-2 py-0.5 bg-blue-100 rounded text-blue-700">
                              {policy.category || 'General'}
                            </span>
                          </div>
                          {policy.description && (
                            <p className="text-sm text-text-muted mt-1">{policy.description}</p>
                          )}
                          {!hasFile && (
                            <p className="text-xs text-amber-700 mt-1 flex items-center gap-1">
                              <AlertTriangle className="w-3 h-3" />
                              No document uploaded - employees cannot view this policy
                            </p>
                          )}
                          
                          {/* Assignment Stats */}
                          <div className="flex items-center gap-4 mt-3 text-sm">
                            <span className="flex items-center gap-1 text-gray-600">
                              <Users className="w-4 h-4" />
                              {stats.total} assigned
                            </span>
                            <span className="flex items-center gap-1 text-green-600">
                              <CheckCircle className="w-4 h-4" />
                              {stats.acknowledged} acknowledged
                            </span>
                            {stats.reviewed > 0 && (
                              <span className="flex items-center gap-1 text-blue-600">
                                <Shield className="w-4 h-4" />
                                {stats.reviewed} reviewed
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                      
                      {/* Actions */}
                      <div className="flex items-center gap-2">
                        {/* View Policy */}
                        {hasFile && (
                          <Button
                            variant="outline"
                            size="sm"
                            className="rounded-lg"
                            onClick={async () => {
                              try {
                                const response = await axios.get(`${API}/policies/${policy.id}/file`, {
                                  headers: { Authorization: `Bearer ${token}` },
                                  responseType: 'blob'
                                });
                                const url = window.URL.createObjectURL(response.data);
                                window.open(url, '_blank');
                              } catch (error) {
                                toast.error('Failed to open policy document');
                              }
                            }}
                            data-testid={`view-policy-file-${policy.id}`}
                          >
                            <Eye className="w-4 h-4 mr-1" />
                            View
                          </Button>
                        )}
                        
                        {/* Upload Document */}
                        {isAdmin() && (
                          <Dialog open={uploadOpen && selectedPolicy?.id === policy.id} onOpenChange={(open) => {
                            setUploadOpen(open);
                            if (open) setSelectedPolicy(policy);
                            else { setSelectedPolicy(null); setUploadFile(null); }
                          }}>
                            <DialogTrigger asChild>
                              <Button variant="outline" size="sm" className="rounded-lg" data-testid={`upload-policy-${policy.id}`}>
                                <Upload className="w-4 h-4 mr-1" />
                                {hasFile ? 'Replace' : 'Upload'}
                              </Button>
                            </DialogTrigger>
                            <DialogContent>
                              <DialogHeader>
                                <DialogTitle className="font-heading">{hasFile ? 'Replace' : 'Upload'} Policy Document</DialogTitle>
                              </DialogHeader>
                              <form onSubmit={handleUploadPolicyFile} className="space-y-4 mt-4">
                                <div className="p-3 bg-[#F8FAFA] rounded-xl">
                                  <p className="font-medium text-text-primary">{policy.title}</p>
                                  <p className="text-sm text-text-muted">Version {policy.version}</p>
                                </div>
                                <div className="space-y-2">
                                  <Label htmlFor="policyFile">Policy Document (PDF recommended)</Label>
                                  <FileUploaderInline
                                    onFileSelect={(file) => setUploadFile(file)}
                                    selectedFile={uploadFile}
                                    onClear={() => setUploadFile(null)}
                                    acceptedTypes={['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']}
                                    placeholder="Drop policy document here or click to browse"
                                  />
                                </div>
                                <div className="flex justify-end gap-3 pt-4">
                                  <Button type="button" variant="outline" onClick={() => { setUploadOpen(false); setUploadFile(null); }} className="rounded-xl">
                                    Cancel
                                  </Button>
                                  <Button type="submit" disabled={isSubmitting || !uploadFile} className="bg-primary hover:bg-primary-hover text-white rounded-xl">
                                    {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Upload Document'}
                                  </Button>
                                </div>
                              </form>
                            </DialogContent>
                          </Dialog>
                        )}
                        
                        {/* Assign Policy - Only if document is uploaded */}
                        {!isAuditor() && hasFile && (
                          <Dialog open={assignOpen && selectedPolicy?.id === policy.id} onOpenChange={(open) => {
                            setAssignOpen(open);
                            if (open) setSelectedPolicy(policy);
                            else { setSelectedPolicy(null); setSelectedEmployees([]); }
                          }}>
                            <DialogTrigger asChild>
                              <Button className="bg-primary hover:bg-primary-hover text-white rounded-lg" size="sm" data-testid={`assign-policy-${policy.id}`}>
                                <Users className="w-4 h-4 mr-1" />
                                Assign
                              </Button>
                            </DialogTrigger>
                            <DialogContent className="max-w-md">
                              <DialogHeader>
                                <DialogTitle className="font-heading">Assign Policy to Employees</DialogTitle>
                              </DialogHeader>
                              <div className="mt-4 space-y-4">
                                <div className="p-3 bg-[#F8FAFA] rounded-xl">
                                  <p className="font-medium text-text-primary">{policy.title}</p>
                                  <p className="text-sm text-text-muted">Version {policy.version}</p>
                                </div>
                                <div className="flex items-center justify-between">
                                  <Label>Select Employees</Label>
                                  <Button type="button" variant="ghost" size="sm" onClick={selectAllEmployees}>
                                    Select All Unassigned
                                  </Button>
                                </div>
                                <div className="max-h-60 overflow-y-auto space-y-2 border border-[#E4E8EB] rounded-xl p-3">
                                  {employees.map((emp) => {
                                    const isAlreadyAssigned = policyAssignments.some(
                                      a => a.policy_id === policy.id && a.employee_id === emp.id
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
                                          onChange={() => !isAlreadyAssigned && toggleEmployee(emp.id)}
                                          disabled={isAlreadyAssigned}
                                          className="rounded border-[#E4E8EB]"
                                        />
                                        <span className="text-text-primary flex-1">
                                          {emp.first_name} {emp.last_name}
                                        </span>
                                        {isAlreadyAssigned && (
                                          <span className="text-xs text-green-600 bg-green-100 px-2 py-0.5 rounded">
                                            Already Assigned
                                          </span>
                                        )}
                                      </label>
                                    );
                                  })}
                                </div>
                                <p className="text-sm text-text-muted">
                                  {selectedEmployees.length} employee(s) selected
                                </p>
                                <div className="flex justify-end gap-3 pt-4">
                                  <Button type="button" variant="outline" onClick={() => { setAssignOpen(false); setSelectedEmployees([]); }} className="rounded-xl">
                                    Cancel
                                  </Button>
                                  <Button 
                                    onClick={handleAssignPolicy} 
                                    disabled={isSubmitting || selectedEmployees.length === 0} 
                                    className="bg-primary hover:bg-primary-hover text-white rounded-xl" 
                                    data-testid="assign-submit"
                                  >
                                    {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Assign Policy'}
                                  </Button>
                                </div>
                              </div>
                            </DialogContent>
                          </Dialog>
                        )}
                        
                        {/* Warning if no document - can't assign */}
                        {!isAuditor() && !hasFile && (
                          <span className="text-xs text-amber-600">Upload document to assign</span>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
