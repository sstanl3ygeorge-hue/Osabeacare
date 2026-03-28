import { useState, useEffect, useRef } from 'react';
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
  Download, RefreshCw, FileArchive, FileSpreadsheet, Printer, FilePdf,
  Camera, Replace, FileX
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
  
  // Training completion dialog states
  const [trainingDialogOpen, setTrainingDialogOpen] = useState(false);
  const [selectedTrainingReq, setSelectedTrainingReq] = useState(null);
  const [trainingExpiryDate, setTrainingExpiryDate] = useState('');
  const [isCompletingTraining, setIsCompletingTraining] = useState(false);
  
  // Training certificate upload states
  const [trainingCertDialogOpen, setTrainingCertDialogOpen] = useState(false);
  const [trainingCertFile, setTrainingCertFile] = useState(null);
  const [isUploadingCert, setIsUploadingCert] = useState(false);
  const [isVerifyingTraining, setIsVerifyingTraining] = useState(false);
  
  // Profile photo upload state
  const [isUploadingPhoto, setIsUploadingPhoto] = useState(false);
  const [profilePhotoBlob, setProfilePhotoBlob] = useState(null);
  const photoInputRef = useRef(null);
  
  // Evidence edit state
  const [editEvidenceOpen, setEditEvidenceOpen] = useState(false);
  const [editEvidenceData, setEditEvidenceData] = useState(null);
  const [editHistory, setEditHistory] = useState([]);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [isEditingEvidence, setIsEditingEvidence] = useState(false);
  const [editForm, setEditForm] = useState({
    issue_date: '',
    expiry_date: '',
    notes: '',
    file_label: '',
    reason: ''
  });
  
  // File management state
  const [removeDialogOpen, setRemoveDialogOpen] = useState(false);
  const [replaceDialogOpen, setReplaceDialogOpen] = useState(false);
  const [requirementHistoryOpen, setRequirementHistoryOpen] = useState(false);
  const [selectedFileForAction, setSelectedFileForAction] = useState(null);
  const [selectedRequirementForAction, setSelectedRequirementForAction] = useState(null);
  const [removeReason, setRemoveReason] = useState('');
  const [replaceReason, setReplaceReason] = useState('');
  const [replaceFile, setReplaceFile] = useState(null);
  const [isRemoving, setIsRemoving] = useState(false);
  const [isReplacing, setIsReplacing] = useState(false);
  const [requirementHistory, setRequirementHistory] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  
  const { token, isAuditor, user } = useAuth();
  
  // Document preview modal state
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewFile, setPreviewFile] = useState(null);
  const [previewFiles, setPreviewFiles] = useState([]); // For multi-file navigation
  
  // Sync tab changes to URL
  const handleTabChange = (value) => {
    setActiveTab(value);
    setSearchParams({ tab: value }, { replace: true });
  };
  
  // Open document in preview modal - supports single file or array
  const handlePreviewDocument = (url, name, filename) => {
    setPreviewFile({ url, name, filename });
    setPreviewFiles([]); // Clear multi-file array
    setPreviewOpen(true);
  };
  
  // Open multiple files in preview modal with navigation
  const handlePreviewMultipleFiles = (files, requirementId) => {
    if (!files || files.length === 0) return;
    
    // Build array of file objects for the modal
    const fileArray = files.map(f => ({
      url: `${API}/employees/${employeeId}/requirements/${requirementId}/evidence/${f.file_id}/view`,
      filename: f.file_label || f.original_filename || 'Document',
      content_type: f.content_type,
      file_id: f.file_id
    }));
    
    setPreviewFiles(fileArray);
    setPreviewFile(fileArray[0]); // Set first file as initial
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

  // Fetch profile photo when employee has one
  useEffect(() => {
    const fetchProfilePhoto = async () => {
      if (!employee?.profile_photo_url || !token) {
        setProfilePhotoBlob(null);
        return;
      }
      try {
        const response = await axios.get(
          `${API}/employees/${employeeId}/profile-photo/view`,
          { headers: { Authorization: `Bearer ${token}` }, responseType: 'blob' }
        );
        const blobUrl = URL.createObjectURL(response.data);
        setProfilePhotoBlob(blobUrl);
      } catch (error) {
        console.error('Failed to fetch profile photo:', error);
        setProfilePhotoBlob(null);
      }
    };
    fetchProfilePhoto();
    // Cleanup blob URL on unmount or when employee changes
    return () => {
      if (profilePhotoBlob) {
        URL.revokeObjectURL(profilePhotoBlob);
      }
    };
  }, [employee?.profile_photo_url, employeeId, token]);

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
      toast.error('Please select a requirement and choose a file to upload');
      return;
    }
    
    setIsUploading(true);
    
    try {
      const formData = new FormData();
      formData.append('file', uploadFile);
      if (documentLabel) {
        formData.append('file_label', documentLabel);
      }
      
      // Use the unified evidence upload endpoint
      await axios.post(`${API}/employees/${employeeId}/requirements/${selectedRequirement}/evidence`, formData, {
        headers: { 
          Authorization: `Bearer ${token}`,
          'Content-Type': 'multipart/form-data'
        }
      });
      
      // POST-UPLOAD FEEDBACK - Clear guidance on next step
      toast.success('Document uploaded — please review and approve', {
        duration: 5000,
        description: 'Check the document is clear and correct, then mark as approved.'
      });
      setUploadDialogOpen(false);
      setSelectedRequirement('');
      setSelectedDocType('');
      setDocumentLabel('');
      setUploadFile(null);
      fetchData();
      fetchCompliance();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Upload failed — please try again');
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

  const handleVerifyDocument = async (docId, fileUrl) => {
    try {
      // First check if file is accessible
      if (fileUrl) {
        try {
          // Try to fetch with HEAD request to verify file exists
          await axios.head(fileUrl, {
            headers: { Authorization: `Bearer ${token}` },
            timeout: 10000
          });
        } catch (fileError) {
          toast.error('Cannot verify - file is not accessible. Please re-upload the document.');
          return;
        }
      }
      
      await axios.post(`${API}/employee-documents/${docId}/verify`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Document approved');
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
    // First, check if the file is accessible before allowing verification
    try {
      // Get the requirement data to find file URL
      const req = complianceRequirements?.requirements?.find(r => r.id === requirementId);
      if (!req) {
        toast.error('Requirement not found');
        return;
      }
      
      // Get evidence files
      const evidenceFiles = req.evidence_files || [];
      if (evidenceFiles.length === 0) {
        toast.error('Cannot verify - no evidence file uploaded');
        return;
      }
      
      // Check if at least one file is accessible
      const fileToCheck = evidenceFiles[0];
      if (fileToCheck?.file_id) {
        try {
          const checkUrl = `${API}/employees/${employeeId}/requirements/${requirementId}/evidence/${fileToCheck.file_id}/view`;
          const checkResponse = await axios.head(checkUrl, {
            headers: { Authorization: `Bearer ${token}` },
            timeout: 10000
          });
          // If we get here, file is accessible
        } catch (fileError) {
          toast.error('Cannot verify - file is not accessible. Please re-upload the document.');
          return;
        }
      }
      
      // File is accessible, proceed with verification
      await axios.post(`${API}/employees/${employeeId}/requirements/${requirementId}/verify-all`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Requirement approved');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to verify requirement');
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

  // Open remove file dialog
  const openRemoveDialog = (file, requirementId) => {
    setSelectedFileForAction(file);
    setSelectedRequirementForAction(requirementId);
    setRemoveReason('');
    setRemoveDialogOpen(true);
  };

  // Handle soft-remove file
  const handleRemoveFile = async () => {
    if (!removeReason.trim() || removeReason.trim().length < 3) {
      toast.error('Please provide a reason (minimum 3 characters)');
      return;
    }

    setIsRemoving(true);
    try {
      await axios.post(
        `${API}/employees/${employeeId}/requirements/${selectedRequirementForAction}/evidence/${selectedFileForAction.file_id}/remove`,
        { reason: removeReason.trim() },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('File removed successfully');
      setRemoveDialogOpen(false);
      setSelectedFileForAction(null);
      setSelectedRequirementForAction(null);
      setRemoveReason('');
      fetchData();
      fetchCompliance();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to remove file');
    } finally {
      setIsRemoving(false);
    }
  };

  // Open replace file dialog
  const openReplaceDialog = (file, requirementId) => {
    setSelectedFileForAction(file);
    setSelectedRequirementForAction(requirementId);
    setReplaceReason('');
    setReplaceFile(null);
    setReplaceDialogOpen(true);
  };

  // Handle replace file
  const handleReplaceFile = async () => {
    if (!replaceReason.trim() || replaceReason.trim().length < 3) {
      toast.error('Please provide a reason (minimum 3 characters)');
      return;
    }
    if (!replaceFile) {
      toast.error('Please select a replacement file');
      return;
    }

    setIsReplacing(true);
    try {
      const formData = new FormData();
      formData.append('file', replaceFile);
      formData.append('reason', replaceReason.trim());
      
      await axios.post(
        `${API}/employees/${employeeId}/requirements/${selectedRequirementForAction}/evidence/${selectedFileForAction.file_id}/replace`,
        formData,
        { 
          headers: { 
            Authorization: `Bearer ${token}`,
            'Content-Type': 'multipart/form-data'
          }
        }
      );
      toast.success('File replaced successfully');
      setReplaceDialogOpen(false);
      setSelectedFileForAction(null);
      setSelectedRequirementForAction(null);
      setReplaceReason('');
      setReplaceFile(null);
      fetchData();
      fetchCompliance();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to replace file');
    } finally {
      setIsReplacing(false);
    }
  };

  // Fetch requirement history
  const fetchRequirementHistory = async (requirementId) => {
    setLoadingHistory(true);
    try {
      const response = await axios.get(
        `${API}/employees/${employeeId}/requirements/${requirementId}/history`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setRequirementHistory(response.data.history || []);
    } catch (error) {
      console.error('Failed to fetch history:', error);
      setRequirementHistory([]);
    } finally {
      setLoadingHistory(false);
    }
  };

  // Open requirement history dialog
  const openHistoryDialog = (requirementId) => {
    setSelectedRequirementForAction(requirementId);
    setRequirementHistoryOpen(true);
    fetchRequirementHistory(requirementId);
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

  // Handle completing a training requirement
  const handleCompleteTraining = async () => {
    if (!selectedTrainingReq) {
      toast.error('No training requirement selected');
      return;
    }
    
    setIsCompletingTraining(true);
    
    try {
      const response = await axios.post(
        `${API}/employees/${employeeId}/complete-training`,
        {
          requirement_id: selectedTrainingReq.id,
          expiry_date: trainingExpiryDate || null
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      toast.success(response.data.message || 'Training marked as complete');
      setTrainingDialogOpen(false);
      setSelectedTrainingReq(null);
      setTrainingExpiryDate('');
      fetchData();
      fetchCompliance();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to complete training');
    } finally {
      setIsCompletingTraining(false);
    }
  };
  
  // Open training completion dialog
  const openTrainingDialog = (requirement) => {
    setSelectedTrainingReq(requirement);
    setTrainingExpiryDate('');
    setTrainingDialogOpen(true);
  };
  
  // Open training certificate upload dialog
  const openTrainingCertDialog = (requirement) => {
    setSelectedTrainingReq(requirement);
    setTrainingExpiryDate('');
    setTrainingCertFile(null);
    setTrainingCertDialogOpen(true);
  };
  
  // Handle uploading training certificate
  const handleUploadTrainingCertificate = async () => {
    if (!selectedTrainingReq || !trainingCertFile) {
      toast.error('Please select a certificate file');
      return;
    }
    
    setIsUploadingCert(true);
    
    try {
      const formData = new FormData();
      formData.append('file', trainingCertFile);
      if (trainingExpiryDate) {
        formData.append('expiry_date', trainingExpiryDate);
      }
      
      const response = await axios.post(
        `${API}/employees/${employeeId}/training/${selectedTrainingReq.id}/upload-certificate`,
        formData,
        { 
          headers: { 
            Authorization: `Bearer ${token}`,
            'Content-Type': 'multipart/form-data'
          } 
        }
      );
      
      toast.success(response.data.message || 'Certificate uploaded successfully');
      setTrainingCertDialogOpen(false);
      setSelectedTrainingReq(null);
      setTrainingCertFile(null);
      setTrainingExpiryDate('');
      fetchData();
      fetchCompliance();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to upload certificate');
    } finally {
      setIsUploadingCert(false);
    }
  };
  
  // Handle verifying training
  const handleVerifyTraining = async (trainingId) => {
    setIsVerifyingTraining(true);
    try {
      await axios.post(
        `${API}/training-records/${trainingId}/verify`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Training verified successfully');
      fetchData();
      fetchCompliance();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to verify training');
    } finally {
      setIsVerifyingTraining(false);
    }
  };
  
  // Handle unverifying training
  const handleUnverifyTraining = async (trainingId) => {
    try {
      await axios.post(
        `${API}/training-records/${trainingId}/unverify`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Training verification removed');
      fetchData();
      fetchCompliance();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to remove verification');
    }
  };
  
  // View training certificate
  const handleViewTrainingCertificate = (trainingId, filename) => {
    const url = `${API}/training-records/${trainingId}/certificate/file`;
    setPreviewFile({ url, name: filename || 'Certificate', filename: filename });
    setPreviewOpen(true);
  };
  
  // Download training certificate
  const handleDownloadTrainingCertificate = async (trainingId, filename) => {
    try {
      const response = await axios.get(
        `${API}/training-records/${trainingId}/certificate/download`,
        {
          headers: { Authorization: `Bearer ${token}` },
          responseType: 'blob'
        }
      );
      const blob = new Blob([response.data]);
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename || 'training_certificate';
      link.click();
      URL.revokeObjectURL(url);
      toast.success('Certificate downloaded');
    } catch (error) {
      toast.error('Failed to download certificate');
    }
  };

  // Profile photo upload handler
  const handlePhotoUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    // Validate file type
    const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp'];
    if (!allowedTypes.includes(file.type)) {
      toast.error('Only JPG, PNG, and WEBP images are allowed');
      return;
    }
    
    // Validate file size (5MB max)
    if (file.size > 5 * 1024 * 1024) {
      toast.error('Image must be less than 5MB');
      return;
    }
    
    setIsUploadingPhoto(true);
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      await axios.post(
        `${API}/employees/${employeeId}/profile-photo`,
        formData,
        {
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'multipart/form-data'
          }
        }
      );
      toast.success('Profile photo uploaded');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to upload photo');
    } finally {
      setIsUploadingPhoto(false);
      if (photoInputRef.current) photoInputRef.current.value = '';
    }
  };

  // Remove profile photo handler
  const handleRemovePhoto = async () => {
    try {
      await axios.delete(
        `${API}/employees/${employeeId}/profile-photo`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Profile photo removed');
      fetchData();
    } catch (error) {
      toast.error('Failed to remove photo');
    }
  };

  // Open edit evidence modal
  const openEditEvidence = (reqId, fileData) => {
    setEditEvidenceData({ 
      requirementId: reqId, 
      file: fileData 
    });
    setEditForm({
      issue_date: fileData.issue_date || '',
      expiry_date: fileData.expiry_date || '',
      notes: fileData.notes || '',
      file_label: fileData.file_label || fileData.original_filename || '',
      reason: ''
    });
    setEditEvidenceOpen(true);
  };

  // Save evidence edits
  const handleSaveEvidenceEdit = async () => {
    if (!editForm.reason || editForm.reason.trim().length < 3) {
      toast.error('Please provide a reason for this change (min 3 characters)');
      return;
    }
    
    setIsEditingEvidence(true);
    try {
      await axios.put(
        `${API}/employees/${employeeId}/requirements/${editEvidenceData.requirementId}/evidence/${editEvidenceData.file.file_id}`,
        {
          issue_date: editForm.issue_date || null,
          expiry_date: editForm.expiry_date || null,
          notes: editForm.notes || null,
          file_label: editForm.file_label || null,
          reason: editForm.reason
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Document details updated');
      setEditEvidenceOpen(false);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update details');
    } finally {
      setIsEditingEvidence(false);
    }
  };

  // Load evidence edit history
  const loadEditHistory = async (reqId, fileId) => {
    try {
      const response = await axios.get(
        `${API}/employees/${employeeId}/requirements/${reqId}/evidence/${fileId}/history`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setEditHistory(response.data);
      setHistoryOpen(true);
    } catch (error) {
      toast.error('Failed to load history');
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
              {/* Profile Photo with Upload */}
              <div className="relative group">
                {profilePhotoBlob ? (
                  <img 
                    src={profilePhotoBlob} 
                    alt={`${employee.first_name} ${employee.last_name}`}
                    className="w-16 h-16 rounded-2xl object-cover border-2 border-[#E4E8EB]"
                    data-testid="profile-photo"
                  />
                ) : (
                  <div className="w-16 h-16 bg-accent rounded-2xl flex items-center justify-center">
                    <span className="text-primary font-heading font-bold text-xl">
                      {employee.first_name?.charAt(0)}{employee.last_name?.charAt(0)}
                    </span>
                  </div>
                )}
                {/* Upload/Edit overlay */}
                {!isAuditor() && (
                  <div className="absolute inset-0 bg-black/50 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                    <label className="cursor-pointer p-2">
                      <input
                        ref={photoInputRef}
                        type="file"
                        accept="image/jpeg,image/jpg,image/png,image/webp"
                        onChange={handlePhotoUpload}
                        className="hidden"
                        disabled={isUploadingPhoto}
                      />
                      {isUploadingPhoto ? (
                        <Loader2 className="h-5 w-5 text-white animate-spin" />
                      ) : (
                        <Camera className="h-5 w-5 text-white" />
                      )}
                    </label>
                    {employee.profile_photo_url && (
                      <button
                        onClick={handleRemovePhoto}
                        className="p-2 hover:bg-white/20 rounded-lg"
                        title="Remove photo"
                      >
                        <XCircle className="h-4 w-4 text-white" />
                      </button>
                    )}
                  </div>
                )}
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
                          {/* Group requirements by type for clarity */}
                          {complianceRequirements?.requirements && (
                            <>
                              {/* Documents (employee-submitted) */}
                              <div className="px-2 py-1.5 text-xs font-semibold text-text-muted bg-gray-50">Documents</div>
                              {complianceRequirements.requirements
                                .filter(req => req.type === 'document' && req.source === 'employee')
                                .map((req) => (
                                  <SelectItem key={req.id} value={req.id}>
                                    <div className="flex items-center gap-2">
                                      <span className={`w-2 h-2 rounded-full ${
                                        req.has_evidence ? 'bg-success' : 'bg-gray-300'
                                      }`} />
                                      {req.name}
                                      {req.evidence_count > 0 && <span className="text-xs text-text-muted">({req.evidence_count})</span>}
                                    </div>
                                  </SelectItem>
                                ))}
                              
                              {/* Internal Checks */}
                              <div className="px-2 py-1.5 text-xs font-semibold text-text-muted bg-gray-50 mt-1">Internal Checks</div>
                              {complianceRequirements.requirements
                                .filter(req => req.type === 'document' && req.source === 'internal')
                                .map((req) => (
                                  <SelectItem key={req.id} value={req.id}>
                                    <div className="flex items-center gap-2">
                                      <span className={`w-2 h-2 rounded-full ${
                                        req.has_evidence ? 'bg-success' : 'bg-gray-300'
                                      }`} />
                                      {req.name}
                                      <span className="text-[10px] bg-purple-100 text-purple-700 px-1 rounded">Internal</span>
                                      {req.evidence_count > 0 && <span className="text-xs text-text-muted">({req.evidence_count})</span>}
                                    </div>
                                  </SelectItem>
                                ))}
                              
                              {/* Forms */}
                              <div className="px-2 py-1.5 text-xs font-semibold text-text-muted bg-gray-50 mt-1">Forms</div>
                              {complianceRequirements.requirements
                                .filter(req => req.type === 'form-generated')
                                .map((req) => (
                                  <SelectItem key={req.id} value={req.id}>
                                    <div className="flex items-center gap-2">
                                      <span className={`w-2 h-2 rounded-full ${
                                        req.has_evidence ? 'bg-success' : 'bg-gray-300'
                                      }`} />
                                      {req.name}
                                      {req.evidence_count > 0 && <span className="text-xs text-text-muted">({req.evidence_count})</span>}
                                    </div>
                                  </SelectItem>
                                ))}
                              
                              {/* Training */}
                              <div className="px-2 py-1.5 text-xs font-semibold text-text-muted bg-gray-50 mt-1">Training Certificates</div>
                              {complianceRequirements.requirements
                                .filter(req => req.type === 'training')
                                .map((req) => (
                                  <SelectItem key={req.id} value={req.id}>
                                    <div className="flex items-center gap-2">
                                      <span className={`w-2 h-2 rounded-full ${
                                        req.has_evidence ? 'bg-success' : 'bg-gray-300'
                                      }`} />
                                      {req.name}
                                      {req.evidence_count > 0 && <span className="text-xs text-text-muted">({req.evidence_count})</span>}
                                    </div>
                                  </SelectItem>
                                ))}
                            </>
                          )}
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

              {/* Generate Forms Dropdown - Hidden for Audit Mode */}
              {/* Forms system hidden from UI. Backend retained for data integrity. */}

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
                      Upload a completed application form and optionally a CV. The form will be stored as uploaded evidence and linked to the employee's compliance checklist.
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
                          Checklist item evidence uploaded automatically
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
                      Upload an existing completed document (Reference letter, Health form, Contract, etc.) to add evidence to the corresponding compliance requirement.
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
                          <SelectItem value="recruitment_checklist">
                            <div className="flex items-center gap-2">
                              <span className="w-2 h-2 rounded-full bg-primary" />
                              Recruitment Compliance Checklist
                            </div>
                          </SelectItem>
                          <SelectItem value="personal_info">
                            <div className="flex items-center gap-2">
                              <span className="w-2 h-2 rounded-full bg-info" />
                              Personal Information Form
                            </div>
                          </SelectItem>
                          <SelectItem value="interview_record">
                            <div className="flex items-center gap-2">
                              <span className="w-2 h-2 rounded-full bg-primary" />
                              Interview Record Form
                            </div>
                          </SelectItem>
                          <SelectItem value="equal_opportunities">
                            <div className="flex items-center gap-2">
                              <span className="w-2 h-2 rounded-full bg-success" />
                              Equal Opportunities Monitoring
                            </div>
                          </SelectItem>
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
                          Checklist requirement evidence uploaded
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
          {/* Forms tab hidden for Audit Mode - forms system hidden from UI */}
          <TabsTrigger value="checklist" className="rounded-lg data-[state=active]:bg-primary data-[state=active]:text-white">
            <CheckCircle className="h-4 w-4 mr-2" />
            What's Needed
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

        {/* Generated Forms Tab - Admin Internal Workflow */}
        <TabsContent value="forms">
          <Card className="border-[#E4E8EB] shadow-sm">
            <CardHeader>
              <CardTitle className="font-heading text-lg flex items-center justify-between">
                <span>Internal Forms (Admin)</span>
                <span className="text-sm font-normal text-text-muted">{generatedForms.length} forms</span>
              </CardTitle>
              <p className="text-sm text-text-muted mt-1">
                Forms are internal workflows. Completed forms generate PDF evidence stored in the checklist.
              </p>
            </CardHeader>
            <CardContent>
              {generatedForms.length === 0 ? (
                <div className="text-center py-8">
                  <ClipboardList className="h-12 w-12 mx-auto text-text-muted/50 mb-3" />
                  <p className="text-text-muted">No internal forms generated yet</p>
                  <p className="text-sm text-text-muted mt-1">Click "Generate Forms" to create internal workflow forms.</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {generatedForms.map((form) => {
                    const isImported = form.status === 'completed_imported' || form.source === 'imported';
                    const hasPdfEvidence = !!form.pdf_url;
                    
                    const statusConfig = {
                      draft: { color: 'bg-gray-100 text-text-muted', label: 'Draft', icon: Clock },
                      sent: { color: 'bg-info/10 text-info', label: 'Sent', icon: Mail },
                      in_progress: { color: 'bg-warning/10 text-warning', label: 'In Progress', icon: Clock },
                      completed: { color: 'bg-info/10 text-info', label: 'Completed', icon: CheckCircle },
                      completed_imported: { color: 'bg-primary/10 text-primary', label: 'Uploaded Evidence', icon: FileText },
                      reviewed: { color: 'bg-warning/10 text-warning', label: 'Reviewed', icon: Eye },
                      signed_off: { color: 'bg-success/10 text-success', label: 'Signed Off', icon: CheckCircle },
                      archived: { color: 'bg-gray-100 text-text-muted', label: 'Archived', icon: FileText }
                    };
                    const config = statusConfig[form.status] || statusConfig.draft;
                    const StatusIcon = config.icon;
                    
                    // For imported forms, show document-first actions instead of navigating to form editor
                    if (isImported) {
                      return (
                        <div 
                          key={form.id} 
                          className="flex items-center justify-between p-4 bg-[#F8FAFA] rounded-xl"
                          data-testid={`form-${form.id}`}
                        >
                          <div className="flex items-center gap-4">
                            <div className="p-2 rounded-lg bg-primary/10">
                              <FileText className="h-5 w-5 text-primary" />
                            </div>
                            <div>
                              <p className="font-medium text-text-primary">{form.template_name}</p>
                              <div className="flex items-center gap-2 text-sm text-text-muted">
                                <span>{form.template_category}</span>
                                <span>•</span>
                                <span>{new Date(form.created_at).toLocaleDateString()}</span>
                                <span>•</span>
                                <span className="text-primary">Uploaded Evidence</span>
                              </div>
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            {hasPdfEvidence ? (
                              <>
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() => {
                                    const viewUrl = `${API}/generated-forms/${form.id}/pdf/file`;
                                    setPreviewFile({ 
                                      url: viewUrl, 
                                      name: form.pdf_filename || form.template_name,
                                      filename: form.pdf_filename 
                                    });
                                    setPreviewOpen(true);
                                  }}
                                  className="text-xs h-8 rounded-lg"
                                  data-testid={`view-form-evidence-${form.id}`}
                                >
                                  <Eye className="h-3 w-3 mr-1" />
                                  View
                                </Button>
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={async () => {
                                    try {
                                      const response = await axios.get(
                                        `${API}/generated-forms/${form.id}/pdf/download`,
                                        { headers: { Authorization: `Bearer ${token}` }, responseType: 'blob' }
                                      );
                                      const blob = new Blob([response.data]);
                                      const url = URL.createObjectURL(blob);
                                      const link = document.createElement('a');
                                      link.href = url;
                                      link.download = form.pdf_filename || `${form.template_name}.pdf`;
                                      link.click();
                                      URL.revokeObjectURL(url);
                                      toast.success('Downloaded');
                                    } catch (e) {
                                      toast.error('Download failed');
                                    }
                                  }}
                                  className="text-xs h-8 rounded-lg"
                                  data-testid={`download-form-evidence-${form.id}`}
                                >
                                  <Download className="h-3 w-3 mr-1" />
                                  Download
                                </Button>
                              </>
                            ) : (
                              <span className="text-xs text-warning flex items-center gap-1">
                                <AlertTriangle className="h-3 w-3" />
                                No file
                              </span>
                            )}
                          </div>
                        </div>
                      );
                    }
                    
                    // Regular forms - show clickable card
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
                            <div className="flex items-center gap-2 text-sm text-text-muted">
                              <span>{form.template_category}</span>
                              <span>•</span>
                              <span>{new Date(form.created_at).toLocaleDateString()}</span>
                              {hasPdfEvidence && (
                                <>
                                  <span>•</span>
                                  <span className="flex items-center gap-1 text-success">
                                    <FileText className="h-3 w-3" />
                                    PDF Generated
                                  </span>
                                </>
                              )}
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className={`px-3 py-1 rounded-full text-xs font-medium ${config.color}`}>
                            {config.label}
                          </span>
                          {/* Warning if no PDF but form is complete */}
                          {['completed', 'signed_off'].includes(form.status) && !hasPdfEvidence && (
                            <span className="flex items-center gap-1 text-warning text-xs">
                              <AlertTriangle className="h-3 w-3" />
                              No PDF
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
                <CardTitle className="font-heading text-lg">Care Status</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-4 bg-success/10 border border-success/20 rounded-xl">
                    <p className="text-sm text-success font-medium">Checked & Approved</p>
                    <p className="text-2xl font-heading font-bold text-success">
                      {complianceRequirements?.summary?.verified || 0}/{complianceRequirements?.summary?.total || 0}
                    </p>
                  </div>
                  <div className="p-4 bg-info/10 border border-info/20 rounded-xl">
                    <p className="text-sm text-info font-medium">Ready for Review</p>
                    <p className="text-2xl font-heading font-bold text-info">
                      {(complianceRequirements?.summary?.completed || 0) - (complianceRequirements?.summary?.verified || 0)}
                    </p>
                  </div>
                  <div className="p-4 bg-error/10 border border-error/20 rounded-xl">
                    <p className="text-sm text-error font-medium">Still Needed</p>
                    <p className="text-2xl font-heading font-bold text-error">
                      {complianceRequirements?.summary?.missing || 0}
                    </p>
                  </div>
                  <div className="p-4 bg-[#F8FAFA] rounded-xl">
                    <p className="text-sm text-text-muted">Policies Signed</p>
                    <p className="text-2xl font-heading font-bold text-text-primary">
                      {policies.filter(p => p.status === 'signed').length}/{policies.length}
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
            complianceRequirements={complianceRequirements}
            isAuditor={isAuditor()}
            onCompleteTraining={(item) => {
              // Map the ComplianceOverview item format to requirement format
              // The trainingType corresponds to the requirement_id in MANDATORY_ITEMS
              const trainingReqMapping = {
                'safeguarding': { id: 'safeguarding', name: 'Safeguarding Training', category: 'N_Training' },
                'manual_handling': { id: 'manual_handling', name: 'Manual Handling Training', category: 'N_Training' },
                'infection_control': { id: 'infection_control', name: 'Infection Control Training', category: 'N_Training' },
                'basic_life_support': { id: 'bls', name: 'Basic Life Support (BLS)', category: 'N_Training' },
                'medication': { id: 'medication_competency', name: 'Medication Competency', category: 'N_Training' },
                'induction': { id: 'induction', name: 'Induction & Competency Assessment', category: 'J_Induction_Shadowing_Observations' }
              };
              const reqData = trainingReqMapping[item.trainingType] || {
                id: item.trainingType || item.id,
                name: item.name,
                category: 'N_Training'
              };
              openTrainingDialog(reqData);
            }}
          />
        </TabsContent>

        {/* What's Needed Tab - Mandatory Items */}
        <TabsContent value="checklist">
          <Card className="border-[#E4E8EB] shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="font-heading text-lg">What's Needed</CardTitle>
                {complianceRequirements && (
                  <p className="text-sm text-text-muted mt-1">
                    {complianceRequirements.summary.verified} approved · {complianceRequirements.summary.completed - complianceRequirements.summary.verified} ready for review · {complianceRequirements.summary.missing} still needed
                  </p>
                )}
              </div>
              {complianceRequirements?.work_readiness && (
                <div className={`flex items-center gap-2 text-sm px-3 py-1.5 rounded-lg font-medium ${
                  complianceRequirements.work_readiness.status === 'fully_compliant' ? 'bg-success/10 text-success' :
                  complianceRequirements.work_readiness.status === 'work_ready' ? 'bg-success/10 text-success' :
                  complianceRequirements.work_readiness.status === 'almost_ready' ? 'bg-warning/10 text-warning' :
                  'bg-error/10 text-error'
                }`}>
                  {complianceRequirements.work_readiness.status === 'fully_compliant' ? (
                    <CheckCircle className="h-4 w-4" />
                  ) : complianceRequirements.work_readiness.status === 'work_ready' ? (
                    <Shield className="h-4 w-4" />
                  ) : (
                    <AlertTriangle className="h-4 w-4" />
                  )}
                  {complianceRequirements.work_readiness.status_label}
                </div>
              )}
            </CardHeader>
            <CardContent>
              {/* WORK READINESS ALERT PANEL */}
              {complianceRequirements?.work_readiness && (
                <div className={`mb-6 p-4 rounded-xl border ${
                  complianceRequirements.work_readiness.is_fully_compliant ? 'bg-green-50 border-green-200' :
                  complianceRequirements.work_readiness.is_work_ready ? 'bg-emerald-50 border-emerald-200' :
                  complianceRequirements.work_readiness.status === 'almost_ready' ? 'bg-amber-50 border-amber-200' :
                  'bg-red-50 border-red-200'
                }`}>
                  <div className="flex items-start gap-3">
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 ${
                      complianceRequirements.work_readiness.is_fully_compliant ? 'bg-green-100' :
                      complianceRequirements.work_readiness.is_work_ready ? 'bg-emerald-100' :
                      complianceRequirements.work_readiness.status === 'almost_ready' ? 'bg-amber-100' :
                      'bg-red-100'
                    }`}>
                      {complianceRequirements.work_readiness.is_fully_compliant ? (
                        <CheckCircle className="h-5 w-5 text-green-600" />
                      ) : complianceRequirements.work_readiness.is_work_ready ? (
                        <Shield className="h-5 w-5 text-emerald-600" />
                      ) : (
                        <AlertTriangle className="h-5 w-5 text-red-600" />
                      )}
                    </div>
                    <div className="flex-1">
                      <h4 className={`font-semibold ${
                        complianceRequirements.work_readiness.is_fully_compliant ? 'text-green-900' :
                        complianceRequirements.work_readiness.is_work_ready ? 'text-emerald-900' :
                        complianceRequirements.work_readiness.status === 'almost_ready' ? 'text-amber-900' :
                        'text-red-900'
                      }`}>
                        Work Readiness Status: {complianceRequirements.work_readiness.status_label}
                      </h4>
                      <p className={`text-sm mt-1 ${
                        complianceRequirements.work_readiness.is_fully_compliant ? 'text-green-800' :
                        complianceRequirements.work_readiness.is_work_ready ? 'text-emerald-800' :
                        complianceRequirements.work_readiness.status === 'almost_ready' ? 'text-amber-800' :
                        'text-red-800'
                      }`}>
                        {complianceRequirements.work_readiness.is_fully_compliant ? (
                          "All compliance requirements are complete and verified. This employee is fully compliant."
                        ) : complianceRequirements.work_readiness.is_work_ready ? (
                          "All mandatory items are verified. This employee can start work."
                        ) : (
                          <>
                            <strong>{complianceRequirements.work_readiness.mandatory?.complete || 0} of {complianceRequirements.work_readiness.mandatory?.total || 0}</strong> required items complete
                          </>
                        )}
                      </p>
                      
                      {/* Missing Mandatory Items */}
                      {complianceRequirements.work_readiness.mandatory?.missing?.length > 0 && (
                        <div className="mt-3">
                          <p className={`text-sm font-medium ${
                            complianceRequirements.work_readiness.status === 'almost_ready' ? 'text-amber-900' : 'text-red-900'
                          }`}>
                            Missing items (required to start work):
                          </p>
                          <ul className={`mt-1 space-y-1 text-sm ${
                            complianceRequirements.work_readiness.status === 'almost_ready' ? 'text-amber-800' : 'text-red-800'
                          }`}>
                            {complianceRequirements.work_readiness.mandatory.missing.map((item, idx) => (
                              <li key={idx} className="flex items-center gap-2">
                                <span className="w-1.5 h-1.5 rounded-full bg-current"></span>
                                {item.name}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* Weighted Score */}
                      <div className="mt-3 flex items-center gap-3">
                        <div className={`text-sm font-medium ${
                          complianceRequirements.work_readiness.weighted_score >= 80 ? 'text-green-700' :
                          complianceRequirements.work_readiness.weighted_score >= 50 ? 'text-amber-700' :
                          'text-red-700'
                        }`}>
                          Compliance Score: {complianceRequirements.work_readiness.weighted_score}%
                        </div>
                        <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
                          <div 
                            className={`h-full rounded-full transition-all ${
                              complianceRequirements.work_readiness.weighted_score >= 80 ? 'bg-green-500' :
                              complianceRequirements.work_readiness.weighted_score >= 50 ? 'bg-amber-500' :
                              'bg-red-500'
                            }`}
                            style={{ width: `${complianceRequirements.work_readiness.weighted_score}%` }}
                          />
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* GLOBAL INSTRUCTION PANEL - CQC Guidance */}
              <div className="mb-6 p-4 bg-blue-50 border border-blue-100 rounded-xl">
                <h3 className="font-semibold text-blue-900 mb-2">Complete Required Items First</h3>
                <p className="text-sm text-blue-800 mb-3">
                  Items marked with <span className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-red-100 text-red-700 rounded text-xs font-medium">🔴 Required</span> must be completed and verified before the employee can start work.
                </p>
                <div className="text-sm text-blue-700 space-y-1">
                  <p className="font-medium">Priority guide:</p>
                  <ul className="space-y-1 ml-2">
                    <li className="flex items-center gap-2">
                      <span className="inline-block w-3 h-3 rounded-full bg-red-500"></span>
                      <span><strong>Required to Start Work</strong> — Complete these first</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <span className="inline-block w-3 h-3 rounded-full bg-orange-500"></span>
                      <span><strong>Required Soon</strong> — Complete within first 2 weeks</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <span className="inline-block w-3 h-3 rounded-full bg-yellow-500"></span>
                      <span><strong>Complete After Start</strong> — For full compliance</span>
                    </li>
                  </ul>
                </div>
              </div>

              {/* TAB CLARITY MESSAGE */}
              <p className="text-xs text-text-muted mb-4 px-1">
                Use "What's Needed" to complete compliance. Other tabs show records and history.
              </p>

              {!complianceRequirements ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="h-8 w-8 animate-spin text-primary" />
                </div>
              ) : (
                <div className="space-y-6">
                  {/* Group requirements by category */}
                  {/* Care-focused category order - highest risk first */}
                  {(() => {
                    // Category display names (care-focused)
                    const CATEGORY_DISPLAY = {
                      "1_Legal_Safety": "Legal & Safety",
                      "2_Core_Training": "Core Training",
                      "3_Role_Readiness": "Role Readiness",
                      "4_Employment": "Employment",
                      "5_Agreements": "Agreements",
                      "6_Admin": "Admin / Other"
                    };
                    
                    // REQUIREMENT MICROCOPY - Helper text for each requirement
                    const REQUIREMENT_HELP = {
                      "right_to_work_documents": "Upload visa, passport, or share code proof",
                      "right_to_work_check": "Upload share code verification or check confirmation",
                      "identity_documents": "Upload passport or driving licence (photo or scan)",
                      "dbs_certificate": "Upload DBS certificate (front page with reference number)",
                      "dbs_check": "Upload DBS update service check confirmation",
                      "safeguarding_training": "Upload training certificate or proof of completion",
                      "manual_handling_training": "Upload training certificate or proof of completion",
                      "infection_control_training": "Upload training certificate or proof of completion",
                      "basic_life_support_training": "Upload BLS certificate or proof of completion",
                      "fire_safety_training": "Upload training certificate or proof of completion",
                      "health_safety_training": "Upload training certificate or proof of completion",
                      "health_questionnaire": "Complete and upload health questionnaire",
                      "induction_completed": "Upload signed induction checklist or confirmation",
                      "references": "Upload reference letter or confirmation email",
                      "employment_contract": "Upload signed employment contract",
                      "job_application": "Upload original job application form",
                      "interview_record": "Upload interview notes or assessment form",
                      "employee_handbook": "Confirm employee has received and read handbook",
                      "policies_signed": "Upload signed policy acknowledgement forms"
                    };
                    
                    // Priority order
                    const categoryOrder = [
                      "1_Legal_Safety",
                      "2_Core_Training",
                      "3_Role_Readiness",
                      "4_Employment",
                      "5_Agreements",
                      "6_Admin"
                    ];
                    
                    return categoryOrder.map((category) => {
                      const categoryItems = complianceRequirements.requirements.filter(req => req.category === category);
                      if (categoryItems.length === 0) return null;
                      
                      const categoryLabel = CATEGORY_DISPLAY[category] || category.replace(/_/g, ' ').replace(/^\d_/, '');
                      const withEvidenceCount = categoryItems.filter(i => i.has_evidence || (i.evidence_files && i.evidence_files.length > 0)).length;
                      const verifiedInCategory = categoryItems.filter(i => i.verified).length;
                      
                      return (
                        <div key={category}>
                          <div className="flex items-center justify-between mb-3">
                            <h3 className="font-semibold text-text-primary">{categoryLabel}</h3>
                            <span className="text-xs text-text-muted">
                              {verifiedInCategory}/{categoryItems.length} approved
                              {withEvidenceCount > verifiedInCategory && ` · ${withEvidenceCount - verifiedInCategory} ready for review`}
                            </span>
                          </div>
                          <div className="space-y-2">
                            {categoryItems.map((req) => {
                              // Get microcopy for this requirement
                              const helpText = REQUIREMENT_HELP[req.id] || req.description || "";
                              
                              // Use new evidence_files array if available, fallback to documents
                              const allEvidenceFiles = req.evidence_files || [];
                              // Filter to only show active files (exclude removed/superseded)
                              const evidenceFiles = allEvidenceFiles.filter(f => !f.status || f.status === 'active');
                              // Keep removed/superseded files for history reference
                              const inactiveFiles = allEvidenceFiles.filter(f => f.status && f.status !== 'active');
                              const docs = req.documents || [];
                              const hasEvidence = req.has_evidence || evidenceFiles.length > 0 || docs.some(d => d.file_url);
                              const isVerified = req.verified || (hasEvidence && req.all_verified);
                              const canVerify = req.can_verify || (hasEvidence && !isVerified);
                              const isNoEvidence = req.status === 'completed_no_evidence';
                            
                            // Determine row styling based on evidence
                            const getRowStyle = () => {
                              if (isVerified) return 'bg-success/5 border-success/20';
                              if (hasEvidence) return 'bg-info/5 border-info/20';
                              return 'bg-error/5 border-error/20';
                            };
                            
                            // Determine status badge - CARE-FOCUSED: Still Needed, Ready for Review, Checked & Approved
                            const getStatusBadge = () => {
                              if (isVerified) return { text: 'Checked & Approved', style: 'bg-success/10 text-success' };
                              if (hasEvidence) return { text: 'Ready for Review', style: 'bg-info/10 text-info' };
                              return { text: 'Still Needed', style: 'bg-error/10 text-error' };
                            };
                            
                            const statusBadge = getStatusBadge();
                            
                            return (
                            <div 
                              key={req.id} 
                              className={`flex flex-col sm:flex-row sm:items-center justify-between p-3 rounded-xl border gap-3 ${getRowStyle()}`}
                              data-testid={`requirement-row-${req.id}`}
                            >
                              <div className="flex items-start gap-3 flex-1">
                                {/* Status Icon - simplified to 3 states */}
                                {isVerified ? (
                                  <Shield className="h-5 w-5 text-success flex-shrink-0 mt-0.5" />
                                ) : hasEvidence ? (
                                  <CheckCircle className="h-5 w-5 text-info flex-shrink-0 mt-0.5" />
                                ) : (
                                  <XCircle className="h-5 w-5 text-error flex-shrink-0 mt-0.5" />
                                )}
                                <div className="flex-1 min-w-0">
                                  <div className="flex items-center gap-2 flex-wrap">
                                    {/* PRIORITY BADGE - Shows work readiness priority */}
                                    {req.priority === 'mandatory' && (
                                      <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-red-100 text-red-700 font-medium flex items-center gap-1">
                                        <span className="w-1.5 h-1.5 rounded-full bg-red-500"></span>
                                        Required
                                      </span>
                                    )}
                                    {req.priority === 'required_soon' && (
                                      <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-orange-100 text-orange-700 font-medium flex items-center gap-1">
                                        <span className="w-1.5 h-1.5 rounded-full bg-orange-500"></span>
                                        Soon
                                      </span>
                                    )}
                                    <p className="font-medium text-text-primary">{req.name}</p>
                                    {/* Source badge - cleaner */}
                                    {req.source === 'internal' && (
                                      <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-purple-100 text-purple-700">
                                        Internal
                                      </span>
                                    )}
                                    {/* Evidence count badge */}
                                    {evidenceFiles.length > 0 && (
                                      <span className="text-xs bg-primary/10 text-primary px-1.5 py-0.5 rounded">
                                        {evidenceFiles.length} file{evidenceFiles.length !== 1 ? 's' : ''}
                                      </span>
                                    )}
                                  </div>
                                  
                                  {/* WORK READY HINT - Shows when item blocks work */}
                                  {req.is_mandatory_for_work && !isVerified && (
                                    <p className="text-[10px] text-red-600 font-medium mt-0.5">
                                      ⚠ Required before employee can start work
                                    </p>
                                  )}
                                  
                                  {/* MICROCOPY HELPER TEXT - Shows guidance for each requirement */}
                                  {helpText && !hasEvidence && !req.is_mandatory_for_work && (
                                    <p className="text-xs text-text-muted mt-0.5">{helpText}</p>
                                  )}
                                  
                                  {/* Multi-file guidance - only show when no evidence */}
                                  {!hasEvidence && (
                                    <p className="text-[10px] text-text-muted/70 mt-1">
                                      You can upload more than one file if needed (e.g. front and back)
                                    </p>
                                  )}
                                  
                                  {/* Evidence files list - shows all files, click View button to browse */}
                                  {evidenceFiles.length > 0 && (
                                    <div className="text-xs text-text-muted space-y-0.5 mt-1">
                                      {evidenceFiles.map((file, idx) => (
                                        <div key={file.file_id || idx} className="flex items-center gap-1.5 py-0.5">
                                          <FileText className="h-3 w-3 flex-shrink-0 text-primary/70" />
                                          <span className="truncate max-w-[200px]">
                                            {file.file_label || file.original_filename || 'Document'}
                                          </span>
                                          {file.verified && <Shield className="h-3 w-3 text-success flex-shrink-0" />}
                                        </div>
                                      ))}
                                    </div>
                                  )}
                                  
                                  {/* Show count of removed/superseded files if any exist */}
                                  {inactiveFiles.length > 0 && (
                                    <button 
                                      onClick={() => openHistoryDialog(req.id)}
                                      className="text-xs text-muted-foreground hover:text-primary mt-1 flex items-center gap-1"
                                    >
                                      <History className="h-3 w-3" />
                                      {inactiveFiles.length} previous file{inactiveFiles.length > 1 ? 's' : ''} in history
                                    </button>
                                  )}
                                  
                                  {/* Warning for form without PDF */}
                                  {req.type === 'form-generated' && req.form && !hasEvidence && (
                                    <p className="text-xs text-warning flex items-center gap-1 mt-1">
                                      <AlertTriangle className="h-3 w-3" />
                                      No PDF evidence - click Generate PDF
                                    </p>
                                  )}
                                </div>
                              </div>
                              
                              {/* Actions - Clean Linear: Upload/Add → View → Download → Verify */}
                              <div className="flex items-center gap-2 flex-wrap justify-end">
                                {/* Status badge */}
                                <span className={`px-2 py-1 rounded-lg text-xs font-medium ${statusBadge.style}`}>
                                  {statusBadge.text}
                                </span>
                                
                                {/* ACTION 1: Upload / Add File */}
                                {!isAuditor() && (
                                  <>
                                    {/* Generate PDF for forms without evidence */}
                                    {req.type === 'form-generated' && req.form && req.form.status && 
                                     ['completed', 'completed_imported', 'signed_off'].includes(req.form.status) && 
                                     !req.form.pdf_url ? (
                                      <Button 
                                        size="sm" 
                                        variant="outline"
                                        onClick={async () => {
                                          try {
                                            await axios.post(
                                              `${API}/generated-forms/${req.form.id}/regenerate-pdf`,
                                              {},
                                              { headers: { Authorization: `Bearer ${token}` } }
                                            );
                                            toast.success('PDF generated successfully');
                                            fetchData();
                                          } catch (e) {
                                            toast.error(e.response?.data?.detail || 'Failed to generate PDF');
                                          }
                                        }}
                                        className="text-xs h-7 text-warning border-warning hover:bg-warning/10 rounded-lg"
                                        data-testid={`generate-pdf-${req.id}`}
                                      >
                                        <FileText className="h-3 w-3 mr-1" />
                                        Generate PDF
                                      </Button>
                                    ) : !hasEvidence ? (
                                      <Button 
                                        size="sm" 
                                        variant="default"
                                        onClick={() => {
                                          if (req.type === 'training') {
                                            openTrainingCertDialog(req);
                                          } else {
                                            setSelectedRequirement(req.id);
                                            setUploadDialogOpen(true);
                                          }
                                        }}
                                        className="text-xs h-7 bg-primary hover:bg-primary-hover text-white rounded-lg"
                                        data-testid={`upload-evidence-${req.id}`}
                                      >
                                        <Upload className="h-3 w-3 mr-1" />
                                        Upload Document
                                      </Button>
                                    ) : req.allow_multiple_files ? (
                                      <Button 
                                        size="sm" 
                                        variant="outline"
                                        onClick={() => {
                                          if (req.type === 'training') {
                                            openTrainingCertDialog(req);
                                          } else {
                                            setSelectedRequirement(req.id);
                                            setUploadDialogOpen(true);
                                          }
                                        }}
                                        className="text-xs h-7 rounded-lg"
                                        data-testid={`add-file-${req.id}`}
                                      >
                                        <Upload className="h-3 w-3 mr-1" />
                                        Add Another File
                                      </Button>
                                    ) : null}
                                  </>
                                )}
                                
                                {/* ACTION 2: View - Opens all files with Next/Prev navigation */}
                                {evidenceFiles.length > 0 && (
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    onClick={() => handlePreviewMultipleFiles(evidenceFiles, req.id)}
                                    className="text-xs h-7 rounded-lg"
                                    data-testid={`view-evidence-${req.id}`}
                                  >
                                    <Eye className="h-3 w-3 mr-1" />
                                    View {evidenceFiles.length > 1 ? `(${evidenceFiles.length})` : ''}
                                  </Button>
                                )}
                                
                                {/* ACTION 3: Download */}
                                {evidenceFiles.length > 0 && (
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    onClick={async () => {
                                      try {
                                        const file = evidenceFiles[0];
                                        const response = await axios.get(
                                          `${API}/employees/${employeeId}/requirements/${req.id}/evidence/${file.file_id}/download`,
                                          { headers: { Authorization: `Bearer ${token}` }, responseType: 'blob' }
                                        );
                                        const blob = new Blob([response.data]);
                                        const url = URL.createObjectURL(blob);
                                        const link = document.createElement('a');
                                        link.href = url;
                                        link.download = file.original_filename || 'evidence';
                                        link.click();
                                        URL.revokeObjectURL(url);
                                        toast.success('Downloaded');
                                      } catch (e) {
                                        toast.error('Download failed');
                                      }
                                    }}
                                    className="text-xs h-7 rounded-lg"
                                    data-testid={`download-evidence-${req.id}`}
                                  >
                                    <Download className="h-3 w-3 mr-1" />
                                    Download
                                  </Button>
                                )}
                                
                                {/* ACTION 4: Approve (only when evidence exists and not yet verified) */}
                                {hasEvidence && !isVerified && !isAuditor() && (
                                  <Button 
                                    size="sm" 
                                    variant="outline"
                                    onClick={async () => {
                                      try {
                                        await axios.post(
                                          `${API}/employees/${employeeId}/requirements/${req.id}/verify`,
                                          {},
                                          { headers: { Authorization: `Bearer ${token}` } }
                                        );
                                        toast.success(`${req.name} marked as Checked & Approved`);
                                        fetchData();
                                        fetchCompliance();
                                      } catch (e) {
                                        toast.error(e.response?.data?.detail || 'Could not approve - please try again');
                                      }
                                    }}
                                    className="text-xs h-7 text-success border-success hover:bg-success/10 rounded-lg"
                                    data-testid={`verify-${req.id}`}
                                    title="Mark as Checked & Approved"
                                  >
                                    <Shield className="h-3 w-3 mr-1" />
                                    Mark as Approved
                                  </Button>
                                )}
                                
                                {/* ACTION 5: File Management Menu (when evidence exists) */}
                                {evidenceFiles.length > 0 && (
                                  <DropdownMenu>
                                    <DropdownMenuTrigger asChild>
                                      <Button 
                                        size="sm" 
                                        variant="ghost"
                                        className="text-xs h-7 px-2 rounded-lg"
                                        data-testid={`more-actions-${req.id}`}
                                      >
                                        <MoreHorizontal className="h-3 w-3" />
                                      </Button>
                                    </DropdownMenuTrigger>
                                    <DropdownMenuContent align="end" className="w-48">
                                      {/* Edit Details */}
                                      {!isAuditor() && (
                                        <DropdownMenuItem 
                                          onClick={() => openEditEvidence(req.id, evidenceFiles.find(f => f.status === 'active' || !f.status) || evidenceFiles[0])}
                                          data-testid={`edit-details-${req.id}`}
                                        >
                                          <Edit className="h-4 w-4 mr-2" />
                                          Edit Details
                                        </DropdownMenuItem>
                                      )}
                                      
                                      {/* Replace File */}
                                      {!isAuditor() && (
                                        <DropdownMenuItem 
                                          onClick={() => openReplaceDialog(
                                            evidenceFiles.find(f => f.status === 'active' || !f.status) || evidenceFiles[0],
                                            req.id
                                          )}
                                          data-testid={`replace-file-${req.id}`}
                                        >
                                          <RefreshCw className="h-4 w-4 mr-2" />
                                          Replace File
                                        </DropdownMenuItem>
                                      )}
                                      
                                      {/* Remove File */}
                                      {!isAuditor() && (
                                        <DropdownMenuItem 
                                          onClick={() => openRemoveDialog(
                                            evidenceFiles.find(f => f.status === 'active' || !f.status) || evidenceFiles[0],
                                            req.id
                                          )}
                                          className="text-red-600"
                                          data-testid={`remove-file-${req.id}`}
                                        >
                                          <Trash2 className="h-4 w-4 mr-2" />
                                          Remove File
                                        </DropdownMenuItem>
                                      )}
                                      
                                      <DropdownMenuSeparator />
                                      
                                      {/* View History - available to all */}
                                      <DropdownMenuItem 
                                        onClick={() => openHistoryDialog(req.id)}
                                        data-testid={`view-history-${req.id}`}
                                      >
                                        <History className="h-4 w-4 mr-2" />
                                        View History
                                      </DropdownMenuItem>
                                    </DropdownMenuContent>
                                  </DropdownMenu>
                                )}
                                
                                {/* Unverify option */}
                                {isVerified && !isAuditor() && (
                                  <Button 
                                    size="sm" 
                                    variant="ghost"
                                    onClick={async () => {
                                      try {
                                        await axios.post(
                                          `${API}/employees/${employeeId}/requirements/${req.id}/unverify`,
                                          {},
                                          { headers: { Authorization: `Bearer ${token}` } }
                                        );
                                        toast.success('Approval removed');
                                        fetchData();
                                      } catch (e) {
                                        toast.error('Failed to remove approval');
                                      }
                                    }}
                                    className="text-xs h-7 text-text-muted hover:text-warning rounded-lg"
                                    data-testid={`unverify-${req.id}`}
                                    title="Remove approval"
                                  >
                                    <XCircle className="h-3 w-3" />
                                  </Button>
                                )}
                              </div>
                            </div>
                          );
                        })}
                        </div>
                      </div>
                    );
                  });
                  })()}
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
                      // Use evidence_files as the single source of truth (same as What's Needed tab)
                      const allEvidenceFiles = req.evidence_files || [];
                      // Filter to only active files
                      const docs = allEvidenceFiles.filter(f => !f.status || f.status === 'active');
                      const hasFiles = docs.length > 0;
                      const verifiedDocs = docs.filter(d => d.verified);
                      const allVerified = hasFiles && verifiedDocs.length === docs.length && docs.length >= (req.min_files || 1);
                      const isComplete = req.status === 'completed' || req.has_evidence;
                      
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
                              {/* Status Badge - Care-focused */}
                              <span className={`px-2 py-1 rounded-lg text-xs font-medium ${
                                allVerified ? 'bg-success/10 text-success' :
                                hasFiles ? 'bg-info/10 text-info' :
                                'bg-error/10 text-error'
                              }`}>
                                {allVerified ? 'Checked & Approved' :
                                 hasFiles ? 'Ready for Review' :
                                 'Still Needed'}
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
                          
                          {/* Files List - Using evidence_files structure */}
                          {docs.length > 0 && (
                            <div className="mt-3 space-y-2">
                              {docs.map((doc, idx) => (
                                <div 
                                  key={doc.file_id || idx} 
                                  className={`flex items-center justify-between p-3 rounded-lg border ${
                                    doc.verified ? 'border-success/30 bg-success/5' : 'border-[#E4E8EB] bg-white'
                                  }`}
                                >
                                  <div className="flex items-center gap-3 flex-1 min-w-0">
                                    <FileText className="h-5 w-5 text-text-muted flex-shrink-0" />
                                    <div className="min-w-0">
                                      <p className="text-sm font-medium text-text-primary truncate">
                                        {doc.file_label || doc.original_filename || 'Document'}
                                      </p>
                                      <div className="flex items-center gap-2 text-xs text-text-muted">
                                        {doc.source_type && (
                                          <span>
                                            {doc.source_type === 'form_submission' ? 'From Form' : 
                                             doc.source_type === 'imported' ? 'Imported' : 
                                             doc.source_type === 'replacement' ? 'Replaced' : 'Manual'}
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
                                  
                                  {/* File Actions - using evidence file endpoint */}
                                  <div className="flex items-center gap-1">
                                    <Button 
                                      size="sm" 
                                      variant="ghost"
                                      className="h-8 w-8 p-0 rounded-lg"
                                      onClick={() => {
                                        const viewUrl = `${API}/employees/${employeeId}/requirements/${req.id}/evidence/${doc.file_id}/view`;
                                        setPreviewFile({
                                          url: viewUrl,
                                          name: doc.file_label || doc.original_filename || 'Document',
                                          filename: doc.original_filename
                                        });
                                        setPreviewFiles([]);
                                        setPreviewOpen(true);
                                      }}
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
                                          const downloadUrl = `${API}/employees/${employeeId}/requirements/${req.id}/evidence/${doc.file_id}/view`;
                                          const response = await axios.get(downloadUrl, {
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
                                      <Download className="h-4 w-4" />
                                    </Button>
                                    {!isAuditor() && !doc.verified && (
                                      <Button 
                                        size="sm" 
                                        variant="ghost"
                                        className="h-8 w-8 p-0 rounded-lg text-success hover:bg-success/10"
                                        onClick={() => handleVerifyRequirement(req.id)}
                                        title="Approve"
                                      >
                                        <Shield className="h-4 w-4" />
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

      {/* Training Completion Dialog */}
      <Dialog open={trainingDialogOpen} onOpenChange={setTrainingDialogOpen}>
        <DialogContent className="sm:max-w-md bg-white">
          <DialogHeader>
            <DialogTitle className="font-heading flex items-center gap-2 text-text-primary">
              <GraduationCap className="h-5 w-5 text-primary" />
              Mark Training Complete
            </DialogTitle>
            <DialogDescription className="text-text-muted">
              Mark this training requirement as completed for the employee.
            </DialogDescription>
          </DialogHeader>
          
          {selectedTrainingReq && (
            <div className="space-y-4 py-4">
              <div className="p-4 bg-[#F8FAFA] rounded-xl">
                <p className="font-medium text-text-primary">{selectedTrainingReq.name}</p>
                <p className="text-sm text-text-muted mt-1">
                  Category: {selectedTrainingReq.category?.replace(/_/g, ' ').replace(/^[A-Z]_/, '')}
                </p>
              </div>
              
              <div className="space-y-2">
                <Label className="text-text-primary">Expiry Date (Optional)</Label>
                <Input
                  type="date"
                  value={trainingExpiryDate}
                  onChange={(e) => setTrainingExpiryDate(e.target.value)}
                  className="rounded-xl"
                  placeholder="Leave empty if no expiry"
                />
                <p className="text-xs text-text-muted">
                  Set an expiry date if this training needs to be renewed
                </p>
              </div>
              
              <div className="bg-info/10 border border-info/20 rounded-xl p-3">
                <p className="text-sm text-info font-medium">What happens:</p>
                <ul className="text-xs text-text-muted mt-1 space-y-1">
                  <li className="flex items-center gap-1">
                    <CheckCircle className="h-3 w-3 text-success" />
                    Training record created or updated
                  </li>
                  <li className="flex items-center gap-1">
                    <CheckCircle className="h-3 w-3 text-success" />
                    Compliance requirement marked complete
                  </li>
                  <li className="flex items-center gap-1">
                    <CheckCircle className="h-3 w-3 text-success" />
                    Compliance score updates immediately
                  </li>
                </ul>
              </div>
            </div>
          )}
          
          <DialogFooter>
            <Button 
              variant="outline" 
              onClick={() => {
                setTrainingDialogOpen(false);
                setSelectedTrainingReq(null);
                setTrainingExpiryDate('');
              }} 
              className="rounded-xl"
            >
              Cancel
            </Button>
            <Button 
              onClick={handleCompleteTraining}
              disabled={isCompletingTraining}
              className="bg-primary hover:bg-primary-hover text-white rounded-xl"
              data-testid="confirm-complete-training"
            >
              {isCompletingTraining ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <>
                  <CheckCircle className="h-4 w-4 mr-2" />
                  Mark Complete
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Training Certificate Upload Dialog */}
      <Dialog open={trainingCertDialogOpen} onOpenChange={setTrainingCertDialogOpen}>
        <DialogContent className="sm:max-w-md bg-white">
          <DialogHeader>
            <DialogTitle className="font-heading flex items-center gap-2 text-text-primary">
              <Upload className="h-5 w-5 text-primary" />
              Upload Training Certificate
            </DialogTitle>
            <DialogDescription className="text-text-muted">
              Upload a certificate as evidence for this training requirement.
            </DialogDescription>
          </DialogHeader>
          
          {selectedTrainingReq && (
            <div className="space-y-4 py-4">
              <div className="p-4 bg-[#F8FAFA] rounded-xl">
                <p className="font-medium text-text-primary">{selectedTrainingReq.name}</p>
                <p className="text-sm text-text-muted mt-1">
                  Category: {selectedTrainingReq.category?.replace(/_/g, ' ').replace(/^[A-Z]_/, '')}
                </p>
              </div>
              
              <div className="space-y-2">
                <Label className="text-text-primary">Certificate File *</Label>
                <Input
                  type="file"
                  accept=".pdf,.jpg,.jpeg,.png,.doc,.docx"
                  onChange={(e) => setTrainingCertFile(e.target.files?.[0] || null)}
                  className="rounded-xl"
                  data-testid="training-cert-file-input"
                />
                <p className="text-xs text-text-muted">
                  Accepted formats: PDF, JPG, PNG, DOC, DOCX
                </p>
              </div>
              
              <div className="space-y-2">
                <Label className="text-text-primary">Certificate Expiry Date (Optional)</Label>
                <Input
                  type="date"
                  value={trainingExpiryDate}
                  onChange={(e) => setTrainingExpiryDate(e.target.value)}
                  className="rounded-xl"
                />
                <p className="text-xs text-text-muted">
                  Set an expiry date if this certificate needs to be renewed
                </p>
              </div>
              
              <div className="bg-success/10 border border-success/20 rounded-xl p-3">
                <p className="text-sm text-success font-medium">Audit-Ready Evidence:</p>
                <ul className="text-xs text-text-muted mt-1 space-y-1">
                  <li className="flex items-center gap-1">
                    <CheckCircle className="h-3 w-3 text-success" />
                    Certificate stored with audit trail
                  </li>
                  <li className="flex items-center gap-1">
                    <CheckCircle className="h-3 w-3 text-success" />
                    Training marked as complete with evidence
                  </li>
                  <li className="flex items-center gap-1">
                    <CheckCircle className="h-3 w-3 text-success" />
                    Certificate can be viewed and downloaded
                  </li>
                  <li className="flex items-center gap-1">
                    <Shield className="h-3 w-3 text-success" />
                    Ready for verification
                  </li>
                </ul>
              </div>
            </div>
          )}
          
          <DialogFooter>
            <Button 
              variant="outline" 
              onClick={() => {
                setTrainingCertDialogOpen(false);
                setSelectedTrainingReq(null);
                setTrainingCertFile(null);
                setTrainingExpiryDate('');
              }} 
              className="rounded-xl"
            >
              Cancel
            </Button>
            <Button 
              onClick={handleUploadTrainingCertificate}
              disabled={isUploadingCert || !trainingCertFile}
              className="bg-primary hover:bg-primary-hover text-white rounded-xl"
              data-testid="confirm-upload-training-cert"
            >
              {isUploadingCert ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <>
                  <Upload className="h-4 w-4 mr-2" />
                  Upload Certificate
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Evidence Details Modal */}
      <Dialog open={editEvidenceOpen} onOpenChange={setEditEvidenceOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="font-heading">Edit Document Details</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 mt-4">
            <p className="text-sm text-text-muted">
              Update document metadata. A reason is required for audit trail purposes.
            </p>
            
            <div className="space-y-2">
              <Label>Document Label</Label>
              <Input
                value={editForm.file_label}
                onChange={(e) => setEditForm(prev => ({ ...prev, file_label: e.target.value }))}
                placeholder="e.g., DBS Certificate 2024"
                className="rounded-xl"
              />
            </div>
            
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label>Issue Date</Label>
                <Input
                  type="date"
                  value={editForm.issue_date}
                  onChange={(e) => setEditForm(prev => ({ ...prev, issue_date: e.target.value }))}
                  className="rounded-xl"
                />
              </div>
              <div className="space-y-2">
                <Label>Expiry Date</Label>
                <Input
                  type="date"
                  value={editForm.expiry_date}
                  onChange={(e) => setEditForm(prev => ({ ...prev, expiry_date: e.target.value }))}
                  className="rounded-xl"
                />
              </div>
            </div>
            
            <div className="space-y-2">
              <Label>Notes</Label>
              <Textarea
                value={editForm.notes}
                onChange={(e) => setEditForm(prev => ({ ...prev, notes: e.target.value }))}
                placeholder="Additional notes about this document..."
                className="rounded-xl"
                rows={3}
              />
            </div>
            
            <div className="space-y-2">
              <Label className="text-warning">Reason for Change *</Label>
              <Textarea
                value={editForm.reason}
                onChange={(e) => setEditForm(prev => ({ ...prev, reason: e.target.value }))}
                placeholder="e.g., Wrong expiry year entered, Corrected issue date from certificate..."
                className="rounded-xl border-warning/50 focus:border-warning"
                rows={2}
              />
              <p className="text-xs text-text-muted">
                This will be recorded in the audit trail for CQC compliance.
              </p>
            </div>
          </div>
          <DialogFooter className="mt-4">
            <Button 
              variant="outline" 
              onClick={() => setEditEvidenceOpen(false)}
              className="rounded-xl"
            >
              Cancel
            </Button>
            <Button 
              onClick={handleSaveEvidenceEdit}
              disabled={isEditingEvidence || !editForm.reason}
              className="bg-primary hover:bg-primary-hover text-white rounded-xl"
            >
              {isEditingEvidence ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <>
                  <Save className="h-4 w-4 mr-2" />
                  Save Changes
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit History Modal */}
      <Dialog open={historyOpen} onOpenChange={setHistoryOpen}>
        <DialogContent className="max-w-lg max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="font-heading flex items-center gap-2">
              <History className="h-5 w-5 text-primary" />
              Change History
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-3 mt-4">
            {editHistory.length === 0 ? (
              <div className="text-center py-8">
                <History className="h-10 w-10 mx-auto text-text-muted/50 mb-2" />
                <p className="text-text-muted">No changes recorded</p>
                <p className="text-xs text-text-muted mt-1">
                  Document details have not been modified since upload.
                </p>
              </div>
            ) : (
              editHistory.map((log) => (
                <div 
                  key={log.id} 
                  className="p-3 bg-[#F8FAFA] rounded-xl border border-[#E4E8EB]"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <User className="h-4 w-4 text-primary" />
                      <span className="font-medium text-text-primary text-sm">
                        {log.changed_by_name}
                      </span>
                    </div>
                    <span className="text-xs text-text-muted">
                      {new Date(log.changed_at).toLocaleString()}
                    </span>
                  </div>
                  <div className="text-sm space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-text-muted">Field:</span>
                      <span className="font-medium text-text-primary capitalize">
                        {log.field_changed.replace(/_/g, ' ')}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-text-muted">From:</span>
                      <span className="text-error line-through">
                        {log.old_value || '(empty)'}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-text-muted">To:</span>
                      <span className="text-success">
                        {log.new_value || '(empty)'}
                      </span>
                    </div>
                    <div className="flex items-start gap-2 mt-2 pt-2 border-t border-[#E4E8EB]">
                      <span className="text-text-muted">Reason:</span>
                      <span className="text-text-primary italic">
                        "{log.reason}"
                      </span>
                    </div>
                    {log.was_verified_before_edit && (
                      <div className="mt-2 px-2 py-1 bg-warning/10 text-warning text-xs rounded-lg inline-block">
                        Changed after approval
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
          <DialogFooter className="mt-4">
            <Button 
              variant="outline" 
              onClick={() => setHistoryOpen(false)}
              className="rounded-xl"
            >
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Remove File Dialog */}
      <Dialog open={removeDialogOpen} onOpenChange={setRemoveDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-error">
              <Trash2 className="h-5 w-5" />
              Remove File
            </DialogTitle>
            <DialogDescription>
              This will mark the file as removed. The file will remain in the history for audit purposes but will no longer count as evidence.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            {selectedFileForAction && (
              <div className="p-3 bg-muted rounded-lg">
                <p className="text-sm font-medium">{selectedFileForAction.file_label || selectedFileForAction.original_filename}</p>
                <p className="text-xs text-muted-foreground mt-1">
                  Uploaded: {new Date(selectedFileForAction.uploaded_at).toLocaleDateString()}
                </p>
              </div>
            )}
            <div className="space-y-2">
              <Label htmlFor="remove-reason">Reason for removal <span className="text-error">*</span></Label>
              <Textarea
                id="remove-reason"
                placeholder="Enter the reason for removing this file (required for audit trail)"
                value={removeReason}
                onChange={(e) => setRemoveReason(e.target.value)}
                className="min-h-[100px]"
              />
              <p className="text-xs text-muted-foreground">This reason will be recorded in the audit trail.</p>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRemoveDialogOpen(false)}>
              Cancel
            </Button>
            <Button 
              variant="destructive" 
              onClick={handleRemoveFile}
              disabled={isRemoving || !removeReason.trim()}
            >
              {isRemoving ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Trash2 className="h-4 w-4 mr-2" />}
              Remove File
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Replace File Dialog */}
      <Dialog open={replaceDialogOpen} onOpenChange={setReplaceDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <RefreshCw className="h-5 w-5 text-primary" />
              Replace File
            </DialogTitle>
            <DialogDescription>
              Uploading a new file will replace the existing one. The old file will be kept in history for audit purposes.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            {selectedFileForAction && (
              <div className="p-3 bg-muted rounded-lg">
                <p className="text-sm text-muted-foreground">Replacing:</p>
                <p className="text-sm font-medium">{selectedFileForAction.file_label || selectedFileForAction.original_filename}</p>
              </div>
            )}
            <div className="space-y-2">
              <Label htmlFor="replace-file">New File <span className="text-error">*</span></Label>
              <Input
                id="replace-file"
                type="file"
                accept=".pdf,.jpg,.jpeg,.png,.webp"
                onChange={(e) => setReplaceFile(e.target.files?.[0] || null)}
                className="cursor-pointer"
              />
              <p className="text-xs text-muted-foreground">Upload PDF or photo (JPG, PNG)</p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="replace-reason">Reason for replacement <span className="text-error">*</span></Label>
              <Textarea
                id="replace-reason"
                placeholder="Why is this file being replaced? (e.g. clearer scan, updated document)"
                value={replaceReason}
                onChange={(e) => setReplaceReason(e.target.value)}
                className="min-h-[80px]"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setReplaceDialogOpen(false)}>
              Cancel
            </Button>
            <Button 
              onClick={handleReplaceFile}
              disabled={isReplacing || !replaceReason.trim() || !replaceFile}
              className="bg-primary hover:bg-primary-hover"
            >
              {isReplacing ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <RefreshCw className="h-4 w-4 mr-2" />}
              Replace File
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Requirement History Dialog */}
      <Dialog open={requirementHistoryOpen} onOpenChange={setRequirementHistoryOpen}>
        <DialogContent className="sm:max-w-lg max-h-[80vh] overflow-hidden flex flex-col">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <History className="h-5 w-5 text-primary" />
              File History
            </DialogTitle>
            <DialogDescription>
              Complete timeline of all file operations for this requirement.
            </DialogDescription>
          </DialogHeader>
          <div className="flex-1 overflow-y-auto py-4">
            {loadingHistory ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-primary" />
              </div>
            ) : requirementHistory.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <History className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p>No history recorded yet</p>
              </div>
            ) : (
              <div className="space-y-3">
                {requirementHistory.map((entry, idx) => (
                  <div key={entry.id || idx} className="p-3 border rounded-lg">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-2">
                        {entry.action === 'replace_evidence' && <RefreshCw className="h-4 w-4 text-blue-500" />}
                        {entry.action === 'remove_evidence' && <Trash2 className="h-4 w-4 text-red-500" />}
                        {entry.action === 'edit_evidence' && <Edit className="h-4 w-4 text-amber-500" />}
                        {entry.action === 'upload_evidence' && <Upload className="h-4 w-4 text-green-500" />}
                        {entry.action === 'verify_evidence' && <Shield className="h-4 w-4 text-green-600" />}
                        {!['replace_evidence', 'remove_evidence', 'edit_evidence', 'upload_evidence', 'verify_evidence'].includes(entry.action) && (
                          <FileText className="h-4 w-4 text-gray-500" />
                        )}
                        <span className="font-medium text-sm capitalize">
                          {entry.action?.replace(/_/g, ' ')}
                        </span>
                      </div>
                      <span className="text-xs text-muted-foreground">
                        {entry.timestamp ? new Date(entry.timestamp).toLocaleString() : 'Unknown'}
                      </span>
                    </div>
                    <p className="text-sm text-muted-foreground mt-1">
                      By: {entry.user_name || 'Unknown'}
                    </p>
                    {entry.reason && (
                      <p className="text-sm mt-2 p-2 bg-muted rounded">
                        <span className="font-medium">Reason:</span> {entry.reason}
                      </p>
                    )}
                    {entry.details && Object.keys(entry.details).length > 0 && (
                      <div className="text-xs text-muted-foreground mt-2 space-y-1">
                        {entry.details.old_filename && (
                          <p>Old file: {entry.details.old_filename}</p>
                        )}
                        {entry.details.new_filename && (
                          <p>New file: {entry.details.new_filename}</p>
                        )}
                        {entry.details.filename && (
                          <p>File: {entry.details.filename}</p>
                        )}
                        {entry.details.field && (
                          <p>Changed: {entry.details.field} from "{entry.details.old_value || 'empty'}" to "{entry.details.new_value}"</p>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRequirementHistoryOpen(false)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Document Preview Modal - supports multi-file navigation */}
      <DocumentPreviewModal
        isOpen={previewOpen}
        onClose={() => { setPreviewOpen(false); setPreviewFiles([]); }}
        fileUrl={previewFile?.url}
        fileName={previewFile?.name || previewFile?.filename}
        token={token}
        files={previewFiles}
        onDownload={previewFile ? async () => {
          try {
            const downloadUrl = previewFile.url.replace('/view', '/download');
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
