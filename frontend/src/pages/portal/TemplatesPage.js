import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Label } from '../../components/ui/label';
import { toast } from 'sonner';
import {
  ClipboardList, Search, Plus, FileText, CheckCircle, User, 
  AlertTriangle, Loader2, Eye, Settings, RefreshCw, Shield,
  Lock, FileCheck, ChevronRight
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function TemplatesPage() {
  const navigate = useNavigate();
  const { token, isAdmin } = useAuth();
  
  const [templates, setTemplates] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [generatedForms, setGeneratedForms] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isSeeding, setIsSeeding] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [generateDialogOpen, setGenerateDialogOpen] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [selectedEmployee, setSelectedEmployee] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);

  useEffect(() => {
    fetchData();
  }, [token]);

  const fetchData = async () => {
    try {
      const [templatesRes, employeesRes, formsRes] = await Promise.all([
        axios.get(`${API}/templates`, { headers: { Authorization: `Bearer ${token}` } }),
        axios.get(`${API}/employees`, { headers: { Authorization: `Bearer ${token}` } }),
        axios.get(`${API}/generated-forms`, { headers: { Authorization: `Bearer ${token}` } })
      ]);
      
      setTemplates(templatesRes.data);
      setEmployees(employeesRes.data);
      setGeneratedForms(formsRes.data);
    } catch (error) {
      console.error('Failed to fetch data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSeedTemplates = async () => {
    if (!isAdmin()) {
      toast.error('Admin access required');
      return;
    }
    
    setIsSeeding(true);
    try {
      const response = await axios.post(`${API}/seed-templates`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success(`${response.data.message} - Created: ${response.data.created}, Updated: ${response.data.updated}`);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to seed templates');
    } finally {
      setIsSeeding(false);
    }
  };

  const handleOpenGenerateDialog = (template) => {
    setSelectedTemplate(template);
    setSelectedEmployee('');
    setGenerateDialogOpen(true);
  };

  const handleGenerateForm = async () => {
    if (!selectedEmployee || !selectedTemplate) {
      toast.error('Please select an employee');
      return;
    }
    
    setIsGenerating(true);
    try {
      const response = await axios.post(
        `${API}/generated-forms`,
        { template_id: selectedTemplate.id, employee_id: selectedEmployee },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      toast.success('Form generated successfully');
      setGenerateDialogOpen(false);
      navigate(`/portal/forms/${response.data.id}`);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to generate form');
    } finally {
      setIsGenerating(false);
    }
  };

  // Filter templates
  const filteredTemplates = templates.filter(template => {
    const matchesSearch = template.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         template.description?.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory = categoryFilter === 'all' || template.category === categoryFilter;
    return matchesSearch && matchesCategory;
  });

  // Group by category
  const groupedTemplates = filteredTemplates.reduce((acc, template) => {
    if (!acc[template.category]) acc[template.category] = [];
    acc[template.category].push(template);
    return acc;
  }, {});

  const categories = [...new Set(templates.map(t => t.category))];

  // Calculate form counts per template
  const formCounts = templates.reduce((acc, template) => {
    acc[template.id] = generatedForms.filter(f => f.template_id === template.id).length;
    return acc;
  }, {});

  const pendingForms = generatedForms.filter(f => 
    ['draft', 'sent', 'in_progress', 'completed'].includes(f.status)
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="templates-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="font-heading text-2xl font-bold text-text-primary">Template Library</h1>
          <p className="text-text-muted">Compliance form templates for employee onboarding</p>
        </div>
        
        {isAdmin() && (
          <Button 
            onClick={handleSeedTemplates}
            disabled={isSeeding}
            className="bg-secondary hover:bg-secondary/90 text-white rounded-xl"
            data-testid="seed-templates-btn"
          >
            {isSeeding ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <RefreshCw className="h-4 w-4 mr-2" />}
            {templates.length === 0 ? 'Load Templates' : 'Update Templates'}
          </Button>
        )}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <Card className="border-[#E4E8EB] shadow-sm">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-primary/10 rounded-lg">
                <ClipboardList className="h-5 w-5 text-primary" />
              </div>
              <div>
                <p className="text-2xl font-bold text-text-primary">{templates.length}</p>
                <p className="text-xs text-text-muted">Templates</p>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card className="border-[#E4E8EB] shadow-sm">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-info/10 rounded-lg">
                <FileText className="h-5 w-5 text-info" />
              </div>
              <div>
                <p className="text-2xl font-bold text-text-primary">{generatedForms.length}</p>
                <p className="text-xs text-text-muted">Forms Generated</p>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card className="border-[#E4E8EB] shadow-sm">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-warning/10 rounded-lg">
                <AlertTriangle className="h-5 w-5 text-warning" />
              </div>
              <div>
                <p className="text-2xl font-bold text-text-primary">{pendingForms.length}</p>
                <p className="text-xs text-text-muted">Pending Review</p>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card className="border-[#E4E8EB] shadow-sm">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-success/10 rounded-lg">
                <CheckCircle className="h-5 w-5 text-success" />
              </div>
              <div>
                <p className="text-2xl font-bold text-text-primary">
                  {generatedForms.filter(f => f.status === 'signed_off').length}
                </p>
                <p className="text-xs text-text-muted">Signed Off</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-muted" />
          <Input
            placeholder="Search templates..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10 rounded-xl"
            data-testid="search-templates"
          />
        </div>
        <Select value={categoryFilter} onValueChange={setCategoryFilter}>
          <SelectTrigger className="w-48 rounded-xl" data-testid="category-filter">
            <SelectValue placeholder="All Categories" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Categories</SelectItem>
            {categories.map(cat => (
              <SelectItem key={cat} value={cat}>{cat}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Templates */}
      {templates.length === 0 ? (
        <Card className="border-[#E4E8EB] shadow-sm">
          <CardContent className="p-12 text-center">
            <ClipboardList className="h-16 w-16 mx-auto text-text-muted/50 mb-4" />
            <h2 className="font-heading text-xl font-semibold text-text-primary mb-2">
              No Templates Loaded
            </h2>
            <p className="text-text-muted mb-6">
              Load the compliance form templates to start generating forms for employees.
            </p>
            {isAdmin() && (
              <Button 
                onClick={handleSeedTemplates}
                disabled={isSeeding}
                className="bg-primary hover:bg-primary-hover text-white rounded-xl"
              >
                {isSeeding ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Plus className="h-4 w-4 mr-2" />}
                Load Templates
              </Button>
            )}
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-6">
          {Object.entries(groupedTemplates).map(([category, categoryTemplates]) => (
            <Card key={category} className="border-[#E4E8EB] shadow-sm">
              <CardHeader className="pb-3">
                <CardTitle className="font-heading text-lg flex items-center gap-2">
                  <span>{category}</span>
                  <span className="text-sm font-normal text-text-muted">
                    ({categoryTemplates.length} templates)
                  </span>
                </CardTitle>
              </CardHeader>
              <CardContent className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {categoryTemplates.map((template) => (
                  <div
                    key={template.id}
                    className="p-4 bg-[#F8FAFA] rounded-xl border border-[#E4E8EB] hover:border-primary/30 transition-colors group"
                    data-testid={`template-${template.id}`}
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <FileCheck className="h-5 w-5 text-primary" />
                        {template.visibility === 'restricted' && (
                          <Shield className="h-4 w-4 text-warning" title="Restricted" />
                        )}
                        {template.visibility === 'confidential' && (
                          <Lock className="h-4 w-4 text-error" title="Confidential" />
                        )}
                      </div>
                      <span className="text-xs text-text-muted">v{template.version}</span>
                    </div>
                    
                    <h3 className="font-medium text-text-primary mb-1 line-clamp-2">
                      {template.name}
                    </h3>
                    <p className="text-sm text-text-muted line-clamp-2 mb-3 min-h-[40px]">
                      {template.description}
                    </p>
                    
                    <div className="flex items-center justify-between text-xs text-text-muted mb-3">
                      <span>{formCounts[template.id] || 0} forms generated</span>
                      <div className="flex gap-1">
                        {template.requires_employee_signature && (
                          <span className="bg-accent px-2 py-0.5 rounded text-primary">Emp</span>
                        )}
                        {template.requires_admin_signature && (
                          <span className="bg-secondary/10 px-2 py-0.5 rounded text-secondary">Admin</span>
                        )}
                      </div>
                    </div>
                    
                    <Button 
                      variant="outline" 
                      size="sm"
                      className="w-full rounded-lg group-hover:bg-primary group-hover:text-white group-hover:border-primary transition-colors"
                      onClick={() => handleOpenGenerateDialog(template)}
                      data-testid={`generate-btn-${template.id}`}
                    >
                      <Plus className="h-4 w-4 mr-2" />
                      Generate Form
                    </Button>
                  </div>
                ))}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Recent Forms */}
      {generatedForms.length > 0 && (
        <Card className="border-[#E4E8EB] shadow-sm">
          <CardHeader>
            <CardTitle className="font-heading text-lg">Recent Forms</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {generatedForms.slice(0, 10).map((form) => {
                const statusColors = {
                  draft: 'bg-gray-100 text-text-muted',
                  sent: 'bg-info/10 text-info',
                  in_progress: 'bg-warning/10 text-warning',
                  completed: 'bg-info/10 text-info',
                  reviewed: 'bg-warning/10 text-warning',
                  signed_off: 'bg-success/10 text-success',
                  archived: 'bg-gray-100 text-text-muted'
                };
                
                return (
                  <div 
                    key={form.id}
                    onClick={() => navigate(`/portal/forms/${form.id}`)}
                    className="flex items-center justify-between p-3 rounded-xl hover:bg-[#F8FAFA] cursor-pointer transition-colors"
                    data-testid={`recent-form-${form.id}`}
                  >
                    <div className="flex items-center gap-3">
                      <FileText className="h-5 w-5 text-text-muted" />
                      <div>
                        <p className="font-medium text-text-primary text-sm">{form.template_name}</p>
                        <p className="text-xs text-text-muted">
                          {form.employee_name} • {form.employee_code}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${statusColors[form.status]}`}>
                        {form.status.replace('_', ' ')}
                      </span>
                      <ChevronRight className="h-4 w-4 text-text-muted" />
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Generate Form Dialog */}
      <Dialog open={generateDialogOpen} onOpenChange={setGenerateDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="font-heading">Generate Form</DialogTitle>
          </DialogHeader>
          
          {selectedTemplate && (
            <div className="space-y-4 mt-4">
              <div className="p-4 bg-[#F8FAFA] rounded-xl">
                <h3 className="font-medium text-text-primary">{selectedTemplate.name}</h3>
                <p className="text-sm text-text-muted mt-1">{selectedTemplate.description}</p>
              </div>
              
              <div className="space-y-2">
                <Label>Select Employee</Label>
                <Select value={selectedEmployee} onValueChange={setSelectedEmployee}>
                  <SelectTrigger className="rounded-xl" data-testid="employee-select">
                    <SelectValue placeholder="Choose an employee" />
                  </SelectTrigger>
                  <SelectContent>
                    {employees.map((emp) => (
                      <SelectItem key={emp.id} value={emp.id}>
                        <div className="flex items-center gap-2">
                          <User className="h-4 w-4 text-text-muted" />
                          <span>{emp.first_name} {emp.last_name}</span>
                          <span className="text-text-muted">({emp.employee_code})</span>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <p className="text-xs text-text-muted">
                  Employee details will be auto-filled into the form.
                </p>
              </div>
              
              <div className="flex justify-end gap-3 pt-4">
                <Button type="button" variant="outline" onClick={() => setGenerateDialogOpen(false)} className="rounded-xl">
                  Cancel
                </Button>
                <Button 
                  onClick={handleGenerateForm}
                  disabled={isGenerating || !selectedEmployee}
                  className="bg-primary hover:bg-primary-hover text-white rounded-xl"
                  data-testid="confirm-generate"
                >
                  {isGenerating ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Generate & Open'}
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
