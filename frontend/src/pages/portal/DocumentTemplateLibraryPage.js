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
import { Loader2, Upload, RefreshCw, Save, Rocket, FileText, Plus } from 'lucide-react';

const API = API_BASE;

const WORKFLOW_AREAS = [
  { value: 'compliance_policy', label: 'Compliance Policy' },
  { value: 'staff_onboarding', label: 'Staff Onboarding' },
  { value: 'staff_policy_acknowledgement', label: 'Staff Policy Acknowledgement' },
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

function safeJsonParse(value, fallback) {
  try {
    return JSON.parse(value);
  } catch {
    return fallback;
  }
}

export default function DocumentTemplateLibraryPage() {
  const { token, isAdmin } = useAuth();

  const [templates, setTemplates] = useState([]);
  const [loadingTemplates, setLoadingTemplates] = useState(true);
  const [selectedTemplateId, setSelectedTemplateId] = useState('');
  const [templateDetail, setTemplateDetail] = useState(null);
  const [selectedVersionId, setSelectedVersionId] = useState('');

  const [file, setFile] = useState(null);
  const [title, setTitle] = useState('');
  const [category, setCategory] = useState('Policy');
  const [documentType, setDocumentType] = useState('policy');
  const [workflowArea, setWorkflowArea] = useState('compliance_policy');
  const [sourceProvider, setSourceProvider] = useState('CQC Expert');
  const [reviewPeriodMonths, setReviewPeriodMonths] = useState('12');
  const [effectiveDate, setEffectiveDate] = useState('');

  const [importing, setImporting] = useState(false);
  const [savingMappings, setSavingMappings] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [generating, setGenerating] = useState(false);

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

  const handleImport = async () => {
    if (!isAdmin()) {
      toast.error('Admin access required');
      return;
    }
    if (!file) {
      toast.error('Select a DOCX or PDF file first');
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
        }
      });

      const importedTemplate = response.data?.template;
      toast.success(`Imported ${importedTemplate?.title || 'template'} successfully`);
      setFile(null);
      setTitle('');
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

  return (
    <div className="space-y-6" data-testid="document-template-library-page">
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3">
        <div>
          <h1 className="font-heading text-2xl font-bold text-text-primary">Template Library</h1>
          <p className="text-sm text-text-muted">
            Import provider templates, map placeholders, publish immutable versions, and generate workflow-ready branded PDFs.
          </p>
        </div>
        <Button variant="outline" onClick={fetchTemplates} disabled={loadingTemplates}>
          {loadingTemplates ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <RefreshCw className="h-4 w-4 mr-2" />}
          Refresh
        </Button>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <Card className="xl:col-span-1 border-[#E4E8EB]">
          <CardHeader>
            <CardTitle className="text-base">Import New Template</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="space-y-1">
              <Label>Template File (DOCX or PDF)</Label>
              <Input type="file" accept=".docx,.pdf" onChange={(e) => setFile(e.target.files?.[0] || null)} />
            </div>

            <div className="space-y-1">
              <Label>Title Override (Optional)</Label>
              <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Use extracted heading if empty" />
            </div>

            <div className="space-y-1">
              <Label>Category</Label>
              <Input value={category} onChange={(e) => setCategory(e.target.value)} />
            </div>

            <div className="space-y-1">
              <Label>Document Type</Label>
              <Input value={documentType} onChange={(e) => setDocumentType(e.target.value)} />
            </div>

            <div className="space-y-1">
              <Label>Workflow Area</Label>
              <Select value={workflowArea} onValueChange={setWorkflowArea}>
                <SelectTrigger>
                  <SelectValue placeholder="Select workflow area" />
                </SelectTrigger>
                <SelectContent>
                  {WORKFLOW_AREAS.map((item) => (
                    <SelectItem key={item.value} value={item.value}>{item.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1">
              <Label>Source Provider</Label>
              <Input value={sourceProvider} onChange={(e) => setSourceProvider(e.target.value)} />
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div className="space-y-1">
                <Label>Review Period (Months)</Label>
                <Input type="number" min="1" max="36" value={reviewPeriodMonths} onChange={(e) => setReviewPeriodMonths(e.target.value)} />
              </div>
              <div className="space-y-1">
                <Label>Effective Date</Label>
                <Input type="date" value={effectiveDate} onChange={(e) => setEffectiveDate(e.target.value)} />
              </div>
            </div>

            <Button onClick={handleImport} disabled={importing || !isAdmin()} className="w-full">
              {importing ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Upload className="h-4 w-4 mr-2" />}
              Import Template
            </Button>
          </CardContent>
        </Card>

        <Card className="xl:col-span-2 border-[#E4E8EB]">
          <CardHeader>
            <CardTitle className="text-base">Templates</CardTitle>
          </CardHeader>
          <CardContent>
            {loadingTemplates ? (
              <div className="h-24 flex items-center justify-center">
                <Loader2 className="h-6 w-6 animate-spin text-primary" />
              </div>
            ) : templates.length === 0 ? (
              <p className="text-sm text-text-muted">No templates imported yet.</p>
            ) : (
              <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
                {templates.map((template) => (
                  <button
                    key={template.id}
                    type="button"
                    onClick={() => setSelectedTemplateId(template.id)}
                    className={`w-full text-left p-3 rounded-lg border transition ${selectedTemplateId === template.id ? 'border-primary bg-primary/5' : 'border-[#E4E8EB] hover:border-primary/40'}`}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="font-medium text-sm text-text-primary">{template.title}</p>
                        <p className="text-xs text-text-muted">{template.doc_code} • {template.workflow_area || 'n/a'}</p>
                      </div>
                      <Badge variant="secondary">{template.status}</Badge>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {templateDetail && selectedVersion && (
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          <Card className="xl:col-span-2 border-[#E4E8EB]">
            <CardHeader>
              <CardTitle className="text-base flex items-center justify-between">
                <span>Placeholder Mapping</span>
                <div className="flex items-center gap-2">
                  <Select value={selectedVersionId} onValueChange={setSelectedVersionId}>
                    <SelectTrigger className="w-48">
                      <SelectValue placeholder="Version" />
                    </SelectTrigger>
                    <SelectContent>
                      {(templateDetail.versions || []).map((v) => (
                        <SelectItem key={v.id} value={v.id}>v{v.version} ({v.status})</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Badge variant="outline">{selectedVersion.status}</Badge>
                </div>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex gap-2">
                <Input
                  value={manualPlaceholder}
                  onChange={(e) => setManualPlaceholder(e.target.value)}
                  placeholder="Add manual placeholder, e.g. [Policy Owner]"
                />
                <Button variant="outline" onClick={handleAddManualPlaceholder}>
                  <Plus className="h-4 w-4 mr-1" />
                  Add
                </Button>
              </div>

              <div className="border rounded-lg max-h-[420px] overflow-y-auto">
                <table className="w-full text-sm">
                  <thead className="bg-muted/40 sticky top-0">
                    <tr>
                      <th className="text-left p-2">Placeholder</th>
                      <th className="text-left p-2">Variable</th>
                      <th className="text-left p-2">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(mappingDraft).length === 0 && (
                      <tr>
                        <td className="p-3 text-text-muted" colSpan={3}>No placeholders detected yet.</td>
                      </tr>
                    )}
                    {Object.entries(mappingDraft).map(([placeholderText, meta]) => (
                      <tr key={placeholderText} className="border-t">
                        <td className="p-2 align-top">
                          <div className="font-medium">{placeholderText}</div>
                          {meta?.detection_reason && (
                            <p className="text-xs text-text-muted">Reason: {meta.detection_reason}</p>
                          )}
                        </td>
                        <td className="p-2 align-top">
                          <Select
                            value={meta?.system_variable || '__none__'}
                            onValueChange={(value) => handleMapChange(placeholderText, 'system_variable', value === '__none__' ? '' : value)}
                          >
                            <SelectTrigger>
                              <SelectValue placeholder="Select system variable" />
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
                            <SelectTrigger>
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

              <div className="flex flex-wrap gap-2">
                <Button onClick={handleSaveMappings} disabled={savingMappings || selectedVersion.status !== 'draft'}>
                  {savingMappings ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Save className="h-4 w-4 mr-2" />}
                  Save Mapping
                </Button>
                <Button onClick={handlePublish} disabled={publishing || selectedVersion.status !== 'draft'}>
                  {publishing ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Rocket className="h-4 w-4 mr-2" />}
                  Publish Version
                </Button>
              </div>
            </CardContent>
          </Card>

          <Card className="xl:col-span-1 border-[#E4E8EB]">
            <CardHeader>
              <CardTitle className="text-base">Generate Branded PDF</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div>
                <Label>Context JSON</Label>
                <Textarea
                  className="min-h-[240px] font-mono text-xs"
                  value={contextJson}
                  onChange={(e) => setContextJson(e.target.value)}
                />
              </div>

              <Button onClick={handleGenerateSample} disabled={generating} className="w-full">
                {generating ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <FileText className="h-4 w-4 mr-2" />}
                Generate Sample
              </Button>

              {lastGenerated?.id && (
                <a
                  href={`${API}/generated-documents/${lastGenerated.id}/pdf`}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center text-sm text-primary underline"
                >
                  Open Generated PDF
                </a>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
