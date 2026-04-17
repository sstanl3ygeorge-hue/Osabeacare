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

const API = process.env.REACT_APP_BACKEND_URL;

// Status styling for training items
const STATUS_STYLES = {
  current: { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200', icon: CheckCircle2, label: 'Verified' },
  completed: { bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200', icon: Clock, label: 'Awaiting Verification' },
  verified: { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200', icon: CheckCircle2, label: 'Verified' },
  expiring_soon: { bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200', icon: Clock, label: 'Renew Soon' },
  due_soon: { bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200', icon: Clock, label: 'Due Soon' },
  expired: { bg: 'bg-red-50', text: 'text-red-700', border: 'border-red-200', icon: AlertTriangle, label: 'Expired' },
  overdue: { bg: 'bg-red-50', text: 'text-red-700', border: 'border-red-200', icon: AlertTriangle, label: 'Overdue' },
  missing: { bg: 'bg-gray-100', text: 'text-gray-600', border: 'border-gray-200', icon: XCircle, label: 'Missing' },
  pending: { bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200', icon: Clock, label: 'Pending Review' },
  awaiting_review: { bg: 'bg-purple-50', text: 'text-purple-700', border: 'border-purple-200', icon: Clock, label: 'Awaiting Review' },
  rejected: { bg: 'bg-orange-50', text: 'text-orange-700', border: 'border-orange-200', icon: XCircle, label: 'Rejected' },
  proposed: { bg: 'bg-purple-50', text: 'text-purple-700', border: 'border-purple-200', icon: Wand2, label: 'Awaiting Review' },
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
  const [activeTab, setActiveTab] = useState('mandatory');
  
  // Data states
  const [mandatoryTraining, setMandatoryTraining] = useState([]);
  const [additionalTraining, setAdditionalTraining] = useState([]);
  const [certificates, setCertificates] = useState([]);
  const [proposedItems, setProposedItems] = useState([]);
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
  
  // Delete training state
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deletingItem, setDeletingItem] = useState(null);
  const [deleteReason, setDeleteReason] = useState('');
  const [deleting, setDeleting] = useState(false);
  const [unverifyDialogOpen, setUnverifyDialogOpen] = useState(false);
  const [unverifyItem, setUnverifyItem] = useState(null);
  const [unverifyReason, setUnverifyReason] = useState('');
  const [unverifying, setUnverifying] = useState(false);
  
  const isAdmin = user?.role === 'admin' || user?.role === 'superadmin' || user?.role === 'super_admin';

  // Fetch all training data
  const fetchTrainingData = useCallback(async () => {
    if (!employeeId) return;
    
    setLoading(true);
    try {
      // Fetch training matrix data
      const [matrixRes, proposedRes, docsRes] = await Promise.all([
        axios.get(`${API}/api/employees/${employeeId}/training/matrix`, {
          headers: { Authorization: `Bearer ${token}` }
        }).catch(() => null),
        axios.get(`${API}/api/employees/${employeeId}/training/proposed-items`, {
          headers: { Authorization: `Bearer ${token}` }
        }).catch(() => ({ data: [] })),
        axios.get(`${API}/api/employees/${employeeId}/training/certificates`, {
          headers: { Authorization: `Bearer ${token}` }
        }).catch(() => ({ data: { certificates: [] } }))
      ]);
      
      // Process matrix data
      const matrixData = matrixRes?.data || {};
      const allItems = matrixData.items || [];
      const additionalFromMatrix = matrixData.additional_items || [];
      
      // All items from the main matrix endpoint are mandatory (8 mandatory items)
      // They may have blocker=true/false but are all required
      setMandatoryTraining(allItems);
      setAdditionalTraining(additionalFromMatrix);
      
      // Handle proposed items - ensure it's an array
      const proposedData = proposedRes?.data;
      const proposedArray = Array.isArray(proposedData) ? proposedData : 
                           proposedData?.items || proposedData?.proposed_items || [];
      setProposedItems(proposedArray);
      
      // Get training certificates from merged endpoint (canonical + legacy)
      const docsData = docsRes?.data;
      const trainingCerts = docsData?.certificates || [];
      setCertificates(trainingCerts);
      
      // Use the summary from API which already has correct calculations
      const apiSummary = matrixData.summary || {};
      const pendingReview = proposedArray.filter(p => p.status === 'proposed').length;
      
      setSummary({
        totalRequired: apiSummary.total || allItems.length,
        current: apiSummary.current || 0,
        needsRenewal: apiSummary.expiring || 0,
        missing: apiSummary.missing || 0,
        blockers: apiSummary.blockers || 0,
        additionalQualifications: apiSummary.additional_count || additionalFromMatrix.length,
        certificatesUploaded: trainingCerts.length,
        needsReview: pendingReview
      });
      
    } catch (err) {
      console.error('Error fetching training data:', err);
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
    setEditingItem(item);
    setEditDialogOpen(true);
  };

  // Approve proposed item
  const handleApproveProposed = async (item) => {
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
            expires_at: item.expires_at
          }]
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Training item approved');
      fetchTrainingData();
      onRefresh?.();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to approve item');
    }
  };

  // Reject proposed item
  const handleRejectProposed = async (item) => {
    try {
      await axios.post(
        `${API}/api/employees/${employeeId}/training/proposed-items/review`,
        {
          items: [{
            item_id: item.id,
            approve: false,
            notes: 'Rejected by admin'
          }]
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success('Training item rejected');
      fetchTrainingData();
      onRefresh?.();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to reject item');
    }
  };

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

  // Verify training record - Admin only
  const handleVerifyTraining = async (item) => {
    try {
      await axios.post(
        `${API}/api/employees/${employeeId}/training/${item.code || item.id}/verify`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success(`${item.title} verified`);
      fetchTrainingData();
      onRefresh?.();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to verify training');
    }
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
    try {
      const response = await axios.post(
        `${API}/api/employees/${employeeId}/training/re-extract`,
        { document_id: documentId },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (response.data.success && response.data.trainings?.length > 0) {
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
          toast.info('All extracted trainings already pending review');
        }
        fetchTrainingData();
      } else {
        toast.error(response.data.message || 'No trainings detected');
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to extract training');
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

  // Progress calculation
  const progressPercent = summary.totalRequired > 0
    ? Math.round((summary.current / summary.totalRequired) * 100)
    : 0;

  if (loading) {
    return (
      <Card className="border-dashed" data-testid="training-matrix-loading">
        <CardContent className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-primary" />
          <span className="ml-2 text-gray-500">Loading training records...</span>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6" data-testid="audit-ready-training-matrix">
      {/* ============================================ */}
      {/* SUMMARY CARDS                               */}
      {/* ============================================ */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-3">
        <div className="p-3 bg-white border border-gray-200 rounded-lg">
          <p className="text-2xl font-bold text-gray-900">{summary.totalRequired}</p>
          <p className="text-xs text-gray-500">Required</p>
        </div>
        <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg">
          <p className="text-2xl font-bold text-emerald-700">{summary.current}</p>
          <p className="text-xs text-emerald-600">Verified</p>
        </div>
        <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
          <p className="text-2xl font-bold text-amber-700">{summary.needsRenewal}</p>
          <p className="text-xs text-amber-600">Needs Renewal</p>
        </div>
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-2xl font-bold text-red-700">{summary.missing}</p>
          <p className="text-xs text-red-600">Missing</p>
        </div>
        <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
          <p className="text-2xl font-bold text-blue-700">{summary.additionalQualifications}</p>
          <p className="text-xs text-blue-600">Additional</p>
        </div>
        <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg">
          <p className="text-2xl font-bold text-slate-700">{summary.certificatesUploaded}</p>
          <p className="text-xs text-slate-600">Certificates</p>
        </div>
        <div className="p-3 bg-purple-50 border border-purple-200 rounded-lg">
          <p className="text-2xl font-bold text-purple-700">{summary.needsReview}</p>
          <p className="text-xs text-purple-600">Needs Review</p>
        </div>
        <div className="p-3 bg-gray-100 border border-gray-200 rounded-lg">
          <p className="text-2xl font-bold text-gray-700">{progressPercent}%</p>
          <p className="text-xs text-gray-500">Compliant</p>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-700">Mandatory Training Completion</span>
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
            All Qualifications ({summary.additionalQualifications + summary.totalRequired})
          </TabsTrigger>
          <TabsTrigger value="certificates" className="flex items-center gap-2">
            <Award className="h-4 w-4" />
            Certificates ({summary.certificatesUploaded})
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
                    These 8 mandatory training items are required for work readiness
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
                  {mandatoryTraining.map((item) => (
                    <TableRow 
                      key={item.code || item.id}
                      className={cn(item.blocker && 'bg-red-50/50')}
                    >
                      <TableCell>
                        <div className="flex items-center gap-2">
                          {item.blocker && (
                            <AlertTriangle className="h-4 w-4 text-red-600 flex-shrink-0" />
                          )}
                          <div>
                            <p className="font-medium text-gray-900">{item.title}</p>
                            {item.blocker && (
                              <p className="text-xs text-red-600">Work blocker</p>
                            )}
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>{renderStatusBadge(item.status)}</TableCell>
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
                        {item.verified || item.is_verified ? (
                          <div className="flex flex-col">
                            <Badge className="bg-green-100 text-green-700 border-green-200 w-fit">
                              <CheckCircle className="h-3 w-3 mr-1" />
                              Verified
                            </Badge>
                            {item.verified_by && (
                              <span className="text-xs text-gray-500 mt-1">{item.verified_by}</span>
                            )}
                          </div>
                        ) : item.status !== 'missing' ? (
                          <Badge className="bg-amber-100 text-amber-700 border-amber-200">
                            Unverified
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
                  ))}
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
                    Complete training record including additional qualifications
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
              {/* Proposed Items Needing Review */}
              {proposedItems.filter(p => p.status === 'proposed').length > 0 && (
                <div className="mb-6">
                  <h4 className="text-sm font-medium text-purple-800 mb-3 flex items-center gap-2">
                    <Wand2 className="h-4 w-4" />
                    Awaiting Review ({proposedItems.filter(p => p.status === 'proposed').length})
                  </h4>
                  <div className="space-y-2">
                    {proposedItems.filter(p => p.status === 'proposed').map((item) => (
                      <div 
                        key={item.id}
                        className="p-3 bg-purple-50 border border-purple-200 rounded-lg flex items-center justify-between"
                      >
                        <div className="flex items-center gap-3">
                          <Wand2 className="h-5 w-5 text-purple-600" />
                          <div>
                            <p className="font-medium text-purple-900">{item.raw_course_title}</p>
                            <p className="text-xs text-purple-600">
                              Extracted from certificate • 
                              {item.mapped_training_title && ` Mapped to: ${item.mapped_training_title}`}
                              {item.completed_at && ` • Completed: ${formatBackendDate(item.completed_at, { format: 'short' })}`}
                              {item.expires_at && ` • Expires: ${formatBackendDate(item.expires_at, { format: 'short' })}`}
                            </p>
                          </div>
                        </div>
                        {isAdmin && (
                          <div className="flex items-center gap-2">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleEditProposed(item)}
                            >
                              <Edit2 className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              className="text-red-600 border-red-200 hover:bg-red-50"
                              onClick={() => handleRejectProposed(item)}
                            >
                              <XCircle className="h-4 w-4" />
                            </Button>
                            <Button
                              size="sm"
                              className="bg-green-600 hover:bg-green-700 text-white"
                              onClick={() => handleApproveProposed(item)}
                            >
                              <CheckCircle className="h-4 w-4 mr-1" />
                              Approve
                            </Button>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* All Training Records */}
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
                    // Deduplicate: one row per canonical training code/title
                    const seen = new Set();
                    return [...mandatoryTraining, ...additionalTraining]
                      .filter(item => {
                        const key = (item.code || item.title || item.id || '').toLowerCase().replace(/[\s&_-]+/g, ' ').trim();
                        if (seen.has(key)) return false;
                        seen.add(key);
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
                            item.status === 'expired' ? 'text-red-600 font-medium' :
                            item.status === 'expiring_soon' ? 'text-amber-600' :
                            'text-gray-600'
                          )}>
                            {formatBackendDate(item.expires_at, { format: 'short' })}
                          </span>
                        ) : (
                          <span className="text-sm text-gray-400">N/A</span>
                        )}
                      </TableCell>
                      <TableCell>
                        {item.is_required || item.blocker !== undefined ? (
                          <Badge className="bg-red-100 text-red-700">Required</Badge>
                        ) : (
                          <Badge variant="outline" className="text-gray-500">Optional</Badge>
                        )}
                      </TableCell>
                      <TableCell>{renderStatusBadge(item.status)}</TableCell>
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
                                onClick={() => handleVerifyTraining(item)}
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
                    Uploaded certificates with extracted training items
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
              {certificates.length === 0 ? (
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
                  {certificates.map((cert) => {
                    // Find proposed items linked to this certificate
                    const linkedItems = proposedItems.filter(p => p.source_document_id === cert.id);
                    const approvedItems = linkedItems.filter(p => p.status === 'approved' || p.status === 'merged');
                    const pendingItems = linkedItems.filter(p => p.status === 'proposed');
                    
                    return (
                      <div 
                        key={cert.id}
                        className="border border-gray-200 rounded-lg overflow-hidden"
                      >
                        {/* Certificate Header */}
                        <div className="p-4 bg-gray-50 flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                              <FileText className="h-5 w-5 text-blue-600" />
                            </div>
                            <div>
                              <p className="font-medium text-gray-900">
                                {cert.original_filename || cert.file_name || 'Training Certificate'}
                              </p>
                              <p className="text-xs text-gray-500">
                                Uploaded {formatBackendDate(cert.uploaded_at, { format: 'medium' })}
                                {cert.uploaded_by && ` by ${cert.uploaded_by}`}
                              </p>
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            <Badge variant="outline" className="text-xs">
                              {linkedItems.length} item{linkedItems.length !== 1 ? 's' : ''} extracted
                            </Badge>
                            {pendingItems.length > 0 && (
                              <Badge className="bg-purple-100 text-purple-700">
                                {pendingItems.length} pending review
                              </Badge>
                            )}
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-8 w-8 p-0"
                              onClick={() => onViewCertificate?.(cert.id)}
                              title="View certificate"
                            >
                              <Eye className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-8 w-8 p-0"
                              title="Download"
                            >
                              <Download className="h-4 w-4" />
                            </Button>
                            {isAdmin && (
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-8 px-2"
                                onClick={() => handleReExtract(cert.id)}
                                title="Re-run extraction"
                              >
                                <Wand2 className="h-4 w-4 mr-1" />
                                Re-extract
                              </Button>
                            )}
                          </div>
                        </div>
                        
                        {/* Extracted Items */}
                        {linkedItems.length > 0 && (
                          <div className="p-4 border-t border-gray-200">
                            <p className="text-xs text-gray-500 uppercase tracking-wide font-medium mb-2">
                              Extracted Training Items
                            </p>
                            <div className="space-y-2">
                              {linkedItems.map((item) => (
                                <div 
                                  key={item.id}
                                  className={cn(
                                    "p-2 rounded-lg flex items-center justify-between",
                                    item.status === 'proposed' ? 'bg-purple-50 border border-purple-200' :
                                    item.status === 'approved' || item.status === 'merged' ? 'bg-green-50 border border-green-200' :
                                    'bg-gray-50 border border-gray-200'
                                  )}
                                >
                                  <div className="flex items-center gap-2">
                                    {item.status === 'approved' || item.status === 'merged' ? (
                                      <CheckCircle className="h-4 w-4 text-green-600" />
                                    ) : item.status === 'proposed' ? (
                                      <Clock className="h-4 w-4 text-purple-600" />
                                    ) : (
                                      <XCircle className="h-4 w-4 text-gray-400" />
                                    )}
                                    <div>
                                      <p className="text-sm font-medium">
                                        {item.mapped_training_title || item.raw_course_title}
                                      </p>
                                      <p className="text-xs text-gray-500">
                                        {item.completed_at && `Completed: ${formatBackendDate(item.completed_at, { format: 'short' })}`}
                                        {item.expires_at && ` • Expires: ${formatBackendDate(item.expires_at, { format: 'short' })}`}
                                      </p>
                                    </div>
                                  </div>
                                  <div className="flex items-center gap-2">
                                    {item.confidence && (
                                      <span className="text-xs text-gray-500">
                                        {Math.round(item.confidence * 100)}% confidence
                                      </span>
                                    )}
                                    {item.mapped_training_code && (
                                      <Badge variant="outline" className="text-xs">
                                        → {item.mapped_training_code}
                                      </Badge>
                                    )}
                                    {renderStatusBadge(item.status)}
                                  </div>
                                </div>
                              ))}
                            </div>
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
    </div>
  );
}
