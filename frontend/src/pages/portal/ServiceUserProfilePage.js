import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  ArrowLeft, User, FileText, ClipboardList, Heart, AlertTriangle,
  Pill, Stethoscope, CalendarCheck, Mail, Plus, Upload, Check,
  MoreVertical, Eye, Trash2, Edit, Phone, MapPin, Calendar,
  Building, UserCircle, Shield
} from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Textarea } from '../../components/ui/textarea';
import { Label } from '../../components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '../../components/ui/dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '../../components/ui/dropdown-menu';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../../components/ui/select';
import { toast } from 'sonner';
import FileUploader from '../../components/ui/file-uploader';
import { formatBackendDate, parseBackendDate } from '../../lib/dateUtils';
import { useAuth } from '../../context/AuthContext';
import API_BASE from '../../utils/apiBase';
import {
  fetchProtectedFileBlob,
  openBlobUrlInNewTab,
  revokeBlobUrlLater,
} from '../../lib/protectedFiles';

const API = API_BASE;
const CARE_PLAN_REQUIRED_SECTIONS = [
  'Personal information / This is me',
  'Consent and capacity',
  'Mobility and falls',
  'Nutrition and hydration',
  'Medication',
  'Personal care',
  'Mental wellbeing',
  'Health conditions',
  'Risk assessments',
  'Daily notes / monitoring link',
  'Care plan review',
];
const CARE_PLAN_SECTION_STATUS_OPTIONS = [
  { value: 'missing', label: 'Missing' },
  { value: 'draft', label: 'Draft' },
  { value: 'complete', label: 'Complete' },
  { value: 'review_due', label: 'Review Due' },
];

function normalizeCarePlanSectionStatuses(sectionStatuses) {
  return CARE_PLAN_REQUIRED_SECTIONS.reduce((accumulator, sectionName) => {
    const nextStatus = sectionStatuses?.[sectionName];
    accumulator[sectionName] = ['missing', 'draft', 'complete', 'review_due'].includes(nextStatus)
      ? nextStatus
      : 'missing';
    return accumulator;
  }, {});
}

function getCarePlanReviewBadge(reviewDueAt) {
  if (!reviewDueAt) {
    return {
      label: 'Review due not set',
      className: 'bg-gray-100 text-gray-700',
    };
  }
  const dueDate = new Date(reviewDueAt);
  if (Number.isNaN(dueDate.getTime())) {
    return {
      label: 'Review date unavailable',
      className: 'bg-gray-100 text-gray-700',
    };
  }
  if (dueDate.getTime() < Date.now()) {
    return {
      label: `Overdue since ${formatBackendDate(reviewDueAt) || reviewDueAt}`,
      className: 'bg-red-100 text-red-700',
    };
  }
  return {
    label: `Review due ${formatBackendDate(reviewDueAt) || reviewDueAt}`,
    className: 'bg-amber-100 text-amber-700',
  };
}

function getDefaultReviewFormState() {
  const reviewedAt = new Date();
  const nextReviewDueAt = new Date(reviewedAt);
  nextReviewDueAt.setDate(nextReviewDueAt.getDate() + 28);
  return {
    reviewed_at: reviewedAt.toISOString().slice(0, 10),
    next_review_due_at: nextReviewDueAt.toISOString().slice(0, 10),
    review_notes: '',
  };
}

function getOnboardingStatusStyles(status) {
  if (status === 'ready') return 'bg-green-100 text-green-700';
  if (status === 'review_due') return 'bg-amber-100 text-amber-700';
  return 'bg-red-100 text-red-700';
}

// Tab configuration matching section structure
const TABS = [
  { id: 'overview', label: 'Overview', icon: User },
  { id: '1_personal_referral', label: '1. Personal Info', icon: UserCircle },
  { id: '2_consent_contracts', label: '2. Consent', icon: Shield },
  { id: '3_assessments', label: '3. Assessments', icon: ClipboardList },
  { id: '4_care_plans', label: '4. Care Plans', icon: Heart },
  { id: '5_risk_assessments', label: '5. Risk Assessments', icon: AlertTriangle },
  { id: '6_monitoring', label: '6. Monitoring', icon: CalendarCheck },
  { id: '7_medication', label: '7. Medication', icon: Pill },
  { id: '8_health_visits', label: '8. Health Visits', icon: Stethoscope },
  { id: '9_reviews', label: '9. Reviews', icon: CalendarCheck },
  { id: '10_correspondence', label: '10. Letters', icon: Mail },
  { id: '11_daily_notes', label: '11. Daily Notes', icon: FileText },
];

export default function ServiceUserProfilePage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { isManagerOrAdmin } = useAuth();
  const [serviceUser, setServiceUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('overview');

  const handleViewUploadedDocument = async (doc) => {
    if (!doc?.file_url) {
      toast.error('Document URL not available');
      return;
    }

    try {
      const token = localStorage.getItem('token');
      const { blobUrl } = await fetchProtectedFileBlob(doc.file_url, token);
      openBlobUrlInNewTab(blobUrl, doc.file_name || doc.title || 'document');
      revokeBlobUrlLater(blobUrl);
    } catch (error) {
      toast.error('Failed to open document');
    }
  };
  const [showUploadDialog, setShowUploadDialog] = useState(false);
  const [showEditDialog, setShowEditDialog] = useState(false);
  const [uploadSection, setUploadSection] = useState(null);
  const [sections, setSections] = useState([]);
  
  const [uploadForm, setUploadForm] = useState({
    title: '',
    document_type: '',
    notes: '',
    expiry_date: '',
    file_url: '',
    file_name: '',
  });
  
  const [editForm, setEditForm] = useState({});
  const [carePlans, setCarePlans] = useState([]);
  const [carePlansLoading, setCarePlansLoading] = useState(false);
  const [carePlansLoaded, setCarePlansLoaded] = useState(false);
  const [createCarePlanForm, setCreateCarePlanForm] = useState({
    care_plan_title: '',
    goals: '',
    needs_summary: '',
    support_instructions: '',
    effective_from: '',
    review_due_at: '',
  });
  const [editingDraftId, setEditingDraftId] = useState(null);
  const [editCarePlanForm, setEditCarePlanForm] = useState({
    care_plan_title: '',
    goals: '',
    needs_summary: '',
    support_instructions: '',
    effective_from: '',
    review_due_at: '',
  });
  const [recordReviewOpen, setRecordReviewOpen] = useState(false);
  const [recordReviewForm, setRecordReviewForm] = useState(getDefaultReviewFormState());
  const [dailyNotes, setDailyNotes] = useState([]);
  const [dailyNotesLoading, setDailyNotesLoading] = useState(false);
  const [dailyNotesLoaded, setDailyNotesLoaded] = useState(false);
  const [onboardingReadiness, setOnboardingReadiness] = useState(null);
  const [onboardingLoading, setOnboardingLoading] = useState(false);

  useEffect(() => {
    fetchServiceUser();
    fetchSections();
    fetchOnboardingReadiness();
  }, [id]);

  useEffect(() => {
    if (activeTab === '4_care_plans' && isManagerOrAdmin() && !carePlansLoaded) {
      fetchCarePlans();
    }
  }, [activeTab, id, carePlansLoaded, isManagerOrAdmin]);

  useEffect(() => {
    if (activeTab === '11_daily_notes' && isManagerOrAdmin() && !dailyNotesLoaded) {
      fetchDailyNotes();
    }
  }, [activeTab, id, dailyNotesLoaded, isManagerOrAdmin]);

  const fetchServiceUser = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API}/service-users/${id}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.ok) {
        const data = await response.json();
        setServiceUser(data);
        setEditForm(data);
      } else {
        toast.error('Service user not found');
        navigate('/portal/service-users');
      }
    } catch (error) {
      console.error('Error fetching service user:', error);
      toast.error('Failed to load service user');
    } finally {
      setLoading(false);
    }
  };

  const fetchSections = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API}/service-users/sections`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.ok) {
        const data = await response.json();
        setSections(data);
      }
    } catch (error) {
      console.error('Error fetching sections:', error);
    }
  };

  const fetchDailyNotes = async () => {
    setDailyNotesLoading(true);
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API}/service-users/${id}/daily-notes`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setDailyNotes(data.daily_notes || []);
        setDailyNotesLoaded(true);
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to load daily notes');
      }
    } catch (error) {
      console.error('Error loading daily notes:', error);
      toast.error('Failed to load daily notes');
    } finally {
      setDailyNotesLoading(false);
    }
  };

  const fetchOnboardingReadiness = async () => {
    setOnboardingLoading(true);
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API}/service-users/${id}/onboarding-readiness`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setOnboardingReadiness(data);
      } else {
        const error = await response.json().catch(() => ({}));
        console.error('Failed to load onboarding readiness:', error);
        setOnboardingReadiness(null);
      }
    } catch (error) {
      console.error('Error loading onboarding readiness:', error);
      setOnboardingReadiness(null);
    } finally {
      setOnboardingLoading(false);
    }
  };

  const handleUploadDocument = async (e) => {
    e.preventDefault();
    
    if (!uploadForm.title || !uploadForm.file_url) {
      toast.error('Please provide a title and upload a file');
      return;
    }

    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API}/service-users/${id}/documents`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          section_id: uploadSection,
          ...uploadForm
        })
      });

      if (response.ok) {
        toast.success('Document uploaded successfully');
        setShowUploadDialog(false);
        setUploadForm({
          title: '',
          document_type: '',
          notes: '',
          expiry_date: '',
          file_url: '',
          file_name: '',
        });
        fetchServiceUser();
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to upload document');
      }
    } catch (error) {
      console.error('Error uploading document:', error);
      toast.error('Failed to upload document');
    }
  };

  const handleVerifyDocument = async (documentId) => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API}/service-users/${id}/documents/${documentId}/verify`, {
        method: 'PUT',
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.ok) {
        toast.success('Document verified');
        fetchServiceUser();
      }
    } catch (error) {
      toast.error('Failed to verify document');
    }
  };

  const handleDeleteDocument = async (documentId) => {
    if (!window.confirm('Are you sure you want to delete this document?')) return;
    
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API}/service-users/${id}/documents/${documentId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.ok) {
        toast.success('Document deleted');
        fetchServiceUser();
      }
    } catch (error) {
      toast.error('Failed to delete document');
    }
  };

  const handleUpdateServiceUser = async (e) => {
    e.preventDefault();
    
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API}/service-users/${id}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(editForm)
      });

      if (response.ok) {
        toast.success('Service user updated');
        setShowEditDialog(false);
        fetchServiceUser();
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to update');
      }
    } catch (error) {
      toast.error('Failed to update service user');
    }
  };

  const openUploadDialog = (sectionId) => {
    setUploadSection(sectionId);
    setShowUploadDialog(true);
  };

  const resetCreateCarePlanForm = () => {
    setCreateCarePlanForm({
      care_plan_title: '',
      goals: '',
      needs_summary: '',
      support_instructions: '',
      effective_from: '',
      review_due_at: '',
    });
  };

  const mapPlanToEditForm = (plan) => {
    setEditCarePlanForm({
      care_plan_title: plan?.care_plan_title || '',
      goals: Array.isArray(plan?.goals) ? plan.goals.join('\n') : '',
      needs_summary: plan?.needs_summary || '',
      support_instructions: plan?.support_instructions || '',
      effective_from: plan?.effective_from?.slice(0, 10) || '',
      review_due_at: plan?.review_due_at?.slice(0, 10) || '',
    });
  };

  const parseGoalsInput = (goalsInput) => {
    return (goalsInput || '')
      .split(/\n|,/)
      .map((goal) => goal.trim())
      .filter(Boolean);
  };

  const normalizeCarePlanPayload = (formState) => {
    return {
      care_plan_title: (formState.care_plan_title || '').trim(),
      goals: parseGoalsInput(formState.goals),
      needs_summary: (formState.needs_summary || '').trim(),
      support_instructions: (formState.support_instructions || '').trim(),
      effective_from: formState.effective_from || null,
      review_due_at: formState.review_due_at || null,
    };
  };

  const fetchCarePlans = async () => {
    if (!isManagerOrAdmin()) {
      return;
    }
    setCarePlansLoading(true);
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API}/service-users/${id}/care-plans?include_archived=true`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setCarePlans(Array.isArray(data) ? data : []);
        setCarePlansLoaded(true);
      } else {
        const error = await response.json().catch(() => ({}));
        toast.error(error.detail || 'Failed to load care plans');
      }
    } catch (error) {
      console.error('Error loading care plans:', error);
      toast.error('Failed to load care plans');
    } finally {
      setCarePlansLoading(false);
    }
  };

  const replaceCarePlanInState = (updatedPlan) => {
    setCarePlans((prev) => prev.map((plan) => (plan.id === updatedPlan.id ? updatedPlan : plan)));
  };

  const handleCreateCarePlanDraft = async (e) => {
    e.preventDefault();
    const payload = normalizeCarePlanPayload(createCarePlanForm);
    if (!payload.care_plan_title) {
      toast.error('Care plan title is required');
      return;
    }

    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API}/service-users/${id}/care-plans`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });
      if (response.ok) {
        toast.success('Draft care plan created');
        resetCreateCarePlanForm();
        await fetchCarePlans();
      } else {
        const error = await response.json().catch(() => ({}));
        toast.error(error.detail || 'Failed to create draft care plan');
      }
    } catch (error) {
      console.error('Error creating draft care plan:', error);
      toast.error('Failed to create draft care plan');
    }
  };

  const beginEditDraft = (plan) => {
    setEditingDraftId(plan.id);
    mapPlanToEditForm(plan);
  };

  const cancelEditDraft = () => {
    setEditingDraftId(null);
    setEditCarePlanForm({
      care_plan_title: '',
      goals: '',
      needs_summary: '',
      support_instructions: '',
      effective_from: '',
      review_due_at: '',
    });
  };

  const handleSaveDraftEdit = async (carePlanId) => {
    const payload = normalizeCarePlanPayload(editCarePlanForm);
    if (!payload.care_plan_title) {
      toast.error('Care plan title is required');
      return;
    }

    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API}/service-users/${id}/care-plans/${carePlanId}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });
      if (response.ok) {
        toast.success('Draft care plan updated');
        cancelEditDraft();
        await fetchCarePlans();
      } else {
        const error = await response.json().catch(() => ({}));
        toast.error(error.detail || 'Failed to update draft care plan');
      }
    } catch (error) {
      console.error('Error updating draft care plan:', error);
      toast.error('Failed to update draft care plan');
    }
  };

  const handleActivateDraft = async (carePlanId) => {
    if (!window.confirm('Activate this draft care plan? This will supersede any currently active version.')) {
      return;
    }
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API}/service-users/${id}/care-plans/${carePlanId}/activate`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (response.ok) {
        toast.success('Care plan activated');
        await fetchCarePlans();
      } else {
        const error = await response.json().catch(() => ({}));
        toast.error(error.detail || 'Failed to activate care plan');
      }
    } catch (error) {
      console.error('Error activating care plan:', error);
      toast.error('Failed to activate care plan');
    }
  };

  const handleArchivePlan = async (carePlanId) => {
    if (!window.confirm('Archive this care plan version?')) {
      return;
    }
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API}/service-users/${id}/care-plans/${carePlanId}/archive`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({}),
      });
      if (response.ok) {
        toast.success('Care plan archived');
        await fetchCarePlans();
      } else {
        const error = await response.json().catch(() => ({}));
        toast.error(error.detail || 'Failed to archive care plan');
      }
    } catch (error) {
      console.error('Error archiving care plan:', error);
      toast.error('Failed to archive care plan');
    }
  };

  const handleDownloadCarePlanPdf = async (plan) => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API}/service-users/${id}/care-plans/${plan.id}/download-pdf`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        toast.error(error.detail || 'Failed to download care-plan PDF');
        return;
      }

      const blob = await response.blob();
      const disposition = response.headers.get('Content-Disposition') || '';
      const filenameMatch = disposition.match(/filename="?([^\"]+)"?/i);
      const fallbackName = `care_plan_v${plan.version_number || '0'}_${plan.id}.pdf`;
      const filename = filenameMatch?.[1] || fallbackName;

      const objectUrl = window.URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = objectUrl;
      anchor.download = filename;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      window.URL.revokeObjectURL(objectUrl);
      toast.success('Care-plan PDF downloaded');
    } catch (error) {
      console.error('Error downloading care-plan PDF:', error);
      toast.error('Failed to download care-plan PDF');
    }
  };

  const handleUpdateCarePlanSectionStatus = async (carePlanId, sectionName, status) => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API}/service-users/${id}/care-plans/${carePlanId}/section-status`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ section_name: sectionName, status }),
      });
      if (response.ok) {
        const updated = await response.json();
        replaceCarePlanInState(updated);
        toast.success('Care plan section updated');
      } else {
        const error = await response.json().catch(() => ({}));
        toast.error(error.detail || 'Failed to update care plan section');
      }
    } catch (error) {
      console.error('Error updating care plan section:', error);
      toast.error('Failed to update care plan section');
    }
  };

  const handleRecordCarePlanReview = async (carePlanId) => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API}/service-users/${id}/care-plans/${carePlanId}/record-review`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          reviewed_at: recordReviewForm.reviewed_at || null,
          next_review_due_at: recordReviewForm.next_review_due_at || null,
          review_notes: recordReviewForm.review_notes || '',
        }),
      });
      if (response.ok) {
        const updated = await response.json();
        replaceCarePlanInState(updated);
        setRecordReviewOpen(false);
        setRecordReviewForm(getDefaultReviewFormState());
        toast.success('Care plan review recorded');
      } else {
        const error = await response.json().catch(() => ({}));
        toast.error(error.detail || 'Failed to record care plan review');
      }
    } catch (error) {
      console.error('Error recording care plan review:', error);
      toast.error('Failed to record care plan review');
    }
  };

  // HARDENING: Use parseBackendDate for safe age calculation
  const calculateAge = (dob) => {
    if (!dob) return null;
    const birth = parseBackendDate(dob);
    if (!birth) return null;
    const today = new Date();
    let age = today.getFullYear() - birth.getFullYear();
    const monthDiff = today.getMonth() - birth.getMonth();
    if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birth.getDate())) {
      age--;
    }
    return age;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (!serviceUser) {
    return (
      <div className="text-center py-12">
        <p className="text-text-muted">Service user not found</p>
        <Button onClick={() => navigate('/portal/service-users')} className="mt-4">
          Back to Service Users
        </Button>
      </div>
    );
  }

  const currentSection = serviceUser.sections?.[activeTab];

  return (
    <div className="space-y-6" data-testid="service-user-profile-page">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={() => navigate('/portal/service-users')}>
            <ArrowLeft className="h-4 w-4 mr-1" />
            Back
          </Button>
          
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center">
              <span className="text-xl font-bold text-primary">
                {serviceUser.full_name?.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase()}
              </span>
            </div>
            <div>
              <h1 className="text-2xl font-bold text-text-primary">{serviceUser.full_name}</h1>
              <div className="flex items-center gap-3 text-sm text-text-muted mt-1">
                <span className="font-mono">{serviceUser.service_user_code}</span>
                {serviceUser.date_of_birth && (
                  <span>{calculateAge(serviceUser.date_of_birth)} years old</span>
                )}
                {serviceUser.nhs_number && (
                  <span className="font-mono">NHS: {serviceUser.nhs_number}</span>
                )}
              </div>
            </div>
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          <span className={`px-3 py-1 rounded-full text-sm font-medium ${
            serviceUser.status === 'inactive' ? 'bg-gray-100 text-gray-600' : 'bg-green-100 text-green-700'
          }`}>
            {serviceUser.status || 'Active'}
          </span>
          <Button variant="outline" onClick={() => setShowEditDialog(true)}>
            <Edit className="h-4 w-4 mr-2" />
            Edit Details
          </Button>
        </div>
      </div>

      {/* Readiness + Next Actions */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <div className="xl:col-span-2">
          <OnboardingReadinessCard
            readiness={onboardingReadiness}
            loading={onboardingLoading}
            onRefresh={fetchOnboardingReadiness}
            onOpenTarget={(targetTab) => setActiveTab(targetTab || 'overview')}
          />
        </div>
        <NextActionsCard
          readiness={onboardingReadiness}
          serviceUserId={id}
          onOpenTab={setActiveTab}
          onNavigate={navigate}
        />
      </div>

      {/* Tab Navigation */}
      <div className="flex gap-1 overflow-x-auto pb-2 border-b border-gray-200">
        {TABS.map((tab) => {
          const Icon = tab.icon;
          const docCount = tab.id !== 'overview' ? serviceUser.sections?.[tab.id]?.document_count || 0 : null;
          
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-t-lg text-sm font-medium whitespace-nowrap transition-colors ${
                activeTab === tab.id
                  ? 'bg-primary text-white'
                  : 'text-text-muted hover:bg-gray-100'
              }`}
              data-testid={`tab-${tab.id}`}
            >
              <Icon className="h-4 w-4" />
              {tab.label}
              {docCount !== null && docCount > 0 && (
                <span className={`px-1.5 py-0.5 rounded-full text-xs ${
                  activeTab === tab.id ? 'bg-white/20' : 'bg-gray-200'
                }`}>
                  {docCount}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Tab Content */}
      <div className="bg-white rounded-xl border border-gray-100 p-6">
        {activeTab === 'overview' ? (
          <OverviewTab serviceUser={serviceUser} onOpenSection={setActiveTab} serviceUserId={id} />
        ) : activeTab === '4_care_plans' ? (
          <CarePlansTab
            carePlans={carePlans}
            carePlansLoading={carePlansLoading}
            canManageCarePlans={isManagerOrAdmin()}
            createCarePlanForm={createCarePlanForm}
            setCreateCarePlanForm={setCreateCarePlanForm}
            onCreateDraft={handleCreateCarePlanDraft}
            editingDraftId={editingDraftId}
            editCarePlanForm={editCarePlanForm}
            setEditCarePlanForm={setEditCarePlanForm}
            onBeginEditDraft={beginEditDraft}
            onCancelEditDraft={cancelEditDraft}
            onSaveDraftEdit={handleSaveDraftEdit}
            onActivateDraft={handleActivateDraft}
            onArchivePlan={handleArchivePlan}
            onDownloadPdf={handleDownloadCarePlanPdf}
            onUpdateSectionStatus={handleUpdateCarePlanSectionStatus}
            recordReviewOpen={recordReviewOpen}
            setRecordReviewOpen={setRecordReviewOpen}
            recordReviewForm={recordReviewForm}
            setRecordReviewForm={setRecordReviewForm}
            onRecordReview={handleRecordCarePlanReview}
            onRefresh={fetchCarePlans}
          />
        ) : activeTab === '11_daily_notes' ? (
          <DailyNotesTimelineTab
            notes={dailyNotes}
            loading={dailyNotesLoading}
            canManage={isManagerOrAdmin()}
            onRefresh={fetchDailyNotes}
          />
        ) : (
          <SectionTab
            section={currentSection}
            sectionId={activeTab}
            onUpload={() => openUploadDialog(activeTab)}
            onVerify={handleVerifyDocument}
            onDelete={handleDeleteDocument}
          />
        )}
      </div>

      {/* Upload Document Dialog */}
      <Dialog open={showUploadDialog} onOpenChange={setShowUploadDialog}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Upload Document</DialogTitle>
            <DialogDescription>
              Add a document to {serviceUser.sections?.[uploadSection]?.name || 'this section'}
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleUploadDocument} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="doc_title">Document Title *</Label>
              <Input
                id="doc_title"
                value={uploadForm.title}
                onChange={(e) => setUploadForm({...uploadForm, title: e.target.value})}
                placeholder="e.g., Initial Care Assessment"
                required
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="doc_type">Document Type</Label>
              <Select
                value={uploadForm.document_type}
                onValueChange={(val) => setUploadForm({...uploadForm, document_type: val})}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select type" />
                </SelectTrigger>
                <SelectContent>
                  {serviceUser.sections?.[uploadSection]?.document_types?.map((type) => (
                    <SelectItem key={type} value={type}>
                      {type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                    </SelectItem>
                  ))}
                  <SelectItem value="other">Other</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            <div className="space-y-2">
              <Label>Upload File *</Label>
              <FileUploader
                onUploadComplete={(url, fileName) => {
                  setUploadForm({...uploadForm, file_url: url, file_name: fileName});
                  toast.success('File uploaded');
                }}
                acceptedTypes={['application/pdf', 'image/*', '.doc', '.docx']}
              />
              {uploadForm.file_name && (
                <p className="text-sm text-green-600">Uploaded: {uploadForm.file_name}</p>
              )}
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="doc_expiry">Expiry Date (optional)</Label>
              <Input
                id="doc_expiry"
                type="date"
                value={uploadForm.expiry_date}
                onChange={(e) => setUploadForm({...uploadForm, expiry_date: e.target.value})}
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="doc_notes">Notes</Label>
              <Textarea
                id="doc_notes"
                value={uploadForm.notes}
                onChange={(e) => setUploadForm({...uploadForm, notes: e.target.value})}
                placeholder="Additional notes about this document"
                rows={3}
              />
            </div>
            
            <div className="flex justify-end gap-3 pt-4">
              <Button type="button" variant="outline" onClick={() => setShowUploadDialog(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={!uploadForm.file_url}>
                <Upload className="h-4 w-4 mr-2" />
                Upload Document
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      {/* Edit Service User Dialog */}
      <Dialog open={showEditDialog} onOpenChange={setShowEditDialog}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Edit Service User Details</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleUpdateServiceUser} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Full Name</Label>
                <Input
                  value={editForm.full_name || ''}
                  onChange={(e) => setEditForm({...editForm, full_name: e.target.value})}
                />
              </div>
              <div className="space-y-2">
                <Label>Date of Birth</Label>
                <Input
                  type="date"
                  value={editForm.date_of_birth || ''}
                  onChange={(e) => setEditForm({...editForm, date_of_birth: e.target.value})}
                />
              </div>
              <div className="space-y-2">
                <Label>NHS Number</Label>
                <Input
                  value={editForm.nhs_number || ''}
                  onChange={(e) => setEditForm({...editForm, nhs_number: e.target.value})}
                />
              </div>
              <div className="space-y-2">
                <Label>Phone</Label>
                <Input
                  value={editForm.phone || ''}
                  onChange={(e) => setEditForm({...editForm, phone: e.target.value})}
                />
              </div>
              <div className="space-y-2">
                <Label>Email</Label>
                <Input
                  type="email"
                  value={editForm.email || ''}
                  onChange={(e) => setEditForm({...editForm, email: e.target.value})}
                />
              </div>
              <div className="space-y-2">
                <Label>Status</Label>
                <Select
                  value={editForm.status || 'active'}
                  onValueChange={(val) => setEditForm({...editForm, status: val})}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="active">Active</SelectItem>
                    <SelectItem value="inactive">Inactive</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            
            <div className="pt-4 border-t">
              <p className="text-sm font-medium text-text-primary mb-3">Address</p>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2 col-span-2">
                  <Label>Address Line 1</Label>
                  <Input
                    value={editForm.address_line_1 || ''}
                    onChange={(e) => setEditForm({...editForm, address_line_1: e.target.value})}
                  />
                </div>
                <div className="space-y-2 col-span-2">
                  <Label>Address Line 2</Label>
                  <Input
                    value={editForm.address_line_2 || ''}
                    onChange={(e) => setEditForm({...editForm, address_line_2: e.target.value})}
                  />
                </div>
                <div className="space-y-2">
                  <Label>City</Label>
                  <Input
                    value={editForm.city || ''}
                    onChange={(e) => setEditForm({...editForm, city: e.target.value})}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Postcode</Label>
                  <Input
                    value={editForm.postcode || ''}
                    onChange={(e) => setEditForm({...editForm, postcode: e.target.value})}
                  />
                </div>
              </div>
            </div>
            
            <div className="pt-4 border-t">
              <p className="text-sm font-medium text-text-primary mb-3">Emergency Contact</p>
              <div className="grid grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label>Name</Label>
                  <Input
                    value={editForm.emergency_contact_name || ''}
                    onChange={(e) => setEditForm({...editForm, emergency_contact_name: e.target.value})}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Phone</Label>
                  <Input
                    value={editForm.emergency_contact_phone || ''}
                    onChange={(e) => setEditForm({...editForm, emergency_contact_phone: e.target.value})}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Relationship</Label>
                  <Input
                    value={editForm.emergency_contact_relationship || ''}
                    onChange={(e) => setEditForm({...editForm, emergency_contact_relationship: e.target.value})}
                  />
                </div>
              </div>
            </div>
            
            <div className="pt-4 border-t">
              <p className="text-sm font-medium text-text-primary mb-3">GP Details</p>
              <div className="grid grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label>GP Name</Label>
                  <Input
                    value={editForm.gp_name || ''}
                    onChange={(e) => setEditForm({...editForm, gp_name: e.target.value})}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Surgery</Label>
                  <Input
                    value={editForm.gp_surgery || ''}
                    onChange={(e) => setEditForm({...editForm, gp_surgery: e.target.value})}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Phone</Label>
                  <Input
                    value={editForm.gp_phone || ''}
                    onChange={(e) => setEditForm({...editForm, gp_phone: e.target.value})}
                  />
                </div>
              </div>
            </div>
            
            <div className="space-y-2">
              <Label>Notes</Label>
              <Textarea
                value={editForm.notes || ''}
                onChange={(e) => setEditForm({...editForm, notes: e.target.value})}
                rows={3}
              />
            </div>
            
            <div className="flex justify-end gap-3 pt-4">
              <Button type="button" variant="outline" onClick={() => setShowEditDialog(false)}>
                Cancel
              </Button>
              <Button type="submit">Save Changes</Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function OnboardingReadinessCard({ readiness, loading, onRefresh, onOpenTarget }) {
  const rows = readiness?.rows || [];
  const overallStatus = readiness?.overall_status || 'missing';
  const counts = readiness?.counts || { total: 0, ready: 0, missing: 0, review_due: 0 };

  return (
    <div className="p-4 rounded-lg bg-gray-50 border border-gray-100">
      <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
        <div>
          <h3 className="text-sm font-semibold text-text-primary">Onboarding Readiness</h3>
          <p className="text-xs text-text-muted">Read-only checklist using existing care-plan and section records.</p>
        </div>
        <div className="flex items-center gap-2">
          <span className={`px-2 py-0.5 rounded text-xs font-medium ${getOnboardingStatusStyles(overallStatus)}`}>
            {overallStatus === 'ready' ? 'Ready' : overallStatus === 'review_due' ? 'Review Due' : 'Missing'}
          </span>
          <Button variant="outline" size="sm" onClick={onRefresh}>
            Refresh
          </Button>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2 mb-3 text-xs text-text-muted">
        <span className="px-2 py-0.5 rounded bg-white border border-gray-200">Total: {counts.total || 0}</span>
        <span className="px-2 py-0.5 rounded bg-green-100 text-green-700">Ready: {counts.ready || 0}</span>
        <span className="px-2 py-0.5 rounded bg-red-100 text-red-700">Missing: {counts.missing || 0}</span>
        <span className="px-2 py-0.5 rounded bg-amber-100 text-amber-700">Review Due: {counts.review_due || 0}</span>
      </div>

      {loading ? (
        <p className="text-sm text-text-muted">Loading onboarding readiness...</p>
      ) : rows.length === 0 ? (
        <p className="text-sm text-text-muted">No onboarding checklist available.</p>
      ) : (
        <div className="space-y-2">
          {rows.map((row) => (
            <div key={row.key} className="flex items-start justify-between gap-3 rounded-md border border-gray-200 bg-white p-3">
              <div className="min-w-0">
                <p className="text-sm font-medium text-text-primary">{row.label}</p>
                <p className="text-xs text-text-muted mt-0.5">{row.reason || '-'}</p>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <span className={`px-2 py-0.5 rounded text-xs font-medium ${getOnboardingStatusStyles(row.status)}`}>
                  {row.status === 'ready' ? 'Ready' : row.status === 'review_due' ? 'Review Due' : 'Missing'}
                </span>
                {row.target_tab ? (
                  <Button size="sm" variant="outline" onClick={() => onOpenTarget(row.target_tab)}>
                    Open
                  </Button>
                ) : null}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function NextActionsCard({ readiness, serviceUserId, onOpenTab, onNavigate }) {
  const encodedServiceUserId = encodeURIComponent(serviceUserId || '');
  const actionableOnboardingRow = (readiness?.rows || []).find((row) => (
    ['missing', 'review_due'].includes(row?.status) && !!row?.target_tab
  ));

  return (
    <div className="p-4 rounded-lg bg-gray-50 border border-gray-100">
      <div className="mb-3">
        <h3 className="text-sm font-semibold text-text-primary">Next Actions</h3>
        <p className="text-xs text-text-muted">Quick operational steps for first-client readiness.</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-1 gap-2">
        <Button
          size="sm"
          variant="outline"
          className="justify-start"
          disabled={!actionableOnboardingRow}
          onClick={() => onOpenTab(actionableOnboardingRow?.target_tab || 'overview')}
        >
          Complete missing onboarding item
        </Button>

        <Button
          size="sm"
          variant="outline"
          className="justify-start"
          onClick={() => onOpenTab('4_care_plans')}
        >
          Create/update care plan
        </Button>

        <Button
          size="sm"
          variant="outline"
          className="justify-start"
          onClick={() => onNavigate(`/portal/shifts?service_user_id=${encodedServiceUserId}`)}
        >
          Create service-user shift
        </Button>

        <Button
          size="sm"
          variant="outline"
          className="justify-start"
          onClick={() => onOpenTab('11_daily_notes')}
        >
          View daily notes
        </Button>

        <Button
          size="sm"
          variant="outline"
          className="justify-start"
          onClick={() => onNavigate(`/portal/compliance-centre?tab=incidents&service_user_id=${encodedServiceUserId}`)}
        >
          View incidents
        </Button>
      </div>

      {!actionableOnboardingRow ? (
        <p className="text-xs text-text-muted mt-2">No onboarding follow-up needed.</p>
      ) : null}
    </div>
  );
}

// Overview Tab Component
function OverviewTab({ serviceUser, onOpenSection, serviceUserId }) {
  const encodedServiceUserId = encodeURIComponent(serviceUserId || '');
  const [bodyMaps, setBodyMaps] = useState([]);
  const [bodyMapsLoading, setBodyMapsLoading] = useState(false);

  useEffect(() => {
    if (!serviceUserId) return;
    const token = localStorage.getItem('token');
    if (!token) return;
    setBodyMapsLoading(true);
    fetch(`${API}/service-users/${serviceUserId}/body-maps`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(r => r.ok ? r.json() : [])
      .then(data => setBodyMaps(Array.isArray(data) ? data : []))
      .catch(() => setBodyMaps([]))
      .finally(() => setBodyMapsLoading(false));
  }, [serviceUserId]);

  const handleDownloadBodyMapPdf = (id) => {
    const token = localStorage.getItem('token');
    fetch(`${API}/compliance/body-maps/${id}/pdf`, {
      headers: { Authorization: `Bearer ${token}` },
    }).then(r => r.blob()).then(blob => {
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `body_map_${id}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    }).catch(() => {});
  };

  return (
    <div className="space-y-6">
      {/* Quick Info Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Personal Info Card */}
        <div className="p-4 rounded-lg bg-gray-50 border border-gray-100">
          <h3 className="text-sm font-semibold text-text-primary mb-3 flex items-center gap-2">
            <User className="h-4 w-4" />
            Personal Information
          </h3>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-text-muted">Date of Birth</span>
              <span className="text-text-primary">{serviceUser.date_of_birth || '-'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-muted">NHS Number</span>
              <span className="text-text-primary font-mono">{serviceUser.nhs_number || '-'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-muted">Phone</span>
              <span className="text-text-primary">{serviceUser.phone || '-'}</span>
            </div>
          </div>
        </div>
        
        {/* Address Card */}
        <div className="p-4 rounded-lg bg-gray-50 border border-gray-100">
          <h3 className="text-sm font-semibold text-text-primary mb-3 flex items-center gap-2">
            <MapPin className="h-4 w-4" />
            Address
          </h3>
          <div className="text-sm text-text-primary space-y-1">
            {serviceUser.address_line_1 && <p>{serviceUser.address_line_1}</p>}
            {serviceUser.address_line_2 && <p>{serviceUser.address_line_2}</p>}
            {(serviceUser.city || serviceUser.postcode) && (
              <p>{[serviceUser.city, serviceUser.postcode].filter(Boolean).join(', ')}</p>
            )}
            {!serviceUser.address_line_1 && <p className="text-text-muted">No address recorded</p>}
          </div>
        </div>
        
        {/* Emergency Contact Card */}
        <div className="p-4 rounded-lg bg-gray-50 border border-gray-100">
          <h3 className="text-sm font-semibold text-text-primary mb-3 flex items-center gap-2">
            <Phone className="h-4 w-4" />
            Emergency Contact
          </h3>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-text-muted">Name</span>
              <span className="text-text-primary">{serviceUser.emergency_contact_name || '-'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-muted">Phone</span>
              <span className="text-text-primary">{serviceUser.emergency_contact_phone || '-'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-muted">Relationship</span>
              <span className="text-text-primary">{serviceUser.emergency_contact_relationship || '-'}</span>
            </div>
          </div>
        </div>
      </div>
      
      {/* GP Details */}
      {(serviceUser.gp_name || serviceUser.gp_surgery) && (
        <div className="p-4 rounded-lg bg-blue-50 border border-blue-100">
          <h3 className="text-sm font-semibold text-text-primary mb-3 flex items-center gap-2">
            <Building className="h-4 w-4" />
            GP Details
          </h3>
          <div className="grid grid-cols-3 gap-4 text-sm">
            <div>
              <span className="text-text-muted">GP Name</span>
              <p className="text-text-primary font-medium">{serviceUser.gp_name || '-'}</p>
            </div>
            <div>
              <span className="text-text-muted">Surgery</span>
              <p className="text-text-primary font-medium">{serviceUser.gp_surgery || '-'}</p>
            </div>
            <div>
              <span className="text-text-muted">Phone</span>
              <p className="text-text-primary font-medium">{serviceUser.gp_phone || '-'}</p>
            </div>
          </div>
        </div>
      )}
      
      {/* File Sections Overview */}
      <div>
        <h3 className="text-lg font-semibold text-text-primary mb-4">Care File Sections</h3>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          {Object.entries(serviceUser.sections || {}).map(([sectionId, section]) => (
            <button
              key={sectionId}
              onClick={() => onOpenSection(sectionId)}
              className="p-4 rounded-lg bg-white border border-gray-200 hover:border-primary hover:bg-primary/5 transition-all text-left"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold text-primary">
                  Section {section.section_number}
                </span>
                <span className={`text-xs px-2 py-0.5 rounded-full ${
                  section.document_count > 0 ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
                }`}>
                  {section.document_count} docs
                </span>
              </div>
              <p className="text-sm font-medium text-text-primary truncate">{section.name}</p>
            </button>
          ))}
        </div>
      </div>

      {/* Related Operational Records (read-only links) */}
      <div className="p-4 rounded-lg bg-blue-50 border border-blue-100">
        <h3 className="text-sm font-semibold text-text-primary mb-1">Related Operational Records</h3>
        <p className="text-xs text-text-muted mb-3">Opens filtered operational records for this service user.</p>
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-2">
          <a
            href={`/portal/compliance-centre?tab=incidents&service_user_id=${encodedServiceUserId}`}
            className="inline-flex items-center justify-center rounded-md border border-blue-200 bg-white px-3 py-2 text-sm font-medium text-blue-700 hover:bg-blue-50"
          >
            Incidents
          </a>
          <a
            href={`/portal/shifts?service_user_id=${encodedServiceUserId}`}
            className="inline-flex items-center justify-center rounded-md border border-blue-200 bg-white px-3 py-2 text-sm font-medium text-blue-700 hover:bg-blue-50"
          >
            Shifts
          </a>
          <a
            href={`/portal/feedback?service_user_id=${encodedServiceUserId}`}
            className="inline-flex items-center justify-center rounded-md border border-blue-200 bg-white px-3 py-2 text-sm font-medium text-blue-700 hover:bg-blue-50"
          >
            Feedback
          </a>
          <button
            type="button"
            onClick={() => onOpenSection('11_daily_notes')}
            className="inline-flex items-center justify-center rounded-md border border-blue-200 bg-white px-3 py-2 text-sm font-medium text-blue-700 hover:bg-blue-50"
          >
            Daily Notes
          </button>
        </div>
      </div>

      {/* Body Maps */}
      <div className="p-4 rounded-lg bg-white border border-slate-200">
        <h3 className="text-sm font-semibold text-text-primary mb-3 flex items-center gap-2">
          <Shield className="h-4 w-4 text-teal-600" />
          Body Maps
        </h3>
        {bodyMapsLoading ? (
          <p className="text-xs text-slate-400">Loading…</p>
        ) : bodyMaps.length === 0 ? (
          <p className="text-xs text-slate-400">No body maps recorded for this service user.</p>
        ) : (
          <div className="space-y-2">
            {bodyMaps.map(bm => (
              <div key={bm.id} className="flex items-start justify-between gap-3 border border-slate-100 rounded-lg px-3 py-2 bg-slate-50 text-sm">
                <div>
                  <p className="font-medium text-slate-800">
                    {bm.gender ? bm.gender.charAt(0).toUpperCase() + bm.gender.slice(1) : ''} body map
                    {' — '}{bm.completed_date ? bm.completed_date.slice(0, 10) : ''}
                  </p>
                  <p className="text-xs text-slate-500 mt-0.5">
                    By {bm.staff_name || '—'}{bm.marks?.length ? ` · ${bm.marks.length} mark(s)` : ''}
                    {' · '}<span className={`capitalize ${bm.status === 'reviewed' ? 'text-green-600' : 'text-amber-600'}`}>{bm.status}</span>
                  </p>
                </div>
                <button
                  onClick={() => handleDownloadBodyMapPdf(bm.id)}
                  className="text-xs text-teal-600 hover:underline whitespace-nowrap mt-0.5"
                >
                  PDF
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
      
      {/* Notes */}
      {serviceUser.notes && (
        <div className="p-4 rounded-lg bg-amber-50 border border-amber-100">
          <h3 className="text-sm font-semibold text-text-primary mb-2">Notes</h3>
          <p className="text-sm text-text-muted whitespace-pre-wrap">{serviceUser.notes}</p>
        </div>
      )}
    </div>
  );
}

function DailyNotesTimelineTab({ notes, loading, canManage, onRefresh }) {
  if (!canManage) {
    return (
      <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
        <p className="text-sm font-medium text-amber-800">Daily notes are restricted to admin and manager roles.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-text-primary">Daily Notes Timeline</h2>
          <p className="text-sm text-text-muted">Chronological notes linked to shifts and care delivery.</p>
        </div>
        <Button variant="outline" onClick={onRefresh} disabled={loading}>
          Refresh
        </Button>
      </div>

      {loading ? (
        <p className="text-sm text-text-muted">Loading daily notes...</p>
      ) : notes.length === 0 ? (
        <div className="rounded-lg border border-dashed border-gray-200 p-8 text-center">
          <p className="text-sm text-text-muted">No daily notes recorded yet.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {notes.map((note) => (
            <div key={note.id} className="rounded-lg border border-gray-200 p-4 space-y-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="font-medium text-text-primary">{note.employee_name || 'Unknown employee'}{note.employee_code ? ` (${note.employee_code})` : ''}</p>
                <p className="text-xs text-text-muted">{formatBackendDate(note.timestamp) || '-'}</p>
              </div>
              <p className="text-sm text-text-muted">
                {(note.care_location_name || note.shift_location_text || 'Location pending')} • {note.shift_role_required || 'Role pending'}
              </p>
              <p className="text-xs text-text-muted">
                Shift window: {formatBackendDate(note.shift_start_at) || '-'} → {formatBackendDate(note.shift_end_at) || '-'}
              </p>
              <p className="text-sm text-text-primary whitespace-pre-wrap">{note.note_text}</p>
              {Array.isArray(note.tags) && note.tags.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {note.tags.map((tag) => (
                    <span key={`${note.id}-${tag}`} className="px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-700">
                      {tag}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function CarePlansTab({
  carePlans,
  carePlansLoading,
  canManageCarePlans,
  createCarePlanForm,
  setCreateCarePlanForm,
  onCreateDraft,
  editingDraftId,
  editCarePlanForm,
  setEditCarePlanForm,
  onBeginEditDraft,
  onCancelEditDraft,
  onSaveDraftEdit,
  onActivateDraft,
  onArchivePlan,
  onDownloadPdf,
  onUpdateSectionStatus,
  recordReviewOpen,
  setRecordReviewOpen,
  recordReviewForm,
  setRecordReviewForm,
  onRecordReview,
  onRefresh,
}) {
  const activePlan = carePlans.find((plan) => plan.status === 'active');
  const orderedPlans = [...carePlans].sort((a, b) => (b.version_number || 0) - (a.version_number || 0));
  const activeSectionStatuses = normalizeCarePlanSectionStatuses(activePlan?.section_statuses);
  const completedSections = Object.values(activeSectionStatuses).filter((status) => status === 'complete').length;
  const reviewBadge = getCarePlanReviewBadge(activePlan?.next_review_due_at || activePlan?.review_due_at);

  const statusStyles = {
    active: 'bg-green-100 text-green-700',
    draft: 'bg-blue-100 text-blue-700',
    superseded: 'bg-amber-100 text-amber-700',
    archived: 'bg-gray-100 text-gray-700',
  };

  const statusLabel = (status) => {
    const normalized = (status || '').toLowerCase();
    if (normalized === 'active') return 'Active';
    if (normalized === 'draft') return 'Draft';
    if (normalized === 'superseded') return 'Superseded';
    if (normalized === 'archived') return 'Archived';
    return status || 'Unknown';
  };

  if (!canManageCarePlans) {
    return (
      <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
        <p className="text-sm font-medium text-amber-800">Care plans are restricted to admin and manager roles.</p>
        <p className="mt-1 text-xs text-amber-700">No worker-facing care-plan UI is enabled in this surface.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-text-primary">Care Plan Versions</h2>
          <p className="text-sm text-text-muted">Backend lifecycle status is authoritative. Active and superseded plans are read-only.</p>
        </div>
        <Button variant="outline" onClick={onRefresh} disabled={carePlansLoading}>
          Refresh
        </Button>
      </div>

      <div className="rounded-lg border border-green-100 bg-green-50 p-4">
        <h3 className="text-sm font-semibold text-text-primary mb-2">Active Plan Details</h3>
        {!activePlan ? (
          <p className="text-sm text-text-muted">No active care plan yet.</p>
        ) : (
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <p className="font-medium text-text-primary">{activePlan.care_plan_title || 'Untitled care plan'}</p>
              <span className={`px-2 py-0.5 rounded text-xs font-medium ${statusStyles.active}`}>Active</span>
              <span className={`px-2 py-0.5 rounded text-xs font-medium ${reviewBadge.className}`}>{reviewBadge.label}</span>
              <span className="text-xs text-text-muted">v{activePlan.version_number}</span>
            </div>
            <div className="flex flex-col gap-2 rounded-md border border-green-100 bg-white/70 p-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-sm font-medium text-text-primary">Completeness</p>
                <p className="text-xs text-text-muted">{completedSections} / {CARE_PLAN_REQUIRED_SECTIONS.length} sections complete</p>
              </div>
              <Button size="sm" onClick={() => setRecordReviewOpen(true)}>
                Record Review
              </Button>
            </div>
            {Array.isArray(activePlan.goals) && activePlan.goals.length > 0 && (
              <div>
                <p className="text-xs font-medium text-text-primary mb-1">Goals</p>
                <ul className="list-disc list-inside text-sm text-text-muted space-y-1">
                  {activePlan.goals.map((goal, index) => (
                    <li key={`${activePlan.id}-goal-${index}`}>{goal}</li>
                  ))}
                </ul>
              </div>
            )}
            {activePlan.needs_summary && (
              <div>
                <p className="text-xs font-medium text-text-primary mb-1">Needs Summary</p>
                <p className="text-sm text-text-muted whitespace-pre-wrap">{activePlan.needs_summary}</p>
              </div>
            )}
            {activePlan.support_instructions && (
              <div>
                <p className="text-xs font-medium text-text-primary mb-1">Support Instructions</p>
                <p className="text-sm text-text-muted whitespace-pre-wrap">{activePlan.support_instructions}</p>
              </div>
            )}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs text-text-muted">
              <p>Effective From: {formatBackendDate(activePlan.effective_from) || '-'}</p>
              <p>Review Due: {formatBackendDate(activePlan.review_due_at) || '-'}</p>
              <p>Next Review Due: {formatBackendDate(activePlan.next_review_due_at) || '-'}</p>
              <p>Reviewed At: {formatBackendDate(activePlan.reviewed_at) || '-'}</p>
              <p>Approved At: {formatBackendDate(activePlan.approved_at) || '-'}</p>
              <p>Updated At: {formatBackendDate(activePlan.updated_at) || '-'}</p>
            </div>
            {activePlan.review_notes ? (
              <div>
                <p className="text-xs font-medium text-text-primary mb-1">Latest Review Notes</p>
                <p className="text-sm text-text-muted whitespace-pre-wrap">{activePlan.review_notes}</p>
              </div>
            ) : null}
            <div>
              <div className="mb-2 flex items-center justify-between gap-2">
                <p className="text-xs font-medium text-text-primary">Required Section Completeness</p>
                <p className="text-xs text-text-muted">Track inspection readiness without changing the editor.</p>
              </div>
              <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
                {CARE_PLAN_REQUIRED_SECTIONS.map((sectionName) => (
                  <div key={sectionName} className="rounded-md border border-gray-200 bg-white p-3">
                    <p className="text-sm font-medium text-text-primary">{sectionName}</p>
                    <div className="mt-2">
                      <Select
                        value={activeSectionStatuses[sectionName]}
                        onValueChange={(value) => onUpdateSectionStatus(activePlan.id, sectionName, value)}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Select status" />
                        </SelectTrigger>
                        <SelectContent>
                          {CARE_PLAN_SECTION_STATUS_OPTIONS.map((option) => (
                            <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      <Dialog open={recordReviewOpen} onOpenChange={setRecordReviewOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Record Care Plan Review</DialogTitle>
            <DialogDescription>Capture the latest monthly review and the next due date for the active care plan.</DialogDescription>
          </DialogHeader>
          {activePlan ? (
            <div className="space-y-3">
              <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                <div className="space-y-1">
                  <Label htmlFor="care-plan-reviewed-at">Reviewed At</Label>
                  <Input
                    id="care-plan-reviewed-at"
                    type="date"
                    value={recordReviewForm.reviewed_at}
                    onChange={(e) => setRecordReviewForm((prev) => ({ ...prev, reviewed_at: e.target.value }))}
                  />
                </div>
                <div className="space-y-1">
                  <Label htmlFor="care-plan-next-review-due">Next Review Due</Label>
                  <Input
                    id="care-plan-next-review-due"
                    type="date"
                    value={recordReviewForm.next_review_due_at}
                    onChange={(e) => setRecordReviewForm((prev) => ({ ...prev, next_review_due_at: e.target.value }))}
                  />
                </div>
              </div>
              <div className="space-y-1">
                <Label htmlFor="care-plan-review-notes">Review Notes</Label>
                <Textarea
                  id="care-plan-review-notes"
                  rows={4}
                  value={recordReviewForm.review_notes}
                  onChange={(e) => setRecordReviewForm((prev) => ({ ...prev, review_notes: e.target.value }))}
                  placeholder="Summarise what was reviewed and any follow-up needed."
                />
              </div>
              <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={() => setRecordReviewOpen(false)}>Cancel</Button>
                <Button onClick={() => onRecordReview(activePlan.id)}>Save Review</Button>
              </div>
            </div>
          ) : null}
        </DialogContent>
      </Dialog>

      <form onSubmit={onCreateDraft} className="rounded-lg border border-gray-200 p-4 space-y-3">
        <h3 className="text-sm font-semibold text-text-primary">Create Draft Care Plan</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div className="space-y-1">
            <Label htmlFor="care_plan_title">Title *</Label>
            <Input
              id="care_plan_title"
              value={createCarePlanForm.care_plan_title}
              onChange={(e) => setCreateCarePlanForm((prev) => ({ ...prev, care_plan_title: e.target.value }))}
              placeholder="e.g., Monthly care plan review"
              required
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="care_plan_goals">Goals (comma or new line separated)</Label>
            <Input
              id="care_plan_goals"
              value={createCarePlanForm.goals}
              onChange={(e) => setCreateCarePlanForm((prev) => ({ ...prev, goals: e.target.value }))}
              placeholder="Mobility, hydration, social engagement"
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="care_plan_effective_from">Effective From</Label>
            <Input
              id="care_plan_effective_from"
              type="date"
              value={createCarePlanForm.effective_from}
              onChange={(e) => setCreateCarePlanForm((prev) => ({ ...prev, effective_from: e.target.value }))}
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="care_plan_review_due_at">Review Due</Label>
            <Input
              id="care_plan_review_due_at"
              type="date"
              value={createCarePlanForm.review_due_at}
              onChange={(e) => setCreateCarePlanForm((prev) => ({ ...prev, review_due_at: e.target.value }))}
            />
          </div>
        </div>
        <div className="space-y-1">
          <Label htmlFor="care_plan_needs_summary">Needs Summary</Label>
          <Textarea
            id="care_plan_needs_summary"
            value={createCarePlanForm.needs_summary}
            onChange={(e) => setCreateCarePlanForm((prev) => ({ ...prev, needs_summary: e.target.value }))}
            rows={3}
          />
        </div>
        <div className="space-y-1">
          <Label htmlFor="care_plan_support_instructions">Support Instructions</Label>
          <Textarea
            id="care_plan_support_instructions"
            value={createCarePlanForm.support_instructions}
            onChange={(e) => setCreateCarePlanForm((prev) => ({ ...prev, support_instructions: e.target.value }))}
            rows={3}
          />
        </div>
        <div className="flex justify-end">
          <Button type="submit" disabled={carePlansLoading}>
            Create Draft
          </Button>
        </div>
      </form>

      <div className="space-y-3">
        {carePlansLoading ? (
          <p className="text-sm text-text-muted">Loading care plans...</p>
        ) : orderedPlans.length === 0 ? (
          <div className="rounded-lg border border-dashed border-gray-200 p-8 text-center">
            <p className="text-sm text-text-muted">No care plans created yet.</p>
          </div>
        ) : (
          orderedPlans.map((plan) => {
            const normalizedStatus = (plan.status || '').toLowerCase();
            const canEditDraft = normalizedStatus === 'draft';
            const canActivateDraft = normalizedStatus === 'draft';
            const canArchive = normalizedStatus === 'draft' || normalizedStatus === 'superseded';

            return (
              <div key={plan.id} className="rounded-lg border border-gray-200 p-4 space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <p className="font-medium text-text-primary">{plan.care_plan_title || 'Untitled care plan'}</p>
                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${statusStyles[normalizedStatus] || 'bg-gray-100 text-gray-700'}`}>
                        {statusLabel(plan.status)}
                      </span>
                      <span className="text-xs text-text-muted">v{plan.version_number}</span>
                    </div>
                    <p className="text-xs text-text-muted">Updated {formatBackendDate(plan.updated_at) || '-'}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button variant="outline" size="sm" onClick={() => onDownloadPdf(plan)}>
                      Download PDF
                    </Button>
                    {canEditDraft && (
                      <Button variant="outline" size="sm" onClick={() => onBeginEditDraft(plan)}>
                        Edit Draft
                      </Button>
                    )}
                    {canActivateDraft && (
                      <Button size="sm" onClick={() => onActivateDraft(plan.id)}>
                        Activate Draft
                      </Button>
                    )}
                    {canArchive && (
                      <Button variant="outline" size="sm" onClick={() => onArchivePlan(plan.id)}>
                        Archive
                      </Button>
                    )}
                  </div>
                </div>

                {editingDraftId === plan.id ? (
                  <div className="rounded-md bg-gray-50 border border-gray-200 p-3 space-y-3">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      <div className="space-y-1">
                        <Label htmlFor={`edit-title-${plan.id}`}>Title *</Label>
                        <Input
                          id={`edit-title-${plan.id}`}
                          value={editCarePlanForm.care_plan_title}
                          onChange={(e) => setEditCarePlanForm((prev) => ({ ...prev, care_plan_title: e.target.value }))}
                        />
                      </div>
                      <div className="space-y-1">
                        <Label htmlFor={`edit-goals-${plan.id}`}>Goals</Label>
                        <Input
                          id={`edit-goals-${plan.id}`}
                          value={editCarePlanForm.goals}
                          onChange={(e) => setEditCarePlanForm((prev) => ({ ...prev, goals: e.target.value }))}
                        />
                      </div>
                      <div className="space-y-1">
                        <Label htmlFor={`edit-effective-${plan.id}`}>Effective From</Label>
                        <Input
                          id={`edit-effective-${plan.id}`}
                          type="date"
                          value={editCarePlanForm.effective_from}
                          onChange={(e) => setEditCarePlanForm((prev) => ({ ...prev, effective_from: e.target.value }))}
                        />
                      </div>
                      <div className="space-y-1">
                        <Label htmlFor={`edit-review-${plan.id}`}>Review Due</Label>
                        <Input
                          id={`edit-review-${plan.id}`}
                          type="date"
                          value={editCarePlanForm.review_due_at}
                          onChange={(e) => setEditCarePlanForm((prev) => ({ ...prev, review_due_at: e.target.value }))}
                        />
                      </div>
                    </div>
                    <div className="space-y-1">
                      <Label htmlFor={`edit-needs-${plan.id}`}>Needs Summary</Label>
                      <Textarea
                        id={`edit-needs-${plan.id}`}
                        value={editCarePlanForm.needs_summary}
                        onChange={(e) => setEditCarePlanForm((prev) => ({ ...prev, needs_summary: e.target.value }))}
                        rows={3}
                      />
                    </div>
                    <div className="space-y-1">
                      <Label htmlFor={`edit-support-${plan.id}`}>Support Instructions</Label>
                      <Textarea
                        id={`edit-support-${plan.id}`}
                        value={editCarePlanForm.support_instructions}
                        onChange={(e) => setEditCarePlanForm((prev) => ({ ...prev, support_instructions: e.target.value }))}
                        rows={3}
                      />
                    </div>
                    <div className="flex justify-end gap-2">
                      <Button variant="outline" size="sm" onClick={onCancelEditDraft}>Cancel</Button>
                      <Button size="sm" onClick={() => onSaveDraftEdit(plan.id)}>Save Draft</Button>
                    </div>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs text-text-muted">
                    <p>Created: {formatBackendDate(plan.created_at) || '-'}</p>
                    <p>Effective From: {formatBackendDate(plan.effective_from) || '-'}</p>
                    <p>Review Due: {formatBackendDate(plan.review_due_at) || '-'}</p>
                    <p>Approved At: {formatBackendDate(plan.approved_at) || '-'}</p>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

// Section Tab Component
function SectionTab({ section, sectionId, onUpload, onVerify, onDelete }) {
  if (!section) {
    return <p className="text-text-muted">Section not found</p>;
  }

  return (
    <div className="space-y-4">
      {/* Section Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-text-primary">
            Section {section.section_number}: {section.name}
          </h2>
          <p className="text-sm text-text-muted">{section.description}</p>
        </div>
        <Button onClick={onUpload}>
          <Plus className="h-4 w-4 mr-2" />
          Add Document
        </Button>
      </div>
      
      {/* Document Types */}
      <div className="flex flex-wrap gap-2">
        {section.document_types?.map((type) => (
          <span key={type} className="px-2 py-1 rounded bg-gray-100 text-xs text-text-muted">
            {type.replace(/_/g, ' ')}
          </span>
        ))}
      </div>
      
      {/* Documents List */}
      {section.documents?.length === 0 ? (
        <div className="text-center py-12 bg-gray-50 rounded-lg border border-dashed border-gray-200">
          <FileText className="h-12 w-12 text-gray-300 mx-auto mb-4" />
          <h3 className="text-sm font-medium text-text-primary mb-2">No Documents Yet</h3>
          <p className="text-xs text-text-muted mb-4">
            Upload documents for this section
          </p>
          <Button size="sm" onClick={onUpload}>
            <Upload className="h-4 w-4 mr-2" />
            Upload Document
          </Button>
        </div>
      ) : (
        <div className="space-y-3">
          {section.documents.map((doc) => (
            <div 
              key={doc.id}
              className="flex items-center justify-between p-4 rounded-lg bg-gray-50 border border-gray-100"
            >
              <div className="flex items-center gap-4">
                <div className="p-2 rounded-lg bg-white border border-gray-200">
                  <FileText className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <p className="font-medium text-text-primary">{doc.title}</p>
                  <div className="flex items-center gap-2 text-xs text-text-muted mt-1">
                    {doc.document_type && (
                      <span className="px-2 py-0.5 rounded bg-gray-200">
                        {doc.document_type.replace(/_/g, ' ')}
                      </span>
                    )}
                    <span>Uploaded {formatBackendDate(doc.uploaded_at)}</span>
                    {doc.expiry_date && (
                      <span className="text-amber-600">Expires {formatBackendDate(doc.expiry_date)}</span>
                    )}
                  </div>
                </div>
              </div>
              
              <div className="flex items-center gap-2">
                {doc.verified ? (
                  <span className="flex items-center gap-1 px-2 py-1 rounded bg-green-100 text-green-700 text-xs">
                    <Check className="h-3 w-3" />
                    Verified
                  </span>
                ) : (
                  <Button variant="outline" size="sm" onClick={() => onVerify(doc.id)}>
                    <Check className="h-4 w-4 mr-1" />
                    Verify
                  </Button>
                )}
                
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost" size="sm">
                      <MoreVertical className="h-4 w-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem onClick={() => handleViewUploadedDocument(doc)}>
                      <Eye className="h-4 w-4 mr-2" />
                      View Document
                    </DropdownMenuItem>
                    <DropdownMenuItem 
                      onClick={() => onDelete(doc.id)}
                      className="text-red-600"
                    >
                      <Trash2 className="h-4 w-4 mr-2" />
                      Delete
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

