import { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs';
import { Progress } from '../../components/ui/progress';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter, DialogDescription } from '../../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from '../../components/ui/dropdown-menu';
import { Label } from '../../components/ui/label';
import { Input } from '../../components/ui/input';
import { Checkbox } from '../../components/ui/checkbox';
import { Textarea } from '../../components/ui/textarea';
import { toast } from 'sonner';
import ComplianceOverview from '../../components/portal/ComplianceOverview';
import {
  ArrowLeft, Upload, FileText, Mail, Phone, MapPin, Calendar,
  CheckCircle, Clock, AlertTriangle, XCircle, Loader2, FileCheck,
  GraduationCap, ClipboardList, History, User, FolderUp, Eye, Shield,
  MoreHorizontal, Edit, Archive, Trash2, RotateCcw, FileDown, Save
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const statusIcons = {
  not_started: Clock,
  requested: Mail,
  uploaded: Upload,
  under_review: Clock,
  approved: CheckCircle,
  rejected: XCircle,
  expired: AlertTriangle,
  not_applicable: XCircle
};

const statusColors = {
  not_started: 'status-neutral',
  requested: 'status-info',
  uploaded: 'status-info',
  under_review: 'status-warning',
  approved: 'status-success',
  rejected: 'status-error',
  expired: 'status-error',
  not_applicable: 'status-neutral'
};

export default function EmployeeProfilePage() {
  const { employeeId } = useParams();
  const navigate = useNavigate();
  const [employee, setEmployee] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [documentTypes, setDocumentTypes] = useState([]);
  const [policies, setPolicies] = useState([]);
  const [training, setTraining] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [generatedForms, setGeneratedForms] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [bulkUploadOpen, setBulkUploadOpen] = useState(false);
  const [generateFormsOpen, setGenerateFormsOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [archiveDialogOpen, setArchiveDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [selectedDocType, setSelectedDocType] = useState('');
  const [uploadFile, setUploadFile] = useState(null);
  const [bulkFiles, setBulkFiles] = useState([]);
  const [bulkDocTypes, setBulkDocTypes] = useState({});
  const [selectedTemplates, setSelectedTemplates] = useState([]);
  const [isUploading, setIsUploading] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [editForm, setEditForm] = useState({});
  const { token, isAuditor, user } = useAuth();

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

  const statuses = [
    { value: 'new', label: 'New' },
    { value: 'screening', label: 'Screening' },
    { value: 'interview', label: 'Interview' },
    { value: 'compliance_review', label: 'Compliance Review' },
    { value: 'onboarding', label: 'Onboarding' },
    { value: 'active', label: 'Active' },
    { value: 'inactive', label: 'Inactive' }
  ];

  const isSuperAdmin = () => user?.role === 'super_admin';

  const fetchData = async () => {
    try {
      const [empRes, docsRes, typesRes, policiesRes, trainingRes, logsRes, formsRes, templatesRes] = await Promise.all([
        axios.get(`${API}/employees/${employeeId}`, { headers: { Authorization: `Bearer ${token}` } }),
        axios.get(`${API}/employee-documents?employee_id=${employeeId}`, { headers: { Authorization: `Bearer ${token}` } }),
        axios.get(`${API}/document-types`, { headers: { Authorization: `Bearer ${token}` } }),
        axios.get(`${API}/policy-assignments?employee_id=${employeeId}`, { headers: { Authorization: `Bearer ${token}` } }),
        axios.get(`${API}/training-records?employee_id=${employeeId}`, { headers: { Authorization: `Bearer ${token}` } }),
        axios.get(`${API}/audit-logs?entity_id=${employeeId}`, { headers: { Authorization: `Bearer ${token}` } }),
        axios.get(`${API}/generated-forms?employee_id=${employeeId}`, { headers: { Authorization: `Bearer ${token}` } }),
        axios.get(`${API}/templates`, { headers: { Authorization: `Bearer ${token}` } })
      ]);
      
      setEmployee(empRes.data);
      setDocuments(docsRes.data);
      setDocumentTypes(typesRes.data);
      setPolicies(policiesRes.data);
      setTraining(trainingRes.data);
      setAuditLogs(logsRes.data);
      setGeneratedForms(formsRes.data);
      setTemplates(templatesRes.data);
    } catch (error) {
      console.error('Failed to fetch employee data:', error);
      toast.error('Failed to load employee data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [employeeId, token]);

  const handleUploadDocument = async (e) => {
    e.preventDefault();
    if (!selectedDocType || !uploadFile) {
      toast.error('Please select a document type and file');
      return;
    }
    
    setIsUploading(true);
    
    try {
      // First, create the document record
      const createRes = await axios.post(`${API}/employee-documents`, {
        employee_id: employeeId,
        document_type_id: selectedDocType
      }, { headers: { Authorization: `Bearer ${token}` } });
      
      // Then upload the file
      const formData = new FormData();
      formData.append('file', uploadFile);
      
      await axios.post(`${API}/employee-documents/${createRes.data.id}/upload`, formData, {
        headers: { 
          Authorization: `Bearer ${token}`,
          'Content-Type': 'multipart/form-data'
        }
      });
      
      toast.success('Document uploaded successfully');
      setUploadDialogOpen(false);
      setSelectedDocType('');
      setUploadFile(null);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to upload document');
    } finally {
      setIsUploading(false);
    }
  };

  const handleUpdateDocumentStatus = async (docId, status) => {
    try {
      await axios.put(`${API}/employee-documents/${docId}`, { status }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success(`Document ${status}`);
      fetchData();
    } catch (error) {
      toast.error('Failed to update document');
    }
  };

  const handleBulkUpload = async () => {
    if (bulkFiles.length === 0) {
      toast.error('Please select files to upload');
      return;
    }
    
    // Check all files have doc type assigned
    const missingTypes = bulkFiles.filter((_, i) => !bulkDocTypes[i]);
    if (missingTypes.length > 0) {
      toast.error('Please assign document types to all files');
      return;
    }
    
    setIsUploading(true);
    
    try {
      const formData = new FormData();
      bulkFiles.forEach((file) => formData.append('files', file));
      const typeIds = bulkFiles.map((_, i) => bulkDocTypes[i]).join(',');
      
      const response = await axios.post(
        `${API}/employees/${employeeId}/bulk-upload?document_type_ids=${typeIds}`,
        formData,
        { 
          headers: { 
            Authorization: `Bearer ${token}`,
            'Content-Type': 'multipart/form-data'
          }
        }
      );
      
      toast.success(`Uploaded ${response.data.successful} documents`);
      if (response.data.errors?.length > 0) {
        response.data.errors.forEach(err => toast.error(err));
      }
      
      setBulkUploadOpen(false);
      setBulkFiles([]);
      setBulkDocTypes({});
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to upload documents');
    } finally {
      setIsUploading(false);
    }
  };

  const handleGenerateForms = async () => {
    if (selectedTemplates.length === 0) {
      toast.error('Please select at least one template');
      return;
    }
    
    setIsGenerating(true);
    
    try {
      const response = await axios.post(
        `${API}/generated-forms/bulk`,
        null,
        {
          headers: { Authorization: `Bearer ${token}` },
          params: {
            employee_id: employeeId,
            template_ids: selectedTemplates
          },
          paramsSerializer: params => {
            return Object.keys(params).map(key => {
              if (Array.isArray(params[key])) {
                return params[key].map(v => `${key}=${v}`).join('&');
              }
              return `${key}=${params[key]}`;
            }).join('&');
          }
        }
      );
      
      toast.success(`Generated ${response.data.created} forms`);
      if (response.data.errors?.length > 0) {
        response.data.errors.forEach(err => toast.warning(err));
      }
      
      setGenerateFormsOpen(false);
      setSelectedTemplates([]);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to generate forms');
    } finally {
      setIsGenerating(false);
    }
  };

  const toggleTemplateSelection = (templateId) => {
    setSelectedTemplates(prev => 
      prev.includes(templateId)
        ? prev.filter(id => id !== templateId)
        : [...prev, templateId]
    );
  };

  const openEditDialog = () => {
    setEditForm({
      first_name: employee?.first_name || '',
      last_name: employee?.last_name || '',
      email: employee?.email || '',
      phone: employee?.phone || '',
      role: employee?.role || '',
      status: employee?.status || '',
      assignment: employee?.assignment || 'Unassigned',
      start_date: employee?.start_date || '',
      notes: employee?.notes || ''
    });
    setEditDialogOpen(true);
  };

  const handleSaveEmployee = async () => {
    setIsSaving(true);
    try {
      await axios.put(`${API}/employees/${employeeId}`, editForm, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Employee details updated');
      setEditDialogOpen(false);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update employee');
    } finally {
      setIsSaving(false);
    }
  };

  const handleArchiveEmployee = async () => {
    try {
      await axios.post(`${API}/employees/${employeeId}/archive`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Employee archived successfully');
      setArchiveDialogOpen(false);
      navigate('/portal/employees');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to archive employee');
    }
  };

  const handleRestoreEmployee = async () => {
    try {
      await axios.post(`${API}/employees/${employeeId}/restore`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Employee restored successfully');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to restore employee');
    }
  };

  const handlePermanentDelete = async () => {
    try {
      await axios.delete(`${API}/employees/${employeeId}/permanent`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Employee permanently deleted');
      setDeleteDialogOpen(false);
      navigate('/portal/employees');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete employee');
    }
  };

  const groupedTemplates = templates.reduce((acc, template) => {
    if (!acc[template.category]) acc[template.category] = [];
    acc[template.category].push(template);
    return acc;
  }, {});

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!employee) {
    return (
      <div className="text-center py-12">
        <p className="text-text-muted">Employee not found</p>
        <Link to="/portal/employees">
          <Button className="mt-4">Back to Employees</Button>
        </Link>
      </div>
    );
  }

  const groupedDocs = documentTypes.reduce((acc, type) => {
    if (!acc[type.category]) acc[type.category] = [];
    const doc = documents.find(d => d.document_type_id === type.id);
    acc[type.category].push({ ...type, document: doc });
    return acc;
  }, {});

  return (
    <div className="space-y-6" data-testid="employee-profile">
      {/* Back Link */}
      <Link to="/portal/employees" className="inline-flex items-center gap-2 text-text-muted hover:text-primary transition-colors" data-testid="back-link">
        <ArrowLeft className="h-4 w-4" />
        Back to Employees
      </Link>

      {/* Header Card */}
      <Card className="border-[#E4E8EB] shadow-sm">
        <CardContent className="p-6">
          <div className="flex flex-col lg:flex-row lg:items-start gap-6">
            <div className="flex items-start gap-4 flex-1">
              <div className="w-16 h-16 bg-accent rounded-2xl flex items-center justify-center">
                <span className="text-primary font-heading font-bold text-xl">
                  {employee.first_name?.charAt(0)}{employee.last_name?.charAt(0)}
                </span>
              </div>
              <div>
                <h1 className="font-heading text-2xl font-bold text-text-primary">
                  {employee.first_name} {employee.last_name}
                </h1>
                <p className="text-text-muted">{employee.employee_code} · {employee.role}</p>
                <span className={`status-chip mt-2 ${
                  employee.status === 'active' ? 'status-success' :
                  employee.status === 'onboarding' ? 'status-info' :
                  'status-neutral'
                }`}>
                  {employee.status?.replace('_', ' ')}
                </span>
              </div>
            </div>

            <div className="flex flex-col items-end gap-4">
              <div className="flex items-center gap-3">
                <div className="text-right">
                  <p className="text-sm text-text-muted">Compliance Score</p>
                  <p className="text-3xl font-heading font-bold text-text-primary">{employee.completion_percentage}%</p>
                </div>
                {!isAuditor() && (
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="outline" size="sm" className="h-10 w-10 p-0 rounded-xl" data-testid="employee-actions-btn">
                        <MoreHorizontal className="h-5 w-5" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end" className="w-52">
                      <DropdownMenuItem onClick={openEditDialog}>
                        <Edit className="h-4 w-4 mr-2" />
                        Edit Details
                      </DropdownMenuItem>
                      <DropdownMenuItem>
                        <FileDown className="h-4 w-4 mr-2" />
                        Export Employee File
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                      {employee.status === 'archived' ? (
                        <DropdownMenuItem onClick={handleRestoreEmployee}>
                          <RotateCcw className="h-4 w-4 mr-2" />
                          Restore Employee
                        </DropdownMenuItem>
                      ) : (
                        <DropdownMenuItem 
                          onClick={() => setArchiveDialogOpen(true)}
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
                            onClick={() => setDeleteDialogOpen(true)}
                            className="text-error"
                          >
                            <Trash2 className="h-4 w-4 mr-2" />
                            Delete Permanently
                          </DropdownMenuItem>
                        </>
                      )}
                    </DropdownMenuContent>
                  </DropdownMenu>
                )}
              </div>
              <Progress value={employee.completion_percentage} className="w-32 h-2" />
            </div>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 mt-6 pt-6 border-t border-[#E4E8EB]">
            <div className="flex items-center gap-3">
              <Mail className="h-5 w-5 text-text-muted" />
              <span className="text-sm text-text-primary">{employee.email}</span>
            </div>
            {employee.phone && (
              <div className="flex items-center gap-3">
                <Phone className="h-5 w-5 text-text-muted" />
                <span className="text-sm text-text-primary">{employee.phone}</span>
              </div>
            )}
            <div className="flex items-center gap-3">
              <MapPin className="h-5 w-5 text-text-muted" />
              <span className="text-sm text-text-primary">{employee.assignment || 'Unassigned'}</span>
            </div>
            {employee.start_date && (
              <div className="flex items-center gap-3">
                <Calendar className="h-5 w-5 text-text-muted" />
                <span className="text-sm text-text-primary">Started: {employee.start_date}</span>
              </div>
            )}
          </div>

          {!isAuditor() && (
            <div className="flex flex-wrap gap-3 mt-6">
              <Dialog open={uploadDialogOpen} onOpenChange={setUploadDialogOpen}>
                <DialogTrigger asChild>
                  <Button className="bg-primary hover:bg-primary-hover text-white rounded-xl" data-testid="upload-doc-btn">
                    <Upload className="mr-2 h-4 w-4" />
                    Upload Document
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle className="font-heading">Upload Document</DialogTitle>
                  </DialogHeader>
                  <form onSubmit={handleUploadDocument} className="space-y-4 mt-4">
                    <div className="space-y-2">
                      <Label>Document Type</Label>
                      <Select value={selectedDocType} onValueChange={setSelectedDocType}>
                        <SelectTrigger className="rounded-xl" data-testid="doc-type-select">
                          <SelectValue placeholder="Select document type" />
                        </SelectTrigger>
                        <SelectContent>
                          {documentTypes.map((type) => (
                            <SelectItem key={type.id} value={type.id}>
                              {type.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label>File</Label>
                      <Input
                        type="file"
                        onChange={(e) => setUploadFile(e.target.files[0])}
                        className="rounded-xl"
                        data-testid="doc-file-input"
                      />
                      <p className="text-xs text-text-muted">
                        Upload a clear copy of the document.
                      </p>
                    </div>
                    <div className="flex justify-end gap-3 pt-4">
                      <Button type="button" variant="outline" onClick={() => setUploadDialogOpen(false)} className="rounded-xl">
                        Cancel
                      </Button>
                      <Button type="submit" disabled={isUploading} className="bg-primary hover:bg-primary-hover text-white rounded-xl" data-testid="upload-submit">
                        {isUploading ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Upload'}
                      </Button>
                    </div>
                  </form>
                </DialogContent>
              </Dialog>

              {/* Bulk Upload Dialog */}
              <Dialog open={bulkUploadOpen} onOpenChange={setBulkUploadOpen}>
                <DialogTrigger asChild>
                  <Button variant="outline" className="rounded-xl" data-testid="bulk-upload-btn">
                    <FolderUp className="mr-2 h-4 w-4" />
                    Bulk Upload
                  </Button>
                </DialogTrigger>
                <DialogContent className="max-w-2xl">
                  <DialogHeader>
                    <DialogTitle className="font-heading">Bulk Document Upload</DialogTitle>
                  </DialogHeader>
                  <div className="space-y-4 mt-4">
                    <div className="space-y-2">
                      <Label>Select Files</Label>
                      <Input
                        type="file"
                        multiple
                        onChange={(e) => {
                          setBulkFiles(Array.from(e.target.files));
                          setBulkDocTypes({});
                        }}
                        className="rounded-xl"
                        data-testid="bulk-file-input"
                      />
                    </div>
                    
                    {bulkFiles.length > 0 && (
                      <div className="space-y-3 max-h-64 overflow-y-auto">
                        <p className="text-sm text-text-muted">{bulkFiles.length} files selected. Assign document types:</p>
                        {bulkFiles.map((file, index) => (
                          <div key={index} className="flex items-center gap-3 p-3 bg-[#F8FAFA] rounded-xl">
                            <FileText className="h-5 w-5 text-text-muted flex-shrink-0" />
                            <span className="text-sm text-text-primary flex-1 truncate">{file.name}</span>
                            <Select 
                              value={bulkDocTypes[index] || ''} 
                              onValueChange={(v) => setBulkDocTypes(prev => ({...prev, [index]: v}))}
                            >
                              <SelectTrigger className="w-48 rounded-lg text-sm">
                                <SelectValue placeholder="Select type" />
                              </SelectTrigger>
                              <SelectContent>
                                {documentTypes.map((type) => (
                                  <SelectItem key={type.id} value={type.id}>
                                    {type.name}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          </div>
                        ))}
                      </div>
                    )}
                    
                    <div className="flex justify-end gap-3 pt-4">
                      <Button type="button" variant="outline" onClick={() => setBulkUploadOpen(false)} className="rounded-xl">
                        Cancel
                      </Button>
                      <Button 
                        onClick={handleBulkUpload} 
                        disabled={isUploading || bulkFiles.length === 0}
                        className="bg-primary hover:bg-primary-hover text-white rounded-xl"
                        data-testid="bulk-upload-submit"
                      >
                        {isUploading ? <Loader2 className="h-4 w-4 animate-spin" /> : `Upload ${bulkFiles.length} Files`}
                      </Button>
                    </div>
                  </div>
                </DialogContent>
              </Dialog>

              {/* Generate Forms Dialog */}
              <Dialog open={generateFormsOpen} onOpenChange={setGenerateFormsOpen}>
                <DialogTrigger asChild>
                  <Button variant="outline" className="rounded-xl" data-testid="generate-forms-btn">
                    <ClipboardList className="mr-2 h-4 w-4" />
                    Generate Forms
                  </Button>
                </DialogTrigger>
                <DialogContent className="max-w-2xl max-h-[80vh] overflow-hidden flex flex-col">
                  <DialogHeader>
                    <DialogTitle className="font-heading">Generate Compliance Forms</DialogTitle>
                  </DialogHeader>
                  <div className="space-y-4 mt-4 overflow-y-auto flex-1 pr-2">
                    <p className="text-sm text-text-muted">
                      Select templates to generate for <strong>{employee?.first_name} {employee?.last_name}</strong>. 
                      Employee details will be auto-filled.
                    </p>
                    
                    {templates.length === 0 ? (
                      <div className="text-center py-8 text-text-muted">
                        <ClipboardList className="h-10 w-10 mx-auto mb-2 opacity-50" />
                        <p>No templates available. Load templates first.</p>
                      </div>
                    ) : (
                      <div className="space-y-4">
                        {Object.entries(groupedTemplates).map(([category, categoryTemplates]) => (
                          <div key={category} className="space-y-2">
                            <h4 className="font-medium text-text-primary text-sm">{category}</h4>
                            <div className="space-y-2">
                              {categoryTemplates.map((template) => {
                                const existingForm = generatedForms.find(
                                  f => f.template_id === template.id && !['archived', 'signed_off'].includes(f.status)
                                );
                                const isSelected = selectedTemplates.includes(template.id);
                                
                                return (
                                  <div 
                                    key={template.id}
                                    className={`flex items-start gap-3 p-3 rounded-xl border transition-colors ${
                                      existingForm 
                                        ? 'bg-gray-50 border-gray-200 opacity-60' 
                                        : isSelected 
                                          ? 'bg-primary/5 border-primary' 
                                          : 'bg-[#F8FAFA] border-[#E4E8EB] hover:border-primary/30'
                                    }`}
                                  >
                                    <Checkbox
                                      id={template.id}
                                      checked={isSelected}
                                      disabled={!!existingForm}
                                      onCheckedChange={() => toggleTemplateSelection(template.id)}
                                    />
                                    <div className="flex-1 min-w-0">
                                      <label 
                                        htmlFor={template.id}
                                        className={`text-sm font-medium cursor-pointer ${existingForm ? 'text-text-muted' : 'text-text-primary'}`}
                                      >
                                        {template.name}
                                      </label>
                                      {template.description && (
                                        <p className="text-xs text-text-muted mt-0.5 line-clamp-1">{template.description}</p>
                                      )}
                                      {existingForm && (
                                        <div className="flex items-center gap-2 mt-1">
                                          <span className="text-xs text-warning">Form exists ({existingForm.status})</span>
                                          <Button
                                            size="sm"
                                            variant="ghost"
                                            className="h-6 px-2 text-xs"
                                            onClick={() => navigate(`/portal/forms/${existingForm.id}`)}
                                          >
                                            <Eye className="h-3 w-3 mr-1" />
                                            View
                                          </Button>
                                        </div>
                                      )}
                                    </div>
                                    <div className="flex gap-1">
                                      {template.requires_employee_signature && (
                                        <span className="text-xs bg-accent text-primary px-2 py-0.5 rounded">Emp Sign</span>
                                      )}
                                      {template.requires_admin_signature && (
                                        <span className="text-xs bg-secondary/10 text-secondary px-2 py-0.5 rounded">Admin Sign</span>
                                      )}
                                    </div>
                                  </div>
                                );
                              })}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                  
                  <div className="flex justify-between items-center gap-3 pt-4 border-t border-[#E4E8EB] mt-4">
                    <span className="text-sm text-text-muted">
                      {selectedTemplates.length} template{selectedTemplates.length !== 1 ? 's' : ''} selected
                    </span>
                    <div className="flex gap-3">
                      <Button type="button" variant="outline" onClick={() => setGenerateFormsOpen(false)} className="rounded-xl">
                        Cancel
                      </Button>
                      <Button 
                        onClick={handleGenerateForms}
                        disabled={isGenerating || selectedTemplates.length === 0}
                        className="bg-primary hover:bg-primary-hover text-white rounded-xl"
                        data-testid="generate-forms-submit"
                      >
                        {isGenerating ? <Loader2 className="h-4 w-4 animate-spin" /> : `Generate ${selectedTemplates.length} Forms`}
                      </Button>
                    </div>
                  </div>
                </DialogContent>
              </Dialog>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Tabs */}
      <Tabs defaultValue="overview" className="space-y-6">
        <TabsList className="bg-white border border-[#E4E8EB] p-1 rounded-xl flex-wrap">
          <TabsTrigger value="overview" className="rounded-lg data-[state=active]:bg-primary data-[state=active]:text-white">
            <User className="h-4 w-4 mr-2" />
            Overview
          </TabsTrigger>
          <TabsTrigger value="forms" className="rounded-lg data-[state=active]:bg-primary data-[state=active]:text-white">
            <ClipboardList className="h-4 w-4 mr-2" />
            Forms
          </TabsTrigger>
          <TabsTrigger value="checklist" className="rounded-lg data-[state=active]:bg-primary data-[state=active]:text-white">
            <CheckCircle className="h-4 w-4 mr-2" />
            Checklist
          </TabsTrigger>
          <TabsTrigger value="documents" className="rounded-lg data-[state=active]:bg-primary data-[state=active]:text-white">
            <FileText className="h-4 w-4 mr-2" />
            Documents
          </TabsTrigger>
          <TabsTrigger value="policies" className="rounded-lg data-[state=active]:bg-primary data-[state=active]:text-white">
            <FileCheck className="h-4 w-4 mr-2" />
            Policies
          </TabsTrigger>
          <TabsTrigger value="training" className="rounded-lg data-[state=active]:bg-primary data-[state=active]:text-white">
            <GraduationCap className="h-4 w-4 mr-2" />
            Training
          </TabsTrigger>
          <TabsTrigger value="audit" className="rounded-lg data-[state=active]:bg-primary data-[state=active]:text-white">
            <History className="h-4 w-4 mr-2" />
            Audit Log
          </TabsTrigger>
        </TabsList>

        {/* Generated Forms Tab */}
        <TabsContent value="forms">
          <Card className="border-[#E4E8EB] shadow-sm">
            <CardHeader>
              <CardTitle className="font-heading text-lg flex items-center justify-between">
                <span>Compliance Forms</span>
                <span className="text-sm font-normal text-text-muted">{generatedForms.length} forms</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {generatedForms.length === 0 ? (
                <div className="text-center py-8">
                  <ClipboardList className="h-12 w-12 mx-auto text-text-muted/50 mb-3" />
                  <p className="text-text-muted">No forms generated yet</p>
                  <p className="text-sm text-text-muted">Click "Generate Forms" to create compliance forms for this employee.</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {generatedForms.map((form) => {
                    const statusConfig = {
                      draft: { color: 'bg-gray-100 text-text-muted', icon: Clock },
                      sent: { color: 'bg-info/10 text-info', icon: Mail },
                      in_progress: { color: 'bg-warning/10 text-warning', icon: Clock },
                      completed: { color: 'bg-info/10 text-info', icon: CheckCircle },
                      reviewed: { color: 'bg-warning/10 text-warning', icon: Eye },
                      signed_off: { color: 'bg-success/10 text-success', icon: CheckCircle },
                      archived: { color: 'bg-gray-100 text-text-muted', icon: FileText }
                    };
                    const config = statusConfig[form.status] || statusConfig.draft;
                    const StatusIcon = config.icon;
                    
                    return (
                      <div 
                        key={form.id} 
                        className="flex items-center justify-between p-4 bg-[#F8FAFA] rounded-xl hover:bg-[#F0F4F5] transition-colors cursor-pointer"
                        onClick={() => navigate(`/portal/forms/${form.id}`)}
                        data-testid={`form-${form.id}`}
                      >
                        <div className="flex items-center gap-4">
                          <div className={`p-2 rounded-lg ${config.color}`}>
                            <StatusIcon className="h-5 w-5" />
                          </div>
                          <div>
                            <p className="font-medium text-text-primary">{form.template_name}</p>
                            <p className="text-sm text-text-muted">
                              {form.template_category} • Created {new Date(form.created_at).toLocaleDateString()}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className={`px-3 py-1 rounded-full text-xs font-medium ${config.color}`}>
                            {form.status.replace('_', ' ')}
                          </span>
                          {form.locked && (
                            <span className="text-success text-xs">Locked</span>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Overview Tab */}
        <TabsContent value="overview">
          <div className="grid lg:grid-cols-2 gap-6">
            <Card className="border-[#E4E8EB] shadow-sm">
              <CardHeader>
                <CardTitle className="font-heading text-lg">Personal Details</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-text-muted">Full Name</p>
                    <p className="font-medium text-text-primary">{employee.first_name} {employee.last_name}</p>
                  </div>
                  <div>
                    <p className="text-sm text-text-muted">Employee ID</p>
                    <p className="font-medium text-text-primary">{employee.employee_code}</p>
                  </div>
                  <div>
                    <p className="text-sm text-text-muted">Role</p>
                    <p className="font-medium text-text-primary">{employee.role}</p>
                  </div>
                  <div>
                    <p className="text-sm text-text-muted">Assignment</p>
                    <p className="font-medium text-text-primary">{employee.assignment || 'Unassigned'}</p>
                  </div>
                  <div>
                    <p className="text-sm text-text-muted">Email</p>
                    <p className="font-medium text-text-primary">{employee.email}</p>
                  </div>
                  <div>
                    <p className="text-sm text-text-muted">Phone</p>
                    <p className="font-medium text-text-primary">{employee.phone || 'Not provided'}</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="border-[#E4E8EB] shadow-sm">
              <CardHeader>
                <CardTitle className="font-heading text-lg">Compliance Summary</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-4 bg-[#F8FAFA] rounded-xl">
                    <p className="text-sm text-text-muted">Documents</p>
                    <p className="text-2xl font-heading font-bold text-text-primary">
                      {documents.filter(d => d.status === 'approved').length}/{documentTypes.length}
                    </p>
                  </div>
                  <div className="p-4 bg-[#F8FAFA] rounded-xl">
                    <p className="text-sm text-text-muted">Policies Signed</p>
                    <p className="text-2xl font-heading font-bold text-text-primary">
                      {policies.filter(p => p.status === 'signed').length}/{policies.length}
                    </p>
                  </div>
                  <div className="p-4 bg-[#F8FAFA] rounded-xl">
                    <p className="text-sm text-text-muted">Training Complete</p>
                    <p className="text-2xl font-heading font-bold text-text-primary">
                      {training.filter(t => t.status === 'completed').length}/{training.length}
                    </p>
                  </div>
                  <div className="p-4 bg-[#F8FAFA] rounded-xl">
                    <p className="text-sm text-text-muted">Missing Items</p>
                    <p className="text-2xl font-heading font-bold text-warning">
                      {documents.filter(d => d.status === 'not_started' || d.status === 'requested').length}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Training & Compliance Overview */}
          <ComplianceOverview
            employee={employee}
            documents={documents}
            training={training}
            policies={policies}
            generatedForms={generatedForms}
          />
        </TabsContent>

        {/* Checklist Tab */}
        <TabsContent value="checklist">
          <Card className="border-[#E4E8EB] shadow-sm">
            <CardContent className="p-6">
              <div className="space-y-6">
                {Object.entries(groupedDocs).map(([category, items]) => (
                  <div key={category} className="space-y-3">
                    <h3 className="font-heading font-semibold text-text-primary">{category}</h3>
                    <div className="space-y-2">
                      {items.map((item) => {
                        const StatusIcon = statusIcons[item.document?.status || 'not_started'];
                        return (
                          <div key={item.id} className="flex items-center justify-between p-3 bg-[#F8FAFA] rounded-xl">
                            <div className="flex items-center gap-3">
                              <StatusIcon className={`h-5 w-5 ${
                                item.document?.status === 'approved' ? 'text-success' :
                                item.document?.status === 'rejected' || item.document?.status === 'expired' ? 'text-error' :
                                item.document?.status === 'uploaded' || item.document?.status === 'under_review' ? 'text-warning' :
                                'text-text-muted'
                              }`} />
                              <div>
                                <p className="font-medium text-text-primary">{item.name}</p>
                                {item.required_before_active && (
                                  <span className="text-xs text-error">Required</span>
                                )}
                              </div>
                            </div>
                            <span className={`status-chip ${statusColors[item.document?.status || 'not_started']}`}>
                              {(item.document?.status || 'not_started').replace('_', ' ')}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Documents Tab */}
        <TabsContent value="documents">
          <Card className="border-[#E4E8EB] shadow-sm">
            <CardContent className="p-0">
              {documents.length === 0 ? (
                <div className="text-center py-12 text-text-muted">
                  <FileText className="h-12 w-12 mx-auto mb-3 opacity-50" />
                  <p>No documents uploaded yet</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-[#E4E8EB] bg-[#F8FAFA]">
                        <th className="text-left p-4 font-medium text-text-muted text-sm">Document</th>
                        <th className="text-left p-4 font-medium text-text-muted text-sm">Category</th>
                        <th className="text-left p-4 font-medium text-text-muted text-sm">Status</th>
                        <th className="text-left p-4 font-medium text-text-muted text-sm">Uploaded</th>
                        {!isAuditor() && <th className="text-left p-4 font-medium text-text-muted text-sm">Actions</th>}
                      </tr>
                    </thead>
                    <tbody>
                      {documents.map((doc) => (
                        <tr key={doc.id} className="border-b border-[#E4E8EB]">
                          <td className="p-4">
                            <p className="font-medium text-text-primary">{doc.document_type_name}</p>
                            {doc.original_filename && (
                              <p className="text-sm text-text-muted">{doc.original_filename}</p>
                            )}
                          </td>
                          <td className="p-4 text-text-muted">{doc.category}</td>
                          <td className="p-4">
                            <span className={`status-chip ${statusColors[doc.status]}`}>
                              {doc.status?.replace('_', ' ')}
                            </span>
                          </td>
                          <td className="p-4 text-text-muted text-sm">
                            {doc.uploaded_at ? new Date(doc.uploaded_at).toLocaleDateString() : '-'}
                          </td>
                          {!isAuditor() && (
                            <td className="p-4">
                              {doc.status === 'uploaded' && (
                                <div className="flex gap-2">
                                  <Button 
                                    size="sm" 
                                    onClick={() => handleUpdateDocumentStatus(doc.id, 'approved')}
                                    className="bg-success hover:bg-success/90 text-white rounded-lg"
                                  >
                                    Approve
                                  </Button>
                                  <Button 
                                    size="sm" 
                                    variant="outline"
                                    onClick={() => handleUpdateDocumentStatus(doc.id, 'rejected')}
                                    className="text-error border-error hover:bg-error/10 rounded-lg"
                                  >
                                    Reject
                                  </Button>
                                </div>
                              )}
                            </td>
                          )}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Policies Tab */}
        <TabsContent value="policies">
          <Card className="border-[#E4E8EB] shadow-sm">
            <CardContent className="p-6">
              {policies.length === 0 ? (
                <div className="text-center py-12 text-text-muted">
                  <FileCheck className="h-12 w-12 mx-auto mb-3 opacity-50" />
                  <p>No policies assigned yet</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {policies.map((policy) => (
                    <div key={policy.id} className="flex items-center justify-between p-4 bg-[#F8FAFA] rounded-xl">
                      <div>
                        <p className="font-medium text-text-primary">{policy.policy_title}</p>
                        <p className="text-sm text-text-muted">Assigned: {new Date(policy.assigned_at).toLocaleDateString()}</p>
                      </div>
                      <span className={`status-chip ${
                        policy.status === 'signed' ? 'status-success' :
                        policy.status === 'viewed' ? 'status-info' :
                        'status-neutral'
                      }`}>
                        {policy.status}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Training Tab */}
        <TabsContent value="training">
          <Card className="border-[#E4E8EB] shadow-sm">
            <CardContent className="p-6">
              {training.length === 0 ? (
                <div className="text-center py-12 text-text-muted">
                  <GraduationCap className="h-12 w-12 mx-auto mb-3 opacity-50" />
                  <p>No training records yet</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {training.map((record) => (
                    <div key={record.id} className="flex items-center justify-between p-4 bg-[#F8FAFA] rounded-xl">
                      <div>
                        <p className="font-medium text-text-primary">{record.training_name}</p>
                        <p className="text-sm text-text-muted">
                          {record.mandatory ? 'Mandatory' : 'Optional'}
                          {record.completion_date && ` · Completed: ${new Date(record.completion_date).toLocaleDateString()}`}
                        </p>
                      </div>
                      <span className={`status-chip ${
                        record.status === 'completed' ? 'status-success' :
                        record.status === 'in_progress' ? 'status-info' :
                        record.status === 'expired' ? 'status-error' :
                        'status-neutral'
                      }`}>
                        {record.status?.replace('_', ' ')}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Audit Log Tab */}
        <TabsContent value="audit">
          <Card className="border-[#E4E8EB] shadow-sm">
            <CardContent className="p-6">
              {auditLogs.length === 0 ? (
                <div className="text-center py-12 text-text-muted">
                  <History className="h-12 w-12 mx-auto mb-3 opacity-50" />
                  <p>No activity recorded yet</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {auditLogs.map((log) => (
                    <div key={log.id} className="flex items-start gap-4 p-4 bg-[#F8FAFA] rounded-xl">
                      <div className="w-10 h-10 bg-accent rounded-xl flex items-center justify-center flex-shrink-0">
                        <History className="h-5 w-5 text-primary" />
                      </div>
                      <div className="flex-1">
                        <p className="font-medium text-text-primary">
                          {log.action?.replace('_', ' ')}
                        </p>
                        <p className="text-sm text-text-muted">
                          By {log.user_name || 'System'} · {new Date(log.created_at).toLocaleString()}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Edit Employee Dialog */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent className="sm:max-w-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="font-heading flex items-center gap-2">
              <Edit className="h-5 w-5 text-primary" />
              Edit Employee Details
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 mt-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>First Name *</Label>
                <Input
                  value={editForm.first_name}
                  onChange={(e) => setEditForm({...editForm, first_name: e.target.value})}
                  className="rounded-xl"
                />
              </div>
              <div className="space-y-2">
                <Label>Last Name *</Label>
                <Input
                  value={editForm.last_name}
                  onChange={(e) => setEditForm({...editForm, last_name: e.target.value})}
                  className="rounded-xl"
                />
              </div>
            </div>
            
            <div className="space-y-2">
              <Label>Email *</Label>
              <Input
                type="email"
                value={editForm.email}
                onChange={(e) => setEditForm({...editForm, email: e.target.value})}
                className="rounded-xl"
              />
            </div>
            
            <div className="space-y-2">
              <Label>Phone</Label>
              <Input
                type="tel"
                value={editForm.phone}
                onChange={(e) => setEditForm({...editForm, phone: e.target.value})}
                className="rounded-xl"
              />
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Role *</Label>
                <Select value={editForm.role} onValueChange={(value) => setEditForm({...editForm, role: value})}>
                  <SelectTrigger className="rounded-xl">
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
                <Label>Status</Label>
                <Select value={editForm.status} onValueChange={(value) => setEditForm({...editForm, status: value})}>
                  <SelectTrigger className="rounded-xl">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {statuses.map((s) => (
                      <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Current Placement</Label>
                <Input
                  value={editForm.assignment}
                  onChange={(e) => setEditForm({...editForm, assignment: e.target.value})}
                  placeholder="e.g., Sunrise Care Home"
                  className="rounded-xl"
                />
              </div>
              <div className="space-y-2">
                <Label>Start Date</Label>
                <Input
                  type="date"
                  value={editForm.start_date}
                  onChange={(e) => setEditForm({...editForm, start_date: e.target.value})}
                  className="rounded-xl"
                />
              </div>
            </div>
            
            <div className="space-y-2">
              <Label>Notes</Label>
              <Textarea
                value={editForm.notes}
                onChange={(e) => setEditForm({...editForm, notes: e.target.value})}
                placeholder="Internal notes about this employee..."
                className="rounded-xl min-h-[80px]"
              />
            </div>
          </div>
          <DialogFooter className="mt-6">
            <Button variant="outline" onClick={() => setEditDialogOpen(false)} className="rounded-xl">
              Cancel
            </Button>
            <Button onClick={handleSaveEmployee} disabled={isSaving} className="bg-primary hover:bg-primary-hover text-white rounded-xl">
              {isSaving ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Save className="h-4 w-4 mr-2" />}
              Save Changes
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Archive Confirmation Dialog */}
      <Dialog open={archiveDialogOpen} onOpenChange={setArchiveDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="font-heading flex items-center gap-2">
              <Archive className="h-5 w-5 text-warning" />
              Archive Employee
            </DialogTitle>
            <DialogDescription className="text-text-muted">
              Are you sure you want to archive <strong>{employee?.first_name} {employee?.last_name}</strong>?
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3 py-4">
            <p className="text-sm text-text-muted">This will:</p>
            <ul className="text-sm text-text-muted list-disc list-inside space-y-1">
              <li>Hide employee from the active employees list</li>
              <li>Retain all documents, forms, and audit history</li>
              <li>Allow restoration at any time</li>
            </ul>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setArchiveDialogOpen(false)} className="rounded-xl">
              Cancel
            </Button>
            <Button onClick={handleArchiveEmployee} className="bg-warning hover:bg-warning/90 text-white rounded-xl">
              <Archive className="h-4 w-4 mr-2" />
              Archive Employee
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Permanent Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="font-heading flex items-center gap-2 text-error">
              <AlertTriangle className="h-5 w-5" />
              Permanent Deletion
            </DialogTitle>
            <DialogDescription className="text-text-muted">
              Are you sure you want to <strong>permanently delete</strong> {employee?.first_name} {employee?.last_name}?
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3 py-4 bg-error/5 p-4 rounded-xl border border-error/20">
            <p className="text-sm font-medium text-error">This action cannot be undone!</p>
            <p className="text-sm text-text-muted">All of the following will be permanently deleted:</p>
            <ul className="text-sm text-text-muted list-disc list-inside space-y-1">
              <li>Employee record</li>
              <li>All uploaded documents</li>
              <li>All compliance forms</li>
              <li>Training records</li>
              <li>Policy assignments</li>
            </ul>
            <p className="text-xs text-text-muted mt-2">Only use this for duplicate records, test data, or incorrect entries.</p>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDialogOpen(false)} className="rounded-xl">
              Cancel
            </Button>
            <Button onClick={handlePermanentDelete} className="bg-error hover:bg-error/90 text-white rounded-xl">
              <Trash2 className="h-4 w-4 mr-2" />
              Delete Permanently
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
