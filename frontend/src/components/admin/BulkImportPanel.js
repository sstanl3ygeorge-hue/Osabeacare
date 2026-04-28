import { useState, useRef } from 'react';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Checkbox } from '../ui/checkbox';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '../ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../ui/table';
import { toast } from 'sonner';
import { 
  Upload, FileText, Loader2, CheckCircle, XCircle, AlertTriangle,
  Trash2, Edit2, Send, RefreshCw, Download, Users, Sparkles
} from 'lucide-react';
import { cn } from '../../lib/utils';

const API = API_BASE;

/**
 * BulkImportPanel - AI-powered PDF application import
 * 
 * Flow:
 * 1. Upload PDF files
 * 2. AI extracts data from each PDF
 * 3. Admin reviews and edits extracted data
 * 4. Confirm to create draft employees
 * 5. Send magic links manually later
 */
export default function BulkImportPanel() {
  const { token } = useAuth();
  const fileInputRef = useRef(null);
  
  // Upload state
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [extracting, setExtracting] = useState(false);
  const [extractionProgress, setExtractionProgress] = useState({ current: 0, total: 0 });
  
  // Extracted data state
  const [extractedRecords, setExtractedRecords] = useState([]);
  const [selectedRecords, setSelectedRecords] = useState([]);
  
  // Import state
  const [importing, setImporting] = useState(false);
  const [importResults, setImportResults] = useState(null);
  
  // Edit dialog
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editingRecord, setEditingRecord] = useState(null);
  const [editingIndex, setEditingIndex] = useState(null);

  const handleFileSelect = (e) => {
    const files = Array.from(e.target.files);
    const pdfFiles = files.filter(f => f.name.toLowerCase().endsWith('.pdf'));
    
    if (pdfFiles.length !== files.length) {
      toast.warning('Some files were skipped - only PDF files are supported');
    }
    
    setUploadedFiles(prev => [...prev, ...pdfFiles]);
  };

  const removeFile = (index) => {
    setUploadedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const extractAllPDFs = async () => {
    if (uploadedFiles.length === 0) {
      toast.error('Please upload PDF files first');
      return;
    }

    setExtracting(true);
    setExtractionProgress({ current: 0, total: uploadedFiles.length });
    const results = [];

    for (let i = 0; i < uploadedFiles.length; i++) {
      const file = uploadedFiles[i];
      setExtractionProgress({ current: i + 1, total: uploadedFiles.length });

      try {
        const formData = new FormData();
        formData.append('file', file);

        const response = await axios.post(
          `${API}/admin/employees/extract-from-pdf`,
          formData,
          {
            headers: {
              Authorization: `Bearer ${token}`,
              'Content-Type': 'multipart/form-data'
            }
          }
        );

        results.push({
          filename: file.name,
          status: 'success',
          data: response.data.extracted_data,
          confidence: response.data.extracted_data.extraction_confidence
        });
      } catch (error) {
        results.push({
          filename: file.name,
          status: 'error',
          error: error.response?.data?.detail || 'Extraction failed',
          data: null
        });
      }
    }

    setExtractedRecords(results);
    setSelectedRecords(results.filter(r => r.status === 'success').map((_, i) => i));
    setExtracting(false);
    setUploadedFiles([]);

    const successCount = results.filter(r => r.status === 'success').length;
    toast.success(`Extracted ${successCount} of ${results.length} PDFs`);
  };

  const toggleRecordSelection = (index) => {
    setSelectedRecords(prev => 
      prev.includes(index) 
        ? prev.filter(i => i !== index)
        : [...prev, index]
    );
  };

  const selectAllRecords = () => {
    const successIndexes = extractedRecords
      .map((r, i) => r.status === 'success' ? i : -1)
      .filter(i => i >= 0);
    setSelectedRecords(successIndexes);
  };

  const deselectAllRecords = () => {
    setSelectedRecords([]);
  };

  const openEditDialog = (record, index) => {
    setEditingRecord({ ...record.data });
    setEditingIndex(index);
    setEditDialogOpen(true);
  };

  const saveEditedRecord = () => {
    if (editingIndex === null) return;
    
    setExtractedRecords(prev => {
      const updated = [...prev];
      updated[editingIndex] = {
        ...updated[editingIndex],
        data: editingRecord
      };
      return updated;
    });
    
    setEditDialogOpen(false);
    setEditingRecord(null);
    setEditingIndex(null);
    toast.success('Record updated');
  };

  const removeRecord = (index) => {
    setExtractedRecords(prev => prev.filter((_, i) => i !== index));
    setSelectedRecords(prev => prev.filter(i => i !== index).map(i => i > index ? i - 1 : i));
  };

  // Send magic link option
  const [sendMagicLinks, setSendMagicLinks] = useState(false);

  const importSelectedRecords = async () => {
    const recordsToImport = selectedRecords
      .map(i => extractedRecords[i])
      .filter(r => r.status === 'success' && r.data);

    if (recordsToImport.length === 0) {
      toast.error('No valid records selected for import');
      return;
    }

    setImporting(true);

    try {
      // Transform extracted data to match bulk import format
      const employees = recordsToImport.map(record => {
        const d = record.data;
        const pd = d.personal_details || {};
        
        return {
          first_name: pd.first_name || '',
          last_name: pd.last_name || '',
          email: pd.email || '',
          phone: pd.phone || '',
          role: d.role || 'Healthcare Assistant',
          date_of_birth: pd.date_of_birth,
          address: pd.address,
          national_insurance: pd.national_insurance,
          employment_history: (d.employment_history || []).map(eh => ({
            employer: eh.employer,
            job_title: eh.job_title,
            start_date: eh.start_date,
            end_date: eh.end_date,
            is_current: eh.is_current || false,
            responsibilities: eh.responsibilities
          })),
          references: (d.references || []).map(ref => ({
            name: ref.name,
            email: ref.email,
            phone: ref.phone,
            organisation: ref.organisation,
            relationship: ref.relationship
          })),
          declarations: d.declarations,
          emergency_contact: d.emergency_contact,
          send_magic_link: sendMagicLinks // Send portal access if checkbox is checked
        };
      });

      const response = await axios.post(
        `${API}/admin/employees/bulk-import`,
        { employees },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      setImportResults(response.data.results);
      
      // Clear successfully imported records
      const createdEmails = response.data.results.created.map(c => c.email.toLowerCase());
      setExtractedRecords(prev => prev.filter(r => 
        r.status !== 'success' || 
        !createdEmails.includes(r.data?.personal_details?.email?.toLowerCase())
      ));
      setSelectedRecords([]);

      const magicLinksMsg = sendMagicLinks && response.data.results.magic_links_sent > 0 
        ? ` (${response.data.results.magic_links_sent} welcome emails sent)` 
        : '';
      toast.success(`Imported ${response.data.results.created.length} employees${magicLinksMsg}`);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Import failed');
    } finally {
      setImporting(false);
    }
  };

  const getConfidenceBadge = (confidence) => {
    switch (confidence) {
      case 'high':
        return <Badge className="bg-green-100 text-green-700">High Confidence</Badge>;
      case 'medium':
        return <Badge className="bg-amber-100 text-amber-700">Medium Confidence</Badge>;
      case 'low':
        return <Badge className="bg-red-100 text-red-700">Low Confidence</Badge>;
      default:
        return <Badge variant="outline">Unknown</Badge>;
    }
  };

  return (
    <div className="space-y-6 p-6" data-testid="bulk-import-panel">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Users className="h-6 w-6 text-primary" />
            Bulk PDF Import
          </h1>
          <p className="text-gray-500 mt-1">
            Import existing paper applications using AI extraction
          </p>
        </div>
      </div>

      {/* Step 1: Upload PDFs */}
      <Card className="border-gray-200 shadow-sm">
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Upload className="h-5 w-5 text-primary" />
            Step 1: Upload PDF Applications
          </CardTitle>
          <CardDescription>
            Upload scanned or digital PDF application forms. AI will extract employee data.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileSelect}
            accept=".pdf"
            multiple
            className="hidden"
          />
          
          <div 
            className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-primary/50 transition-colors cursor-pointer"
            onClick={() => fileInputRef.current?.click()}
          >
            <FileText className="h-12 w-12 mx-auto text-gray-400 mb-4" />
            <p className="text-gray-600 mb-2">Click to upload PDF files or drag and drop</p>
            <p className="text-sm text-gray-400">Only PDF files are supported</p>
          </div>

          {/* Uploaded files list */}
          {uploadedFiles.length > 0 && (
            <div className="mt-4 space-y-2">
              <p className="text-sm font-medium text-gray-700">{uploadedFiles.length} files ready for extraction:</p>
              {uploadedFiles.map((file, index) => (
                <div key={index} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                  <span className="text-sm flex items-center gap-2">
                    <FileText className="h-4 w-4 text-red-500" />
                    {file.name}
                  </span>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => removeFile(index)}
                    className="h-8 w-8 p-0 text-gray-400 hover:text-red-500"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              ))}
              
              <Button 
                onClick={extractAllPDFs} 
                disabled={extracting}
                className="mt-4"
                data-testid="extract-pdfs-btn"
              >
                {extracting ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Extracting ({extractionProgress.current}/{extractionProgress.total})...
                  </>
                ) : (
                  <>
                    <Sparkles className="h-4 w-4 mr-2" />
                    Extract Data from {uploadedFiles.length} PDFs
                  </>
                )}
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Step 2: Review Extracted Data */}
      {extractedRecords.length > 0 && (
        <Card className="border-gray-200 shadow-sm">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-lg flex items-center gap-2">
                  <CheckCircle className="h-5 w-5 text-primary" />
                  Step 2: Review Extracted Data
                </CardTitle>
                <CardDescription>
                  Review and edit the extracted information before importing.
                </CardDescription>
              </div>
              <div className="flex items-center gap-2">
                <Button variant="outline" size="sm" onClick={selectAllRecords}>
                  Select All
                </Button>
                <Button variant="outline" size="sm" onClick={deselectAllRecords}>
                  Deselect All
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-12"></TableHead>
                  <TableHead>File</TableHead>
                  <TableHead>Name</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead>Confidence</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {extractedRecords.map((record, index) => (
                  <TableRow 
                    key={index}
                    className={cn(
                      record.status === 'error' && "bg-red-50",
                      selectedRecords.includes(index) && "bg-primary/5"
                    )}
                    data-testid={`extracted-record-${index}`}
                  >
                    <TableCell>
                      {record.status === 'success' && (
                        <Checkbox
                          checked={selectedRecords.includes(index)}
                          onCheckedChange={() => toggleRecordSelection(index)}
                        />
                      )}
                    </TableCell>
                    <TableCell className="font-medium text-sm">
                      {record.filename}
                    </TableCell>
                    <TableCell>
                      {record.status === 'success' ? (
                        `${record.data?.personal_details?.first_name || ''} ${record.data?.personal_details?.last_name || ''}`
                      ) : (
                        <span className="text-red-500">-</span>
                      )}
                    </TableCell>
                    <TableCell className="text-sm">
                      {record.data?.personal_details?.email || '-'}
                    </TableCell>
                    <TableCell className="text-sm">
                      {record.data?.role || '-'}
                    </TableCell>
                    <TableCell>
                      {record.status === 'success' ? (
                        getConfidenceBadge(record.confidence)
                      ) : (
                        '-'
                      )}
                    </TableCell>
                    <TableCell>
                      {record.status === 'success' ? (
                        <Badge className="bg-green-100 text-green-700">
                          <CheckCircle className="h-3 w-3 mr-1" />
                          Extracted
                        </Badge>
                      ) : (
                        <Badge className="bg-red-100 text-red-700">
                          <XCircle className="h-3 w-3 mr-1" />
                          Failed
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-1">
                        {record.status === 'success' && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => openEditDialog(record, index)}
                            className="h-8 w-8 p-0"
                            data-testid={`edit-record-${index}`}
                          >
                            <Edit2 className="h-4 w-4" />
                          </Button>
                        )}
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => removeRecord(index)}
                          className="h-8 w-8 p-0 text-red-500"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* Step 3: Import */}
      {extractedRecords.filter(r => r.status === 'success').length > 0 && (
        <Card className="border-gray-200 shadow-sm">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Users className="h-5 w-5 text-primary" />
              Step 3: Import Employees
            </CardTitle>
            <CardDescription>
              Create employee records from extracted PDF data. Workers can complete their profiles via the portal.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">
                  <strong>{selectedRecords.length}</strong> records selected for import
                </p>
              </div>
            </div>
            
            {/* Magic Link Option */}
            <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <Checkbox
                  id="send-magic-links"
                  checked={sendMagicLinks}
                  onCheckedChange={setSendMagicLinks}
                  className="mt-0.5"
                  data-testid="send-magic-links-checkbox"
                />
                <div>
                  <Label htmlFor="send-magic-links" className="text-sm font-medium text-purple-900 cursor-pointer">
                    Send Welcome Emails with Portal Access Links
                  </Label>
                  <p className="text-xs text-purple-700 mt-1">
                    Each worker will receive an email with a magic link to access their portal and complete their profile.
                    {sendMagicLinks && (
                      <span className="block mt-1 font-medium">
                        Workers will be guided through the Profile Completion Wizard to fill in any missing information.
                      </span>
                    )}
                  </p>
                </div>
              </div>
            </div>
            
            <div className="flex justify-end">
              <Button
                onClick={importSelectedRecords}
                disabled={importing || selectedRecords.length === 0}
                className={sendMagicLinks ? "bg-purple-600 hover:bg-purple-700" : ""}
                data-testid="import-btn"
              >
                {importing ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    {sendMagicLinks ? 'Importing & Sending...' : 'Importing...'}
                  </>
                ) : (
                  <>
                    {sendMagicLinks ? <Send className="h-4 w-4 mr-2" /> : <Download className="h-4 w-4 mr-2" />}
                    {sendMagicLinks 
                      ? `Import & Send Links (${selectedRecords.length})`
                      : `Import ${selectedRecords.length} Records`
                    }
                  </>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Import Results */}
      {importResults && (
        <Card className="border-green-200 shadow-sm bg-green-50/50">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2 text-green-700">
              <CheckCircle className="h-5 w-5" />
              Import Complete
import API_BASE from '../../utils/apiBase';
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <p className="text-green-700">
                Successfully created <strong>{importResults.created?.length || 0}</strong> draft employees.
              </p>
              
              {importResults.created?.length > 0 && (
                <div className="bg-white rounded-lg p-4 border border-green-200">
                  <p className="text-sm font-medium mb-2">Created Employees:</p>
                  <ul className="text-sm space-y-1">
                    {importResults.created.map((emp, i) => (
                      <li key={i} className="flex items-center gap-2">
                        <CheckCircle className="h-3 w-3 text-green-500" />
                        {emp.name} ({emp.email}) - Ref: {emp.applicant_reference}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {importResults.errors?.length > 0 && (
                <div className="bg-red-50 rounded-lg p-4 border border-red-200">
                  <p className="text-sm font-medium text-red-700 mb-2">Errors:</p>
                  <ul className="text-sm space-y-1 text-red-600">
                    {importResults.errors.map((err, i) => (
                      <li key={i} className="flex items-center gap-2">
                        <XCircle className="h-3 w-3" />
                        {err.email}: {err.error}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="pt-4 border-t border-green-200">
                <p className="text-sm text-gray-600 mb-3">
                  Next: Go to Recruitment page to review and send magic links to employees.
                </p>
                <Button variant="outline" asChild>
                  <a href="/portal/recruitment">
                    <Send className="h-4 w-4 mr-2" />
                    Go to Recruitment Page
                  </a>
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Edit Dialog */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Edit Extracted Data</DialogTitle>
            <DialogDescription>
              Review and correct the AI-extracted information.
            </DialogDescription>
          </DialogHeader>
          
          {editingRecord && (
            <div className="space-y-6 py-4">
              {/* Personal Details */}
              <div className="space-y-4">
                <h4 className="font-medium text-gray-700 border-b pb-2">Personal Details</h4>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>First Name *</Label>
                    <Input
                      value={editingRecord.personal_details?.first_name || ''}
                      onChange={(e) => setEditingRecord({
                        ...editingRecord,
                        personal_details: { ...editingRecord.personal_details, first_name: e.target.value }
                      })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Last Name *</Label>
                    <Input
                      value={editingRecord.personal_details?.last_name || ''}
                      onChange={(e) => setEditingRecord({
                        ...editingRecord,
                        personal_details: { ...editingRecord.personal_details, last_name: e.target.value }
                      })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Email *</Label>
                    <Input
                      type="email"
                      value={editingRecord.personal_details?.email || ''}
                      onChange={(e) => setEditingRecord({
                        ...editingRecord,
                        personal_details: { ...editingRecord.personal_details, email: e.target.value }
                      })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Phone</Label>
                    <Input
                      value={editingRecord.personal_details?.phone || ''}
                      onChange={(e) => setEditingRecord({
                        ...editingRecord,
                        personal_details: { ...editingRecord.personal_details, phone: e.target.value }
                      })}
                    />
                  </div>
                </div>
              </div>

              {/* Role */}
              <div className="space-y-2">
                <Label>Role *</Label>
                <select
                  value={editingRecord.role || ''}
                  onChange={(e) => setEditingRecord({ ...editingRecord, role: e.target.value })}
                  className="w-full h-10 px-3 border border-gray-200 rounded-md"
                >
                  <option value="">Select role...</option>
                  <option value="Healthcare Assistant">Healthcare Assistant</option>
                  <option value="Senior Healthcare Assistant">Senior Healthcare Assistant</option>
                  <option value="Nurse (Registered)">Nurse (Registered)</option>
                  <option value="Senior Nurse">Senior Nurse</option>
                  <option value="Care Assistant">Care Assistant</option>
                  <option value="Support Worker">Support Worker</option>
                </select>
              </div>

              {/* Employment History Summary */}
              <div className="space-y-2">
                <h4 className="font-medium text-gray-700 border-b pb-2">Employment History</h4>
                {editingRecord.employment_history?.length > 0 ? (
                  <ul className="text-sm space-y-1">
                    {editingRecord.employment_history.map((eh, i) => (
                      <li key={i} className="p-2 bg-gray-50 rounded">
                        {eh.job_title} at {eh.employer} ({eh.start_date} - {eh.end_date || 'Present'})
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-gray-500">No employment history extracted</p>
                )}
              </div>

              {/* References Summary */}
              <div className="space-y-2">
                <h4 className="font-medium text-gray-700 border-b pb-2">References</h4>
                {editingRecord.references?.length > 0 ? (
                  <ul className="text-sm space-y-1">
                    {editingRecord.references.map((ref, i) => (
                      <li key={i} className="p-2 bg-gray-50 rounded">
                        {ref.name} - {ref.relationship} ({ref.email || ref.phone || 'No contact'})
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-gray-500">No references extracted</p>
                )}
              </div>

              {/* Extraction Notes */}
              {editingRecord.extraction_notes && (
                <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
                  <p className="text-sm text-amber-700">
                    <AlertTriangle className="h-4 w-4 inline mr-1" />
                    <strong>AI Notes:</strong> {editingRecord.extraction_notes}
                  </p>
                </div>
              )}
            </div>
          )}

          <DialogFooter>
            <Button variant="outline" onClick={() => setEditDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={saveEditedRecord}>
              Save Changes
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

