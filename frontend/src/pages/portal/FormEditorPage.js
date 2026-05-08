import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../../components/ui/dialog';
import { Textarea } from '../../components/ui/textarea';
import { Label } from '../../components/ui/label';
import { toast } from 'sonner';
import FormFieldRenderer from '../../components/portal/FormFieldRenderer';
import SignaturePad, { SignatureDisplay } from '../../components/portal/SignaturePad';
import DocumentPreviewModal from '../../components/portal/DocumentPreviewModal';
import { 
  ArrowLeft, Save, Send, CheckCircle, Lock, Loader2, 
  FileText, User, Calendar, Building, Download, Printer,
  AlertTriangle, Shield, Eye, ExternalLink
} from 'lucide-react';
import { formatBackendDate, formatBackendDateTime } from '../../lib/dateUtils';
import API_BASE from '../../utils/apiBase';

const API = API_BASE;

export default function FormEditorPage() {
  const { formId } = useParams();
  const navigate = useNavigate();
  const { token, user, isAdmin } = useAuth();
  const formRef = useRef(null);
  
  const [form, setForm] = useState(null);
  const [template, setTemplate] = useState(null);
  const [formData, setFormData] = useState({});
  const [loading, setLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [signoffOpen, setSignoffOpen] = useState(false);
  const [adminSignature, setAdminSignature] = useState(null);
  const [employeeSignature, setEmployeeSignature] = useState(null);
  const [signoffNotes, setSignoffNotes] = useState('');
  const [previewOpen, setPreviewOpen] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);

  useEffect(() => {
    fetchData();
  }, [formId, token]);

  const fetchData = async () => {
    try {
      const formRes = await axios.get(`${API}/generated-forms/${formId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setForm(formRes.data);
      setFormData(formRes.data.form_data || {});
      
      // Load existing signatures
      if (formRes.data.employee_signature) {
        try {
          setEmployeeSignature(JSON.parse(formRes.data.employee_signature));
        } catch {
          setEmployeeSignature({ typed: formRes.data.employee_signature, hasSignature: true });
        }
      }
      if (formRes.data.admin_signature) {
        try {
          setAdminSignature(JSON.parse(formRes.data.admin_signature));
        } catch {
          setAdminSignature({ typed: formRes.data.admin_signature, hasSignature: true });
        }
      }

      // Only load template for non-imported forms
      const isImported = formRes.data.status === 'completed_imported' || formRes.data.source === 'imported';
      if (!isImported && formRes.data.template_id) {
        try {
          const templateRes = await axios.get(`${API}/templates/${formRes.data.template_id}`, {
            headers: { Authorization: `Bearer ${token}` }
          });
          setTemplate(templateRes.data);
        } catch (templateError) {
          // Template not found - treat as imported
          console.log('Template not found');
          setTemplate(null);
        }
      }
    } catch (error) {
      console.error('Failed to fetch form:', error);
      toast.error('Form not found');
    } finally {
      setLoading(false);
    }
  };

  const handleFieldChange = (fieldName, value) => {
    setFormData(prev => ({ ...prev, [fieldName]: value }));
  };

  const handleSave = async (newStatus = null) => {
    setIsSaving(true);
    try {
      const updateData = { form_data: formData };
      if (newStatus) updateData.status = newStatus;
      
      if (employeeSignature?.hasSignature) {
        updateData.employee_signature = JSON.stringify(employeeSignature);
        updateData.employee_signed_at = employeeSignature.date || new Date().toISOString();
      }

      await axios.put(`${API}/generated-forms/${formId}`, updateData, {
        headers: { Authorization: `Bearer ${token}` }
      });

      toast.success('Form saved successfully');
      fetchData();
    } catch (error) {
      toast.error('Failed to save form');
    } finally {
      setIsSaving(false);
    }
  };

  const handleSend = async () => {
    try {
      await axios.post(`${API}/generated-forms/${formId}/send`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Form sent to employee');
      fetchData();
    } catch (error) {
      toast.error('Failed to send form');
    }
  };

  const handleMarkComplete = async () => {
    if (template?.requires_employee_signature && !employeeSignature?.hasSignature) {
      toast.error('Employee signature is required before completing');
      return;
    }
    
    setIsSaving(true);
    try {
      const updateData = {
        form_data: formData,
        status: 'completed'
      };
      
      if (employeeSignature?.hasSignature) {
        updateData.employee_signature = JSON.stringify(employeeSignature);
        updateData.employee_signed_at = employeeSignature.date || new Date().toISOString();
      }

      await axios.put(`${API}/generated-forms/${formId}`, updateData, {
        headers: { Authorization: `Bearer ${token}` }
      });

      toast.success('Form marked as completed');
      fetchData();
    } catch (error) {
      toast.error('Failed to complete form');
    } finally {
      setIsSaving(false);
    }
  };

  const handleSignoff = async () => {
    if (!adminSignature?.hasSignature) {
      toast.error('Admin signature is required');
      return;
    }

    setIsSaving(true);
    try {
      await axios.post(`${API}/generated-forms/${formId}/signoff`, null, {
        headers: { Authorization: `Bearer ${token}` },
        params: {
          admin_signature: JSON.stringify(adminSignature),
          notes: signoffNotes || null
        }
      });

      toast.success('Form signed off and locked');
      setSignoffOpen(false);
      fetchData();
    } catch (error) {
      toast.error('Failed to sign off form');
    } finally {
      setIsSaving(false);
    }
  };

  const downloadGeneratedFormPdf = async () => {
    const response = await axios.get(`${API}/generated-forms/${formId}/pdf/download`, {
      headers: { Authorization: `Bearer ${token}` },
      responseType: 'blob'
    });
    const blob = new Blob([response.data]);
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = form?.pdf_filename || `${form?.template_name || 'form'}_${form?.employee_code || 'form'}.pdf`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const handleExportPDF = async () => {
    setIsExporting(true);
    try {
      await downloadGeneratedFormPdf();
      toast.success('PDF exported successfully');
    } catch (error) {
      console.error('PDF export failed:', error);
      toast.error('Failed to export PDF');
    } finally {
      setIsExporting(false);
    }
  };

  const handlePrint = () => {
    window.print();
  };

  const handleDownloadEvidence = async () => {
    if (!form?.pdf_url) {
      toast.error('No evidence file available');
      return;
    }
    try {
      await downloadGeneratedFormPdf();
      toast.success('Document downloaded');
    } catch (error) {
      toast.error('Failed to download document');
    }
  };

  const handleVerifyForm = async () => {
    setIsVerifying(true);
    try {
      await axios.post(`${API}/generated-forms/${formId}/verify`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast.success('Form verified');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to verify');
    } finally {
      setIsVerifying(false);
    }
  };

  // Get employee role for role-specific field filtering
  const employeeRole = formData.employee_role || form?.employee_role || '';

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!form) {
    return (
      <div className="text-center py-12">
        <p className="text-text-muted">Form not found</p>
        <button onClick={() => navigate(-1)}>
          <Button className="mt-4">Go Back</Button>
        </button>
      </div>
    );
  }
  
  // Check if this is an imported document (document-first view)
  const isImported = form.status === 'completed_imported' || form.source === 'imported' || !template;
  const hasEvidence = !!form.pdf_url;
  const isVerified = form.verified;

  // ============ IMPORTED DOCUMENT VIEW ============
  if (isImported) {
    return (
      <div className="space-y-6" data-testid="imported-document-view">
        {/* Back Link */}
        <button 
          onClick={() => navigate(-1)} 
          className="inline-flex items-center gap-2 text-text-muted hover:text-primary transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Back
        </button>

        {/* Document Card */}
        <Card className="border-[#E4E8EB] shadow-sm">
          <CardContent className="p-6">
            {/* Header */}
            <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-4 mb-6">
              <div>
                <div className="flex items-center gap-3 mb-2 flex-wrap">
                  <h1 className="font-heading text-2xl font-bold text-text-primary">
                    {form.template_name || 'Imported Document'}
                  </h1>
                  <span className="px-3 py-1 rounded-full text-sm font-medium bg-info/10 text-info">
                    Uploaded Evidence
                  </span>
                  {isVerified && (
                    <span className="flex items-center gap-1 text-success text-sm bg-success/10 px-2 py-1 rounded-full">
                      <Shield className="h-4 w-4" />
                      Verified
                    </span>
                  )}
                </div>
                <p className="text-text-muted">
                  {form.employee_name} ({form.employee_code || '—'})
                </p>
              </div>
            </div>

            {/* Banner */}
            <div className="bg-info/5 border border-info/20 rounded-xl p-4 mb-6">
              <div className="flex items-start gap-3">
                <FileText className="h-5 w-5 text-info flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-info">Uploaded Evidence Document</p>
                  <p className="text-xs text-text-muted mt-1">
                    This document was uploaded as compliance evidence. The original file is available below.
                  </p>
                </div>
              </div>
            </div>

            {/* Evidence Actions */}
            {hasEvidence ? (
              <div className="space-y-4">
                <div className="flex flex-wrap gap-3">
                  <Button
                    onClick={() => setPreviewOpen(true)}
                    className="bg-primary hover:bg-primary-hover text-white rounded-xl"
                    data-testid="view-evidence-btn"
                  >
                    <Eye className="h-4 w-4 mr-2" />
                    View Document
                  </Button>

                </div>

                {/* File Info */}
                <div className="p-4 bg-[#F8FAFA] rounded-xl">
                  <div className="flex items-center gap-3">
                    <FileText className="h-8 w-8 text-primary" />
                    <div>
                      <p className="font-medium text-text-primary">
                        {form.pdf_filename || `${form.template_name}.pdf`}
                      </p>
                      <p className="text-xs text-text-muted">
                        Uploaded {formatBackendDate(form.created_at)}
                        {form.verified && ` • Verified by ${form.verified_by_name || 'Admin'}`}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-center py-8 bg-error/5 border border-error/20 rounded-xl">
                <AlertTriangle className="h-10 w-10 text-error mx-auto mb-3" />
                <p className="text-error font-medium">No Evidence Uploaded</p>
                <p className="text-sm text-text-muted mt-1">
                  This requirement does not have an evidence file attached.
                </p>
              </div>
            )}

            {/* Metadata */}
            <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 mt-6 pt-6 border-t border-[#E4E8EB]">
              <div className="flex items-center gap-3">
                <User className="h-5 w-5 text-text-muted" />
                <div>
                  <p className="text-xs text-text-muted">Employee</p>
                  <p className="font-medium text-text-primary">{form.employee_name}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <FileText className="h-5 w-5 text-text-muted" />
                <div>
                  <p className="text-xs text-text-muted">Employee ID</p>
                  <p className="font-medium text-text-primary">{form.employee_code || '—'}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <Building className="h-5 w-5 text-text-muted" />
                <div>
                  <p className="text-xs text-text-muted">Category</p>
                  <p className="font-medium text-text-primary">{form.template_category || '-'}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <Calendar className="h-5 w-5 text-text-muted" />
                <div>
                  <p className="text-xs text-text-muted">Date</p>
                  <p className="font-medium text-text-primary">
                    {formatBackendDate(form.created_at)}
                  </p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Document Preview Modal */}
        <DocumentPreviewModal
          isOpen={previewOpen}
          onClose={() => setPreviewOpen(false)}
          fileUrl={`${API}/generated-forms/${formId}/pdf/file`}
          fileName={form.pdf_filename || form.template_name}
          token={token}
          onDownload={handleDownloadEvidence}
        />
      </div>
    );
  }

  // ============ REGULAR FORM EDITOR VIEW ============
  const statusColors = {
    draft: 'bg-gray-100 text-text-muted',
    sent: 'bg-info/10 text-info',
    in_progress: 'bg-warning/10 text-warning',
    completed: 'bg-info/10 text-info',
    reviewed: 'bg-warning/10 text-warning',
    signed_off: 'bg-success/10 text-success',
    archived: 'bg-gray-100 text-text-muted'
  };

  const visibilityBadge = template?.visibility === 'restricted' ? (
    <span className="flex items-center gap-1 text-warning text-xs bg-warning/10 px-2 py-1 rounded-full">
      <Shield className="h-3 w-3" />
      Restricted
    </span>
  ) : template?.visibility === 'confidential' ? (
    <span className="flex items-center gap-1 text-error text-xs bg-error/10 px-2 py-1 rounded-full">
      <AlertTriangle className="h-3 w-3" />
      Confidential
    </span>
  ) : null;

  return (
    <div className="space-y-6 print:space-y-4" data-testid="form-editor">
      {/* Back Link - hide on print */}
      <div className="print:hidden">
        <button 
          onClick={() => navigate(-1)} 
          className="inline-flex items-center gap-2 text-text-muted hover:text-primary transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Back
        </button>
      </div>

      {/* Form Content - for PDF export */}
      <div ref={formRef} className="space-y-6 bg-white">
        {/* Header */}
        <Card className="border-[#E4E8EB] shadow-sm print:shadow-none print:border-b print:rounded-none">
          <CardContent className="p-6">
            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
              <div>
                <div className="flex items-center gap-3 mb-2 flex-wrap">
                  <h1 className="font-heading text-2xl font-bold text-text-primary">
                    {template?.name || form.template_name}
                  </h1>
                  <span className={`px-3 py-1 rounded-full text-sm font-medium ${statusColors[form.status] || 'bg-gray-100 text-text-muted'}`}>
                    {form.status?.replace('_', ' ')}
                  </span>
                  {form.locked && (
                    <span className="flex items-center gap-1 text-success text-sm bg-success/10 px-2 py-1 rounded-full">
                      <Lock className="h-4 w-4" />
                      Locked
                    </span>
                  )}
                  {visibilityBadge}
                </div>
                {template?.description && <p className="text-text-muted">{template.description}</p>}
              </div>

              {/* Actions - hide on print */}
              <div className="flex flex-wrap gap-2 print:hidden" data-no-print>
                <Button 
                  variant="outline" 
                  onClick={handlePrint}
                  className="rounded-xl"
                >
                  <Printer className="h-4 w-4 mr-2" />
                  Print
                </Button>
                <Button 
                  variant="outline" 
                  onClick={handleExportPDF}
                  disabled={isExporting}
                  className="rounded-xl"
                >
                  {isExporting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Download className="h-4 w-4 mr-2" />}
                  Export PDF
                </Button>
                
                {!form.locked && (
                  <>
                    <Button 
                      variant="outline" 
                      onClick={() => handleSave()}
                      disabled={isSaving}
                      className="rounded-xl"
                      data-testid="save-form"
                    >
                      {isSaving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4 mr-2" />}
                      Save
                    </Button>
                    
                    {form.status === 'draft' && (
                      <Button 
                        onClick={handleSend}
                        className="bg-info hover:bg-info/90 text-white rounded-xl"
                        data-testid="send-form"
                      >
                        <Send className="h-4 w-4 mr-2" />
                        Send Reminder
                      </Button>
                    )}

                    {['sent', 'in_progress'].includes(form.status) && (
                      <Button 
                        onClick={handleMarkComplete}
                        className="bg-success hover:bg-success/90 text-white rounded-xl"
                        data-testid="complete-form"
                      >
                        <CheckCircle className="h-4 w-4 mr-2" />
                        Mark Complete
                      </Button>
                    )}

                    {(form.status === 'completed' || form.status === 'reviewed') && isAdmin() && (
                      <Dialog open={signoffOpen} onOpenChange={setSignoffOpen}>
                        <DialogTrigger asChild>
                          <Button className="bg-success hover:bg-success/90 text-white rounded-xl" data-testid="signoff-btn">
                            <CheckCircle className="h-4 w-4 mr-2" />
                            Sign Off & Lock
                          </Button>
                        </DialogTrigger>
                        <DialogContent className="max-w-lg">
                          <DialogHeader>
                            <DialogTitle className="font-heading">Admin Sign-Off</DialogTitle>
                          </DialogHeader>
                          <div className="space-y-4 mt-4">
                            <p className="text-text-muted text-sm">
                              By signing off, you confirm that all information has been reviewed and is accurate. 
                              The form will be <strong>locked</strong> and cannot be edited after sign-off.
                            </p>
                            
                            <SignaturePad
                              label="Admin Signature"
                              value={adminSignature}
                              onChange={setAdminSignature}
                              required
                            />

                            <div className="space-y-2">
                              <Label>Sign-Off Notes (optional)</Label>
                              <Textarea
                                value={signoffNotes}
                                onChange={(e) => setSignoffNotes(e.target.value)}
                                placeholder="Any additional notes..."
                                className="rounded-xl"
                                rows={3}
                              />
                            </div>

                            <div className="flex justify-end gap-3 pt-4">
                              <Button type="button" variant="outline" onClick={() => setSignoffOpen(false)} className="rounded-xl">
                                Cancel
                              </Button>
                              <Button 
                                onClick={handleSignoff}
                                disabled={isSaving || !adminSignature?.hasSignature}
                                className="bg-success hover:bg-success/90 text-white rounded-xl"
                                data-testid="confirm-signoff"
                              >
                                {isSaving ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Sign Off & Lock'}
                              </Button>
                            </div>
                          </div>
                        </DialogContent>
                      </Dialog>
                    )}
                  </>
                )}
              </div>
            </div>

            {/* Employee Info Header */}
            <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 mt-6 pt-6 border-t border-[#E4E8EB]">
              <div className="flex items-center gap-3">
                <User className="h-5 w-5 text-text-muted" />
                <div>
                  <p className="text-xs text-text-muted">Employee</p>
                  <p className="font-medium text-text-primary">{form.employee_name}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <FileText className="h-5 w-5 text-text-muted" />
                <div>
                  <p className="text-xs text-text-muted">Employee ID</p>
                  <p className="font-medium text-text-primary">{form.employee_code || '—'}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <Building className="h-5 w-5 text-text-muted" />
                <div>
                  <p className="text-xs text-text-muted">Role</p>
                  <p className="font-medium text-text-primary">{formData.employee_role || '-'}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <Calendar className="h-5 w-5 text-text-muted" />
                <div>
                  <p className="text-xs text-text-muted">Generated</p>
                  <p className="font-medium text-text-primary">
                    {formatBackendDate(form.created_at)}
                  </p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Form Fields */}
        <Card className="border-[#E4E8EB] shadow-sm print:shadow-none print:border-0">
          <CardContent className="p-6 space-y-6">
            {template?.form_fields?.map((field, index) => (
              <FormFieldRenderer
                key={field.name || index}
                field={field}
                value={formData[field.name]}
                onChange={handleFieldChange}
                disabled={form.locked}
                employeeRole={employeeRole}
              />
            ))}

            {/* Signatures Section */}
            {(template?.requires_employee_signature || template?.requires_admin_signature) && (
              <div className="border-t border-[#E4E8EB] pt-6 mt-6">
                <h3 className="font-heading font-semibold text-text-primary mb-6">Signatures</h3>
                
                <div className="grid sm:grid-cols-2 gap-6">
                  {template?.requires_employee_signature && (
                    <div>
                      {form.locked || form.employee_signature ? (
                        <SignatureDisplay 
                          signature={employeeSignature}
                          label="Employee Signature"
                        />
                      ) : (
                        <SignaturePad
                          label="Employee Signature"
                          value={employeeSignature}
                          onChange={setEmployeeSignature}
                          disabled={form.locked}
                          required={template?.requires_employee_signature}
                        />
                      )}
                    </div>
                  )}

                  {template?.requires_admin_signature && (
                    <div>
                      <SignatureDisplay 
                        signature={adminSignature}
                        label="Admin Signature"
                      />
                    </div>
                  )}
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Timeline */}
        {(form.sent_at || form.viewed_at || form.completed_at || form.signed_off_at) && (
          <Card className="border-[#E4E8EB] shadow-sm print:shadow-none print:border-0">
            <CardHeader>
              <CardTitle className="font-heading text-lg">Form Timeline</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {form.created_at && (
                  <div className="flex items-center gap-3 text-sm">
                    <div className="w-2 h-2 bg-primary rounded-full"></div>
                    <span className="text-text-muted w-24">Created</span>
                    <span className="text-text-primary">{formatBackendDateTime(form.created_at)}</span>
                  </div>
                )}
                {form.sent_at && (
                  <div className="flex items-center gap-3 text-sm">
                    <div className="w-2 h-2 bg-info rounded-full"></div>
                    <span className="text-text-muted w-24">Sent</span>
                    <span className="text-text-primary">{formatBackendDateTime(form.sent_at)}</span>
                  </div>
                )}
                {form.viewed_at && (
                  <div className="flex items-center gap-3 text-sm">
                    <div className="w-2 h-2 bg-warning rounded-full"></div>
                    <span className="text-text-muted w-24">Viewed</span>
                    <span className="text-text-primary">{formatBackendDateTime(form.viewed_at)}</span>
                  </div>
                )}
                {form.completed_at && (
                  <div className="flex items-center gap-3 text-sm">
                    <div className="w-2 h-2 bg-info rounded-full"></div>
                    <span className="text-text-muted w-24">Completed</span>
                    <span className="text-text-primary">{formatBackendDateTime(form.completed_at)}</span>
                  </div>
                )}
                {form.signed_off_at && (
                  <div className="flex items-center gap-3 text-sm">
                    <div className="w-2 h-2 bg-success rounded-full"></div>
                    <span className="text-text-muted w-24">Signed Off</span>
                    <span className="text-text-primary">{formatBackendDateTime(form.signed_off_at)}</span>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Print styles */}
      <style>{`
        @media print {
          body * {
            visibility: hidden;
          }
          #root, #root * {
            visibility: visible;
          }
          [data-no-print] {
            display: none !important;
          }
          .print\\:hidden {
            display: none !important;
          }
        }
      `}</style>
    </div>
  );
}

