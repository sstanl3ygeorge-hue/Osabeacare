import { useCallback, useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { useAuth } from '../../context/AuthContext';
import API_BASE from '../../utils/apiBase';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Textarea } from '../../components/ui/textarea';
import { Badge } from '../../components/ui/badge';
import { 
  Loader2, Upload, RefreshCw, Save, Rocket, FileText, Plus, Eye, Edit2, 
  Archive, RotateCcw, Search, Filter, AlertCircle, CheckCircle2, Clock 
} from 'lucide-react';

const API = API_BASE;
const MAX_FILE_SIZE = 25 * 1024 * 1024; // 25MB

const WORKFLOW_AREAS = [
  { value: 'compliance_policy', label: 'Compliance Policy' },
  { value: 'staff_onboarding', label: 'Staff Onboarding' },
  { value: 'service_user_record', label: 'Service User Record' },
  { value: 'care_plan', label: 'Care Plan' },
  { value: 'risk_assessment', label: 'Risk Assessment' },
  { value: 'body_map', label: 'Body Map' },
  { value: 'incident_report', label: 'Incident Report' },
  { value: 'medication', label: 'Medication' },
  { value: 'audit', label: 'Audit' },
  { value: 'complaint', label: 'Complaint' },
  { value: 'insurance_certificate', label: 'Insurance Certificate' }
];

const CATEGORIES = [
  'Policy', 'Procedure', 'Form', 'Checklist', 'Assessment', 
  'Agreement', 'Certificate', 'Record', 'Incident', 'Report'
];

const SYSTEM_VARIABLES = [
  'org.name',
  'org.address',
  'org.registration_number',
  'org.phone',
  'employee.full_name',
  'employee.role',
  'employee.start_date',
  'service_user.full_name',
  'service_user.dob',
  'incident.date',
  'incident.location',
  'care_plan.review_date',
  'document.generated_date',
  'manager.full_name'
];

// Auto-generate doc_code based on category and workflow
function generateDocCode(category, workflowArea) {
  const categoryAbbr = {
    'Policy': 'POL', 'Procedure': 'PROC', 'Form': 'FORM', 'Checklist': 'CHK',
    'Assessment': 'ASS', 'Agreement': 'AGR', 'Certificate': 'CERT', 'Record': 'REC',
    'Incident': 'INC', 'Report': 'RPT'
  };
  
  const workflowAbbr = {
    'compliance_policy': 'CP', 'staff_onboarding': 'SO', 'service_user_record': 'SU',
    'care_plan': 'CP', 'risk_assessment': 'RA', 'body_map': 'BM',
    'incident_report': 'INC', 'medication': 'MED', 'audit': 'AUD',
    'complaint': 'CMP', 'insurance_certificate': 'INS'
  };
  
  const catAbbr = categoryAbbr[category] || 'DOC';
  const wfAbbr = workflowAbbr[workflowArea] || 'GEN';
  const num = Math.floor(Math.random() * 1000).toString().padStart(3, '0');
  return `${catAbbr}-${wfAbbr}-${num}`;
}

function safeJsonParse(value, fallback) {
  try {
    return JSON.parse(value);
  } catch {
    return fallback;
  }
}

function StatusBadge({ status }) {
  const variants = {
    'draft': 'bg-yellow-100 text-yellow-800 border-yellow-300',
    'published': 'bg-green-100 text-green-800 border-green-300',
    'archived': 'bg-gray-100 text-gray-800 border-gray-300',
  };
  return <Badge className={`${variants[status] || variants.draft} border`}>{status}</Badge>;
}

function RenewalBadge({ renewalDueDate }) {
  if (!renewalDueDate) return null;
  const daysUntilDue = Math.floor((new Date(renewalDueDate) - new Date()) / (1000 * 60 * 60 * 24));
  const isOverdue = daysUntilDue < 0;
  if (isOverdue) {
    return <Badge className="bg-red-100 text-red-800 border-red-300 border"><AlertCircle className="h-3 w-3 mr-1" />Renewal Overdue</Badge>;
  }
  if (daysUntilDue <= 30) {
    return <Badge className="bg-orange-100 text-orange-800 border-orange-300 border"><Clock className="h-3 w-3 mr-1" />Due in {daysUntilDue}d</Badge>;
  }
  return null;
}

export default function DocumentTemplateLibraryPage() {
  const { token, isAdmin } = useAuth();

  const [templates, setTemplates] = useState([]);
  const [filteredTemplates, setFilteredTemplates] = useState([]);
  const [loadingTemplates, setLoadingTemplates] = useState(true);
  const [selectedTemplateId, setSelectedTemplateId] = useState('');
  const [templateDetail, setTemplateDetail] = useState(null);
  const [selectedVersionId, setSelectedVersionId] = useState('');

  // Upload form
  const [file, setFile] = useState(null);
  const [fileError, setFileError] = useState('');
  const [uploadProgress, setUploadProgress] = useState(0);
  const [title, setTitle] = useState('');
  const [category, setCategory] = useState('Policy');
  const [documentType, setDocumentType] = useState('policy');
  const [workflowArea, setWorkflowArea] = useState('compliance_policy');
  const [sourceProvider, setSourceProvider] = useState('');
  const [reviewPeriodMonths, setReviewPeriodMonths] = useState('12');
  const [effectiveDate, setEffectiveDate] = useState('');
  const [generatedDocCode, setGeneratedDocCode] = useState('');

  // States
  const [importing, setImporting] = useState(false);
  const [savingMappings, setSavingMappings] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [archiving, setArchiving] = useState(false);

  // Placeholder review modal
  const [showPlaceholderReview, setShowPlaceholderReview] = useState(false);
  const [reviewingPlaceholders, setReviewingPlaceholders] = useState({});

  // Filtering
  const [searchQuery, setSearchQuery] = useState('');
  const [filterCategory, setFilterCategory] = useState('');
  const [filterWorkflow, setFilterWorkflow] = useState('');
  const [filterStatus, setFilterStatus] = useState('');
  const [filterProvider, setFilterProvider] = useState('');

  // Placeholder mapping
  const [manualPlaceholder, setManualPlaceholder] = useState('');
  const [mappingDraft, setMappingDraft] = useState({});
  const [contextJson, setContextJson] = useState(JSON.stringify({
    org: { name: 'OsabeaCare', registration_number: 'ORG-001' },
    manager: { full_name: 'Registered Manager' },
    employee: { full_name: 'Jane Doe', role: 'Support Worker', start_date: '2026-01-01' }
  }, null, 2));
  const [lastGenerated, setLastGenerated] = useState(null);

  const authHeaders = useMemo(() => ({ Authorization: `Bearer ${token}` }), [token]);

  const selectedVersion = useMemo(() => {
    if (!templateDetail?.versions?.length) return null;
    return templateDetail.versions.find(v => v.id === selectedVersionId) || templateDetail.versions[0];
  }, [templateDetail, selectedVersionId]);

  // Count unmapped placeholders
  const unmappedCount = useMemo(() => {
    return Object.values(mappingDraft).filter(m => !m.system_variable).length;
  }, [mappingDraft]);

  // Fetch templates
  const fetchTemplates = useCallback(async () => {
    setLoadingTemplates(true);
    try {
      const response = await axios.get(`${API}/document-templates`, { headers: authHeaders });
      const list = Array.isArray(response.data) ? response.data : [];
      setTemplates(list);
      if (!selectedTemplateId && list.length > 0) {
        setSelectedTemplateId(list[0].id);
      }
    } catch (error) {
      console.error('Failed to load templates', error);
      toast.error(error.response?.data?.detail || 'Failed to load template library');
    } finally {
      setLoadingTemplates(false);
    }
  }, [authHeaders, selectedTemplateId]);

  // Filter templates
  useEffect(() => {
    let filtered = templates;
    
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      filtered = filtered.filter(t => 
        t.title?.toLowerCase().includes(q) || 
        t.doc_code?.toLowerCase().includes(q) ||
        t.source_provider?.toLowerCase().includes(q)
      );
    }
    
    if (filterCategory) {
      filtered = filtered.filter(t => t.category === filterCategory);
    }
    if (filterWorkflow) {
      filtered = filtered.filter(t => t.workflow_area === filterWorkflow);
    }
    if (filterStatus) {
      filtered = filtered.filter(t => t.status === filterStatus);
    }
    if (filterProvider) {
      filtered = filtered.filter(t => t.source_provider === filterProvider);
    }
    
    setFilteredTemplates(filtered);
  }, [templates, searchQuery, filterCategory, filterWorkflow, filterStatus, filterProvider]);

  // Fetch template detail
  const fetchTemplateDetail = useCallback(async (templateId) => {
    try {
      const response = await axios.get(`${API}/document-templates/${templateId}`, { headers: authHeaders });
      setTemplateDetail(response.data);
      const firstDraft = (response.data?.versions || []).find(v => v.status === 'draft');
      const current = response.data?.template?.current_version_id;
      setSelectedVersionId(firstDraft?.id || current || response.data?.versions?.[0]?.id || '');
    } catch (error) {
      console.error('Failed to load template detail', error);
      toast.error(error.response?.data?.detail || 'Failed to load template detail');
    }
  }, [authHeaders]);

  useEffect(() => {
    fetchTemplates();
  }, [fetchTemplates]);

  useEffect(() => {
    if (!selectedTemplateId) return;
    fetchTemplateDetail(selectedTemplateId);
  }, [fetchTemplateDetail, selectedTemplateId]);

  useEffect(() => {
    if (!selectedVersionId || !selectedVersion) {
      setMappingDraft({});
      return;
    }
    setMappingDraft(selectedVersion.placeholder_map || {});
  }, [selectedVersion, selectedVersionId]);

  // Handle file selection with validation
  const handleFileChange = (e) => {
    const selectedFile = e.target.files?.[0];
    if (!selectedFile) {
      setFile(null);
      setFileError('');
      return;
    }

    // Validate file type
    const validTypes = ['application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/pdf'];
    if (!validTypes.includes(selectedFile.type)) {
      setFileError('Only DOCX and PDF files are supported');
      setFile(null);
      return;
    }

    // Validate file size
    if (selectedFile.size > MAX_FILE_SIZE) {
      setFileError(`File size exceeds ${MAX_FILE_SIZE / 1024 / 1024}MB limit`);
      setFile(null);
      return;
    }

    setFile(selectedFile);
    setFileError('');
    setUploadProgress(0);
  };

  // Handle import with placeholder review
  const handleImport = async () => {
    if (!isAdmin()) {
      toast.error('Admin access required');
      return;
    }
    if (!file) {
      toast.error('Select a DOCX or PDF file first');
      return;
    }
    if (fileError) {
      toast.error(fileError);
      return;
    }

    const formData = new FormData();
    formData.append('file', file);
    if (title.trim()) formData.append('title', title.trim());
    formData.append('category', category);
    formData.append('document_type', documentType);
    formData.append('workflow_area', workflowArea);
    formData.append('source_provider', sourceProvider);
    formData.append('review_period_months', reviewPeriodMonths || '12');
    if (effectiveDate) formData.append('effective_date', effectiveDate);

    setImporting(true);
    try {
      const response = await axios.post(`${API}/document-templates/import`, formData, {
        headers: {
          ...authHeaders,
          'Content-Type': 'multipart/form-data'
        },
        onUploadProgress: (progressEvent) => {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          setUploadProgress(progress);
        }
      });

      const importedTemplate = response.data?.template;
      const importedVersion = response.data?.version;

      // Show placeholder review modal
      if (importedVersion?.detected_placeholders) {
        setReviewingPlaceholders(importedVersion.detected_placeholders.reduce((acc, p) => {
          acc[p.placeholder_text] = {
            ...p,
            system_variable: '',
            status: 'detected'
          };
          return acc;
        }, {}));
        setShowPlaceholderReview(true);
      }

      toast.success(`Imported ${importedTemplate?.title || 'template'} successfully`);
      setFile(null);
      setTitle('');
      setUploadProgress(0);
      await fetchTemplates();
      if (importedTemplate?.id) {
        setSelectedTemplateId(importedTemplate.id);
      }
    } catch (error) {
      console.error('Import failed', error);
      toast.error(error.response?.data?.detail || 'Template import failed');
    } finally {
      setImporting(false);
    }
  };

  const handleReviewPlaceholderMapping = (placeholder, key, value) => {
    setReviewingPlaceholders(prev => ({
      ...prev,
      [placeholder]: {
        ...(prev[placeholder] || {}),
        [key]: value
      }
    }));
  };

  const handleSaveReviewedMapping = async () => {
    // Find the first draft version and update mapping
    if (!selectedTemplateId) return;
    
    const template = templates.find(t => t.id === selectedTemplateId);
    if (!template) return;

    // This mapping will be applied in the next step when user works with the template
    // For now just close the modal
    setShowPlaceholderReview(false);
    toast.success('Placeholder review complete. You can now map them in detail.');
  };

  const handleMapChange = (placeholderText, key, value) => {
    setMappingDraft(prev => ({
      ...prev,
      [placeholderText]: {
        ...(prev[placeholderText] || {}),
        [key]: value
      }
    }));
  };

  const handleAddManualPlaceholder = () => {
    const key = manualPlaceholder.trim();
    if (!key) return;
    setMappingDraft(prev => ({
      ...prev,
      [key]: {
        ...(prev[key] || {}),
        status: 'manual',
        system_variable: prev[key]?.system_variable || ''
      }
    }));
    setManualPlaceholder('');
  };

  const handleSaveMappings = async () => {
    if (!selectedVersionId) {
      toast.error('Select a template version first');
      return;
    }

    const mappings = Object.entries(mappingDraft).map(([placeholder_text, meta]) => ({
      placeholder_text,
      system_variable: meta?.system_variable || null,
      status: meta?.status || 'accepted',
      notes: meta?.notes || null
    }));

    setSavingMappings(true);
    try {
      await axios.put(
        `${API}/document-template-versions/${selectedVersionId}/placeholder-map`,
        { mappings, manually_added_placeholders: [] },
        { headers: authHeaders }
      );
      toast.success('Placeholder mapping saved');
      await fetchTemplateDetail(selectedTemplateId);
    } catch (error) {
      console.error('Save mapping failed', error);
      toast.error(error.response?.data?.detail || 'Failed to save mappings');
    } finally {
      setSavingMappings(false);
    }
  };

  const handlePublish = async () => {
    if (unmappedCount > 0) {
      const confirmed = window.confirm(
        `${unmappedCount} placeholders remain unmapped. Publish anyway?`
      );
      if (!confirmed) return;
    }

    if (!selectedTemplateId || !selectedVersionId) {
      toast.error('Select a template and version to publish');
      return;
    }

    setPublishing(true);
    try {
      await axios.post(
        `${API}/document-templates/${selectedTemplateId}/publish`,
        {
          template_version_id: selectedVersionId,
          effective_date: effectiveDate || null
        },
        { headers: authHeaders }
      );
      toast.success('Template version published');
      await fetchTemplates();
      await fetchTemplateDetail(selectedTemplateId);
    } catch (error) {
      console.error('Publish failed', error);
      toast.error(error.response?.data?.detail || 'Failed to publish template');
    } finally {
      setPublishing(false);
    }
  };

  const handleGenerateSample = async () => {
    if (!selectedTemplateId || !selectedVersionId) {
      toast.error('Select a template and version');
      return;
    }

    const context = safeJsonParse(contextJson, null);
    if (!context) {
      toast.error('Context JSON is invalid');
      return;
    }

    setGenerating(true);
    try {
      const response = await axios.post(
        `${API}/generated-documents`,
        {
          template_id: selectedTemplateId,
          template_version_id: selectedVersionId,
          workflow_area: templateDetail?.template?.workflow_area || 'compliance_policy',
          related_entity_type: 'template_preview',
          related_entity_id: selectedTemplateId,
          context
        },
        { headers: authHeaders }
      );

      setLastGenerated(response.data);
      toast.success('Sample branded PDF generated');
    } catch (error) {
      console.error('Generate failed', error);
      toast.error(error.response?.data?.detail || 'Failed to generate sample PDF');
    } finally {
      setGenerating(false);
    }
  };

  const handleArchive = async (templateId) => {
    if (!window.confirm('Archive this template? It will no longer be available for use.')) return;
    
    setArchiving(true);
    try {
      // Backend endpoint for archive (to be implemented)
      await axios.post(
        `${API}/document-templates/${templateId}/archive`,
        {},
        { headers: authHeaders }
      );
      toast.success('Template archived');
      await fetchTemplates();
    } catch (error) {
      console.error('Archive failed', error);
      toast.error(error.response?.data?.detail || 'Failed to archive template');
    } finally {
      setArchiving(false);
    }
  };

  return (
    <div className="w-full space-y-6 p-4 md:p-0" data-testid="document-template-library-page">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
        <div className="flex-1">
          <h1 className="font-heading text-2xl md:text-3xl font-bold text-text-primary">Template Library</h1>
          <p className="text-sm text-text-muted mt-1">
            Import provider templates, map placeholders, publish versions, and generate branded PDFs.
          </p>
        </div>
        <Button variant="outline" onClick={fetchTemplates} disabled={loadingTemplates} className="w-full md:w-auto">
          {loadingTemplates ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <RefreshCw className="h-4 w-4 mr-2" />}
          Refresh
        </Button>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Import Form */}
        <Card className="lg:col-span-1 border-[#E4E8EB] h-fit sticky top-4">
          <CardHeader>
            <CardTitle className="text-base">Import New Template</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="space-y-1">
              <Label className="text-xs font-semibold">Template File</Label>
              <div className="relative">
                <Input 
                  type="file" 
                  accept=".docx,.pdf" 
                  onChange={handleFileChange}
                  className="cursor-pointer"
                />
                {file && <CheckCircle2 className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-green-600" />}
              </div>
              {fileError && <p className="text-xs text-red-600">{fileError}</p>}
              {file && <p className="text-xs text-text-muted">{file.name}</p>}
              {uploadProgress > 0 && uploadProgress < 100 && (
                <div className="w-full bg-gray-200 rounded h-2">
                  <div className="bg-primary h-2 rounded transition-all" style={{ width: `${uploadProgress}%` }} />
                </div>
              )}
            </div>

            <div className="space-y-1">
              <Label className="text-xs font-semibold">Title (Optional)</Label>
              <Input 
                value={title} 
                onChange={(e) => setTitle(e.target.value)} 
                placeholder="Use file name if empty"
                className="text-xs"
              />
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div className="space-y-1">
                <Label className="text-xs font-semibold">Category</Label>
                <Select value={category} onValueChange={(v) => {
                  setCategory(v);
                  setGeneratedDocCode(generateDocCode(v, workflowArea));
                }}>
                  <SelectTrigger className="text-xs">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {CATEGORIES.map((cat) => (
                      <SelectItem key={cat} value={cat}>{cat}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1">
                <Label className="text-xs font-semibold">Workflow Area</Label>
                <Select value={workflowArea} onValueChange={(v) => {
                  setWorkflowArea(v);
                  setGeneratedDocCode(generateDocCode(category, v));
                }}>
                  <SelectTrigger className="text-xs">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {WORKFLOW_AREAS.map((item) => (
                      <SelectItem key={item.value} value={item.value}>{item.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-1">
              <Label className="text-xs font-semibold">Doc Code (Auto)</Label>
              <Input 
                value={generatedDocCode || generateDocCode(category, workflowArea)} 
                disabled
                className="text-xs bg-muted"
              />
            </div>

            <div className="space-y-1">
              <Label className="text-xs font-semibold">Source Provider</Label>
              <Input 
                value={sourceProvider} 
                onChange={(e) => setSourceProvider(e.target.value)}
                placeholder="e.g. CQC Expert, Internal"
                className="text-xs"
              />
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div className="space-y-1">
                <Label className="text-xs font-semibold">Review Period (Mo)</Label>
                <Input 
                  type="number" 
                  min="1" 
                  max="36" 
                  value={reviewPeriodMonths} 
                  onChange={(e) => setReviewPeriodMonths(e.target.value)}
                  className="text-xs"
                />
              </div>
              <div className="space-y-1">
                <Label className="text-xs font-semibold">Effective Date</Label>
                <Input 
                  type="date" 
                  value={effectiveDate} 
                  onChange={(e) => setEffectiveDate(e.target.value)}
                  className="text-xs"
                />
              </div>
            </div>

            <Button 
              onClick={handleImport} 
              disabled={importing || !isAdmin() || !file} 
              className="w-full text-xs"
            >
              {importing ? <Loader2 className="h-3 w-3 mr-2 animate-spin" /> : <Upload className="h-3 w-3 mr-2" />}
              Import
            </Button>
          </CardContent>
        </Card>

        {/* Templates Table */}
        <Card className="lg:col-span-3 border-[#E4E8EB]">
          <CardHeader>
            <CardTitle className="text-base mb-4">Templates ({filteredTemplates.length})</CardTitle>
            
            {/* Search and Filter */}
            <div className="space-y-3">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-muted" />
                <Input 
                  placeholder="Search by title, code, or provider..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10 text-xs"
                />
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                <Select value={filterCategory} onValueChange={setFilterCategory}>
                  <SelectTrigger className="text-xs">
                    <SelectValue placeholder="Category" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">All Categories</SelectItem>
                    {CATEGORIES.map((cat) => (
                      <SelectItem key={cat} value={cat}>{cat}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                <Select value={filterWorkflow} onValueChange={setFilterWorkflow}>
                  <SelectTrigger className="text-xs">
                    <SelectValue placeholder="Workflow" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">All Workflows</SelectItem>
                    {WORKFLOW_AREAS.map((item) => (
                      <SelectItem key={item.value} value={item.value}>{item.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                <Select value={filterStatus} onValueChange={setFilterStatus}>
                  <SelectTrigger className="text-xs">
                    <SelectValue placeholder="Status" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">All Statuses</SelectItem>
                    <SelectItem value="draft">Draft</SelectItem>
                    <SelectItem value="published">Published</SelectItem>
                    <SelectItem value="archived">Archived</SelectItem>
                  </SelectContent>
                </Select>

                {[...new Set(templates.map(t => t.source_provider))].filter(Boolean).length > 0 && (
                  <Select value={filterProvider} onValueChange={setFilterProvider}>
                    <SelectTrigger className="text-xs">
                      <SelectValue placeholder="Provider" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="">All Providers</SelectItem>
                      {[...new Set(templates.map(t => t.source_provider))].map((prov) => (
                        <SelectItem key={prov} value={prov}>{prov}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              </div>
            </div>
          </CardHeader>

          <CardContent>
            {loadingTemplates ? (
              <div className="h-40 flex items-center justify-center">
                <Loader2 className="h-6 w-6 animate-spin text-primary" />
              </div>
            ) : filteredTemplates.length === 0 ? (
              <p className="text-sm text-text-muted text-center py-8">
                {templates.length === 0 ? 'No templates imported yet.' : 'No templates match your filters.'}
              </p>
            ) : (
              <div className="overflow-x-auto -mx-6 md:mx-0">
                <table className="w-full text-xs">
                  <thead className="bg-muted/40 border-b sticky top-0">
                    <tr>
                      <th className="text-left p-3">Title</th>
                      <th className="text-left p-3">Code</th>
                      <th className="text-left p-3 hidden md:table-cell">Category</th>
                      <th className="text-left p-3 hidden lg:table-cell">Workflow Area</th>
                      <th className="text-left p-3">Version</th>
                      <th className="text-left p-3">Status</th>
                      <th className="text-left p-3 hidden xl:table-cell">Next Review</th>
                      <th className="text-left p-3">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredTemplates.map((template) => (
                      <tr key={template.id} className={`border-b hover:bg-muted/20 transition ${selectedTemplateId === template.id ? 'bg-primary/5' : ''}`}>
                        <td className="p-3">
                          <button
                            onClick={() => setSelectedTemplateId(template.id)}
                            className="text-primary hover:underline font-medium"
                          >
                            {template.title}
                          </button>
                        </td>
                        <td className="p-3 font-mono text-xs">{template.doc_code}</td>
                        <td className="p-3 hidden md:table-cell text-xs">{template.category}</td>
                        <td className="p-3 hidden lg:table-cell text-xs">
                          {WORKFLOW_AREAS.find(wa => wa.value === template.workflow_area)?.label || template.workflow_area}
                        </td>
                        <td className="p-3 text-xs">v{template.current_version || '1'}</td>
                        <td className="p-3">
                          <StatusBadge status={template.status} />
                        </td>
                        <td className="p-3 hidden xl:table-cell">
                          <RenewalBadge renewalDueDate={template.renewal_due_date} />
                        </td>
                        <td className="p-3">
                          <div className="flex gap-1 flex-wrap">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => setSelectedTemplateId(template.id)}
                              title="View details"
                              className="h-7 w-7 p-0"
                            >
                              <Eye className="h-3 w-3" />
                            </Button>
                            {template.status === 'draft' && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => setSelectedTemplateId(template.id)}
                                title="Map placeholders"
                                className="h-7 w-7 p-0"
                              >
                                <Edit2 className="h-3 w-3" />
                              </Button>
                            )}
                            {template.status !== 'archived' && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleArchive(template.id)}
                                disabled={archiving}
                                title="Archive"
                                className="h-7 w-7 p-0"
                              >
                                <Archive className="h-3 w-3" />
                              </Button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Detail View */}
      {templateDetail && selectedVersion && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Mapping Panel */}
          <Card className="lg:col-span-2 border-[#E4E8EB]">
            <CardHeader>
              <CardTitle className="text-base flex items-center justify-between flex-wrap gap-2">
                <span>Placeholder Mapping</span>
                <div className="flex items-center gap-2 flex-wrap justify-end">
                  <Select value={selectedVersionId} onValueChange={setSelectedVersionId}>
                    <SelectTrigger className="w-40 text-xs">
                      <SelectValue placeholder="Version" />
                    </SelectTrigger>
                    <SelectContent>
                      {(templateDetail.versions || []).map((v) => (
                        <SelectItem key={v.id} value={v.id}>v{v.version} ({v.status})</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <StatusBadge status={selectedVersion.status} />
                </div>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {unmappedCount > 0 && selectedVersion.status === 'draft' && (
                <div className="bg-orange-50 border border-orange-200 rounded-lg p-3 flex gap-2">
                  <AlertCircle className="h-4 w-4 text-orange-600 mt-0.5 flex-shrink-0" />
                  <div className="text-sm text-orange-800">
                    <p className="font-semibold">{unmappedCount} unmapped placeholders</p>
                    <p className="text-xs mt-1">Map all placeholders before publishing to ensure complete template generation.</p>
                  </div>
                </div>
              )}

              <div className="flex gap-2">
                <Input
                  value={manualPlaceholder}
                  onChange={(e) => setManualPlaceholder(e.target.value)}
                  placeholder="Add placeholder, e.g. [Policy Owner]"
                  className="text-xs"
                />
                <Button 
                  variant="outline" 
                  onClick={handleAddManualPlaceholder}
                  className="text-xs"
                >
                  <Plus className="h-3 w-3" />
                </Button>
              </div>

              <div className="border rounded-lg overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full text-xs bg-white">
                    <thead className="bg-muted/40 border-b sticky top-0">
                      <tr>
                        <th className="text-left p-2">Placeholder</th>
                        <th className="text-left p-2">System Variable</th>
                        <th className="text-left p-2">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(mappingDraft).length === 0 && (
                        <tr>
                          <td className="p-3 text-text-muted" colSpan={3}>No placeholders detected.</td>
                        </tr>
                      )}
                      {Object.entries(mappingDraft).map(([placeholderText, meta]) => (
                        <tr key={placeholderText} className="border-t hover:bg-muted/20">
                          <td className="p-2 align-top max-w-xs">
                            <div className="font-mono break-words">{placeholderText}</div>
                            {meta?.confidence && (
                              <p className="text-xs text-text-muted mt-0.5">Confidence: {(meta.confidence * 100).toFixed(0)}%</p>
                            )}
                          </td>
                          <td className="p-2 align-top">
                            <Select
                              value={meta?.system_variable || '__none__'}
                              onValueChange={(value) => handleMapChange(placeholderText, 'system_variable', value === '__none__' ? '' : value)}
                            >
                              <SelectTrigger className="text-xs w-40">
                                <SelectValue placeholder="Select" />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="__none__">Unmapped</SelectItem>
                                {SYSTEM_VARIABLES.map((item) => (
                                  <SelectItem key={item} value={item}>{item}</SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          </td>
                          <td className="p-2 align-top">
                            <Select value={meta?.status || 'accepted'} onValueChange={(value) => handleMapChange(placeholderText, 'status', value)}>
                              <SelectTrigger className="text-xs w-28">
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="accepted">Accepted</SelectItem>
                                <SelectItem value="ignored">Ignored</SelectItem>
                                <SelectItem value="manual">Manual</SelectItem>
                                <SelectItem value="detected">Detected</SelectItem>
                              </SelectContent>
                            </Select>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="flex flex-wrap gap-2 justify-end pt-2">
                <Button 
                  variant="outline"
                  onClick={handleSaveMappings} 
                  disabled={savingMappings || selectedVersion.status !== 'draft'}
                  className="text-xs"
                >
                  {savingMappings ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : <Save className="h-3 w-3 mr-1" />}
                  Save Mapping
                </Button>
                <Button 
                  onClick={handlePublish} 
                  disabled={publishing || selectedVersion.status !== 'draft'}
                  className="text-xs"
                >
                  {publishing ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : <Rocket className="h-3 w-3 mr-1" />}
                  Publish Version
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* PDF Generation Panel */}
          <Card className="lg:col-span-1 border-[#E4E8EB] h-fit">
            <CardHeader>
              <CardTitle className="text-base">Generate Sample PDF</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="space-y-1">
                <Label className="text-xs font-semibold">Context JSON</Label>
                <Textarea
                  className="min-h-[200px] font-mono text-xs resize-none"
                  value={contextJson}
                  onChange={(e) => setContextJson(e.target.value)}
                />
              </div>

              <Button 
                onClick={handleGenerateSample} 
                disabled={generating}
                className="w-full text-xs"
              >
                {generating ? <Loader2 className="h-3 w-3 mr-2 animate-spin" /> : <FileText className="h-3 w-3 mr-2" />}
                Generate
              </Button>

              {lastGenerated?.id && (
                <a
                  href={`${API}/generated-documents/${lastGenerated.id}/pdf`}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center text-xs text-primary underline hover:no-underline w-full text-center justify-center py-2"
                >
                  📄 Open PDF
                </a>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* Placeholder Review Modal */}
      {showPlaceholderReview && Object.keys(reviewingPlaceholders).length > 0 && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <Card className="w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <CardHeader>
              <CardTitle>Review Detected Placeholders</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm text-text-muted">
                The system detected {Object.keys(reviewingPlaceholders).length} placeholders. Review and map them now:
              </p>

              <div className="space-y-3 max-h-[400px] overflow-y-auto">
                {Object.entries(reviewingPlaceholders).map(([placeholder, meta]) => (
                  <div key={placeholder} className="border rounded-lg p-3 space-y-2">
                    <p className="font-mono text-sm font-semibold">{placeholder}</p>
                    <div className="grid grid-cols-2 gap-2">
                      <Select
                        value={meta?.system_variable || '__none__'}
                        onValueChange={(value) => handleReviewPlaceholderMapping(
                          placeholder,
                          'system_variable',
                          value === '__none__' ? '' : value
                        )}
                      >
                        <SelectTrigger className="text-xs">
                          <SelectValue placeholder="Select variable" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="__none__">Unmapped</SelectItem>
                          {SYSTEM_VARIABLES.map((item) => (
                            <SelectItem key={item} value={item}>{item}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <Select
                        value={meta?.status || 'accepted'}
                        onValueChange={(value) => handleReviewPlaceholderMapping(placeholder, 'status', value)}
                      >
                        <SelectTrigger className="text-xs">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="accepted">Accepted</SelectItem>
                          <SelectItem value="ignored">Ignored</SelectItem>
                          <SelectItem value="manual">Manual</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                ))}
              </div>

              <div className="flex gap-2 justify-end pt-4">
                <Button
                  variant="outline"
                  onClick={() => setShowPlaceholderReview(false)}
                  className="text-xs"
                >
                  Skip for Now
                </Button>
                <Button
                  onClick={handleSaveReviewedMapping}
                  className="text-xs"
                >
                  Continue
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
