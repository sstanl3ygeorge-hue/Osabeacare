import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { toast } from 'sonner';
import DocumentPreviewModal from '../../components/portal/DocumentPreviewModal';
import { FileUploaderInline } from '../../components/ui/file-uploader';
import {
  Shield, FileText, AlertTriangle, CheckCircle, Clock, Upload,
  Loader2, Building, Users, ClipboardList, AlertCircle, Calendar,
  RefreshCw, Download, Plus, Search, Filter, Eye, XCircle, UserPlus,
  Edit, History, Save, BookOpen, ArrowRight, TrendingUp, Bell, Mail, Send,
  Trash2, Package
} from 'lucide-react';
import { formatBackendDate, formatBackendDateTime, parseBackendDate } from '../../lib/dateUtils';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function ComplianceCentrePage() {
  const { token, isAdmin } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const serviceUserIdFilter = searchParams.get('service_user_id') || '';
  
  // Initialize tab from URL for navigation state persistence
  const [activeTab, setActiveTab] = useState(searchParams.get('tab') || 'policies');
  const [loading, setLoading] = useState(true);
  const [dashboard, setDashboard] = useState(null);
  const [centreSummary, setCentreSummary] = useState(null);
  const [policies, setPolicies] = useState([]);
  const [insurance, setInsurance] = useState([]);
  const [incidents, setIncidents] = useState([]);
  const [staffMeetings, setStaffMeetings] = useState([]);
  const [employerAudits, setEmployerAudits] = useState([]);
  const [incidentFilter, setIncidentFilter] = useState({ status: 'all', severity: 'all' }); // Incident filters
  const [dbsReport, setDbsReport] = useState(null);
  const [trainingReport, setTrainingReport] = useState(null);
  const [complianceAlerts, setComplianceAlerts] = useState(null); // For Insights tab
  
  // Document preview modal state
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewFile, setPreviewFile] = useState(null);
  
  // Sync tab changes to URL
  const handleTabChange = (value) => {
    setActiveTab(value);
    const next = { tab: value };
    if (serviceUserIdFilter) next.service_user_id = serviceUserIdFilter;
    setSearchParams(next, { replace: true });
  };
  
  // Open document in preview modal
  const handleViewDocument = (type, id, title, filename) => {
    const endpoint = type === 'policy' 
      ? `${API}/compliance/policies/${id}/file`
      : `${API}/compliance/insurance/${id}/file`;
    
    setPreviewFile({
      url: endpoint,
      name: title || filename || 'Document',
      filename: filename
    });
    setPreviewOpen(true);
  };
  
  // Download document with authentication
  const handleDownloadDocument = async (type, id, filename) => {
    try {
      toast.loading('Downloading...');
      
      const endpoint = type === 'policy' 
        ? `${API}/compliance/policies/${id}/download`
        : `${API}/compliance/insurance/${id}/download`;
      
      const response = await axios.get(endpoint, {
        headers: { Authorization: `Bearer ${token}` },
        responseType: 'blob'
      });
      
      const blob = new Blob([response.data]);
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename || 'document.pdf';
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      
      toast.dismiss();
      toast.success('Document downloaded');
    } catch (error) {
      console.error('Failed to download document:', error);
      toast.dismiss();
      toast.error('Failed to download document');
    }
  };

  const handleDownloadPolicyAcknowledgement = async (assignment) => {
    if (!assignment?.id) return;
    try {
      toast.loading('Preparing acknowledgement PDF...');
      const response = await axios.get(
        `${API}/policy-assignments/${assignment.id}/acknowledgement-pdf`,
        {
          headers: { Authorization: `Bearer ${token}` },
          responseType: 'blob'
        }
      );

      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      const safeTitle = (assignment.policy_title || policyToAssign?.name || 'policy').replace(/\s+/g, '_');
      const safeEmployee = (assignment.employee_name || 'employee').replace(/\s+/g, '_');
      link.href = url;
      link.download = `${safeTitle}_${safeEmployee}_acknowledgement.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      toast.dismiss();
      toast.success('Acknowledgement downloaded');
    } catch (error) {
      toast.dismiss();
      toast.error(error.response?.data?.detail || 'Failed to download acknowledgement');
    }
  };

  const handleDownloadStaffMeetingPdf = async (meeting) => {
    if (!meeting?.id) return;
    try {
      toast.loading('Preparing staff meeting PDF...');
      const response = await axios.get(
        `${API}/compliance/staff-meetings/${meeting.id}/download-pdf`,
        {
          headers: { Authorization: `Bearer ${token}` },
          responseType: 'blob'
        }
      );

      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      const meetingDate = (meeting.meeting_date || 'meeting').toString().split('T')[0];
      link.href = url;
      link.download = `staff_meeting_${meetingDate}_${meeting.id.slice(0, 8)}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      toast.dismiss();
      toast.success('Staff meeting PDF downloaded');
    } catch (error) {
      toast.dismiss();
      toast.error(error.response?.data?.detail || 'Failed to download staff meeting PDF');
    }
  };

  const handleDownloadEmployerAuditPdf = async (audit) => {
    if (!audit?.id) return;
    try {
      toast.loading('Preparing employer audit PDF...');
      const response = await axios.get(
        `${API}/compliance/employer-audits/${audit.id}/download-pdf`,
        {
          headers: { Authorization: `Bearer ${token}` },
          responseType: 'blob'
        }
      );

      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      const auditDate = (audit.audit_date || 'audit').toString().split('T')[0];
      link.href = url;
      link.download = `employer_audit_${auditDate}_${audit.id.slice(0, 8)}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      toast.dismiss();
      toast.success('Employer audit PDF downloaded');
    } catch (error) {
      toast.dismiss();
      toast.error(error.response?.data?.detail || 'Failed to download employer audit PDF');
    }
  };
  
  // Upload states
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [selectedPolicy, setSelectedPolicy] = useState(null);
  const [selectedInsurance, setSelectedInsurance] = useState(null);
  const [uploadFile, setUploadFile] = useState(null);
  const [uploadVersion, setUploadVersion] = useState('');
  const [uploadReviewDate, setUploadReviewDate] = useState('');
  const [uploadExpiryDate, setUploadExpiryDate] = useState('');
  const [uploadPolicyNumber, setUploadPolicyNumber] = useState('');
  const [uploadProvider, setUploadProvider] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [createCertDialogOpen, setCreateCertDialogOpen] = useState(false);
  const [isCreatingCert, setIsCreatingCert] = useState(false);
  const [newCert, setNewCert] = useState({
    name: '',
    insurance_type: '',
    category: 'safety',
    issue_date: '',
    expiry_date: '',
    provider: '',
    policy_number: '',
    notes: '',
    required: false,
    conditional: true,
    valid_until_replaced: false
  });
  const [isReplaceMode, setIsReplaceMode] = useState(false);
  const [replaceReason, setReplaceReason] = useState('');
  const [removeDialogOpen, setRemoveDialogOpen] = useState(false);
  const [removeTarget, setRemoveTarget] = useState(null);
  const [removeReason, setRemoveReason] = useState('');
  
  // Incident form
  const [incidentDialogOpen, setIncidentDialogOpen] = useState(false);
  const [newIncident, setNewIncident] = useState({
    incident_type: 'incident',
    title: '',
    description: '',
    date_occurred: new Date().toISOString().split('T')[0],
    location: '',
    persons_involved: '',
    immediate_actions: '',
    root_cause: '',
    corrective_actions: '',
    is_reportable: false,
    report_category: '',
    reported_to_authority: false,
    reported_at: '',
    report_reference: '',
    report_notes: ''
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Staff meeting form
  const [staffMeetingDialogOpen, setStaffMeetingDialogOpen] = useState(false);
  const [newStaffMeeting, setNewStaffMeeting] = useState({
    meeting_date: new Date().toISOString().split('T')[0],
    meeting_type: 'monthly_staff_meeting',
    employee_ids: [],
    agenda: '',
    notes: '',
    actions_required: '',
    next_meeting_date: ''
  });
  const [isSubmittingMeeting, setIsSubmittingMeeting] = useState(false);

  // Employer audit/checklist form
  const [employerAuditDialogOpen, setEmployerAuditDialogOpen] = useState(false);
  const [newEmployerAudit, setNewEmployerAudit] = useState({
    audit_type: 'infection_control_audit',
    audit_date: new Date().toISOString().split('T')[0],
    completed_by: '',
    overall_outcome: 'compliant',
    findings: '',
    actions_required: '',
    next_review_date: '',
    status: 'open'
  });
  const [isSubmittingEmployerAudit, setIsSubmittingEmployerAudit] = useState(false);

  // Employee Assignment state
  const [assignDialogOpen, setAssignDialogOpen] = useState(false);
  const [policyToAssign, setPolicyToAssign] = useState(null);
  const [employees, setEmployees] = useState([]);
  const [policyAssignments, setPolicyAssignments] = useState([]);
  const [selectedEmployees, setSelectedEmployees] = useState([]);
  const [isAssigning, setIsAssigning] = useState(false);

  // Amendment states - for editing policies, insurance, incidents, meetings, employer audits with audit trail
  const [amendDialogOpen, setAmendDialogOpen] = useState(false);
  const [amendType, setAmendType] = useState(null); // 'policy', 'insurance', 'incident', 'meeting', 'audit'
  const [amendRecord, setAmendRecord] = useState(null);
  const [amendForm, setAmendForm] = useState({});
  const [isAmending, setIsAmending] = useState(false);
  
  // History states - for viewing amendment history
  const [historyDialogOpen, setHistoryDialogOpen] = useState(false);
  const [historyType, setHistoryType] = useState(null);
  const [historyRecordId, setHistoryRecordId] = useState(null);
  const [historyData, setHistoryData] = useState([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  
  // CQC Evidence Mapping state
  const [cqcEvidenceMap, setCqcEvidenceMap] = useState(null);
  const [cqcLoading, setCqcLoading] = useState(false);
  
  // Inspection Pack generation state
  const [generatingPack, setGeneratingPack] = useState(false);
  const [canonicalStaffReadiness, setCanonicalStaffReadiness] = useState(null);

  useEffect(() => {
    fetchData();
  }, [token, serviceUserIdFilter]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const insurancePromise = isAdmin()
        ? axios.get(`${API}/compliance/insurance`, { headers: { Authorization: `Bearer ${token}` } })
        : Promise.resolve({ data: [] });

      const [dashRes, summaryRes, policiesRes, insuranceRes, incidentsRes, meetingsRes, auditsRes, employeesRes, assignmentsRes] = await Promise.all([
        axios.get(`${API}/compliance/dashboard`, { headers: { Authorization: `Bearer ${token}` } }),
        axios.get(`${API}/compliance/centre-summary`, { headers: { Authorization: `Bearer ${token}` } }),
        axios.get(`${API}/compliance/policies`, { headers: { Authorization: `Bearer ${token}` } }),
        insurancePromise,
        axios.get(`${API}/compliance/incidents`, {
          headers: { Authorization: `Bearer ${token}` },
          params: serviceUserIdFilter ? { service_user_id: serviceUserIdFilter } : undefined
        }),
        axios.get(`${API}/compliance/staff-meetings`, { headers: { Authorization: `Bearer ${token}` } }),
        axios.get(`${API}/compliance/employer-audits`, { headers: { Authorization: `Bearer ${token}` } }),
        axios.get(`${API}/staff/employees`, { headers: { Authorization: `Bearer ${token}` } }),
        axios.get(`${API}/policy-assignments?include_inactive=true`, { headers: { Authorization: `Bearer ${token}` } })
      ]);
      
      setDashboard(dashRes.data);
      setCentreSummary(summaryRes.data);
      setPolicies(policiesRes.data);
      setInsurance(insuranceRes.data);
      setIncidents(incidentsRes.data);
      setStaffMeetings(meetingsRes.data);
      setEmployerAudits(auditsRes.data);
      const activeEmployees = employeesRes.data.filter(e => !['archived', 'withdrawn', 'superseded'].includes(e.status));
      setEmployees(activeEmployees);
      const staffForReadiness = activeEmployees.filter(e =>
        e.person_stage === 'employee' ||
        ['onboarding', 'active', 'inactive', 'active_employee'].includes(e.status)
      );
      const employeeIds = staffForReadiness.map((employee) => employee.id).filter(Boolean);
      const readinessRes = employeeIds.length > 0
        ? await axios.get(`${API}/employees/unified-progress-summary`, {
            params: { employee_ids: employeeIds.join(',') },
            headers: { Authorization: `Bearer ${token}` }
          }).catch(() => ({ data: [] }))
        : { data: [] };
      const workReady = (readinessRes.data || []).filter((summary) => summary.is_work_ready === true).length;
      setCanonicalStaffReadiness({
        total: staffForReadiness.length,
        workReady,
        notReady: staffForReadiness.length - workReady
      });
      setPolicyAssignments(assignmentsRes.data);
    } catch (error) {
      console.error('Failed to fetch compliance data:', error);
    } finally {
      setLoading(false);
    }
  };
  
  // Fetch CQC Evidence Map (only when tab is clicked)
  const fetchCqcEvidenceMap = async () => {
    if (cqcEvidenceMap) return; // Already loaded
    setCqcLoading(true);
    try {
      const response = await axios.get(`${API}/compliance/cqc-evidence-map`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setCqcEvidenceMap(response.data);
    } catch (error) {
      console.error('Failed to fetch CQC evidence map:', error);
      toast.error('Failed to load CQC evidence mapping');
    } finally {
      setCqcLoading(false);
    }
  };

  const handleSeedPolicies = async () => {
    try {
      await axios.post(`${API}/compliance/seed-policies`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      await axios.post(`${API}/compliance/seed-insurance`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Compliance items created');
      fetchData();
    } catch (error) {
      toast.error('Failed to seed compliance items');
    }
  };

  const handleCreateCertificateRecord = async (e) => {
    e.preventDefault();

    const normalizedType = (newCert.insurance_type || '').trim().toLowerCase().replace(/\s+/g, '_');
    if (!newCert.name.trim() || !normalizedType) {
      toast.error('Name and type are required');
      return;
    }

    if (!newCert.valid_until_replaced && !newCert.expiry_date) {
      toast.error('Expiry or due date is required unless set to valid until replaced');
      return;
    }

    setIsCreatingCert(true);
    try {
      await axios.post(
        `${API}/compliance/insurance`,
        {
          name: newCert.name.trim(),
          insurance_type: normalizedType,
          category: newCert.category,
          issue_date: newCert.issue_date || null,
          expiry_date: newCert.valid_until_replaced ? null : (newCert.expiry_date || null),
          provider: newCert.provider || null,
          policy_number: newCert.policy_number || null,
          notes: newCert.notes || null,
          required: !!newCert.required,
          conditional: !!newCert.conditional,
          valid_until_replaced: !!newCert.valid_until_replaced,
          requires_expiry_date: !newCert.valid_until_replaced,
          renewal_period_months: 12,
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      toast.success('Certificate/check record created');
      setCreateCertDialogOpen(false);
      setNewCert({
        name: '',
        insurance_type: '',
        category: 'safety',
        issue_date: '',
        expiry_date: '',
        provider: '',
        policy_number: '',
        notes: '',
        required: false,
        conditional: true,
        valid_until_replaced: false
      });
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create certificate/check record');
    } finally {
      setIsCreatingCert(false);
    }
  };

  // Handle generating inspection pack (REUSES existing data endpoints)
  const handleGenerateInspectionPack = async () => {
    setGeneratingPack(true);
    try {
      const response = await axios.get(`${API}/inspection-pack/generate`, {
        headers: { Authorization: `Bearer ${token}` },
        responseType: 'blob',
        params: {
          include_policies: true,
          include_certificates: true,
          include_staff_summary: true
        }
      });
      
      // Create download link
      const blob = new Blob([response.data], { type: 'application/zip' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      
      // Extract filename from response headers or generate default
      const contentDisposition = response.headers['content-disposition'];
      let filename = 'CQC_Inspection_Pack.zip';
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename=([^;]+)/);
        if (filenameMatch) {
          filename = filenameMatch[1].replace(/"/g, '');
        }
      }
      
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      toast.success('Inspection Pack generated successfully');
    } catch (error) {
      console.error('Failed to generate inspection pack:', error);
      toast.error('Failed to generate Inspection Pack');
    } finally {
      setGeneratingPack(false);
    }
  };

  // Handle assigning policy to employees
  const handleAssignPolicy = async () => {
    if (!policyToAssign || selectedEmployees.length === 0) {
      toast.error('Please select at least one employee');
      return;
    }
    
    setIsAssigning(true);
    try {
      // Create assignments for each selected employee using the policy assignments API
      // Note: We use the policy-assignments endpoint which expects policy_id from employee policies collection
      // But the Compliance Centre uses org_policy_id - need to create linking
      const response = await axios.post(`${API}/policies/assign`, {
        policy_id: policyToAssign.id,
        employee_ids: selectedEmployees
      }, { headers: { Authorization: `Bearer ${token}` } });
      
      toast.success(response.data.message || `Policy assigned to ${selectedEmployees.length} employees`);
      setAssignDialogOpen(false);
      setPolicyToAssign(null);
      setSelectedEmployees([]);
      await fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to assign policy');
    } finally {
      setIsAssigning(false);
    }
  };

  // Toggle employee selection
  const toggleEmployeeSelection = (empId) => {
    setSelectedEmployees(prev => 
      prev.includes(empId) 
        ? prev.filter(id => id !== empId)
        : [...prev, empId]
    );
  };

  const toggleMeetingAttendeeSelection = (employeeId) => {
    setNewStaffMeeting(prev => ({
      ...prev,
      employee_ids: prev.employee_ids.includes(employeeId)
        ? prev.employee_ids.filter(id => id !== employeeId)
        : [...prev.employee_ids, employeeId]
    }));
  };

  // Select all unassigned employees
  const selectAllUnassigned = () => {
    if (!policyToAssign) return;
    const alreadyAssigned = policyAssignments
      .filter(a => a.policy_id === policyToAssign.id && !['unassigned', 'withdrawn'].includes(a.status))
      .map(a => a.employee_id);
    const unassigned = employees.filter(e => !alreadyAssigned.includes(e.id)).map(e => e.id);
    setSelectedEmployees(unassigned);
  };

  // Get assignment count for a policy
  const getAssignmentStats = (policyId) => {
    const assignments = policyAssignments.filter(a => a.policy_id === policyId && !['unassigned', 'withdrawn'].includes(a.status));
    const total = assignments.length;
    const acknowledged = assignments.filter(a => a.status === 'acknowledged' || a.status === 'signed').length;
    return { total, acknowledged };
  };

  const getPolicyAssignmentTriage = (policyId) => {
    const assignments = policyAssignments.filter(a => a.policy_id === policyId && !['unassigned', 'withdrawn'].includes(a.status));
    return {
      total: assignments.length,
      pendingAcknowledgement: assignments.filter(a => ['assigned', 'viewed'].includes(a.status)).length,
      awaitingAdminReview: assignments.filter(a => ['acknowledged', 'signed'].includes(a.status) && !a.admin_reviewed).length,
      reviewed: assignments.filter(a => a.admin_reviewed).length,
    };
  };

  const handleUploadPolicy = async (e) => {
    e.preventDefault();
    if (!uploadFile || !selectedPolicy) return;
    
    setIsUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', uploadFile);
      
      let url = `${API}/compliance/policies/${selectedPolicy.id}/upload`;
      const params = new URLSearchParams();
      if (uploadVersion) params.append('version', uploadVersion);
      if (uploadReviewDate) params.append('review_date', uploadReviewDate);
      if (params.toString()) url += `?${params.toString()}`;
      
      await axios.post(url, formData, {
        headers: { 
          Authorization: `Bearer ${token}`,
          'Content-Type': 'multipart/form-data'
        }
      });
      
      toast.success('Policy document uploaded');
      setUploadDialogOpen(false);
      resetUploadForm();
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to upload policy');
    } finally {
      setIsUploading(false);
    }
  };

  const handleUploadInsurance = async (e) => {
    e.preventDefault();
    if (!uploadFile || !selectedInsurance) return;
    
    // Check if expiry is required for this certificate type
    const requiresExpiry = selectedInsurance.requires_expiry_date !== false;
    if (requiresExpiry && !uploadExpiryDate) {
      toast.error('Expiry date is required for this certificate type');
      return;
    }
    
    setIsUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', uploadFile);
      
      // Build URL with optional expiry date
      let url = `${API}/compliance/insurance/${selectedInsurance.id}/upload`;
      const params = new URLSearchParams();
      if (uploadExpiryDate) params.append('expiry_date', uploadExpiryDate);
      if (uploadPolicyNumber) params.append('policy_number', uploadPolicyNumber);
      if (uploadProvider) params.append('provider', uploadProvider);
      if (params.toString()) url += `?${params.toString()}`;
      
      await axios.post(url, formData, {
        headers: { 
          Authorization: `Bearer ${token}`,
          'Content-Type': 'multipart/form-data'
        }
      });
      
      toast.success('Certificate uploaded successfully');
      setUploadDialogOpen(false);
      resetUploadForm();
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to upload certificate');
    } finally {
      setIsUploading(false);
    }
  };

  const handleCreateIncident = async (e) => {
    e.preventDefault();
    if (newIncident.is_reportable) {
      if (!newIncident.report_category?.trim()) {
        toast.error('Report category is required when incident is marked reportable');
        return;
      }
      if (!newIncident.report_notes?.trim()) {
        toast.error('Report notes are required when incident is marked reportable');
        return;
      }
      if (newIncident.reported_to_authority && (!newIncident.reported_at || !newIncident.report_reference?.trim())) {
        toast.error('Reported date and reference are required when marked as reported to authority');
        return;
      }
    }
    setIsSubmitting(true);
    
    try {
      await axios.post(`${API}/compliance/incidents`, newIncident, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      toast.success('Incident report created');
      setIncidentDialogOpen(false);
      setNewIncident({
        incident_type: 'incident',
        title: '',
        description: '',
        date_occurred: new Date().toISOString().split('T')[0],
        location: '',
        persons_involved: '',
        immediate_actions: '',
        root_cause: '',
        corrective_actions: '',
        is_reportable: false,
        report_category: '',
        reported_to_authority: false,
        reported_at: '',
        report_reference: '',
        report_notes: ''
      });
      fetchData();
    } catch (error) {
      toast.error('Failed to create incident report');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCreateStaffMeeting = async (e) => {
    e.preventDefault();
    if (!newStaffMeeting.meeting_date || !newStaffMeeting.meeting_type || !newStaffMeeting.agenda || !newStaffMeeting.notes) {
      toast.error('Meeting date, type, agenda and notes are required');
      return;
    }

    setIsSubmittingMeeting(true);
    try {
      await axios.post(`${API}/compliance/staff-meetings`, newStaffMeeting, {
        headers: { Authorization: `Bearer ${token}` }
      });

      toast.success('Staff meeting record created');
      setStaffMeetingDialogOpen(false);
      setNewStaffMeeting({
        meeting_date: new Date().toISOString().split('T')[0],
        meeting_type: 'monthly_staff_meeting',
        employee_ids: [],
        agenda: '',
        notes: '',
        actions_required: '',
        next_meeting_date: ''
      });
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create staff meeting record');
    } finally {
      setIsSubmittingMeeting(false);
    }
  };

  const handleCreateEmployerAudit = async (e) => {
    e.preventDefault();
    if (!newEmployerAudit.audit_type || !newEmployerAudit.audit_date || !newEmployerAudit.completed_by || !newEmployerAudit.overall_outcome || !newEmployerAudit.findings) {
      toast.error('Audit type, date, completed by, outcome and findings are required');
      return;
    }

    setIsSubmittingEmployerAudit(true);
    try {
      await axios.post(`${API}/compliance/employer-audits`, newEmployerAudit, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Employer audit record created');
      setEmployerAuditDialogOpen(false);
      setNewEmployerAudit({
        audit_type: 'infection_control_audit',
        audit_date: new Date().toISOString().split('T')[0],
        completed_by: '',
        overall_outcome: 'compliant',
        findings: '',
        actions_required: '',
        next_review_date: '',
        status: 'open'
      });
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create employer audit record');
    } finally {
      setIsSubmittingEmployerAudit(false);
    }
  };

  const fetchReports = async (type) => {
    try {
      if (type === 'dbs' && !dbsReport) {
        const res = await axios.get(`${API}/compliance/reports/staff-dbs`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        setDbsReport(res.data);
      }
      if (type === 'training' && !trainingReport) {
        const res = await axios.get(`${API}/compliance/reports/training?months=12`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        setTrainingReport(res.data);
      }
    } catch (error) {
      toast.error('Failed to generate report');
    }
  };

  const resetUploadForm = () => {
    setSelectedPolicy(null);
    setSelectedInsurance(null);
    setUploadFile(null);
    setUploadVersion('');
    setUploadReviewDate('');
    setUploadExpiryDate('');
    setUploadPolicyNumber('');
    setUploadProvider('');
    setIsReplaceMode(false);
    setReplaceReason('');
  };

  // ==================== DOCUMENT REMOVE/REPLACE HANDLERS ====================
  
  const handleRemoveDocument = async (type, id, name) => {
    setRemoveTarget({ type, id, name });
    setRemoveReason('');
    setRemoveDialogOpen(true);
  };

  const handleConfirmRemoveDocument = async () => {
    if (!removeTarget || !removeReason.trim()) return;

    try {
      const endpoint = removeTarget.type === 'policy' 
        ? `${API}/compliance/policies/${removeTarget.id}/file`
        : `${API}/compliance/insurance/${removeTarget.id}/file`;
      
      await axios.delete(`${endpoint}?reason=${encodeURIComponent(removeReason.trim())}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      toast.success('Document removed successfully');
      setRemoveDialogOpen(false);
      setRemoveTarget(null);
      setRemoveReason('');
      fetchData();
    } catch (error) {
      console.error('Failed to remove document:', error);
      toast.error(error.response?.data?.detail || 'Failed to remove document');
    }
  };

  const handleReplaceDocument = async (e) => {
    e.preventDefault();
    if (!uploadFile) return;
    if (!replaceReason.trim()) {
      toast.error('Please provide a reason for replacing the document');
      return;
    }
    
    setIsUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', uploadFile);
      
      let url, params;
      
      if (selectedPolicy) {
        url = `${API}/compliance/policies/${selectedPolicy.id}/replace`;
        params = new URLSearchParams();
        params.append('reason', replaceReason);
        if (uploadVersion) params.append('version', uploadVersion);
        if (uploadReviewDate) params.append('review_date', uploadReviewDate);
      } else if (selectedInsurance) {
        // Check if expiry is required
        const requiresExpiry = selectedInsurance.requires_expiry_date !== false;
        if (requiresExpiry && !uploadExpiryDate) {
          toast.error('Expiry date is required for this certificate type');
          setIsUploading(false);
          return;
        }
        
        url = `${API}/compliance/insurance/${selectedInsurance.id}/replace`;
        params = new URLSearchParams();
        params.append('reason', replaceReason);
        if (uploadExpiryDate) params.append('expiry_date', uploadExpiryDate);
        if (uploadPolicyNumber) params.append('policy_number', uploadPolicyNumber);
        if (uploadProvider) params.append('provider', uploadProvider);
      }
      
      url += `?${params.toString()}`;
      
      await axios.post(url, formData, {
        headers: { 
          Authorization: `Bearer ${token}`,
          'Content-Type': 'multipart/form-data'
        }
      });
      
      toast.success('Document replaced successfully');
      setUploadDialogOpen(false);
      resetUploadForm();
      fetchData();
    } catch (error) {
      console.error('Failed to replace document:', error);
      toast.error(error.response?.data?.detail || 'Failed to replace document');
    } finally {
      setIsUploading(false);
    }
  };

  // ==================== AMENDMENT HANDLERS ====================
  
  // Open amendment dialog with record data
  const openAmendDialog = (type, record) => {
    setAmendType(type);
    setAmendRecord(record);
    
    // Pre-populate form based on type
    if (type === 'policy') {
      setAmendForm({
        name: record.name || '',
        category: record.category || '',
        version: record.version || '',
        review_date: record.review_date ? record.review_date.split('T')[0] : '',
        notes: record.notes || '',
        reason: ''
      });
    } else if (type === 'insurance') {
      setAmendForm({
        name: record.name || '',
        expiry_date: record.expiry_date ? record.expiry_date.split('T')[0] : '',
        policy_number: record.policy_number || '',
        provider: record.provider || '',
        notes: record.notes || '',
        reason: ''
      });
    } else if (type === 'incident') {
      setAmendForm({
        title: record.title || '',
        description: record.description || '',
        incident_type: record.incident_type || 'incident',
        status: record.status || 'open',
        action_taken: record.action_taken || '',
        date_occurred: record.date_occurred ? record.date_occurred.split('T')[0] : '',
        location: record.location || '',
        people_involved: record.people_involved || record.persons_involved || '',
        persons_involved: record.persons_involved || '',
        witnesses: record.witnesses || '',
        immediate_actions_taken: record.immediate_actions_taken || record.immediate_actions || '',
        immediate_actions: record.immediate_actions || '',
        injury_or_harm: record.injury_or_harm || '',
        safeguarding_concern: !!record.safeguarding_concern,
        escalation_required: !!record.escalation_required,
        escalation_details: record.escalation_details || '',
        learning_outcome: record.learning_outcome || record.lessons_learned || '',
        prevention_actions: record.prevention_actions || record.corrective_actions || '',
        root_cause: record.root_cause || '',
        corrective_actions: record.corrective_actions || '',
        lessons_learned: record.lessons_learned || '',
        is_reportable: !!record.is_reportable,
        report_category: record.report_category || '',
        reported_to_authority: !!record.reported_to_authority,
        reported_at: record.reported_at ? record.reported_at.split('T')[0] : '',
        report_reference: record.report_reference || '',
        report_notes: record.report_notes || '',
        reason: ''
      });
    } else if (type === 'meeting') {
      setAmendForm({
        meeting_date: record.meeting_date ? record.meeting_date.split('T')[0] : '',
        meeting_type: record.meeting_type || 'monthly_staff_meeting',
        employee_ids: Array.isArray(record.employee_ids) ? record.employee_ids : [],
        agenda: record.agenda || '',
        notes: record.notes || '',
        actions_required: record.actions_required || '',
        next_meeting_date: record.next_meeting_date ? record.next_meeting_date.split('T')[0] : '',
        actions_status: record.actions_status || 'open',
        reason: ''
      });
    } else if (type === 'audit') {
      setAmendForm({
        audit_type: record.audit_type || 'infection_control_audit',
        audit_date: record.audit_date ? record.audit_date.split('T')[0] : '',
        completed_by: record.completed_by || '',
        overall_outcome: record.overall_outcome || 'compliant',
        findings: record.findings || '',
        actions_required: record.actions_required || '',
        next_review_date: record.next_review_date ? record.next_review_date.split('T')[0] : '',
        status: record.status || 'open',
        reason: ''
      });
    }
    
    setAmendDialogOpen(true);
  };
  
  // Submit amendment
  const handleAmendSubmit = async () => {
    if (!amendForm.reason || amendForm.reason.trim().length < 3) {
      toast.error('Please provide a reason for this change (min 3 characters)');
      return;
    }
    if (amendType === 'incident' && amendForm.is_reportable) {
      if (!amendForm.report_category?.trim()) {
        toast.error('Report category is required when incident is marked reportable');
        return;
      }
      if (!amendForm.report_notes?.trim()) {
        toast.error('Report notes are required when incident is marked reportable');
        return;
      }
      if (amendForm.reported_to_authority && (!amendForm.reported_at || !amendForm.report_reference?.trim())) {
        toast.error('Reported date and reference are required when marked as reported to authority');
        return;
      }
    }
    
    setIsAmending(true);
    try {
      const endpoint = amendType === 'policy' 
        ? `${API}/compliance/policies/${amendRecord.id}/amend`
        : amendType === 'insurance'
        ? `${API}/compliance/insurance/${amendRecord.id}/amend`
        : amendType === 'incident'
        ? `${API}/compliance/incidents/${amendRecord.id}/amend`
        : amendType === 'meeting'
        ? `${API}/compliance/staff-meetings/${amendRecord.id}/amend`
        : `${API}/compliance/employer-audits/${amendRecord.id}/amend`;
      
      await axios.put(endpoint, amendForm, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      toast.success(`${amendType.charAt(0).toUpperCase() + amendType.slice(1)} updated successfully`);
      setAmendDialogOpen(false);
      setAmendRecord(null);
      setAmendForm({});
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || `Failed to update ${amendType}`);
    } finally {
      setIsAmending(false);
    }
  };
  
  // Load amendment history
  const loadHistory = async (type, recordId) => {
    setHistoryType(type);
    setHistoryRecordId(recordId);
    setIsLoadingHistory(true);
    setHistoryDialogOpen(true);
    
    try {
      const endpoint = type === 'policy' 
        ? `${API}/compliance/policies/${recordId}/history`
        : type === 'insurance'
        ? `${API}/compliance/insurance/${recordId}/history`
        : type === 'incident'
        ? `${API}/compliance/incidents/${recordId}/history`
        : type === 'meeting'
        ? `${API}/compliance/staff-meetings/${recordId}/history`
        : `${API}/compliance/employer-audits/${recordId}/history`;
      
      const response = await axios.get(endpoint, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      setHistoryData(response.data.history || []);
    } catch (error) {
      toast.error('Failed to load history');
      setHistoryData([]);
    } finally {
      setIsLoadingHistory(false);
    }
  };

  const getStatusBadge = (status) => {
    const config = {
      active: { bg: 'bg-success/10', text: 'text-success', icon: CheckCircle },
      valid: { bg: 'bg-success/10', text: 'text-success', icon: CheckCircle },
      missing: { bg: 'bg-error/10', text: 'text-error', icon: XCircle },
      expired: { bg: 'bg-error/10', text: 'text-error', icon: AlertTriangle },
      expiring_soon: { bg: 'bg-warning/10', text: 'text-warning', icon: Clock },
      under_review: { bg: 'bg-info/10', text: 'text-info', icon: Clock },
      reviewing: { bg: 'bg-info/10', text: 'text-info', icon: Clock },
      open: { bg: 'bg-error/10', text: 'text-error', icon: AlertCircle },
      investigating: { bg: 'bg-warning/10', text: 'text-warning', icon: Search },
      resolved: { bg: 'bg-info/10', text: 'text-info', icon: CheckCircle },
      closed: { bg: 'bg-success/10', text: 'text-success', icon: CheckCircle }
    };
    const c = config[status] || config.missing;
    const Icon = c.icon;
    
    return (
      <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${c.bg} ${c.text}`}>
        <Icon className="h-3 w-3" />
        {status.replace('_', ' ')}
      </span>
    );
  };

  const getFollowUpStatusBadge = (status, dueDate) => {
    const normalized = String(status || '').trim().toLowerCase();
    if (!normalized) return null;

    const due = parseBackendDate(dueDate);
    const isOverdue = normalized === 'open' && due instanceof Date && !Number.isNaN(due.getTime()) && due < new Date();
    const effective = normalized === 'closed' ? 'closed' : (isOverdue ? 'overdue' : 'open');

    const config = {
      open: { bg: 'bg-amber-100', text: 'text-amber-700', icon: Clock, label: 'open' },
      overdue: { bg: 'bg-red-100', text: 'text-red-700', icon: AlertTriangle, label: 'overdue' },
      closed: { bg: 'bg-green-100', text: 'text-green-700', icon: CheckCircle, label: 'closed' }
    };

    const c = config[effective] || config.open;
    const Icon = c.icon;

    return (
      <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium ${c.bg} ${c.text}`}>
        <Icon className="h-3 w-3" />
        Follow-up: {c.label}
      </span>
    );
  };

  const groupedPolicies = policies.reduce((acc, policy) => {
    if (!acc[policy.category]) acc[policy.category] = [];
    acc[policy.category].push(policy);
    return acc;
  }, {});

  const certificateBuckets = {
    missing: insurance.filter((item) => item.status === 'missing'),
    expired: insurance.filter((item) => item.status === 'expired'),
    expiringSoon: insurance.filter((item) => item.status === 'expiring_soon'),
    valid: insurance.filter((item) => item.status === 'valid')
  };

  const certificateStatusPriority = {
    expired: 0,
    missing: 1,
    expiring_soon: 2,
    under_review: 3,
    valid: 4
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="compliance-centre">
      {serviceUserIdFilter && (
        <div className="flex items-center justify-between rounded-lg border border-blue-200 bg-blue-50 px-3 py-2">
          <span className="text-sm text-blue-700 font-medium">Filtered by service user</span>
          <Button
            variant="outline"
            size="sm"
            className="h-7 border-blue-200 text-blue-700 hover:bg-blue-100"
            onClick={() => {
              const next = { tab: activeTab };
              setSearchParams(next, { replace: true });
            }}
          >
            Clear filter
          </Button>
        </div>
      )}

      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="font-heading text-2xl font-bold text-text-primary">Compliance Centre</h1>
          <p className="text-text-muted">Organisation-level compliance management for CQC readiness</p>
        </div>
        
        {isAdmin() && policies.length === 0 && (
          <Button onClick={handleSeedPolicies} className="bg-primary hover:bg-primary-hover text-white rounded-xl">
            <Plus className="h-4 w-4 mr-2" />
            Initialize Compliance Items
          </Button>
        )}
      </div>

      {/* CQC Compliance Summary */}
      {centreSummary && (
        <div className="space-y-4">
          {/* Overall Status Banner */}
          <Card className={`border-l-4 shadow-sm ${
            centreSummary.overall_status === 'OK' 
              ? 'border-l-success bg-success/5' 
              : centreSummary.overall_status === 'Critical'
              ? 'border-l-error bg-error/5'
              : 'border-l-warning bg-warning/5'
          }`}>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  {centreSummary.overall_status === 'OK' ? (
                    <CheckCircle className="h-8 w-8 text-success" />
                  ) : centreSummary.overall_status === 'Critical' ? (
                    <XCircle className="h-8 w-8 text-error" />
                  ) : (
                    <AlertTriangle className="h-8 w-8 text-warning" />
                  )}
                  <div>
                    <h2 className="font-heading text-lg font-bold">
                      {centreSummary.overall_status === 'OK' 
                        ? 'CQC Compliance: All Clear' 
                        : centreSummary.overall_status === 'Critical'
                        ? 'CQC Compliance: Critical Issues'
                        : 'CQC Compliance: Needs Attention'}
                    </h2>
                    <p className="text-sm text-text-muted">
                      {centreSummary.overall_status === 'OK' 
                        ? 'All required policies and certificates are in place'
                        : `${centreSummary.missing_items.required_policies.length + centreSummary.missing_items.required_certificates.length} required items missing`}
                    </p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
          
          {/* Summary Cards */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Policies */}
            <Card className="border-[#E4E8EB] shadow-sm">
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-lg ${
                    centreSummary.policies.missing === 0 ? 'bg-success/10' : 'bg-error/10'
                  }`}>
                    <FileText className={`h-5 w-5 ${
                      centreSummary.policies.missing === 0 ? 'text-success' : 'text-error'
                    }`} />
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-text-primary">
                      {centreSummary.policies.complete}/{centreSummary.policies.total}
                    </p>
                    <p className="text-xs text-text-muted">Policies Active</p>
                    {centreSummary.policies.overdue > 0 && (
                      <p className="text-[10px] text-error font-medium">{centreSummary.policies.overdue} overdue review</p>
                    )}
                    {centreSummary.policies.due_soon > 0 && centreSummary.policies.overdue === 0 && (
                      <p className="text-[10px] text-warning font-medium">{centreSummary.policies.due_soon} due for review</p>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
            
            {/* Certificates */}
            <Card className="border-[#E4E8EB] shadow-sm">
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-lg ${
                    centreSummary.certificates.missing === 0 && centreSummary.certificates.expired === 0 
                      ? 'bg-success/10' 
                      : 'bg-error/10'
                  }`}>
                    <Shield className={`h-5 w-5 ${
                      centreSummary.certificates.missing === 0 && centreSummary.certificates.expired === 0
                        ? 'text-success' 
                        : 'text-error'
                    }`} />
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-text-primary">
                      {centreSummary.certificates.valid}/{centreSummary.certificates.total}
                    </p>
                    <p className="text-xs text-text-muted">Certificates Valid</p>
                    {centreSummary.certificates.expired > 0 && (
                      <p className="text-[10px] text-error font-medium">{centreSummary.certificates.expired} expired</p>
                    )}
                    {centreSummary.certificates.expiring > 0 && centreSummary.certificates.expired === 0 && (
                      <p className="text-[10px] text-warning font-medium">{centreSummary.certificates.expiring} expiring soon</p>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
            
            {/* Staff Compliance - DBS */}
            <Card className="border-[#E4E8EB] shadow-sm">
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-lg ${
                    centreSummary.staff_compliance.dbs_missing === 0 ? 'bg-success/10' : 'bg-error/10'
                  }`}>
                    <Users className={`h-5 w-5 ${
                      centreSummary.staff_compliance.dbs_missing === 0 ? 'text-success' : 'text-error'
                    }`} />
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-text-primary">
                      {centreSummary.staff_compliance.dbs_valid}/{centreSummary.staff_compliance.total}
                    </p>
                    <p className="text-xs text-text-muted">Staff DBS Valid</p>
                    {centreSummary.staff_compliance.dbs_missing > 0 && (
                      <p className="text-[10px] text-error font-medium">{centreSummary.staff_compliance.dbs_missing} missing DBS</p>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
            
            {/* Staff Training */}
            <Card className="border-[#E4E8EB] shadow-sm">
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-info/10">
                    <BookOpen className="h-5 w-5 text-info" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-text-primary">
                      {centreSummary.staff_compliance.training_last_12_months}/{centreSummary.staff_compliance.total}
                    </p>
                    <p className="text-xs text-text-muted">Training (12 months)</p>
                    <p className="text-[10px] text-text-muted">Staff with recent training</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
          
          {/* Missing Required Items Panel */}
          {(centreSummary.missing_items.required_policies.length > 0 || 
            centreSummary.missing_items.required_certificates.length > 0) && (
            <Card className="border-error/30 bg-error/5 shadow-sm">
              <CardHeader className="pb-2">
                <CardTitle className="font-heading text-base text-error flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4" />
                  Required Items Missing
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid md:grid-cols-2 gap-4">
                  {centreSummary.missing_items.required_policies.length > 0 && (
                    <div>
                      <h4 className="font-medium text-sm mb-2">Policies</h4>
                      <ul className="space-y-1">
                        {centreSummary.missing_items.required_policies.slice(0, 5).map((item, idx) => (
                          <li key={idx} className="text-sm flex items-center gap-2">
                            <XCircle className="h-3 w-3 text-error flex-shrink-0" />
                            <span>{item.name}</span>
                            <span className="text-[10px] px-1.5 py-0.5 bg-error/20 text-error rounded">REQUIRED</span>
                          </li>
                        ))}
                        {centreSummary.missing_items.required_policies.length > 5 && (
                          <li className="text-xs text-text-muted">
                            +{centreSummary.missing_items.required_policies.length - 5} more
                          </li>
                        )}
                      </ul>
                    </div>
                  )}
                  {centreSummary.missing_items.required_certificates.length > 0 && (
                    <div>
                      <h4 className="font-medium text-sm mb-2">Certificates</h4>
                      <ul className="space-y-1">
                        {centreSummary.missing_items.required_certificates.slice(0, 5).map((item, idx) => (
                          <li key={idx} className="text-sm flex items-center gap-2">
                            <XCircle className="h-3 w-3 text-error flex-shrink-0" />
                            <span>{item.name}</span>
                            <span className="text-[10px] px-1.5 py-0.5 bg-error/20 text-error rounded">REQUIRED</span>
                          </li>
                        ))}
                        {centreSummary.missing_items.required_certificates.length > 5 && (
                          <li className="text-xs text-text-muted">
                            +{centreSummary.missing_items.required_certificates.length - 5} more
                          </li>
                        )}
                      </ul>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={handleTabChange} className="space-y-6">
        <TabsList className="bg-white border border-[#E4E8EB] p-1 rounded-xl flex-wrap">
          <TabsTrigger value="policies" className="rounded-lg data-[state=active]:bg-primary data-[state=active]:text-white" data-testid="tab-policies">
            <FileText className="h-4 w-4 mr-2" />
            Policies
          </TabsTrigger>
          {isAdmin() && (
            <TabsTrigger value="certificates" className="rounded-lg data-[state=active]:bg-primary data-[state=active]:text-white" data-testid="tab-certificates">
              <Shield className="h-4 w-4 mr-2" />
              Certificates
            </TabsTrigger>
          )}
          <TabsTrigger value="staff" className="rounded-lg data-[state=active]:bg-primary data-[state=active]:text-white" data-testid="tab-staff">
            <Users className="h-4 w-4 mr-2" />
            Staff Compliance
          </TabsTrigger>
          <TabsTrigger value="incidents" className="rounded-lg data-[state=active]:bg-primary data-[state=active]:text-white" data-testid="tab-incidents">
            <AlertCircle className="h-4 w-4 mr-2" />
            Incidents
          </TabsTrigger>
          <TabsTrigger value="staff-meetings" className="rounded-lg data-[state=active]:bg-primary data-[state=active]:text-white" data-testid="tab-staff-meetings">
            <ClipboardList className="h-4 w-4 mr-2" />
            Staff Meetings
          </TabsTrigger>
          <TabsTrigger value="employer-audits" className="rounded-lg data-[state=active]:bg-primary data-[state=active]:text-white" data-testid="tab-employer-audits">
            <CheckCircle className="h-4 w-4 mr-2" />
            Employer Audits
          </TabsTrigger>
          <TabsTrigger 
            value="reports" 
            className="rounded-lg data-[state=active]:bg-primary data-[state=active]:text-white"
            onClick={() => fetchReports('dbs')}
            data-testid="tab-reports"
          >
            <TrendingUp className="h-4 w-4 mr-2" />
            Insights
          </TabsTrigger>
          <TabsTrigger 
            value="cqc-view" 
            className="rounded-lg data-[state=active]:bg-primary data-[state=active]:text-white"
            onClick={() => fetchCqcEvidenceMap()}
            data-testid="tab-cqc-view"
          >
            <Eye className="h-4 w-4 mr-2" />
            CQC View
          </TabsTrigger>
        </TabsList>

        {/* Policies Tab */}
        <TabsContent value="policies">
          <Card className="border-[#E4E8EB] shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="font-heading text-lg">Organisation Policies</CardTitle>
                <p className="text-sm text-text-muted mt-1">
                  Upload and manage your organisation's policies here. Assign them to employees once uploaded.
                </p>
                <p className="text-xs text-text-muted mt-1">
                  {policies.filter(p => p.status === 'active').length} of {policies.length} policies uploaded
                </p>
              </div>
              {isAdmin() && policies.length > 0 && policies.some(p => p.status === 'missing') && (
                <div className="flex items-center gap-2 text-sm text-warning bg-warning/10 px-3 py-1.5 rounded-lg">
                  <AlertTriangle className="h-4 w-4" />
                  {policies.filter(p => p.status === 'missing').length} policies missing
                </div>
              )}
            </CardHeader>
            <CardContent>
              {policies.length === 0 ? (
                <div className="text-center py-12">
                  <FileText className="h-12 w-12 mx-auto text-text-muted/50 mb-3" />
                  <p className="text-text-muted">No policies configured</p>
                  {isAdmin() && (
                    <Button onClick={handleSeedPolicies} className="mt-4 rounded-xl">
                      Initialize Core Policies
                    </Button>
                  )}
                </div>
              ) : (
                <div className="space-y-8">
                  {['Core', 'Clinical', 'Operational', 'Governance'].map((category) => {
                    const categoryPolicies = groupedPolicies[category] || [];
                    if (categoryPolicies.length === 0) return null;
                    
                    const activeCount = categoryPolicies.filter(p => p.status === 'active').length;
                    const missingCount = categoryPolicies.filter(p => p.status === 'missing').length;
                    const expiringCount = categoryPolicies.filter(p => p.status === 'expired' || p.status === 'under_review').length;
                    
                    const categoryColors = {
                      'Core': 'bg-primary',
                      'Clinical': 'bg-info',
                      'Operational': 'bg-warning',
                      'Governance': 'bg-success'
                    };
                    
                    return (
                      <div key={category} data-testid={`policy-category-${category.toLowerCase()}`}>
                        <div className="flex items-center justify-between mb-4">
                          <div className="flex items-center gap-3">
                            <div className={`w-1 h-8 rounded-full ${categoryColors[category]}`}></div>
                            <div>
                              <h3 className="font-semibold text-text-primary">{category}</h3>
                              <p className="text-xs text-text-muted">
                                {activeCount}/{categoryPolicies.length} uploaded
                                {missingCount > 0 && <span className="text-error ml-2">• {missingCount} missing</span>}
                                {expiringCount > 0 && <span className="text-warning ml-2">• {expiringCount} expiring</span>}
                              </p>
                            </div>
                          </div>
                        </div>
                        <div className="space-y-2 ml-4">
                          {categoryPolicies.map((policy) => (
                            <div 
                              key={policy.id}
                              className={`flex items-center justify-between p-4 bg-[#F8FAFA] rounded-xl border transition-colors ${
                                policy.review_status === 'overdue' 
                                  ? 'border-error/50 bg-error/5' 
                                  : policy.review_status === 'due_soon'
                                  ? 'border-warning/50 bg-warning/5'
                                  : 'border-[#E4E8EB] hover:border-primary/30'
                              }`}
                              data-testid={`policy-${policy.id}`}
                            >
                              <div className="flex items-center gap-4">
                                <div className={`p-2 rounded-lg ${policy.status === 'active' ? 'bg-success/10' : 'bg-error/10'}`}>
                                  <FileText className={`h-5 w-5 ${policy.status === 'active' ? 'text-success' : 'text-error'}`} />
                                </div>
                                <div>
                                  <div className="flex items-center gap-2">
                                    <p className="font-medium text-text-primary">{policy.name}</p>
                                    {/* Required/Conditional Tags */}
                                    {policy.required !== false && (
                                      <span className="text-[9px] px-1.5 py-0.5 bg-error/20 text-error rounded font-medium">
                                        REQUIRED
                                      </span>
                                    )}
                                    {policy.conditional && (
                                      <span className="text-[9px] px-1.5 py-0.5 bg-warning/20 text-warning rounded font-medium">
                                        CONDITIONAL
                                      </span>
                                    )}
                                    {/* Review Status */}
                                    {policy.review_status === 'overdue' && (
                                      <span className="text-[9px] px-1.5 py-0.5 bg-error text-white rounded font-medium">
                                        REVIEW OVERDUE
                                      </span>
                                    )}
                                    {policy.review_status === 'due_soon' && (
                                      <span className="text-[9px] px-1.5 py-0.5 bg-warning text-white rounded font-medium">
                                        REVIEW DUE
                                      </span>
                                    )}
                                  </div>
                                  <div className="flex items-center gap-3 text-xs text-text-muted mt-1">
                                    <span>Version: {policy.version}</span>
                                    {policy.review_date && (
                                      <span className={`flex items-center gap-1 ${
                                        policy.review_status === 'overdue' ? 'text-error' : 
                                        policy.review_status === 'due_soon' ? 'text-warning' : ''
                                      }`}>
                                        <Calendar className="h-3 w-3" />
                                        Next review: {formatBackendDate(policy.review_date)}
                                      </span>
                                    )}
                                    {policy.last_reviewed_at && (
                                      <span className="flex items-center gap-1 text-success">
                                        <CheckCircle className="h-3 w-3" />
                                        Last: {formatBackendDate(policy.last_reviewed_at)}
                                      </span>
                                    )}
                                    {policy.assigned_staff_count > 0 && (
                                      <span className="flex items-center gap-1">
                                        <Users className="h-3 w-3" />
                                        {policy.assigned_staff_count} assigned
                                      </span>
                                    )}
                                  </div>
                                </div>
                              </div>
                              
                              <div className="flex items-center gap-3">
                                {getStatusBadge(policy.status)}
                                
                                {policy.file_url ? (
                                  <div className="flex items-center gap-2">
                                    <Button 
                                      variant="outline" 
                                      size="sm"
                                      className="rounded-lg"
                                      onClick={() => handleViewDocument('policy', policy.id, policy.name, policy.original_filename)}
                                      data-testid={`view-policy-${policy.id}`}
                                    >
                                      <Eye className="h-4 w-4 mr-1" />
                                      View
                                    </Button>
                                    <Button 
                                      variant="outline" 
                                      size="sm"
                                      className="rounded-lg"
                                      onClick={() => handleDownloadDocument('policy', policy.id, policy.original_filename || `${policy.name}.pdf`)}
                                      data-testid={`download-policy-${policy.id}`}
                                    >
                                      <Download className="h-4 w-4 mr-1" />
                                      Download
                                    </Button>
                                    {isAdmin() && (
                                      <>
                                        <Button 
                                          size="sm"
                                          variant="outline"
                                          className="rounded-lg"
                                          onClick={() => openAmendDialog('policy', policy)}
                                          data-testid={`edit-policy-${policy.id}`}
                                        >
                                          <Edit className="h-4 w-4 mr-1" />
                                          Edit
                                        </Button>
                                        <Button 
                                          size="sm"
                                          variant="ghost"
                                          className="rounded-lg text-text-muted hover:text-text-primary"
                                          onClick={() => loadHistory('policy', policy.id)}
                                          data-testid={`history-policy-${policy.id}`}
                                          title="View amendment history"
                                        >
                                          <History className="h-4 w-4" />
                                        </Button>
                                        <Button 
                                          size="sm"
                                          variant="outline"
                                          className="rounded-lg text-primary border-primary/30 hover:bg-primary/5"
                                          onClick={() => {
                                            setSelectedPolicy(policy);
                                            setSelectedInsurance(null);
                                            setIsReplaceMode(true);
                                            setUploadDialogOpen(true);
                                          }}
                                          data-testid={`replace-policy-${policy.id}`}
                                        >
                                          <RefreshCw className="h-4 w-4 mr-1" />
                                          Replace
                                        </Button>
                                        <Button 
                                          variant="ghost" 
                                          size="sm"
                                          className="rounded-lg text-error hover:bg-error/10"
                                          onClick={() => handleRemoveDocument('policy', policy.id, policy.name)}
                                          title="Remove file"
                                          data-testid={`remove-policy-${policy.id}`}
                                        >
                                          <Trash2 className="h-4 w-4" />
                                        </Button>
                                        {/* Assign to Employees Button */}
                                        <Button 
                                          size="sm"
                                          className="bg-primary hover:bg-primary-hover text-white rounded-lg"
                                          onClick={() => {
                                            setPolicyToAssign(policy);
                                            setSelectedEmployees([]);
                                            setAssignDialogOpen(true);
                                          }}
                                          data-testid={`assign-policy-${policy.id}`}
                                        >
                                          <UserPlus className="h-4 w-4 mr-1" />
                                          Assign to Employees
                                          {(() => {
                                            const stats = getAssignmentStats(policy.id);
                                            return stats.total > 0 ? (
                                              <span className="ml-1 text-xs bg-white/20 px-1.5 py-0.5 rounded">
                                                {stats.acknowledged}/{stats.total}
                                              </span>
                                            ) : null;
                                          })()}
                                        </Button>
                                      </>
                                    )}
                                  </div>
                                ) : isAdmin() && (
                                  <div className="flex items-center gap-2">
                                    <Button 
                                      size="sm"
                                      className="bg-primary hover:bg-primary-hover text-white rounded-lg"
                                      onClick={() => {
                                        setSelectedPolicy(policy);
                                        setSelectedInsurance(null);
                                        setUploadDialogOpen(true);
                                      }}
                                    >
                                      <Upload className="h-4 w-4 mr-1" />
                                      Upload
                                    </Button>
                                    {/* Disabled Assign Button - no document yet */}
                                    <Button 
                                      size="sm"
                                      variant="outline"
                                      className="rounded-lg text-text-muted"
                                      disabled
                                      title="Upload policy document before assigning to employees"
                                    >
                                      <UserPlus className="h-4 w-4 mr-1" />
                                      Assign
                                    </Button>
                                  </div>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Certificates Tab (formerly Insurance) */}
        {isAdmin() && <TabsContent value="certificates">
          <Card className="border-[#E4E8EB] shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="font-heading text-lg">Compliance Certificates</CardTitle>
                <p className="text-sm text-text-muted mt-1">
                  Insurance, regulatory, and safety certificates required for CQC compliance
                </p>
                <p className="text-xs text-text-muted mt-1">
                  {certificateBuckets.valid.length} of {insurance.length} certificates valid
                </p>
                <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
                  <span className="inline-flex items-center gap-1 rounded-full bg-success/10 px-2 py-0.5 text-success">
                    Current: {certificateBuckets.valid.length}
                  </span>
                  <span className="inline-flex items-center gap-1 rounded-full bg-warning/10 px-2 py-0.5 text-warning">
                    Expiring soon: {certificateBuckets.expiringSoon.length}
                  </span>
                  <span className="inline-flex items-center gap-1 rounded-full bg-error/10 px-2 py-0.5 text-error">
                    Expired: {certificateBuckets.expired.length}
                  </span>
                  <span className="inline-flex items-center gap-1 rounded-full bg-error/10 px-2 py-0.5 text-error">
                    Missing: {certificateBuckets.missing.length}
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {insurance.some(i => i.status === 'missing' || i.status === 'expired') && (
                  <div className="flex items-center gap-2 text-sm text-error bg-error/10 px-3 py-1.5 rounded-lg">
                    <AlertTriangle className="h-4 w-4" />
                    {insurance.filter(i => i.status === 'missing' || i.status === 'expired').length} require attention
                  </div>
                )}
                <Button
                  onClick={() => setCreateCertDialogOpen(true)}
                  className="rounded-xl"
                  data-testid="add-certificate-record"
                >
                  <Plus className="h-4 w-4 mr-2" />
                  Add Certificate/Check
                </Button>
                </div>
            </CardHeader>
            <CardContent>
              {insurance.length === 0 ? (
                <div className="text-center py-12">
                  <Shield className="h-12 w-12 mx-auto text-text-muted/50 mb-3" />
                  <p className="text-text-muted">No certificates configured</p>
                  {isAdmin() && (
                    <Button 
                      onClick={async () => {
                        try {
                          await axios.post(`${API}/compliance/seed-insurance`, {}, {
                            headers: { Authorization: `Bearer ${token}` }
                          });
                          toast.success('Certificate types initialized');
                          fetchData();
                        } catch (error) {
                          toast.error('Failed to initialize certificates');
                        }
                      }} 
                      className="mt-4 rounded-xl"
                    >
                      Initialize Certificates
                    </Button>
                  )}
                </div>
              ) : (
                <div className="space-y-6">
                  {(certificateBuckets.expired.length > 0 || certificateBuckets.missing.length > 0 || certificateBuckets.expiringSoon.length > 0) && (
                    <div className="rounded-xl border border-warning/30 bg-warning/5 p-4">
                      <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
                        <div>
                          <p className="text-sm font-semibold text-text-primary">Operational attention buckets</p>
                          <p className="text-xs text-text-muted">Use the row actions below to upload missing files or replace renewed certificates.</p>
                        </div>
                        <div className="text-xs text-text-muted">
                          Priority order: expired, missing, expiring soon
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Group by category */}
                  {['insurance', 'regulatory', 'safety'].map((category) => {
                    const categoryItems = insurance
                      .filter(i => (i.category || 'insurance') === category)
                      .sort((a, b) => {
                        const byStatus = (certificateStatusPriority[a.status] ?? 99) - (certificateStatusPriority[b.status] ?? 99);
                        if (byStatus !== 0) return byStatus;
                        return Number(Boolean(b.required)) - Number(Boolean(a.required));
                      });
                    if (categoryItems.length === 0) return null;
                    
                    const categoryNames = {
                      'insurance': 'Insurance',
                      'regulatory': 'Regulatory Certificates',
                      'safety': 'Safety Certificates'
                    };
                    
                    const categoryColors = {
                      'insurance': 'bg-info',
                      'regulatory': 'bg-primary',
                      'safety': 'bg-warning'
                    };
                    
                    return (
                      <div key={category}>
                        <div className="flex items-center gap-3 mb-3">
                          <div className={`w-1 h-6 rounded-full ${categoryColors[category]}`}></div>
                          <h3 className="font-semibold text-text-primary">{categoryNames[category]}</h3>
                          <span className="text-xs text-text-muted">
                            {categoryItems.filter(i => i.status === 'valid').length}/{categoryItems.length} valid
                          </span>
                        </div>
                        <div className="space-y-2 ml-4">
                          {categoryItems.map((cert) => (
                            <div 
                              key={cert.id}
                              className={`flex items-center justify-between p-4 rounded-xl border transition-colors ${
                                cert.status === 'expired' 
                                  ? 'bg-error/5 border-error/30' 
                                  : cert.status === 'expiring_soon'
                                  ? 'bg-warning/5 border-warning/30'
                                  : 'bg-[#F8FAFA] border-[#E4E8EB] hover:border-primary/30'
                              }`}
                              data-testid={`certificate-${cert.id}`}
                            >
                              <div className="flex items-center gap-4">
                                <div className={`p-2 rounded-lg ${
                                  cert.status === 'valid' ? 'bg-success/10' : 
                                  cert.status === 'expiring_soon' ? 'bg-warning/10' : 'bg-error/10'
                                }`}>
                                  <Shield className={`h-5 w-5 ${
                                    cert.status === 'valid' ? 'text-success' : 
                                    cert.status === 'expiring_soon' ? 'text-warning' : 'text-error'
                                  }`} />
                                </div>
                                <div>
                                  <div className="flex items-center gap-2">
                                    <p className="font-medium text-text-primary">{cert.name}</p>
                                    {cert.required !== false && (
                                      <span className="text-[9px] px-1.5 py-0.5 bg-error/20 text-error rounded font-medium">
                                        REQUIRED
                                      </span>
                                    )}
                                    {cert.conditional && (
                                      <span className="text-[9px] px-1.5 py-0.5 bg-warning/20 text-warning rounded font-medium">
                                        CONDITIONAL
                                      </span>
                                    )}
                                  </div>
                                  <div className="flex items-center gap-3 text-xs text-text-muted mt-1">
                                    {cert.provider && <span>Provider: {cert.provider}</span>}
                                    {cert.policy_number && <span>Ref #: {cert.policy_number}</span>}
                                    {cert.issue_date && (
                                      <span className="flex items-center gap-1">
                                        Issued: {formatBackendDate(cert.issue_date)}
                                      </span>
                                    )}
                                    {cert.expiry_date && (
                                      <span className={`flex items-center gap-1 ${
                                        cert.status === 'expired' ? 'text-error font-medium' :
                                        cert.status === 'expiring_soon' ? 'text-warning font-medium' : ''
                                      }`}>
                                        <Calendar className="h-3 w-3" />
                                        {cert.status === 'expired' ? 'Expired: ' : 'Expires: '}
                                        {formatBackendDate(cert.expiry_date)}
                                      </span>
                                    )}
                                    {cert.renewal_period_months && cert.renewal_period_months > 0 && (
                                      <span className="text-text-muted/70">
                                        Renews: {cert.renewal_period_months === 12 ? 'Annually' : 
                                                 cert.renewal_period_months === 60 ? 'Every 5 years' :
                                                 `Every ${cert.renewal_period_months} months`}
                                      </span>
                                    )}
                                  </div>
                                </div>
                              </div>
                              
                              <div className="flex items-center gap-3">
                                {getStatusBadge(cert.status)}
                                
                                {cert.file_url ? (
                                  <div className="flex items-center gap-2">
                                    <Button 
                                      variant="outline" 
                                      size="sm"
                                      className="rounded-lg"
                                      onClick={() => handleViewDocument('insurance', cert.id, cert.name, cert.original_filename)}
                                      data-testid={`view-certificate-${cert.id}`}
                                    >
                                      <Eye className="h-4 w-4 mr-1" />
                                      View
                                    </Button>
                                    {isAdmin() && (
                                      <>
                                        <Button 
                                          variant="outline" 
                                          size="sm"
                                          className="rounded-lg text-primary border-primary/30 hover:bg-primary/5"
                                          onClick={() => {
                                            setSelectedPolicy(null);
                                            setSelectedInsurance(cert);
                                            setIsReplaceMode(true);
                                            setUploadDialogOpen(true);
                                          }}
                                          data-testid={`replace-certificate-${cert.id}`}
                                        >
                                          <RefreshCw className="h-4 w-4 mr-1" />
                                          Replace / Renew
                                        </Button>
                                        <Button 
                                          variant="outline" 
                                          size="sm"
                                          className="rounded-lg"
                                          onClick={() => openAmendDialog('insurance', cert)}
                                        >
                                          <Edit className="h-4 w-4 mr-1" />
                                          Amend
                                        </Button>
                                        <Button 
                                          variant="ghost" 
                                          size="sm"
                                          className="rounded-lg text-error hover:bg-error/10"
                                          onClick={() => handleRemoveDocument('insurance', cert.id, cert.name)}
                                          title="Remove file"
                                          data-testid={`remove-certificate-${cert.id}`}
                                        >
                                          <Trash2 className="h-4 w-4" />
                                        </Button>
                                        <Button 
                                          variant="ghost" 
                                          size="sm"
                                          className="rounded-lg text-text-muted"
                                          onClick={() => loadHistory('insurance', cert.id)}
                                          title="View history"
                                        >
                                          <History className="h-4 w-4" />
                                        </Button>
                                      </>
                                    )}
                                  </div>
                                ) : isAdmin() && (
                                  <Button 
                                    size="sm"
                                    className="bg-primary hover:bg-primary-hover text-white rounded-lg"
                                    onClick={() => {
                                      setSelectedPolicy(null);
                                      setSelectedInsurance(cert);
                                      setUploadDialogOpen(true);
                                    }}
                                    data-testid={`upload-certificate-${cert.id}`}
                                  >
                                    <Upload className="h-4 w-4 mr-1" />
                                    Upload Now
                                  </Button>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>}
        
        {/* Staff Compliance Tab */}
        <TabsContent value="staff">
          <div className="space-y-6">
            {/* Staff Compliance Summary Cards */}
            <div className="grid md:grid-cols-3 gap-4">
              {/* DBS Register */}
              <Card className="border-[#E4E8EB] shadow-sm">
                <CardHeader className="pb-2">
                  <CardTitle className="font-heading text-base flex items-center gap-2">
                    <Shield className="h-4 w-4 text-primary" />
                    DBS Register Status
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {centreSummary && (
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-text-muted">Valid DBS</span>
                        <span className="font-bold text-success">{centreSummary.staff_compliance.dbs_valid}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-text-muted">Missing DBS</span>
                        <span className={`font-bold ${centreSummary.staff_compliance.dbs_missing > 0 ? 'text-error' : 'text-success'}`}>
                          {centreSummary.staff_compliance.dbs_missing}
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-text-muted">Expiring Soon</span>
                        <span className={`font-bold ${centreSummary.staff_compliance.dbs_expiring > 0 ? 'text-warning' : 'text-success'}`}>
                          {centreSummary.staff_compliance.dbs_expiring}
                        </span>
                      </div>
                      <div className="pt-2 border-t">
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div 
                            className="bg-success h-2 rounded-full" 
                            style={{ 
                              width: `${centreSummary.staff_compliance.total > 0 
                                ? (centreSummary.staff_compliance.dbs_valid / centreSummary.staff_compliance.total) * 100 
                                : 0}%` 
                            }}
                          ></div>
                        </div>
                        <p className="text-xs text-text-muted mt-1">
                          {centreSummary.staff_compliance.dbs_valid}/{centreSummary.staff_compliance.total} staff with valid DBS
                        </p>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
              
              {/* Training Last 12 Months */}
              <Card className="border-[#E4E8EB] shadow-sm">
                <CardHeader className="pb-2">
                  <CardTitle className="font-heading text-base flex items-center gap-2">
                    <BookOpen className="h-4 w-4 text-info" />
                    Training (Last 12 Months)
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {centreSummary && (
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-text-muted">Staff with Training</span>
                        <span className="font-bold text-success">{centreSummary.staff_compliance.training_last_12_months}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-text-muted">No Recent Training</span>
                        <span className={`font-bold ${
                          centreSummary.staff_compliance.total - centreSummary.staff_compliance.training_last_12_months > 0 
                            ? 'text-warning' 
                            : 'text-success'
                        }`}>
                          {centreSummary.staff_compliance.total - centreSummary.staff_compliance.training_last_12_months}
                        </span>
                      </div>
                      <div className="pt-2 border-t">
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div 
                            className="bg-info h-2 rounded-full" 
                            style={{ 
                              width: `${centreSummary.staff_compliance.total > 0 
                                ? (centreSummary.staff_compliance.training_last_12_months / centreSummary.staff_compliance.total) * 100 
                                : 0}%` 
                            }}
                          ></div>
                        </div>
                        <p className="text-xs text-text-muted mt-1">
                          {Math.round((centreSummary.staff_compliance.training_last_12_months / centreSummary.staff_compliance.total) * 100) || 0}% training coverage
                        </p>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
              
              {/* Staff List Completeness */}
              <Card className="border-[#E4E8EB] shadow-sm">
                <CardHeader className="pb-2">
                  <CardTitle className="font-heading text-base flex items-center gap-2">
                    <Users className="h-4 w-4 text-primary" />
                    Staff List Completeness
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {centreSummary && dashboard && (
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-text-muted">Total Active Staff</span>
                        <span className="font-bold">{canonicalStaffReadiness?.total ?? centreSummary.staff_compliance.total}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-text-muted">Work Ready</span>
                        <span className="font-bold text-success">{canonicalStaffReadiness?.workReady ?? dashboard.staff?.work_ready ?? 0}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-text-muted">Not Yet Compliant</span>
                        <span className={`font-bold ${
                          ((canonicalStaffReadiness?.notReady ?? dashboard.staff?.pending_compliance ?? 0) > 0) ? 'text-warning' : 'text-success'
                        }`}>
                          {canonicalStaffReadiness?.notReady ?? dashboard.staff?.pending_compliance ?? (centreSummary.staff_compliance.total - (dashboard.staff?.work_ready || 0))}
                        </span>
                      </div>
                      <div className="pt-2 border-t">
                        <Button
                          variant="outline"
                          size="sm"
                          className="w-full rounded-lg"
                          onClick={() => window.location.href = '/portal/employees'}
                        >
                          View All Staff
                        </Button>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
            
            {/* Staff with Issues Alert */}
            {centreSummary && (centreSummary.staff_compliance.dbs_missing > 0 || centreSummary.staff_compliance.dbs_expiring > 0) && (
              <Card className="border-warning/30 bg-warning/5 shadow-sm">
                <CardHeader className="pb-2">
                  <CardTitle className="font-heading text-base text-warning flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4" />
                    Staff Requiring Attention
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-text-muted">
                    {centreSummary.staff_compliance.dbs_missing > 0 && (
                      <span className="text-error">{centreSummary.staff_compliance.dbs_missing} staff missing DBS checks. </span>
                    )}
                    {centreSummary.staff_compliance.dbs_expiring > 0 && (
                      <span className="text-warning">{centreSummary.staff_compliance.dbs_expiring} DBS checks expiring within 30 days.</span>
                    )}
                  </p>
                  <Button
                    variant="outline"
                    size="sm"
                    className="mt-3 rounded-lg"
                    onClick={() => window.location.href = '/portal/employees?filter=dbs_issues'}
                  >
                    Review Staff
                  </Button>
                </CardContent>
              </Card>
            )}
          </div>
        </TabsContent>

        {/* Incidents Tab */}
        <TabsContent value="incidents">
          <div className="space-y-4">
            {/* Incidents KPI Summary Bar */}
            {(() => {
              const openCount = incidents.filter(i => i.status === 'open' || i.status === 'reviewing' || i.status === 'under_review' || i.status === 'investigating').length;
              const closedCount = incidents.filter(i => i.status === 'closed' || i.status === 'resolved').length;
              const overdueCount = incidents.filter(i => {
                if (i.status === 'closed' || i.status === 'resolved') return false;
                // HARDENING: Use parseBackendDate for safe calculation
                const dateOccurred = parseBackendDate(i.date_occurred);
                if (!dateOccurred) return false;
                const daysOld = Math.ceil((new Date() - dateOccurred) / (1000 * 60 * 60 * 24));
                return daysOld > 7; // Overdue if open for more than 7 days
              }).length;
              
              return (
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                  <Card className="border-amber-200 bg-amber-50/50">
                    <CardContent className="p-4">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-xs text-amber-600 font-medium">Open</p>
                          <p className="text-2xl font-bold text-amber-700">{openCount}</p>
                        </div>
                        <AlertCircle className="h-8 w-8 text-amber-400" />
                      </div>
                    </CardContent>
                  </Card>
                  <Card className="border-green-200 bg-green-50/50">
                    <CardContent className="p-4">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-xs text-green-600 font-medium">Closed</p>
                          <p className="text-2xl font-bold text-green-700">{closedCount}</p>
                        </div>
                        <CheckCircle className="h-8 w-8 text-green-400" />
                      </div>
                    </CardContent>
                  </Card>
                  <Card className={`border-${overdueCount > 0 ? 'red' : 'gray'}-200 bg-${overdueCount > 0 ? 'red' : 'gray'}-50/50`}>
                    <CardContent className="p-4">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className={`text-xs ${overdueCount > 0 ? 'text-red-600' : 'text-gray-600'} font-medium`}>Overdue (&gt;7d)</p>
                          <p className={`text-2xl font-bold ${overdueCount > 0 ? 'text-red-700' : 'text-gray-700'}`}>{overdueCount}</p>
                        </div>
                        <Clock className={`h-8 w-8 ${overdueCount > 0 ? 'text-red-400' : 'text-gray-400'}`} />
                      </div>
                    </CardContent>
                  </Card>
                  <Card className="border-blue-200 bg-blue-50/50">
                    <CardContent className="p-4">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-xs text-blue-600 font-medium">Total</p>
                          <p className="text-2xl font-bold text-blue-700">{incidents.length}</p>
                        </div>
                        <ClipboardList className="h-8 w-8 text-blue-400" />
                      </div>
                    </CardContent>
                  </Card>
                </div>
              );
            })()}
            
            <Card className="border-[#E4E8EB] shadow-sm">
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="font-heading text-lg">Incident & Outbreak Logs</CardTitle>
                <div className="flex items-center gap-3">
                  {/* Filters */}
                  <Select value={incidentFilter.status} onValueChange={(v) => setIncidentFilter({...incidentFilter, status: v})}>
                    <SelectTrigger className="w-32 rounded-lg h-9">
                      <SelectValue placeholder="Status" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Status</SelectItem>
                      <SelectItem value="open">Open</SelectItem>
                      <SelectItem value="reviewing">Reviewing</SelectItem>
                      <SelectItem value="investigating">Investigating</SelectItem>
                      <SelectItem value="resolved">Resolved</SelectItem>
                      <SelectItem value="closed">Closed</SelectItem>
                    </SelectContent>
                  </Select>
                  <Select value={incidentFilter.severity} onValueChange={(v) => setIncidentFilter({...incidentFilter, severity: v})}>
                    <SelectTrigger className="w-32 rounded-lg h-9">
                      <SelectValue placeholder="Type" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Types</SelectItem>
                      <SelectItem value="incident">Incident</SelectItem>
                      <SelectItem value="outbreak">Outbreak</SelectItem>
                      <SelectItem value="near_miss">Near Miss</SelectItem>
                      <SelectItem value="complaint">Complaint</SelectItem>
                    </SelectContent>
                  </Select>
                  
                  <Dialog open={incidentDialogOpen} onOpenChange={setIncidentDialogOpen}>
                    <DialogTrigger asChild>
                      <Button className="bg-primary hover:bg-primary-hover text-white rounded-xl">
                        <Plus className="h-4 w-4 mr-2" />
                        Report Incident
                      </Button>
                    </DialogTrigger>
                <DialogContent className="max-w-2xl w-[95vw] max-h-[90vh] overflow-y-auto">
                  <DialogHeader>
                    <DialogTitle className="font-heading text-lg pr-6">Report Incident/Outbreak</DialogTitle>
                  </DialogHeader>
                  <form onSubmit={handleCreateIncident} className="space-y-4 mt-4">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label>Incident Type *</Label>
                        <Select 
                          value={newIncident.incident_type} 
                          onValueChange={(v) => setNewIncident({...newIncident, incident_type: v})}
                        >
                          <SelectTrigger className="rounded-xl">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="incident">Incident</SelectItem>
                            <SelectItem value="outbreak">Outbreak</SelectItem>
                            <SelectItem value="near_miss">Near Miss</SelectItem>
                            <SelectItem value="complaint">Complaint</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="space-y-2">
                        <Label>Date Occurred *</Label>
                        <Input
                          type="date"
                          value={newIncident.date_occurred}
                          onChange={(e) => setNewIncident({...newIncident, date_occurred: e.target.value})}
                          required
                          className="rounded-xl"
                        />
                      </div>
                    </div>
                    
                    <div className="space-y-2">
                      <Label>Title *</Label>
                      <Input
                        value={newIncident.title}
                        onChange={(e) => setNewIncident({...newIncident, title: e.target.value})}
                        placeholder="Brief title for the incident"
                        required
                        className="rounded-xl"
                      />
                    </div>
                    
                    <div className="space-y-2">
                      <Label>Description *</Label>
                      <Textarea
                        value={newIncident.description}
                        onChange={(e) => setNewIncident({...newIncident, description: e.target.value})}
                        placeholder="Detailed description of what happened"
                        required
                        className="rounded-xl"
                        rows={3}
                      />
                    </div>
                    
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label>Location</Label>
                        <Input
                          value={newIncident.location}
                          onChange={(e) => setNewIncident({...newIncident, location: e.target.value})}
                          placeholder="Where did it occur?"
                          className="rounded-xl"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>Persons Involved</Label>
                        <Input
                          value={newIncident.persons_involved}
                          onChange={(e) => setNewIncident({...newIncident, persons_involved: e.target.value})}
                          placeholder="Names/roles of people involved"
                          className="rounded-xl"
                        />
                      </div>
                    </div>
                    
                    <div className="space-y-2">
                      <Label>Immediate Actions Taken</Label>
                      <Textarea
                        value={newIncident.immediate_actions}
                        onChange={(e) => setNewIncident({...newIncident, immediate_actions: e.target.value})}
                        placeholder="What actions were taken immediately?"
                        className="rounded-xl"
                        rows={2}
                      />
                    </div>
                    
                    <div className="space-y-2">
                      <Label>Root Cause Analysis</Label>
                      <Textarea
                        value={newIncident.root_cause}
                        onChange={(e) => setNewIncident({...newIncident, root_cause: e.target.value})}
                        placeholder="What was the underlying cause?"
                        className="rounded-xl"
                        rows={2}
                      />
                    </div>
                    
                    <div className="space-y-2">
                      <Label>Corrective Actions</Label>
                      <Textarea
                        value={newIncident.corrective_actions}
                        onChange={(e) => setNewIncident({...newIncident, corrective_actions: e.target.value})}
                        placeholder="What steps will be taken to prevent recurrence?"
                        className="rounded-xl"
                        rows={2}
                      />
                    </div>

                    <div className="space-y-3 rounded-xl border border-[#E4E8EB] p-3">
                      <label className="flex items-center gap-2 text-sm font-medium text-text-primary">
                        <input
                          type="checkbox"
                          checked={!!newIncident.is_reportable}
                          onChange={(e) => setNewIncident({
                            ...newIncident,
                            is_reportable: e.target.checked,
                            report_category: e.target.checked ? newIncident.report_category : '',
                            reported_to_authority: e.target.checked ? newIncident.reported_to_authority : false,
                            reported_at: e.target.checked ? newIncident.reported_at : '',
                            report_reference: e.target.checked ? newIncident.report_reference : '',
                            report_notes: e.target.checked ? newIncident.report_notes : ''
                          })}
                        />
                        Potentially reportable incident
                      </label>
                      <p className="text-xs text-text-muted">
                        Flag incidents that may be reportable (for example, RIDDOR-related) so reporting evidence is captured consistently.
                      </p>
                      {newIncident.is_reportable && (
                        <>
                          <div className="space-y-2">
                            <Label>Report Category</Label>
                            <Input
                              value={newIncident.report_category}
                              onChange={(e) => setNewIncident({...newIncident, report_category: e.target.value})}
                              placeholder="e.g., injury, dangerous occurrence"
                              className="rounded-xl"
                            />
                          </div>
                          <label className="flex items-center gap-2 text-sm text-text-primary">
                            <input
                              type="checkbox"
                              checked={!!newIncident.reported_to_authority}
                              onChange={(e) => setNewIncident({
                                ...newIncident,
                                reported_to_authority: e.target.checked,
                                reported_at: e.target.checked ? newIncident.reported_at : '',
                                report_reference: e.target.checked ? newIncident.report_reference : ''
                              })}
                            />
                            Reported to authority
                          </label>
                          {newIncident.reported_to_authority && (
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                              <div className="space-y-2">
                                <Label>Reported At</Label>
                                <Input
                                  type="date"
                                  value={newIncident.reported_at}
                                  onChange={(e) => setNewIncident({...newIncident, reported_at: e.target.value})}
                                  className="rounded-xl"
                                />
                              </div>
                              <div className="space-y-2">
                                <Label>Report Reference</Label>
                                <Input
                                  value={newIncident.report_reference}
                                  onChange={(e) => setNewIncident({...newIncident, report_reference: e.target.value})}
                                  placeholder="Authority reference"
                                  className="rounded-xl"
                                />
                              </div>
                            </div>
                          )}
                          <div className="space-y-2">
                            <Label>Report Notes</Label>
                            <Textarea
                              value={newIncident.report_notes}
                              onChange={(e) => setNewIncident({...newIncident, report_notes: e.target.value})}
                              placeholder="Internal report handling notes"
                              className="rounded-xl"
                              rows={2}
                            />
                          </div>
                        </>
                      )}
                    </div>
                    
                    <div className="flex flex-col-reverse sm:flex-row justify-end gap-3 pt-4 border-t border-[#E4E8EB]">
                      <Button type="button" variant="outline" onClick={() => setIncidentDialogOpen(false)} className="rounded-xl w-full sm:w-auto">
                        Cancel
                      </Button>
                      <Button type="submit" disabled={isSubmitting} className="bg-primary hover:bg-primary-hover text-white rounded-xl w-full sm:w-auto">
                        {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Submit Report'}
                      </Button>
                    </div>
                  </form>
                </DialogContent>
              </Dialog>
                </div>
            </CardHeader>
            <CardContent>
              {(() => {
                // Apply filters
                const filteredIncidents = incidents.filter(incident => {
                  if (incidentFilter.status !== 'all') {
                    const status = (incident.status || '').toLowerCase();
                    if (incidentFilter.status === 'reviewing') {
                      if (!['reviewing', 'under_review', 'investigating'].includes(status)) return false;
                    } else if (status !== incidentFilter.status) {
                      return false;
                    }
                  }
                  if (incidentFilter.severity !== 'all' && incident.incident_type !== incidentFilter.severity) return false;
                  return true;
                });
                
                if (filteredIncidents.length === 0) {
                  return (
                    <div className="text-center py-12">
                      <AlertCircle className="h-12 w-12 mx-auto text-text-muted/50 mb-3" />
                      <p className="text-text-muted">
                        {incidents.length === 0 ? 'No incidents recorded' : 'No incidents match filters'}
                      </p>
                    </div>
                  );
                }
                
                return (
                  <div className="space-y-3">
                    {filteredIncidents.map((incident) => {
                      // HARDENING: Use parseBackendDate for safe calculation
                      const dateOccurred = parseBackendDate(incident.date_occurred);
                      const daysOld = dateOccurred ? Math.ceil((new Date() - dateOccurred) / (1000 * 60 * 60 * 24)) : 0;
                      const isOverdue = (incident.status === 'open' || incident.status === 'reviewing' || incident.status === 'under_review' || incident.status === 'investigating') && daysOld > 7;
                      
                      return (
                        <div 
                          key={incident.id}
                          className={`p-4 rounded-xl border ${isOverdue ? 'bg-red-50/50 border-red-200' : 'bg-[#F8FAFA] border-[#E4E8EB]'}`}
                          data-testid={`incident-${incident.id}`}
                        >
                          <div className="flex items-start justify-between">
                            <div className="flex-1">
                              <div className="flex items-center gap-2 mb-1 flex-wrap">
                                <span className="text-xs font-mono text-text-muted">{incident.reference_number}</span>
                                {getStatusBadge(incident.status)}
                                <span className={`text-xs px-2 py-0.5 rounded ${
                                  incident.incident_type === 'outbreak' ? 'bg-error/10 text-error' :
                                  incident.incident_type === 'complaint' ? 'bg-warning/10 text-warning' :
                                  incident.incident_type === 'near_miss' ? 'bg-amber-100 text-amber-700' :
                                  'bg-info/10 text-info'
                                }`}>
                                  {incident.incident_type?.replace('_', ' ')}
                                </span>
                                {incident.is_reportable && (
                                  <span className="text-xs px-2 py-0.5 rounded bg-red-100 text-red-700 font-medium">
                                    {incident.reported_to_authority ? 'Reportable: reported' : 'Reportable: pending authority report'}
                                  </span>
                                )}
                                {isOverdue && (
                                  <span className="text-xs px-2 py-0.5 rounded bg-red-100 text-red-700 font-medium">
                                    Overdue ({daysOld}d)
                                  </span>
                                )}
                              </div>
                              <p className="font-medium text-text-primary">{incident.title}</p>
                              <p className="text-sm text-text-muted mt-1 line-clamp-2">{incident.description}</p>
                              <div className="flex items-center gap-3 text-xs text-text-muted mt-2">
                                <span>Date: {formatBackendDate(incident.date_occurred)}</span>
                                {incident.location && <span>Location: {incident.location}</span>}
                                {incident.report_category && <span>Category: {incident.report_category}</span>}
                                {incident.reported_at && <span>Reported: {formatBackendDate(incident.reported_at)}</span>}
                                {incident.follow_up_due_date && <span>Follow-up due: {formatBackendDate(incident.follow_up_due_date)}</span>}
                                {getFollowUpStatusBadge(incident.follow_up_status, incident.follow_up_due_date)}
                              </div>
                            </div>
                            {/* Action buttons for incidents */}
                            <div className="flex items-center gap-2 ml-4">
                              <Button 
                                size="sm"
                                variant="outline"
                                className="rounded-lg"
                                onClick={() => openAmendDialog('incident', incident)}
                                data-testid={`view-incident-${incident.id}`}
                              >
                                <Eye className="h-4 w-4 mr-1" />
                                View
                              </Button>
                              {isAdmin() && (
                                <>
                                  <Button 
                                    size="sm"
                                    variant="outline"
                                    className="rounded-lg"
                                    onClick={() => openAmendDialog('incident', incident)}
                                    data-testid={`edit-incident-${incident.id}`}
                                  >
                                    <Edit className="h-4 w-4 mr-1" />
                                    Edit
                                  </Button>
                                  {(incident.status === 'open' || incident.status === 'reviewing' || incident.status === 'under_review' || incident.status === 'investigating') && (
                                    <Button 
                                      size="sm"
                                      variant="default"
                                      className="rounded-lg bg-green-600 hover:bg-green-700"
                                      onClick={() => {
                                        // Quick close incident
                                        openAmendDialog('incident', {...incident, status: 'closed'});
                                      }}
                                      data-testid={`close-incident-${incident.id}`}
                                    >
                                      <CheckCircle className="h-4 w-4 mr-1" />
                                      Close
                                    </Button>
                                  )}
                                  <Button 
                                    size="sm"
                                    variant="ghost"
                                    className="rounded-lg text-text-muted hover:text-text-primary"
                                    onClick={() => loadHistory('incident', incident.id)}
                                    data-testid={`history-incident-${incident.id}`}
                                    title="View amendment history"
                                  >
                                    <History className="h-4 w-4" />
                                  </Button>
                                </>
                              )}
                            </div>
                          </div>
                          {incident.root_cause && (
                            <div className="mt-3 pt-3 border-t border-[#E4E8EB]">
                              <p className="text-xs text-text-muted">Root Cause:</p>
                              <p className="text-sm text-text-primary">{incident.root_cause}</p>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                );
              })()}
            </CardContent>
          </Card>
          </div>
        </TabsContent>

        {/* Staff Meetings Tab */}
        <TabsContent value="staff-meetings">
          <Card className="border-[#E4E8EB] shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="font-heading text-lg">Monthly Staff Meeting Records</CardTitle>
                <p className="text-sm text-text-muted mt-1">Admin-only meeting minutes register for employer compliance evidence.</p>
              </div>
              <Dialog open={staffMeetingDialogOpen} onOpenChange={setStaffMeetingDialogOpen}>
                <DialogTrigger asChild>
                  <Button className="bg-primary hover:bg-primary-hover text-white rounded-xl">
                    <Plus className="h-4 w-4 mr-2" />
                    New Meeting Record
                  </Button>
                </DialogTrigger>
                <DialogContent className="max-w-2xl w-[95vw] max-h-[90vh] overflow-y-auto">
                  <DialogHeader>
                    <DialogTitle className="font-heading text-lg pr-6">Create Staff Meeting Record</DialogTitle>
                  </DialogHeader>
                  <form onSubmit={handleCreateStaffMeeting} className="space-y-4 mt-4">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label>Meeting Date *</Label>
                        <Input
                          type="date"
                          value={newStaffMeeting.meeting_date}
                          onChange={(e) => setNewStaffMeeting({ ...newStaffMeeting, meeting_date: e.target.value })}
                          required
                          className="rounded-xl"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>Meeting Type *</Label>
                        <Select
                          value={newStaffMeeting.meeting_type}
                          onValueChange={(v) => setNewStaffMeeting({ ...newStaffMeeting, meeting_type: v })}
                        >
                          <SelectTrigger className="rounded-xl">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="monthly_staff_meeting">Monthly Staff Meeting</SelectItem>
                            <SelectItem value="team_meeting">Team Meeting</SelectItem>
                            <SelectItem value="compliance_meeting">Compliance Meeting</SelectItem>
                            <SelectItem value="ad_hoc_meeting">Ad Hoc Meeting</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>

                    <div className="space-y-2">
                      <Label>Attendees (employee_ids)</Label>
                      <div className="max-h-40 overflow-y-auto space-y-2 border border-[#E4E8EB] rounded-xl p-3">
                        {employees.length === 0 ? (
                          <p className="text-sm text-text-muted">No employees found</p>
                        ) : (
                          employees.map((emp) => (
                            <label key={emp.id} className="flex items-center gap-2 text-sm text-text-primary">
                              <input
                                type="checkbox"
                                checked={newStaffMeeting.employee_ids.includes(emp.id)}
                                onChange={() => toggleMeetingAttendeeSelection(emp.id)}
                              />
                              <span>{emp.first_name} {emp.last_name}</span>
                            </label>
                          ))
                        )}
                      </div>
                    </div>

                    <div className="space-y-2">
                      <Label>Agenda *</Label>
                      <Textarea
                        value={newStaffMeeting.agenda}
                        onChange={(e) => setNewStaffMeeting({ ...newStaffMeeting, agenda: e.target.value })}
                        rows={3}
                        required
                        className="rounded-xl"
                      />
                    </div>

                    <div className="space-y-2">
                      <Label>Notes / Minutes *</Label>
                      <Textarea
                        value={newStaffMeeting.notes}
                        onChange={(e) => setNewStaffMeeting({ ...newStaffMeeting, notes: e.target.value })}
                        rows={4}
                        required
                        className="rounded-xl"
                      />
                    </div>

                    <div className="space-y-2">
                      <Label>Actions Required</Label>
                      <Textarea
                        value={newStaffMeeting.actions_required}
                        onChange={(e) => setNewStaffMeeting({ ...newStaffMeeting, actions_required: e.target.value })}
                        rows={2}
                        className="rounded-xl"
                      />
                    </div>

                    <div className="space-y-2">
                      <Label>Next Meeting Date</Label>
                      <Input
                        type="date"
                        value={newStaffMeeting.next_meeting_date}
                        onChange={(e) => setNewStaffMeeting({ ...newStaffMeeting, next_meeting_date: e.target.value })}
                        className="rounded-xl"
                      />
                    </div>

                    <div className="flex flex-col-reverse sm:flex-row justify-end gap-3 pt-4 border-t border-[#E4E8EB]">
                      <Button type="button" variant="outline" onClick={() => setStaffMeetingDialogOpen(false)} className="rounded-xl w-full sm:w-auto">
                        Cancel
                      </Button>
                      <Button type="submit" disabled={isSubmittingMeeting} className="bg-primary hover:bg-primary-hover text-white rounded-xl w-full sm:w-auto">
                        {isSubmittingMeeting ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Create Record'}
                      </Button>
                    </div>
                  </form>
                </DialogContent>
              </Dialog>
            </CardHeader>
            <CardContent>
              {staffMeetings.length === 0 ? (
                <div className="text-center py-10 text-text-muted">
                  <ClipboardList className="h-10 w-10 mx-auto mb-2 opacity-50" />
                  <p>No staff meeting records yet</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {staffMeetings.map((meeting) => {
                    const attendeeNames = (meeting.employee_ids || [])
                      .map((empId) => employees.find((e) => e.id === empId))
                      .filter(Boolean)
                      .map((emp) => `${emp.first_name} ${emp.last_name}`);
                    return (
                      <div key={meeting.id} className="p-4 rounded-xl border bg-[#F8FAFA] border-[#E4E8EB]">
                        <div className="flex items-start justify-between gap-3">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 flex-wrap mb-1">
                              <span className="text-xs px-2 py-0.5 rounded bg-blue-100 text-blue-700">
                                {meeting.meeting_type?.replace(/_/g, ' ')}
                              </span>
                              <span className={`text-xs px-2 py-0.5 rounded ${meeting.actions_status === 'closed' ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'}`}>
                                Actions {meeting.actions_status || 'open'}
                              </span>
                            </div>
                            <p className="text-sm text-text-primary"><span className="font-medium">Meeting:</span> {formatBackendDate(meeting.meeting_date)}</p>
                            {meeting.next_meeting_date && <p className="text-sm text-text-muted">Next: {formatBackendDate(meeting.next_meeting_date)}</p>}
                            <p className="text-sm text-text-primary mt-2"><span className="font-medium">Agenda:</span> {meeting.agenda}</p>
                            <p className="text-sm text-text-muted mt-1"><span className="font-medium text-text-primary">Minutes:</span> {meeting.notes}</p>
                            {meeting.actions_required && <p className="text-sm text-text-muted mt-1"><span className="font-medium text-text-primary">Actions:</span> {meeting.actions_required}</p>}
                            <p className="text-xs text-text-muted mt-2">
                              Attendees ({(meeting.employee_ids || []).length}): {attendeeNames.length > 0 ? attendeeNames.join(', ') : 'No attendees selected'}
                            </p>
                          </div>
                          <div className="flex items-center gap-2">
                            <Button
                              size="sm"
                              variant="outline"
                              className="rounded-lg"
                              onClick={() => handleDownloadStaffMeetingPdf(meeting)}
                            >
                              <Download className="h-4 w-4 mr-1" />
                              PDF
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              className="rounded-lg"
                              onClick={() => openAmendDialog('meeting', meeting)}
                            >
                              <Edit className="h-4 w-4 mr-1" />
                              Edit
                            </Button>
                            {meeting.actions_status !== 'closed' && (
                              <Button
                                size="sm"
                                className="rounded-lg bg-green-600 hover:bg-green-700"
                                onClick={() => openAmendDialog('meeting', { ...meeting, actions_status: 'closed' })}
                              >
                                <CheckCircle className="h-4 w-4 mr-1" />
                                Close Actions
                              </Button>
                            )}
                            <Button
                              size="sm"
                              variant="ghost"
                              className="rounded-lg"
                              onClick={() => loadHistory('meeting', meeting.id)}
                              title="View amendment history"
                            >
                              <History className="h-4 w-4" />
                            </Button>
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

        {/* Employer Audits Tab */}
        <TabsContent value="employer-audits">
          <Card className="border-[#E4E8EB] shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="font-heading text-lg">Employer Audit / Checklist Register</CardTitle>
                <p className="text-sm text-text-muted mt-1">Admin-only provider audit records for compliance evidence.</p>
              </div>
              <Dialog open={employerAuditDialogOpen} onOpenChange={setEmployerAuditDialogOpen}>
                <DialogTrigger asChild>
                  <Button className="bg-primary hover:bg-primary-hover text-white rounded-xl">
                    <Plus className="h-4 w-4 mr-2" />
                    New Audit Record
                  </Button>
                </DialogTrigger>
                <DialogContent className="max-w-2xl w-[95vw] max-h-[90vh] overflow-y-auto">
                  <DialogHeader>
                    <DialogTitle className="font-heading text-lg pr-6">Create Employer Audit Record</DialogTitle>
                  </DialogHeader>
                  <form onSubmit={handleCreateEmployerAudit} className="space-y-4 mt-4">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label>Audit Type *</Label>
                        <Select value={newEmployerAudit.audit_type} onValueChange={(v) => setNewEmployerAudit({ ...newEmployerAudit, audit_type: v })}>
                          <SelectTrigger className="rounded-xl"><SelectValue /></SelectTrigger>
                          <SelectContent>
                            <SelectItem value="infection_control_audit">Infection Control Audit</SelectItem>
                            <SelectItem value="medication_audit">Medication Audit</SelectItem>
                            <SelectItem value="health_and_safety_audit">Health and Safety Audit</SelectItem>
                            <SelectItem value="fire_safety_audit">Fire Safety Audit</SelectItem>
                            <SelectItem value="cleaning_audit">Cleaning Audit</SelectItem>
                            <SelectItem value="daily_records_audit">Daily Records Audit</SelectItem>
                            <SelectItem value="general_quality_audit">General Quality Audit</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="space-y-2">
                        <Label>Audit Date *</Label>
                        <Input type="date" value={newEmployerAudit.audit_date} onChange={(e) => setNewEmployerAudit({ ...newEmployerAudit, audit_date: e.target.value })} className="rounded-xl" required />
                      </div>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label>Completed By *</Label>
                        <Input value={newEmployerAudit.completed_by} onChange={(e) => setNewEmployerAudit({ ...newEmployerAudit, completed_by: e.target.value })} className="rounded-xl" required />
                      </div>
                      <div className="space-y-2">
                        <Label>Overall Outcome *</Label>
                        <Select value={newEmployerAudit.overall_outcome} onValueChange={(v) => setNewEmployerAudit({ ...newEmployerAudit, overall_outcome: v })}>
                          <SelectTrigger className="rounded-xl"><SelectValue /></SelectTrigger>
                          <SelectContent>
                            <SelectItem value="compliant">Compliant</SelectItem>
                            <SelectItem value="partially_compliant">Partially Compliant</SelectItem>
                            <SelectItem value="non_compliant">Non-Compliant</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>

                    <div className="space-y-2">
                      <Label>Findings *</Label>
                      <Textarea value={newEmployerAudit.findings} onChange={(e) => setNewEmployerAudit({ ...newEmployerAudit, findings: e.target.value })} className="rounded-xl" rows={4} required />
                    </div>

                    <div className="space-y-2">
                      <Label>Actions Required</Label>
                      <Textarea value={newEmployerAudit.actions_required} onChange={(e) => setNewEmployerAudit({ ...newEmployerAudit, actions_required: e.target.value })} className="rounded-xl" rows={2} />
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label>Next Review Date</Label>
                        <Input type="date" value={newEmployerAudit.next_review_date} onChange={(e) => setNewEmployerAudit({ ...newEmployerAudit, next_review_date: e.target.value })} className="rounded-xl" />
                      </div>
                      <div className="space-y-2">
                        <Label>Status</Label>
                        <Select value={newEmployerAudit.status} onValueChange={(v) => setNewEmployerAudit({ ...newEmployerAudit, status: v })}>
                          <SelectTrigger className="rounded-xl"><SelectValue /></SelectTrigger>
                          <SelectContent>
                            <SelectItem value="open">Open</SelectItem>
                            <SelectItem value="closed">Closed</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>

                    <div className="flex flex-col-reverse sm:flex-row justify-end gap-3 pt-4 border-t border-[#E4E8EB]">
                      <Button type="button" variant="outline" onClick={() => setEmployerAuditDialogOpen(false)} className="rounded-xl w-full sm:w-auto">Cancel</Button>
                      <Button type="submit" disabled={isSubmittingEmployerAudit} className="bg-primary hover:bg-primary-hover text-white rounded-xl w-full sm:w-auto">
                        {isSubmittingEmployerAudit ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Create Record'}
                      </Button>
                    </div>
                  </form>
                </DialogContent>
              </Dialog>
            </CardHeader>
            <CardContent>
              {employerAudits.length === 0 ? (
                <div className="text-center py-10 text-text-muted">
                  <CheckCircle className="h-10 w-10 mx-auto mb-2 opacity-50" />
                  <p>No employer audit records yet</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {employerAudits.map((audit) => (
                    <div key={audit.id} className="p-4 rounded-xl border bg-[#F8FAFA] border-[#E4E8EB]">
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 flex-wrap mb-1">
                            <span className="text-xs px-2 py-0.5 rounded bg-blue-100 text-blue-700">{audit.audit_type?.replace(/_/g, ' ')}</span>
                            {getStatusBadge(audit.status || 'open')}
                            <span className={`text-xs px-2 py-0.5 rounded ${audit.overall_outcome === 'compliant' ? 'bg-green-100 text-green-700' : audit.overall_outcome === 'partially_compliant' ? 'bg-amber-100 text-amber-700' : 'bg-red-100 text-red-700'}`}>
                              {(audit.overall_outcome || '').replace(/_/g, ' ')}
                            </span>
                          </div>
                          <p className="text-sm text-text-primary"><span className="font-medium">Audit Date:</span> {formatBackendDate(audit.audit_date)}</p>
                          <p className="text-sm text-text-primary"><span className="font-medium">Completed By:</span> {audit.completed_by}</p>
                          <p className="text-sm text-text-muted mt-2"><span className="font-medium text-text-primary">Findings:</span> {audit.findings}</p>
                          {audit.actions_required && <p className="text-sm text-text-muted mt-1"><span className="font-medium text-text-primary">Actions:</span> {audit.actions_required}</p>}
                          {audit.next_review_date && <p className="text-xs text-text-muted mt-2">Next review: {formatBackendDate(audit.next_review_date)}</p>}
                        </div>
                        <div className="flex items-center gap-2">
                          <Button
                            size="sm"
                            variant="outline"
                            className="rounded-lg"
                            onClick={() => handleDownloadEmployerAuditPdf(audit)}
                          >
                            <Download className="h-4 w-4 mr-1" />
                            PDF
                          </Button>
                          <Button size="sm" variant="outline" className="rounded-lg" onClick={() => openAmendDialog('audit', audit)}>
                            <Edit className="h-4 w-4 mr-1" />
                            Edit
                          </Button>
                          {audit.status !== 'closed' && (
                            <Button
                              size="sm"
                              className="rounded-lg bg-green-600 hover:bg-green-700"
                              onClick={() => openAmendDialog('audit', { ...audit, status: 'closed' })}
                            >
                              <CheckCircle className="h-4 w-4 mr-1" />
                              Close
                            </Button>
                          )}
                          <Button size="sm" variant="ghost" className="rounded-lg" onClick={() => loadHistory('audit', audit.id)} title="View amendment history">
                            <History className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Compliance Insights Tab (formerly Reports) */}
        <TabsContent value="reports">
          <div className="space-y-6">
            {/* Compliance Alerts Section */}
            <Card className="border-[#E4E8EB] shadow-sm">
              <CardHeader>
                <CardTitle className="font-heading text-lg flex items-center gap-2">
                  <Bell className="h-5 w-5 text-amber-500" />
                  Active Alerts
                </CardTitle>
              </CardHeader>
              <CardContent>
                {(() => {
                  const alerts = [];
                  
                  // Add DBS alerts
                  if (dbsReport?.report) {
                    const expiringDbs = dbsReport.report.filter(s => 
                      s.dbs_status === 'expiring_soon' || s.dbs_status === 'expired'
                    );
                    expiringDbs.forEach(s => alerts.push({
                      type: 'dbs',
                      severity: s.dbs_status === 'expired' ? 'high' : 'medium',
                      title: `${s.name} - DBS ${s.dbs_status === 'expired' ? 'Expired' : 'Expiring'}`,
                      date: s.dbs_expiry
                    }));
                  }
                  
                  // Add Training alerts
                  if (trainingReport?.report) {
                    trainingReport.report.forEach(s => {
                      if (s.expiring_soon?.length > 0) {
                        s.expiring_soon.forEach(t => alerts.push({
                          type: 'training',
                          severity: 'medium',
                          title: `${s.name} - ${t} expiring`,
                          employee: s.name
                        }));
                      }
                    });
                  }
                  
                  // Add policy/certificate expiry alerts from dashboard
                  if (dashboard?.expiring_policies?.length > 0) {
                    dashboard.expiring_policies.forEach(p => alerts.push({
                      type: 'policy',
                      severity: 'medium',
                      title: `Policy "${p.title}" expiring`,
                      date: p.review_date
                    }));
                  }
                  
                  if (alerts.length === 0) {
                    return (
                      <div className="text-center py-8 text-text-muted">
                        <CheckCircle className="h-12 w-12 mx-auto text-green-400 mb-3" />
                        <p className="font-medium text-green-700">No Active Alerts</p>
                        <p className="text-sm">All compliance items are up to date</p>
                      </div>
                    );
                  }
                  
                  return (
                    <div className="space-y-2 max-h-64 overflow-y-auto">
                      {alerts.slice(0, 10).map((alert, idx) => (
                        <div 
                          key={idx} 
                          className={`flex items-center justify-between p-3 rounded-lg border ${
                            alert.severity === 'high' ? 'bg-red-50 border-red-200' : 'bg-amber-50 border-amber-200'
                          }`}
                        >
                          <div className="flex items-center gap-3">
                            <AlertTriangle className={`h-4 w-4 ${alert.severity === 'high' ? 'text-red-500' : 'text-amber-500'}`} />
                            <div>
                              <p className={`font-medium text-sm ${alert.severity === 'high' ? 'text-red-700' : 'text-amber-700'}`}>
                                {alert.title}
                              </p>
                              {alert.date && (
                                <p className="text-xs text-text-muted">
                                  {formatBackendDate(alert.date)}
                                </p>
                              )}
                            </div>
                          </div>
                          <span className={`text-xs px-2 py-0.5 rounded ${
                            alert.type === 'dbs' ? 'bg-purple-100 text-purple-700' :
                            alert.type === 'training' ? 'bg-blue-100 text-blue-700' :
                            'bg-gray-100 text-gray-700'
                          }`}>
                            {alert.type.toUpperCase()}
                          </span>
                        </div>
                      ))}
                      {alerts.length > 10 && (
                        <p className="text-xs text-text-muted text-center py-2">
                          + {alerts.length - 10} more alerts
                        </p>
                      )}
                    </div>
                  );
                })()}
              </CardContent>
            </Card>
            
            {/* Action Cards Grid */}
            <div className="grid md:grid-cols-3 gap-4">
              {/* DBS Register Card */}
              <Card className="border-[#E4E8EB] shadow-sm hover:shadow-md transition-shadow cursor-pointer" 
                    onClick={() => window.location.href = '/portal/dbs-register'}>
                <CardContent className="p-6">
                  <div className="flex items-center justify-between mb-4">
                    <div className="w-12 h-12 rounded-xl bg-purple-100 flex items-center justify-center">
                      <Shield className="h-6 w-6 text-purple-600" />
                    </div>
                    <ArrowRight className="h-5 w-5 text-text-muted" />
                  </div>
                  <h3 className="font-semibold text-text-primary mb-1">DBS Register</h3>
                  <p className="text-sm text-text-muted mb-3">View and manage DBS checks</p>
                  {dbsReport && (
                    <div className="flex items-center gap-2">
                      <span className="text-xs px-2 py-0.5 rounded bg-green-100 text-green-700">
                        {dbsReport.report?.filter(s => s.dbs_status === 'valid').length || 0} Valid
                      </span>
                      <span className="text-xs px-2 py-0.5 rounded bg-amber-100 text-amber-700">
                        {dbsReport.report?.filter(s => s.dbs_status === 'expiring_soon').length || 0} Expiring
                      </span>
                    </div>
                  )}
                </CardContent>
              </Card>
              
              {/* Training Matrix Card */}
              <Card className="border-[#E4E8EB] shadow-sm hover:shadow-md transition-shadow cursor-pointer"
                    onClick={() => window.location.href = '/portal/training'}>
                <CardContent className="p-6">
                  <div className="flex items-center justify-between mb-4">
                    <div className="w-12 h-12 rounded-xl bg-blue-100 flex items-center justify-center">
                      <BookOpen className="h-6 w-6 text-blue-600" />
                    </div>
                    <ArrowRight className="h-5 w-5 text-text-muted" />
                  </div>
                  <h3 className="font-semibold text-text-primary mb-1">Training Matrix</h3>
                  <p className="text-sm text-text-muted mb-3">Track staff training status</p>
                  {trainingReport && (
                    <div className="flex items-center gap-2">
                      <span className="text-xs px-2 py-0.5 rounded bg-green-100 text-green-700">
                        {trainingReport.report?.reduce((sum, s) => sum + s.completed_count, 0) || 0} Completed
                      </span>
                      <span className="text-xs px-2 py-0.5 rounded bg-amber-100 text-amber-700">
                        {trainingReport.report?.reduce((sum, s) => sum + s.pending_count, 0) || 0} Awaiting Completion
                      </span>
                    </div>
                  )}
                </CardContent>
              </Card>
              
              {/* Policies Card */}
              <Card className="border-[#E4E8EB] shadow-sm hover:shadow-md transition-shadow cursor-pointer"
                    onClick={() => handleTabChange('policies')}>
                <CardContent className="p-6">
                  <div className="flex items-center justify-between mb-4">
                    <div className="w-12 h-12 rounded-xl bg-green-100 flex items-center justify-center">
                      <FileText className="h-6 w-6 text-green-600" />
                    </div>
                    <ArrowRight className="h-5 w-5 text-text-muted" />
                  </div>
                  <h3 className="font-semibold text-text-primary mb-1">Policies</h3>
                  <p className="text-sm text-text-muted mb-3">Manage organisational policies</p>
                  <div className="flex items-center gap-2">
                    <span className="text-xs px-2 py-0.5 rounded bg-green-100 text-green-700">
                      {policies.filter(p => p.status === 'active').length} Active
                    </span>
                    <span className="text-xs px-2 py-0.5 rounded bg-amber-100 text-amber-700">
                      {policies.filter(p => p.status === 'review_due').length} Review Due
                    </span>
                  </div>
                </CardContent>
              </Card>
            </div>
            
            {/* Quick Actions */}
            <Card className="border-[#E4E8EB] shadow-sm">
              <CardHeader>
                <CardTitle className="font-heading text-lg">Quick Actions</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid md:grid-cols-3 gap-3">
                  <Button 
                    variant="outline" 
                    className="justify-start h-auto py-4 px-4 rounded-xl"
                    onClick={() => window.location.href = '/portal/employees'}
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-lg bg-red-100 flex items-center justify-center">
                        <FileText className="h-5 w-5 text-red-600" />
                      </div>
                      <div className="text-left">
                        <p className="font-medium">Request Documents</p>
                        <p className="text-xs text-text-muted">Request missing documents from staff</p>
                      </div>
                    </div>
                  </Button>
                  
                  <Button 
                    variant="outline" 
                    className="justify-start h-auto py-4 px-4 rounded-xl"
                    onClick={() => handleTabChange('policies')}
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center">
                        <Plus className="h-5 w-5 text-blue-600" />
                      </div>
                      <div className="text-left">
                        <p className="font-medium">Assign Policies</p>
                        <p className="text-xs text-text-muted">Upload and assign new policies</p>
                      </div>
                    </div>
                  </Button>
                  
                  <Button 
                    variant="outline" 
                    className="justify-start h-auto py-4 px-4 rounded-xl"
                    onClick={() => toast.info('Email reminders feature coming soon')}
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-lg bg-amber-100 flex items-center justify-center">
                        <Send className="h-5 w-5 text-amber-600" />
                      </div>
                      <div className="text-left">
                        <p className="font-medium">Send Reminders</p>
                        <p className="text-xs text-text-muted">Notify staff about outstanding items</p>
                      </div>
                    </div>
                  </Button>
                </div>
              </CardContent>
            </Card>
            
            {/* Original Reports Grid (kept for data reference) */}
            <div className="grid md:grid-cols-2 gap-6">
              {/* Staff DBS Report */}
              <Card className="border-[#E4E8EB] shadow-sm">
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="font-heading text-lg">Staff DBS Dates</CardTitle>
                <Button 
                  variant="outline" 
                  size="sm" 
                  className="rounded-lg"
                  onClick={() => fetchReports('dbs')}
                >
                  <RefreshCw className="h-4 w-4 mr-1" />
                  Refresh
                </Button>
              </CardHeader>
              <CardContent>
                {dbsReport ? (
                  <div className="space-y-2 max-h-96 overflow-y-auto">
                    {dbsReport.report.map((staff) => (
                      <div key={staff.employee_id} className="flex items-center justify-between p-3 bg-[#F8FAFA] rounded-lg">
                        <div>
                          <p className="font-medium text-text-primary text-sm">{staff.name}</p>
                          <p className="text-xs text-text-muted">{staff.role} • {staff.assignment}</p>
                        </div>
                        <div className="text-right">
                          {getStatusBadge(staff.dbs_status)}
                          {staff.dbs_expiry && (
                            <p className="text-xs text-text-muted mt-1">
                              Exp: {formatBackendDate(staff.dbs_expiry)}
                            </p>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <Loader2 className="h-6 w-6 animate-spin mx-auto text-text-muted" />
                    <p className="text-sm text-text-muted mt-2">Loading report...</p>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Training Report */}
            <Card className="border-[#E4E8EB] shadow-sm">
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="font-heading text-lg">Training Report (12 months)</CardTitle>
                <Button 
                  variant="outline" 
                  size="sm" 
                  className="rounded-lg"
                  onClick={() => fetchReports('training')}
                >
                  <RefreshCw className="h-4 w-4 mr-1" />
                  Refresh
                </Button>
              </CardHeader>
              <CardContent>
                {trainingReport ? (
                  <div className="space-y-2 max-h-96 overflow-y-auto">
                    {trainingReport.report.map((staff) => (
                      <div key={staff.employee_id} className="flex items-center justify-between p-3 bg-[#F8FAFA] rounded-lg">
                        <div>
                          <p className="font-medium text-text-primary text-sm">{staff.name}</p>
                          <p className="text-xs text-text-muted">{staff.role}</p>
                        </div>
                        <div className="text-right">
                          <span className="text-sm font-medium text-success">{staff.completed_count} completed</span>
                          {staff.pending_count > 0 && (
                            <span className="text-sm text-warning ml-2">{staff.pending_count} outstanding</span>
                          )}
                          {staff.expiring_soon?.length > 0 && (
                            <p className="text-xs text-error mt-1">{staff.expiring_soon.length} expiring</p>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <Button onClick={() => fetchReports('training')} variant="outline" className="rounded-xl">
                      Generate Report
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
          </div>
        </TabsContent>
        
        {/* CQC View Tab - Inspection Readiness Evidence Mapping */}
        <TabsContent value="cqc-view">
          <div className="space-y-6">
            {/* CQC View Header */}
            <Card className="border-[#E4E8EB] shadow-sm bg-gradient-to-r from-primary/5 to-info/5">
              <CardContent className="p-4">
                <div className="flex items-start justify-between">
                  <div>
                    <h2 className="font-heading text-lg font-bold flex items-center gap-2">
                      <Eye className="h-5 w-5 text-primary" />
                      CQC Inspection View
                    </h2>
                    <p className="text-sm text-text-muted mt-1">
                      Evidence mapped to CQC 5 Key Questions for inspection readiness
                    </p>
                    <p className="text-xs text-text-muted mt-2 bg-white/50 px-2 py-1 rounded inline-block">
                      Read-only view — does not affect compliance calculations or employee readiness status
                    </p>
                  </div>
                  <div className="flex flex-col items-end gap-2">
                    {cqcEvidenceMap && (
                      <div className="text-right">
                        <p className="text-2xl font-bold text-text-primary">
                          {cqcEvidenceMap.summary.present}/{cqcEvidenceMap.summary.total_items - cqcEvidenceMap.summary.n_a}
                        </p>
                        <p className="text-xs text-text-muted">Evidence Items Present</p>
                      </div>
                    )}
                    {/* Generate Inspection Pack Button */}
                    <Button
                      onClick={handleGenerateInspectionPack}
                      disabled={generatingPack}
                      className="bg-primary hover:bg-primary-hover text-white rounded-xl"
                      data-testid="generate-inspection-pack-btn"
                    >
                      {generatingPack ? (
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      ) : (
                        <Package className="mr-2 h-4 w-4" />
                      )}
                      Generate Inspection Pack
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
            
            {cqcLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
                <span className="ml-3 text-text-muted">Loading CQC evidence mapping...</span>
              </div>
            ) : cqcEvidenceMap ? (
              <div className="space-y-6">
                {/* Summary Badges */}
                <div className="flex flex-wrap gap-2">
                  <span className="px-3 py-1 bg-success/10 text-success rounded-full text-sm font-medium">
                    {cqcEvidenceMap.summary.present} Present
                  </span>
                  <span className="px-3 py-1 bg-error/10 text-error rounded-full text-sm font-medium">
                    {cqcEvidenceMap.summary.missing} Missing
                  </span>
                  {cqcEvidenceMap.summary.due_review > 0 && (
                    <span className="px-3 py-1 bg-warning/10 text-warning rounded-full text-sm font-medium">
                      {cqcEvidenceMap.summary.due_review} Due Review
                    </span>
                  )}
                  {cqcEvidenceMap.summary.expired > 0 && (
                    <span className="px-3 py-1 bg-error/10 text-error rounded-full text-sm font-medium">
                      {cqcEvidenceMap.summary.expired} Expired
                    </span>
                  )}
                  {cqcEvidenceMap.summary.partial > 0 && (
                    <span className="px-3 py-1 bg-info/10 text-info rounded-full text-sm font-medium">
                      {cqcEvidenceMap.summary.partial} Partial
                    </span>
                  )}
                  <span className="px-3 py-1 bg-gray-100 text-text-muted rounded-full text-sm">
                    {cqcEvidenceMap.summary.n_a} N/A
                  </span>
                </div>
                
                {/* CQC Key Questions Sections */}
                {['safe', 'effective', 'caring', 'responsive', 'well_led'].map((key) => {
                  const section = cqcEvidenceMap.cqc_mapping[key];
                  if (!section) return null;
                  
                  const presentCount = section.items.filter(i => i.status === 'present' || i.status === 'partial').length;
                  const totalCount = section.items.filter(i => i.status !== 'n/a').length;
                  const hasIssues = section.items.some(i => ['missing', 'expired', 'overdue'].includes(i.status));
                  
                  // Color schemes for each key question
                  const colors = {
                    safe: { bg: 'bg-green-500', light: 'bg-green-50', border: 'border-green-200', text: 'text-green-700' },
                    effective: { bg: 'bg-blue-500', light: 'bg-blue-50', border: 'border-blue-200', text: 'text-blue-700' },
                    caring: { bg: 'bg-purple-500', light: 'bg-purple-50', border: 'border-purple-200', text: 'text-purple-700' },
                    responsive: { bg: 'bg-orange-500', light: 'bg-orange-50', border: 'border-orange-200', text: 'text-orange-700' },
                    well_led: { bg: 'bg-indigo-500', light: 'bg-indigo-50', border: 'border-indigo-200', text: 'text-indigo-700' }
                  };
                  const color = colors[key];
                  
                  return (
                    <Card key={key} className={`border shadow-sm ${hasIssues ? 'border-warning/30' : 'border-[#E4E8EB]'}`}>
                      <CardHeader className={`pb-3 ${color.light} rounded-t-lg`}>
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <div className={`w-1.5 h-12 rounded-full ${color.bg}`}></div>
                            <div>
                              <CardTitle className={`font-heading text-lg ${color.text}`}>
                                {section.title}
                              </CardTitle>
                              <p className="text-sm text-text-muted">{section.description}</p>
                            </div>
                          </div>
                          <div className="text-right">
                            <p className={`text-xl font-bold ${presentCount === totalCount ? 'text-success' : hasIssues ? 'text-warning' : 'text-text-primary'}`}>
                              {presentCount}/{totalCount}
                            </p>
                            <p className="text-xs text-text-muted">items present</p>
                          </div>
                        </div>
                      </CardHeader>
                      <CardContent className="pt-4">
                        <div className="space-y-2">
                          {section.items.map((item, idx) => (
                            <div 
                              key={idx}
                              className={`flex items-center justify-between p-3 rounded-lg border transition-colors ${
                                item.status === 'present' ? 'bg-success/5 border-success/20' :
                                item.status === 'partial' ? 'bg-info/5 border-info/20' :
                                item.status === 'missing' ? 'bg-error/5 border-error/20' :
                                item.status === 'expired' || item.status === 'overdue' ? 'bg-error/5 border-error/20' :
                                item.status === 'due_review' || item.status === 'expiring' ? 'bg-warning/5 border-warning/20' :
                                'bg-gray-50 border-gray-200'
                              }`}
                            >
                              <div className="flex items-center gap-3">
                                {/* Status Icon */}
                                {item.status === 'present' && <CheckCircle className="h-4 w-4 text-success flex-shrink-0" />}
                                {item.status === 'partial' && <AlertCircle className="h-4 w-4 text-info flex-shrink-0" />}
                                {item.status === 'missing' && <XCircle className="h-4 w-4 text-error flex-shrink-0" />}
                                {(item.status === 'expired' || item.status === 'overdue') && <XCircle className="h-4 w-4 text-error flex-shrink-0" />}
                                {(item.status === 'due_review' || item.status === 'expiring') && <Clock className="h-4 w-4 text-warning flex-shrink-0" />}
                                {item.status === 'n/a' && <span className="h-4 w-4 text-text-muted flex-shrink-0 text-center">—</span>}
                                
                                <div>
                                  <p className="font-medium text-sm text-text-primary">{item.name}</p>
                                  <div className="flex items-center gap-2 mt-0.5">
                                    <span className="text-[10px] px-1.5 py-0.5 bg-gray-100 text-text-muted rounded capitalize">
                                      {item.source_type}
                                    </span>
                                    {item.details && (
                                      <span className="text-xs text-text-muted">{item.details}</span>
                                    )}
                                    {item.conditional && (
                                      <span className="text-[10px] px-1.5 py-0.5 bg-warning/20 text-warning rounded">
                                        CONDITIONAL
                                      </span>
                                    )}
                                  </div>
                                </div>
                              </div>
                              
                              <div className="flex items-center gap-3">
                                {/* Review/Expiry Date */}
                                {(item.review_date || item.expiry_date) && (
                                  <span className={`text-xs flex items-center gap-1 ${
                                    item.status === 'overdue' || item.status === 'expired' ? 'text-error' :
                                    item.status === 'due_review' || item.status === 'expiring' ? 'text-warning' :
                                    'text-text-muted'
                                  }`}>
                                    <Calendar className="h-3 w-3" />
                                    {item.review_date ? `Review: ${formatBackendDate(item.review_date)}` :
                                     item.expiry_date ? `Expires: ${formatBackendDate(item.expiry_date)}` : ''}
                                  </span>
                                )}
                                
                                {/* Status Badge */}
                                <span className={`text-[10px] px-2 py-1 rounded-full font-medium ${
                                  item.status === 'present' ? 'bg-success/20 text-success' :
                                  item.status === 'partial' ? 'bg-info/20 text-info' :
                                  item.status === 'missing' ? 'bg-error/20 text-error' :
                                  item.status === 'expired' || item.status === 'overdue' ? 'bg-error/20 text-error' :
                                  item.status === 'due_review' || item.status === 'expiring' ? 'bg-warning/20 text-warning' :
                                  'bg-gray-200 text-text-muted'
                                }`}>
                                  {item.status === 'present' ? 'Present' :
                                   item.status === 'partial' ? 'Partial' :
                                   item.status === 'missing' ? 'Missing' :
                                   item.status === 'expired' ? 'Expired' :
                                   item.status === 'overdue' ? 'Overdue' :
                                   item.status === 'due_review' ? 'Due Review' :
                                   item.status === 'expiring' ? 'Expiring' :
                                   'N/A'}
                                </span>
                                
                                {/* Link to source */}
                                {item.link && item.status !== 'n/a' && (
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    className="h-7 px-2 text-xs"
                                    onClick={() => window.location.href = item.link}
                                  >
                                    View
                                  </Button>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      </CardContent>
                    </Card>
                  );
                })}
                
                {/* Footer Note */}
                <div className="p-4 bg-gray-50 rounded-xl border border-gray-200">
                  <p className="text-xs text-text-muted text-center">
                    <span className="font-medium">Note:</span> This view maps existing system evidence to CQC Key Questions for inspection preparation. 
                    It does not change employee compliance calculations, progress percentages, or Ready to Work status.
                    <br />
                    Generated: {formatBackendDateTime(cqcEvidenceMap.generated_at)}
                  </p>
                </div>
              </div>
            ) : (
              <div className="text-center py-12">
                <Eye className="h-12 w-12 mx-auto text-text-muted/50 mb-3" />
                <p className="text-text-muted">Click on the CQC View tab to load evidence mapping</p>
              </div>
            )}
          </div>
        </TabsContent>
      </Tabs>

      <Dialog open={createCertDialogOpen} onOpenChange={setCreateCertDialogOpen}>
        <DialogContent className="max-w-lg w-[95vw] max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="font-heading text-lg pr-6">Add Provider Certificate or Check</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleCreateCertificateRecord} className="space-y-4 mt-3">
            <div className="space-y-2">
              <Label>Name *</Label>
              <Input
                value={newCert.name}
                onChange={(e) => setNewCert(prev => ({ ...prev, name: e.target.value }))}
                placeholder="e.g., Waste Contract"
                className="rounded-xl"
                required
              />
            </div>
            <div className="space-y-2">
              <Label>Type Key *</Label>
              <Input
                value={newCert.insurance_type}
                onChange={(e) => setNewCert(prev => ({ ...prev, insurance_type: e.target.value }))}
                placeholder="e.g., waste_contract"
                className="rounded-xl"
                required
              />
            </div>
            <div className="space-y-2">
              <Label>Category *</Label>
              <Select value={newCert.category} onValueChange={(v) => setNewCert(prev => ({ ...prev, category: v }))}>
                <SelectTrigger className="rounded-xl"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="insurance">Insurance</SelectItem>
                  <SelectItem value="regulatory">Regulatory</SelectItem>
                  <SelectItem value="safety">Safety</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label>Issue Date</Label>
                <Input
                  type="date"
                  value={newCert.issue_date}
                  onChange={(e) => setNewCert(prev => ({ ...prev, issue_date: e.target.value }))}
                  className="rounded-xl"
                />
              </div>
              <div className="space-y-2">
                <Label>Expiry/Due Date {newCert.valid_until_replaced ? '(optional)' : '*'}</Label>
                <Input
                  type="date"
                  value={newCert.expiry_date}
                  onChange={(e) => setNewCert(prev => ({ ...prev, expiry_date: e.target.value }))}
                  className="rounded-xl"
                  required={!newCert.valid_until_replaced}
                />
              </div>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label>Provider/Vendor</Label>
                <Input
                  value={newCert.provider}
                  onChange={(e) => setNewCert(prev => ({ ...prev, provider: e.target.value }))}
                  placeholder="Issuer or contractor"
                  className="rounded-xl"
                />
              </div>
              <div className="space-y-2">
                <Label>Reference</Label>
                <Input
                  value={newCert.policy_number}
                  onChange={(e) => setNewCert(prev => ({ ...prev, policy_number: e.target.value }))}
                  placeholder="Certificate or contract ref"
                  className="rounded-xl"
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Notes</Label>
              <Textarea
                value={newCert.notes}
                onChange={(e) => setNewCert(prev => ({ ...prev, notes: e.target.value }))}
                className="rounded-xl"
                placeholder="Optional compliance notes"
              />
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <label className="flex items-center gap-2 text-sm text-text-primary">
                <input
                  type="checkbox"
                  checked={newCert.required}
                  onChange={(e) => setNewCert(prev => ({ ...prev, required: e.target.checked }))}
                />
                Required item
              </label>
              <label className="flex items-center gap-2 text-sm text-text-primary">
                <input
                  type="checkbox"
                  checked={newCert.valid_until_replaced}
                  onChange={(e) => setNewCert(prev => ({
                    ...prev,
                    valid_until_replaced: e.target.checked,
                    expiry_date: e.target.checked ? '' : prev.expiry_date
                  }))}
                />
                Valid until replaced
              </label>
            </div>
            <div className="flex flex-col-reverse sm:flex-row justify-end gap-3 pt-2 border-t border-[#E4E8EB]">
              <Button type="button" variant="outline" onClick={() => setCreateCertDialogOpen(false)} className="rounded-xl w-full sm:w-auto">
                Cancel
              </Button>
              <Button type="submit" disabled={isCreatingCert} className="rounded-xl w-full sm:w-auto">
                {isCreatingCert ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Create Record'}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      {/* Upload Dialog */}
      <Dialog open={uploadDialogOpen} onOpenChange={(open) => { setUploadDialogOpen(open); if (!open) resetUploadForm(); }}>
        <DialogContent className="max-w-lg w-[95vw] max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="font-heading text-lg pr-6">
              {isReplaceMode 
                ? `Replace Document: ${selectedPolicy?.name || selectedInsurance?.name}` 
                : selectedPolicy 
                  ? `Upload ${selectedPolicy.name}` 
                  : selectedInsurance 
                    ? `Upload ${selectedInsurance.name}` 
                    : 'Upload Document'}
            </DialogTitle>
          </DialogHeader>
          
          <form onSubmit={isReplaceMode ? handleReplaceDocument : (selectedPolicy ? handleUploadPolicy : handleUploadInsurance)} className="space-y-4 mt-4">
            {/* Replace mode warning */}
            {isReplaceMode && (
              <div className="bg-amber-50 border border-amber-200 rounded-xl p-3">
                <div className="flex items-start gap-2">
                  <AlertTriangle className="h-4 w-4 text-amber-600 mt-0.5 flex-shrink-0" />
                  <div className="text-sm text-amber-800">
                    <p className="font-medium">Replacing existing document</p>
                    <p className="text-xs mt-1">The current document will be moved to history and replaced with the new file.</p>
                  </div>
                </div>
              </div>
            )}
            
            {/* Replacement reason (required for replace mode) */}
            {isReplaceMode && (
              <div className="space-y-2">
                <Label>Reason for Replacement *</Label>
                <Input
                  value={replaceReason}
                  onChange={(e) => setReplaceReason(e.target.value)}
                  placeholder="e.g., Wrong document uploaded, newer version available"
                  required
                  className="rounded-xl"
                />
              </div>
            )}
            
            <div className="space-y-2">
              <Label>Document File *</Label>
              <FileUploaderInline
                onFileSelect={(file) => setUploadFile(file)}
                selectedFile={uploadFile}
                onClear={() => setUploadFile(null)}
                placeholder="Drop document here or click to browse"
              />
              {uploadFile && (
                <p className="text-xs text-text-muted truncate" title={uploadFile.name}>
                  Selected: {uploadFile.name}
                </p>
              )}
            </div>
            
            {selectedPolicy && (
              <>
                <div className="space-y-2">
                  <Label>Version</Label>
                  <Input
                    value={uploadVersion}
                    onChange={(e) => setUploadVersion(e.target.value)}
                    placeholder="e.g., v2.0"
                    className="rounded-xl"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Next Review Date</Label>
                  <Input
                    type="date"
                    value={uploadReviewDate}
                    onChange={(e) => setUploadReviewDate(e.target.value)}
                    className="rounded-xl"
                  />
                </div>
              </>
            )}
            
            {selectedInsurance && (
              <>
                {/* Conditional Expiry Date based on certificate type */}
                {selectedInsurance.requires_expiry_date !== false ? (
                  <div className="space-y-2">
                    <Label>Expiry Date *</Label>
                    <Input
                      type="date"
                      value={uploadExpiryDate}
                      onChange={(e) => setUploadExpiryDate(e.target.value)}
                      required
                      className="rounded-xl"
                    />
                  </div>
                ) : (
                  <div className="space-y-2">
                    <Label>Expiry Date (optional)</Label>
                    <Input
                      type="date"
                      value={uploadExpiryDate}
                      onChange={(e) => setUploadExpiryDate(e.target.value)}
                      className="rounded-xl"
                    />
                    {selectedInsurance.valid_until_replaced && (
                      <p className="text-xs text-success flex items-center gap-1">
                        <CheckCircle className="h-3 w-3" />
                        Valid until replaced — no expiry date required
                      </p>
                    )}
                  </div>
                )}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="space-y-2">
                    <Label>Policy/Ref Number</Label>
                    <Input
                      value={uploadPolicyNumber}
                      onChange={(e) => setUploadPolicyNumber(e.target.value)}
                      placeholder="Certificate reference"
                      className="rounded-xl"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Provider/Issuer</Label>
                    <Input
                      value={uploadProvider}
                      onChange={(e) => setUploadProvider(e.target.value)}
                      placeholder="e.g., Companies House"
                      className="rounded-xl"
                    />
                  </div>
                </div>
              </>
            )}
            
            <div className="flex flex-col-reverse sm:flex-row justify-end gap-3 pt-4 border-t border-[#E4E8EB]">
              <Button type="button" variant="outline" onClick={() => { setUploadDialogOpen(false); resetUploadForm(); }} className="rounded-xl w-full sm:w-auto">
                Cancel
              </Button>
              <Button 
                type="submit" 
                disabled={isUploading || !uploadFile} 
                className="bg-primary hover:bg-primary-hover text-white rounded-xl w-full sm:w-auto"
              >
                {isUploading ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Upload'}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      {/* Remove Document Dialog */}
      <Dialog open={removeDialogOpen} onOpenChange={(open) => {
        setRemoveDialogOpen(open);
        if (!open) {
          setRemoveTarget(null);
          setRemoveReason('');
        }
      }}>
        <DialogContent className="max-w-md w-[95vw]">
          <DialogHeader>
            <DialogTitle className="font-heading text-lg">Remove Document</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 mt-2">
            <p className="text-sm text-text-muted">
              {removeTarget?.name
                ? `This will mark the document under "${removeTarget.name}" as missing.`
                : 'This will mark the document as missing.'}
            </p>
            <div className="space-y-2">
              <Label>Reason *</Label>
              <Textarea
                value={removeReason}
                onChange={(e) => setRemoveReason(e.target.value)}
                placeholder="Why are you removing this document?"
                className="min-h-[90px]"
              />
            </div>
            <div className="flex flex-col-reverse sm:flex-row justify-end gap-3 pt-2">
              <Button
                variant="outline"
                onClick={() => {
                  setRemoveDialogOpen(false);
                  setRemoveTarget(null);
                  setRemoveReason('');
                }}
                className="rounded-xl w-full sm:w-auto"
              >
                Cancel
              </Button>
              <Button
                onClick={handleConfirmRemoveDocument}
                disabled={!removeReason.trim()}
                className="bg-red-600 hover:bg-red-700 text-white rounded-xl w-full sm:w-auto"
              >
                Remove Document
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Document Preview Modal */}
      <DocumentPreviewModal
        isOpen={previewOpen}
        onClose={() => setPreviewOpen(false)}
        fileUrl={previewFile?.url}
        fileName={previewFile?.name}
        token={token}
        onDownload={previewFile ? () => {
          // Determine type from URL
          const isPolicy = previewFile.url?.includes('/policies/');
          const id = previewFile.url?.split('/').slice(-2, -1)[0];
          if (id) {
            handleDownloadDocument(isPolicy ? 'policy' : 'insurance', id, previewFile.filename);
          }
        } : undefined}
      />

      {/* Policy Assignment Modal */}
      <Dialog open={assignDialogOpen} onOpenChange={(open) => {
        setAssignDialogOpen(open);
        if (!open) {
          setPolicyToAssign(null);
          setSelectedEmployees([]);
        }
      }}>
        <DialogContent className="max-w-md w-[95vw] max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="font-heading text-lg pr-6">Assign Policy to Employees</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 mt-4">
            {policyToAssign && (() => {
              const triage = getPolicyAssignmentTriage(policyToAssign.id);
              return triage.total > 0 ? (
                <div className="flex flex-wrap items-center gap-2 rounded-xl border border-[#E4E8EB] bg-[#F8FAFA] p-3 text-xs">
                  <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-amber-700">
                    Pending acknowledgement: {triage.pendingAcknowledgement}
                  </span>
                  <span className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-2 py-0.5 text-blue-700">
                    Awaiting admin review: {triage.awaitingAdminReview}
                  </span>
                  <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2 py-0.5 text-green-700">
                    Reviewed: {triage.reviewed}
                  </span>
                </div>
              ) : null;
            })()}

            {policyToAssign && (
              <div className="p-3 bg-[#F8FAFA] rounded-xl border border-[#E4E8EB]">
                <p className="font-medium text-text-primary truncate" title={policyToAssign.name}>{policyToAssign.name}</p>
                <p className="text-sm text-text-muted">Version {policyToAssign.version}</p>
              </div>
            )}
            
            <div className="flex items-center justify-between gap-2 flex-wrap">
              <Label className="text-sm font-medium">Select Employees</Label>
              <Button 
                type="button" 
                variant="ghost" 
                size="sm"
                onClick={selectAllUnassigned}
                className="text-primary text-xs"
              >
                Select All Unassigned
              </Button>
            </div>
            
            <div className="max-h-60 overflow-y-auto space-y-2 border border-[#E4E8EB] rounded-xl p-3">
              {employees.length === 0 ? (
                <p className="text-sm text-text-muted text-center py-4">No employees found</p>
              ) : (
                [...employees].sort((a, b) => {
                  const getPriority = (empId) => {
                    const current = policyAssignments.find(
                      item => item.policy_id === policyToAssign?.id && item.employee_id === empId && !['unassigned', 'withdrawn'].includes(item.status)
                    );
                    const latest = policyAssignments
                      .filter(item => item.policy_id === policyToAssign?.id && item.employee_id === empId)
                      .sort((first, second) => {
                        const firstDate = new Date(first.updated_at || first.withdrawn_at || first.unassigned_at || first.acknowledged_at || first.assigned_at || 0).getTime();
                        const secondDate = new Date(second.updated_at || second.withdrawn_at || second.unassigned_at || second.acknowledged_at || second.assigned_at || 0).getTime();
                        return secondDate - firstDate;
                      })[0];
                    const effective = current || latest;
                    if (!effective || ['unassigned', 'withdrawn'].includes(effective.status)) return 3;
                    if (['assigned', 'viewed'].includes(effective.status)) return 0;
                    if ((effective.status === 'acknowledged' || effective.status === 'signed') && !effective.admin_reviewed) return 1;
                    if (effective.admin_reviewed) return 2;
                    return 3;
                  };
                  return getPriority(a.id) - getPriority(b.id) || `${a.first_name} ${a.last_name}`.localeCompare(`${b.first_name} ${b.last_name}`);
                }).map((emp) => {
                  const isAlreadyAssigned = policyAssignments.some(
                    a => a.policy_id === policyToAssign?.id && 
                         a.employee_id === emp.id && 
                         !['unassigned', 'withdrawn'].includes(a.status)
                  );
                  const assignment = policyAssignments.find(
                    a => a.policy_id === policyToAssign?.id && 
                         a.employee_id === emp.id && 
                         !['unassigned', 'withdrawn'].includes(a.status)
                  );
                  const latestAssignment = policyAssignments
                    .filter(a => a.policy_id === policyToAssign?.id && a.employee_id === emp.id)
                    .sort((a, b) => {
                      const aDate = new Date(a.updated_at || a.withdrawn_at || a.unassigned_at || a.acknowledged_at || a.assigned_at || 0).getTime();
                      const bDate = new Date(b.updated_at || b.withdrawn_at || b.unassigned_at || b.acknowledged_at || b.assigned_at || 0).getTime();
                      return bDate - aDate;
                    })[0];
                  const effectiveAssignment = assignment || latestAssignment;
                  const effectiveStatus = effectiveAssignment?.status;
                  const isAcked = effectiveStatus === 'acknowledged' || effectiveStatus === 'signed';
                  const isWithdrawn = effectiveStatus === 'withdrawn';
                  const isUnassigned = effectiveStatus === 'unassigned';
                  const canDownloadAck = Boolean(effectiveAssignment?.acknowledged_at);
                  const statusLabel = effectiveAssignment?.admin_reviewed
                    ? 'Reviewed'
                    : isAcked
                      ? 'Awaiting review'
                      : effectiveStatus === 'viewed'
                        ? 'Viewed'
                        : isWithdrawn
                          ? 'Withdrawn'
                          : isUnassigned
                            ? 'Unassigned'
                            : effectiveAssignment
                              ? 'Assigned'
                              : null;
                  
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
                        onChange={() => !isAlreadyAssigned && toggleEmployeeSelection(emp.id)}
                        disabled={isAlreadyAssigned}
                        className="rounded border-[#E4E8EB] flex-shrink-0"
                      />
                      <span className="text-text-primary flex-1 truncate">
                        {emp.first_name} {emp.last_name}
                      </span>
                      {effectiveAssignment && (
                        <div className="flex items-center gap-2">
                          <span className={`text-xs px-2 py-0.5 rounded whitespace-nowrap ${
                            effectiveAssignment?.admin_reviewed
                              ? 'bg-green-100 text-green-700'
                              : isAcked
                                ? 'bg-blue-100 text-blue-700'
                              : effectiveStatus === 'viewed'
                                  ? 'bg-amber-100 text-amber-700'
                                : isWithdrawn
                                  ? 'bg-red-100 text-red-700'
                                  : isUnassigned
                                    ? 'bg-gray-100 text-gray-600'
                                    : 'bg-amber-100 text-amber-700'
                          }`}>
                            {statusLabel}
                          </span>
                          {canDownloadAck && (
                            <Button
                              type="button"
                              size="sm"
                              variant="ghost"
                              className="h-7 px-2"
                              onClick={(event) => {
                                event.preventDefault();
                                event.stopPropagation();
                                handleDownloadPolicyAcknowledgement(effectiveAssignment);
                              }}
                              title="Download acknowledgement PDF"
                            >
                              <Download className="h-3.5 w-3.5" />
                            </Button>
                          )}
                        </div>
                      )}
                      {effectiveAssignment && (
                        <span className="sr-only">
                          {effectiveAssignment.admin_reviewed
                            ? `Reviewed ${formatBackendDateTime(effectiveAssignment.admin_reviewed_at)}`
                            : effectiveAssignment.acknowledged_at
                              ? `Acknowledged ${formatBackendDateTime(effectiveAssignment.acknowledged_at)} by ${effectiveAssignment.acknowledged_by_employee_name || effectiveAssignment.employee_name || 'employee'}`
                              : effectiveAssignment.viewed_at
                                ? `Viewed ${formatBackendDateTime(effectiveAssignment.viewed_at)}`
                                : `Assigned ${formatBackendDateTime(effectiveAssignment.assigned_at)}`}
                        </span>
                      )}
                    </label>
                  );
                })
              )}
            </div>

            {policyToAssign && (
              <div className="text-xs text-text-muted bg-[#F8FAFA] border border-[#E4E8EB] rounded-lg p-2">
                Tip: pending acknowledgement rows are shown first, then acknowledgements awaiting admin review, then reviewed records. Use the download icon to open acknowledgement evidence.
              </div>
            )}
            
            <p className="text-sm text-text-muted">
              {selectedEmployees.length} employee(s) selected
            </p>
            
            <div className="flex flex-col-reverse sm:flex-row justify-end gap-3 pt-4 border-t border-[#E4E8EB]">
              <Button 
                type="button" 
                variant="outline" 
                onClick={() => { setAssignDialogOpen(false); setSelectedEmployees([]); }} 
                className="rounded-xl w-full sm:w-auto"
              >
                Cancel
              </Button>
              <Button 
                onClick={handleAssignPolicy}
                disabled={isAssigning || selectedEmployees.length === 0} 
                className="bg-primary hover:bg-primary-hover text-white rounded-xl w-full sm:w-auto"
                data-testid="assign-policy-submit"
              >
                {isAssigning ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Assign Policy'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Amendment Dialog - Edit Policy/Insurance/Incident with audit trail */}
      <Dialog open={amendDialogOpen} onOpenChange={(open) => {
        setAmendDialogOpen(open);
        if (!open) {
          setAmendRecord(null);
          setAmendType(null);
          setAmendForm({});
        }
      }}>
        <DialogContent className="max-w-lg w-[95vw] max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="font-heading text-lg pr-6">
              Edit {amendType === 'policy' ? 'Policy' : amendType === 'insurance' ? 'Certificate' : amendType === 'incident' ? 'Incident' : amendType === 'meeting' ? 'Staff Meeting' : 'Employer Audit'} Details
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 mt-4">
            <p className="text-sm text-text-muted">
              Update details below. A reason is required for audit compliance.
            </p>
            
            {/* Policy Amendment Fields */}
            {amendType === 'policy' && (
              <>
                <div className="space-y-2">
                  <Label>Policy Name</Label>
                  <Input
                    value={amendForm.name || ''}
                    onChange={(e) => setAmendForm({...amendForm, name: e.target.value})}
                    className="rounded-xl"
                  />
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="space-y-2">
                    <Label>Category</Label>
                    <Select 
                      value={amendForm.category || ''} 
                      onValueChange={(v) => setAmendForm({...amendForm, category: v})}
                    >
                      <SelectTrigger className="rounded-xl">
                        <SelectValue placeholder="Select category" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="Core">Core</SelectItem>
                        <SelectItem value="Clinical">Clinical</SelectItem>
                        <SelectItem value="Operational">Operational</SelectItem>
                        <SelectItem value="Governance">Governance</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>Version</Label>
                    <Input
                      value={amendForm.version || ''}
                      onChange={(e) => setAmendForm({...amendForm, version: e.target.value})}
                      placeholder="e.g., v2.1"
                      className="rounded-xl"
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label>Next Review Date</Label>
                  <Input
                    type="date"
                    value={amendForm.review_date || ''}
                    onChange={(e) => setAmendForm({...amendForm, review_date: e.target.value})}
                    className="rounded-xl"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Notes</Label>
                  <Textarea
                    value={amendForm.notes || ''}
                    onChange={(e) => setAmendForm({...amendForm, notes: e.target.value})}
                    placeholder="Additional notes..."
                    className="rounded-xl"
                    rows={2}
                  />
                </div>
              </>
            )}
            
            {/* Insurance/Certificate Amendment Fields */}
            {amendType === 'insurance' && (
              <>
                <div className="space-y-2">
                  <Label>Certificate Name</Label>
                  <Input
                    value={amendForm.name || ''}
                    onChange={(e) => setAmendForm({...amendForm, name: e.target.value})}
                    className="rounded-xl"
                  />
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="space-y-2">
                    {/* Conditional expiry label based on certificate type */}
                    <Label>
                      {amendRecord?.requires_expiry_date === false 
                        ? 'Expiry Date (optional)' 
                        : 'Expiry Date'}
                    </Label>
                    <Input
                      type="date"
                      value={amendForm.expiry_date || ''}
                      onChange={(e) => setAmendForm({...amendForm, expiry_date: e.target.value})}
                      className="rounded-xl"
                    />
                    {amendRecord?.valid_until_replaced && (
                      <p className="text-xs text-success flex items-center gap-1">
                        <CheckCircle className="h-3 w-3" />
                        Valid until replaced
                      </p>
                    )}
                  </div>
                  <div className="space-y-2">
                    <Label>Policy/Ref Number</Label>
                    <Input
                      value={amendForm.policy_number || ''}
                      onChange={(e) => setAmendForm({...amendForm, policy_number: e.target.value})}
                      placeholder="Reference #"
                      className="rounded-xl"
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label>Provider/Issuer</Label>
                  <Input
                    value={amendForm.provider || ''}
                    onChange={(e) => setAmendForm({...amendForm, provider: e.target.value})}
                    placeholder="e.g., Companies House, CQC"
                    className="rounded-xl"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Notes</Label>
                  <Textarea
                    value={amendForm.notes || ''}
                    onChange={(e) => setAmendForm({...amendForm, notes: e.target.value})}
                    placeholder="Additional notes..."
                    className="rounded-xl"
                    rows={2}
                  />
                </div>
              </>
            )}
            
            {/* Incident Amendment Fields */}
            {amendType === 'incident' && (
              <>
                {(amendRecord?.follow_up_due_date || amendRecord?.follow_up_status) && (
                  <div className="rounded-xl border border-blue-200 bg-blue-50 p-3 text-xs text-blue-900">
                    <p className="font-medium">Linked Follow-up</p>
                    <div className="mt-1 flex items-center gap-2 flex-wrap">
                      {getFollowUpStatusBadge(amendRecord?.follow_up_status, amendRecord?.follow_up_due_date) || <span>Status: -</span>}
                      {amendRecord?.follow_up_due_date && <span>Due: {formatBackendDate(amendRecord.follow_up_due_date)}</span>}
                    </div>
                  </div>
                )}
                <div className="space-y-2">
                  <Label>Title</Label>
                  <Input
                    value={amendForm.title || ''}
                    onChange={(e) => setAmendForm({...amendForm, title: e.target.value})}
                    className="rounded-xl"
                  />
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="space-y-2">
                    <Label>Incident Type</Label>
                    <Select 
                      value={amendForm.incident_type || ''} 
                      onValueChange={(v) => setAmendForm({...amendForm, incident_type: v})}
                    >
                      <SelectTrigger className="rounded-xl">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="incident">Incident</SelectItem>
                        <SelectItem value="outbreak">Outbreak</SelectItem>
                        <SelectItem value="near_miss">Near Miss</SelectItem>
                        <SelectItem value="complaint">Complaint</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>Date Occurred</Label>
                    <Input
                      type="date"
                      value={amendForm.date_occurred || ''}
                      onChange={(e) => setAmendForm({...amendForm, date_occurred: e.target.value})}
                      className="rounded-xl"
                    />
                  </div>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="space-y-2">
                    <Label>Status</Label>
                    <Select
                      value={amendForm.status || 'open'}
                      onValueChange={(v) => setAmendForm({ ...amendForm, status: v })}
                    >
                      <SelectTrigger className="rounded-xl">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="open">Open</SelectItem>
                        <SelectItem value="reviewing">Reviewing</SelectItem>
                        <SelectItem value="closed">Closed</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>Action / Outcome Notes</Label>
                    <Input
                      value={amendForm.action_taken || ''}
                      onChange={(e) => setAmendForm({ ...amendForm, action_taken: e.target.value })}
                      className="rounded-xl"
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label>Description</Label>
                  <Textarea
                    value={amendForm.description || ''}
                    onChange={(e) => setAmendForm({...amendForm, description: e.target.value})}
                    className="rounded-xl"
                    rows={3}
                  />
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="space-y-2">
                    <Label>Location</Label>
                    <Input
                      value={amendForm.location || ''}
                      onChange={(e) => setAmendForm({...amendForm, location: e.target.value})}
                      className="rounded-xl"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Persons Involved</Label>
                    <Input
                      value={amendForm.persons_involved || ''}
                      onChange={(e) => setAmendForm({...amendForm, persons_involved: e.target.value})}
                      className="rounded-xl"
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label>Immediate Actions Taken</Label>
                  <Textarea
                    value={amendForm.immediate_actions || ''}
                    onChange={(e) => setAmendForm({...amendForm, immediate_actions: e.target.value})}
                    className="rounded-xl"
                    rows={2}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Root Cause</Label>
                  <Textarea
                    value={amendForm.root_cause || ''}
                    onChange={(e) => setAmendForm({...amendForm, root_cause: e.target.value})}
                    className="rounded-xl"
                    rows={2}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Corrective Actions</Label>
                  <Textarea
                    value={amendForm.corrective_actions || ''}
                    onChange={(e) => setAmendForm({...amendForm, corrective_actions: e.target.value})}
                    className="rounded-xl"
                    rows={2}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Lessons Learned</Label>
                  <Textarea
                    value={amendForm.lessons_learned || ''}
                    onChange={(e) => setAmendForm({...amendForm, lessons_learned: e.target.value})}
                    className="rounded-xl"
                    rows={2}
                  />
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <label className="flex items-center gap-2 text-sm text-text-primary">
                    <input
                      type="checkbox"
                      checked={!!amendForm.safeguarding_concern}
                      onChange={(e) => setAmendForm({ ...amendForm, safeguarding_concern: e.target.checked })}
                    />
                    Safeguarding concern
                  </label>
                  <label className="flex items-center gap-2 text-sm text-text-primary">
                    <input
                      type="checkbox"
                      checked={!!amendForm.escalation_required}
                      onChange={(e) => setAmendForm({ ...amendForm, escalation_required: e.target.checked })}
                    />
                    Escalation required
                  </label>
                </div>
                <div className="space-y-3 rounded-xl border border-[#E4E8EB] p-3">
                  <label className="flex items-center gap-2 text-sm font-medium text-text-primary">
                    <input
                      type="checkbox"
                      checked={!!amendForm.is_reportable}
                      onChange={(e) => setAmendForm({
                        ...amendForm,
                        is_reportable: e.target.checked,
                        report_category: e.target.checked ? (amendForm.report_category || '') : '',
                        reported_to_authority: e.target.checked ? !!amendForm.reported_to_authority : false,
                        reported_at: e.target.checked ? (amendForm.reported_at || '') : '',
                        report_reference: e.target.checked ? (amendForm.report_reference || '') : '',
                        report_notes: e.target.checked ? (amendForm.report_notes || '') : ''
                      })}
                    />
                    Potentially reportable incident
                  </label>
                  <p className="text-xs text-text-muted">
                    Flag incidents that may be reportable (for example, RIDDOR-related) so reporting evidence is captured consistently.
                  </p>
                  {amendForm.is_reportable && (
                    <>
                      <div className="space-y-2">
                        <Label>Report Category</Label>
                        <Input
                          value={amendForm.report_category || ''}
                          onChange={(e) => setAmendForm({...amendForm, report_category: e.target.value})}
                          className="rounded-xl"
                          placeholder="e.g., injury, dangerous occurrence"
                        />
                      </div>
                      <label className="flex items-center gap-2 text-sm text-text-primary">
                        <input
                          type="checkbox"
                          checked={!!amendForm.reported_to_authority}
                          onChange={(e) => setAmendForm({
                            ...amendForm,
                            reported_to_authority: e.target.checked,
                            reported_at: e.target.checked ? (amendForm.reported_at || '') : '',
                            report_reference: e.target.checked ? (amendForm.report_reference || '') : ''
                          })}
                        />
                        Reported to authority
                      </label>
                      {amendForm.reported_to_authority && (
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                          <div className="space-y-2">
                            <Label>Reported At</Label>
                            <Input
                              type="date"
                              value={amendForm.reported_at || ''}
                              onChange={(e) => setAmendForm({...amendForm, reported_at: e.target.value})}
                              className="rounded-xl"
                            />
                          </div>
                          <div className="space-y-2">
                            <Label>Report Reference</Label>
                            <Input
                              value={amendForm.report_reference || ''}
                              onChange={(e) => setAmendForm({...amendForm, report_reference: e.target.value})}
                              className="rounded-xl"
                              placeholder="Authority reference"
                            />
                          </div>
                        </div>
                      )}
                      <div className="space-y-2">
                        <Label>Report Notes</Label>
                        <Textarea
                          value={amendForm.report_notes || ''}
                          onChange={(e) => setAmendForm({...amendForm, report_notes: e.target.value})}
                          className="rounded-xl"
                          rows={2}
                          placeholder="Internal report handling notes"
                        />
                      </div>
                    </>
                  )}
                </div>
              </>
            )}

            {/* Staff Meeting Amendment Fields */}
            {amendType === 'meeting' && (
              <>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="space-y-2">
                    <Label>Meeting Date</Label>
                    <Input
                      type="date"
                      value={amendForm.meeting_date || ''}
                      onChange={(e) => setAmendForm({ ...amendForm, meeting_date: e.target.value })}
                      className="rounded-xl"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Meeting Type</Label>
                    <Select
                      value={amendForm.meeting_type || 'monthly_staff_meeting'}
                      onValueChange={(v) => setAmendForm({ ...amendForm, meeting_type: v })}
                    >
                      <SelectTrigger className="rounded-xl">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="monthly_staff_meeting">Monthly Staff Meeting</SelectItem>
                        <SelectItem value="team_meeting">Team Meeting</SelectItem>
                        <SelectItem value="compliance_meeting">Compliance Meeting</SelectItem>
                        <SelectItem value="ad_hoc_meeting">Ad Hoc Meeting</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label>Attendees (employee_ids)</Label>
                  <div className="max-h-36 overflow-y-auto space-y-2 border border-[#E4E8EB] rounded-xl p-3">
                    {employees.map((emp) => (
                      <label key={emp.id} className="flex items-center gap-2 text-sm text-text-primary">
                        <input
                          type="checkbox"
                          checked={(amendForm.employee_ids || []).includes(emp.id)}
                          onChange={() => {
                            const current = amendForm.employee_ids || [];
                            const next = current.includes(emp.id)
                              ? current.filter(id => id !== emp.id)
                              : [...current, emp.id];
                            setAmendForm({ ...amendForm, employee_ids: next });
                          }}
                        />
                        <span>{emp.first_name} {emp.last_name}</span>
                      </label>
                    ))}
                  </div>
                </div>

                <div className="space-y-2">
                  <Label>Agenda</Label>
                  <Textarea
                    value={amendForm.agenda || ''}
                    onChange={(e) => setAmendForm({ ...amendForm, agenda: e.target.value })}
                    className="rounded-xl"
                    rows={3}
                  />
                </div>

                <div className="space-y-2">
                  <Label>Notes / Minutes</Label>
                  <Textarea
                    value={amendForm.notes || ''}
                    onChange={(e) => setAmendForm({ ...amendForm, notes: e.target.value })}
                    className="rounded-xl"
                    rows={4}
                  />
                </div>

                <div className="space-y-2">
                  <Label>Actions Required</Label>
                  <Textarea
                    value={amendForm.actions_required || ''}
                    onChange={(e) => setAmendForm({ ...amendForm, actions_required: e.target.value })}
                    className="rounded-xl"
                    rows={2}
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="space-y-2">
                    <Label>Next Meeting Date</Label>
                    <Input
                      type="date"
                      value={amendForm.next_meeting_date || ''}
                      onChange={(e) => setAmendForm({ ...amendForm, next_meeting_date: e.target.value })}
                      className="rounded-xl"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Actions Status</Label>
                    <Select
                      value={amendForm.actions_status || 'open'}
                      onValueChange={(v) => setAmendForm({ ...amendForm, actions_status: v })}
                    >
                      <SelectTrigger className="rounded-xl">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="open">Open</SelectItem>
                        <SelectItem value="closed">Closed</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </>
            )}

            {/* Employer Audit Amendment Fields */}
            {amendType === 'audit' && (
              <>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="space-y-2">
                    <Label>Audit Type</Label>
                    <Select
                      value={amendForm.audit_type || 'infection_control_audit'}
                      onValueChange={(v) => setAmendForm({ ...amendForm, audit_type: v })}
                    >
                      <SelectTrigger className="rounded-xl"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="infection_control_audit">Infection Control Audit</SelectItem>
                        <SelectItem value="medication_audit">Medication Audit</SelectItem>
                        <SelectItem value="health_and_safety_audit">Health and Safety Audit</SelectItem>
                        <SelectItem value="fire_safety_audit">Fire Safety Audit</SelectItem>
                        <SelectItem value="cleaning_audit">Cleaning Audit</SelectItem>
                        <SelectItem value="daily_records_audit">Daily Records Audit</SelectItem>
                        <SelectItem value="general_quality_audit">General Quality Audit</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>Audit Date</Label>
                    <Input
                      type="date"
                      value={amendForm.audit_date || ''}
                      onChange={(e) => setAmendForm({ ...amendForm, audit_date: e.target.value })}
                      className="rounded-xl"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="space-y-2">
                    <Label>Completed By</Label>
                    <Input
                      value={amendForm.completed_by || ''}
                      onChange={(e) => setAmendForm({ ...amendForm, completed_by: e.target.value })}
                      className="rounded-xl"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Overall Outcome</Label>
                    <Select
                      value={amendForm.overall_outcome || 'compliant'}
                      onValueChange={(v) => setAmendForm({ ...amendForm, overall_outcome: v })}
                    >
                      <SelectTrigger className="rounded-xl"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="compliant">Compliant</SelectItem>
                        <SelectItem value="partially_compliant">Partially Compliant</SelectItem>
                        <SelectItem value="non_compliant">Non-Compliant</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label>Findings</Label>
                  <Textarea
                    value={amendForm.findings || ''}
                    onChange={(e) => setAmendForm({ ...amendForm, findings: e.target.value })}
                    className="rounded-xl"
                    rows={3}
                  />
                </div>

                <div className="space-y-2">
                  <Label>Actions Required</Label>
                  <Textarea
                    value={amendForm.actions_required || ''}
                    onChange={(e) => setAmendForm({ ...amendForm, actions_required: e.target.value })}
                    className="rounded-xl"
                    rows={2}
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="space-y-2">
                    <Label>Next Review Date</Label>
                    <Input
                      type="date"
                      value={amendForm.next_review_date || ''}
                      onChange={(e) => setAmendForm({ ...amendForm, next_review_date: e.target.value })}
                      className="rounded-xl"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Status</Label>
                    <Select
                      value={amendForm.status || 'open'}
                      onValueChange={(v) => setAmendForm({ ...amendForm, status: v })}
                    >
                      <SelectTrigger className="rounded-xl"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="open">Open</SelectItem>
                        <SelectItem value="closed">Closed</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </>
            )}
            
            {/* Reason for Change - Required for all types */}
            <div className="space-y-2 pt-2 border-t border-[#E4E8EB]">
              <Label className="text-warning font-medium">Reason for Change *</Label>
              <Textarea
                value={amendForm.reason || ''}
                onChange={(e) => setAmendForm({...amendForm, reason: e.target.value})}
                placeholder="e.g., Correcting expiry date, Updating provider details, Adding missing information..."
                className="rounded-xl border-warning/50 focus:border-warning"
                rows={2}
              />
              <p className="text-xs text-text-muted">
                This will be recorded in the audit trail for CQC compliance.
              </p>
            </div>
            
            <div className="flex flex-col-reverse sm:flex-row justify-end gap-3 pt-4 border-t border-[#E4E8EB]">
              <Button 
                type="button" 
                variant="outline" 
                onClick={() => setAmendDialogOpen(false)} 
                className="rounded-xl w-full sm:w-auto"
              >
                Cancel
              </Button>
              <Button 
                onClick={handleAmendSubmit}
                disabled={isAmending || !amendForm.reason?.trim()} 
                className="bg-primary hover:bg-primary-hover text-white rounded-xl w-full sm:w-auto"
                data-testid="amend-submit-btn"
              >
                {isAmending ? <Loader2 className="h-4 w-4 animate-spin" /> : (
                  <>
                    <Save className="h-4 w-4 mr-2" />
                    Save Changes
                  </>
                )}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* History Dialog - View amendment history */}
      <Dialog open={historyDialogOpen} onOpenChange={setHistoryDialogOpen}>
        <DialogContent className="max-w-lg w-[95vw] max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="font-heading text-lg flex items-center gap-2 pr-6">
              <History className="h-5 w-5" />
              Amendment History
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 mt-4">
            {isLoadingHistory ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-primary" />
              </div>
            ) : historyData.length === 0 ? (
              <div className="text-center py-8 text-text-muted">
                <History className="h-12 w-12 mx-auto opacity-50 mb-3" />
                <p>No amendments recorded</p>
                <p className="text-xs mt-1">Changes will appear here after edits are made.</p>
              </div>
            ) : (
              <div className="space-y-3">
                {historyData.map((entry, index) => (
                  <div 
                    key={index}
                    className="p-4 bg-[#F8FAFA] rounded-xl border border-[#E4E8EB]"
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div>
                        <p className="text-sm font-medium text-text-primary">
                          Amendment #{historyData.length - index}
                        </p>
                        <p className="text-xs text-text-muted">
                          {entry.amended_at ? formatBackendDateTime(entry.amended_at) : 'Unknown date'}
                        </p>
                      </div>
                    </div>
                    <div className="space-y-2">
                      <div className="flex items-start gap-2">
                        <span className="text-xs font-medium text-warning bg-warning/10 px-2 py-0.5 rounded whitespace-nowrap">
                          Reason
                        </span>
                        <p className="text-sm text-text-primary flex-1 break-words">
                          {entry.amendment_reason || 'No reason provided'}
                        </p>
                      </div>
                      {/* Show previous values for key fields */}
                      {historyType === 'policy' && (
                        <div className="text-xs text-text-muted space-y-1 pt-2 border-t border-[#E4E8EB]">
                          {entry.name && <p className="truncate"><span className="font-medium">Name:</span> {entry.name}</p>}
                          {entry.version && <p><span className="font-medium">Version:</span> {entry.version}</p>}
                          {entry.review_date && <p><span className="font-medium">Review Date:</span> {formatBackendDate(entry.review_date)}</p>}
                        </div>
                      )}
                      {historyType === 'insurance' && (
                        <div className="text-xs text-text-muted space-y-1 pt-2 border-t border-[#E4E8EB]">
                          {entry.name && <p className="truncate"><span className="font-medium">Name:</span> {entry.name}</p>}
                          {entry.expiry_date && <p><span className="font-medium">Expiry:</span> {formatBackendDate(entry.expiry_date)}</p>}
                          {entry.provider && <p className="truncate"><span className="font-medium">Provider:</span> {entry.provider}</p>}
                          {entry.policy_number && <p><span className="font-medium">Policy #:</span> {entry.policy_number}</p>}
                        </div>
                      )}
                      {historyType === 'incident' && (
                        <div className="text-xs text-text-muted space-y-1 pt-2 border-t border-[#E4E8EB]">
                          {entry.title && <p className="truncate"><span className="font-medium">Title:</span> {entry.title}</p>}
                          {entry.incident_type && <p><span className="font-medium">Type:</span> {entry.incident_type}</p>}
                          {entry.date_occurred && <p><span className="font-medium">Date:</span> {formatBackendDate(entry.date_occurred)}</p>}
                          {entry.status && <p><span className="font-medium">Status:</span> {entry.status}</p>}
                        </div>
                      )}
                      {historyType === 'meeting' && (
                        <div className="text-xs text-text-muted space-y-1 pt-2 border-t border-[#E4E8EB]">
                          {(entry.meeting_type || entry.changes?.meeting_type) && <p><span className="font-medium">Type:</span> {entry.meeting_type || entry.changes?.meeting_type}</p>}
                          {(entry.meeting_date || entry.changes?.meeting_date) && <p><span className="font-medium">Date:</span> {formatBackendDate(entry.meeting_date || entry.changes?.meeting_date)}</p>}
                          {(entry.actions_status || entry.changes?.actions_status) && <p><span className="font-medium">Actions:</span> {entry.actions_status || entry.changes?.actions_status}</p>}
                        </div>
                      )}
                      {historyType === 'audit' && (
                        <div className="text-xs text-text-muted space-y-1 pt-2 border-t border-[#E4E8EB]">
                          {(entry.audit_type || entry.changes?.audit_type) && <p><span className="font-medium">Type:</span> {entry.audit_type || entry.changes?.audit_type}</p>}
                          {(entry.audit_date || entry.changes?.audit_date) && <p><span className="font-medium">Date:</span> {formatBackendDate(entry.audit_date || entry.changes?.audit_date)}</p>}
                          {(entry.overall_outcome || entry.changes?.overall_outcome) && <p><span className="font-medium">Outcome:</span> {entry.overall_outcome || entry.changes?.overall_outcome}</p>}
                          {(entry.status || entry.changes?.status) && <p><span className="font-medium">Status:</span> {entry.status || entry.changes?.status}</p>}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
            
            <div className="flex justify-end pt-4 border-t border-[#E4E8EB]">
              <Button 
                variant="outline" 
                onClick={() => setHistoryDialogOpen(false)} 
                className="rounded-xl"
              >
                Close
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
