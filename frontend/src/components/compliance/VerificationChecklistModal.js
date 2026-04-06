/**
 * VerificationChecklistModal - Smart Verification System
 * 
 * Admin completes this checklist to verify employee documents.
 * Generates a system verification record that must be approved.
 * Only approved verifications count toward compliance %.
 */

import { useState, useEffect } from 'react';
import axios from 'axios';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '../ui/dialog';
import { Button } from '../ui/button';
import { Checkbox } from '../ui/checkbox';
import { Label } from '../ui/label';
import { Input } from '../ui/input';
import { Textarea } from '../ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Badge } from '../ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Separator } from '../ui/separator';
import { toast } from 'sonner';
import { 
  CheckCircle, AlertTriangle, FileText, User, MapPin, Calendar,
  Shield, Loader2, Eye, Video, Building, ExternalLink, ClipboardCheck
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const VERIFICATION_METHOD_LABELS = {
  'in_person': 'Verified Original In Person',
  'video_call': 'Verified via Video Call',
  'online_check': 'Online Check (gov.uk / DBS Update Service)'
};

const REQUIREMENT_ICONS = {
  'right_to_work': Shield,
  'dbs': Shield,
  'identity': User,
  'proof_of_address': MapPin
};

const REQUIREMENT_LABELS = {
  'right_to_work': 'Right to Work',
  'dbs': 'DBS Certificate',
  'identity': 'Identity Document',
  'proof_of_address': 'Proof of Address'
};

export default function VerificationChecklistModal({
  isOpen,
  onClose,
  requirementId,
  employeeId,
  employeeName,
  evidenceDocument,
  aiExtraction,
  onVerificationComplete
}) {
  const [template, setTemplate] = useState(null);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  
  // Form state
  const [verificationMethod, setVerificationMethod] = useState('');
  const [checklistValues, setChecklistValues] = useState({});
  const [extraFieldValues, setExtraFieldValues] = useState({});
  const [adminNotes, setAdminNotes] = useState('');
  
  // Fetch template on open
  useEffect(() => {
    if (isOpen && requirementId) {
      fetchTemplate();
    }
  }, [isOpen, requirementId]);
  
  const fetchTemplate = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API}/verification/checklist-template/${requirementId}`);
      setTemplate(response.data);
      
      // Initialize checkbox values to false
      const initialValues = {};
      response.data.fields?.forEach(field => {
        initialValues[field.id] = false;
      });
      setChecklistValues(initialValues);
      
      // Set default verification method
      if (response.data.verification_methods?.length === 1) {
        setVerificationMethod(response.data.verification_methods[0]);
      }
    } catch (error) {
      console.error('Error fetching template:', error);
      toast.error('Failed to load verification checklist');
    } finally {
      setLoading(false);
    }
  };
  
  const handleCheckboxChange = (fieldId, checked) => {
    setChecklistValues(prev => ({
      ...prev,
      [fieldId]: checked
    }));
  };
  
  const handleExtraFieldChange = (fieldId, value) => {
    setExtraFieldValues(prev => ({
      ...prev,
      [fieldId]: value
    }));
  };
  
  const allRequiredChecked = () => {
    if (!template) return false;
    return template.fields.filter(f => f.required).every(f => checklistValues[f.id] === true);
  };
  
  const handleSubmit = async () => {
    if (!verificationMethod) {
      toast.error('Please select a verification method');
      return;
    }
    
    if (!allRequiredChecked()) {
      toast.error('Please complete all required checklist items');
      return;
    }
    
    setSubmitting(true);
    try {
      const payload = {
        requirement_id: requirementId,
        employee_id: employeeId,
        evidence_document_id: evidenceDocument?.id,
        verification_method: verificationMethod,
        admin_notes: adminNotes,
        // Common fields from checklist
        document_appears_genuine: checklistValues.document_appears_genuine || false,
        details_match_profile: checklistValues.details_match_profile || false,
        // Identity specific
        photo_matches_applicant: checklistValues.photo_matches_applicant,
        security_features_verified: checklistValues.security_features_verified,
        expiry_date_valid: checklistValues.expiry_date_valid,
        // POA specific
        address_matches_declared: checklistValues.address_matches_declared,
        document_within_6_months: checklistValues.document_within_6_months,
        document_type_acceptable: checklistValues.document_type_acceptable,
        name_matches_employee: checklistValues.name_matches_employee,
        // RTW specific
        share_code_verified: checklistValues.share_code_verified,
        right_to_work_confirmed: checklistValues.right_to_work_confirmed,
        share_code_used: extraFieldValues.share_code_used,
        work_restrictions: extraFieldValues.work_restrictions,
        // DBS specific
        dbs_update_service_checked: checklistValues.dbs_update_service_checked,
        certificate_number_matches: checklistValues.certificate_number_matches,
        dbs_status: extraFieldValues.dbs_status
      };
      
      const response = await axios.post(`${API}/verification/submit-checklist`, payload);
      
      if (response.data.success) {
        toast.success('Verification checklist submitted!', {
          description: 'Click "Approve Verification" to complete the process.'
        });
        
        // Now auto-approve if all checks passed
        const approveResponse = await axios.post(`${API}/verification/approve`, {
          verification_document_id: response.data.verification_document_id,
          approved: true
        });
        
        if (approveResponse.data.success) {
          toast.success('Verification approved!', {
            description: 'This document now counts toward compliance.'
          });
          onVerificationComplete?.();
          onClose();
        }
      }
    } catch (error) {
      console.error('Error submitting verification:', error);
      toast.error('Failed to submit verification', {
        description: error.response?.data?.detail || 'Please try again'
      });
    } finally {
      setSubmitting(false);
    }
  };
  
  const Icon = REQUIREMENT_ICONS[requirementId] || FileText;
  
  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-2xl max-h-[90vh] overflow-y-auto bg-white">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-lg">
            <ClipboardCheck className="h-5 w-5 text-primary" />
            {REQUIREMENT_LABELS[requirementId] || 'Document'} Verification Checklist
          </DialogTitle>
          <DialogDescription>
            Complete this checklist to verify {employeeName}'s {REQUIREMENT_LABELS[requirementId]?.toLowerCase() || 'document'}.
            Only approved verifications count toward compliance.
          </DialogDescription>
        </DialogHeader>
        
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        ) : template ? (
          <div className="space-y-6 py-4">
            {/* AI Extraction Results (if available) */}
            {aiExtraction && Object.keys(aiExtraction.validation_results || {}).length > 0 && (
              <Card className="border-blue-200 bg-blue-50">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-blue-800 flex items-center gap-2">
                    <Eye className="h-4 w-4" />
                    AI Document Analysis
                  </CardTitle>
                </CardHeader>
                <CardContent className="text-sm space-y-2">
                  {aiExtraction.extracted_name && (
                    <div className="flex items-center gap-2">
                      <span className="text-blue-600">Name:</span>
                      <span>{aiExtraction.extracted_name}</span>
                      {aiExtraction.validation_results?.name_match && (
                        <Badge className="bg-green-100 text-green-700 text-xs">
                          <CheckCircle className="h-3 w-3 mr-1" />
                          {aiExtraction.confidence_scores?.name_match || 0}% match
                        </Badge>
                      )}
                    </div>
                  )}
                  {aiExtraction.extracted_address && (
                    <div className="flex items-center gap-2">
                      <span className="text-blue-600">Address:</span>
                      <span className="truncate max-w-xs">{aiExtraction.extracted_address}</span>
                      {aiExtraction.validation_results?.address_match !== undefined && (
                        <Badge className={aiExtraction.validation_results.address_match ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}>
                          {aiExtraction.validation_results.address_match ? 'Match' : 'Mismatch'}
                        </Badge>
                      )}
                    </div>
                  )}
                  {aiExtraction.extracted_date && (
                    <div className="flex items-center gap-2">
                      <span className="text-blue-600">Document Date:</span>
                      <span>{aiExtraction.extracted_date}</span>
                      {aiExtraction.validation_results?.date_valid !== undefined && (
                        <Badge className={aiExtraction.validation_results.date_valid ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}>
                          {aiExtraction.validation_results.date_valid ? 'Within 6 months' : 'Too old'}
                        </Badge>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>
            )}
            
            {/* Verification Method */}
            <div className="space-y-2">
              <Label className="text-sm font-medium">Verification Method *</Label>
              <Select value={verificationMethod} onValueChange={setVerificationMethod}>
                <SelectTrigger data-testid="verification-method-select">
                  <SelectValue placeholder="Select how you verified this document" />
                </SelectTrigger>
                <SelectContent>
                  {template.verification_methods?.map(method => (
                    <SelectItem key={method} value={method}>
                      <div className="flex items-center gap-2">
                        {method === 'in_person' && <User className="h-4 w-4" />}
                        {method === 'video_call' && <Video className="h-4 w-4" />}
                        {method === 'online_check' && <ExternalLink className="h-4 w-4" />}
                        {VERIFICATION_METHOD_LABELS[method] || method}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            <Separator />
            
            {/* Checklist Items */}
            <div className="space-y-3">
              <Label className="text-sm font-medium">Verification Checklist</Label>
              {template.fields?.map(field => (
                <div 
                  key={field.id} 
                  className={`flex items-start gap-3 p-3 rounded-lg border transition-colors ${
                    checklistValues[field.id] 
                      ? 'bg-green-50 border-green-200' 
                      : 'bg-gray-50 border-gray-200'
                  }`}
                >
                  <Checkbox
                    id={field.id}
                    checked={checklistValues[field.id] || false}
                    onCheckedChange={(checked) => handleCheckboxChange(field.id, checked)}
                    data-testid={`checklist-${field.id}`}
                    className="mt-0.5"
                  />
                  <Label 
                    htmlFor={field.id} 
                    className="text-sm cursor-pointer flex-1"
                  >
                    {field.label}
                    {field.required && <span className="text-red-500 ml-1">*</span>}
                  </Label>
                  {checklistValues[field.id] && (
                    <CheckCircle className="h-4 w-4 text-green-600" />
                  )}
                </div>
              ))}
            </div>
            
            {/* Extra Fields (text inputs for things like share code) */}
            {template.extra_fields?.length > 0 && (
              <>
                <Separator />
                <div className="space-y-3">
                  <Label className="text-sm font-medium">Additional Information</Label>
                  {template.extra_fields.map(field => (
                    <div key={field.id} className="space-y-1">
                      <Label htmlFor={field.id} className="text-sm text-gray-600">
                        {field.label}
                      </Label>
                      {field.type === 'select' ? (
                        <Select 
                          value={extraFieldValues[field.id] || ''} 
                          onValueChange={(v) => handleExtraFieldChange(field.id, v)}
                        >
                          <SelectTrigger>
                            <SelectValue placeholder={`Select ${field.label.toLowerCase()}`} />
                          </SelectTrigger>
                          <SelectContent>
                            {field.options?.map(opt => (
                              <SelectItem key={opt} value={opt}>
                                {opt.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      ) : (
                        <Input
                          id={field.id}
                          value={extraFieldValues[field.id] || ''}
                          onChange={(e) => handleExtraFieldChange(field.id, e.target.value)}
                          placeholder={`Enter ${field.label.toLowerCase()}`}
                          data-testid={`extra-${field.id}`}
                        />
                      )}
                    </div>
                  ))}
                </div>
              </>
            )}
            
            {/* Admin Notes */}
            <div className="space-y-2">
              <Label htmlFor="admin-notes" className="text-sm font-medium">
                Additional Notes (Optional)
              </Label>
              <Textarea
                id="admin-notes"
                value={adminNotes}
                onChange={(e) => setAdminNotes(e.target.value)}
                placeholder="Any additional observations or notes about this verification..."
                rows={3}
                data-testid="admin-notes"
              />
            </div>
            
            {/* Status Summary */}
            <Card className={allRequiredChecked() && verificationMethod ? "border-green-300 bg-green-50" : "border-yellow-300 bg-yellow-50"}>
              <CardContent className="py-3">
                <div className="flex items-center gap-2">
                  {allRequiredChecked() && verificationMethod ? (
                    <>
                      <CheckCircle className="h-5 w-5 text-green-600" />
                      <span className="text-sm font-medium text-green-700">
                        Ready to submit and approve verification
                      </span>
                    </>
                  ) : (
                    <>
                      <AlertTriangle className="h-5 w-5 text-yellow-600" />
                      <span className="text-sm font-medium text-yellow-700">
                        Please complete all required items
                      </span>
                    </>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        ) : (
          <div className="py-8 text-center text-gray-500">
            No template available for this requirement type
          </div>
        )}
        
        <DialogFooter className="gap-2">
          <Button variant="outline" onClick={onClose} disabled={submitting}>
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={submitting || !allRequiredChecked() || !verificationMethod}
            className="bg-green-600 hover:bg-green-700"
            data-testid="submit-verification-btn"
          >
            {submitting ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Submitting...
              </>
            ) : (
              <>
                <CheckCircle className="h-4 w-4 mr-2" />
                Complete Verification
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
