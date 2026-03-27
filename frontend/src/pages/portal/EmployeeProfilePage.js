import { useState, useEffect } from 'react';
import { useParams, Link, useNavigate, useSearchParams } from 'react-router-dom';
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
import DocumentPreviewModal from '../../components/portal/DocumentPreviewModal';
import {
  ArrowLeft, Upload, FileText, Mail, Phone, Calendar,
  CheckCircle, Clock, AlertTriangle, XCircle, Loader2, FileCheck,
  GraduationCap, ClipboardList, History, User, FolderUp, Eye, Shield,
  MoreHorizontal, Edit, Archive, Trash2, RotateCcw, FileDown, Save,
  Download, RefreshCw, FileArchive, FileSpreadsheet, Printer, FilePdf
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
  const [searchParams, setSearchParams] = useSearchParams();
  
  // Initialize active tab from URL for navigation state persistence
  const [activeTab, setActiveTab] = useState(searchParams.get('tab') || 'overview');
  const [employee, setEmployee] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [documentTypes, setDocumentTypes] = useState([]);
  const [policies, setPolicies] = useState([]);
  const [training, setTraining] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [generatedForms, setGeneratedForms] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [compliance, setCompliance] = useState(null);
  const [loading, setLoading] = useState(true);
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [bulkUploadOpen, setBulkUploadOpen] = useState(false);
  const [generateFormsOpen, setGenerateFormsOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [archiveDialogOpen, setArchiveDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [isRefreshingStatus, setIsRefreshingStatus] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [selectedDocType, setSelectedDocType] = useState('');
  const [uploadFile, setUploadFile] = useState(null);
  const [bulkFiles, setBulkFiles] = useState([]);
  const [bulkDocTypes, setBulkDocTypes] = useState({});
  const [selectedTemplates, setSelectedTemplates] = useState([]);
  const [isUploading, setIsUploading] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [editForm, setEditForm] = useState({});
  const [importAppOpen, setImportAppOpen] = useState(false);
  const [importAppFile, setImportAppFile] = useState(null);
  const [importCvFile, setImportCvFile] = useState(null);
  const [isImporting, setIsImporting] = useState(false);
  const [complianceRequirements, setComplianceRequirements] = useState(null);
  const [selectedRequirement, setSelectedRequirement] = useState('');
  const [documentLabel, setDocumentLabel] = useState('');
  // Import document dialog states
  const [importDocOpen, setImportDocOpen] = useState(false);
  const [importDocType, setImportDocType] = useState('');
  const [importDocFile, setImportDocFile] = useState(null);
  const [importDocNotes, setImportDocNotes] = useState('');
  const { token, isAuditor, user } = useAuth();
  
  // Document preview modal state
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewFile, setPreviewFile] = useState(null);
  
  // Sync tab changes to URL
  const handleTabChange = (value) => {
    setActiveTab(value);
    setSearchParams({ tab: value }, { replace: true });
  };
  
  // Open document in preview modal
  const handlePreviewDocument = (url, name, filename) => {
    setPreviewFile({ url, name, filename });
    setPreviewOpen(true);
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

  const statuses = [
    { value: 'new', label: 'New' },
    { value: 'screening', label: 'Screening' },
    { value: 'interview', label: 'Interview' },
    { value: 'compliance_review', label: 'Compliance Review' },
    { value: 'onboarding', label: 'Onboarding' },
    { value: 'active', label: 'Active' },
    { value: 'inactive', label: 'Inactive' }
  ];

  const onboardingStatuses = [
    'New',
    'Documents Pending',
    'Under Review',
    'Ready for Placement',
    'Active',
    'Archived'
  ];

  const isSuperAdmin = () => user?.role === 'super_admin';

  const fetchData = async () => {
    try {
      const [empRes, docsRes, typesRes, policiesRes, trainingRes, logsRes, formsRes, templatesRes, compReqRes] = await Promise.all([
        axios.get(`${API}/employees/${employeeId}`, { headers: { Authorization: `Bearer ${token}` } }),
        axios.get(`${API}/employee-documents?employee_id=${employeeId}`, { headers: { Authorization: `Bearer ${token}` } }),
        axios.get(`${API}/document-types`, { headers: { Authorization: `Bearer ${token}` } }),
        axios.get(`${API}/policy-assignments?employee_id=${employeeId}`, { headers: { Authorization: `Bearer ${token}` } }),
        axios.get(`${API}/training-records?employee_id=${employeeId}`, { headers: { Authorization: `Bearer ${token}` } }),
        axios.get(`${API}/audit-logs?entity_id=${employeeId}`, { headers: { Authorization: `Bearer ${token}` } }),
        axios.get(`${API}/generated-forms?employee_id=${employeeId}`, { headers: { Authorization: `Bearer ${token}` } }),
        axios.get(`${API}/templates`, { headers: { Authorization: `Bearer ${token}` } }),
        axios.get(`${API}/employees/${employeeId}/compliance-requirements`, { headers: { Authorization: `Bearer ${token}` } })
      ]);
      
      setEmployee(empRes.data);
      setDocuments(docsRes.data);
      setDocumentTypes(typesRes.data);
      setPolicies(policiesRes.data);
      setTraining(trainingRes.data);
      setAuditLogs(logsRes.data);
      setGeneratedForms(formsRes.data);
      setTemplates(templatesRes.data);
      setComplianceRequirements(compReqRes.data);
    } catch (error) {
      console.error('Failed to fetch employee data:', error);
      toast.error('Failed to load employee data');
    } finally {
      setLoading(false);
    }
  };

  const fetchCompliance = async () => {
    try {
      const response = await axios.get(`${API}/employees/${employeeId}/compliance`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setCompliance(response.data);
    } catch (error) {
      console.error('Failed to fetch compliance:', error);
    }
  };

  useEffect(() => {
    fetchData();
    fetchCompliance();
  }, [employeeId, token]);

  const handleRefreshStatus = async () => {
    setIsRefreshingStatus(true);
    try {
      const response = await axios.post(`${API}/employees/${employeeId}/refresh-status`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (response.data.status_changed) {
        toast.success(`Status updated to: ${response.data.new_status}`);
      } else {
        toast.info('Status is already up to date');
      }
      fetchData();
      fetchCompliance();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to refresh status');
    } finally {
      setIsRefreshingStatus(false);
    }
  };

  const handleExportFile = async () => {
    setIsExporting(true);
    try {
      const response = await axios.get(`${API}/employees/${employeeId}/export-file`, {
        headers: { Authorization: `Bearer ${token}` },
        responseType: 'blob'
      });
      
      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      const filename = response.headers['content-disposition']?.split('filename=')[1]?.replace(/"/g, '') 
        || `${employee?.employee_code}_File.zip`;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      toast.success('Employee file exported successfully');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to export file');
    } finally {
      setIsExporting(false);
    }
  };

  const handleExportComplianceSummary = async () => {
    try {
      const response = await axios.get(`${API}/employees/${employeeId}/export-compliance-summary`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      // Convert JSON to downloadable file
      const blob = new Blob([JSON.stringify(response.data, null, 2)], { type: 'application/json' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${employee?.employee_code}_Compliance_Summary.json`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      toast.success('Compliance summary exported');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to export compliance summary');
    }
  };

  const handleExportCompliancePDF = async () => {
    setIsExporting(true);
    try {
      const response = await axios.get(`${API}/employees/${employeeId}/export-compliance-pdf`, {
        headers: { Authorization: `Bearer ${token}` },
        responseType: 'blob'
      });
      
      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }));
      const link = document.createElement('a');
      link.href = url;
      const filename = response.headers['content-disposition']?.split('filename=')[1]?.replace(/"/g, '') 
        || `${employee?.employee_code}_Compliance_Summary.pdf`;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      toast.success('Compliance PDF exported successfully');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to export PDF');
    } finally {
      setIsExporting(false);
    }
  };

  const handlePrintCompliancePDF = async () => {
    try {
      const response = await axios.get(`${API}/employees/${employeeId}/export-compliance-pdf`, {
        headers: { Authorization: `Bearer ${token}` },
        responseType: 'blob'
      });
      
      // Open in new tab for printing
      const url = window.URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }));
      const printWindow = window.open(url, '_blank');
      if (printWindow) {
        printWindow.onload = () => {
          printWindow.print();
        };
      }
    } catch (error) {
      toast.error('Failed to open PDF for printing');
    }
  };

  const handleUploadDocument = async (e) => {
    e.preventDefault();
    if (!selectedRequirement || !uploadFile) {
      toast.error('Please select a requirement and file');
      return;
    }
    
    setIsUploading(true);
    
    try {
      const formData = new FormData();
      formData.append('requirement_id', selectedRequirement);
      formData.append('file', uploadFile);
      if (documentLabel) {
        formData.append('document_label', documentLabel);
      }
      
      await axios.post(`${API}/employees/${employeeId}/upload-document`, formData, {
        headers: { 
          Authorization: `Bearer ${token}`,
          'Content-Type': 'multipart/form-data'
        }
      });
      
      toast.success('Document uploaded successfully');
      setUploadDialogOpen(false);
      setSelectedRequirement('');
      setSelectedDocType('');
      setDocumentLabel('');
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

  const handleVerifyDocument = async (docId) => {
    try {
      await axios.post(`${API}/employee-documents/${docId}/verify`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Document verified');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to verify document');
    }
  };

  const handleUnverifyDocument = async (docId) => {
    try {
      await axios.post(`${API}/employee-documents/${docId}/unverify`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Verification removed');
      fetchData();
    } catch (error) {
      toast.error('Failed to remove verification');
    }
  };

  const handleSaveFormAsDocument = async (formId, e) => {
    e.stopPropagation(); // Prevent navigation to form editor
    try {
      toast.loading('Saving form as document...');
      const response = await axios.post(`${API}/generated-forms/${formId}/save-as-document`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.dismiss();
      toast.success(`Saved to ${response.data.folder}`);
      fetchData();
    } catch (error) {
      toast.dismiss();
      toast.error(error.response?.data?.detail || 'Failed to save form as document');
    }
  };

  // Verify all documents under a requirement
  const handleVerifyRequirement = async (requirementId) => {
    try {
      await axios.post(`${API}/employees/${employeeId}/requirements/${requirementId}/verify-all`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Requirement verified');
      fetchData();
    } catch (error) {
      toast.error('Failed to verify requirement');
    }
  };

  // Delete a specific document (for multi-file requirements)
  const handleDeleteDocument = async (docId) => {
    try {
      await axios.delete(`${API}/employee-documents/${docId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Document deleted');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete document');
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

  const handleImportApplication = async () => {
    if (!importAppFile) {
      toast.error('Please select an application form to upload');
      return;
    }
    
    setIsImporting(true);
    
    try {
      const formData = new FormData();
      formData.append('employee_id', employeeId);
      formData.append('application_file', importAppFile);
      if (importCvFile) {
        formData.append('cv_file', importCvFile);
      }
      
      const response = await axios.post(
        `${API}/generated-forms/import-application`,
        formData,
        {
          headers: { 
            Authorization: `Bearer ${token}`,
            'Content-Type': 'multipart/form-data'
          }
        }
      );
      
      toast.success(response.data.message || 'Application imported successfully');
      setImportAppOpen(false);
      setImportAppFile(null);
      setImportCvFile(null);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to import application');
    } finally {
      setIsImporting(false);
    }
  };

  // Import document for Reference, Health Screening, Contract, etc.
  const handleImportDocument = async () => {
    if (!importDocFile || !importDocType) {
      toast.error('Please select document type and file');
      return;
    }
    
    setIsImporting(true);
    
    try {
      const formData = new FormData();
      formData.append('employee_id', employeeId);
      formData.append('form_type', importDocType);
      formData.append('document_file', importDocFile);
      if (importDocNotes) {
        formData.append('notes', importDocNotes);
      }
      
      const response = await axios.post(
        `${API}/generated-forms/import-document`,
        formData,
        {
          headers: { 
            Authorization: `Bearer ${token}`,
            'Content-Type': 'multipart/form-data'
          }
        }
      );
      
      toast.success(response.data.message || 'Document imported successfully');
      setImportDocOpen(false);
      setImportDocType('');
      setImportDocFile(null);
      setImportDocNotes('');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to import document');
    } finally {
      setIsImporting(false);
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
      onboarding_status: employee?.onboarding_status || 'New',
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
      {/* Back Link - Uses browser history to preserve filter/tab state */}
      <button 
        onClick={() => navigate(-1)} 
        className="inline-flex items-center gap-2 text-text-muted hover:text-primary transition-colors"
        data-testid="back-link"
      >
        <ArrowLeft className="h-4 w-4" />
        Back
      </button>

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
                <div className="flex items-center gap-2 mt-2">
                  <span className={`status-chip ${
                    employee.status === 'active' ? 'status-success' :
                    employee.status === 'onboarding' ? 'status-info' :
                    'status-neutral'
                  }`}>
                    {employee.status?.replace('_', ' ')}
                  </span>
                  <span className={`px-2 py-1 rounded-lg text-xs font-medium ${
                    employee.onboarding_status === 'Ready for Placement' ? 'bg-success/10 text-success' :
                    employee.onboarding_status === 'Under Review' ? 'bg-info/10 text-info' :
                    employee.onboarding_status === 'Documents Pending' ? 'bg-warning/10 text-warning' :
                    employee.onboarding_status === 'Active' ? 'bg-success/10 text-success' :
                    'bg-gray-100 text-gray-600'
                  }`}>
                    {employee.onboarding_status || 'New'}
                  </span>
                </div>
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
                    <DropdownMenuContent align="end" className="w-56">
                      <DropdownMenuItem onClick={openEditDialog}>
                        <Edit className="h-4 w-4 mr-2" />
                        Edit Details
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={handleRefreshStatus} disabled={isRefreshingStatus}>
                        <RefreshCw className={`h-4 w-4 mr-2 ${isRefreshingStatus ? 'animate-spin' : ''}`} />
                        Refresh Status
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem onClick={handleExportFile} disabled={isExporting}>
                        <FileArchive className="h-4 w-4 mr-2" />
                        Export Employee File (ZIP)
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={handleExportCompliancePDF} disabled={isExporting} data-testid="download-compliance-pdf-btn">
                        <FileDown className="h-4 w-4 mr-2" />
                        Download Compliance PDF
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={handlePrintCompliancePDF} data-testid="print-compliance-pdf-btn">
                        <Printer className="h-4 w-4 mr-2" />
                        Print Compliance PDF
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
              <ClipboardList className="h-5 w-5 text-text-muted" />
              <span className="text-sm text-text-primary">{employee.onboarding_status || 'New'}</span>
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
                      <Label>Compliance Requirement</Label>
                      <Select value={selectedRequirement} onValueChange={setSelectedRequirement}>
                        <SelectTrigger className="rounded-xl" data-testid="requirement-select">
                          <SelectValue placeholder="Select requirement to upload for" />
                        </SelectTrigger>
                        <SelectContent className="max-h-[300px]">
                          {complianceRequirements?.requirements
                            ?.filter(req => req.type === 'document' || req.type === 'db_record')
                            .map((req) => (
                              <SelectItem key={req.id} value={req.id}>
                                <div className="flex items-center gap-2">
                                  <span className={`w-2 h-2 rounded-full ${
                                    req.status === 'completed' ? 'bg-success' :
                                    req.status === 'in_progress' ? 'bg-warning' : 'bg-gray-300'
                                  }`} />
                                  {req.name}
                                  {req.allow_multiple_files && <span className="text-xs bg-info/20 text-info px-1 rounded">Multi</span>}
                                  {req.document_count > 0 && <span className="text-xs text-text-muted">({req.document_count} file{req.document_count !== 1 ? 's' : ''})</span>}
                                </div>
                              </SelectItem>
                            ))}
                        </SelectContent>
                      </Select>
                      {selectedRequirement && (() => {
                        const selectedReq = complianceRequirements?.requirements?.find(r => r.id === selectedRequirement);
                        if (selectedReq?.document_count > 0 && !selectedReq?.allow_multiple_files) {
                          return (
                            <p className="text-xs text-warning flex items-center gap-1">
                              <AlertTriangle className="h-3 w-3" />
                              This will replace the existing document
                            </p>
                          );
                        }
                        if (selectedReq?.allow_multiple_files) {
                          return (
                            <p className="text-xs text-info flex items-center gap-1">
                              This requirement accepts multiple files
                            </p>
                          );
                        }
                        return null;
                      })()}
                    </div>
                    {/* Document Label for multi-file requirements */}
                    {selectedRequirement && complianceRequirements?.requirements?.find(r => r.id === selectedRequirement)?.allow_multiple_files && (
                      <div className="space-y-2">
                        <Label>Document Label (optional)</Label>
                        <Input
                          type="text"
                          placeholder="e.g., Passport Front, Visa, BRP Card"
                          value={documentLabel || ''}
                          onChange={(e) => setDocumentLabel(e.target.value)}
                          className="rounded-xl"
                          data-testid="doc-label-input"
                        />
                        <p className="text-xs text-text-muted">
                          Give this file a descriptive name to help identify it.
                        </p>
                      </div>
                    )}
                    <div className="space-y-2">
                      <Label>File</Label>
                      <Input
                        type="file"
                        onChange={(e) => setUploadFile(e.target.files[0])}
                        className="rounded-xl"
                        data-testid="doc-file-input"
                      />
                      <p className="text-xs text-text-muted">
                        Upload a clear copy of the document. PDF, JPG, PNG accepted.
                      </p>
                    </div>
                    <div className="flex justify-end gap-3 pt-4">
                      <Button type="button" variant="outline" onClick={() => { setUploadDialogOpen(false); setSelectedRequirement(''); setDocumentLabel(''); }} className="rounded-xl">
                        Cancel
                      </Button>
                      <Button type="submit" disabled={isUploading || !selectedRequirement} className="bg-primary hover:bg-primary-hover text-white rounded-xl" data-testid="upload-submit">
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

              {/* Generate Forms Dropdown */}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" className="rounded-xl" data-testid="generate-forms-btn">
                    <ClipboardList className="mr-2 h-4 w-4" />
                    Generate Forms
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-56">
                  <DropdownMenuItem onClick={() => setGenerateFormsOpen(true)} data-testid="generate-blank-forms">
                    <ClipboardList className="mr-2 h-4 w-4" />
                    Generate Blank Forms
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={() => setImportAppOpen(true)} data-testid="import-application">
                    <FolderUp className="mr-2 h-4 w-4" />
                    Import Application Form
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => setImportDocOpen(true)} data-testid="import-document">
                    <FileCheck className="mr-2 h-4 w-4" />
                    Import Other Document
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>

              {/* Generate Blank Forms Dialog */}
              <Dialog open={generateFormsOpen} onOpenChange={setGenerateFormsOpen}>
                <DialogContent className="max-w-2xl max-h-[80vh] overflow-hidden flex flex-col bg-white">
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

              {/* Import Existing Application Dialog */}
              <Dialog open={importAppOpen} onOpenChange={setImportAppOpen}>
                <DialogContent className="max-w-lg bg-white">
                  <DialogHeader>
                    <DialogTitle className="font-heading">Create from Existing Application</DialogTitle>
                    <DialogDescription>
                      Upload a completed application form and optionally a CV. The form will be marked as "Completed (Imported)" and linked to the employee's compliance checklist.
                    </DialogDescription>
                  </DialogHeader>
                  <div className="space-y-4 mt-4">
                    <div className="space-y-2">
                      <Label className="text-sm font-medium">
                        Application Form <span className="text-red-500">*</span>
                      </Label>
                      <div 
                        className={`border-2 border-dashed rounded-xl p-6 text-center transition-colors ${
                          importAppFile ? 'border-primary bg-primary/5' : 'border-[#E4E8EB] hover:border-primary/50'
                        }`}
                      >
                        <input
                          type="file"
                          accept=".pdf,.doc,.docx"
                          onChange={(e) => setImportAppFile(e.target.files?.[0] || null)}
                          className="hidden"
                          id="import-app-file"
                        />
                        <label htmlFor="import-app-file" className="cursor-pointer">
                          {importAppFile ? (
                            <div className="flex items-center justify-center gap-2">
                              <FileText className="h-5 w-5 text-primary" />
                              <span className="text-sm font-medium text-primary">{importAppFile.name}</span>
                            </div>
                          ) : (
                            <div>
                              <Upload className="h-8 w-8 mx-auto mb-2 text-text-muted" />
                              <p className="text-sm text-text-muted">Click to upload application form</p>
                              <p className="text-xs text-text-muted mt-1">PDF, DOC, DOCX accepted</p>
                            </div>
                          )}
                        </label>
                      </div>
                    </div>

                    <div className="space-y-2">
                      <Label className="text-sm font-medium">
                        CV / Resume <span className="text-text-muted">(optional)</span>
                      </Label>
                      <div 
                        className={`border-2 border-dashed rounded-xl p-4 text-center transition-colors ${
                          importCvFile ? 'border-primary bg-primary/5' : 'border-[#E4E8EB] hover:border-primary/50'
                        }`}
                      >
                        <input
                          type="file"
                          accept=".pdf,.doc,.docx"
                          onChange={(e) => setImportCvFile(e.target.files?.[0] || null)}
                          className="hidden"
                          id="import-cv-file"
                        />
                        <label htmlFor="import-cv-file" className="cursor-pointer">
                          {importCvFile ? (
                            <div className="flex items-center justify-center gap-2">
                              <FileText className="h-5 w-5 text-primary" />
                              <span className="text-sm font-medium text-primary">{importCvFile.name}</span>
                            </div>
                          ) : (
                            <div className="py-1">
                              <p className="text-sm text-text-muted">Click to upload CV</p>
                            </div>
                          )}
                        </label>
                      </div>
                    </div>

                    <div className="bg-[#F8FAFA] rounded-xl p-4 space-y-2">
                      <h4 className="text-sm font-medium text-text-primary">What happens next:</h4>
                      <ul className="text-xs text-text-muted space-y-1">
                        <li className="flex items-start gap-2">
                          <CheckCircle className="h-3.5 w-3.5 text-green-500 mt-0.5 shrink-0" />
                          Application Form marked as "Completed (Imported)"
                        </li>
                        <li className="flex items-start gap-2">
                          <CheckCircle className="h-3.5 w-3.5 text-green-500 mt-0.5 shrink-0" />
                          Document stored in employee's A_Application folder
                        </li>
                        <li className="flex items-start gap-2">
                          <CheckCircle className="h-3.5 w-3.5 text-green-500 mt-0.5 shrink-0" />
                          Checklist item automatically marked as complete
                        </li>
                        <li className="flex items-start gap-2">
                          <CheckCircle className="h-3.5 w-3.5 text-green-500 mt-0.5 shrink-0" />
                          Form fields locked (read-only) unless manually edited
                        </li>
                      </ul>
                    </div>
                  </div>

                  <div className="flex justify-end gap-3 pt-4 border-t border-[#E4E8EB] mt-4">
                    <Button 
                      variant="outline" 
                      onClick={() => { setImportAppOpen(false); setImportAppFile(null); setImportCvFile(null); }} 
                      className="rounded-xl"
                    >
                      Cancel
                    </Button>
                    <Button 
                      onClick={handleImportApplication}
                      disabled={isImporting || !importAppFile}
                      className="bg-primary hover:bg-primary-hover text-white rounded-xl"
                      data-testid="import-application-submit"
                    >
                      {isImporting ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Import Application'}
                    </Button>
                  </div>
                </DialogContent>
              </Dialog>

              {/* Import Other Document Dialog (Reference, Health Screening, Contract) */}
              <Dialog open={importDocOpen} onOpenChange={setImportDocOpen}>
                <DialogContent className="max-w-lg bg-white">
                  <DialogHeader>
                    <DialogTitle className="font-heading">Import Existing Document</DialogTitle>
                    <DialogDescription>
                      Upload an existing completed document (Reference letter, Health form, Contract, etc.) to mark the corresponding compliance requirement as complete.
                    </DialogDescription>
                  </DialogHeader>
                  <div className="space-y-4 mt-4">
                    <div className="space-y-2">
                      <Label className="text-sm font-medium">
                        Document Type <span className="text-red-500">*</span>
                      </Label>
                      <Select value={importDocType} onValueChange={setImportDocType}>
                        <SelectTrigger className="rounded-xl" data-testid="import-doc-type-select">
                          <SelectValue placeholder="Select document type" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="reference_1">
                            <div className="flex items-center gap-2">
                              <span className="w-2 h-2 rounded-full bg-warning" />
                              Reference 1
                            </div>
                          </SelectItem>
                          <SelectItem value="reference_2">
                            <div className="flex items-center gap-2">
                              <span className="w-2 h-2 rounded-full bg-warning" />
                              Reference 2
                            </div>
                          </SelectItem>
                          <SelectItem value="health_screening">
                            <div className="flex items-center gap-2">
                              <span className="w-2 h-2 rounded-full bg-info" />
                              Health Screening Questionnaire
                            </div>
                          </SelectItem>
                          <SelectItem value="contract">
                            <div className="flex items-center gap-2">
                              <span className="w-2 h-2 rounded-full bg-success" />
                              Contract / Offer Letter
                            </div>
                          </SelectItem>
                          <SelectItem value="induction">
                            <div className="flex items-center gap-2">
                              <span className="w-2 h-2 rounded-full bg-primary" />
                              Induction & Competency
                            </div>
                          </SelectItem>
                          <SelectItem value="handbook">
                            <div className="flex items-center gap-2">
                              <span className="w-2 h-2 rounded-full bg-gray-400" />
                              Employee Handbook Acknowledgement
                            </div>
                          </SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="space-y-2">
                      <Label className="text-sm font-medium">
                        Document File <span className="text-red-500">*</span>
                      </Label>
                      <div 
                        className={`border-2 border-dashed rounded-xl p-6 text-center transition-colors ${
                          importDocFile ? 'border-primary bg-primary/5' : 'border-[#E4E8EB] hover:border-primary/50'
                        }`}
                      >
                        <input
                          type="file"
                          accept=".pdf,.doc,.docx,.jpg,.jpeg,.png"
                          onChange={(e) => setImportDocFile(e.target.files?.[0] || null)}
                          className="hidden"
                          id="import-doc-file"
                        />
                        <label htmlFor="import-doc-file" className="cursor-pointer">
                          {importDocFile ? (
                            <div className="flex items-center justify-center gap-2">
                              <FileText className="h-5 w-5 text-primary" />
                              <span className="text-sm font-medium text-primary">{importDocFile.name}</span>
                            </div>
                          ) : (
                            <div>
                              <Upload className="h-8 w-8 mx-auto mb-2 text-text-muted" />
                              <p className="text-sm text-text-muted">Click to upload document</p>
                              <p className="text-xs text-text-muted mt-1">PDF, DOC, DOCX, JPG, PNG accepted</p>
                            </div>
                          )}
                        </label>
                      </div>
                    </div>

                    <div className="space-y-2">
                      <Label className="text-sm font-medium">
                        Notes <span className="text-text-muted">(optional)</span>
                      </Label>
                      <Textarea 
                        value={importDocNotes}
                        onChange={(e) => setImportDocNotes(e.target.value)}
                        placeholder="e.g., Reference from John Smith, previous employer at ABC Company"
                        className="rounded-xl resize-none"
                        rows={2}
                      />
                    </div>

                    <div className="bg-[#F8FAFA] rounded-xl p-4 space-y-2">
                      <h4 className="text-sm font-medium text-text-primary">What happens:</h4>
                      <ul className="text-xs text-text-muted space-y-1">
                        <li className="flex items-start gap-2">
                          <CheckCircle className="h-3.5 w-3.5 text-green-500 mt-0.5 shrink-0" />
                          Form marked as "Completed (Imported)"
                        </li>
                        <li className="flex items-start gap-2">
                          <CheckCircle className="h-3.5 w-3.5 text-green-500 mt-0.5 shrink-0" />
                          Document stored in employee's compliance folder
                        </li>
                        <li className="flex items-start gap-2">
                          <CheckCircle className="h-3.5 w-3.5 text-green-500 mt-0.5 shrink-0" />
                          Checklist requirement marked complete
                        </li>
                        <li className="flex items-start gap-2">
                          <CheckCircle className="h-3.5 w-3.5 text-green-500 mt-0.5 shrink-0" />
                          Ready for verification
                        </li>
                      </ul>
                    </div>
                  </div>

                  <div className="flex justify-end gap-3 pt-4 border-t border-[#E4E8EB] mt-4">
                    <Button 
                      variant="outline" 
                      onClick={() => { setImportDocOpen(false); setImportDocType(''); setImportDocFile(null); setImportDocNotes(''); }} 
                      className="rounded-xl"
                    >
                      Cancel
                    </Button>
                    <Button 
                      onClick={handleImportDocument}
                      disabled={isImporting || !importDocFile || !importDocType}
                      className="bg-primary hover:bg-primary-hover text-white rounded-xl"
                      data-testid="import-document-submit"
                    >
                      {isImporting ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Import Document'}
                    </Button>
                  </div>
                </DialogContent>
              </Dialog>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={handleTabChange} className="space-y-6">
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
                          {(form.status === 'completed' || form.status === 'completed_imported' || form.status === 'signed_off') && !form.saved_as_document_id && (
                            <Button
                              size="sm"
                              variant="outline"
                              className="text-primary border-primary hover:bg-primary/10 rounded-lg text-xs"
                              onClick={(e) => handleSaveFormAsDocument(form.id, e)}
                              data-testid={`save-form-doc-${form.id}`}
                            >
                              <FileDown className="h-3 w-3 mr-1" />
                              Save as Doc
                            </Button>
                          )}
                          {form.saved_as_document_id && (
                            <span className="text-xs text-success flex items-center gap-1">
                              <CheckCircle className="h-3 w-3" />
                              Saved
                            </span>
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
                    <p className="text-sm text-text-muted">Onboarding Status</p>
                    <p className="font-medium text-text-primary">{employee.onboarding_status || 'New'}</p>
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
                    <p className="text-sm text-text-muted">Requirements Complete</p>
                    <p className="text-2xl font-heading font-bold text-text-primary">
                      {complianceRequirements?.summary?.completed || 0}/{complianceRequirements?.summary?.total || 0}
                    </p>
                  </div>
                  <div className="p-4 bg-[#F8FAFA] rounded-xl">
                    <p className="text-sm text-text-muted">Verified</p>
                    <p className="text-2xl font-heading font-bold text-success">
                      {complianceRequirements?.summary?.verified || 0}/{complianceRequirements?.summary?.completed || 0}
                    </p>
                  </div>
                  <div className="p-4 bg-[#F8FAFA] rounded-xl">
                    <p className="text-sm text-text-muted">Policies Signed</p>
                    <p className="text-2xl font-heading font-bold text-text-primary">
                      {policies.filter(p => p.status === 'signed').length}/{policies.length}
                    </p>
                  </div>
                  <div className="p-4 bg-[#F8FAFA] rounded-xl">
                    <p className="text-sm text-text-muted">Missing Requirements</p>
                    <p className="text-2xl font-heading font-bold text-warning">
                      {complianceRequirements?.summary?.missing || 0}
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

        {/* Checklist Tab - Mandatory Items */}
        <TabsContent value="checklist">
          <Card className="border-[#E4E8EB] shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="font-heading text-lg">Mandatory Compliance Items</CardTitle>
                {complianceRequirements && (
                  <p className="text-sm text-text-muted mt-1">
                    {complianceRequirements.summary.completed} of {complianceRequirements.summary.total} items complete 
                    ({complianceRequirements.summary.verified} verified)
                  </p>
                )}
              </div>
              {complianceRequirements && complianceRequirements.summary.missing > 0 && (
                <div className="flex items-center gap-2 text-sm text-error bg-error/10 px-3 py-1.5 rounded-lg">
                  <AlertTriangle className="h-4 w-4" />
                  {complianceRequirements.summary.missing} missing
                </div>
              )}
            </CardHeader>
            <CardContent>
              {!complianceRequirements ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="h-8 w-8 animate-spin text-primary" />
                </div>
              ) : (
                <div className="space-y-6">
                  {/* Group requirements by category */}
                  {['A_Application_Form', 'B_Recruitment_Checklist', 'C_Personal_Information', 'D_Interview', 
                    'E_Equal_Opportunities', 'F_Health_Screening', 'G_Identity_RTW', 'H_References', 'I_DBS',
                    'J_Induction_Shadowing_Observations', 'L_Contract', 'N_Training', 'O_Other'].map((category) => {
                    const categoryItems = complianceRequirements.requirements.filter(req => req.category === category);
                    if (categoryItems.length === 0) return null;
                    
                    const categoryLabel = category.replace(/_/g, ' ').replace(/^[A-Z]_/, '');
                    const completedInCategory = categoryItems.filter(i => i.status === 'completed').length;
                    const verifiedInCategory = categoryItems.filter(i => i.verified).length;
                    
                    return (
                      <div key={category}>
                        <div className="flex items-center justify-between mb-3">
                          <h3 className="font-semibold text-text-primary">{categoryLabel}</h3>
                          <span className="text-xs text-text-muted">
                            {completedInCategory}/{categoryItems.length} complete
                            {verifiedInCategory > 0 && ` (${verifiedInCategory} verified)`}
                          </span>
                        </div>
                        <div className="space-y-2">
                          {categoryItems.map((req) => {
                            const docs = req.documents || [];
                            const hasFiles = docs.length > 0;
                            const verifiedDocs = docs.filter(d => d.verified);
                            const allVerified = hasFiles && verifiedDocs.length === docs.length;
                            
                            return (
                            <div 
                              key={req.id} 
                              className={`flex items-center justify-between p-3 rounded-xl border ${
                                allVerified || req.verified ? 'bg-success/5 border-success/20' :
                                req.status === 'completed' ? 'bg-info/5 border-info/20' :
                                req.status === 'in_progress' || req.status === 'pending' ? 'bg-warning/5 border-warning/20' :
                                'bg-error/5 border-error/20'
                              }`}
                            >
                              <div className="flex items-center gap-3">
                                {allVerified || req.verified ? (
                                  <Shield className="h-5 w-5 text-success" />
                                ) : req.status === 'completed' ? (
                                  <CheckCircle className="h-5 w-5 text-info" />
                                ) : req.status === 'in_progress' || req.status === 'pending' ? (
                                  <Clock className="h-5 w-5 text-warning" />
                                ) : (
                                  <XCircle className="h-5 w-5 text-error" />
                                )}
                                <div>
                                  <p className="font-medium text-text-primary">
                                    {req.name}
                                    {req.allow_multiple_files && docs.length > 0 && (
                                      <span className="ml-2 text-xs bg-primary/10 text-primary px-1.5 py-0.5 rounded">
                                        {docs.length} file{docs.length !== 1 ? 's' : ''}
                                      </span>
                                    )}
                                  </p>
                                  {docs.length > 0 && (
                                    <div className="text-xs text-text-muted space-y-0.5 mt-1">
                                      {docs.slice(0, 3).map((doc, idx) => (
                                        <p key={doc.id} className="flex items-center gap-1">
                                          <FileText className="h-3 w-3" />
                                          {doc.document_label || doc.original_filename || 'Document uploaded'}
                                          {doc.verified && <CheckCircle className="h-3 w-3 text-success" />}
                                        </p>
                                      ))}
                                      {docs.length > 3 && (
                                        <p className="text-primary">+{docs.length - 3} more</p>
                                      )}
                                    </div>
                                  )}
                                  {req.form && (
                                    <p className="text-xs text-text-muted flex items-center gap-1">
                                      <ClipboardList className="h-3 w-3" />
                                      Form: {req.form.status.replace('_', ' ')}
                                    </p>
                                  )}
                                  {req.training && (
                                    <p className="text-xs text-text-muted flex items-center gap-1">
                                      <GraduationCap className="h-3 w-3" />
                                      Training: {req.training.status.replace('_', ' ')}
                                    </p>
                                  )}
                                </div>
                              </div>
                              <div className="flex items-center gap-2">
                                <span className={`px-2 py-1 rounded-lg text-xs font-medium ${
                                  allVerified || req.verified ? 'bg-success/10 text-success' :
                                  req.status === 'completed' ? 'bg-info/10 text-info' :
                                  req.status === 'in_progress' || req.status === 'pending' ? 'bg-warning/10 text-warning' :
                                  'bg-error/10 text-error'
                                }`}>
                                  {allVerified || req.verified ? 'Verified' :
                                   req.status === 'completed' ? 'Complete' :
                                   req.status === 'pending' ? 'Pending' :
                                   req.status === 'in_progress' ? 'In Progress' :
                                   'Missing'}
                                </span>
                                {docs.length === 0 && req.type === 'document' && (
                                  <Button 
                                    size="sm" 
                                    variant="outline"
                                    onClick={() => { setSelectedRequirement(req.id); setUploadDialogOpen(true); }}
                                    className="text-xs h-7 rounded-lg"
                                  >
                                    <Upload className="h-3 w-3 mr-1" />
                                    Upload
                                  </Button>
                                )}
                                {docs.length > 0 && !allVerified && req.status === 'completed' && (
                                  <Button 
                                    size="sm" 
                                    variant="outline"
                                    onClick={() => handleVerifyRequirement(req.id)}
                                    className="text-xs h-7 text-success border-success hover:bg-success/10 rounded-lg"
                                  >
                                    <Shield className="h-3 w-3 mr-1" />
                                    Verify All
                                  </Button>
                                )}
                              </div>
                            </div>
                          )})}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Documents Tab - Requirement-based view (supports multi-file requirements) */}
        <TabsContent value="documents">
          <Card className="border-[#E4E8EB] shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between border-b border-[#E4E8EB]">
              <div>
                <CardTitle className="font-heading text-lg">Document Requirements</CardTitle>
                <p className="text-sm text-text-muted mt-1">
                  Upload documents for each requirement. Multi-file requirements accept multiple files.
                </p>
              </div>
              {complianceRequirements && (
                <div className="flex items-center gap-3 text-sm">
                  <span className="text-text-muted">
                    {complianceRequirements.requirements.filter(r => (r.type === 'document') && r.document_count > 0).length} / {complianceRequirements.requirements.filter(r => r.type === 'document').length} requirements with files
                  </span>
                </div>
              )}
            </CardHeader>
            <CardContent className="p-0">
              {!complianceRequirements ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="h-8 w-8 animate-spin text-primary" />
                </div>
              ) : (
                <div className="divide-y divide-[#E4E8EB]">
                  {complianceRequirements.requirements
                    .filter(req => req.type === 'document' || req.type === 'db_record')
                    .map((req) => {
                      const docs = req.documents || [];
                      const hasFiles = docs.length > 0;
                      const verifiedDocs = docs.filter(d => d.verified);
                      const allVerified = hasFiles && verifiedDocs.length === docs.length && docs.length >= (req.min_files || 1);
                      const isComplete = req.status === 'completed';
                      
                      return (
                        <div key={req.id} className={`p-4 ${
                          !hasFiles ? 'bg-error/5' : 
                          allVerified ? 'bg-success/5' : ''
                        }`}>
                          {/* Requirement Header Row */}
                          <div className="flex items-start justify-between mb-2">
                            <div className="flex-1">
                              <div className="flex items-center gap-2">
                                <p className="font-medium text-text-primary">{req.name}</p>
                                {req.allow_multiple_files && (
                                  <span className="text-xs bg-info/10 text-info px-1.5 py-0.5 rounded">
                                    Multi-file
                                  </span>
                                )}
                                {docs.length > 0 && (
                                  <span className="text-xs bg-primary/10 text-primary px-1.5 py-0.5 rounded">
                                    {docs.length} file{docs.length !== 1 ? 's' : ''}
                                  </span>
                                )}
                              </div>
                              <p className="text-xs text-text-muted mt-0.5">
                                {req.category?.replace(/_/g, ' ').replace(/^[A-Z]_/, '')}
                                {req.min_files > 1 && ` • Min ${req.min_files} files required`}
                              </p>
                            </div>
                            <div className="flex items-center gap-2">
                              {/* Status Badge */}
                              <span className={`px-2 py-1 rounded-lg text-xs font-medium ${
                                allVerified ? 'bg-success/10 text-success' :
                                isComplete ? 'bg-info/10 text-info' :
                                hasFiles ? 'bg-warning/10 text-warning' :
                                'bg-error/10 text-error'
                              }`}>
                                {allVerified ? 'Verified' :
                                 isComplete ? 'Complete' :
                                 hasFiles ? 'In Progress' :
                                 'Missing'}
                              </span>
                              
                              {/* Action Buttons */}
                              {!isAuditor() && (
                                <>
                                  {hasFiles && !allVerified && isComplete && (
                                    <Button 
                                      size="sm" 
                                      variant="outline"
                                      onClick={() => handleVerifyRequirement(req.id)}
                                      className="text-xs h-7 text-success border-success hover:bg-success/10 rounded-lg"
                                      data-testid={`verify-all-${req.id}`}
                                    >
                                      <Shield className="h-3 w-3 mr-1" />
                                      Verify All
                                    </Button>
                                  )}
                                  <Button 
                                    size="sm" 
                                    variant={hasFiles && !req.allow_multiple_files ? "ghost" : "default"}
                                    className={hasFiles && !req.allow_multiple_files ? "text-text-muted rounded-lg h-7 text-xs" : "bg-primary hover:bg-primary-hover text-white rounded-lg h-7 text-xs"}
                                    onClick={() => { setSelectedRequirement(req.id); setUploadDialogOpen(true); }}
                                    data-testid={`upload-btn-${req.id}`}
                                  >
                                    <Upload className="h-3 w-3 mr-1" />
                                    {!hasFiles ? 'Upload' : req.allow_multiple_files ? 'Add File' : 'Replace'}
                                  </Button>
                                </>
                              )}
                            </div>
                          </div>
                          
                          {/* Files List */}
                          {docs.length > 0 && (
                            <div className="mt-3 space-y-2">
                              {docs.map((doc, idx) => (
                                <div 
                                  key={doc.id} 
                                  className={`flex items-center justify-between p-3 rounded-lg border ${
                                    doc.verified ? 'border-success/30 bg-success/5' : 'border-[#E4E8EB] bg-white'
                                  }`}
                                >
                                  <div className="flex items-center gap-3 flex-1 min-w-0">
                                    <FileText className="h-5 w-5 text-text-muted flex-shrink-0" />
                                    <div className="min-w-0">
                                      <p className="text-sm font-medium text-text-primary truncate">
                                        {doc.document_label || doc.original_filename || 'Document'}
                                      </p>
                                      <div className="flex items-center gap-2 text-xs text-text-muted">
                                        {doc.version_number > 1 && (
                                          <span className="text-primary">v{doc.version_number}</span>
                                        )}
                                        {doc.source_type && (
                                          <span>
                                            {doc.source_type === 'form_submission' ? 'From Form' : 
                                             doc.source_type === 'imported' ? 'Imported' : 'Manual'}
                                          </span>
                                        )}
                                        {doc.uploaded_at && (
                                          <span>{new Date(doc.uploaded_at).toLocaleDateString()}</span>
                                        )}
                                        {doc.verified && (
                                          <span className="flex items-center gap-1 text-success">
                                            <Shield className="h-3 w-3" />
                                            Verified
                                          </span>
                                        )}
                                      </div>
                                    </div>
                                  </div>
                                  
                                  {/* File Actions */}
                                  <div className="flex items-center gap-1">
                                    {doc.file_url && (
                                      <>
                                        <Button 
                                          size="sm" 
                                          variant="ghost"
                                          className="h-8 w-8 p-0 rounded-lg"
                                          onClick={() => handlePreviewDocument(
                                            `${API}/employee-documents/${doc.id}/file`,
                                            doc.document_type,
                                            doc.original_filename
                                          )}
                                          title="View"
                                        >
                                          <Eye className="h-4 w-4" />
                                        </Button>
                                        <Button 
                                          size="sm" 
                                          variant="ghost"
                                          className="h-8 w-8 p-0 rounded-lg"
                                          onClick={async () => {
                                            try {
                                              const response = await axios.get(`${API}/employee-documents/${doc.id}/download`, {
                                                headers: { Authorization: `Bearer ${token}` },
                                                responseType: 'blob'
                                              });
                                              const blob = new Blob([response.data]);
                                              const url = URL.createObjectURL(blob);
                                              const link = document.createElement('a');
                                              link.href = url;
                                              link.download = doc.original_filename || 'document';
                                              link.click();
                                              URL.revokeObjectURL(url);
                                              toast.success('Downloaded');
                                            } catch (error) {
                                              toast.error('Failed to download');
                                            }
                                          }}
                                          title="Download"
                                        >
                                          <FileDown className="h-4 w-4" />
                                        </Button>
                                      </>
                                    )}
                                    {!isAuditor() && doc.status === 'uploaded' && (
                                      <>
                                        <Button 
                                          size="sm" 
                                          variant="ghost"
                                          className="h-8 w-8 p-0 rounded-lg text-success hover:bg-success/10"
                                          onClick={() => handleUpdateDocumentStatus(doc.id, 'approved')}
                                          title="Approve"
                                        >
                                          <CheckCircle className="h-4 w-4" />
                                        </Button>
                                        <Button 
                                          size="sm" 
                                          variant="ghost"
                                          className="h-8 w-8 p-0 rounded-lg text-error hover:bg-error/10"
                                          onClick={() => handleUpdateDocumentStatus(doc.id, 'rejected')}
                                          title="Reject"
                                        >
                                          <XCircle className="h-4 w-4" />
                                        </Button>
                                      </>
                                    )}
                                    {!isAuditor() && doc.status === 'approved' && !doc.verified && (
                                      <Button 
                                        size="sm" 
                                        variant="ghost"
                                        className="h-8 w-8 p-0 rounded-lg text-success hover:bg-success/10"
                                        onClick={() => handleVerifyDocument(doc.id)}
                                        title="Verify"
                                      >
                                        <Shield className="h-4 w-4" />
                                      </Button>
                                    )}
                                    {!isAuditor() && doc.verified && (
                                      <Button 
                                        size="sm" 
                                        variant="ghost"
                                        className="h-8 w-8 p-0 rounded-lg text-text-muted hover:text-error"
                                        onClick={() => handleUnverifyDocument(doc.id)}
                                        title="Remove verification"
                                      >
                                        <XCircle className="h-4 w-4" />
                                      </Button>
                                    )}
                                    {!isAuditor() && req.allow_multiple_files && (
                                      <Button 
                                        size="sm" 
                                        variant="ghost"
                                        className="h-8 w-8 p-0 rounded-lg text-text-muted hover:text-error hover:bg-error/10"
                                        onClick={() => {
                                          if (window.confirm('Delete this file?')) {
                                            handleDeleteDocument(doc.id);
                                          }
                                        }}
                                        title="Delete file"
                                      >
                                        <Trash2 className="h-4 w-4" />
                                      </Button>
                                    )}
                                  </div>
                                </div>
                              ))}
                            </div>
                          )}
                          
                          {/* Empty State for Missing Files */}
                          {!hasFiles && (
                            <div className="mt-2 p-3 rounded-lg border border-dashed border-error/30 bg-error/5 text-center">
                              <p className="text-sm text-error">No files uploaded</p>
                            </div>
                          )}
                        </div>
                      );
                    })}
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
        <DialogContent className="sm:max-w-lg max-h-[90vh] overflow-y-auto bg-white">
          <DialogHeader>
            <DialogTitle className="font-heading flex items-center gap-2 text-gray-900">
              <Edit className="h-5 w-5 text-teal-600" />
              Edit Employee Details
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 mt-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label className="text-gray-700 font-medium">First Name *</Label>
                <Input
                  value={editForm.first_name}
                  onChange={(e) => setEditForm({...editForm, first_name: e.target.value})}
                  className="rounded-xl bg-gray-50 border-gray-300 text-gray-900 placeholder:text-gray-400 focus:ring-2 focus:ring-teal-600 focus:border-teal-600"
                />
              </div>
              <div className="space-y-2">
                <Label className="text-gray-700 font-medium">Last Name *</Label>
                <Input
                  value={editForm.last_name}
                  onChange={(e) => setEditForm({...editForm, last_name: e.target.value})}
                  className="rounded-xl bg-gray-50 border-gray-300 text-gray-900 placeholder:text-gray-400 focus:ring-2 focus:ring-teal-600 focus:border-teal-600"
                />
              </div>
            </div>
            
            <div className="space-y-2">
              <Label className="text-gray-700 font-medium">Email *</Label>
              <Input
                type="email"
                value={editForm.email}
                onChange={(e) => setEditForm({...editForm, email: e.target.value})}
                className="rounded-xl bg-gray-50 border-gray-300 text-gray-900 placeholder:text-gray-400 focus:ring-2 focus:ring-teal-600 focus:border-teal-600"
              />
            </div>
            
            <div className="space-y-2">
              <Label className="text-gray-700 font-medium">Phone</Label>
              <Input
                type="tel"
                value={editForm.phone}
                onChange={(e) => setEditForm({...editForm, phone: e.target.value})}
                className="rounded-xl bg-gray-50 border-gray-300 text-gray-900 placeholder:text-gray-400 focus:ring-2 focus:ring-teal-600 focus:border-teal-600"
              />
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label className="text-gray-700 font-medium">Role *</Label>
                <Select value={editForm.role} onValueChange={(value) => setEditForm({...editForm, role: value})}>
                  <SelectTrigger className="rounded-xl bg-gray-50 border-gray-300 text-gray-900 focus:ring-2 focus:ring-teal-600 focus:border-teal-600">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-white border-gray-200">
                    {roles.map((role) => (
                      <SelectItem key={role} value={role} className="text-gray-900">{role}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label className="text-gray-700 font-medium">Status</Label>
                <Select value={editForm.status} onValueChange={(value) => setEditForm({...editForm, status: value})}>
                  <SelectTrigger className="rounded-xl bg-gray-50 border-gray-300 text-gray-900 focus:ring-2 focus:ring-teal-600 focus:border-teal-600">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-white border-gray-200">
                    {statuses.map((s) => (
                      <SelectItem key={s.value} value={s.value} className="text-gray-900">{s.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label className="text-gray-700 font-medium">Onboarding Status</Label>
                <Select value={editForm.onboarding_status} onValueChange={(value) => setEditForm({...editForm, onboarding_status: value})}>
                  <SelectTrigger className="rounded-xl bg-gray-50 border-gray-300 text-gray-900 focus:ring-2 focus:ring-teal-600 focus:border-teal-600">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-white border-gray-200">
                    {onboardingStatuses.map((s) => (
                      <SelectItem key={s} value={s} className="text-gray-900">{s}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label className="text-gray-700 font-medium">Start Date</Label>
                <Input
                  type="date"
                  value={editForm.start_date}
                  onChange={(e) => setEditForm({...editForm, start_date: e.target.value})}
                  className="rounded-xl bg-gray-50 border-gray-300 text-gray-900 focus:ring-2 focus:ring-teal-600 focus:border-teal-600"
                />
              </div>
            </div>
            
            <div className="space-y-2">
              <Label className="text-gray-700 font-medium">Notes</Label>
              <Textarea
                value={editForm.notes}
                onChange={(e) => setEditForm({...editForm, notes: e.target.value})}
                placeholder="Internal notes about this employee..."
                className="rounded-xl min-h-[80px] bg-gray-50 border-gray-300 text-gray-900 placeholder:text-gray-400 focus:ring-2 focus:ring-teal-600 focus:border-teal-600"
              />
            </div>
          </div>
          <DialogFooter className="mt-6">
            <Button variant="outline" onClick={() => setEditDialogOpen(false)} className="rounded-xl border-gray-300 text-gray-700 hover:bg-gray-50">
              Cancel
            </Button>
            <Button onClick={handleSaveEmployee} disabled={isSaving} className="bg-teal-600 hover:bg-teal-700 text-white rounded-xl">
              {isSaving ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Save className="h-4 w-4 mr-2" />}
              Save Changes
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Archive Confirmation Dialog */}
      <Dialog open={archiveDialogOpen} onOpenChange={setArchiveDialogOpen}>
        <DialogContent className="bg-white">
          <DialogHeader>
            <DialogTitle className="font-heading flex items-center gap-2 text-gray-900">
              <Archive className="h-5 w-5 text-amber-500" />
              Archive Employee
            </DialogTitle>
            <DialogDescription className="text-gray-500">
              Are you sure you want to archive <strong className="text-gray-900">{employee?.first_name} {employee?.last_name}</strong>?
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
              Are you sure you want to <strong className="text-gray-900">permanently delete</strong> {employee?.first_name} {employee?.last_name}?
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

      {/* Document Preview Modal */}
      <DocumentPreviewModal
        isOpen={previewOpen}
        onClose={() => setPreviewOpen(false)}
        fileUrl={previewFile?.url}
        fileName={previewFile?.name}
        token={token}
        onDownload={previewFile ? async () => {
          try {
            const downloadUrl = previewFile.url.replace('/file', '/download');
            const response = await axios.get(downloadUrl, {
              headers: { Authorization: `Bearer ${token}` },
              responseType: 'blob'
            });
            const blob = new Blob([response.data]);
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = previewFile.filename || 'document';
            link.click();
            URL.revokeObjectURL(url);
            toast.success('Document downloaded');
          } catch (error) {
            toast.error('Failed to download');
          }
        } : undefined}
      />
    </div>
  );
}
