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
  MoreHorizontal, MoreVertical, Edit, Archive, Trash2, RotateCcw, FileDown, Save,
  Download, RefreshCw, FileArchive, FileSpreadsheet, Printer, FilePdf,
  Camera, Replace, FileX, ClipboardCheck, FormInput, ChevronRight
} from 'lucide-react';
import { FileUploaderInline } from '../../components/ui/file-uploader';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Form-based requirements (open modal instead of file upload)
const FORM_BASED_REQUIREMENTS = [
  'health_screening', 
  'induction', 
  'interview_record', 
  'recruitment_checklist', 
  'equal_opportunities',
  'hmrc_starter_checklist',
  'staff_personal_info',
  'staff_health_questionnaire'
];

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
  
  // Training correction/history dialog states
  const [trainingCorrectionDialogOpen, setTrainingCorrectionDialogOpen] = useState(false);
  const [editingTrainingRecord, setEditingTrainingRecord] = useState(null);
  const [trainingCorrectionField, setTrainingCorrectionField] = useState('expiry_date');
  const [trainingCorrectionValue, setTrainingCorrectionValue] = useState('');
  const [trainingCorrectionReason, setTrainingCorrectionReason] = useState('');
  const [trainingHistoryDialogOpen, setTrainingHistoryDialogOpen] = useState(false);
  const [trainingHistory, setTrainingHistory] = useState([]);
  
  // Delete training record states
  const [deleteTrainingDialogOpen, setDeleteTrainingDialogOpen] = useState(false);
  const [deletingTrainingRecord, setDeletingTrainingRecord] = useState(null);
  const [deleteTrainingReason, setDeleteTrainingReason] = useState('');
  const [isDeletingTraining, setIsDeletingTraining] = useState(false);
  
  // Acknowledgement states (for Contract/Handbook acknowledgement flow)
  const [acknowledgementDialogOpen, setAcknowledgementDialogOpen] = useState(false);
  const [acknowledgingRequirement, setAcknowledgingRequirement] = useState(null);
  const [isAcknowledging, setIsAcknowledging] = useState(false);
  const [acknowledgementConfirmed, setAcknowledgementConfirmed] = useState(false);
  
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
  
  // Form submission modal state (for structured forms)
  const [formModalOpen, setFormModalOpen] = useState(false);
  const [formTemplate, setFormTemplate] = useState(null);
  const [formData, setFormData] = useState({});
  const [isSubmittingForm, setIsSubmittingForm] = useState(false);
  const [viewFormOpen, setViewFormOpen] = useState(false);
  const [viewFormData, setViewFormData] = useState(null);
  
  // Profile extraction from application form state
  const [extractionDialogOpen, setExtractionDialogOpen] = useState(false);
  const [extractionResult, setExtractionResult] = useState(null);
  const [extractionFailed, setExtractionFailed] = useState(null); // For graceful failure handling
  const [isExtracting, setIsExtracting] = useState(false);
  const [fieldsToApply, setFieldsToApply] = useState({});
  const [isApplyingExtraction, setIsApplyingExtraction] = useState(false);
  
  const { token, isAuditor, isAdmin, user } = useAuth();
  
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
    'Recruitment File: Incomplete',
    'Under Review',
    'Ready for Placement',
    'Active',
    'Archived'
  ];

  const isSuperAdmin = () => user?.role === 'super_admin';

  const fetchData = async () => {
    // Use Promise.allSettled to allow partial success
    const results = await Promise.allSettled([
      axios.get(`${API}/employees/${employeeId}`, { headers: { Authorization: `Bearer ${token}` } }),
      axios.get(`${API}/employee-documents?employee_id=${employeeId}`, { headers: { Authorization: `Bearer ${token}` } }),
      axios.get(`${API}/document-types`, { headers: { Authorization: `Bearer ${token}` } }),
      axios.get(`${API}/policy-assignments?employee_id=${employeeId}`, { headers: { Authorization: `Bearer ${token}` } }),
      axios.get(`${API}/training-records?employee_id=${employeeId}`, { headers: { Authorization: `Bearer ${token}` } }),
      axios.get(`${API}/audit-logs?entity_id=${employeeId}&compliance_only=true`, { headers: { Authorization: `Bearer ${token}` } }),
      axios.get(`${API}/generated-forms?employee_id=${employeeId}`, { headers: { Authorization: `Bearer ${token}` } }),
      axios.get(`${API}/templates`, { headers: { Authorization: `Bearer ${token}` } }),
      axios.get(`${API}/employees/${employeeId}/compliance-requirements`, { headers: { Authorization: `Bearer ${token}` } })
    ]);
    
    // Process results - extract data or use defaults
    const [empRes, docsRes, typesRes, policiesRes, trainingRes, logsRes, formsRes, templatesRes, compReqRes] = results;
    
    let hasError = false;
    
    // Employee data is critical - if it fails, show error
    if (empRes.status === 'fulfilled') {
      setEmployee(empRes.value.data);
    } else {
      console.error('Failed to fetch employee:', empRes.reason);
      hasError = true;
    }
    
    // Other data can fail gracefully with defaults
    setDocuments(docsRes.status === 'fulfilled' ? docsRes.value.data : []);
    setDocumentTypes(typesRes.status === 'fulfilled' ? typesRes.value.data : []);
    setPolicies(policiesRes.status === 'fulfilled' ? policiesRes.value.data : []);
    setTraining(trainingRes.status === 'fulfilled' ? trainingRes.value.data : []);
    setAuditLogs(logsRes.status === 'fulfilled' ? logsRes.value.data : []);
    setGeneratedForms(formsRes.status === 'fulfilled' ? formsRes.value.data : []);
    setTemplates(templatesRes.status === 'fulfilled' ? templatesRes.value.data : []);
    setComplianceRequirements(compReqRes.status === 'fulfilled' ? compReqRes.value.data : {});
    
    if (hasError) {
      toast.error('Failed to load employee data');
    }
    
    setLoading(false);
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
    try {
      // Get the requirement data
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
      
      // Proceed with verification - backend will handle file validation
      await axios.post(`${API}/employees/${employeeId}/requirements/${requirementId}/verify-all`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Requirement approved');
      await fetchData();
      await fetchCompliance();
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

  // Handle permanent delete file (removes from active use, keeps audit trail)
  const handleDeleteFile = async () => {
    setIsRemoving(true);
    try {
      await axios.post(
        `${API}/employees/${employeeId}/requirements/${selectedRequirementForAction}/evidence/${selectedFileForAction.file_id}/delete`,
        { reason: removeReason.trim() || null },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('File deleted successfully');
      setRemoveDialogOpen(false);
      setSelectedFileForAction(null);
      setSelectedRequirementForAction(null);
      setRemoveReason('');
      // CRITICAL: await fetchData to ensure UI syncs immediately
      await fetchData();
      await fetchCompliance();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete file');
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
      // CRITICAL: await fetchData to ensure UI syncs immediately
      await fetchData();
      await fetchCompliance();
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
    if (!trainingId) {
      toast.error('Training record not found');
      return;
    }
    const url = `${API}/training-records/${trainingId}/certificate/file`;
    setPreviewFile({ url, name: filename || 'Certificate', filename: filename || 'Certificate' });
    setPreviewOpen(true);
  };
  
  // Download training certificate
  const handleDownloadTrainingCertificate = async (trainingId, filename) => {
    if (!trainingId) {
      toast.error('Training record not found');
      return;
    }
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
      console.error('Download error:', error);
      toast.error(error.response?.status === 404 ? 'Certificate file not found' : 'Failed to download certificate');
    }
  };
  
  // Training correction handler
  const handleTrainingCorrection = async () => {
    if (!trainingCorrectionReason || trainingCorrectionReason.trim().length < 3) {
      toast.error('Please provide a reason for this correction (minimum 3 characters)');
      return;
    }
    
    try {
      await axios.post(
        `${API}/training-records/${editingTrainingRecord.id}/correct`,
        {
          field: trainingCorrectionField,
          old_value: editingTrainingRecord[trainingCorrectionField],
          new_value: trainingCorrectionValue,
          reason: trainingCorrectionReason.trim()
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Training record corrected');
      setTrainingCorrectionDialogOpen(false);
      setEditingTrainingRecord(null);
      await fetchData();
      await fetchCompliance();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to correct training record');
    }
  };

  // Delete training record handler
  const handleDeleteTrainingRecord = async () => {
    setIsDeletingTraining(true);
    try {
      await axios.delete(
        `${API}/training-records/${deletingTrainingRecord.id}`,
        { 
          headers: { Authorization: `Bearer ${token}` },
          params: { reason: deleteTrainingReason.trim() || undefined }
        }
      );
      toast.success('Training record deleted');
      setDeleteTrainingDialogOpen(false);
      setDeletingTrainingRecord(null);
      setDeleteTrainingReason('');
      await fetchData();
      await fetchCompliance();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete training record');
    } finally {
      setIsDeletingTraining(false);
    }
  };

  // Open training correction dialog from What's Needed tab
  // This reuses the same dialog as the Training tab for consistency
  const openTrainingCorrectionFromWhatsNeeded = (requirement) => {
    if (!requirement.training?.id) {
      toast.error('No training record found for this requirement');
      return;
    }
    
    // Build a training record object compatible with the correction dialog
    const trainingRecord = {
      id: requirement.training.id,
      training_name: requirement.name,
      status: requirement.training.status,
      expiry_date: requirement.training.expiry_date,
      completion_date: requirement.training.completed_at,
      verified: requirement.training.verified
    };
    
    setEditingTrainingRecord(trainingRecord);
    setTrainingCorrectionField('expiry_date');
    setTrainingCorrectionValue(trainingRecord.expiry_date?.split('T')[0] || '');
    setTrainingCorrectionReason('');
    setTrainingCorrectionDialogOpen(true);
  };

  // Open delete training dialog from What's Needed tab
  const openDeleteTrainingFromWhatsNeeded = (requirement) => {
    if (!requirement.training?.id) {
      toast.error('No training record found for this requirement');
      return;
    }
    
    // Build a training record object compatible with the delete dialog
    const trainingRecord = {
      id: requirement.training.id,
      training_name: requirement.name,
      status: requirement.training.status,
      verified: requirement.training.verified
    };
    
    setDeletingTrainingRecord(trainingRecord);
    setDeleteTrainingReason('');
    setDeleteTrainingDialogOpen(true);
  };

  // Handle requirement acknowledgement (Contract/Handbook)
  const handleAcknowledgeRequirement = async () => {
    if (!acknowledgingRequirement) return;
    
    setIsAcknowledging(true);
    try {
      await axios.post(
        `${API}/employees/${employeeId}/requirements/${acknowledgingRequirement.id}/acknowledge`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success(`${acknowledgingRequirement.name} acknowledged and completed`);
      setAcknowledgementDialogOpen(false);
      setAcknowledgingRequirement(null);
      setAcknowledgementConfirmed(false);
      await fetchData();
      await fetchCompliance();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to submit acknowledgement');
    } finally {
      setIsAcknowledging(false);
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
      // Force refresh data immediately after edit to ensure expiry status is recalculated
      await fetchData();
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

  // ========== Application Form Extraction Handlers ==========
  
  // Start extraction from application form
  const handleExtractFromApplication = async () => {
    setIsExtracting(true);
    setExtractionDialogOpen(true);
    setExtractionResult(null);
    setExtractionFailed(null);
    setFieldsToApply({});
    
    try {
      const response = await axios.post(
        `${API}/employees/${employeeId}/extract-from-application`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      // Check if extraction failed gracefully (returns extraction_failed: true)
      if (response.data.extraction_failed) {
        setExtractionFailed(response.data);
        // Don't show error toast - show the options modal instead
      } else {
        setExtractionResult(response.data);
        
        // Initialize fields to apply based on extraction result
        const initialFields = {};
        response.data.fields.forEach(field => {
          // Default: apply if field is empty in profile OR if extracted value differs
          initialFields[field.field_name] = field.apply;
        });
        setFieldsToApply(initialFields);
        
        toast.success(`Extracted ${response.data.fields.length} fields from application form`);
      }
    } catch (error) {
      // Only show toast for actual API errors (not graceful failures)
      const errorDetail = error.response?.data?.detail;
      if (errorDetail && errorDetail.includes('No application form found')) {
        toast.error('No application form found. Please upload an application form first.');
        setExtractionDialogOpen(false);
      } else {
        // For unexpected errors, show failure options
        setExtractionFailed({
          extraction_failed: true,
          message: errorDetail || 'An unexpected error occurred during extraction.',
          options: [
            { action: 'fill_manually', label: 'Fill form manually', description: 'Enter profile data manually' },
            { action: 'retry', label: 'Retry extraction', description: 'Try extracting again' }
          ]
        });
      }
    } finally {
      setIsExtracting(false);
    }
  };
  
  // Handle extraction failure options
  const handleExtractionOption = async (action) => {
    switch (action) {
      case 'fill_manually':
        setExtractionDialogOpen(false);
        setExtractionFailed(null);
        // Switch to forms tab for manual entry
        setActiveTab('forms');
        toast.info('You can manually enter profile data using the forms below.');
        break;
      case 'view_document':
        if (extractionFailed?.file_url) {
          window.open(extractionFailed.file_url, '_blank');
        }
        break;
      case 'retry':
        setExtractionFailed(null);
        await handleExtractFromApplication();
        break;
      default:
        break;
    }
  };
  
  // Toggle a field for applying
  const toggleFieldToApply = (fieldName) => {
    setFieldsToApply(prev => ({
      ...prev,
      [fieldName]: !prev[fieldName]
    }));
  };
  
  // Apply selected extracted fields to profile
  const handleApplyExtraction = async () => {
    if (!extractionResult) return;
    
    const selectedFields = Object.entries(fieldsToApply)
      .filter(([_, apply]) => apply)
      .map(([fieldName]) => fieldName);
    
    if (selectedFields.length === 0) {
      toast.error('Please select at least one field to apply');
      return;
    }
    
    setIsApplyingExtraction(true);
    try {
      const response = await axios.post(
        `${API}/extractions/${extractionResult.extraction_id}/apply`,
        { extraction_id: extractionResult.extraction_id, fields_to_apply: selectedFields },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      const result = response.data;
      
      // Show success with details
      if (result.applied_fields && result.applied_fields.length > 0) {
        toast.success(`Profile updated: ${result.applied_fields.length} field(s) applied`);
      }
      
      // Show warnings for failed fields
      if (result.warnings?.failed_fields?.length > 0) {
        const failedNames = result.warnings.failed_fields.map(f => f.field).join(', ');
        toast.warning(`Some fields could not be applied: ${failedNames}`);
      }
      
      // Show info for unsupported fields
      if (result.unsupported?.fields?.length > 0) {
        const unsupportedNames = result.unsupported.fields.map(f => f.field).join(', ');
        toast.info(`Unsupported fields skipped: ${unsupportedNames}`);
      }
      
      setExtractionDialogOpen(false);
      setExtractionResult(null);
      
      // Refresh employee data
      try {
        await fetchData();
      } catch (refreshError) {
        console.error('Error refreshing data after apply:', refreshError);
        // Don't show error toast - the apply was successful
      }
    } catch (error) {
      const errorDetail = error.response?.data?.detail;
      
      if (typeof errorDetail === 'object') {
        // Structured error response
        const message = errorDetail.message || 'Failed to apply extracted data';
        const failedFields = errorDetail.failed_fields || [];
        const unsupportedFields = errorDetail.unsupported_fields || [];
        
        if (failedFields.length > 0) {
          const failedInfo = failedFields.map(f => `${f.field}: ${f.reason}`).join('\n');
          toast.error(`${message}\n${failedInfo}`);
        } else if (unsupportedFields.length > 0) {
          toast.error(`${message}: ${unsupportedFields.map(f => f.field).join(', ')}`);
        } else {
          toast.error(message);
        }
      } else {
        toast.error(errorDetail || 'Failed to apply extracted data');
      }
    } finally {
      setIsApplyingExtraction(false);
    }
  };
  
  // Discard extraction without applying
  const handleDiscardExtraction = async () => {
    // If there's a failed extraction, just close the dialog
    if (extractionFailed) {
      setExtractionDialogOpen(false);
      setExtractionFailed(null);
      return;
    }
    
    if (!extractionResult) {
      setExtractionDialogOpen(false);
      return;
    }
    
    try {
      await axios.post(
        `${API}/extractions/${extractionResult.extraction_id}/discard`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.info('Extraction discarded');
    } catch (error) {
      // Ignore discard errors
    }
    
    setExtractionDialogOpen(false);
    setExtractionResult(null);
    setExtractionFailed(null);
  };
  
  // Human-readable field name mapping
  const FIELD_LABELS = {
    first_name: 'First Name',
    last_name: 'Last Name',
    email: 'Email Address',
    phone: 'Phone Number',
    address_line_1: 'Address Line 1',
    address_line_2: 'Address Line 2',
    city: 'City',
    county: 'County',
    postcode: 'Postcode',
    country: 'Country',
    ni_number: 'NI Number',
    date_of_birth: 'Date of Birth',
    next_of_kin_name: 'Next of Kin Name',
    next_of_kin_relationship: 'Next of Kin Relationship',
    next_of_kin_phone: 'Next of Kin Phone',
    next_of_kin_address: 'Next of Kin Address',
    emergency_contact_name: 'Emergency Contact Name',
    emergency_contact_phone: 'Emergency Contact Phone',
    emergency_contact_relationship: 'Emergency Contact Relationship',
    reference_1_name: 'Reference 1 Name',
    reference_1_company: 'Reference 1 Company',
    reference_1_phone: 'Reference 1 Phone',
    reference_1_email: 'Reference 1 Email',
    reference_2_name: 'Reference 2 Name',
    reference_2_company: 'Reference 2 Company',
    reference_2_phone: 'Reference 2 Phone',
    reference_2_email: 'Reference 2 Email',
    has_driving_licence: 'Has Driving Licence',
    driving_licence_type: 'Driving Licence Type',
    has_own_vehicle: 'Has Own Vehicle',
    vehicle_registration: 'Vehicle Registration'
  };

  // ========== Form Submission Handlers ==========
  
  // Open form modal for a specific requirement
  const openFormModal = async (requirementId) => {
    try {
      const response = await axios.get(`${API}/form-submissions/template/${requirementId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setFormTemplate(response.data);
      
      // Check if there's an existing submission to pre-fill
      const existingResponse = await axios.get(`${API}/form-submissions?employee_id=${employeeId}&requirement_id=${requirementId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      // Get today's date in YYYY-MM-DD format for auto-fill
      const today = new Date().toISOString().split('T')[0];
      
      if (existingResponse.data && existingResponse.data.length > 0) {
        // Use existing submission data
        setFormData(existingResponse.data[0].data || {});
      } else {
        // Fetch auto-fill data from backend based on employee profile
        try {
          const autoFillResponse = await axios.get(
            `${API}/form-submissions/auto-fill/${requirementId}/${employeeId}`,
            { headers: { Authorization: `Bearer ${token}` } }
          );
          // Add today's date for signature_date if not already set
          const autoFillData = autoFillResponse.data.auto_fill_data || {};
          if (!autoFillData.signature_date) {
            autoFillData.signature_date = today;
          }
          setFormData(autoFillData);
        } catch (autoFillError) {
          // Fallback to basic employee data if auto-fill endpoint fails
          setFormData({
            employee_name: `${employee.first_name} ${employee.last_name}`,
            full_name: `${employee.first_name} ${employee.last_name}`,
            candidate_name: `${employee.first_name} ${employee.last_name}`,
            signature_date: today
          });
        }
      }
      
      setFormModalOpen(true);
    } catch (error) {
      toast.error('Failed to load form template');
    }
  };
  
  // Submit structured form
  const handleFormSubmit = async () => {
    if (!formTemplate) return;
    
    setIsSubmittingForm(true);
    try {
      await axios.post(`${API}/form-submissions`, {
        employee_id: employeeId,
        requirement_id: formTemplate.requirement_id,
        form_type: formTemplate.form_type,
        data: formData
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      toast.success(`${formTemplate.name} submitted successfully`);
      setFormModalOpen(false);
      setFormTemplate(null);
      setFormData({});
      fetchData(); // Refresh all data including compliance requirements
    } catch (error) {
      console.error('Form submission error:', error);
      toast.error(error.response?.data?.detail || 'Failed to submit form');
    } finally {
      setIsSubmittingForm(false);
    }
  };
  
  // View submitted form
  const openViewForm = (requirement) => {
    if (requirement.form_submission) {
      setViewFormData({
        ...requirement.form_submission,
        requirementName: requirement.name
      });
      setViewFormOpen(true);
    }
  };
  
  // Verify form submission
  const handleVerifyFormSubmission = async (submissionId) => {
    try {
      await axios.post(`${API}/form-submissions/${submissionId}/verify`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Form verified successfully');
      setViewFormOpen(false);
      fetchData(); // Refresh all data including compliance requirements
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to verify form');
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
                  {/* File Status Badge - Uses API work_readiness status (single source of truth) */}
                  {(() => {
                    const workReadiness = complianceRequirements?.work_readiness || {};
                    const statusLabel = workReadiness.status_label || 'Unknown';
                    const statusColor = workReadiness.status_color === 'success' ? 'bg-success/10 text-success' : 
                                       workReadiness.status_color === 'warning' ? 'bg-warning/10 text-warning' : 
                                       'bg-gray-100 text-gray-600';
                    return (
                      <span className={`px-2 py-1 rounded-lg text-xs font-medium ${statusColor}`}>
                        {statusLabel}
                      </span>
                    );
                  })()}
                </div>
              </div>
            </div>

            <div className="flex flex-col items-end gap-4">
              <div className="flex items-center gap-3">
                <div className="text-right">
                  <p className="text-sm text-text-muted">Progress</p>
                  {/* Use single source of truth from complianceRequirements */}
                  <p className="text-3xl font-heading font-bold text-text-primary">
                    {complianceRequirements?.statuses?.overall_compliance?.percentage ?? employee.completion_percentage ?? 0}% Complete
                  </p>
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
              <Progress 
                value={complianceRequirements?.statuses?.overall_compliance?.percentage ?? employee.completion_percentage ?? 0} 
                className="w-32 h-2" 
              />
            </div>
          </div>

          {/* AUDIT QUICK VIEW - Key compliance items at a glance */}
          {(() => {
            // Extract key compliance data for audit visibility
            const reqs = complianceRequirements?.requirements || [];
            
            // SAFETY ENGINES - USE COMPUTED DATA FROM API (single source of truth)
            const rtwSummary = complianceRequirements?.rtw_summary || {};
            const dbsSummary = complianceRequirements?.dbs_summary || {};
            const trainingSummary = complianceRequirements?.training_summary || {};
            const safetyStatus = complianceRequirements?.safety_status || {};
            
            // Calculate missing items (no evidence)
            const missingItems = reqs.filter(r => !r.has_evidence && r.requirement_type !== 'conditional').length;
            
            // Calculate pending review (has evidence but not verified)
            const pendingReview = reqs.filter(r => r.has_evidence && !r.verified).length;
            
            // Safety engine blocking status
            const isBlocking = safetyStatus.is_safe_to_deploy === false;
            const blockingReasons = complianceRequirements?.statuses?.safety_blocking_reasons || [];
            
            // DBS info from safety engine
            const dbsExpiry = dbsSummary.review_due_date || dbsSummary.next_dbs_review_due;
            const dbsExpiryDays = dbsSummary.days_remaining;
            const dbsBlocking = dbsSummary.is_blocking;
            
            // RTW info from safety engine
            const rtwExpiry = rtwSummary.expiry_date;
            const rtwExpiryDays = rtwSummary.days_remaining;
            const rtwBlocking = rtwSummary.is_blocking;
            
            // Training info from safety engine
            const trainingBlocking = trainingSummary.is_blocking;
            
            // Category breakdown
            const categoryStats = {};
            reqs.forEach(r => {
              const cat = r.category || 'Other';
              if (!categoryStats[cat]) {
                categoryStats[cat] = { total: 0, complete: 0, verified: 0 };
              }
              categoryStats[cat].total += 1;
              if (r.has_evidence) categoryStats[cat].complete += 1;
              if (r.verified) categoryStats[cat].verified += 1;
            });
            
            // Map categories to display names
            const categoryDisplayNames = {
              '1_Legal_Safety': 'Legal & Safety',
              '2_Core_Training': 'Training',
              '3_Competency_Health': 'Health',
              '4_Recruitment_Record': 'Recruitment',
              '5_Agreements': 'Agreements',
              '6_Admin': 'Admin'
            };
            
            return (
              <div className="mt-6 pt-6 border-t border-[#E4E8EB]">
                {/* Audit Quick View Header */}
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider">Audit Quick View</h3>
                  <p className="text-xs text-text-muted">Key compliance items for checker review</p>
                </div>
                
                {/* Quick Status Cards - 4 cards */}
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-3" data-testid="audit-quick-view">
                  {/* DBS Status with Expiry */}
                  <div className={`p-3 rounded-xl border ${
                    dbsBlocking || dbsSummary.dbs_status_color === 'red' ? 'border-red-200 bg-red-50' :
                    dbsSummary.status_band === 'urgent' || dbsSummary.status_band === 'due_soon' ? 'border-amber-200 bg-amber-50' :
                    dbsSummary.dbs_status_color === 'green' ? 'border-green-200 bg-green-50' : 'border-blue-200 bg-blue-50'
                  }`} data-testid="dbs-status-card">
                    <div className="flex items-center gap-2 mb-1">
                      <Shield className={`h-4 w-4 ${
                        dbsBlocking || dbsSummary.dbs_status_color === 'red' ? 'text-red-600' :
                        dbsSummary.status_band === 'urgent' || dbsSummary.status_band === 'due_soon' ? 'text-amber-600' :
                        dbsSummary.dbs_status_color === 'green' ? 'text-green-600' : 'text-blue-600'
                      }`} />
                      <span className="text-xs font-semibold text-text-primary">DBS</span>
                      {dbsBlocking && <span className="text-xs px-1 py-0.5 bg-red-600 text-white rounded">BLOCKED</span>}
                    </div>
                    <p className={`text-sm font-medium ${
                      dbsBlocking || dbsSummary.dbs_status_color === 'red' ? 'text-red-700' :
                      dbsSummary.status_band === 'urgent' || dbsSummary.status_band === 'due_soon' ? 'text-amber-700' :
                      dbsSummary.dbs_status_color === 'green' ? 'text-green-700' : 'text-blue-700'
                    }`}>
                      {dbsSummary.dbs_status_label || 'Unknown'}
                    </p>
                    {dbsExpiry && (
                      <p className={`text-xs mt-1 ${
                        dbsExpiryDays !== null && dbsExpiryDays < 0 ? 'text-red-600 font-medium' :
                        dbsSummary.status_band === 'urgent' ? 'text-amber-600 font-medium' : 'text-text-muted'
                      }`}>
                        {dbsExpiryDays !== null && dbsExpiryDays < 0 ? 'Overdue: ' : 'Review: '}
                        {new Date(dbsExpiry).toLocaleDateString()}
                        {dbsExpiryDays !== null && dbsExpiryDays > 0 && dbsExpiryDays <= 60 && (
                          <span className="ml-1">({dbsExpiryDays}d)</span>
                        )}
                      </p>
                    )}
                  </div>
                  
                  {/* RTW Status with Expiry - MUST show expiry date clearly */}
                  <div className={`p-3 rounded-xl border ${
                    rtwBlocking || rtwSummary.rtw_status_color === 'red' ? 'border-red-200 bg-red-50' :
                    rtwSummary.status_band === 'urgent' || rtwSummary.status_band === 'due_soon' ? 'border-amber-200 bg-amber-50' :
                    rtwSummary.rtw_status_color === 'green' ? 'border-green-200 bg-green-50' : 'border-blue-200 bg-blue-50'
                  }`} data-testid="rtw-status-card">
                    <div className="flex items-center gap-2 mb-1">
                      <FileCheck className={`h-4 w-4 ${
                        rtwBlocking || rtwSummary.rtw_status_color === 'red' ? 'text-red-600' :
                        rtwSummary.status_band === 'urgent' || rtwSummary.status_band === 'due_soon' ? 'text-amber-600' :
                        rtwSummary.rtw_status_color === 'green' ? 'text-green-600' : 'text-blue-600'
                      }`} />
                      <span className="text-xs font-semibold text-text-primary">Right to Work</span>
                      {rtwBlocking && <span className="text-xs px-1 py-0.5 bg-red-600 text-white rounded">BLOCKED</span>}
                    </div>
                    <p className={`text-sm font-medium ${
                      rtwBlocking || rtwSummary.rtw_status_color === 'red' ? 'text-red-700' :
                      rtwSummary.status_band === 'urgent' || rtwSummary.status_band === 'due_soon' ? 'text-amber-700' :
                      rtwSummary.rtw_status_color === 'green' ? 'text-green-700' : 'text-blue-700'
                    }`}>
                      {rtwSummary.rtw_status_label || 'Unknown'}
                    </p>
                    {/* RTW Expiry - prominently displayed */}
                    {rtwExpiry ? (
                      <p className={`text-xs mt-1 font-medium ${
                        rtwSummary.status_band === 'expired' ? 'text-red-600' :
                        rtwSummary.status_band === 'urgent' ? 'text-amber-600' : 'text-text-muted'
                      }`}>
                        {rtwSummary.status_band === 'expired' ? '⚠ Expired: ' : 'Expires: '}
                        {new Date(rtwExpiry).toLocaleDateString()}
                        {rtwExpiryDays !== undefined && rtwExpiryDays !== null && rtwExpiryDays > 0 && (
                          <span className="ml-1">({rtwExpiryDays}d)</span>
                        )}
                      </p>
                    ) : rtwSummary.permission_type === 'permanent' ? (
                      <p className="text-xs mt-1 text-green-600 font-medium">Permanent - No Expiry</p>
                    ) : (
                      <p className="text-xs mt-1 text-text-muted">No expiry set</p>
                    )}
                  </div>
                  
                  {/* Alerts Card - Show blocking status prominently */}
                  <div className={`p-3 rounded-xl border ${
                    isBlocking ? 'border-red-200 bg-red-50' :
                    (missingItems > 0 || pendingReview > 0) ? 'border-amber-200 bg-amber-50' : 
                    'border-green-200 bg-green-50'
                  }`} data-testid="alerts-card">
                    <div className="flex items-center gap-2 mb-1">
                      <AlertTriangle className={`h-4 w-4 ${
                        isBlocking ? 'text-red-600' :
                        (missingItems > 0 || pendingReview > 0) ? 'text-amber-600' : 'text-green-600'
                      }`} />
                      <span className="text-xs font-semibold text-text-primary">
                        {isBlocking ? 'BLOCKED' : 'Alerts'}
                      </span>
                    </div>
                    {isBlocking ? (
                      <div className="space-y-0.5">
                        <p className="text-xs text-red-700 font-semibold">Not Work Ready</p>
                        {blockingReasons.slice(0, 2).map((reason, idx) => (
                          <p key={idx} className="text-xs text-red-600 line-clamp-1" title={reason}>
                            {reason?.split(' - ')[0] || reason}
                          </p>
                        ))}
                      </div>
                    ) : (missingItems > 0 || pendingReview > 0) ? (
                      <div className="space-y-0.5">
                        {missingItems > 0 && (
                          <p className="text-xs text-amber-700">{missingItems} missing</p>
                        )}
                        {pendingReview > 0 && (
                          <p className="text-xs text-amber-700">{pendingReview} pending</p>
                        )}
                      </div>
                    ) : (
                      <p className="text-sm font-medium text-green-700">Work Ready</p>
                    )}
                  </div>
                  
                  {/* Compliance Breakdown Card */}
                  <div className="p-3 rounded-xl border border-slate-200 bg-slate-50" data-testid="compliance-breakdown-card">
                    <div className="flex items-center gap-2 mb-2">
                      <ClipboardList className="h-4 w-4 text-slate-600" />
                      <span className="text-xs font-semibold text-text-primary">Breakdown</span>
                    </div>
                    <div className="grid grid-cols-2 gap-x-3 gap-y-1">
                      {Object.entries(categoryStats)
                        .sort(([a], [b]) => a.localeCompare(b))
                        .slice(0, 4) // Show top 4 categories
                        .map(([cat, stats]) => {
                          const displayName = categoryDisplayNames[cat] || cat.replace(/^\d+_/, '').replace(/_/g, ' ');
                          const isComplete = stats.complete === stats.total;
                          return (
                            <div key={cat} className="flex items-center justify-between">
                              <span className="text-xs text-text-muted truncate">{displayName}</span>
                              <span className={`text-xs font-medium ${isComplete ? 'text-green-600' : 'text-amber-600'}`}>
                                {stats.complete}/{stats.total}
                              </span>
                            </div>
                          );
                        })}
                    </div>
                  </div>
                </div>
              </div>
            );
          })()}

          {/* Status Strip - Replaces contact row */}
          <div className="flex flex-wrap items-center gap-4 mt-4 pt-4 border-t border-[#E4E8EB]" data-testid="status-strip">
            {/* Employee ID - Always show business-facing code (OCS-XXXX), never internal UUID */}
            <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-100 rounded-lg">
              <User className="h-4 w-4 text-slate-500" />
              <span className="text-sm text-slate-500">Employee ID:</span>
              <span className="text-sm font-semibold text-slate-700">{employee.employee_code || 'Not assigned'}</span>
            </div>
            
            {/* Missing Items */}
            {(() => {
              const reqs = complianceRequirements?.requirements || [];
              const missing = reqs.filter(r => !r.has_evidence && r.requirement_type !== 'conditional').length;
              if (missing > 0) {
                return (
                  <div className="flex items-center gap-2 px-3 py-1.5 bg-red-100 rounded-lg">
                    <XCircle className="h-4 w-4 text-red-600" />
                    <span className="text-sm font-medium text-red-700">{missing} Missing</span>
                  </div>
                );
              }
              return null;
            })()}
            
            {/* Pending Review */}
            {(() => {
              const reqs = complianceRequirements?.requirements || [];
              const pending = reqs.filter(r => r.has_evidence && !r.verified).length;
              if (pending > 0) {
                return (
                  <div className="flex items-center gap-2 px-3 py-1.5 bg-amber-100 rounded-lg">
                    <Clock className="h-4 w-4 text-amber-600" />
                    <span className="text-sm font-medium text-amber-700">{pending} Pending Review</span>
                  </div>
                );
              }
              return null;
            })()}
            
            {/* Key Expiry - Show most critical */}
            {(() => {
              const dbsSummary = complianceRequirements?.dbs_summary || {};
              const rtwSummary = complianceRequirements?.rtw_summary || {};
              
              // Check RTW expiry first (more critical)
              if (rtwSummary.expiry_date) {
                const days = rtwSummary.days_until_expiry;
                if (days !== undefined && days <= 30) {
                  return (
                    <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg ${
                      days <= 0 ? 'bg-red-100' : 'bg-amber-100'
                    }`}>
                      <Calendar className={`h-4 w-4 ${days <= 0 ? 'text-red-600' : 'text-amber-600'}`} />
                      <span className={`text-sm font-medium ${days <= 0 ? 'text-red-700' : 'text-amber-700'}`}>
                        RTW {days <= 0 ? 'Expired' : `Expires ${days}d`}
                      </span>
                    </div>
                  );
                }
              }
              
              // Check DBS expiry
              if (dbsSummary.next_dbs_review_due) {
                const days = Math.ceil((new Date(dbsSummary.next_dbs_review_due) - new Date()) / (1000 * 60 * 60 * 24));
                if (days <= 30) {
                  return (
                    <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg ${
                      days <= 0 ? 'bg-red-100' : 'bg-amber-100'
                    }`}>
                      <Calendar className={`h-4 w-4 ${days <= 0 ? 'text-red-600' : 'text-amber-600'}`} />
                      <span className={`text-sm font-medium ${days <= 0 ? 'text-red-700' : 'text-amber-700'}`}>
                        DBS {days <= 0 ? 'Overdue' : `Review ${days}d`}
                      </span>
                    </div>
                  );
                }
              }
              
              return null;
            })()}
            
            {/* All Clear badge if no issues */}
            {(() => {
              const reqs = complianceRequirements?.requirements || [];
              const missing = reqs.filter(r => !r.has_evidence && r.requirement_type !== 'conditional').length;
              const pending = reqs.filter(r => r.has_evidence && !r.verified).length;
              
              if (missing === 0 && pending === 0) {
                return (
                  <div className="flex items-center gap-2 px-3 py-1.5 bg-green-100 rounded-lg">
                    <CheckCircle className="h-4 w-4 text-green-600" />
                    <span className="text-sm font-medium text-green-700">All Verified</span>
                  </div>
                );
              }
              return null;
            })()}
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
                      <FileUploaderInline
                        onFileSelect={(file) => setUploadFile(file)}
                        selectedFile={uploadFile}
                        onClear={() => setUploadFile(null)}
                        placeholder="Drop file here or click to browse"
                        data-testid="doc-file-input"
                      />
                      <p className="text-xs text-text-muted">
                        Upload a clear copy of the document. PDF, JPG, PNG accepted (max 10MB).
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

              {/* Note: Bulk Upload functionality removed from individual employee profile.
                  Bulk operations should be done from the bulk actions screen. */}

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
                      <FileUploaderInline
                        onFileSelect={(file) => setImportAppFile(file)}
                        selectedFile={importAppFile}
                        onClear={() => setImportAppFile(null)}
                        acceptedTypes={['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']}
                        placeholder="Drop application form here or click to browse"
                      />
                    </div>

                    <div className="space-y-2">
                      <Label className="text-sm font-medium">
                        CV / Resume <span className="text-text-muted">(optional)</span>
                      </Label>
                      <FileUploaderInline
                        onFileSelect={(file) => setImportCvFile(file)}
                        selectedFile={importCvFile}
                        onClear={() => setImportCvFile(null)}
                        acceptedTypes={['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']}
                        placeholder="Drop CV here or click to browse"
                      />
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
                      <FileUploaderInline
                        onFileSelect={(file) => setImportDocFile(file)}
                        selectedFile={importDocFile}
                        onClear={() => setImportDocFile(null)}
                        acceptedTypes={['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'image/jpeg', 'image/jpg', 'image/png']}
                        placeholder="Drop document here or click to browse"
                      />
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
                <div className="flex items-center justify-between">
                  <CardTitle className="font-heading text-lg">Personal Details</CardTitle>
                  {!isAuditor() && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleExtractFromApplication}
                      disabled={isExtracting}
                      className="text-xs"
                      data-testid="extract-from-app-btn"
                    >
                      {isExtracting ? (
                        <><Loader2 className="h-3 w-3 animate-spin mr-1" /> Extracting...</>
                      ) : (
                        <><FileText className="h-3 w-3 mr-1" /> Extract from App Form</>
                      )}
                    </Button>
                  )}
                </div>
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
                  {employee.ni_number && (
                    <div>
                      <p className="text-sm text-text-muted">NI Number</p>
                      <p className="font-medium text-text-primary">{employee.ni_number}</p>
                    </div>
                  )}
                  {employee.date_of_birth && (
                    <div>
                      <p className="text-sm text-text-muted">Date of Birth</p>
                      <p className="font-medium text-text-primary">{employee.date_of_birth}</p>
                    </div>
                  )}
                </div>
                
                {/* Address Section */}
                {(employee.address_line_1 || employee.city || employee.postcode) && (
                  <div className="pt-3 border-t border-gray-100">
                    <p className="text-sm text-text-muted mb-1">Address</p>
                    <p className="font-medium text-text-primary">
                      {[employee.address_line_1, employee.address_line_2, employee.city, employee.county, employee.postcode, employee.country]
                        .filter(Boolean)
                        .join(', ')}
                    </p>
                  </div>
                )}
                
                {/* Emergency Contact Section */}
                {(employee.next_of_kin_name || employee.emergency_contact_name) && (
                  <div className="pt-3 border-t border-gray-100">
                    <p className="text-sm text-text-muted mb-1">Emergency Contact / Next of Kin</p>
                    {employee.next_of_kin_name && (
                      <p className="font-medium text-text-primary text-sm">
                        {employee.next_of_kin_name} {employee.next_of_kin_relationship && `(${employee.next_of_kin_relationship})`}
                        {employee.next_of_kin_phone && ` - ${employee.next_of_kin_phone}`}
                      </p>
                    )}
                    {employee.emergency_contact_name && !employee.next_of_kin_name && (
                      <p className="font-medium text-text-primary text-sm">
                        {employee.emergency_contact_name} {employee.emergency_contact_relationship && `(${employee.emergency_contact_relationship})`}
                        {employee.emergency_contact_phone && ` - ${employee.emergency_contact_phone}`}
                      </p>
                    )}
                  </div>
                )}
                
                {/* Driving Info */}
                {(employee.has_driving_licence || employee.has_own_vehicle) && (
                  <div className="pt-3 border-t border-gray-100">
                    <p className="text-sm text-text-muted mb-1">Driving / Vehicle</p>
                    <div className="flex gap-3 text-sm">
                      {employee.has_driving_licence && (
                        <span className="px-2 py-0.5 bg-green-100 text-green-700 rounded">
                          {employee.driving_licence_type || 'Driving Licence'}
                        </span>
                      )}
                      {employee.has_own_vehicle && (
                        <span className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded">
                          Own Vehicle {employee.vehicle_registration && `(${employee.vehicle_registration})`}
                        </span>
                      )}
                    </div>
                  </div>
                )}
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
                <p className="text-xs text-text-muted mt-1">
                  Upload each required document, then verify it. Only verified documents count towards compliance.
                </p>
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
              {/* START STATUS ALERT PANEL - Using new statuses model */}
              {complianceRequirements?.statuses?.start_status && (
                <div className={`mb-6 p-4 rounded-xl border ${
                  complianceRequirements.statuses.start_status.status === 'ready_to_work' ? 'bg-green-50 border-green-200' :
                  complianceRequirements.statuses.start_status.status === 'supervised_start_only' ? 'bg-amber-50 border-amber-200' :
                  'bg-red-50 border-red-200'
                }`}>
                  <div className="flex items-start gap-3">
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 ${
                      complianceRequirements.statuses.start_status.status === 'ready_to_work' ? 'bg-green-100' :
                      complianceRequirements.statuses.start_status.status === 'supervised_start_only' ? 'bg-amber-100' :
                      'bg-red-100'
                    }`}>
                      {complianceRequirements.statuses.start_status.status === 'ready_to_work' ? (
                        <Shield className="h-5 w-5 text-green-600" />
                      ) : complianceRequirements.statuses.start_status.status === 'supervised_start_only' ? (
                        <Shield className="h-5 w-5 text-amber-600" />
                      ) : (
                        <AlertTriangle className="h-5 w-5 text-red-600" />
                      )}
                    </div>
                    <div className="flex-1">
                      <h4 className={`font-semibold ${
                        complianceRequirements.statuses.start_status.status === 'ready_to_work' ? 'text-green-900' :
                        complianceRequirements.statuses.start_status.status === 'supervised_start_only' ? 'text-amber-900' :
                        'text-red-900'
                      }`}>
                        Start Status: {complianceRequirements.statuses.start_status.label}
                      </h4>
                      <p className={`text-sm mt-1 ${
                        complianceRequirements.statuses.start_status.status === 'ready_to_work' ? 'text-green-800' :
                        complianceRequirements.statuses.start_status.status === 'supervised_start_only' ? 'text-amber-800' :
                        'text-red-800'
                      }`}>
                        {complianceRequirements.statuses.start_status.status === 'ready_to_work' ? (
                          "All legal, safety, and core training requirements are verified. This employee can safely start work."
                        ) : complianceRequirements.statuses.start_status.status === 'supervised_start_only' ? (
                          "Legal and safety basics are complete but health/competency items are still incomplete. Employee can start with supervision."
                        ) : (
                          <>
                            <strong>{complianceRequirements.statuses.start_status.verified || 0} of {complianceRequirements.statuses.start_status.total || 0}</strong> required items verified
                          </>
                        )}
                      </p>
                      
                      {/* Missing Required Items */}
                      {complianceRequirements.statuses.start_status.missing?.length > 0 && (
                        <div className="mt-3">
                          <p className={`text-sm font-medium ${
                            complianceRequirements.statuses.start_status.status === 'supervised_start_only' ? 'text-amber-900' : 'text-red-900'
                          }`}>
                            Missing items (required to start work):
                          </p>
                          <ul className={`mt-1 space-y-1 text-sm ${
                            complianceRequirements.statuses.start_status.status === 'supervised_start_only' ? 'text-amber-800' : 'text-red-800'
                          }`}>
                            {complianceRequirements.statuses.start_status.missing.map((item, idx) => (
                              <li key={idx} className="flex items-center gap-2">
                                <span className="w-1.5 h-1.5 rounded-full bg-current"></span>
                                {item.name}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* Overall Compliance Score */}
                      <div className="mt-3 flex items-center gap-3">
                        <div className={`text-sm font-medium ${
                          (complianceRequirements.statuses.overall_compliance?.percentage || 0) >= 80 ? 'text-green-700' :
                          (complianceRequirements.statuses.overall_compliance?.percentage || 0) >= 50 ? 'text-amber-700' :
                          'text-red-700'
                        }`}>
                          Overall Compliance: {complianceRequirements.statuses.overall_compliance?.percentage || 0}%
                        </div>
                        <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
                          <div 
                            className={`h-full rounded-full transition-all ${
                              (complianceRequirements.statuses.overall_compliance?.percentage || 0) >= 80 ? 'bg-green-500' :
                              (complianceRequirements.statuses.overall_compliance?.percentage || 0) >= 50 ? 'bg-amber-500' :
                              'bg-red-500'
                            }`}
                            style={{ width: `${complianceRequirements.statuses.overall_compliance?.percentage || 0}%` }}
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
                  Items marked with <span className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-red-100 text-red-700 rounded text-xs font-medium">Required</span> must be completed and verified before the employee can start work.
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
                      <span><strong>Supervised Start / Health</strong> — Required for supervised work</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <span className="inline-block w-3 h-3 rounded-full bg-blue-500"></span>
                      <span><strong>Recruitment File</strong> — Pre-employment record</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <span className="inline-block w-3 h-3 rounded-full bg-gray-400"></span>
                      <span><strong>Complete After Start</strong> — For full compliance</span>
                    </li>
                  </ul>
                </div>
              </div>

              {/* TAB CLARITY MESSAGE */}
              <p className="text-xs text-text-muted mb-4 px-1">
                Use "What's Needed" to complete compliance. Other tabs show records and history.
              </p>

              {/* COMPLIANCE ALERTS - Expiry Warnings */}
              {complianceRequirements?.expiry_alerts?.has_alerts && (
                <div className={`mb-6 p-4 rounded-xl border ${
                  complianceRequirements.expiry_alerts.expired_count > 0 
                    ? 'bg-red-50 border-red-200' 
                    : 'bg-amber-50 border-amber-200'
                }`}>
                  <div className="flex items-start gap-3">
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 ${
                      complianceRequirements.expiry_alerts.expired_count > 0 ? 'bg-red-100' : 'bg-amber-100'
                    }`}>
                      <Clock className={`h-5 w-5 ${
                        complianceRequirements.expiry_alerts.expired_count > 0 ? 'text-red-600' : 'text-amber-600'
                      }`} />
                    </div>
                    <div className="flex-1">
                      <h4 className={`font-semibold ${
                        complianceRequirements.expiry_alerts.expired_count > 0 ? 'text-red-900' : 'text-amber-900'
                      }`}>
                        Compliance Alerts
                      </h4>
                      <p className={`text-sm mt-1 ${
                        complianceRequirements.expiry_alerts.expired_count > 0 ? 'text-red-800' : 'text-amber-800'
                      }`}>
                        {complianceRequirements.expiry_alerts.expired_count > 0 && (
                          <span className="font-medium">{complianceRequirements.expiry_alerts.expired_count} item{complianceRequirements.expiry_alerts.expired_count !== 1 ? 's' : ''} expired</span>
                        )}
                        {complianceRequirements.expiry_alerts.expired_count > 0 && complianceRequirements.expiry_alerts.expiring_soon_count > 0 && ' · '}
                        {complianceRequirements.expiry_alerts.expiring_soon_count > 0 && (
                          <span>{complianceRequirements.expiry_alerts.expiring_soon_count} item{complianceRequirements.expiry_alerts.expiring_soon_count !== 1 ? 's' : ''} expiring soon</span>
                        )}
                      </p>
                      
                      {/* Expired Items */}
                      {complianceRequirements.expiry_alerts.expired?.length > 0 && (
                        <div className="mt-2">
                          <p className="text-xs font-medium text-red-900">Expired:</p>
                          <ul className="mt-1 space-y-0.5">
                            {complianceRequirements.expiry_alerts.expired.map((item, idx) => (
                              <li key={idx} className="text-xs text-red-800 flex items-center gap-1">
                                <span className="w-1 h-1 rounded-full bg-red-500"></span>
                                {item.name} — expired {item.days_overdue} day{item.days_overdue !== 1 ? 's' : ''} ago
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                      
                      {/* Expiring Soon Items */}
                      {complianceRequirements.expiry_alerts.expiring_soon?.length > 0 && (
                        <div className="mt-2">
                          <p className="text-xs font-medium text-amber-900">Expiring Soon:</p>
                          <ul className="mt-1 space-y-0.5">
                            {complianceRequirements.expiry_alerts.expiring_soon.map((item, idx) => (
                              <li key={idx} className="text-xs text-amber-800 flex items-center gap-1">
                                <span className="w-1 h-1 rounded-full bg-amber-500"></span>
                                {item.name} — expires in {item.days_until_expiry} day{item.days_until_expiry !== 1 ? 's' : ''}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* CONDITIONAL ITEMS INFO - Show items not required due to existing evidence */}
              {complianceRequirements?.conditional_not_required?.length > 0 && (
                <div className="mb-4 p-3 bg-gray-50 border border-gray-200 rounded-lg">
                  <div className="flex items-start gap-2">
                    <CheckCircle className="h-4 w-4 text-green-600 mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="text-sm font-medium text-gray-700">Some items not required for this employee:</p>
                      <ul className="mt-1 space-y-0.5">
                        {complianceRequirements.conditional_not_required.map((item, idx) => (
                          <li key={idx} className="text-xs text-gray-600">
                            {item.name} — {item.reason}
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>
              )}

              {!complianceRequirements ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="h-8 w-8 animate-spin text-primary" />
                </div>
              ) : (
                <div className="space-y-6">
                  {/* Group requirements by category */}
                  {/* Care-focused category order - highest risk first */}
                  {(() => {
                    // Category display names (care-focused) - MUST match backend MANDATORY_ITEMS
                    const CATEGORY_DISPLAY = {
                      "1_Legal_Safety": "Legal & Safety",
                      "2_Core_Training": "Core Training",
                      "3_Competency_Health": "Supervised Start / Health",
                      "4_Recruitment_Record": "Recruitment File",
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
                      "policies_signed": "Upload signed policy acknowledgement forms",
                      "hmrc_starter_checklist": "Complete this form if employee does not have a P45 from previous employer"
                    };
                    
                    // Priority order - MUST match backend MANDATORY_ITEMS categories
                    const categoryOrder = [
                      "1_Legal_Safety",
                      "2_Core_Training",
                      "3_Competency_Health",
                      "4_Recruitment_Record",
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
                                    {req.priority === 'start_required' && (
                                      <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-red-100 text-red-700 font-medium flex items-center gap-1">
                                        <span className="w-1.5 h-1.5 rounded-full bg-red-500"></span>
                                        Required
                                      </span>
                                    )}
                                    {req.priority === 'supervised_start' && (
                                      <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-orange-100 text-orange-700 font-medium flex items-center gap-1">
                                        <span className="w-1.5 h-1.5 rounded-full bg-orange-500"></span>
                                        Health
                                      </span>
                                    )}
                                    {req.priority === 'recruitment' && (
                                      <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-blue-100 text-blue-700 font-medium flex items-center gap-1">
                                        <span className="w-1.5 h-1.5 rounded-full bg-blue-500"></span>
                                        Recruitment
                                      </span>
                                    )}
                                    
                                    {/* HIGH RISK BADGE - DBS and RTW items get special visibility */}
                                    {(req.id === 'dbs_certificate' || req.id === 'dbs_check' || req.id === 'dbs_update_service') && (
                                      <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-semibold flex items-center gap-1 ${
                                        !hasEvidence ? 'bg-red-600 text-white' :
                                        isVerified ? 'bg-green-600 text-white' : 'bg-amber-500 text-white'
                                      }`}>
                                        <Shield className="h-2.5 w-2.5" />
                                        DBS
                                      </span>
                                    )}
                                    {(req.id === 'right_to_work_documents' || req.id === 'right_to_work_check') && (
                                      <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-semibold flex items-center gap-1 ${
                                        !hasEvidence ? 'bg-red-600 text-white' :
                                        isVerified ? 'bg-green-600 text-white' : 'bg-amber-500 text-white'
                                      }`}>
                                        <FileCheck className="h-2.5 w-2.5" />
                                        RTW
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
                                  {(req.priority === 'start_required' || req.is_mandatory_for_work) && !isVerified && (
                                    <p className="text-[10px] text-red-600 font-medium mt-0.5">
                                      Required before employee can start work
                                    </p>
                                  )}
                                  
                                  {/* MICROCOPY HELPER TEXT - Shows guidance for each requirement */}
                                  {helpText && !hasEvidence && !(req.priority === 'start_required' || req.is_mandatory_for_work) && (
                                    <p className="text-xs text-text-muted mt-0.5">{helpText}</p>
                                  )}
                                  
                                  {/* CONDITIONAL REQUIREMENT NOTICE - For items like HMRC that depend on other documents */}
                                  {req.id === 'hmrc_starter_checklist' && !hasEvidence && (
                                    <p className="text-[10px] text-purple-600 font-medium mt-0.5 flex items-center gap-1">
                                      <span className="w-1.5 h-1.5 rounded-full bg-purple-500"></span>
                                      Required because no P45 is on file
                                    </p>
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
                                          <span className="truncate max-w-[180px]">
                                            {file.file_label || file.original_filename || 'Document'}
                                          </span>
                                          {file.verified && <Shield className="h-3 w-3 text-success flex-shrink-0" />}
                                          {/* Expiry Status Badge */}
                                          {file.expiry_status && (
                                            <span className={`text-[9px] px-1 py-0.5 rounded flex-shrink-0 ${
                                              file.expiry_status.status === 'expired' 
                                                ? 'bg-red-100 text-red-700' 
                                                : file.expiry_status.status === 'expiring_soon'
                                                ? 'bg-amber-100 text-amber-700'
                                                : 'bg-green-100 text-green-700'
                                            }`} title={file.expiry_status.label}>
                                              {file.expiry_status.status === 'expired' ? 'Expired' : 
                                               file.expiry_status.status === 'expiring_soon' ? 'Expiring' : 
                                               'Valid'}
                                            </span>
                                          )}
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
                                  
                                  {/* ACKNOWLEDGEMENT STATUS INFO */}
                                  {req.type === 'acknowledgement' && req.acknowledged && (
                                    <div className="flex flex-wrap items-center gap-2 mt-2 pt-1.5 border-t border-[#E4E8EB]/50">
                                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-green-50 text-green-700 flex items-center gap-1">
                                        <CheckCircle className="h-2.5 w-2.5" />
                                        Acknowledged{req.acknowledged_by ? ` by ${req.acknowledged_by}` : ''}
                                      </span>
                                      {req.acknowledged_at && (
                                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-50 text-blue-700 flex items-center gap-1">
                                          <Calendar className="h-2.5 w-2.5" />
                                          {new Date(req.acknowledged_at).toLocaleDateString()}
                                        </span>
                                      )}
                                    </div>
                                  )}
                                  
                                  {/* OPTIONAL ITEM INDICATOR */}
                                  {req.optional && (
                                    <p className="text-xs text-text-muted flex items-center gap-1 mt-1">
                                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-100 text-gray-600">Optional</span>
                                      Does not affect compliance score
                                    </p>
                                  )}
                                  
                                  {/* TRAINING STATUS INFO - Shows completion/verification status from training record */}
                                  {req.type === 'training' && req.training && (
                                    <div className="flex flex-wrap items-center gap-2 mt-2 pt-1.5 border-t border-[#E4E8EB]/50">
                                      {/* Completion Date */}
                                      {req.training.completed_at && (
                                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-50 text-blue-700 flex items-center gap-1">
                                          <Calendar className="h-2.5 w-2.5" />
                                          Completed: {new Date(req.training.completed_at).toLocaleDateString()}
                                        </span>
                                      )}
                                      {/* Expiry Date */}
                                      {req.training.expiry_date && (
                                        <span className={`text-[10px] px-1.5 py-0.5 rounded flex items-center gap-1 ${
                                          new Date(req.training.expiry_date) < new Date() 
                                            ? 'bg-red-50 text-red-700' 
                                            : 'bg-green-50 text-green-700'
                                        }`}>
                                          <Clock className="h-2.5 w-2.5" />
                                          Expires: {new Date(req.training.expiry_date).toLocaleDateString()}
                                        </span>
                                      )}
                                      {/* Verification Status */}
                                      {req.training.verified && (
                                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-green-50 text-green-700 flex items-center gap-1">
                                          <Shield className="h-2.5 w-2.5" />
                                          Verified{req.training.verified_by ? ` by ${req.training.verified_by}` : ''}
                                        </span>
                                      )}
                                      {/* No Evidence Warning */}
                                      {!req.training.has_evidence && req.training.status === 'completed' && (
                                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-50 text-amber-700 flex items-center gap-1">
                                          <AlertTriangle className="h-2.5 w-2.5" />
                                          No certificate uploaded
                                        </span>
                                      )}
                                    </div>
                                  )}
                                </div>
                              </div>
                              
                              {/* Actions - Clean Linear: Upload/Add → View → Download → Verify */}
                              <div className="flex items-center gap-2 flex-wrap justify-end">
                                {/* Expiry Status Badge - shown when requirement tracks expiry */}
                                {req.tracks_expiry && req.expiry_status && (
                                  <span className={`px-2 py-1 rounded-lg text-xs font-medium ${
                                    req.expiry_status.status === 'expired' 
                                      ? 'bg-red-100 text-red-700' 
                                      : req.expiry_status.status === 'expiring_soon'
                                      ? 'bg-amber-100 text-amber-700'
                                      : 'bg-green-100 text-green-700'
                                  }`} title={req.expiry_status.label}>
                                    <Clock className="h-3 w-3 inline mr-1" />
                                    {req.expiry_status.status === 'expired' 
                                      ? `Expired ${req.expiry_status.expiry_date}` 
                                      : req.expiry_status.status === 'expiring_soon'
                                      ? `Expires ${req.expiry_status.expiry_date}`
                                      : `Valid until ${req.expiry_status.expiry_date}`}
                                  </span>
                                )}
                                
                                {/* Status badge */}
                                <span className={`px-2 py-1 rounded-lg text-xs font-medium ${statusBadge.style}`}>
                                  {statusBadge.text}
                                </span>
                                
                                {/* ACTION 1: Upload / Add File / Acknowledge */}
                                {!isAuditor() && (
                                  <>
                                    {/* ACKNOWLEDGEMENT TYPE - Confirm & Complete */}
                                    {req.type === 'acknowledgement' && !req.acknowledged && (
                                      <Button 
                                        size="sm" 
                                        variant="default"
                                        onClick={() => {
                                          setAcknowledgingRequirement(req);
                                          setAcknowledgementDialogOpen(true);
                                        }}
                                        className="text-xs h-7 bg-green-600 hover:bg-green-700 text-white rounded-lg"
                                        data-testid={`acknowledge-${req.id}`}
                                      >
                                        <CheckCircle className="h-3 w-3 mr-1" />
                                        Confirm & Complete
                                      </Button>
                                    )}
                                    {req.type === 'acknowledgement' && req.acknowledged && (
                                      <span className="text-xs text-green-600 flex items-center gap-1 px-2">
                                        <Shield className="h-3 w-3" />
                                        Acknowledged
                                      </span>
                                    )}
                                    
                                    {/* Generate PDF for forms without evidence */}
                                    {req.type !== 'acknowledgement' && req.type === 'form-generated' && req.form && req.form.status && 
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
                                    ) : req.type !== 'acknowledgement' && !hasEvidence && FORM_BASED_REQUIREMENTS.includes(req.id) ? (
                                      /* FORM-BASED REQUIREMENT: Show "Fill Form" button */
                                      <Button 
                                        size="sm" 
                                        variant="default"
                                        onClick={() => openFormModal(req.id)}
                                        className="text-xs h-7 bg-primary hover:bg-primary-hover text-white rounded-lg"
                                        data-testid={`fill-form-${req.id}`}
                                      >
                                        <ClipboardCheck className="h-3 w-3 mr-1" />
                                        Fill Form
                                      </Button>
                                    ) : req.type !== 'acknowledgement' && !hasEvidence ? (
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
                                    ) : req.type !== 'acknowledgement' && req.allow_multiple_files ? (
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
                                
                                {/* View/Edit Form Submission */}
                                {req.form_submission && (
                                  <>
                                    <Button
                                      size="sm"
                                      variant="outline"
                                      onClick={() => openViewForm(req)}
                                      className="text-xs h-7 rounded-lg"
                                      data-testid={`view-form-${req.id}`}
                                    >
                                      <Eye className="h-3 w-3 mr-1" />
                                      View Form
                                    </Button>
                                    <Button
                                      size="sm"
                                      variant="outline"
                                      onClick={() => openFormModal(req.id)}
                                      className="text-xs h-7 rounded-lg"
                                      data-testid={`edit-form-${req.id}`}
                                    >
                                      <Edit className="h-3 w-3 mr-1" />
                                      Edit
                                    </Button>
                                  </>
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
                                {/* For training requirements, use training-specific endpoint */}
                                {hasEvidence && !isVerified && !isAuditor() && (
                                  <Button 
                                    size="sm" 
                                    variant="outline"
                                    onClick={async () => {
                                      try {
                                        if (req.type === 'training' && req.training?.id) {
                                          // Use training-specific verify endpoint
                                          await handleVerifyTraining(req.training.id);
                                        } else {
                                          // Use standard requirement verify endpoint
                                          await axios.post(
                                            `${API}/employees/${employeeId}/requirements/${req.id}/verify`,
                                            {},
                                            { headers: { Authorization: `Bearer ${token}` } }
                                          );
                                          toast.success(`${req.name} marked as Checked & Approved`);
                                          await fetchData();
                                          await fetchCompliance();
                                        }
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
                                    <DropdownMenuContent align="end" className="w-56">
                                      {/* TRAINING-SPECIFIC ACTIONS - Uses unified training record system */}
                                      {req.type === 'training' && req.training?.id ? (
                                        <>
                                          {/* Verify Training */}
                                          {!isAuditor() && !req.training.verified && (
                                            <DropdownMenuItem 
                                              onClick={() => handleVerifyTraining(req.training.id)}
                                              data-testid={`verify-training-${req.id}`}
                                            >
                                              <Shield className="h-4 w-4 mr-2 text-green-600" />
                                              Verify Training
                                            </DropdownMenuItem>
                                          )}
                                          {!isAuditor() && req.training.verified && (
                                            <DropdownMenuItem 
                                              onClick={() => handleUnverifyTraining(req.training.id)}
                                              data-testid={`unverify-training-${req.id}`}
                                            >
                                              <Shield className="h-4 w-4 mr-2 text-red-600" />
                                              Remove Verification
                                            </DropdownMenuItem>
                                          )}
                                          
                                          {/* Edit Training Record - Opens correction dialog */}
                                          {!isAuditor() && (
                                            <DropdownMenuItem 
                                              onClick={() => openTrainingCorrectionFromWhatsNeeded(req)}
                                              data-testid={`edit-training-${req.id}`}
                                            >
                                              <Edit className="h-4 w-4 mr-2" />
                                              Edit Training Record
                                            </DropdownMenuItem>
                                          )}
                                          
                                          {/* Replace Certificate - upload new evidence */}
                                          {!isAuditor() && (
                                            <DropdownMenuItem 
                                              onClick={() => openTrainingCertDialog(req)}
                                              data-testid={`replace-training-cert-${req.id}`}
                                            >
                                              <RefreshCw className="h-4 w-4 mr-2" />
                                              Replace Certificate
                                            </DropdownMenuItem>
                                          )}
                                          
                                          <DropdownMenuSeparator />
                                          
                                          {/* View Training History */}
                                          <DropdownMenuItem 
                                            onClick={async () => {
                                              try {
                                                const res = await axios.get(`${API}/training-records/${req.training.id}/history`, {
                                                  headers: { Authorization: `Bearer ${token}` }
                                                });
                                                setTrainingHistory(res.data.history || []);
                                                setTrainingHistoryDialogOpen(true);
                                              } catch (error) {
                                                toast.error('Failed to load history');
                                              }
                                            }}
                                            data-testid={`training-history-${req.id}`}
                                          >
                                            <History className="h-4 w-4 mr-2" />
                                            View History
                                          </DropdownMenuItem>
                                          
                                          {/* Delete Training Record */}
                                          {!isAuditor() && (
                                            <DropdownMenuItem 
                                              onClick={() => openDeleteTrainingFromWhatsNeeded(req)}
                                              className="text-red-600"
                                              data-testid={`delete-training-${req.id}`}
                                            >
                                              <Trash2 className="h-4 w-4 mr-2" />
                                              Delete Training Record
                                            </DropdownMenuItem>
                                          )}
                                        </>
                                      ) : (
                                        <>
                                          {/* DOCUMENT ACTIONS - For non-training requirements */}
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
                                              Delete File
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
                                        </>
                                      )}
                                    </DropdownMenuContent>
                                  </DropdownMenu>
                                )}
                                
                                {/* TRAINING: Show action menu even without evidence files */}
                                {req.type === 'training' && req.training?.id && evidenceFiles.length === 0 && (
                                  <DropdownMenu>
                                    <DropdownMenuTrigger asChild>
                                      <Button 
                                        size="sm" 
                                        variant="ghost"
                                        className="text-xs h-7 px-2 rounded-lg"
                                        data-testid={`training-actions-${req.id}`}
                                      >
                                        <MoreHorizontal className="h-3 w-3" />
                                      </Button>
                                    </DropdownMenuTrigger>
                                    <DropdownMenuContent align="end" className="w-56">
                                      {/* Edit Training Record */}
                                      {!isAuditor() && (
                                        <DropdownMenuItem 
                                          onClick={() => openTrainingCorrectionFromWhatsNeeded(req)}
                                          data-testid={`edit-training-noevidence-${req.id}`}
                                        >
                                          <Edit className="h-4 w-4 mr-2" />
                                          Edit Training Record
                                        </DropdownMenuItem>
                                      )}
                                      
                                      {/* View Training History */}
                                      <DropdownMenuItem 
                                        onClick={async () => {
                                          try {
                                            const res = await axios.get(`${API}/training-records/${req.training.id}/history`, {
                                              headers: { Authorization: `Bearer ${token}` }
                                            });
                                            setTrainingHistory(res.data.history || []);
                                            setTrainingHistoryDialogOpen(true);
                                          } catch (error) {
                                            toast.error('Failed to load history');
                                          }
                                        }}
                                        data-testid={`training-history-noevidence-${req.id}`}
                                      >
                                        <History className="h-4 w-4 mr-2" />
                                        View History
                                      </DropdownMenuItem>
                                      
                                      {/* Delete Training Record */}
                                      {!isAuditor() && (
                                        <DropdownMenuItem 
                                          onClick={() => openDeleteTrainingFromWhatsNeeded(req)}
                                          className="text-red-600"
                                          data-testid={`delete-training-noevidence-${req.id}`}
                                        >
                                          <Trash2 className="h-4 w-4 mr-2" />
                                          Delete Training Record
                                        </DropdownMenuItem>
                                      )}
                                    </DropdownMenuContent>
                                  </DropdownMenu>
                                )}
                                
                                {/* Unverify option - Use training endpoint for training requirements */}
                                {isVerified && !isAuditor() && !(req.type === 'training' && req.training?.id) && (
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
                                        await fetchData();
                                        await fetchCompliance();
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
                                {/* Training unverify - handled via dropdown for consistency */}
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
                <CardTitle className="font-heading text-lg">Documents</CardTitle>
                <p className="text-xs text-text-muted mt-1">
                  Upload and verify documents. Only verified documents count towards compliance.
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
                              {docs.map((doc, idx) => {
                                // File error state is tracked via failed requests
                                const isFileBroken = doc.file_error === true;
                                
                                return (
                                <div 
                                  key={doc.file_id || idx} 
                                  className={`flex items-center justify-between p-3 rounded-lg border ${
                                    isFileBroken ? 'border-red-200 bg-red-50' :
                                    doc.expiry_status?.status === 'expired' ? 'border-red-300 bg-red-50' :
                                    doc.expiry_status?.status === 'expiring_soon' ? 'border-amber-300 bg-amber-50' :
                                    doc.verified ? 'border-success/30 bg-success/5' : 'border-[#E4E8EB] bg-white'
                                  }`}
                                  data-testid={`file-row-${doc.file_id}`}
                                >
                                  <div className="flex items-center gap-3 flex-1 min-w-0">
                                    <FileText className={`h-5 w-5 flex-shrink-0 ${
                                      isFileBroken ? 'text-red-400' : 
                                      doc.expiry_status?.status === 'expired' ? 'text-red-500' :
                                      doc.expiry_status?.status === 'expiring_soon' ? 'text-amber-500' :
                                      'text-text-muted'
                                    }`} />
                                    <div className="min-w-0 flex-1">
                                      <div className="flex items-center gap-2 flex-wrap">
                                        <p className={`text-sm font-medium truncate ${isFileBroken ? 'text-red-600' : 'text-text-primary'}`}>
                                          {isFileBroken ? 'File unavailable' : (doc.file_label || doc.original_filename || 'Document')}
                                        </p>
                                        {/* DBS/RTW highlight */}
                                        {(req.id === 'dbs_certificate' || req.id === 'dbs_check') && (
                                          <span className="text-[9px] px-1.5 py-0.5 rounded bg-purple-100 text-purple-700 font-semibold">DBS</span>
                                        )}
                                        {(req.id === 'right_to_work_documents' || req.id === 'right_to_work_check') && (
                                          <span className="text-[9px] px-1.5 py-0.5 rounded bg-purple-100 text-purple-700 font-semibold">RTW</span>
                                        )}
                                        {/* Expiry Status Badge - Prominent */}
                                        {doc.expiry_status && (
                                          <span className={`text-[9px] px-1.5 py-0.5 rounded font-medium ${
                                            doc.expiry_status.status === 'expired' 
                                              ? 'bg-red-600 text-white' 
                                              : doc.expiry_status.status === 'expiring_soon'
                                              ? 'bg-amber-500 text-white'
                                              : 'bg-green-600 text-white'
                                          }`}>
                                            {doc.expiry_status.label}
                                          </span>
                                        )}
                                        {/* Verified badge */}
                                        {doc.verified && !isFileBroken && (
                                          <span className="text-[9px] px-1.5 py-0.5 rounded bg-green-100 text-green-700 font-medium flex items-center gap-0.5">
                                            <Shield className="h-2.5 w-2.5" />
                                            Verified
                                          </span>
                                        )}
                                      </div>
                                      <div className="flex items-center gap-2 text-xs text-text-muted mt-0.5">
                                        {!isFileBroken && doc.source_type && (
                                          <span>
                                            {doc.source_type === 'form_submission' ? 'From Form' : 
                                             doc.source_type === 'imported' ? 'Imported' : 
                                             doc.source_type === 'replacement' ? 'Replaced' : 'Manual'}
                                          </span>
                                        )}
                                        {doc.uploaded_at && (
                                          <span>Uploaded: {new Date(doc.uploaded_at).toLocaleDateString()}</span>
                                        )}
                                        {/* Expiry Date - show actual date */}
                                        {doc.expiry_date && (
                                          <span className={doc.expiry_status?.status === 'expired' ? 'text-red-600 font-medium' : ''}>
                                            Expires: {new Date(doc.expiry_date).toLocaleDateString()}
                                          </span>
                                        )}
                                        {isFileBroken && (
                                          <span className="text-red-500">Cannot access file</span>
                                        )}
                                      </div>
                                    </div>
                                  </div>
                                  
                                  {/* File Actions: View, Download, Replace, Delete */}
                                  <div className="flex items-center gap-1">
                                    {/* View - disabled if file is broken */}
                                    <Button 
                                      size="sm" 
                                      variant="ghost"
                                      className="h-8 w-8 p-0 rounded-lg"
                                      disabled={isFileBroken}
                                      onClick={async () => {
                                        try {
                                          const viewUrl = `${API}/employees/${employeeId}/requirements/${req.id}/evidence/${doc.file_id}/view`;
                                          setPreviewFile({
                                            url: viewUrl,
                                            name: doc.file_label || doc.original_filename || 'Document',
                                            filename: doc.original_filename
                                          });
                                          setPreviewFiles([]);
                                          setPreviewOpen(true);
                                        } catch (e) {
                                          toast.error('File unavailable');
                                        }
                                      }}
                                      title={isFileBroken ? 'File unavailable' : 'View'}
                                      data-testid={`view-file-${doc.file_id}`}
                                    >
                                      <Eye className={`h-4 w-4 ${isFileBroken ? 'text-gray-300' : ''}`} />
                                    </Button>
                                    
                                    {/* Download - disabled if file is broken */}
                                    <Button 
                                      size="sm" 
                                      variant="ghost"
                                      className="h-8 w-8 p-0 rounded-lg"
                                      disabled={isFileBroken}
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
                                          toast.error('File unavailable');
                                        }
                                      }}
                                      title={isFileBroken ? 'File unavailable' : 'Download'}
                                      data-testid={`download-file-${doc.file_id}`}
                                    >
                                      <Download className={`h-4 w-4 ${isFileBroken ? 'text-gray-300' : ''}`} />
                                    </Button>
                                    
                                    {/* Replace - always available (works for broken files too) */}
                                    {!isAuditor() && (
                                      <Button 
                                        size="sm" 
                                        variant="ghost"
                                        className="h-8 w-8 p-0 rounded-lg text-blue-600 hover:bg-blue-50"
                                        onClick={() => openReplaceDialog(doc, req.id)}
                                        title="Replace"
                                        data-testid={`replace-file-${doc.file_id}`}
                                      >
                                        <RefreshCw className="h-4 w-4" />
                                      </Button>
                                    )}
                                    
                                    {/* Delete - always available (works for broken files too) */}
                                    {!isAuditor() && (
                                      <Button 
                                        size="sm" 
                                        variant="ghost"
                                        className="h-8 w-8 p-0 rounded-lg text-red-600 hover:bg-red-50"
                                        onClick={() => openRemoveDialog(doc, req.id)}
                                        title="Delete"
                                        data-testid={`delete-file-${doc.file_id}`}
                                      >
                                        <Trash2 className="h-4 w-4" />
                                      </Button>
                                    )}
                                    
                                    {/* Verify - only for non-broken files */}
                                    {!isAuditor() && !doc.verified && !isFileBroken && (
                                      <Button 
                                        size="sm" 
                                        variant="ghost"
                                        className="h-8 w-8 p-0 rounded-lg text-success hover:bg-success/10"
                                        onClick={() => handleVerifyRequirement(req.id)}
                                        title="Approve"
                                        data-testid={`verify-file-${doc.file_id}`}
                                      >
                                        <Shield className="h-4 w-4" />
                                      </Button>
                                    )}
                                  </div>
                                </div>
                                );
                              })}
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
              {/* Header with stats */}
              <div className="flex items-center justify-between mb-6 pb-4 border-b border-[#E4E8EB]">
                <div>
                  <h3 className="font-heading text-lg font-semibold text-text-primary">Assigned Policies</h3>
                  <p className="text-sm text-text-muted">
                    {policies.filter(p => p.status === 'acknowledged' || p.status === 'signed').length} of {policies.length} acknowledged
                  </p>
                  <p className="text-xs text-text-muted mt-1">
                    Employees must read and acknowledge assigned policies.
                  </p>
                </div>
                {policies.length > 0 && (
                  <div className="flex items-center gap-2 text-sm">
                    <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-gray-100 text-gray-600">
                      <Clock className="w-3 h-3" /> {policies.filter(p => p.status === 'assigned' || p.status === 'viewed').length} Not Read
                    </span>
                    <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-green-100 text-green-700">
                      <CheckCircle className="w-3 h-3" /> {policies.filter(p => p.status === 'acknowledged' || p.status === 'signed').length} Acknowledged
                    </span>
                  </div>
                )}
              </div>

              {policies.length === 0 ? (
                <div className="text-center py-12 text-text-muted">
                  <FileCheck className="h-12 w-12 mx-auto mb-3 opacity-50" />
                  <p>No policies assigned yet</p>
                  <p className="text-sm mt-1">Policies can be assigned from the Compliance Centre</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {policies.map((policy) => (
                    <div key={policy.id} className={`p-4 rounded-xl border ${
                      policy.admin_reviewed ? 'bg-green-50 border-green-200' :
                      (policy.status === 'acknowledged' || policy.status === 'signed') ? 'bg-blue-50 border-blue-200' :
                      policy.status === 'viewed' ? 'bg-amber-50 border-amber-200' :
                      'bg-[#F8FAFA] border-[#E4E8EB]'
                    }`}>
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <p className="font-semibold text-text-primary">{policy.policy_title}</p>
                            <span className="text-xs px-2 py-0.5 bg-gray-200 rounded text-gray-600">
                              v{policy.policy_version || '1.0'}
                            </span>
                          </div>
                          <p className="text-sm text-text-muted mt-1">
                            Assigned: {new Date(policy.assigned_at).toLocaleDateString()} 
                            {policy.assigned_by_name && ` by ${policy.assigned_by_name}`}
                          </p>
                          
                          {/* Signature Information Display */}
                          {(policy.status === 'acknowledged' || policy.status === 'signed') && (
                            <div className="mt-3 p-3 bg-white/80 rounded-lg border border-green-200">
                              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Employee Acknowledgement</p>
                              <p className="text-sm font-medium text-green-800">
                                {policy.acknowledged_by_employee_name || policy.employee_name || 'Employee'}
                              </p>
                              <p className="text-xs text-green-600">
                                {policy.acknowledged_at ? new Date(policy.acknowledged_at).toLocaleString() : 
                                 policy.signed_at ? new Date(policy.signed_at).toLocaleString() : ''}
                              </p>
                            </div>
                          )}
                          
                          {policy.admin_reviewed && (
                            <div className="mt-2 p-3 bg-white/80 rounded-lg border border-green-200">
                              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Admin Review</p>
                              <p className="text-sm font-medium text-green-800">
                                {policy.admin_reviewed_by_name || 'Admin'}
                              </p>
                              <p className="text-xs text-green-600">
                                {policy.admin_reviewed_at ? new Date(policy.admin_reviewed_at).toLocaleString() : ''}
                              </p>
                            </div>
                          )}
                        </div>
                        
                        <div className="flex flex-col items-end gap-2">
                          {/* Status Badge */}
                          <span className={`status-chip ${
                            policy.admin_reviewed ? 'status-success' :
                            (policy.status === 'acknowledged' || policy.status === 'signed') ? 'bg-green-100 text-green-700 border-green-200' :
                            'bg-gray-100 text-gray-600 border-gray-200'
                          }`}>
                            {policy.admin_reviewed ? 'Reviewed & Approved' :
                             (policy.status === 'acknowledged' || policy.status === 'signed') ? 'Acknowledged' :
                             'Not Read'}
                          </span>
                          
                          {/* Action Buttons */}
                          <div className="flex items-center gap-2 flex-wrap justify-end">
                            {/* View Policy Button */}
                            <Button
                              size="sm"
                              variant="outline"
                              className="rounded-lg text-xs"
                              onClick={async () => {
                                try {
                                  // Mark as viewed if not already
                                  if (policy.status === 'assigned') {
                                    await axios.put(`${API}/policy-assignments/${policy.id}/view`, {}, {
                                      headers: { Authorization: `Bearer ${token}` }
                                    });
                                  }
                                  // Open policy file
                                  const response = await axios.get(`${API}/policies/${policy.policy_id}/file`, {
                                    headers: { Authorization: `Bearer ${token}` },
                                    responseType: 'blob'
                                  });
                                  const url = window.URL.createObjectURL(response.data);
                                  window.open(url, '_blank');
                                  await fetchData();
                                } catch (error) {
                                  if (error.response?.status === 404) {
                                    toast.error('Policy document not found');
                                  } else {
                                    toast.error('Failed to open policy');
                                  }
                                }
                              }}
                              data-testid={`view-policy-${policy.id}`}
                            >
                              <Eye className="w-3 h-3 mr-1" />
                              View Policy
                            </Button>
                            
                            {/* Acknowledge Button - only if not yet acknowledged */}
                            {policy.status !== 'acknowledged' && policy.status !== 'signed' && !isAuditor() && (
                              <Button
                                size="sm"
                                className="rounded-lg text-xs bg-primary hover:bg-primary-hover text-white"
                                onClick={async () => {
                                  try {
                                    await axios.put(`${API}/policy-assignments/${policy.id}/acknowledge`, {}, {
                                      headers: { Authorization: `Bearer ${token}` }
                                    });
                                    toast.success('Policy acknowledged successfully');
                                    await fetchData();
                                  } catch (error) {
                                    toast.error(error.response?.data?.detail || 'Failed to acknowledge policy');
                                  }
                                }}
                                data-testid={`acknowledge-policy-${policy.id}`}
                              >
                                <CheckCircle className="w-3 h-3 mr-1" />
                                Mark as Read & Understood
                              </Button>
                            )}
                            
                            {/* Admin Review Button - only if acknowledged but not reviewed */}
                            {(policy.status === 'acknowledged' || policy.status === 'signed') && !policy.admin_reviewed && isAdmin() && (
                              <Button
                                size="sm"
                                variant="outline"
                                className="rounded-lg text-xs border-green-300 text-green-700 hover:bg-green-50"
                                onClick={async () => {
                                  try {
                                    await axios.put(`${API}/policy-assignments/${policy.id}/admin-review`, {}, {
                                      headers: { Authorization: `Bearer ${token}` }
                                    });
                                    toast.success('Policy reviewed and approved');
                                    await fetchData();
                                  } catch (error) {
                                    toast.error(error.response?.data?.detail || 'Failed to review policy');
                                  }
                                }}
                                data-testid={`admin-review-policy-${policy.id}`}
                              >
                                <Shield className="w-3 h-3 mr-1" />
                                Reviewed and Approved
                              </Button>
                            )}
                            
                            {/* Unassign Button - only for unacknowledged policies (admin/manager only) */}
                            {policy.status !== 'acknowledged' && policy.status !== 'signed' && 
                             policy.status !== 'unassigned' && policy.status !== 'withdrawn' && 
                             isAdmin() && (
                              <Button
                                size="sm"
                                variant="outline"
                                className="rounded-lg text-xs border-amber-300 text-amber-700 hover:bg-amber-50"
                                onClick={async () => {
                                  if (!window.confirm('Remove this policy from the employee\'s active policy list?')) return;
                                  try {
                                    await axios.put(`${API}/policy-assignments/${policy.id}/unassign`, {}, {
                                      headers: { Authorization: `Bearer ${token}` }
                                    });
                                    toast.success('Policy unassigned');
                                    await fetchData();
                                  } catch (error) {
                                    toast.error(error.response?.data?.detail || 'Failed to unassign policy');
                                  }
                                }}
                                data-testid={`unassign-policy-${policy.id}`}
                              >
                                <XCircle className="w-3 h-3 mr-1" />
                                Unassign
                              </Button>
                            )}
                            
                            {/* Withdraw Button - only for acknowledged policies (admin only) */}
                            {(policy.status === 'acknowledged' || policy.status === 'signed') && 
                             policy.status !== 'withdrawn' && isAdmin() && (
                              <Button
                                size="sm"
                                variant="outline"
                                className="rounded-lg text-xs border-red-300 text-red-700 hover:bg-red-50"
                                onClick={async () => {
                                  if (!window.confirm('Withdraw this policy? The acknowledgement history will be preserved for audit purposes.')) return;
                                  try {
                                    await axios.put(`${API}/policy-assignments/${policy.id}/withdraw`, {}, {
                                      headers: { Authorization: `Bearer ${token}` }
                                    });
                                    toast.success('Policy assignment withdrawn');
                                    await fetchData();
                                  } catch (error) {
                                    toast.error(error.response?.data?.detail || 'Failed to withdraw policy');
                                  }
                                }}
                                data-testid={`withdraw-policy-${policy.id}`}
                              >
                                <RotateCcw className="w-3 h-3 mr-1" />
                                Withdraw
                              </Button>
                            )}
                          </div>
                        </div>
                      </div>
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
              <div className="mb-4 pb-4 border-b border-[#E4E8EB]">
                <h3 className="font-heading text-lg font-semibold text-text-primary">Training & Certifications</h3>
                <p className="text-sm text-text-muted">Track completion status, expiry dates, and renewal status. Verified training counts toward work readiness.</p>
              </div>
              {training.length === 0 ? (
                <div className="text-center py-12 text-text-muted">
                  <GraduationCap className="h-12 w-12 mx-auto mb-3 opacity-50" />
                  <p>No training records yet</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {training.map((record) => {
                    // Calculate expiry status
                    let expiryStatus = null;
                    if (record.expiry_date) {
                      const now = new Date();
                      const expiry = new Date(record.expiry_date);
                      const daysUntilExpiry = Math.ceil((expiry - now) / (1000 * 60 * 60 * 24));
                      
                      if (daysUntilExpiry < 0) {
                        expiryStatus = { status: 'expired', label: 'Expired', color: 'red', days: Math.abs(daysUntilExpiry) };
                      } else if (daysUntilExpiry <= 30) {
                        expiryStatus = { status: 'expiring_soon', label: 'Needs Renewal', color: 'amber', days: daysUntilExpiry };
                      } else {
                        expiryStatus = { status: 'valid', label: 'Valid', color: 'green', days: daysUntilExpiry };
                      }
                    }
                    
                    const hasEvidence = record.certificate_url || (record.evidence_files && record.evidence_files.length > 0);
                    
                    return (
                      <div key={record.id} className="p-4 bg-[#F8FAFA] rounded-xl border border-[#E4E8EB]" data-testid={`training-record-${record.id}`}>
                        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                          <div className="flex-1">
                            <div className="flex items-center gap-2">
                              <p className="font-medium text-text-primary">{record.training_name}</p>
                              {record.mandatory && (
                                <span className="text-xs px-2 py-0.5 bg-red-100 text-red-600 rounded">Mandatory</span>
                              )}
                              {record.verified && (
                                <span className="text-xs px-2 py-0.5 bg-green-100 text-green-600 rounded flex items-center gap-1">
                                  <Shield className="h-3 w-3" />Verified
                                </span>
                              )}
                            </div>
                            <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-text-muted mt-1">
                              {record.completion_date && (
                                <span>Completed: {new Date(record.completion_date).toLocaleDateString()}</span>
                              )}
                              {record.expiry_date && (
                                <span>Expires: {new Date(record.expiry_date).toLocaleDateString()}</span>
                              )}
                            </div>
                          </div>
                          
                          {/* Status and Renewal Status */}
                          <div className="flex items-center gap-3">
                            {/* Renewal Status Badge */}
                            {expiryStatus && (
                              <div className={`text-center px-3 py-1 rounded-lg ${
                                expiryStatus.color === 'red' ? 'bg-red-100' :
                                expiryStatus.color === 'amber' ? 'bg-amber-100' : 'bg-green-100'
                              }`}>
                                <p className={`text-xs font-medium ${
                                  expiryStatus.color === 'red' ? 'text-red-700' :
                                  expiryStatus.color === 'amber' ? 'text-amber-700' : 'text-green-700'
                                }`}>{expiryStatus.label}</p>
                                <p className={`text-xs ${
                                  expiryStatus.color === 'red' ? 'text-red-600' :
                                  expiryStatus.color === 'amber' ? 'text-amber-600' : 'text-green-600'
                                }`}>
                                  {expiryStatus.status === 'expired' ? `${expiryStatus.days}d ago` : `${expiryStatus.days}d left`}
                                </p>
                              </div>
                            )}
                            
                            {/* Status Badge */}
                            <span className={`px-3 py-1 rounded-lg text-sm font-medium ${
                              record.status === 'completed' ? 'bg-green-100 text-green-700' :
                              record.status === 'in_progress' ? 'bg-blue-100 text-blue-700' :
                              record.status === 'expired' ? 'bg-red-100 text-red-700' :
                              record.status === 'expiring' ? 'bg-amber-100 text-amber-700' :
                              'bg-gray-100 text-gray-700'
                            }`}>
                              {record.status?.replace('_', ' ')}
                            </span>
                          </div>
                          
                          {/* Actions */}
                          <div className="flex items-center gap-1">
                            {/* View Evidence */}
                            {hasEvidence && (
                              <Button 
                                size="sm" 
                                variant="ghost"
                                className="h-8 w-8 p-0 rounded-lg"
                                onClick={() => handleViewTrainingCertificate(record.id, record.certificate_filename)}
                                title="View Evidence"
                              >
                                <Eye className="h-4 w-4" />
                              </Button>
                            )}
                            
                            {/* Download */}
                            {hasEvidence && (
                              <Button 
                                size="sm" 
                                variant="ghost"
                                className="h-8 w-8 p-0 rounded-lg"
                                onClick={() => handleDownloadTrainingCertificate(record.id, record.certificate_filename)}
                                title="Download"
                              >
                                <Download className="h-4 w-4" />
                              </Button>
                            )}
                            
                            {/* Edit/Correct - shown via dropdown for admins */}
                            {!isAuditor() && (
                              <DropdownMenu>
                                <DropdownMenuTrigger asChild>
                                  <Button size="sm" variant="ghost" className="h-8 w-8 p-0 rounded-lg">
                                    <MoreVertical className="h-4 w-4" />
                                  </Button>
                                </DropdownMenuTrigger>
                                <DropdownMenuContent align="end">
                                  {!record.verified && (
                                    <DropdownMenuItem onClick={() => handleVerifyTraining(record.id)}>
                                      <Shield className="h-4 w-4 mr-2 text-green-600" />
                                      Verify
                                    </DropdownMenuItem>
                                  )}
                                  {record.verified && (
                                    <DropdownMenuItem onClick={() => handleUnverifyTraining(record.id)}>
                                      <Shield className="h-4 w-4 mr-2 text-red-600" />
                                      Remove Verification
                                    </DropdownMenuItem>
                                  )}
                                  <DropdownMenuItem onClick={() => {
                                    setEditingTrainingRecord(record);
                                    setTrainingCorrectionField('expiry_date');
                                    setTrainingCorrectionValue(record.expiry_date?.split('T')[0] || '');
                                    setTrainingCorrectionReason('');
                                    setTrainingCorrectionDialogOpen(true);
                                  }}>
                                    <Edit className="h-4 w-4 mr-2" />
                                    Edit / Correct
                                  </DropdownMenuItem>
                                  <DropdownMenuItem onClick={async () => {
                                    try {
                                      const res = await axios.get(`${API}/training-records/${record.id}/history`, {
                                        headers: { Authorization: `Bearer ${token}` }
                                      });
                                      setTrainingHistory(res.data.history || []);
                                      setTrainingHistoryDialogOpen(true);
                                    } catch (error) {
                                      toast.error('Failed to load history');
                                    }
                                  }}>
                                    <History className="h-4 w-4 mr-2" />
                                    View History
                                  </DropdownMenuItem>
                                  <DropdownMenuItem 
                                    className="text-red-600"
                                    onClick={() => {
                                      setDeletingTrainingRecord(record);
                                      setDeleteTrainingDialogOpen(true);
                                    }}
                                  >
                                    <Trash2 className="h-4 w-4 mr-2" />
                                    Delete Record
                                  </DropdownMenuItem>
                                </DropdownMenuContent>
                              </DropdownMenu>
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
        </TabsContent>

        {/* Audit Log Tab */}
        <TabsContent value="audit">
          <Card className="border-[#E4E8EB] shadow-sm">
            <CardContent className="p-6">
              <div className="mb-4 pb-4 border-b border-[#E4E8EB]">
                <h3 className="font-heading text-lg font-semibold text-text-primary">Compliance Audit Trail</h3>
                <p className="text-sm text-text-muted">Shows document uploads, verifications, policy acknowledgements, and status changes</p>
              </div>
              {auditLogs.length === 0 ? (
                <div className="text-center py-12 text-text-muted">
                  <History className="h-12 w-12 mx-auto mb-3 opacity-50" />
                  <p>No compliance activity recorded yet</p>
                </div>
              ) : (
                <div className="space-y-6">
                  {/* Group audit logs by category */}
                  {(() => {
                    // Categorize logs
                    const categorizeLog = (action) => {
                      if (action?.includes('policy')) return 'policies';
                      if (action?.includes('training') || action?.includes('certificate')) return 'training';
                      if (action?.includes('document') || action?.includes('evidence') || action?.includes('verify') || action?.includes('upload') || action?.includes('file_deleted')) return 'documents';
                      return 'profile';
                    };
                    
                    const grouped = {
                      documents: auditLogs.filter(l => categorizeLog(l.action) === 'documents'),
                      training: auditLogs.filter(l => categorizeLog(l.action) === 'training'),
                      policies: auditLogs.filter(l => categorizeLog(l.action) === 'policies'),
                      profile: auditLogs.filter(l => categorizeLog(l.action) === 'profile')
                    };
                    
                    const categoryConfig = {
                      documents: { label: 'Documents', icon: <Upload className="h-5 w-5" />, color: 'text-primary', bgColor: 'bg-primary/10' },
                      training: { label: 'Training', icon: <GraduationCap className="h-5 w-5" />, color: 'text-blue-600', bgColor: 'bg-blue-100' },
                      policies: { label: 'Policies', icon: <FileCheck className="h-5 w-5" />, color: 'text-purple-600', bgColor: 'bg-purple-100' },
                      profile: { label: 'Profile Changes', icon: <User className="h-5 w-5" />, color: 'text-gray-600', bgColor: 'bg-gray-100' }
                    };
                    
                    // Format action for display
                    const formatAction = (action) => {
                      const actionMap = {
                        'policy_assigned': 'Policy Assigned',
                        'policy_viewed': 'Policy Viewed',
                        'policy_acknowledged': 'Policy Acknowledged',
                        'policy_admin_reviewed': 'Policy Reviewed by Admin',
                        'policy_unassigned': 'Policy Unassigned',
                        'policy_withdrawn': 'Policy Withdrawn',
                        'document_verified': 'Document Verified',
                        'verify_requirement': 'Requirement Verified',
                        'unverify_requirement': 'Verification Removed',
                        'upload_evidence': 'Evidence Uploaded',
                        'document_uploaded': 'Document Uploaded',
                        'document_replaced': 'Document Replaced',
                        'document_removed': 'Document Removed',
                        'file_deleted': 'File Deleted',
                        'delete_evidence': 'Evidence Deleted',
                        'status_change': 'Status Changed',
                        'refresh_status': 'Status Refreshed',
                        'update_employee': 'Employee Updated',
                        'signoff_form': 'Form Signed Off',
                        'complete_form': 'Form Completed',
                        'training_correction': 'Training Record Corrected',
                        'upload_training_certificate': 'Training Certificate Uploaded',
                        'verify_training': 'Training Verified',
                        'unverify_training': 'Training Verification Removed',
                        'complete_training': 'Training Completed'
                      };
                      return actionMap[action] || action?.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                    };
                    
                    return Object.entries(grouped)
                      .filter(([_, logs]) => logs.length > 0)
                      .map(([category, logs]) => {
                        const config = categoryConfig[category];
                        return (
                          <div key={category} className="space-y-3">
                            <div className="flex items-center gap-2 pb-2 border-b border-[#E4E8EB]">
                              <div className={`p-1.5 rounded-lg ${config.bgColor} ${config.color}`}>
                                {config.icon}
                              </div>
                              <h4 className="font-medium text-text-primary">{config.label}</h4>
                              <span className="text-xs text-text-muted bg-[#F8FAFA] px-2 py-0.5 rounded-full">{logs.length}</span>
                            </div>
                            <div className="space-y-2 pl-4">
                              {logs.slice(0, 10).map((log, idx) => (
                                <div key={log.id || idx} className="flex items-start gap-3 p-3 bg-[#F8FAFA] rounded-lg text-sm">
                                  <div className="flex-1">
                                    <p className="font-medium text-text-primary">
                                      {formatAction(log.action)}
                                    </p>
                                    {log.metadata && (
                                      <div className="text-text-muted mt-0.5 text-xs space-y-0.5">
                                        {log.metadata.requirement_name && <p>• {log.metadata.requirement_name}</p>}
                                        {log.metadata.filename && <p>• File: {log.metadata.filename}</p>}
                                        {log.metadata.policy_title && <p>• {log.metadata.policy_title}</p>}
                                        {log.metadata.training_name && <p>• {log.metadata.training_name}</p>}
                                        {log.metadata.field_changed && (
                                          <p>• {log.metadata.field_changed}: {log.metadata.old_value || '(empty)'} → {log.metadata.new_value}</p>
                                        )}
                                        {log.metadata.deleted_by && <p>• Deleted by: {log.metadata.deleted_by}</p>}
                                        {log.metadata.reason && <p className="italic">Reason: {log.metadata.reason}</p>}
                                      </div>
                                    )}
                                    {/* Fallback to details if metadata not available */}
                                    {!log.metadata && log.details && (
                                      <div className="text-text-muted mt-0.5 text-xs">
                                        {log.details.requirement_name && <p>• {log.details.requirement_name}</p>}
                                        {log.details.policy_title && <p>• {log.details.policy_title}</p>}
                                      </div>
                                    )}
                                  </div>
                                  <div className="text-right text-xs text-text-muted flex-shrink-0">
                                    <p>{log.user_name || 'System'}</p>
                                    <p>{new Date(log.created_at).toLocaleString()}</p>
                                  </div>
                                </div>
                              ))}
                              {logs.length > 10 && (
                                <p className="text-xs text-text-muted text-center py-2">
                                  + {logs.length - 10} more entries
                                </p>
                              )}
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
                <FileUploaderInline
                  onFileSelect={(file) => setTrainingCertFile(file)}
                  selectedFile={trainingCertFile}
                  onClear={() => setTrainingCertFile(null)}
                  acceptedTypes={['application/pdf', 'image/jpeg', 'image/jpg', 'image/png', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']}
                  placeholder="Drop certificate here or click to browse"
                  data-testid="training-cert-file-input"
                />
                <p className="text-xs text-text-muted">
                  Accepted formats: PDF, JPG, PNG, DOC, DOCX (max 10MB)
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
            
            {/* DBS Update Service Check - Special labels and auto-calculation */}
            {editEvidenceData?.requirementId === 'dbs_check' ? (
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-2">
                  <Label>Last DBS Check Date</Label>
                  <Input
                    type="date"
                    value={editForm.issue_date}
                    onChange={(e) => {
                      const checkDate = e.target.value;
                      // Auto-calculate Next Review Due = Check Date + 12 months
                      let nextReviewDate = '';
                      if (checkDate) {
                        const date = new Date(checkDate);
                        date.setFullYear(date.getFullYear() + 1);
                        nextReviewDate = date.toISOString().split('T')[0];
                      }
                      setEditForm(prev => ({ 
                        ...prev, 
                        issue_date: checkDate,
                        expiry_date: nextReviewDate
                      }));
                    }}
                    className="rounded-xl"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Next DBS Review Due</Label>
                  <Input
                    type="date"
                    value={editForm.expiry_date}
                    onChange={(e) => setEditForm(prev => ({ ...prev, expiry_date: e.target.value }))}
                    className="rounded-xl bg-gray-50"
                    title="Auto-calculated as 12 months from Last DBS Check Date"
                  />
                  <p className="text-xs text-text-muted">Auto-calculated (+12 months)</p>
                </div>
              </div>
            ) : (
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
            )}
            
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

      {/* Delete File Dialog */}
      <Dialog open={removeDialogOpen} onOpenChange={setRemoveDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-red-600">
              <Trash2 className="h-5 w-5" />
              Delete File
            </DialogTitle>
            <DialogDescription>
              This will permanently remove the file from active use. The file will no longer count towards compliance. An audit record will be kept.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            {selectedFileForAction && (
              <div className="p-3 bg-red-50 rounded-lg border border-red-200">
                <p className="text-sm font-medium text-red-800">{selectedFileForAction.file_label || selectedFileForAction.original_filename || 'File'}</p>
                {selectedFileForAction.uploaded_at && (
                  <p className="text-xs text-red-600 mt-1">
                    Uploaded: {new Date(selectedFileForAction.uploaded_at).toLocaleDateString()}
                  </p>
                )}
              </div>
            )}
            <div className="space-y-2">
              <Label htmlFor="delete-reason">Reason for deletion (optional)</Label>
              <Textarea
                id="delete-reason"
                placeholder="Enter an optional reason for deleting this file"
                value={removeReason}
                onChange={(e) => setRemoveReason(e.target.value)}
                className="min-h-[80px] rounded-xl"
              />
              <p className="text-xs text-text-muted">This reason will be recorded in the audit trail if provided.</p>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRemoveDialogOpen(false)} className="rounded-xl">
              Cancel
            </Button>
            <Button 
              variant="destructive" 
              onClick={handleDeleteFile}
              disabled={isRemoving}
              className="rounded-xl"
              data-testid="confirm-delete-file"
            >
              {isRemoving ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Trash2 className="h-4 w-4 mr-2" />}
              Delete File
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
              <FileUploaderInline
                onFileSelect={(file) => setReplaceFile(file)}
                selectedFile={replaceFile}
                onClear={() => setReplaceFile(null)}
                acceptedTypes={['application/pdf', 'image/jpeg', 'image/jpg', 'image/png', 'image/webp']}
                placeholder="Drop replacement file here or click to browse"
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
      
      {/* Training Correction Dialog */}
      <Dialog open={trainingCorrectionDialogOpen} onOpenChange={setTrainingCorrectionDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="font-heading">Edit Training Record</DialogTitle>
            <DialogDescription>
              Make a correction to this training record. All changes require a reason and are logged for audit purposes.
            </DialogDescription>
          </DialogHeader>
          {editingTrainingRecord && (
            <div className="space-y-4 mt-4">
              <div className="p-3 bg-[#F8FAFA] rounded-lg border border-[#E4E8EB]">
                <p className="font-medium text-text-primary">{editingTrainingRecord.training_name}</p>
              </div>
              
              <div className="space-y-2">
                <Label>Field to Edit</Label>
                <Select value={trainingCorrectionField} onValueChange={(value) => {
                  setTrainingCorrectionField(value);
                  setTrainingCorrectionValue(editingTrainingRecord[value]?.split?.('T')?.[0] || editingTrainingRecord[value] || '');
                }}>
                  <SelectTrigger className="rounded-xl">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="expiry_date">Expiry Date</SelectItem>
                    <SelectItem value="completion_date">Completion Date</SelectItem>
                    <SelectItem value="status">Status</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              
              <div className="space-y-2">
                <Label>Current Value</Label>
                <Input 
                  value={editingTrainingRecord[trainingCorrectionField] || '(not set)'} 
                  disabled 
                  className="rounded-xl bg-gray-100"
                />
              </div>
              
              <div className="space-y-2">
                <Label>New Value *</Label>
                {trainingCorrectionField === 'status' ? (
                  <Select value={trainingCorrectionValue} onValueChange={setTrainingCorrectionValue}>
                    <SelectTrigger className="rounded-xl">
                      <SelectValue placeholder="Select new status" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="not_started">Not Started</SelectItem>
                      <SelectItem value="in_progress">In Progress</SelectItem>
                      <SelectItem value="completed">Completed</SelectItem>
                      <SelectItem value="expired">Expired</SelectItem>
                      <SelectItem value="expiring">Expiring</SelectItem>
                    </SelectContent>
                  </Select>
                ) : (
                  <Input 
                    type="date" 
                    value={trainingCorrectionValue?.split?.('T')?.[0] || trainingCorrectionValue || ''} 
                    onChange={(e) => setTrainingCorrectionValue(e.target.value)}
                    className="rounded-xl"
                  />
                )}
              </div>
              
              <div className="space-y-2">
                <Label>Reason for Change *</Label>
                <Textarea 
                  placeholder="Explain why this correction is being made (required for audit trail)"
                  value={trainingCorrectionReason}
                  onChange={(e) => setTrainingCorrectionReason(e.target.value)}
                  className="rounded-xl min-h-[80px]"
                />
              </div>
            </div>
          )}
          <DialogFooter className="mt-6">
            <Button variant="outline" onClick={() => setTrainingCorrectionDialogOpen(false)} className="rounded-xl">
              Cancel
            </Button>
            <Button 
              onClick={handleTrainingCorrection} 
              disabled={!trainingCorrectionReason || !trainingCorrectionValue}
              className="bg-primary hover:bg-primary-hover text-white rounded-xl"
            >
              Save Correction
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      
      {/* Training History Dialog */}
      <Dialog open={trainingHistoryDialogOpen} onOpenChange={setTrainingHistoryDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle className="font-heading">Training Record History</DialogTitle>
          </DialogHeader>
          <div className="space-y-3 max-h-96 overflow-y-auto mt-4">
            {trainingHistory.length === 0 ? (
              <div className="text-center py-8 text-text-muted">
                <History className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p>No correction history</p>
              </div>
            ) : (
              trainingHistory.map((entry, idx) => (
                <div key={entry.id || idx} className="p-3 bg-white rounded-lg border border-[#E4E8EB]">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="font-medium text-text-primary">
                        {entry.action === 'training_correction' ? 'Correction' : entry.action?.replace('_', ' ')}
                      </p>
                      {entry.field_changed && (
                        <p className="text-sm text-text-muted">
                          <span className="font-medium">{entry.field_changed}</span>: {entry.old_value || '(empty)'} → {entry.new_value}
                        </p>
                      )}
                      {entry.reason && (
                        <p className="text-sm text-text-muted mt-1">
                          <span className="font-medium">Reason:</span> {entry.reason}
                        </p>
                      )}
                    </div>
                    <div className="text-right text-xs text-text-muted">
                      <p>{entry.changed_by_name || 'System'}</p>
                      <p>{entry.created_at ? new Date(entry.created_at).toLocaleString() : ''}</p>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </DialogContent>
      </Dialog>
      
      {/* Delete Training Record Dialog */}
      <Dialog open={deleteTrainingDialogOpen} onOpenChange={setDeleteTrainingDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-red-600">
              <Trash2 className="h-5 w-5" />
              Delete Training Record
            </DialogTitle>
            <DialogDescription>
              This will permanently remove this training record. An audit trail will be kept.
            </DialogDescription>
          </DialogHeader>
          {deletingTrainingRecord && (
            <div className="space-y-4 py-4">
              <div className="p-3 bg-red-50 rounded-lg border border-red-200">
                <p className="font-medium text-red-800">{deletingTrainingRecord.training_name}</p>
                <p className="text-sm text-red-600 mt-1">
                  Status: {deletingTrainingRecord.status?.replace('_', ' ')}
                </p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="delete-training-reason">Reason for deletion (optional)</Label>
                <Textarea
                  id="delete-training-reason"
                  placeholder="Enter an optional reason for deleting this record"
                  value={deleteTrainingReason}
                  onChange={(e) => setDeleteTrainingReason(e.target.value)}
                  className="min-h-[80px] rounded-xl"
                />
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteTrainingDialogOpen(false)} className="rounded-xl">
              Cancel
            </Button>
            <Button 
              variant="destructive" 
              onClick={handleDeleteTrainingRecord}
              disabled={isDeletingTraining}
              className="rounded-xl"
            >
              {isDeletingTraining ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Trash2 className="h-4 w-4 mr-2" />}
              Delete Record
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      
      {/* Acknowledgement Dialog - For Contract/Handbook acknowledgements */}
      <Dialog open={acknowledgementDialogOpen} onOpenChange={(open) => {
        setAcknowledgementDialogOpen(open);
        if (!open) {
          setAcknowledgementConfirmed(false);
          setAcknowledgingRequirement(null);
        }
      }}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-green-600">
              <CheckCircle className="h-5 w-5" />
              Confirm & Complete
            </DialogTitle>
            <DialogDescription>
              Please confirm that this employee has received and understood the document.
            </DialogDescription>
          </DialogHeader>
          {acknowledgingRequirement && (
            <div className="space-y-4 py-4">
              <div className="p-4 bg-green-50 rounded-lg border border-green-200">
                <p className="font-semibold text-green-800">{acknowledgingRequirement.name}</p>
                <p className="text-sm text-green-600 mt-2">
                  {acknowledgingRequirement.description}
                </p>
              </div>
              
              <div className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg border">
                <Checkbox 
                  id="acknowledgement-confirm"
                  checked={acknowledgementConfirmed}
                  onCheckedChange={setAcknowledgementConfirmed}
                  className="mt-0.5"
                  data-testid="acknowledgement-checkbox"
                />
                <label htmlFor="acknowledgement-confirm" className="text-sm cursor-pointer">
                  {acknowledgingRequirement.acknowledgement_text || 
                    `I confirm that this employee has received, read, and understood the ${acknowledgingRequirement.name.replace(' Acknowledgement', '')}.`}
                </label>
              </div>
              
              <p className="text-xs text-text-muted">
                This acknowledgement will be logged with your name and timestamp for audit purposes.
              </p>
            </div>
          )}
          <DialogFooter>
            <Button 
              variant="outline" 
              onClick={() => setAcknowledgementDialogOpen(false)} 
              className="rounded-xl"
            >
              Cancel
            </Button>
            <Button 
              onClick={handleAcknowledgeRequirement}
              disabled={!acknowledgementConfirmed || isAcknowledging}
              className="rounded-xl bg-green-600 hover:bg-green-700"
              data-testid="submit-acknowledgement-btn"
            >
              {isAcknowledging ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <CheckCircle className="h-4 w-4 mr-2" />
              )}
              Confirm & Complete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Form Submission Modal - Structured forms with sections */}
      <Dialog open={formModalOpen} onOpenChange={(open) => {
        setFormModalOpen(open);
        if (!open) {
          setFormTemplate(null);
          setFormData({});
        }
      }}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          {/* Branded Header for Staff Health Questionnaire */}
          {formTemplate?.branding?.show_logo && (
            <div className="bg-[#2E7D32] text-white p-4 -m-6 mb-4 rounded-t-lg">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 bg-white rounded-full flex items-center justify-center">
                  <span className="text-[#2E7D32] font-bold text-xl">O</span>
                </div>
                <div>
                  <h2 className="text-lg font-bold">{formTemplate?.branding?.company_name || 'Osabea Healthcare Solutions Ltd'}</h2>
                  <p className="text-sm opacity-90">{formTemplate?.name}</p>
                </div>
              </div>
            </div>
          )}
          
          <DialogHeader className={formTemplate?.branding?.show_logo ? 'pt-0' : ''}>
            {!formTemplate?.branding?.show_logo && (
              <DialogTitle className="font-heading flex items-center gap-2">
                <ClipboardCheck className="h-5 w-5 text-primary" />
                {formTemplate?.name || 'Complete Form'}
              </DialogTitle>
            )}
            {formTemplate?.description && (
              <DialogDescription className="text-sm text-text-muted">
                {formTemplate.description}
              </DialogDescription>
            )}
          </DialogHeader>
          
          {formTemplate && (
            <div className="space-y-6 mt-4">
              {/* Optional form notice */}
              {formTemplate.is_optional && (
                <div className="p-3 bg-blue-50 border border-blue-200 rounded-xl">
                  <p className="text-sm text-blue-700 flex items-center gap-2">
                    <span className="px-2 py-0.5 bg-blue-100 text-blue-800 text-xs font-medium rounded">Optional</span>
                    This form does not affect compliance percentage or work readiness status.
                  </p>
                </div>
              )}
              
              {/* Auto-fill notice */}
              {formTemplate.auto_fill_fields?.length > 0 && Object.keys(formData).length > 0 && (
                <div className="p-3 bg-green-50 border border-green-200 rounded-xl">
                  <p className="text-sm text-green-700 flex items-center gap-2">
                    <CheckCircle className="h-4 w-4" />
                    Some fields have been pre-filled from the employee profile. Please review and update as needed.
                  </p>
                </div>
              )}
              
              {/* Profile update notice */}
              {formTemplate.updates_profile && (
                <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl">
                  <p className="text-sm text-amber-700 flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4" />
                    This form can update the employee's profile data when submitted.
                  </p>
                </div>
              )}
              
              {/* Render sections if available, otherwise fallback to flat fields */}
              {formTemplate.sections?.length > 0 ? (
                <div className="space-y-6">
                  {formTemplate.sections.map((section) => {
                    // Skip admin-only sections for non-admins
                    if (section.admin_only && !isAdmin()) return null;
                    
                    // Use green header style if form has branding
                    const sectionHeaderClass = formTemplate?.branding?.header_color 
                      ? 'bg-[#2E7D32] text-white px-4 py-3 border-b border-[#2E7D32]'
                      : 'bg-gray-50 px-4 py-3 border-b border-gray-200';
                    
                    return (
                      <div key={section.id} className="border border-gray-200 rounded-xl overflow-hidden">
                        <div className={sectionHeaderClass}>
                          <h4 className={`font-medium ${formTemplate?.branding?.header_color ? 'text-white' : 'text-text-primary'}`}>
                            {section.title}
                          </h4>
                          {section.description && (
                            <p className={`text-xs mt-0.5 ${formTemplate?.branding?.header_color ? 'text-white/80' : 'text-text-muted'}`}>
                              {section.description}
                            </p>
                          )}
                        </div>
                        <div className="p-4 space-y-4">
                          {section.fields.map((field) => {
                            // Handle conditional fields
                            if (field.conditional_on) {
                              const conditionValue = formData[field.conditional_on];
                              if (conditionValue !== field.conditional_value) {
                                return null;
                              }
                            }
                            
                            return (
                              <div key={field.id} className="space-y-1.5">
                                {field.type === 'info' ? (
                                  <p className="text-sm text-text-muted italic bg-[#F8FAFA] p-3 rounded-lg">
                                    {field.label}
                                  </p>
                                ) : (
                                  <>
                                    <Label className="text-sm font-medium flex items-center gap-2">
                                      {field.label}
                                      {field.required && <span className="text-error">*</span>}
                                      {field.auto_fill && formData[field.id] && (
                                        <span className="text-xs text-green-600 font-normal">(auto-filled)</span>
                                      )}
                                    </Label>
                                    
                                    {field.type === 'text' && (
                                      <Input
                                        value={formData[field.id] || ''}
                                        onChange={(e) => setFormData({...formData, [field.id]: e.target.value})}
                                        placeholder={field.placeholder || ''}
                                        className="rounded-xl"
                                      />
                                    )}
                                    
                                    {field.type === 'number' && (
                                      <Input
                                        type="number"
                                        value={formData[field.id] || ''}
                                        onChange={(e) => setFormData({...formData, [field.id]: e.target.value})}
                                        placeholder={field.placeholder || ''}
                                        className="rounded-xl"
                                      />
                                    )}
                                    
                                    {field.type === 'textarea' && (
                                      <Textarea
                                        value={formData[field.id] || ''}
                                        onChange={(e) => setFormData({...formData, [field.id]: e.target.value})}
                                        placeholder={field.placeholder || ''}
                                        className="rounded-xl"
                                        rows={3}
                                      />
                                    )}
                                    
                                    {field.type === 'date' && (
                                      <Input
                                        type="date"
                                        value={formData[field.id] || ''}
                                        onChange={(e) => setFormData({...formData, [field.id]: e.target.value})}
                                        className="rounded-xl"
                                      />
                                    )}
                                    
                                    {field.type === 'checkbox' && (
                                      <div className="flex items-center gap-2">
                                        <Checkbox
                                          id={field.id}
                                          checked={formData[field.id] || false}
                                          onCheckedChange={(checked) => setFormData({...formData, [field.id]: checked})}
                                        />
                                        <label htmlFor={field.id} className="text-sm cursor-pointer">Yes</label>
                                      </div>
                                    )}
                                    
                                    {field.type === 'select' && (
                                      <Select 
                                        value={formData[field.id] || ''} 
                                        onValueChange={(v) => setFormData({...formData, [field.id]: v})}
                                      >
                                        <SelectTrigger className="rounded-xl">
                                          <SelectValue placeholder="Select..." />
                                        </SelectTrigger>
                                        <SelectContent>
                                          {field.options?.map((opt) => (
                                            <SelectItem key={opt} value={opt}>{opt}</SelectItem>
                                          ))}
                                        </SelectContent>
                                      </Select>
                                    )}
                                    
                                    {field.type === 'multi_select' && (
                                      <div className="flex flex-wrap gap-2">
                                        {field.options?.map((opt) => (
                                          <label key={opt} className="flex items-center gap-1.5 text-sm">
                                            <Checkbox
                                              checked={(formData[field.id] || []).includes(opt)}
                                              onCheckedChange={(checked) => {
                                                const current = formData[field.id] || [];
                                                if (checked) {
                                                  setFormData({...formData, [field.id]: [...current, opt]});
                                                } else {
                                                  setFormData({...formData, [field.id]: current.filter(v => v !== opt)});
                                                }
                                              }}
                                            />
                                            {opt}
                                          </label>
                                        ))}
                                      </div>
                                    )}
                                  </>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                /* Fallback to flat fields for backward compatibility */
                <div className="grid gap-4">
                  {formTemplate.fields?.map((field) => (
                    <div key={field.id} className="space-y-1.5">
                      {field.type === 'info' ? (
                        <p className="text-sm text-text-muted italic bg-[#F8FAFA] p-3 rounded-lg">
                          {field.label}
                        </p>
                      ) : (
                        <>
                          <Label className="text-sm font-medium">
                            {field.label}
                            {field.required && <span className="text-error ml-1">*</span>}
                          </Label>
                          
                          {field.type === 'text' && (
                            <Input
                              value={formData[field.id] || ''}
                              onChange={(e) => setFormData({...formData, [field.id]: e.target.value})}
                              placeholder={field.placeholder || ''}
                              className="rounded-xl"
                            />
                          )}
                          
                          {field.type === 'textarea' && (
                            <Textarea
                              value={formData[field.id] || ''}
                              onChange={(e) => setFormData({...formData, [field.id]: e.target.value})}
                              placeholder={field.placeholder || ''}
                              className="rounded-xl"
                              rows={3}
                            />
                          )}
                          
                          {field.type === 'date' && (
                            <Input
                              type="date"
                              value={formData[field.id] || ''}
                              onChange={(e) => setFormData({...formData, [field.id]: e.target.value})}
                              className="rounded-xl"
                            />
                          )}
                          
                          {field.type === 'checkbox' && (
                            <div className="flex items-center gap-2">
                              <Checkbox
                                id={field.id}
                                checked={formData[field.id] || false}
                                onCheckedChange={(checked) => setFormData({...formData, [field.id]: checked})}
                              />
                              <label htmlFor={field.id} className="text-sm cursor-pointer">Yes</label>
                            </div>
                          )}
                          
                          {field.type === 'select' && (
                            <Select 
                              value={formData[field.id] || ''} 
                              onValueChange={(v) => setFormData({...formData, [field.id]: v})}
                            >
                              <SelectTrigger className="rounded-xl">
                                <SelectValue placeholder="Select..." />
                              </SelectTrigger>
                              <SelectContent>
                                {field.options?.map((opt) => (
                                  <SelectItem key={opt} value={opt}>{opt}</SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          )}
                        </>
                      )}
                    </div>
                  ))}
                </div>
              )}
              
              <DialogFooter className="pt-4">
                <Button 
                  variant="outline" 
                  onClick={() => setFormModalOpen(false)} 
                  className="rounded-xl"
                >
                  Cancel
                </Button>
                <Button 
                  onClick={handleFormSubmit}
                  disabled={isSubmittingForm}
                  className="rounded-xl bg-primary hover:bg-primary/90"
                  data-testid="submit-form-btn"
                >
                  {isSubmittingForm ? (
                    <><Loader2 className="h-4 w-4 animate-spin mr-2" /> Submitting...</>
                  ) : (
                    'Submit Form'
                  )}
                </Button>
              </DialogFooter>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* View Form Modal - Display submitted form data */}
      <Dialog open={viewFormOpen} onOpenChange={setViewFormOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="font-heading flex items-center gap-2">
              <ClipboardCheck className="h-5 w-5 text-primary" />
              {viewFormData?.requirementName || 'Form Submission'}
            </DialogTitle>
          </DialogHeader>
          
          {viewFormData && (
            <div className="space-y-4 mt-4">
              {/* Status badges */}
              <div className="flex items-center gap-3 p-3 bg-[#F8FAFA] rounded-xl">
                <div className="flex items-center gap-2">
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                    viewFormData.verified 
                      ? 'bg-green-100 text-green-700' 
                      : 'bg-blue-100 text-blue-700'
                  }`}>
                    {viewFormData.verified ? 'Verified' : 'Submitted'}
                  </span>
                </div>
                <div className="text-xs text-text-muted">
                  Submitted: {viewFormData.submitted_at ? new Date(viewFormData.submitted_at).toLocaleString() : 'Unknown'}
                </div>
                {viewFormData.submitted_by_name && (
                  <div className="text-xs text-text-muted">
                    By: {viewFormData.submitted_by_name}
                  </div>
                )}
              </div>
              
              {/* Form data display */}
              <div className="space-y-3">
                {Object.entries(viewFormData.data || {}).map(([key, value]) => (
                  <div key={key} className="flex items-start gap-3 p-2 border-b border-[#E4E8EB]">
                    <span className="text-sm font-medium text-text-primary min-w-[180px] capitalize">
                      {key.replace(/_/g, ' ')}:
                    </span>
                    <span className="text-sm text-text-muted flex-1">
                      {typeof value === 'boolean' ? (value ? 'Yes' : 'No') : (value || '-')}
                    </span>
                  </div>
                ))}
              </div>
              
              {/* Verification info if verified */}
              {viewFormData.verified && viewFormData.verified_by_name && (
                <div className="p-3 bg-green-50 rounded-xl border border-green-200">
                  <p className="text-sm text-green-700">
                    <CheckCircle className="h-4 w-4 inline mr-2" />
                    Verified by {viewFormData.verified_by_name} on {new Date(viewFormData.verified_at).toLocaleString()}
                  </p>
                </div>
              )}
              
              <DialogFooter className="pt-4">
                <Button 
                  variant="outline" 
                  onClick={() => setViewFormOpen(false)} 
                  className="rounded-xl"
                >
                  Close
                </Button>
                {!viewFormData.verified && isAdmin() && (
                  <Button 
                    onClick={() => handleVerifyFormSubmission(viewFormData.id)}
                    className="rounded-xl bg-green-600 hover:bg-green-700"
                    data-testid="verify-form-btn"
                  >
                    <CheckCircle className="h-4 w-4 mr-2" />
                    Verify Form
                  </Button>
                )}
              </DialogFooter>
            </div>
          )}
        </DialogContent>
      </Dialog>
      
      {/* Extraction Review Dialog */}
      <Dialog open={extractionDialogOpen} onOpenChange={(open) => {
        if (!open && !isApplyingExtraction) {
          handleDiscardExtraction();
        }
      }}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="font-heading flex items-center gap-2">
              <FileText className="h-5 w-5 text-primary" />
              {extractionFailed ? 'Extraction Options' : 'Review Extracted Data'}
            </DialogTitle>
            <DialogDescription>
              {extractionFailed ? (
                extractionFailed.message
              ) : (
                <>
                  Review the extracted values below. Select which fields to apply to the employee profile.
                  <span className="block mt-2 text-amber-600 font-medium">
                    Note: This updates profile data only. Compliance evidence requirements remain unchanged.
                  </span>
                </>
              )}
            </DialogDescription>
          </DialogHeader>
          
          {isExtracting ? (
            <div className="flex flex-col items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-primary mb-4" />
              <p className="text-text-muted">Extracting data from application form...</p>
              <p className="text-xs text-text-muted mt-1">This may take a few seconds</p>
            </div>
          ) : extractionFailed ? (
            /* Extraction Failed - Show Options */
            <div className="space-y-4">
              {/* Friendly Message */}
              <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg">
                <div className="flex items-start gap-3">
                  <AlertTriangle className="h-5 w-5 text-amber-600 mt-0.5 flex-shrink-0" />
                  <div className="text-sm text-amber-800">
                    <p className="font-medium mb-1">Don't worry - you can still proceed!</p>
                    <p>Automatic extraction didn't work for this document, but you have options to continue.</p>
                    {extractionFailed.extraction_log && (
                      <p className="text-xs mt-2 text-amber-600">
                        Details: {extractionFailed.extraction_log.file_type} ({Math.round((extractionFailed.extraction_log.file_size_bytes || 0) / 1024)} KB)
                        {extractionFailed.extraction_log.failure_reason && (
                          <span className="block">Reason: {extractionFailed.extraction_log.failure_reason}</span>
                        )}
                      </p>
                    )}
                  </div>
                </div>
              </div>
              
              {/* Options Buttons */}
              <div className="space-y-3">
                {extractionFailed.options?.map((option) => (
                  <button
                    key={option.action}
                    onClick={() => handleExtractionOption(option.action)}
                    className="w-full flex items-center gap-4 p-4 border rounded-lg hover:bg-gray-50 transition-colors text-left"
                    data-testid={`extraction-option-${option.action}`}
                  >
                    <div className="flex-shrink-0">
                      {option.action === 'fill_manually' && (
                        <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center">
                          <Edit className="h-5 w-5 text-blue-600" />
                        </div>
                      )}
                      {option.action === 'view_document' && (
                        <div className="w-10 h-10 rounded-full bg-purple-100 flex items-center justify-center">
                          <Eye className="h-5 w-5 text-purple-600" />
                        </div>
                      )}
                      {option.action === 'retry' && (
                        <div className="w-10 h-10 rounded-full bg-green-100 flex items-center justify-center">
                          <RefreshCw className="h-5 w-5 text-green-600" />
                        </div>
                      )}
                    </div>
                    <div className="flex-1">
                      <p className="font-medium text-text-primary">{option.label}</p>
                      <p className="text-sm text-text-muted">{option.description}</p>
                    </div>
                    <ChevronRight className="h-5 w-5 text-gray-400" />
                  </button>
                ))}
              </div>
              
              <DialogFooter className="pt-4">
                <Button
                  variant="outline"
                  onClick={handleDiscardExtraction}
                  data-testid="close-extraction-dialog"
                >
                  Close
                </Button>
              </DialogFooter>
            </div>
          ) : extractionResult ? (
            <div className="space-y-4">
              {/* Extraction Method & Low Confidence Warning */}
              {extractionResult.low_confidence_fields?.length > 0 && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                  <div className="flex items-start gap-2">
                    <AlertTriangle className="h-4 w-4 text-red-600 mt-0.5 flex-shrink-0" />
                    <div className="text-sm text-red-800">
                      <p className="font-medium">Low Confidence Fields Detected</p>
                      <p>Please review highlighted fields carefully: {extractionResult.low_confidence_fields.map(f => FIELD_LABELS[f] || f).join(', ')}</p>
                    </div>
                  </div>
                </div>
              )}
              
              {/* Extraction Method Badge */}
              {extractionResult.extraction_method && (
                <div className="flex items-center gap-2 text-xs">
                  <span className="text-text-muted">Extraction method:</span>
                  <span className={`px-2 py-0.5 rounded font-medium ${
                    extractionResult.extraction_method === 'ai' ? 'bg-blue-100 text-blue-700' :
                    extractionResult.extraction_method === 'ai+ocr' ? 'bg-purple-100 text-purple-700' :
                    'bg-gray-100 text-gray-700'
                  }`}>
                    {extractionResult.extraction_method === 'ai' ? 'AI Vision' :
                     extractionResult.extraction_method === 'ai+ocr' ? 'AI + OCR' :
                     extractionResult.extraction_method === 'ocr' ? 'OCR' : extractionResult.extraction_method}
                  </span>
                </div>
              )}
              
              {/* Compliance Note */}
              <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
                <div className="flex items-start gap-2">
                  <AlertTriangle className="h-4 w-4 text-amber-600 mt-0.5 flex-shrink-0" />
                  <div className="text-sm text-amber-800">
                    <p className="font-medium">Profile Data Only</p>
                    <p>Extracted values will populate profile fields (e.g., NI Number field). They do NOT complete compliance requirements (e.g., "Proof of NI Number" still needs evidence upload).</p>
                  </div>
                </div>
              </div>
              
              {/* Fields Table */}
              <div className="border rounded-lg overflow-hidden">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="text-left p-3 font-medium">Apply</th>
                      <th className="text-left p-3 font-medium">Field</th>
                      <th className="text-left p-3 font-medium">Extracted Value</th>
                      <th className="text-left p-3 font-medium">Current Value</th>
                      <th className="text-left p-3 font-medium">Confidence</th>
                    </tr>
                  </thead>
                  <tbody>
                    {extractionResult.fields.map((field, idx) => {
                      // Handle both numeric confidence and string confidence_label
                      const confidenceScore = typeof field.confidence === 'number' ? field.confidence : null;
                      const confidenceLabel = field.confidence_label || 
                        (typeof field.confidence === 'string' ? field.confidence : 
                         confidenceScore >= 0.8 ? 'high' : confidenceScore >= 0.5 ? 'medium' : 'low');
                      const isLowConfidence = confidenceLabel === 'low' || (confidenceScore !== null && confidenceScore < 0.5);
                      
                      return (
                        <tr 
                          key={field.field_name} 
                          className={`${idx % 2 === 0 ? 'bg-white' : 'bg-gray-50'} ${isLowConfidence ? 'bg-red-50/50' : ''}`}
                        >
                          <td className="p-3">
                            <input
                              type="checkbox"
                              checked={fieldsToApply[field.field_name] || false}
                              onChange={() => toggleFieldToApply(field.field_name)}
                              className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
                              data-testid={`apply-field-${field.field_name}`}
                            />
                          </td>
                          <td className="p-3 font-medium text-text-primary">
                            {FIELD_LABELS[field.field_name] || field.field_name}
                            {isLowConfidence && (
                              <span className="ml-2 text-red-500" title="Low confidence - please verify">⚠</span>
                            )}
                          </td>
                          <td className="p-3">
                            <span className={`${field.extracted_value ? 'text-text-primary' : 'text-text-muted italic'} ${isLowConfidence ? 'text-red-700' : ''}`}>
                              {field.extracted_value || 'Not found'}
                            </span>
                          </td>
                          <td className="p-3">
                            <span className={`${field.current_value ? 'text-text-primary' : 'text-text-muted italic'}`}>
                              {field.current_value || 'Empty'}
                            </span>
                          </td>
                          <td className="p-3">
                            <div className="flex items-center gap-1">
                              <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                                confidenceLabel === 'high' ? 'bg-green-100 text-green-700' :
                                confidenceLabel === 'medium' ? 'bg-amber-100 text-amber-700' :
                                'bg-red-100 text-red-700'
                              }`}>
                                {confidenceLabel}
                              </span>
                              {confidenceScore !== null && (
                                <span className="text-xs text-text-muted">
                                  {Math.round(confidenceScore * 100)}%
                                </span>
                              )}
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
              
              {/* Quick Actions */}
              <div className="flex gap-2 text-xs">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    const allSelected = {};
                    extractionResult.fields.forEach(f => { allSelected[f.field_name] = true; });
                    setFieldsToApply(allSelected);
                  }}
                >
                  Select All
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    const emptyOnly = {};
                    extractionResult.fields.forEach(f => {
                      emptyOnly[f.field_name] = !f.current_value && !!f.extracted_value;
                    });
                    setFieldsToApply(emptyOnly);
                  }}
                >
                  Select Empty Only
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setFieldsToApply({})}
                >
                  Clear All
                </Button>
              </div>
              
              <DialogFooter className="pt-4">
                <Button
                  variant="outline"
                  onClick={handleDiscardExtraction}
                  disabled={isApplyingExtraction}
                >
                  Discard
                </Button>
                <Button
                  onClick={handleApplyExtraction}
                  disabled={isApplyingExtraction || Object.values(fieldsToApply).filter(Boolean).length === 0}
                  data-testid="apply-extraction-btn"
                >
                  {isApplyingExtraction ? (
                    <><Loader2 className="h-4 w-4 animate-spin mr-2" /> Applying...</>
                  ) : (
                    <>Apply {Object.values(fieldsToApply).filter(Boolean).length} Field(s)</>
                  )}
                </Button>
              </DialogFooter>
            </div>
          ) : (
            <div className="text-center py-8 text-text-muted">
              <p>No extraction data available.</p>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
