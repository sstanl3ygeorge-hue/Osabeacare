import React, { useState, useCallback } from 'react';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Badge } from '../ui/badge';
import { Checkbox } from '../ui/checkbox';
import { Label } from '../ui/label';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../ui/table';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select';
import {
  Upload,
  Loader2,
  FileText,
  CheckCircle,
  AlertTriangle,
  Wand2,
  Calendar,
  Edit2,
  Trash2,
  Plus
} from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '../../lib/utils';
import { useDropzone } from 'react-dropzone';

const API = process.env.REACT_APP_BACKEND_URL;

// Common CSTF trainings for quick selection
const COMMON_CSTF_TRAININGS = [
  { name: "CSTF Fire Safety", validity: "1 year" },
  { name: "CSTF Moving & Handling", validity: "1 year" },
  { name: "CSTF Safeguarding Adults", validity: "3 years" },
  { name: "CSTF Infection Prevention and Control", validity: "1 year" },
  { name: "CSTF Health & Safety", validity: "3 years" },
  { name: "CSTF Basic Life Support", validity: "1 year" },
  { name: "CSTF Information Governance / GDPR", validity: "1 year" },
  { name: "CSTF Equality, Diversity and Human Rights", validity: "3 years" },
  { name: "CSTF Preventing Radicalisation (PREVENT)", validity: "3 years" },
  { name: "CSTF NHS Conflict Resolution", validity: "3 years" },
  { name: "CSTF Food Hygiene", validity: "3 years" },
  { name: "CSTF Medication Awareness", validity: "1 year" },
  { name: "CSTF Dementia Awareness", validity: "3 years" },
  { name: "CSTF Mental Capacity Act", validity: "3 years" },
  { name: "CSTF Safeguarding Children (Optional)", validity: "3 years" },
  { name: "Other", validity: null },
];

/**
 * TrainingCertificateExtractor - AI-powered training extraction with preview step
 * 
 * Features:
 * 1. Upload PDF/image certificates
 * 2. AI extracts all training records (handles multi-course tables)
 * 3. Preview step allows admin to review, select, edit dates
 * 4. Manual entry option
 * 5. Save selected records to profile
 */
export default function TrainingCertificateExtractor({ 
  employeeId, 
  employeeName,
  isOpen, 
  onClose, 
  onSuccess 
}) {
  const { token } = useAuth();
  const [uploadedFile, setUploadedFile] = useState(null);
  const [extracting, setExtracting] = useState(false);
  const [extractedTrainings, setExtractedTrainings] = useState([]);
  const [selectedItems, setSelectedItems] = useState([]);
  const [saving, setSaving] = useState(false);
  const [showManualEntry, setShowManualEntry] = useState(false);
  const [manualEntry, setManualEntry] = useState({
    name: '',
    completion_date: '',
    expiry_date: '',
    reason: '',
    showCustomName: false
  });

  // Dropzone for file upload
  const onDrop = useCallback((acceptedFiles) => {
    if (acceptedFiles.length > 0) {
      setUploadedFile(acceptedFiles[0]);
      setExtractedTrainings([]);
      setSelectedItems([]);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'image/*': ['.png', '.jpg', '.jpeg', '.webp']
    },
    maxFiles: 1
  });

  // Extract trainings using AI
  const handleExtract = async () => {
    if (!uploadedFile) {
      toast.error('Please upload a certificate first');
      return;
    }

    setExtracting(true);

    try {
      const formData = new FormData();
      formData.append('file', uploadedFile);

      const response = await axios.post(
        `${API}/api/employees/${employeeId}/training/extract-certificate`,
        formData,
        {
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'multipart/form-data'
          }
        }
      );

      const trainings = response.data.trainings || [];
      
      if (trainings.length === 0) {
        toast.warning('No training records detected in this certificate');
      } else {
        toast.success(`Extracted ${trainings.length} training record(s)`);
        setExtractedTrainings(trainings.map((t, idx) => ({
          ...t,
          id: `extracted_${idx}`,
          selected: true
        })));
        setSelectedItems(trainings.map((_, idx) => idx));
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to extract training data');
    } finally {
      setExtracting(false);
    }
  };

  // Toggle item selection
  const toggleSelection = (index) => {
    setSelectedItems(prev => 
      prev.includes(index) 
        ? prev.filter(i => i !== index)
        : [...prev, index]
    );
  };

  // Select/deselect all
  const toggleAllSelection = () => {
    if (selectedItems.length === extractedTrainings.length) {
      setSelectedItems([]);
    } else {
      setSelectedItems(extractedTrainings.map((_, idx) => idx));
    }
  };

  // Edit a training item
  const handleEditItem = (index, field, value) => {
    setExtractedTrainings(prev => 
      prev.map((item, idx) => 
        idx === index ? { ...item, [field]: value } : item
      )
    );
  };

  // Delete a training item
  const handleDeleteItem = (index) => {
    setExtractedTrainings(prev => prev.filter((_, idx) => idx !== index));
    setSelectedItems(prev => prev.filter(i => i !== index).map(i => i > index ? i - 1 : i));
  };

  // Add manual entry
  const handleAddManual = () => {
    if (!manualEntry.name || !manualEntry.completion_date) {
      toast.error('Training name and completion date are required');
      return;
    }

    // Check if training is optional (Safeguarding Children)
    const isOptional = manualEntry.name.toLowerCase().includes('safeguarding') && 
                       manualEntry.name.toLowerCase().includes('children');

    setExtractedTrainings(prev => [...prev, {
      id: `manual_${Date.now()}`,
      training_name: manualEntry.name,
      completion_date: manualEntry.completion_date,
      expiry_date: manualEntry.expiry_date || null,
      provider: 'Manual Entry',
      confidence: 'high',
      manual: true,
      is_optional: isOptional
    }]);
    setSelectedItems(prev => [...prev, extractedTrainings.length]);
    setManualEntry({ name: '', completion_date: '', expiry_date: '', reason: '', showCustomName: false });
    setShowManualEntry(false);
    toast.success('Training added');
  };

  // Save selected items to profile
  const handleSaveSelected = async () => {
    const itemsToSave = selectedItems.map(idx => extractedTrainings[idx]).filter(Boolean);
    
    if (itemsToSave.length === 0) {
      toast.error('No items selected to save');
      return;
    }

    setSaving(true);

    try {
      const response = await axios.post(
        `${API}/api/employees/${employeeId}/training/bulk-save`,
        {
          trainings: itemsToSave.map(t => ({
            training_name: t.training_name,
            completion_date: t.completion_date,
            expiry_date: t.expiry_date,
            provider: t.provider,
            document_id: t.document_id
          }))
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      toast.success(response.data.message || `Submitted ${response.data.saved_count || itemsToSave.length} item(s) for review`);
      onSuccess?.();
      onClose();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to submit training items');
    } finally {
      setSaving(false);
    }
  };

  // Reset state when closing
  const handleClose = () => {
    setUploadedFile(null);
    setExtractedTrainings([]);
    setSelectedItems([]);
    setShowManualEntry(false);
    onClose();
  };

  // Format date for display
  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    try {
      return new Date(dateStr).toLocaleDateString('en-GB');
    } catch {
      return dateStr;
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Wand2 className="h-5 w-5 text-primary" />
            Extract Training from Certificate
          </DialogTitle>
          <DialogDescription>
            Upload a training certificate for {employeeName}. AI will extract all training records.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Upload Section */}
          {extractedTrainings.length === 0 && (
            <div
              {...getRootProps()}
              className={cn(
                "border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors",
                isDragActive ? "border-primary bg-primary/5" : "border-gray-300 hover:border-gray-400",
                uploadedFile && "border-green-500 bg-green-50"
              )}
            >
              <input {...getInputProps()} />
              <div className="flex flex-col items-center gap-3">
                {uploadedFile ? (
                  <>
                    <FileText className="h-10 w-10 text-green-600" />
                    <p className="font-medium text-green-700">{uploadedFile.name}</p>
                    <p className="text-sm text-gray-500">Click or drag to replace</p>
                  </>
                ) : (
                  <>
                    <Upload className="h-10 w-10 text-gray-400" />
                    <p className="font-medium text-gray-700">Drop certificate here or click to upload</p>
                    <p className="text-sm text-gray-500">Supports PDF, PNG, JPG (including multi-page)</p>
                  </>
                )}
              </div>
            </div>
          )}

          {/* Extract Button */}
          {uploadedFile && extractedTrainings.length === 0 && (
            <div className="flex justify-center">
              <Button
                onClick={handleExtract}
                disabled={extracting}
                className="gap-2"
                data-testid="extract-training-btn"
              >
                {extracting ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Extracting...
                  </>
                ) : (
                  <>
                    <Wand2 className="h-4 w-4" />
                    Extract Training Records
                  </>
                )}
              </Button>
            </div>
          )}

          {/* Preview Table */}
          {extractedTrainings.length > 0 && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium text-gray-700">
                  Detected {extractedTrainings.length} training record(s)
                </p>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={toggleAllSelection}
                    data-testid="toggle-all-btn"
                  >
                    {selectedItems.length === extractedTrainings.length ? 'Deselect All' : 'Select All'}
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setShowManualEntry(true)}
                    className="gap-1"
                    data-testid="add-manual-btn"
                  >
                    <Plus className="h-4 w-4" />
                    Add Manually
                  </Button>
                </div>
              </div>

              <div className="border rounded-lg overflow-hidden">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-gray-50">
                      <TableHead className="w-12">Select</TableHead>
                      <TableHead>Training Name</TableHead>
                      <TableHead>Completed</TableHead>
                      <TableHead>Valid Until</TableHead>
                      <TableHead>Confidence</TableHead>
                      <TableHead className="w-20">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {extractedTrainings.map((training, idx) => (
                      <TableRow 
                        key={training.id}
                        className={cn(
                          selectedItems.includes(idx) ? "bg-blue-50" : "",
                          training.manual && "bg-purple-50"
                        )}
                      >
                        <TableCell>
                          <Checkbox
                            checked={selectedItems.includes(idx)}
                            onCheckedChange={() => toggleSelection(idx)}
                            data-testid={`select-training-${idx}`}
                          />
                        </TableCell>
                        <TableCell>
                          <Input
                            value={training.training_name || ''}
                            onChange={(e) => handleEditItem(idx, 'training_name', e.target.value)}
                            className="border-0 bg-transparent p-0 h-auto focus:ring-0"
                          />
                        </TableCell>
                        <TableCell>
                          <Input
                            type="date"
                            value={training.completion_date || ''}
                            onChange={(e) => handleEditItem(idx, 'completion_date', e.target.value)}
                            className="border-0 bg-transparent p-0 h-auto w-32 focus:ring-0"
                          />
                        </TableCell>
                        <TableCell>
                          <Input
                            type="date"
                            value={training.expiry_date || ''}
                            onChange={(e) => handleEditItem(idx, 'expiry_date', e.target.value)}
                            className="border-0 bg-transparent p-0 h-auto w-32 focus:ring-0"
                            placeholder="Optional"
                          />
                        </TableCell>
                        <TableCell>
                          <div className="flex flex-col gap-1">
                            {training.is_optional && (
                              <Badge className="bg-gray-100 text-gray-600 text-[10px]">Optional</Badge>
                            )}
                            {training.manual ? (
                              <Badge className="bg-purple-100 text-purple-700">Manual</Badge>
                            ) : training.confidence === 'high' ? (
                              <Badge className="bg-green-100 text-green-700">High</Badge>
                            ) : training.confidence === 'medium' ? (
                              <Badge className="bg-amber-100 text-amber-700">Medium</Badge>
                            ) : (
                              <Badge className="bg-red-100 text-red-700">Low</Badge>
                            )}
                          </div>
                        </TableCell>
                        <TableCell>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleDeleteItem(idx)}
                            className="text-red-500 hover:text-red-700"
                            data-testid={`delete-training-${idx}`}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              <p className="text-sm text-gray-500">
                {selectedItems.length} of {extractedTrainings.length} selected for import
              </p>
            </div>
          )}

          {/* Manual Entry Form */}
          {showManualEntry && (
            <div className="border rounded-lg p-4 space-y-4 bg-purple-50">
              <h4 className="font-medium flex items-center gap-2">
                <Plus className="h-4 w-4" />
                Add Training Manually
              </h4>
              <p className="text-xs text-gray-500">
                If AI missed a training from the certificate, add it manually here.
              </p>
              <div className="grid grid-cols-2 gap-4">
                <div className="col-span-2">
                  <Label>Select Training Type</Label>
                  <Select 
                    value={manualEntry.name}
                    onValueChange={(value) => {
                      const training = COMMON_CSTF_TRAININGS.find(t => t.name === value);
                      setManualEntry(prev => ({ 
                        ...prev, 
                        name: value === 'Other' ? '' : value,
                        showCustomName: value === 'Other'
                      }));
                      // Auto-calculate expiry if we have completion date and validity
                      if (manualEntry.completion_date && training?.validity) {
                        const years = parseInt(training.validity);
                        if (!isNaN(years)) {
                          const date = new Date(manualEntry.completion_date);
                          date.setFullYear(date.getFullYear() + years);
                          setManualEntry(prev => ({ 
                            ...prev, 
                            name: value === 'Other' ? '' : value,
                            showCustomName: value === 'Other',
                            expiry_date: date.toISOString().split('T')[0]
                          }));
                        }
                      }
                    }}
                  >
                    <SelectTrigger data-testid="manual-training-select">
                      <SelectValue placeholder="Select a CSTF training..." />
                    </SelectTrigger>
                    <SelectContent>
                      {COMMON_CSTF_TRAININGS.map(training => (
                        <SelectItem key={training.name} value={training.name}>
                          {training.name} {training.validity && `(${training.validity})`}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                {manualEntry.showCustomName && (
                  <div className="col-span-2">
                    <Label>Custom Training Name *</Label>
                    <Input
                      value={manualEntry.name}
                      onChange={(e) => setManualEntry(prev => ({ ...prev, name: e.target.value }))}
                      placeholder="Enter training name..."
                      data-testid="manual-training-name"
                    />
                  </div>
                )}
                <div>
                  <Label>Completion Date *</Label>
                  <Input
                    type="date"
                    value={manualEntry.completion_date}
                    onChange={(e) => setManualEntry(prev => ({ ...prev, completion_date: e.target.value }))}
                    data-testid="manual-completion-date"
                  />
                </div>
                <div>
                  <Label>Expiry Date (Optional)</Label>
                  <Input
                    type="date"
                    value={manualEntry.expiry_date}
                    onChange={(e) => setManualEntry(prev => ({ ...prev, expiry_date: e.target.value }))}
                    data-testid="manual-expiry-date"
                  />
                </div>
                <div className="col-span-2">
                  <Label>Reason for Manual Entry</Label>
                  <Input
                    value={manualEntry.reason}
                    onChange={(e) => setManualEntry(prev => ({ ...prev, reason: e.target.value }))}
                    placeholder="e.g., AI missed this training from certificate"
                    data-testid="manual-reason"
                  />
                </div>
              </div>
              <div className="flex gap-2">
                <Button onClick={handleAddManual} data-testid="save-manual-btn">
                  Add Training
                </Button>
                <Button variant="outline" onClick={() => setShowManualEntry(false)}>
                  Cancel
                </Button>
              </div>
            </div>
          )}
        </div>

        <DialogFooter className="gap-2">
          <Button variant="outline" onClick={handleClose}>
            Cancel
          </Button>
          {extractedTrainings.length > 0 && (
            <Button
              onClick={handleSaveSelected}
              disabled={saving || selectedItems.length === 0}
              className="gap-2"
              data-testid="save-selected-btn"
            >
              {saving ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <CheckCircle className="h-4 w-4" />
                  Submit {selectedItems.length} Selected for Review
                </>
              )}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
