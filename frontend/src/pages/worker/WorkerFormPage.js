import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { RadioGroup, RadioGroupItem } from '../../components/ui/radio-group';
import { toast } from 'sonner';
import { 
  ArrowLeft, Save, Send, Loader2, CheckCircle, Clock,
  FileText, Heart, User, Briefcase, Info, AlertCircle
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Icon lookup for form types — purely cosmetic
const FORM_ICONS = {
  staff_health_questionnaire: Heart,
  staff_personal_info: User,
  hmrc_starter_checklist: Briefcase,
  equal_opportunities: FileText,
  emergency_contacts: User,
};

export default function WorkerFormPage() {
  const { formId } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [formData, setFormData] = useState({});
  const [formMeta, setFormMeta] = useState(null);
  const [autoFillData, setAutoFillData] = useState({});
  const [lastSaved, setLastSaved] = useState(null);
  const [canEdit, setCanEdit] = useState(true);
  const [formStatus, setFormStatus] = useState(null);
  const [correctionReason, setCorrectionReason] = useState('');

  useEffect(() => {
    fetchFormData();
  }, [formId]);

  const fetchFormData = async () => {
    try {
      const token = localStorage.getItem('workerToken');
      const response = await axios.get(`${API}/worker/forms/${formId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setFormData(response.data.data || {});
      setFormMeta(response.data.form_definition);
      setAutoFillData(response.data.auto_fill_data || {});
      setLastSaved(response.data.last_saved);
      setCanEdit(response.data.can_edit !== false);
      setFormStatus(response.data.status || null);
      setCorrectionReason(response.data.correction_reason || '');
    } catch (error) {
      toast.error('Failed to load form');
      navigate('/worker/dashboard');
    } finally {
      setLoading(false);
    }
  };

  const handleFieldChange = (fieldId, value) => {
    setFormData(prev => ({
      ...prev,
      [fieldId]: value
    }));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const token = localStorage.getItem('workerToken');
      const response = await axios.post(
        `${API}/worker/forms/${formId}/save`,
        { form_data: formData },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setLastSaved(response.data.saved_at);
      toast.success('Progress saved! You can return later to continue.');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save');
    } finally {
      setSaving(false);
    }
  };

  const handleSubmit = async () => {
    // Validate required fields
    const missingFields = [];
    formMeta?.sections?.forEach(section => {
      section.fields.forEach(field => {
        // Skip conditional fields whose parent condition is not met
        if (field.conditional_on && formData[field.conditional_on] !== field.conditional_value) return;
        if (field.required && !formData[field.id]) {
          missingFields.push(field.label);
        }
      });
    });

    if (missingFields.length > 0) {
      toast.error(`Please complete required fields: ${missingFields.slice(0, 3).join(', ')}${missingFields.length > 3 ? '...' : ''}`);
      return;
    }

    setSubmitting(true);
    try {
      const token = localStorage.getItem('workerToken');
      console.log('Submitting form:', formId, 'with data:', formData);
      const response = await axios.post(
        `${API}/worker/forms/${formId}/submit`,
        { form_data: formData },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      console.log('Submit response:', response.data);
      toast.success('Form sent for Osabea review.');
      navigate('/worker/dashboard');
    } catch (error) {
      console.error('Submit error:', error.response?.data || error);
      toast.error(error.response?.data?.detail || 'Failed to submit form. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  const renderField = (field) => {
    const value = formData[field.id] ?? '';
    const isAutoFilled = autoFillData[field.id] !== undefined && formData[field.id] === autoFillData[field.id];

    // Conditional field visibility
    if (field.conditional_on) {
      const parentValue = formData[field.conditional_on];
      if (parentValue !== field.conditional_value) return null;
    }

    const fieldEl = (() => {
      switch (field.type) {
        case 'text':
        case 'tel':
        case 'email':
        case 'date':
        case 'number':
          return (
            <Input
              type={field.type}
              value={value}
              onChange={(e) => handleFieldChange(field.id, e.target.value)}
              placeholder={field.placeholder}
              disabled={!canEdit}
              className={`mt-1 ${isAutoFilled ? 'border-green-300 bg-green-50/40' : ''}`}
            />
          );
        
        case 'textarea':
          return (
            <Textarea
              value={value}
              onChange={(e) => handleFieldChange(field.id, e.target.value)}
              placeholder={field.placeholder}
              disabled={!canEdit}
              className={`mt-1 ${isAutoFilled ? 'border-green-300 bg-green-50/40' : ''}`}
              rows={3}
            />
          );
        
        case 'select':
          return (
            <Select
              value={value}
              onValueChange={(v) => handleFieldChange(field.id, v)}
              disabled={!canEdit}
            >
              <SelectTrigger className={`mt-1 ${isAutoFilled ? 'border-green-300 bg-green-50/40' : ''}`}>
                <SelectValue placeholder="Select an option" />
              </SelectTrigger>
              <SelectContent>
                {(field.options || []).map(opt => {
                  const optValue = typeof opt === 'object' ? opt.value : opt;
                  const optLabel = typeof opt === 'object' ? opt.label : opt;
                  return (
                    <SelectItem key={optValue} value={optValue}>{optLabel}</SelectItem>
                  );
                })}
              </SelectContent>
            </Select>
          );
        
        case 'radio':
          return (
            <RadioGroup
              value={value}
              onValueChange={(v) => handleFieldChange(field.id, v)}
              disabled={!canEdit}
              className="mt-2 space-y-2"
            >
              {(field.options || []).map(opt => (
                <div key={opt} className="flex items-center space-x-2">
                  <RadioGroupItem value={opt} id={`${field.id}-${opt}`} />
                  <Label htmlFor={`${field.id}-${opt}`} className="font-normal cursor-pointer">
                    {opt}
                  </Label>
                </div>
              ))}
            </RadioGroup>
          );
        
        case 'checkbox':
          return (
            <div className="flex items-start space-x-3 mt-2">
              <input
                type="checkbox"
                id={field.id}
                checked={!!value}
                onChange={(e) => handleFieldChange(field.id, e.target.checked)}
                disabled={!canEdit}
                className="mt-1 h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <Label htmlFor={field.id} className="font-normal cursor-pointer text-sm text-slate-600">
                {field.label}
              </Label>
            </div>
          );

        case 'info':
          return (
            <div className="text-sm text-slate-500 bg-slate-50 p-3 rounded-md border">
              {field.label}
            </div>
          );
        
        default:
          return null;
      }
    })();

    // Checkbox renders its own label, so skip wrapping label for it
    if (field.type === 'checkbox' || field.type === 'info') return fieldEl;

    return (
      <div key={field.id}>
        <div className="flex items-center gap-2">
          <Label className="text-sm font-medium">
            {field.label}
            {field.required && <span className="text-red-500 ml-1">*</span>}
          </Label>
          {isAutoFilled && (
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-green-100 text-green-700 border border-green-200 whitespace-nowrap">
              Pre-filled
            </span>
          )}
        </div>
        {fieldEl}
      </div>
    );
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  if (!formMeta?.sections) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <Card className="max-w-md">
          <CardContent className="pt-6 text-center">
            <p className="text-slate-600">Form not found</p>
            <Button onClick={() => navigate('/worker/dashboard')} className="mt-4">
              Back to Dashboard
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const FormIcon = FORM_ICONS[formId] || FileText;
  const autoFillCount = Object.keys(autoFillData).filter(k => formData[k] === autoFillData[k]).length;
  const totalFields = formMeta.sections.reduce((n, s) => n + s.fields.length, 0);
  const isCorrectionRequired = ['returned_for_correction', 'reopened_for_worker_correction', 'amendment_requested', 'rejected'].includes(formStatus);

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <div className="bg-white border-b sticky top-0 z-10">
        <div className="max-w-3xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Button variant="ghost" size="sm" onClick={() => navigate('/worker/dashboard')}>
                <ArrowLeft className="h-4 w-4" />
              </Button>
              <div className="flex items-center gap-2">
                <FormIcon className="h-5 w-5 text-blue-600" />
                <h1 className="font-semibold text-lg">{formMeta?.name || formId}</h1>
              </div>
            </div>
            {canEdit && (
              <div className="flex items-center gap-2">
                {lastSaved && (
                  <span className="text-xs text-slate-500 flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    Saved {new Date(lastSaved).toLocaleTimeString()}
                  </span>
                )}
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={handleSave}
                  disabled={saving}
                >
                  {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                  <span className="ml-1 hidden sm:inline">Save</span>
                </Button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Form Content */}
      <div className="max-w-3xl mx-auto px-4 py-6 space-y-6">
        {!canEdit && (
          <div className="bg-green-50 border border-green-200 rounded-lg p-4 flex items-center gap-3">
            <CheckCircle className="h-5 w-5 text-green-600" />
            <p className="text-green-800">This form has been sent for Osabea review.</p>
          </div>
        )}

        {canEdit && isCorrectionRequired && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-3">
            <AlertCircle className="h-5 w-5 text-red-600 mt-0.5 shrink-0" />
            <div>
              <p className="text-sm font-medium text-red-800">Correction required</p>
              <p className="text-sm text-red-700 mt-1">
                {correctionReason || 'Admin has reopened this form for correction. Please update it and submit again.'}
              </p>
            </div>
          </div>
        )}

        {canEdit && autoFillCount > 0 && (
          <div className="bg-green-50 border border-green-200 rounded-lg p-4 flex items-start gap-3">
            <Info className="h-5 w-5 text-green-600 mt-0.5 shrink-0" />
            <div>
              <p className="text-sm font-medium text-green-800">
                {autoFillCount === totalFields
                  ? 'Auto-filled from your application'
                  : `${autoFillCount} field${autoFillCount !== 1 ? 's' : ''} auto-filled from your application`}
              </p>
              <p className="text-xs text-green-600 mt-0.5">
                Pre-filled fields are marked with a green badge. Please review and correct if needed.
              </p>
            </div>
          </div>
        )}

        {formMeta.sections.map((section, sIdx) => (
          <Card key={sIdx} className="shadow-sm">
            <CardHeader>
              <CardTitle className="text-lg">{section.title}</CardTitle>
              {section.description && (
                <CardDescription>{section.description}</CardDescription>
              )}
            </CardHeader>
            <CardContent className="space-y-4">
              {section.fields.map((field) => {
                const rendered = renderField(field);
                if (!rendered) return null;
                // renderField already wraps non-checkbox/info fields with label div
                if (field.type === 'checkbox' || field.type === 'info') {
                  return <div key={field.id}>{rendered}</div>;
                }
                return <div key={field.id}>{rendered}</div>;
              })}
            </CardContent>
          </Card>
        ))}

        {/* Submit Button */}
        {canEdit && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
            <p className="text-sm text-blue-800 mb-3">
              <strong>{isCorrectionRequired ? 'Ready to resend?' : 'Ready to send?'}</strong> Once sent, this form cannot be edited unless Osabea returns it for correction.
            </p>
            <div className="flex justify-end gap-3">
              <Button variant="outline" onClick={handleSave} disabled={saving}>
                <Save className="h-4 w-4 mr-2" />
                Save Draft
              </Button>
              <Button onClick={handleSubmit} disabled={submitting} className="bg-green-600 hover:bg-green-700">
                {submitting ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <Send className="h-4 w-4 mr-2" />
                )}
                Submit to Admin
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
