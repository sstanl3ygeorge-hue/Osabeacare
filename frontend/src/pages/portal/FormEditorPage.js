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
import html2canvas from 'html2canvas';
import jsPDF from 'jspdf';
import { 
  ArrowLeft, Save, Send, CheckCircle, Lock, Loader2, 
  FileText, User, Calendar, Building, Download, Printer,
  AlertTriangle, Shield, Eye
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

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

      // Get template for form fields (optional - imported forms may not have templates)
      try {
        const templateRes = await axios.get(`${API}/templates/${formRes.data.template_id}`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        setTemplate(templateRes.data);
      } catch (templateError) {
        // Template not found - this is expected for imported forms
        console.log('Template not found - showing imported document view');
        setTemplate(null);
      }
    } catch (error) {
      console.error('Failed to fetch form:', error);
      toast.error('Failed to load form');
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
      
      // Include signatures if changed
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

  const handleExportPDF = async () => {
    if (!formRef.current) return;
    
    setIsExporting(true);
    try {
      // Hide buttons and action elements
      const actionElements = formRef.current.querySelectorAll('[data-no-print]');
      actionElements.forEach(el => el.style.display = 'none');
      
      const canvas = await html2canvas(formRef.current, {
        scale: 2,
        useCORS: true,
        logging: false,
        backgroundColor: '#ffffff'
      });
      
      // Restore hidden elements
      actionElements.forEach(el => el.style.display = '');
      
      const imgData = canvas.toDataURL('image/png');
      const pdf = new jsPDF({
        orientation: 'portrait',
        unit: 'mm',
        format: 'a4'
      });
      
      const imgWidth = 210; // A4 width in mm
      const pageHeight = 297; // A4 height in mm
      const imgHeight = (canvas.height * imgWidth) / canvas.width;
      let heightLeft = imgHeight;
      let position = 0;
      
      pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight);
      heightLeft -= pageHeight;
      
      while (heightLeft >= 0) {
        position = heightLeft - imgHeight;
        pdf.addPage();
        pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight);
        heightLeft -= pageHeight;
      }
      
      const fileName = `${form.template_name.replace(/\s+/g, '_')}_${form.employee_code}_${new Date().toISOString().split('T')[0]}.pdf`;
      pdf.save(fileName);
      
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
        <Link to="/portal/templates">
          <Button className="mt-4">Back to Templates</Button>
        </Link>
      </div>
    );
  }
  
  // For imported forms without templates, show a simplified view
  const isImportedWithoutTemplate = !template;

  const statusColors = {
    draft: 'bg-gray-100 text-text-muted',
    sent: 'bg-info/10 text-info',
    in_progress: 'bg-warning/10 text-warning',
    completed: 'bg-info/10 text-info',
    completed_imported: 'bg-info/10 text-info',
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
  
  // Safe form name - fallback for imported forms
  const formName = template?.name || form.template_name || 'Imported Document';
  const formDescription = template?.description || '';

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
                    {formName}
                  </h1>
                  <span className={`px-3 py-1 rounded-full text-sm font-medium ${statusColors[form.status] || 'bg-gray-100 text-text-muted'}`}>
                    {form.status === 'completed_imported' ? 'Imported' : form.status?.replace('_', ' ')}
                  </span>
                  {form.locked && (
                    <span className="flex items-center gap-1 text-success text-sm bg-success/10 px-2 py-1 rounded-full">
                      <Lock className="h-4 w-4" />
                      Locked
                    </span>
                  )}
                  {visibilityBadge}
                </div>
                {formDescription && <p className="text-text-muted">{formDescription}</p>}
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
                        Send to Employee
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
                  <p className="font-medium text-text-primary">{form.employee_code}</p>
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
                    {new Date(form.created_at).toLocaleDateString()}
                  </p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Form Fields */}
        <Card className="border-[#E4E8EB] shadow-sm print:shadow-none print:border-0">
          <CardContent className="p-6 space-y-6">
            {/* For imported forms without template, show read-only view */}
            {isImportedWithoutTemplate ? (
              <div className="space-y-4">
                <div className="bg-info/5 border border-info/20 rounded-xl p-4">
                  <p className="text-sm text-info font-medium mb-2">Imported Document</p>
                  <p className="text-xs text-text-muted">
                    This document was imported from an existing file. The original document is stored as evidence.
                  </p>
                </div>
                
                {/* Show form data if any */}
                {Object.keys(formData).length > 0 && (
                  <div className="space-y-3">
                    <h4 className="font-medium text-text-primary">Form Data</h4>
                    {Object.entries(formData).map(([key, value]) => (
                      <div key={key} className="flex justify-between items-start p-3 bg-[#F8FAFA] rounded-lg">
                        <span className="text-sm text-text-muted capitalize">{key.replace(/_/g, ' ')}</span>
                        <span className="text-sm text-text-primary font-medium text-right max-w-[60%]">
                          {typeof value === 'object' ? JSON.stringify(value) : String(value || '-')}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
                
                {/* Show PDF link if available */}
                {form.pdf_url && (
                  <div className="border-t border-[#E4E8EB] pt-4 mt-4">
                    <h4 className="font-medium text-text-primary mb-3">Evidence Document</h4>
                    <a 
                      href={form.pdf_url} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-2 text-primary hover:underline"
                    >
                      <FileText className="h-4 w-4" />
                      View Original Document
                    </a>
                  </div>
                )}
              </div>
            ) : (
              <>
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
              </>
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
                    <span className="text-text-primary">{new Date(form.created_at).toLocaleString()}</span>
                  </div>
                )}
                {form.sent_at && (
                  <div className="flex items-center gap-3 text-sm">
                    <div className="w-2 h-2 bg-info rounded-full"></div>
                    <span className="text-text-muted w-24">Sent</span>
                    <span className="text-text-primary">{new Date(form.sent_at).toLocaleString()}</span>
                  </div>
                )}
                {form.viewed_at && (
                  <div className="flex items-center gap-3 text-sm">
                    <div className="w-2 h-2 bg-warning rounded-full"></div>
                    <span className="text-text-muted w-24">Viewed</span>
                    <span className="text-text-primary">{new Date(form.viewed_at).toLocaleString()}</span>
                  </div>
                )}
                {form.completed_at && (
                  <div className="flex items-center gap-3 text-sm">
                    <div className="w-2 h-2 bg-info rounded-full"></div>
                    <span className="text-text-muted w-24">Completed</span>
                    <span className="text-text-primary">{new Date(form.completed_at).toLocaleString()}</span>
                  </div>
                )}
                {form.signed_off_at && (
                  <div className="flex items-center gap-3 text-sm">
                    <div className="w-2 h-2 bg-success rounded-full"></div>
                    <span className="text-text-muted w-24">Signed Off</span>
                    <span className="text-text-primary">{new Date(form.signed_off_at).toLocaleString()}</span>
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
