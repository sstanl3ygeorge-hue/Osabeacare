import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Textarea } from '../../components/ui/textarea';
import { Label } from '../../components/ui/label';
import { 
  GraduationCap, CheckCircle, XCircle, Loader2, AlertTriangle,
  Upload, Home, Clock, FileText, Plus, X, Send
} from 'lucide-react';
import { toast } from 'sonner';
import { API_BASE_URL, API_ROOT_URL } from './';

const API = API_ROOT_URL;

/**
 * TrainingUploadPage - Public page for employees to upload training certificates
 * 
 * Flow:
 * 1. Employee receives email with secure link
 * 2. Opens link (no login required)
 * 3. Uploads one or more training certificates
 * 4. Certificates enter extraction + review queue
 */
export default function TrainingUploadPage() {
  const { token } = useParams();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [pageData, setPageData] = useState(null);
  const [files, setFiles] = useState([]);
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);

  useEffect(() => {
    fetchPageData();
  }, [token]);

  const fetchPageData = async () => {
    try {
      const response = await axios.get(`${API}/api/training/respond/${token}`);
      setPageData(response.data);
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (err.response?.status === 410 || detail?.includes('expired')) {
        setError({ type: 'expired', message: 'This link has expired. Please contact your administrator for a new link.' });
      } else if (detail?.includes('invalid')) {
        setError({ type: 'invalid', message: 'This link is invalid or has already been used.' });
      } else {
        setError({ type: 'error', message: detail || 'Failed to load the upload page' });
      }
    } finally {
      setLoading(false);
    }
  };

  const handleFileChange = (e) => {
    const newFiles = Array.from(e.target.files);
    
    // Validate files
    const validFiles = newFiles.filter(file => {
      const isValid = file.type === 'application/pdf' || file.type.startsWith('image/');
      const isSmallEnough = file.size <= 10 * 1024 * 1024; // 10MB
      
      if (!isValid) {
        toast.error(`${file.name} is not a valid file type. Please upload PDF or image files.`);
      }
      if (!isSmallEnough) {
        toast.error(`${file.name} is too large. Maximum file size is 10MB.`);
      }
      
      return isValid && isSmallEnough;
    });

    setFiles(prev => [...prev, ...validFiles]);
  };

  const removeFile = (index) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (files.length === 0) {
      toast.error('Please select at least one file to upload');
      return;
    }

    setSubmitting(true);
    setUploadProgress(0);

    try {
      const formData = new FormData();
      files.forEach(file => formData.append('files', file));
      if (notes.trim()) {
        formData.append('notes', notes.trim());
      }

      await axios.post(`${API}/api/training/respond/${token}/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (progressEvent) => {
          const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          setUploadProgress(percent);
        }
      });

      setSubmitted(true);
      toast.success('Training certificates uploaded successfully!');
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (err.response?.status === 410) {
        setError({ type: 'expired', message: 'This link has expired. Please contact your administrator for a new link.' });
      } else {
        toast.error(detail || 'Failed to upload certificates. Please try again.');
      }
    } finally {
      setSubmitting(false);
    }
  };

  // Loading state
  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-blue-50 to-white flex items-center justify-center p-4">
        <Card className="w-full max-w-md shadow-lg">
          <CardContent className="p-8 text-center">
            <Loader2 className="h-12 w-12 mx-auto animate-spin text-primary mb-4" />
            <p className="text-text-muted">Loading...</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Error states
  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-blue-50 to-white flex items-center justify-center p-4">
        <Card className="w-full max-w-md shadow-lg">
          <CardContent className="p-8 text-center">
            {error.type === 'expired' ? (
              <Clock className="h-16 w-16 mx-auto text-amber-500 mb-4" />
            ) : (
              <XCircle className="h-16 w-16 mx-auto text-red-500 mb-4" />
            )}
            <h2 className="text-xl font-heading font-semibold text-text-primary mb-2">
              {error.type === 'expired' ? 'Link Expired' : 'Unable to Load'}
            </h2>
            <p className="text-text-muted mb-6">{error.message}</p>
            <Link to="/">
              <Button variant="outline" className="rounded-xl">
                <Home className="h-4 w-4 mr-2" />
                Return to Home
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Success state
  if (submitted) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-green-50 to-white flex items-center justify-center p-4">
        <Card className="w-full max-w-md shadow-lg">
          <CardContent className="p-8 text-center">
            <div className="w-20 h-20 mx-auto bg-green-100 rounded-full flex items-center justify-center mb-6">
              <CheckCircle className="h-12 w-12 text-green-600" />
            </div>
            <h2 className="text-2xl font-heading font-semibold text-text-primary mb-2">
              Upload Complete!
            </h2>
            <p className="text-text-muted mb-6">
              Your training certificates have been submitted successfully. 
              The compliance team will review them shortly.
            </p>
            <div className="p-4 bg-gray-50 rounded-xl mb-6 text-sm text-text-muted">
              <p>{files.length} certificate(s) uploaded</p>
            </div>
            <Link to="/">
              <Button className="bg-primary hover:bg-primary-hover text-white rounded-xl">
                <Home className="h-4 w-4 mr-2" />
                Return to Home
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Main upload form
  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-white py-8 px-4">
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 mx-auto bg-primary/10 rounded-full flex items-center justify-center mb-4">
            <GraduationCap className="h-8 w-8 text-primary" />
          </div>
          <h1 className="text-2xl sm:text-3xl font-heading font-bold text-text-primary mb-2">
            Training Certificate Upload
          </h1>
          {pageData?.employee_name && (
            <p className="text-text-muted">
              For: <span className="font-medium text-text-primary">{pageData.employee_name}</span>
            </p>
          )}
        </div>

        {/* Custom Message from Admin */}
        {pageData?.custom_message && (
          <Card className="mb-6 border-blue-200 bg-blue-50/50">
            <CardContent className="p-4">
              <div className="flex items-start gap-3">
                <AlertTriangle className="h-5 w-5 text-blue-600 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="font-medium text-blue-800 text-sm">Message from HR:</p>
                  <p className="text-blue-700 text-sm mt-1">{pageData.custom_message}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Requested Training Types */}
        {pageData?.training_types?.length > 0 && (
          <Card className="mb-6 border-amber-200 bg-amber-50/50">
            <CardContent className="p-4">
              <p className="font-medium text-amber-800 text-sm mb-2">Certificates Requested:</p>
              <div className="flex flex-wrap gap-2">
                {pageData.training_types.map((type, idx) => (
                  <span 
                    key={idx}
                    className="px-2 py-1 bg-amber-100 text-amber-800 text-xs rounded-lg"
                  >
                    {type.replace(/_/g, ' ').replace(/training$/, '').trim()}
                  </span>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Due Date */}
        {pageData?.due_date && (
          <div className="flex items-center justify-center gap-2 mb-6 text-sm text-text-muted">
            <Clock className="h-4 w-4" />
            <span>Please submit by: </span>
            <span className="font-medium text-text-primary">
              {new Date(pageData.due_date).toLocaleDateString('en-GB', { 
                weekday: 'long', 
                year: 'numeric', 
                month: 'long', 
                day: 'numeric' 
              })}
            </span>
          </div>
        )}

        {/* Upload Form */}
        <Card className="shadow-lg">
          <CardHeader>
            <CardTitle className="font-heading">Upload Your Certificates</CardTitle>
            <CardDescription>
              Upload PDF or image files of your training certificates. You can upload multiple files.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* File Drop Zone */}
              <div className="space-y-3">
                <Label className="text-sm font-medium">Training Certificates *</Label>
                <div 
                  className="border-2 border-dashed border-gray-200 rounded-xl p-8 text-center hover:border-primary/50 transition-colors cursor-pointer"
                  onClick={() => document.getElementById('file-input').click()}
                  data-testid="file-drop-zone"
                >
                  <Upload className="h-10 w-10 mx-auto text-gray-400 mb-3" />
                  <p className="text-text-primary font-medium">Click to upload certificates</p>
                  <p className="text-sm text-text-muted mt-1">PDF, PNG, JPG up to 10MB each</p>
                  <input
                    id="file-input"
                    type="file"
                    multiple
                    accept=".pdf,.png,.jpg,.jpeg,image/*,application/pdf"
                    onChange={handleFileChange}
                    className="hidden"
                    data-testid="file-input"
                  />
                </div>

                {/* Selected Files List */}
                {files.length > 0 && (
                  <div className="space-y-2">
                    {files.map((file, index) => (
                      <div 
                        key={index}
                        className="flex items-center justify-between p-3 bg-[#F8FAFA] rounded-lg border"
                      >
                        <div className="flex items-center gap-3">
                          <FileText className="h-5 w-5 text-primary" />
                          <div>
                            <p className="text-sm font-medium text-text-primary">{file.name}</p>
                            <p className="text-xs text-text-muted">
                              {(file.size / 1024).toFixed(1)} KB
                            </p>
                          </div>
                        </div>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => removeFile(index)}
                          className="h-8 w-8 p-0 text-gray-400 hover:text-red-500"
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      </div>
                    ))}
                    
                    {/* Add More Button */}
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => document.getElementById('file-input').click()}
                      className="w-full rounded-lg"
                    >
                      <Plus className="h-4 w-4 mr-2" />
                      Add More Files
                    </Button>
                  </div>
                )}
              </div>

              {/* Notes */}
              <div className="space-y-2">
                <Label className="text-sm font-medium">Additional Notes (Optional)</Label>
                <Textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Any additional information about these certificates..."
                  className="rounded-lg min-h-[80px]"
                  maxLength={500}
                  data-testid="upload-notes"
                />
              </div>

              {/* Upload Progress */}
              {submitting && uploadProgress > 0 && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-text-muted">Uploading...</span>
                    <span className="font-medium">{uploadProgress}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div 
                      className="bg-primary h-2 rounded-full transition-all duration-300"
                      style={{ width: `${uploadProgress}%` }}
                    />
                  </div>
                </div>
              )}

              {/* Submit Button */}
              <Button
                type="submit"
                disabled={files.length === 0 || submitting}
                className="w-full bg-primary hover:bg-primary-hover text-white rounded-xl h-12"
                data-testid="submit-upload-btn"
              >
                {submitting ? (
                  <>
                    <Loader2 className="h-5 w-5 mr-2 animate-spin" />
                    Uploading...
                  </>
                ) : (
                  <>
                    <Send className="h-5 w-5 mr-2" />
                    Submit {files.length} Certificate{files.length !== 1 ? 's' : ''}
                  </>
                )}
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Help Text */}
        <p className="text-center text-xs text-text-muted mt-6">
          Having trouble? Contact your HR administrator for assistance.
        </p>
      </div>
    </div>
  );
}

