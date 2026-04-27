import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Progress } from '../ui/progress';
import { Input } from '../ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../ui/table';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog';
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '../ui/accordion';
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  GraduationCap,
  Loader2,
  Clock,
  Shield,
  Upload,
  Eye,
  FileText,
  Calendar,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  Filter,
  Search,
  Book,
  Award,
  Link as LinkIcon,
  Edit2,
  Download,
  CheckCircle,
  Wand2,
  Trash2
} from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '../../lib/utils';
import { formatBackendDate } from '../../lib/dateUtils';
import TrainingDetailDrawer from './TrainingDetailDrawer';
import TrainingCertificateExtractor from './TrainingCertificateExtractor';
import EvidenceReviewViewerDialog from '../compliance/EvidenceReviewViewerDialog';
import {
  getPendingProposedTrainingItems,
  getTrainingLibraryBannerState,
} from './trainingLibraryBanner';

const API = process.env.REACT_APP_BACKEND_URL;

// Status styling for training items
const STATUS_STYLES = {
  current: { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200', icon: CheckCircle2, label: 'Current' },
  completed: { bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200', icon: Clock, label: 'Submitted, not reviewed' },
  verified: { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200', icon: CheckCircle2, label: 'Verified' },
  expiring_soon: { bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200', icon: Clock, label: 'Due soon' },
  due_soon: { bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200', icon: Clock, label: 'Due soon' },
  expired: { bg: 'bg-red-50', text: 'text-red-700', border: 'border-red-200', icon: AlertTriangle, label: 'Expired' },
  overdue: { bg: 'bg-red-50', text: 'text-red-700', border: 'border-red-200', icon: AlertTriangle, label: 'Overdue' },
  missing: { bg: 'bg-gray-100', text: 'text-gray-600', border: 'border-gray-200', icon: XCircle, label: 'Missing' },
  pending: { bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200', icon: Clock, label: 'Awaiting admin review' },
  awaiting_review: { bg: 'bg-purple-50', text: 'text-purple-700', border: 'border-purple-200', icon: Clock, label: 'Awaiting admin review' },
  partial: { bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200', icon: AlertTriangle, label: 'Partial' },
  rejected: { bg: 'bg-orange-50', text: 'text-orange-700', border: 'border-orange-200', icon: XCircle, label: 'Rejected / action required' },
  proposed: { bg: 'bg-purple-50', text: 'text-purple-700', border: 'border-purple-200', icon: Wand2, label: 'Awaiting admin review' },
  cannot_assess: { bg: 'bg-red-50', text: 'text-red-700', border: 'border-red-200', icon: AlertTriangle, label: 'Cannot assess' },
};

const TIMING_CURRENT_STATUSES = new Set(['current', 'verified', 'valid', 'no_expiry']);
const TIMING_DUE_SOON_STATUSES = new Set(['expiring_soon', 'due_soon']);
const TIMING_EXPIRED_STATUSES = new Set(['expired', 'overdue']);
const PENDING_REVIEW_STATUSES = new Set(['completed', 'pending', 'awaiting_review', 'proposed']);
const REJECTED_STATUSES = new Set(['rejected', 'action_required']);

const requiresReverification = (item) => Boolean(
  item?.source_evidence_removed ||
  item?.needs_review ||
  item?.needs_review_reason === 'source_certificate_deleted' ||
  item?.needs_review_reason === 'certificate_evidence_removed_by_admin' ||
  item?.needs_review_reason === 'evidence_replaced_reverification_required'
);
const isTrainingVerified = (item) => {
  if (requiresReverification(item)) return false;
  return Boolean(item?.verified || item?.is_verified || item?.status === 'verified');
};
const getTrainingTimingStatus = (item) => (
  item?.status_band ||
  item?.renewal_status ||
  item?.timing_status ||
  item?.renewalStatus ||
  item?.status
);
const getTrainingExpiryDate = (item) => item?.expires_at || item?.expiry_date;
const isExpiryDatePast = (expiryDate) => {
  if (!expiryDate) return false;
  const parsed = new Date(expiryDate);
  if (Number.isNaN(parsed.getTime())) return false;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  parsed.setHours(0, 0, 0, 0);
  return parsed < today;
};
const isTrainingExpiredOrOverdue = (item) => (
  TIMING_EXPIRED_STATUSES.has(getTrainingTimingStatus(item)) ||
  isExpiryDatePast(getTrainingExpiryDate(item))
);
const isTrainingDueSoon = (item) => (
  !isTrainingExpiredOrOverdue(item) &&
  TIMING_DUE_SOON_STATUSES.has(getTrainingTimingStatus(item))
);
const isTrainingCurrent = (item) => (
  !isTrainingExpiredOrOverdue(item) &&
  (TIMING_CURRENT_STATUSES.has(getTrainingTimingStatus(item)) || isTrainingDueSoon(item))
);
const isMandatoryTrainingSatisfied = (item) => isTrainingVerified(item) && isTrainingCurrent(item);
const isEvidenceOnFile = (item) => Boolean(
  item?.completed_at ||
  item?.source_document_id ||
  item?.certificate_url ||
  item?.evidence_files?.length ||
  item?.evidence?.length
);

const normaliseCanonicalTrainingRecord = (record) => {
  const expiryDate = record?.expiry_date || record?.expires_at;
  const needsReverification = requiresReverification(record);
  const verified = !needsReverification && Boolean(record?.verified || record?.is_verified || record?.verification_status === 'verified');
  const timingStatus = isExpiryDatePast(expiryDate) ? 'expired' : 'valid';
  const status = record?.verification_status === 'rejected'
    ? 'rejected'
    : needsReverification
      ? 'completed'
    : verified
      ? (timingStatus === 'expired' ? 'expired' : 'verified')
      : (record?.status || 'completed');

  return {
    ...record,
    id: record?.id,
    record_id: record?.id,
    code: record?.requirement_id || record?.mapped_training_code || record?.id,
    title: record?.training_name || record?.mapped_training_title || 'Training record',
    status,
    completed_at: record?.completion_date || record?.completed_at,
    expires_at: expiryDate,
    is_verified: verified,
    verified,
    is_required: Boolean(record?.mandatory || record?.is_mandatory),
    is_mandatory: Boolean(record?.mandatory || record?.is_mandatory),
    provider: record?.provider_name || record?.provider,
    source_document_id: record?.source_document_id || record?.certificate_document_id,
  };
};

/**
 * AuditReadyTrainingMatrix - Comprehensive training management for CQC audit readiness
 * 
 * Features:
 * 1. Mandatory Training section - 6 required baseline items with blocker logic
 * 2. Training Library - All qualifications including additional/optional
 * 3. Certificates section - Certificate-centric view with extraction details
 * 4. Summary cards showing complete picture
 */
export default function AuditReadyTrainingMatrix({
  employeeId,
  employeeName,
  role,
  onUploadCertificate,
  onViewCertificate,
  onRefresh
}) {
  const { token, user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [sourceErrors, setSourceErrors] = useState({
    matrix: false,
    certificates: false,
    proposedItems: false,
    trainingRecords: false,
  });
  const [activeTab, setActiveTab] = useState('mandatory');
  
  // Data states
  const [mandatoryTraining, setMandatoryTraining] = useState([]);
  const [canonicalTrainingRecords, setCanonicalTrainingRecords] = useState([]);
  const [certificates, setCertificates] = useState([]);
  const [proposedItems, setProposedItems] = useState([]);
      const [unmappedItems, setUnmappedItems] = useState([]);
    const [dependencyWarnings, setDependencyWarnings] = useState([]);
  const [summary, setSummary] = useState({
    totalRequired: 0,
    current: 0,
    needsRenewal: 0,
    missing: 0,
    blockers: 0,
    additionalQualifications: 0,
    certificatesUploaded: 0,
    needsReview: 0
  });
  
  // UI states
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTraining, setSelectedTraining] = useState(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [extractorOpen, setExtractorOpen] = useState(false); // AI Certificate Extractor dialog
  const [editingItem, setEditingItem] = useState(null);
  const [trainingReviewOpen, setTrainingReviewOpen] = useState(false);
  const [trainingReviewItem, setTrainingReviewItem] = useState(null);
  const [trainingReviewPurpose, setTrainingReviewPurpose] = useState('proposed');
  
  // Delete training state
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deletingItem, setDeletingItem] = useState(null);
  const [deleteReason, setDeleteReason] = useState('');
  const [deleting, setDeleting] = useState(false);
  const [unverifyDialogOpen, setUnverifyDialogOpen] = useState(false);
  const [unverifyItem, setUnverifyItem] = useState(null);
  const [unverifyReason, setUnverifyReason] = useState('');
  const [unverifying, setUnverifying] = useState(false);

  // Remove certificate state
  const [removeCertDialogCert, setRemoveCertDialogCert] = useState(null);
  const [removingCert, setRemovingCert] = useState(false);

  // Approve-and-verify state
  const [quickVerifying, setQuickVerifying] = useState({}); // itemId → bool
  const [selectedForBatch, setSelectedForBatch] = useState(new Set());
  const [batchVerifying, setBatchVerifying] = useState(false);
  
  const isAdmin = user?.role === 'admin' || user?.role === 'superadmin' || user?.role === 'super_admin';

  const closeTrainingReview = useCallback(() => {
    setTrainingReviewOpen(false);
    setTrainingReviewItem(null);
    setTrainingReviewPurpose('proposed');
  }, []);

  // Fetch all training data
  const fetchTrainingData = useCallback(async () => {
    if (!employeeId) return;
    
    setLoading(true);
    try {
      setLoadError(false);
      setSourceErrors({ matrix: false, certificates: false, proposedItems: false, trainingRecords: false });
      // Fetch training matrix data
      const [matrixResult, proposedResult, docsResult, recordsResult] = await Promise.allSettled([
        axios.get(`${API}/api/employees/${employeeId}/training/matrix`, {
          headers: { Authorization: `Bearer ${token}` }
        }),
        axios.get(`${API}/api/employees/${employeeId}/training/proposed-items`, {
          headers: { Authorization: `Bearer ${token}` }
        }),
        axios.get(`${API}/api/employees/${employeeId}/training/certificates`, {
          headers: { Authorization: `Bearer ${token}` }
        }),
        axios.get(`${API}/api/training-records`, {
          headers: { Authorization: `Bearer ${token}` },
          params: { employee_id: employeeId }
        })
      ]);

      if (matrixResult.status !== 'fulfilled') {
        setSourceErrors({
          matrix: true,
          certificates: docsResult.status !== 'fulfilled',
          proposedItems: proposedResult.status !== 'fulfilled',
          trainingRecords: recordsResult.status !== 'fulfilled',
        });
        throw new Error('Training matrix unavailable');
      }
      
      // Process matrix data
      const matrixData = matrixResult.value?.data || {};

      // ✅ NEW BACKEND STRUCTURE
      const requiredItems = matrixData.role_required_requirements || [];
      const allQualifications = matrixData.all_qualifications || [];
      const matrixDependencyWarnings = matrixData.dependency_warnings || [];
      setDependencyWarnings(matrixDependencyWarnings);

      setUnmappedItems(matrixData.unmapped_items || []);
      const completionSummary = matrixData.completion_summary || {};

      // ✅ SET STATE CORRECTLY
      setMandatoryTraining(requiredItems);
      setCanonicalTrainingRecords(allQualifications);

      // Handle proposed items - ensure it's an array
      const proposedFailed = proposedResult.status !== 'fulfilled';
      const proposedData = proposedFailed ? null : proposedResult.value?.data;
      const proposedArray = Array.isArray(proposedData) ? proposedData : 
                           proposedData?.items || proposedData?.proposed_items || [];
      setProposedItems(proposedArray);

      const recordsFailed = recordsResult.status !== 'fulfilled';
      const recordsData = recordsFailed ? [] : recordsResult.value?.data;
      const canonicalRecords = Array.isArray(recordsData)
        ? recordsData.map(normaliseCanonicalTrainingRecord)
        : [];
      setCanonicalTrainingRecords(canonicalRecords);
      
      // Get training certificates from merged endpoint (canonical + legacy)
      const certificatesFailed = docsResult.status !== 'fulfilled';
      const docsData = certificatesFailed ? null : docsResult.value?.data;
      const trainingCerts = docsData?.certificates || [];
      setCertificates(trainingCerts);
      setSourceErrors({
        matrix: false,
        certificates: certificatesFailed,
        proposedItems: proposedFailed,
        trainingRecords: recordsFailed,
      });
      
      // Use completion_summary only
      const apiSummary = matrixData.completion_summary || {};
      const pendingReview = proposedFailed ? null : proposedArray.filter(p => p.status === 'proposed').length;

      setSummary({
        totalRequired: apiSummary.required_total || requiredItems.length,
        current: apiSummary.current || requiredItems.filter(isMandatoryTrainingSatisfied).length,
        needsRenewal: apiSummary.needsRenewal || requiredItems.filter(isTrainingDueSoon).length,
        missing: apiSummary.missing || requiredItems.filter(item => item.status === 'missing').length,
        blockers: apiSummary.blockers || 0,
        additionalQualifications: recordsFailed ? null : allQualifications.length,
        certificatesUploaded: certificatesFailed ? null : trainingCerts.length,
        needsReview: pendingReview
      });

      // Store dependency warnings for later use
      setDependencyWarnings(dependencyWarnings);

    } catch (err) {
      console.error('Error fetching training data:', err);
      setLoadError(true);
      setSourceErrors(prev => ({ ...prev, matrix: true }));
      toast.error('Failed to load training data');
    } finally {
      setLoading(false);
    }
  }, [employeeId, token]);
  
  useEffect(() => {
    fetchTrainingData();
  }, [fetchTrainingData]);

  // Open training detail drawer
  const handleOpenDetail = (item) => {
    setSelectedTraining(item);
    setDrawerOpen(true);
  };

  // Open edit dialog for proposed item
  const handleEditProposed = (item) => {
    if (sourceErrors.proposedItems) {
      toast.error('Cannot assess pending reviews until training review data loads.');
      return;
    }
    setEditingItem(item);
    setEditDialogOpen(true);
  };

  const getSourceCertificateFileForProposedItem = (item) => {
    if (!item?.source_document_id) return null;
    return {
      id: item.source_document_id,
      file_id: item.source_document_id,
      file_name: item.source_document?.filename || 'Source training certificate',
      name: item.source_document?.filename || 'Source training certificate',
      uploaded_at: item.source_document?.uploaded_at,
    };
  };

  const getSourceCertificateFileForTrainingItem = (item) => {
    const evidenceFile = Array.isArray(item?.evidence_files) ? item.evidence_files[0] : null;
    const documentId = item?.source_document_id || evidenceFile?.document_id;
    if (!documentId) return null;
    return {
      id: documentId,
      file_id: documentId,
      file_name: item?.original_filename || evidenceFile?.original_filename || item?.title || 'Training certificate',
      name: item?.original_filename || evidenceFile?.original_filename || item?.title || 'Training certificate',
      uploaded_at: item?.uploaded_at || evidenceFile?.uploaded_at,
    };
  };

  const openTrainingEvidenceReview = (item) => {
    if (sourceErrors.proposedItems) {
      toast.error('Cannot assess pending reviews until training review data loads.');
      return;
    }
    if (item?.status !== 'proposed') {
      toast.info('This extracted training item has already been reviewed.');
      return;
    }
    if (!getSourceCertificateFileForProposedItem(item)) {
      toast.error('Source certificate is missing for this extracted item.');
      return;
    }
    setTrainingReviewItem(item);
    setTrainingReviewPurpose('proposed');
    setTrainingReviewOpen(true);
  };

  // Approve proposed item
  const handleApproveProposed = async (item, notes) => {
    if (sourceErrors.proposedItems) {
      toast.error('Cannot assess pending reviews until training review data loads.');
      return;
    }
    try {
      await axios.post(
        `${API}/api/employees/${employeeId}/training/proposed-items/review`,
        {
          items: [{
            item_id: item.id,
            approve: true,
            mapped_training_code: item.mapped_training_code,
            mapped_training_title: item.mapped_training_title,
            completed_at: item.completed_at,
            expires_at: item.expires_at,
            notes
          }]
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Training item approved');
      closeTrainingReview();
      fetchTrainingData();
      onRefresh?.();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to approve item');
    }
  };

  // Reject proposed item
  const handleRejectProposed = async (item, notes = 'Rejected by admin') => {
    if (sourceErrors.proposedItems) {
      toast.error('Cannot assess pending reviews until training review data loads.');
      return;
    }
    try {
      await axios.post(
        `${API}/api/employees/${employeeId}/training/proposed-items/review`,
        {
          items: [{
            item_id: item.id,
            approve: false,
            notes
          }]
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Training item rejected');
      closeTrainingReview();
      fetchTrainingData();
      onRefresh?.();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to reject item');
    }
  };

  // Quick-verify eligibility check (mirrors backend safety rules)
  const canQuickVerify = (item) => (
    Boolean(item?.source_document_id) &&         // source certificate present
    Boolean((item?.raw_course_title || '').trim()) &&  // extracted title present
    Boolean(item?.mapped_training_code || item?.mapped_training_title) && // mapped
    Boolean(item?.completed_at) &&               // completed date present
    !item?.is_unmapped                           // not flagged unmapped
  );

  // One-step approve + verify a single extracted item
  const handleApproveAndVerify = async (item, force = false) => {
    if (sourceErrors.proposedItems) {
      toast.error('Cannot assess pending reviews until training review data loads.');
      return;
    }
    setQuickVerifying(prev => ({ ...prev, [item.id]: true }));
    try {
      const res = await axios.post(
        `${API}/api/employees/${employeeId}/training/proposed-items/approve-and-verify`,
        {
          items: [{
            item_id: item.id,
            mapped_training_code: item.mapped_training_code,
            mapped_training_title: item.mapped_training_title,
            completed_at: item.completed_at,
            expires_at: item.expires_at,
            force,
          }]
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      const data = res.data;
      if (data.approved_and_verified_count > 0) {
        toast.success(`${item.raw_course_title || 'Item'} approved and verified`);
      } else if (data.needs_review?.length > 0) {
        const reason = data.needs_review[0]?.skip_reason || 'review_required';
        toast.warning(`Needs manual review: ${reason.replace(/_/g, ' ')}`);
        // Fall back to evidence-review modal
        openTrainingEvidenceReview(item);
      }
      fetchTrainingData();
      onRefresh?.();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to approve and verify item');
    } finally {
      setQuickVerifying(prev => ({ ...prev, [item.id]: false }));
    }
  };

  // Batch approve-and-verify for selected items
  const handleBatchApproveAndVerify = async () => {
    if (selectedForBatch.size === 0) return;
    setBatchVerifying(true);
    try {
      const itemsInBatch = proposedItems
        .filter(p => p.status === 'proposed' && selectedForBatch.has(p.id));
      const res = await axios.post(
        `${API}/api/employees/${employeeId}/training/proposed-items/approve-and-verify`,
        {
          items: itemsInBatch.map(item => ({
            item_id: item.id,
            mapped_training_code: item.mapped_training_code,
            mapped_training_title: item.mapped_training_title,
            completed_at: item.completed_at,
            expires_at: item.expires_at,
            force: false,
          }))
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      const data = res.data;
      const verifiedCount = data.approved_and_verified_count || 0;
      const reviewCount = data.needs_review_count || 0;
      if (verifiedCount > 0 && reviewCount === 0) {
        toast.success(`${verifiedCount} item${verifiedCount !== 1 ? 's' : ''} approved and verified`);
      } else if (verifiedCount > 0) {
        toast.success(`${verifiedCount} approved and verified — ${reviewCount} still need manual review`);
      } else {
        toast.warning(`${reviewCount} item${reviewCount !== 1 ? 's' : ''} require manual review`);
      }
      setSelectedForBatch(new Set());
      fetchTrainingData();
      onRefresh?.();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Batch verify failed');
    } finally {
      setBatchVerifying(false);
    }
  };

  const toggleBatchSelect = (itemId) => {
    setSelectedForBatch(prev => {
      const next = new Set(prev);
      if (next.has(itemId)) next.delete(itemId);
      else next.add(itemId);
      return next;
    });
  };

  const selectAllForBatch = (items) => {
    setSelectedForBatch(new Set(items.map(i => i.id)));
  };

  const clearBatchSelection = () => setSelectedForBatch(new Set());

  // Delete training record - Admin only with audit trail
  const handleDeleteTraining = async () => {
    if (!deletingItem) return;
    
    const recordId = deletingItem.record_id || deletingItem.id;
    if (!recordId) {
      toast.error('No record ID found for this training');
      return;
    }
    
    setDeleting(true);
    try {
      await axios.delete(
        `${API}/api/training-records/${recordId}`,
        { 
          headers: { Authorization: `Bearer ${token}` },
          params: { reason: deleteReason || 'Deleted by admin' }
        }
      );
      toast.success(`"${deletingItem.title}" deleted successfully`);
      setDeleteDialogOpen(false);
      setDeletingItem(null);
      setDeleteReason('');
      fetchTrainingData();
      onRefresh?.();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to delete training');
    } finally {
      setDeleting(false);
    }
  };
  
  // Open delete confirmation
  const openDeleteDialog = (item) => {
    setDeletingItem(item);
    setDeleteReason('');
    setDeleteDialogOpen(true);
  };

  const submitVerifyTraining = async (item) => {
    await axios.post(
      `${API}/api/employees/${employeeId}/training/${item.code || item.id}/verify`,
      {},
      { headers: { Authorization: `Bearer ${token}` } }
    );
    toast.success(`${item.title} verified`);
    closeTrainingReview();
    fetchTrainingData();
    onRefresh?.();
  };

  // Verify training record - Admin only
  const handleVerifyTraining = async (item) => {
    try {
      await submitVerifyTraining(item);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to verify training');
    }
  };

  const openTrainingVerifyReview = (item) => {
    if (isTrainingVerified(item)) {
      toast.info(`${item.title} is already verified`);
      return;
    }
    const sourceFile = getSourceCertificateFileForTrainingItem(item);
    if (!sourceFile) {
      handleVerifyTraining(item);
      return;
    }
    setTrainingReviewItem(item);
    setTrainingReviewPurpose('verify');
    setTrainingReviewOpen(true);
  };

  // Unverify training record - Admin only, requires reason
  const handleUnverifyTraining = async (item) => {
    setUnverifyItem(item);
    setUnverifyReason('');
    setUnverifyDialogOpen(true);
  };

  const confirmUnverifyTraining = async () => {
    if (!unverifyItem || !unverifyReason.trim()) return;

    setUnverifying(true);
    try {
      await axios.post(
        `${API}/api/employees/${employeeId}/training/${unverifyItem.code || unverifyItem.id}/unverify`,
        { reason: unverifyReason.trim() },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success(`${unverifyItem.title} unverified`);
      setUnverifyDialogOpen(false);
      setUnverifyItem(null);
      setUnverifyReason('');
      fetchTrainingData();
      onRefresh?.();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to unverify training');
    } finally {
      setUnverifying(false);
    }
  };

  // Re-run extraction on certificate
  const handleReExtract = async (documentId) => {
    if (sourceErrors.certificates) {
      toast.error('Cannot assess certificates until certificate data loads.');
      return;
    }
    try {
      const response = await axios.post(
        `${API}/api/employees/${employeeId}/training/re-extract`,
        { document_id: documentId },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (response.data.success && response.data.trainings?.length > 0) {
        // If AI was skipped because items already exist, just inform the admin
        if (response.data.skipped_ai) {
          toast.info(response.data.message || 'Items already extracted — check Training Library for pending reviews');
          fetchTrainingData();
          return;
        }
        // Auto-submit extracted items as proposed for review
        const trainingsToSave = response.data.trainings
          .filter(t => !t.already_proposed)
          .map(t => ({ ...t, document_id: documentId }));
        if (trainingsToSave.length > 0) {
          await axios.post(
            `${API}/api/employees/${employeeId}/training/bulk-save`,
            { trainings: trainingsToSave },
            { headers: { Authorization: `Bearer ${token}` } }
          );
          toast.success(`Extracted ${trainingsToSave.length} training(s) — submitted for review`);
        } else {
          toast.info('All extracted trainings already pending review — check Training Library tab');
        }
        fetchTrainingData();
      } else {
        toast.error(response.data.message || 'No trainings detected');
        fetchTrainingData();
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to extract training');
      fetchTrainingData();
    }
  };

  // Remove certificate file + extracted items
  const handleRemoveCertificate = async () => {
    if (!removeCertDialogCert) return;
    setRemovingCert(true);
    try {
      const res = await axios.delete(
        `${API}/api/employees/${employeeId}/training/certificates/${removeCertDialogCert.id}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      const preserved = res.data?.approved_training_records_preserved || 0;
      const deleted = res.data?.proposed_items_deleted || 0;
      toast.success(
        preserved > 0
          ? `Certificate removed. ${deleted} extracted item(s) deleted. ${preserved} approved training record(s) preserved.`
          : `Certificate removed${deleted > 0 ? `. ${deleted} extracted item(s) deleted.` : '.'}`
      );
      setRemoveCertDialogCert(null);
      fetchTrainingData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to remove certificate.');
    } finally {
      setRemovingCert(false);
    }
  };

  // Render status badge
  const renderStatusBadge = (status) => {
    const style = STATUS_STYLES[status] || STATUS_STYLES.missing;
    const Icon = style.icon;
    return (
      <Badge className={cn('text-xs', style.bg, style.text, style.border)}>
        <Icon className="h-3 w-3 mr-1" />
        {style.label}
      </Badge>
    );
  };

  const renderExtractionStatusBadge = (cert) => {
    const status = cert.extraction_status || (cert.extraction_count || cert.extracted_item_count ? 'extracted_with_matches' : 'not_extracted');
    const extractedCount = cert.extracted_item_count ?? cert.extraction_count ?? 0;
    const statusConfig = {
      not_extracted: { label: 'Not extracted', className: 'bg-gray-100 text-gray-700 border-gray-200', icon: Clock },
      extraction_pending: { label: 'Extraction pending', className: 'bg-blue-50 text-blue-700 border-blue-200', icon: Loader2 },
      extraction_failed: { label: 'Extraction failed', className: 'bg-red-50 text-red-700 border-red-200', icon: AlertTriangle },
      extracted_no_match: { label: 'Extracted: no matches', className: 'bg-amber-50 text-amber-700 border-amber-200', icon: AlertTriangle },
      extracted_with_matches: { label: `Extracted: ${extractedCount} item${extractedCount === 1 ? '' : 's'}`, className: 'bg-emerald-50 text-emerald-700 border-emerald-200', icon: CheckCircle2 },
      completed: { label: `Extracted: ${extractedCount} item${extractedCount === 1 ? '' : 's'}`, className: 'bg-emerald-50 text-emerald-700 border-emerald-200', icon: CheckCircle2 },
    };
    const config = statusConfig[status] || statusConfig.not_extracted;
    const Icon = config.icon;

    return (
      <Badge variant="outline" className={cn('text-xs', config.className)}>
        <Icon className={cn('h-3 w-3 mr-1', status === 'extraction_pending' && 'animate-spin')} />
        {config.label}
      </Badge>
    );
  };

  // Progress calculation
  const progressPercent = summary.totalRequired > 0
    ? Math.round((summary.current / summary.totalRequired) * 100)
    : 0;
  const mandatoryVerifiedCurrent = mandatoryTraining.filter(isMandatoryTrainingSatisfied);
  const mandatoryMissing = mandatoryTraining.filter(item => item.status === 'missing');
  const mandatoryDueSoon = mandatoryTraining.filter(isTrainingDueSoon);
  const mandatoryExpired = mandatoryTraining.filter(isTrainingExpiredOrOverdue);
  const mandatoryPendingVerification = mandatoryTraining.filter(item =>
    !isMandatoryTrainingSatisfied(item) &&
    !REJECTED_STATUSES.has(item.status) &&
    !isTrainingExpiredOrOverdue(item) &&
    !isTrainingDueSoon(item) &&
    (PENDING_REVIEW_STATUSES.has(item.status) || (isEvidenceOnFile(item) && !isTrainingVerified(item)))
  );
  const mandatoryBlockers = mandatoryTraining.filter(item =>
    item.status === 'missing' ||
    REJECTED_STATUSES.has(item.status) ||
    isTrainingExpiredOrOverdue(item) ||
    !isMandatoryTrainingSatisfied(item)
  );
  const exactBlockerNames = mandatoryBlockers
    .map(item => item.title || item.training_name || item.code || 'Unnamed training')
    .filter(Boolean);
  const normalizeTrainingKey = (value) => (
    (value || '').toLowerCase().replace(/&/g, 'and').replace(/[\s_-]+/g, ' ').trim()
  );
  const getPendingExtractedMatch = (mandatoryItem) => {
    const mandatoryCandidates = [
      mandatoryItem?.code,
      mandatoryItem?.title,
      mandatoryItem?.id,
      mandatoryItem?.training_name,
    ].map(normalizeTrainingKey).filter(Boolean);

    return proposedItems.find((proposed) => {
      if (proposed.status !== 'proposed') return false;
      const proposedCandidates = [
        proposed.mapped_training_code,
        proposed.mapped_training_title,
        proposed.raw_course_title,
        proposed.training_name,
        proposed.course_name,
      ].map(normalizeTrainingKey).filter(Boolean);

      return mandatoryCandidates.some((mandatoryKey) =>
        proposedCandidates.some((proposedKey) =>
          proposedKey === mandatoryKey ||
          proposedKey.includes(mandatoryKey) ||
          mandatoryKey.includes(proposedKey)
        )
      );
    });
  };
  const mandatoryKeys = new Set(
    mandatoryTraining.map(item => normalizeTrainingKey(item.code || item.title || item.id))
  );
  const isRequiredTrainingItem = (item) => {
    const key = normalizeTrainingKey(item?.code || item?.title || item?.id);
    return Boolean(item?.is_required || item?.is_mandatory || item?.required || item?.mandatory || mandatoryKeys.has(key));
  };
  const cannotAssessCount = (sourceErrors.certificates ? 1 : 0) + (sourceErrors.proposedItems ? 1 : 0) + (sourceErrors.trainingRecords ? 1 : 0);
  const pendingProposedItems = getPendingProposedTrainingItems(proposedItems);
  const trainingLibraryBanner = getTrainingLibraryBannerState({
    proposedItems,
    proposedItemsErrored: sourceErrors.proposedItems,
  });
  let trainingDecisionState = 'Training ready';
  if (loadError) {
    trainingDecisionState = 'Cannot assess';
  } else if (sourceErrors.matrix) {
    trainingDecisionState = 'Matrix error';
  }
  const getDisplayStatus = (item) => {
    const pendingExtractedMatch = !isMandatoryTrainingSatisfied(item)
      ? getPendingExtractedMatch(item)
      : null;
    if (item?.status === 'missing' && pendingExtractedMatch) {
      return 'pending';
    }
    return item?.status;
  };

  const trainingDecisionClasses = trainingDecisionState === 'Training ready'
    ? {
        panel: 'border-emerald-200 bg-emerald-50',
        icon: 'text-emerald-600',
        text: 'text-emerald-800',
        subtext: 'text-emerald-700',
      }
    : trainingDecisionState === 'Cannot assess'
      ? {
          panel: 'border-red-200 bg-red-50',
          icon: 'text-red-600',
          text: 'text-red-800',
          subtext: 'text-red-700',
        }
      : {
          panel: 'border-amber-200 bg-amber-50',
          icon: 'text-amber-600',
          text: 'text-amber-800',
          subtext: 'text-amber-700',
        };
  if (loadError) {
    return (
      <Card className="border-red-200" data-testid="training-matrix-error">
        <CardContent className="text-center py-12 text-red-700">
          <AlertTriangle className="h-10 w-10 mx-auto mb-3 text-red-500" />
          <p className="font-medium">Cannot assess training</p>
          <p className="text-sm mt-1">Training data unavailable. Upload, verify, and review actions are disabled until this source loads.</p>
          <Button variant="outline" size="sm" onClick={fetchTrainingData} className="mt-4">
            <RefreshCw className="h-4 w-4 mr-2" />
            Retry
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6" data-testid="audit-ready-training-matrix">
      {dependencyWarnings.length > 0 && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">
          <p className="font-medium">Training dependency issues</p>
          <ul className="list-disc pl-5 mt-1">
            {dependencyWarnings.map((w, i) => (
              <li key={i}>{w.message}</li>
            ))}
          </ul>
        </div>
      )}
      {/* Dependency Warnings */}
      {dependencyWarnings && dependencyWarnings.length > 0 && (
        <div className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
          <strong>Dependency Warnings:</strong>
          <ul className="list-disc pl-5 mt-1">
            {dependencyWarnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      )}
      <div className={`rounded-lg border p-4 ${trainingDecisionClasses.panel}`}>
        <div className="flex items-start gap-3">
          <div className={`mt-0.5 ${trainingDecisionClasses.icon}`}>
            {trainingDecisionState === 'Training ready' ? (
              <CheckCircle2 className="h-5 w-5" />
            ) : (
              <AlertTriangle className="h-5 w-5" />
            )}
          </div>
          <div className="flex-1">
            <p className={`font-medium ${trainingDecisionClasses.text}`}>
              Training status: {trainingDecisionState}
            </p>
            <p className={`mt-1 text-sm ${trainingDecisionClasses.subtext}`}>
              Only verified and current mandatory training counts toward work readiness.
            </p>
            <p className={`mt-1 text-sm ${trainingDecisionClasses.subtext}`}>
              Certificates are evidence only. Extracted items must be reviewed into training records before required training status changes.
            </p>
            {trainingDecisionState === 'Blocked' && exactBlockerNames.length > 0 && (
              <div className={`mt-2 text-sm ${trainingDecisionClasses.subtext}`}>
                <p className="font-medium">Required training still needed</p>
                <ul className="mt-1 list-disc space-y-1 pl-5">
                  {exactBlockerNames.slice(0, 8).map((name) => (
                    <li key={name}>{name}</li>
                  ))}
                  {exactBlockerNames.length > 8 && (
                    <li>{exactBlockerNames.length - 8} more mandatory item{exactBlockerNames.length - 8 !== 1 ? 's' : ''}</li>
                  )}
                </ul>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ============================================ */}
      {/* SUMMARY CARDS                               */}
      {/* ============================================ */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-10 gap-3">
        <div className="p-3 bg-white border border-gray-200 rounded-lg">
          <p className="text-2xl font-bold text-gray-900">{summary.totalRequired}</p>
          <p className="text-xs text-gray-500">Required</p>
        </div>
        <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg">
          <p className="text-2xl font-bold text-emerald-700">{mandatoryVerifiedCurrent.length}</p>
          <p className="text-xs text-emerald-600">Verified/current</p>
        </div>
        <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
          <p className="text-2xl font-bold text-amber-700">{mandatoryDueSoon.length}</p>
          <p className="text-xs text-amber-600">Due soon</p>
        </div>
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-2xl font-bold text-red-700">{mandatoryExpired.length}</p>
          <p className="text-xs text-red-600">Expired/overdue</p>
        </div>
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-2xl font-bold text-red-700">{mandatoryMissing.length}</p>
          <p className="text-xs text-red-600">Missing</p>
        </div>
        <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
          <p className={cn('font-bold text-blue-700', sourceErrors.trainingRecords ? 'text-sm' : 'text-2xl')}>
            {sourceErrors.trainingRecords ? 'Cannot assess' : summary.additionalQualifications}
          </p>
          <p className="text-xs text-blue-600">Approved</p>
        </div>
        <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg">
          <p className={cn('font-bold text-slate-700', sourceErrors.certificates ? 'text-sm' : 'text-2xl')}>
            {sourceErrors.certificates ? 'Cannot assess' : summary.certificatesUploaded}
          </p>
          <p className="text-xs text-slate-600">Certificates</p>
        </div>
        <div className="p-3 bg-purple-50 border border-purple-200 rounded-lg">
          <p className={cn('font-bold text-purple-700', sourceErrors.proposedItems ? 'text-sm' : 'text-2xl')}>
            {sourceErrors.proposedItems ? 'Cannot assess' : summary.needsReview}
          </p>
          <p className="text-xs text-purple-600">Awaiting admin review</p>
        </div>
        <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
          <p className="text-2xl font-bold text-blue-700">{mandatoryPendingVerification.length}</p>
          <p className="text-xs text-blue-600">Pending verification</p>
        </div>
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-2xl font-bold text-red-700">{cannotAssessCount}</p>
          <p className="text-xs text-red-600">Cannot assess</p>
        </div>
        <div className="p-3 bg-gray-100 border border-gray-200 rounded-lg">
          <p className="text-2xl font-bold text-gray-700">{progressPercent}%</p>
          <p className="text-xs text-gray-500">Current</p>
        </div>
      </div>

      <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
        <span className="font-medium">Required training still needed:</span> {mandatoryBlockers.length} &nbsp;|&nbsp;
        <span className="font-medium">Pending verification:</span> {mandatoryPendingVerification.length} &nbsp;|&nbsp;
        <span className="font-medium">Expired/overdue:</span> {mandatoryExpired.length} &nbsp;|&nbsp;
        <span className="font-medium">Cannot assess:</span> {cannotAssessCount} &nbsp;|&nbsp;
        <span className="font-medium">Verified/current:</span> {mandatoryVerifiedCurrent.length}/{summary.totalRequired}
        {sourceErrors.certificates && <span> | Cannot assess certificates</span>}
        {sourceErrors.proposedItems && <span> | Cannot assess pending reviews</span>}
        {sourceErrors.trainingRecords && <span> | Cannot assess approved qualifications</span>}
      </div>

      {/* Progress Bar */}
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-700">Mandatory Training Current</span>
          <span className="text-sm font-bold">{progressPercent}%</span>
        </div>
        <Progress 
          value={progressPercent}
          className={cn(
            "h-3",
            progressPercent >= 80 ? "[&>div]:bg-emerald-500" :
            progressPercent >= 50 ? "[&>div]:bg-amber-500" :
            "[&>div]:bg-red-500"
          )}
        />
        {summary.blockers > 0 && (
          <div className="mt-3 p-2 bg-red-50 border border-red-200 rounded flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-red-600" />
            <span className="text-sm text-red-800">
              {summary.blockers} work-blocking item{summary.blockers !== 1 ? 's' : ''} require attention
            </span>
          </div>
        )}
      </div>

      {/* ============================================ */}
      {/* TABBED SECTIONS                             */}
      {/* ============================================ */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-3 lg:w-auto lg:inline-flex">
          <TabsTrigger value="mandatory" className="flex items-center gap-2">
            <Shield className="h-4 w-4" />
            Mandatory ({summary.totalRequired})
          </TabsTrigger>
          <TabsTrigger value="library" className="flex items-center gap-2">
            <Book className="h-4 w-4" />
            All Qualifications ({sourceErrors.trainingRecords ? 'Cannot assess' : canonicalTrainingRecords.length})
          </TabsTrigger>
          <TabsTrigger value="certificates" className="flex items-center gap-2">
            <Award className="h-4 w-4" />
            Certificates ({sourceErrors.certificates ? 'Cannot assess' : summary.certificatesUploaded})
          </TabsTrigger>
        </TabsList>

        {/* MANDATORY TRAINING TAB */}
        <TabsContent value="mandatory" className="mt-4">
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-lg flex items-center gap-2">
                    <Shield className="h-5 w-5 text-primary" />
                    Mandatory Training Requirements
                  </CardTitle>
                  <CardDescription>
                    Mandatory only reflects approved training records. Extracted certificate evidence must be reviewed and then verified before it can satisfy work readiness.
                  </CardDescription>
                </div>
                <div className="flex items-center gap-2">
                  {isAdmin && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setExtractorOpen(true)}
                      data-testid="upload-training-cert-btn"
                    >
                      <Upload className="h-4 w-4 mr-1" />
                      Upload Certificate
                    </Button>
                  )}
                  <Button variant="ghost" size="sm" onClick={fetchTrainingData}>
                    <RefreshCw className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[250px]">Training</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Certificate(s)</TableHead>
                    <TableHead>Completed</TableHead>
                    <TableHead>Expires</TableHead>
                    <TableHead>Verified</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {(mandatoryTraining.length > 0 ? mandatoryTraining : (matrixData.items || [])).map((item) => {
                    const pendingExtractedMatch = !isMandatoryTrainingSatisfied(item)
                      ? getPendingExtractedMatch(item)
                      : null;

                  let displayStatus = item.status;
                  // If a mapped proposed item exists, override status to 'proposed' for badge
                  if (pendingExtractedMatch && (pendingExtractedMatch.mapped_training_code || pendingExtractedMatch.mapped_training_title)) {
                    displayStatus = 'proposed';
                  }
                  // If status is missing and there is a pending extracted match, show as pending
                  if (item.status === 'missing' && pendingExtractedMatch) {
                    displayStatus = 'pending';
                  }

                    return (
                      <TableRow
                        key={item.code || item.id}
                        className={cn(item.blocker && 'bg-red-50/50')}
                      >
                        <TableCell>
                          <div className="flex items-center gap-2">
                            {item.is_currently_blocking && (
                              <AlertTriangle className="h-4 w-4 text-red-600 flex-shrink-0" />
                            )}
                            <div>
                              <p className="font-medium text-gray-900">{item.title}</p>
                              {item.is_currently_blocking && (
                                <p className="text-xs text-red-600">Work blocker</p>
                              )}
                              {pendingExtractedMatch && (
                                <p className="text-xs text-purple-700">
                                  Matching extracted evidence awaiting admin review
                                </p>
                              )}
                            </div>
                          </div>
                        </TableCell>
                        <TableCell>{renderStatusBadge(displayStatus)}</TableCell>
                        <TableCell>
                          {(item.record_id || item.id) && (item.source_document_id || item.certificate_url || item.evidence_files?.length) ? (
                            <Button
                              variant="link"
                              size="sm"
                              className="h-auto p-0 text-blue-600"
                              onClick={() => onViewCertificate?.(item.record_id || item.id)}
                            >
                              <FileText className="h-3 w-3 mr-1" />
                              View
                            </Button>
                          ) : item.certificate_url ? (
                            <a
                              href={item.certificate_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center text-sm text-blue-600 hover:underline"
                            >
                              <FileText className="h-3 w-3 mr-1" />
                              View
                            </a>
                          ) : item.evidence?.length > 0 ? (
                            <div className="flex items-center gap-1">
                              <FileText className="h-4 w-4 text-gray-400" />
                              <span className="text-sm text-gray-600">
                                {item.evidence.length} file{item.evidence.length !== 1 ? 's' : ''}
                              </span>
                            </div>
                          ) : (
                            <span className="text-sm text-gray-400">None</span>
                          )}
                        </TableCell>
                        <TableCell>
                          <span className="text-sm text-gray-600">
                            {item.completed_at ? formatBackendDate(item.completed_at, { format: 'short' }) : '-'}
                          </span>
                        </TableCell>
                        <TableCell>
                          {item.expires_at ? (
                            <span className={cn(
                              "text-sm",
                              item.status === 'expired' ? 'text-red-600 font-medium' :
                              item.status === 'expiring_soon' ? 'text-amber-600' :
                              'text-gray-600'
                            )}>
                              {formatBackendDate(item.expires_at, { format: 'short' })}
                            </span>
                          ) : (
                            <span className="text-sm text-gray-400">-</span>
                          )}
                        </TableCell>
                        <TableCell>
                          {item.verified || item.is_verified || displayStatus === 'verified' ? (
                            <div className="flex flex-col">
                              <Badge className="bg-green-100 text-green-700 border-green-200 w-fit">
                                <CheckCircle className="h-3 w-3 mr-1" />
                                Verified
                              </Badge>
                              {item.verified_by && (
                                <span className="text-xs text-gray-500 mt-1">{item.verified_by}</span>
                              )}
                            </div>
                          ) : displayStatus !== 'missing' ? (
                            <Badge className="bg-amber-100 text-amber-700 border-amber-200">
                              Submitted, not reviewed
                            </Badge>
                          ) : null}
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-1">
                            {/* View button - always available for completed training */}
                            {item.completed_at && (
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-8 w-8 p-0"
                                onClick={() => handleOpenDetail(item)}
                                title="View details"
                              >
                                <Eye className="h-4 w-4" />
                              </Button>
                            )}
                            {/* Edit button for Admin */}
                            {isAdmin && item.completed_at && (
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-8 w-8 p-0 text-gray-500 hover:text-primary"
                                onClick={() => {
                                  setEditingItem(item);
                                  setEditDialogOpen(true);
                                }}
                                title="Edit dates"
                              >
                                <Edit2 className="h-4 w-4" />
                              </Button>
                            )}
                            {isAdmin && item.status === 'missing' && (
                              <Button
                                variant="outline"
                                size="sm"
                                className="h-8"
                                onClick={onUploadCertificate}
                              >
                                <Upload className="h-3.5 w-3.5 mr-1" />
                                Upload
                              </Button>
                            )}
                          </div>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        {/* TRAINING LIBRARY TAB */}
        <TabsContent value="library" className="mt-4">
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-lg flex items-center gap-2">
                    <Book className="h-5 w-5 text-primary" />
                    Training Library
                  </CardTitle>
                  <CardDescription>
                    This tab separates approved/canonical qualifications from extracted certificate items awaiting admin review.
                  </CardDescription>
                </div>
                <div className="relative w-64">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                  <Input
                    placeholder="Search training..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-9"
                  />
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className={cn(
                'mb-4 rounded-lg p-3 text-sm',
                trainingLibraryBanner.tone === 'instructional' && 'border border-blue-200 bg-blue-50 text-blue-800',
                trainingLibraryBanner.tone === 'clear' && 'border border-emerald-200 bg-emerald-50 text-emerald-800',
                trainingLibraryBanner.tone === 'error' && 'border border-red-200 bg-red-50 text-red-700',
              )}>
                <p className="font-medium">{trainingLibraryBanner.title}</p>
                <p className="mt-1">
                  {trainingLibraryBanner.body}
                </p>
              </div>
              {(() => {
                const pendingItems = pendingProposedItems;
                if (pendingItems.length === 0) return null;

                // Group by source_document_id to expose batch opportunities
                const byDoc = pendingItems.reduce((acc, item) => {
                  const key = item.source_document_id || '__none__';
                  if (!acc[key]) acc[key] = [];
                  acc[key].push(item);
                  return acc;
                }, {});
                const multiDocKeys = Object.keys(byDoc).filter(k => byDoc[k].length > 1 && k !== '__none__');

                return (
                  <div className="mb-6">
                    {/* Header + batch bar */}
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="text-sm font-medium text-purple-800 flex items-center gap-2">
                        <Wand2 className="h-4 w-4" />
                        Extracted items awaiting admin review ({pendingItems.length})
                      </h4>
                      {isAdmin && pendingItems.length > 1 && (
                        <div className="flex items-center gap-2">
                          {selectedForBatch.size > 0 ? (
                            <>
                              <span className="text-xs text-purple-700">{selectedForBatch.size} selected</span>
                              <Button
                                size="sm"
                                variant="outline"
                                className="h-7 text-xs border-purple-300 text-purple-700 hover:bg-purple-50"
                                onClick={clearBatchSelection}
                              >
                                Clear
                              </Button>
                              <Button
                                size="sm"
                                className="h-7 text-xs bg-emerald-600 hover:bg-emerald-700 text-white"
                                disabled={batchVerifying || sourceErrors.proposedItems}
                                onClick={handleBatchApproveAndVerify}
                              >
                                {batchVerifying ? (
                                  <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                                ) : (
                                  <CheckCircle2 className="h-3 w-3 mr-1" />
                                )}
                                Approve & Verify selected
                              </Button>
                            </>
                          ) : (
                            multiDocKeys.length > 0 && (
                              <Button
                                size="sm"
                                variant="ghost"
                                className="h-7 text-xs text-purple-700"
                                onClick={() => selectAllForBatch(pendingItems)}
                              >
                                Select all
                              </Button>
                            )
                          )}
                        </div>
                      )}
                    </div>
                    <p className="mb-3 text-sm text-purple-700">
                      Obvious items can be approved and verified in one step. Items that need correction
                      use the <span className="font-medium">Review Evidence</span> flow.
                    </p>

                    <div className="space-y-2">
                      {pendingItems.map((item) => {
                        const quickOk = canQuickVerify(item);
                        const isVerifying = quickVerifying[item.id];
                        const isSelected = selectedForBatch.has(item.id);
                        return (
                          <div
                            key={item.id}
                            className={cn(
                              'p-3 border rounded-lg',
                              isSelected
                                ? 'bg-emerald-50 border-emerald-300'
                                : 'bg-purple-50 border-purple-200'
                            )}
                          >
                            <div className="flex items-start gap-3">
                              {/* Batch checkbox */}
                              {isAdmin && pendingItems.length > 1 && (
                                <input
                                  type="checkbox"
                                  checked={isSelected}
                                  onChange={() => toggleBatchSelect(item.id)}
                                  className="mt-1 h-4 w-4 rounded border-gray-300 text-emerald-600 cursor-pointer focus:ring-emerald-500"
                                />
                              )}

                              {/* Info */}
                              <div className="flex-1 min-w-0">
                                <p className="font-medium text-purple-900 truncate">{item.raw_course_title}</p>
                                <p className="text-xs text-purple-600 mt-0.5">
                                  {item.mapped_training_code
                                    ? `Mapped → ${item.mapped_training_title || item.mapped_training_code}`
                                    : <span className="text-amber-600 font-medium">Unmapped — needs correction</span>}
                                  {item.completed_at && ` · Completed ${formatBackendDate(item.completed_at, { format: 'short' })}`}
                                  {item.expires_at && ` · Expires ${formatBackendDate(item.expires_at, { format: 'short' })}`}
                                </p>
                                {!quickOk && (
                                  <p className="text-xs text-amber-700 mt-0.5">
                                    ⚠ Needs correction before fast-approval
                                    {!item.mapped_training_code && ' — unmapped'}
                                    {!item.completed_at && ' — no completed date'}
                                    {!item.source_document_id && ' — no source certificate'}
                                  </p>
                                )}
                              </div>

                              {/* Badges */}
                              <div className="flex items-center gap-1 flex-shrink-0">
                                <Badge
                                  variant="outline"
                                  className={item.is_mandatory
                                    ? 'bg-red-50 text-red-700 border-red-200 text-xs'
                                    : 'text-gray-500 text-xs'}
                                >
                                  {item.is_mandatory ? 'Required' : 'Additional'}
                                </Badge>
                                {item.is_unmapped && (
                                  <Badge variant="outline" className="bg-amber-50 text-amber-700 border-amber-200 text-xs">
                                    Unmapped
                                  </Badge>
                                )}
                              </div>

                              {/* Action buttons */}
                              {isAdmin && (
                                <div className="flex items-center gap-1 flex-shrink-0">
                                  {quickOk ? (
                                    <>
                                      <Button
                                        size="sm"
                                        className="h-7 px-2 text-xs bg-emerald-600 hover:bg-emerald-700 text-white"
                                        disabled={isVerifying || sourceErrors.proposedItems}
                                        onClick={() => handleApproveAndVerify(item)}
                                        title="Approve this item and mark it verified in one step"
                                      >
                                        {isVerifying ? (
                                          <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                                        ) : (
                                          <CheckCircle2 className="h-3 w-3 mr-1" />
                                        )}
                                        Approve &amp; Verify
                                      </Button>
                                      <Button
                                        size="sm"
                                        variant="outline"
                                        className="h-7 px-2 text-xs text-red-600 border-red-200 hover:bg-red-50"
                                        disabled={isVerifying || sourceErrors.proposedItems}
                                        onClick={() => handleRejectProposed(item)}
                                        title="Mark this extracted item as rejected"
                                      >
                                        <XCircle className="h-3 w-3 mr-1" />
                                        Reject
                                      </Button>
                                      {item.source_document_id && (
                                        <Button
                                          size="sm"
                                          variant="ghost"
                                          className="h-7 px-2 text-xs text-gray-500"
                                          disabled={sourceErrors.proposedItems}
                                          onClick={() => openTrainingEvidenceReview(item)}
                                          title="Open full evidence review"
                                        >
                                          <Eye className="h-3 w-3" />
                                        </Button>
                                      )}
                                    </>
                                  ) : (
                                    <>
                                      <Button
                                        size="sm"
                                        variant="outline"
                                        className="h-7 px-2 text-xs"
                                        disabled={sourceErrors.proposedItems}
                                        onClick={() => openTrainingEvidenceReview(item)}
                                      >
                                        <Eye className="h-3 w-3 mr-1" />
                                        Review Evidence
                                      </Button>
                                      <Button
                                        variant="ghost"
                                        size="sm"
                                        className="h-7 px-2"
                                        disabled={sourceErrors.proposedItems}
                                        onClick={() => handleEditProposed(item)}
                                        title="Edit extracted values"
                                      >
                                        <Edit2 className="h-3 w-3" />
                                      </Button>
                                    </>
                                  )}
                                </div>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                );
              })()}

              {/* All Training Records */}
              {sourceErrors.trainingRecords && (
                <div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                  <span className="font-medium">Cannot assess approved qualifications.</span> Canonical training records did not load, so the approved list is unavailable.
                </div>
              )}
              <div className="mb-3">
                <h4 className="text-sm font-medium text-gray-900">Approved/canonical qualifications</h4>
                <p className="text-sm text-gray-500">
                  These rows come from approved training records. Mandatory uses this canonical record set, not raw certificate files or unreviewed extraction results.
                </p>
              </div>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[240px]">Training Name</TableHead>
                    <TableHead>Source Certificate</TableHead>
                    <TableHead>Completed</TableHead>
                    <TableHead>Expires</TableHead>
                    <TableHead>Required?</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Verified By</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {(() => {
                    const records = canonicalTrainingRecords.length > 0 ? canonicalTrainingRecords : (matrixData.all_qualifications || []);
                    return records
                      .filter(item => {
                        if (!searchQuery) return true;
                        const q = searchQuery.toLowerCase();
                        return item.title?.toLowerCase().includes(q) ||
                               item.code?.toLowerCase().includes(q);
                      })
                      .map((item) => (
                    <TableRow key={item.code || item.id}>
                      <TableCell>
                        <p className="font-medium text-gray-900">{item.title}</p>
                        {item.provider && (
                          <p className="text-xs text-gray-500">{item.provider}</p>
                        )}
                        {item.history_count > 0 && (
                          <p className="text-xs text-indigo-500 mt-0.5">{item.history_count} record{item.history_count !== 1 ? 's' : ''} — history available</p>
                        )}
                      </TableCell>
                      <TableCell>
                        {(item.record_id || item.id) && (item.source_document_id || item.certificate_url || item.evidence_files?.length) ? (
                          <Button
                            variant="link"
                            size="sm"
                            className="h-auto p-0 text-blue-600"
                            onClick={() => onViewCertificate?.(item.record_id || item.id)}
                          >
                            <LinkIcon className="h-3 w-3 mr-1" />
                            View Cert
                          </Button>
                        ) : item.certificate_url ? (
                          <a 
                            href={item.certificate_url} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="inline-flex items-center text-sm text-blue-600 hover:underline"
                          >
                            <LinkIcon className="h-3 w-3 mr-1" />
                            View Cert
                          </a>
                        ) : (
                          <span className="text-sm text-gray-400">-</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <span className="text-sm text-gray-600">
                          {item.completed_at ? formatBackendDate(item.completed_at, { format: 'short' }) : '-'}
                        </span>
                      </TableCell>
                      <TableCell>
                        {item.expires_at ? (
                            <span className={cn(
                              "text-sm",
                              getDisplayStatus(item) === 'expired' ? 'text-red-600 font-medium' :
                              getDisplayStatus(item) === 'expiring_soon' ? 'text-amber-600' :
                              'text-gray-600'
                            )}>
                              {formatBackendDate(item.expires_at, { format: 'short' })}
                            </span>
                        ) : (
                          <span className="text-sm text-gray-400">N/A</span>
                        )}
                      </TableCell>
                      <TableCell>
                        {isRequiredTrainingItem(item) ? (
                          <Badge className="bg-red-100 text-red-700">Required</Badge>
                        ) : (
                          <Badge variant="outline" className="text-gray-500">Optional</Badge>
                        )}
                      </TableCell>
                      <TableCell>{renderStatusBadge(getDisplayStatus(item))}</TableCell>
                      <TableCell>
                        {item.verified_by ? (
                          <div className="text-xs">
                            <p className="text-gray-700">{item.verified_by}</p>
                            {item.verified_at && (
                              <p className="text-gray-400">
                                {formatBackendDate(item.verified_at, { format: 'short' })}
                              </p>
                            )}
                          </div>
                        ) : (
                          <span className="text-xs text-gray-400">-</span>
                        )}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-1">
                          {/* View Button */}
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-8 w-8 p-0"
                            onClick={() => handleOpenDetail(item)}
                            data-testid={`view-training-${item.code || item.id}`}
                          >
                            <Eye className="h-4 w-4" />
                          </Button>
                          
                          {/* Edit Button - Admin only */}
                          {isAdmin && item.completed_at && (
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-8 w-8 p-0 text-gray-500 hover:text-primary"
                              onClick={() => {
                                setEditingItem(item);
                                setEditDialogOpen(true);
                              }}
                              data-testid={`edit-training-${item.code || item.id}`}
                            >
                              <Edit2 className="h-4 w-4" />
                            </Button>
                          )}
                          
                          {/* Verify/Unverify Button - Admin only */}
                          {isAdmin && item.completed_at && (
                            item.is_verified || item.status === 'verified' ? (
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-8 px-2 text-amber-600 hover:text-amber-700 hover:bg-amber-50"
                                onClick={() => handleUnverifyTraining(item)}
                                data-testid={`unverify-training-${item.code || item.id}`}
                              >
                                <XCircle className="h-4 w-4 mr-1" />
                                <span className="text-xs">Unverify</span>
                              </Button>
                            ) : (
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-8 px-2 text-green-600 hover:text-green-700 hover:bg-green-50"
                                onClick={() => openTrainingVerifyReview(item)}
                                data-testid={`verify-training-${item.code || item.id}`}
                              >
                                <CheckCircle className="h-4 w-4 mr-1" />
                                <span className="text-xs">Verify</span>
                              </Button>
                            )
                          )}
                          
                          {/* Delete Button - Admin only */}
                          {isAdmin && (item.record_id || item.id) && (
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-8 px-2 text-red-500 hover:text-red-700 hover:bg-red-50"
                              onClick={() => openDeleteDialog(item)}
                              data-testid={`delete-training-${item.code || item.id}`}
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
                  })()}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        {/* CERTIFICATES TAB */}
        <TabsContent value="certificates" className="mt-4">
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-lg flex items-center gap-2">
                    <Award className="h-5 w-5 text-primary" />
                    Training Certificates
                  </CardTitle>
                  <CardDescription>
                    Certificates are the raw evidence library. Extraction creates review items; it does not verify training or satisfy Mandatory compliance by itself.
                  </CardDescription>
                </div>
                {isAdmin && (
                  <Button onClick={onUploadCertificate} data-testid="upload-cert-btn">
                    <Upload className="h-4 w-4 mr-2" />
                    Upload Certificate
                  </Button>
                )}
              </div>
            </CardHeader>
            <CardContent>
              {sourceErrors.certificates ? (
                <div className="text-center py-12 text-red-700">
                  <AlertTriangle className="h-12 w-12 text-red-400 mx-auto mb-4" />
                  <p className="font-medium">Cannot assess certificates</p>
                  <p className="mt-1 text-sm">Certificate evidence did not load. Certificate counts and extraction links are unavailable.</p>
                  <Button variant="outline" size="sm" onClick={fetchTrainingData} className="mt-4">
                    <RefreshCw className="h-4 w-4 mr-2" />
                    Retry
                  </Button>
                </div>
              ) : certificates.length === 0 ? (
                <div className="text-center py-12">
                  <Award className="h-12 w-12 text-gray-300 mx-auto mb-4" />
                  <p className="text-gray-500">No training certificates uploaded yet</p>
                  {isAdmin && (
                    <Button 
                      variant="outline" 
                      className="mt-4"
                      onClick={onUploadCertificate}
                    >
                      <Upload className="h-4 w-4 mr-2" />
                      Upload First Certificate
                    </Button>
                  )}
                </div>
              ) : (
                <div className="space-y-4">
                  {/* Separate: certificates, proposed_items, unmapped_items */}
                  <div>
                    <h4 className="font-semibold text-blue-900 mb-2">Uploaded Certificates</h4>
                    <ul className="space-y-2">
                      {certificates.map(cert => (
                        <li key={cert.id} className="border border-gray-200 rounded-lg p-3 flex items-center gap-3">
                          <FileText className="h-5 w-5 text-blue-600" />
                          <span className="font-medium">{cert.original_filename || cert.file_name || 'Training Certificate'}</span>
                          <span className="text-xs text-gray-500">Uploaded {formatBackendDate(cert.uploaded_at, { format: 'medium' })}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <h4 className="font-semibold text-purple-900 mt-6 mb-2">Extracted/Proposed Items</h4>
                    <ul className="space-y-2">
                      {(proposedItems && proposedItems.length > 0 ? proposedItems : (matrixData.proposed_items || [])).map(item => (
                        <li key={item.id} className="border border-purple-200 rounded-lg p-3 flex items-center gap-3">
                          <Wand2 className="h-4 w-4 text-purple-600" />
                          <span className="font-medium">{item.mapped_training_title || item.raw_course_title}</span>
                          <span className="text-xs text-gray-500">Status: {item.status}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <h4 className="font-semibold text-amber-900 mt-6 mb-2">Unmapped Items</h4>
                    <ul className="space-y-2">
                      {unmappedItems.map(item => (
                        <li key={item.id} className="border border-amber-200 rounded-lg p-3 flex items-center gap-3">
                          <AlertTriangle className="h-4 w-4 text-amber-600" />
                          <span className="font-medium">{item.raw_course_title}</span>
                          <span className="text-xs text-amber-700">Unmapped</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* ========== EDIT TRAINING DIALOG ========== */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Edit2 className="h-5 w-5 text-blue-600" />
              Edit Training Record
            </DialogTitle>
            <DialogDescription>
              Correct the details for {editingItem?.title || editingItem?.training_title || 'this training'}
            </DialogDescription>
          </DialogHeader>
          
          {editingItem && (
            <div className="space-y-4 py-4">
              {/* Completion Date */}
              <div className="space-y-2">
                <label className="text-sm font-medium">Completion Date</label>
                <Input
                  type="date"
                  defaultValue={editingItem.completed_at?.split('T')[0] || ''}
                  onChange={(e) => setEditingItem({...editingItem, completed_at: e.target.value})}
                  data-testid="edit-training-completion-date"
                />
              </div>
              
              {/* Expiry Date */}
              <div className="space-y-2">
                <label className="text-sm font-medium">Expiry Date</label>
                <Input
                  type="date"
                  defaultValue={editingItem.expires_at?.split('T')[0] || editingItem.expiry_date?.split('T')[0] || ''}
                  onChange={(e) => setEditingItem({...editingItem, expires_at: e.target.value, expiry_date: e.target.value})}
                  data-testid="edit-training-expiry-date"
                />
                <p className="text-xs text-slate-500">Leave blank for training that doesn't expire</p>
              </div>
              
              {/* Provider */}
              <div className="space-y-2">
                <label className="text-sm font-medium">Provider</label>
                <Input
                  type="text"
                  defaultValue={editingItem.provider || editingItem.training_provider || ''}
                  onChange={(e) => setEditingItem({...editingItem, provider: e.target.value})}
                  placeholder="e.g., Skills for Care, Company Training"
                  data-testid="edit-training-provider"
                />
              </div>
              
              {/* Certificate Number */}
              <div className="space-y-2">
                <label className="text-sm font-medium">Certificate Number (optional)</label>
                <Input
                  type="text"
                  defaultValue={editingItem.certificate_number || ''}
                  onChange={(e) => setEditingItem({...editingItem, certificate_number: e.target.value})}
                  placeholder="e.g., CERT-12345"
                  data-testid="edit-training-cert-number"
                />
              </div>
            </div>
          )}
          
          <DialogFooter>
            <Button 
              variant="outline" 
              onClick={() => {
                setEditDialogOpen(false);
                setEditingItem(null);
              }}
            >
              Cancel
            </Button>
            <Button
              onClick={async () => {
                if (!editingItem) return;
                try {
                  // Use the PATCH endpoint which accepts bulk updates with proper format
                  const trainingCode = editingItem.code || editingItem.requirement_id || editingItem.id;
                  
                  await axios.patch(
                    `${API}/api/employees/${employeeId}/training/${trainingCode}`,
                    {
                      completion_date: editingItem.completed_at,
                      expiry_date: editingItem.expires_at || editingItem.expiry_date || null,
                      reason: 'Admin date correction via Edit dialog'
                    },
                    { headers: { Authorization: `Bearer ${token}` } }
                  );
                  toast.success('Training record updated successfully');
                  setEditDialogOpen(false);
                  setEditingItem(null);
                  fetchTrainingData();
                  onRefresh?.();
                } catch (err) {
                  console.error('Error updating training:', err);
                  toast.error(err.response?.data?.detail || 'Failed to update training record');
                }
              }}
              className="bg-blue-600 hover:bg-blue-700"
              data-testid="edit-training-save-btn"
            >
              Save Changes
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Training Detail Drawer */}
      <TrainingDetailDrawer
        isOpen={drawerOpen}
        onClose={() => {
          setDrawerOpen(false);
          setSelectedTraining(null);
        }}
        trainingItem={selectedTraining}
        employeeId={employeeId}
        onUpdate={() => {
          fetchTrainingData();
          onRefresh?.();
        }}
        isAdmin={isAdmin}
      />

      {/* AI Certificate Extractor with Preview Step */}
      <TrainingCertificateExtractor
        employeeId={employeeId}
        employeeName={employeeName}
        isOpen={extractorOpen}
        onClose={() => setExtractorOpen(false)}
        onSuccess={() => {
          fetchTrainingData();
          onRefresh?.();
        }}
      />

      <EvidenceReviewViewerDialog
        isOpen={trainingReviewOpen}
        onClose={closeTrainingReview}
        file={trainingReviewPurpose === 'verify'
          ? getSourceCertificateFileForTrainingItem(trainingReviewItem)
          : getSourceCertificateFileForProposedItem(trainingReviewItem)}
        employeeId={employeeId}
        employeeName={employeeName}
        requirementType="training_certificate"
        mode="training-review"
        trainingItem={trainingReviewItem}
        trainingAcceptLabel={trainingReviewPurpose === 'verify' ? 'Verify training' : 'Accept extracted item'}
        trainingRejectLabel={trainingReviewPurpose === 'verify' ? null : 'Reject / needs correction'}
        trainingCompletionMessage={trainingReviewPurpose === 'verify'
          ? 'Training verification has been recorded after evidence review.'
          : 'The extracted training item decision has been recorded. Verification remains a separate step on the canonical training record.'}
        onTrainingAccepted={async ({ notes }) => {
          if (!trainingReviewItem) return;
          if (trainingReviewPurpose === 'verify') {
            await submitVerifyTraining(trainingReviewItem);
          } else {
            await handleApproveProposed(trainingReviewItem, notes);
          }
        }}
        onTrainingRejected={trainingReviewPurpose === 'verify' ? undefined : async ({ notes }) => {
          if (!trainingReviewItem) return;
          await handleRejectProposed(trainingReviewItem, notes);
        }}
      />
      
      {/* Delete Training Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-red-600">
              <Trash2 className="h-5 w-5" />
              Delete Training Record
            </DialogTitle>
            <DialogDescription>
              This will soft-delete "{deletingItem?.title}" from the employee's training records.
              The record will be archived for audit purposes.
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <div className="p-3 bg-red-50 rounded-lg border border-red-100">
              <p className="text-sm text-red-800">
                <strong>Training:</strong> {deletingItem?.title}
              </p>
              {deletingItem?.completed_at && (
                <p className="text-sm text-red-600 mt-1">
                  Completed: {formatBackendDate(deletingItem.completed_at, { format: 'short' })}
                </p>
              )}
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-1">
                Reason for deletion (required for audit trail)
              </label>
              <Input
                value={deleteReason}
                onChange={(e) => setDeleteReason(e.target.value)}
                placeholder="e.g., Test data, duplicate entry, uploaded in error..."
                data-testid="delete-reason-input"
              />
            </div>
          </div>
          
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setDeleteDialogOpen(false);
                setDeletingItem(null);
                setDeleteReason('');
              }}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDeleteTraining}
              disabled={deleting || !deleteReason.trim()}
              data-testid="confirm-delete-btn"
            >
              {deleting ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <Trash2 className="h-4 w-4 mr-2" />
              )}
              Delete Training
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={unverifyDialogOpen} onOpenChange={setUnverifyDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-amber-600">
              <AlertTriangle className="h-5 w-5" />
              Unverify Training Record
            </DialogTitle>
            <DialogDescription>
              This will mark "{unverifyItem?.title}" as unverified and require re-verification.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3 py-2">
            <label className="block text-sm font-medium">Reason *</label>
            <Input
              value={unverifyReason}
              onChange={(e) => setUnverifyReason(e.target.value)}
              placeholder="Reason for unverifying this training record"
              data-testid="unverify-reason-input"
            />
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setUnverifyDialogOpen(false);
                setUnverifyItem(null);
                setUnverifyReason('');
              }}
            >
              Cancel
            </Button>
            <Button
              className="bg-amber-600 hover:bg-amber-700 text-white"
              onClick={confirmUnverifyTraining}
              disabled={unverifying || !unverifyReason.trim()}
              data-testid="confirm-unverify-btn"
            >
              {unverifying ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
              Unverify
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Remove certificate confirm dialog */}
      <Dialog open={!!removeCertDialogCert} onOpenChange={open => { if (!open) setRemoveCertDialogCert(null); }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Remove certificate?</DialogTitle>
            <DialogDescription>
              This will delete the certificate file and any extracted training items that have not yet been approved.
              Already-approved training records will be preserved.
            </DialogDescription>
          </DialogHeader>
          {removeCertDialogCert && (
            <div className="rounded-md border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700 mt-2">
              <p className="font-medium">{removeCertDialogCert.original_filename || removeCertDialogCert.file_name || 'Training Certificate'}</p>
              <p className="text-xs text-slate-500 mt-0.5">Uploaded {formatBackendDate(removeCertDialogCert.uploaded_at, { format: 'medium' })}</p>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setRemoveCertDialogCert(null)} disabled={removingCert}>
              Cancel
            </Button>
            <Button
              className="bg-red-600 hover:bg-red-700 text-white"
              onClick={handleRemoveCertificate}
              disabled={removingCert}
              data-testid="confirm-remove-cert-btn"
            >
              {removingCert ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Trash2 className="h-4 w-4 mr-2" />}
              Remove certificate
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

