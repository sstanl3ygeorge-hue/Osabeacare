import { useState, useEffect, useRef, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter, DialogDescription } from '../../components/ui/dialog';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '../../components/ui/dropdown-menu';
import { toast } from 'sonner';
import { 
  GraduationCap, Plus, CheckCircle, Clock, AlertTriangle, Loader2, 
  MoreVertical, Edit, History, Filter, CalendarClock, ShieldCheck,
  Download, FileSpreadsheet, FileText, FileSearch, Eye, ExternalLink
} from 'lucide-react';
import DocumentExtractionReview from '../../components/documents/DocumentExtractionReview';
import { formatBackendDate, formatBackendDateTime } from '../../lib/dateUtils';
import { API_BASE_URL, API_ROOT_URL } from './';

const API = API_BASE_URL;

// ═══════════════════════════════════════════════════════════════════════════════
// SINGLE SOURCE OF TRUTH: Status comes from backend ONLY
// Frontend MUST use backend-computed status (computed_status, renewal_status, status_label, status_color)
// NO local date calculations for expired/valid/renewal status
// ═══════════════════════════════════════════════════════════════════════════════

// Helper to get expiry display from backend-computed fields ONLY
const getBackendExpiryStatus = (record) => {
  // Use backend-computed fields - NO LOCAL CALCULATION
  if (record.computed_status) {
    return {
      status: record.renewal_status || record.computed_status,
      label: record.status_label || record.computed_status,
      daysText: record.days_until_expiry !== null && record.days_until_expiry !== undefined
        ? (record.days_until_expiry < 0 ? `${Math.abs(record.days_until_expiry)} days ago` : `${record.days_until_expiry} days`)
        : '',
      color: record.status_color || 'gray'
    };
  }
  
  // No computed status and no expiry = no expiry badge needed
  if (!record.expiry_date) return null;
  
  // Backend should always provide computed_status for records with expiry_date
  // If we reach here, it's a data issue - return safe default
  console.warn('Training record missing computed_status:', record.id);
  return {
    status: 'unknown',
    label: 'Status pending',
    daysText: '',
    color: 'gray'
  };
};

export default function TrainingPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [training, setTraining] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [trainingDefinitions, setTrainingDefinitions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [addOpen, setAddOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  // Track if initial data has been fetched to prevent infinite loops
  const hasFetched = useRef(false);
  
  // Initialize filter from URL params
  const [filter, setFilter] = useState(searchParams.get('filter') || 'all');
  const [employeeFilter, setEmployeeFilter] = useState(searchParams.get('employee_id') || 'all');
  const { token, isAuditor, loading: authLoading } = useAuth();

  // Sync filter state to URL - keep deep links stable for dashboard drill-down
  useEffect(() => {
    const currentFilter = searchParams.get('filter') || 'all';
    const currentEmployee = searchParams.get('employee_id') || 'all';

    // Only update URL if state differs from URL
    if (currentFilter !== filter || currentEmployee !== employeeFilter) {
      const newParams = new URLSearchParams(searchParams);
      if (filter && filter !== 'all') {
        newParams.set('filter', filter);
      } else {
        newParams.delete('filter');
      }
      if (employeeFilter && employeeFilter !== 'all') {
        newParams.set('employee_id', employeeFilter);
      } else {
        newParams.delete('employee_id');
      }
      setSearchParams(newParams, { replace: true });
    }
  }, [filter, employeeFilter, searchParams, setSearchParams]);


  // Correction modal state
  const [editOpen, setEditOpen] = useState(false);
  const [editingRecord, setEditingRecord] = useState(null);
  const [correction, setCorrection] = useState({ field: 'expiry_date', new_value: '', reason: '' });
  
  // History modal state
  const [historyOpen, setHistoryOpen] = useState(false);
  const [historyRecord, setHistoryRecord] = useState(null);
  const [historyData, setHistoryData] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  
  // Export state
  const [exporting, setExporting] = useState(false);
  
  // Summary data from backend (single source of truth)
  const [matrixSummary, setMatrixSummary] = useState(null);
  const [pendingExtractions, setPendingExtractions] = useState([]);
  const [showExtractionPanel, setShowExtractionPanel] = useState(false);
  
  // Extraction review modal
  const [extractionReviewOpen, setExtractionReviewOpen] = useState(false);
  const [reviewingDocumentId, setReviewingDocumentId] = useState(null);

  const [newRecord, setNewRecord] = useState({
    employee_id: '',
    training_name: '',
    mandatory: true,
    status: 'not_started',
    expiry_date: ''
  });

  const fetchData = useCallback(async () => {
    if (!token) {
      setLoading(false);
      return;
    }
    
    try {
      setLoading(true);
      const headers = { Authorization: `Bearer ${token}` };
      
      const [trainingRes, employeesRes, summaryRes, extractionsRes, defsRes] = await Promise.all([
        axios.get(`${API}/training-records`, { headers }),
        // Training matrix is employee-only: exclude applicant/recruitment-stage people
        axios.get(`${API}/employees?stage=employee`, { headers }),
        axios.get(`${API}/training/matrix/summary`, { headers }).catch((err) => {
          console.warn('[TrainingPage] Matrix summary fetch failed:', err);
          return null;
        }),
        axios.get(`${API}/document-extractions/pending-review?limit=50`, { headers }).catch((err) => {
          console.warn('[TrainingPage] Extractions fetch failed:', err);
          return null;
        }),
        axios.get(`${API}/training/definitions`, { headers }).catch((err) => {
          console.warn('[TrainingPage] Training definitions fetch failed:', err);
          return null;
        })
      ]);
      
      setTraining(trainingRes.data || []);
      const activeWorkforceEmployees = (employeesRes.data || []).filter((employee) => {
        const status = (employee?.status || '').toLowerCase();
        return status === 'active' || status === 'active_employee';
      });
      setEmployees(activeWorkforceEmployees);
      
      // Set training definitions from canonical source
      if (defsRes?.data?.definitions) {
        setTrainingDefinitions(defsRes.data.definitions);
      }
      
      // Set summary from backend (canonical source)
      if (summaryRes?.data) {
        setMatrixSummary(summaryRes.data);
      }
      
      // Filter extractions to training certificates only
      if (extractionsRes?.data?.extractions) {
        const trainingExtractions = extractionsRes.data.extractions.filter(
          ext => ext.document_type === 'training_certificate'
        );
        setPendingExtractions(trainingExtractions);
      }
    } catch (error) {
      console.error('Failed to fetch training data:', error);
      toast.error('Failed to load training data. Please refresh the page.');
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    // Only fetch data once when auth is complete and token is available
    if (!authLoading && token && !hasFetched.current) {
      hasFetched.current = true;
      fetchData();
    }
  }, [token, authLoading, fetchData]);

  const handleAddTraining = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    
    try {
      const payload = { ...newRecord };
      if (!payload.expiry_date) delete payload.expiry_date;
      
      await axios.post(`${API}/training-records`, payload, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Training record added');
      setAddOpen(false);
      setNewRecord({ employee_id: '', training_name: '', mandatory: true, status: 'not_started', expiry_date: '' });
      hasFetched.current = false; // Allow refetch after mutation
      await fetchData();
    } catch (error) {
      toast.error('Failed to add training record');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCorrection = async () => {
    if (!correction.reason || correction.reason.trim().length < 3) {
      toast.error('Please provide a reason for this correction (minimum 3 characters)');
      return;
    }
    if (!correction.new_value) {
      toast.error('Please enter the new value');
      return;
    }
    
    setIsSubmitting(true);
    try {
      await axios.post(`${API}/training-records/${editingRecord.id}/correct`, {
        field: correction.field,
        old_value: editingRecord[correction.field],
        new_value: correction.new_value,
        reason: correction.reason.trim()
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      toast.success('Training record corrected');
      setEditOpen(false);
      setEditingRecord(null);
      setCorrection({ field: 'expiry_date', new_value: '', reason: '' });
      hasFetched.current = false; // Allow refetch after mutation
      await fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to correct training record');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleViewHistory = async (record) => {
    setHistoryRecord(record);
    setHistoryOpen(true);
    setHistoryLoading(true);
    
    try {
      const res = await axios.get(`${API}/training-records/${record.id}/history`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setHistoryData(res.data.history || []);
    } catch (error) {
      toast.error('Failed to load history');
      setHistoryData([]);
    } finally {
      setHistoryLoading(false);
    }
  };

  const openEditModal = (record, field = 'expiry_date') => {
    setEditingRecord(record);
    setCorrection({ 
      field, 
      new_value: record[field] || '', 
      reason: '' 
    });
    setEditOpen(true);
  };

  const getEmployeeName = (employeeId) => {
    const emp = employees.find(e => e.id === employeeId);
    return emp ? `${emp.first_name} ${emp.last_name}` : null;
  };

  // Export training matrix - uses existing backend endpoint
  const handleExport = async (format) => {
    setExporting(true);
    try {
      const response = await axios.get(`${API}/training-matrix/export`, {
        params: { format },
        headers: { Authorization: `Bearer ${token}` },
        responseType: 'blob'
      });
      
      // Create download link
      const blob = new Blob([response.data], { 
        type: format === 'csv' ? 'text/csv' : 'application/pdf' 
      });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      
      // Extract filename from response headers or generate default
      const contentDisposition = response.headers['content-disposition'];
      let filename = `training_matrix.${format}`;
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
      
      toast.success(`Training matrix exported as ${format.toUpperCase()}`);
    } catch (error) {
      console.error('Export failed:', error);
      toast.error('Failed to export training matrix');
    } finally {
      setExporting(false);
    }
  };

  // Filter training records using backend-computed status
  const filteredTraining = training.filter(record => {
    if (employeeFilter !== 'all' && record.employee_id !== employeeFilter) return false;
    if (filter === 'all') return true;
    
    // Use backend-computed renewal_status or computed_status
    const renewalStatus = record.renewal_status || record.computed_status;
    if (!renewalStatus && (filter === 'expired' || filter === 'expiring_soon')) return false;
    if (!renewalStatus && filter === 'valid') return !record.expiry_date;
    
    return renewalStatus === filter || (filter === 'expiring_soon' && renewalStatus === 'needs_renewal');
  });

  // Use backend summary as source of truth, fallback to local calculation
  const completed = matrixSummary?.completed ?? training.filter(t => t.status === 'completed' || t.computed_status === 'completed').length;
  const expired = matrixSummary?.expired ?? training.filter(t => t.renewal_status === 'expired' || t.computed_status === 'expired').length;
  const expiringSoon = matrixSummary?.needs_renewal ?? training.filter(t => t.renewal_status === 'expiring_soon' || t.computed_status === 'needs_renewal').length;
  const verified = matrixSummary?.verified ?? training.filter(t => t.verified).length;
  const awaitingExtractionReview = matrixSummary?.awaiting_extraction_review ?? pendingExtractions.length;

  // Handle extraction review
  const handleOpenExtractionReview = (documentId) => {
    setReviewingDocumentId(documentId);
    setExtractionReviewOpen(true);
  };

  const handleExtractionReviewComplete = () => {
    setExtractionReviewOpen(false);
    setReviewingDocumentId(null);
    hasFetched.current = false; // Allow refetch after mutation
    fetchData(); // Refresh to update counts
  };

  return (
    <div className="space-y-6" data-testid="training-page">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="font-heading text-2xl sm:text-3xl font-bold text-text-primary">
            Training Matrix
          </h1>
          <p className="text-text-muted mt-1">
            Track staff training, expiry dates, and renewals. Use filters to find risks quickly.
          </p>
        </div>
        
        <div className="flex items-center gap-2">
          {/* Export Dropdown */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button 
                variant="outline" 
                className="rounded-xl" 
                disabled={exporting}
                data-testid="export-matrix-btn"
              >
                {exporting ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Download className="mr-2 h-4 w-4" />
                )}
                Export
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => handleExport('csv')} data-testid="export-csv">
                <FileSpreadsheet className="mr-2 h-4 w-4" />
                Export as CSV
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => handleExport('pdf')} data-testid="export-pdf">
                <FileText className="mr-2 h-4 w-4" />
                Export as PDF
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
          
          {!isAuditor() && (
            <Dialog open={addOpen} onOpenChange={setAddOpen}>
              <DialogTrigger asChild>
                <Button className="bg-primary hover:bg-primary-hover text-white rounded-xl" data-testid="add-training-btn">
                  <Plus className="mr-2 h-4 w-4" />
                  Add Training
                </Button>
              </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle className="font-heading">Add Training Record</DialogTitle>
              </DialogHeader>
              <form onSubmit={handleAddTraining} className="space-y-4 mt-4">
                <div className="space-y-2">
                  <Label>Employee *</Label>
                  <Select value={newRecord.employee_id} onValueChange={(value) => setNewRecord({...newRecord, employee_id: value})}>
                    <SelectTrigger className="rounded-xl" data-testid="training-employee">
                      <SelectValue placeholder="Select employee" />
                    </SelectTrigger>
                    <SelectContent>
                      {employees.map((emp) => (
                        <SelectItem key={emp.id} value={emp.id}>
                          {emp.first_name} {emp.last_name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Training Course *</Label>
                  <Select value={newRecord.training_name} onValueChange={(value) => setNewRecord({...newRecord, training_name: value})}>
                    <SelectTrigger className="rounded-xl" data-testid="training-name">
                      <SelectValue placeholder="Select training" />
                    </SelectTrigger>
                    <SelectContent>
                      {/* Canonical training definitions from backend */}
                      {trainingDefinitions.map((d) => (
                        <SelectItem key={d.id} value={d.name}>{d.name}{d.mandatory_for_compliance ? ' *' : ''}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Expiry Date (optional)</Label>
                  <Input 
                    type="date" 
                    value={newRecord.expiry_date} 
                    onChange={(e) => setNewRecord({...newRecord, expiry_date: e.target.value})}
                    className="rounded-xl"
                    data-testid="training-expiry-date"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Status</Label>
                  <Select value={newRecord.status} onValueChange={(value) => setNewRecord({...newRecord, status: value})}>
                    <SelectTrigger className="rounded-xl" data-testid="training-status">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="not_started">Not Started</SelectItem>
                      <SelectItem value="in_progress">In Progress</SelectItem>
                      <SelectItem value="completed">Completed</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="flex justify-end gap-3 pt-4">
                  <Button type="button" variant="outline" onClick={() => setAddOpen(false)} className="rounded-xl">
                    Cancel
                  </Button>
                  <Button type="submit" disabled={isSubmitting} className="bg-primary hover:bg-primary-hover text-white rounded-xl" data-testid="training-submit">
                    {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Add Record'}
                  </Button>
                </div>
              </form>
            </DialogContent>
          </Dialog>
          )}
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        <Card className="border-[#E4E8EB] shadow-sm">
          <CardContent className="p-4 flex items-center gap-4">
            <div className="w-12 h-12 bg-green-100 rounded-xl flex items-center justify-center">
              <CheckCircle className="h-6 w-6 text-green-600" />
            </div>
            <div>
              <p className="text-2xl font-heading font-bold text-text-primary">{completed}</p>
              <p className="text-sm text-text-muted">Completed</p>
            </div>
          </CardContent>
        </Card>
        <Card className="border-[#E4E8EB] shadow-sm">
          <CardContent className="p-4 flex items-center gap-4">
            <div className="w-12 h-12 bg-green-100 rounded-xl flex items-center justify-center">
              <ShieldCheck className="h-6 w-6 text-green-600" />
            </div>
            <div>
              <p className="text-2xl font-heading font-bold text-text-primary">{verified}</p>
              <p className="text-sm text-text-muted">Verified</p>
            </div>
          </CardContent>
        </Card>
        <Card className={`border-[#E4E8EB] shadow-sm ${expiringSoon > 0 ? 'border-amber-200 bg-amber-50' : ''}`}>
          <CardContent className="p-4 flex items-center gap-4">
            <div className="w-12 h-12 bg-amber-100 rounded-xl flex items-center justify-center">
              <CalendarClock className="h-6 w-6 text-amber-600" />
            </div>
            <div>
              <p className="text-2xl font-heading font-bold text-amber-700">{expiringSoon}</p>
              <p className="text-sm text-amber-600">Needs Renewal</p>
            </div>
          </CardContent>
        </Card>
        <Card className={`border-[#E4E8EB] shadow-sm ${expired > 0 ? 'border-red-200 bg-red-50' : ''}`}>
          <CardContent className="p-4 flex items-center gap-4">
            <div className="w-12 h-12 bg-red-100 rounded-xl flex items-center justify-center">
              <AlertTriangle className="h-6 w-6 text-red-600" />
            </div>
            <div>
              <p className="text-2xl font-heading font-bold text-red-700">{expired}</p>
              <p className="text-sm text-red-600">Expired</p>
            </div>
          </CardContent>
        </Card>
        {/* Awaiting Extraction Review - NEW in Step 8 */}
        <Card 
          className={`border-[#E4E8EB] shadow-sm cursor-pointer transition-all hover:shadow-md ${awaitingExtractionReview > 0 ? 'border-blue-200 bg-blue-50' : ''}`}
          onClick={() => awaitingExtractionReview > 0 && setShowExtractionPanel(!showExtractionPanel)}
          data-testid="awaiting-extraction-card"
        >
          <CardContent className="p-4 flex items-center gap-4">
            <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center">
              <FileSearch className="h-6 w-6 text-blue-600" />
            </div>
            <div>
              <p className="text-2xl font-heading font-bold text-blue-700">{awaitingExtractionReview}</p>
              <p className="text-sm text-blue-600">Awaiting Review</p>
              {awaitingExtractionReview > 0 && (
                <p className="text-xs text-blue-500">Click to review</p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Pending Extraction Review Panel - Shown when card is clicked */}
      {showExtractionPanel && pendingExtractions.length > 0 && (
        <Card className="border-blue-200 bg-blue-50/50 shadow-sm" data-testid="extraction-review-panel">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="font-heading text-lg flex items-center gap-2">
                <FileSearch className="h-5 w-5 text-blue-600" />
                Training Certificates Awaiting Extraction Review
              </CardTitle>
              <Button 
                variant="ghost" 
                size="sm" 
                onClick={() => setShowExtractionPanel(false)}
                className="text-blue-600 hover:text-blue-800"
              >
                Hide
              </Button>
            </div>
            <p className="text-sm text-text-muted">
              AI-extracted data must be reviewed before it updates canonical training records
            </p>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {pendingExtractions.map((ext) => (
                <div 
                  key={ext.id}
                  className="flex items-center justify-between p-3 bg-white rounded-lg border border-blue-200 hover:border-blue-400 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <FileText className="h-5 w-5 text-blue-600" />
                    <div>
                      <p className="font-medium text-text-primary">{ext.document_file_name || 'Training Certificate'}</p>
                      <p className="text-sm text-text-muted">
                        {ext.employee_name || 'Unknown Employee'} • Extracted: {ext.extracted_at ? new Date(ext.extracted_at).toLocaleDateString() : 'N/A'}
                      </p>
                      {ext.extracted_fields?.training_title && (
                        <p className="text-xs text-blue-600 mt-1">
                          Training: {ext.extracted_fields.training_title}
                        </p>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {ext.confidence_score && (
                      <span className={`text-xs px-2 py-1 rounded ${
                        ext.confidence_score >= 0.8 ? 'bg-green-100 text-green-700' :
                        ext.confidence_score >= 0.5 ? 'bg-amber-100 text-amber-700' :
                        'bg-red-100 text-red-700'
                      }`}>
                        {Math.round(ext.confidence_score * 100)}% confidence
                      </span>
                    )}
                    <Button
                      size="sm"
                      variant="outline"
                      className="rounded-xl border-blue-300 text-blue-700 hover:bg-blue-100"
                      onClick={() => handleOpenExtractionReview(ext.document_id)}
                      data-testid={`review-extraction-${ext.document_id}`}
                    >
                      <Eye className="h-4 w-4 mr-1" />
                      Review
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Filters */}
      <Card className="border-[#E4E8EB] shadow-sm">
        <CardContent className="p-4">
          <div className="flex flex-wrap items-center gap-3">
            <Filter className="h-4 w-4 text-text-muted" />
            <span className="text-sm text-text-muted">Filter:</span>
            <div className="flex flex-wrap gap-2">
              <Button 
                variant={filter === 'all' ? 'default' : 'outline'} 
                size="sm" 
                className="rounded-xl"
                onClick={() => setFilter('all')}
                data-testid="filter-all"
              >
                All Records
              </Button>
              <Button 
                variant={filter === 'expired' ? 'default' : 'outline'} 
                size="sm" 
                className={`rounded-xl ${filter === 'expired' ? 'bg-red-600 hover:bg-red-700' : 'text-red-600 border-red-200 hover:bg-red-50'}`}
                onClick={() => setFilter('expired')}
                data-testid="filter-expired"
              >
                Expired ({expired})
              </Button>
              <Button 
                variant={filter === 'expiring_soon' ? 'default' : 'outline'} 
                size="sm" 
                className={`rounded-xl ${filter === 'expiring_soon' ? 'bg-amber-600 hover:bg-amber-700' : 'text-amber-600 border-amber-200 hover:bg-amber-50'}`}
                onClick={() => setFilter('expiring_soon')}
                data-testid="filter-expiring"
              >
                Needs Renewal ({expiringSoon})
              </Button>
              <Button 
                variant={filter === 'valid' ? 'default' : 'outline'} 
                size="sm" 
                className={`rounded-xl ${filter === 'valid' ? 'bg-green-600 hover:bg-green-700' : 'text-green-600 border-green-200 hover:bg-green-50'}`}
                onClick={() => setFilter('valid')}
                data-testid="filter-valid"
              >
                Valid
              </Button>
            </div>
            <Select value={employeeFilter} onValueChange={setEmployeeFilter}>
              <SelectTrigger className="w-full sm:w-72 rounded-xl" data-testid="filter-employee">
                <SelectValue placeholder="Filter by employee" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All employees</SelectItem>
                {employees.map((emp) => (
                  <SelectItem key={emp.id} value={emp.id}>
                    {emp.first_name} {emp.last_name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Training Records Table */}
      <Card className="border-[#E4E8EB] shadow-sm">
        <CardHeader>
          <CardTitle className="font-heading text-lg">Training Records</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {loading ? (
            <div className="flex items-center justify-center h-32">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
          ) : filteredTraining.length === 0 ? (
            <div className="text-center py-12 text-text-muted">
              <GraduationCap className="h-12 w-12 mx-auto mb-3 opacity-50" />
              <p>
                {employeeFilter !== 'all'
                  ? 'No training records for this employee and filter'
                  : (filter === 'all' ? 'No training records yet' : `No ${filter.replace('_', ' ')} training records`)}
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-[#E4E8EB] bg-[#F8FAFA]">
                    <th className="text-left p-4 font-medium text-text-muted text-sm">Employee</th>
                    <th className="text-left p-4 font-medium text-text-muted text-sm">Training</th>
                    <th className="text-left p-4 font-medium text-text-muted text-sm">Status</th>
                    <th className="text-left p-4 font-medium text-text-muted text-sm">Expiry Date</th>
                    <th className="text-left p-4 font-medium text-text-muted text-sm">Renewal Status</th>
                    <th className="text-left p-4 font-medium text-text-muted text-sm">Verified</th>
                    <th className="text-left p-4 font-medium text-text-muted text-sm w-12">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredTraining.map((record) => {
                    // Use backend-computed status - SINGLE SOURCE OF TRUTH
                    const expiryStatus = getBackendExpiryStatus(record);
                    
                    return (
                      <tr key={record.id} className="border-b border-[#E4E8EB] hover:bg-[#F8FAFA]" data-testid={`training-row-${record.id}`}>
                        <td className="p-4 font-medium text-text-primary">
                          {record.employee_name || getEmployeeName(record.employee_id) || record.employee_id || 'Unknown'}
                        </td>
                        <td className="p-4 text-text-primary">
                          <div>
                            {record.training_name}
                            {record.mandatory && (
                              <span className="ml-2 text-xs text-red-600 font-medium">Mandatory</span>
                            )}
                          </div>
                        </td>
                        <td className="p-4">
                          {/* UI INTEGRITY: Status must include verification state and intake workflow states */}
                          <span className={`px-2 py-1 rounded-lg text-xs font-medium ${
                            record.status === 'completed' && record.verified ? 'bg-green-100 text-green-700' :
                            record.status === 'completed' ? 'bg-blue-100 text-blue-700' :
                            record.status === 'awaiting_extraction_review' ? 'bg-purple-100 text-purple-700' :
                            record.status === 'awaiting_evidence' || record.status === 'evidence_requested' ? 'bg-amber-100 text-amber-700' :
                            record.status === 'in_progress' ? 'bg-amber-100 text-amber-700' :
                            'bg-gray-100 text-gray-700'
                          }`}>
                            {record.status === 'completed' && record.verified ? 'Completed & Verified' :
                             record.status === 'completed' ? 'Completed (Awaiting Verification)' :
                             record.status === 'awaiting_extraction_review' ? 'Awaiting Extraction Review' :
                             record.status === 'awaiting_evidence' || record.status === 'evidence_requested' ? 'Evidence Requested' :
                             record.status === 'in_progress' ? 'In Progress' :
                             'Not Started'}
                          </span>
                        </td>
                        <td className="p-4 text-text-muted text-sm">
                          {formatBackendDate(record.expiry_date, { format: 'medium', fallback: '-' })}
                        </td>
                        <td className="p-4">
                          {expiryStatus ? (
                            <div className="flex flex-col">
                              <span className={`px-2 py-1 rounded-lg text-xs font-medium inline-block w-fit ${
                                expiryStatus.color === 'red' ? 'bg-red-100 text-red-700' :
                                expiryStatus.color === 'amber' ? 'bg-amber-100 text-amber-700' :
                                'bg-green-100 text-green-700'
                              }`}>
                                {expiryStatus.label}
                              </span>
                              <span className="text-xs text-text-muted mt-1">{expiryStatus.daysText}</span>
                            </div>
                          ) : (
                            <span className="text-xs text-text-muted">No expiry set</span>
                          )}
                        </td>
                        <td className="p-4">
                          {record.verified ? (
                            <div className="flex items-center gap-1">
                              <ShieldCheck className="h-4 w-4 text-green-600" />
                              <span className="text-xs text-green-600">Yes</span>
                            </div>
                          ) : (
                            <span className="text-xs text-text-muted">No</span>
                          )}
                        </td>
                        <td className="p-4">
                          {!isAuditor() && (
                            <DropdownMenu>
                              <DropdownMenuTrigger asChild>
                                <Button variant="ghost" size="sm" className="h-8 w-8 p-0" data-testid={`training-actions-${record.id}`}>
                                  <MoreVertical className="h-4 w-4" />
                                </Button>
                              </DropdownMenuTrigger>
                              <DropdownMenuContent align="end">
                                <DropdownMenuItem onClick={() => openEditModal(record, 'expiry_date')}>
                                  <Edit className="mr-2 h-4 w-4" />
                                  Edit Expiry Date
                                </DropdownMenuItem>
                                <DropdownMenuItem onClick={() => openEditModal(record, 'completion_date')}>
                                  <Edit className="mr-2 h-4 w-4" />
                                  Edit Completion Date
                                </DropdownMenuItem>
                                <DropdownMenuItem onClick={() => openEditModal(record, 'status')}>
                                  <Edit className="mr-2 h-4 w-4" />
                                  Edit Status
                                </DropdownMenuItem>
                                <DropdownMenuItem onClick={() => handleViewHistory(record)}>
                                  <History className="mr-2 h-4 w-4" />
                                  View History
                                </DropdownMenuItem>
                              </DropdownMenuContent>
                            </DropdownMenu>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Edit/Correction Modal */}
      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="font-heading">Edit Training Record</DialogTitle>
            <DialogDescription>
              Make a correction to this training record. All changes require a reason and are logged for audit purposes.
            </DialogDescription>
          </DialogHeader>
          {editingRecord && (
            <div className="space-y-4 mt-4">
              <div className="p-3 bg-[#F8FAFA] rounded-lg border border-[#E4E8EB]">
                <p className="font-medium text-text-primary">{editingRecord.training_name}</p>
                <p className="text-sm text-text-muted">{getEmployeeName(editingRecord.employee_id)}</p>
              </div>
              
              <div className="space-y-2">
                <Label>Field to Edit</Label>
                <Select value={correction.field} onValueChange={(value) => setCorrection({...correction, field: value, new_value: editingRecord[value] || ''})}>
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
                  value={editingRecord[correction.field] || '(not set)'} 
                  disabled 
                  className="rounded-xl bg-gray-100"
                />
              </div>
              
              <div className="space-y-2">
                <Label>New Value *</Label>
                {correction.field === 'status' ? (
                  <Select value={correction.new_value} onValueChange={(value) => setCorrection({...correction, new_value: value})}>
                    <SelectTrigger className="rounded-xl" data-testid="correction-new-value">
                      <SelectValue placeholder="Select new status" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="not_started">Not Started</SelectItem>
                      <SelectItem value="in_progress">In Progress</SelectItem>
                      <SelectItem value="completed">Completed</SelectItem>
                      <SelectItem value="expired">Expired</SelectItem>
                      <SelectItem value="renewal_due">Renewal Due</SelectItem>
                    </SelectContent>
                  </Select>
                ) : (
                  <Input 
                    type="date" 
                    value={correction.new_value?.split('T')[0] || ''} 
                    onChange={(e) => setCorrection({...correction, new_value: e.target.value})}
                    className="rounded-xl"
                    data-testid="correction-new-value"
                  />
                )}
              </div>
              
              <div className="space-y-2">
                <Label>Reason for Change *</Label>
                <Textarea 
                  placeholder="Explain why this correction is being made (required for audit trail)"
                  value={correction.reason}
                  onChange={(e) => setCorrection({...correction, reason: e.target.value})}
                  className="rounded-xl min-h-[80px]"
                  data-testid="correction-reason"
                />
                <p className="text-xs text-text-muted">This will be permanently recorded in the audit log</p>
              </div>
              
              {editingRecord.verified && (
                <div className="p-3 bg-amber-50 rounded-lg border border-amber-200">
                  <p className="text-sm text-amber-700">
                    <AlertTriangle className="h-4 w-4 inline mr-2" />
                    This record has been verified. Corrections will be flagged in the audit log.
                  </p>
                </div>
              )}
            </div>
          )}
          <DialogFooter className="mt-6">
            <Button variant="outline" onClick={() => setEditOpen(false)} className="rounded-xl">
              Cancel
            </Button>
            <Button 
              onClick={handleCorrection} 
              disabled={isSubmitting || !correction.reason || !correction.new_value}
              className="bg-primary hover:bg-primary-hover text-white rounded-xl"
              data-testid="correction-submit"
            >
              {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Save Correction'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* History Modal */}
      <Dialog open={historyOpen} onOpenChange={setHistoryOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle className="font-heading">Training Record History</DialogTitle>
          </DialogHeader>
          {historyRecord && (
            <div className="space-y-4 mt-4">
              <div className="p-3 bg-[#F8FAFA] rounded-lg border border-[#E4E8EB]">
                <p className="font-medium text-text-primary">{historyRecord.training_name}</p>
                <p className="text-sm text-text-muted">{getEmployeeName(historyRecord.employee_id)}</p>
              </div>
              
              {historyLoading ? (
                <div className="flex items-center justify-center h-32">
                  <Loader2 className="h-6 w-6 animate-spin text-primary" />
                </div>
              ) : historyData.length === 0 ? (
                <div className="text-center py-8 text-text-muted">
                  <History className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p>No correction history</p>
                </div>
              ) : (
                <div className="space-y-3 max-h-80 overflow-y-auto">
                  {historyData.map((entry, idx) => (
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
                          {entry.was_verified_before_correction && (
                            <span className="inline-block mt-1 px-2 py-0.5 bg-amber-100 text-amber-700 text-xs rounded">
                              Corrected after verification
                            </span>
                          )}
                        </div>
                        <div className="text-right text-xs text-text-muted">
                          <p>{entry.changed_by_name || 'System'}</p>
                          <p>{entry.created_at ? formatBackendDateTime(entry.created_at) : ''}</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Extraction Review Modal - Step 8 */}
      {extractionReviewOpen && reviewingDocumentId && (
        <DocumentExtractionReview
          documentId={reviewingDocumentId}
          onClose={() => setExtractionReviewOpen(false)}
          onApproved={handleExtractionReviewComplete}
          documentName="Training Certificate"
        />
      )}
    </div>
  );
}

